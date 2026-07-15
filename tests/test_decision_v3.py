"""Offline tests: the v3 decision layer — A3 (buy/research split), A7 (the
coherence guard, incl. the Catch-1 interaction with A4 reorderers), A5 (SCALE
reachable with execution pains, blocked by A7), and A6 (the panel trust-ceiling
warning). No API calls.

Run: python tests/test_decision_v3.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import (
    build_decision,
    _intent_action_incoherent,
    _research_over_frame,
)
from agent.purpose import resolve_purpose
from agent.run_service import _trust_ceiling_warning
from agent.schema import AgentTranscript, BehavioralSignal, Decision, Pain
from agent.synthesis_types import DispositionTarget, TargetClassification

DIRECT = resolve_purpose("direct_sell")
COLD = resolve_purpose("cold_hook")
RETAIN = resolve_purpose("retain_winback")


def _t(agent_id: int, label: str, action: str, next_step: str) -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(
            action=action, action_reasoning="x",
            next_step=next_step, next_step_reasoning="x"),
    )


def _tc(cls_map: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in cls_map.items()
        ],
    )


def _pain(pid: str, severity: str, stage: str = "conversion") -> Pain:
    return Pain(id=pid, pain="p", funnel_stage=stage, severity=severity,
                within_target=True, cited_by=["a", "b"])


# ---- A3: the buy / research split ----

def test_a3_buy_and_research_are_separate() -> None:
    """The headline counts BUY-intent only; research_first is a separate,
    honestly-labelled companion — never folded in (the '63% = buyers +
    info-seekers' fix)."""
    ts = (
        [_t(i, "aud", "tap_cta", "buy_now") for i in range(3)]
        + [_t(10 + i, "aud", "linger", "buy_at_restock") for i in range(2)]
        + [_t(20 + i, "aud", "linger", "research_first") for i in range(4)]
        + [_t(30, "aud", "scroll_past", "nothing")]
    )
    d = build_decision(ts, _tc({"aud": "within"}), None, "MIXED", [], [],
                       purpose="direct_sell")
    # buy-intent = buy_now(3) + buy_at_restock(2) = 5 of 10
    assert (d.target_action_num, d.target_action_denom) == (5, 10)
    assert abs(d.target_action_rate - 0.5) < 1e-9
    # research = research_first(4) of 10 — reported SEPARATELY
    assert (d.research_num, d.research_denom) == (4, 10)
    assert abs(d.research_rate - 0.4) < 1e-9
    # never double-counted into the headline
    assert d.target_action_num + d.research_num <= d.target_action_denom
    print("  OK  A3: buy headline (5/10) and research companion (4/10) are separate")


def test_a3_research_helper_over_frame() -> None:
    frame = (
        [_t(i, "aud", "linger", "research_first") for i in range(3)]
        + [_t(10 + i, "aud", "tap_cta", "buy_now") for i in range(2)]
    )
    rate, num, denom = _research_over_frame(frame)
    assert (num, denom) == (3, 5) and abs(rate - 0.6) < 1e-9
    assert _research_over_frame([]) == (None, 0, 0)
    print("  OK  A3: _research_over_frame counts research_first over parsed signals")


# ---- A7: the coherence guard ----

def test_a7_fires_on_buy_intent_without_handraise() -> None:
    """Buy-intent (buy_now) present but ZERO in-feed hand-raise -> the guard
    fires, and blocks the otherwise-strong SCALE."""
    ts = (
        [_t(i, "aud_a", "scroll_past", "buy_now") for i in range(5)]
        + [_t(10 + i, "aud_b", "scroll_past", "buy_now") for i in range(5)]
    )
    d = build_decision(ts, _tc({"aud_a": "within", "aud_b": "within"}),
                       None, "MIXED", [], [], purpose="direct_sell")
    assert d.coherence_incoherent is True
    # buy-intent is 100% and trust would be HIGH, but A7 blocks SCALE.
    assert d.decision != "SCALE", d.rationale
    print("  OK  A7: buy_now with no hand-raise -> incoherent -> SCALE blocked")


def test_a7_does_not_fire_on_reorder_pattern() -> None:
    """CATCH 1 — the A4 interaction. A running-low loyalist who scrolls past a
    familiar brand and intends buy_at_restock is COHERENT; the guard must not
    fire on that pattern (it keys on buy_now, not buy_at_restock)."""
    reorderers = [_t(i, "aud", "scroll_past", "buy_at_restock") for i in range(5)]
    assert _intent_action_incoherent(reorderers, DIRECT) is False
    # end-to-end: a whole panel of scroll-past reorderers is coherent AND can
    # legitimately reach SCALE (they will re-buy) — exactly what A4 must allow.
    ts = (
        [_t(i, "aud_a", "scroll_past", "buy_at_restock") for i in range(5)]
        + [_t(10 + i, "aud_b", "scroll_past", "buy_at_restock") for i in range(5)]
    )
    d = build_decision(ts, _tc({"aud_a": "within", "aud_b": "within"}),
                       None, "MIXED", [], [], purpose="direct_sell")
    assert d.coherence_incoherent is False
    assert d.decision == "SCALE", d.rationale
    print("  OK  A7: reorder pattern (buy_at_restock + scroll) is coherent -> can SCALE")


def test_a7_does_not_fire_with_handraise_present() -> None:
    frame = (
        [_t(i, "aud", "tap_cta", "buy_now") for i in range(3)]
        + [_t(10 + i, "aud", "scroll_past", "nothing") for i in range(2)]
    )
    assert _intent_action_incoherent(frame, DIRECT) is False
    print("  OK  A7: any in-feed hand-raise (tap/save/share) clears the guard")


def test_a7_exempt_on_existing_customer_frame() -> None:
    # retain targets existing customers, who legitimately buy without engaging
    # THIS ad — the guard is scoped away from the existing frame.
    frame = [_t(i, "loyalist_a", "scroll_past", "buy_now") for i in range(5)]
    assert _intent_action_incoherent(frame, RETAIN) is False
    print("  OK  A7: exempt on the existing-customer (retain) frame")


# ---- A5: SCALE reachability ----

def test_a5_scale_reachable_with_execution_pain() -> None:
    """The headline change that makes SCALE a real decision: strong + coherent +
    HIGH trust reaches SCALE even WITH an execution pain ('scale while iterating')
    — previously any within pain blocked it."""
    ts = (
        [_t(i, "aud_a", "tap_cta", "buy_now") for i in range(5)]
        + [_t(10 + i, "aud_b", "tap_cta", "buy_now") for i in range(5)]
    )
    tc = _tc({"aud_a": "within", "aud_b": "within"})
    d = build_decision(ts, tc, None, "MIXED", [], [_pain("P1", "execution")],
                       purpose="direct_sell")
    assert d.decision == "SCALE", d.rationale
    assert d.load_bearing_pain_id == "P1"   # the execution pain is carried, not a blocker
    # same panel, STRUCTURAL pain -> REBUILD (step 4 still wins).
    d2 = build_decision(ts, tc, None, "FAILING",
                        [], [_pain("P1", "structural", stage="attention")],
                        purpose="direct_sell")
    assert d2.decision == "REBUILD", d2.rationale
    print("  OK  A5: SCALE reachable with an execution pain; structural -> REBUILD")


def test_a5_a7_interaction_blocks_scale() -> None:
    """The two guards compose: the SAME strong panel, if incoherent (buy-intent
    with no hand-raise), is blocked from SCALE by A7."""
    ts = (
        [_t(i, "aud_a", "scroll_past", "buy_now") for i in range(5)]
        + [_t(10 + i, "aud_b", "scroll_past", "buy_now") for i in range(5)]
    )
    d = build_decision(ts, _tc({"aud_a": "within", "aud_b": "within"}),
                       None, "MIXED", [], [], purpose="direct_sell")
    assert d.coherence_incoherent is True and d.decision != "SCALE"
    print("  OK  A5+A7: strong-but-incoherent panel is kept out of SCALE")


# ---- A6: the panel trust-ceiling warning ----

def test_a6_trust_ceiling_warning() -> None:
    assert _trust_ceiling_warning(2) is None
    assert _trust_ceiling_warning(3) is None
    w1 = _trust_ceiling_warning(1)
    assert w1 is not None and "1 within-target disposition;" in w1 and "SCALE" in w1
    w0 = _trust_ceiling_warning(0)
    assert w0 is not None and "0 within-target dispositions" in w0
    print("  OK  A6: trust-ceiling warning fires for <2 within, silent for >=2")


# ---- schema: the new Decision fields round-trip ----

def test_decision_v3_fields_roundtrip() -> None:
    d = Decision(
        decision="SCALE", target_action_rate=0.8, trust="HIGH",
        research_rate=0.1, research_num=1, research_denom=10,
        coherence_incoherent=False,
        by_cycle_position={"running_low": {"rate": 0.9, "num": 9, "denom": 10}},
    )
    back = Decision.from_dict(d.to_dict())
    assert back.research_rate == 0.1 and (back.research_num, back.research_denom) == (1, 10)
    assert back.coherence_incoherent is False
    assert back.by_cycle_position["running_low"]["num"] == 9
    # legacy Decision (no v3 keys) loads with safe defaults.
    legacy = Decision.from_dict({"decision": "ITERATE", "target_action_rate": 0.5})
    assert legacy.research_rate is None and legacy.coherence_incoherent is False
    assert legacy.by_cycle_position == {}
    print("  OK  Decision v3 fields round-trip; legacy dict loads with defaults")


def main() -> None:
    print("=== v3 decision layer (A3/A5/A6/A7) ===")
    test_a3_buy_and_research_are_separate()
    test_a3_research_helper_over_frame()
    test_a7_fires_on_buy_intent_without_handraise()
    test_a7_does_not_fire_on_reorder_pattern()
    test_a7_does_not_fire_with_handraise_present()
    test_a7_exempt_on_existing_customer_frame()
    test_a5_scale_reachable_with_execution_pain()
    test_a5_a7_interaction_blocks_scale()
    test_a6_trust_ceiling_warning()
    test_decision_v3_fields_roundtrip()
    print("PASS — A3 split, A7 guard (+ Catch-1 reorder exemption), A5 reachable SCALE, A6 warning.")


if __name__ == "__main__":
    main()
