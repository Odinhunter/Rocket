"""Phase 4 offline test: compute_behavioral_distribution aggregates the R7
behavioral signals of a segment's transcripts into exact counts — the
locked "distributions are Python, not the model" pattern. Transcripts with
no parsed R7 are excluded from n so proportions are over real signals.
No API calls.

Run: python tests/test_l2_behavioral_distribution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import AgentTranscript, BehavioralSignal
from agent.synthesis_l2 import _build_l2_summary, compute_behavioral_distribution


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


def _sig(action: str, next_step: str) -> BehavioralSignal:
    return BehavioralSignal(
        action=action, action_reasoning="x", next_step=next_step, next_step_reasoning="x"
    )


def test_counts_are_exact() -> None:
    transcripts = [
        _transcript(0, _sig("tap_cta", "buy_now")),
        _transcript(1, _sig("tap_cta", "research_first")),
        _transcript(2, _sig("scroll_past", "nothing")),
        _transcript(3, _sig("linger", "buy_at_restock")),
        _transcript(4, _sig("scroll_past", "nothing")),
    ]
    dist = compute_behavioral_distribution(transcripts)
    assert dist.counts == {"tap_cta": 2, "scroll_past": 2, "linger": 1}, dist.counts
    assert dist.next_step_counts == {
        "buy_now": 1, "research_first": 1, "nothing": 2, "buy_at_restock": 1
    }, dist.next_step_counts
    # buy-intent = buy_now + buy_at_restock (research_first is NOT counted).
    assert dist.buy_intent_count == 2, dist.buy_intent_count
    assert dist.n == 5
    assert sum(dist.counts.values()) == dist.n
    assert sum(dist.next_step_counts.values()) == dist.n
    print("  OK  behavioral distribution counts (action + next_step) are exact")


def test_unparsed_signal_excluded_from_n() -> None:
    """A transcript whose signal didn't parse (behavioral_signal is None) must
    not inflate n — proportions L3.5 derives must be over real signals."""
    transcripts = [
        _transcript(0, _sig("tap_cta", "buy_now")),
        _transcript(1, None),  # signal failed to parse
        _transcript(2, _sig("scroll_past", "nothing")),
        _transcript(3, None),  # signal failed to parse
    ]
    dist = compute_behavioral_distribution(transcripts)
    assert dist.n == 2, f"expected n=2 (None signals excluded), got {dist.n}"
    assert dist.counts == {"tap_cta": 1, "scroll_past": 1}
    assert dist.next_step_counts == {"buy_now": 1, "nothing": 1}
    assert dist.buy_intent_count == 1
    print("  OK  unparsed signals are excluded from n")


def test_empty_segment() -> None:
    dist = compute_behavioral_distribution([])
    assert dist.n == 0 and dist.counts == {} and dist.next_step_counts == {}
    assert dist.buy_intent_count == 0
    # All-None also yields an empty distribution.
    dist2 = compute_behavioral_distribution([_transcript(0, None), _transcript(1, None)])
    assert dist2.n == 0 and dist2.counts == {}
    print("  OK  empty / all-unparsed segment yields an empty distribution")


def test_roundtrips() -> None:
    transcripts = [
        _transcript(0, _sig("save", "buy_at_restock")),
        _transcript(1, _sig("share", "mention_to_someone")),
    ]
    dist = compute_behavioral_distribution(transcripts)
    from agent.schema import BehavioralSignalDistribution
    dist2 = BehavioralSignalDistribution.from_dict(dist.to_dict())
    assert dist == dist2, "BehavioralSignalDistribution round-trip mismatch"
    print("  OK  computed distribution round-trips through the schema")


def test_malformed_representative_quotes_degrade_not_crash() -> None:
    """The σ study surfaced the L2 model occasionally emitting
    representative_quotes as a bare string (or list) instead of the
    {round: Quote} object the schema asks for. _build_l2_summary must degrade
    to no-quotes for that segment, never crash the (already-paid-for) run."""
    base = {
        "summary_paragraph": "they mostly scrolled past.",
        "within_cell_variance": "tight",
        "outlier_note": None,
        "emotional_read": "flat",
        "friction_summary": "price unclear",
    }
    for bad in ("a stray string the model emitted", ["not", "an", "object"], 42):
        summary = _build_l2_summary("disp_a", "disp_a|impulsive", {**base, "representative_quotes": bad})
        assert summary.representative_quotes == {}, f"expected no quotes for {type(bad).__name__}"
        assert summary.summary_paragraph == "they mostly scrolled past."
    # A well-formed map still parses.
    good = {**base, "representative_quotes": {
        "1": {"quote": "another clean bar", "disposition": "disp_a", "round": 1, "context": "c"}}}
    summary = _build_l2_summary("disp_a", "disp_a|impulsive", good)
    assert summary.representative_quotes[1].quote == "another clean bar"
    print("  OK  malformed representative_quotes (str/list/int) degrade to {}; good map parses")


def main() -> None:
    print("=== L2 v2 behavioral distribution smoke ===")
    test_counts_are_exact()
    test_unparsed_r7_excluded_from_n()
    test_empty_segment()
    test_roundtrips()
    test_malformed_representative_quotes_degrade_not_crash()
    print("PASS — R7 distribution is computed deterministically in Python.")


if __name__ == "__main__":
    main()
