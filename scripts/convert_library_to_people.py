#!/usr/bin/env python3
"""Turn a library of demographic BANDS into a population of PEOPLE.  ($0, offline)

    .venv/bin/python scripts/convert_library_to_people.py generated_audience_v2.json \
        --out generated_audience_v2_people.json

THE DEFECT THIS EXISTS FOR, MEASURED 2026-08-15
-----------------------------------------------
A buyer type carries an age RANGE and an income RANGE, and a declared buy clips
those ranges to itself. Measured against the real 32-type library:

    the shipped brief (25-44, Rs7-40L)   31 of 32 types have anyone in them
    women 45-60, tier-3                   2 of 32
    women 55-75, tier-3                   0 of 32
    men 18-24, Rs0-3.5L                   0 of 32

Both failure modes are silent. At 2-of-32 the run builds 100 agents carrying two
opinions, and simulates them as "Coimbatore / tier-2 staff nurse" while the report
says tier-3. At 0-of-32 `_clipped_bundle_points` falls back to the declared frames,
so ALL 32 types return as blank `55-75 / female / tier-3` shells with an EMPTY
occupation and household -- the whole biography layer evaporates and the panel
looks FULLER the worse the mismatch is.

WHAT THIS DOES
--------------
Each range bundle becomes one specific person: a concrete age and a concrete income
placed inside that bundle's own range. Lakshmi is 52, not "45-54".

Everything downstream then works with no engine change, because
`panel._range_overlap_frac` ALREADY special-cases a degenerate range:

    if span <= 0:  # degenerate point range: in-or-out
        return 1.0 if lo_b <= lo_a <= hi_b else 0.0

So a person aged 52 scores 1.0 against a 45-60 buy AND against a 47-63 buy, and
0.0 against 25-44 -- arbitrary customer-chosen ranges, no bands, no snapping. And
`panel._clip_point` becomes the IDENTITY on a point, so the city, the career and
the household survive instead of being clipped off.

PLACEMENT IS A SEEDED SPREAD, NOT THE MIDPOINT
----------------------------------------------
The midpoint is deterministic but it collapses every 45-54 bundle onto 49. Spread
places them across 45..54, which is what a narrow query needs: DENSITY, not just
coverage. Measured cost of having none -- the entire 45+ women's panel in the
current library is TWO women, aged 45 and 46, so a brief of 47-63 empties it.

Placement is a hash of (label, bundle index), so it is deterministic and
reproducible: the same input file always yields the same population.

Coherent by construction: the ON CAREERS directive in `generate_audience.py`
already requires every occupation to be plausible at BOTH ends of its own range,
so any point inside that range carries a career that still fits.

WHAT THIS DOES *NOT* FIX
------------------------
It converts bands to people; it does not un-weld an opinion from a demographic.
`loyalist_monthly_biscuit_tin` will still be held by a 38-year-old Chennai woman
AND a 49-year-old Jaipur man, because that is how it was generated. Fixing that
needs generation per declared region -- Stage 1 of the plan, not this script.

Nothing here is installed. Nothing here overwrites its input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.vectors import (
    DemographicBundle,
    DemographicPoint,
    NamedDisposition,
)

# Briefs the conversion is reported against. Chosen to include the buy the
# library was authored for AND the ones the measurement showed it fails, so the
# print-out cannot flatter the change.
_REPORT_BRIEFS = (
    ("the shipped brief  25-44 Rs7-40L any", "any", 25, 44, 7.0, 40.0),
    ("women 45-60        any income", "female", 45, 60, 0.0, 100.0),
    ("women 47-63        any income", "female", 47, 63, 0.0, 100.0),
    ("women 55-75        any income", "female", 55, 75, 0.0, 100.0),
    ("men   18-24        Rs0-3.5L", "male", 18, 24, 0.0, 3.5),
    ("all   30-40        Rs3.5-17L", "any", 30, 40, 3.5, 17.0),
)


_MAX_PEOPLE_PER_BAND = 4
_YEARS_PER_PERSON = 4


def _jitter(key: str) -> float:
    """A stable number in [0.15, 0.85] from `key`.

    ⚠ Not `random`. `random` would make the population depend on interpreter
    state, so two runs of this script over one input would install two different
    libraries and no run could be reproduced.
    """
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return 0.15 + 0.70 * (int(digest, 16) / float(1 << 48))


def _headcount(lo: float, hi: float) -> int:
    """How many people to draw from one band. One per ~4 years of span.

    ⚠ COLLAPSING A BAND ONTO ONE PERSON THROWS THE BAND AWAY, and it was
    measured doing exactly that: a 41-50 bundle rendered as a single person
    lands wherever the hash puts them, so the library's only two 45-plus women
    vanished and a `women 45-60` buy fell from 2 types to 0. The band asserts
    that this opinion is held across ten years of life; drawing three people
    across those ten years is the faithful reading, drawing one is not.
    """
    return max(1, min(_MAX_PEOPLE_PER_BAND, 1 + int(hi - lo) // _YEARS_PER_PERSON))


def to_people(
    bundle: DemographicBundle, label: str, idx: int
) -> list[DemographicBundle]:
    """One band bundle -> the specific people it was asserting exist.

    Stratified: person i is drawn from the i-th sub-interval of the band, so
    two people from one band can never collide and the whole span stays covered.
    The position *within* the sub-interval is jittered off the label, so every
    41-50 bundle in the library does not produce the same three ages.

    ⚠ AGE AND INCOME MOVE TOGETHER, on one shared position. Drawing them
    independently would mint the 47-year-old on a starter salary and the
    23-year-old at the top of the band inside the SAME career — and
    `DemographicBundle`'s whole contract is that a bundle stays internally
    coherent ("settled doctor, 45-54, affluent" — never "family head on
    <Rs3.5L").
    """
    p = bundle.point
    k = _headcount(p.age_min, p.age_max)
    out = []
    for i in range(k):
        t = (i + _jitter(f"{label}|{idx}|{i}")) / k
        age = int(round(p.age_min + t * (p.age_max - p.age_min)))
        income = round(
            p.income_lpa_min + t * (p.income_lpa_max - p.income_lpa_min), 1
        )
        out.append(DemographicBundle(
            point=DemographicPoint(
                gender=p.gender,
                age_min=age, age_max=age,
                income_lpa_min=income, income_lpa_max=income,
                geography=p.geography,
                occupation_hint=p.occupation_hint,
                household_hint=p.household_hint,
            ),
            # Split so the band's total share of its disposition is unchanged —
            # this redistributes a population, it must not re-weight one.
            weight=bundle.weight / k,
        ))
    return out


def convert(disposition: NamedDisposition) -> NamedDisposition:
    """The same opinion, now held by specific people instead of by bands.

    ⚠ The anchor, the vector and the notes are untouched. This script changes
    WHO holds an opinion, never WHAT the opinion is -- so a conversion can never
    move a verdict by editing what the panel thinks.
    """
    return NamedDisposition(
        label=disposition.label,
        vector=disposition.vector,
        anchor=disposition.anchor,
        notes=disposition.notes,
        provisional=disposition.provisional,
        # ⚠ Carried, not defaulted. EMPTY MEANS UNSCOPED, NEVER MISMATCHED —
        # dropping the field would turn an unscoped disposition into a
        # differently-unscoped one on paper and churn `disposition_version`.
        authored_for=list(disposition.authored_for),
        demographic_bundles=[
            person
            for i, b in enumerate(disposition.demographic_bundles)
            for person in to_people(b, disposition.label, i)
        ],
    )


def _reach(dispositions: list[NamedDisposition], frame: DemographicPoint) -> int:
    from agent.panel import audience_mass
    return sum(1 for d in dispositions if audience_mass(d, [frame]) > 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="a generated-audience JSON or a library.json")
    ap.add_argument("--out", help="output path (default: <input>_people.json)")
    args = ap.parse_args()

    src = Path(args.path)
    payload = json.loads(src.read_text())
    if "dispositions" not in payload:
        sys.exit("no `dispositions` in that file — nothing to convert")

    before = [NamedDisposition.from_dict(d) for d in payload["dispositions"]]
    after = [convert(d) for d in before]
    for d in after:
        d.validate()

    n_people = sum(len(d.demographic_bundles) for d in after)
    print(f"{len(after)} opinions, {n_people} specific people  "
          f"($0, deterministic, no API call)\n")

    ages = sorted({b.point.age_min for d in after for b in d.demographic_bundles})
    print(f"distinct ages in the population: {len(ages)}  "
          f"(from {ages[0]} to {ages[-1]})")

    print(f"\n{'brief':<40}{'bands (before)':>16}{'people (after)':>16}")
    for label, gender, lo, hi, ilo, ihi in _REPORT_BRIEFS:
        f = DemographicPoint(gender=gender, age_min=lo, age_max=hi,
                             income_lpa_min=ilo, income_lpa_max=ihi,
                             geography="any")
        print(f"{label:<40}{_reach(before, f):>16}{_reach(after, f):>16}")

    # ⚠ NEVER over the input. The file being read is a paid artifact and the
    # brand installed from it is the $8-checkpoint comparison run.
    out = Path(args.out) if args.out else src.with_name(f"{src.stem}_people.json")
    if out.resolve() == src.resolve():
        sys.exit("refusing to overwrite the input — pass a different --out")
    payload["dispositions"] = [d.to_dict() for d in after]

    # ⚠ `raw` MUST BE CONVERTED TOO, or the file disagrees with itself. `raw` is
    # the model's own output and it is what every gate in
    # `check_generated_audience.py` reads — leaving it in band shape produces a
    # file whose dispositions are people and whose gates say "this is a BAND,
    # not a person", 77 times. Caught by gate 5 the first time this ran.
    by_label = {d.label: d for d in after}
    for t in payload.get("raw", []):
        d = by_label.get(t.get("label"))
        if d is None:
            continue
        t["bundles"] = [
            {"gender": b.point.gender,
             "age": b.point.age_min, "income_lpa": b.point.income_lpa_min,
             "geography": b.point.geography,
             "occupation_hint": b.point.occupation_hint,
             "household_hint": b.point.household_hint,
             "weight": b.weight}
            for b in d.demographic_bundles
        ]
    payload["converted_from"] = src.name
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\n-> {out}")
    print("NOTHING has been installed. The input file is untouched.")


if __name__ == "__main__":
    main()
