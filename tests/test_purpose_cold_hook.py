"""Offline test: v2.4 cold-hook scoring (the metric seam, P3).

Cold-hook grades the STOP, not the sale: the headline metric is the fraction of
a (broad, cold) panel doing anything other than scroll_past, and the SCALE bar
is the cold-hook floor, not direct-sell's. The RETARGET/REBUILD/ITERATE branch
structure transfers unchanged (attention-stage pain -> REBUILD). Direct-sell
stays byte-for-byte v2.3. No API calls.

Run: python tests/test_purpose_cold_hook.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import build_decision, purpose_primary_metric
from agent.purpose import resolve_purpose
from agent.schema import AgentTranscript, BehavioralSignal, Pain
from agent.synthesis_types import DispositionTarget, TargetClassification


def _t(agent_id: int, label: str, action: str, would_act: bool) -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="commute_scroll",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(
            action=action, action_reasoning="x",
            next_step="buy_now" if would_act else "nothing", next_step_reasoning="x"),
    )


def _tc(classifications: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in classifications.items()
        ],
    )


def _pain(pid: str, severity: str, stage: str = "attention") -> Pain:
    return Pain(id=pid, pain="p", funnel_stage=stage, severity=severity,
                within_target=True, cited_by=["a", "b"])


COLD = resolve_purpose("cold_hook")
DIRECT = resolve_purpose("direct_sell")


def test_stop_rate_is_broad_and_ignores_would_act() -> None:
    # 2 within + 1 outside disposition. Most linger/seek (stop) but almost none
    # would buy — the cold audience stops without purchasing.
    ts = (
        [_t(i, "aud_a", "linger", False) for i in range(4)]
        + [_t(10 + i, "aud_b", "linger", False) for i in range(4)]
        + [_t(20, "aud_a", "scroll_past", False), _t(21, "aud_b", "scroll_past", False)]
        + [_t(30 + i, "cold_x", "linger", False) for i in range(3)]
        + [_t(40, "cold_x", "scroll_past", False)]
    )
    tc = _tc({"aud_a": "within", "aud_b": "within", "cold_x": "outside"})
    (rate, num, denom), by_disp = purpose_primary_metric(ts, tc, COLD)
    # broad frame: 11 stops (linger) of 14 with signal.
    assert denom == 14 and num == 11, (num, denom)
    assert abs(rate - 11 / 14) < 1e-9, rate
    # direct-sell over the same transcripts reads ~0 (nobody would buy).
    (d_rate, _n, _d), _ = purpose_primary_metric(ts, tc, DIRECT)
    assert d_rate == 0.0, d_rate
    print("  OK  cold-hook headline = broad stop-and-lean-in rate, not would-act")


def test_clean_broad_hook_scales_at_cold_floor() -> None:
    # Broad panel stops well above the cold floor (0.55), no within pain,
    # 2 within dispositions -> HIGH trust -> SCALE. (direct-sell's 0.75 floor
    # is NOT what gates this — the cold floor is.)
    ts = (
        [_t(i, "aud_a", "linger", False) for i in range(5)]
        + [_t(10 + i, "aud_b", "linger", False) for i in range(5)]
        + [_t(20, "aud_a", "scroll_past", False), _t(21, "aud_b", "scroll_past", False)]
    )
    tc = _tc({"aud_a": "within", "aud_b": "within"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="cold_hook")
    assert d.decision == "SCALE", d.rationale
    assert d.purpose == "cold_hook"
    assert d.target_action_rate is not None and d.target_action_rate >= COLD.provisional_scale_floor
    # the same strong-stop / zero-buy panel would NOT scale as direct-sell.
    d2 = build_decision(ts, tc, None, "WORKING", [], [], purpose="direct_sell")
    assert d2.decision != "SCALE", d2.rationale
    print("  OK  clean broad hook -> SCALE at the cold floor; not as direct-sell")


def test_attention_pain_rebuilds() -> None:
    # Broad stop rate high, but the TARGET has a structural attention-stage pain
    # (they scroll past) -> REBUILD, exactly as the direct-sell structure does.
    ts = (
        [_t(i, "aud_a", "linger", False) for i in range(3)]
        + [_t(10 + i, "aud_b", "linger", False) for i in range(3)]
    )
    tc = _tc({"aud_a": "within", "aud_b": "within"})
    d = build_decision(ts, tc, None, "FAILING",
                       [], [_pain("P1", "structural", "attention")], purpose="cold_hook")
    assert d.decision == "REBUILD", d.rationale
    print("  OK  structural attention pain -> REBUILD under cold-hook")


def test_hooks_wrong_crowd_retargets() -> None:
    # The within target barely stops; a non-target disposition hooks hard ->
    # RETARGET ('right hook, wrong crowd'). Uses within-vs-champion, not the
    # broad headline, as the base.
    ts = (
        [_t(i, "aud_a", "scroll_past", False) for i in range(4)]
        + [_t(4, "aud_a", "linger", False)]           # within: 1/5 stop = 0.20
        + [_t(10 + i, "cold_x", "linger", False) for i in range(5)]  # outside: 5/5 = 1.0
    )
    tc = _tc({"aud_a": "within", "cold_x": "outside"})
    d = build_decision(ts, tc, None, "MIXED", [], [], purpose="cold_hook")
    assert d.decision == "RETARGET", d.rationale
    assert d.champion_disposition == "cold_x"
    print("  OK  target barely hooks, outsider hooks hard -> RETARGET")


def test_direct_sell_unchanged_through_seam() -> None:
    # Sanity: routing direct-sell through the new dispatcher is byte-identical to
    # within_target_action_rate (2/3 within act -> 0.666..).
    ts = [_t(0, "aud", "tap_cta", True), _t(1, "aud", "tap_cta", True),
          _t(2, "aud", "scroll_past", False)]
    tc = _tc({"aud": "within"})
    (rate, num, denom), _ = purpose_primary_metric(ts, tc, DIRECT)
    assert num == 2 and denom == 3 and abs(rate - 2 / 3) < 1e-9
    print("  OK  direct-sell through the seam == within_target_action_rate")


def main() -> None:
    print("=== cold-hook scoring (v2.4 P3) ===")
    test_stop_rate_is_broad_and_ignores_would_act()
    test_clean_broad_hook_scales_at_cold_floor()
    test_attention_pain_rebuilds()
    test_hooks_wrong_crowd_retargets()
    test_direct_sell_unchanged_through_seam()
    print("PASS — cold-hook grades the stop; branch structure transfers; direct-sell intact.")


if __name__ == "__main__":
    main()
