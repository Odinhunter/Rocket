"""Telemetry sidecar — append one JSONL line per Anthropic API call.

Lives in its own module (rather than `agent/persistence.py`) so the
runner and synthesis layers can import it without pulling in synthesis
dataclasses, which would create a circular import.

Usage:
    from agent.telemetry import current_run_id, call_with_telemetry

    # In batch_run.main:
    current_run_id.set(run_id)

    # In runner / synthesis:
    response = call_with_telemetry(
        client, layer="agent", model=use_model, agent_id=aid,
        round_num=rnd, max_tokens=200, system=system, messages=messages,
    )

When `current_run_id` is unset (unit tests, scripts running outside a
batch_run context), `record_telemetry` is a no-op — instrumentation
adds zero overhead off the batch path.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

RUNS_DIR = Path("runs")

current_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_run_id", default=None,
)


def make_run_id(seed: int, focal_label: str) -> str:
    """<YYYYmmdd_HHMMSS>_seed<N>_<focal_slug>."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "_", focal_label.lower()).strip("_")[:30]
    return f"{timestamp}_seed{seed}_{slug}"


def run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def record_telemetry(
    *,
    layer: str,
    model: str,
    latency_ms: float,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_tokens: int | None = None,
    cache_creation_tokens: int | None = None,
    agent_id: int | None = None,
    round_num: int | None = None,
    retries: int = 0,
    status: str = "ok",
    error: str | None = None,
) -> None:
    """Append one JSONL event to runs/<run_id>/telemetry.jsonl. No-op if
    `current_run_id` is unset."""
    rid = current_run_id.get()
    if rid is None:
        return
    path = run_dir(rid) / "telemetry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "layer": layer,
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "agent_id": agent_id,
        "round_num": round_num,
        "retries": retries,
        "status": status,
        "error": error,
    }
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def call_with_telemetry(
    client: Any,
    *,
    layer: str,
    model: str,
    agent_id: int | None = None,
    round_num: int | None = None,
    retries: int = 0,
    status: str = "ok",
    **create_kwargs: Any,
) -> Any:
    """Wrap client.messages.create(...) with timing + token telemetry.

    On exception, records status=failed with error message and re-raises.
    Returns the response unchanged on success.
    """
    t0 = time.time()
    try:
        response = client.messages.create(model=model, **create_kwargs)
    except Exception as exc:
        elapsed = (time.time() - t0) * 1000
        record_telemetry(
            layer=layer, model=model, latency_ms=elapsed,
            agent_id=agent_id, round_num=round_num,
            retries=retries, status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    elapsed = (time.time() - t0) * 1000
    usage = getattr(response, "usage", None)
    record_telemetry(
        layer=layer, model=model, latency_ms=elapsed,
        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        cache_read_tokens=(
            getattr(usage, "cache_read_input_tokens", None) if usage else None
        ),
        cache_creation_tokens=(
            getattr(usage, "cache_creation_input_tokens", None) if usage else None
        ),
        agent_id=agent_id, round_num=round_num,
        retries=retries, status=status,
    )
    return response


def telemetry_summary(run_id: str) -> str:
    """Human-readable summary table of a run's telemetry sidecar."""
    path = run_dir(run_id) / "telemetry.jsonl"
    if not path.exists():
        return "(no telemetry recorded)"
    events = [
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
    ]
    if not events:
        return "(telemetry file empty)"

    by_layer: dict[str, list[dict]] = {}
    for ev in events:
        by_layer.setdefault(ev["layer"], []).append(ev)

    # Per-million-token cost estimates (USD); update as pricing changes.
    rates = {
        "claude-sonnet-4-6": (3.0, 15.0),
        "claude-opus-4-7": (15.0, 75.0),
    }

    lines = ["=" * 78, "TELEMETRY SUMMARY", "=" * 78]
    grand_in, grand_out, grand_cost = 0, 0, 0.0
    grand_retries, grand_failed = 0, 0
    for layer in ("agent", "per_round_synthesis", "target_id", "strategist"):
        layer_events = by_layer.get(layer, [])
        if not layer_events:
            continue
        in_tot = sum((e.get("input_tokens") or 0) for e in layer_events)
        out_tot = sum((e.get("output_tokens") or 0) for e in layer_events)
        latencies = sorted(
            [e["latency_ms"] for e in layer_events if e.get("latency_ms")]
        )
        p50 = latencies[len(latencies) // 2] if latencies else 0
        p95 = (
            latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
            if latencies else 0
        )
        retries = sum(e.get("retries", 0) for e in layer_events)
        failed = sum(1 for e in layer_events if e.get("status") == "failed")
        models = {e["model"] for e in layer_events}
        cost = 0.0
        for e in layer_events:
            r = rates.get(e["model"])
            if r and e.get("input_tokens") and e.get("output_tokens"):
                cost += (e["input_tokens"] / 1e6) * r[0] + (e["output_tokens"] / 1e6) * r[1]
        grand_in += in_tot
        grand_out += out_tot
        grand_cost += cost
        grand_retries += retries
        grand_failed += failed
        lines.append(
            f"  {layer:25s}  calls={len(layer_events):3d}  "
            f"in={in_tot:>7,}  out={out_tot:>6,}  "
            f"p50={p50:>5.0f}ms  p95={p95:>5.0f}ms  "
            f"retries={retries}  failed={failed}  ~${cost:.3f}"
        )
        lines.append(f"      models: {', '.join(sorted(models))}")
    lines.append("-" * 78)
    lines.append(
        f"  {'TOTAL':25s}  calls={len(events):3d}  "
        f"in={grand_in:>7,}  out={grand_out:>6,}  "
        f"retries={grand_retries}  failed={grand_failed}  ~${grand_cost:.3f}"
    )
    return "\n".join(lines)
