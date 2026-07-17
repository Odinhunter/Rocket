"""L1 — bundled agent runtime.

  - The agent is a PanelAgent (a point across the four population axes).
  - The system prompt is the RENDERED persona core (from agent/render.py).
    The context is rendered separately and goes in the USER message,
    AFTER the cached image block — so agents that share a persona core
    share the cached system+image prefix even when their contexts differ.
  - v3 two-call reaction (docs/v3_protocol.md §2): Call A (Encounter) emits
    the IN-FEED `action` as a terminal JSON line — captured at the glance,
    System-1. Call B (Reflection) emits the defined follow-through `next_step`
    as a terminal JSON line — the considered "a day or two later" judgement.
    Both are parsed into AgentTranscript.behavioral_signal. Never a funnel rate.

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
    _VALID_NEXT_STEPS,
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

# The reaction-surface version. Bumped when the Call A / Call B prompt STRUCTURE
# or the emitted signal shape changes — NOT for wording tweaks (Week-3 A/B arms
# take -rc{n}). Pinned by the byte-identity guards (W1·E2). docs/v3_protocol.md §10.
REACTION_PROTOCOL_VERSION = "reaction-v3"

# Sized to fit a terminal JSON line on EACH call (Call A action / Call B
# next_step) without crowding the R-sections. Both calls carry one now.
_MAX_TOKENS = 1250

_ENCODING_USER = (
    "You are a real person glancing at an ad, NOT a "
    "writer. Keep every section to 1-2 plain sentences (a line or two). "
    "Be blunt and conversational; never eloquent, thorough, or clever — "
    "no literary phrasing, no neat metaphors, no tidy summaries. Three "
    "labelled sections.\n\n"
    "R1 GUT: 1-2 sentences. The first thing that goes through your head, "
    "before you really think about it.\n\n"
    "R2 COMPREHENSION: 1-2 sentences. What is this selling, and who do you "
    "picture it being for — what kind of person comes to mind? And does that "
    "feel like you, or like someone else?\n\n"
    "R3 INTEREST: 1-2 sentences. Did any of it catch your interest, or did it "
    "kind of wash over you? Your own words.\n\n"
    "ACTION: after those three lines, emit exactly ONE line of JSON and nothing "
    "after it:\n"
    '{"action": "<scroll_past|linger|tap_cta|save|share>", "reasoning": "<one '
    'short sentence in your own words, about the ad you just saw>"}\n'
    "This is what your thumb ACTUALLY does in that half-second — scroll on by, "
    "stop and look, tap through, save it, or send it to someone. Not what you "
    "might do later; what you do right now. Never a funnel rate or a percentage."
)

# The next_step is a single terminal JSON line so it parses deterministically
# out of otherwise free-form reflection prose.
#
# CONDITIONAL PROBES (the 2026-07-11 finding, docs/v3_protocol.md §2.2):
# an earlier build asked R8 novelty + R9 brand_recall on EVERY run. A paid anchor
# run proved this CONTAMINATES the blind reaction — asking "did this teach you
# something new?" before the follow-through reframes purchase intent around
# novelty and roughly HALVED within-target intent on a familiar-brand direct-sell
# ad (68% -> 26%, same ad/seed, actions unchanged). So a probe is asked ONLY on
# the purpose that reads it: novelty on informer, brand_recall on brand-building.
# The three would-act/action jobs (direct-sell, cold-hook, retain) get the
# probe-free reflection. Per-persona blindness holds — an extra reflection
# question never reveals the ad's objective.

# The probe-free reflection base (R4/R5/R6) + the terminal next_step. v3 retires
# the v2.3 byte-identity (the terminal line now emits next_step, not an R7
# action); a new guard pins reaction-v3 (W1·E2). docs/v3_protocol.md §2.2, §10.
_REFLECTION_BASE = (
    "It's a day or two later. Keep every section to 1-2 sentences, "
    "plain and short. If an ad left "
    "almost nothing behind, say so plainly — don't manufacture depth.\n\n"
    "R4 STICKINESS: 1-2 sentences. If anything, what do you remember about "
    "the ad?\n\n"
    "R5 SOCIAL: 1-2 sentences. Would you bring it up to anyone — and who?\n\n"
    "R6 FRICTION: 1-2 sentences. If you did think about getting it, what's "
    "the one thing that'd hold you back?\n\n"
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
_NEXT_STEP_HEAD = "NEXT_STEP: emit exactly ONE line of JSON and nothing after it:\n"
_NEXT_STEP_CORE = (
    '{"next_step": "<buy_now|buy_at_restock|research_first|mention_to_someone|nothing>", '
    '"reasoning": "<one short sentence in your own words>"'
)
_NEXT_STEP_NOTE = (
    "next_step = what you would ACTUALLY do next about this, a day or two on: "
    "buy_now (order it right away), buy_at_restock (buy it when you next run out "
    "or need more), research_first (look it up or compare before deciding — "
    "interest, not a commitment), mention_to_someone (wouldn't buy it yourself "
    "but would tell or recommend someone), or nothing. Be honest — most ads end "
    "in nothing. Never a funnel rate or a percentage."
)


def _reflection_user_for(purpose: str) -> str:
    """The Call B reflection prompt for a run's declared purpose: R4-R6 + the
    terminal next_step JSON. The core three (direct-sell / cold-hook / retain)
    get the probe-free string; informer adds R8 novelty; brand-building adds R9
    brand_recall — each only where its metric reads it, so the would-act/action
    jobs are never contaminated (docs/v3_protocol.md §2.2)."""
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
    note = _NEXT_STEP_NOTE
    if notes:
        note = _NEXT_STEP_NOTE + " Also: " + "; ".join(notes) + "."
    return _REFLECTION_BASE + prose + _NEXT_STEP_HEAD + _NEXT_STEP_CORE + json_extra + "}\n" + note


def _creative_copy_block(ci: CreativeInputs) -> str:
    """The ad copy + offer accompanying the image, formatted as the agent
    reads it in feed. Empty string when nothing was provided (so image-only
    runs are byte-unchanged). MUST go in the UNCACHED user text — never the
    cached persona-core/image prefix — so it does not perturb caching."""
    lines = []
    if ci.headline.strip():
        lines.append(f"The big line on it: {ci.headline.strip()}")
    if ci.primary_text.strip():
        lines.append(f"The smaller text: {ci.primary_text.strip()}")
    if ci.offer.strip():
        lines.append(f"The price / offer: {ci.offer.strip()}")
    if not lines:
        return ""
    return (
        "There are words on the ad too — you read them off the picture as "
        "you scroll:\n" + "\n".join(lines) + "\n\n"
    )


# ---- Signal parsing (pure functions — offline-testable) ----

# Find the last balanced {...} JSON object in the text. Tolerant of prose bleed.
_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}")


def _last_json_with(text: str, key: str, valid: set[str]) -> dict | None:
    """The last balanced {...} block whose `key` holds a value in `valid`,
    parsed to a dict. Scanned from the END so stray braces in earlier prose
    don't capture. None if no such block exists. The enum-membership check is
    the LOUD backstop against a stale/removed literal matching silently."""
    for raw in reversed(_JSON_OBJ_RE.findall(text)):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if obj.get(key) in valid:
            return obj
    return None


def parse_encounter_action(encoding_text: str) -> dict | None:
    """The Call A terminal action JSON (or None if missing/malformed)."""
    return _last_json_with(encoding_text, "action", _VALID_BEHAVIORAL_ACTIONS)


def parse_reflection_obj(reflection_text: str) -> dict | None:
    """The Call B terminal next_step JSON — carries next_step, reasoning, and
    (only when scored) the probe fields. Shared by signal + probe parsing so
    both read the SAME terminal block."""
    return _last_json_with(reflection_text, "next_step", _VALID_NEXT_STEPS)


def parse_behavioral_signal(
    encoding_text: str, reflection_text: str
) -> BehavioralSignal | None:
    """Assemble the v3 BehavioralSignal from the Call A action + the Call B
    next_step. Returns None — never raises — if EITHER terminal block is missing
    or malformed (L2 handles the gap; n counts only complete signals)."""
    action_obj = parse_encounter_action(encoding_text)
    if action_obj is None:
        _log.warning("parse_behavioral_signal: no valid Call A action JSON found")
        return None
    step_obj = parse_reflection_obj(reflection_text)
    if step_obj is None:
        _log.warning("parse_behavioral_signal: no valid Call B next_step JSON found")
        return None
    return BehavioralSignal(
        action=action_obj["action"],
        action_reasoning=str(action_obj.get("reasoning", "")),
        next_step=step_obj["next_step"],
        next_step_reasoning=str(step_obj.get("reasoning", "")),
    )


def parse_probe_signal(reflection_text: str) -> ProbeSignal | None:
    """Extract the conditional R8/R9 probes from the same Call B terminal JSON
    as the next_step.

    Returns None — never raises — when there is no terminal block at all, OR
    when neither probe key is present (a probe-free run reads as no-probe-signal
    rather than a false default)."""
    obj = parse_reflection_obj(reflection_text)
    if obj is None:
        return None
    if "novelty" not in obj and "brand_recall" not in obj:
        return None
    return ProbeSignal.from_dict(obj)


_CYCLE_PROSE = {
    "just_bought": "just recently stocked up on {cat} — well supplied, with no near-term need.",
    "mid_cycle": "partway through their current {cat} — not thinking about restocking yet.",
    "running_low": "nearly out of {cat} — they'll need to restock soon.",
}


def _cycle_line(cycle_position: str, category: str) -> str:
    """A deterministic, TEMPLATED (no model call) line stating where the persona
    is in their category cycle right now. Goes in the UNCACHED context block so it
    never fragments the cached persona core (v3 A4, docs/v3_protocol.md §5)."""
    cat = category.replace("_", " ")
    body = _CYCLE_PROSE.get(cycle_position, _CYCLE_PROSE["mid_cycle"]).format(cat=cat)
    return "WHERE THINGS STAND FOR THEM RIGHT NOW: " + body


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
        f"{_cycle_line(agent.cycle_position, agent.category)}\n\n"
        "Attention gates everything that follows. If this context implies "
        "low attention, the ad probably gets a sub-second thumb-flick "
        "regardless of whether they would be interested in a more "
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
        behavioral_signal=parse_behavioral_signal(encoding_text, reflection_text),
        probe_signal=parse_probe_signal(reflection_text),
        cycle_position=agent.cycle_position,
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
