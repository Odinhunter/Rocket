#!/usr/bin/env python3
"""Do the generated PEOPLE hold together as people?  ($0, offline, no API calls)

    .venv/bin/python scripts/audit_generated_people.py generated_audience_w4560_t3_v2.json

⚠ THIS IS NOT A GATE AND MUST NOT BECOME ONE. `check_generated_audience.py`
decides admissibility; this only REPORTS. Every check below rests on a fuzzy
semantic map (life-stage -> likely age, phrase -> occupation bucket), and the
repo has already learned twice what gating on a fuzzy classifier does: it
teaches the generator to write around the classifier. Gate on this and the next
region simply stops naming its children's life stages — the arithmetic stays
wrong and the alarm goes quiet. Same reasoning as `_report_mix` in
`generate_audience.py`, written down there at length.

WHY IT EXISTS. The user read the first two regions and caught what no gate had:
"a 55-year-old woman cannot have a son who is training for the police force
right now." She was right, and it generalises — the generator writes each
household line on its own and never checks it against the woman's own age.
Nothing in the prompt carries a fact about when women in this population marry
or give birth, and `household_hint` was described to the model in twenty-three
characters ("ONE household detail. Same bans.") against `occupation_hint`'s
seven hundred.

WHAT IT MEASURES, and what each number is worth:

  1. AGE AT FIRST BIRTH, from her children. Only counts a child who is an ONLY
     child or explicitly the ELDEST — the youngest of four being in school says
     nothing about when she started. Every life-stage bound is the OLDEST the
     child could plausibly be, so the implied age at birth comes out as LOW as
     the text permits: the number is a floor, and the real figure is worse.
  2. AGE AT FIRST BIRTH, from her grandchildren. Independent of (1) and pulls
     the OTHER way — assumes her own child became a parent at GEN2. Its job is
     to catch the impossible tail (a 49-year-old with school-age grandchildren
     needs to have given birth at 16).
  3. OCCUPATION CLUSTERING. ⚠ The one that corrects an earlier claim. "190
     distinct occupation strings of 192" was reported as diversity; it is
     string distinctness, and it passes while the same nine or ten jobs repeat
     under different wording. A vacuous-measure shape — see memory
     `vacuous_test_shapes`.
  4. FAMILY SIZE, DUPLICATE SLOTS, REPEATED SUPPORTING CHARACTERS, RETIREMENT
     ARITHMETIC, TIER LABELLING. Cheap consistency checks, each of which found
     something real on v2.

⚠ NO POPULATION TARGET IS ASSERTED HERE. There is deliberately no "expected"
column for age at first birth: the sourced figure belongs in
`agent/demography.py` next to the PLFS table, cited, and nothing may be typed
in from memory. Until it is sourced this script reports the SHAPE of what was
generated — a distribution with no left tail is damning without needing a
reference number to compare against.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict

# --------------------------------------------------------------------------
# Life stages -> the OLDEST a child at that stage plausibly is.
# ⚠ Generous ON PURPOSE, in the generator's favour. Read with central
# estimates instead, every implied age below rises by roughly three years.
# --------------------------------------------------------------------------
CHILD_STAGES = [
    (r"\bmiddle school\b", 14, "middle school"),
    (r"\bclass (?:5|five|6|six|7|seven|8|eight|9|nine)\b", 15, "class 5-9"),
    (r"\bclass (?:10|ten)\b|\bboard exam", 17, "class 10 / boards"),
    (r"school-going|school-age|\bin school\b|still in school", 17, "school-going"),
    (r"\bclass (?:11|eleven|12|twelve)\b|\bintermediate\b", 19, "class 11-12"),
    (r"engineering entrance|\bentrance\b", 19, "entrance exam"),
    (r"\bdiploma\b|\bITI\b", 21, "diploma / ITI"),
    (r"nursing (?:course|college)|B\.?Com|B\.?Ed|engineering (?:college|hostel)"
     r"|\bcollege\b|\bhostel\b|\bcourse\b|final year|stud(?:ies|ying)", 23, "college"),
    (r"police recruitment|railway exam|bank exam|looking for work", 26, "entry job hunt"),
]

# Grandchild stages, for the second route.
GRANDCHILD_STAGES = [
    (r"toddler|\bsmall grandson\b|wakes at night|grandchild expected", 2, "toddler/newborn"),
    (r"granddaughter slokas|minds the grandson", 6, "young child"),
    (r"grandchild.{0,30}same room|sleep in her room", 7, "young child"),
    (r"class (?:5|five)\b", 10, "class 5"),
    (r"class (?:6|six)\b", 11, "class 6"),
    (r"(?:grandchild|grandson|granddaughter|grandchildren).{0,40}(?:school|homework)"
     r"|(?:school|homework).{0,40}(?:grandchild|grandson|granddaughter|grandchildren)"
     r"|walks the grandchildren to school|takes the two grandsons", 9, "school-age"),
]
# The age her own child was when the grandchild arrived. One assumption, stated.
GEN2 = 24

OWN_CHILD = re.compile(r"\b(?:one|a|an|her|his|the)?\s*(son|daughter)\b", re.I)
SIBLINGS = re.compile(
    r"\b(children|two|three|four|both|sons|daughters|twins|elder|younger|eldest|youngest|other)\b", re.I)
ELDEST = re.compile(r"\b(eldest|elder)\b", re.I)
# Somebody else's child tells us nothing about her own births.
NOT_HERS = re.compile(
    r"grandchild|grandson|granddaughter|daughter-in-law|son-in-law|\bniece\b|\bnephew\b"
    r"|sister's|brother's|son's (?:wife|family)|daughter's (?:family|husband)", re.I)
# ⚠ A child who WORKS at a school is not a child IN school. This one false
# positive ("son teaches at a private school") was the worst case in the first
# draft of this instrument, and it inflated the headline. Keep it.
WORKS_AT_SCHOOL = re.compile(
    r"teach|works at a (?:private )?school|school van|headmaster|principal", re.I)

OCCUPATION_BUCKETS = [
    ("stitching / tailoring", r"stitch|tailoring|petticoat|blouse|embroidery|sews"),
    ("tiffin / cooking for sale",
     r"tiffin|cooks and (?:delivers|sends|packs|serves)|canteen|cook in two houses|cooks and cleans"),
    ("home tuition", r"tuition|teaches (?:maths|Hindi|Telugu|Marathi|Carnatic)|tuitions"),
    ("unpaid bookkeeping at the family shop",
     r"(?:accounts book|ledger|daybook|books|credit register|cash book|billing).{0,60}(?:husband|family)"
     r"|takes no salary|draws no salary|unpaid|takes nothing for it"),
    ("beauty parlour", r"beauty parlour|ladies. parlour|parlour"),
    ("anganwadi / ASHA", r"anganwadi|ASHA"),
    ("nurse / lab / health worker", r"\bnurse\b|lab technician|nurse-aide|health worker"),
    ("shop counter, family shop", r"counter|minds the family|sits at (?:the|her)"),
    ("buffalo / milk round", r"buffalo|milk round|milk-selling|sells the (?:morning )?milk|cow and milk"),
    ("school teacher", r"\bteacher\b|teaches .{0,20}at a|primary school teacher|senior teacher"),
]

SUPPORTING_CHARACTERS = [
    ("husband drives a school van", r"school van"),
    ("husband works in the Gulf", r"\bGulf\b"),
    ("a cooperative bank, hers or his", r"cooperative bank"),
    ("a bedridden relative", r"bedridden|cannot walk|needs help walking"),
    ("mother-in-law in the house", r"mother-in-law"),
    ("husband posted out of town", r"posted (?:out of town|at|in)|works away|travels for"),
    ("bhajan / satsang / mahila group", r"bhajan|satsang|temple committee|mahila|bachat gat"),
]

RETIREMENT_AGE = 58  # earliest ordinary government / bank retirement in India
WORD_NUMBERS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def people(path: str) -> list[dict]:
    data = json.loads(open(path).read())
    return [b["point"] for d in data["dispositions"] for b in d["demographic_bundles"]]


def _clauses(text: str) -> list[str]:
    return [c.strip() for c in re.split(r"[;,]", text) if c.strip()]


def _stage(text: str, stages, pick_oldest: bool = False):
    best = None
    for pat, age, label in stages:
        if re.search(pat, text, re.I):
            better = (best is None
                      or (age > best[0] if pick_oldest else age < best[0]))
            if better:
                best = (age, label)
    return best


def first_birth_from_children(P: list[dict]) -> list[tuple]:
    """Only hints that pin her FIRST birth: an only child, or the eldest."""
    out = []
    for p in P:
        hint = p["household_hint"]
        best = None
        for clause in _clauses(hint):
            if NOT_HERS.search(clause) or WORKS_AT_SCHOOL.search(clause):
                continue
            if not OWN_CHILD.search(clause):
                continue
            st = _stage(clause, CHILD_STAGES)
            if st and (best is None or st[0] < best[0]):
                best = (*st, clause)
        if not best:
            continue
        child_age, label, clause = best
        is_eldest = bool(ELDEST.search(clause))
        has_siblings = bool(SIBLINGS.search(hint))
        if not is_eldest and has_siblings:
            continue          # youngest of several says nothing about the first
        out.append((p["age_min"] - child_age, p["age_min"], child_age, label, hint))
    return sorted(out)


def first_birth_from_grandchildren(P: list[dict]) -> list[tuple]:
    out = []
    for p in P:
        text = f'{p["occupation_hint"]} || {p["household_hint"]}'
        if not re.search(r"grandchild|grandson|granddaughter|grandchildren", text, re.I):
            continue
        st = _stage(text, GRANDCHILD_STAGES, pick_oldest=True)
        if not st:
            continue
        g, label = st
        out.append((p["age_min"] - g - GEN2, p["age_min"], g, label, text))
    return sorted(out)


def report(path: str) -> None:
    P = people(path)
    n = len(P)
    print(f"==== {path}   ({n} people)\n")

    kids = first_birth_from_children(P)
    if kids:
        ages = [k[0] for k in kids]
        print(f"1) AGE AT FIRST BIRTH, from her own children — {len(kids)} datable")
        print(f"   min {min(ages)}   median {statistics.median(ages)}   max {max(ages)}")
        print(f"   under 23: {len([a for a in ages if a < 23])}"
              f"   |  30 or later: {len([a for a in ages if a >= 30])}")
        print("   ⚠ every bound is the child's OLDEST plausible age, so these are floors")
        for implied, age, ca, label, hint in kids[::-1][:8]:
            print(f"     {age}y, child ~{ca} ({label}) -> first birth at ~{implied}  | {hint[:78]}")
        print()

    grands = first_birth_from_grandchildren(P)
    if grands:
        ages = [g[0] for g in grands]
        impossible = [g for g in grands if g[0] < 18]
        print(f"2) AGE AT FIRST BIRTH, from her grandchildren — {len(grands)} datable"
              f"  (assumes her child became a parent at {GEN2})")
        print(f"   min {min(ages)}   median {statistics.median(ages)}   max {max(ages)}")
        print(f"   ARITHMETICALLY IMPOSSIBLE (under 18): {len(impossible)}")
        for implied, age, g, label, text in impossible:
            print(f"     {age}y, grandchild ~{g} ({label}) -> she was ~{implied}  | {text[:78]}")
        print()

    covered: set[int] = set()
    print("3) OCCUPATION CLUSTERING")
    hits = []
    for name, pat in OCCUPATION_BUCKETS:
        idx = [i for i, p in enumerate(P) if re.search(pat, p["occupation_hint"], re.I)]
        hits.append((len(idx), name))
        covered |= set(idx)
    for count, name in sorted(hits, reverse=True):
        print(f"   {count:3d}  ({100 * count / n:4.1f}%)  {name}")
    print(f"   ---> {len(covered)} of {n} people ({100 * len(covered) / n:.0f}%) "
          f"in {len(OCCUPATION_BUCKETS)} job types")
    print(f"   ---> distinct occupation STRINGS: {len(set(p['occupation_hint'] for p in P))} of {n}"
          f"   ⚠ string distinctness is NOT job diversity")
    print()

    only, several, none_ = 0, 0, 0
    kid_word = re.compile(r"\b(son|daughter|children|child)\b", re.I)
    for p in P:
        t = f'{p["household_hint"]} {p["occupation_hint"]}'
        if not kid_word.search(t):
            none_ += 1
        elif SIBLINGS.search(t):
            several += 1
        else:
            only += 1
    print("4) FAMILY SIZE implied")
    print(f"   {several:3d}  ({100 * several / n:4.1f}%)  two or more children")
    print(f"   {only:3d}  ({100 * only / n:4.1f}%)  exactly one child")
    print(f"   {none_:3d}  ({100 * none_ / n:4.1f}%)  no children mentioned")
    print()

    print("5) REPEATED SUPPORTING CHARACTERS")
    for name, pat in SUPPORTING_CHARACTERS:
        c = sum(1 for p in P
                if re.search(pat, f'{p["occupation_hint"]} {p["household_hint"]}', re.I))
        print(f"   {c:3d}  ({100 * c / n:4.1f}%)  {name}")
    print()

    slots = Counter((p["age_min"], p["income_lpa_min"], p["geography"]) for p in P)
    shared = {k: v for k, v in slots.items() if v > 1}
    print("6) PEOPLE SHARING AN (age, income, town) SLOT")
    for (age, inc, geo), c in sorted(shared.items(), key=lambda x: -x[1]):
        print(f"   {c}x  {age}y  ₹{inc}L  {geo}")
    print(f"   ---> {sum(shared.values())} of {n}")
    print()

    print(f"7) RETIREMENT ARITHMETIC (ordinary retirement is {RETIREMENT_AGE}-60)")
    for p in P:
        text = f'{p["occupation_hint"]} || {p["household_hint"]}'
        if re.search(r"^retired|; now|, now", p["occupation_hint"], re.I) \
                and re.search(r"retired", p["occupation_hint"], re.I) \
                and p["age_min"] < RETIREMENT_AGE:
            print(f'   {p["age_min"]}y retired already  | {p["occupation_hint"][:80]}')
        m = re.search(r"(\w+) years? from retirement", text, re.I)
        if m and WORD_NUMBERS.get(m.group(1).lower()):
            retires = p["age_min"] + WORD_NUMBERS[m.group(1).lower()]
            if retires > 60:
                print(f'   {p["age_min"]}y "{m.group(0)}" -> retires at {retires}'
                      f'  | {p["occupation_hint"][:60]}')
    print()

    # ⚠ THE PROTAGONIST-ABSENCE CHECK. Three times now the generator has been
    # unable to write a LACK for the woman the panel is about, while writing it
    # freely for the people around her: no paid work (the homemaker gap, 1 of
    # 194), no second income after retiring (11 of 12 re-employed), no living
    # husband (below). Counting her against the household around her is what
    # makes the asymmetry visible — a bare widow count looks merely low.
    hers = [p for p in P
            if re.search(r"\bwidow(?:ed)?\b", f'{p["occupation_hint"]} {p["household_hint"]}', re.I)
            and not re.search(r"widowed (?:sister|mother|brother)|sister-in-law",
                              f'{p["occupation_hint"]} {p["household_hint"]}', re.I)]
    others = [p for p in P
              if re.search(r"widowed (?:sister|mother|sister-in-law)",
                           f'{p["occupation_hint"]} {p["household_hint"]}', re.I)]
    print("8) WIDOWHOOD — hers, against the household's")
    print(f"   {len(hers):3d}  ({100 * len(hers) / n:4.1f}%)  SHE is widowed")
    print(f"   {len(others):3d}  ({100 * len(others) / n:4.1f}%)  someone ELSE in the house is widowed")
    print("   ⚠ direction only — no sourced target; see the sourcing list in "
          "docs/people_audit_w4560_t3.md")
    print()

    # ⚠ REPORTED, AND DELIBERATELY NOT ACTED ON. Whether the panel should carry
    # religious community at all is a product decision belonging to the user,
    # and the obvious "fix" — a name and a garment — is worse than the gap.
    print("9) COMMUNITY MARKERS  (reported only — the user's call, see the audit doc)")
    for name, pat in [
        ("Hindu", r"bhajan|temple|satsang|puja|tulsi|mandir"),
        ("Sikh", r"gurudwara|gurdwara"),
        ("Christian", r"church"),
        ("Muslim", r"\bmasjid|namaz|madrasa|\bEid\b|dargah|\bIdgah\b"),
    ]:
        c = sum(1 for p in P
                if re.search(pat, f'{p["occupation_hint"]} {p["household_hint"]}', re.I))
        print(f"   {c:3d}  ({100 * c / n:4.1f}%)  {name}")
    print()

    labels = defaultdict(set)
    for p in P:
        town, _, label = p["geography"].partition(" / ")
        labels[town].add(label)
    mixed = sorted(t for t, v in labels.items() if len(v) > 1)
    print("10) TIER LABEL")
    print(f"   {len(labels)} distinct towns")
    print(f"   labelled BOTH 'tier-3 town' and 'tier-3 city': {len(mixed)}  {mixed}")
    print()

    inc = sorted(p["income_lpa_min"] for p in P)
    print("11) HOUSEHOLD INCOME, ₹ lakh/yr  (reported, not judged — no sourced target)")
    print(f"   min {inc[0]}   p25 {inc[n // 4]}   median {statistics.median(inc)}"
          f"   p75 {inc[3 * n // 4]}   max {inc[-1]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for path in sys.argv[1:]:
        report(path)
