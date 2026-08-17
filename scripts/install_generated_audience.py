#!/usr/bin/env python3
"""Install a generated audience as a NEW brand profile.  ($0, no API calls)

    .venv/bin/python scripts/install_generated_audience.py generated_audience.json

⚠ IT NEVER TOUCHES `health_wellness_demo`. That brand holds the one validated
library on disk and it is the control in this comparison — overwrite it and
there is nothing left to compare the generated panel against. Everything here
goes to a new brand profile with its own library and its own audience.

⚠ Deliberately NOT `scaffold_health_wellness.main()`, which overwrites six files
and rewrites the shared `runs/demo/account.json`.

The audience it writes copies the CONTEXT ENVELOPE, CHAOS MIX, PANEL SIZE and
DEMOGRAPHIC FRAME from the existing validated audience verbatim. That is the
whole experimental design: the only thing that differs between this run and the
SY PB Bar run is WHO IS IN THE PANEL. Change the contexts too and a difference
in the result would have two candidate causes and prove nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import population
from agent.entities import (
    AUDIENCE_DISPOSITION_CAP, AudienceSpec, BrandProfile, DispositionLibrary,
    SavedAudience,
)
from agent.vectors import NamedDisposition

ACCOUNT = "demo"
SOURCE_BRAND = "health_wellness_demo"        # the control — read only
NEW_BRAND = "hw_generated_v1"
NEW_LIBRARY = "snacking_generated_lib_v1"
NEW_AUDIENCE = "snacking_cold_v1"


def _merge(existing: list[NamedDisposition],
           incoming: list[NamedDisposition]) -> list[NamedDisposition]:
    """Add a region's buyer types to a population that already exists.

    ⚠ A POPULATION ACCUMULATES; IT IS NEVER REPLACED. Each generation covers ONE
    demographic region, and a brand's population is the union of every region
    anyone has ever bought against. Replacing would throw away the region the
    last customer paid for.

    ⚠ LABELS COLLIDE ACROSS REGIONS AND THAT IS NORMAL. `skeptic_no_sugar` is a
    good name for a 26-year-old in Mumbai and for a 52-year-old in Nagpur, but
    `DispositionLibrary.validate()` rejects duplicate labels — so a collision is
    suffixed with the incoming type's region key. The two are NOT duplicates:
    they are the same stance in two different lives, which is the entire reason
    generation is region-scoped.
    """
    taken = {d.label for d in existing}
    merged = list(existing)
    for d in incoming:
        if d.label in taken:
            region_key = population.parse_notes(d.notes).get("region", "")
            candidate = f"{d.label}__{region_key}" if region_key else d.label
            n = 2
            while candidate in taken:
                candidate = f"{d.label}__{region_key}_{n}"
                n += 1
            print(f"  label collision: {d.label} -> {candidate}")
            d.label = candidate
        taken.add(d.label)
        merged.append(d)
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--category", default="health_wellness_nutrition")
    ap.add_argument("--append", action="store_true",
                    help="add these buyer types to the brand's existing "
                         "population instead of replacing it")
    ap.add_argument("--brand", default=NEW_BRAND,
                    help=f"target brand profile (default {NEW_BRAND})")
    args = ap.parse_args()

    if args.brand == SOURCE_BRAND:
        sys.exit(f"refusing to write to {SOURCE_BRAND} — it is the control")

    data = json.loads(Path(args.path).read_text())
    if "dispositions" not in data:
        sys.exit("no converted dispositions in that file — run the generator first")
    dispositions = [NamedDisposition.from_dict(d) for d in data["dispositions"]]

    # The control's saved audience supplies everything that is NOT the audience.
    source = SavedAudience.load(ACCOUNT, SOURCE_BRAND, "cold_traffic_v1")
    template = source.spec

    if args.append:
        try:
            before = DispositionLibrary.load(ACCOUNT, args.brand).dispositions
        except FileNotFoundError:
            before = []
        dispositions = _merge(before, dispositions)
        print(f"  population {len(before)} -> {len(dispositions)} buyer types")

    library = DispositionLibrary(
        library_id=NEW_LIBRARY, brand_profile_id=args.brand,
        account_id=ACCOUNT, dispositions=dispositions,
    )
    library.validate()

    spec = AudienceSpec.from_dict(template.to_dict())
    # ⚠ A LIBRARY IS UNCAPPED BUT A RUN IS NOT. Once a population accumulates
    # past AUDIENCE_DISPOSITION_CAP the saved audience cannot list all of it, so
    # the template carries a SELECTION — spread across the demand spaces rather
    # than the first N in generation order. The per-buy selection at run time
    # comes from the same function.
    selected = population.select(dispositions, spec.demographics,
                                 AUDIENCE_DISPOSITION_CAP)
    if len(selected) < len(dispositions):
        print(f"  ⚠ {len(dispositions)} in the population, {len(selected)} seats "
              f"in a run — the saved audience carries a stratified selection")
    if not selected:
        sys.exit("no buyer type in this population is reachable by the template's "
                 "own demographic frame — nothing to save")
    spec.disposition_labels = [d.label for d in selected]
    # ⚠ "disposition", not "disposition_chaos_band". At 40 types the chaos-band
    # split costs ~$2.40 more per run for per-mood-band resolution in a funnel
    # projection that is off by default and uncalibrated. See the cost note on
    # AUDIENCE_DISPOSITION_CAP.
    spec.segment_granularity = "disposition"
    spec.validate()

    profile = BrandProfile(
        brand_profile_id=NEW_BRAND, account_id=ACCOUNT,
        categories=[args.category], library_id=NEW_LIBRARY,
        audience_ids=[NEW_AUDIENCE],
    )
    profile.validate()

    saved = SavedAudience(
        audience_id=NEW_AUDIENCE, name="Snacking demand space — generated",
        brand_profile_id=NEW_BRAND, account_id=ACCOUNT, spec=spec,
    )
    saved.validate()

    for obj in (library, profile, saved):
        print(f"  wrote {obj.save()}")

    print(f"\n{len(dispositions)} buyer types installed as {ACCOUNT}/{NEW_BRAND}")
    print(f"  library    : {NEW_LIBRARY}")
    print(f"  audience   : {NEW_AUDIENCE}  ({len(spec.disposition_labels)} types, "
          f"panel {spec.panel_size}, granularity {spec.segment_granularity})")
    print(f"  contexts   : {[c.label for c in spec.context_envelope]}   (copied from the control)")
    print(f"\n⚠ {SOURCE_BRAND} untouched.")


if __name__ == "__main__":
    main()
