"""L1 — Bundled agent runtime.

One agent = one (disposition, context, seed) cell. Two API calls per agent:
  - Call A — Encoding: R1 GUT + R2 COMPREHENSION + R3 EMOTION (single prompt)
  - Call B — Reflection: R4 STICKINESS + R5 SOCIAL + R6 FRICTION

Anthropic prompt caching on the persona+image prefix (cache_control marker
on system text block AND on image block in the user message). Single
marker — no secondary on Call B (the threaded history reuses the cached
prefix established by Call A).

Sonnet 4.6 on both calls. max_tokens=1100. Strict "exactly N sentences.
Stop after the Nth period." prompt language does the actual rationing.

Idempotent per-call persistence: each successful Encoding / Reflection
call writes runs/<account>/<brand>/<run_id>/agent_calls/<aid>__<phase>.json
with the messages, output, and usage. On resume, RunService checks the
agent_calls/ dir before firing a call; if the artifact exists, the
transcript is loaded from disk and the call is skipped.

Productionizes scripts/cache_validation_test_v2.py.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from agent.config import RunConfig
from agent.prompt import build_agent_prompt
from agent.schema import AgentTranscript
from agent.telemetry import call_with_telemetry, run_dir


_log = logging.getLogger(__name__)


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


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


_REFLECTION_USER = (
    "REFLECTION PHASE — 48 hours later. Emit three sections, each "
    "labelled.\n\n"
    "R4 STICKINESS: 3-4 sentences. What stuck from that ad, and what "
    "didn't? Be specific. Stop after the fourth period at most.\n\n"
    "R5 SOCIAL: 3-4 sentences. Would you share/screenshot/mention this "
    "ad to anyone? Why or why not? What social cost or upside?\n\n"
    "R6 FRICTION: 4-5 sentences. If you were considering buying, what's "
    "the single biggest friction the ad introduced — and would you act "
    "on it?"
)


_MAX_TOKENS = 1100


# ---- Agent spec ----


@dataclass
class AgentSpec:
    """One cell in the (disposition, context, seed) matrix.

    agent_id is the position in the RunConfig's cell ordering. cell_key
    is (disposition_label, context_label). Used by L2 to group transcripts
    by disposition.
    """
    agent_id: int
    disposition: tuple[str, str]      # (label, description)
    context: tuple[str, str]          # (label, description)
    seed_idx: int = 0

    @property
    def disposition_label(self) -> str:
        return self.disposition[0]

    @property
    def context_label(self) -> str:
        return self.context[0]

    @property
    def cell_key(self) -> tuple[str, str]:
        return (self.disposition_label, self.context_label)


# ---- Public API ----


async def run_agent_bundled_async(
    spec: AgentSpec,
    config: RunConfig,
    *,
    run_id: str,
) -> AgentTranscript:
    """Async wrapper: run Encoding then Reflection for one agent.

    Idempotent: on resume, existing agent_calls/ artifacts are loaded
    from disk and the corresponding API call is skipped.
    """
    return await asyncio.to_thread(run_agent_bundled, spec, config, run_id=run_id)


def run_agent_bundled(
    spec: AgentSpec,
    config: RunConfig,
    *,
    run_id: str,
) -> AgentTranscript:
    """Sync entry point. Fires Encoding then Reflection, with idempotent
    per-call persistence. Returns AgentTranscript.

    On rate-limit or transient failures the Anthropic SDK retries up to
    max_retries=5 internally; the outer-loop retry happens at RunService.
    """
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["agent"]

    system_text = build_agent_prompt(
        archetype=config.archetype,
        ad_content="",
        disposition=spec.disposition,
        context=spec.context,
    )
    # Cacheable prefix: system text + image. Single cache_control marker
    # on each of these two blocks. ~3,099 tokens per the v2 validation.
    system = [
        {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}},
    ]

    encoding_user_content = [
        _image_block(config.asset.image_path, cache=True),
        {"type": "text", "text": _ENCODING_USER},
    ]

    # Call A — Encoding (R1 + R2 + R3). Idempotent: skip if artifact exists.
    enc_artifact = _load_artifact(run_id, config, spec.agent_id, "encoding")
    if enc_artifact is None:
        response_a = call_with_telemetry(
            client,
            layer="agent",
            model=model,
            agent_id=spec.agent_id,
            round_num=1,  # bundled call A covers rounds 1-3
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": encoding_user_content}],
        )
        encoding_text = _extract_text(response_a)
        _persist_artifact(
            run_id, config, spec, "encoding",
            request={
                "system": system,
                "messages": [{"role": "user", "content": _redact_image_b64(encoding_user_content)}],
                "model": model,
                "max_tokens": _MAX_TOKENS,
            },
            response_text=encoding_text,
            usage=_usage_dict(response_a),
            stop_reason=getattr(response_a, "stop_reason", None),
        )
    else:
        encoding_text = enc_artifact["response_text"]

    # Call B — Reflection (R4 + R5 + R6). Same system, threaded history
    # includes the encoded image block so the cached prefix is reused.
    ref_artifact = _load_artifact(run_id, config, spec.agent_id, "reflection")
    if ref_artifact is None:
        response_b = call_with_telemetry(
            client,
            layer="agent",
            model=model,
            agent_id=spec.agent_id,
            round_num=4,  # bundled call B covers rounds 4-6
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[
                {"role": "user", "content": encoding_user_content},
                {"role": "assistant", "content": encoding_text},
                {"role": "user", "content": _REFLECTION_USER},
            ],
        )
        reflection_text = _extract_text(response_b)
        _persist_artifact(
            run_id, config, spec, "reflection",
            request={
                "system": "(elided — same as encoding)",
                "messages": [
                    {"role": "user", "content": "(image elided)"},
                    {"role": "assistant", "content": encoding_text},
                    {"role": "user", "content": _REFLECTION_USER},
                ],
                "model": model,
                "max_tokens": _MAX_TOKENS,
            },
            response_text=reflection_text,
            usage=_usage_dict(response_b),
            stop_reason=getattr(response_b, "stop_reason", None),
        )
    else:
        reflection_text = ref_artifact["response_text"]

    return AgentTranscript(
        agent_id=spec.agent_id,
        disposition_label=spec.disposition_label,
        context_label=spec.context_label,
        seed_idx=spec.seed_idx,
        encoding_text=encoding_text,
        reflection_text=reflection_text,
    )


# ---- Idempotent per-call persistence ----


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


def _load_artifact(run_id: str, config: RunConfig, agent_id: int, phase: str) -> dict | None:
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
    spec: AgentSpec,
    phase: str,
    *,
    request: dict,
    response_text: str,
    usage: dict | None,
    stop_reason: str | None,
) -> None:
    path = _artifact_path(run_id, config, spec.agent_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "agent_id": spec.agent_id,
        "phase": phase,
        "disposition_label": spec.disposition_label,
        "context_label": spec.context_label,
        "seed_idx": spec.seed_idx,
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


# ---- Helpers ----


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
