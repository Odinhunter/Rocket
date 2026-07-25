"""Price a Creative Read run BEFORE paying for it. Spends nothing.

`RunService.prepare()` has exactly two paid surfaces: `identify_target`
($0.15) and render-cache MISSES ($0.005 each). Everything before target_id is
deterministic and local. This script runs that free prefix and then prices the
paid remainder exactly, by set-diffing the panel's `persona_core_hash` values
against the cores already warm on disk.

Use it before any paid run on a brand whose cache you believe is warm. Zero
misses means prepare() costs $0.15 and the full run costs the printed estimate;
a non-trivial miss count means the real number is higher than the folklore one,
and you want to know that before spending, not after.

It doubles as a $0-cost check that a run is wired correctly at all: the free
prefix is where nearly all the "does this config actually resolve" risk lives
(library resolution, disposition labels, panel composition, spec loading).

    .venv/bin/python scripts/preflight_cost.py \
        --asset assets/mb_biozyme_ad.png \
        --audience-spec specs/health_wellness_cold_traffic.json \
        --category health_wellness_nutrition \
        --account demo --brand-profile health_wellness_demo \
        --marketer-led

⚠ This REPLICATES prepare()'s free prefix rather than calling it (calling it
would fire the paid target_id). If prepare() changes, re-check this against
`RunService.prepare` in agent/run_service.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack
from agent.config import build_run_config, default_asset_label
from agent.entities import DispositionLibrary
from agent.panel import build_panel, compute_panel_version
from agent.run_service import (
    _COST_L3,
    _COST_L4,
    _COST_PER_AGENT,
    _COST_PER_L2_SEGMENT,
    _COST_PER_RENDER,
    _COST_TARGET_ID,
    _disposition_description,
    _render_cache_dir,
)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Price a run before paying for it. Makes no API calls.",
    )
    ap.add_argument("--asset", required=True)
    ap.add_argument("--asset-label", default="")
    ap.add_argument("--audience-spec", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--archetype", default="unspecified")
    ap.add_argument("--account", default="internal")
    ap.add_argument("--brand-profile", default="default")
    ap.add_argument("--library-id", default="")
    ap.add_argument("--audience-id", default="")
    ap.add_argument("--seed", type=int, default=71)
    ap.add_argument("--marketer-led", action="store_true")
    ap.add_argument("--tail-fraction", type=float, default=0.0)
    ap.add_argument(
        "--segment-granularity", default="disposition_chaos_band",
        choices=["disposition", "disposition_chaos_band"],
    )
    args = ap.parse_args()

    # Same seam batch_run and the operator tool use, so this prices the config
    # that would actually run — not a hand-rolled lookalike.
    config = build_run_config(
        asset_path=args.asset,
        asset_label=args.asset_label or default_asset_label(args.asset),
        audience_spec=args.audience_spec,
        category=args.category,
        archetype=args.archetype,
        account_id=args.account,
        brand_profile_id=args.brand_profile,
        library_id=args.library_id,
        audience_id=args.audience_id,
        seed=args.seed,
        marketer_led=args.marketer_led,
        tail_fraction=args.tail_fraction,
        segment_granularity=args.segment_granularity,
    )
    config.validate()   # asset exists, supported extension, under the b64 ceiling
    spec = config.audience_spec
    assert spec is not None

    print(f"asset          {config.asset.image_path}  ({config.asset.label})")
    print(f"category       {config.category}")
    print(f"account/brand  {config.account_id}/{config.brand_profile_id}")
    print(f"panel_size     {spec.panel_size}   seed {config.seed}   "
          f"marketer_led {config.marketer_led}")

    load_pack(config.category)
    library = DispositionLibrary.load(config.account_id, config.brand_profile_id)
    dispositions = library.resolve(spec.disposition_labels)
    print(f"\nresolved {len(dispositions)} dispositions:")
    for d in dispositions:
        print(f"  - {d.label}{'  [provisional]' if d.provisional else ''}")

    panel = build_panel(
        spec, dispositions, category=config.category,
        segment_granularity=config.segment_granularity, seed=config.seed,
        marketer_led=config.marketer_led, tail_fraction=config.tail_fraction,
    )
    panel_version = compute_panel_version(
        spec, dispositions, category=config.category,
        segment_granularity=config.segment_granularity, seed=config.seed,
        marketer_led=config.marketer_led, tail_fraction=config.tail_fraction,
    )
    n_segments = len({a.segment_key for a in panel})
    print(f"\npanel          {len(panel)} agents / {n_segments} segments")
    print(f"panel_version  {panel_version}")

    # target_id's input is assembled but NOT sent — that call is the paid step.
    pool = [(d.label, _disposition_description(d)) for d in dispositions]
    print(f"target_id in   {len(pool)} descriptions, "
          f"{sum(len(p[1]) for p in pool)} chars (not sent)")

    cache_dir = _render_cache_dir(config)
    cached = {p.stem for p in cache_dir.glob("*.json")} if cache_dir.exists() else set()
    wanted = {a.persona_core_hash for a in panel}
    misses = len(wanted - cached)

    render_cost = misses * _COST_PER_RENDER
    prepare_cost = _COST_TARGET_ID + render_cost
    commit_cost = (
        len(panel) * _COST_PER_AGENT
        + n_segments * _COST_PER_L2_SEGMENT
        + _COST_L3 + _COST_L4
    )

    print(f"\nrender cache   {cache_dir}  ({len(cached)} warm)")
    print(f"panel wants    {len(wanted)} unique cores  ->  MISSES {misses}")
    print(f"\n  target_id            ${_COST_TARGET_ID:.3f}")
    print(f"  persona renders      ${render_cost:.3f}   ({misses} x ${_COST_PER_RENDER})")
    print(f"  ------------------------------")
    print(f"  prepare() only       ${prepare_cost:.3f}")
    print(f"  + commit() L1-L4     ${commit_cost:.2f}")
    print(f"  FULL RUN             ${prepare_cost + commit_cost:.2f}")

    if misses:
        print(f"\n⚠ {misses} cold cores — prepare() is ${prepare_cost:.3f}, not "
              f"${_COST_TARGET_ID:.3f}. Confirm the spend before running.")
    else:
        print(f"\n✓ cache fully warm — prepare() is exactly ${_COST_TARGET_ID:.3f}.")
    print("\nNothing was spent; no API call was made.")


if __name__ == "__main__":
    main()
