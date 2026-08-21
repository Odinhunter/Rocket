"""An action the persona would have taken anyway is not an ad effect.

⚠⚠ WHY THIS FILE EXISTS. Nothing in this system compared a persona's own
history to the advertised brand at scoring time. `cycle_position` was computed
per agent and consumed in exactly one place — as a *reported breakdown*. Never a
filter, never an adjustment, never an input to a verdict. That single absence
produced two verdict-flipping bugs and one wrong headline on a paid run.

THE MEASURED CASE (2026-08-22, `docs/fnb_stance_discrimination_result.md`):
an `upgrader` whose own anchor named the advertised brand AND its price
(*"₹104 for a 52g bar… you order another box on Zepto"*) reached
`buy_at_restock` in 7 of 8 agents — **two of them `cycle_position=just_bought`,
i.e. they had a box at home already.** That was reported as the sharpest signal
the project had produced. It was retention, scored as conversion.

  F1 — an existing customer can be crowned the RETARGET champion, so the
       customer is told "Right ad, wrong person" about their own loyalists.
  F2 — a retention ad can reach SCALE ("ship it") on reorders where nobody
       engaged with the creative at all.

Both are the same absence, which is why they are fixed and tested together.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from agent.decision import build_decision                       # noqa: E402
from agent.schema import AgentTranscript, BehavioralSignal      # noqa: E402
from agent.synthesis_types import (                             # noqa: E402
    DispositionTarget, TargetClassification,
)


def _t(agent_id: int, label: str, *, action: str, next_step: str,
       cycle: str = "mid_cycle") -> AgentTranscript:
    """Action and next_step set INDEPENDENTLY — the whole point is the pattern
    where someone scrolls past and still says they'd rebuy."""
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        cycle_position=cycle,
        behavioral_signal=BehavioralSignal(
            action=action, action_reasoning="x",
            next_step=next_step, next_step_reasoning="x"),
    )


def _tc(classifications: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in classifications.items()
        ],
    )


# --------------------------------------------------------------------------
# F1 — a brand's own loyalist must not become the "wrong person" champion
# --------------------------------------------------------------------------

def test_a_loyalist_restocking_does_not_fire_retarget() -> None:
    """The exact production shape. Cold prospects (within target) barely act;
    the brand's own loyalists reorder at 100% because that is what loyalists do.

    ⚠ Before the guard this cleared `_RETARGET_GAP` (0.15) and
    `_RETARGET_FLOOR` (0.20) and returned RETARGET — telling the customer their
    ad was landing on the wrong people, when it was landing on the people who
    already buy from them every month."""
    ts = (
        [_t(i, "aspirant_cold_prospect", action="scroll_past", next_step="nothing")
         for i in range(8)]
        + [_t(10 + i, "loyalist_of_this_brand",
              action="scroll_past", next_step="buy_at_restock",
              cycle="just_bought")
           for i in range(8)]
    )
    tc = _tc({"aspirant_cold_prospect": "within", "loyalist_of_this_brand": "outside"})
    d = build_decision(ts, tc, None, "MIXED", [], [], purpose="direct_sell")

    assert d.champion_disposition != "loyalist_of_this_brand", (
        "a loyalist reordering is the null hypothesis, not a rival audience"
    )
    assert d.decision != "RETARGET", d.rationale


def test_a_genuine_prospect_champion_still_fires_retarget() -> None:
    """⭐ THE CONTROL, and it is the half that matters. A guard that suppressed
    every champion would 'fix' F1 by making RETARGET unreachable. A non-customer
    stance out-performing the target must still be reported."""
    ts = (
        [_t(i, "aspirant_declared_target", action="scroll_past", next_step="nothing")
         for i in range(8)]
        + [_t(10 + i, "pragmatist_undeclared", action="tap_cta", next_step="buy_now")
           for i in range(8)]
    )
    tc = _tc({"aspirant_declared_target": "within", "pragmatist_undeclared": "outside"})
    d = build_decision(ts, tc, None, "MIXED", [], [], purpose="direct_sell")

    assert d.decision == "RETARGET", d.rationale
    assert d.champion_disposition == "pragmatist_undeclared"


def test_retain_still_reaches_its_prospect_champion() -> None:
    """⚠ REGRESSION PIN, and honest about what it proves. `retain_winback`
    recasts the classification map so existing customers ARE "within", so the
    guard is a no-op there and its champion is a PROSPECT by construction —
    the real "wrong crowd" story for a retention ad, which must stay reachable.

    ⭐ A first draft of the fix carried an `exclude_existing_customers=False`
    opt-out for retain and this test claimed to verify it. A mutation run showed
    flipping that flag changed nothing — the test was vacuous for that mutation
    because the champion here is a prospect either way. The knob was deleted
    rather than kept as configuration that cannot do anything; this test remains
    as the pin that retain's champion path still works."""
    ts = (
        [_t(i, "loyalist_target", action="scroll_past", next_step="nothing")
         for i in range(4)]
        + [_t(4, "loyalist_target", action="tap_cta", next_step="buy_now")]
        + [_t(10 + i, "aspirant_new_prospect", action="tap_cta", next_step="buy_now")
           for i in range(5)]
    )
    tc = _tc({"loyalist_target": "within", "aspirant_new_prospect": "outside"})
    d = build_decision(ts, tc, None, "MIXED", [], [], purpose="retain_winback")

    assert d.decision == "RETARGET", d.rationale
    assert d.champion_disposition == "aspirant_new_prospect"


# --------------------------------------------------------------------------
# F2 — a reorder nobody engaged with is a subscription, not a creative
# --------------------------------------------------------------------------

def test_retain_cannot_scale_when_nobody_engaged_with_the_ad() -> None:
    """Everyone scrolls straight past and still says they will rebuy — which is
    exactly what a customer on a monthly cadence does whether or not the ad
    exists.

    ⚠⚠ `_intent_action_incoherent` cannot catch this: its own docstring says it
    "cannot fire on the A4 reorder pattern (buy_at_restock + scroll_past)"
    because it keys on `buy_now`, and it is scoped to direct-sell. For retain
    that pattern IS the headline — so the one purpose whose number is built from
    reorders was the one purpose with no reorder guard."""
    ts = (
        [_t(i, "loyalist_a", action="scroll_past", next_step="buy_at_restock")
         for i in range(5)]
        + [_t(10 + i, "lapsed_b", action="scroll_past", next_step="buy_at_restock")
           for i in range(4)]
    )
    tc = _tc({"loyalist_a": "within", "lapsed_b": "within"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="retain_winback")

    assert d.decision != "SCALE", (
        f"100% reorder with zero engagement must not ship an ad: {d.rationale}"
    )
    assert d.coherence_incoherent is True


def test_retain_scales_when_they_actually_engaged() -> None:
    """⭐ THE CONTROL. One non-scroll action anywhere in the claiming set makes
    the signal coherent — 'stopped to look, then said they'd reorder' is real
    evidence, and the guard must not swallow it."""
    ts = (
        [_t(i, "loyalist_a", action="tap_cta", next_step="buy_at_restock")
         for i in range(5)]
        + [_t(10 + i, "lapsed_b", action="linger", next_step="buy_at_restock")
           for i in range(4)]
    )
    tc = _tc({"loyalist_a": "within", "lapsed_b": "within"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="retain_winback")

    assert d.decision == "SCALE", d.rationale
    assert d.coherence_incoherent is False


def test_the_direct_sell_guard_is_untouched() -> None:
    """⚠ REGRESSION PIN. F2 added a second guard; the SCALE branch now reads a
    SET of blocking flags rather than one name. This asserts the original guard
    still blocks — the refactor's whole risk is silently dropping it."""
    ts = [_t(i, "aspirant_x", action="scroll_past", next_step="buy_now")
          for i in range(6)]
    tc = _tc({"aspirant_x": "within"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="direct_sell")

    assert d.decision != "SCALE", d.rationale
    assert d.coherence_incoherent is True
