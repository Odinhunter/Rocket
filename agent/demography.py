"""How many of the people in a demographic region actually hold a job.

⚠ WHY THIS MODULE EXISTS. The first region ever generated — women 45-60 in
tier-3 towns — produced 194 people and **zero homemakers**. Measured 2026-08-16
by regex over every `occupation_hint` and `household_hint` in
`generated_audience_w4560_t3.json`. Every one of the 194 had a paid job. In the
real population that region is majority housewife, so the panel was not a
sample of the buy, it was a sample of the minority of it that goes to work.

Three causes, all in the generator rather than the gates (`check_generated_
audience.py` was verified NOT to reject "housewife" or "homemaker"):

  1. the field is called `occupation_hint` and was described as "The job";
  2. all fifteen career exemplars in the system prompt were paid employment;
  3. the phrase "across the whole economy" reads as *the paid economy*.

Fixing the words alone would make homemakers POSSIBLE. It would not make them
the right FRACTION, because nothing told the writer what the fraction is. This
module is that number.

⚠ THIS IS WHO-LAYER DATA, NOT CATEGORY DATA. Labour force participation is a
fact about a population, not about snacking, so it does NOT belong in a market
pack. It is keyed by geography and gender and serves every category we ever
add. Per the architecture, WHO is rebuilt for a new geography and never for a
new product.

⚠ TIER IS MAPPED TO "URBAN", AND THAT IS A MODELLING ASSUMPTION, NOT A FACT.
The survey splits rural and urban; it does not know about tier-1/2/3. Tier-1,
-2 and -3 towns are all statistically urban, so all three map to the urban
column — but a tier-3 town sits closer to rural in character than a metro does,
and rural female participation is nearly twenty points HIGHER. So for tier-3
these numbers are, if anything, an UNDER-count of who works. Stated here rather
than buried, per the pack's own rule on assumptions.

SOURCE. All figures are from the Periodic Labour Force Survey (PLFS) 2023-24,
as computed from unit-level data by UNFPA India, *Gendered Pattern of Labour
Force Participation in India*, Analytical Paper Series #10, December 2025 —
https://india.unfpa.org/sites/default/files/pub-pdf/2date26-date3/Analytical%20Paper%20%2310%20-%20Labour%20Force%20Participation%20in%20India%20-%20Final_0.pdf

⚠ SECONDARY SOURCE, AND DELIBERATELY SO. Every mospi.gov.in and pib.gov.in URL
fails from this machine (self-signed certificate in chain / HTTP 403), so the
PLFS report itself could not be fetched — checked repeatedly on 2026-08-16 and
-17. The user's call was that the numbers do not need to be government-verified
or decimal-exact for this purpose. They are read off Figures 1, 2, 4.1 and 5 of
a UN agency paper computed from the official microdata, which is good enough to
set a proportion and is recorded as such rather than dressed up as official.

⚠ NOTHING HERE MAY BE FILLED IN FROM MEMORY. A fabricated statistics table
feeding every persona we ever generate is worse than the gap it closes, because
it looks sourced. Any row added later needs a URL that resolved.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Labour force participation, women, by age.  [Figure 2, 15+ years]
# --------------------------------------------------------------------------
# The share of women of that age who are in the labour force at all — working
# or actively looking. The complement is out of the labour force entirely, and
# above ~30 that complement is overwhelmingly full-time domestic work: PLFS
# reports "attended domestic duties" as its own activity status, and students
# have left the count by then.
#
# ⚠ NOT the same thing as "has a job". PLFS counts an unpaid family helper as
# employed, which is most of why the female figure moved 23.3 -> 41.7 between
# 2017-18 and 2023-24. A woman who keeps the books at her husband's shop for no
# wage is INSIDE this number. See WORK_SHAPE below — it is the more useful half.

_FEMALE_LFPR: list[tuple[int, int, float, float]] = [
    # age_lo, age_hi, rural %, urban %
    (15, 29, 30.8, 23.8),
    (30, 44, 64.0, 37.8),
    (45, 59, 66.5, 32.6),
    (60, 74, 31.3, 11.9),
    (75, 120, 6.2, 3.3),
]

# Totals, 15+: female 47.6 rural / 28.0 urban / 41.7 all-India. [Figures 1, 2]
# Male 15+: 78.8 all-India, up from 75.8 in 2017-18. [Figure 1]
#
# ⚠ THERE IS NO MALE AGE CURVE HERE AND IT IS NOT AN OVERSIGHT. The paper is
# female-focused and no age-banded male table was sourced. It is deliberately
# left absent rather than guessed: male participation IS near-universal through
# prime age, but "near-universal" is a recollection, not a citation, and the
# male side is not where the defect was. A male region therefore gets the work-
# SHAPE facts below, which are sourced, and no participation claim.
MALE_LFPR_15_PLUS = 78.8
FEMALE_LFPR_15_PLUS = 41.7

# --------------------------------------------------------------------------
# What the work IS, for the people who have it.  [Figures 4.1, 4.2, 5]
# --------------------------------------------------------------------------
# ⚠ THE MORE LOAD-BEARING HALF OF THIS MODULE. The generator's failure was not
# only that it employed everyone — it employed everyone in a SALARIED JOB, and
# a salaried job is what two thirds of Indian women workers do not have.

WORK_SHAPE = {
    #                self-employed, regular wage, casual labour   (% of workers)
    "female": (67, 16, 17),
    "male": (54, 25, 21),
}

# Share of employment that is informal, by settlement.  [Figure 5]
INFORMAL_SHARE = {
    ("female", "rural"): 96.7, ("female", "urban"): 77.2,
    ("male", "rural"): 93.5, ("male", "urban"): 75.5,
}

# Urban female participation by education — a U, and the bottom of the U is the
# aspirational middling household that a tier-2/3 panel is mostly made of.
# [Figure 2; rural figures kept for when a rural region is generated]
EDUCATION_LFPR = {
    #                          rural, urban
    "not literate": (54.7, 29.9),
    "up to primary": (56.8, 32.1),
    "middle/secondary": (40.3, 21.3),
    "higher secondary": (36.6, 15.8),
    "graduate and above": (44.1, 39.8),
}

# Marital status, female. [Figure 2] Kept because the urban column is the
# surprise: marriage barely moves urban participation (28.4 married vs 26.4
# never-married) while it moves rural participation by thirty points.
MARITAL_LFPR = {
    "never married": (25.1, 26.4),
    "currently married": (54.7, 28.4),
    "widowed/divorced/separated": (39.8, 28.4),
}


def settlement_for_tier(tier: str) -> str:
    """Which survey column a city tier reads from. See the assumption note in
    the module docstring — every tier is urban, including tier-3."""
    return "rural" if "rural" in (tier or "").lower() else "urban"


def female_lfpr(age_min: int, age_max: int, tier: str = "any") -> float:
    """The share of women aged `age_min`-`age_max` in the labour force.

    A region rarely lines up with a survey band, so bands are averaged weighted
    by how many YEARS of the region each one covers: women 45-60 is fifteen
    years of the 45-59 band at 32.6% and one year of the 60-74 band at 11.9%,
    giving 31.3%. Crude, and deliberately so — the number sets a proportion in
    a prompt, and a prompt cannot act on a tenth of a percent anyway.
    """
    col = 0 if settlement_for_tier(tier) == "rural" else 1
    years = weighted = 0.0
    for lo, hi, rural, urban in _FEMALE_LFPR:
        overlap = min(hi, age_max) - max(lo, age_min) + 1
        if overlap > 0:
            years += overlap
            weighted += overlap * (rural if col == 0 else urban)
    if not years:                       # a region entirely below 15
        return 0.0
    return round(weighted / years, 1)


def brief(gender: str, age_min: int, age_max: int, tier: str = "any") -> str:
    """The population paragraph for a region, for the generator's system block.

    Returns "" when there is nothing sourced to say — a region with no gender
    stated gets the work-shape facts but no participation claim, because
    averaging a sourced female rate with an unsourced male one would invent a
    number that is in neither table.
    """
    settle = settlement_for_tier(tier)
    lines = [
        "WHAT THIS POPULATION ACTUALLY LOOKS LIKE — Periodic Labour Force "
        "Survey 2023-24. These are the real proportions for the region above. "
        "Match them. Do not caricature them and do not round them to all-or-"
        "nothing.\n"
    ]

    if gender == "female":
        rate = female_lfpr(age_min, age_max, tier)
        lines.append(
            f"  WORK. About {rate:.0f} in 100 women this age are in the "
            f"labour force at all. The other {100 - rate:.0f} are not — and at "
            "this age almost none of those are students, so they are running "
            "households. A region of 100 women holding 100 jobs is not this "
            "region.\n"
        )

    if gender in ("female", "any"):
        self_emp, wage, casual = WORK_SHAPE["female"]
        informal = INFORMAL_SHARE[("female", settle)]
        lines.append(
            f"  AND WHEN SHE DOES WORK it is usually her OWN work, not a "
            f"salary: {self_emp} of every 100 working women in India are "
            f"self-employed and only {wage} hold a regular wage or salaried "
            f"job ({casual} do casual labour). {informal:.0f}% of "
            f"{settle} women's employment is informal. Tailoring at home, a "
            "tiffin service, a beauty parlour, tuition, running the family "
            "shop or keeping its accounts unpaid — these are the ordinary "
            "shapes of a working woman's day here, not the exceptions.\n"
        )
        no_school = EDUCATION_LFPR["not literate"][1]
        middling = EDUCATION_LFPR["higher secondary"][1]
        grad = EDUCATION_LFPR["graduate and above"][1]
        lines.append(
            f"  EDUCATION CUTS AGAINST INTUITION. Urban female participation "
            f"is a U: {no_school:.0f}% among women with no schooling, "
            f"{middling:.0f}% among women who finished higher secondary, "
            f"{grad:.0f}% among graduates. The woman LEAST likely to hold a "
            "job is the middling-educated one — which is most of a tier-2 or "
            "tier-3 town.\n"
        )

    if gender in ("male", "any"):
        self_emp, wage, casual = WORK_SHAPE["male"]
        informal = INFORMAL_SHARE[("male", settle)]
        lines.append(
            f"  MEN work in a wider mix but still mostly not for a salary: "
            f"{self_emp} of every 100 male workers are self-employed, {wage} "
            f"hold a regular wage or salaried job, {casual} do casual labour, "
            f"and {informal:.0f}% of {settle} men's employment is informal. A "
            "panel of salaried men is the same mistake in the other gender.\n"
        )

    lines.append(
        "SO THE `occupation_hint` FIELD IS WHAT FILLS THIS PERSON'S DAY, not "
        "necessarily a job. \"Runs the house — cooking, the grandchildren "
        "after school, and the Tuesday temple committee\" is a correct, "
        "common and specific answer. So is \"helps at her husband's hardware "
        "shop in the afternoons, takes no salary from it\". Write the day. "
        "Where she does hold a paid job, write the job."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Reading back what was actually written.
# --------------------------------------------------------------------------
# ⚠ A HEURISTIC AND REPORTED AS ONE. This classifies a free-text hint by
# keyword, so it will miscount at the edges. It exists to PRINT an achieved mix
# next to the expected one after a generation, never to gate or reject a
# person: gating on a keyword list would teach the generator to write the
# keywords. Miscounting a few is fine; the check is looking for "0 of 194".

_UNPAID_MARKERS = (
    # A day centred on the household.
    "homemaker", "housewife", "home-maker", "housework",
    "runs the house", "runs the home", "keeps house", "keeps the house",
    "looks after the house", "looks after the home", "domestic duties",
    "full-time mother",
    # Unpaid work inside somebody else's business — PLFS calls this employed,
    # a marketer would not, and it is a real and common shape of the day.
    "unpaid", "no salary", "takes no salary", "without a salary",
    "helps her husband", "helps his wife", "helps at the family",
    "helps in the family",
)

# ⚠ "RETIRED" IS DELIBERATELY NOT A MARKER, and the reason is a finding.
# Measured on the pre-fix region: 12 of the 194 people were written as retired
# and ELEVEN of them were immediately given a second income — "retired college
# lecturer now taking private tuitions", "retired postmistress now teaching at
# a tuition centre", "retired from the state electricity board office, now
# manages two rented shops". Those people are in the labour force; counting
# them as unpaid would have reported a 7% household share where the true one
# was under 1%. It is the same defect in a subtler costume: the generator could
# not write a person with no work at all. So a retiree is counted as unpaid
# only if the rest of the hint independently says so.
#
# ⚠ THE ACHIEVED AND EXPECTED NUMBERS ARE NOT THE SAME QUANTITY, and the two
# errors point in OPPOSITE directions — so read the report as an alarm, never
# as a calibration:
#   - too low: a genuinely retired person on a pension alone is missed here,
#     while the expected share (100 - LFPR) does count her.
#   - too high: a woman who helps unpaid at her husband's shop is counted here
#     as unpaid, but PLFS counts her as EMPLOYED, so she is inside the 31% too.
#     A perfectly calibrated generation could therefore read slightly ABOVE the
#     expected share.
# Neither error matters for the one job this has — noticing that the count is
# zero. Do not tune a generation to close the gap between these two numbers.


def looks_unpaid(occupation_hint: str) -> bool:
    """Whether a hint describes a day that is not paid work.

    Keyword matching, so it is approximate — see the caveats above. It reports;
    it never gates.
    """
    return any(m in (occupation_hint or "").lower() for m in _UNPAID_MARKERS)


def achieved_mix(bundles: list[dict]) -> tuple[int, int]:
    """(unpaid-looking, total) across a generation's people."""
    return sum(looks_unpaid(b.get("occupation_hint", "")) for b in bundles), len(bundles)
