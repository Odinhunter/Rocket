"""L3 v2 — population synthesis (rocket-2.0.0).

Adapted from agent/synthesis_l3.py. The narrative synthesis (robust /
fragile / within- / outside-target themes, per-context fit) is unchanged —
the v1 tool schema and system prompt carry over verbatim. v2 reads
per-SEGMENT L2 summaries (up to ~21 of them) rather than ~7 per-disposition
ones, but the L3 model treats them the same way.

Two additions, both DETERMINISTIC PYTHON (the locked "distributions are
Python, not the model" pattern — extended, never moved to the model):
  - segment_behavioral_distributions: each L2 summary's R7 distribution,
    keyed by segment_label.
  - population_behavioral_distribution: those distributions summed.

These feed L3.5 (agent/projection_l35.py), the funnel projection layer.
"""

from __future__ import annotations

import json
import logging
from collections import Counter

import anthropic

from typing import Any

from agent.config import RunConfig
from agent.schema import BehavioralSignalDistribution, Quote
from agent.synthesis_types import (
    ConfidenceSignals,
    ContextFitFinding,
    L2Summary,
    L3Summary,
    TargetClassification,
    Theme,
)
from agent.telemetry import call_with_telemetry

_log = logging.getLogger(__name__)


# ---- Tool schema ----


_L3_TOOL = {
    "name": "emit_population_synthesis",
    "description": (
        "Emit the narrative synthesis: cross-disposition robust themes, "
        "fragile (single-disposition) flags, within- vs outside-target "
        "findings, and per-context fit. Verdict-level reasoning belongs "
        "to L4, not here — L3 produces the structured evidence base. "
        "Quote pool and confidence signals are NOT emitted by the model; "
        "they are computed deterministically in Python from the L2 inputs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "robust_themes": {
                "type": "array",
                "description": "Findings cited by >=3 dispositions (or by all dispositions when fewer than 3 exist in this run).",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "cited_by": {"type": "array", "items": {"type": "string"}},
                        "rounds": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["statement", "cited_by", "rounds"],
                },
            },
            "fragile_themes": {
                "type": "array",
                "description": "Findings flagged by only one disposition; surfaced for transparency but not load-bearing.",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "cited_by": {"type": "array", "items": {"type": "string"}},
                        "rounds": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["statement", "cited_by", "rounds"],
                },
            },
            "within_target_findings": {
                "type": "array",
                "description": (
                    "Findings drawn ONLY from dispositions classified 'within' "
                    "in the target classification. These are the load-bearing "
                    "verdict drivers for L4."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "cited_by": {"type": "array", "items": {"type": "string"}},
                        "rounds": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["statement", "cited_by", "rounds"],
                },
            },
            "outside_target_findings": {
                "type": "array",
                "description": (
                    "Findings drawn ONLY from dispositions classified 'outside'. "
                    "Informational context, not verdict drivers."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "cited_by": {"type": "array", "items": {"type": "string"}},
                        "rounds": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["statement", "cited_by", "rounds"],
                },
            },
            "context_fit": {
                "type": "object",
                "description": (
                    "One entry per context label that appears in this run's "
                    "L2 summaries. Use the exact context_label string as the key. "
                    "verdict is lowercase: working / mixed / failing."
                ),
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "verdict": {"type": "string", "enum": ["working", "mixed", "failing"]},
                        "friction_summary": {"type": "string"},
                    },
                    "required": ["verdict", "friction_summary"],
                },
            },
        },
        "required": [
            "robust_themes",
            "fragile_themes",
            "within_target_findings",
            "outside_target_findings",
            "context_fit",
        ],
    },
}


_L3_SYSTEM = """\
You are a senior consumer-research analyst doing population synthesis on \
a multi-agent Creative Read. Your job is to compress per-disposition L2 \
summaries into a structured evidence base that a strategist (L4) will turn \
into a verdict memo.

You will receive:
(a) A list of L2 summaries — one per disposition. Each carries a 4-6 \
sentence summary, within-cell variance label, optional outlier note, \
emotional_read, friction_summary, and a representative_quotes map keyed \
by round (R1..R6).
(b) A target classification — per-disposition within/outside/ambiguous \
labels with reasoning.
(c) The list of context labels present in this run.

# What you produce

A structured population synthesis via the emit_population_synthesis tool. \
Specifically:

- **robust_themes**: findings supported by >= 3 dispositions (or all \
dispositions when there are fewer than 3 in the run). One sentence per \
theme, exact disposition labels in cited_by. Rounds is the set of rounds \
where the theme surfaced (de-duplicated).

- **fragile_themes**: findings supported by exactly one disposition. \
Surfaced for transparency — L4 will deprioritize them.

- **within_target_findings**: themes drawn ONLY from dispositions \
classified "within" in the target classification. These are the verdict-\
load-bearing findings. If only one disposition is within-target, the \
findings come from just that one — that's still useful, but note it \
implicitly through cited_by length.

- **outside_target_findings**: themes drawn ONLY from outside-target \
dispositions. These are informational about how the ad reads cross-\
segment — not verdict drivers.

- **context_fit**: one entry per context label that appears in the L2 \
summaries. verdict is "working" / "mixed" / "failing" — lowercase — \
based on whether the ad's within-target story holds, breaks, or wobbles \
in that attention state. friction_summary is one sentence describing \
the dominant friction in that context.

You do NOT emit a quote pool or confidence signals — those are computed \
in Python from the L2 inputs. Your job is the *narrative* synthesis: \
themes, findings, context fit. The quantitative scaffolding is handled \
elsewhere.

# Discipline

- Use the exact disposition_label strings from the input. Don't shorten, \
don't rephrase.
- Use the exact context labels from the input. Don't add or rename them.
- Theme statements are ONE sentence each, specific to this ad, traceable \
to L2 evidence.
- Do not invent quotes. representative_quotes are pulled from the L2 \
inputs verbatim.
- Do not commit a verdict here — that's L4's job. Your output is the \
evidence base, not the conclusion."""


def _extract_tool_use(response: Any, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(
        f"Expected tool_use block named {tool_name!r}, got blocks: "
        f"{[getattr(b, 'type', None) for b in response.content]}"
    )


def _pool_quotes_from_l2(l2_summaries: list[L2Summary]) -> list[Quote]:
    """Gather all quotes from L2 summaries' representative_quotes maps into one
    flat pool that L4 can draw evidence from. Order: by round, then by
    disposition."""
    pool: list[Quote] = []
    for round_num in range(1, 7):
        for summary in sorted(l2_summaries, key=lambda s: s.disposition_label):
            q = summary.representative_quotes.get(round_num)
            if q is not None:
                pool.append(q)
    return pool


# ---- Public entry point ----


def synthesize_population_v2(
    l2_summaries: list[L2Summary],
    target_classification: TargetClassification,
    config: RunConfig,
) -> L3Summary:
    """L3 v2 synthesis. One Sonnet call for the narrative; the quote pool,
    confidence signals, and behavioral-signal distributions are computed in
    Python."""
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["l3"]
    user_payload = _build_user_payload(l2_summaries, target_classification, config)

    response = call_with_telemetry(
        client,
        layer="l3",
        model=model,
        max_tokens=4000,
        temperature=config.temperatures["l3"],
        system=_L3_SYSTEM,
        messages=[{"role": "user", "content": user_payload}],
        tools=[_L3_TOOL],
        tool_choice={"type": "tool", "name": "emit_population_synthesis"},
    )

    tool_use = _extract_tool_use(response, "emit_population_synthesis")
    return _build_l3_summary(tool_use, l2_summaries, target_classification)


# ---- Internals ----


def _build_l3_summary(
    tool_input: dict,
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
) -> L3Summary:
    context_fit = {
        k: ContextFitFinding(verdict=v["verdict"], friction_summary=v["friction_summary"])
        for k, v in tool_input.get("context_fit", {}).items()
    }
    seg_dists, pop_dist = _compute_behavioral_distributions(l2_summaries)
    return L3Summary(
        robust_themes=[Theme(**t) for t in tool_input.get("robust_themes", [])],
        fragile_themes=[Theme(**t) for t in tool_input.get("fragile_themes", [])],
        within_target_findings=[
            Theme(**t) for t in tool_input.get("within_target_findings", [])
        ],
        outside_target_findings=[
            Theme(**t) for t in tool_input.get("outside_target_findings", [])
        ],
        context_fit=context_fit,
        representative_quotes=_pool_quotes_from_l2(l2_summaries),
        confidence_signals=_compute_confidence_signals_v2(
            l2_summaries, tc, context_fit
        ),
        segment_behavioral_distributions=seg_dists,
        population_behavioral_distribution=pop_dist,
    )


def _compute_behavioral_distributions(
    l2_summaries: list[L2Summary],
) -> tuple[dict[str, BehavioralSignalDistribution], BehavioralSignalDistribution]:
    """Deterministic: collect each segment's R7 distribution (keyed by
    segment_label) and sum them into the population distribution."""
    seg_dists: dict[str, BehavioralSignalDistribution] = {}
    pop_counts: dict[str, int] = {}
    pop_would_act = 0
    pop_n = 0
    for s in l2_summaries:
        label = s.segment_label or s.disposition_label
        dist = s.behavioral_distribution
        seg_dists[label] = dist
        for action, count in dist.counts.items():
            pop_counts[action] = pop_counts.get(action, 0) + count
        pop_would_act += dist.would_act_within_week_count
        pop_n += dist.n
    pop_dist = BehavioralSignalDistribution(
        counts=pop_counts, would_act_within_week_count=pop_would_act, n=pop_n
    )
    return seg_dists, pop_dist


def _compute_confidence_signals_v2(
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
    context_fit: dict[str, ContextFitFinding],
) -> ConfidenceSignals:
    """Deterministic counts. v2 difference: L2 summaries are per-SEGMENT, so
    multiple summaries share a disposition_label — within_target_count must
    count DISTINCT within-target dispositions, not segments."""
    within_labels = set(tc.within_target_labels())
    dispositions_present = {s.disposition_label for s in l2_summaries}
    within_count = len(dispositions_present & within_labels)
    homog_count = sum(
        1 for s in l2_summaries if s.within_cell_variance == "tight"
    )
    total_contexts = len(context_fit)
    verdicts = [cf.verdict for cf in context_fit.values()]
    contexts_in_agreement = (
        Counter(verdicts).most_common(1)[0][1] if verdicts else 0
    )
    return ConfidenceSignals(
        within_target_disposition_count=within_count,
        contexts_in_agreement=contexts_in_agreement,
        total_contexts=total_contexts,
        homogenization_flag_count=homog_count,
        total_segments=len(l2_summaries),
    )


def _build_user_payload(
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
    config: RunConfig,
) -> str:
    payload = {
        "asset_label": config.asset.label,
        "category": config.category,
        "target_classification": tc.to_dict(),
        "l2_summaries": [s.to_dict() for s in l2_summaries],
    }
    return (
        "INPUTS FOR POPULATION SYNTHESIS\n"
        "================================\n\n"
        "Note: l2_summaries are per-SEGMENT (disposition x chaos-band). "
        "Multiple segments may share a disposition_label. Treat each as a "
        "distinct evidence cell; use disposition_label for the "
        "within/outside-target split.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\n\nCall emit_population_synthesis with your structured output."
    )
