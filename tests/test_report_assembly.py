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
from agent.render import RENDER_PROMPT_VERSION
from agent.provenance import _stable_text
from agent.run_service import _run_json_payload, stamp_config_provenance
from agent.runtime import REACTION_PROTOCOL_VERSION
from agent.vectors import VECTOR_SCHEMA_VERSION
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


def test_run_json_stamps_all_versions() -> None:
    # The §10 version table must LAND in run.json — the -rc{n} arm scheme (#9's
    # spend, the Week-3 comparison) is only attributable if every version the run
    # used is stamped in the persisted record, not just held in a constant.
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
        archetype="unspecified", category="personal_audio",
    )
    payload = _run_json_payload(cfg, "rid123", status="complete", report=None)
    assert payload["protocol_version"] == "rocket-3.0.0-dev"
    assert payload["reaction_protocol_version"] == "reaction-v3"  # v3 two-call surface
    assert payload["render_prompt_version"] == "render-6"  # v3 persona voice + gates
    assert payload["assess_prompt_version"] == "assess-3"  # v3 A5 (short-PainMap permission)
    assert payload["prescribe_prompt_version"] == "prescribe-1"
    assert payload["decision_version"] == "decision-3"  # v3 (A3/A5/A7)
    assert payload["purpose_version"] == "purpose-2"  # v3 (buy-intent headline)
    assert "l4_prompt_version" in payload  # retained for back-compat
    # Stamps must equal the live constants, so a bump can't drift from the record.
    assert payload["reaction_protocol_version"] == REACTION_PROTOCOL_VERSION
    assert payload["render_prompt_version"] == RENDER_PROMPT_VERSION
    print("  OK  run.json stamps protocol + reaction + render + assess + prescribe "
          "+ decision + purpose (+ legacy l4)")


def test_run_json_freezes_the_configuration_not_just_its_version_labels() -> None:
    """§5.1. The eight version strings above are hand-bumped, so an edited
    prompt with an unbumped constant is invisible in the record. These are the
    things that actually pin what produced a run — and each was a real gap:
    `panel_version` lived only in preparation.json, `funnel_enabled` was a field
    that never serialised at all, and nothing fingerprinted prompt TEXT."""
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
        archetype="unspecified", category="personal_audio",
    )
    cfg.panel_version = "abc123def456"
    payload = _run_json_payload(cfg, "rid123", status="complete", report=None)
    config = payload["config"]
    assert config["panel_version"] == "abc123def456"
    assert config["funnel_enabled"] is False
    assert config["vector_schema_version"] == VECTOR_SCHEMA_VERSION

    fp = payload["prompt_fingerprints"]
    assert fp, "no prompt fingerprints in the run record"
    # Every template must RESOLVE. "unavailable" is what a renamed or moved
    # constant produces, and it is recorded rather than dropped precisely so it
    # shows up here instead of quietly shrinking the record.
    unresolved = sorted(k for k, v in fp.items() if v == "unavailable")
    assert not unresolved, f"prompt templates no longer resolve: {unresolved}"
    # Both halves of the purpose-conditional reflection prompt are covered
    # separately, so a change is attributable to the block it happened in.
    for expected in ("assess.system", "prescribe.system", "agent.encoding",
                     "agent.reflection_base", "agent.reflection_novelty",
                     "agent.reflection_brand_check", "render.persona_system"):
        assert expected in fp, f"{expected} is not fingerprinted"

    # A fingerprint must track CONTENT. Templates are not all plain strings —
    # `agent.cycle_prose` is a dict — and a hash that only saw its shape would
    # look like provenance while missing every edit to the prose inside it.
    a = _stable_text({"running_low": "nearly out", "just_bought": "stocked up"})
    b = _stable_text({"running_low": "REWORDED", "just_bought": "stocked up"})
    assert a != b, "editing a dict template's text left the fingerprint unchanged"
    # ...and not on Python's iteration order, or every run would differ.
    assert _stable_text({"x": "1", "y": "2"}) == _stable_text({"y": "2", "x": "1"})
    print(f"  OK  run.json freezes panel/funnel/vector + {len(fp)} prompt fingerprints")


def test_config_provenance_records_which_inputs_the_run_read() -> None:
    """`disposition_version` has been the literal string "auto" on every run
    ever made — the field and its hash existed, nothing called it. Two runs
    whose disposition library text differs must not look identical in the
    record."""
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
        archetype="unspecified", category="personal_audio",
    )
    assert cfg.disposition_version == "auto", "the untouched default changed"
    pool = [("aspirant_clean_label", "wants clean labels"),
            ("skeptic_lapsed_protein", "burned by a previous tub")]
    stamp_config_provenance(cfg, pool, "panelv1")

    assert cfg.disposition_version != "auto", "the run never recorded its library"
    assert cfg.panel_version == "panelv1"
    first = cfg.disposition_version

    # Same pool, same hash — otherwise the field is noise and no two runs can
    # ever be declared comparable.
    stamp_config_provenance(cfg, list(reversed(pool)), "panelv1")
    assert cfg.disposition_version == first, "hash is not stable across orderings"

    # Edited disposition TEXT, same labels: the case the field exists for.
    stamp_config_provenance(
        cfg, [("aspirant_clean_label", "wants clean labels AND a price"),
              ("skeptic_lapsed_protein", "burned by a previous tub")], "panelv1")
    assert cfg.disposition_version != first, \
        "edited disposition text left the run record unchanged"
    print("  OK  config provenance stamps disposition_version + panel_version")


def test_a_broken_fingerprint_never_costs_a_paid_run() -> None:
    """The most expensive trap in this codebase: something that raises at the
    END of the paid path replaces the return value of a synthesis already paid
    for. A provenance record is worth a lot; it is not worth a ~$4 run."""
    import agent.run_service as rs

    original = rs.prompt_fingerprints
    try:
        rs.prompt_fingerprints = lambda: 1 / 0        # noqa: E731
        cfg = RunConfig(
            asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
            archetype="unspecified", category="personal_audio",
        )
        payload = _run_json_payload(cfg, "rid123", status="complete", report=None)
    finally:
        rs.prompt_fingerprints = original
    assert payload["status"] == "complete", "a broken fingerprint killed the run record"
    assert payload["prompt_fingerprints"] is None, \
        "an unavailable record must be null, never a half-built dict"
    assert payload["config"]["category"] == "personal_audio", "the rest of the record survived"
    print("  OK  a raising fingerprint helper degrades to null, run record intact")


def main() -> None:
    print("=== assess+prescribe -> Report assembly (rocket-2.3.0) ===")
    test_build_target_match_buckets()
    test_assemble_aligned()
    test_assemble_mismatched_appends_flag()
    test_painmap_deliverable_roundtrips_from_report()
    test_methodology_gap_empty_prescription()
    test_run_json_stamps_all_versions()
    test_run_json_freezes_the_configuration_not_just_its_version_labels()
    test_config_provenance_records_which_inputs_the_run_read()
    test_a_broken_fingerprint_never_costs_a_paid_run()
    print("PASS — report assembly + version stamps locked.")


if __name__ == "__main__":
    main()
