"""Population-protocol v2: within-cell replication + comparative anchoring + structured synthesis.

Architecture
------------
Sampling is cell-based: D dispositions × C contexts × S seeds. seed_idx is a
*label* for pairing/replication, not a deterministic control — Anthropic SDK
has no `seed` parameter, so within-cell variance comes from API stochasticity
at temperature=1.0 at runtime.

Each agent runs the 6-round protocol on each stimulus as INDEPENDENT
conversations (no `prior.messages` cross-pollination between focal and
anchor). Threading them would anchor scoring to whichever stimulus came
first; cold re-prompt is the right interpretation.

Per round, all (agent × stimulus) conversations fire in parallel via
asyncio.gather + asyncio.to_thread wrapping the sync run_agent. Order of
firing within each round is randomized to avoid time-skew bias under the
ITPM-throttled semaphore.

Throttling: SEMAPHORE=2, INTER_ROUND_SLEEP_S=30, hand-tuned to org's 30K
ITPM ceiling. At 189-agent production scale (378 conversations × 6 rounds
= 2268 calls) these constants must be recomputed from measured tokens-per-
call against ITPM headroom. Per-conversation transcripts to disk and
synthesis Opus-call chunking also become mandatory at that scale; flagged
here for future work, not solved.

Runtime (validation 9-agent run): ~10-12 min for 18 conversations × 6
rounds + synthesis (4 Opus calls).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")

import anthropic

from agent.persistence import (
    current_run_id,
    dump_checkpoint,
    dump_run,
    load_checkpoint,
    make_run_id,
    telemetry_summary,
)
from agent.runner import RunResult, run_agent
from agent.synthesis import (
    format_population_report,
    format_target_classification,
    identify_target_audience,
    synthesize_population_report,
    synthesize_strategic_critique,
)
from archetypes.context import list_contexts
from archetypes.disposition import list_dispositions

ARCHETYPE = "urban_indian_male_22_30"
CATEGORY = "chocolate"

# Cell config: D × C × S. Concept-test = 7 × 1 × 1 = 7 (matches original
# Silk run; calibration check on the new target-aware synthesis against
# the prior population-pattern critique-mode memo).
DISPOSITIONS_PER_RUN = 7
CONTEXTS_PER_RUN = 1
SEEDS_PER_CELL = 1

STIMULI = {
    "focal":  {"image_path": "assets/cadbury_ad.png", "label": "Cadbury Dairy Milk Silk — How far will you go for love?"},
    "anchor": {"image_path": "assets/fr_ad.png",      "label": "Ferrero Rocher Valentine's Day — Add your golden touch"},
}

SEED = 71
SEMAPHORE = 2
INTER_ROUND_SLEEP_S = 30

ROUND_LABELS = {
    1: "gut reaction",
    2: "comprehension audit",
    3: "emotional mapping",
    4: "stickiness (two days later)",
    5: "social calculus",
    6: "purchase friction",
}

_sem: asyncio.Semaphore | None = None

_log = logging.getLogger(__name__)


async def _run_agent_with_retry(**kwargs) -> RunResult | None:
    """Wrap run_agent with one explicit RateLimitError retry.

    The Anthropic client is constructed with max_retries=5 (runner.py), giving
    ~32s of cumulative SDK backoff. If we still hit RateLimitError after that,
    the ITPM bucket likely needs another full window to clear — sleep 60-90s
    (with jitter, to de-synchronize parallel conversations) and try once more.
    Second RateLimitError gives up; the conversation is dropped from the run.
    """
    try:
        return await asyncio.to_thread(run_agent, **kwargs)
    except anthropic.RateLimitError as exc:
        wait = 60 + random.uniform(0, 30)
        _log.warning(
            "RateLimitError after SDK retries (run_agent kwargs round=%s "
            "image=%s); sleeping %.1fs before one more attempt: %s",
            kwargs.get("round_num"), kwargs.get("image_path"), wait, exc,
        )
        await asyncio.sleep(wait)
        return await asyncio.to_thread(run_agent, **kwargs)


def build_agent_specs(rng: random.Random) -> list[dict]:
    disp_pool = list_dispositions(ARCHETYPE, CATEGORY)
    ctx_pool = list_contexts(ARCHETYPE)
    chosen_disps = rng.sample(disp_pool, DISPOSITIONS_PER_RUN)
    chosen_ctxs = rng.sample(ctx_pool, CONTEXTS_PER_RUN)

    specs: list[dict] = []
    agent_id = 0
    for disp in chosen_disps:
        for ctx in chosen_ctxs:
            for seed_idx in range(SEEDS_PER_CELL):
                specs.append({
                    "agent_id": agent_id,
                    "disposition": disp,
                    "context": ctx,
                    "seed_idx": seed_idx,
                    "cell_key": (disp[0], ctx[0]),
                })
                agent_id += 1
    return specs


async def fire_round_1(agent_id, stim_id, disp, ctx, image_path):
    async with _sem:
        try:
            result = await _run_agent_with_retry(
                archetype=ARCHETYPE,
                ad_content="",
                round_num=1,
                image_path=image_path,
                disposition=disp,
                context=ctx,
                agent_id=agent_id,
            )
            return (agent_id, stim_id), result, None
        except Exception as exc:
            return (agent_id, stim_id), None, exc


async def fire_round(agent_id, stim_id, prior, round_num):
    async with _sem:
        try:
            result = await _run_agent_with_retry(
                archetype=ARCHETYPE,
                ad_content="",
                round_num=round_num,
                prior=prior,
                agent_id=agent_id,
            )
            return (agent_id, stim_id), result, None
        except Exception as exc:
            return (agent_id, stim_id), None, exc


def _check_stimulus_assets() -> None:
    missing = []
    for stim_id, cfg in STIMULI.items():
        if not os.path.exists(cfg["image_path"]):
            missing.append(f"  {stim_id}: {cfg['image_path']}  ({cfg['label']})")
    if missing:
        raise FileNotFoundError(
            "Missing stimulus image(s):\n" + "\n".join(missing) +
            "\n\nDrop the missing image(s) at the path(s) above and re-run."
        )


def _build_run_config() -> dict:
    """Snapshot the module-level config constants for persistence + resume."""
    return {
        "archetype": ARCHETYPE,
        "category": CATEGORY,
        "dispositions_per_run": DISPOSITIONS_PER_RUN,
        "contexts_per_run": CONTEXTS_PER_RUN,
        "seeds_per_cell": SEEDS_PER_CELL,
        "stimuli": {sid: dict(cfg) for sid, cfg in STIMULI.items()},
        "seed": SEED,
        "semaphore": SEMAPHORE,
        "inter_round_sleep_s": INTER_ROUND_SLEEP_S,
    }


async def main():
    global _sem
    _sem = asyncio.Semaphore(SEMAPHORE)

    parser = argparse.ArgumentParser(description="Population-protocol v2 batch run.")
    parser.add_argument(
        "--resume", metavar="RUN_ID",
        help="Resume an existing run from its checkpoint (skip completed rounds).",
    )
    args = parser.parse_args()

    _check_stimulus_assets()

    if args.resume:
        ck = load_checkpoint(args.resume)
        run_id = args.resume
        config = ck["config"]
        specs = ck["specs"]
        histories = ck["histories"]
        failures_in = ck["failures"]
        failures: dict[tuple[int, str], list[tuple[int, str]]] = defaultdict(list)
        for k, v in failures_in.items():
            failures[k] = list(v)
        start_round = ck["current_round"] + 1
        print(f"# Resuming run_id={run_id} from round {start_round}")
    else:
        config = _build_run_config()
        run_id = make_run_id(SEED, STIMULI["focal"]["label"])
        rng = random.Random(SEED)
        specs = build_agent_specs(rng)
        pairs_all = [(spec["agent_id"], stim_id) for spec in specs for stim_id in STIMULI]
        histories = {k: [] for k in pairs_all}
        failures = defaultdict(list)
        start_round = 1
        print(f"# Starting fresh run_id={run_id}")

    current_run_id.set(run_id)

    n_agents = len(specs)
    pairs_all = [(spec["agent_id"], stim_id) for spec in specs for stim_id in STIMULI]
    n_conv = len(pairs_all)

    # Ensure histories has all keys (resume may load a subset if a future
    # spec_change scenario ever happens; harmless if already present).
    for k in pairs_all:
        histories.setdefault(k, [])

    print(f"# Cells: D={config['dispositions_per_run']} × C={config['contexts_per_run']} × S={config['seeds_per_cell']} = {n_agents} agents")
    print(f"# Stimuli: {' + '.join(s['label'] for s in STIMULI.values())} ({len(STIMULI)} per agent)")
    print(f"# Total conversations: {n_conv} × 6 rounds = {n_conv * 6} API calls")
    print(f"# Concurrency: {SEMAPHORE} · drain: {INTER_ROUND_SLEEP_S}s · run_id: {run_id}")
    print(f"# NOTE: seed_idx is a label, not deterministic. Variance from temp=1.0 stochasticity.")
    print()
    print("Agent specs:")
    for spec in specs:
        d, c = spec["disposition"][0], spec["context"][0]
        print(f"  agent {spec['agent_id']:02d}: disp={d:38s} ctx={c:25s} seed_idx={spec['seed_idx']}")
    print()

    # Initial run.json snapshot (config only — synthesis fills in later).
    dump_run(run_id, config=config)

    # ---- ROUND 1 ----
    if start_round <= 1:
        print("=" * 78)
        print(f"ROUND 1 · {ROUND_LABELS[1]}  ·  firing {n_conv} conversations in parallel")
        print("=" * 78)

        rng_shuffle = random.Random(SEED + 1)
        pairs = pairs_all[:]
        rng_shuffle.shuffle(pairs)

        coros = []
        for agent_id, stim_id in pairs:
            spec = specs[agent_id]
            coros.append(fire_round_1(
                agent_id, stim_id,
                spec["disposition"], spec["context"],
                STIMULI[stim_id]["image_path"],
            ))
        results = await asyncio.gather(*coros)
        results.sort(key=lambda r: r[0])

        for (agent_id, stim_id), result, exc in results:
            spec = specs[agent_id]
            print()
            print(
                f"[agent {agent_id:02d}] [{stim_id}] disp={spec['disposition'][0]} | "
                f"ctx={spec['context'][0]} | seed_idx={spec['seed_idx']}"
            )
            if exc is not None:
                print(f"  !! FAILED: {type(exc).__name__}: {exc}")
                failures[(agent_id, stim_id)].append((1, f"{type(exc).__name__}: {exc}"))
                continue
            if result is None:
                print("  !! FAILED: run_agent returned None")
                failures[(agent_id, stim_id)].append((1, "returned None"))
                continue
            histories[(agent_id, stim_id)].append(result)
            print(result.output)

        dump_checkpoint(
            run_id, config=config, specs=specs,
            histories=histories, failures=dict(failures), current_round=1,
        )

    # ---- ROUNDS 2-6 ----
    for round_num in range(max(start_round, 2), 7):
        print()
        print(f"  ... draining ITPM window for {INTER_ROUND_SLEEP_S}s ...")
        await asyncio.sleep(INTER_ROUND_SLEEP_S)
        print()

        active_pairs = [k for k in pairs_all if len(histories[k]) == round_num - 1]
        rng_shuffle = random.Random(SEED + round_num)
        rng_shuffle.shuffle(active_pairs)
        dropped = [k for k in pairs_all if len(histories[k]) < round_num - 1]

        print("=" * 78)
        print(
            f"ROUND {round_num} · {ROUND_LABELS[round_num]}  ·  "
            f"firing {len(active_pairs)} conversations in parallel"
        )
        for agent_id, stim_id in sorted(dropped):
            last_fail = failures.get((agent_id, stim_id), [(None, "?")])[-1]
            print(
                f"  [skipping agent {agent_id:02d} {stim_id} — "
                f"failed at round {last_fail[0]}: {last_fail[1]}]"
            )
        print("=" * 78)

        if not active_pairs:
            print("\n  no active conversations remain. Stopping.")
            break

        coros = [
            fire_round(aid, sid, histories[(aid, sid)][-1], round_num)
            for aid, sid in active_pairs
        ]
        results = await asyncio.gather(*coros)
        results.sort(key=lambda r: r[0])

        for (agent_id, stim_id), result, exc in results:
            spec = specs[agent_id]
            print()
            print(
                f"[agent {agent_id:02d}] [{stim_id}] disp={spec['disposition'][0]} | "
                f"ctx={spec['context'][0]} | seed_idx={spec['seed_idx']}"
            )
            if exc is not None:
                print(f"  !! FAILED: {type(exc).__name__}: {exc}")
                failures[(agent_id, stim_id)].append((round_num, f"{type(exc).__name__}: {exc}"))
                continue
            if result is None:
                print("  !! FAILED: run_agent returned None (R3 JSON retries exhausted)")
                failures[(agent_id, stim_id)].append((round_num, "returned None"))
                continue
            histories[(agent_id, stim_id)].append(result)
            if round_num == 3:
                print(json.dumps(result.parsed, indent=2))
            else:
                print(result.output)

        dump_checkpoint(
            run_id, config=config, specs=specs,
            histories=histories, failures=dict(failures), current_round=round_num,
        )

    # ---- COMPLETION SUMMARY ----
    print()
    print("=" * 78)
    print("ROUND-BY-ROUND COMPLETION")
    print("=" * 78)
    completed = sum(1 for h in histories.values() if len(h) == 6)
    print(f"  conversations completing all 6 rounds: {completed}/{n_conv}")
    for k in sorted(failures.keys()):
        for r, msg in failures[k]:
            print(f"  agent {k[0]:02d} [{k[1]}] · round {r} · {msg}")
    if not failures:
        print("  no failures across the batch.")

    # ---- SYNTHESIS ----
    print()
    print("=" * 78)
    print("RUNNING SYNTHESIS  ·  4 Opus per-round calls + numeric/categorical")
    print("=" * 78)
    report = synthesize_population_report(
        histories=dict(histories),
        failures=dict(failures),
        agent_specs=specs,
        focal_label=STIMULI["focal"]["label"],
        anchor_label=STIMULI["anchor"]["label"],
    )
    print()
    print(format_population_report(report))
    dump_run(run_id, config=config, population_report=report)

    # ---- TARGET CLASSIFICATION (vision Opus call, no population data) ----
    print()
    print("=" * 78)
    print("TARGET IDENTIFICATION  ·  vision Opus call on focal+anchor")
    print("=" * 78)
    target_cls = identify_target_audience(
        report,
        focal_label=STIMULI["focal"]["label"],
        anchor_label=STIMULI["anchor"]["label"],
        focal_image_path=STIMULI["focal"]["image_path"],
        anchor_image_path=STIMULI["anchor"]["image_path"],
        category=CATEGORY,
        archetype=ARCHETYPE,
    )
    print()
    print(format_target_classification(target_cls))
    dump_run(
        run_id, config=config, population_report=report,
        target_classification=target_cls,
    )

    # ---- STRATEGIST MEMO (single Opus prose call) ----
    print()
    print("=" * 78)
    print("STRATEGIST MEMO  ·  Opus prose synthesis over population + target")
    print("=" * 78)
    critique = synthesize_strategic_critique(
        report,
        focal_label=STIMULI["focal"]["label"],
        anchor_label=STIMULI["anchor"]["label"],
        category=CATEGORY,
        target_classification=target_cls,
    )
    print(f"\n[model: {critique.model} · verdict: {critique.verdict_band or 'n/a'}]\n")
    print(critique.memo)
    dump_run(
        run_id, config=config, population_report=report,
        target_classification=target_cls, strategic_critique=critique,
    )

    # ---- TELEMETRY SUMMARY ----
    print()
    print(telemetry_summary(run_id))
    print()
    print(f"# Run artifacts at runs/{run_id}/")


if __name__ == "__main__":
    asyncio.run(main())
