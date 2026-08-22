#!/usr/bin/env python3
"""Generate a MECE audience — many different opinions, not a few scaled up.

    .venv/bin/python scripts/generate_audience.py --dry-run          # $0, prints the plan
    .venv/bin/python scripts/generate_audience.py --market snacking  # ~$1 (PAID)

    # a REGION — the demographic slice these opinions are written FOR
    .venv/bin/python scripts/generate_audience.py --dry-run \
        --gender female --age 45-60 --income 3-17 --tier tier-3

WHO THESE PEOPLE ARE, AND WHY IT IS A GENERATION INPUT (2026-08-15)
-------------------------------------------------------------------
Every buyer type is written FOR a declared region, and every bundle is one
SPECIFIC PERSON — one age, one income — not a band.

⚠ THE DEFECT THAT FORCED BOTH. The first run of this script was given no
demographic brief, so the model wrote everyone into the single world it could
infer: oldest person 54, zero tier-3, 36 metro / 31 tier-2 / 7 tier-1. Measured
against that library, the shipped buy reached 31 of 32 buyer types — but a
`women 45-60` buy reached TWO, and `women 55-75` reached ZERO. Neither raised
anything: a buy with nobody in it falls back to the declared frames, so it
returns MORE types than a partial match, as blank shells with no job and no
household. The panel looked FULLER the worse the mismatch got.

Bands caused the second half of it. A band is clipped to the buy at run time,
which simulated a "Coimbatore / tier-2 staff nurse" under a tier-3 brief and
stranded careers outside the income they need. A person is selected in-or-out by
ANY customer-chosen range — 45-60, 47-63, 50-55 — because
`panel._range_overlap_frac` already special-cases a zero-width range, and
`panel._clip_point` leaves a point untouched so the city and career survive.

⚠ THE REGION IS NOT A FILTER APPLIED AFTERWARDS. It is the brief, because the
OPINION changes with the demographic and not just the name tag. A 26-year-old
Mumbai skeptic doubts whether "20g protein" is real protein; a 52-year-old
tier-3 skeptic doubts whether packaged food is food. Reusing one opinion across
both is voice diversity, which is not opinion diversity.

⚠ GENDER IS A GENERATION AXIS for the same reason — and measured: 27 of the 32
types in the first library carried BOTH genders, i.e. unisex opinions with a
gender stapled on. `distinctness_key` had to widen with it: `gender` is not one
of the eight vector axes, so a men's and a women's version of one cell collide
on an identical coordinate and the old key would have culled one as a duplicate.

⚠ A CELL MAY BE REFUSED. The grid is MECE by construction, and demanding every
cell be filled for a narrow region is a demand to invent people. `refusals`
carries the cell and the reason, gate 4 counts it as ADDRESSED, and the retry
loop never re-asks it.

THE DEFECT THIS EXISTS FOR, MEASURED 2026-08-13
-----------------------------------------------
A 100-agent panel produced **3 distinct behavioural positions**. The pyramid:

        5 dispositions      <- the only real opinion-generators
       15 biographies       <- the same 5 stances wearing different name tags
       45 rendered people
      100 agents            <- 45 people under 4 contexts x 3 chaos x 3 cycles

Context and chaos were standing in for population diversity. Hand-authoring more
dispositions does not fix it: 6 stances is 6 opinions however many biographies
you hang off them, and each one costs 30-40 minutes of human authoring.

WHAT THIS DOES
--------------
Composes buyer types from a **demand-space grid** — occasions x stances — so the
set is MECE by construction: mutually exclusive because two types cannot occupy
one cell, collectively exhaustive because every cell in the brief is filled.

⚠ THE GRID IS THE WHOLE POINT, AND IT IS WHY THE SUPERYOU RUN FAILED. That run's
library was scoped to PROTEIN SUPPLEMENTS: 20 brands, zero confectionery, every
price point a ₹1,250-4,800 tub. The ad was aimed at someone who would otherwise
buy a chocolate bar — a person who could not exist in that world, because the
thing they trade up FROM was not in it. Scope the grid to the DEMAND SPACE (the
4pm slump) and not to the product category (protein), and the buyer becomes
representable.

WHAT IT DOES NOT DO
-------------------
⚠ It makes the audience SCALABLE, not CORRECT. A generated library carries
exactly the same never-validated-against-humans status as a hand-built one. The
gates below test discrimination and diversity; nothing here tests truth.

⚠ It does not touch `health_wellness_nutrition`. Output goes to a NEW brand
profile so the one validated library on disk stays byte-identical and the two
stay comparable.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(override=True)

from agent import demography
from agent.artifact_pack import load_pack
# ⚠ The NOTE FORMAT belongs to the engine, not to this script: panel
# selection parses it back at run time to stratify across the grid. One
# definition, in agent/population.py.
from agent.population import notes_for, parse_notes  # noqa: F401
from agent.vectors import (
    DemographicBundle,
    DemographicPoint,
    DispositionVector,
    NamedDisposition,
    _VALID_DISPOSITION,
)

# ⚠ IMPORTED, NOT RE-IMPLEMENTED. `--fill` must re-ask for exactly the types the
# admissibility checker would reject, or the two drift and a file can pass one
# and fail the other. See `ceiling_failures`' docstring.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_generated_audience import (  # noqa: E402
    ceiling_failures,
    distinctness_key,
)

MODEL = "claude-opus-5"
_PER_BATCH = 5


# --------------------------------------------------------------------------
# THE DECLARED REGION — the demographic slice a generation is written FOR.
# --------------------------------------------------------------------------
# ⚠ THE DEFECT THIS FIXES, MEASURED 2026-08-15. The first generation was never
# given a demographic brief, so the model wrote everyone into the world of the
# one brief it could infer: oldest person 54, zero tier-3, 36 metro / 31 tier-2
# / 7 tier-1. Against the shipped buy that library reached 31 of 32 types; a
# `women 45-60` buy reached TWO, and `women 55-75` reached ZERO — and neither
# raised anything, because a buy with no one in it falls back to blank frames
# and returns MORE types, not fewer.
#
# A region is not a filter applied afterwards. It is the brief the opinions are
# WRITTEN for, because the opinion is what changes with the demographic: a
# 26-year-old Mumbai skeptic doubts whether "20g protein" is real protein; a
# 52-year-old Nagpur skeptic doubts whether packaged food is food. Those are two
# opinions, not one opinion in two outfits.

@dataclass(frozen=True)
class Region:
    """The demographic slice a batch of buyer types is authored for."""

    gender: str = "any"
    age_min: int = 18
    age_max: int = 75
    income_min: float = 0.0
    income_max: float = 100.0
    tier: str = "any"

    @property
    def key(self) -> str:
        """A short stable id — goes in `notes`, and disambiguates across
        generations when a population accumulates."""
        g = {"any": "a", "female": "f", "male": "m"}[self.gender]
        t = self.tier.replace("tier-", "t").replace("any", "ta")
        return (f"{g}{self.age_min}-{self.age_max}"
                f"_{self.income_min:g}-{self.income_max:g}_{t}")

    def contains(self, gender: str, age: int, income: float) -> bool:
        """⚠ The same in-or-out test `panel.demographic_overlap` will apply to
        these people at run time. Checked here so a person who could never be
        selected is never written."""
        if self.gender != "any" and gender not in (self.gender, "any"):
            return False
        return (self.age_min <= age <= self.age_max
                and self.income_min <= income <= self.income_max)

    def brief(self) -> str:
        who = {"any": "adults of any gender", "female": "women", "male": "men"}[
            self.gender]
        money = ("any household income" if (self.income_min, self.income_max)
                 == (0.0, 100.0) else
                 f"household income ₹{self.income_min:g}-{self.income_max:g} LPA")
        where = "any city tier" if self.tier == "any" else self.tier
        return (f"{who}, aged {self.age_min}-{self.age_max}, {money}, {where}")


def _parse_range(text: str, what: str) -> tuple[float, float]:
    try:
        lo, hi = text.split("-", 1)
        lo_f, hi_f = float(lo), float(hi)
    except ValueError:
        raise SystemExit(f"--{what} must look like 45-60, got {text!r}") from None
    if lo_f > hi_f:
        raise SystemExit(f"--{what} is inverted: {text!r}")
    return lo_f, hi_f


# --------------------------------------------------------------------------
# THE DEMAND SPACE — layer 2 of the architecture, and the layer that did not
# exist before today. An occasion, not a person: the trigger, what actually
# gets bought (INCLUDING "nothing"), what decides it, and where.
#
# ⚠ Every competitive set here names things OUTSIDE the protein category on
# purpose. A grid whose alternatives are all protein products reproduces the
# SuperYou failure with more steps.
# --------------------------------------------------------------------------

SNACKING_GRID = {
    "market": "Indian urban snacking and nutrition",
    "occasions": [
        {
            "key": "desk_slump_4pm",
            "moment": "the 4pm dip at a desk — hungry, flagging, two hours from dinner",
            "competes_with": "biscuits from the office jar, a chocolate bar, samosa/vada from "
                             "the canteen, chai, a banana, or skipping it entirely",
            "decided_by": "speed, taste, what is within arm's reach, mild guilt",
            "channel": "office pantry, vending machine, the desk drawer stocked on Blinkit",
        },
        {
            "key": "late_night_craving",
            "moment": "11pm, scrolling in bed, wants something sweet",
            "competes_with": "chocolate, ice cream, leftover mithai, biscuits, nothing",
            "decided_by": "craving, what is in the fridge, 10-minute delivery",
            "channel": "Blinkit / Zepto / Instamart, the kitchen cupboard",
        },
        {
            "key": "post_workout",
            "moment": "straight after the gym, 45 minutes before a proper meal",
            "competes_with": "a whey shake, eggs, a banana, dal-chawal at home, nothing",
            "decided_by": "protein per serving, habit, what the trainer said",
            "channel": "gym counter, HealthKart, Amazon, the gym bag",
        },
        {
            "key": "breakfast_on_the_run",
            "moment": "leaving the house late, will not sit down to eat",
            "competes_with": "toast, poha, cereal, a bought sandwich, coffee alone, skipping",
            "decided_by": "one hand, no crumbs, keeps until 11am",
            "channel": "kitchen counter, the metro station kiosk, monthly grocery order",
        },
        {
            "key": "guilt_free_treat",
            "moment": "a weekend or a bad day — wants a treat but not to feel bad about it",
            "competes_with": "dark chocolate, a 'healthy' dessert, regular chocolate anyway, fruit",
            "decided_by": "permission — whether it reads as a treat or as a compromise",
            "channel": "quick commerce, the supermarket aisle, a cafe",
        },
        {
            "key": "travel_and_commute",
            "moment": "airport, long drive, or a two-hour commute with no real meal in sight",
            "competes_with": "airport sandwich, chips, nuts, a Snickers at the counter, nothing",
            "decided_by": "portability, shelf life, what the counter is selling",
            "channel": "airport store, highway stop, petrol pump, packed from home",
        },
        {
            "key": "daily_health_routine",
            "moment": "a standing daily habit someone has decided to keep",
            "competes_with": "a powder, gummies, a multivitamin, real food, nothing",
            "decided_by": "routine, whether it is working, cost per day",
            "channel": "Amazon subscribe, HealthKart, the pharmacy, D2C",
        },
        {
            "key": "household_stock_up",
            "moment": "the monthly or weekly shop — buying for other people as well as themselves",
            "competes_with": "biscuit packs, namkeen, cereal, whatever the kids will eat",
            "decided_by": "price per unit, family acceptance, keeps in the cupboard",
            "channel": "supermarket, BigBasket, the local kirana",
        },
    ],
    # ⚠ THE COMPETITIVE SET, AND IT IS THE FIX FOR THE SUPERYOU FAILURE.
    #
    # The category pack holds 20 brands and NOT ONE of them is confectionery —
    # every price point is a ₹1,250-4,800 tub. So a persona built from the pack
    # alone lives in a world with no chocolate bar in it, and literally cannot
    # weigh "this instead of that" for a product whose whole pitch is being the
    # better version of a 4pm chocolate bar. The pack is scoped to a PRODUCT
    # CATEGORY; a demand space needs what people actually choose between.
    #
    # These are nameable alongside the pack's brands. Real products, real
    # prices, the things that genuinely win the occasion most of the time.
    "everyday_alternatives": [
        "Cadbury Dairy Milk — ₹10 to ₹100 depending on size; the default sweet thing",
        "Snickers — ~₹40 for 50g; the 'it's basically food' bar at the counter",
        "KitKat / Perk / Munch — ₹10-₹40 impulse chocolate",
        "Britannia Good Day, Marie Gold, 50-50, Bourbon — ₹10-₹40 biscuit packs",
        "Parle-G — ₹5-₹10; the floor of the category",
        "Sunfeast Dark Fantasy — ~₹30; the indulgent biscuit",
        "Lay's / Kurkure / Bingo — ₹20 chips and namkeen",
        "Haldiram's namkeen — ₹20-₹50 packs, and the household tin",
        "Amul / Kwality Walls ice cream — ₹40-₹80 for the late-night version",
        "canteen samosa, vada pav, or chai — ₹10-₹25, hot and immediate",
        "a banana or an apple from the fruit cart — ₹10-₹20",
        "leftover mithai in the fridge after any festival",
        "nothing at all — waiting it out until the next meal",
    ],
    # The reusable stance grammar. Category-independent by design — what changes
    # per occasion is what they are skeptical OF, not that they are a skeptic.
    "stances": [
        "loyalist", "switcher", "upgrader", "aspirant", "skeptic",
        "purist", "pragmatist", "gifter",
    ],
}

# --------------------------------------------------------------------------
# THE F&B DEMAND MAP — 21 moments, all of food & beverage, built once per market.
#
# ⭐⭐ USER DECISION 2026-08-21 (session 47): THE MAP REPLACES THE GRID. Settled
# on the five real days in `docs/fnb_real_events.md` — on the 34 items a
# snacking-and-nutrition grid actually claims, SNACKING_GRID placed 3 and this
# map placed 29.
#
# ⚠⚠ TRANSCRIBED, NOT AUTHORED. Every `question` below is VERBATIM from the
# published map (artifact e6332193-5226-40ac-916f-89ccb9f6cbc8), and every
# `competes_with` starts from that card's own "instead" list. ⚠ Do not rewrite a
# question from memory — a name-only reconstruction has already put Stock-up in
# the wrong band once.
#
# ⭐⭐⭐ WHY `question` IS A FIELD AND NOT A COMMENT. The single biggest finding of
# the five real days is that SNACKING_GRID's cells fail because they are written
# as VIGNETTES: "the 4pm dip AT A DESK" threw out three real people's afternoon
# chai (none of the three was at a desk); "wants something SWEET" threw out Maggi
# at 2am; "LEAVING LATE, will not sit down" threw out four sat-down breakfasts.
# Incidental scene-setting silently becomes an exclusion criterion.
#   The questions are what won 29-3. If they stayed in a doc, the generator would
# never see them and we would reproduce the defect at 176-cell scale. So the
# question IS the definition; `moment` is examples and carries no filter.
# See memory `cell_is_a_question_not_a_vignette`.
#
# ⚠ ONE DELIBERATE DEVIATION FROM THE PUBLISHED MAP, and it is the only one:
# `at_home_tea_or_snack` replaces the published `Evening tea`, whose question was
# "is the HOUSEHOLD SITTING DOWN TOGETHER with tea?". The published pair cut on
# two DIFFERENT AXES — the afternoon dip on LOCATION (away from home), evening
# tea on COMPANY — which left a hole at "at home + alone" that took 5 of one
# housewife's 12 items. Re-cut on location alone. ✓ Verified against all 52 real
# items: it catches those five and wrongly catches nothing.
#
# ⭐⭐ SECOND DELIBERATE DEVIATION, DECIDED BY THE USER 2026-08-21: the published
# map's two dinner cells are MERGED into one `evening_meal`, because it split
# dinner by provenance while leaving lunch whole. So this map is 21 moments, not
# the published 22. Full reasoning at the cell itself.
# --------------------------------------------------------------------------

FNB_MAP = {
    "market": "Indian urban food and beverage",
    # ⭐ `band` drives tie-break 1 (event beats clock) and tie-break 2 (clock
    # beats habit). It is a real property of the moment, not a display grouping.
    "occasions": [
        # ---- THE CLOCK: triggered by time of day, and the day is a sequence ----
        {
            "key": "first_cup", "band": "clock",
            "question": "Is this the first thing consumed today, before any food?",
            "moment": "the first thing of the day, before any food",
            "competes_with": "chai, filter coffee, instant coffee, green tea, "
                             "hot water and lemon, or nothing until breakfast",
            "decided_by": "habit, who else is awake, what is already in the house",
            "channel": "the kitchen at home, the tea stall on the way out",
        },
        {
            "key": "breakfast_sat_down", "band": "clock",
            "question": "Is a morning meal being eaten at a table?",
            "moment": "a morning meal eaten sitting down",
            "competes_with": "poha, upma, idli, paratha, cereal, oats, bread and egg, "
                             "last night's leftovers",
            "decided_by": "what the household eats, who cooked, how much time there is",
            "channel": "the home kitchen, the monthly grocery order",
        },
        {
            "key": "breakfast_in_motion", "band": "clock",
            "question": "Is morning food being eaten standing, travelling, or at a desk?",
            "moment": "morning food taken standing, on the way, or at a desk",
            "competes_with": "a banana, biscuit and chai at the stall, a packaged bar, "
                             "a bought sandwich, an aloo patty, skipping it",
            "decided_by": "one hand, no crumbs, whether it lasts until lunch",
            "channel": "the stall outside, a station kiosk, the desk drawer",
        },
        {
            "key": "mid_morning_break", "band": "clock",
            "question": "Is this the pause at work or college before lunch?",
            "moment": "the pause at work or college between breakfast and lunch",
            "competes_with": "canteen chai and biscuit, a vending machine, something "
                             "brought from home, black coffee alone, nothing at all",
            "decided_by": "whether the break exists, who is going, what is nearby",
            "channel": "the office pantry, the college canteen, the cart outside",
        },
        {
            "key": "midday_meal", "band": "clock",
            "question": "Is this lunch, wherever it came from?",
            "moment": "lunch, from any source",
            "competes_with": "tiffin from home, a canteen thali, ordered in, a food "
                             "court, a colleague's box, a meal the employer provides",
            "decided_by": "what was packed or provided, price, how long the break is",
            "channel": "home tiffin, the canteen, a delivery app, the bhojanalay",
        },
        {
            "key": "afternoon_dip", "band": "clock",
            "question": "Is this the 3-6pm energy trough, away from home?",
            # ⚠⚠ "away from home", NEVER "at a desk". The desk wording is exactly
            # what cost SNACKING_GRID three real people: a building site, a chai
            # tapri and a college canteen are all this moment and none is a desk.
            "moment": "the mid-afternoon trough, somewhere that is not home",
            "competes_with": "chai and biscuit, coffee, namkeen, chocolate, fruit, "
                             "a samosa or vada pav, fafda, a protein bar, nothing",
            "decided_by": "speed, what the stall or canteen sells, who else is going",
            "channel": "the canteen, the tea stall outside, the office pantry, a cafe",
        },
        {
            "key": "at_home_tea_or_snack", "band": "clock",
            # ⚠ THE ONE DEVIATION. Published question was "is the household sitting
            # down together with tea?" — see the header note. Cut on LOCATION so it
            # is the true partner of `afternoon_dip` and the hole closes.
            "question": "Is this an at-home tea or snack between lunch and dinner?",
            "moment": "tea or something to eat at home in the afternoon, alone or with "
                      "whoever is in",
            "competes_with": "chai with biscuits or khaari, pakora and fried things, "
                             "rusk, namkeen, bread and jam, instant noodles, "
                             "leftover mithai, fruit",
            "decided_by": "what is in the house, whether anyone else is home, habit",
            "channel": "the kitchen, the biscuit tin, a ten-minute delivery app",
        },
        {
            "key": "after_school_feed", "band": "clock",
            "question": "Is an adult deciding what a child eats on getting home?",
            "moment": "feeding a child as they come in from school",
            "competes_with": "something home-made, biscuits, malted milk, fruit, "
                             "a packaged snack the child asked for",
            "decided_by": "what the child will actually eat, whether it counts as food",
            "channel": "the kitchen, the household stock-up, the shop downstairs",
        },
        {
            "key": "evening_out_of_home", "band": "clock",
            "question": "Is this being bought and eaten outside, before dinner?",
            "moment": "something bought and eaten outside in the evening",
            "competes_with": "chaat, vada pav, momos, fresh juice, ice cream, "
                             "cinema popcorn, a cafe order",
            "decided_by": "who is there, what the street is selling, the mood",
            "channel": "the street cart, the market, a cafe, the cinema counter",
        },
        {
            # ⭐⭐ USER DECISION 2026-08-21: the two published dinner cells
            # (`Dinner at home` / `Dinner brought in`) are MERGED into one. The
            # published map split dinner by provenance and left lunch whole,
            # though a delivered lunch behaves exactly like a delivered dinner —
            # the Pune content creator's 1pm Zomato order is the case. Asked to
            # split lunch or merge dinner, the user merged.
            #
            # ⭐ The question is now source-agnostic and deliberately MIRRORS
            # `midday_meal`'s ("wherever it came from"), which is the consistency
            # the split was failing.
            #
            # ⚠ WHAT THE MERGE COSTS, STATED SO IT IS NOT FORGOTTEN: provenance
            # stops being visible in the cell. That is acceptable ONLY because
            # WHO PROVIDED THIS needs its own axis anyway — four of five real
            # people ate substantial food they did not buy, and no cell in either
            # map can express it. See `docs/fnb_real_events.md` finding 4.
            #
            # ⚠ It also absorbs, rather than fixes, finding 11: this cell holds a
            # family's Friday Zomato order AND a migrant worker eating dal-chawal
            # at a bhojanalay because he has no kitchen. Necessity and indulgence
            # in one cell. The description below must never pick one of them.
            "key": "evening_meal", "band": "clock",
            "question": "Is this the main evening meal, however it arrived?",
            "moment": "the main meal of the evening — cooked at home, ordered in, or "
                      "eaten out, by choice or because there is no kitchen",
            "competes_with": "roti-sabzi, rice-dal, khichdi, whatever was cooked, "
                             "Swiggy or Zomato, the restaurant downstairs, a bhojanalay "
                             "or mess, takeaway on the way home, a friend's house",
            "decided_by": "who cooks, cost, what is open, who is paying, "
                          "whether there is a kitchen at all",
            "channel": "the home kitchen, a delivery app, the eatery on the corner, "
                       "a friend's kitchen",
        },
        {
            "key": "late_night", "band": "clock",
            "question": "Is this after 10pm, unplanned, and usually alone?",
            # ⚠⚠ NOT "wants something sweet". That wording cost SNACKING_GRID a real
            # 2am plate of Maggi and chips.
            "moment": "after 10pm, unplanned, usually on your own",
            "competes_with": "instant noodles, chips, ice cream, chocolate, "
                             "leftover mithai, an app order, nothing",
            "decided_by": "what is in the cupboard, what will arrive in ten minutes",
            "channel": "quick commerce, the kitchen cupboard, a late delivery app",
        },
        {
            "key": "bedtime_cup", "band": "clock",
            "question": "Is a drink being had to end the day or help someone sleep?",
            "moment": "a drink that ends the day, for yourself or for someone else",
            "competes_with": "malted milk, plain or haldi doodh, herbal tea, nothing",
            "decided_by": "routine, whether it is for a child, whether it helps sleep",
            "channel": "the kitchen, the monthly grocery order",
        },
        # ---- THE EVENT: triggered by the calendar or by life. Unordered. ----
        {
            "key": "journey", "band": "event",
            "question": "Is a journey the reason this is being bought or packed?",
            "moment": "a journey — packed for it, or bought because of it",
            "competes_with": "theplas packed from home, station snacks, the airport "
                             "counter, a highway dhaba, biscuits and namkeen for the bag",
            "decided_by": "portability, shelf life, what the counter has, captive pricing",
            "channel": "packed at home, the station, the airport store, a highway stop",
        },
        {
            "key": "hosting", "band": "event",
            "question": "Is food being put out because someone else is in the house?",
            # ⚠ Written from the HOST's side. The GUEST has no cell in this map —
            # a real gap found on the five days, recorded, not yet fixed.
            "moment": "putting food out because someone has come over",
            "competes_with": "namkeen, mithai, a chocolate box, cold drinks, tea service, "
                             "something ordered in for everyone",
            "decided_by": "what looks right in front of a guest, what is in the tin",
            "channel": "the household stock-up, the sweet shop, a delivery app",
        },
        {
            "key": "festival_and_gifting", "band": "event",
            "question": "Is this bought for someone else, because of an occasion?",
            "moment": "buying for someone else because the calendar says so",
            "competes_with": "mithai boxes, dry fruit, chocolate hampers, "
                             "corporate gift packs",
            "decided_by": "what it says about the giver, price bracket, presentation",
            "channel": "the sweet shop, a supermarket gifting aisle, online hampers",
        },
        {
            "key": "celebration", "band": "event",
            "question": "Is there a reason to treat — a result, a promotion, a match?",
            "moment": "a reason to treat, alone or as a group",
            "competes_with": "cake, chocolate, ice cream, eating out, a round for "
                             "the office, a spread arranged by an employer",
            "decided_by": "the size of the occasion, who is paying, what is shared",
            "channel": "a bakery, a restaurant, a delivery app, the office pantry",
        },
        {
            "key": "recovery_and_care", "band": "event",
            "question": "Is someone unwell, pregnant, elderly or convalescing?",
            "moment": "food for someone who is unwell, pregnant, elderly or recovering",
            "competes_with": "khichdi, ORS, prescribed nutrition, home remedies, "
                             "what the doctor said, plain food",
            "decided_by": "what the doctor said, what will stay down, what is gentle",
            "channel": "the kitchen, the pharmacy, a prescription",
        },
        {
            "key": "fitness_session", "band": "event",
            "question": "Is this immediately before or after exercise?",
            "moment": "the window either side of exercise",
            "competes_with": "a whey shake, eggs, a banana, an electrolyte, "
                             "dal-chawal at home, nothing",
            "decided_by": "protein per serving, timing, what the trainer said",
            "channel": "the gym counter, specialist online, the gym bag",
        },
        # ---- THE STANDING HABIT: runs regardless of clock or calendar ----
        {
            "key": "daily_regimen", "band": "habit",
            "question": "Is this taken on a schedule, whether or not anyone is hungry?",
            # ⚠ NOT "a habit someone has DECIDED to keep". A doctor decides some of
            # these, and that wording put a real prescription outside the cell.
            "moment": "something taken on a schedule — chosen by them or prescribed",
            "competes_with": "a powder, gummies, a multivitamin, a prescribed tablet, "
                             "a high-protein drink, \"I'd rather just eat properly\"",
            "decided_by": "routine, whether it seems to work, cost per day, "
                          "whether a doctor said so",
            "channel": "a subscription, specialist online, the pharmacy, the kitchen",
        },
        {
            "key": "hydration", "band": "habit",
            "question": "Is this drunk for thirst rather than as part of a moment?",
            "moment": "drinking for thirst, not as part of anything else",
            "competes_with": "water, buttermilk, coconut water, a cold drink, juice, "
                             "an electrolyte, nimbu pani",
            "decided_by": "heat, what is cold and nearby, price",
            "channel": "the fridge, a shop counter, a street cart, the water bottle",
        },
        {
            "key": "household_stock_up", "band": "habit",
            "question": "Is this a purchase for later, by and for several people?",
            "moment": "the weekly or monthly shop — buying for other people too",
            "competes_with": "biscuit packs, namkeen, cereal, staples, "
                             "whatever the children will actually eat",
            "decided_by": "price per unit, family acceptance, what keeps",
            "channel": "the supermarket, online grocery, the local kirana, quick commerce",
        },
    ],
    # ⚠ HEADING DELIBERATELY DIFFERENT FROM SNACKING_GRID'S. Its heading reads
    # "WHAT THEY ACTUALLY BUY MOST OF THE TIME", and the five real days showed
    # that four of five people ate substantial food they did NOT buy — a boss, a
    # mother, a wife, a host. One man chose 2 of his 14 items. A grid that asks
    # only about buying cannot see most of the food.
    "alternatives_heading": "WHAT USUALLY WINS THESE MOMENTS — nameable, real, and "
                            "often not bought by the person who eats it:",
    "everyday_alternatives": [
        "chai — made at home, or ₹10-₹20 at a stall; the single most common thing "
        "in an Indian day and the default in at least four of these moments",
        "Parle-G / Britannia Marie, Good Day, 50-50 — ₹5-₹40 biscuit packs",
        "khaari, rusk, fafda, khakra, dhokla, pakoda, thepla, chakli, murukku — ₹10-₹50, "
        "regional and everyday, usually bought loose by weight from a farsan shop or a "
        "bakery with no brand and no date on it",
        "jalebi, mithai and the local halwai's sweets — bought by weight, and the thing "
        "a wife packs into a lunch tiffin without anybody calling it a treat",
        "canteen samosa, vada pav, aloo patty, momos — ₹10-₹40, hot and immediate",
        "Cadbury Dairy Milk, KitKat, Snickers — ₹10-₹100 impulse chocolate",
        "Lay's / Kurkure / Bingo — ₹20 chips",
        "Maggi and other instant noodles — ₹15-₹30, and the 2am default",
        "Amul buttermilk, Frooti, Sprite, Coke, fresh lime — ₹10-₹40 cold drinks",
        "filter coffee, instant coffee, a ₹250 cafe frappe at the other end",
        "Amul / Kwality Walls ice cream — ₹40-₹80",
        "a banana or an apple from the fruit cart — ₹10-₹20",
        "home food someone else cooked or packed — a tiffin, a thali, a spread the "
        "employer laid on; costs the eater nothing and still wins the moment",
        "nothing at all — waiting it out until the next meal",
    ],
    # Unchanged from SNACKING_GRID. A stance is category-independent by design:
    # what changes per moment is what they are skeptical OF.
    "stances": [
        "loyalist", "switcher", "upgrader", "aspirant", "skeptic",
        "purist", "pragmatist", "gifter",
    ],
}


GRIDS = {"snacking": SNACKING_GRID, "fnb": FNB_MAP}


# --------------------------------------------------------------------------
# The tool. Every vector axis is a CLOSED ENUM taken from agent.vectors, so the
# model cannot emit an invalid combination — the schema, not a validator, is
# what makes that true. The anchor is split into five NAMED fields rather than
# one blob so each line's job is enforceable and L3 can be checked for its
# refusals.
# --------------------------------------------------------------------------

def _tool(grid: dict) -> dict:
    return {
        "name": "emit_buyer_types",
        "description": "Emit the batch of buyer types you were asked for.",
        # ⚠ STRICT, and it is not optional. Without it, batch 4 of the first
        # real run emitted five types carrying only the prose fields — no
        # vector axes at all — despite all eight being in `required`. A
        # non-strict schema is a request, not a contract. `strict: true`
        # requires `additionalProperties: false` on every object level, which
        # is why they appear below.
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "buyer_types": {
                    "type": "array",
                    "description": "EXACTLY one entry per cell you were asked "
                                   "for, in the same order. Returning fewer "
                                   "than asked is the single most common "
                                   "failure — count them before you emit.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "<stance>_<2-3 word anchor key>, snake_case, "
                                               "e.g. skeptic_lapsed_protein. No brand names.",
                            },
                            "display_name": {
                                "type": "string",
                                "description": "WHAT A MARKETER READS for this buyer "
                                               "type, on a screen they pay for. 3-7 "
                                               "ordinary words naming the PERSON, not "
                                               "the stance: 'Desk worker who traded up "
                                               "from biscuits', 'Buys the office round "
                                               "at four'. ⚠ Never the label with its "
                                               "underscores removed, never a stance word "
                                               "on its own, no brand names. Sentence "
                                               "case, no trailing full stop.",
                            },
                            "occasion": {
                                "type": "string",
                                "enum": [o["key"] for o in grid["occasions"]],
                            },
                            "stance": {"type": "string", "enum": grid["stances"]},
                            **{
                                dim: {"type": "string", "enum": sorted(valid)}
                                for dim, valid in _VALID_DISPOSITION.items()
                            },
                            "l1_context": {
                                "type": "string",
                                "description": "HOW THEY CAME TO THE CATEGORY. <=30 words. "
                                               "⚠ NO age, NO city, NO job, NO income, NO gender "
                                               "— those live in the bundles.",
                            },
                            "l2_category": {
                                "type": "string",
                                "description": "How they interact with the category: frequency, "
                                               "channel, typical price band, one habit. <=30 words.",
                            },
                            "l3_knowledge": {
                                "type": "string",
                                "description": "What they know AND explicitly what they do not. "
                                               "MUST contain at least two 'does NOT' clauses. "
                                               "This is the ceiling that stops consultant voice.",
                            },
                            "l4_stance": {
                                "type": "string",
                                "description": "What they want and what they REJECT, and why. "
                                               "Must contain an explicit rejection. <=30 words.",
                            },
                            "l5_behavior": {
                                "type": "string",
                                "description": "ONE recent thing they actually DID, named at "
                                               "product and channel level. A specific act, not a "
                                               "summary. ⚠ A single price is allowed as texture; "
                                               "COMPARING two prices, or any per-gram / multiple "
                                               "arithmetic, is banned — write the behaviour, not "
                                               "the calculation. <=30 words.",
                            },
                            "bundles": {
                                "type": "array",
                                "description": "2-4 SPECIFIC PEOPLE who hold this stance. Each "
                                               "is one person with one age and one income — "
                                               "'Lakshmi is 52 and earns ₹5.4L', never 'women "
                                               "45-54 on ₹4-8L'. Every one of them must fall "
                                               "inside the declared region. Vary them within "
                                               "it: different ages, different cities, different "
                                               "work. ⚠ AND VARY WHAT THEY LACK, not only what "
                                               "they have. Across the people you write, the "
                                               "region's population figures should be visible: "
                                               "some with no paid work, some with no spouse, "
                                               "some with four children and some with none, "
                                               "some doing manual or farm work. Writing every "
                                               "one of them employed, married and comfortable "
                                               "is the measured failure of this field — see "
                                               "rule 6.",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "gender": {"type": "string",
                                                   "enum": ["male", "female", "any"]},
                                        # ⚠ ONE AGE, ONE INCOME — the schema, not a
                                        # validator, is what makes a band unemittable.
                                        # A band gets clipped to the buy at run time,
                                        # which is what produced a "Coimbatore /
                                        # tier-2 staff nurse" under a tier-3 brief and
                                        # stranded careers outside their own range.
                                        "age": {
                                            "type": "integer",
                                            "description": "This person's age, in years. "
                                                           "Not a range.",
                                        },
                                        # ⚠ THE FLOOR GOES MISSING BEFORE THE
                                        # JOBS DO. In the audited region the
                                        # median household sat at ₹5.5L and
                                        # almost nobody was near the bottom —
                                        # and the manual, farm and domestic
                                        # workers were missing in exactly the
                                        # same proportion. The two failures are
                                        # one: an income band that never goes
                                        # low cannot hold the people who do
                                        # that work. ⚠ NO SOURCED INCOME
                                        # DISTRIBUTION EXISTS ON DISK — NFHS
                                        # publishes wealth quintiles, not
                                        # rupees — so this states the
                                        # CONSTRAINT and invents no number.
                                        "income_lpa": {
                                            "type": "number",
                                            "description": "This person's annual HOUSEHOLD "
                                                           "income in lakhs. Not a range. A "
                                                           "real figure, e.g. 5.4. ⚠ Use the "
                                                           "whole width the region allows, "
                                                           "including the bottom of it. A woman "
                                                           "who packs at a spice unit and a "
                                                           "woman who runs a bank back-office "
                                                           "team do not live in the same "
                                                           "household income — so if these "
                                                           "figures all cluster in one "
                                                           "comfortable band, the manual and "
                                                           "farm work you were asked for has "
                                                           "quietly disappeared along with "
                                                           "them.",
                                        },
                                        # ⚠ THE TIER WORD WAS NOISE, MEASURED.
                                        # In the audited region 12 people lived
                                        # in a "tier-3 city" and 180 in a
                                        # "tier-3 town" — and all eight of
                                        # those "cities" appear as "towns"
                                        # elsewhere in the same file. A label
                                        # that flips at random on the same
                                        # place is worse than no label: it
                                        # reads as a real distinction.
                                        "geography": {
                                            "type": "string",
                                            "description": "City and tier, e.g. 'Indore / "
                                                           "tier-2'. ⚠ Use the tier the region "
                                                           "declares, spelled exactly "
                                                           "'tier-1'/'tier-2'/'tier-3', and do "
                                                           "not add 'city' or 'town' after it — "
                                                           "the same place was labelled both "
                                                           "ways in one file. Real places only, "
                                                           "and sized to the tier. Spread them: "
                                                           "no two people in a batch from the "
                                                           "same town, and never two people who "
                                                           "share both a town and an age.",
                                        },
                                        # ⚠ THE FIELD KEY STAYS `occupation_hint`.
                                        # It is a real field on `DemographicPoint`,
                                        # it is digested by `persona_core_hash`, and
                                        # renaming it would move every persona on
                                        # disk. Only what it MEANS is being fixed:
                                        # described as "The job", it made all 194
                                        # people in the first region earners and zero
                                        # of them homemakers, in a slice that is
                                        # roughly two-thirds homemaker in life.
                                        "occupation_hint": {
                                            "type": "string",
                                            "description": "WHAT FILLS THIS PERSON'S DAY, plainly "
                                                           "and specifically — not necessarily a "
                                                           "paid job. A real contemporary Indian "
                                                           "occupation is right when they hold "
                                                           # ⚠ THREE EXEMPLARS, EACH DEMONSTRATING
                                                           # A SHAPE THIS FIELD GOT WRONG, AND
                                                           # NONE OF THEM REPEATED ANYWHERE ELSE
                                                           # IN THE PROMPT. The old set repeated
                                                           # `demography.brief`'s line verbatim
                                                           # and named a family shop that came
                                                           # back as 8% of the panel. ⚠ The third
                                                           # one used to read "retired from the
                                                           # state transport depot, NOW DOES THE
                                                           # MORNING MARKET RUN" — the prompt was
                                                           # demonstrating the exact defect the
                                                           # audit found, a retiree who is
                                                           # immediately given a second
                                                           # occupation. Eleven of twelve retired
                                                           # people came back re-employed.
                                                           # ⚠ THE PAID-MANUAL EXEMPLAR WAS
                                                           # REMOVED 2026-08-19 ON ITS OWN
                                                           # EVIDENCE. It read "packs and seals at
                                                           # a spice unit on the edge of town" and
                                                           # the probe run came back with TWO of
                                                           # its thirty women at a spice unit —
                                                           # 6.7%, from a single mention, in the
                                                           # same session that removed the last
                                                           # menu for the same reason. The
                                                           # industry spread in the population
                                                           # brief now names manual work as a
                                                           # CLASS with a percentage, and the
                                                           # probe drew a rice mill, a paper-bag
                                                           # piece rate, an orange orchard and a
                                                           # court-sweeping job out of it without
                                                           # any exemplar at all. ⭐ So the two
                                                           # that remain are the two the table
                                                           # cannot express: unpaid family work,
                                                           # and a retirement that actually ends.
                                                           "one; so is 'works unpaid in the "
                                                           "family's trade and would not call it "
                                                           "a job — takes no salary from it', or "
                                                           "'retired from the municipal school "
                                                           "two years ago and has not worked "
                                                           "since'. ⚠ Those are SHAPES, not a "
                                                           "menu — do not lift the trades. Take "
                                                           "the kind of work from the region's "
                                                           "spread and invent the specific job "
                                                           "inside it. Never a generic label. ⚠ It "
                                                           "MUST fit THIS person's age. It need "
                                                           "NOT be what earns the household its "
                                                           "income — that figure is the "
                                                           "HOUSEHOLD's and somebody else may be "
                                                           "earning it. But where they do hold a "
                                                           "paid job it has to be plausible at "
                                                           "that age: nobody is a team lead at "
                                                           "23, and nobody runs a district depot "
                                                           "on a trainee's pay. ⚠ NO ₹ figure, "
                                                           "NO income word, NO product, NO "
                                                           "opinion about the category.",
                                        },
                                        # ⚠ THE FIELD THAT WAS SPECIFIED IN
                                        # TWENTY-THREE CHARACTERS — "ONE
                                        # household detail. Same bans." — while
                                        # `occupation_hint` beside it carried
                                        # seven hundred. Everything the audit of
                                        # 2026-08-18 found in family life
                                        # followed from that asymmetry: a
                                        # median age at first birth of 28-31
                                        # against a real 21.7, one-child
                                        # families at 28% against a real 9%,
                                        # widows at 1% against a real 11.5%,
                                        # and two arithmetically impossible
                                        # grandmothers. The field description
                                        # IS the spec — see the trap note about
                                        # `occupation_hint` being described as
                                        # "The job".
                                        "household_hint": {
                                            "type": "string",
                                            "description": "ONE household detail: who is in "
                                                           "the house with this person, or who "
                                                           "is missing from it. A husband who "
                                                           "works away, a mother-in-law who "
                                                           "needs help, a daughter who has "
                                                           "married out, a son looking for work, "
                                                           "nobody at all between eight and six. "
                                                           "⚠⚠ DO THE ARITHMETIC BEFORE YOU "
                                                           "WRITE IT — this is the single most "
                                                           "common error in this field. Every "
                                                           "relative you name has an age implied "
                                                           "by their life stage, and it must "
                                                           "work against THIS person's age. "
                                                           "Subtract: her age minus the child's "
                                                           "age is how old she was when she had "
                                                           "them, and the population figures say "
                                                           "what that number usually is. A "
                                                           "49-year-old with a grandchild in "
                                                           "school needs to have given birth at "
                                                           "16 AND her daughter at 17 — so "
                                                           "either that grandchild is a toddler "
                                                           "or this woman is older. A "
                                                           "55-year-old whose son is sitting "
                                                           "police recruitment had him at 33, "
                                                           "which is possible but is not the "
                                                           "median and must not be the default. "
                                                           "⚠ Retirement is arithmetic too: "
                                                           "government, bank and school service "
                                                           "runs to the late fifties or sixty, "
                                                           "so nobody is retired at 52 and a "
                                                           "57-year-old is not 'ten years from "
                                                           "retirement'. ⚠ Same bans as "
                                                           "occupation_hint: NO ₹ figure, NO "
                                                           "income word, NO product, NO brand, "
                                                           "NO opinion about the category.",
                                        },
                                        "weight": {"type": "number"},
                                    },
                                    "required": ["gender", "age", "income_lpa",
                                                 "geography", "occupation_hint",
                                                 "household_hint", "weight"],
                                },
                            },
                        },
                        "required": ["label", "display_name", "occasion", "stance",
                                     "l1_context",
                                     "l2_category", "l3_knowledge", "l4_stance",
                                     "l5_behavior", "bundles",
                                     *sorted(_VALID_DISPOSITION)],
                    },
                },
                # ⚠ AN EMPTY CELL MUST BE SAYABLE, OR THE GENERATOR FABRICATES.
                # The grid is MECE by construction, and demanding every cell be
                # filled for a narrow region — women 55-75 in tier-3 — forces
                # positions into existence that nobody there holds. That is the
                # pyramid inverted: instead of three opinions wearing a hundred
                # name tags, it is a hundred name tags with nothing behind them.
                # The gates test FORM, not truth, so nothing downstream would
                # catch it. A refusal is a finding for the brand manager.
                "refusals": {
                    "type": "array",
                    "description": "Cells you are deliberately NOT filling, with the "
                                   "reason. Use this when the position genuinely does "
                                   "not occur in this region, or when it is identical "
                                   "to one already written and a second copy would add "
                                   "no disagreement. ⚠ NEVER use it to save effort — a "
                                   "refusal is a claim about the market that a brand "
                                   "manager will read. Empty array if you filled "
                                   "every cell.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "occasion": {"type": "string",
                                         "enum": [o["key"] for o in grid["occasions"]]},
                            "stance": {"type": "string", "enum": grid["stances"]},
                            "reason": {
                                "type": "string",
                                "description": "Why nobody in this region holds this "
                                               "position, in one concrete sentence about "
                                               "the people — not about the brief.",
                            },
                        },
                        "required": ["occasion", "stance", "reason"],
                    },
                },
            },
            "required": ["buyer_types", "refusals"],
        },
    }


_SYSTEM = """\
You author consumer buyer types for a simulated-audience instrument that reads \
advertising. Each type you write becomes the hard constraint on a persona that \
then reacts to an ad as that person. Your output IS the panel.

THE ONE THING THAT MATTERS: these people must DISAGREE WITH EACH OTHER. A panel \
of a hundred agents recently produced three distinct positions because six \
stances were scaled across a hundred slots. Two buyers who would react the same \
way to the same ad are one buyer, however different their jobs and cities are. \
Difference of OPINION is the product; difference of biography is decoration.

SIX RULES. The third is the one people get wrong; the sixth is the one \
this generator has failed three separate times.

1. AIM AT THE TOP 20% OF A COHORT, NEVER THE TOP 0.1%. An engaged buyer watches \
one review video and reads three Amazon reviews. She does not keep a comparison \
spreadsheet, does not read lab reports, does not post in forums. The moment a \
type reads as an industry insider it stops being a consumer.

2. CONDITION ON EXPERIENCE, NOT ON CONCLUSIONS. "Believes clean labels matter" \
is a position an ad cannot move. "Binned a half-used ₹1,599 tub after the gym \
habit died" is a thing that happened, and it produces reactions. Write what \
happened to them.

3. L3 AND L4 ARE CEILINGS AND THEY ARE NON-NEGOTIABLE. L3 states what this \
person does NOT know; L4 states what they REJECT. Without them the persona \
writer assumes maximum expertise and maximum agreeableness, and every type you \
write will like every ad it is shown. A panel that likes everything measures \
nothing. Two explicit "does NOT" clauses in L3, minimum, and they must be \
things a real person in this cohort genuinely would not know.

4. WRITE THE EXPERIENCE, NOT THE ARITHMETIC. The pack gives you a world that is \
concrete down to the SKU and the rupee, and that world is what this person \
reasons INSIDE — it is not what they say. So: name real things, never invent a \
brand or a price, and take everything you name from the category pack or the \
everyday alternatives list. But the LINE you write is what happened to them.

⚠ A single price is fine as texture — "the ₹10 pack", "a ₹96 bar someone \
brought back from a cafe". PRICE COMPARISON IS BANNED in every authored line: \
no per-gram maths, no multiples, no "X costs 5 times Y", no two prices weighed \
against each other. The agent can do that arithmetic later if the ad puts the \
question to it; a type that opens by comparing unit economics is a spreadsheet, \
not a shopper.

Write this: "Tried swapping the 11pm sweet for a 'healthy' bar for two weeks; \
went back to chocolate because it never actually ended the craving."
Not this: "Compares a ₹17 24g chocolate bar against an ₹80 45g protein bar at \
2.5x the price per gram."

Most of these people, most of the time, buy the everyday alternative. Write that \
honestly: a type whose whole world is protein products is a type that cannot \
tell you why someone picked the chocolate bar instead.

5. STAY IN YOUR CELL. Each type belongs to ONE occasion and ONE stance. Do not \
write a second version of a type that already exists — you will be shown every \
type written so far, and a near-duplicate is a wasted slot.

6. WRITE ABSENCE. ⚠⚠ THE FAILURE THIS GENERATOR HAS NOW MADE THREE TIMES, AND \
IT IS ONE FAILURE IN THREE COSTUMES. Asked for a region of 194 women it gave \
193 of them a paid job, and it re-employed eleven of the twelve people it \
retired. Being told the real participation rate fixed the first of those — the \
next file had 71 of 192 running households instead of 1 of 194 — and the \
defect simply moved: that same corrected file gave 190 of its 192 women a \
living husband, in a population where one in nine that age is a widow. It \
writes widowed sisters, jobless brothers-in-law and bedridden fathers without \
hesitation. So it is not that it cannot imagine absence — it cannot give \
absence to the person the type is ABOUT, and fixing one face of that just \
relocates it to the next.

Some of these people have no job. Some have no income of their own. Some have \
no spouse — never married, or widowed, or he works in another city. Some have \
no children, and some have four. Some have nobody at home during the day and \
some cannot leave the house alone. The population figures below carry the \
proportion for each of those in THIS region; they are not a garnish and they \
are not sad exceptions, they are the ordinary spread of a real population.

⚠ SHOW EACH ABSENCE THROUGH WHAT THE PERSON DOES OR WHO IS THERE, NEVER \
THROUGH A MONEY WORD. The hint fields are checked for income language and the \
words "income", "earns", "salary" and "affluent" will fail the file — see the \
ban at the foot of this brief. So: "has never worked outside the house", not \
"has no income"; "her husband died four years ago and the shop went with him", \
not "lost the household earnings". The absence is a fact about her life, and \
writing it as a fact about her money is both a gate failure and a worse line.

⚠ AND THE REASON IT MATTERS FOR AN AD, not just for realism: a panel in which \
everyone has a job, an income, a husband and one convenient child is a panel of \
the comfortable half. It has no one for whom ₹80 is a real decision, and it \
will find almost any ad acceptable. Absence is where disagreement comes from.

ON WHO THESE PEOPLE ARE: the anchor lines carry NO demographics. No age, no \
city, no job, no income, no gendered pronoun. Those live in the bundles, which \
is a separate layer the engine cross-products against the anchor. A biography \
in the anchor contradicts the demographic the agent was actually assigned.

ON HOW THESE PEOPLE SPEND THEIR DAYS, which is the part of a bundle that does \
the most work. It is what makes a persona a person rather than an age bracket, \
and a marketer reads it first. Four things it has to be:

- NOT ALWAYS A JOB. ⚠ THE SINGLE BIGGEST MEASURED FAILURE OF THIS GENERATOR: \
asked for a region of small-town women aged 45-60, it wrote 194 people and gave \
every one of them a paid job. In that population most women do not have one. \
Full-time homemakers, women who help unpaid at a family business, retired \
people, women who earn a little from home and would not call it a job — these \
are the majority of some regions and they are people, not a diversity garnish. \
The population figures below tell you the real proportion for THIS region. Hit \
it.
- REAL AND CURRENT, AND SPREAD ACROSS THE WHOLE ECONOMY. Where there IS a job, \
the jobs Indians actually hold in 2026 — and the whole economy is mostly not \
salaried. ⚠ THIS PROMPT USED TO LIST FIFTEEN TRADES HERE AND THE LIST IS GONE \
ON PURPOSE. Measured: six of those nouns came back as 49% of the people, and \
ten jobs covered 69% of a 192-person panel whose job strings were all \
different. An illustrative list is read as a menu. The population figures \
below give you the real spread BY KIND OF WORK instead — manual and production, \
services, selling, farm, professional, clerical, with a percentage on each. \
Work from those proportions and invent the specific job inside the class. \
Three monocultures fail here: five variations on "software engineer"; the \
quieter one where everybody has an employer; and the quietest one, where \
everybody runs a small respectable business of their own and nobody works a \
shift, a site or a field.
- SIZED TO THE PERSON. It must be plausible at THIS person's exact age. It need \
not explain the household's income — somebody else in the house may be earning \
it, and for a homemaker somebody else usually is.
- SPECIFIC WITHOUT BEING A CV. This is a CONTRAST, not a menu — do not lift \
the words. "professional" is empty. "housewife" alone is nearly empty. "VP of \
Global Payments Infrastructure" is a LinkedIn headline. "back-office \
operations team lead at a bank" is right, because it says what the day \
contains and where. One clause, the day and its setting.

⚠ INCOME NEVER APPEARS IN A HINT. Not a ₹ figure, not "affluent", not \
"budget-conscious". The occupation and household hints reach the persona writer \
and income is deliberately withheld from it. A hint carrying income defeats a \
redaction that exists for a measured reason. Hints carry the job, the city and \
one household detail — nothing else. No product, no brand, no opinion about the \
category.\
"""


def _pack_brief(pack) -> str:
    # ⭐ `[moment moment]` is the brand's SUBSCRIPTION — which moments it actually
    # competes in. Lowercase snake_case on purpose: `render._vocab_tokens` builds
    # the invented-brand guardrail from TitleCase tokens, so these add none.
    # ⚠ Packs written before the F&B map have empty `moments`, so their brief is
    # byte-identical to the pre-2026-08-21 version. Pinned by test.
    brands = "\n".join(
        f"  - {b.name} ({b.tier}) — {b.note}"
        + (f"  [{' '.join(b.moments)}]" if b.moments else "")
        for b in pack.brand_landscape
    )
    prices = "\n".join(f"  - {p.item}: {p.price_inr} [{p.channel}]" for p in pack.price_points)
    return (
        f"THE BRANDS THAT EXIST IN THIS MARKET (use ONLY these):\n{brands}\n\n"
        f"REAL PRICE POINTS:\n{prices}\n\n"
        f"WHERE PEOPLE BUY:\n" + "\n".join(f"  - {c}" for c in pack.retail_channels) + "\n\n"
        f"WHAT IS IN THE AIR:\n" + "\n".join(f"  - {c}" for c in pack.cultural_references) + "\n\n"
        f"HOW PEOPLE IN THIS MARKET TALK:\n"
        + "\n".join(f'  - "{v}"' for v in pack.voice_samples) + "\n\n"
        f"BACKDROP:\n{pack.behavioral_priors}\n"
    )


def _grid_brief(grid: dict) -> str:
    """Render the demand grid for the prompt.

    ⚠⚠ TWO SHAPES, ONE FUNCTION, AND THE OLD SHAPE MUST NOT MOVE. `SNACKING_GRID`
    has no `question` and no `band`, so every branch below is opt-in and its brief
    is byte-identical to the pre-2026-08-21 version. That matters because
    `tests/test_generation_prompt.py` reads the ASSEMBLED prompt as one artifact —
    every audit defect it was written for lived in the seams between `_SYSTEM`,
    the schema and this function, and each module's own tests passed throughout.

    ⭐⭐ WHY THE QUESTION IS EMITTED AT ALL. Five real days (`#68`) showed every
    `SNACKING_GRID` failure was one shape: incidental scene-setting in `moment`
    acting as an exclusion criterion — "at a desk", "wants something sweet",
    "leaving late". The discriminating QUESTION is what routed 29 of 34 items
    where the grid routed 3. If it stayed in a doc the generator would never see
    it. So when a grid carries questions, the prompt says plainly that the
    question is the definition and the prose is only colour.
    """
    out = [f"THE DEMAND SPACE — {grid['market']}.",
           "An occasion is a MOMENT, not a person. Each one names what the buyer would",
           "otherwise have bought. That alternative is the thing your type is deciding",
           "against, and it is usually NOT another product in this category.\n"]
    if any(o.get("question") for o in grid["occasions"]):
        out.append("⚠ EACH MOMENT IS DEFINED BY ITS QUESTION — the line after the key is only")
        out.append("an example of what it often looks like. Never treat that example as a")
        out.append("filter. A moment belongs to anyone the QUESTION is true of, wherever they")
        out.append("are and whatever their income: the afternoon trough is a building site and")
        out.append("a tea stall as much as an office, and a late-night plate is as often")
        out.append("savoury as sweet.\n")
    if any(o.get("band") for o in grid["occasions"]):
        out.append("Moments carry a BAND. (clock) is triggered by the time of day, (event) by")
        out.append("the calendar or by life, (habit) runs in the background regardless of")
        out.append("either. One person holds moments from all three bands at once.\n")
    for o in grid["occasions"]:
        band = f"  ({o['band']})" if o.get("band") else ""
        out.append(f"[{o['key']}]{band}  {o['moment']}")
        if o.get("question"):
            out.append(f"    DEFINED BY             : {o['question']}")
        out.append(f"    instead they might buy : {o['competes_with']}")
        out.append(f"    what decides it        : {o['decided_by']}")
        out.append(f"    where                  : {o['channel']}\n")
    # ⚠ SNACKING_GRID's heading is "WHAT THEY ACTUALLY BUY MOST OF THE TIME", and
    # the five real days showed four of five people ate substantial food they did
    # not buy — a boss, a mother, a wife, a host; one man chose 2 of his 14 items.
    # A grid that asks only about BUYING cannot see most of the food. Overridable
    # per grid rather than rewritten here, so the old grid's prompt does not move.
    if grid.get("alternatives_heading"):
        out.append(grid["alternatives_heading"])
    else:
        out.append("WHAT THEY ACTUALLY BUY MOST OF THE TIME — nameable, real, and usually")
        out.append("the thing that wins the occasion:")
    out += [f"  - {a}" for a in grid["everyday_alternatives"]]
    return "\n".join(out)


def _cells(grid: dict, n: int, occasion: str | None = None) -> list[tuple[str, str]]:
    """Walk occasions x stances so consecutive batches spread across the grid
    rather than exhausting one occasion first — a batch of five siblings from
    one occasion is exactly how near-duplicates get written.

    ⭐ `occasion` PINS ONE MOMENT AND WALKS THE STANCES INSIDE IT, which the
    occasion-major walk above cannot express at any count. Added 2026-08-19 for
    the F&B part-A test, which needs ONE moment across ALL EIGHT stances.

    ⚠⚠ THE DEFECT THIS EXISTS TO FIX HAS BITTEN TWICE. Because the default walk
    is occasion-MAJOR, `--count 8` against an 8x8 grid returns eight different
    occasions all at `loyalist` — the first stance, eight times. That is
    precisely how the 2026-08-19 probe came back as 8 loyalists + 2 switchers
    and was then installed as an "audience" that could not disagree with
    itself. A partial count is not a sample of the grid; it is the first
    column of it.

    ⚠ With `occasion` set there are only `len(stances)` cells in the space, so
    a larger `n` would cycle and emit duplicate coordinates. The caller is
    responsible for capping n — `main` does, and refuses rather than truncating
    silently.
    """
    if occasion is not None:
        return [(occasion, s) for s in grid["stances"]][:n]
    occ = [o["key"] for o in grid["occasions"]]
    out = []
    i = 0
    while len(out) < n:
        out.append((occ[i % len(occ)], grid["stances"][(i // len(occ)) % len(grid["stances"])]))
        i += 1
    return out[:n]


def _already(types: list[dict]) -> str:
    if not types:
        return "(none yet — this is the first batch)"
    return "\n".join(
        f"  - {t['label']}  [{t['occasion']} / {t['stance']}] — {t['l1_context']}"
        for t in types
    )


def _region_brief(region: Region) -> str:
    """The slice these opinions are being written FOR.

    ⚠ In the CACHED system block, not the user turn: it is constant across every
    batch of one generation, so it caches with the pack and the grid and a batch
    retry pays output only."""
    gender_rule = (
        "EVERY person you write is a woman, and every opinion is a woman's."
        if region.gender == "female" else
        "EVERY person you write is a man, and every opinion is a man's."
        if region.gender == "male" else
        "Write both men and women. Where a position genuinely differs by "
        "gender, write it once per gender; where it genuinely does not, write "
        "it ONCE and do not mint a mirror copy with a different pronoun."
    )
    return (
        "THE REGION YOU ARE WRITING FOR — every person must live inside it:\n"
        f"  {region.brief()}\n\n"
        "⚠ THIS IS NOT A FILTER APPLIED AFTERWARDS. It is the brief. The "
        "opinion is what changes with the demographic, not just the name tag: "
        "a 26-year-old in Mumbai doubts whether '20g protein' is real protein "
        "or marketing; a 52-year-old in a tier-3 town doubts whether packaged "
        "food is food and whether ₹80 is anybody's money. Those are two "
        "different opinions. A type whose opinion would read identically at "
        "any age is a type you have not written yet.\n\n"
        f"ON GENDER. {gender_rule} Gender is a real difference in this "
        "category and it is not a pronoun: a man's relationship to a protein "
        "bar runs through the gym, visible strength, and being seen buying it; "
        "a woman's more often runs through feeding everyone else first and "
        "getting to her own nutrition last. ⚠ But do NOT manufacture a "
        "difference that is not there — an invented gender split is as false "
        "as a missing one.\n\n"
        "⚠ IF A CELL DOES NOT EXIST HERE, REFUSE IT. Some positions genuinely "
        "have nobody behind them in a given slice, and inventing one to fill "
        "the grid puts a person in the room who does not exist. Say so in "
        "`refusals`, with the reason, and move on. A refusal is information.\n\n"
        # ⚠ The measured fix for the zero-homemaker defect — see
        # `agent/demography.py`. It goes in the CACHED block with the rest of
        # the region because it is constant across every batch of one
        # generation, so a batch retry pays output only.
        + demography.brief(region.gender, region.age_min, region.age_max,
                           region.tier)
    )


def _report_mix(done: list[dict], region: Region) -> None:
    """Print the achieved unpaid/paid split next to the population's.

    ⚠ REPORTED, NEVER ENFORCED, and that is the whole design. Gating on this
    would teach the generator to write the keywords `demography.looks_unpaid`
    scans for, which is how you get 194 people who all say "runs the house" and
    are otherwise identical. It is a smoke alarm for the failure that actually
    happened — 0 of 194 — not a quota. The classifier is a keyword heuristic
    and will miscount at the edges; a rough number is enough to see a zero.
    """
    people = [b for t in done for b in t.get("bundles", [])]
    if not people:
        return
    unpaid, total = demography.achieved_mix(people)
    print(f"\nhow they spend their days: {unpaid} of {total} people "
          f"({unpaid / total:.0%}) have an unpaid or household-centred day")
    if region.gender == "female":
        expect = 100 - demography.female_lfpr(region.age_min, region.age_max,
                                              region.tier)
        print(f"  the population says roughly {expect:.0f}% for this region "
              f"(PLFS 2023-24 — see agent/demography.py)")
        if unpaid == 0:
            print("  ⚠ ZERO. This is the defect demography.py exists to fix; "
                  "the brief did not land.")


def _build(grid: dict, pack, cells, done: list[dict],
           region: Region) -> tuple[list[dict], str]:
    ask = "\n".join(f"  {i+1}. occasion={o}  stance={s}" for i, (o, s) in enumerate(cells))
    system = [
        {"type": "text", "text": _SYSTEM},
        # Stable prefix: pack + grid + region never change across batches of one
        # generation, so they cache.
        {"type": "text",
         "text": _pack_brief(pack) + "\n\n" + _grid_brief(grid)
                 + "\n\n" + _region_brief(region),
         "cache_control": {"type": "ephemeral"}},
    ]
    user = (
        f"ALREADY WRITTEN — do not write any of these people again:\n{_already(done)}\n\n"
        f"Write up to {len(cells)} NEW buyer types, one for each cell:\n{ask}\n\n"
        "Each must be someone the others in the list above would disagree with about "
        "an ad. Any cell you do not fill goes in `refusals` with its reason. "
        "Use the emit_buyer_types tool."
    )
    return system, user


def _to_disposition(t: dict, region: Region) -> NamedDisposition:
    anchor = "\n\n".join(
        t[k] for k in ("l1_context", "l2_category", "l3_knowledge", "l4_stance", "l5_behavior")
    )
    return NamedDisposition(
        label=t["label"],
        display_name=t.get("display_name", ""),
        vector=DispositionVector(**{d: t[d] for d in _VALID_DISPOSITION}),
        anchor=anchor,
        # ⭐ The moment as DATA, not only inside the notes string. `notes` is a
        # free-text curator field and stays one; `moment` is what a read joins
        # against `BrandArtifact.moments` to cut the world. Same value, two
        # homes — deriving behaviour by parsing the display string is the
        # defect class `#80` closed.
        moment=t["occasion"],
        notes=notes_for(t["occasion"], t["stance"], region.key),
        demographic_bundles=[
            DemographicBundle(
                # ⚠ A POINT, NOT A BAND: min == max on both axes.
                # `panel._range_overlap_frac` already special-cases a zero-width
                # range as in-or-out, so a person aged 52 is selected by ANY
                # customer-chosen range containing 52 — 45-60, 47-63, 50-55 —
                # with no band, no snapping and no clipping. And
                # `panel._clip_point` becomes the identity, so this person's
                # city, career and household survive into the render instead of
                # being clipped off.
                point=DemographicPoint(
                    gender=b["gender"],
                    age_min=int(b["age"]), age_max=int(b["age"]),
                    income_lpa_min=float(b["income_lpa"]),
                    income_lpa_max=float(b["income_lpa"]),
                    geography=b["geography"], occupation_hint=b["occupation_hint"],
                    household_hint=b["household_hint"],
                ),
                weight=float(b["weight"]),
            )
            for b in t["bundles"]
        ],
    )


def _settle(payload: dict, done: list[dict],
            dispositions: list[NamedDisposition]) -> None:
    """Write `raw` / `dropped` / `dispositions` so the file agrees with itself.

    ⚠ `_convert` drops people who fall outside the region, and a type that loses
    every person is dropped whole — so `raw` and `dispositions` diverge unless
    they are settled together. Caught by the offline rehearsal: the saved file
    carried 15 raw types (one with an empty `bundles`) against 14 dispositions,
    and the gates read `raw`, so a file whose dispositions were clean reported
    NOT ADMISSIBLE.

    ⚠ NOTHING PAID IS THROWN AWAY. What was dropped moves to `dropped` rather
    than being deleted — it was generated with real money, and it is the
    evidence for why a cell came back empty.
    """
    kept = {d.label for d in dispositions}
    payload["raw"] = [t for t in done if t["label"] in kept]
    dropped = [t for t in done if t["label"] not in kept]
    if dropped:
        payload["dropped"] = dropped
    payload["dispositions"] = [d.to_dict() for d in dispositions]


def _convert(raw: list[dict], region: Region) -> list[NamedDisposition]:
    """Raw tool output -> validated dispositions. Free and re-runnable, which is
    why it happens strictly after the raw output is on disk."""
    missing = [
        (t.get("label", "?"), sorted(set(_VALID_DISPOSITION) - set(t)))
        for t in raw if set(_VALID_DISPOSITION) - set(t)
    ]
    if missing:
        print("\n⚠ types missing vector axes (the tool schema did not hold):")
        for label, gaps in missing[:10]:
            print(f"    {label}: missing {gaps}")
        raise SystemExit(
            f"{len(missing)} of {len(raw)} types are unusable. The raw output is "
            "saved; fix the converter or the schema and re-run with --from-raw."
        )
    # ⚠ A FILE FROM BEFORE PEOPLE-SHAPED BUNDLES MUST STOP HERE, CLEANLY. Every
    # check below reads `age`/`income_lpa`, and a band carries `age_min`/`age_max`
    # instead — so an old file died on a bare `KeyError: 'age'`. On `--from-raw`
    # that is a confusing traceback on a documented $0 command; on `--fill` it is
    # a traceback AFTER the paid batches have run, which is the exact
    # "generated fine, crashed while transforming" shape that cost ~$1 on
    # 2026-08-14. (Nothing is lost — the raw is already on disk — but the
    # operator has to work out why.)
    bands = [t.get("label", "?") for t in raw
             for b in t.get("bundles", []) if "age" not in b]
    if bands:
        raise SystemExit(
            f"{len(bands)} bundle(s) are BANDS, not people (no `age` field) — "
            f"e.g. {bands[0]}.\nThis file predates people-shaped bundles. Convert "
            f"it first, which is free and offline:\n"
            f"  .venv/bin/python scripts/convert_library_to_people.py <this file>"
        )
    # ⚠ A PERSON OUTSIDE THE REGION CAN NEVER BE SELECTED BY THE BUY THAT ASKED
    # FOR THEM — they are dead weight that still costs a render and still dilutes
    # the panel. The schema cannot express "inside this region", so this is the
    # one place it is checkable. Loud, and it does not throw away the raw file.
    strays = [
        (t.get("label", "?"), b)
        for t in raw for b in t.get("bundles", [])
        if not region.contains(b["gender"], int(b["age"]), float(b["income_lpa"]))
    ]
    if strays:
        print(f"\n⚠ {len(strays)} person(s) fall OUTSIDE the declared region "
              f"({region.brief()}) and were dropped:")
        for label, b in strays[:10]:
            print(f"    {label}: {b['gender']} aged {b['age']}, "
                  f"₹{b['income_lpa']}L, {b['geography']}")
        for t in raw:
            t["bundles"] = [
                b for b in t.get("bundles", [])
                if region.contains(b["gender"], int(b["age"]), float(b["income_lpa"]))
            ]
    out = [_to_disposition(t, region) for t in raw if t.get("bundles")]
    dropped = len(raw) - len(out)
    if dropped:
        print(f"⚠ {dropped} type(s) lost every person and were dropped entirely.")
    for d in out:
        d.validate()
    return out


def _generate(client, tool, grid, pack, cells: list[tuple[str, str]],
              done: list[dict], region: Region,
              refusals: list[dict] | None = None,
              checkpoint=None) -> list[dict]:
    """Write one type per cell, in batches, re-asking any batch that comes
    back short. Returns the new types; also appends them to `done`, which is
    the already-written set the writer is shown so it does not repeat itself,
    and appends any declined cells to `refusals`.

    ⚠⚠ `checkpoint` IS CALLED AFTER EVERY BATCH AND IT IS NOT OPTIONAL POLISH.
    Measured 2026-08-15: a 13-batch region run got through two batches — ten
    buyer types, ~7,500 output tokens — and died on batch three with
    `anthropic.APIConnectionError`. Everything was still in memory. **All of it
    was lost.** That is the same shape as the ~$1 loss on 2026-08-14, and the
    "SAVE ANYTHING PAID THE INSTANT IT EXISTS" rule was written for it — but the
    rule had only ever been applied to the CONVERSION step, never to this loop,
    so a 13-batch run was thirteen chances to lose everything.

    ⚠ A checkpointed crash is RESUMABLE and costs nothing extra: `--fill` on the
    partial file works out which cells are still unaddressed and asks only for
    those. Recovery is already built; it just needed something on disk.

    ⚠ Checkpointing must never itself raise — a failed write here would replace
    a live API error with a disk error and still lose the batch.

    ⚠ A REFUSED CELL IS NOT A SHORT BATCH. The retry below exists because a
    batch can silently return fewer types than asked; a refusal is a deliberate
    claim that nobody in this region holds that position. Re-asking it would
    badger the model into inventing the person it just said does not exist —
    turning the one honesty valve in the generator into a fabrication loop.

    ⚠ A SHORT BATCH IS WELL-FORMED AND WILL PASS SILENTLY. Measured
    2026-08-15: batches 1 and 6 of an 8-batch run returned ONE type each
    instead of five (out=367 and out=713 tokens against ~3,600 for a good
    batch), and the run finished "successfully" with 32 of 40 types. The tool
    schema constrains the SHAPE of each type but says nothing about how MANY,
    so nothing downstream noticed. `--repair` does not catch it either: it
    looks for a missing vector axis or a duplicate coordinate, and a batch
    that is merely SHORT has neither.

    So the count is checked here, per batch, against the cells actually asked
    for — and the missing cells are re-asked rather than lost. Cheap: the
    system block is cached, so a retry pays for output only.

    ⚠ ONE COPY OF THIS LOOP. `--fill` runs the same path as a fresh
    generation, differing only in which cells it is handed and what `done`
    starts as — a second copy would be a second place for the short-batch bug
    to come back.
    """
    batches = [cells[i:i + _PER_BATCH] for i in range(0, len(cells), _PER_BATCH)]
    produced: list[dict] = []
    refusals = refusals if refusals is not None else []
    for i, batch in enumerate(batches, 1):
        got: list[dict] = []
        declined: list[dict] = []
        pending = list(batch)
        for attempt in range(1, 4):
            system, user = _build(grid, pack, pending, done + got, region)
            resp = client.messages.create(
                model=MODEL, max_tokens=8000,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "emit_buyer_types"},
                output_config={"effort": "high"},
            )
            block = next(b for b in resp.content
                         if getattr(b, "type", None) == "tool_use")
            fresh = block.input["buyer_types"]
            fresh_refusals = block.input.get("refusals") or []
            got.extend(fresh)
            declined.extend(fresh_refusals)
            u = resp.usage
            label = f"  batch {i}/{len(batches)}"
            if attempt > 1:
                label += f" (retry {attempt - 1})"
            print(f"{label}: +{len(fresh)} types "
                  + (f"+{len(fresh_refusals)} refused " if fresh_refusals else "")
                  + f"(in {u.input_tokens}, cached {u.cache_read_input_tokens}, "
                  f"out {u.output_tokens})")
            for r in fresh_refusals:
                print(f"      · no {r['stance']} at {r['occasion']}: {r['reason']}")
            # A cell is settled when it holds a type OR a refusal. Only genuinely
            # unanswered cells are re-asked.
            settled = {(t.get("occasion"), t.get("stance")) for t in got}
            settled |= {(r.get("occasion"), r.get("stance")) for r in declined}
            pending = [c for c in batch if c not in settled]
            if not pending:
                break
            print(f"    ⚠ short batch — {len(pending)} cell(s) unanswered, re-asking: "
                  + ", ".join(f"{o}/{s}" for o, s in pending))
        else:
            print(f"    ⚠ STILL UNANSWERED after 3 attempts — leaving "
                  f"{len(pending)} cell(s) empty: "
                  + ", ".join(f"{o}/{s}" for o, s in pending))
        done.extend(got)
        produced.extend(got)
        refusals.extend(declined)
        if checkpoint is not None:
            try:
                checkpoint()
            except Exception as exc:      # noqa: BLE001 — see the docstring
                print(f"    ⚠ CHECKPOINT FAILED ({exc}) — this batch is only in "
                      f"memory and a crash now would lose it.")
    return produced


def _full_grid(grid: dict, occasion: str | None = None) -> list[tuple[str, str]]:
    """Every cell in the grid. `_cells(grid, n)` walks the same space but stops
    at n, and because it walks OCCASION-MAJOR a partial count is not a random
    sample — `--count 40` against an 8x8 grid asks for the first five stances
    across all eight occasions and never mentions the last three at all. That
    is why the v2 file has no purist, pragmatist or gifter: they were not
    generated badly, they were never requested.

    ⚠⚠ `occasion` IS NOT COSMETIC HERE — IT IS THE GUARD ON A ~$1.40 MISTAKE.
    A file generated with `--occasion` holds one moment's 8 cells. Without this
    parameter a later `--fill` on that file would compute a 64-cell target,
    find 56 "missing", and buy the other seven moments — turning a $0.15
    single-moment artifact into a full region nobody asked for, silently, and
    breaking the part-A comparison it existed to serve. The restriction is
    persisted in the payload precisely so the fill path can read it back;
    `saved_region` already sets the precedent that the FILE, not the flags,
    is the authority on what a saved run is.
    """
    if occasion is not None:
        return [(occasion, s) for s in grid["stances"]]
    return [(o["key"], s) for s in grid["stances"] for o in grid["occasions"]]


def _triage(raw: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Split saved types into the ones worth keeping and the ones to re-ask.

    Three ways a type is unusable, and the third is the one that has actually
    bitten: a MISSING AXIS is malformed; a DUPLICATE eight-axis coordinate is
    a second copy of an opinion already in the set; and a MISSING CEILING is
    well-formed, uniquely positioned, and will like every ad it is shown.
    `--repair` tests the first two only, which is how `loyalist_office_jar_kitkat`
    (`l1_context == "x"`, no refusals anywhere) came back "nothing to repair".
    """
    seen: dict[tuple, str] = {}
    keep: list[dict] = []
    drop: list[tuple[dict, str]] = []
    for t in raw:
        if set(_VALID_DISPOSITION) - set(t):
            missing = sorted(set(_VALID_DISPOSITION) - set(t))
            drop.append((t, f"missing vector axis: {', '.join(missing)}"))
            continue
        coord = distinctness_key(t)
        if coord in seen:
            drop.append((t, f"duplicate opinion — same coordinate as {seen[coord]}"))
            continue
        failures = ceiling_failures(t)
        if failures:
            drop.append((t, "; ".join(failures)))
            continue
        seen[coord] = t["label"]
        keep.append(t)
    return keep, drop


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repair", metavar="PATH",
                    help="PAID: regenerate only the malformed types in a saved file")
    ap.add_argument("--fill", metavar="PATH",
                    help="PAID: complete a saved file — write the grid cells that "
                         "are empty or whose type is unusable, keep the rest")
    ap.add_argument("--from-raw", metavar="PATH",
                    help="re-convert a saved raw file without paying again")
    ap.add_argument("--market", default="snacking", choices=sorted(GRIDS))
    ap.add_argument("--occasion", default=None, metavar="KEY",
                    help="pin ONE moment and walk every stance inside it, "
                         "instead of the default occasion-major walk across "
                         "the whole grid. Without this, --count 8 returns "
                         "eight occasions all at the FIRST stance.")
    ap.add_argument("--category", default="health_wellness_nutrition")
    # ⚠ Both default to None so `--fill` can mean something different by
    # DEFAULT than a fresh run without changing what a fresh run does: a fresh
    # run still writes 40 types to generated_audience.json, while a fill
    # completes the WHOLE grid and writes back to the file it was given. A
    # `--out` that defaulted to a filename would silently clobber a paid file.
    ap.add_argument("--count", type=int, default=None,
                    help="fresh run: how many types (default 40). "
                         "--fill: cap the grid (default: complete it)")
    ap.add_argument("--out", default=None,
                    help="fresh run: output path (default generated_audience.json). "
                         "--fill: defaults to writing back to the input file")
    # ⚠ THE REGION. A generation with no region is what produced a library whose
    # oldest person was 54 and which held zero tier-3 people — see the Region
    # docstring. The wide default reproduces "the whole urban market", which is
    # a legitimate ask for a base population; a narrow one tops up a thin slice.
    ap.add_argument("--gender", default="any", choices=("any", "female", "male"),
                    help="the region's gender — a GENERATION axis, not a filter")
    ap.add_argument("--age", default="18-75", metavar="MIN-MAX",
                    help="the region's age range, e.g. 45-60")
    ap.add_argument("--income", default="0-100", metavar="MIN-MAX",
                    help="the region's household income in LPA, e.g. 3.5-17")
    ap.add_argument("--tier", default="any",
                    choices=("any", "tier-1", "tier-2", "tier-3"),
                    help="the region's city tier")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    age_lo, age_hi = _parse_range(args.age, "age")
    inc_lo, inc_hi = _parse_range(args.income, "income")
    cli_region = Region(gender=args.gender, age_min=int(age_lo), age_max=int(age_hi),
                        income_min=inc_lo, income_max=inc_hi, tier=args.tier)

    def saved_region(payload: dict) -> Region:
        """⚠ The region comes from the FILE, never from the CLI flags. Re-filling
        or re-converting a saved generation under a different region would mix
        two populations in one file and silently invalidate its own containment
        check. Files written before regions existed are treated as unscoped."""
        return Region(**payload["region"]) if payload.get("region") else Region()

    if args.from_raw:
        p = Path(args.from_raw)
        payload = json.loads(p.read_text())
        disp = _convert(payload["raw"], saved_region(payload))
        _settle(payload, payload["raw"], disp)
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"{len(disp)} buyer types converted -> {p}   ($0, no API call)")
        return

    if args.fill:
        # PAID, and it supersedes --repair for everything except a file whose
        # grid you do not want completed: --repair re-asks only what is BROKEN,
        # --fill re-asks what is broken AND what was never written. The v2 file
        # needed both — one type with no ceilings, and 32 cells (purist,
        # pragmatist, gifter) that `--count 40` never requested.
        p = Path(args.fill)
        payload = json.loads(p.read_text())
        grid = payload["grid"]
        # ⚠ The pack comes from the FILE, never from --category. A file whose
        # first half was written against one world and second half against
        # another is inconsistent in a way no gate would catch.
        pack = load_pack(payload["category"])
        raw = payload["raw"]
        region = saved_region(payload)
        prior_refusals = list(payload.get("refusals") or [])

        # ⚠ BEFORE SPENDING, not in `_convert` after it. `_convert` runs at the
        # END of a fill, so a band-shaped input would pay for every batch and
        # only then refuse to transform.
        if any("age" not in b for t in raw for b in t.get("bundles", [])):
            raise SystemExit(
                "this file's bundles are BANDS, not people, so a fill would mix "
                "two shapes in one library.\nConvert it first — free and "
                "offline:\n  .venv/bin/python scripts/convert_library_to_people.py "
                + str(p))

        keep, drop = _triage(raw)
        # ⚠⚠ THE RESTRICTION COMES FROM THE FILE, NEVER FROM THE FLAGS — the
        # same rule `saved_region` follows one line up. A file generated with
        # --occasion holds ONE moment; without this its fill would target all
        # 64 cells, find 56 missing and buy seven moments nobody asked for.
        saved_occasion = payload.get("occasion")
        target = (_cells(grid, args.count, saved_occasion) if args.count
                  else _full_grid(grid, saved_occasion))
        have = {(t["occasion"], t["stance"]) for t in keep}
        # ⚠ A CELL ALREADY REFUSED IS SETTLED, NOT MISSING. Re-asking it on every
        # fill would grind the model down until it invented the person it had
        # already said does not exist in this region.
        have |= {(r["occasion"], r["stance"]) for r in prior_refusals}
        todo = [c for c in target if c not in have]
        n_cells = (len(grid["stances"]) if saved_occasion
                   else len(grid["occasions"]) * len(grid["stances"]))

        print(f"market      : {grid['market']}")
        print(f"grid        : {len(grid['occasions'])} occasions x "
              f"{len(grid['stances'])} stances = {n_cells} cells")
        if saved_occasion:
            print(f"occasion    : {saved_occasion} — PINNED BY THE FILE, so a "
                  f"fill targets {n_cells} cells, not the whole grid")
        print(f"region      : {region.brief()}")
        print(f"pack        : {payload['category']} ({len(pack.brand_landscape)} brands)")
        print(f"on file     : {len(raw)} types — {len(keep)} usable, "
              f"{len(drop)} to re-ask"
              + (f", {len(prior_refusals)} cell(s) already refused"
                 if prior_refusals else ""))
        for t, why in drop:
            print(f"    ✗ {t.get('label', '?')}  "
                  f"[{t.get('occasion', '?')}/{t.get('stance', '?')}] — {why}")
        print(f"target      : {len(target)} cell(s)")
        print(f"to generate : {len(todo)} cell(s) in "
              f"{-(-len(todo) // _PER_BATCH)} batches of {_PER_BATCH}")
        for o, s in todo:
            print(f"    + {o}/{s}")

        if not todo:
            print("\nnothing to fill — every targeted cell holds a usable type.")
            return
        if args.dry_run:
            print("\n$0 — no API call was made.")
            return

        import anthropic
        # ⚠ 8, not 5. Two 13-batch region runs died on `APIConnectionError`
        # after ~4 batches on 2026-08-16 — the connection drops mid-run often
        # enough that 5 SDK retries did not cover it. Batches are checkpointed
        # either way, so a crash now costs a resume rather than the run.
        client = anthropic.Anthropic(max_retries=8)
        done = list(keep)
        refusals = list(prior_refusals)

        out = Path(args.out) if args.out else p
        if out == p:
            bak = p.with_suffix(p.suffix + ".bak")
            bak.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
            print(f"\nprevious file backed up -> {bak}")

        def _checkpoint() -> None:
            payload["raw"], payload["refusals"] = done, refusals
            out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

        _checkpoint()
        try:
            _generate(client, _tool(grid), grid, pack, todo, done, region,
                      refusals, checkpoint=_checkpoint)
        except BaseException:
            _checkpoint()
            print(f"\n⚠ FILL FAILED. {len(done)} type(s) ARE SAVED at {out} — "
                  f"re-run the same --fill to resume.")
            raise

        # ⚠ SAVE BEFORE TRANSFORMING — a crash in `_convert` must not cost the
        # batches. (The .bak and the per-batch checkpoints are above.)
        _checkpoint()
        print(f"raw output saved -> {out}  ({len(done)} types, "
              f"{len(refusals)} refused)")

        dispositions = _convert(done, region)
        _settle(payload, done, dispositions)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"\n{len(dispositions)} buyer types -> {out}")
        _report_mix(done, region)
        print("NOTHING has been installed as a library yet. Run the checks first:")
        print("  .venv/bin/python scripts/check_generated_audience.py " + str(out))
        return

    if args.repair:
        # PAID, but only for the cells that came back malformed — one batch of
        # five costs cents, where regenerating all forty costs a dollar and
        # throws away thirty-five good types to fix five bad ones.
        p = Path(args.repair)
        payload = json.loads(p.read_text())
        raw = payload["raw"]
        grid, pack = payload["grid"], load_pack(payload["category"])
        # Two kinds of broken. A missing axis is malformed. A DUPLICATE
        # eight-axis coordinate is worse: it is well-formed and it is the exact
        # defect this whole script exists to prevent — a second copy of an
        # opinion already in the set. Both get regenerated; for a duplicate we
        # keep the first and re-roll the later one, so the survivor is the one
        # written with less of the grid already spoken for.
        import collections as _c
        seen: dict[tuple, str] = {}
        broken, keep = [], []
        for t in raw:
            if set(_VALID_DISPOSITION) - set(t):
                broken.append(t)
                continue
            coord = tuple(t[a] for a in sorted(_VALID_DISPOSITION))
            if coord in seen:
                print(f"  duplicate opinion: {t['label']} == {seen[coord]}  (re-rolling the later)")
                broken.append(t)
            else:
                seen[coord] = t["label"]
                keep.append(t)
        if not broken:
            print("nothing to repair — every type has its full vector.")
            return
        print(f"repairing {len(broken)} malformed type(s); {len(keep)} kept untouched")
        import anthropic
        # ⚠ 8, not 5. Two 13-batch region runs died on `APIConnectionError`
        # after ~4 batches on 2026-08-16 — the connection drops mid-run often
        # enough that 5 SDK retries did not cover it. Batches are checkpointed
        # either way, so a crash now costs a resume rather than the run.
        client = anthropic.Anthropic(max_retries=8)
        cells = [(t["occasion"], t["stance"]) for t in broken]
        system, user = _build(grid, pack, cells, keep, saved_region(payload))
        resp = client.messages.create(
            model=MODEL, max_tokens=8000, system=system,
            messages=[{"role": "user", "content": user}],
            tools=[_tool(grid)],
            tool_choice={"type": "tool", "name": "emit_buyer_types"},
            output_config={"effort": "high"},
        )
        block = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
        fixed = block.input["buyer_types"]
        u = resp.usage
        print(f"  regenerated {len(fixed)} (in {u.input_tokens}, "
              f"cached {u.cache_read_input_tokens}, out {u.output_tokens})")
        payload["raw"] = keep + fixed
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        disp = _convert(payload["raw"], saved_region(payload))
        _settle(payload, payload["raw"], disp)
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"{len(disp)} buyer types -> {p}")
        return

    grid = GRIDS[args.market]
    pack = load_pack(args.category)

    # ⚠ VALIDATE THE OCCASION AGAINST THE GRID BEFORE ANYTHING ELSE. A typo
    # would otherwise produce a file of 8 types whose `occasion` matches no
    # cell in the grid — well-formed, gate-passing, and unfillable and
    # unmergeable forever after.
    if args.occasion is not None:
        keys = [o["key"] for o in grid["occasions"]]
        if args.occasion not in keys:
            raise SystemExit(
                f"no occasion {args.occasion!r} in the {args.market!r} grid.\n"
                f"  choose one of: {', '.join(keys)}")

    # ⚠ THE DEFAULT COUNT DEPENDS ON THE SPACE BEING WALKED. Pinning one
    # occasion leaves only len(stances) distinct cells, so the usual default of
    # 40 would cycle the stance list five times and ask for 40 types at 8
    # coordinates — every one after the eighth a duplicate that `_triage` would
    # then drop as a DUPLICATE coordinate, after it had been paid for.
    n_available = len(grid["stances"]) if args.occasion else None
    count = args.count if args.count else (n_available or 40)
    if args.occasion and count > n_available:
        raise SystemExit(
            f"--occasion {args.occasion} has only {n_available} cells (one per "
            f"stance) but --count is {count}.\n"
            f"  Asking for more would emit duplicate coordinates and pay for "
            f"them. Drop --count, or set it to {n_available} or fewer.")
    cells = _cells(grid, count, args.occasion)
    batches = [cells[i:i + _PER_BATCH] for i in range(0, len(cells), _PER_BATCH)]

    print(f"market      : {grid['market']}")
    print(f"grid        : {len(grid['occasions'])} occasions x {len(grid['stances'])} stances")
    if args.occasion:
        print(f"occasion    : {args.occasion} — PINNED, walking all "
              f"{len(grid['stances'])} stances inside it")
    print(f"region      : {cli_region.brief()}")
    print(f"generating  : {count} buyer types in {len(batches)} batches of {_PER_BATCH}")
    print(f"model       : {MODEL}")
    print(f"pack        : {args.category} ({len(pack.brand_landscape)} brands)")

    if args.dry_run:
        system, user = _build(grid, pack, batches[0], [], cli_region)
        print("\n" + "=" * 70)
        print(system[0]["text"])
        print("-" * 70)
        # ⚠ WHOLE, NOT TRUNCATED. This used to print the first 2000
        # characters — a habit from when the prompt was short and the block was
        # mostly the pack. The population brief that fixes the audit's eight
        # defects sits at the END of this block, so a truncated dry-run showed
        # everything except the part being reviewed. Reviewing the prompt
        # before spending is the entire purpose of this flag.
        print(system[1]["text"])
        print("-" * 70)
        print(user)
        print("=" * 70)
        print("\n$0 — no API call was made.")
        return

    import anthropic
    # ⚠ 8, not 5. Two 13-batch region runs died on `APIConnectionError` after
    # ~4 batches on 2026-08-16 — i.e. the connection drops mid-run often enough
    # that 5 SDK retries did not cover it. Batches are checkpointed either way,
    # so a crash now costs a resume rather than the run.
    client = anthropic.Anthropic(max_retries=8)
    done: list[dict] = []
    refusals: list[dict] = []

    # ⚠ THE FILE EXISTS BEFORE THE FIRST BATCH IS PAID FOR. A 13-batch run died
    # on batch 3 on 2026-08-15 and lost ten finished types because nothing was
    # on disk until the last batch landed. Now every batch is checkpointed, and
    # a crash leaves a partial file that `--fill` resumes for the cost of the
    # REMAINING cells only.
    out = Path(args.out) if args.out else Path("generated_audience.json")
    # ⚠ `occasion` IS PERSISTED SO --fill CANNOT LATER BUY THE REST OF THE GRID.
    # See `_full_grid`. It is written even when None, so a reader can tell "no
    # restriction" from "written by a version that did not record one".
    payload = {"market": args.market, "category": args.category,
               "grid": grid, "occasion": args.occasion,
               "region": asdict(cli_region),
               "raw": done, "refusals": refusals}

    def _checkpoint() -> None:
        payload["raw"], payload["refusals"] = done, refusals
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    _checkpoint()
    try:
        _generate(client, _tool(grid), grid, pack, cells, done, cli_region,
                  refusals, checkpoint=_checkpoint)
    except BaseException:
        _checkpoint()
        print(f"\n⚠ GENERATION FAILED. {len(done)} type(s) and {len(refusals)} "
              f"refusal(s) ARE SAVED at {out}.\n"
              f"  Resume for the cost of the remaining cells only:\n"
              f"    .venv/bin/python scripts/generate_audience.py --fill {out}")
        raise

    # ⚠ SAVE BEFORE TRANSFORMING. Learned the expensive way on 2026-08-14: the
    # first run of this script generated all 40 types, crashed converting them,
    # and threw away ~$1 of model output that was sitting in memory. Anything
    # paid for goes to disk the instant it exists; transformation is free and
    # can be retried with --from-raw.
    _checkpoint()
    print(f"\nraw output saved -> {out}  ({len(done)} types, "
          f"{len(refusals)} refused)")

    dispositions = _convert(done, cli_region)
    _settle(payload, done, dispositions)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\n{len(dispositions)} buyer types -> {out}")
    _report_mix(done, cli_region)
    print("NOTHING has been installed as a library yet. Run the checks first:")
    print("  .venv/bin/python scripts/check_generated_audience.py " + str(out))


if __name__ == "__main__":
    main()
