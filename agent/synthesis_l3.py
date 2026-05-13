"""L3 — Population synthesis.

Single Sonnet call. Reads L2 per-disposition summaries + TargetClassification,
emits an L3Summary that L4 will turn into the consumer-facing memo.

Tool-use mode is used here (safe on Sonnet — the L4 failure mode was Opus
+ long memo + complex nested schema → truncation inside tool input).
L3 outputs a flatter schema; the truncation risk does not apply.

What L3 produces:
- robust_themes: findings supported by >= 3 dispositions (or all of them, if
  there are fewer than 3 in the run)
- fragile_themes: findings flagged by only one disposition
- within_target_findings / outside_target_findings: split using the target
  classification's `classification` field
- context_fit: one entry per context label seen across the L2 summaries
- representative_quotes: a global pool of 10-20 quotes for L4 to draw from
- confidence_signals: quantitative summary (within_target_count,
  contexts_in_agreement, etc.) so L4 can land on the confidence anchors
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.synthesis_types import (
    ConfidenceSignals,
    ContextFitFinding,
    DispositionTarget,
    L2Summary,
    L3Summary,
    TargetClassification,
    Theme,
)
from agent.schema import Quote
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


# ---- Public entry point ----


def synthesize_population(
    l2_summaries: list[L2Summary],
    target_classification: TargetClassification,
    config: RunConfig,
) -> L3Summary:
    """L3 synthesis. One Sonnet call with structured tool-use output."""
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


def _extract_tool_use(response: Any, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(
        f"Expected tool_use block named {tool_name!r}, got blocks: "
        f"{[getattr(b, 'type', None) for b in response.content]}"
    )


def _build_l3_summary(
    tool_input: dict,
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
) -> L3Summary:
    context_fit = {
        k: ContextFitFinding(verdict=v["verdict"], friction_summary=v["friction_summary"])
        for k, v in tool_input.get("context_fit", {}).items()
    }
    return L3Summary(
        robust_themes=[Theme(**t) for t in tool_input.get("robust_themes", [])],
        fragile_themes=[Theme(**t) for t in tool_input.get("fragile_themes", [])],
        within_target_findings=[Theme(**t) for t in tool_input.get("within_target_findings", [])],
        outside_target_findings=[Theme(**t) for t in tool_input.get("outside_target_findings", [])],
        context_fit=context_fit,
        representative_quotes=_pool_quotes_from_l2(l2_summaries),
        confidence_signals=_compute_confidence_signals(l2_summaries, tc, context_fit),
    )


def _pool_quotes_from_l2(l2_summaries: list[L2Summary]) -> list[Quote]:
    """Gather all quotes from L2 summaries' representative_quotes maps into one
    flat pool that L4 can draw evidence from. Order: by round, then by
    disposition, so the pool has predictable round coverage.

    No filtering, no model judgment — just aggregation. L4 picks 5-10 for
    the consumer-facing verbatim_consumer_voice based on its own judgment.
    """
    pool: list[Quote] = []
    # Iterate rounds 1..6 to get balanced coverage, then within each round
    # iterate sorted by disposition.
    for round_num in range(1, 7):
        for summary in sorted(l2_summaries, key=lambda s: s.disposition_label):
            q = summary.representative_quotes.get(round_num)
            if q is not None:
                pool.append(q)
    return pool


def _compute_confidence_signals(
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
    context_fit: dict[str, ContextFitFinding],
) -> ConfidenceSignals:
    """Deterministic counts. Don't ask the model; just count."""
    within_labels = set(tc.within_target_labels())

    within_count = sum(
        1 for s in l2_summaries if s.disposition_label in within_labels
    )
    homog_count = sum(1 for s in l2_summaries if s.within_cell_variance == "tight")
    total_contexts = len(context_fit)

    # contexts_in_agreement: count contexts where the L3 verdict label
    # matches across-context for the within-target-only set of L2 summaries.
    # In the simple case where one context per agent, the L3 emits a verdict
    # per context; agreement here is just "how many contexts share the same
    # verdict label as the majority." If only one context exists, agreement = 1.
    verdicts = [cf.verdict for cf in context_fit.values()]
    if not verdicts:
        contexts_in_agreement = 0
    else:
        # Majority verdict count
        from collections import Counter
        most_common_count = Counter(verdicts).most_common(1)[0][1]
        contexts_in_agreement = most_common_count

    return ConfidenceSignals(
        within_target_disposition_count=within_count,
        contexts_in_agreement=contexts_in_agreement,
        total_contexts=total_contexts,
        homogenization_flag_count=homog_count,
    )


def _build_user_payload(
    l2_summaries: list[L2Summary],
    tc: TargetClassification,
    config: RunConfig,
) -> str:
    payload = {
        "asset_label": config.asset.label,
        "category": config.category,
        "archetype": config.archetype,
        "target_classification": tc.to_dict(),
        "l2_summaries": [s.to_dict() for s in l2_summaries],
    }
    return (
        "INPUTS FOR POPULATION SYNTHESIS\n"
        "================================\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\n\nCall emit_population_synthesis with your structured output."
    )
