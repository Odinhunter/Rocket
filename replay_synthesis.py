"""Replay the synthesis layers (L2 → L3 → L4) on a stored run, skipping L1.

Useful for prompt iteration on the synthesis stack without paying L1's
agent-call cost. Reads the stored transcripts.json (or rebuilds it from
agent_calls/ artifacts) and the stored target_classification.json, then
re-runs L2 fan-out → L3 → L4 with the *current* prompts and code.

Usage:
    python replay_synthesis.py <run_dir>

`run_dir` is the full path to a run's directory, e.g.
`runs/internal/default/20260513_000634_seed71_boat_airdopes_prime_512_1_199`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")

from agent.config import AssetSpec, RunConfig
from agent.entities import AudienceSpec
from agent.panel import PanelAgent
from agent.projection_l35 import project_funnel
from agent.schema import AgentTranscript, validate_report
from agent.synthesis_l2 import synthesize_disposition_async
from agent.synthesis_l2_v2 import synthesize_segment_async
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l3_v2 import synthesize_population_v2
from agent.synthesis_l4 import synthesize_memo
from agent.synthesis_l4_v2 import synthesize_memo_v2
from agent.synthesis_types import TargetClassification
from agent.telemetry import (
    current_account_id,
    current_brand_profile_id,
    current_run_id,
)


def _load_transcripts(run_dir: Path) -> list[AgentTranscript]:
    transcripts_path = run_dir / "transcripts.json"
    if transcripts_path.exists():
        raw = json.loads(transcripts_path.read_text())
        return [AgentTranscript.from_dict(d) for d in raw]

    agent_calls_dir = run_dir / "agent_calls"
    if not agent_calls_dir.exists():
        raise FileNotFoundError(
            f"Neither {transcripts_path} nor {agent_calls_dir} exist. "
            "Cannot replay without L1 outputs."
        )

    encoding_by_aid: dict[int, dict] = {}
    reflection_by_aid: dict[int, dict] = {}
    for p in agent_calls_dir.glob("*.json"):
        data = json.loads(p.read_text())
        aid = int(data["agent_id"])
        if data["phase"] == "encoding":
            encoding_by_aid[aid] = data
        elif data["phase"] == "reflection":
            reflection_by_aid[aid] = data

    transcripts: list[AgentTranscript] = []
    for aid in sorted(set(encoding_by_aid) & set(reflection_by_aid)):
        e = encoding_by_aid[aid]
        r = reflection_by_aid[aid]
        transcripts.append(AgentTranscript(
            agent_id=aid,
            disposition_label=e["disposition_label"],
            context_label=e["context_label"],
            seed_idx=int(e.get("seed_idx", 0) or 0),
            encoding_text=e["response_text"],
            reflection_text=r["response_text"],
        ))
    return transcripts


def _config_from_run_json(run_dir: Path) -> RunConfig:
    raw = json.loads((run_dir / "run.json").read_text())
    cfg_dict = raw["config"]
    return RunConfig(
        asset=AssetSpec(
            image_path=cfg_dict["asset"]["image_path"],
            label=cfg_dict["asset"]["label"],
        ),
        archetype=cfg_dict["archetype"],
        category=cfg_dict["category"],
        account_id=cfg_dict["account_id"],
        brand_profile_id=cfg_dict["brand_profile_id"],
        dispositions_per_run=cfg_dict["dispositions_per_run"],
        contexts_per_run=cfg_dict["contexts_per_run"],
        seeds_per_cell=cfg_dict["seeds_per_cell"],
        max_concurrent_agents=cfg_dict.get("max_concurrent_agents", 20),
        protocol_version=cfg_dict.get("protocol_version", "rocket-1.0.0"),
        disposition_version=cfg_dict.get("disposition_version", "auto"),
        model_versions=dict(cfg_dict["model_versions"]),
        seed=cfg_dict["seed"],
    )


def _config_from_run_json_v2(run_dir: Path) -> RunConfig:
    raw = json.loads((run_dir / "run.json").read_text())
    c = raw["config"]
    audience = c.get("audience_spec")
    return RunConfig(
        asset=AssetSpec(
            image_path=c["asset"]["image_path"], label=c["asset"]["label"]
        ),
        archetype=c["archetype"],
        category=c["category"],
        account_id=c["account_id"],
        brand_profile_id=c["brand_profile_id"],
        max_concurrent_agents=c.get("max_concurrent_agents", 4),
        protocol_version=c.get("protocol_version", "rocket-2.0.0"),
        model_versions=dict(c["model_versions"]),
        seed=c["seed"],
        audience_spec=AudienceSpec.from_dict(audience) if audience else None,
        segment_granularity=c.get("segment_granularity", "disposition_chaos_band"),
        baseline_funnel=c.get("baseline_funnel"),
        library_id=c.get("library_id", ""),
        audience_id=c.get("audience_id", ""),
    )


async def _replay_v2(run_dir: Path) -> None:
    """Replay the v2 synthesis chain: L2 v2 -> L3 v2 -> L3.5 -> L4 v2."""
    config = _config_from_run_json_v2(run_dir)
    transcripts = _load_transcripts(run_dir)
    panel = [
        PanelAgent.from_dict(d)
        for d in json.loads((run_dir / "panel.json").read_text())
    ]
    print(f"# v2 replay — {len(transcripts)} transcripts, {len(panel)} panel agents")

    current_account_id.set(config.account_id)
    current_brand_profile_id.set(config.brand_profile_id)
    current_run_id.set(run_dir.name + "_replay")

    tc = TargetClassification.from_dict(
        json.loads((run_dir / "target_classification.json").read_text())
    )

    # Group transcripts by segment_key via the panel.
    segment_of = {a.agent_id: a.segment_key for a in panel}
    by_segment: dict[str, list[AgentTranscript]] = defaultdict(list)
    for t in transcripts:
        by_segment[segment_of[t.agent_id]].append(t)

    t0 = time.time()
    l2_summaries = await asyncio.gather(*[
        synthesize_segment_async(label, ts, config)
        for label, ts in sorted(by_segment.items())
    ])
    l2_summaries = sorted(l2_summaries, key=lambda s: s.segment_label)
    print(f"# L2 v2 fan-out: {len(l2_summaries)} segment summaries in {time.time()-t0:.1f}s")

    t0 = time.time()
    l3 = await asyncio.to_thread(
        synthesize_population_v2, l2_summaries, tc, config
    )
    print(f"# L3 v2 in {time.time()-t0:.1f}s")

    projection = project_funnel(l3, config.baseline_funnel)
    print(f"# L3.5 projection (basis: {projection.overall.basis})")

    t0 = time.time()
    provisional = sorted(
        s.disposition_label for s in l2_summaries
    )  # best-effort; replay has no library
    report = await asyncio.to_thread(
        synthesize_memo_v2, l3, tc, projection, config,
    )
    validate_report(report)
    print(f"# L4 v2 in {time.time()-t0:.1f}s")

    print()
    print("=" * 78)
    print(f"REPLAY (v2) — verdict: {report.verdict} confidence={report.confidence}")
    print("=" * 78)
    print(f"bet_ranking ({len(report.bet_ranking)} bets):")
    for i, bet in enumerate(report.bet_ranking, 1):
        print(f"  {i}. {bet}")
    out_path = run_dir / "replay_report.json"
    out_path.write_text(report.to_json())
    print(f"\n# Replay report saved to {out_path}")


async def _replay(run_dir: Path) -> None:
    # v2 runs carry a panel.json — dispatch to the v2 synthesis chain.
    if (run_dir / "panel.json").exists():
        await _replay_v2(run_dir)
        return

    config = _config_from_run_json(run_dir)
    transcripts = _load_transcripts(run_dir)
    print(f"# Loaded {len(transcripts)} transcripts from {run_dir}")

    current_account_id.set(config.account_id)
    current_brand_profile_id.set(config.brand_profile_id)
    current_run_id.set(run_dir.name + "_replay")

    tc_path = run_dir / "target_classification.json"
    if not tc_path.exists():
        raise FileNotFoundError(
            f"Cannot replay without target_classification.json at {tc_path}. "
            "Re-run the original pipeline first."
        )
    tc = TargetClassification.from_dict(json.loads(tc_path.read_text()))
    print(f"# target: within={tc.within_target_labels()} outside={tc.outside_target_labels()}")

    by_disp: dict[str, list[AgentTranscript]] = defaultdict(list)
    for t in transcripts:
        by_disp[t.disposition_label].append(t)

    t0 = time.time()
    l2_summaries = await asyncio.gather(*[
        synthesize_disposition_async(d, ts, config) for d, ts in by_disp.items()
    ])
    l2_summaries = sorted(l2_summaries, key=lambda s: s.disposition_label)
    print(f"# L2 fan-out: {len(l2_summaries)} summaries in {time.time()-t0:.1f}s")

    t0 = time.time()
    l3 = await asyncio.to_thread(synthesize_population, l2_summaries, tc, config)
    print(f"# L3 in {time.time()-t0:.1f}s")

    t0 = time.time()
    report = await asyncio.to_thread(synthesize_memo, l3, tc, config)
    validate_report(report)
    print(f"# L4 in {time.time()-t0:.1f}s")

    print()
    print("=" * 78)
    print(f"REPLAY VERDICT: {report.verdict} confidence={report.confidence}")
    print("=" * 78)
    for i, c in enumerate(report.top_3_changes, 1):
        print(f"  {i}. {c.change}")
    print(f"\nverbatim_consumer_voice: {len(report.verbatim_consumer_voice)}")

    out_path = run_dir / "replay_report.json"
    out_path.write_text(report.to_json())
    print(f"\n# Replay report saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay L2->L3->L4 on a stored run.")
    parser.add_argument("run_dir", type=Path, help="Path to a runs/<account>/<brand>/<run_id>/ directory.")
    args = parser.parse_args()

    if not args.run_dir.exists():
        print(f"ERROR: run_dir not found: {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_replay(args.run_dir))


if __name__ == "__main__":
    main()
