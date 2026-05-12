"""L2 — Per-disposition aggregation.

One Sonnet call per disposition. Reads all AgentTranscripts belonging to
one disposition (across contexts and seeds within that disposition) and
emits an L2Summary that L3 will fan into population-level findings.

Tool-use mode (same rationale as L3 — Sonnet, flatter schema, not Opus,
no truncation risk).

L2 input: list[AgentTranscript] for ONE disposition (all contexts & seeds
in that disposition cell). The encoding_text / reflection_text contain
labelled sections (R1 GUT: ..., R2 COMPREHENSION: ..., etc.). L2 reads
the raw text — section splitting is the model's job in the prompt.

L2 output: L2Summary with summary_paragraph, within_cell_variance,
optional outlier_note, representative_quotes (one per round R1-R6),
emotional_read, friction_summary.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.schema import AgentTranscript, Quote
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


_L2_SYSTEM = """\
You are a senior consumer-research analyst doing per-disposition \
aggregation on a multi-agent Creative Read. You will be given all the \
transcripts produced by ONE disposition (one consumer-type voice), \
across multiple attention contexts and seeds. Your job is to compress \
those raw transcripts into one structured summary that a population-\
level synthesizer (L3) will fan into cross-disposition findings.

# How to read the transcripts

Each transcript comes from ONE agent — one (disposition, context, seed) \
cell — and contains two text blocks:

- **encoding_text** has three labelled sections:
  - `R1 GUT:` 1-2 sentences, the agent's first-glance reaction
  - `R2 COMPREHENSION:` 3 sentences on what message landed
  - `R3 EMOTION:` 4-5 sentences on emotional texture
- **reflection_text** has three labelled sections:
  - `R4 STICKINESS:` what stuck 48 hours later
  - `R5 SOCIAL:` would they share / mention / post
  - `R6 FRICTION:` the single biggest friction on purchase

All agents in this batch are the SAME disposition. Variance across them \
comes from context (which attention state they were in) and seed (within-\
cell stochasticity). Your aggregation answers: what is this disposition's \
consistent read of the ad, where does the read vary, and what's the \
representative voice across rounds?

# What you produce

Use the emit_disposition_summary tool with:

- **summary_paragraph**: 4-6 sentences in third-person describing what \
this disposition thinks of the ad. Span the cognitive arc (gut → \
comprehension → emotion → recall → social → friction). Specific to the \
ad. Traceable to evidence in the transcripts. No generic strategy \
language ("the brand should sharpen", "needs better messaging").

- **within_cell_variance**: 'tight' if agents said roughly the same thing \
across contexts (homogenization flag — the disposition may be performing \
sameness rather than signaling real variance). 'spread' for healthy \
contextual variance. 'outlier_present' if one agent diverged sharply on a \
load-bearing dimension.

- **outlier_note**: one sentence describing the outlier if present, else \
null.

- **representative_quotes**: one quote per round (R1-R6) — six entries \
total if the transcripts cover all six rounds. Pick the MOST quotable, \
most specific verbatim from that round across this disposition's \
transcripts. The quote MUST be a verbatim extract — copy the exact \
phrasing, do not paraphrase. Use the exact disposition_label (provided \
in the input), the round number, and the exact context_label of the \
transcript the quote came from.

- **emotional_read**: 1-2 sentences synthesizing R3 EMOTION across the \
transcripts. What did the ad make this disposition FEEL?

- **friction_summary**: 1-2 sentences synthesizing R6 FRICTION across the \
transcripts. What's the single biggest friction this disposition surfaces \
on purchase?

# Discipline

- Use the exact disposition_label and context_label strings from the \
input. Don't shorten or rephrase.
- Quotes are verbatim. Do not edit, even for grammar.
- Do not invent rounds that aren't in the transcripts. If R3 EMOTION is \
empty in one transcript, draw from another transcript in the same cell.
- Do not commit a verdict. That's L4's job. L2 produces the disposition-\
level evidence base."""


# ---- Public entry point ----


async def synthesize_disposition_async(
    disposition_label: str,
    transcripts: list[AgentTranscript],
    config: RunConfig,
) -> L2Summary:
    """Async wrapper for parallel L2 fan-out. Spawns a thread for the
    blocking Anthropic call."""
    return await asyncio.to_thread(
        synthesize_disposition, disposition_label, transcripts, config
    )


def synthesize_disposition(
    disposition_label: str,
    transcripts: list[AgentTranscript],
    config: RunConfig,
) -> L2Summary:
    """One Sonnet call per disposition. transcripts must all share
    `disposition_label`; this is asserted, not silently filtered."""
    if not transcripts:
        raise ValueError(f"L2 needs at least one transcript for {disposition_label!r}")
    for t in transcripts:
        if t.disposition_label != disposition_label:
            raise ValueError(
                f"transcript disposition_label {t.disposition_label!r} "
                f"doesn't match expected {disposition_label!r}"
            )

    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["l2"]
    user_payload = _build_user_payload(disposition_label, transcripts, config)

    response = call_with_telemetry(
        client,
        layer="l2",
        model=model,
        max_tokens=2000,
        system=_L2_SYSTEM,
        messages=[{"role": "user", "content": user_payload}],
        tools=[_L2_TOOL],
        tool_choice={"type": "tool", "name": "emit_disposition_summary"},
    )

    tool_input = _extract_tool_use(response, "emit_disposition_summary")
    return _build_l2_summary(disposition_label, tool_input)


# ---- Internals ----


def _extract_tool_use(response: Any, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(
        f"Expected tool_use block named {tool_name!r}, got blocks: "
        f"{[getattr(b, 'type', None) for b in response.content]}"
    )


def _build_l2_summary(disposition_label: str, tool_input: dict) -> L2Summary:
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
    )


def _build_user_payload(
    disposition_label: str,
    transcripts: list[AgentTranscript],
    config: RunConfig,
) -> str:
    """Compose the user-side payload. Transcripts are passed as compact JSON
    so the model can see the full text and the metadata together."""
    payload = {
        "disposition_label": disposition_label,
        "asset_label": config.asset.label,
        "transcripts": [
            {
                "agent_id": t.agent_id,
                "context": t.context_label,
                "seed_idx": t.seed_idx,
                "encoding_text": t.encoding_text,
                "reflection_text": t.reflection_text,
            }
            for t in transcripts
        ],
    }
    return (
        f"DISPOSITION: {disposition_label}\n"
        f"COUNT: {len(transcripts)} transcript(s) across "
        f"contexts {sorted({t.context_label for t in transcripts})}\n\n"
        "INPUTS\n======\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\n\nCall emit_disposition_summary with your structured output."
    )
