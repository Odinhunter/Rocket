"""Phase 4 offline tests (rocket-2.2.0, diagnosis rung): the assess+prescribe
-> Report assembly seam. Feeds canned AssessResult + PrescribeResult (no model
call) and checks field mapping, deterministic target_match, the
declared_audience_disjoint attach, the METHODOLOGY_GAP empty-prescription path,
the painmap deliverable round-trip, and the run.json dual prompt-version stamp.

Run: python tests/test_report_assembly.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import AssetSpec, RunConfig
from agent.schema import (
    AudienceMatch,
    BehavioralSignalDistribution,
    ContextFitEntry,
    FunnelProjection,
    FunnelRates,
    Pain,
    Quote,
    Strength,
    TopChange,
    validate_report,
)
from agent.synthesis_assess import AssessResult, frozen_painmap_from_report
from agent.synthesis_l4 import _assemble_report, _build_target_match
from agent.synthesis_prescribe import PrescribeResult
from agent.run_service import _run_json_payload
from agent.synthesis_types import (
    DispositionTarget,
    InferredAudience,
    TargetClassification,
)


def _tc() -> TargetClassification:
    return TargetClassification(
        inferred_target_description="protein-curious adults 25-34",
        target_reasoning="clean-label cues",
        disposition_classifications=[
            DispositionTarget(disposition_label="aspirant_clean_label", classification="within", reasoning=""),
            DispositionTarget(disposition_label="purist_food_first", classification="outside", reasoning=""),
            DispositionTarget(disposition_label="skeptic_lapsed_protein", classification="ambiguous", reasoning=""),
        ],
        inferred_audience=InferredAudience(gender="mixed", age_band="25_34"),
    )


def _funnel() -> FunnelProjection:
    fr = FunnelRates(
        stop_rate=0.42, stop_band=(0.30, 0.54),
        click_rate=0.031, click_band=(0.022, 0.040),
        visit_rate=0.028, visit_band=(0.019, 0.037),
        convert_rate=0.011, convert_band=(0.006, 0.016),
        basis="heuristic_v1", baseline_source="acct avg 90d",
    )
    return FunnelProjection(
        overall=fr, by_segment=[],
        population_behavioral_distribution=BehavioralSignalDistribution(
            counts={"linger": 4, "tap_cta": 3},
            next_step_counts={"buy_now": 3, "nothing": 12}, n=15),
        calibration_note="directional",
    )


def _assess(verdict="MIXED", confidence=58, flags=("single_within_target",)) -> AssessResult:
    q = Quote(quote="another clean energy bar", disposition="aspirant_clean_label", round=1, context="commute_scroll")
    return AssessResult(
        verdict=verdict, confidence=confidence,
        pain_map=[
            Pain(id="P1", pain="generic hero -> category wallpaper", funnel_stage="attention",
                 severity="execution", within_target=True, prevalence="most", cited_by=["aspirant_clean_label"],
                 evidence_quotes=[q]),
            Pain(id="P2", pain="DIY-equivalence leak", funnel_stage="consideration",
                 severity="structural", within_target=True, prevalence="some", cited_by=["aspirant_clean_label"],
                 evidence_quotes=[q]),
        ],
        strengths_to_preserve=[Strength(strength="transparency lands", evidence_quotes=[q])],
        context_fit_map={"commute_scroll": ContextFitEntry(verdict="mixed", friction_summary="ok")},
        verbatim_consumer_voice=[q],
        methodology_flags=list(flags),
    )


def _prescribe(n=3) -> PrescribeResult:
    changes = [
        TopChange(change=f"specific move {i}", why=f"reasoning {i}",
                  derives_from_pains=["P1", "P2"], lever_class="creative",
                  within_target_corroboration="within-target flagged")
        for i in range(n)
    ]
    return PrescribeResult(top_3_changes=changes, bet_ranking=["lead with the proof point"])


def test_build_target_match_buckets() -> None:
    tm = _build_target_match(_tc())
    assert [d.disposition for d in tm.reached] == ["aspirant_clean_label"]
    assert tm.reached[0].classification == "within"
    # outside AND ambiguous both land in missed, tagged with their true class.
    missed = {d.disposition: d.classification for d in tm.missed}
    assert missed == {"purist_food_first": "outside", "skeptic_lapsed_protein": "ambiguous"}
    print("  OK  target_match: reached=within, missed=outside+ambiguous (lossless)")


def test_assemble_aligned() -> None:
    report = _assemble_report(_assess(), _prescribe(), _tc(), _funnel(), None, [])
    assert report.verdict == "MIXED" and report.confidence == 58
    assert [p.id for p in report.pain_map] == ["P1", "P2"]
    assert len(report.top_3_changes) == 3
    assert report.top_3_changes[0].derives_from_pains == ["P1", "P2"]
    assert report.bet_ranking == ["lead with the proof point"]
    assert report.methodology_flags == ["single_within_target"]  # no audience flag
    assert report.funnel_projection is not None
    assert report.audience_match is None
    validate_report(report)
    print("  OK  assemble (aligned): fields mapped, validates")


def test_assemble_mismatched_appends_flag() -> None:
    am = AudienceMatch(verdict="mismatched", declared_summary="women 20-24",
                       inferred_summary="men 45-54", axes=["gender", "age"], message="disjoint")
    report = _assemble_report(_assess(), _prescribe(), _tc(), _funnel(), am, [])
    assert "declared_audience_disjoint" in report.methodology_flags
    assert report.audience_match is not None and report.audience_match.verdict == "mismatched"
    validate_report(report)
    print("  OK  assemble (mismatched): declared_audience_disjoint attached")


def test_painmap_deliverable_roundtrips_from_report() -> None:
    assess = _assess()
    report = _assemble_report(assess, _prescribe(), _tc(), _funnel(), None, [])
    # The painmap.json written off the report must equal the frozen painmap the
    # prescribe pass consumed — deliverable and handoff never drift.
    assert frozen_painmap_from_report(report) == assess.to_frozen_painmap()
    print("  OK  painmap deliverable reconstructed from report == frozen handoff")


def test_methodology_gap_empty_prescription() -> None:
    assess = _assess(verdict="METHODOLOGY_GAP", confidence=15, flags=("pool_archetype_mismatch",))
    report = _assemble_report(assess, PrescribeResult(top_3_changes=[], bet_ranking=[]), _tc(), _funnel(), None, [])
    assert report.verdict == "METHODOLOGY_GAP"
    assert report.top_3_changes == [] and report.bet_ranking == []
    validate_report(report)  # 0 changes allowed + confidence <= 20
    print("  OK  METHODOLOGY_GAP assembles with empty prescription + validates")


def test_run_json_stamps_both_prompt_versions() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
        archetype="unspecified", category="personal_audio",
    )
    payload = _run_json_payload(cfg, "rid123", status="complete", report=None)
    assert payload["assess_prompt_version"] == "assess-2"
    assert payload["prescribe_prompt_version"] == "prescribe-1"
    assert payload["decision_version"] == "decision-2"  # unchanged by v2.4
    assert payload["purpose_version"] == "purpose-1"  # rocket-2.4.0 (purpose layer)
    assert "l4_prompt_version" in payload  # retained for back-compat
    assert payload["protocol_version"] == "rocket-3.0.0-dev"
    print("  OK  run.json stamps assess + prescribe + decision + purpose versions (+ legacy l4)")


def main() -> None:
    print("=== assess+prescribe -> Report assembly (rocket-2.3.0) ===")
    test_build_target_match_buckets()
    test_assemble_aligned()
    test_assemble_mismatched_appends_flag()
    test_painmap_deliverable_roundtrips_from_report()
    test_methodology_gap_empty_prescription()
    test_run_json_stamps_both_prompt_versions()
    print("PASS — report assembly + version stamps locked.")


if __name__ == "__main__":
    main()
