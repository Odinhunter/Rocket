"""Step-1 smoke test: a hand-typed Report instance round-trips through
to_json / from_json byte-identically, and validate_report enforces the
structural invariants we depend on.

Run: python tests/test_schema_roundtrip.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import (
    AgentTranscript,
    ContextFitEntry,
    DispositionRef,
    Quote,
    Report,
    SchemaError,
    Strength,
    TargetMatch,
    TopChange,
    validate_report,
)


def _make_fixture_report() -> Report:
    return Report(
        verdict="MIXED",
        confidence=65,
        target_match=TargetMatch(
            reached=[
                DispositionRef(disposition="brand_loyal_boat_user", classification="within"),
                DispositionRef(disposition="price_sensitive_minimalist", classification="within"),
            ],
            missed=[
                DispositionRef(disposition="specialty_audiophile", classification="outside"),
            ],
        ),
        top_3_changes=[
            TopChange(
                change="Disclose the original price next to the ₹1,199 deal price",
                why="Within-target dispositions flagged the deal price as suspicious without an anchor",
                evidence_quotes=[
                    Quote(
                        quote="₹1,199 for what — these were 800 last week?",
                        disposition="price_sensitive_minimalist",
                        round=6,
                        context="pre_purchase_research",
                    ),
                ],
                within_target_corroboration="2 of 2 within-target dispositions flagged price-anchor absence",
            ),
            TopChange(
                change="Move the 'Prime' badge off the front",
                why="Reads as cosmetic premium rather than a real tier upgrade",
                evidence_quotes=[
                    Quote(
                        quote="Prime sticker is doing more work than the product",
                        disposition="brand_loyal_boat_user",
                        round=2,
                        context="commute_scroll",
                    ),
                ],
                within_target_corroboration="1 of 2 within-target flagged; 1 ambiguous corroborated in R4",
            ),
            TopChange(
                change="Show the case open or the buds in-ear",
                why="Closed case alone leaves the product unfelt — comprehension drops",
                evidence_quotes=[],
                within_target_corroboration="Both within-target struggled in R2 to describe what's new",
            ),
        ],
        strengths_to_preserve=[
            Strength(
                strength="Price up-front in the visual frame",
                evidence_quotes=[
                    Quote(
                        quote="At least I know what I'm looking at, no fishing",
                        disposition="price_sensitive_minimalist",
                        round=1,
                        context="commute_scroll",
                    ),
                ],
            ),
        ],
        context_fit_map={
            "commute_scroll": ContextFitEntry(
                verdict="mixed",
                friction_summary="Reads on pause but loses to thumb in <1s without the price hook",
            ),
            "pre_purchase_research": ContextFitEntry(
                verdict="working",
                friction_summary="Active-mode buyers anchor on the deal price; comparison opens",
            ),
            "late_night_wind_down": ContextFitEntry(
                verdict="failing",
                friction_summary="Low-attention scroll; product never registers",
            ),
        },
        verbatim_consumer_voice=[
            Quote(
                quote="₹1,199 for what — these were 800 last week?",
                disposition="price_sensitive_minimalist",
                round=6,
                context="pre_purchase_research",
            ),
            Quote(
                quote="Prime sticker is doing more work than the product",
                disposition="brand_loyal_boat_user",
                round=2,
                context="commute_scroll",
            ),
            Quote(
                quote="At least I know what I'm looking at, no fishing",
                disposition="price_sensitive_minimalist",
                round=1,
                context="commute_scroll",
            ),
            Quote(
                quote="If I'm buying earbuds tonight I'll search this — but in 5 minutes I'll forget",
                disposition="brand_loyal_boat_user",
                round=4,
                context="late_night_wind_down",
            ),
            Quote(
                quote="Not screenshotting, not telling anyone, no story material",
                disposition="specialty_audiophile",
                round=5,
                context="commute_scroll",
            ),
        ],
    )


def test_report_roundtrip_byte_identical() -> None:
    report = _make_fixture_report()
    s1 = report.to_json()
    report2 = Report.from_json(s1)
    s2 = report2.to_json()
    assert s1 == s2, "byte-identical round-trip failed"
    assert report.to_dict() == report2.to_dict(), "dict round-trip mismatch"
    print("  OK  report round-trip byte-identical")


def test_validate_report_accepts_fixture() -> None:
    report = _make_fixture_report()
    validate_report(report)
    print("  OK  validate_report accepts the fixture")


def test_validate_rejects_bad_verdict() -> None:
    r = _make_fixture_report()
    r.verdict = "BOGUS"  # type: ignore[assignment]
    try:
        validate_report(r)
    except SchemaError as e:
        assert "verdict" in str(e)
        print("  OK  bad verdict rejected:", e)
        return
    raise AssertionError("validate_report should have raised on bad verdict")


def test_validate_rejects_bad_confidence() -> None:
    r = _make_fixture_report()
    r.confidence = 150
    try:
        validate_report(r)
    except SchemaError as e:
        assert "confidence" in str(e)
        print("  OK  bad confidence rejected:", e)
        return
    raise AssertionError("validate_report should have raised on bad confidence")


def test_validate_rejects_non_three_changes_on_non_methodology() -> None:
    r = _make_fixture_report()
    r.top_3_changes = r.top_3_changes[:2]  # only 2
    try:
        validate_report(r)
    except SchemaError as e:
        assert "top_3_changes" in str(e)
        print("  OK  non-3 top_3_changes rejected:", e)
        return
    raise AssertionError("validate_report should have raised on non-3 top_3_changes")


def test_methodology_gap_allows_zero_changes() -> None:
    r = _make_fixture_report()
    r.verdict = "METHODOLOGY_GAP"
    r.top_3_changes = []
    r.confidence = 0
    validate_report(r)
    print("  OK  METHODOLOGY_GAP with 0 changes accepted")


def test_methodology_gap_rejects_changes() -> None:
    r = _make_fixture_report()
    r.verdict = "METHODOLOGY_GAP"
    # leave top_3_changes populated; should fail
    try:
        validate_report(r)
    except SchemaError as e:
        assert "METHODOLOGY_GAP" in str(e)
        print("  OK  METHODOLOGY_GAP with changes rejected:", e)
        return
    raise AssertionError("METHODOLOGY_GAP with changes should be rejected")


def test_agent_transcript_roundtrip() -> None:
    t = AgentTranscript(
        agent_id=0,
        disposition_label="brand_loyal_boat_user",
        context_label="commute_scroll",
        seed_idx=0,
        encoding_text="R1 GUT: ...\n\nR2 COMPREHENSION: ...\n\nR3 EMOTION: ...",
        reflection_text="R4 STICKINESS: ...\n\nR5 SOCIAL: ...\n\nR6 FRICTION: ...",
    )
    d = t.to_dict()
    t2 = AgentTranscript.from_dict(d)
    assert t == t2, "AgentTranscript round-trip mismatch"
    print("  OK  AgentTranscript round-trip")


def main() -> None:
    print("=== schema round-trip smoke ===")
    test_report_roundtrip_byte_identical()
    test_validate_report_accepts_fixture()
    test_validate_rejects_bad_verdict()
    test_validate_rejects_bad_confidence()
    test_validate_rejects_non_three_changes_on_non_methodology()
    test_methodology_gap_allows_zero_changes()
    test_methodology_gap_rejects_changes()
    test_agent_transcript_roundtrip()
    print("PASS — schema is locked.")


if __name__ == "__main__":
    main()
