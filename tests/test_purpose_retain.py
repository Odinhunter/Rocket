"""Offline test: v2.4 retain/win-back machinery (P4).

Retain scores re-engagement among EXISTING/LAPSED-customer dispositions. The
machinery is real but INERT until a brand library carries such personas: a run
with none is honestly dormant (INCONCLUSIVE), never a faked reorder rate on cold
prospects. With them present it scores like direct-sell over that frame. No API.

Run: python tests/test_purpose_retain.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import build_decision, _is_existing_customer
from agent.schema import AgentTranscript, BehavioralSignal
from agent.synthesis_types import DispositionTarget, TargetClassification


def _t(agent_id: int, label: str, would_act: bool) -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(
            action="tap_cta" if would_act else "scroll_past",
            reasoning="x", would_act_within_week=would_act),
    )


def _tc(classifications: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in classifications.items()
        ],
    )


def test_existing_customer_detection() -> None:
    assert _is_existing_customer("loyalist_daily_drinker")
    assert _is_existing_customer("lapsed_protein_user")
    assert _is_existing_customer("subscriber_auto_reorder")
    assert not _is_existing_customer("aspirant_clean_label")
    assert not _is_existing_customer("skeptic_lapsed_protein")  # stance is 'skeptic'
    print("  OK  existing-customer detection keys off the stance prefix")


def test_dormant_when_no_existing_customers() -> None:
    # A normal acquisition panel (no loyalist/lapsed personas) -> retain is inert.
    ts = [_t(0, "aspirant_x", True), _t(1, "skeptic_y", False)]
    tc = _tc({"aspirant_x": "within", "skeptic_y": "outside"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="retain_winback")
    assert d.decision == "INCONCLUSIVE", d.decision
    assert d.purpose == "retain_winback"
    assert d.target_action_rate is None            # no faked reorder rate
    assert "existing-customer" in d.rationale
    print("  OK  no existing-customer personas -> dormant INCONCLUSIVE (no faked rate)")


def test_scores_when_existing_customers_present() -> None:
    # Two existing-customer dispositions strongly re-engage, no pain, HIGH trust
    # -> SCALE at the retain floor.
    ts = (
        [_t(i, "loyalist_a", True) for i in range(4)]
        + [_t(10 + i, "lapsed_b", True) for i in range(4)]
        + [_t(20, "loyalist_a", False)]
    )
    tc = _tc({"loyalist_a": "within", "lapsed_b": "within"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="retain_winback")
    assert d.decision == "SCALE", d.rationale
    assert d.target_action_rate is not None and d.target_action_rate >= 0.75
    # denominator counts only existing-customer transcripts (the retain frame).
    assert d.target_action_denom == 9, d.target_action_denom
    print("  OK  existing customers re-engage strongly -> SCALE over the retain frame")


def test_retarget_when_prospects_beat_existing() -> None:
    # Lapsed/loyal barely re-engage; a NON-existing prospect group re-engages
    # hard -> RETARGET ('lands on new prospects, not the lapsed target').
    ts = (
        [_t(i, "loyalist_a", False) for i in range(4)]
        + [_t(4, "loyalist_a", True)]                 # existing: 1/5
        + [_t(10 + i, "aspirant_new", True) for i in range(5)]   # prospects: 5/5
    )
    tc = _tc({"loyalist_a": "within", "aspirant_new": "outside"})
    d = build_decision(ts, tc, None, "MIXED", [], [], purpose="retain_winback")
    assert d.decision == "RETARGET", d.rationale
    assert d.champion_disposition == "aspirant_new"
    print("  OK  prospects out-engage the lapsed target -> RETARGET")


def main() -> None:
    print("=== retain/win-back machinery (v2.4 P4) ===")
    test_existing_customer_detection()
    test_dormant_when_no_existing_customers()
    test_scores_when_existing_customers_present()
    test_retarget_when_prospects_beat_existing()
    print("PASS — retain scores existing customers; honestly dormant without them.")


if __name__ == "__main__":
    main()
