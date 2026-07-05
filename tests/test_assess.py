"""Phase 2 offline tests (rocket-2.2.0, diagnosis rung): the deterministic
machinery of the assess pass — the labelled-corpus builder, the deterministic
methodology_flags, the structural confidence clamp, the frozen-painmap handoff
shape, and the matching validate_report cap invariants. The model call itself
is not exercised (offline).

Run: python tests/test_assess.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import (
    AgentTranscript,
    ContextFitEntry,
    DispositionRef,
    Pain,
    Quote,
    Report,
    SchemaError,
    Strength,
    TargetMatch,
    TopChange,
    validate_report,
)
from agent.synthesis_assess import (
    AssessResult,
    apply_confidence_caps,
    build_corpus,
    compute_methodology_flags,
    resolve_verdict,
    _classification_map,
    _drop_unverifiable,
    _keep_grounded,
)
from agent.synthesis_types import (
    ConfidenceSignals,
    DispositionTarget,
    InferredAudience,
    TargetClassification,
)


def _tc(classifications: list[tuple[str, str]], *, ambiguity_note=None, no_match_note=None) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="protein-curious adults 25-34",
        target_reasoning="clean-label cues, metro aesthetic",
        disposition_classifications=[
            DispositionTarget(disposition_label=d, classification=c, reasoning="")
            for d, c in classifications
        ],
        ambiguity_note=ambiguity_note,
        no_match_note=no_match_note,
        inferred_audience=InferredAudience(gender="mixed", age_band="25_34"),
    )


def _signals(*, within_count: int, tight: int = 8, segs: int = 12) -> ConfidenceSignals:
    # rocket-2.2.0 Phase 7: total_contexts/contexts_in_agreement are no longer
    # produced by L3 (single_context_only now derives from n_contexts, passed to
    # compute_methodology_flags straight from the transcripts).
    return ConfidenceSignals(
        within_target_disposition_count=within_count,
        homogenization_flag_count=tight,
        total_segments=segs,
    )


def test_classification_map_and_corpus() -> None:
    tc = _tc([("aspirant_clean_label", "within"), ("purist_food_first", "outside")])
    cls = _classification_map(tc)
    assert cls == {"aspirant_clean_label": "within", "purist_food_first": "outside"}
    transcripts = [
        AgentTranscript(
            agent_id=7, disposition_label="aspirant_clean_label",
            context_label="commute_scroll", seed_idx=0,
            encoding_text="R1 GUT: looks clean but generic",
            reflection_text="R6 FRICTION: what does it cost",
        ),
        AgentTranscript(
            agent_id=8, disposition_label="purist_food_first",
            context_label="pantry_restock", seed_idx=0,
            encoding_text="R1 GUT: I'd rather eat real food",
            reflection_text="R7 ACTION: scroll past",
        ),
    ]
    corpus = build_corpus(transcripts, cls)
    assert "agent 007 | aspirant_clean_label [WITHIN-TARGET] | context=commute_scroll" in corpus
    assert "agent 008 | purist_food_first [OUTSIDE-TARGET] | context=pantry_restock" in corpus
    assert "looks clean but generic" in corpus and "what does it cost" in corpus
    print("  OK  classification map + labelled corpus builder")


def test_flags_two_within_is_clean() -> None:
    tc = _tc([("a", "within"), ("b", "within"), ("c", "outside")])
    flags = compute_methodology_flags(tc, _signals(within_count=2), [], n_contexts=3)
    assert flags == [], flags  # no structural flags, no provisional, 3 contexts
    print("  OK  two within-target -> no structural flags")


def test_flags_single_within() -> None:
    tc = _tc([("a", "within"), ("b", "outside")])
    flags = compute_methodology_flags(tc, _signals(within_count=1), [], n_contexts=3)
    assert flags == ["single_within_target"], flags
    print("  OK  single within-target -> single_within_target flag")


def test_flags_zero_within_graded() -> None:
    tc = _tc([("a", "outside"), ("b", "outside")])
    flags = compute_methodology_flags(tc, _signals(within_count=0), [], n_contexts=3)
    assert flags == ["no_within_target_evidence"], flags
    print("  OK  zero within-target (graded) -> no_within_target_evidence flag")


def test_flags_no_match_and_all_ambiguous() -> None:
    tc_nm = _tc([("a", "outside")], no_match_note="pool does not match the ad's target")
    assert "pool_archetype_mismatch" in compute_methodology_flags(tc_nm, _signals(within_count=0), [], n_contexts=3)
    # no_match suppresses the graded no_within flag (it's METHODOLOGY_GAP, not graded)
    assert "no_within_target_evidence" not in compute_methodology_flags(tc_nm, _signals(within_count=0), [], n_contexts=3)
    tc_amb = _tc([("a", "ambiguous"), ("b", "ambiguous")], ambiguity_note="ad gives no target signal")
    assert "target_unsignaled" in compute_methodology_flags(tc_amb, _signals(within_count=0), [], n_contexts=3)
    print("  OK  no_match -> pool_archetype_mismatch; all-ambiguous -> target_unsignaled")


def test_flags_provisional_and_single_context() -> None:
    tc = _tc([("a", "within"), ("b", "within")])
    flags = compute_methodology_flags(tc, _signals(within_count=2), ["prov_disp"], n_contexts=1)
    assert "provisional_disposition_present" in flags
    assert "single_context_only" in flags
    print("  OK  provisional + single-context flags")


def test_resolve_verdict_forces_methodology_gap_on_pool_flags() -> None:
    # Pool-quality flags force METHODOLOGY_GAP regardless of the model's verdict.
    assert resolve_verdict("MIXED", ["pool_archetype_mismatch"]) == "METHODOLOGY_GAP"
    assert resolve_verdict("FAILING", ["target_unsignaled"]) == "METHODOLOGY_GAP"
    # Non-pool flags leave the model verdict intact.
    assert resolve_verdict("MIXED", ["single_within_target"]) == "MIXED"
    assert resolve_verdict("WORKING", []) == "WORKING"
    # And the forced gap composes with the <=20 cap (plix_acv path: MIXED 42 -> 20).
    v = resolve_verdict("MIXED", ["pool_archetype_mismatch"])
    assert apply_confidence_caps(v, 42, ["pool_archetype_mismatch"]) == 20
    print("  OK  resolve_verdict forces METHODOLOGY_GAP on pool flags (+ <=20 cap)")


def test_confidence_caps() -> None:
    # METHODOLOGY_GAP hard-capped at 20 regardless of what the model emitted.
    assert apply_confidence_caps("METHODOLOGY_GAP", 90, ["pool_archetype_mismatch"]) == 20
    # zero-within capped at 35.
    assert apply_confidence_caps("FAILING", 70, ["no_within_target_evidence"]) == 35
    # single-within is NOT capped (decision 2) — a vivid read keeps its number.
    assert apply_confidence_caps("MIXED", 72, ["single_within_target"]) == 72
    # two-within, no cap flags -> untouched.
    assert apply_confidence_caps("WORKING", 88, []) == 88
    # already-low confidence never raised.
    assert apply_confidence_caps("FAILING", 15, ["no_within_target_evidence"]) == 15
    print("  OK  confidence caps: METHODOLOGY_GAP<=20, zero-within<=35, single-within uncapped")


def _report_with(verdict: str, confidence: int, flags: list[str]) -> Report:
    n = 0 if verdict == "METHODOLOGY_GAP" else 3
    return Report(
        verdict=verdict,  # type: ignore[arg-type]
        confidence=confidence,
        target_match=TargetMatch(reached=[DispositionRef(disposition="a", classification="within")], missed=[]),
        top_3_changes=[TopChange(change=f"c{i}", why=f"w{i}") for i in range(n)],
        strengths_to_preserve=[],
        context_fit_map={},
        verbatim_consumer_voice=[],
        methodology_flags=flags,
    )


def test_validate_report_enforces_structural_caps() -> None:
    # METHODOLOGY_GAP at 25 must be rejected by the schema invariant.
    try:
        validate_report(_report_with("METHODOLOGY_GAP", 25, ["pool_archetype_mismatch"]))
        raise AssertionError("METHODOLOGY_GAP conf 25 should be rejected")
    except SchemaError as e:
        assert "METHODOLOGY_GAP confidence" in str(e)
    # zero-within at 40 must be rejected.
    try:
        validate_report(_report_with("FAILING", 40, ["no_within_target_evidence"]))
        raise AssertionError("no_within conf 40 should be rejected")
    except SchemaError as e:
        assert "no_within_target_evidence" in str(e)
    # single-within at 72 is fine — no cap.
    validate_report(_report_with("MIXED", 72, ["single_within_target"]))
    print("  OK  validate_report enforces METHODOLOGY_GAP<=20 + zero-within<=35, single-within free")


def test_frozen_painmap_shape_has_no_raw_reactions() -> None:
    ar = AssessResult(
        verdict="MIXED",
        confidence=58,
        pain_map=[
            Pain(id="P1", pain="generic hero", funnel_stage="attention", severity="execution",
                 within_target=True, prevalence="most", cited_by=["a"],
                 evidence_quotes=[Quote(quote="looks generic", disposition="a", round=1, context="c")]),
        ],
        strengths_to_preserve=[
            Strength(strength="transparency lands", evidence_quotes=[Quote(quote="honest", disposition="a", round=2, context="c")]),
        ],
        context_fit_map={"c": ContextFitEntry(verdict="mixed", friction_summary="ok")},
        verbatim_consumer_voice=[Quote(quote="looks generic", disposition="a", round=1, context="c")],
        methodology_flags=["single_within_target"],
    )
    frozen = ar.to_frozen_painmap()
    assert set(frozen.keys()) == {"verdict", "confidence", "pain_map", "strengths_to_preserve", "context_fit"}
    # The prescribe pass must NOT be able to see raw reactions or verbatim_voice.
    assert "verbatim_voice" not in frozen and "verbatim_consumer_voice" not in frozen
    assert frozen["pain_map"][0]["id"] == "P1"
    assert frozen["strengths_to_preserve"][0]["strength"] == "transparency lands"
    import json
    json.dumps(frozen)  # must be JSON-serializable for the prescribe handoff
    print("  OK  frozen painmap is prescribe-safe (no raw reactions) + JSON-serializable")


_GROUND_CORPUS = "R1 GUT: another clean energy bar, they all say the same thing\nR6: what does it even cost"


def test_keep_grounded_filters_unverifiable() -> None:
    real = Quote(quote="another clean energy bar, they all say the same thing", disposition="a", round=1, context="c")
    fake = Quote(quote="this line was never said by anyone in the room", disposition="a", round=1, context="c")
    kept = _keep_grounded([real, fake], _GROUND_CORPUS)
    assert kept == [real], "grounded filter kept the wrong set"
    print("  OK  _keep_grounded keeps grounded quotes, drops invented ones")


def test_drop_unverifiable_keeps_pain_logs_when_empty() -> None:
    fake = Quote(quote="entirely invented sentence not present at all", disposition="a", round=1, context="c")
    real = Quote(quote="another clean energy bar, they all say the same thing", disposition="a", round=1, context="c")
    pains = [
        Pain(id="P1", pain="x", funnel_stage="attention", severity="execution",
             within_target=True, cited_by=["a"], evidence_quotes=[real, fake]),
        Pain(id="P2", pain="y", funnel_stage="recall", severity="execution",
             within_target=True, cited_by=["a"], evidence_quotes=[fake]),  # loses all -> kept, logged
    ]
    strengths = [Strength(strength="s", evidence_quotes=[real, fake])]
    _drop_unverifiable(pains, strengths, _GROUND_CORPUS)
    assert pains[0].evidence_quotes == [real]
    assert pains[1].evidence_quotes == []          # pain retained, evidence emptied
    assert len(pains) == 2                          # the diagnosis stands on its own
    assert strengths[0].evidence_quotes == [real]
    print("  OK  _drop_unverifiable filters quotes in place, keeps pains that lose all evidence")


def main() -> None:
    print("=== assess pass deterministic machinery (rocket-2.2.0) ===")
    test_classification_map_and_corpus()
    test_flags_two_within_is_clean()
    test_flags_single_within()
    test_flags_zero_within_graded()
    test_flags_no_match_and_all_ambiguous()
    test_flags_provisional_and_single_context()
    test_resolve_verdict_forces_methodology_gap_on_pool_flags()
    test_confidence_caps()
    test_validate_report_enforces_structural_caps()
    test_frozen_painmap_shape_has_no_raw_reactions()
    test_keep_grounded_filters_unverifiable()
    test_drop_unverifiable_keeps_pain_logs_when_empty()
    print("PASS — assess deterministic machinery locked.")


if __name__ == "__main__":
    main()
