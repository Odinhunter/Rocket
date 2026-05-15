"""Rocket Creative Read — CLI entry point.

Two modes:

  v1 (rocket-1.3.0) — archetype/category sampling:
    python batch_run.py --asset assets/boat_ad.png
    python batch_run.py --asset assets/boat_ad.png --dispositions 5 --contexts 3

  v2 (rocket-2.0.0) — two-phase run against a composed AudienceSpec:
    python batch_run.py --asset assets/boat_ad.png \\
        --audience-spec specs/cold_traffic.json \\
        --category personal_audio --account acme --brand-profile boat
    Add --yes to skip the confirmation prompt (auto-confirm).

The v2 path resolves the AudienceSpec against the Brand Profile's
disposition library (which must already exist on disk under
runs/<account>/<brand>/entities/), runs prepare() -> shows the
confirmation surface -> commit() (which debits the credit).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

from agent.config import AssetSpec, RunConfig
from agent.entities import AudienceSpec
from agent.run_service import RunService
from agent.run_service_v2 import RunPreparation, RunServiceV2
from agent.schema import Report
from agent.telemetry import run_dir, telemetry_summary

_DEFAULT_ARCHETYPE = "urban_indian_male_22_30"
_DEFAULT_CATEGORY = "personal_audio"


# ---- Report printing ----


def _print_target_and_changes(report: Report) -> None:
    print("\nTarget reach:")
    for d in report.target_match.reached:
        print(f"  ✓ {d.disposition}  ({d.classification})")
    print("\nTarget missed:")
    for d in report.target_match.missed:
        print(f"  ✗ {d.disposition}  ({d.classification})")

    if report.top_3_changes:
        print("\nTOP 3 CHANGES:")
        for i, c in enumerate(report.top_3_changes, 1):
            print(f"\n  {i}. {c.change}")
            print(f"     why: {c.why}")
            print(f"     within-target corroboration: {c.within_target_corroboration}")
            for q in c.evidence_quotes:
                print(f"     ↪ \"{q.quote}\"  — {q.disposition} (R{q.round}, {q.context})")

    if report.strengths_to_preserve:
        print("\nSTRENGTHS TO PRESERVE:")
        for s in report.strengths_to_preserve:
            print(f"\n  • {s.strength}")
            for q in s.evidence_quotes:
                print(f"    ↪ \"{q.quote}\"  — {q.disposition} (R{q.round}, {q.context})")

    print("\nCONTEXT-FIT MAP:")
    for ctx, entry in report.context_fit_map.items():
        print(f"  [{entry.verdict:>7}]  {ctx}")
        print(f"            {entry.friction_summary}")

    print(f"\nCONSUMER VOICE ({len(report.verbatim_consumer_voice)} quotes):")
    for q in report.verbatim_consumer_voice:
        print(f"  \"{q.quote}\"")
        print(f"    — {q.disposition}, R{q.round}, {q.context}\n")


def _print_v1_report(report: Report) -> None:
    print()
    print("=" * 78)
    print(f"VERDICT: {report.verdict}   confidence: {report.confidence}/100")
    print("=" * 78)
    if report.methodology_flags:
        print(f"\nMETHODOLOGY FLAGS ({len(report.methodology_flags)}):")
        for flag in report.methodology_flags:
            print(f"  ⚑ {flag}")
    _print_target_and_changes(report)


def _print_v2_report(report: Report) -> None:
    """v2 leads with the bet ranking — the brand-manager headline. Verdict,
    confidence and the funnel projection are supporting metadata."""
    print()
    print("=" * 78)
    print("STRATEGIC BET RANKING  (highest expected marketing-ROI payoff first)")
    print("=" * 78)
    for i, bet in enumerate(report.bet_ranking, 1):
        print(f"\n  {i}. {bet}")

    fp = report.funnel_projection
    if fp is not None:
        o = fp.overall
        print("\n" + "-" * 78)
        print(f"PROJECTED FUNNEL  (overall — basis: {o.basis})")
        print("-" * 78)
        for stage, rate, band in (
            ("stop", o.stop_rate, o.stop_band),
            ("click", o.click_rate, o.click_band),
            ("visit", o.visit_rate, o.visit_band),
            ("convert", o.convert_rate, o.convert_band),
        ):
            print(f"  {stage:>8}: {rate*100:6.3f}%   "
                  f"[{band[0]*100:.3f}% – {band[1]*100:.3f}%]")
        print(f"\n  {fp.calibration_note}")
        if fp.by_segment:
            print("\n  By segment (convert rate):")
            for seg in fp.by_segment:
                print(f"    {seg.segment_label:<42} "
                      f"{seg.funnel_rates.convert_rate*100:6.3f}%")

    print("\n" + "-" * 78)
    print(f"METHODOLOGY  —  verdict: {report.verdict}   "
          f"confidence: {report.confidence}/100")
    if report.methodology_flags:
        print(f"  flags: {', '.join(report.methodology_flags)}")
    if report.provisional_dispositions:
        print(f"  provisional dispositions (awaiting team review): "
              f"{', '.join(report.provisional_dispositions)}")
    print("-" * 78)
    _print_target_and_changes(report)


def _print_telemetry(config: RunConfig) -> None:
    base = Path("runs") / config.account_id / config.brand_profile_id
    if not base.exists():
        return
    latest = sorted(base.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest = [p for p in latest if p.is_dir() and p.name != "library_renders"
              and p.name != "entities"]
    if latest:
        run_id = latest[0].name
        print()
        print(telemetry_summary(
            run_id, account_id=config.account_id,
            brand_profile_id=config.brand_profile_id,
        ))
        print(f"\n# Artifacts: {latest[0]}/")


# ---- v2 path ----


def _print_preparation(prep: RunPreparation) -> None:
    print()
    print("=" * 78)
    print("RUN PREPARATION  —  review before committing a credit")
    print("=" * 78)
    tc = prep.target_classification
    print(f"\nInferred target of the creative:\n  {tc.inferred_target_description}")
    print(f"\n  reasoning: {tc.target_reasoning}")
    print("\nHow your selected dispositions map to that target:")
    for d in tc.disposition_classifications:
        print(f"  [{d.classification:>9}]  {d.disposition_label}")
    if tc.no_match_note:
        print(f"\n  ⚠ no_match_note: {tc.no_match_note}")
    if tc.ambiguity_note:
        print(f"\n  ⚠ ambiguity_note: {tc.ambiguity_note}")
    a = prep.audience_summary
    print(f"\nResolved audience: {a['panel_size']} agents across "
          f"{len(a['disposition_labels'])} dispositions × "
          f"{len(a['context_envelope'])} contexts, "
          f"{a['n_segments']} segments ({a['segment_granularity']}).")
    print(f"  chaos mix: " + ", ".join(
        f"{c['profile']} {c['weight']*100:.0f}%" for c in a["chaos_distribution"]
    ))
    if prep.provisional_dispositions:
        print(f"  provisional dispositions (will be flagged in the report): "
              f"{', '.join(prep.provisional_dispositions)}")
    print(f"\nEstimated cost: ~${prep.estimated_cost_usd:.2f}   "
          f"(persona cores rendered: {prep.persona_cores_rendered})")
    print("=" * 78)


def _run_v2(args: argparse.Namespace, asset_path: Path, asset_label: str) -> None:
    spec_data = json.loads(Path(args.audience_spec).read_text())
    audience_spec = AudienceSpec.from_dict(spec_data)

    baseline_funnel = None
    if args.baseline_funnel:
        baseline_funnel = json.loads(Path(args.baseline_funnel).read_text())

    config = RunConfig(
        asset=AssetSpec(image_path=str(asset_path), label=asset_label),
        archetype=args.archetype,
        category=args.category,
        account_id=args.account,
        brand_profile_id=args.brand_profile,
        max_concurrent_agents=args.max_concurrent,
        seed=args.seed,
        protocol_version="rocket-2.0.0",
        audience_spec=audience_spec,
        segment_granularity=args.segment_granularity,
        baseline_funnel=baseline_funnel,
        library_id=args.library_id,
        audience_id=args.audience_id,
    )

    print("# Rocket Creative Read — v2 (rocket-2.0.0)")
    print(f"# asset: {asset_path}  ({asset_label})")
    print(f"# category: {config.category}")
    print(f"# account / brand_profile: {config.account_id} / {config.brand_profile_id}")
    print(f"# audience spec: {args.audience_spec}")

    prep = RunServiceV2.prepare(config)
    _print_preparation(prep)

    if not args.yes:
        answer = input("\nProceed and commit 1 credit? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted — no credit debited. The prepared run is on disk; "
                  f"re-run with --yes or commit it later.\n# {run_dir(prep.run_id, account_id=config.account_id, brand_profile_id=config.brand_profile_id)}/")
            return

    report = RunServiceV2.commit(prep)
    _print_v2_report(report)
    _print_telemetry(config)


# ---- v1 path ----


def _run_v1(args: argparse.Namespace, asset_path: Path, asset_label: str) -> None:
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

    print("# Rocket Creative Read — v1 (rocket-1.3.0)")
    print(f"# asset: {asset_path}  ({asset_label})")
    print(f"# archetype: {config.archetype} / category: {config.category}")
    print(f"# agents: D={config.dispositions_per_run} × C={config.contexts_per_run} × "
          f"S={config.seeds_per_cell} = {config.total_agents()}")
    print(f"# account / brand_profile: {config.account_id} / {config.brand_profile_id}")
    print(f"# concurrency: {config.max_concurrent_agents}")

    report = RunService.run(config, resume_run_id=args.resume)
    _print_v1_report(report)
    _print_telemetry(config)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rocket Creative Read — v1 archetype sampling or v2 "
                    "two-phase AudienceSpec run.",
    )
    parser.add_argument("--asset", required=True,
                        help="Path to the creative asset (.png / .jpg / .webp).")
    parser.add_argument("--asset-label", default=None,
                        help="Human caption for the asset. Defaults to filename.")
    parser.add_argument("--category", default=_DEFAULT_CATEGORY)
    parser.add_argument("--account", default="internal", help="Account ID.")
    parser.add_argument("--brand-profile", default="default", help="Brand Profile ID.")
    parser.add_argument("--max-concurrent", type=int, default=4,
                        help="Max parallel agents. Default 4.")
    parser.add_argument("--seed", type=int, default=71, help="Sampling seed.")

    # --- v2 flags ---
    parser.add_argument("--audience-spec", default=None,
                        help="Path to an AudienceSpec JSON file. Presence of this "
                             "flag selects the v2 two-phase path.")
    parser.add_argument("--baseline-funnel", default=None,
                        help="(v2) Path to a JSON file with the customer's baseline "
                             "funnel: stop_rate / click_rate / visit_rate / convert_rate.")
    parser.add_argument("--segment-granularity", default="disposition_chaos_band",
                        choices=["disposition", "disposition_chaos_band"],
                        help="(v2) L2 fan-out granularity. Default disposition_chaos_band.")
    parser.add_argument("--library-id", default="", help="(v2) Disposition library id.")
    parser.add_argument("--audience-id", default="", help="(v2) Saved audience id.")
    parser.add_argument("--yes", action="store_true",
                        help="(v2) Skip the confirmation prompt; auto-commit.")

    # --- v1 flags ---
    parser.add_argument("--archetype", default=_DEFAULT_ARCHETYPE,
                        help="(v1) Archetype to sample dispositions/contexts from.")
    parser.add_argument("--dispositions", type=int, default=5,
                        help="(v1) Dispositions per run. Default 5.")
    parser.add_argument("--contexts", type=int, default=3,
                        help="(v1) Contexts per run. Default 3.")
    parser.add_argument("--seeds", type=int, default=1,
                        help="(v1) Seeds per cell. Default 1.")
    parser.add_argument("--resume", metavar="RUN_ID", default=None,
                        help="(v1) Resume an existing run by run_id.")
    args = parser.parse_args()

    asset_path = Path(args.asset)
    if not asset_path.exists():
        print(f"ERROR: asset not found at {asset_path}", file=sys.stderr)
        sys.exit(1)
    asset_label = args.asset_label or asset_path.stem.replace("_", " ").title()

    if args.audience_spec:
        _run_v2(args, asset_path, asset_label)
    else:
        _run_v1(args, asset_path, asset_label)


if __name__ == "__main__":
    main()
