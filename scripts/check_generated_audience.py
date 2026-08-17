#!/usr/bin/env python3
"""Is a generated audience admissible?  ($0, offline, no API calls)

    .venv/bin/python scripts/check_generated_audience.py generated_audience.json

Four gates, run before a generated library is allowed anywhere near a paid run.
None of them tests whether the audience is TRUE — see the honesty note at the
bottom. They test whether it is well-formed, bounded, distinct, and clean.

GATE 1 — CEILINGS. The one that matters. A buyer type without explicit refusals
is a buyer type that likes every ad it is shown, and a panel that likes
everything measures nothing. L3 must say what this person does NOT know; L4
must say what they REJECT. This is the single failure mode that would make a
generated library look healthier than the hand-built one while being worse.

GATE 2 — DISTINCTNESS. Two types occupying the same eight-axis coordinate are
the same person twice, whatever their names. The panel already collapsed 100
agents into 3 opinions once; this is the check that catches it happening at the
authoring layer instead of after a $4 run.

GATE 3 — THE INCOME SEAM. `occupation_hint` and `household_hint` reach the
persona writer and are NOT redacted, unlike income. A ₹ figure or a tier word
there walks straight past a redaction that exists because handing the writer
income costs -4.51 on SimBench. Same seam as
test_no_hint_smuggles_income_past_the_writer_redaction — ⚠ but NOT the same
pattern, and deliberately not. That test guards INSTALLED dispositions and
matches only a rupee figure or a tier word; this gate runs BEFORE install, on
output nobody has paid to render yet, so it is broader on purpose ("earn",
"affluent", "salaried"). Do not consolidate them into one regex: tightening
the test to this breadth would red the suite on libraries already on disk,
and loosening this to the test's breadth would let an authoring habit through
at the only stage where it is still free to fix.

GATE 4 — GRID COVERAGE. Mutually exclusive: no cell twice. Collectively
exhaustive: report the holes rather than pretending they are not there. ⚠ A
REFUSED cell is ADDRESSED, not missing — demanding a type in every cell of a
narrow region is a demand to invent people nobody would meet there.

GATE 5 — PEOPLE. Every bundle must be one specific person (one age, one income)
and must fall inside the region the file was generated for. A BAND gets clipped
to the buy at run time, which is what simulated a "tier-2 staff nurse" under a
tier-3 brief; a person outside the region can never be selected at all.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# A hint may say what someone does for a living. It may not price them.
_MONEY = re.compile(
    r"₹|\brs\.?\b|\blpa\b|\blakh|\bcrore|\bsalar|\bincome\b|\bearn|\baffluen|"
    r"\bwealthy\b|\brich\b|\bpoor\b|\bbudget[- ]conscious\b|\bwell[- ]off\b|"
    r"\bhigh[- ]earning\b|\blow[- ]income\b|\bupper[- ]middle\b",
    re.I,
)
# ⚠ "TAKES NO SALARY" IS NOT AN INCOME LEAK — IT IS THE UNPAID FAMILY HELPER,
# AND THE SYSTEM ASKS FOR HER BY NAME. `demography.brief` offers "helps at her
# husband's hardware shop in the afternoons, takes no salary from it" as a
# VERBATIM exemplar, and `_tool`'s `occupation_hint` description repeats it.
# A gate that bans the canonical English for a shape the prompt mandates makes
# the two halves of this system inconsistent by construction, and the failure
# mode is the one `agent/demography.py` exists to prevent: the generator
# quietly stops writing women who do not draw a wage.
#
# Statable WITHOUT reference to any output, which is the test that separates a
# fix from rigging: this gate's own rule is "may say what someone does for a
# living, may not price them". A negated salary says what she does and prices
# nobody — it is an employment ARRANGEMENT, not an income level, and a woman
# who takes no salary from the family shop may live in a ₹2L or a ₹40L
# household. The redaction it guards is over `income_lpa`, which is untouched.
#
# ⚠ NEGATED ONLY. "salary of ₹40,000", "a good salary" and "salaried job" all
# still fail — they price her. Mutation-proved in `tests/test_demography.py`.
_NO_SALARY = re.compile(
    r"\b(?:takes?|draws?|gets?|receives?|paid)\s+no\s+salary\b|\bno\s+salary\b|"
    r"\bwithout\s+(?:a\s+)?salary\b|\bunsalaried\b",
    re.I,
)
_REFUSAL = re.compile(r"does not|doesn't|does NOT|never |cannot|can't|won't|will not", re.I)
_REJECT = re.compile(r"reject|refus|distrust|won't|will not|dismiss|puts? .* off|"
                     r"not for (me|them|her|him)|no interest|switches off", re.I)


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}")


def ceiling_failures(t: dict) -> list[str]:
    """Every way this one type fails GATE 1, as printable clauses. Empty list
    means it carries both ceilings.

    ⚠ THIS IS THE SINGLE DEFINITION AND `generate_audience.py --fill` IMPORTS
    IT. A type that fails here is a type the generator must re-ask for, and
    two copies of the rule would drift into two opinions about what a usable
    buyer type is — the exact way `loyalist_office_jar_kitkat` survived
    `--repair` (all eight axes, unique coordinate, and `l1_context == "x"`).
    """
    out = []
    l3, l4 = t.get("l3_knowledge", ""), t.get("l4_stance", "")
    n_not = len(re.findall(r"does not|doesn't|does NOT", l3, re.I))
    if n_not < 2:
        out.append(f"L3 has {n_not} 'does NOT' clause(s), needs 2 — "
                   f"the expertise ceiling is missing")
    elif not _REFUSAL.search(l3):
        out.append("L3 states no refusal at all")
    if not _REJECT.search(l4):
        out.append("L4 rejects nothing — this person will like every ad")
    return out


def gate_ceilings(raw: list[dict]) -> int:
    print("\nGATE 1 — CEILINGS (the refusals that stop the panel liking everything)")
    bad = 0
    for t in raw:
        for clause in ceiling_failures(t):
            _fail(f"{t['label']}: {clause}")
            bad += 1
    print(f"  {len(raw) - bad if bad <= len(raw) else 0} of {len(raw)} types carry both ceilings"
          if bad else f"  ✓ all {len(raw)} types carry an expertise ceiling and a rejection")
    return bad


_AXES = ("category_relationship", "brand_stance", "price_orientation",
         "decision_driver", "category_involvement", "prior_experience_valence",
         "channel_behavior", "life_stage")


def distinctness_key(t: dict) -> tuple:
    """What makes two buyer types the same person twice.

    ⚠ THE 8-AXIS COORDINATE ALONE IS NOT ENOUGH ONCE GENDER IS A GENERATION
    AXIS, and it bites on the first gendered run rather than eventually.
    `gender` is not one of the eight axes — checked against
    `agent.vectors._VALID_DISPOSITION` — so a men's loyalist/desk_slump and a
    women's loyalist/desk_slump land on an IDENTICAL coordinate. Under the old
    key the second is reported as a duplicate opinion and `--fill` re-rolls it,
    which would delete exactly the gender difference the region was generated
    to capture.

    ⚠ THE OCCASION IS PART OF IT TOO, added 2026-08-16 after a 64-cell region
    generation collided twice in a row. The eight axes have NO occasion
    component, so the same stance in two different moments — a pragmatist at the
    4pm slump and a pragmatist on the road — is FORCED onto one coordinate no
    matter how differently the two are written. With 64 cells drawn from eight
    stances, that is arithmetic, not sloppiness.

    ⚠ AND NOTHING DOWNSTREAM KEYS ON THE COORDINATE, which is what makes this
    safe rather than a gate weakened to let output through. Checked, not
    assumed: `PanelAgent.segment_key` groups L2 by the disposition LABEL, and
    `persona_core_hash` digests the ANCHOR — and the anchors of two cells differ
    completely, because each is written for its own moment. Two same-coordinate
    types in different cells render as different people, run as different
    segments, and are reported separately.

    ⚠ It stays strict WITHIN an occasion, which is the case that would really be
    one opinion twice. Gate 4 separately forbids two types in one cell.

    ⚠ THIS IS THE SINGLE DEFINITION AND `generate_audience.py` IMPORTS IT, for
    the same reason `ceiling_failures` lives here: a type this calls a duplicate
    is a type the generator must re-ask for, and two copies of the rule drift
    into two opinions about what a distinct buyer type is.
    """
    coord = tuple(t[a] for a in _AXES)
    genders = tuple(sorted({b.get("gender", "any") for b in t.get("bundles", [])}))
    return coord + (genders, t.get("occasion", ""))


def gate_distinct(raw: list[dict]) -> int:
    print("\nGATE 2 — DISTINCTNESS (is any of these the same person twice?)")
    seen: dict[tuple, list[str]] = collections.defaultdict(list)
    for t in raw:
        seen[distinctness_key(t)].append(t["label"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    for coord, labels in dupes.items():
        _fail(f"identical stance coordinate and gender: {', '.join(labels)}")
    labels = [t["label"] for t in raw]
    if len(set(labels)) != len(labels):
        rep = [l for l, n in collections.Counter(labels).items() if n > 1]
        _fail(f"duplicate labels: {rep}")
    print(f"  {len(seen)} distinct stance coordinates across {len(raw)} types"
          + ("" if not dupes else f"  <- {sum(len(v) for v in dupes.values())} collide"))
    return sum(len(v) - 1 for v in dupes.values())


def gate_income_seam(raw: list[dict]) -> int:
    print("\nGATE 3 — THE INCOME SEAM (hints reach the writer; income must not)")
    bad = 0
    for t in raw:
        for b in t["bundles"]:
            for field in ("occupation_hint", "household_hint"):
                # ⚠ Strip the negated forms FIRST, then look for money in what
                # is left — see `_NO_SALARY`. Doing it as a removal pass rather
                # than a negative lookaround keeps every other money word live
                # in the same sentence: "helps at the shop, takes no salary,
                # household earns ₹8L" still fails on the ₹ and on "earn".
                text = _NO_SALARY.sub(" ", b[field] or "")
                hit = _MONEY.search(text)
                if hit:
                    _fail(f"{t['label']}: {field} smuggles income — "
                          f"{b[field]!r} (matched {hit.group(0)!r})")
                    bad += 1
    print(f"  ✓ no hint carries a ₹ figure or an income word" if not bad
          else f"  {bad} hint(s) leak income past the redaction")
    return bad


def gate_people(raw: list[dict], region: dict | None) -> int:
    """GATE 5 — ARE THESE PEOPLE, AND ARE THEY IN THE ROOM THEY WERE WRITTEN FOR?

    Two checks the other four cannot make.

    ⚠ A BAND IS NOT A PERSON. A bundle carrying an age RANGE gets clipped to the
    buy at run time, and clipping is what rendered a "Coimbatore / tier-2 staff
    nurse" under a tier-3 brief and stranded a team lead outside the income band
    their career needs. A person — one age, one income — is selected in-or-out by
    any customer-chosen range, and `panel._clip_point` leaves them untouched.

    ⚠ A PERSON OUTSIDE THE REGION CAN NEVER BE SELECTED by the buy that paid to
    write them. They still cost a render and still dilute the grid.
    """
    print("\nGATE 5 — PEOPLE (one age, one income, inside the declared region)")
    bad = 0
    for t in raw:
        for b in t.get("bundles", []):
            if "age" not in b or "income_lpa" not in b:
                _fail(f"{t['label']}: bundle is a BAND, not a person "
                      f"(no `age`/`income_lpa`) — it will be clipped to the buy")
                bad += 1
                continue
            if region is None:
                continue
            age, inc, g = int(b["age"]), float(b["income_lpa"]), b["gender"]
            if region["gender"] != "any" and g not in (region["gender"], "any"):
                _fail(f"{t['label']}: {g} in a {region['gender']} region")
                bad += 1
            elif not (region["age_min"] <= age <= region["age_max"]):
                _fail(f"{t['label']}: aged {age}, region is "
                      f"{region['age_min']}-{region['age_max']}")
                bad += 1
            elif not (region["income_min"] <= inc <= region["income_max"]):
                _fail(f"{t['label']}: ₹{inc:g}L, region is "
                      f"₹{region['income_min']:g}-{region['income_max']:g}L")
                bad += 1
    people = [b for t in raw for b in t.get("bundles", [])]
    ages = sorted({int(b["age"]) for b in people if "age" in b})
    if not bad:
        print(f"  ✓ {len(people)} specific people"
              + (f", aged {ages[0]}-{ages[-1]} across {len(ages)} distinct ages"
                 if ages else "")
              + (", all inside the region" if region else
                 " — ⚠ NO REGION on file, so containment was not checked"))
    else:
        print(f"  {bad} problem(s) across {len(people)} bundles")
    return bad


def gate_grid(raw: list[dict], grid: dict, refusals: list[dict]) -> int:
    print("\nGATE 4 — GRID COVERAGE (mutually exclusive, collectively exhaustive)")
    cells = collections.Counter((t["occasion"], t["stance"]) for t in raw)
    dupes = {c: n for c, n in cells.items() if n > 1}
    for c, n in dupes.items():
        _fail(f"cell {c[0]}/{c[1]} filled {n} times — not mutually exclusive")
    by_occ = collections.Counter(t["occasion"] for t in raw)
    total = len(grid["occasions"]) * len(grid["stances"])
    # ⚠ A REFUSED CELL IS ANSWERED, NOT MISSING. Collective exhaustiveness means
    # every cell has been ADDRESSED, not that every cell holds a person. For a
    # narrow region — women 55-75 in tier-3 — demanding a type per cell is a
    # demand to invent people, and these gates test form rather than truth so
    # nothing downstream would catch the invention. A refusal is a claim about
    # the market that the brand manager reads.
    refused = {(r["occasion"], r["stance"]): r["reason"] for r in refusals}
    both = set(cells) & set(refused)
    for c in sorted(both):
        _fail(f"cell {c[0]}/{c[1]} is BOTH filled and refused — one of the two is wrong")
    print(f"  {len(cells)} cells filled, {len(refused)} refused, "
          f"{total - len(cells) - len(refused)} unaddressed, of {total} in the grid")
    for o in grid["occasions"]:
        k = o["key"]
        n_ref = sum(1 for (occ, _s) in refused if occ == k)
        print(f"     {k:24} {by_occ.get(k, 0)} type(s)"
              + (f", {n_ref} refused" if n_ref else "")
              + ("   <- EMPTY" if not by_occ.get(k) and not n_ref else ""))
    if refused:
        print("\n  refused — nobody in this region holds these positions:")
        for (occ, stance), reason in sorted(refused.items()):
            print(f"     {stance} @ {occ}: {reason}")
    return len(dupes) + len(both)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    data = json.loads(Path(args.path).read_text())
    raw, grid = data["raw"], data["grid"]
    refusals = data.get("refusals") or []
    region = data.get("region")

    print("=" * 74)
    print(f"GENERATED AUDIENCE — {len(raw)} buyer types, market: {data['market']}")
    if region:
        print(f"region: {region['gender']}, {region['age_min']}-{region['age_max']}, "
              f"Rs{region['income_min']:g}-{region['income_max']:g} LPA, {region['tier']}")
    print("=" * 74)

    failures = (gate_ceilings(raw) + gate_distinct(raw)
                + gate_income_seam(raw) + gate_grid(raw, grid, refusals)
                + gate_people(raw, region))

    print("\n" + "=" * 74)
    if failures:
        print(f"NOT ADMISSIBLE — {failures} failure(s). Fix or regenerate before spending.")
    else:
        print("ADMISSIBLE — all five gates pass.")
    print("⚠ These gates test FORM, not TRUTH. A library that passes every one of")
    print("  them carries exactly the same never-validated-against-humans status as")
    print("  the hand-built one. What they buy is the right to spend $5 finding out")
    print("  whether the panel produces more than 3 opinions.")
    print("=" * 74)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
