"""Offline tests: v3 A4 — purchase-cycle position. The mix resolver, the
deterministic (uncached) cycle prose, the transcript carry-through, the
mix-independent by-cycle breakdown, and the END-TO-END A4/A7 interaction
(running-low reorderers flow coherently and can reach SCALE). No API calls.

Run: python tests/test_cycle_position.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import build_decision, _buy_intent_by_cycle
from agent.panel import CYCLE_POSITIONS, DEFAULT_CYCLE_MIX, resolve_cycle_mix
from agent.runtime import _cycle_line
from agent.schema import AgentTranscript, BehavioralSignal
from agent.synthesis_types import DispositionTarget, TargetClassification


def _t(agent_id: int, label: str, action: str, next_step: str,
       cycle: str = "mid_cycle") -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id, disposition_label=label, context_label="feed",
        seed_idx=0, encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(
            action=action, action_reasoning="x",
            next_step=next_step, next_step_reasoning="x"),
        cycle_position=cycle,
    )


def _tc(cls_map: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t", target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in cls_map.items()
        ],
    )


# ---- the mix resolver (spec-declarable, not a buried baseline) ----

def test_resolve_cycle_mix() -> None:
    assert resolve_cycle_mix(None) == DEFAULT_CYCLE_MIX
    assert abs(sum(DEFAULT_CYCLE_MIX.values()) - 1.0) < 1e-9
    assert set(DEFAULT_CYCLE_MIX) <= set(CYCLE_POSITIONS)
    # normalises to sum 1
    r = resolve_cycle_mix({"running_low": 3.0, "mid_cycle": 1.0})
    assert abs(r["running_low"] - 0.75) < 1e-9 and abs(r["mid_cycle"] - 0.25) < 1e-9
    # loud on bad keys / empty / non-positive weights
    for bad in ({"nope": 1.0}, {}, {"mid_cycle": 0.0}, {"mid_cycle": -1.0}):
        try:
            resolve_cycle_mix(bad)
            raise AssertionError(f"should reject {bad}")
        except ValueError:
            pass
    print("  OK  resolve_cycle_mix: None->default, normalises, rejects bad keys/weights")


# ---- the deterministic (uncached) cycle prose ----

def test_cycle_line_prose() -> None:
    """⚠⚠ THIS TEST USED TO RATIFY A BUG. Until 2026-08-22 it asserted
    `"recently stocked up on health wellness nutrition"` — i.e. it pinned the
    raw category SLUG being read aloud to the persona as a mass noun. With the
    F&B pack that produced *"you are partway through your current fnb world"*,
    and a model reading the same slug elsewhere told every agent in a $3.85 run
    that the ad was for "international food and drink" — for an INDIAN pack.

    ⭐ A test that asserts the defect is a stronger blocker than no test at all:
    fixing the bug broke the suite, which is how the bug survived. It now
    asserts the LAW instead of the output — no category value, of any spelling,
    may reach this line."""
    assert "nearly out of" in _cycle_line("running_low", "coffee")
    assert "recently stocked up" in _cycle_line("just_bought", "health_wellness_nutrition")
    assert "partway through" in _cycle_line("mid_cycle", "coffee")
    # an unknown position falls back to mid_cycle prose — never crashes.
    assert "partway through" in _cycle_line("weird", "coffee")


def test_no_category_value_of_any_spelling_reaches_the_persona() -> None:
    """⭐⭐ THE LAW, not the string. `_cycle_line` reaches EVERY agent in EVERY
    run, so a category token here is read by every simulated person alive.

    Mutation-proof by construction: the sentinel is passed as the argument, so
    if anyone re-introduces interpolation in any form — raw, underscored,
    humanised or title-cased — one of these four assertions fires."""
    sentinel = "zzq_marker_category"
    for position in ("just_bought", "mid_cycle", "running_low", "unknown"):
        line = _cycle_line(position, sentinel)
        assert sentinel not in line
        assert sentinel.replace("_", " ") not in line
        assert sentinel.replace("_", " ").title() not in line
        assert "zzq" not in line.lower()
    print("  OK  _cycle_line templates deterministic prose (category interpolated)")


# ---- the transcript carry-through ----

def test_agent_transcript_cycle_roundtrip() -> None:
    t = _t(1, "aud", "tap_cta", "buy_now", "running_low")
    back = AgentTranscript.from_dict(t.to_dict())
    assert back.cycle_position == "running_low"
    # legacy transcript (no cycle_position key) -> mid_cycle default.
    legacy = AgentTranscript.from_dict({
        "agent_id": 2, "disposition_label": "d", "context_label": "c",
        "seed_idx": 0, "encoding_text": "", "reflection_text": ""})
    assert legacy.cycle_position == "mid_cycle"
    print("  OK  AgentTranscript carries cycle_position; legacy dict -> mid_cycle")


# ---- the by-cycle breakdown (the mix-independent primary read) ----

def test_by_cycle_breakdown_is_mix_independent() -> None:
    # running-low buys hard (3/4); mid-cycle soft (1/4). Same disposition.
    ts = (
        [_t(i, "aud", "tap_cta", "buy_now", "running_low") for i in range(3)]
        + [_t(3, "aud", "scroll_past", "nothing", "running_low")]
        + [_t(10, "aud", "tap_cta", "buy_now", "mid_cycle")]
        + [_t(11 + i, "aud", "scroll_past", "nothing", "mid_cycle") for i in range(3)]
    )
    d = build_decision(ts, _tc({"aud": "within"}), None, "MIXED", [], [],
                       purpose="direct_sell")
    bc = d.by_cycle_position
    assert bc["running_low"] == {"rate": 0.75, "num": 3, "denom": 4}, bc
    assert bc["mid_cycle"] == {"rate": 0.25, "num": 1, "denom": 4}, bc
    # Catch 2: the blended headline is EXACTLY the sum over cycles — so the
    # breakdown is the honest read and the headline just re-weights it.
    assert d.target_action_num == bc["running_low"]["num"] + bc["mid_cycle"]["num"] == 4
    assert d.target_action_denom == 8
    print("  OK  A4: per-cycle breakdown is exact; the headline blends it (4/8)")


def test_by_cycle_helper_skips_unparsed() -> None:
    frame = [
        _t(0, "aud", "tap_cta", "buy_now", "running_low"),
        AgentTranscript(agent_id=1, disposition_label="aud", context_label="c",
                        seed_idx=0, encoding_text="", reflection_text="",
                        behavioral_signal=None, cycle_position="running_low"),
    ]
    bc = _buy_intent_by_cycle(frame)
    assert bc["running_low"] == {"rate": 1.0, "num": 1, "denom": 1}  # None excluded
    print("  OK  _buy_intent_by_cycle excludes unparsed signals from the denom")


def test_by_cycle_empty_for_non_buy_purpose() -> None:
    ts = [_t(i, "aud", "linger", "nothing", "running_low") for i in range(4)]
    d = build_decision(ts, _tc({"aud": "within"}), None, "MIXED", [], [],
                       purpose="cold_hook")
    assert d.by_cycle_position == {}
    print("  OK  by-cycle breakdown is populated only for buy-frame jobs")


# ---- END-TO-END: A4 + A7 flow coherently (the Catch-1 interaction) ----

def test_a4_a7_reorderers_flow_coherently() -> None:
    """A panel of running-low loyalists who scroll past a familiar brand and
    intend buy_at_restock flows through the WHOLE decision layer coherently:
    A7 leaves them alone (keys on buy_now, not buy_at_restock), the by-cycle
    read shows their buys, and they can reach SCALE — exactly the pattern A4
    generates, and exactly what the guard must NOT block."""
    ts = (
        [_t(i, "loyal_a", "scroll_past", "buy_at_restock", "running_low") for i in range(5)]
        + [_t(10 + i, "loyal_b", "scroll_past", "buy_at_restock", "running_low") for i in range(5)]
    )
    d = build_decision(ts, _tc({"loyal_a": "within", "loyal_b": "within"}),
                       None, "MIXED", [], [], purpose="direct_sell")
    assert d.coherence_incoherent is False, "A7 must not fire on reorderers"
    assert d.by_cycle_position["running_low"] == {"rate": 1.0, "num": 10, "denom": 10}
    assert d.decision == "SCALE", d.rationale
    print("  OK  A4/A7 end-to-end: running-low reorderers are coherent and can SCALE")


def main() -> None:
    print("=== v3 A4 purchase-cycle position ===")
    test_resolve_cycle_mix()
    test_cycle_line_prose()
    test_agent_transcript_cycle_roundtrip()
    test_by_cycle_breakdown_is_mix_independent()
    test_by_cycle_helper_skips_unparsed()
    test_by_cycle_empty_for_non_buy_purpose()
    test_a4_a7_reorderers_flow_coherently()
    print("PASS — cycle sampled + carried + rendered; mix-independent breakdown; "
          "A4/A7 coherent end-to-end.")


if __name__ == "__main__":
    main()
