"""Offline test: v2.4 awareness/informer breadth read (P6, the finale).

Informer output is a BREADTH count, not an agent rate: how many distinct audience
TYPES registered the ad as news (R8 novelty). Built as pure Python over the
structured probe -> replay-stable by construction (the discriminating check the
advisor named). Deliberately DISJOINT from brand-building (novelty vs attribution)
so the two purposes stay distinct rulers. No API calls.

Run: python tests/test_purpose_informer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import (
    build_decision,
    _agent_win,
    _INFORMER_REGISTER_THRESHOLD,
)
from agent.purpose import resolve_purpose
from agent.schema import AgentTranscript, BehavioralSignal, Pain, ProbeSignal
from agent.synthesis_types import DispositionTarget, TargetClassification

INFORMER = resolve_purpose("awareness_informer")
BRAND = resolve_purpose("brand_building")


def _t(agent_id: int, label: str, novelty: bool,
       action: str = "linger", recall: str = "none") -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(action=action, action_reasoning="x",
                                           next_step="nothing", next_step_reasoning="x"),
        probe_signal=ProbeSignal(novelty=novelty, brand_recall=recall),
    )


def _tc(labels: list[str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification="ambiguous", reasoning="")
            for lab in labels
        ],
    )


def _disp(label: str, novel: int, total: int, start: int) -> list[AgentTranscript]:
    return [_t(start + i, label, i < novel) for i in range(total)]


def test_breadth_is_a_disposition_count_not_agent_rate() -> None:
    # ONE disposition is wildly novel (10/10); three others register nothing.
    # Agent-level novelty rate would be 10/13 = 0.77 (high) — but breadth is 1 of
    # 4 audience types = 0.25. The read must reflect the disposition count.
    ts = (_disp("a", 10, 10, 0)
          + _disp("b", 0, 1, 100) + _disp("c", 0, 1, 200) + _disp("d", 0, 1, 300))
    d = build_decision(ts, _tc(["a", "b", "c", "d"]), None, "MIXED", [], [],
                       purpose="awareness_informer")
    assert d.target_action_num == 1 and d.target_action_denom == 4, (d.target_action_num, d.target_action_denom)
    assert abs(d.target_action_rate - 0.25) < 1e-9, d.target_action_rate
    assert d.decision == "ITERATE", d.rationale
    print("  OK  breadth is a distinct-disposition count, not an agent-level rate")


def test_broad_registration_scales_and_is_replay_stable() -> None:
    # 4 audience types each register the news (majority novel) -> breadth 1.0,
    # >= 3 registered -> HIGH trust -> SCALE.
    ts = (_disp("a", 3, 3, 0) + _disp("b", 3, 3, 10)
          + _disp("c", 2, 3, 20) + _disp("d", 3, 3, 30))
    tc = _tc(["a", "b", "c", "d"])
    d1 = build_decision(ts, tc, None, "WORKING", [], [], purpose="awareness_informer")
    d2 = build_decision(ts, tc, None, "WORKING", [], [], purpose="awareness_informer")
    assert d1.decision == "SCALE", d1.rationale
    assert d1.trust == "HIGH" and d1.target_action_num == 4 and d1.target_action_denom == 4
    # replay-stable: identical count/decision on the same transcripts.
    assert (d1.decision, d1.target_action_num, d1.target_action_denom, d1.target_action_rate) == \
           (d2.decision, d2.target_action_num, d2.target_action_denom, d2.target_action_rate)
    print("  OK  broad registration -> SCALE; breadth count replay-stable")


def test_structural_attention_pain_rebuilds() -> None:
    ts = _disp("a", 3, 3, 0) + _disp("b", 3, 3, 10) + _disp("c", 3, 3, 20)
    pain = Pain(id="P1", pain="p", funnel_stage="attention", severity="structural",
                within_target=True, cited_by=["a", "b"])
    d = build_decision(ts, _tc(["a", "b", "c"]), None, "FAILING", [], [pain],
                       purpose="awareness_informer")
    assert d.decision == "REBUILD", d.rationale
    print("  OK  structural attention block -> REBUILD (few notice it)")


def test_no_novelty_signal_is_inconclusive() -> None:
    # every agent lacks the probe -> no novelty signal -> INCONCLUSIVE.
    ts = [AgentTranscript(agent_id=i, disposition_label="a", context_label="f",
                          seed_idx=0, encoding_text="", reflection_text="",
                          behavioral_signal=BehavioralSignal("linger", "x", "nothing", "x"),
                          probe_signal=None) for i in range(3)]
    d = build_decision(ts, _tc(["a"]), None, "MIXED", [], [], purpose="awareness_informer")
    assert d.decision == "INCONCLUSIVE" and d.target_action_rate is None
    print("  OK  no novelty signal -> INCONCLUSIVE (no faked breadth)")


def test_informer_disjoint_from_brand_building() -> None:
    # An agent that learned something (novelty) but scrolled and forgot the brand:
    # a WIN for informer, NOT for brand-building. Zero shared win-components ->
    # the two purposes are genuinely distinct rulers.
    t = _t(0, "a", novelty=True, action="scroll_past", recall="none")
    assert _agent_win(t, INFORMER) is True
    assert _agent_win(t, BRAND) is False
    # and the inverse: engaged + attributed but learned nothing -> brand yes, informer no.
    t2 = _t(1, "a", novelty=False, action="linger", recall="confident")
    assert _agent_win(t2, INFORMER) is False
    assert _agent_win(t2, BRAND) is True
    print("  OK  informer (novelty) and brand-building (attribution) share no win-components")


def test_threshold_is_named_and_provisional() -> None:
    assert _INFORMER_REGISTER_THRESHOLD == 0.5
    print("  OK  register threshold is a named, provisional constant (0.5)")


def main() -> None:
    print("=== awareness/informer breadth read (v2.4 P6) ===")
    test_breadth_is_a_disposition_count_not_agent_rate()
    test_broad_registration_scales_and_is_replay_stable()
    test_structural_attention_pain_rebuilds()
    test_no_novelty_signal_is_inconclusive()
    test_informer_disjoint_from_brand_building()
    test_threshold_is_named_and_provisional()
    print("PASS — informer breadth is a disposition count, replay-stable, novelty-based.")


if __name__ == "__main__":
    main()
