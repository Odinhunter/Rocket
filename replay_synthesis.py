"""Replay the v2 synthesis layers (L2 → L3 → L3.5 → L4) on a stored run.

Useful for prompt iteration on the synthesis stack without paying L1's
agent-call cost. Reads the stored transcripts.json (or rebuilds it from
agent_calls/ artifacts), panel.json, and target_classification.json, then
re-runs L2 fan-out → L3 → L3.5 projection → L4 with the *current* prompts
and code.

Usage:
    python replay_synthesis.py <run_dir>

`run_dir` is the full path to a v2 run's directory, e.g.
`runs/internal/default/20260517_220643_seed71_boat_ad/`.
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

from agent.config import AssetSpec, CreativeInputs, RunConfig
from agent.entities import AudienceSpec
from agent.panel import PanelAgent
from agent.projection_l35 import project_funnel
from agent.schema import AgentTranscript, validate_report
from agent.synthesis_l2 import synthesize_segment_async
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import synthesize_memo
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
        creative_inputs=CreativeInputs.from_dict(c.get("creative_inputs")),
        declared_targeting=c.get("declared_targeting", ""),
    )


async def _replay(run_dir: Path) -> None:
    if not (run_dir / "panel.json").exists():
        raise FileNotFoundError(
            f"{run_dir}/panel.json not found. This replay tool only supports "
            "rocket-2.0.0 runs (which carry a panel). v1 runs are no longer "
            "replayable after the Phase 6 cutover."
        )

    config = _config_from_run_json(run_dir)
    transcripts = _load_transcripts(run_dir)
    panel = [
        PanelAgent.from_dict(d)
        for d in json.loads((run_dir / "panel.json").read_text())
    ]
    print(f"# replay — {len(transcripts)} transcripts, {len(panel)} panel agents")

    current_account_id.set(config.account_id)
    current_brand_profile_id.set(config.brand_profile_id)
    current_run_id.set(run_dir.name + "_replay")

    tc = TargetClassification.from_dict(
        json.loads((run_dir / "target_classification.json").read_text())
    )

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
    print(f"# L2 fan-out: {len(l2_summaries)} segment summaries in {time.time()-t0:.1f}s")

    t0 = time.time()
    l3 = await asyncio.to_thread(synthesize_population, l2_summaries, tc, config)
    print(f"# L3 in {time.time()-t0:.1f}s")

    projection = project_funnel(
        l3, config.baseline_funnel, provided_inputs=config.provided_inputs()
    )
    print(f"# L3.5 projection (basis: {projection.overall.basis})")

    t0 = time.time()
    report = await asyncio.to_thread(
        synthesize_memo, l3, tc, projection, config,
    )
    validate_report(report)
    print(f"# L4 in {time.time()-t0:.1f}s")

    print()
    print("=" * 78)
    print(f"REPLAY — verdict: {report.verdict} confidence={report.confidence}")
    print("=" * 78)
    print(f"bet_ranking ({len(report.bet_ranking)} bets):")
    for i, bet in enumerate(report.bet_ranking, 1):
        print(f"  {i}. {bet}")
    out_path = run_dir / "replay_report.json"
    out_path.write_text(report.to_json())
    print(f"\n# Replay report saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay L2->L3->L3.5->L4 on a stored run.")
    parser.add_argument("run_dir", type=Path, help="Path to a runs/<account>/<brand>/<run_id>/ directory.")
    args = parser.parse_args()

    if not args.run_dir.exists():
        print(f"ERROR: run_dir not found: {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_replay(args.run_dir))


if __name__ == "__main__":
    main()
