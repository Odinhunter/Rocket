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
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def runs_root() -> Path:
    """Where runs live. ABSOLUTE, and resolved fresh on every call.

    This was `RUNS_DIR = Path("runs")` — relative, and therefore resolved
    against the current working directory. Two things went wrong with that,
    and the second one costs money:

      1. The offline test suite runs from the repo root, so a test that
         reached the engine wrote into the REAL runs/ directory no matter what
         `create_app(runs_root=tmp_path)` had been told. That is how a phantom
         `demo/default/...` run appeared among real client work.
      2. ⚠ Start uvicorn from anywhere other than the repo root — which is
         exactly what a container does — and the ENGINE writes a finished run
         to `<cwd>/runs` while the SERVER reads `REPO_ROOT/runs`. The run
         completes, the money is spent, and it never appears in the app.

    A function rather than a module constant on purpose: three modules used to
    do `from agent.telemetry import RUNS_DIR`, which binds the value at import
    time, so rebinding the attribute here would have fixed some call sites and
    silently missed those. There is no `RUNS_DIR` left to import.

    `ROCKET_RUNS_DIR` overrides it — P6 needs the runs on a mounted volume
    rather than inside the container image.
    """
    override = os.environ.get("ROCKET_RUNS_DIR", "").strip()
    return Path(override).expanduser().resolve() if override else REPO_ROOT / "runs"

current_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_run_id", default=None,
)
# Multi-tenant scaffolding (Week 1 = filesystem-only stubs; full Account /
# BrandProfile entities arrive Week 2/3). Set by RunService at the start of
# every run alongside current_run_id; defaults preserve the flat layout for
# scripts that run outside RunService (cache_validation tests, etc.).
current_account_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_account_id", default=None,
)
current_brand_profile_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_brand_profile_id", default=None,
)


def make_run_id(seed: int, asset_label: str) -> str:
    """<YYYYmmdd_HHMMSS>_seed<N>_<asset_slug>."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "_", asset_label.lower()).strip("_")[:30]
    return f"{timestamp}_seed{seed}_{slug}"


def run_dir(
    run_id: str,
    *,
    account_id: str | None = None,
    brand_profile_id: str | None = None,
) -> Path:
    """Return runs/<account_id>/<brand_profile_id>/<run_id>/.

    account_id / brand_profile_id default to the values set in the context
    vars (RunService sets these at run start). If both are unset, falls back
    to the flat layout `runs/<run_id>/` — preserves compatibility with
    cache-validation scripts and any standalone use outside RunService.
    """
    aid = account_id if account_id is not None else current_account_id.get()
    bpid = brand_profile_id if brand_profile_id is not None else current_brand_profile_id.get()
    root = runs_root()
    if aid is not None and bpid is not None:
        return root / aid / bpid / run_id
    return root / run_id


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


def _rate_table() -> dict[str, tuple[float, float, float, float]]:
    """Per-million-token USD rates: (input, output, cache_read, cache_write).

    ⚠ A FUNCTION, NOT A LOCAL DICT, so a test can read the SAME table
    production prices against. It lived inside `telemetry_summary` until
    2026-08-22, which meant the only way to check it was to re-type it —
    and a re-typed table cannot tell you a model is missing from the real
    one. See tests/test_every_model_is_priced.py.

    ⚠⚠ EVERY MODEL THE ENGINE CAN CALL MUST HAVE A ROW. An unpriced model
    contributes nothing to the total, so its calls report as $0.00 — which
    is how a $5-8 generation path came to have a cost meter reading zero.
    """
    return {
        "claude-sonnet-4-6": (3.0, 15.0, 0.3, 3.75),
        # Opus 4.7 / 4.8 are $5/$25 per MTok (cache read 0.1x input, write 1.25x
        # @ 5-min TTL). The prior (15,75) on opus-4-7 was a stale Opus-3-era rate,
        # 3x too high — it overcounted target_id (and any opus layer) in every run.
        "claude-opus-4-7": (5.0, 25.0, 0.5, 6.25),
        "claude-opus-4-8": (5.0, 25.0, 0.5, 6.25),
        # ⚠⚠ ADDED 2026-08-22, AND ITS ABSENCE MADE THIS METER READ ZERO ON THE
        # PATH THAT SPENDS THE MOST. `scripts/generate_audience.py` runs on
        # claude-opus-5 (MODEL, line 124) — a $5-8 region generation reported
        # $0.00 here because an unpriced model contributes nothing to the total.
        # ⭐ Opus 5 is $5/$25 per MTok, cache read 0.1x input, cache write 1.25x
        # at the 5-minute TTL — the same rates as 4.7/4.8, which is exactly why
        # nobody noticed the row was missing.
        "claude-opus-5": (5.0, 25.0, 0.5, 6.25),
        # Sonnet 5 is $3/$15 list. ⚠ An introductory $2/$10 runs to 2026-08-31;
        # the list rate is used here deliberately, so this OVER-states rather
        # than under-states during the intro window. Nothing in the engine uses
        # it today — it is here so a future switch cannot silently read zero.
        "claude-sonnet-5": (3.0, 15.0, 0.3, 3.75),
    }


def telemetry_summary(
    run_id: str,
    *,
    account_id: str | None = None,
    brand_profile_id: str | None = None,
) -> str:
    """Human-readable summary table of a run's telemetry sidecar."""
    path = run_dir(run_id, account_id=account_id, brand_profile_id=brand_profile_id) / "telemetry.jsonl"
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
    # (in_rate, out_rate, cache_read_rate, cache_write_5m_rate)
    rates = _rate_table()

    lines = ["=" * 78, "TELEMETRY SUMMARY", "=" * 78]
    grand_in, grand_out, grand_cost = 0, 0, 0.0
    grand_retries, grand_failed = 0, 0
    # rocket-2.2.0: assessor/prescriber are the v2.2 L4 split (strategist is the
    # legacy single-pass). Include any recorded layer not in the fixed order so
    # a new layer never silently drops out of the cost total.
    _known = ("agent", "l2", "l3", "target_id", "strategist", "assessor", "prescriber")
    for layer in _known + tuple(sorted(set(by_layer) - set(_known))):
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
            if r is None:
                continue
            in_t = e.get("input_tokens") or 0
            out_t = e.get("output_tokens") or 0
            cr = e.get("cache_read_tokens") or 0
            cw = e.get("cache_creation_tokens") or 0
            cost += (
                in_t * r[0]
                + out_t * r[1]
                + cr * r[2]
                + cw * r[3]
            ) / 1_000_000
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
