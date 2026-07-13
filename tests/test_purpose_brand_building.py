"""Offline test: v2.4 brand-building scoring (P5).

Brand-building grades resonance x brand-memorability: an agent counts only if it
BOTH leaned in (engaged, not scrolled) AND recalled the brand confidently (the R9
probe). "Loved the ad, forgot the brand" therefore fails. Trust is earned by
BREADTH (>= _BROAD_MIN_DISPOSITIONS distinct dispositions registering), not by one
group — the v2.3 SCALE guard ported to a broad frame. No API calls.

Run: python tests/test_purpose_brand_building.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import build_decision, purpose_primary_metric, _BROAD_MIN_DISPOSITIONS
from agent.purpose import resolve_purpose
from agent.schema import AgentTranscript, BehavioralSignal, ProbeSignal
from agent.synthesis_types import DispositionTarget, TargetClassification

BRAND = resolve_purpose("brand_building")


def _t(agent_id: int, label: str, action: str, recall: str | None) -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(action=action, action_reasoning="x",
                                           next_step="nothing", next_step_reasoning="x"),
        probe_signal=(ProbeSignal(novelty=False, brand_recall=recall)
                      if recall is not None else None),
    )


def _tc(classifications: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in classifications.items()
        ],
    )


def _panel(recall_by_disp: dict[str, str], per: int = 3, action: str = "linger"):
    """`per` engaged agents per disposition, each with the given brand_recall."""
    ts, i = [], 0
    for label, recall in recall_by_disp.items():
        for _ in range(per):
            ts.append(_t(i, label, action, recall)); i += 1
    return ts


def test_win_needs_engagement_and_confident_recall() -> None:
    ts = [
        _t(0, "d", "linger", "confident"),     # win
        _t(1, "d", "linger", "unsure"),         # loved it, forgot brand -> fail
        _t(2, "d", "scroll_past", "confident"), # recalled but didn't engage -> fail
        _t(3, "d", "save", "none"),             # engaged, no brand -> fail
    ]
    tc = _tc({"d": "within"})
    (rate, num, denom), _ = purpose_primary_metric(ts, tc, BRAND)
    assert denom == 4 and num == 1, (num, denom)
    assert abs(rate - 0.25) < 1e-9, rate
    print("  OK  win = engaged AND confident brand recall (mis-attribution fails)")


def test_probeless_agent_excluded() -> None:
    ts = [_t(0, "d", "linger", "confident"), _t(1, "d", "linger", None)]  # 2nd: no probe
    (rate, num, denom), _ = purpose_primary_metric(ts, _tc({"d": "within"}), BRAND)
    assert denom == 1 and num == 1, (num, denom)   # probeless excluded, not failed
    print("  OK  a probe-less (pre-v2.4) transcript is excluded, not counted as fail")


def test_broad_resonant_and_branded_scales() -> None:
    # 3 distinct dispositions all engage + recall confidently -> breadth trust
    # HIGH, rate above the brand floor -> SCALE.
    ts = _panel({"a": "confident", "b": "confident", "c": "confident"})
    tc = _tc({"a": "within", "b": "within", "c": "outside"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="brand_building")
    assert d.decision == "SCALE", d.rationale
    assert d.purpose == "brand_building" and d.trust == "HIGH"
    assert d.target_action_rate is not None and d.target_action_rate >= BRAND.provisional_scale_floor
    print("  OK  broad resonant + correctly-branded across dispositions -> SCALE")


def test_loved_but_forgot_brand_does_not_scale() -> None:
    # Everyone engages hard but nobody retains the brand -> resonance without
    # attribution -> NOT SCALE (ITERATE: weak brand linkage).
    ts = _panel({"a": "unsure", "b": "unsure", "c": "none"})
    tc = _tc({"a": "within", "b": "within", "c": "outside"})
    d = build_decision(ts, tc, None, "MIXED", [], [], purpose="brand_building")
    assert d.decision != "SCALE", d.rationale
    assert d.target_action_rate == 0.0
    print("  OK  loved-but-forgot-the-brand -> does NOT scale")


def test_breadth_trust_guard_blocks_narrow_scale() -> None:
    # Only 2 dispositions register (below the breadth floor) even though their
    # rate is high -> DIRECTIONAL trust -> SCALE withheld. This is the guard that
    # stops the provisional bar firing on thin, single-group evidence.
    assert _BROAD_MIN_DISPOSITIONS == 3
    ts = _panel({"a": "confident", "b": "confident"})  # only 2 register
    tc = _tc({"a": "within", "b": "within"})
    d = build_decision(ts, tc, None, "WORKING", [], [], purpose="brand_building")
    assert d.trust == "DIRECTIONAL", d.trust
    assert d.decision != "SCALE", d.rationale
    print("  OK  breadth-trust guard blocks SCALE on too-few registering dispositions")


def main() -> None:
    print("=== brand-building scoring (v2.4 P5) ===")
    test_win_needs_engagement_and_confident_recall()
    test_probeless_agent_excluded()
    test_broad_resonant_and_branded_scales()
    test_loved_but_forgot_brand_does_not_scale()
    test_breadth_trust_guard_blocks_narrow_scale()
    print("PASS — brand-building rewards resonance WITH attribution; breadth-gated.")


if __name__ == "__main__":
    main()
