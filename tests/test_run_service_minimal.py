"""API smoke: a full Creative Read end-to-end through the two-phase
orchestrator — entities on disk -> RunConfig -> prepare() -> commit() ->
validated Report.

Asserts the run goes prepared -> committed -> complete cleanly, the credit
is debited exactly once at commit, all artifacts land on disk, and the
Report carries a bet_ranking headline + the L3.5 funnel projection.

Cost: a 6-agent panel (~12 L1 calls) + target_id + 2x L2 + L3 + L4,
roughly $0.80-1.10.

Run: python tests/test_run_service_minimal.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from agent.telemetry import RUNS_DIR, run_dir
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
    p = RUNS_DIR / _ACCOUNT
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


def _disposition(label: str, **overrides) -> NamedDisposition:
    base = dict(
        category_relationship="regular", brand_stance="neutral",
        price_orientation="price_first", decision_driver="function",
        category_involvement="low", prior_experience_valence="neutral",
        channel_behavior="offline_first", life_stage="early_career",
    )
    base.update(overrides)
    return NamedDisposition(label=label, vector=DispositionVector(**base))


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
        dispositions=[
            _disposition("budget_deal_buyer", brand_stance="favorable"),
            _disposition(
                "spec_skeptic", brand_stance="skeptical",
                price_orientation="value_calculator",
                prior_experience_valence="burned",
            ),
        ],
    ).save()


def _config() -> RunConfig:
    spec = AudienceSpec(
        demographics=[
            DemographicPoint(
                gender="male", age_band="25_34", income_tier="upper_mid",
                geography="Bangalore / metro tier-1",
            )
        ],
        disposition_labels=["budget_deal_buyer", "spec_skeptic"],
        context_envelope=[
            _context("commute_scroll"),
            _context("pre_purchase_research", attention_level="high",
                     intent_state="actively_shopping", energy_state="alert"),
            _context("late_night_wind_down", energy_state="drained"),
        ],
        chaos_distribution=_chaos(),
        panel_size=6,
    )
    return RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat minimal"),
        archetype="urban_indian_male_22_30", category="personal_audio",
        account_id=_ACCOUNT, brand_profile_id=_BRAND,
        audience_spec=spec,
        segment_granularity="disposition",  # cheaper for the minimal gate
        library_id="lib_1", audience_id="aud_1",
        baseline_funnel={
            "stop_rate": 0.11, "click_rate": 0.018,
            "visit_rate": 0.014, "convert_rate": 0.005,
        },
    )


def main() -> None:
    print("=== run_service minimal end-to-end ===")
    _cleanup()
    if not Path("assets/boat_ad.png").exists():
        raise SystemExit("missing test asset: assets/boat_ad.png")
    try:
        _setup_entities()
        config = _config()

        # --- prepare() — no credit debited ---
        prep = RunService.prepare(config)
        assert not credits.is_committed(prep.run_id, _ACCOUNT, _BRAND), (
            "prepare() debited a credit — it must not"
        )
        assert len(prep.panel) == 6, f"panel size {len(prep.panel)} != 6"
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
        assert report.funnel_projection is not None, "no funnel_projection attached"
        for artifact in (
            "transcripts.json", "l2_summaries.json", "l3_summary.json",
            "l35_projection.json", "committed.marker",
        ):
            assert (rd / artifact).exists(), f"missing artifact: {artifact}"
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
        _cleanup()
        _setup_entities()
        report2 = RunService.run(_config())
        validate_report(report2)
        assert report2.funnel_projection is not None
        print("  OK  RunService.run() (prepare + commit convenience) returned a valid Report")

        print(f"\n  bet_ranking ({len(report.bet_ranking)} bets):")
        for bet in report.bet_ranking:
            print(f"    - {bet}")
        fp = report.funnel_projection.overall
        print(f"  funnel (overall, {fp.basis}): "
              f"click {fp.click_rate:.4f} [{fp.click_band[0]:.4f}-{fp.click_band[1]:.4f}], "
              f"convert {fp.convert_rate:.4f}")
        print("PASS — run goes prepare -> confirm -> commit; credit debited once.")
    finally:
        _cleanup()


if __name__ == "__main__":
    main()
