"""Phase 4 offline test: compute_behavioral_distribution aggregates the R7
behavioral signals of a segment's transcripts into exact counts — the
locked "distributions are Python, not the model" pattern. Transcripts with
no parsed R7 are excluded from n so proportions are over real signals.
No API calls.

Run: python tests/test_l2_v2_behavioral_distribution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import AgentTranscript, BehavioralSignal
from agent.synthesis_l2_v2 import compute_behavioral_distribution


def _transcript(agent_id: int, signal: BehavioralSignal | None) -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id,
        disposition_label="disp_a",
        context_label="ctx_0",
        seed_idx=0,
        encoding_text="R1 ...\nR2 ...\nR3 ...",
        reflection_text="R4 ...\nR5 ...\nR6 ...\nR7 ...",
        behavioral_signal=signal,
    )


def _sig(action: str, would_act: bool) -> BehavioralSignal:
    return BehavioralSignal(action=action, reasoning="x", would_act_within_week=would_act)


def test_counts_are_exact() -> None:
    transcripts = [
        _transcript(0, _sig("tap_cta", True)),
        _transcript(1, _sig("tap_cta", False)),
        _transcript(2, _sig("scroll_past", False)),
        _transcript(3, _sig("seek_info", True)),
        _transcript(4, _sig("scroll_past", False)),
    ]
    dist = compute_behavioral_distribution(transcripts)
    assert dist.counts == {"tap_cta": 2, "scroll_past": 2, "seek_info": 1}, dist.counts
    assert dist.would_act_within_week_count == 2, dist.would_act_within_week_count
    assert dist.n == 5
    assert sum(dist.counts.values()) == dist.n
    print("  OK  behavioral distribution counts are exact")


def test_unparsed_r7_excluded_from_n() -> None:
    """A transcript whose R7 didn't parse (behavioral_signal is None) must
    not inflate n — proportions L3.5 derives must be over real signals."""
    transcripts = [
        _transcript(0, _sig("tap_cta", True)),
        _transcript(1, None),  # R7 failed to parse
        _transcript(2, _sig("scroll_past", False)),
        _transcript(3, None),  # R7 failed to parse
    ]
    dist = compute_behavioral_distribution(transcripts)
    assert dist.n == 2, f"expected n=2 (None signals excluded), got {dist.n}"
    assert dist.counts == {"tap_cta": 1, "scroll_past": 1}
    assert dist.would_act_within_week_count == 1
    print("  OK  unparsed R7 signals are excluded from n")


def test_empty_segment() -> None:
    dist = compute_behavioral_distribution([])
    assert dist.n == 0 and dist.counts == {} and dist.would_act_within_week_count == 0
    # All-None also yields an empty distribution.
    dist2 = compute_behavioral_distribution([_transcript(0, None), _transcript(1, None)])
    assert dist2.n == 0 and dist2.counts == {}
    print("  OK  empty / all-unparsed segment yields an empty distribution")


def test_roundtrips() -> None:
    transcripts = [_transcript(0, _sig("save", True)), _transcript(1, _sig("share", False))]
    dist = compute_behavioral_distribution(transcripts)
    from agent.schema import BehavioralSignalDistribution
    dist2 = BehavioralSignalDistribution.from_dict(dist.to_dict())
    assert dist == dist2, "BehavioralSignalDistribution round-trip mismatch"
    print("  OK  computed distribution round-trips through the schema")


def main() -> None:
    print("=== L2 v2 behavioral distribution smoke ===")
    test_counts_are_exact()
    test_unparsed_r7_excluded_from_n()
    test_empty_segment()
    test_roundtrips()
    print("PASS — R7 distribution is computed deterministically in Python.")


if __name__ == "__main__":
    main()
