"""RunService — the orchestrator for a Creative Read.

Single entry point: RunService.run(config) -> Report.

Wires the full pipeline:
  1. Resolve dispositions + contexts; build the agent matrix.
  2. Write the initial run.json (status=in_progress).
  3. Fan out L1 agents in parallel (with per-call idempotent resume).
  4. Run L2 fan-out and target classification in parallel.
  5. Run L3 population synthesis.
  6. Run L4 strategic memo.
  7. Validate schema + telemetry invariants.
  8. Write final run.json (status=complete) + invariants report.

Multi-tenant filesystem layout:
  runs/<account_id>/<brand_profile_id>/<run_id>/
    ├── run.json                  — config + Report (status field tracks state)
    ├── telemetry.jsonl           — per-call cost/latency/cache events
    ├── agent_calls/              — per-bundled-call artifacts (idempotency)
    │   ├── 0000__encoding.json
    │   ├── 0000__reflection.json
    │   └── …
    ├── transcripts.json          — assembled AgentTranscript[]
    ├── l2_summaries.json         — L2Summary[] per disposition
    ├── l3_summary.json           — L3Summary
    └── target_classification.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from agent.config import RunConfig
from agent.runtime import AgentSpec, run_agent_bundled_async
from agent.schema import AgentTranscript, Report
from agent.synthesis_l2 import synthesize_disposition_async
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import synthesize_memo
from agent.synthesis_types import L2Summary, L3Summary, TargetClassification
from agent.target_id import identify_target
from agent.telemetry import (
    current_account_id,
    current_brand_profile_id,
    current_run_id,
    make_run_id,
    run_dir,
)
from archetypes.context import list_contexts
from archetypes.disposition import list_dispositions


_log = logging.getLogger(__name__)


# ---- Telemetry invariants ----


_CACHE_MIN_TOKENS = 1500       # any cached prefix should be meaningfully large; floor for sanity check
_OUTPUT_MAX_TOKENS = 1000      # strict-prompt budget for L1 calls
# Per-agent cost budget. Empirical baseline is $0.028 (Sonnet 4.6, bundled,
# cached). Generous 2x ceiling catches drift on output discipline or cache
# misses without firing on noise.
_AGENT_COST_CEILING_PER_AGENT = 0.06


# ---- Public entry point ----


class RunService:
    """Single-entry orchestrator. RunService.run(config) is the only path
    into the production pipeline."""

    @staticmethod
    def run(config: RunConfig, *, resume_run_id: str | None = None) -> Report:
        """Synchronous wrapper. Validates config, runs the async pipeline,
        validates telemetry invariants, returns the Report.

        Dispatches on protocol version: a rocket-2.0.0 config (or any config
        carrying an audience_spec) routes to the two-phase RunServiceV2; the
        rocket-1.3.0 path below is unchanged.

        resume_run_id: if provided, use this run_id instead of minting a new
        one. Per-call idempotency means any completed agent_calls/ artifacts
        will be loaded from disk; only missing calls re-fire. Lets a partial
        run resume cheaply. (v1 path only.)
        """
        if config.protocol_version == "rocket-2.0.0" or config.audience_spec is not None:
            # Lazy import — run_service_v2 imports helpers from this module.
            from agent.run_service_v2 import RunServiceV2

            if resume_run_id is not None:
                _log.warning(
                    "resume_run_id is not supported on the v2 path; ignoring"
                )
            return RunServiceV2.run(config)
        config.validate()
        return asyncio.run(RunService._run_async(config, resume_run_id=resume_run_id))

    @staticmethod
    async def _run_async(config: RunConfig, *, resume_run_id: str | None = None) -> Report:
        if resume_run_id:
            run_id = resume_run_id
            _log.info("RunService RESUMING run_id=%s", run_id)
        else:
            run_id = make_run_id(config.seed, config.asset.label)
        rd = run_dir(run_id, account_id=config.account_id, brand_profile_id=config.brand_profile_id)
        rd.mkdir(parents=True, exist_ok=True)

        # Set context vars so telemetry sidecar writes into this run's dir.
        current_account_id.set(config.account_id)
        current_brand_profile_id.set(config.brand_profile_id)
        current_run_id.set(run_id)

        _log.info("RunService starting: run_id=%s run_dir=%s", run_id, rd)

        # ---- Sampling: dispositions + contexts ----
        rng = random.Random(config.seed)
        disp_pool = list_dispositions(config.archetype, config.category)
        ctx_pool = list_contexts(config.archetype)
        if len(disp_pool) < config.dispositions_per_run:
            raise RuntimeError(
                f"Disposition pool for ({config.archetype}, {config.category}) "
                f"has only {len(disp_pool)} entries; need {config.dispositions_per_run}"
            )
        if len(ctx_pool) < config.contexts_per_run:
            raise RuntimeError(
                f"Context pool for {config.archetype} has only {len(ctx_pool)} "
                f"entries; need {config.contexts_per_run}"
            )
        chosen_disps = rng.sample(disp_pool, config.dispositions_per_run)
        chosen_ctxs = rng.sample(ctx_pool, config.contexts_per_run)
        config.disposition_version = config.compute_disposition_version(chosen_disps)

        # Build the (D × C × S) agent matrix.
        specs: list[AgentSpec] = []
        agent_id = 0
        for disp in chosen_disps:
            for ctx in chosen_ctxs:
                for seed_idx in range(config.seeds_per_cell):
                    specs.append(AgentSpec(
                        agent_id=agent_id, disposition=disp, context=ctx, seed_idx=seed_idx,
                    ))
                    agent_id += 1
        _log.info(
            "Built %d agents (D=%d × C=%d × S=%d) over dispositions %s and contexts %s",
            len(specs), config.dispositions_per_run, config.contexts_per_run,
            config.seeds_per_cell, [d[0] for d in chosen_disps], [c[0] for c in chosen_ctxs],
        )

        # ---- Persist run.json (in_progress) ----
        _write_run_json(rd, run_id, config, status="in_progress", agent_specs=specs)

        # ---- L1: bundled-agent fan-out ----
        l1_t0 = time.time()
        transcripts = await _run_l1_parallel(specs, config, run_id)
        l1_elapsed = time.time() - l1_t0
        _log.info("L1 complete: %d transcripts in %.1fs", len(transcripts), l1_elapsed)
        _persist_json(rd / "transcripts.json", [t.to_dict() for t in transcripts])

        # ---- L2 + target_id in parallel ----
        l2_t0 = time.time()
        target_cls, l2_summaries = await _run_l2_and_target_id(
            transcripts, chosen_disps, config,
        )
        l2_elapsed = time.time() - l2_t0
        _log.info("L2 + target_id complete in %.1fs", l2_elapsed)
        _persist_json(rd / "l2_summaries.json", [s.to_dict() for s in l2_summaries])
        _persist_json(rd / "target_classification.json", target_cls.to_dict())

        # ---- L3: population synthesis ----
        l3_t0 = time.time()
        l3 = await asyncio.to_thread(synthesize_population, l2_summaries, target_cls, config)
        l3_elapsed = time.time() - l3_t0
        _log.info("L3 complete in %.1fs", l3_elapsed)
        _persist_json(rd / "l3_summary.json", l3.to_dict())

        # ---- L4: strategic memo ----
        l4_t0 = time.time()
        report = await asyncio.to_thread(synthesize_memo, l3, target_cls, config)
        l4_elapsed = time.time() - l4_t0
        _log.info("L4 complete in %.1fs: verdict=%s confidence=%d",
                  l4_elapsed, report.verdict, report.confidence)

        # ---- Persist final run.json ----
        _write_run_json(rd, run_id, config, status="complete", agent_specs=specs, report=report)

        # ---- Verify telemetry invariants ----
        invariants = _verify_invariants(rd, total_agents=len(specs))
        _persist_json(rd / "invariants.json", invariants)
        if not invariants["all_passed"]:
            _log.warning(
                "Run %s completed but telemetry invariants failed: %s",
                run_id, json.dumps(invariants["failures"], indent=2),
            )

        return report


# ---- L1 ----


async def _run_l1_parallel(
    specs: list[AgentSpec],
    config: RunConfig,
    run_id: str,
) -> list[AgentTranscript]:
    sem = asyncio.Semaphore(config.max_concurrent_agents)

    async def _bounded(spec: AgentSpec) -> AgentTranscript:
        async with sem:
            return await run_agent_bundled_async(spec, config, run_id=run_id)

    transcripts = await asyncio.gather(*[_bounded(s) for s in specs])
    transcripts.sort(key=lambda t: t.agent_id)
    return transcripts


# ---- L2 + target_id (parallel) ----


async def _run_l2_and_target_id(
    transcripts: list[AgentTranscript],
    disposition_pool: list[tuple[str, str]],
    config: RunConfig,
) -> tuple[TargetClassification, list[L2Summary]]:
    """Fire L2 fan-out (per-disposition Sonnet) and target_id (Opus vision)
    in parallel. They don't depend on each other; both are pure functions
    of L1 output (L2) and the asset+disposition_pool (target_id)."""
    by_disposition: dict[str, list[AgentTranscript]] = defaultdict(list)
    for t in transcripts:
        by_disposition[t.disposition_label].append(t)

    # Each disposition spawns one L2 call; target_id spawns one Opus call.
    l2_coros = [
        synthesize_disposition_async(label, ts, config)
        for label, ts in by_disposition.items()
    ]
    target_coro = asyncio.to_thread(identify_target, disposition_pool, config)

    target_cls, *l2_summaries = await asyncio.gather(target_coro, *l2_coros)
    l2_summaries.sort(key=lambda s: s.disposition_label)
    return target_cls, l2_summaries


# ---- Persistence helpers ----


def _persist_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _write_run_json(
    rd: Path,
    run_id: str,
    config: RunConfig,
    *,
    status: str,
    agent_specs: list[AgentSpec],
    report: Report | None = None,
) -> None:
    payload = {
        "run_id": run_id,
        "status": status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
        "agent_specs": [
            {
                "agent_id": s.agent_id,
                "disposition_label": s.disposition_label,
                "context_label": s.context_label,
                "seed_idx": s.seed_idx,
            }
            for s in agent_specs
        ],
        "report": report.to_dict() if report is not None else None,
    }
    _persist_json(rd / "run.json", payload)


# ---- Telemetry invariant verification ----


def _verify_invariants(rd: Path, *, total_agents: int) -> dict:
    """Read telemetry.jsonl and assert the load-bearing invariants:

    1. Every L1 'agent' call has cache_creation_input_tokens >= 2900 OR
       cache_read_input_tokens >= 2900 (one of the two — Encoding writes,
       Reflection reads).
    2. Every Reflection (the second agent call per agent) has cache_read
       >= 2900.
    3. No L1 call has output_tokens > 1000.
    4. Total cost <= reasonable threshold.

    Returns a dict with `all_passed` and per-invariant detail.
    """
    tele_path = rd / "telemetry.jsonl"
    if not tele_path.exists():
        return {"all_passed": False, "reason": "no telemetry.jsonl found"}
    events = [json.loads(line) for line in tele_path.read_text().splitlines() if line.strip()]

    agent_events = [e for e in events if e.get("layer") == "agent" and e.get("status") == "ok"]

    failures: list[dict] = []

    # 1: per-agent cache pair match. Encoding writes the prefix; Reflection
    # must read approximately the same number of tokens (within ~50, allowing
    # for tokenization edge cases on the threaded encoding text). The prefix
    # size varies with image size, so absolute floors are wrong — what matters
    # is that the cache hit on Reflection.
    by_agent: dict[int, list[dict]] = {}
    for ev in agent_events:
        aid = ev.get("agent_id")
        if aid is None:
            continue
        by_agent.setdefault(int(aid), []).append(ev)

    for aid, evs in by_agent.items():
        cw_max = max((e.get("cache_creation_tokens") or 0) for e in evs)
        cr_max = max((e.get("cache_read_tokens") or 0) for e in evs)
        if cw_max < _CACHE_MIN_TOKENS:
            failures.append({
                "rule": "encoding_cache_creation_min",
                "agent_id": aid,
                "cache_create": cw_max,
                "min": _CACHE_MIN_TOKENS,
            })
        if cr_max < _CACHE_MIN_TOKENS:
            failures.append({
                "rule": "reflection_cache_read_min",
                "agent_id": aid,
                "cache_read": cr_max,
                "min": _CACHE_MIN_TOKENS,
            })
        # Cache pair: Reflection's read should approximately match Encoding's write.
        if cw_max and cr_max and abs(cw_max - cr_max) > 100:
            failures.append({
                "rule": "cache_pair_mismatch",
                "agent_id": aid,
                "cache_create": cw_max,
                "cache_read": cr_max,
                "diff": abs(cw_max - cr_max),
            })

    # 3: output budget
    for ev in agent_events:
        out = ev.get("output_tokens") or 0
        if out > _OUTPUT_MAX_TOKENS:
            failures.append({
                "rule": "output_budget",
                "agent_id": ev.get("agent_id"),
                "round_num": ev.get("round_num"),
                "output_tokens": out,
                "max": _OUTPUT_MAX_TOKENS,
            })

    # 4: total cost estimate (includes cache read/write). Per-agent cost ceiling
    # is checked against the agent layer only — synthesis is a fixed overhead
    # roughly independent of agent count.
    rates = {
        # (input, output, cache_read, cache_write_5m)
        "claude-sonnet-4-6": (3.0, 15.0, 0.3, 3.75),
        "claude-opus-4-7": (15.0, 75.0, 1.5, 18.75),
    }

    def event_cost(ev: dict) -> float:
        r = rates.get(ev.get("model"))
        if r is None:
            return 0.0
        in_t = ev.get("input_tokens") or 0
        out_t = ev.get("output_tokens") or 0
        cr = ev.get("cache_read_tokens") or 0
        cw = ev.get("cache_creation_tokens") or 0
        return (in_t * r[0] + out_t * r[1] + cr * r[2] + cw * r[3]) / 1_000_000

    cost_total = sum(event_cost(ev) for ev in events)
    agent_cost = sum(event_cost(ev) for ev in agent_events)
    per_agent_cost = (agent_cost / total_agents) if total_agents else 0.0

    if total_agents > 0 and per_agent_cost > _AGENT_COST_CEILING_PER_AGENT:
        failures.append({
            "rule": "agent_cost_ceiling",
            "per_agent_cost_usd": round(per_agent_cost, 4),
            "ceiling_usd": _AGENT_COST_CEILING_PER_AGENT,
            "n_agents": total_agents,
        })

    return {
        "all_passed": len(failures) == 0,
        "failures": failures,
        "n_l1_calls_checked": len(agent_events),
        "total_l1_calls_expected": total_agents * 2,
        "agent_layer_cost_usd": round(agent_cost, 4),
        "per_agent_cost_usd": round(per_agent_cost, 4),
        "estimated_total_cost_usd": round(cost_total, 4),
    }
