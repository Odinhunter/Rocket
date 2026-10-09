"""API smoke: a full Creative Read end-to-end through the two-phase
orchestrator — entities on disk -> RunConfig -> prepare() -> commit() ->
validated Report.

Asserts the run goes prepared -> committed -> complete cleanly, the credit
is debited exactly once at commit, all artifacts land on disk, and the
Report carries a bet_ranking headline + the L3.5 funnel projection.

⚠⚠ COST: THIS RUNS THE WHOLE PIPELINE **TWICE**, and the old quote here did
not say so. prepare() + commit() is the first; `RunService.run()` at the foot
of main() is a second complete prepare + commit for the convenience wrapper.
So: 2 x (9-agent panel, ~18 L1 calls + target_id + 3x L2 + L3 + L4 + assess +
prescribe) ≈ **$2.20-2.80**, not the $0.80-1.10 this docstring claimed for
years. The coverage is real and stays; the number was wrong.

Run: pytest tests/test_run_service_minimal.py --paid   (or: python tests/test_run_service_minimal.py)
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from dotenv import load_dotenv

load_dotenv()

from agent import credits
from agent.config import AssetSpec, RunConfig
from agent.entities import (
    Account,
    AudienceSpec,
    BrandProfile,
    DispositionLibrary,
)
from agent.run_service import RunService
from agent.schema import validate_report
from agent.telemetry import run_dir, runs_root, telemetry_summary
from agent.vectors import (
    ChaosDistribution,
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)

_ACCOUNT = "_test_rs_acct"
_BRAND = "_test_rs_brand"


def _cleanup() -> None:
    p = runs_root() / _ACCOUNT
    if p.exists():
        shutil.rmtree(p)


def _chaos() -> ChaosDistribution:
    def profile(label: str, dv: str) -> ChaosProfile:
        return ChaosProfile(
            label=label,
            vector=ChaosVector(
                decision_velocity=dv, suggestibility="medium",
                consistency="variable", risk_tolerance="balanced",
            ),
        )

    return ChaosDistribution(
        weighted=[
            (profile("impulsive", "impulsive"), 0.34),
            (profile("moderate", "moderate"), 0.33),
            (profile("deliberate", "deliberate"), 0.33),
        ]
    )


# ⚠⚠ THE THREE BUYER TYPES ARE READ OFF DISK, NOT HAND-WRITTEN HERE.
#
# Until 2026-08-22 this file rolled its own: `budget_deal_buyer` and
# `spec_skeptic`, both on one base vector, both with an EMPTY `anchor`, and
# neither leading with a stance the engine knows. Three separate things were
# wrong with that, and the first one is fatal:
#
#   1. ⚠⚠ `agent/preflight.py` BLOCKS a run whose labels carry no known stance,
#      at the top of prepare(), with no override flag. Verified offline: this
#      fixture raised PreflightError. The most expensive test in the tier could
#      not have reached its first model call. (Session 48 verified the preflight
#      against 8 packs x 7 installed libraries and never against a test fixture,
#      because these files were collecting nothing at the time.)
#   2. An empty `anchor` is a MEASURED realism defect, not a cosmetic one.
#      `docs/fnb_test_b_result.md` (#64): transplanting people WITHOUT their
#      anchor made the model contradict a man's own purchase history. The
#      biography is not enough; the anchor has to travel.
#   3. Two dispositions on one base vector is a panel that mostly agrees with
#      itself — `_SYSTEM` rule 3's own failure mode, and against the standing
#      directive that diversity of OPINION is the deliverable.
#
# ⭐ THE FIX IS THE ONE THIS REPO ALREADY WROTE DOWN — vacuous shape 4: copy a
# real artifact off disk rather than authoring a minimal one. `boat_audio` is
# the library for THIS AD (assets/sample_creative.png, category personal_audio), with
# seven convention-compliant types carrying real anchors.
#
# ⚠ THE THREE ARE CHOSEN FOR SPREAD, NOT FOR A FLATTERING VERDICT: one
# favorable, one hostile, one in the middle. ⭐ And the loyalist of the
# ADVERTISED brand is deliberate — that is the exact F1 shape `#79`/`#80`
# guards against (a brand's own customer crowned "right ad, wrong person"), so
# this run is the first time those guards see a real call.
_SOURCE_LIBRARY = Path("runs/demo/boat_audio/entities/library.json")
_WANTED = ("loyalist_airdopes", "skeptic_warranty", "pragmatist_urgent_replacement")


def _dispositions_from_disk() -> list[NamedDisposition]:
    """The three real buyer types, re-homed into this test's own account.

    ⚠ READ ONLY. The demo library is client-shaped data the app serves; this
    test writes exclusively under `_ACCOUNT`, which `_cleanup()` removes.
    """
    if not _SOURCE_LIBRARY.exists():
        raise SystemExit(f"missing source library: {_SOURCE_LIBRARY}")
    by_label = {
        d["label"]: d
        for d in json.loads(_SOURCE_LIBRARY.read_text())["dispositions"]
    }
    missing = [w for w in _WANTED if w not in by_label]
    if missing:
        raise SystemExit(
            f"{_SOURCE_LIBRARY} no longer carries {missing}. Pick replacements "
            f"with the same spread (one favorable, one hostile, one middle) "
            f"from: {sorted(by_label)}"
        )
    out = []
    for label in _WANTED:
        d = by_label[label]
        out.append(NamedDisposition(
            label=d["label"],
            vector=DispositionVector(**d["vector"]),
            anchor=d.get("anchor", ""),
            notes=d.get("notes", ""),
        ))
    assert all(d.anchor for d in out), (
        "a disposition arrived without its anchor — the anchor is the half "
        "that carries this person's history (#64)"
    )
    return out


def _context(label: str, **overrides) -> NamedContext:
    base = dict(
        attention_level="low", device_posture="commute",
        intent_state="killing_time", energy_state="drained",
        social_setting="public",
    )
    base.update(overrides)
    return NamedContext(label=label, vector=ContextVector(**base))


def _setup_entities() -> None:
    Account(account_id=_ACCOUNT, name="Test Co").save()
    BrandProfile(
        brand_profile_id=_BRAND, account_id=_ACCOUNT, categories=["personal_audio"],
        library_id="lib_1", audience_ids=["aud_1"],
    ).save()
    DispositionLibrary(
        library_id="lib_1", brand_profile_id=_BRAND, account_id=_ACCOUNT,
        dispositions=_dispositions_from_disk(),
    ).save()


def _config(**overrides) -> RunConfig:
    spec = AudienceSpec(
        demographics=[
            DemographicPoint(
                gender="male", age_band="25_34", income_tier="upper_mid",
                geography="Bangalore / metro tier-1",
            )
        ],
        disposition_labels=list(_WANTED),
        context_envelope=[
            _context("commute_scroll"),
            _context("pre_purchase_research", attention_level="high",
                     intent_state="actively_shopping", energy_state="alert"),
            _context("late_night_wind_down", energy_state="drained"),
        ],
        chaos_distribution=_chaos(),
        # ⚠⚠ 9, NOT 6, AND THE NUMBER IS LOAD-BEARING. 3 buyer types x 3
        # contexts x 1 demographic = a grid of 9. `_choose_cells` splits on
        # panel_size vs grid: at N >= G every cell is filled exactly once and
        # the panel is 3/3/3. At N < G it does a marginal-coverage pass and then
        # pads ROUND-ROBIN OVER THE GRID — and the grid is disposition-major, so
        # the whole remainder lands on whichever type sorts first.
        #
        # Measured at panel_size=6: 4 loyalists, 1 skeptic, 1 pragmatist. Two
        # thirds of the panel would have been the ADVERTISED BRAND'S OWN
        # CUSTOMER — the `#74`-`#76` shape (a loyalist-heavy sample inflating
        # the read) rebuilt one level down, in panel composition. Balance here
        # is neutrality, not a thumb on the scale.
        #
        # ⚠ Do not "save money" by dropping back to 6, and do not reorder
        # _WANTED to fix it — reordering only aims the skew at a different type.
        # The general defect is recorded in the handoff; it needs
        # `_choose_cells` to pad over DISPOSITIONS rather than over the grid,
        # and that is its own change with its own test.
        panel_size=9,
    )
    return RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat minimal"),
        archetype="urban_indian_male_22_30", category="personal_audio",
        account_id=_ACCOUNT, brand_profile_id=_BRAND,
        audience_spec=spec,
        segment_granularity="disposition",  # cheaper for the minimal gate
        library_id="lib_1", audience_id="aud_1",
        baseline_funnel={
            "stop_rate": 0.11, "click_rate": 0.018,
            "visit_rate": 0.014, "convert_rate": 0.005,
        },
        **overrides,
    )


def main() -> None:
    print("=== run_service minimal end-to-end ===")
    _cleanup()
    if not Path("assets/sample_creative.png").exists():
        raise SystemExit("missing test asset: assets/sample_creative.png")
    try:
        _setup_entities()
        config = _config()

        # --- prepare() — no credit debited ---
        prep = RunService.prepare(config)
        assert not credits.is_committed(prep.run_id, _ACCOUNT, _BRAND), (
            "prepare() debited a credit — it must not"
        )
        assert len(prep.panel) == 9, f"panel size {len(prep.panel)} != 9"
        seats = Counter(a.disposition_label for a in prep.panel)
        assert set(seats.values()) == {3}, (
            f"the panel is not balanced across the three buyer types: {dict(seats)}. "
            "At N == grid every cell fills exactly once; anything else means the "
            "grid moved and the remainder is piling onto whichever type sorts first."
        )
        assert prep.persona_cores_rendered >= 1
        assert prep.estimated_cost_usd > 0
        rd = run_dir(prep.run_id, account_id=_ACCOUNT, brand_profile_id=_BRAND)
        assert (rd / "preparation.json").exists()
        assert (rd / "panel.json").exists()
        assert (rd / "target_classification.json").exists()
        assert json.loads((rd / "run.json").read_text())["status"] == "prepared"
        print(f"  OK  prepare(): {len(prep.panel)} agents, "
              f"{prep.persona_cores_rendered} cores rendered, "
              f"est ${prep.estimated_cost_usd:.2f}, no credit debited")
        print(f"      inferred target: {prep.target_classification.inferred_target_description}")

        # --- commit() — credit debited exactly once, L1->L4 runs ---
        report = RunService.commit(prep)
        validate_report(report)
        assert credits.account_debits(_ACCOUNT) == 1, (
            f"expected exactly 1 credit debited, got {credits.account_debits(_ACCOUNT)}"
        )
        assert report.bet_ranking, "report has no bet_ranking"

        # ⚠⚠ THE FUNNEL IS OFF BY DEFAULT (v3 D4) AND THIS ASSERTION USED TO SAY
        # THE OPPOSITE. It read `is not None`, was written at rocket-2.0.0 when
        # the projection was always attached, and went stale the day `v3 #7`
        # gated it off — heuristic_v1 is unfitted, so it is computed and logged
        # for a future calibration fit but must not reach the customer or move
        # the prescription. Nobody found out for a year because pytest collected
        # ZERO functions from this file. ⭐ The first --paid run (2026-08-22)
        # found it on its first outing, which is the whole argument for the tier.
        assert report.funnel_projection is None, (
            "the funnel reached the report with funnel_enabled=False — v3 D4 "
            "says an unfitted heuristic must not reach the customer"
        )
        for artifact in (
            "transcripts.json", "l2_summaries.json", "l3_summary.json",
            "l35_projection.json", "committed.marker",
        ):
            assert (rd / artifact).exists(), f"missing artifact: {artifact}"
        # ⭐ AND IT IS STILL COMPUTED: withheld from the report, persisted for
        # the calibration fit. "Off" must mean "not shown", never "not recorded".
        l35 = json.loads((rd / "l35_projection.json").read_text())
        assert l35["overall"]["basis"] == "heuristic_v1"

        run_json = json.loads((rd / "run.json").read_text())
        assert run_json["status"] == "complete"
        assert run_json["report"]["verdict"] == report.verdict
        print(f"  OK  commit(): verdict={report.verdict} confidence={report.confidence}, "
              f"1 credit debited, all artifacts on disk")

        # --- idempotency: re-commit must not double-debit ---
        RunService.commit(prep)
        assert credits.account_debits(_ACCOUNT) == 1, "re-commit double-debited!"
        print("  OK  re-commit did not double-debit the credit")

        # --- convenience: RunService.run wires prepare + commit ---
        # ⭐ AND IT CARRIES THE OTHER HALF OF THE D4 GATE FOR FREE. This test
        # already paid for a second full run; spending it on the SAME config
        # tested the same branch twice. With funnel_enabled=True it verifies the
        # opt-in path — and with it, the in/out-of-target split (`#84`) on a real
        # call, which no offline fixture can prove.
        _cleanup()
        _setup_entities()
        report2 = RunService.run(_config(funnel_enabled=True))
        validate_report(report2)
        assert report2.funnel_projection is not None, (
            "funnel_enabled=True did not attach the projection"
        )
        fp2 = report2.funnel_projection
        assert fp2.within_target is not None or fp2.outside_target is not None, (
            "the projection carries no target split — every parsed signal must "
            "land on one side of the target line (#84)"
        )
        sides = [x for x in (fp2.within_target, fp2.outside_target) if x]
        assert sum(x.behavioral_distribution.n for x in sides) == (
            fp2.population_behavioral_distribution.n
        ), "the target split does not sum to the panel"
        print("  OK  RunService.run() returned a valid Report; funnel_enabled=True "
              "attached it")
        for side in sides:
            r = side.funnel_rates
            print(f"      {side.segment_label:>14} (n={side.behavioral_distribution.n}): "
                  f"convert {r.convert_rate*100:.3f}%  "
                  f"[{r.convert_band[0]*100:.3f}-{r.convert_band[1]*100:.3f}%]")
        print(f"      {'whole panel':>14} "
              f"(n={fp2.population_behavioral_distribution.n}): "
              f"convert {fp2.overall.convert_rate*100:.3f}%  <- pooled, not the read")

        print(f"\n  bet_ranking ({len(report.bet_ranking)} bets):")
        for bet in report.bet_ranking:
            print(f"    - {bet}")
        # ⚠ PRINT THE SPEND BEFORE `finally` DELETES IT. telemetry.jsonl lives
        # inside the run directory this test removes, so without this the most
        # expensive test in the tier leaves NO record of what it cost. The first
        # --paid run could only estimate its own bill.
        print("\n" + telemetry_summary(
            prep.run_id, account_id=_ACCOUNT, brand_profile_id=_BRAND))
        print("PASS — run goes prepare -> confirm -> commit; credit debited once.")
    finally:
        _cleanup()


@pytest.mark.paid
def test_full_creative_read_end_to_end() -> None:
    """Costs ~$2.20-2.80 of real API calls — it runs the pipeline TWICE (see
    the module docstring). Skipped unless --paid is passed.

    ⚠ Until 2026-08-22 this file had no `test_` function at all: pytest
    collected zero from it while it sat in tests/ named test_*.py. It was
    run by hand, which means in practice it was not run."""
    main()


if __name__ == "__main__":
    main()
