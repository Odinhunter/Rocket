"""P1 offline tests (rocket-2.3.0, the decision layer): the pure signal
functions that feed resolve_decision — the within-target action rate, the
per-disposition action rates, and the load-bearing within-target pain pick.

The signal math is checked on small synthetic transcripts; the load-bearing
pick is checked against the four real Session-11 painmaps snapshotted into
tests/fixtures/decision/. No model call (offline).

Run: python tests/test_decision_signals.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.decision import (
    action_by_disposition,
    load_bearing_within_pain,
    within_target_action_rate,
)
from agent.schema import AgentTranscript, BehavioralSignal, Pain
from agent.synthesis_types import DispositionTarget, TargetClassification

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "decision"


def _t(agent_id: int, label: str, would_act: bool | None) -> AgentTranscript:
    """A transcript with a parsed R7 signal, or would_act=None for an
    unparsed signal (behavioral_signal is None -> excluded from the denominator)."""
    bs = None
    if would_act is not None:
        bs = BehavioralSignal(
            action="tap_cta" if would_act else "scroll_past",
            action_reasoning="x",
            next_step="buy_now" if would_act else "nothing",
            next_step_reasoning="x",
        )
    return AgentTranscript(
        agent_id=agent_id,
        disposition_label=label,
        context_label="feed_default",
        seed_idx=0,
        encoding_text="",
        reflection_text="",
        behavioral_signal=bs,
    )


def _tc(classifications: dict[str, str]) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="t",
        target_reasoning="r",
        disposition_classifications=[
            DispositionTarget(disposition_label=lab, classification=cls, reasoning="")
            for lab, cls in classifications.items()
        ],
    )


def _load_pains(name: str) -> list[Pain]:
    data = json.loads((FIXTURES / name).read_text())
    return [Pain.from_dict(p) for p in data["pain_map"]]


def test_within_target_action_rate() -> None:
    # within: loyalist 2/3 act, aspirant 1/2 act -> 3/5 = 0.6 overall.
    # outside: skeptic 0/2. One within agent has an unparsed signal (excluded).
    ts = [
        _t(1, "loyalist", True),
        _t(2, "loyalist", True),
        _t(3, "loyalist", False),
        _t(4, "aspirant", True),
        _t(5, "aspirant", False),
        _t(6, "aspirant", None),  # unparsed -> not counted in n
        _t(7, "skeptic", False),
        _t(8, "skeptic", False),
    ]
    tc = _tc({"loyalist": "within", "aspirant": "within", "skeptic": "outside"})
    rate, num, denom = within_target_action_rate(ts, tc)
    assert (num, denom) == (3, 5), (num, denom)
    assert abs(rate - 0.6) < 1e-9, rate
    print("  within_target_action_rate: 3/5 = 0.60, unparsed signal excluded ✓")


def test_within_target_action_rate_empty() -> None:
    # No within-target disposition -> (None, 0, 0), never a ZeroDivisionError.
    ts = [_t(1, "skeptic", True), _t(2, "skeptic", False)]
    tc = _tc({"skeptic": "outside"})
    rate, num, denom = within_target_action_rate(ts, tc)
    assert rate is None and (num, denom) == (0, 0), (rate, num, denom)
    print("  within_target_action_rate: empty within-set -> (None, 0, 0) ✓")


def test_action_by_disposition() -> None:
    ts = [
        _t(1, "loyalist", True),
        _t(2, "loyalist", True),
        _t(3, "loyalist", False),
        _t(4, "aspirant", True),
        _t(5, "aspirant", False),
        _t(6, "skeptic", None),  # all unparsed -> denom 0 -> rate 0.0
    ]
    by = action_by_disposition(ts)
    assert by["loyalist"] == (2 / 3, 2, 3), by["loyalist"]
    assert by["aspirant"] == (0.5, 1, 2), by["aspirant"]
    assert by["skeptic"] == (0.0, 0, 0), by["skeptic"]
    print("  action_by_disposition: per-label rates + empty-denom -> 0.0 ✓")


def test_load_bearing_within_pain() -> None:
    # Earliest-funnel-stage within-target pain drives the severity; the four real
    # painmaps pin the pick (and its severity — the ITERATE/REBUILD pivot).
    expected = {
        # (fixture, pain_id, severity, funnel_stage)
        "mb_whey.painmap.json": ("P1", "execution", "consideration"),
        "buzzword.painmap.json": ("P5", "execution", "attention"),
        "twt_pack.painmap.json": ("P2", "execution", "consideration"),
        "proski.painmap.json": ("P1", "structural", "attention"),
    }
    for name, (pid, sev, stage) in expected.items():
        pains = _load_pains(name)
        lb = load_bearing_within_pain(pains)
        assert lb is not None, name
        assert lb.id == pid, f"{name}: expected {pid}, got {lb.id}"
        assert lb.severity == sev, f"{name}: expected {sev}, got {lb.severity}"
        assert lb.funnel_stage == stage, f"{name}: expected {stage}, got {lb.funnel_stage}"
        print(f"  load_bearing[{name.split('.')[0]:9}] -> {lb.id} ({lb.severity}, {lb.funnel_stage}) ✓")
    # No within-target pain -> None.
    assert load_bearing_within_pain([]) is None
    print("  load_bearing_within_pain: no within pain -> None ✓")


def main() -> None:
    test_within_target_action_rate()
    test_within_target_action_rate_empty()
    test_action_by_disposition()
    test_load_bearing_within_pain()
    print("PASS — decision signals: rate math + earliest-stage load-bearing pain.")


if __name__ == "__main__":
    main()
