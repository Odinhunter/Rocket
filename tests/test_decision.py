"""P2 offline tests (rocket-2.3.0, the decision layer): resolve_decision maps
signals to the brand-facing call. The four real Session-11 runs are the
calibration anchors — asserted here as scalar bundles (the exact A_within and
per-disposition rates recomputed live from their transcripts), with the
load-bearing pain pulled from the snapshotted painmaps via the P1 function.

    MB whey  68% / execution / aligned          -> ITERATE
    Buzzword 25% / execution / aligned          -> ITERATE
    TWT pack  0% / champion 32% (ambiguous)     -> RETARGET
    ProSki    9% / structural / no champion     -> REBUILD

Plus the edge branches (METHODOLOGY_GAP, empty within-set, audience mismatch)
and a schema round-trip. A guarded integration check re-derives the decisions
from the real run dirs when present (skips cleanly under CI, where runs/ is
gitignored). No model call (offline).

Run: python tests/test_decision.py
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import batch_run
from agent.config import AssetSpec, RunConfig
from agent.decision import build_decision, load_bearing_within_pain, resolve_decision
from agent.schema import (
    AgentTranscript,
    AudienceMatch,
    BehavioralSignal,
    Decision,
    Pain,
    Report,
    TargetMatch,
    TopChange,
    validate_report,
)
from agent.synthesis_assess import AssessResult
from agent.synthesis_prescribe import PrescribeResult
from agent.synthesis_types import DispositionTarget, TargetClassification
import agent.synthesis_l4 as l4

ROOT = Path(__file__).resolve().parent.parent
DEC_FIX = Path(__file__).resolve().parent / "fixtures" / "decision"


def _pains(name: str) -> list[Pain]:
    data = json.loads((DEC_FIX / name).read_text())
    return [Pain.from_dict(p) for p in data["pain_map"]]


def _pain(pid: str, severity: str, *, stage: str = "consideration", within: bool = True) -> Pain:
    """A minimal synthetic Pain for the SCALE-branch composite tests."""
    return Pain.from_dict({
        "id": pid, "pain": f"{pid} pain", "funnel_stage": stage,
        "severity": severity, "within_target": within,
        "prevalence": "some", "cited_by": ["d1"], "evidence_quotes": [],
    })


# The four anchors as scalar bundles (A_within + per-disposition rates recomputed
# live from the 2026-07-07 transcripts; classification from target_classification).
ANCHORS = {
    "MB whey": dict(
        painmap="mb_whey.painmap.json",
        a_within=13 / 19,
        action={
            "enthusiast_macros_lifter": (13 / 19, 13, 19),
            "switcher_results_chaser": (0.0, 0, 19),
            "aspirant_clean_label": (0.0, 0, 24),
            "pragmatist_protein_snacker": (0.0, 0, 23),
            "skeptic_lapsed_protein": (0.0, 0, 15),
        },
        cmap={
            "enthusiast_macros_lifter": "within",
            "switcher_results_chaser": "outside",
            "aspirant_clean_label": "outside",
            "pragmatist_protein_snacker": "outside",
            "skeptic_lapsed_protein": "outside",
        },
        within=["enthusiast_macros_lifter"],
        audience="aligned",
        verdict="MIXED",
        flags=["single_within_target"],
        expect_decision="ITERATE",
        expect_trust="DIRECTIONAL",
        expect_champion=None,
    ),
    "Buzzword": dict(
        painmap="buzzword.painmap.json",
        a_within=6 / 24,
        action={
            "aspirant_clean_label": (6 / 24, 6, 24),
            "switcher_results_chaser": (0.0, 0, 19),
            "enthusiast_macros_lifter": (0.0, 0, 19),
            "pragmatist_protein_snacker": (0.0, 0, 23),
            "skeptic_lapsed_protein": (0.0, 0, 15),
        },
        cmap={
            "aspirant_clean_label": "within",
            "switcher_results_chaser": "ambiguous",
            "enthusiast_macros_lifter": "outside",
            "pragmatist_protein_snacker": "outside",
            "skeptic_lapsed_protein": "outside",
        },
        within=["aspirant_clean_label"],
        audience="aligned",
        verdict="MIXED",
        flags=["single_within_target"],
        expect_decision="ITERATE",
        expect_trust="DIRECTIONAL",
        expect_champion=None,
    ),
    "TWT pack": dict(
        painmap="twt_pack.painmap.json",
        a_within=0.0,
        action={
            "enthusiast_macros_lifter": (6 / 19, 6, 19),
            "aspirant_clean_label": (3 / 24, 3, 24),
            "switcher_results_chaser": (0.0, 0, 19),
            "pragmatist_protein_snacker": (0.0, 0, 23),
            "skeptic_lapsed_protein": (0.0, 0, 15),
        },
        cmap={
            "skeptic_lapsed_protein": "within",
            "enthusiast_macros_lifter": "ambiguous",
            "aspirant_clean_label": "ambiguous",
            "switcher_results_chaser": "outside",
            "pragmatist_protein_snacker": "outside",
        },
        within=["skeptic_lapsed_protein"],
        audience="aligned",
        verdict="MIXED",
        flags=["single_within_target"],
        expect_decision="RETARGET",
        expect_trust="DIRECTIONAL",
        expect_champion="enthusiast_macros_lifter",
    ),
    "ProSki": dict(
        painmap="proski.painmap.json",
        a_within=4 / 47,
        action={
            "pragmatist_protein_snacker": (2 / 23, 2, 23),
            "aspirant_clean_label": (2 / 24, 2, 24),
            "switcher_results_chaser": (1 / 19, 1, 19),
            "enthusiast_macros_lifter": (1 / 19, 1, 19),
            "skeptic_lapsed_protein": (0.0, 0, 15),
        },
        cmap={
            "aspirant_clean_label": "within",
            "pragmatist_protein_snacker": "within",
            "switcher_results_chaser": "ambiguous",
            "enthusiast_macros_lifter": "outside",
            "skeptic_lapsed_protein": "outside",
        },
        within=["aspirant_clean_label", "pragmatist_protein_snacker"],
        audience="aligned",
        verdict="FAILING",
        flags=[],
        expect_decision="REBUILD",
        expect_trust="HIGH",
        expect_champion=None,
    ),
}


def test_anchors() -> None:
    for name, a in ANCHORS.items():
        lb = load_bearing_within_pain(_pains(a["painmap"]))
        d = resolve_decision(
            a["a_within"], a["action"], a["cmap"], a["within"], lb,
            a["audience"], a["verdict"], a["flags"],
        )
        assert d.decision == a["expect_decision"], (
            f"{name}: expected {a['expect_decision']}, got {d.decision} ({d.rationale})"
        )
        assert d.trust == a["expect_trust"], f"{name}: trust {d.trust}"
        # None of the four flawed anchors clears the composite SCALE bar (each
        # keeps a within-target lever and/or falls short of _SCALE_FLOOR).
        assert d.decision != "SCALE", f"{name}: should not reach the SCALE bar"
        if a["expect_champion"] is None:
            assert d.champion_disposition == "", f"{name}: unexpected champion {d.champion_disposition}"
        else:
            assert d.champion_disposition == a["expect_champion"], (
                f"{name}: champion {d.champion_disposition}"
            )
            assert d.champion_action_rate and d.champion_action_rate > 0.3
        print(
            f"  {name:9} A_within={('%.0f%%' % (d.target_action_rate*100)) if d.target_action_rate is not None else 'n/a':>4}"
            f"  -> {d.decision:11} trust={d.trust:11} :: {d.rationale}"
        )


def test_edge_branches() -> None:
    # METHODOLOGY_GAP verdict -> INCONCLUSIVE regardless of anything else.
    d = resolve_decision(0.9, {}, {}, ["x"], None, "aligned", "METHODOLOGY_GAP", [])
    assert d.decision == "INCONCLUSIVE", d.decision

    # audience mismatched -> RETARGET even with a strong within rate.
    d = resolve_decision(
        0.8, {"a": (0.8, 8, 10)}, {"a": "within"}, ["a"], None, "mismatched", "MIXED", [],
    )
    assert d.decision == "RETARGET", d.decision

    # empty within-set, no champion -> INCONCLUSIVE (never divide by zero).
    d = resolve_decision(
        None, {"o": (0.1, 1, 10)}, {"o": "outside"}, [], None, "aligned", "MIXED",
        ["no_within_target_evidence"],
    )
    assert d.decision == "INCONCLUSIVE", d.decision

    # empty within-set BUT a champion clears the floor -> RETARGET.
    d = resolve_decision(
        None, {"o": (0.4, 4, 10)}, {"o": "outside"}, [], None, "aligned", "MIXED",
        ["no_within_target_evidence"],
    )
    assert d.decision == "RETARGET", d.decision
    print("  edge branches: GAP/mismatch/empty-within(±champion) ✓")


def test_scale_branch() -> None:
    """The provisional SCALE branch (decision-2): a strong + clean read scales;
    the floor, the residual-lever composite, and the upstream guards all hold."""
    from agent.decision import _SCALE_FLOOR
    within = ["enthusiast_macros_lifter", "aspirant_clean_label"]  # 2 -> HIGH trust
    cmap = {"enthusiast_macros_lifter": "within", "aspirant_clean_label": "within"}
    action = {
        "enthusiast_macros_lifter": (0.82, 14, 17),
        "aspirant_clean_label": (0.82, 14, 17),
    }

    # strong + clean (no within-target lever left) + HIGH trust -> SCALE.
    d = resolve_decision(0.82, action, cmap, within, None, "aligned", "MIXED", [])
    assert d.decision == "SCALE", d.rationale
    assert d.trust == "HIGH" and d.load_bearing_pain_id == ""

    # THE TRUST GUARD: same strong+clean read but on a single within persona
    # (DIRECTIONAL) must NOT scale — that thin-evidence path is exactly where a
    # too-easy composite would false-fire, so it falls through to ITERATE.
    solo = ["enthusiast_macros_lifter"]
    solo_cmap = {"enthusiast_macros_lifter": "within"}
    solo_action = {"enthusiast_macros_lifter": (0.83, 15, 18)}
    d = resolve_decision(0.83, solo_action, solo_cmap, solo, None, "aligned", "MIXED",
                         ["single_within_target"])
    assert d.decision == "ITERATE" and d.trust == "DIRECTIONAL", d.rationale
    # even with 2 within dispositions, a thin-evidence flag drops trust -> no SCALE.
    d = resolve_decision(0.82, action, cmap, within, None, "aligned", "MIXED",
                         ["no_within_target_evidence"])
    assert d.decision != "SCALE" and d.trust == "DIRECTIONAL", d.rationale

    # exactly at the floor, clean -> SCALE (>=, not >).
    d = resolve_decision(_SCALE_FLOOR, action, cmap, within, None, "aligned", "MIXED", [])
    assert d.decision == "SCALE", d.rationale

    # a hair below the floor, clean -> ITERATE (fails toward ITERATE, never SCALE).
    d = resolve_decision(_SCALE_FLOOR - 0.01, action, cmap, within, None, "aligned", "MIXED", [])
    assert d.decision == "ITERATE", d.rationale

    # v3/A5: above the floor WITH a within-target EXECUTION pain -> SCALE
    #   ("scale while iterating") — the execution pain is carried, not a blocker.
    d = resolve_decision(0.9, action, cmap, within, _pain("P9", "execution"), "aligned", "MIXED", [])
    assert d.decision == "SCALE", d.rationale
    assert d.load_bearing_pain_id == "P9"

    # above the floor BUT a structural within-target pain -> REBUILD (step 4 first).
    d = resolve_decision(0.9, action, cmap, within, _pain("P9", "structural", stage="attention"), "aligned", "MIXED", [])
    assert d.decision == "REBUILD", d.rationale

    # v3/A7: strong + HIGH trust BUT the coherence guard fired
    #   (intent_action_incoherent) -> SCALE blocked -> ITERATE.
    d = resolve_decision(0.9, action, cmap, within, None, "aligned", "MIXED",
                         ["intent_action_incoherent"])
    assert d.decision != "SCALE" and d.decision == "ITERATE", d.rationale

    # SCALE never overrides an audience mismatch (step 1 wins even when strong).
    d = resolve_decision(0.9, action, cmap, within, None, "mismatched", "MIXED", [])
    assert d.decision == "RETARGET", d.rationale
    print("  SCALE branch: strong -> SCALE (execution pain coexists); "
          "floor/trust/A7/structural/mismatch guards ✓")


def test_schema_roundtrip() -> None:
    # A Report carrying a Decision validates and round-trips through JSON.
    dec = Decision(
        decision="ITERATE", target_action_rate=0.68, trust="DIRECTIONAL",
        within_dispositions=["enthusiast_macros_lifter"], load_bearing_pain_id="P1",
        rationale="load-bearing within pain P1 is fixable",
    )
    rep = Report(
        verdict="MIXED", confidence=82, target_match=TargetMatch(),
        top_3_changes=[], strengths_to_preserve=[], context_fit_map={},
        verbatim_consumer_voice=[], methodology_flags=["single_within_target"],
        decision=dec,
    )
    # top_3_changes must be 3 for non-GAP; give it a minimal valid shape.
    from agent.schema import TopChange
    rep.top_3_changes = [TopChange(change=f"c{i}", why="w") for i in range(3)]
    validate_report(rep)
    back = Report.from_dict(rep.to_dict())
    assert back.decision is not None
    assert back.decision.decision == "ITERATE"
    assert abs(back.decision.target_action_rate - 0.68) < 1e-9
    # v3/A5: a SCALE MAY carry an EXECUTION load-bearing pain ("scale while
    # iterating"); a STRUCTURAL one cannot (that path is REBUILD).
    from agent.schema import Pain
    dec.decision = "SCALE"
    dec.load_bearing_pain_id = "P1"
    dec.target_action_rate = 0.82
    rep.pain_map = [Pain(id="P1", pain="p", funnel_stage="conversion",
                         severity="execution", within_target=True, cited_by=["a"])]
    validate_report(rep)  # execution pain coexists with SCALE -> OK
    # flip P1 to structural -> rejected (a SCALE over a structural block is a bug).
    rep.pain_map[0].severity = "structural"
    try:
        validate_report(rep)
        raise AssertionError("SCALE with a STRUCTURAL load-bearing pain should be rejected")
    except Exception as e:
        assert "STRUCTURAL" in str(e), e
    # SCALE without a within-target rate is rejected (it is a strong-target call).
    rep.pain_map = []
    dec.load_bearing_pain_id = ""
    dec.target_action_rate = None
    try:
        validate_report(rep)
        raise AssertionError("SCALE without a within-target rate should be rejected")
    except Exception as e:
        assert "requires a within-target action rate" in str(e), e
    print("  schema round-trip + v3 SCALE invariants (execution coexists, structural rejected) ✓")


def test_integration_from_real_runs() -> None:
    """Best-effort: re-derive the decisions from the real run dirs via
    build_decision (guards the signal-extraction path end to end). Skips when
    runs/ is absent (CI: gitignored)."""
    base = ROOT / "runs" / "demo" / "health_wellness_demo"
    dirs = {
        "MB whey": "20260707_002346_seed71_muscleblaze_biozyme_performanc",
        "Buzzword": "20260707_010253_seed71_ai_hype_protein_buzzword_contr",
        "TWT pack": "20260707_011505_seed71_the_whole_truth_whey_isolate_p",
        "ProSki": "20260707_012645_seed71_proski_protein_cereal",
    }
    checked = 0
    for name, d in dirs.items():
        rd = base / d
        if not (rd / "transcripts.json").exists():
            continue
        run = json.loads((rd / "run.json").read_text())
        # v3 clean break (docs/v3_protocol.md §3): pre-v3 runs carry the old
        # signal shape (no next_step) AND pre-v3 rate semantics (would_act, not
        # buy-intent) — neither deserializes nor compares. Skip them; this path
        # re-arms once a v3 run exists (its anchors are re-derived from it, not
        # the v2 numbers in ANCHORS).
        if not str(run.get("protocol_version", "")).startswith("rocket-3"):
            continue
        from agent.schema import AgentTranscript
        ts = [AgentTranscript.from_dict(x) for x in json.loads((rd / "transcripts.json").read_text())]
        tc = TargetClassification.from_dict(json.loads((rd / "target_classification.json").read_text()))
        pm_data = json.loads((rd / "painmap.json").read_text())
        pains = [Pain.from_dict(p) for p in pm_data["pain_map"]]
        rep = run.get("report") or {}
        am = rep.get("audience_match")
        audience = AudienceMatch.from_dict(am) if am else None
        dec = build_decision(
            ts, tc, audience, rep.get("verdict", pm_data.get("verdict")),
            rep.get("methodology_flags", []), pains,
        )
        expect = ANCHORS[name]
        assert dec.decision == expect["expect_decision"], f"{name}: {dec.decision}"
        assert abs((dec.target_action_rate or 0.0) - expect["a_within"]) < 0.02, (
            f"{name}: A_within {dec.target_action_rate} vs {expect['a_within']}"
        )
        checked += 1
        print(f"  integration[{name:9}] -> {dec.decision:11} A_within={dec.target_action_rate*100:.0f}% ✓")
    if checked == 0:
        print("  integration: SKIP (no local v3 run dirs — pre-v3 runs skipped by design)")


def _sig(agent_id: int, label: str, act: bool) -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(
            action="tap_cta" if act else "scroll_past", action_reasoning="x",
            next_step="buy_now" if act else "nothing", next_step_reasoning="x",
        ),
    )


def test_synthesize_report_seam() -> None:
    """The production wiring — synthesize_report -> report.decision =
    build_decision(...) -> validate_report — with the two model calls mocked.
    This is the seam no other offline test reaches (assess/prescribe need the
    API). Guards arg order + the validate_report interaction on every run."""
    # 2 within dispositions (loyalist 2/2, aspirant 1/2 -> A_within 3/4 = 0.75), 1
    # outside; one within EXECUTION pain. v3/A5: this now SCALEs @ HIGH trust
    # ("scale while iterating") — the execution pain coexists, and the buy-intent
    # is corroborated by in-feed taps so A7 does not fire.
    transcripts = [
        _sig(1, "loyalist", True), _sig(2, "loyalist", True),
        _sig(3, "aspirant", True), _sig(4, "aspirant", False),
        _sig(5, "skeptic", False), _sig(6, "skeptic", False),
    ]
    tc = TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label="loyalist", classification="within", reasoning=""),
            DispositionTarget(disposition_label="aspirant", classification="within", reasoning=""),
            DispositionTarget(disposition_label="skeptic", classification="outside", reasoning=""),
        ],
    )
    pain = Pain(id="P1", pain="price loop", funnel_stage="consideration",
                severity="execution", within_target=True, cited_by=["loyalist"])
    fake_assess = AssessResult(
        verdict="MIXED", confidence=72, pain_map=[pain],
        strengths_to_preserve=[], context_fit_map={}, verbatim_consumer_voice=[],
        methodology_flags=[],
    )
    fake_pres = PrescribeResult(
        top_3_changes=[TopChange(change=f"c{i}", why="w", derives_from_pains=["P1"]) for i in range(3)],
        bet_ranking=["b1", "b2", "b3"],
    )
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="X"),
        archetype="unspecified", category="personal_audio",
    )
    l3stub = SimpleNamespace(confidence_signals=None)
    orig_a, orig_p = l4.assess_reactions, l4.prescribe_from_painmap
    l4.assess_reactions = lambda *a, **k: fake_assess
    l4.prescribe_from_painmap = lambda *a, **k: fake_pres
    try:
        report = l4.synthesize_report(transcripts, l3stub, tc, None, cfg, provisional_dispositions=[])
    finally:
        l4.assess_reactions, l4.prescribe_from_painmap = orig_a, orig_p
    assert report.decision is not None
    assert report.decision.decision == "SCALE", report.decision.decision
    assert report.decision.trust == "HIGH", report.decision.trust
    assert report.decision.load_bearing_pain_id == "P1"  # execution pain carried
    assert not report.decision.coherence_incoherent      # in-feed taps corroborate
    assert (report.decision.target_action_num, report.decision.target_action_denom) == (3, 4)
    assert abs(report.decision.target_action_rate - 0.75) < 1e-9
    validate_report(report)  # already called inside; re-assert it holds
    print("  seam: synthesize_report -> build_decision -> validate_report (ITERATE/HIGH) ✓")


def test_inconclusive_render_no_action_rate() -> None:
    """An INCONCLUSIVE read must NEVER print a confident action-rate headline,
    even when a_within is non-None (the pool_archetype_mismatch case)."""
    dec = Decision(
        decision="INCONCLUSIVE", target_action_rate=0.42, target_action_num=5,
        target_action_denom=12, trust="DIRECTIONAL",
        within_dispositions=["aspirant_clean_label"],
        rationale="verdict is METHODOLOGY_GAP (data quality)",
    )
    rep = Report(
        verdict="METHODOLOGY_GAP", confidence=18, target_match=TargetMatch(),
        top_3_changes=[], strengths_to_preserve=[], context_fit_map={},
        verbatim_consumer_voice=[], methodology_flags=["pool_archetype_mismatch"],
        decision=dec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        batch_run._print_decision_headline(rep)
    out = buf.getvalue()
    assert "% of your target" not in out, "INCONCLUSIVE leaked a confident action rate"
    assert "42%" not in out, "INCONCLUSIVE leaked the raw rate"
    assert "trustworthy read" in out
    assert "add a disposition profile" in out  # the pool-mismatch what-to-change
    print("  render: INCONCLUSIVE suppresses action rate, shows why + what-to-change ✓")


def main() -> None:
    test_anchors()
    test_edge_branches()
    test_scale_branch()
    test_schema_roundtrip()
    test_synthesize_report_seam()
    test_inconclusive_render_no_action_rate()
    test_integration_from_real_runs()
    print("PASS — decision function: anchors + edges + schema + seam + render + integration.")


if __name__ == "__main__":
    main()
