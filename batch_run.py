"""Rocket Creative Read — CLI entry point (rocket-2.0.0).

Two-phase run against a composed AudienceSpec:

    python batch_run.py --asset assets/boat_ad.png \\
        --audience-spec specs/cold_traffic.json \\
        --category personal_audio --account acme --brand-profile boat

Add --yes to skip the confirmation prompt (auto-commit).

The run resolves the AudienceSpec against the Brand Profile's disposition
library (which must already exist on disk under
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

from agent.config import AssetSpec, CreativeInputs, RunConfig
from agent.entities import AudienceSpec
from agent.run_service import RunPreparation, RunService
from agent.schema import Report
from agent.telemetry import run_dir, telemetry_summary

_DEFAULT_ARCHETYPE = "unspecified"
_DEFAULT_CATEGORY = "personal_audio"


# ---- Report printing ----


def _print_target_and_changes(report: Report) -> None:
    am = report.audience_match
    if am is not None:
        mark = "✓" if am.verdict == "aligned" else "⚠"
        print(f"\nAudience match [{am.verdict}] {mark}")
        print(f"  declared: {am.declared_summary}  |  creative reads: {am.inferred_summary}")
        if am.verdict == "mismatched":
            print(f"  {am.message}")

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


def _print_report(report: Report) -> None:
    """Lead with the bet ranking — the brand-manager headline. Verdict,
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
        meta_by_key = {m.stage_key: m for m in fp.stage_meta}
        print("\n" + "-" * 78)
        print(f"PROJECTED FUNNEL  (overall — basis: {o.basis})")
        print("-" * 78)
        for stage, rate, band in (
            ("stop", o.stop_rate, o.stop_band),
            ("click", o.click_rate, o.click_band),
            ("visit", o.visit_rate, o.visit_band),
            ("convert", o.convert_rate, o.convert_band),
        ):
            m = meta_by_key.get(stage)
            label = f"  {stage:>8}"
            if m:  # observable mapping (legacy projections have no stage_meta)
                label += f" → {m.observable_label}"
            line = (f"{label}: {rate*100:6.3f}%   "
                    f"[{band[0]*100:.3f}% – {band[1]*100:.3f}%]")
            if m and m.status == "scenario":
                need = ", ".join(m.required_inputs) or "its input"
                line += f"   (SCENARIO — image-only; provide {need} to ground)"
            print(line)
        print(f"\n  {fp.calibration_note}")
        if fp.by_segment:
            convert_meta = meta_by_key.get("convert")
            convert_scenario = bool(
                convert_meta and convert_meta.status == "scenario"
            )
            print("\n  By segment (convert rate):")
            if convert_scenario:
                need = ", ".join(convert_meta.required_inputs) or "an offer"
                print(f"    (SCENARIO — image-only; no {need} provided — "
                      "ungrounded estimates, not purchase predictions)")
            floored = False
            for seg in fp.by_segment:
                rates = seg.funnel_rates
                # Run-level convert SCENARIO wins over per-segment floor
                # suppression: with no offer reaching the agents, the whole
                # convert column is ungrounded and the asterisk is moot.
                if (not convert_scenario
                        and seg.behavioral_distribution.would_act_within_week_count == 0):
                    lo, hi = rates.convert_band
                    print(f"    {seg.segment_label:<42} "
                          f"   —    [{lo*100:.3f}% – {hi*100:.3f}%] *")
                    floored = True
                else:
                    print(f"    {seg.segment_label:<42} "
                          f"{rates.convert_rate*100:6.3f}%   "
                          f"[{rates.convert_band[0]*100:.3f}% – "
                          f"{rates.convert_band[1]*100:.3f}%]")
            if floored:
                print("    * no would-act signal in segment — central rate "
                      "suppressed (it sits at the heuristic floor and is "
                      "identical across all such segments); band reflects "
                      "the segment's N.")

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
    if prep.demographic_mismatch is not None:
        m = prep.demographic_mismatch
        print("\n" + "!" * 78)
        print("⚠  GROSS DEMOGRAPHIC MISMATCH  —  this overrides --yes")
        print(f"   {m.message}")
        print("   Advisory, not a block: if this is intentional, re-run with")
        print("   --acknowledge-demographic-mismatch. Otherwise fix the declared")
        print("   audience, or check you uploaded the right creative.")
        print("!" * 78)
    print(f"\nEstimated cost: ~${prep.estimated_cost_usd:.2f}   "
          f"(persona cores rendered: {prep.persona_cores_rendered})")
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rocket Creative Read — two-phase AudienceSpec run.",
    )
    parser.add_argument("--asset", required=True,
                        help="Path to the creative asset (.png / .jpg / .webp).")
    parser.add_argument("--asset-label", default=None,
                        help="Human caption for the asset. Defaults to filename.")
    parser.add_argument("--audience-spec", required=True,
                        help="Path to an AudienceSpec JSON file.")
    parser.add_argument("--category", default=_DEFAULT_CATEGORY)
    parser.add_argument("--account", default="internal", help="Account ID.")
    parser.add_argument("--brand-profile", default="default", help="Brand Profile ID.")
    parser.add_argument("--archetype", default=_DEFAULT_ARCHETYPE,
                        help="Optional archetype label. Default 'unspecified' "
                             "lets the target classifier infer the pool from "
                             "the dispositions + category instead of a fixed "
                             "label. Pass a real descriptor only to add a hint.")
    parser.add_argument("--max-concurrent", type=int, default=4,
                        help="Max parallel agents. Default 4.")
    parser.add_argument("--seed", type=int, default=71, help="Sampling seed.")
    parser.add_argument("--baseline-funnel", default=None,
                        help="Path to a JSON file with the customer's baseline "
                             "funnel: stop_rate / click_rate / visit_rate / convert_rate.")
    parser.add_argument("--segment-granularity", default="disposition_chaos_band",
                        choices=["disposition", "disposition_chaos_band"],
                        help="L2 fan-out granularity. Default disposition_chaos_band.")
    parser.add_argument("--library-id", default="", help="Disposition library id.")
    parser.add_argument("--audience-id", default="", help="Saved audience id.")
    parser.add_argument("--primary-text", default="",
                        help="Ad body / primary caption. Grounds the click stage "
                             "and reaches the agents' reaction.")
    parser.add_argument("--headline", default="",
                        help="Ad headline. Grounds the click stage with --primary-text.")
    parser.add_argument("--offer", default="",
                        help="Offer + price, e.g. '₹2,699, 20%% off first order'. "
                             "Grounds the convert stage and reaches the agents.")
    parser.add_argument("--creative-json", default=None,
                        help="Path to a JSON file with primary_text / headline / "
                             "offer (alternative to the individual flags).")
    parser.add_argument("--declared-targeting", default="",
                        help="The customer's stated Meta audience (free text). A "
                             "hint to the target classifier; does not override the "
                             "creative-derived inferred audience.")
    parser.add_argument("--yes", action="store_true",
                        help="Skip the confirmation prompt; auto-commit.")
    parser.add_argument("--acknowledge-demographic-mismatch", action="store_true",
                        help="Proceed even if the ad grossly mismatches the "
                             "declared audience demographic (e.g. deliberately "
                             "testing an off-demographic creative). Required to "
                             "run through a gross mismatch; it overrides --yes.")
    args = parser.parse_args()

    asset_path = Path(args.asset)
    if not asset_path.exists():
        print(f"ERROR: asset not found at {asset_path}", file=sys.stderr)
        sys.exit(1)
    asset_label = args.asset_label or asset_path.stem.replace("_", " ").title()

    spec_data = json.loads(Path(args.audience_spec).read_text())
    audience_spec = AudienceSpec.from_dict(spec_data)

    baseline_funnel = None
    if args.baseline_funnel:
        baseline_funnel = json.loads(Path(args.baseline_funnel).read_text())

    # Creative inputs: a JSON file (if given) provides the defaults; individual
    # flags override any field they set.
    creative_data = {}
    if args.creative_json:
        creative_data = json.loads(Path(args.creative_json).read_text())
    creative_inputs = CreativeInputs(
        primary_text=args.primary_text or creative_data.get("primary_text", ""),
        headline=args.headline or creative_data.get("headline", ""),
        offer=args.offer or creative_data.get("offer", ""),
    )

    config = RunConfig(
        asset=AssetSpec(image_path=str(asset_path), label=asset_label),
        archetype=args.archetype,
        category=args.category,
        account_id=args.account,
        brand_profile_id=args.brand_profile,
        max_concurrent_agents=args.max_concurrent,
        seed=args.seed,
        audience_spec=audience_spec,
        segment_granularity=args.segment_granularity,
        baseline_funnel=baseline_funnel,
        library_id=args.library_id,
        audience_id=args.audience_id,
        creative_inputs=creative_inputs,
        declared_targeting=args.declared_targeting,
    )

    print("# Rocket Creative Read (rocket-2.0.0)")
    print(f"# asset: {asset_path}  ({asset_label})")
    print(f"# category: {config.category}")
    print(f"# account / brand_profile: {config.account_id} / {config.brand_profile_id}")
    print(f"# audience spec: {args.audience_spec}")

    prep = RunService.prepare(config)
    _print_preparation(prep)

    # A gross demographic mismatch overrides --yes: never silently auto-commit
    # through it. Advisory only — proceed via --acknowledge-demographic-mismatch.
    if prep.demographic_mismatch is not None and not args.acknowledge_demographic_mismatch:
        print("\nABORT — gross demographic mismatch (see the flag above). No "
              "credit debited. This overrides --yes. To run anyway (e.g. you are "
              "deliberately testing an off-demographic creative), re-run with "
              "--acknowledge-demographic-mismatch. Otherwise fix the declared "
              "audience or the uploaded creative.")
        return

    if not args.yes:
        answer = input("\nProceed and commit 1 credit? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted — no credit debited. The prepared run is on disk; "
                  f"re-run with --yes or commit it later.\n# {run_dir(prep.run_id, account_id=config.account_id, brand_profile_id=config.brand_profile_id)}/")
            return

    report = RunService.commit(prep)
    _print_report(report)
    _print_telemetry(config)


if __name__ == "__main__":
    main()
