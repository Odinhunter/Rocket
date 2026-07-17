"""Phase 1 offline tests (rocket-2.2.0, diagnosis rung): the PainMap schema
additions round-trip; validate_report enforces the new pain-axis + rec->pain
referential-integrity invariants; a legacy Report (no pain_map) still
round-trips byte-identically; and the pure grounding validators catch a
fabricated quote and a dangling pain reference.

Run: python tests/test_painmap_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.grounding import (
    check_lever_space,
    verify_pain_references,
    verify_quote_authenticity,
)
from agent.schema import (
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

# A tiny raw-corpus string standing in for the ~100-reaction assess input. The
# fixture's evidence quotes are exact substrings of this.
_CORPUS = (
    "--- agent 001 | aspirant_clean_label [WITHIN-TARGET] | context=commute_scroll ---\n"
    "R1 GUT: another clean energy bar, they all say the same thing\n"
    "R6 FRICTION: I can just make this at home with dates and whey, why would I pay\n"
    "--- agent 002 | pragmatist_protein_snacker [WITHIN-TARGET] | context=pantry_restock ---\n"
    "R2 COMPREHENSION: the pink packaging reads like it is for women, not me\n"
    "R6 FRICTION: nothing here tells me the price\n"
    '{"action": "scroll_past", "reasoning": "no price shown, not for me"}\n'
)


def _make_painmap_fixture() -> Report:
    """A v2.2 Report: assess-produced pains + a prescribe rec that derives from
    them. Every evidence quote is a verbatim substring of _CORPUS."""
    pains = [
        Pain(
            id="P1",
            pain="Generic 'clean energy' hero collapses into category wallpaper; "
            "nothing signals why THIS bar over the shelf",
            funnel_stage="attention",
            severity="execution",
            within_target=True,
            prevalence="most within-target dispositions on R1",
            cited_by=["aspirant_clean_label"],
            evidence_quotes=[
                Quote(
                    quote="another clean energy bar, they all say the same thing",
                    disposition="aspirant_clean_label",
                    round=1,
                    context="commute_scroll",
                ),
            ],
        ),
        Pain(
            id="P2",
            pain="Transparency of ingredients reads as a DIY-equivalence cue — "
            "buyers conclude they can replicate it, eroding the reason to buy",
            funnel_stage="consideration",
            severity="structural",
            within_target=True,
            prevalence="clean-label aspirants on R6",
            cited_by=["aspirant_clean_label"],
            evidence_quotes=[
                Quote(
                    quote="I can just make this at home with dates and whey, why would I pay",
                    disposition="aspirant_clean_label",
                    round=6,
                    context="commute_scroll",
                ),
            ],
        ),
        Pain(
            id="P3",
            pain="Pink aesthetic mis-sorts the ad as women-coded, pushing "
            "within-target male pragmatists out at comprehension",
            funnel_stage="comprehension",
            severity="execution",
            within_target=True,
            prevalence="pragmatist snackers on R2",
            cited_by=["pragmatist_protein_snacker"],
            evidence_quotes=[
                Quote(
                    quote="the pink packaging reads like it is for women, not me",
                    disposition="pragmatist_protein_snacker",
                    round=2,
                    context="pantry_restock",
                ),
            ],
        ),
    ]
    changes = [
        TopChange(
            change="Demote the generic 'clean energy' line; lead with the one "
            "concrete proof point the bar owns",
            why="Resolves the wallpaper problem AND the DIY-equivalence leak — a "
            "specific, hard-to-replicate claim answers 'why pay'",
            within_target_corroboration="within-target aspirants flagged both on R1 and R6",
            derives_from_pains=["P1", "P2"],
            lever_class="creative",
        ),
        TopChange(
            change="De-gender the palette so the ad doesn't self-sort as women-only",
            why="Male pragmatists mis-read the pink as a not-for-me signal at comprehension",
            within_target_corroboration="pragmatist snacker flagged on R2",
            derives_from_pains=["P3"],
            lever_class="creative",
        ),
        TopChange(
            change="Put the price in-frame for the pantry-restock placement",
            why="Absence of price is the terminal blocker on the action beat",
            within_target_corroboration="snacker scrolled past citing missing price at the action beat",
            derives_from_pains=["P1"],
            lever_class="offer",
        ),
    ]
    return Report(
        verdict="MIXED",
        confidence=58,
        target_match=TargetMatch(
            reached=[
                DispositionRef(disposition="aspirant_clean_label", classification="within"),
                DispositionRef(disposition="pragmatist_protein_snacker", classification="within"),
            ],
            missed=[],
        ),
        top_3_changes=changes,
        strengths_to_preserve=[
            Strength(
                strength="Ingredient transparency lands as credible",
                evidence_quotes=[
                    Quote(
                        quote="I can just make this at home with dates and whey, why would I pay",
                        disposition="aspirant_clean_label",
                        round=6,
                        context="commute_scroll",
                    ),
                ],
            ),
        ],
        context_fit_map={
            "commute_scroll": ContextFitEntry(
                verdict="mixed", friction_summary="reads on pause, loses to DIY doubt"
            ),
        },
        verbatim_consumer_voice=[
            Quote(
                quote="the pink packaging reads like it is for women, not me",
                disposition="pragmatist_protein_snacker",
                round=2,
                context="pantry_restock",
            ),
        ],
        methodology_flags=[],
        bet_ranking=["Demote the generic hero for a proof point — strongest projected lift"],
        pain_map=pains,
    )


def test_painmap_report_roundtrip_byte_identical() -> None:
    r = _make_painmap_fixture()
    s1 = r.to_json()
    r2 = Report.from_json(s1)
    s2 = r2.to_json()
    assert s1 == s2, "PainMap Report round-trip not byte-identical"
    assert len(r2.pain_map) == 3
    assert r2.pain_map[0].id == "P1"
    assert r2.top_3_changes[0].derives_from_pains == ["P1", "P2"]
    assert r2.top_3_changes[0].lever_class == "creative"
    print("  OK  PainMap Report round-trips byte-identical")


def test_validate_accepts_painmap_fixture() -> None:
    validate_report(_make_painmap_fixture())
    print("  OK  validate_report accepts the PainMap fixture")


def test_validate_rejects_bad_funnel_stage() -> None:
    r = _make_painmap_fixture()
    r.pain_map[0].funnel_stage = "bogus"  # type: ignore[assignment]
    try:
        validate_report(r)
    except SchemaError as e:
        assert "funnel_stage" in str(e)
        print("  OK  bad funnel_stage rejected:", e)
        return
    raise AssertionError("validate_report should reject a bad funnel_stage")


def test_validate_rejects_bad_severity() -> None:
    r = _make_painmap_fixture()
    r.pain_map[1].severity = "catastrophic"  # type: ignore[assignment]
    try:
        validate_report(r)
    except SchemaError as e:
        assert "severity" in str(e)
        print("  OK  bad severity rejected:", e)
        return
    raise AssertionError("validate_report should reject a bad severity")


def test_validate_rejects_bad_lever_class() -> None:
    r = _make_painmap_fixture()
    r.top_3_changes[0].lever_class = "product"
    try:
        validate_report(r)
    except SchemaError as e:
        assert "lever_class" in str(e)
        print("  OK  bad lever_class rejected:", e)
        return
    raise AssertionError("validate_report should reject a bad lever_class")


def test_validate_rejects_dangling_pain_reference() -> None:
    r = _make_painmap_fixture()
    r.top_3_changes[0].derives_from_pains = ["P1", "P99"]  # P99 not in the map
    try:
        validate_report(r)
    except SchemaError as e:
        assert "P99" in str(e) and "unknown pain id" in str(e)
        print("  OK  dangling pain reference rejected:", e)
        return
    raise AssertionError("validate_report should reject a dangling pain reference")


def test_legacy_report_without_painmap_roundtrips() -> None:
    """A Report with no pain_map / derives_from_pains (a legacy or pre-v2.2
    shape) must still round-trip byte-identically and validate — the new
    fields are additive with empty defaults."""
    r = Report(
        verdict="MIXED",
        confidence=45,
        target_match=TargetMatch(
            reached=[DispositionRef(disposition="loyalist_airdopes", classification="within")],
            missed=[],
        ),
        top_3_changes=[
            TopChange(change=f"c{i}", why=f"w{i}") for i in range(3)
        ],
        strengths_to_preserve=[],
        context_fit_map={},
        verbatim_consumer_voice=[],
        methodology_flags=["single_within_target"],
    )
    s1 = r.to_json()
    r2 = Report.from_json(s1)
    s2 = r2.to_json()
    assert s1 == s2, "legacy (no pain_map) Report no longer round-trips byte-identically"
    assert r2.pain_map == []
    assert r2.top_3_changes[0].derives_from_pains == []
    assert r2.top_3_changes[0].lever_class == ""
    validate_report(r2)
    print("  OK  legacy Report (no pain_map) still round-trips + validates")


def test_quote_authenticity_prefix_match() -> None:
    real = [q for p in _make_painmap_fixture().pain_map for q in p.evidence_quotes]
    assert verify_quote_authenticity(real, _CORPUS) == [], "real quotes flagged as fabricated"
    # Wholesale invention (no real head) is rejected.
    fake = real + [Quote(quote="this exact sentence never appears in the corpus", disposition="x", round=1, context="y")]
    assert verify_quote_authenticity(fake, _CORPUS) == ["this exact sentence never appears in the corpus"]
    # Near-verbatim: a real >=40-char head with a reworded tail is ACCEPTED —
    # opus lightly reworders real reactions, and the prefix match tolerates that
    # (the caller drops what it can't verify; it never fabricates). This is the
    # deliberate reversal of the exact-full-match rule that killed live runs.
    near_verbatim = [Quote(
        quote="I can just make this at home with dates and whey and skip the markup entirely",
        disposition="x", round=6, context="y",
    )]
    assert verify_quote_authenticity(near_verbatim, _CORPUS) == [], "near-verbatim (real head) wrongly rejected"
    print("  OK  verify_quote_authenticity: rejects invention, accepts near-verbatim (prefix match)")


def test_pain_references_catches_dangling() -> None:
    r = _make_painmap_fixture()
    assert verify_pain_references(r.top_3_changes, r.pain_map) == [], "clean refs flagged"
    r.top_3_changes[1].derives_from_pains = ["P3", "P42"]
    assert verify_pain_references(r.top_3_changes, r.pain_map) == ["P42"]
    print("  OK  verify_pain_references catches a dangling id")


def test_lever_space_catches_out_of_scope() -> None:
    r = _make_painmap_fixture()
    assert check_lever_space(r.top_3_changes, r.bet_ranking) == [], "in-scope recs flagged"
    bad = [TopChange(change="Launch a smaller pack / trial size to lower the barrier", why="cheaper entry")]
    hits = check_lever_space(bad, [])
    assert any("smaller pack" in h or "trial size" in h for h in hits), hits
    print("  OK  check_lever_space flags out-of-scope product/pack moves")


def main() -> None:
    print("=== PainMap schema + grounding validators (rocket-2.2.0) ===")
    test_painmap_report_roundtrip_byte_identical()
    test_validate_accepts_painmap_fixture()
    test_validate_rejects_bad_funnel_stage()
    test_validate_rejects_bad_severity()
    test_validate_rejects_bad_lever_class()
    test_validate_rejects_dangling_pain_reference()
    test_legacy_report_without_painmap_roundtrips()
    test_quote_authenticity_prefix_match()
    test_pain_references_catches_dangling()
    test_lever_space_catches_out_of_scope()
    print("PASS — PainMap schema + grounding validators locked.")


if __name__ == "__main__":
    main()
