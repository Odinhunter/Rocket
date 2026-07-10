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
from agent.purpose import DEFAULT_PURPOSE, PURPOSE_ORDER, resolve_purpose
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


# rocket-2.3.0: the decision layer. Every line the brand manager reads is a
# decision or an action; the categorical verdict is demoted to an engine read.
_DECISION_TAGLINE = {
    "SCALE": "Put spend behind it — no in-scope lever would materially lift it.",
    "ITERATE": "Target responds; a specific in-scope fix is leaking conversion. "
               "Fix it, re-run, then scale.",
    "RETARGET": "The creative works — for a different audience than it's aimed at. "
                "Fix the buy, not the ad.",
    "REBUILD": "The target rejects it on grounds no in-scope tweak fixes. "
               "Don't run as-is.",
    "INCONCLUSIVE": "The read isn't trustworthy yet — see why below.",
}
_LEVER_HEADING = {
    "ITERATE": "THE FIX(ES)  (highest-leverage first):",
    "RETARGET": "RE-AIM + FIX  (highest-leverage first):",
    "REBUILD": "IF YOU REBUILD, what has to change:",
    "INCONCLUSIVE": "TO GET A TRUSTWORTHY READ:",
    "SCALE": "PROTECT ON SCALE-UP:",
}


def _humanize(label: str) -> str:
    return label.replace("_", " ")


def _inconclusive_lines(report: Report) -> list[str]:
    """Plain-language why + what-to-change for an INCONCLUSIVE read (spec §4).
    An untrustworthy read must NEVER show a confident action-rate headline — the
    number rests on the wrong people or an unreadable target."""
    flags = set(report.methodology_flags)
    if "pool_archetype_mismatch" in flags:
        why = ("the audience this ad targets isn't represented in your "
               "disposition library, so the read rests on the wrong people")
        fix = ("add a disposition profile that matches this ad's audience, "
               "then re-run")
    elif "target_unsignaled" in flags:
        why = ("the ad doesn't clearly signal who it's for — every audience "
               "read as a maybe")
        fix = ("clarify the creative's target, or declare the audience you're "
               "buying against, then re-run")
    else:
        why = (report.decision.rationale if report.decision else
               "the read isn't trustworthy on this pool")
        fix = "check that the audience you declared matches who the ad is for"
    return [
        "  We can't give you a trustworthy read on this creative yet.",
        f"  Why: {why}.",
        f"  To get a real read: {fix}.",
    ]


def _headline_metric_line(d) -> str:
    """The one number the brand manager reads, phrased for the ad's JOB. Direct-
    sell is byte-for-byte the v2.3 line; other jobs swap the metric + frame."""
    preset = resolve_purpose(getattr(d, "purpose", "direct_sell") or "direct_sell")
    rate = f"{d.target_action_rate:.0%}"
    tail = (f"  —  {d.target_action_num} of {d.target_action_denom}"
            if d.target_action_denom else "")
    if preset.name == "direct_sell":
        who = _humanize(", ".join(d.within_dispositions)) if d.within_dispositions else "your target"
        return f"  {rate} of your target ({who}) would act{tail}."
    if preset.name == "cold_hook":
        return (f"  {rate} of a cold audience stopped and leaned in{tail}  "
                f"(vs scrolling past — the hook, not the sale).")
    # retain / others: a generic metric-labelled line.
    return f"  {rate} — {preset.metric_label}{tail}."


def _trust_line(d) -> str:
    if d.trust == "HIGH":
        line = "Trust: HIGH"
        if len(d.within_dispositions) >= 2:
            line += f" — {len(d.within_dispositions)} within-target dispositions agree"
        if d.target_action_denom:
            line += f" ({d.target_action_denom} in the target sample)"
        return line + "."
    return ("Trust: DIRECTIONAL — thin evidence (one narrow audience engaged); "
            "treat as a lead, not a verdict.")


def _print_decision_headline(report: Report) -> None:
    d = report.decision
    if d is None:  # legacy report (no decision) — fall back to the bet ranking
        print()
        print("=" * 78)
        print("STRATEGIC BET RANKING  (highest expected marketing-ROI payoff first)")
        print("=" * 78)
        for i, bet in enumerate(report.bet_ranking, 1):
            print(f"\n  {i}. {bet}")
        return

    print()
    print("=" * 78)
    print(f"DECISION:  {d.decision}")
    print("=" * 78)
    print(f"\n  {_DECISION_TAGLINE.get(d.decision, '')}")

    print()
    if d.decision == "INCONCLUSIVE":
        # Never show an action rate here — the read is untrustworthy by
        # definition, even when a_within happens to be non-None (pool mismatch).
        for line in _inconclusive_lines(report):
            print(line)
    elif d.target_action_rate is not None:
        print(_headline_metric_line(d))
        preset = resolve_purpose(getattr(d, "purpose", "direct_sell") or "direct_sell")
        if d.decision == "RETARGET" and d.champion_disposition:
            print(f"  But the {_humanize(d.champion_disposition)} — whom you are NOT "
                  f"targeting — acts at {d.champion_action_rate:.0%}. Right ad, wrong person.")
        elif d.decision in ("ITERATE", "REBUILD") and preset.audience_frame == "narrow":
            # "everyone else scrolls, tighten targeting" only fits a narrow-frame
            # job — a cold-hook/awareness ad WANTS broad reach.
            print("  It reaches no one else (everyone else scrolls — expected; "
                  "tighten targeting).")
    else:
        print(f"  No trustworthy within-target read — {d.rationale}.")

    if report.bet_ranking:
        print()
        print(f"  {_LEVER_HEADING.get(d.decision, 'ACTIONS:')}")
        for i, bet in enumerate(report.bet_ranking, 1):
            print(f"    {i}. {bet}")

    print()
    print(f"  {_trust_line(d)}")


def _print_report(report: Report) -> None:
    """Lead with the DECISION (rocket-2.3.0) — the call a brand manager acts on.
    The categorical verdict/confidence are demoted to an internal engine read;
    the funnel projection and pain detail sit below for those who want depth."""
    _print_decision_headline(report)

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
    print("ENGINE READ  (internal — the clinical verdict, not the headline)")
    print(f"  verdict: {report.verdict}   confidence: {report.confidence}/100")
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
    declared_preset = resolve_purpose(prep.config.creative_inputs.purpose)
    print(f"\nGrading against the job: {declared_preset.label} "
          f"({declared_preset.metric_label})")
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
    if prep.coverage_warning is not None:
        c = prep.coverage_warning
        print("\n" + "~" * 78)
        print(f"⚠  THIN AUDIENCE COVERAGE  —  {c.eligible_count}/{c.total_count} personas in the declared slice")
        print(f"   {c.message}")
        print("~" * 78)
    if prep.purpose_mismatch is not None:
        pm = prep.purpose_mismatch
        print("\n" + "!" * 78)
        print(f"⚠  PURPOSE MISMATCH  —  reads as {pm.apparent_label.upper()}, "
              f"grading as {pm.declared_label.upper()}")
        print(f"   {pm.message}")
        print("   Advisory, not a block — the run proceeds. Re-run with "
              f"{pm.suggested_flag} to grade against the apparent job.")
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
    parser.add_argument("--purpose", default=DEFAULT_PURPOSE,
                        choices=list(PURPOSE_ORDER),
                        help="v2.4: the ad's JOB — the ruler the report grades "
                             "against. direct_sell (default) = would-buy-this-week; "
                             "cold_hook = stop-the-scroll; awareness_informer = "
                             "notice+understand; brand_building = feel+remember; "
                             "retain_winback = re-engage existing customers.")
    parser.add_argument("--declared-targeting", default="",
                        help="The customer's stated Meta audience (free text). A "
                             "hint to the target classifier; does not override the "
                             "creative-derived inferred audience.")
    parser.add_argument("--marketer-led", action="store_true",
                        help="rocket-2.1.0: compose the panel from the declared "
                             "audience (spec.demographics) — select/weight personas "
                             "that live in the buy, simulate at the declared "
                             "demographics. Off by default (legacy composition).")
    parser.add_argument("--tail-fraction", type=float, default=0.0,
                        help="Marketer-led discovery tail: fraction (0..1) of the "
                             "panel reserved for out-of-frame personas, segregated "
                             "from the declared-audience numbers. Default 0.")
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
        # A --purpose flag wins; else the creative-json's purpose; else default.
        # (argparse default is DEFAULT_PURPOSE, so an unset flag falls through
        # to the json only when json sets a non-default purpose.)
        purpose=(args.purpose if args.purpose != DEFAULT_PURPOSE
                 else creative_data.get("purpose") or DEFAULT_PURPOSE),
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
        marketer_led=args.marketer_led,
        tail_fraction=args.tail_fraction,
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
