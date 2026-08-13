"""Did the panel actually contain the buyer this ad is aimed at?

THE RUN THIS EXISTS FOR — SY PB Bar, 2026-08-13, a real ~$4 run. The classifier
looked at the creative and wrote, correctly, that it was aimed at "protein-
curious snackers who like chocolate/wafer formats". The library held six
supplement-buyer identities and nobody who would trade up from a chocolate bar.
Two of them were classified `within` anyway, `no_match_note` came back EMPTY,
and the run returned **FAILING / REBUILD at trust HIGH, confidence 84**.

Nothing was broken in the arithmetic. The wrong people were in the room and the
instrument had no way to notice.

TWO HOLES, TWO FIXES:

1. `no_match_note` is the sole trigger for `pool_archetype_mismatch`, and the
   model is asked for it only when NOTHING matches — a precondition it decides
   for itself, read afterwards with a bare `.get()`. If every disposition
   landed outside, that precondition is objectively true whatever the model
   wrote, so Python synthesizes the note. A guard that depends on the thing it
   guards is not a guard.

2. The SY PB Bar failure was a PARTIAL gap — two types matched — so no field
   existed for it at all. `uncovered_target_note` asks the question
   unconditionally and is REQUIRED in the tool schema, so it must be answered
   rather than skipped. Null is a judgement; silence was not.

⚠ WHAT THIS DELIBERATELY DOES NOT DO. It does not warn before spending, and it
does not touch the verdict. The user's explicit call, 2026-08-14: *"we are not
showing coverage gaps at all - all of this goes into the how did the run happen
part at the end of the results page."* `pool_coverage_gap` is a disclosure flag,
NOT `pool_archetype_mismatch` — that one forces METHODOLOGY_GAP and caps
confidence at 20, and wiring this to it would reverse that decision sideways.

Offline. No API calls.

Run: .venv/bin/python -m pytest tests/test_coverage_gap_detection.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import _VALID_METHODOLOGY_FLAGS
from agent.synthesis_types import TargetClassification
from agent.target_id import _TOOL, _build_target_classification

POOL = [
    ("aspirant_clean_label", "a clean-label wellness buyer"),
    ("pragmatist_protein_snacker", "keeps a protein bar around"),
]


def _tool_input(classifications, **over):
    data = {
        "inferred_target_description": (
            "protein-curious snackers who like chocolate/wafer formats"
        ),
        "target_reasoning": "the pack and the wafer format",
        "inferred_audience": {"gender": "any", "age_band": "25_34"},
        "inferred_purpose": "direct_sell",
        "disposition_classifications": [
            {"disposition_label": label, "classification": c,
             "reasoning": "because"}
            for label, c in classifications
        ],
    }
    data.update(over)
    return data


# ---- 1. the deterministic backstop ---------------------------------------

def test_zero_within_synthesizes_the_note_the_model_withheld() -> None:
    """Every disposition outside and the model volunteered nothing. Python
    fills it in, because "no dispositions match" is a fact about the
    classifications, not an opinion the classifier gets to skip."""
    tc = _build_target_classification(
        _tool_input([("aspirant_clean_label", "outside"),
                     ("pragmatist_protein_snacker", "outside")]),
        POOL,
    )
    assert tc.no_match_note, (
        "no disposition was within-target and no_match_note is still empty — "
        "the backstop did not fire, and pool_archetype_mismatch will never "
        "trigger for a pool that matched nobody"
    )
    print("  zero within-target synthesizes the missing no_match_note ✓")


def test_the_models_own_note_is_never_overwritten() -> None:
    """The backstop fills a hole; it does not talk over the classifier, whose
    note names a better-fitting archetype and is more useful than ours."""
    theirs = "this needs a confectionery trade-up pool"
    tc = _build_target_classification(
        _tool_input([("aspirant_clean_label", "outside"),
                     ("pragmatist_protein_snacker", "outside")],
                    no_match_note=theirs),
        POOL,
    )
    assert tc.no_match_note == theirs
    print("  a note the model DID write survives untouched ✓")


def test_a_matching_pool_is_left_alone() -> None:
    """The positive control. Without it a backstop that fired unconditionally
    would pass both tests above and quietly flag every healthy run."""
    tc = _build_target_classification(
        _tool_input([("aspirant_clean_label", "within"),
                     ("pragmatist_protein_snacker", "outside")]),
        POOL,
    )
    assert not tc.no_match_note, (
        "a pool with a within-target type was flagged as matching nobody"
    )
    print("  a pool that matched somebody is not flagged ✓")


# ---- 2. the partial gap — the SY PB Bar case ------------------------------

def test_the_partial_gap_has_a_field_and_it_is_required() -> None:
    """The exact shape of the failure: two types classified `within`, and the
    buyer the ad is aimed at still absent. `no_match_note` is correctly silent
    here — its precondition is genuinely false — which is why a second field
    had to exist."""
    missing = "nobody here would trade up from a chocolate bar"
    tc = _build_target_classification(
        _tool_input([("aspirant_clean_label", "within"),
                     ("pragmatist_protein_snacker", "within")],
                    uncovered_target_note=missing),
        POOL,
    )
    assert tc.no_match_note is None, "no_match_note fired on a partial gap"
    assert tc.uncovered_target_note == missing
    print("  a PARTIAL gap is captured where no_match_note cannot see it ✓")


def test_the_question_is_required_so_it_cannot_be_skipped() -> None:
    """⚠ The whole reason the original hole existed: an optional field read
    with `.get()` returns None on silence, and silence is indistinguishable
    from "no gap". Requiring it forces an answer; the answer may still be
    null."""
    assert "uncovered_target_note" in _TOOL["input_schema"]["required"], (
        "uncovered_target_note is optional again — the model can omit it and "
        "the gap becomes invisible exactly as it did on SY PB Bar"
    )
    assert "uncovered_target_note" in _TOOL["input_schema"]["properties"]
    desc = _TOOL["input_schema"]["properties"]["uncovered_target_note"]["description"]
    assert "EVEN IF some dispositions matched" in desc, (
        "the prompt no longer tells the model to answer despite a partial "
        "match — which is the precondition bug, reintroduced"
    )
    print("  the coverage question is REQUIRED and asks despite a match ✓")


# ---- 3. disclosure only, never a verdict ---------------------------------

def test_the_flag_exists_and_is_not_the_verdict_forcing_one() -> None:
    assert "pool_coverage_gap" in _VALID_METHODOLOGY_FLAGS
    assert "pool_archetype_mismatch" in _VALID_METHODOLOGY_FLAGS
    assert "pool_coverage_gap" != "pool_archetype_mismatch"
    print("  the disclosure flag is distinct from the verdict-forcing one ✓")


def test_assess_raises_the_disclosure_flag_not_the_verdict_one() -> None:
    """Wiring a partial gap to `pool_archetype_mismatch` would force
    METHODOLOGY_GAP and cap confidence at 20 on every partial gap — turning a
    footnote the user asked for into a headline they did not."""
    import inspect

    from agent import synthesis_assess
    src = inspect.getsource(synthesis_assess)
    assert "tc.uncovered_target_note" in src, (
        "assess never reads the coverage note, so the flag can never be raised"
    )
    i_note = src.index("tc.uncovered_target_note")
    window = src[i_note:i_note + 400]
    assert "pool_coverage_gap" in window
    assert "pool_archetype_mismatch" not in window, (
        "the coverage note is wired to the VERDICT-FORCING flag"
    )
    print("  a coverage note raises disclosure, never the verdict flag ✓")


# ---- 4. it survives a round trip -----------------------------------------

def test_the_note_round_trips_and_legacy_artifacts_still_load() -> None:
    tc = TargetClassification(
        inferred_target_description="x", target_reasoning="y",
        disposition_classifications=[],
        uncovered_target_note="the chocolate-bar switcher is missing",
    )
    back = TargetClassification.from_dict(tc.to_dict())
    assert back.uncovered_target_note == "the chocolate-bar switcher is missing"

    # Every target_classification.json written before 2026-08-14 has no such
    # key and must still load.
    legacy = tc.to_dict()
    del legacy["uncovered_target_note"]
    assert TargetClassification.from_dict(legacy).uncovered_target_note is None
    print("  round-trips, and pre-v4 artifacts still load ✓")
