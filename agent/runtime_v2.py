"""L1 — v2 bundled agent runtime (rocket-2.0.0).

Adapted from agent/runtime.py. Same bundled-call + prompt-caching +
idempotent-artifact structure, three changes:

  1. The agent is a PanelAgent (a point across the four population axes),
     not a v1 AgentSpec.
  2. The system prompt is the RENDERED persona core (from agent/render.py),
     not the v1 build_agent_prompt concatenation. The context is rendered
     separately and goes in the USER message, AFTER the cached image block —
     so agents that share a persona core share the cached system+image
     prefix even when their contexts differ.
  3. Call B (Reflection) gains R7 — a terminal in-character behavioral
     signal emitted as one JSON line, parsed into AgentTranscript.
     behavioral_signal. The agent emits an action, never a funnel rate.

Caching layout (unchanged in shape from v1): one cache_control marker on
the system text block, one on the image block. The cached prefix is
persona-core + image. Context prose and the round prompts come after, in
the user message, uncached.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from agent.artifact_pack import CategoryArtifactPack
from agent.config import RunConfig
from agent.panel import PanelAgent
from agent.render import render_context, render_persona_core
from agent.runtime import (
    _extract_text,
    _image_block,
    _redact_image_b64,
    _usage_dict,
)
from agent.schema import AgentTranscript, BehavioralSignal, _VALID_BEHAVIORAL_ACTIONS
from agent.telemetry import call_with_telemetry, run_dir

_log = logging.getLogger(__name__)

# 1100 in v1; bumped to fit the R7 JSON line on Call B without crowding R4-R6.
_MAX_TOKENS = 1250

_ENCODING_USER = (
    "ENCODING PHASE — emit three sections, each labelled.\n\n"
    "R1 GUT: exactly 1-2 sentences. Your first-glance reaction "
    "before parsing the ad. Pre-thought, visceral. Stop after the "
    "second period.\n\n"
    "R2 COMPREHENSION: exactly 3 sentences. What message did the "
    "ad land for you? What did you actually take from it? Stop "
    "after the third period.\n\n"
    "R3 EMOTION: free-form prose, 4-5 sentences max. The "
    "emotional texture the ad left on you — what did it stir, "
    "what did it leave flat? Be honest about the feeling."
)

# R4-R6 carry over from v1; R7 is new. R7 is a single JSON line so it parses
# deterministically out of otherwise free-form reflection prose.
_REFLECTION_USER = (
    "REFLECTION PHASE — 48 hours later. Emit four sections, each "
    "labelled.\n\n"
    "R4 STICKINESS: 3-4 sentences. What stuck from that ad, and what "
    "didn't? Be specific. Stop after the fourth period at most.\n\n"
    "R5 SOCIAL: 3-4 sentences. Would you share/screenshot/mention this "
    "ad to anyone? Why or why not? What social cost or upside?\n\n"
    "R6 FRICTION: 4-5 sentences. If you were considering buying, what's "
    "the single biggest friction the ad introduced — and would you act "
    "on it?\n\n"
    "R7 ACTION: after R6, emit exactly ONE line of JSON and nothing else "
    "after it:\n"
    '{"action": "<scroll_past|linger|tap_cta|save|share|seek_info>", '
    '"reasoning": "<one in-character sentence, anchored to something '
    'specific in the creative>", "would_act_within_week": <true|false>}\n'
    "Emit an in-character behavioral signal — what you would actually DO. "
    "Never a funnel rate, a percentage, or a probability."
)


# ---- R7 parsing (pure function — offline-testable) ----

# Find the last {...} JSON object in the text. Tolerant of R6 prose bleed.
_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}")


def parse_r7_signal(reflection_text: str) -> BehavioralSignal | None:
    """Extract the R7 behavioral signal from a reflection transcript.

    Returns None — never raises — if R7 is missing or malformed. L2 handles
    the gap. We scan for the LAST balanced {...} block so stray braces in R6
    prose don't capture; the action must be in the valid enum."""
    candidates = _JSON_OBJ_RE.findall(reflection_text)
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        action = obj.get("action")
        if action not in _VALID_BEHAVIORAL_ACTIONS:
            continue
        reasoning = obj.get("reasoning", "")
        would_act = obj.get("would_act_within_week")
        if not isinstance(would_act, bool):
            # Tolerate "true"/"false"/1/0; reject anything genuinely unparseable.
            if isinstance(would_act, str) and would_act.lower() in ("true", "false"):
                would_act = would_act.lower() == "true"
            elif would_act in (0, 1):
                would_act = bool(would_act)
            else:
                continue
        return BehavioralSignal(
            action=action,
            reasoning=str(reasoning),
            would_act_within_week=would_act,
        )
    _log.warning("parse_r7_signal: no valid R7 JSON line found in reflection text")
    return None


# ---- Public API ----


async def run_agent_v2_async(
    agent: PanelAgent,
    config: RunConfig,
    pack: CategoryArtifactPack,
    *,
    run_id: str,
    render_cache_dir: Path | None = None,
) -> AgentTranscript:
    """Async wrapper — run Encoding then Reflection for one PanelAgent."""
    return await asyncio.to_thread(
        run_agent_v2, agent, config, pack, run_id=run_id,
        render_cache_dir=render_cache_dir,
    )


def run_agent_v2(
    agent: PanelAgent,
    config: RunConfig,
    pack: CategoryArtifactPack,
    *,
    run_id: str,
    render_cache_dir: Path | None = None,
) -> AgentTranscript:
    """Sync entry point. Renders (or cache-loads) the persona core + context,
    fires Encoding then Reflection with idempotent per-call persistence,
    parses R7, returns an AgentTranscript with behavioral_signal populated.
    """
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["agent"]

    # Persona core (cached prefix) and context (uncached, in the user msg).
    core_prose = render_persona_core(
        agent.demographic, agent.disposition.vector, agent.chaos.vector, pack,
        anchor=agent.disposition.anchor, cache_dir=render_cache_dir,
    )
    context_prose = render_context(
        agent.context.vector, pack, cache_dir=render_cache_dir,
    )

    # System = persona core ONLY, cache-marked. Context is NOT here — it goes
    # in the user message so agents sharing a core share the cached prefix.
    system = [
        {"type": "text", "text": core_prose, "cache_control": {"type": "ephemeral"}},
    ]
    context_block = (
        "THE EXACT MOMENT THIS AD APPEARS IN THEIR FEED\n\n"
        f"{context_prose.strip()}\n\n"
        "Attention gates everything that follows. If this context implies "
        "low attention, the ad probably gets a sub-second thumb-flick "
        "regardless of whether the persona would be interested in a more "
        "alert moment.\n\n"
    )
    encoding_user_content = [
        _image_block(config.asset.image_path, cache=True),
        {"type": "text", "text": context_block + _ENCODING_USER},
    ]

    # Call A — Encoding (R1-R3). Idempotent: skip if artifact exists.
    enc_artifact = _load_artifact(run_id, config, agent.agent_id, "encoding")
    if enc_artifact is None:
        response_a = call_with_telemetry(
            client, layer="agent", model=model,
            agent_id=agent.agent_id, round_num=1,
            max_tokens=_MAX_TOKENS, temperature=config.temperatures["agent"],
            system=system,
            messages=[{"role": "user", "content": encoding_user_content}],
        )
        encoding_text = _extract_text(response_a)
        _persist_artifact(
            run_id, config, agent, "encoding",
            request={
                "system": system,
                "messages": [
                    {"role": "user", "content": _redact_image_b64(encoding_user_content)}
                ],
                "model": model, "max_tokens": _MAX_TOKENS,
            },
            response_text=encoding_text,
            usage=_usage_dict(response_a),
            stop_reason=getattr(response_a, "stop_reason", None),
        )
    else:
        encoding_text = enc_artifact["response_text"]

    # Call B — Reflection (R4-R7). Same system + image -> cached prefix reused.
    ref_artifact = _load_artifact(run_id, config, agent.agent_id, "reflection")
    if ref_artifact is None:
        response_b = call_with_telemetry(
            client, layer="agent", model=model,
            agent_id=agent.agent_id, round_num=4,
            max_tokens=_MAX_TOKENS, temperature=config.temperatures["agent"],
            system=system,
            messages=[
                {"role": "user", "content": encoding_user_content},
                {"role": "assistant", "content": encoding_text},
                {"role": "user", "content": _REFLECTION_USER},
            ],
        )
        reflection_text = _extract_text(response_b)
        _persist_artifact(
            run_id, config, agent, "reflection",
            request={
                "system": "(elided — same as encoding)",
                "messages": [
                    {"role": "user", "content": "(image + context elided)"},
                    {"role": "assistant", "content": encoding_text},
                    {"role": "user", "content": _REFLECTION_USER},
                ],
                "model": model, "max_tokens": _MAX_TOKENS,
            },
            response_text=reflection_text,
            usage=_usage_dict(response_b),
            stop_reason=getattr(response_b, "stop_reason", None),
        )
    else:
        reflection_text = ref_artifact["response_text"]

    return AgentTranscript(
        agent_id=agent.agent_id,
        disposition_label=agent.disposition_label,
        context_label=agent.context_label,
        seed_idx=0,
        encoding_text=encoding_text,
        reflection_text=reflection_text,
        behavioral_signal=parse_r7_signal(reflection_text),
    )


# ---- Idempotent per-call persistence (PanelAgent variant) ----


def _agent_calls_dir(run_id: str, config: RunConfig) -> Path:
    return run_dir(
        run_id,
        account_id=config.account_id,
        brand_profile_id=config.brand_profile_id,
    ) / "agent_calls"


def _artifact_path(run_id: str, config: RunConfig, agent_id: int, phase: str) -> Path:
    if phase not in ("encoding", "reflection"):
        raise ValueError(f"phase must be encoding|reflection, got {phase!r}")
    return _agent_calls_dir(run_id, config) / f"{agent_id:04d}__{phase}.json"


def _load_artifact(
    run_id: str, config: RunConfig, agent_id: int, phase: str
) -> dict | None:
    path = _artifact_path(run_id, config, agent_id, phase)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("Failed to load agent_calls artifact %s: %s", path, exc)
        return None


def _persist_artifact(
    run_id: str,
    config: RunConfig,
    agent: PanelAgent,
    phase: str,
    *,
    request: dict,
    response_text: str,
    usage: dict | None,
    stop_reason: str | None,
) -> None:
    path = _artifact_path(run_id, config, agent.agent_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "agent_id": agent.agent_id,
        "phase": phase,
        "disposition_label": agent.disposition_label,
        "context_label": agent.context_label,
        "chaos_band": agent.chaos_band,
        "segment_key": agent.segment_key,
        "asset_label": config.asset.label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "response_text": response_text,
        "usage": usage,
        "stop_reason": stop_reason,
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)
