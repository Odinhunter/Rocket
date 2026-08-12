"""Scaffold the disposition library + AudienceSpec for the
`health_wellness_nutrition` category — India D2C supplements / protein /
wellness, the first category built fresh under Protocol v2.

────────────────────────────────────────────────────────────────────────
7 dispositions authored 2026-06-02 under docs/disposition_protocol_v2.md.
Grounded in data/voice_samples/health_wellness_nutrition.md (live web
research: Amazon.in / Nykaa / Flipkart / HealthKart / Quora / Practo
reviews + market reports). PENDING ISHAN REVIEW (Protocol v2 §5 Lever 5).
────────────────────────────────────────────────────────────────────────

Design frame (see `dispositions_are_tg_gateways` memory): each disposition
is a GATEWAY to one attitudinal target group — the runtime render +
reaction AI does the rest of the lifting. The library deliberately spans
sub-categories (whey / plant protein / gummies / vitamins / bars), because
the unit of design is the TG, not the SKU. Cohort spread per Protocol v2
§5 Lever 3: 1 obsessive, 2 high, 1 medium, 3 low — load-bearing on the
scroll-past / reject voices so the audience isn't "engaged buyers only".

  1. enthusiast_macros_lifter   OBSESSIVE — serious gym lifter, tub-loyal
  2. aspirant_clean_label       HIGH      — Insta-discovered clean-label buyer
  3. switcher_results_chaser    HIGH      — serial trier, switches on no-result
  4. doctor_triggered_vitamin   MEDIUM    — deficiency cohort, "medicine not lifestyle"
  5. skeptic_lapsed_protein     LOW       — bought once, "did nothing", lapsed
  6. pragmatist_protein_snacker LOW       — "snack, not supplement"
  7. purist_food_first          LOW       — "dal-rice-ghee is enough", anti-supplement

IMPORTANT — anchors are DEMOGRAPHIC-FREE by design. Gender / age / city /
income / occupation come from the AudienceSpec.demographics axis (the
render engine cross-products demographic × disposition × context, and
render.py:222 requires the persona's gender/age/identity to come from the
demographic axis — the anchor "must not assume a gender or assign a name").
The anchor pins the *object* of the stance (the PRODUCT, the behaviour, the
knowledge ceiling) — not who the person is. This matches the shipped
bru_coffee / personal_audio pattern, and the gateway reframe, and OVERRIDES
the literal "L1 = demographics" wording in disposition_protocol_v2.md §3.
⚠ That doc has now been CORRECTED (2026-08-13) rather than merely flagged —
§3 carries the reasons in full, including the one that is not obvious: an
anchor L1 written to the old wording would carry "income tier" straight past
the `_persona_user_payload` income redaction (§2.6). The biography the old
L1 was reaching for is real and now lives in `demographic_bundles` below.

⚠⚠ IMPORTANT — anchors are also BRAND-FREE and PLATFORM-FREE (render-10,
2026-08-12). Name the PRODUCT ("a plant protein", "a 20g protein bar",
"a weekly 60K IU vitamin-D sachet"), never a brand and never a marketplace.
WHY, measured: `aspirant_clean_label` used to say "on Nykaa" twice, and
because the anchor is injected as a HARD CONSTRAINT it beat the artifact
pack's own channel list — 24 of 24 of that disposition's persona briefs
carried Nykaa, into a PROTEIN BAR run, where nobody buys protein. The two
dispositions whose anchors named a different shop scored 0/19 and 0/15 on
it. Uniformity, not the mention, is the defect: a hard-coded channel is
indistinguishable from consensus downstream, so a prevalence floor cannot
catch it. The pack's brand + platform landscape is handed to the persona
WRITER (`render._pack_brief`) so each persona SELECTS what fits them —
which is why an 18-year-old beauty-supplement buyer may still land on
Nykaa while a bar buyer lands on quick-commerce. Same rule for
`occupation_hint` and for L5: describe a lived EXPERIENCE, never a
pre-written verdict about an ad ("sees an ad and rolls their eyes"), which
the person cannot be moved off by the ad being tested.
See tests/test_anchors_are_brand_free.py — it fails the build if a brand
or platform comes back.

REMAINING BEFORE A LIVE RUN (not in this file):
  - packs/health_wellness_nutrition.py  (brand landscape + price points +
    voice samples + chaos; ~20-25 brands. Reuse data/voice_samples/ +
    the pack-construction notes in the prior plan.)
  - then re-run this scaffold to also write the AudienceSpec + specs JSON.

Run: python scripts/scaffold_health_wellness.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack
from agent.entities import (
    Account,
    AudienceSpec,
    BrandProfile,
    DispositionLibrary,
    SavedAudience,
)
from agent.vectors import (
    ContextVector,
    DemographicBundle,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)


def _b(
    weight: float, gender: str, age: str, income: str, geo: str,
    occ: str, household: str,
) -> DemographicBundle:
    """Terse DemographicBundle constructor for the per-disposition income
    distributions (see docs/disposition_demographic_bundles.md). `weight` is
    the bundle's % of that disposition's agents; the weights per disposition
    reproduce its row in docs/disposition_income_brackets.md."""
    return DemographicBundle(
        point=DemographicPoint(
            gender=gender, age_band=age, income_tier=income, geography=geo,
            occupation_hint=occ, household_hint=household,
        ),
        weight=weight,
    )


# Per-disposition coherent demographic bundles. Income varies realistically
# AND every occupation/geo stays consistent with its tier (no "family head on
# <₹3.5L"). Grounded in MBB/Kantar/PRICE/category research — see
# docs/disposition_income_brackets.md (distributions) and
# docs/disposition_demographic_bundles.md (the personas).
#
# ⚠⚠ THE BUNDLE OWNS WHO THIS PERSON IS. THE ANCHOR OWNS WHAT THEY THINK OF
# THE CATEGORY. Never mix the two. A hint carrying category content
# ("outcome-driven", "buys imported whey", "mid-market gummies", "distrusts
# the category") is the Nykaa defect in a second seam: `occupation_hint`
# reaches the persona writer through `persona_writer_demographics`, and every
# agent drawn from that bundle gets it verbatim — so the panel arrives
# pre-agreeing about the very thing the run is trying to measure, and a
# prevalence floor cannot tell a pinned constant from consensus. It also
# leaks the WRONG PRODUCT across runs: a "protein bar as a convenient snack"
# biography meets a collagen ad unchanged. Two of the old hints additionally
# CONTRADICTED their own anchor's L3 knowledge ceiling — a switcher hint said
# "dermatologist-guided" where L3 says "does NOT see a dermatologist first",
# and a purist hint made the person a doctor where L3 says "does NOT read the
# studies". Write the JOB, the CITY and one HOUSEHOLD detail; nothing else.
#
# ⚠ NO ₹ FIGURES AND NO INCOME WORDS in a hint. `income_tier` is redacted at
# the `_persona_user_payload` seam on purpose (§2.6) — the hints are not, so
# a rupee number here walks straight past that redaction.
# ⚠ NO GENDERED PRONOUN in a bundle whose gender is "any" — the writer is
# handed both, and the pronoun wins.
#
# ⚠ SPLITTING RULE — the invariant that makes this safe: sub-bundles of one
# documented row share its gender, age_band, income_tier and SUMMED weight,
# and differ ONLY in geography / occupation_hint / household_hint.
# `demographic_overlap` is gender × age × income ONLY (panel.py:325), so every
# sub-bundle of a row scores the identical overlap and `audience_mass` — the
# marketer-led selection weight — is arithmetically unchanged. Geography is
# free to sharpen to named cities: it composes the targeting sentence and adds
# render vividness, but it does NOT narrow the panel.
# ⚠ Rows under ~10% are left WHOLE. At ~17 agents per disposition a 5% row is
# already under one agent; splitting it deletes it from the panel instead of
# diversifying it.
#
# WHY, MEASURED (2026-08-13): under the shipped 25-44 / ₹7-40L brief, the five
# rows per disposition collapse to the two that overlap it, so 100 agents were
# backed by 10 biographies and 15 people shared the single most common one.
# See docs/disposition_demographic_bundles.md for the before/after.

_BUNDLES_ENTHUSIAST = [  # [12, 26, 38, 18, 6] — young, male-skewed
    _b(6, "male", "18_24", "mass", "Nagpur / tier-2 town",
       "second-year college student; trains before morning classes",
       "lives with parents and a younger brother; no rent, small allowance"),
    _b(6, "male", "18_24", "mass", "Rajkot / tier-3 town",
       "works the counter at his family's mobile-repair shop",
       "joint family home; eats whatever the kitchen cooks"),

    _b(13, "male", "25_34", "lower_mid", "Indore / tier-2 city",
       "junior field-sales executive covering a two-district territory",
       "shares a rented 1BHK with two flatmates; sends money home monthly"),
    _b(13, "male", "25_34", "lower_mid", "Coimbatore / tier-2 city",
       "assistant trainer at a neighbourhood gym; takes the evening batches",
       "rented room near the gym; cooks on a single burner"),

    _b(13, "male", "25_34", "upper_mid", "Bangalore / metro tier-1",
       "backend engineer at a mid-stage startup; lifts before work five days a week",
       "1BHK in a gated block, lives alone; orders in most nights"),
    _b(13, "male", "25_34", "upper_mid", "Pune / metro tier-1",
       "operations manager at a logistics firm; 6am gym before the shift",
       "2BHK with a flatmate; meal-preps chicken and rice on Sundays"),
    _b(12, "male", "25_34", "upper_mid", "Hyderabad / metro tier-1",
       "product designer; lifts four evenings a week after office",
       "1BHK near the office; parents visit twice a year"),

    _b(9, "male", "35_44", "affluent", "Delhi NCR / metro tier-1",
       "chartered accountant running his own practice; members' gym before the office",
       "owns a 3BHK, married, one toddler"),
    _b(9, "male", "35_44", "affluent", "Mumbai / metro tier-1",
       "regional sales head; works out in hotel gyms three weeks a month",
       "owns a flat, married; travels Monday to Thursday"),

    _b(3, "male", "35_44", "premium", "Mumbai / metro tier-1",
       "founder of a mid-size firm; trains with a personal coach at a boutique studio",
       "high-rise apartment with family; a cook handles meals"),
    _b(3, "male", "35_44", "premium", "Gurugram / metro tier-1",
       "senior banking executive; 5am strength sessions with a coach",
       "owns a duplex; two kids in school, staff at home"),
]

_BUNDLES_ASPIRANT = [  # [5, 17, 45, 26, 7] — woman, 25-40, metro
    _b(5, "female", "25_34", "mass", "Jaipur / tier-2 city",
       "front-desk executive at a clinic",
       "lives with parents; saving for a wedding"),

    _b(9, "female", "25_34", "lower_mid", "Kochi / tier-2 city",
       "early-career content writer at a small agency",
       "shares a flat with a colleague; cooks most dinners"),
    _b(8, "female", "25_34", "lower_mid", "Chandigarh / tier-1",
       "junior HR executive at a mid-size company",
       "paying-guest room; family in the same city"),

    _b(15, "female", "25_34", "upper_mid", "Mumbai / metro tier-1",
       "brand marketing manager at a consumer company",
       "1BHK in the metro core, lives alone; long commute"),
    _b(15, "female", "25_34", "upper_mid", "Bangalore / metro tier-1",
       "UX designer at a product company; morning yoga three times a week",
       "2BHK with her partner; recently married"),
    _b(15, "female", "25_34", "upper_mid", "Delhi NCR / metro tier-1",
       "account manager at an agency; Pilates class on weekends",
       "rented 2BHK with a flatmate; family an hour away"),

    _b(13, "female", "35_44", "affluent", "Mumbai / metro tier-1",
       "senior product manager; a tight morning routine before the kids wake",
       "owns a 3BHK; two young kids and full-time help"),
    _b(13, "female", "35_44", "affluent", "Bangalore / metro tier-1",
       "runs a small design studio she founded",
       "owns a flat, married, one child in playschool"),

    _b(7, "female", "35_44", "premium", "Delhi NCR / metro tier-1",
       "co-founder of a growing company; a trainer on retainer",
       "large flat, household staff; two kids"),
]

_BUNDLES_SWITCHER = [  # [12, 30, 39, 16, 3] — working women, 25-44, broad
    _b(6, "female", "25_34", "mass", "Patna / tier-3 town",
       "school teacher in her second year of work",
       "lives with parents; contributes to the household"),
    _b(6, "female", "25_34", "mass", "Nashik / tier-2 city",
       "receptionist at a small clinic",
       "shares a flat with her sister; both send money home"),

    _b(10, "female", "25_34", "lower_mid", "Hyderabad / tier-1",
       "process associate on a night shift at a BPO",
       "shares a flat with two colleagues; sleeps days"),
    _b(10, "female", "25_34", "lower_mid", "Lucknow / tier-2 city",
       "retail floor supervisor at a mall store; on her feet nine hours",
       "lives with family; long bus commute"),
    _b(10, "female", "25_34", "lower_mid", "Bhopal / tier-2 city",
       "primary school teacher; grades papers after dinner",
       "married, one small child; joint family home"),

    _b(13, "female", "25_34", "upper_mid", "Bangalore / metro tier-1",
       "business analyst at a consulting firm; long desk hours",
       "1BHK alone; parents in another city"),
    _b(13, "female", "25_34", "upper_mid", "Mumbai / metro tier-1",
       "assistant manager at a bank; two-hour daily commute",
       "shares a 2BHK; recently engaged"),
    _b(13, "female", "25_34", "upper_mid", "Chennai / metro tier-1",
       "software tester; back-to-back calls most afternoons",
       "2BHK with her husband; no kids yet"),

    _b(8, "female", "35_44", "affluent", "Delhi NCR / metro tier-1",
       "senior HR business partner; travels for hiring drives",
       "owns a 3BHK; one child in primary school"),
    _b(8, "female", "35_44", "affluent", "Pune / metro tier-1",
       "runs a boutique event-management outfit",
       "owns a flat, married; help comes twice a day"),

    _b(3, "female", "35_44", "premium", "Mumbai / metro tier-1",
       "practice head at a consulting firm; long-haul travel most months",
       "sea-facing flat; full household staff"),
]

_BUNDLES_SKEPTIC = [  # [20, 32, 32, 12, 4] — mirrors enthusiast, lapsed/value
    _b(10, "male", "18_24", "mass", "Kanpur / tier-3 town",
       "final-year college student; plays cricket on Sundays",
       "lives with family in a rented ground-floor flat"),
    _b(10, "male", "18_24", "mass", "Jodhpur / tier-2 town",
       "works at his uncle's electrical-goods shop",
       "joint family; eats all three meals at home"),

    _b(11, "male", "25_34", "lower_mid", "Surat / tier-2 city",
       "salaried accountant at a textile trading firm",
       "shares a flat; carries a home-packed lunch"),
    _b(11, "male", "25_34", "lower_mid", "Vadodara / tier-2 city",
       "junior civil engineer on site most days",
       "rented room near the site; family in the village"),
    _b(10, "male", "25_34", "lower_mid", "Mysuru / tier-2 city",
       "customer-support executive on rotating shifts",
       "shares a 1BHK with a cousin"),

    _b(11, "any", "25_34", "upper_mid", "Bangalore / metro tier-1",
       "QA engineer at a services company; desk job, walks in the evening",
       "1BHK alone; cooks twice a week"),
    _b(11, "any", "25_34", "upper_mid", "Delhi NCR / metro tier-1",
       "media planner at an agency; irregular hours",
       "shares a 2BHK with two flatmates"),
    _b(10, "any", "25_34", "upper_mid", "Chennai / metro tier-1",
       "school administrator; steady nine-to-five",
       "lives with parents; the family kitchen runs the meals"),

    _b(6, "any", "35_44", "affluent", "Mumbai / metro tier-1",
       "project manager at an IT firm; badminton twice a week",
       "owns a 2BHK, married, one child"),
    _b(6, "any", "35_44", "affluent", "Hyderabad / metro tier-1",
       "runs a small trading business",
       "owns a flat; two kids, the kitchen runs on a fixed routine"),

    _b(4, "any", "35_44", "premium", "Bangalore / metro tier-1",
       "engineering director at a large tech company",
       "villa in a gated community; a cook and daily help"),
]

_BUNDLES_SNACKER = [  # [6, 18, 40, 26, 10] — 25-44, mixed, metro, no mass tail
    _b(6, "any", "25_34", "mass", "Guwahati / tier-2 city",
       "junior lab technician at a diagnostics centre",
       "shares a rented room; canteen lunches"),

    _b(9, "any", "25_34", "lower_mid", "Bhubaneswar / tier-2 city",
       "graphic designer at a small studio; works late often",
       "shares a flat; skips dinner more often than not"),
    _b(9, "any", "25_34", "lower_mid", "Kochi / tier-1",
       "trainee at an audit firm; long client-site days",
       "paying-guest accommodation; no kitchen"),

    _b(14, "any", "25_34", "upper_mid", "Bangalore / metro tier-1",
       "consultant at a professional-services firm; back-to-back meetings",
       "1BHK alone; a 4pm slump most days"),
    _b(13, "any", "25_34", "upper_mid", "Mumbai / metro tier-1",
       "investment banking analyst; desk lunch, late finishes",
       "shares a 2BHK; barely home except to sleep"),
    _b(13, "any", "25_34", "upper_mid", "Gurugram / metro tier-1",
       "product marketer at a tech company; hybrid, three days in office",
       "2BHK with a partner; neither of them cooks much"),

    _b(13, "any", "35_44", "affluent", "Delhi NCR / metro tier-1",
       "senior manager at a consumer company; school run before office",
       "owns a 3BHK; two kids, packed mornings"),
    _b(13, "any", "35_44", "affluent", "Pune / metro tier-1",
       "engineering lead; keeps a desk drawer stocked for late evenings",
       "owns a flat, married; one child"),

    _b(5, "any", "35_44", "premium", "Mumbai / metro tier-1",
       "vice-president at a financial services firm; gym at 6am, office by 8",
       "high-rise flat; a cook, a driver, two kids"),
    _b(5, "any", "35_44", "premium", "Bangalore / metro tier-1",
       "startup founder; eats at the desk between meetings",
       "large apartment; help manages the house"),
]

_BUNDLES_PURIST = [  # [12, 22, 34, 24, 8] — older 35-55, traditional
    _b(6, "any", "45_54", "mass", "Varanasi / tier-3 town",
       "shopkeeper on a busy market lane; opens at eight every morning",
       "joint family above the shop; one kitchen for nine people"),
    _b(6, "any", "45_54", "mass", "Salem / tier-2 town",
       "government clerk nearing thirty years of service",
       "own small house; a vegetable patch at the back"),

    _b(11, "any", "35_44", "lower_mid", "Jalandhar / tier-2 city",
       "runs a small hardware business with a brother",
       "family home; mother still runs the kitchen"),
    _b(11, "any", "35_44", "lower_mid", "Trichy / tier-2 city",
       "bank clerk; cycles to work",
       "rented house; two school-going kids"),

    _b(12, "any", "35_44", "upper_mid", "Chennai / metro tier-1",
       "civil engineer at a construction firm; carries lunch from home daily",
       "2BHK with parents and one child"),
    _b(11, "any", "35_44", "upper_mid", "Pune / metro tier-1",
       "college lecturer; walks in the mornings",
       "family flat; someone cooks fresh every evening"),
    _b(11, "any", "35_44", "upper_mid", "Kolkata / metro tier-1",
       "bank branch manager; fixed hours, home by seven",
       "family home; three generations at one table"),

    # ⚠ NOT a doctor any more. The old hint here said "settled professional /
    # doctor", which handed this persona medical expertise its own anchor L3
    # explicitly denies ("does NOT read the studies") — a vector/anchor
    # contradiction of exactly the kind protocol v2 §8 exists to catch.
    _b(12, "any", "45_54", "affluent", "Delhi NCR / metro tier-1",
       "practising lawyer with an independent chamber",
       "owns a house; grown kids, home-cooked meals"),
    _b(12, "any", "45_54", "affluent", "Mumbai / metro tier-1",
       "senior government officer close to retirement",
       "owns a flat; a cook who has been with the family for years"),

    _b(8, "any", "55_plus", "premium", "Bangalore / metro tier-1",
       "retired professor; a morning walk and the newspaper",
       "large house; children abroad, help lives in"),
]

# --- target tenancy ---
ACCOUNT_ID = "demo"
BRAND_PROFILE_ID = "health_wellness_demo"
LIBRARY_ID = "health_wellness_nutrition_lib_v1"
AUDIENCE_ID = "cold_traffic_v1"
CATEGORY = "health_wellness_nutrition"


# ---- The 7 hand-mapped health_wellness_nutrition dispositions ----
#
# Each anchor is 5 lines (L1 CONTEXT / L2 CATEGORY / L3 KNOWLEDGE /
# L4 STANCE / L5 ANCHOR-BEHAVIOR), separated by blank lines so the render
# engine reads them as discrete clauses, and treated as a HARD CONSTRAINT.
# Demographic-free + gender-neutral ("they") — see module note above.

def _library() -> DispositionLibrary:
    dispositions = [
        # 1 — OBSESSIVE. Coherence: loyalist + value_calculator + function +
        # obsessive all pull toward "I know what works, the math justifies
        # the brand, I'm not switching."
        NamedDisposition(
            label="enthusiast_macros_lifter",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="obsessive",
                prior_experience_valence="positive",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Three years into a structured 5-day push/pull/legs gym "
                "routine; treats supplements as tracked engineering inputs, "
                "not a lifestyle.\n\n"
                "Buys a 1kg tub of performance whey at around ₹2,700 every "
                "six-to-seven weeks, always from a seller where the "
                "authenticity seal can be scanned; the same cart adds "
                "creatine monohydrate and an omega-3.\n\n"
                "Knows protein-per-rupee and the third-party purity "
                "seals cold; does NOT lab-test, does NOT read the trials "
                "behind '50% better absorption', is NOT a nutritionist.\n\n"
                "Wants a consistent 25g per scoop, no added sugar, and a real "
                "authenticity seal; rejects loose 'imported' tubs and "
                "'proprietary blends' that hide the macros.\n\n"
                "Watches one supplement-review YouTuber before any first-time "
                "switch; has re-bought the same tub four times now, because "
                "nothing since has given them a reason to re-run the "
                "comparison."
            ),
            demographic_bundles=_BUNDLES_ENTHUSIAST,
        ),
        # 2 — HIGH. Coherence: favorable (not loyalist — they'd switch) +
        # identity + value_calculator + mixed valence = Insta-discovered,
        # switches when the next aesthetic clean brand drops.
        NamedDisposition(
            label="aspirant_clean_label",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="favorable",
                price_orientation="value_calculator",
                decision_driver="identity",
                category_involvement="high",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Came to wellness through Instagram in the post-COVID "
                "self-care wave; supplements are part of a clean-living "
                "identity, not performance.\n\n"
                "Rotates a plant protein (~₹2,000 a kilo), a biotin gummy "
                "(~₹700), and a magnesium for sleep; ₹2-3K a month, most of "
                "it found through Instagram rather than searched for.\n\n"
                "Scans for 'plant-based', 'clean', 'no maltodextrin'; does "
                "NOT track clinical dosages, does NOT know what inositol "
                "does, does NOT tell Type I from Type III collagen.\n\n"
                "Wants clean labels and Insta-coded brand aesthetics; rejects "
                "gym-bro positioning and opaque white tubs — 'not for me'; "
                "trusts a nutritionist's tag over an ad.\n\n"
                "Bought a plant collagen last month at ₹1,499 after a "
                "nutritionist's reel; mixes a scoop into oat milk before "
                "yoga; would switch for a cleaner brand under ₹1,500."
            ),
            demographic_bundles=_BUNDLES_ASPIRANT,
        ),
        # 3 — HIGH, skeptical. Coherence: skeptical + value_calculator +
        # function + mixed = serial switching driven by lack of visible proof.
        NamedDisposition(
            label="switcher_results_chaser",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="high",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Started taking hair and skin supplements after visible "
                "shedding during a stressful stretch; two years in, still "
                "chasing a brand that visibly works.\n\n"
                "Has cycled through four or five hair-and-skin brands in two "
                "years, switching each time one 'does nothing visible after "
                "three months'; spends ₹1.5-2.5K a month.\n\n"
                "Knows what biotin and collagen 'are supposed to do' and "
                "reads back-of-pack lists; does NOT see a dermatologist "
                "first, does NOT track a baseline, does NOT distinguish "
                "collagen types.\n\n"
                "Wants a visible result inside 90 days and a heavy "
                "verified-review count wherever they buy (500+ at 4 stars); "
                "rejects brands that 'look pretty on Insta but did nothing'.\n\n"
                "Six weeks into their current collagen at ₹1,499, with photos "
                "on their phone from the week they started; has told "
                "themselves they'll give it eight more weeks."
            ),
            demographic_bundles=_BUNDLES_SWITCHER,
            # §2.3 — THE DISPOSITION THE SCOPE FIELD EXISTS FOR, and the only
            # one scoped so far. This is a BEAUTY-SUPPLEMENT persona: hair and
            # skin, biotin and collagen, shedding, review density. It is
            # correct there. It was then run unchanged against a PROTEIN BAR,
            # and 43 of 100 persona cores carried its vocabulary before seeing
            # any ad — the panel arrived pre-loaded with the wrong product's
            # language. The advisory fires correctly today (verified on the
            # 2026-08-11 protein-bar run); the scope stays even though
            # render-10 stripped the brand names, because the SUBJECT of the
            # persona is still collagen/biotin — that is what it is scoped on.
            #
            # ⚠ Scoping is opt-in, ONE disposition at a time, on evidence. The
            # other six here stay unscoped deliberately: an advisory that fired
            # everywhere on its first run would be noise, and a guess at a scope
            # is worse than no scope. `doctor_triggered_vitamin` is the obvious
            # next candidate (a prescribed-deficiency persona, not a protein
            # one) — but nobody has MEASURED that one leaking, so it is left
            # for whoever does.
            authored_for=[
                "collagen", "biotin", "hair supplement", "skin supplement",
                "beauty supplement",
            ],
        ),
        # 4 — MEDIUM. Coherence: neutral + price_first + function + family =
        # brand-indifferent, doctor-driven, "medicine not lifestyle".
        # EXCLUDED from the cold-traffic audience below (ignores every
        # wellness-brand ad); belongs in a deficiency/medical audience.
        NamedDisposition(
            label="doctor_triggered_vitamin",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="function",
                category_involvement="medium",
                prior_experience_valence="neutral",
                channel_behavior="quick_commerce",
                life_stage="family",
            ),
            anchor=(
                "Does not think of themselves as a 'supplements person', yet "
                "takes three daily — all because a blood test flagged a "
                "deficiency and a doctor named them.\n\n"
                "Takes a weekly 60K IU vitamin-D sachet (~₹35), an iron "
                "tablet, and a calcium; reorders from the same pharmacy app "
                "the household uses for its other medicines.\n\n"
                "Knows the deficiency number and that they take it "
                "'because the doctor said'; does NOT know what an IU is, does "
                "NOT compare brands, does NOT look at the D2C wellness "
                "shelf.\n\n"
                "Wants prescription-grade reliability, the doctor-named "
                "brand, and pharmacy convenience; rejects supplements that "
                "'feel marketed at gym types or influencers' — this is "
                "medicine, not lifestyle.\n\n"
                "Reorders the week the last sachet runs out; the only date "
                "that matters is the next blood test, and the report goes "
                "back to the same doctor."
            ),
        ),
        # 5 — LOW, burned. Coherence: lapsed + skeptical + burned + low =
        # the structurally honest scroll-past buyer. Load-bearing.
        NamedDisposition(
            label="skeptic_lapsed_protein",
            vector=DispositionVector(
                category_relationship="lapsed",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="low",
                prior_experience_valence="burned",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Joined a gym once on a motivation spike and bought protein "
                "to match; quit within six months; now reflexively distrusts "
                "the whole supplement pitch.\n\n"
                "Bought a ₹1,599 tub of whey their gym trainer pushed on them "
                "online in 2024; used about 60%, the rest sat in the "
                "cupboard for a year until it got binned.\n\n"
                "Knows whey is 'for muscle' and 'you have to actually work "
                "out for it to do anything'; does NOT think supplements alone "
                "do anything, does NOT tell concentrate from isolate.\n\n"
                "Wants proof something measurably works; rejects ad copy "
                "promising 'muscle gain' or 'fat loss' without conditions; "
                "half-remembers that 'most Indian protein is adulterated'.\n\n"
                "The binned tub is still a running joke with their flatmate — "
                "the ₹1,600 cupboard decoration — and they retell it whenever "
                "someone at work says they're starting the gym."
            ),
            demographic_bundles=_BUNDLES_SKEPTIC,
        ),
        # 6 — LOW/occasional. Coherence: occasional + neutral + price_first +
        # habit = the "snack not supplement" mental model. Load-bearing.
        NamedDisposition(
            label="pragmatist_protein_snacker",
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="habit",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="quick_commerce",
                life_stage="early_career",
            ),
            anchor=(
                "Would never call themselves 'into fitness', but keeps a "
                "protein bar around as a less-guilty snack; the supplements "
                "world feels like someone else's.\n\n"
                "Grabs a 20g protein bar five-pack (~₹625) off a "
                "quick-commerce app or the airport store; reaches for one "
                "instead of a biscuit during a 4pm crash about three times a "
                "week.\n\n"
                "Knows the bars have 'more protein than a chocolate bar'; "
                "does NOT see them as 'supplements', does NOT read past the "
                "front of the pack, does NOT track macros.\n\n"
                "Wants taste, portability, and 'feeling less guilty than a "
                "Snickers'; rejects whey powder and the whole visible "
                "gym-supplements aisle — not their world.\n\n"
                "Keeps two bars in a desk drawer and one in the laptop bag; "
                "only restocks when the drawer is empty, usually tacked onto "
                "a grocery order they were placing anyway."
            ),
            demographic_bundles=_BUNDLES_SNACKER,
        ),
        # 7 — LOW, hostile-to-category. Coherence: never + hostile +
        # quality_first(food) + identity + low = the food-first rejecter who
        # actively resents the wellness shelf. Distinct from #5 (disappointed)
        # — this one thinks the whole category is a scam on principle.
        NamedDisposition(
            label="purist_food_first",
            vector=DispositionVector(
                category_relationship="never",
                brand_stance="hostile",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="offline_first",
                life_stage="settled",
            ),
            anchor=(
                "Buys no supplements on principle; believes a home kitchen of "
                "dal, rice, ghee, eggs and milk already does everything a "
                "powder claims.\n\n"
                "The only pill in the house is a doctor-prescribed vitamin-D "
                "someone takes; the D2C wellness shelf has never entered the "
                "monthly shop.\n\n"
                "Has absorbed the headlines — 'most Indian protein is "
                "adulterated', 'multivitamins are a waste' — but does NOT "
                "read the studies; anti-supplement, not anti-medicine.\n\n"
                "Believes real food and a grandmother's wisdom beat any "
                "powder; sees the wellness shelf as marketing that "
                "manufactures anxiety; repeats what the food-first "
                "nutritionists and the doctors who call out adulterated "
                "protein say.\n\n"
                "Cooks dal, rice and a vegetable most nights and packs the "
                "same for lunch; when a cousin brought a protein tub home "
                "last year it was an argument at the dinner table for a week."
            ),
            demographic_bundles=_BUNDLES_PURIST,
        ),
    ]
    return DispositionLibrary(
        library_id=LIBRARY_ID,
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        dispositions=dispositions,
    )


# ---- Demographics: 3 addressability frames spanning the buyer reality ----
#
# These own gender / age / income / geography / occupation. They cross-
# product with the (now demographic-free) dispositions, so some atypical
# cells appear (e.g. a female macros-lifter, a male clean-label buyer) —
# valid panel members, and how the engine is designed to work (panel.py).

_DEMO_MALE_PERFORMANCE = DemographicPoint(
    gender="male",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Bangalore / metro tier-1",
    occupation_hint="software engineer at a mid-stage SaaS startup",
    household_hint="shares a 2-3BHK with flatmates; sends money home monthly",
)

_DEMO_FEMALE_WELLNESS = DemographicPoint(
    gender="female",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Mumbai / Bangalore metro",
    occupation_hint="early/mid-career — marketing, design, product",
    household_hint="single or recently married; 1-2BHK in the metro core",
)

_DEMO_METRO_SETTLED = DemographicPoint(
    gender="any",
    age_band="35_44",
    income_tier="affluent",
    geography="metro tier-1 (Chennai / Pune / Delhi)",
    occupation_hint="settled professional — finance, corporate, family head",
    household_hint="married with kids; runs the household shop",
)


# ---- Context envelope: 4 attention states where a wellness ad is met ----

_CONTEXT_ENVELOPE = [
    NamedContext(
        label="commute_scroll",
        vector=ContextVector(
            attention_level="low", device_posture="commute",
            intent_state="killing_time", energy_state="drained",
            social_setting="public",
        ),
    ),
    NamedContext(
        label="pre_purchase_research",
        vector=ContextVector(
            attention_level="high", device_posture="desk",
            intent_state="actively_shopping", energy_state="alert",
            social_setting="alone",
        ),
    ),
    NamedContext(
        label="late_night_wind_down",
        vector=ContextVector(
            attention_level="low", device_posture="lying_down",
            intent_state="killing_time", energy_state="drained",
            social_setting="alone",
        ),
    ),
    NamedContext(
        label="weekend_afternoon_browse",
        vector=ContextVector(
            attention_level="medium", device_posture="couch",
            intent_state="passive_browse", energy_state="neutral",
            social_setting="alone",
        ),
    ),
]


def _audience_spec(pack) -> AudienceSpec:
    """Cold acquisition traffic — health_wellness_nutrition.

    6 of the 7 dispositions (obsessive → high → high → low → low → low),
    deliberately scroll-past-heavy so the panel isn't engaged-buyers-only.
    doctor_triggered_vitamin is EXCLUDED — they ignore every wellness-brand
    ad; that disposition belongs in a separate deficiency/medical audience
    for vitamin-positioning brands.
    """
    return AudienceSpec(
        demographics=[
            _DEMO_MALE_PERFORMANCE,
            _DEMO_FEMALE_WELLNESS,
            _DEMO_METRO_SETTLED,
        ],
        disposition_labels=[
            "enthusiast_macros_lifter",
            "aspirant_clean_label",
            "switcher_results_chaser",
            "skeptic_lapsed_protein",
            "pragmatist_protein_snacker",
            "purist_food_first",
        ],
        context_envelope=_CONTEXT_ENVELOPE,
        chaos_distribution=pack.default_chaos_distribution,
        panel_size=100,
    )


# Conservative D2C-wellness-on-Meta baseline placeholders. Supplement
# conversion runs a touch higher than CPG (considered purchase, review-led)
# but trust friction is high. Replace with the customer's real numbers.
_BASELINE_FUNNEL = {
    "stop_rate": 0.11,
    "click_rate": 0.020,
    "visit_rate": 0.012,
    "convert_rate": 0.006,
}


def main() -> None:
    print("=== scaffolding health_wellness_nutrition starter ===")

    # 1. Entity model on disk — the disposition library does NOT depend on
    #    the artifact pack, so it always materializes.
    account = Account(account_id=ACCOUNT_ID, name="Demo — Health & Wellness Nutrition")
    account.validate()
    account.save()

    library = _library()
    library.validate()
    lib_path = library.save()
    print(f"  disposition library: {len(library.dispositions)} hand-mapped "
          f"dispositions -> {lib_path}")

    # 2. The AudienceSpec + BrandProfile need the artifact pack (chaos mix +
    #    brand-name validation at render time). If it isn't built yet, save
    #    the library and stop with a clear next step.
    try:
        pack = load_pack(CATEGORY)
    except Exception as exc:  # noqa: BLE001 — pack module not built yet
        print()
        print(f"  artifact pack '{CATEGORY}' not found ({exc.__class__.__name__}).")
        print("  Library is saved. Build packs/health_wellness_nutrition.py")
        print("  next (brand landscape + price points + voice samples +")
        print("  chaos), then re-run this scaffold for the AudienceSpec.")
        print()
        print("PARTIAL — library scaffolded; pack + audience pending.")
        return

    print(f"  artifact pack OK — {len(pack.brand_landscape)} brands, "
          f"{len(pack.price_points)} price points")

    brand = BrandProfile(
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        categories=[CATEGORY],
        library_id=LIBRARY_ID,
        audience_ids=[AUDIENCE_ID],
    )
    brand.validate()
    brand.save()

    spec = _audience_spec(pack)
    spec.validate()
    audience = SavedAudience(
        audience_id=AUDIENCE_ID,
        name="Cold acquisition traffic — health & wellness nutrition",
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        spec=spec,
    )
    audience.validate()
    aud_path = audience.save()
    print(f"  saved audience: {len(spec.disposition_labels)} dispositions x "
          f"{len(spec.context_envelope)} contexts x "
          f"{len(spec.demographics)} demographics, panel_size="
          f"{spec.panel_size} -> {aud_path}")

    # 3. Standalone spec + baseline JSON for batch_run.py --audience-spec.
    specs_dir = Path(__file__).resolve().parent.parent / "specs"
    specs_dir.mkdir(exist_ok=True)
    spec_path = specs_dir / "health_wellness_cold_traffic.json"
    spec_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))
    baseline_path = specs_dir / "health_wellness_baseline.json"
    baseline_path.write_text(json.dumps(_BASELINE_FUNNEL, indent=2))
    print(f"  standalone audience spec -> {spec_path}")
    print(f"  sample baseline funnel  -> {baseline_path}")

    print()
    print("PASS — health_wellness_nutrition starter scaffolded.")


if __name__ == "__main__":
    main()
