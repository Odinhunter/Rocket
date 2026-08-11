"""render-8 — everything that reaches an agent ADDRESSES it, never describes it.

Through render-7 the persona core was third person ("She's been taking hair and
skin supplements for about two years...") and `runtime.run_agent` passed it as
the ENTIRE system block with no framing around it. Nothing anywhere said the
person described WAS the model. A third-person brief in the system slot asks a
model to portray someone; "you are" asks it to be them. The user's call,
2026-08-11, taken with the raw 1886-char system block in front of them.

⚠ THE POINT OF THIS FILE IS THE SWEEP. Third person reached the agent from FIVE
places, and fixing only the persona core would leave the seams talking ABOUT the
person in the same breath the core talks TO them. Two of the five are model
written and can only be pinned as INSTRUCTION offline — the same limit
`test_persona_system_render_6_contract` already concedes for register. The other
three are deterministic and are pinned HARD, by driving the real functions.

⚠ WHY NOT A BLANKET PRONOUN SWEEP OVER EVERY AGENT-FACING STRING: it false-fires
on legitimate third person that is not about the person.
`_creative_copy_block` says "you read them off the picture as you scroll" —
"them" is the words on the ad. The scope here is the composed deterministic
strings only, and `test_the_sweep_would_catch_a_regression` mutation-proves that
the scope is still tight enough to catch one.
"""

from __future__ import annotations

import re

from agent import runtime as rt
from agent.render import _CONTEXT_SYSTEM, _PERSONA_SYSTEM

# Third-person reference to the PERSON. Deliberately narrow: possessives and
# subject pronouns plus the two noun phrases a render drifts into.
_THIRD_PERSON = re.compile(
    r"\b(he|she|him|her|hers|his|they|them|their|theirs|"
    r"this person|the person|the buyer|the consumer)\b",
    re.IGNORECASE,
)

# Stands in for the model-written context render, which cannot be asserted on
# offline. Deliberately free of pronouns so any hit below is the DETERMINISTIC
# text's fault and never this stub's.
_STUB_CONTEXT = "Lying down, phone held above face, scrolling with no goal."


def _offending(text: str) -> list[str]:
    return _THIRD_PERSON.findall(text)


# ---- The three deterministic strings, driven not grepped ----


def test_the_cycle_line_addresses_the_person() -> None:
    """`_cycle_line` is templated, not model-written, so it is pinnable exactly.
    All three positions, because only `mid_cycle` is the default and a regression
    in the other two would ride to production behind a passing test."""
    for position in ("just_bought", "mid_cycle", "running_low"):
        line = rt._cycle_line(position, "health_wellness_nutrition")
        assert not _offending(line), (
            f"{position}: third-person reference reaches the agent: "
            f"{_offending(line)} in {line!r}"
        )
        assert "YOU" in line or "you" in line, (
            f"{position}: the cycle line must address the person, not just "
            f"avoid naming them — got {line!r}"
        )
    print("  OK  _cycle_line addresses the person in all 3 cycle positions")


def test_the_context_block_addresses_the_person() -> None:
    """The composed encoding preamble: feed header + cycle line + attention gate.
    Driven through the real function with a pronoun-free stub standing in for the
    model-written context prose."""
    for position in ("just_bought", "mid_cycle", "running_low"):
        block = rt._context_block(_STUB_CONTEXT, position, "health_wellness_nutrition")
        assert not _offending(block), (
            f"{position}: third-person reference in the context block: "
            f"{_offending(block)}"
        )
    block = rt._context_block(_STUB_CONTEXT, "mid_cycle", "coffee")
    assert "IN YOUR FEED" in block, "the feed header must address the person"
    assert "whether you would be interested" in block, (
        "the attention gate must address the person"
    )
    print("  OK  _context_block: header, cycle line and attention gate all 2nd person")


def test_the_encoding_and_reflection_turns_already_addressed_the_person() -> None:
    """These two were ALREADY second person before render-8, asserted so a sweep
    that fixed the core and broke the task turn cannot pass.

    ⚠ THE DETECTOR IS DELIBERATELY NOT RUN OVER THESE, and the reason is the
    whole reason a blanket pronoun sweep is wrong. R8 asks "did the ad tell you
    something about the brand you didn't already know — 'huh, I didn't know THEY
    made this', a claim that changed your picture of THEM?" Both are the BRAND,
    not the person, and both are correct English that must survive. The same
    holds for `_creative_copy_block`'s "you read THEM off the picture" (the
    words on the ad). Third person about a third party is fine; third person
    about the PERSON is the defect. Only strings with no third-party referent
    can be swept, which is why the hard pins above cover the cycle line and the
    context block and stop there. Here we assert the POSITIVE property instead."""
    assert "You are a real person" in rt._ENCODING_USER
    assert "goes through your head" in rt._ENCODING_USER
    # All five purposes, not a sample: awareness_informer and brand_building
    # append the R8 / R9 probe blocks, which no other purpose ever sees.
    for purpose in (
        "direct_sell",
        "cold_hook",
        "awareness_informer",
        "brand_building",
        "retain_winback",
    ):
        turn = rt._reflection_user_for(purpose)
        assert "what do you remember about" in turn, purpose
        assert "hold you back" in turn, purpose
        # The person is never referred to in the third person even though the
        # BRAND may be — these are the phrasings a regression would produce.
        for bad in ("what do they remember", "hold them back", "the person would"):
            assert bad not in turn.lower(), f"{purpose}: {bad!r}"
    print("  OK  the encoding + all 5 reflection turns address the person")


# ---- The two model-written strings, pinnable only as instruction ----


def test_the_persona_writer_is_told_to_address_the_person() -> None:
    """`_PERSONA_SYSTEM` produces the core; the core is model output, so offline
    can only pin that the INSTRUCTION demands second person. Whether the output
    complies is the live check (`scripts/render_persona_samples.py`).

    ⚠ Asserted on the instruction's DEMANDS, never by sweeping `_PERSONA_SYSTEM`
    for pronouns — the prompt necessarily contains "he/she/they" inside the very
    rule that bans them, exactly as it contains the banned analyst words as
    negative examples."""
    assert "SECOND-PERSON" in _PERSONA_SYSTEM, (
        "the writer must be told the output is second person"
    )
    assert "ADDRESSED TO" in _PERSONA_SYSTEM
    assert 'ADDRESS THEM AS "you" IN EVERY SENTENCE' in _PERSONA_SYSTEM, (
        "the per-sentence rule is what stops a render drifting back to "
        "third person halfway down"
    )
    assert "character brief" in _PERSONA_SYSTEM, (
        "the WHY has to travel with the rule — a brief gets portrayed, an "
        "identity gets inhabited"
    )
    # The old instruction was the exact opposite and must be gone.
    assert 'no "you are" framing' not in _PERSONA_SYSTEM, (
        "render-7 explicitly FORBADE the framing render-8 requires"
    )
    assert "THIRD-PERSON description" not in _PERSONA_SYSTEM
    print("  OK  _PERSONA_SYSTEM demands second-person output")


def test_the_context_writer_is_told_to_address_the_person() -> None:
    """`_CONTEXT_SYSTEM` mandated "they" through render-7, and for a real reason:
    one context render composes onto ANY persona, so it could not assume a
    gender. Second person keeps that property and drops the third person — the
    rationale must survive the change or someone restores "they" for
    gender-neutrality and undoes it."""
    assert 'ADDRESS THE PERSON AS "you"' in _CONTEXT_SYSTEM
    assert 'Refer to the person as "they"' not in _CONTEXT_SYSTEM, (
        "the render-7 mandate is the thing being reversed"
    )
    assert "gender-neutral" in _CONTEXT_SYSTEM, (
        "why 'you' replaces 'they' rather than 'he/she' must travel with it"
    )
    print("  OK  _CONTEXT_SYSTEM demands second-person address")


def test_the_utterances_stay_first_person_while_the_frame_moved() -> None:
    """The HOW YOU TALK block is second person in its CAPTION and first person in
    its CONTENTS, and both are correct at once. A sweep that "fixed" the
    utterances to second person would destroy the register anchor — those lines
    are the person speaking, not the person being addressed."""
    # ⚠ Assert the FULL template line, not the bare label. "HOW YOU TALK"
    # appears TWICE in _PERSONA_SYSTEM — once as a section heading and once as
    # the emitted template — so a bare-label assertion passes while the template
    # alone reverts to "HOW THEY TALK". That mutation SURVIVED the first version
    # of this test; it is the repo's own "never assert a pattern that appears
    # twice" rule, caught here by the mutation harness rather than in review.
    assert "HOW YOU TALK (register only — how your own sentences sound." in (
        _PERSONA_SYSTEM
    ), "the emitted caption template, not the heading, must be second person"
    assert "HOW THEY TALK" not in _PERSONA_SYSTEM, (
        "no occurrence of the render-7 caption may survive anywhere in the "
        "prompt — heading or template"
    )
    assert "UTTERANCES stay first person" in _PERSONA_SYSTEM, (
        "without this the writer 'corrects' the utterances into second person "
        "and the shown register is lost"
    )
    assert "Never repeat these lines" in _PERSONA_SYSTEM, (
        "the C1 anti-parroting caption survives render-8"
    )
    print("  OK  caption is 2nd person, utterances stay 1st — both pinned")


def test_the_utterances_are_banned_from_mentioning_advertising() -> None:
    """render-9. The core is CACHED and replayed as the system prompt for every
    ad this person is ever shown, so an utterance mentioning advertising is a
    pre-written stance toward the stimulus — it contaminates the measurement
    before the ad exists.

    ⚠ render-8 carried this as ONE soft line ("These are ad-agnostic") and 2 of
    6 rendered personas emitted one anyway. Offline can only pin that the ban is
    stated with its word list and its reason; whether output complies is the live
    check (`scripts/render_persona_samples.py`, which greps the rendered
    utterances)."""
    for word in ("advert", "commercial", "marketing", "sponsored", "reel", "promo"):
        assert word in _PERSONA_SYSTEM, f"{word!r} missing from the banned list"
    assert "ABSOLUTE BAN, NOT A PREFERENCE" in _PERSONA_SYSTEM
    assert "CACHED and replayed" in _PERSONA_SYSTEM, (
        "the REASON must travel with the ban — without it the next editor "
        "reads it as fussiness and softens it, which is how render-8 lost it"
    )
    # The per-line final check, which is the half that made it stick.
    assert "LAST, ON THE UTTERANCES" in _PERSONA_SYSTEM
    print("  OK  the advertising ban is explicit, enumerated and justified")


def test_the_utterances_are_capped_short() -> None:
    """render-9. render-8 emitted 80-140 char utterances with up to 4 commas,
    stacking brand + price + channel + verdict into one breath. The block is the
    register the AGENT inherits, so a comma-spliced sample teaches comma-spliced
    reactions."""
    assert "KEEP THEM SHORT" in _PERSONA_SYSTEM
    assert "ONE thought per line" in _PERSONA_SYSTEM
    assert "90 characters" in _PERSONA_SYSTEM, "the length ceiling must be numeric"
    assert "AT MOST ONE COMMA" in _PERSONA_SYSTEM
    # The negative example is a real render-8 output, kept verbatim so the rule
    # shows the failure rather than describing it.
    assert "biozyme 1kg chocolate, ₹2,699 on healthkart" in _PERSONA_SYSTEM, (
        "the counter-example is a REAL render-8 utterance — a described rule "
        "is weaker than a shown one"
    )
    print("  OK  the utterance length/comma cap is stated numerically")


def test_the_sweep_would_catch_a_regression() -> None:
    """⚠ THE MUTATION PROOF, in-process. Every assertion above is an ABSENCE, and
    an absence test that cannot fail is the repo's most-repeated defect. This
    reverts each deterministic site to its render-7 wording and requires the
    detector to fire.

    Not a substitute for reverting the real source — that was done by hand for
    all five sites — but it keeps the detector honest after any later edit."""
    original = dict(rt._CYCLE_PROSE)
    try:
        rt._CYCLE_PROSE["mid_cycle"] = (
            "partway through their current {cat} — not thinking about restocking yet."
        )
        line = rt._cycle_line("mid_cycle", "coffee")
        assert _offending(line), (
            "the detector missed a reverted _CYCLE_PROSE — it is not scoped "
            "tightly enough to catch a real regression"
        )
        block = rt._context_block(_STUB_CONTEXT, "mid_cycle", "coffee")
        assert _offending(block), "the detector missed it through _context_block"
    finally:
        rt._CYCLE_PROSE.clear()
        rt._CYCLE_PROSE.update(original)

    # And the restored version must be clean again, or the test above passed for
    # the wrong reason (a permanently-dirty module would fail every assertion).
    assert not _offending(rt._cycle_line("mid_cycle", "coffee"))
    print("  OK  the detector fires on a reverted site, and the revert is undone")
