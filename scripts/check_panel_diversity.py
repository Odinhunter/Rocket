#!/usr/bin/env python3
"""How many genuinely different PEOPLE back a panel? ($0, offline, no API.)

Run after ANY edit to a library's `demographic_bundles`.

WHY THIS EXISTS. `demographic_overlap` is gender × age × income ONLY, so the
income rows that do not overlap the declared brief score zero and drop out of
the panel entirely. A library can look richly authored — five income rows per
disposition — and still hand the persona writer a handful of identical
biographies once a real targeting brief is applied. Measured 2026-08-13 on the
shipped 25-44 / ₹7-40L brief: 100 agents were backed by **10 biographies**,
and **15 agents shared one**. After re-authoring: 25 and 5.

⚠ READ THE `largest identical cluster` NUMBER, NOT THE BUNDLE COUNT. The
bundle count is what you authored; the cluster is what survives the brief.

⚠ `distinct persona cores` IS A COST. Each one is a ~$0.02 render on a cold
cache — that is the one-time price of a bundle edit, paid on the next run.

Usage:
    .venv/bin/python scripts/check_panel_diversity.py [--verbose]
    .venv/bin/python scripts/check_panel_diversity.py --run <run_dir>

With no arguments it measures the library's OWN shipped audience (read from
the scaffold, so it works in a clean checkout where `runs/` does not exist).
`--run` instead replays the exact declared frame of a finished run.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack  # noqa: E402
from agent.entities import AudienceSpec  # noqa: E402
from agent.panel import build_panel  # noqa: E402
from agent.render import persona_core_hash  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
_SCAFFOLD = _REPO / "scripts" / "scaffold_health_wellness.py"
_CATEGORY = "health_wellness_nutrition"


def _scaffold():
    spec = importlib.util.spec_from_file_location("_scaffold_hw_div", _SCAFFOLD)
    mod = importlib.util.module_from_spec(spec)
    with redirect_stdout(io.StringIO()):  # the module prints on import
        spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="a finished run dir; use its declared frame")
    ap.add_argument("--verbose", action="store_true", help="list every biography")
    args = ap.parse_args()

    mod = _scaffold()
    library = {d.label: d for d in mod._library().dispositions}

    if args.run:
        cfg = json.loads((Path(args.run) / "run.json").read_text())["config"]
        spec = AudienceSpec.from_dict(cfg["audience_spec"])
        category = cfg["category"]
        kwargs = dict(
            segment_granularity=cfg["segment_granularity"], seed=cfg["seed"],
            marketer_led=cfg["marketer_led"], tail_fraction=cfg["tail_fraction"],
        )
        source = args.run
    else:
        spec = mod._audience_spec(load_pack(_CATEGORY))
        category = _CATEGORY
        kwargs = dict(
            segment_granularity="disposition_chaos_band", seed=71,
            marketer_led=True, tail_fraction=0.0,
        )
        source = "the library's own shipped audience"

    missing = [l for l in spec.disposition_labels if l not in library]
    if missing:
        print(f"ERROR: spec names dispositions not in the library: {missing}")
        return 1
    disps = [library[l] for l in spec.disposition_labels]

    agents = build_panel(spec, disps, category=category, **kwargs)

    bios = collections.Counter(
        (a.disposition.label, a.demographic.occupation_hint,
         a.demographic.household_hint)
        for a in agents
    )
    cores = collections.Counter(
        persona_core_hash(a.demographic, a.disposition.vector, a.chaos,
                          category, a.disposition.anchor)
        for a in agents
    )
    authored = sum(len(d.demographic_bundles) for d in disps)
    biggest = bios.most_common(1)[0][1]

    print(f"frame                       : {source}")
    print(f"panel size                  : {len(agents)}")
    print(f"dispositions in panel       : "
          f"{len({a.disposition.label for a in agents})} "
          f"of {len(spec.disposition_labels)} named")
    print(f"bundles authored            : {authored}")
    print(f"distinct BIOGRAPHIES        : {len(bios)}"
          f"   <- how many different people the writer is handed")
    print(f"  largest identical cluster : {biggest}"
          f"   <- agents who are the same person")
    print(f"  cluster sizes             : {sorted(bios.values(), reverse=True)}")
    print(f"distinct persona cores      : {len(cores)}"
          f"   <- ~${0.02 * len(cores):.2f} of renders on a cold cache")

    if args.verbose:
        print("\n--- biographies ---")
        for (label, occ, house), n in bios.most_common():
            print(f"{n:3d}  {label:<28} {occ}  |  {house}")

    if biggest > 7:
        print(f"\n⚠ {biggest} agents share one biography. Split the income row "
              f"they sit in — see docs/disposition_demographic_bundles.md.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
