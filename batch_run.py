"""Rocket Creative Read — CLI entry point.

Thin wrapper around RunService. Builds a RunConfig from CLI args, runs
the pipeline, prints the report.

Usage:
    python batch_run.py --asset assets/boat_ad.png
    python batch_run.py --asset assets/boat_ad.png --dispositions 5 --contexts 3 --seeds 1
    python batch_run.py --asset assets/boat_ad.png --account acme --brand-profile boat
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

from agent.config import AssetSpec, RunConfig
from agent.run_service import RunService
from agent.telemetry import telemetry_summary, run_dir


_DEFAULT_ARCHETYPE = "urban_indian_male_22_30"
_DEFAULT_CATEGORY = "personal_audio"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rocket Creative Read — single-asset bundled-protocol pipeline.",
    )
    parser.add_argument("--asset", required=True, help="Path to the creative asset (.png / .jpg / .webp).")
    parser.add_argument("--asset-label", default=None,
                        help="Human caption for the asset (used in headers and quotes). Defaults to filename.")
    parser.add_argument("--archetype", default=_DEFAULT_ARCHETYPE)
    parser.add_argument("--category", default=_DEFAULT_CATEGORY)
    parser.add_argument("--dispositions", type=int, default=5,
                        help="Dispositions per run (D). Default 5. Cap is 7 per Brand Profile.")
    parser.add_argument("--contexts", type=int, default=3,
                        help="Contexts per run (C). Default 3.")
    parser.add_argument("--seeds", type=int, default=1,
                        help="Seeds per cell (S). Default 1.")
    parser.add_argument("--account", default="internal", help="Account ID (multi-tenant). Default 'internal'.")
    parser.add_argument("--brand-profile", default="default",
                        help="Brand Profile ID. Default 'default'.")
    parser.add_argument("--max-concurrent", type=int, default=20,
                        help="Max parallel agents. Default 20.")
    parser.add_argument("--seed", type=int, default=71,
                        help="Sampling seed for which dispositions/contexts are drawn.")
    parser.add_argument("--resume", metavar="RUN_ID", default=None,
                        help="Resume an existing run by run_id; loads completed agent_calls "
                             "from disk and only fires missing ones. Requires the same "
                             "--seed, --dispositions, --contexts, --seeds, --asset to "
                             "reproduce the same matrix.")
    args = parser.parse_args()

    asset_path = Path(args.asset)
    if not asset_path.exists():
        print(f"ERROR: asset not found at {asset_path}", file=sys.stderr)
        sys.exit(1)

    asset_label = args.asset_label or asset_path.stem.replace("_", " ").title()

    config = RunConfig(
        asset=AssetSpec(image_path=str(asset_path), label=asset_label),
        archetype=args.archetype,
        category=args.category,
        account_id=args.account,
        brand_profile_id=args.brand_profile,
        dispositions_per_run=args.dispositions,
        contexts_per_run=args.contexts,
        seeds_per_cell=args.seeds,
        max_concurrent_agents=args.max_concurrent,
        seed=args.seed,
    )
    config.validate()

    print(f"# Rocket Creative Read")
    print(f"# asset: {asset_path}  ({asset_label})")
    print(f"# archetype: {config.archetype} / category: {config.category}")
    print(f"# agents: D={config.dispositions_per_run} × C={config.contexts_per_run} × "
          f"S={config.seeds_per_cell} = {config.total_agents()}")
    print(f"# account / brand_profile: {config.account_id} / {config.brand_profile_id}")
    print(f"# concurrency: {config.max_concurrent_agents}")
    print()

    report = RunService.run(config, resume_run_id=args.resume)

    print()
    print("=" * 78)
    print(f"VERDICT: {report.verdict}   confidence: {report.confidence}/100")
    print("=" * 78)

    print(f"\nTarget reach:")
    for d in report.target_match.reached:
        print(f"  ✓ {d.disposition}  ({d.classification})")
    print(f"\nTarget missed:")
    for d in report.target_match.missed:
        print(f"  ✗ {d.disposition}  ({d.classification})")

    if report.top_3_changes:
        print(f"\nTOP 3 CHANGES:")
        for i, c in enumerate(report.top_3_changes, 1):
            print(f"\n  {i}. {c.change}")
            print(f"     why: {c.why}")
            print(f"     within-target corroboration: {c.within_target_corroboration}")
            for q in c.evidence_quotes:
                print(f"     ↪ \"{q.quote}\"  — {q.disposition} (R{q.round}, {q.context})")

    if report.strengths_to_preserve:
        print(f"\nSTRENGTHS TO PRESERVE:")
        for s in report.strengths_to_preserve:
            print(f"\n  • {s.strength}")
            for q in s.evidence_quotes:
                print(f"    ↪ \"{q.quote}\"  — {q.disposition} (R{q.round}, {q.context})")

    print(f"\nCONTEXT-FIT MAP:")
    for ctx, entry in report.context_fit_map.items():
        print(f"  [{entry.verdict:>7}]  {ctx}")
        print(f"            {entry.friction_summary}")

    print(f"\nCONSUMER VOICE ({len(report.verbatim_consumer_voice)} quotes):")
    for q in report.verbatim_consumer_voice:
        print(f"  \"{q.quote}\"")
        print(f"    — {q.disposition}, R{q.round}, {q.context}\n")

    # Telemetry summary — find the run we just produced.
    base = Path("runs") / config.account_id / config.brand_profile_id
    if base.exists():
        latest = sorted(base.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if latest:
            run_id = latest[0].name
            print()
            print(telemetry_summary(run_id, account_id=config.account_id, brand_profile_id=config.brand_profile_id))
            print(f"\n# Artifacts: {latest[0]}/")


if __name__ == "__main__":
    main()
