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
    BehavioralSignal,
    BehavioralSignalDistribution,
    ContextFitEntry,
    DispositionRef,
    FunnelProjection,
    FunnelRates,
    Quote,
    Report,
    SchemaError,
    SegmentProjection,
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
        methodology_flags=[],
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
    r.methodology_flags = ["pool_archetype_mismatch"]
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


def test_methodology_flags_accept_valid_values() -> None:
    r = _make_fixture_report()
    r.methodology_flags = [
        "no_within_target_evidence",
        "single_within_target",
        "homogenization_high",
        "single_context_only",
    ]
    validate_report(r)
    print("  OK  methodology_flags accepts valid enum values")


def test_methodology_flags_rejects_unknown_value() -> None:
    r = _make_fixture_report()
    r.methodology_flags = ["bogus_flag"]
    try:
        validate_report(r)
    except SchemaError as e:
        assert "methodology_flags" in str(e)
        print("  OK  methodology_flags rejects unknown enum value:", e)
        return
    raise AssertionError("methodology_flags should reject unknown enum value")


def test_methodology_flags_round_trip() -> None:
    """A flag set must round-trip byte-identically through to_json/from_json
    and survive validate_report on both ends. Brand-facing render reads
    methodology_flags directly; silent drop would be a quality bug."""
    r = _make_fixture_report()
    r.methodology_flags = ["no_within_target_evidence", "single_context_only"]
    s1 = r.to_json()
    r2 = Report.from_json(s1)
    s2 = r2.to_json()
    assert s1 == s2, "methodology_flags round-trip not byte-identical"
    assert r2.methodology_flags == [
        "no_within_target_evidence", "single_context_only"
    ], f"flags drift: {r2.methodology_flags}"
    validate_report(r2)
    print("  OK  methodology_flags round-trip preserves the list")


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


# ---- rocket-2.0.0 additions: funnel projection + R7 behavioral signal ----


def _make_funnel_rates(basis: str = "heuristic_v1") -> FunnelRates:
    return FunnelRates(
        stop_rate=0.42, stop_band=(0.30, 0.54),
        click_rate=0.031, click_band=(0.022, 0.040),
        visit_rate=0.028, visit_band=(0.019, 0.037),
        convert_rate=0.011, convert_band=(0.006, 0.016),
        basis=basis,
        baseline_source="customer account average, last 90d",
    )


def _make_v2_fixture_report() -> Report:
    """A v1 fixture report plus the rocket-2.0.0 fields populated."""
    r = _make_fixture_report()
    r.bet_ranking = [
        "Lead with the price anchor for impulsive cold-traffic — strongest projected lift",
        "Hold spend on deliberate retargeting until the comprehension fix lands",
    ]
    r.provisional_dispositions = ["value_calculating_skeptic"]
    r.methodology_flags = ["provisional_disposition_present"]
    pop_dist = BehavioralSignalDistribution(
        counts={"scroll_past": 6, "linger": 4, "tap_cta": 3, "seek_info": 2},
        would_act_within_week_count=4,
        n=15,
    )
    r.funnel_projection = FunnelProjection(
        overall=_make_funnel_rates(),
        by_segment=[
            SegmentProjection(
                segment_label="brand_loyal_boat_user::impulsive",
                behavioral_distribution=BehavioralSignalDistribution(
                    counts={"tap_cta": 3, "linger": 2},
                    would_act_within_week_count=3,
                    n=5,
                ),
                funnel_rates=_make_funnel_rates(),
            ),
        ],
        population_behavioral_distribution=pop_dist,
        calibration_note=(
            "Directional — heuristic_v1, not fitted to in-market outcomes. "
            "Bands tighten as your account history accrues."
        ),
    )
    return r


def test_v1_fixture_still_roundtrips_unchanged() -> None:
    """The v1 Report fixture (no v2 fields) must still round-trip byte-
    identically after the additive rocket-2.0.0 schema extension."""
    r = _make_fixture_report()
    s1 = r.to_json()
    r2 = Report.from_json(s1)
    s2 = r2.to_json()
    assert s1 == s2, "v1 fixture no longer round-trips byte-identically"
    assert r2.funnel_projection is None
    assert r2.bet_ranking == []
    assert r2.provisional_dispositions == []
    validate_report(r2)
    print("  OK  v1 fixture still round-trips after additive v2 extension")


def test_v2_fixture_roundtrip() -> None:
    r = _make_v2_fixture_report()
    s1 = r.to_json()
    r2 = Report.from_json(s1)
    s2 = r2.to_json()
    assert s1 == s2, "v2 Report round-trip not byte-identical"
    assert r2.funnel_projection is not None
    assert r2.funnel_projection.overall.basis == "heuristic_v1"
    assert len(r2.funnel_projection.by_segment) == 1
    assert r2.bet_ranking == r.bet_ranking
    print("  OK  v2 Report (funnel_projection + bet_ranking) round-trip")


def test_validate_accepts_v2_fixture() -> None:
    validate_report(_make_v2_fixture_report())
    print("  OK  validate_report accepts the v2 fixture")


def test_validate_rejects_inverted_funnel_band() -> None:
    r = _make_v2_fixture_report()
    # Invert the overall click band: lo > hi.
    r.funnel_projection.overall.click_band = (0.040, 0.022)
    try:
        validate_report(r)
    except SchemaError as e:
        assert "click_band" in str(e)
        print("  OK  validate_report rejects an inverted funnel band:", e)
        return
    raise AssertionError("validate_report should reject an inverted funnel band")


def test_validate_rejects_rate_outside_band() -> None:
    r = _make_v2_fixture_report()
    r.funnel_projection.overall.convert_rate = 0.99  # outside [0.006, 0.016]
    try:
        validate_report(r)
    except SchemaError as e:
        assert "convert_rate" in str(e)
        print("  OK  validate_report rejects a rate outside its band:", e)
        return
    raise AssertionError("validate_report should reject a rate outside its band")


def test_provisional_disposition_flag_accepted() -> None:
    r = _make_v2_fixture_report()
    assert "provisional_disposition_present" in r.methodology_flags
    validate_report(r)
    print("  OK  'provisional_disposition_present' methodology flag accepted")


def test_agent_transcript_v2_behavioral_signal_roundtrip() -> None:
    t = AgentTranscript(
        agent_id=0,
        disposition_label="brand_loyal_boat_user",
        context_label="commute_scroll",
        seed_idx=0,
        encoding_text="R1 GUT: ...\n\nR2 COMPREHENSION: ...\n\nR3 EMOTION: ...",
        reflection_text="R4 ...\n\nR5 ...\n\nR6 ...\n\nR7 ACTION: {...}",
        behavioral_signal=BehavioralSignal(
            action="tap_cta",
            reasoning="the ₹1,199 deal price is a clear-enough hook to tap",
            would_act_within_week=True,
        ),
    )
    t2 = AgentTranscript.from_dict(t.to_dict())
    assert t == t2, "AgentTranscript w/ behavioral_signal round-trip mismatch"
    # And the v1 shape (no behavioral_signal) still round-trips.
    t_v1 = AgentTranscript(
        agent_id=1,
        disposition_label="d",
        context_label="c",
        seed_idx=0,
        encoding_text="...",
        reflection_text="...",
    )
    t_v1_2 = AgentTranscript.from_dict(t_v1.to_dict())
    assert t_v1 == t_v1_2 and t_v1_2.behavioral_signal is None
    print("  OK  AgentTranscript round-trip with and without behavioral_signal")


def main() -> None:
    print("=== schema round-trip smoke ===")
    test_report_roundtrip_byte_identical()
    test_validate_report_accepts_fixture()
    test_validate_rejects_bad_verdict()
    test_validate_rejects_bad_confidence()
    test_validate_rejects_non_three_changes_on_non_methodology()
    test_methodology_gap_allows_zero_changes()
    test_methodology_gap_rejects_changes()
    test_methodology_flags_accept_valid_values()
    test_methodology_flags_rejects_unknown_value()
    test_methodology_flags_round_trip()
    test_agent_transcript_roundtrip()
    test_v1_fixture_still_roundtrips_unchanged()
    test_v2_fixture_roundtrip()
    test_validate_accepts_v2_fixture()
    test_validate_rejects_inverted_funnel_band()
    test_validate_rejects_rate_outside_band()
    test_provisional_disposition_flag_accepted()
    test_agent_transcript_v2_behavioral_signal_roundtrip()
    print("PASS — schema is locked.")


if __name__ == "__main__":
    main()
