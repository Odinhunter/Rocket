"""L3 — deterministic population synthesis (the quantitative core).

rocket-2.2.0 (v2.2 diagnosis rung, Phase 7): L3 no longer makes a model call.
Its narrative themes + per-context fit were subsumed by the assess pass, which
reads the FULL raw reaction corpus directly. What remains is the DETERMINISTIC
quantitative core the rest of the stack still needs:
  - segment/population behavioral-signal distributions  -> L3.5 funnel projection
  - confidence_signals (distinct within-target disposition count, homogenization
    count, total segments)  -> the assess pass's deterministic methodology flags
  - a pooled quote list  -> kept in the l3_summary.json artifact for debugging

No Sonnet call, no themes, no context_fit — those are the assess pass's job now.
The old model-produced theme/context_fit fields on L3Summary remain (defaulting
empty) so the artifact shape and legacy run.json round-trips are unchanged.
"""

from __future__ import annotations

from agent.schema import BehavioralSignalDistribution, Quote
from agent.synthesis_types import (
    ConfidenceSignals,
    L2Summary,
    L3Summary,
    TargetClassification,
)

_log_name = __name__  # (no logger needed — deterministic, no I/O)


# ---- Public entry point ----


def synthesize_population(
    l2_summaries: list[L2Summary],
    target_classification: TargetClassification,
    config=None,   # retained for call-site compatibility; L3 no longer calls a model
) -> L3Summary:
    """Deterministic population synthesis: behavioral-signal distributions +
    confidence signals + a pooled quote list. No model call (rocket-2.2.0
    Phase 7) — the narrative/diagnosis moved to the assess pass, which reads the
    raw corpus."""
    seg_dists, pop_dist = _compute_behavioral_distributions(l2_summaries)
    return L3Summary(
        robust_themes=[],
        fragile_themes=[],
        within_target_findings=[],
        outside_target_findings=[],
        context_fit={},
        representative_quotes=_pool_quotes_from_l2(l2_summaries),
        confidence_signals=_compute_confidence_signals(l2_summaries, target_classification),
        segment_behavioral_distributions=seg_dists,
        population_behavioral_distribution=pop_dist,
    )


# ---- Deterministic internals ----


def _pool_quotes_from_l2(l2_summaries: list[L2Summary]) -> list[Quote]:
    """Gather all quotes from L2 summaries' representative_quotes maps into one
    flat pool. Order: by round, then by disposition. Kept for the artifact; the
    assess pass grounds its own quotes against the raw corpus, not this pool."""
    pool: list[Quote] = []
    for round_num in range(1, 7):
        for summary in sorted(l2_summaries, key=lambda s: s.disposition_label):
            q = summary.representative_quotes.get(round_num)
            if q is not None:
                pool.append(q)
    return pool


def _compute_behavioral_distributions(
    l2_summaries: list[L2Summary],
) -> tuple[dict[str, BehavioralSignalDistribution], BehavioralSignalDistribution]:
    """Deterministic: collect each segment's R7 distribution (keyed by
    segment_label) and sum them into the population distribution."""
    seg_dists: dict[str, BehavioralSignalDistribution] = {}
    pop_counts: dict[str, int] = {}
    pop_next_step: dict[str, int] = {}
    pop_n = 0
    for s in l2_summaries:
        label = s.segment_label or s.disposition_label
        dist = s.behavioral_distribution
        seg_dists[label] = dist
        for action, count in dist.counts.items():
            pop_counts[action] = pop_counts.get(action, 0) + count
        for step, count in dist.next_step_counts.items():
            pop_next_step[step] = pop_next_step.get(step, 0) + count
        pop_n += dist.n
    pop_dist = BehavioralSignalDistribution(
        counts=pop_counts, next_step_counts=pop_next_step, n=pop_n
    )
    return seg_dists, pop_dist


def _compute_confidence_signals(
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
) -> ConfidenceSignals:
    """Deterministic counts. L2 summaries are per-SEGMENT, so multiple summaries
    may share a disposition_label — within_target_disposition_count counts
    DISTINCT within-target dispositions, not segments.

    total_contexts / contexts_in_agreement are no longer computed here (they
    needed the L3 model's context_fit). The assess pass derives the
    single_context_only flag straight from the raw transcripts instead; both
    fields default to 0 on the returned signals for back-compat."""
    within_labels = set(tc.within_target_labels())
    dispositions_present = {s.disposition_label for s in l2_summaries}
    within_count = len(dispositions_present & within_labels)
    homog_count = sum(
        1 for s in l2_summaries if s.within_cell_variance == "tight"
    )
    return ConfidenceSignals(
        within_target_disposition_count=within_count,
        homogenization_flag_count=homog_count,
        total_segments=len(l2_summaries),
    )
