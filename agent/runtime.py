"""L1 — bundled agent runtime.

  - The agent is a PanelAgent (a point across the four population axes).
  - The system prompt is the RENDERED persona core (from agent/render.py).
    The context is rendered separately and goes in the USER message,
    AFTER the cached image block — so agents that share a persona core
    share the cached system+image prefix even when their contexts differ.
  - Call B (Reflection) emits R7 — a terminal in-character behavioral
    signal as one JSON line, parsed into AgentTranscript.behavioral_signal.
    The agent emits an action, never a funnel rate.

Caching layout: one cache_control marker on the system text block, one on
the image block. The cached prefix is persona-core + image. Context prose
and the round prompts come after, in the user message, uncached.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from agent.artifact_pack import CategoryArtifactPack
from agent.config import CreativeInputs, RunConfig
from agent.panel import PanelAgent
from agent.purpose import resolve_purpose
from agent.render import render_context, render_persona_core
from agent.schema import (
    AgentTranscript,
    BehavioralSignal,
    ProbeSignal,
    _VALID_BEHAVIORAL_ACTIONS,
)
from agent.telemetry import call_with_telemetry, run_dir


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _image_block(image_path: str, *, cache: bool) -> dict:
    path = Path(image_path)
    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise ValueError(
            f"Unsupported image extension {path.suffix!r}. Supported: {sorted(_MEDIA_TYPES)}"
        )
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    block: dict = {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }
    if cache:
        block["cache_control"] = {"type": "ephemeral"}
    return block


def _extract_text(response: object) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _redact_image_b64(content: list[dict]) -> list[dict]:
    """Drop the base64 image payload from the persisted record; keep media
    type and the path reference. Cuts artifact size by ~300KB without losing
    debuggability."""
    out = []
    for block in content:
        if block.get("type") == "image":
            src = dict(block.get("source", {}))
            if "data" in src:
                src["data"] = f"(base64 elided, {len(src['data'])} chars)"
            out.append({**block, "source": src})
        else:
            out.append(block)
    return out


def _usage_dict(response: object) -> dict | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
    }

_log = logging.getLogger(__name__)

# Sized to fit the R7 JSON line on Call B without crowding R4-R6.
_MAX_TOKENS = 1250

_ENCODING_USER = (
    "ENCODING PHASE — you are a real person glancing at an ad, NOT a "
    "writer. Keep every section to 1-2 plain sentences (a line or two). "
    "Be blunt and conversational; never eloquent, thorough, or clever — "
    "no literary phrasing, no neat metaphors, no tidy summaries. Three "
    "labelled sections.\n\n"
    "R1 GUT: 1-2 sentences. Your instant, pre-thought reaction.\n\n"
    "R2 COMPREHENSION: 1-2 sentences. What's it selling, who's it for, and "
    "is that you? If the creative's signals (the model's "
    "gender/age/life-stage, the benefit, the styling) clearly aren't "
    "aimed at someone like you, say so plainly — don't explain it away or "
    "assume what 'people like you' prefer.\n\n"
    "R3 EMOTION: 1-2 sentences. What it made you feel, or that it left you "
    "cold. Plain words."
)

# R7 is a single terminal JSON line so it parses deterministically out of
# otherwise free-form reflection prose.
#
# v2.4 CONDITIONAL PROBES (see the 2026-07-11 finding, docs/v2_4 §probe-contamination):
# an earlier build asked R8 novelty + R9 brand_recall on EVERY run. A paid anchor
# run proved this CONTAMINATES the blind reaction — asking "did this teach you
# something new?" before "would you buy?" reframes purchase intent around novelty
# and roughly HALVED within-target would_act on a familiar-brand direct-sell ad
# (68% -> 26%, same ad/seed, actions unchanged). So a probe is now asked ONLY on
# the purpose that reads it: novelty on informer, brand_recall on brand-building.
# The three would_act/action jobs (direct-sell, cold-hook, retain) get the
# probe-free reflection prompt that is BYTE-IDENTICAL to the validated v2.3 one
# (guarded by tests/test_reflection_prompt.py). Per-persona blindness holds — an
# extra reflection question never reveals the ad's objective.

# The validated, probe-free base (R4/R5/R6). MUST stay byte-identical to the
# v2.3 reflection prompt for the core three — the identity test asserts it.
_REFLECTION_BASE = (
    "REFLECTION PHASE — a day or two later, still a real person, still "
    "plain and short. Keep every section to 1-2 sentences. If an ad left "
    "almost nothing behind, say so plainly — don't manufacture depth.\n\n"
    "R4 STICKINESS: 1-2 sentences. What, if anything, stuck.\n\n"
    "R5 SOCIAL: 1-2 sentences. Would you share or mention it, and why or "
    "why not?\n\n"
    "R6 FRICTION: 1-2 sentences. If you'd consider buying, the one thing "
    "that stops you. If the ad isn't aimed at someone like you, that's a "
    "fine reason — one factor, not a lecture.\n\n"
)
_NOVELTY_BLOCK = (
    "R8 NEW-TO-YOU: 1-2 sentences. Did the ad tell you something about the "
    "brand you didn't already know — 'huh, I didn't know they made this', a "
    "claim or fact that changed your picture of them? Or was it all stuff "
    "you'd already expect? Be honest — most ads teach you nothing.\n\n"
)
_BRAND_CHECK_BLOCK = (
    "R9 BRAND CHECK: 1-2 sentences. Without scrolling back, which brand was "
    "this ad for, and how sure are you? Totally fine to say you don't "
    "remember or you're guessing.\n\n"
)
_R7_HEAD = "R7 ACTION: emit exactly ONE line of JSON and nothing after it:\n"
_R7_CORE = (
    '{"action": "<scroll_past|linger|tap_cta|save|share|seek_info>", '
    '"reasoning": "<one short in-character sentence, anchored to the '
    'creative>", "would_act_within_week": <true|false>'
)
_R7_ACTION_NOTE = "What you would actually DO. Never a funnel rate or percentage."


def _reflection_user_for(purpose: str) -> str:
    """The reflection prompt for a run's declared purpose. The core three
    (direct-sell / cold-hook / retain) get the probe-free string, byte-identical
    to the validated v2.3 prompt. informer adds R8 novelty; brand-building adds
    R9 brand_recall — each only where its metric reads it, so the would_act/action
    jobs are never contaminated."""
    probes = resolve_purpose(purpose).scored_probes
    prose = ""
    json_extra = ""
    notes: list[str] = []
    if "novelty" in probes:
        prose += _NOVELTY_BLOCK
        json_extra += ', "novelty": <true|false>'
        notes.append("novelty = did R8 genuinely teach you something new about the brand")
    if "brand_attribution" in probes:
        prose += _BRAND_CHECK_BLOCK
        json_extra += ', "brand_recall": "<confident|unsure|none>"'
        notes.append("brand_recall = how sure you are which brand it was "
                     "(confident if you can name it, unsure if hazy, none if you couldn't say)")
    action_note = _R7_ACTION_NOTE
    if notes:
        action_note = "; ".join(notes) + ". The " + _R7_ACTION_NOTE[0].lower() + _R7_ACTION_NOTE[1:]
    return _REFLECTION_BASE + prose + _R7_HEAD + _R7_CORE + json_extra + "}\n" + action_note


def _creative_copy_block(ci: CreativeInputs) -> str:
    """The ad copy + offer accompanying the image, formatted as the agent
    reads it in feed. Empty string when nothing was provided (so image-only
    runs are byte-unchanged). MUST go in the UNCACHED user text — never the
    cached persona-core/image prefix — so it does not perturb caching."""
    lines = []
    if ci.headline.strip():
        lines.append(f"Headline: {ci.headline.strip()}")
    if ci.primary_text.strip():
        lines.append(f"Body: {ci.primary_text.strip()}")
    if ci.offer.strip():
        lines.append(f"Offer / price: {ci.offer.strip()}")
    if not lines:
        return ""
    return (
        "AD COPY & OFFER accompanying this image (read it as you would in "
        "feed, alongside the visual):\n" + "\n".join(lines) + "\n\n"
    )


# ---- R7 parsing (pure function — offline-testable) ----

# Find the last {...} JSON object in the text. Tolerant of R6 prose bleed.
_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}")


def _terminal_signal_obj(reflection_text: str) -> dict | None:
    """The last balanced {...} block carrying a valid R7 action, parsed to a
    dict. Shared by R7 + probe parsing so both read the SAME terminal JSON. We
    scan from the end so stray braces in R6 prose don't capture; the action
    must be in the valid enum. None if no such block exists."""
    for raw in reversed(_JSON_OBJ_RE.findall(reflection_text)):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if obj.get("action") in _VALID_BEHAVIORAL_ACTIONS:
            return obj
    return None


def parse_r7_signal(reflection_text: str) -> BehavioralSignal | None:
    """Extract the R7 behavioral signal from a reflection transcript.

    Returns None — never raises — if R7 is missing or malformed. L2 handles
    the gap. Extra keys (the v2.4 probe fields) are ignored here."""
    obj = _terminal_signal_obj(reflection_text)
    if obj is None:
        _log.warning("parse_r7_signal: no valid R7 JSON line found in reflection text")
        return None
    would_act = obj.get("would_act_within_week")
    if not isinstance(would_act, bool):
        # Tolerate "true"/"false"/1/0; reject anything genuinely unparseable.
        if isinstance(would_act, str) and would_act.lower() in ("true", "false"):
            would_act = would_act.lower() == "true"
        elif would_act in (0, 1):
            would_act = bool(would_act)
        else:
            _log.warning("parse_r7_signal: R7 JSON has unparseable would_act_within_week")
            return None
    return BehavioralSignal(
        action=obj["action"],
        reasoning=str(obj.get("reasoning", "")),
        would_act_within_week=would_act,
    )


def parse_probe_signal(reflection_text: str) -> ProbeSignal | None:
    """Extract the v2.4 R8/R9 probes from the same terminal JSON as R7.

    Returns None — never raises — when there is no terminal signal at all, OR
    when the terminal block predates the probes (neither probe key present) so a
    pre-v2.4 transcript reads as no-probe-signal rather than a false default."""
    obj = _terminal_signal_obj(reflection_text)
    if obj is None:
        return None
    if "novelty" not in obj and "brand_recall" not in obj:
        return None
    return ProbeSignal.from_dict(obj)


# ---- Public API ----


async def run_agent_async(
    agent: PanelAgent,
    config: RunConfig,
    pack: CategoryArtifactPack,
    *,
    run_id: str,
    render_cache_dir: Path | None = None,
) -> AgentTranscript:
    """Async wrapper — run Encoding then Reflection for one PanelAgent."""
    return await asyncio.to_thread(
        run_agent, agent, config, pack, run_id=run_id,
        render_cache_dir=render_cache_dir,
    )


def run_agent(
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
    copy_block = _creative_copy_block(config.creative_inputs)
    encoding_user_content = [
        _image_block(config.asset.image_path, cache=True),
        {"type": "text", "text": context_block + copy_block + _ENCODING_USER},
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
    # The reflection prompt is purpose-conditional (probes only where scored).
    reflection_user = _reflection_user_for(config.creative_inputs.purpose)
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
                {"role": "user", "content": reflection_user},
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
                    {"role": "user", "content": reflection_user},
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
        probe_signal=parse_probe_signal(reflection_text),
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
