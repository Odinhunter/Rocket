"""L2 — per-SEGMENT aggregation.

Fans out per SEGMENT, where a segment is a disposition
(segment_granularity == "disposition") or a disposition × chaos-band (the
default, "disposition_chaos_band"). The caller (run_service) groups by
PanelAgent.segment_key and hands each group here.

The Sonnet call does the *narrative* aggregation (summary, variance,
R1-R6 representative quotes). L2Summary also carries `segment_label` and
`behavioral_distribution`. The behavioral_distribution is the R7 signal
aggregate, computed DETERMINISTICALLY IN PYTHON from the transcripts —
never emitted by the model ("distributions are Python, not the model",
same as L3's quote pool and confidence signals).
"""

from __future__ import annotations

import asyncio
import json
import logging

import anthropic

from typing import Any

from agent.config import RunConfig
from agent.schema import AgentTranscript, BehavioralSignalDistribution, Quote
from agent.synthesis_types import L2Summary
from agent.telemetry import call_with_telemetry

_log = logging.getLogger(__name__)


_L2_TOOL = {
    "name": "emit_disposition_summary",
    "description": (
        "Emit the per-disposition summary: a 4-6 sentence read of what "
        "this disposition thinks of the ad, within-cell variance flag, "
        "optional outlier note, representative quotes per round (R1-R6), "
        "emotional read, friction summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary_paragraph": {
                "type": "string",
                "description": (
                    "4-6 sentences in third-person, summarizing what this "
                    "disposition's read of the ad is across the contexts "
                    "and seeds in this cell. Specific to the ad, traceable "
                    "to evidence in the transcripts. No generic strategy "
                    "language."
                ),
            },
            "within_cell_variance": {
                "type": "string",
                "enum": ["tight", "spread", "outlier_present"],
                "description": (
                    "'tight': agents in this cell said roughly the same thing "
                    "(homogenization flag — may indicate model echo rather "
                    "than disposition signal). 'spread': healthy variance "
                    "across contexts/seeds within the disposition. "
                    "'outlier_present': one agent diverged sharply — set "
                    "outlier_note in that case."
                ),
            },
            "outlier_note": {
                "type": ["string", "null"],
                "description": (
                    "If within_cell_variance == 'outlier_present', describe "
                    "the outlier in one sentence. Otherwise null."
                ),
            },
            "representative_quotes": {
                "type": "object",
                "description": (
                    "Map keyed by round number as STRING ('1', '2', '3', '4', "
                    "'5', '6'). Each value is one Quote — the most specific, "
                    "quotable verbatim from that round across this "
                    "disposition's transcripts. Include all six rounds when "
                    "the transcripts cover them. Quotes are verbatim — copy "
                    "exact phrasing, do not paraphrase."
                ),
                "properties": {
                    "1": {"$ref": "#/$defs/Quote"},
                    "2": {"$ref": "#/$defs/Quote"},
                    "3": {"$ref": "#/$defs/Quote"},
                    "4": {"$ref": "#/$defs/Quote"},
                    "5": {"$ref": "#/$defs/Quote"},
                    "6": {"$ref": "#/$defs/Quote"},
                },
                "additionalProperties": False,
            },
            "emotional_read": {
                "type": "string",
                "description": (
                    "1-2 sentences synthesizing the R3 EMOTION sections across "
                    "the transcripts. What did the ad make this disposition "
                    "feel, in their own register?"
                ),
            },
            "friction_summary": {
                "type": "string",
                "description": (
                    "1-2 sentences synthesizing R6 FRICTION across the "
                    "transcripts. What single biggest friction did this "
                    "disposition surface? Use their language."
                ),
            },
        },
        "required": [
            "summary_paragraph",
            "within_cell_variance",
            "outlier_note",
            "representative_quotes",
            "emotional_read",
            "friction_summary",
        ],
        "$defs": {
            "Quote": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "disposition": {"type": "string"},
                    "round": {"type": "integer", "minimum": 1, "maximum": 6},
                    "context": {"type": "string"},
                },
                "required": ["quote", "disposition", "round", "context"],
            },
        },
    },
}


def _extract_tool_use(response: Any, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(
        f"Expected tool_use block named {tool_name!r}, got blocks: "
        f"{[getattr(b, 'type', None) for b in response.content]}"
    )


_L2_SYSTEM = """\
You are a senior consumer-research analyst doing per-SEGMENT aggregation \
on a multi-agent Creative Read. You will be given all the transcripts \
produced by ONE segment — a single consumer disposition at a single \
decision-making style (chaos band) — across multiple attention contexts. \
Your job is to compress those raw transcripts into one structured summary \
that a population-level synthesizer (L3) will fan into cross-segment \
findings.

# How to read the transcripts

Each transcript comes from ONE agent and contains two text blocks:

- **encoding_text** has three labelled sections:
  - `R1 GUT:` 1-2 sentences, the agent's first-glance reaction
  - `R2 COMPREHENSION:` 3 sentences on what message landed
  - `R3 EMOTION:` 4-5 sentences on emotional texture
- **reflection_text** has four labelled sections:
  - `R4 STICKINESS:` what stuck 48 hours later
  - `R5 SOCIAL:` would they share / mention / post
  - `R6 FRICTION:` the single biggest friction on purchase
  - `R7 ACTION:` a one-line JSON behavioral signal (an action + reasoning)

All agents in this batch are the SAME segment. Variance across them comes \
from the attention context. Your aggregation answers: what is this \
segment's consistent read of the ad, where does the read vary, and what's \
the representative voice across rounds R1-R6.

# What you produce — and what you do NOT

Use the emit_disposition_summary tool with summary_paragraph, \
within_cell_variance, outlier_note, representative_quotes (one per round \
R1-R6), emotional_read, friction_summary — exactly as the tool schema \
describes.

You do NOT summarize or count R7. The R7 behavioral-signal distribution is \
computed deterministically in Python from the transcripts — it is not \
your job and you must not emit it. Read R7 only as context for your \
narrative (it tells you what the agent would actually DO), but the counts \
are handled elsewhere.

# Discipline

- Use the exact disposition_label and context_label strings from the \
input. Don't shorten or rephrase.
- Quotes are verbatim. Do not edit, even for grammar. R1-R6 only.
- Do not invent rounds that aren't in the transcripts.
- Do not commit a verdict. That's L4's job. L2 produces the segment-level \
evidence base."""


# ---- Deterministic Python: the R7 behavioral-signal distribution ----


def compute_behavioral_distribution(
    transcripts: list[AgentTranscript],
) -> BehavioralSignalDistribution:
    """Aggregate the R7 behavioral signals of a segment's transcripts into a
    BehavioralSignalDistribution. Counts only — never emitted by the model.
    Transcripts whose R7 failed to parse (behavioral_signal is None) are
    counted in `n` is NOT — n is the count of agents with a usable signal,
    so the proportions L3.5 derives are over real signals, not gaps."""
    counts: dict[str, int] = {}
    would_act = 0
    n = 0
    for t in transcripts:
        sig = t.behavioral_signal
        if sig is None:
            continue
        counts[sig.action] = counts.get(sig.action, 0) + 1
        if sig.would_act_within_week:
            would_act += 1
        n += 1
    return BehavioralSignalDistribution(
        counts=counts, would_act_within_week_count=would_act, n=n
    )


# ---- Public entry point ----


async def synthesize_segment_async(
    segment_label: str,
    transcripts: list[AgentTranscript],
    config: RunConfig,
) -> L2Summary:
    """Async wrapper for parallel L2 fan-out."""
    return await asyncio.to_thread(
        synthesize_segment, segment_label, transcripts, config
    )


def synthesize_segment(
    segment_label: str,
    transcripts: list[AgentTranscript],
    config: RunConfig,
) -> L2Summary:
    """One Sonnet call per segment. transcripts must all belong to the same
    segment (the caller groups by PanelAgent.segment_key); they are asserted
    to share a disposition_label as a sanity check."""
    if not transcripts:
        raise ValueError(f"L2 needs at least one transcript for segment {segment_label!r}")
    disposition_label = transcripts[0].disposition_label
    for t in transcripts:
        if t.disposition_label != disposition_label:
            raise ValueError(
                f"segment {segment_label!r} mixes disposition_labels: "
                f"{t.disposition_label!r} != {disposition_label!r}"
            )

    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["l2"]
    user_payload = _build_user_payload(segment_label, transcripts, config)

    response = call_with_telemetry(
        client,
        layer="l2",
        model=model,
        max_tokens=2000,
        temperature=config.temperatures["l2"],
        system=_L2_SYSTEM,
        messages=[{"role": "user", "content": user_payload}],
        tools=[_L2_TOOL],
        tool_choice={"type": "tool", "name": "emit_disposition_summary"},
    )

    tool_input = _extract_tool_use(response, "emit_disposition_summary")
    summary = _build_l2_summary(disposition_label, segment_label, tool_input)
    # The R7 distribution is computed in Python — never from the model.
    summary.behavioral_distribution = compute_behavioral_distribution(transcripts)
    return summary


# ---- Internals ----


def _build_l2_summary(
    disposition_label: str, segment_label: str, tool_input: dict
) -> L2Summary:
    rep = tool_input.get("representative_quotes", {}) or {}
    quotes: dict[int, Quote] = {}
    for k, v in rep.items():
        try:
            round_num = int(k)
        except (TypeError, ValueError):
            continue
        if not isinstance(v, dict):
            continue
        quotes[round_num] = Quote(
            quote=str(v.get("quote", "")),
            disposition=str(v.get("disposition", disposition_label)),
            round=int(v.get("round", round_num)),
            context=str(v.get("context", "")),
        )
    return L2Summary(
        disposition_label=disposition_label,
        summary_paragraph=tool_input["summary_paragraph"],
        within_cell_variance=tool_input.get("within_cell_variance", "spread"),
        outlier_note=tool_input.get("outlier_note"),
        representative_quotes=quotes,
        emotional_read=tool_input.get("emotional_read", ""),
        friction_summary=tool_input.get("friction_summary", ""),
        segment_label=segment_label,
        # behavioral_distribution is set by the caller (synthesize_segment)
        # from compute_behavioral_distribution — Python, not the model.
    )


def _build_user_payload(
    segment_label: str,
    transcripts: list[AgentTranscript],
    config: RunConfig,
) -> str:
    payload = {
        "segment_label": segment_label,
        "disposition_label": transcripts[0].disposition_label,
        "asset_label": config.asset.label,
        "transcripts": [
            {
                "agent_id": t.agent_id,
                "context": t.context_label,
                "encoding_text": t.encoding_text,
                "reflection_text": t.reflection_text,
            }
            for t in transcripts
        ],
    }
    return (
        f"SEGMENT: {segment_label}\n"
        f"DISPOSITION: {transcripts[0].disposition_label}\n"
        f"COUNT: {len(transcripts)} transcript(s) across "
        f"contexts {sorted({t.context_label for t in transcripts})}\n\n"
        "INPUTS\n======\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\n\nCall emit_disposition_summary with your structured output. "
        "Do NOT summarize or count R7 — that is handled in Python."
    )
