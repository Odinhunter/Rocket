"""What a demographic region actually looks like: who works, and who they live with.

⚠ TWO SOURCES, TWO DEFECTS, AND THEY ARE KEPT SEPARATE ON PURPOSE. The WORK half
(PLFS 2023-24, via UNFPA) answers "does she have a job"; the FAMILY half (NFHS-5
2019-21) answers "when did she marry, how many children, is her husband alive".
They come from different surveys with different definitions and different age
ceilings, so nothing here blends a number from one into a number from the other.
Read each block's own caveats before quoting it.

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

SECOND SOURCE, ADDED 2026-08-19 — FAMILY FORMATION. National Family Health
Survey (NFHS-5), 2019-21, India Report, IIPS and ICF, March 2022 — the DHS
Program's FR375. Fetched successfully from
https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf (10.9 MB, 715 pp) on 2026-08-19
and read table by table; the table numbers are cited on every block below.

⚠ THIS IS THE PRIMARY REPORT, NOT A SECONDARY READ. Unlike the PLFS block above,
these figures come from the survey's own final report, so they are quotable as
published. It is a government-of-India survey (MoHFW/IIPS) distributed through
the DHS Program, which is why it fetches where mospi.gov.in does not.

⚠ THE AGE CEILING IS 49 AND IT IS THE MAIN LIMITATION. NFHS-5 interviews women
15-49, so every family figure below stops there. A region reaching above 49 gets
the 45-49 row as a BOUND, never as a match — and the direction beyond it is
known, because every one of these series moves monotonically with age: older
cohorts married earlier, bore more children, and are more often widowed. So for
a 50+ region the 45-49 row understates marriage-earliness, family size and
widowhood. Stated here rather than buried, exactly as the tier→urban assumption
above is. `cohort_note` returns this in words when a region crosses the ceiling.

⚠ AND THE SURVEY IS 2019-21, SO THE COHORTS HAVE AGED. A woman who is 52 today
was ~46 when she was interviewed, i.e. she is IN the 45-49 row. A woman who is
60 today was ~54 and is off the table entirely. The bands below are labelled by
age AT SURVEY and `_family_row` does not silently shift them; the ceiling note
is what covers the gap, because a five-year shift is smaller than the error in
reading a proportion off a prompt anyway.

⚠ NOTHING HERE MAY BE FILLED IN FROM MEMORY. A fabricated statistics table
feeding every persona we ever generate is worse than the gap it closes, because
it looks sourced. Any row added later needs a URL that resolved.

⚠ THE EIGHT-DEFECT AUDIT IS WHY THE FAMILY HALF EXISTS — `docs/people_audit_
w4560_t3.md`, 2026-08-18. The generated region put median age at first birth at
28-31 against a sourced 21.7, gave 28% of women exactly one child against a
sourced 9%, made 1% of them widows against a sourced 11.5%, and employed zero
of 192 in farm or manual work against a sourced 9.4% + 27.9% of urban working
women. Every one of those is a number this module now carries.
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


# --------------------------------------------------------------------------
# FAMILY FORMATION — NFHS-5 (2019-21).  Added 2026-08-19 for the eight-defect
# audit. See the module docstring for the source, the age ceiling, and the
# survey-vintage caveat; none of it is repeated here.
# --------------------------------------------------------------------------
# ⚠ THE HALF THE GENERATOR HAD NOTHING FOR. `occupation_hint` carried ~700
# characters of instruction because the homemaker gap was fixed; the field
# beside it that carries every husband, child, parent and grandchild was
# specified in twenty-three: "ONE household detail. Same bans." Everything the
# audit found in family life follows from that asymmetry, so the fix is a
# sourced distribution per fact rather than a longer sentence.

# The NFHS age bands, in survey order. Every family table below is keyed to
# these, so a region is resolved to bands once, in `_family_row`.
_FAMILY_BANDS = ((15, 19), (20, 24), (25, 29), (30, 34),
                 (35, 39), (40, 44), (45, 49))
FAMILY_AGE_CEILING = 49

# --- Age at first birth. [Table 4.8, all-India; Table 4.9, by residence] ----
#
# ⚠ THE CUMULATIVE CURVE IS THE POINT, NOT THE MEDIAN. The audit's finding 1
# was not a wrong median, it was a MISSING LEFT TAIL: not one woman of 192 had
# a first child before 23, on the reading most generous to the generator. A
# median can be hit by a distribution with no tail at all. The percentages
# below cannot — they say what share had a first birth by 18, by 20, by 22.

# Share of women in each band who had given birth by exact age 15/18/20/22/25,
# and the share who never have. [Table 4.8] ⚠ ALL-INDIA — this table is not
# published split by residence, so it is stated as an all-India shape and the
# urban/rural correction rides on the medians below instead.
_FIRST_BIRTH_BY_AGE: dict[tuple[int, int], tuple[float, float, float, float, float, float]] = {
    #             by 15  by 18  by 20  by 22  by 25   never
    (25, 29):     (1.6,  12.9,  31.3,  51.6,  71.7,   19.6),
    (30, 34):     (2.7,  17.0,  36.3,  56.1,  76.6,    7.1),
    (35, 39):     (3.1,  19.8,  40.6,  59.9,  78.9,    4.2),
    (40, 44):     (3.5,  20.7,  41.3,  61.4,  80.4,    3.8),
    (45, 49):     (3.3,  19.8,  40.2,  60.0,  79.6,    3.3),
}
# ⚠ NO ROWS FOR 15-24 AND IT IS NOT AN OVERSIGHT — the report prints "a = not
# calculated" for them, because fewer than half those women have given birth
# yet. A young region therefore gets the never-given-birth share (below) and no
# first-birth curve, which is the honest shape: most of them have not had one.
_NEVER_GIVEN_BIRTH = {(15, 19): 95.5, (20, 24): 55.1}

# Median age at first birth, by band and residence. [Table 4.9]
_MEDIAN_FIRST_BIRTH = {
    #            rural, urban
    (25, 29): (21.3, 23.4),
    (30, 34): (20.8, 22.6),
    (35, 39): (20.5, 22.0),
    (40, 44): (20.4, 21.7),
    (45, 49): (20.6, 21.7),
}

# Median age at first MARRIAGE, by band and residence. [Table 6.3.1]
# Kept alongside the birth figure because the gap between them is about two
# years and a persona's marriage is far more often mentioned than her first
# birth — the household hints in the audited file name a husband constantly.
_MEDIAN_FIRST_MARRIAGE = {
    #            rural, urban
    (25, 29): (19.1, 21.3),
    (30, 34): (18.4, 20.5),
    (35, 39): (17.9, 19.8),
    (40, 44): (17.6, 19.5),
    (45, 49): (17.8, 19.3),
}

# --- Children ever born. [Table 4.5, all women] ----------------------------
# ⚠ FINDING 6 IS THIS TABLE. The generated region implied exactly one child for
# 28% of its women. For the cohort it was written about the published figure is
# 9.0%, and 57% have three or more — which the generator wrote almost never.
_CHILDREN_EVER_BORN: dict[tuple[int, int], tuple[float, float, float, float, float]] = {
    #            none   one    two   three  four+
    (15, 19):   (95.5,   3.9,   0.5,   0.1,   0.0),
    (20, 24):   (55.1,  25.5,  15.3,   3.4,   0.6),
    (25, 29):   (19.6,  22.9,  36.2,  15.1,   6.0),
    (30, 34):   ( 7.1,  15.3,  41.6,  21.5,  14.5),
    (35, 39):   ( 4.2,  10.8,  39.5,  24.2,  21.2),
    (40, 44):   ( 3.8,   9.1,  35.0,  24.9,  27.3),
    (45, 49):   ( 3.3,   9.0,  29.7,  25.4,  32.5),
}
# Mean children ever born, same bands. [Table 4.5]
_MEAN_CEB = {(15, 19): 0.05, (20, 24): 0.69, (25, 29): 1.67, (30, 34): 2.28,
             (35, 39): 2.63, (40, 44): 2.87, (45, 49): 3.09}

# --- Marital status. [Table 6.1] -------------------------------------------
# ⚠ FINDING 5 IS THIS TABLE, AND IT IS THE THIRD FACE OF ONE DEFECT — see
# `generator_cannot_write_absence`. The generator wrote 2 widows in 192 (1%)
# while writing widowed sisters and mothers freely. Urban women 45-49 are
# 11.5% widowed. It could write absence for a side character and not for its
# protagonist.
#
# ⭐ AND WIDOWHOOD IS THE NARROW READING. The useful number is everyone with no
# husband in the house: never-married + widowed + divorced + separated +
# deserted. For urban women 45-49 that is 14.7%; for urban women 25-29 it is
# 19.3%, and almost all of THAT is never-married. One rule, two very different
# regions — which is exactly why the brief has to be conditional.
_MARITAL_FEMALE: dict[tuple[int, int], dict[str, tuple[float, float]]] = {
    # band: {status: (rural, urban)}
    (15, 19): {"never": (84.5, 92.5), "widowed": (0.0, 0.0), "sep_div": (0.1, 0.1)},
    (20, 24): {"never": (32.8, 52.8), "widowed": (0.3, 0.2), "sep_div": (0.7, 0.6)},
    (25, 29): {"never": ( 7.3, 17.4), "widowed": (0.9, 0.7), "sep_div": (1.2, 1.2)},
    (30, 34): {"never": ( 1.9,  4.3), "widowed": (2.3, 2.1), "sep_div": (1.2, 1.7)},
    (35, 39): {"never": ( 1.0,  2.1), "widowed": (4.1, 3.9), "sep_div": (1.4, 2.1)},
    (40, 44): {"never": ( 0.9,  1.7), "widowed": (7.0, 6.8), "sep_div": (1.6, 1.9)},
    (45, 49): {"never": ( 0.6,  1.2), "widowed": (10.8, 11.5), "sep_div": (1.4, 2.0)},
}
# Men, same table — sparser because NFHS interviews men 15-54 in a smaller
# sample. ⚠ THE ASYMMETRY IS REAL AND NOT A DATA GAP: urban men 45-49 are 1.2%
# widowed against urban women's 11.5%, because Indian husbands are on average
# some years older and men remarry. A male region must not be given the female
# widowhood share.
_MARITAL_MALE: dict[tuple[int, int], dict[str, tuple[float, float]]] = {
    (20, 24): {"never": (73.5, 87.6), "widowed": (0.0, 0.0), "sep_div": (0.4, 0.3)},
    (25, 29): {"never": (35.4, 51.8), "widowed": (0.3, 0.2), "sep_div": (0.9, 1.2)},
    (30, 34): {"never": (11.7, 21.3), "widowed": (0.5, 0.1), "sep_div": (0.9, 0.8)},
    (35, 39): {"never": ( 3.8,  6.2), "widowed": (0.9, 0.7), "sep_div": (1.1, 1.3)},
    (40, 44): {"never": ( 1.9,  3.7), "widowed": (1.2, 0.5), "sep_div": (1.2, 1.3)},
    (45, 49): {"never": ( 1.8,  3.7), "widowed": (1.4, 1.2), "sep_div": (1.0, 0.9)},
}

# --- What the work IS, by industry. [Table 3.11] ---------------------------
# ⚠⚠ FINDING 4, AND THIS IS THE URBAN COLUMN — which is the whole reason it is
# usable. The audit explicitly banned "agriculture is India's biggest employer
# of women" as the target, because that is an all-India rural-dominated figure
# and our regions are urban. This table publishes urban and rural separately,
# so the urban column answers the question that was actually asked.
#
# The measured failure: 0 farm, 0 construction, 0 factory and 2 domestic
# workers among 192 town women. Against the urban column, agricultural and
# production work together are 37.3% of employed women.
#
# ⚠ "Production worker" is the report's own label and it FOOTNOTES as "includes
# skilled and unskilled manual occupations" — so it is the factory, the
# construction site, the beedi and garment piece-work and the packing line, not
# a euphemism. "Professional" likewise footnotes as including technical,
# administrative and managerial work.
OCCUPATION_MIX: dict[str, dict[str, tuple[float, float]]] = {
    # gender: {occupation: (rural, urban)}  — % of those employed in the last
    # 12 months. [Table 3.11]
    "female": {
        "professional/technical/managerial": (5.4, 22.2),
        "clerical": (1.1, 3.2),
        "sales": (3.8, 11.0),
        "agricultural": (60.8, 9.4),
        "services": (7.3, 20.8),
        "manual/production": (17.7, 27.9),
        "other": (3.7, 5.1),
    },
    "male": {
        "professional/technical/managerial": (4.3, 13.2),
        "clerical": (1.5, 4.0),
        "sales": (7.5, 18.2),
        "agricultural": (46.1, 6.5),
        "services": (6.2, 13.3),
        "manual/production": (29.3, 37.9),
        "other": (4.9, 6.7),
    },
}

# Who employs a working woman, and whether she is paid at all. [Table 3.12]
# ⚠ DIFFERENT DEFINITION FROM `WORK_SHAPE` ABOVE — do NOT state both as if they
# were one series. PLFS calls 67% of working women "self-employed"; NFHS says
# 75.9% are "employed by a family member" and only 11.4% self-employed. The two
# surveys draw the line between "my own work" and "the family's work" in
# different places. They agree on the thing that matters — a salaried employer
# is the exception — and that is all either is quoted for.
EMPLOYER_TYPE_FEMALE = {"family member": 75.9, "non-family member": 12.7,
                        "self-employed": 11.4}
# ⭐ AND 14.4% OF WORKING WOMEN ARE NOT PAID AT ALL. [Table 3.12, "type of
# earnings"] This is the sourced version of the unpaid-family-helper shape the
# homemaker fix introduced by exemplar — a proportion to hit rather than a
# phrase to copy.
UNPAID_SHARE_OF_WORKING_WOMEN = 14.4

# --- Household shape. [Table 2.14] -----------------------------------------
# ⚠ FINDING 8's SUPPORTING CAST. The audited file put a mother-in-law in 21 of
# 192 households and a bedridden relative in 11 — plausible individually, and
# the generator had nothing telling it how common a joint household actually
# is. Urban households are 61.3% nuclear and average 4.2 people.
HOUSEHOLD_SHAPE = {
    #                    rural, urban
    "mean_size": (4.5, 4.2),
    "nuclear_pct": (56.7, 61.3),
    "female_headed_pct": (17.6, 17.1),
}


def _col(tier: str) -> int:
    """0 for the rural column, 1 for urban. One definition, used by every
    family lookup, so a table cannot be read off the wrong column."""
    return 0 if settlement_for_tier(tier) == "rural" else 1


def _family_row(age_min: int, age_max: int) -> tuple[tuple[int, int], ...]:
    """The NFHS bands a region overlaps, clamped to the survey's 15-49 range.

    ⚠ CLAMPED, NOT EXTRAPOLATED. A region of women 45-60 overlaps exactly one
    published band, 45-49, and gets it — with `cohort_note` saying out loud
    that eleven of its sixteen years sit past the survey's ceiling. Inventing a
    50-59 row by extending the trend is precisely the fabrication the module
    docstring bans, however obvious the direction is.
    """
    hit = tuple(b for b in _FAMILY_BANDS
                if min(b[1], age_max) >= max(b[0], age_min))
    if hit:
        return hit
    # Entirely above the ceiling (a 55-70 region): the top band, as a bound.
    return (_FAMILY_BANDS[-1],) if age_min > FAMILY_AGE_CEILING else ()


def _weighted(rows: tuple[tuple[int, int], ...], table: dict,
              age_min: int, age_max: int, pick) -> float:
    """Average `pick(table[band])` over the bands a region touches, weighted by
    years of overlap — the same crude weighting `female_lfpr` uses, and crude
    for the same reason: it sets a proportion in a prompt.

    Overlap is measured against the BAND, so a region of women 45-60 counts the
    45-49 band as the five years it actually is, not as fifteen.
    """
    years = weighted = 0.0
    for band in rows:
        if band not in table:
            continue
        overlap = min(band[1], age_max) - max(band[0], age_min) + 1
        if overlap <= 0:
            # ⚠ THE ABOVE-CEILING FALLBACK, AND IT MUST NOT SILENTLY RETURN 0.
            # `_family_row` hands back the top band for a region that does not
            # touch it at all — women 55-70. Weighting by overlap would give
            # that band -5 years, drop it, and report every family figure as
            # zero, which reads exactly like "no widows here". Use the band
            # whole instead: that is what "read the top row as a bound" means,
            # and `cohort_note` is what says so in words.
            overlap = band[1] - band[0] + 1
        years += overlap
        weighted += overlap * pick(table[band])
    return round(weighted / years, 1) if years else 0.0


def median_age_at_first_birth(age_min: int, age_max: int,
                              tier: str = "any") -> float:
    """Median age at first birth for the cohort in this region. [Table 4.9]"""
    col = _col(tier)
    return _weighted(_family_row(age_min, age_max), _MEDIAN_FIRST_BIRTH,
                     age_min, age_max, lambda r: r[col])


def median_age_at_first_marriage(age_min: int, age_max: int,
                                 tier: str = "any") -> float:
    """Median age at first marriage for the cohort. [Table 6.3.1]"""
    col = _col(tier)
    return _weighted(_family_row(age_min, age_max), _MEDIAN_FIRST_MARRIAGE,
                     age_min, age_max, lambda r: r[col])


def first_birth_curve(age_min: int, age_max: int) -> dict[int, float] | None:
    """Share of the cohort who had their first child by exact age 18/20/22/25.

    Returns None for a region young enough that the report declines to compute
    it — under 25 most women have not had a first birth, so there is no curve
    to state and pretending otherwise would invent the tail this exists to fix.
    [Table 4.8, all-India]
    """
    rows = _family_row(age_min, age_max)
    if not any(b in _FIRST_BIRTH_BY_AGE for b in rows):
        return None
    # ⚠ "by exact age 15" IS in the source table and is deliberately not
    # returned. 3.3% of this cohort had a first birth by 15 is a true and
    # terrible number; handing it to a persona writer as a proportion to hit
    # is asking it to write child marriage into a snack-ad panel. The tail
    # this exists to restore is visible at 18 and 20.
    return {
        age: _weighted(rows, _FIRST_BIRTH_BY_AGE, age_min, age_max,
                       lambda r, i=i: r[i])
        for i, age in ((1, 18), (2, 20), (3, 22), (4, 25))
    }


def children_ever_born(age_min: int, age_max: int) -> dict[str, float] | None:
    """Percent distribution of children ever born, for this cohort. [Table 4.5]"""
    rows = _family_row(age_min, age_max)
    if not rows:
        return None
    keys = ("none", "one", "two", "three", "four or more")
    return {k: _weighted(rows, _CHILDREN_EVER_BORN, age_min, age_max,
                         lambda r, i=i: r[i])
            for i, k in enumerate(keys)}


def unpartnered_share(gender: str, age_min: int, age_max: int,
                      tier: str = "any") -> dict[str, float] | None:
    """Share of this cohort with no spouse in the house, split by why.

    ⭐ THE SPLIT IS THE WHOLE VALUE. At 25-29 the missing husband is a husband
    who never arrived; at 45-49 he is a husband who died. Handing a generator
    one blended "15% unmarried" number would produce widows in a region of
    twenty-somethings and never-married women in a region of fifty-somethings.
    Returns None for a gender with no table (i.e. "any"). [Table 6.1]
    """
    table = {"female": _MARITAL_FEMALE, "male": _MARITAL_MALE}.get(gender)
    if table is None:
        return None
    rows = tuple(b for b in _family_row(age_min, age_max) if b in table)
    if not rows:
        return None
    col = _col(tier)
    out = {k: _weighted(rows, table, age_min, age_max,
                        lambda r, k=k: r[k][col])
           for k in ("never", "widowed", "sep_div")}
    out["total"] = round(sum(out.values()), 1)
    return out


def cohort_note(age_min: int, age_max: int) -> str:
    """One sentence naming how far a region reaches past the survey's ceiling.

    ⚠ RETURNED AS TEXT AND MEANT TO REACH THE MODEL. A silent clamp is the
    failure mode here: the caller would state a 45-49 figure for a 45-60 region
    as if it fitted, and nothing downstream would know. See the docstring.
    """
    if age_max <= FAMILY_AGE_CEILING:
        return ""
    past = age_max - max(age_min - 1, FAMILY_AGE_CEILING)
    span = age_max - age_min + 1
    return (
        f"⚠ THE FAMILY FIGURES STOP AT {FAMILY_AGE_CEILING} AND THIS REGION "
        f"DOES NOT — {past} of its {span} years sit above the survey's oldest "
        "band, so the numbers above are read off women aged 45-49 and are a "
        "FLOOR for anyone older. Every one of these series moves the same way "
        "with age: the older she is, the earlier she married, the more "
        "children she had, and the more likely her husband has died. Lean "
        "past these numbers for the older half of the region, never short of "
        "them."
    )


def _industry_lines(gender: str, settle: str, rate: float | None = None) -> str:
    """The industry spread, as a proportion per class of work. [Table 3.11]

    ⚠ THIS EXISTS BECAUSE A LIST OF JOBS DOES NOT WORK — see the note at its
    call site. It names classes ("manual and production work"), never job
    titles, so there is no noun to copy. The model has to invent a job inside a
    class, which is the behaviour the audit found was missing: it obeyed every
    proportion it was given and copied every example it was given.

    Finding 4 of the audit is one line of this table: 192 small-town women and
    not one of them did farm, construction or factory work.
    """
    col = 0 if settle == "rural" else 1
    mix = OCCUPATION_MIX[gender]
    who = "women" if gender == "female" else "men"
    order = ("manual/production", "professional/technical/managerial",
             "services", "sales", "agricultural", "clerical")
    label = {
        "manual/production": "manual and production work — a factory or mill "
                             "floor, a construction site, packing, piece-rate "
                             "work taken in from a contractor",
        "professional/technical/managerial": "professional, technical, "
                                             "administrative or managerial",
        "services": "service work — cooking, cleaning and care in other "
                    "people's homes and premises, hospitality, salons",
        "sales": "selling — a counter, a stall, a route, an agency",
        "agricultural": "agricultural and land labour, which does NOT stop at "
                        "the city limits: small towns have fields at their "
                        "edge and people who work them",
        "clerical": "clerical and office",
    }
    rows = "\n".join(f"    {mix[k][col]:>5.1f}%  {label[k]}" for k in order)
    biggest = max(order, key=lambda k: mix[k][col])
    lines = [
        f"  AND WHAT THAT WORK IS — ⚠ OF EVERY 100 {settle.upper()} "
        f"{who.upper()} WHO ARE EMPLOYED, which is not the same as of every "
        "100 in the region. By kind of work (National Family Health Survey "
        "2019-21):\n"
        f"{rows}\n"
        f"    {mix['other'][col]:>5.1f}%  other\n"
    ]
    # ⚠⚠ THE REGION-TERMS RESTATEMENT, AND IT IS THE FIX FOR A MEASURED
    # REGRESSION. Probe of 2026-08-19: this table is eleven vivid numeric lines
    # sitting directly under ONE sentence of participation, and the generator
    # anchored on the table — the unpaid share fell from 37% (v2) to ~27%. The
    # employment detail crowded out the fact that most of these women are not
    # employed at all. Doing the multiplication FOR the model puts both numbers
    # in the same sentence, where they cannot be read past each other.
    if rate is not None:
        per100 = {k: mix[k][col] * rate / 100 for k in order}
        named = ", ".join(
            f"~{per100[k]:.0f} in {label[k].split(' —')[0].split(', which')[0]}"
            for k in ("manual/production", "services",
                      "professional/technical/managerial", "agricultural"))
        lines.append(
            f"  ⚠⚠ NOW PUT THAT BACK INTO THE REGION, because the percentages "
            f"above are of the {rate:.0f} who work and NOT of the 100. In a "
            f"room of 100 {who} from this region: {named} — and "
            f"{100 - rate:.0f} with no job at all. ⚠ THE LARGEST GROUP IN THE "
            "ROOM IS THE ONE WITH NO JOB, and it is larger than every "
            "employed class put together. Write the room, not the table.\n"
        )
    if gender == "female":
        manual = mix["manual/production"][col] + mix["agricultural"][col]
        lines.append(
            f"  ⚠ READ THAT AGAINST YOUR INSTINCT. {manual:.0f} of every 100 "
            f"employed {settle} women do farm or manual work — more than the "
            f"{mix['professional/technical/managerial'][col]:.0f} in "
            "professional, technical or managerial jobs. A panel of small "
            "traders, tutors and tailors with nobody on a factory floor or a "
            "field is not this population; it is the shop-front of it. And "
            "the poorest working women are inside these numbers, so a region "
            "whose lowest household income is comfortable has lost them "
            "too.\n"
        )
    else:
        lines.append(
            f"  The largest single class is {label[biggest].split(' —')[0]}, "
            f"at {mix[biggest][col]:.0f}%.\n"
        )
    return "".join(lines)


# --------------------------------------------------------------------------
# The family half of the brief.
# --------------------------------------------------------------------------
# ⚠⚠ CONDITIONAL ON THE REGION, AND THAT IS THE WHOLE DESIGN. The prompt has to
# serve young tier-1 women as readily as the 45-60 tier-3 women it was first
# written for — the user's standing instruction, 2026-08-18. A brief that
# always talks about widowhood and grandchildren rebuilds the middle-age
# assumption in the very act of fixing it. So every paragraph below is gated on
# what the tables actually say for THIS age range: a region of 22-28-year-olds
# is told that a third of them have never married and hears nothing about
# widows, because 0.5% is not a fact worth a persona writer's attention.

def _pct(x: float) -> str:
    """A proportion a persona writer can act on. 11.5 -> 'about 1 in 9'."""
    if x <= 0:
        return "essentially none"
    n = round(100 / x)
    return f"about 1 in {n}" if n > 1 else "nearly all"


def _family_brief(gender: str, age_min: int, age_max: int, tier: str) -> str:
    """Marriage, children and who is missing from the house, for this region.

    ⚠ THE FIELD THIS IS AIMED AT IS `household_hint`, which carried a
    twenty-three-character specification while `occupation_hint` carried seven
    hundred — and every family defect in the audit followed from that gap. The
    numbers go here, in the cached region block; the ARITHMETIC RULE that binds
    them together goes on the field itself, because it is an instruction rather
    than a population fact.
    """
    settle = settlement_for_tier(tier)
    col = 0 if settle == "rural" else 1
    out: list[str] = []

    if gender in ("female", "any"):
        marriage = median_age_at_first_marriage(age_min, age_max, tier)
        birth = median_age_at_first_birth(age_min, age_max, tier)
        if marriage and birth:
            out.append(
                f"  WHEN SHE MARRIED, AND WHEN THE FIRST CHILD CAME. For "
                f"{settle} women of this age the median age at first marriage "
                f"is {marriage:.0f} and the median age at first birth is "
                f"{birth:.0f}. ⚠ Those are MEDIANS, so half of them are "
                "earlier — and the half that is earlier is the half a writer "
                "keeps leaving out.\n"
            )
        curve = first_birth_curve(age_min, age_max)
        if curve:
            out.append(
                f"  THE SHAPE OF IT, WHICH MATTERS MORE THAN THE MEDIAN: of "
                f"every 100 women this age, {curve[18]:.0f} had their first "
                f"child by 18, {curve[20]:.0f} by 20, {curve[22]:.0f} by 22 "
                f"and {curve[25]:.0f} by 25. ⚠ SO ROUGHLY "
                f"{curve[20]:.0f} IN 100 WERE MOTHERS BEFORE THEY WERE 20. A "
                "set of these women in which nobody had a child before her "
                "mid-twenties is not a sample of them.\n"
            )
        kids = children_ever_born(age_min, age_max)
        if kids:
            out.append(
                f"  HOW MANY CHILDREN, of every 100 women this age: "
                f"{kids['none']:.0f} none, {kids['one']:.0f} exactly one, "
                f"{kids['two']:.0f} two, {kids['three']:.0f} three, "
                f"{kids['four or more']:.0f} four or more. ⚠ THE ONE-CHILD "
                "family is the trap here — it feels like the default and it "
                f"is {kids['one']:.0f}%.\n"
            )

    for g in (("female", "male") if gender == "any" else (gender,)):
        share = unpartnered_share(g, age_min, age_max, tier)
        if not share or share["total"] < 3.0:
            # ⚠ BELOW ~3% IT IS DELIBERATELY NOT MENTIONED. A proportion a
            # writer cannot act on across a few dozen people is noise, and
            # naming it invites a token widow in a room of 25-year-olds —
            # which is the same costume-marker failure the audit warns about
            # for community. Absence is stated where absence is common.
            continue
        noun = "women" if g == "female" else "men"
        her = "her" if g == "female" else "his"
        lead = max(("never", share["never"]), ("widowed", share["widowed"]),
                   key=lambda kv: kv[1])[0]
        out.append(
            f"  WHO HAS NO SPOUSE IN THE HOUSE — {share['total']:.0f} of "
            f"every 100 {settle} {noun} this age: {share['never']:.0f} never "
            f"married, {share['widowed']:.0f} widowed, "
            f"{share['sep_div']:.0f} divorced, separated or deserted. "
            + (f"⚠ At this age that is mostly a spouse who never arrived, not "
               f"one who died — do not write these as widows.\n"
               if lead == "never" else
               f"⚠ That is {_pct(share['widowed'])} of them widowed"
               # ⚠ The emphasis is gated on the size of the number. Calling 5%
               # "the most under-written fact about this population" would be
               # the same overclaiming this brief is trying to stop.
               + (", and it is the single most under-written fact about this "
                  "population — the generator that wrote this region before "
                  "managed 1 in 100.\n" if share["widowed"] >= 8 else ".\n")
               + f"  ⚠ Absence is also normal in the ordinary direction: "
                 f"{her} spouse may work in another city, or be ill, or be "
                 f"out of work.\n")
        )

    if out:
        size = HOUSEHOLD_SHAPE["mean_size"][col]
        nuclear = HOUSEHOLD_SHAPE["nuclear_pct"][col]
        headed = HOUSEHOLD_SHAPE["female_headed_pct"][col]
        out.append(
            f"  AND THE HOUSE ITSELF averages {size} people and is nuclear "
            f"{nuclear:.0f}% of the time — a couple and their unmarried "
            f"children, no in-laws in it. {100 - nuclear:.0f}% is the joint "
            f"household, not the default. {headed:.0f}% of households are "
            "headed by a woman.\n"
        )
        note = cohort_note(age_min, age_max)
        if note:
            out.append(f"  {note}\n")
        out.insert(0,
                   f"WHO {'SHE' if gender == 'female' else 'HE' if gender == 'male' else 'THEY'} "
                   f"{'LIVES' if gender != 'any' else 'LIVE'} WITH — National "
                   "Family Health Survey (NFHS-5), 2019-21. Same instruction "
                   "as the work figures: match them, do not caricature "
                   "them.\n")
    return "\n".join(out)


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
        # ⚠ THE STUDENT CLAUSE IS AN OVER-30 CLAIM AND WAS BEING MADE AT EVERY
        # AGE. This module's own docstring scopes it — "above ~30 that
        # complement is overwhelmingly full-time domestic work… students have
        # left the count by then" — but the sentence went out unconditionally,
        # so a region of 22-year-olds was told that none of the three quarters
        # outside the labour force were studying. That is the middle-age
        # assumption leaking through the fix for it, which is the one failure
        # a region-general brief cannot have.
        rest = (
            "and at this age almost none of those are students, so they are "
            "running households"
            if age_min >= 30 else
            "and at this age that includes women who are still studying as "
            "well as women running households — PLFS does not give us the "
            "split, so do not silently assume either one"
        )
        lines.append(
            f"  WORK. About {rate:.0f} in 100 women this age are in the "
            f"labour force at all. The other {100 - rate:.0f} are not — {rest}"
            ". A region of 100 women holding 100 jobs is not this region.\n"
        )

    if gender in ("female", "any"):
        self_emp, wage, casual = WORK_SHAPE["female"]
        informal = INFORMAL_SHARE[("female", settle)]
        # ⚠ THE SIX-NOUN MENU THAT USED TO END THIS PARAGRAPH IS GONE, AND
        # DELIBERATELY. "Tailoring at home, a tiffin service, a beauty parlour,
        # tuition, running the family shop or keeping its accounts unpaid" was
        # meant as illustration and was read as a menu: those six accounted for
        # 94 of 192 people (49%) in the region it was used on. The industry
        # split below replaces it — same job, sourced, and stated as CLASSES of
        # work rather than job titles, so there is nothing to copy verbatim.
        lines.append(
            f"  AND WHEN SHE DOES WORK it is usually her OWN work, not a "
            f"salary: {self_emp} of every 100 working women in India are "
            f"self-employed and only {wage} hold a regular wage or salaried "
            f"job ({casual} do casual labour). {informal:.0f}% of "
            f"{settle} women's employment is informal, and "
            f"{UNPAID_SHARE_OF_WORKING_WOMEN}% of working women are not paid "
            "at all.\n"
        )
        # ⚠ THE RATE ONLY EXISTS FOR A FEMALE REGION, AND PASSING None HERE IS
        # THE SAME DECISION THE REST OF THIS MODULE MAKES. No age-banded male
        # participation figure was ever sourced, so an "any" region gets the
        # industry SPREAD (sourced) and no region-terms restatement (which
        # would need a participation rate this module does not have). Caught by
        # `test_any_gender_carries_both_halves_and_still_no_invented_average`,
        # which crashed on the unbound name before it could check the claim.
        lines.append(_industry_lines(
            "female", settle, rate if gender == "female" else None))
        no_school = EDUCATION_LFPR["not literate"][1]
        middling = EDUCATION_LFPR["higher secondary"][1]
        grad = EDUCATION_LFPR["graduate and above"][1]
        lines.append(
            f"  EDUCATION CUTS AGAINST INTUITION. Urban female participation "
            f"is a U: {no_school:.0f}% among women with no schooling, "
            f"{middling:.0f}% among women who finished higher secondary, "
            f"{grad:.0f}% among graduates. The woman LEAST likely to hold a "
            "job is the middling-educated one"
            # ⚠ Same leak as the student clause, one town smaller: the tail
            # "which is most of a tier-2 or tier-3 town" was asserted for
            # tier-1 regions too.
            + (" — which is most of a tier-2 or tier-3 town.\n"
               if tier in ("tier-2", "tier-3", "any") else
               ", who is a smaller share of a metro than of a small town but "
               "is still the middle of this region.\n")
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
        lines.append(_industry_lines("male", settle))

    # ⚠ ONE EXEMPLAR, NOT THREE, AND THE COUNT IS THE POINT. This paragraph
    # used to offer two and the `occupation_hint` schema repeated both, so the
    # same nouns reached the model three times in one prompt and came back as
    # its two largest job clusters. The rule now: any given exemplar appears
    # EXACTLY ONCE across the whole assembled prompt. This one earns its place
    # because it demonstrates a SHAPE the model otherwise gets wrong — a day
    # rather than a label — and the shape cannot be conveyed by a proportion.
    # ⚠ AND THE ONE SURVIVING EXEMPLAR IS AGE-GATED, because the version that
    # shipped named grandchildren — which a region of 25-year-olds does not
    # have. An exemplar that contradicts the region is worse than none: it is
    # the one line in this brief the model is most likely to copy.
    # ⚠ AND THE PRONOUN IS GATED TOO. "Where SHE does hold a paid job" went out
    # on mixed-gender regions as well, which is the same leak one word wide.
    poss = {"female": "her", "male": "his"}.get(gender, "their")
    subj = {"female": "she", "male": "he"}.get(gender, "they")
    does = "does" if gender in ("female", "male") else "do"
    unpaid_day = (
        "cooking, the grandchildren after school, and the Tuesday temple "
        "committee" if age_min >= 45 else
        f"the cooking and the washing, {poss} mother-in-law's hospital trips, "
        "and the two hours the house is quiet"
    )
    lines.append(
        "SO THE `occupation_hint` FIELD IS WHAT FILLS THIS PERSON'S DAY, not "
        f"necessarily a job. \"Runs the house — {unpaid_day}\" is a correct, "
        "common and specific answer: it is a day, not a job title. Write the "
        f"day. Where {subj} {does} hold a paid job, write the job — and take "
        "it from the spread above, not from the two or three trades that come "
        "to mind first."
    )

    family = _family_brief(gender, age_min, age_max, tier)
    if family:
        lines.append("\n" + family)
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
    # ⚠ ADDED 2026-08-19 FROM A MEASURED MISS. The 2026-08-19 probe wrote
    # "keeps the ledgers and cash box at her husband's cycle-parts shop, TAKES
    # NOTHING FROM IT" twice, and this list — which scanned only for "no
    # salary" — counted neither. It reported 13% unpaid where a hand read of
    # the same 30 people found ~27%. ⚠ The lesson generalises past this
    # phrase: thinning the prompt's exemplars moves the OUTPUT off the exact
    # wordings the classifier was built from, so a keyword report drifts
    # downward for free. Read the people, not only the counter.
    "takes nothing", "take nothing", "takes no money", "no wage",
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
