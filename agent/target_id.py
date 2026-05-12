"""Target classification — Opus vision call, single-asset variant.

Identifies the ad's apparent target audience from creative cues alone,
then classifies each disposition in the run pool as within / outside /
ambiguous against that target.

Deliberately does NOT see population reactions. Target is a property of
the ad, not of who happened to react; keeping reactions out prevents the
model from rationalizing the target to fit who responded.

Single-asset variant: the anchor image from the pre-refactor focal+anchor
flow is gone. This means we lose the "what does premium look like in this
category" calibration; accept the loss for Week 1. If real customer runs
start drifting on target classification, reopen with a per-category text
exemplar.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.synthesis_types import DispositionTarget, TargetClassification
from agent.telemetry import call_with_telemetry


_log = logging.getLogger(__name__)


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


_TOOL = {
    "name": "classify_ad_target",
    "description": (
        "Identify the ad's target audience from creative cues alone, and "
        "classify each disposition in the population pool as within, "
        "outside, or ambiguous against that target. The classification "
        "must be evidence-anchored to specific creative elements — visual, "
        "copy, occasion, brand positioning, demographic signals — not vibes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "inferred_target_description": {
                "type": "string",
                "description": (
                    "One or two sentences describing who this ad is for. "
                    "Specific: age range, life stage, household role, income "
                    "tier, occasion, regional/cultural context where signaled."
                ),
            },
            "target_reasoning": {
                "type": "string",
                "description": (
                    "Trace the inferred target back to specific creative "
                    "evidence. Visual palette, models / no-models, settings, "
                    "props, language register, copy tone, occasion framing, "
                    "brand positioning cues, demographic signals. Avoid vibes "
                    "('looks Indian, must be mass-market') — name the "
                    "specific cues."
                ),
            },
            "disposition_classifications": {
                "type": "array",
                "description": (
                    "One entry per disposition in the input pool. Use the "
                    "exact disposition_label string from the input."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "disposition_label": {"type": "string"},
                        "classification": {
                            "type": "string",
                            "enum": ["within", "outside", "ambiguous"],
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["disposition_label", "classification", "reasoning"],
                },
            },
            "ambiguity_note": {
                "type": ["string", "null"],
                "description": (
                    "Set if the ad's creative does not clearly signal a "
                    "target audience (generic / category-only / multiple "
                    "competing targets). An ad that does not signal target "
                    "*has* a creative problem; flag it. Otherwise null."
                ),
            },
            "no_match_note": {
                "type": ["string", "null"],
                "description": (
                    "Set if no dispositions in the pool match the inferred "
                    "target. State which archetype or disposition pool would "
                    "be a better fit. Otherwise null."
                ),
            },
        },
        "required": [
            "inferred_target_description",
            "target_reasoning",
            "disposition_classifications",
        ],
    },
}


_SYSTEM = """\
You are a senior consumer-research analyst doing target identification on \
a single ad. You will be shown the ad image and a list of dispositions \
describing distinct consumer types within a single archetype. Your job:

1. Identify the target audience of the ad — who is it for.
2. For each disposition, classify it as within / outside / ambiguous \
against the ad's inferred target.

# How to read the ad

Examine the creative for these specific cues. Every claim about target \
must trace to one or more of these — no vibes, no stereotypes:

- **Visual palette** — colors, lighting, contrast, polish vs grain
- **Models or no models** — if models, their age range, gender, dress, \
demographic and aspirational signals; if none, what that itself says
- **Setting and props** — kitchen vs office vs cafe vs home; festive items, \
furniture tier, location class
- **Copy tone and language register** — English / Hinglish / regional, \
formal / casual / aspirational, claim style (price-led / quality-led / \
emotion-led / occasion-led)
- **Occasion framing** — festive (Diwali, Valentine's, Raksha Bandhan, \
wedding), everyday utility, gifting, indulgence, performance / fitness
- **Brand positioning cues** — mass-market / premium / D2C-disruptor / \
legacy-incumbent. Look at logo prominence, packaging shown, retail \
context, price disclosure
- **Demographic signals** — age, income tier, household role, regional / \
cultural context where signaled

# Within / outside / ambiguous

- **within** — the disposition fits the inferred target on the load-bearing \
dimensions (life stage, household role, income tier, attitudinal stance, \
occasion-relevance). Multiple match-points; few or no contradictions.
- **outside** — the disposition fails the target on a load-bearing \
dimension. The household role is wrong, the income tier mismatches, the \
occasion is irrelevant, the attitudinal stance puts them in a different \
segment entirely.
- **ambiguous** — partial match. Some dimensions fit, others don't. Use \
this when the disposition could plausibly be in target depending on \
unspecified context. Don't use ambiguous as a safe default — pick within \
or outside when the evidence supports a clean call.

# Edge cases

- If the creative does not clearly signal a target — generic mass-market \
ad, category-only, multiple competing targets — set `ambiguity_note` and \
classify dispositions liberally as ambiguous. The unsignaled target is \
itself a finding.
- If no dispositions in the pool match the inferred target, set \
`no_match_note` with the archetype that would fit better. All \
classifications can be "outside" in this case.
- The brand or product positioning may target a wider audience than this \
specific ad does. Classify against THIS ad's target as expressed in the \
creative, not the brand's overall positioning.

# Output

Use the classify_ad_target tool. Be specific. Brand managers read your \
classification reasoning and judge whether you've called the target \
correctly — vague reasoning will be dismissed; specific reasoning ("the \
deal price plus the no-model closed-case framing plus the 'Shop Now' CTA \
signal a quick-decision online purchase pitch for existing Boat-tier \
buyers") holds up."""


def identify_target(
    disposition_pool: list[tuple[str, str]],
    config: RunConfig,
) -> TargetClassification:
    """Run target classification on the asset against the disposition pool.

    disposition_pool: list of (label, description) tuples — the dispositions
    that will participate in this run. The model classifies each against
    the inferred target.
    """
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["target_id"]

    image_block = _image_block(config.asset.image_path)
    disposition_text = "\n\n".join(
        f"**{label}** — {desc}" for label, desc in disposition_pool
    )

    user_content = [
        image_block,
        {
            "type": "text",
            "text": (
                f"AD CONTEXT: {config.asset.label}\n"
                f"Category: {config.category}\n"
                f"Archetype: {config.archetype}\n\n"
                "DISPOSITIONS IN THE RUN POOL:\n\n"
                + disposition_text
                + "\n\nClassify each disposition above against the ad's "
                "inferred target. Use the classify_ad_target tool."
            ),
        },
    ]

    response = call_with_telemetry(
        client,
        layer="target_id",
        model=model,
        max_tokens=4000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "classify_ad_target"},
    )

    tool_input = _extract_tool_use(response, "classify_ad_target")
    return _build_target_classification(tool_input, disposition_pool)


def _build_target_classification(
    tool_input: dict,
    disposition_pool: list[tuple[str, str]],
) -> TargetClassification:
    """Normalize: if the model missed a disposition, add it as ambiguous so
    no entries vanish silently."""
    seen = {d["disposition_label"] for d in tool_input.get("disposition_classifications", [])}
    classifications = [DispositionTarget(**d) for d in tool_input["disposition_classifications"]]
    for label, _ in disposition_pool:
        if label not in seen:
            _log.warning("target_id model dropped disposition %r — coercing to ambiguous", label)
            classifications.append(DispositionTarget(
                disposition_label=label,
                classification="ambiguous",
                reasoning="(target classifier did not classify this disposition; defaulting to ambiguous)",
            ))
    return TargetClassification(
        inferred_target_description=tool_input["inferred_target_description"],
        target_reasoning=tool_input["target_reasoning"],
        disposition_classifications=classifications,
        ambiguity_note=tool_input.get("ambiguity_note"),
        no_match_note=tool_input.get("no_match_note"),
    )


def _extract_tool_use(response: Any, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(
        f"Expected tool_use block named {tool_name!r}, got blocks: "
        f"{[getattr(b, 'type', None) for b in response.content]}"
    )


def _image_block(image_path: str) -> dict:
    path = Path(image_path)
    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise ValueError(
            f"Unsupported image extension {path.suffix!r}. Supported: {sorted(_MEDIA_TYPES)}"
        )
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }
