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
    within_dist, outside_dist = _split_by_target(l2_summaries, target_classification)
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
        within_target_behavioral_distribution=within_dist,
        outside_target_behavioral_distribution=outside_dist,
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
    for s in l2_summaries:
        label = s.segment_label or s.disposition_label
        seg_dists[label] = s.behavioral_distribution
    pop_dist = _sum_distributions(
        [s.behavioral_distribution for s in l2_summaries]
    )
    return seg_dists, pop_dist


def _sum_distributions(
    dists: list[BehavioralSignalDistribution],
) -> BehavioralSignalDistribution:
    """Integer sum of a list of distributions. One place, so the population
    pool and the target split can never drift apart in how they add up."""
    counts: dict[str, int] = {}
    next_step: dict[str, int] = {}
    n = 0
    for dist in dists:
        for action, count in dist.counts.items():
            counts[action] = counts.get(action, 0) + count
        for step, count in dist.next_step_counts.items():
            next_step[step] = next_step.get(step, 0) + count
        n += dist.n
    return BehavioralSignalDistribution(
        counts=counts, next_step_counts=next_step, n=n
    )


def _split_by_target(
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
) -> tuple[BehavioralSignalDistribution, BehavioralSignalDistribution]:
    """Pool the R7 distributions TWICE: once over within-target segments, once
    over everything else. L3.5 projects each separately.

    ⚠ Why this exists at all: a panel-wide aggregate that pools in- and
    out-of-target is the mistake that has cost this project a rebuild twice
    (docs/v3_out_of_target_response.md; the same warning is written into
    read_model.next_steps_in_target). On a narrow ad the out-of-target majority
    swamps the signal — 19 in target converting at 30% against 81 outside at 0%
    pools to 5.7%, and the customer is told an ad that worked has DROPPED their
    conversion. The projection is the last unsplit aggregate in the stack.

    `within` is membership of tc.within_target_labels() — BYTE-FOR-BYTE the same
    rule as decision.within_target_action_rate, so the funnel and the headline
    metric can never disagree about who the target is. AMBIGUOUS FALLS OUTSIDE,
    exactly as it does in that headline's denominator. Do not "fix" this into a
    three-way split on one side only.

    The two returned distributions sum to population_behavioral_distribution by
    construction — an integer identity, pinned by test.
    """
    within_labels = set(tc.within_target_labels())
    within = [s.behavioral_distribution for s in l2_summaries
              if s.disposition_label in within_labels]
    outside = [s.behavioral_distribution for s in l2_summaries
               if s.disposition_label not in within_labels]
    return _sum_distributions(within), _sum_distributions(outside)


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
