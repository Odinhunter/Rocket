"""THE F&B WORLD — the competitive universe the 21-moment demand map reasons inside.

⭐⭐ WHY THIS PACK EXISTS, AND WHY IT IS NOT `health_nutrition_snacking` PLUS DRINKS.
The user settled decision 3 on 2026-08-21: the F&B demand map replaces the 8-occasion
grid (`FNB_MAP` in `scripts/generate_audience.py`). A map of 21 moments is useless
against a pack scoped to one product category, because `_pack_brief` hands the model
*"THE BRANDS THAT EXIST IN THIS MARKET (use ONLY these)"* and `_SYSTEM` reinforces it
with *"never invent a brand"*. **The pack is a closed universe.** So a persona at the
afternoon dip, generated against a pack with no chai in it, literally cannot name the
thing that actually wins that moment.

⚠⚠ AND THE SIZE OF THAT HOLE WAS COUNTED, NOT ARGUED. Five real days, 52 items
(`docs/fnb_real_events.md`): **12 of 52 items were beverages and all five people had at
least one.** Both existing packs contain **zero**. That is the SuperYou failure a fifth
time — `#48` no confectionery, `#58` no beverages, `#62` the pack was not the lever,
event 1b a real buyer's protein incumbent was a MILK.

⭐ WHAT EACH BRAND CARRIES THAT NO EARLIER PACK DID: a `moments` subscription list.
A brand no longer belongs to a category; it competes in moments. Parle-G, a Whole Truth
bar and a cup of Bru all list `afternoon_dip`, because that is where they meet in life.
⚠ Values must be `FNB_MAP` keys — pinned by `tests/test_fnb_world.py`.

⚠⚠ THE SIZE TRADE-OFF, STATED BECAUSE IT IS A REAL COST. This pack is far larger than
the 45-brand snacking pack, because it spans what used to be four category packs.
`render._vocab_tokens` builds the invented-brand guardrail out of every TitleCase token
in the pack, so a wider world **makes that check weaker for every run**. Two things pay
for it: (1) `artifact_pack.cut_to_moments()` narrows the world to the moments in play at
read time, which is where a panel is actually assembled; (2) unbranded street and home
food lives in `everyday_alternatives` and `price_points`, NOT in `brand_landscape`, so
it costs the guardrail nothing. ⚠ Recorded in `open_questions` so it is not forgotten.

PROVENANCE. Brand notes and prices researched 2026-08-21 by three bounded web-research
passes (~60 searches total); every price traces to a retrieved listing or report and
nothing was invented. Anything the research could not confirm is in `open_questions`
rather than guessed at. Working notes: `scratchpad/research/`.

⚠ SOURCE PACKS ARE NOT MODIFIED AND MUST NOT BE. `health_nutrition_snacking` is the
before-evidence for the map's 3-of-34 measurement; `health_nutrition_snacking_bev` says
NOT FOR INSTALL on its own first line; `coffee` is hand-authored-era evidence. Brand
notes harvested from them are copied, never moved.
"""

from __future__ import annotations

from agent.artifact_pack import (
    BrandLandscapeEntry as B,
    CategoryArtifactPack,
    Community,
    PricePoint as P,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector



def _chaos() -> ChaosDistribution:
    """⚠ ONE STEP MORE IMPULSIVE THAN THE SNACKING PACK (0.30/0.45/0.25), AND FOR A
    REASON THAT CAME OUT OF THE FIVE REAL DAYS RATHER THAN OUT OF THEORY.

    The snacking pack reasoned that Kantar finds 75%+ of confectionery and salty-snack
    purchases decided BEFORE entering a shop — impulse moved upstream to the screen
    rather than disappearing. That still holds and the deliberate band stays real,
    because the protein and supplement half of this world genuinely reads labels.

    ⭐ But an all-of-F&B world contains moments the snacking grid never had, and they
    are the impulsive ones: a 2am Maggi ordered on Zepto, a 4pm frappuccino bought
    alone, a chai at a stall because the other four are going. Meanwhile it also gains
    the most deliberate behaviour in the whole system — a twice-daily prescription that
    a doctor set. So the distribution widens at BOTH ends and the middle gives up a
    little.
    """
    impulsive = ChaosProfile(
        label="impulsive",
        vector=ChaosVector(
            decision_velocity="impulsive",
            suggestibility="high",
            consistency="erratic",
            risk_tolerance="seeking",
        ),
    )
    moderate = ChaosProfile(
        label="moderate",
        vector=ChaosVector(
            decision_velocity="moderate",
            suggestibility="medium",
            consistency="variable",
            risk_tolerance="balanced",
        ),
    )
    deliberate = ChaosProfile(
        label="deliberate",
        vector=ChaosVector(
            decision_velocity="deliberate",
            suggestibility="low",
            consistency="steady",
            risk_tolerance="averse",
        ),
    )
    return ChaosDistribution(
        weighted=[(impulsive, 0.35), (moderate, 0.38), (deliberate, 0.27)]
    )

# --------------------------------------------------------------------------
# ⚠ `moments` values are FNB_MAP keys. The 21, for reference:
#   clock : first_cup breakfast_sat_down breakfast_in_motion mid_morning_break
#           midday_meal afternoon_dip at_home_tea_or_snack after_school_feed
#           evening_out_of_home evening_meal late_night bedtime_cup
#   event : journey hosting festival_and_gifting celebration recovery_and_care
#           fitness_session
#   habit : daily_regimen hydration household_stock_up
# --------------------------------------------------------------------------

_BRANDS = [
    # ---- TEA, and it is the single most important thing in this pack --------
    B("Tata Tea Premium", "mass",
      "north Indian household default; 'Desh Ki Chai', bought as a 250g or 1kg pouch "
      "and made in a pan, not a bag",
      ["first_cup", "breakfast_sat_down", "at_home_tea_or_snack", "hosting",
       "household_stock_up"]),
    B("Brooke Bond Red Label", "mass",
      "HUL's volume workhorse; in a permanent near-identical price war with Tata and "
      "chosen on whichever pouch is cheaper that month",
      ["first_cup", "breakfast_sat_down", "at_home_tea_or_snack", "hosting",
       "household_stock_up"]),
    B("Taj Mahal", "mass-premium",
      "the aspirational tea kept aside for guests rather than made for the family every "
      "morning",
      ["first_cup", "hosting", "household_stock_up"]),
    B("Wagh Bakri", "regional",
      "Gujarat-origin and now semi-national; strong household lock-in among Gujarati and "
      "Rajasthani families who will not switch",
      ["first_cup", "at_home_tea_or_snack", "hosting", "household_stock_up"]),
    B("Society Tea", "regional",
      "Mumbai and Maharashtra loyalty; embedded in the tapri and hotel supply chain more "
      "than in the household pouch",
      ["first_cup", "at_home_tea_or_snack", "household_stock_up"]),

    # ---- COFFEE, retail ----------------------------------------------------
    B("Nescafé", "mass",
      "for most Indian households instant IS coffee; the small sachet is the category's "
      "actual entry point, not the jar",
      ["first_cup", "mid_morning_break", "afternoon_dip", "household_stock_up"]),
    B("Bru", "mass",
      "HUL's chicory blend; dominant in South instant and in the sub-₹10 sachet economy, "
      "and the coffee a tea household buys",
      ["first_cup", "mid_morning_break", "afternoon_dip", "household_stock_up"]),
    B("Tata Coffee Grand", "mass-premium",
      "decoction-crystal claim a rung above Nescafé Classic; premium instant for a "
      "household trading up without leaving the jar",
      ["first_cup", "breakfast_sat_down", "household_stock_up"]),
    B("Cothas Coffee", "regional",
      "Bengaluru institution; the powder behind South Indian filter coffee, bought by "
      "habit and never by advertising",
      ["first_cup", "breakfast_sat_down", "household_stock_up"]),
    B("Blue Tokai", "d2c-disruptor",
      "defined Indian specialty coffee; single-estate bags for home brewers and now a "
      "café chain, still a class signal in a metro",
      ["first_cup", "mid_morning_break", "household_stock_up"]),

    # ---- CAFÉ CHAINS — the price ceiling, and a real competitive ladder -----
    B("Starbucks India", "premium-cafe",
      "the price ceiling and the status venue; sells seating, air-conditioning and a "
      "place to meet as much as it sells coffee",
      ["mid_morning_break", "afternoon_dip", "evening_out_of_home", "celebration"]),
    B("Third Wave Coffee", "premium-cafe",
      "specialty coffee well under Starbucks; the young-professional default in "
      "Bengaluru and NCR",
      ["mid_morning_break", "afternoon_dip", "evening_out_of_home"]),
    B("abCoffee", "mid-cafe",
      "grab-and-go kiosks explicitly undercutting Starbucks on the identical drink; no "
      "seating, no rent, no lingering",
      ["mid_morning_break", "afternoon_dip", "breakfast_in_motion"]),
    B("Chaayos", "mid-cafe",
      "chai as a café ritual; charges many times the tapri for customisation, hygiene "
      "and somewhere to sit",
      ["mid_morning_break", "afternoon_dip", "evening_out_of_home"]),
    B("Café Coffee Day", "mid-cafe",
      "the fading incumbent; still the cheapest sit-down coffee in many tier-2 malls, "
      "trading on habit rather than pull",
      ["afternoon_dip", "evening_out_of_home"]),

    # ---- CARBONATED --------------------------------------------------------
    B("Thums Up", "mass",
      "strong-fizz cola with masculine codes; over-indexes male and small-town, and is "
      "the default cola drunk with street food",
      ["midday_meal", "evening_meal", "evening_out_of_home", "hosting", "hydration",
       "celebration"]),
    B("Coca-Cola", "mass",
      "aspirational urban default, strongest in QSR and family packs; losing single-serve "
      "ground to Campa on price alone",
      ["midday_meal", "evening_meal", "evening_out_of_home", "hosting", "celebration"]),
    B("Diet Coke", "mass-premium",
      "the sugar-free cola bought by people managing a waistline or a reading rather "
      "than chasing a taste; drunk with a meal, and quietly the only 'diet' thing many "
      "households buy",
      ["evening_meal", "midday_meal", "hydration", "daily_regimen"]),
    B("Sprite", "mass",
      "clear lemon-lime sold as heat relief rather than indulgence; the no-nonsense pick, "
      "peaks in the north Indian summer",
      ["hydration", "midday_meal", "evening_out_of_home", "hosting"]),
    B("Pepsi", "mass",
      "perennial number two; buys share through discount price-packs rather than any "
      "genuine brand preference",
      ["midday_meal", "evening_meal", "evening_out_of_home", "hosting"]),
    B("Mountain Dew", "mass",
      "high-sugar citrus with teen-male adventure codes; disproportionately strong in "
      "tier-2 and tier-3 towns",
      ["evening_out_of_home", "hydration", "late_night"]),
    B("Campa Cola", "mass",
      "Reliance's ₹10 revival; buys shelf with retailer margin and has reset what an "
      "entry-price cola costs in India",
      ["midday_meal", "evening_out_of_home", "hosting", "hydration",
       "household_stock_up"]),
    B("Fanta", "mass",
      "orange fizz skewing young and kid-led; an add-on to the trip, almost never the "
      "reason for it",
      ["after_school_feed", "hosting", "evening_out_of_home"]),

    # ---- JUICE AND MANGO ---------------------------------------------------
    B("Frooti", "mass",
      "Parle Agro's mango staple; the small tetra is a school-bag and kirana-counter "
      "product, and the thing an employer hands out free",
      ["after_school_feed", "midday_meal", "journey", "breakfast_in_motion",
       "evening_out_of_home"]),
    B("Maaza", "mass",
      "Coca-Cola's mango; the family bottle at a meal and the default 'aam' drink in a "
      "QSR combo",
      ["midday_meal", "evening_meal", "hosting", "hydration"]),
    B("Real", "mass-premium",
      "Dabur's fridge-door juice for middle-class households; health-adjacent positioning "
      "over mostly reconstituted concentrate",
      ["breakfast_sat_down", "household_stock_up", "recovery_and_care", "hosting"]),
    B("Tropicana", "mass-premium",
      "carries a faintly imported cue over Real; lives in hotel breakfasts and office "
      "pantries more than in home fridges",
      ["breakfast_sat_down", "mid_morning_break", "household_stock_up"]),
    B("Paper Boat", "mass-premium",
      "nostalgia-coded ethnic drinks — aam panna, jaljeera; urban, and bought for a "
      "journey or a gift more than for a Tuesday",
      ["journey", "hydration", "festival_and_gifting"]),

    # ---- DAIRY DRINKS ------------------------------------------------------
    B("Amul Masti Chaas", "mass",
      "spiced buttermilk in a cheap pouch; meal-adjacent hydration that directly "
      "displaces a soft drink at lunch",
      ["midday_meal", "evening_meal", "hydration"]),
    B("Amul Kool", "mass",
      "flavoured milk in a bottle; kid-facing, sold cold at kirana counters and railway "
      "stalls",
      ["after_school_feed", "journey", "evening_out_of_home"]),
    B("Mother Dairy Lassi", "mass",
      "Delhi-NCR stronghold; sweet lassi as an afternoon indulgence at a fraction of any "
      "café equivalent",
      ["midday_meal", "afternoon_dip", "at_home_tea_or_snack", "hydration"]),
    B("Nandini, Aavin, Verka and the state co-ops", "regional",
      "near-monopoly local trust with semi-political pricing; undercut every private "
      "dairy brand in their own state",
      ["first_cup", "breakfast_sat_down", "bedtime_cup", "household_stock_up"]),

    # ---- WATER AND COCONUT -------------------------------------------------
    B("Bisleri", "mass",
      "the generic word for bottled water; the trust brand whose price sets the floor "
      "everyone else undercuts",
      ["hydration", "journey", "midday_meal", "evening_out_of_home"]),
    B("Kinley", "mass",
      "sold on distribution muscle and restaurant tie-ups rather than on any consumer "
      "preference",
      ["hydration", "midday_meal", "journey"]),
    B("Himalayan", "premium",
      "natural mineral water as a hotel, boardroom and gifting signal, priced several "
      "times mass water for the same thirst",
      ["hydration", "hosting", "festival_and_gifting"]),
    B("Tender Coco", "premium",
      "packaged coconut water for gyms and offices; charges a large convenience premium "
      "over the street nariyal it copies",
      ["hydration", "fitness_session"]),

    # ---- ENERGY AND SPORTS -------------------------------------------------
    B("Sting", "mass",
      "₹20 'energy' that functions as cheap cola for drivers, riders and shift workers; "
      "enormous volume at a price no premium brand can follow",
      ["mid_morning_break", "afternoon_dip", "journey", "fitness_session", "late_night"]),
    B("Red Bull", "premium",
      "still the aspiration and the nightlife default; lost a mass market it was never "
      "priced to hold",
      ["late_night", "fitness_session", "celebration", "evening_out_of_home"]),
    B("Charged by Thums Up", "mass",
      "Coca-Cola's ₹20 answer to Sting; a distribution-led me-too with equity borrowed "
      "from the cola",
      ["afternoon_dip", "journey", "fitness_session"]),
    B("Gatorade", "mass-premium",
      "gym and cricket-coded rehydration; competes with ORS and coconut water far more "
      "than with energy drinks",
      ["fitness_session", "hydration", "recovery_and_care"]),

    # ---- MALTED DRINKS -----------------------------------------------------
    B("Horlicks", "mass",
      "the mother-bought growth drink; functionally a milk additive rather than a "
      "beverage anyone chooses for themselves",
      ["bedtime_cup", "after_school_feed", "breakfast_sat_down", "recovery_and_care",
       "household_stock_up"]),
    B("Bournvita", "mass",
      "the chocolate malt that wins on taste where Horlicks claims nutrition; dented by "
      "the 2023 sugar controversy and still bought",
      ["bedtime_cup", "after_school_feed", "breakfast_sat_down", "household_stock_up"]),
    B("Boost", "mass",
      "sports-coded malt built on cricket endorsements; strongest in south and east India",
      ["bedtime_cup", "after_school_feed", "fitness_session"]),
    B("Complan", "mass-premium",
      "the height-and-growth claim priced above Horlicks per gram, with a share that "
      "shrinks every year",
      ["bedtime_cup", "after_school_feed", "recovery_and_care"]),

    # ---- HIGH-PROTEIN DAIRY ⭐ the four-times-measured miss, finally named ---
    B("Provilac", "d2c-disruptor",
      "Pune-origin subscription dairy now on quick commerce; 25g-protein lactose-free "
      "milk that displaces a whey scoop for people who do not go to a gym",
      ["breakfast_sat_down", "daily_regimen", "fitness_session"]),
    B("Amul High Protein", "mass",
      "cooperative trust at ₹25-30 a pack; makes protein an ordinary dairy purchase "
      "rather than a supplement decision",
      ["breakfast_sat_down", "daily_regimen", "fitness_session", "midday_meal",
       "household_stock_up"]),
    B("Epigamia", "premium",
      "Greek-yoghurt d2c gone mainstream; the Turbo shakes price protein as a lifestyle "
      "beverage and displace a café cold coffee, not a whey tub",
      ["breakfast_sat_down", "mid_morning_break", "afternoon_dip", "daily_regimen"]),
    B("Milky Mist", "mass-premium",
      "Tamil Nadu dairy scaling nationally; brings a protein claim to the curd shelf on "
      "freshness cues rather than on price",
      ["breakfast_sat_down", "daily_regimen", "household_stock_up"]),

    # ---- PROTEIN BARS AND BETTER-FOR-YOU -----------------------------------
    B("Yogabar", "mass-premium",
      "the default quick-commerce protein bar; competes with a Snickers and a biscuit "
      "packet, not with a tub of whey",
      ["breakfast_in_motion", "afternoon_dip", "fitness_session", "journey"]),
    B("The Whole Truth", "d2c-disruptor",
      "dates-sweetened and radically ingredient-transparent; signals reading labels "
      "rather than lifting weights, and sells in boxes rather than singles",
      ["afternoon_dip", "breakfast_in_motion", "fitness_session", "journey"]),
    B("SuperYou", "d2c-disruptor",
      "celebrity-founded wafer bars priced to undercut the premium set; buys trial from "
      "first-time protein buyers rather than converting lifters",
      ["afternoon_dip", "late_night", "fitness_session", "breakfast_in_motion"]),
    B("RiteBite Max Protein", "mass-premium",
      "the gym-counter and chemist incumbent; what 'protein bar' meant before d2c "
      "arrived, and the one that reliably sells a single bar",
      ["afternoon_dip", "fitness_session", "journey"]),
    B("Too Yumm", "mass",
      "baked-not-fried, celebrity-fronted; fights Lay's on the salty shelf while "
      "borrowing a protein claim rather than owning one",
      ["afternoon_dip", "late_night", "evening_out_of_home"]),
    B("Farmley", "d2c-disruptor",
      "dates, makhana and seed mixes; converting dry fruit from occasion gifting into "
      "daily snacking",
      ["afternoon_dip", "household_stock_up", "festival_and_gifting", "journey"]),

    # ---- WHEY AND SUPPLEMENTS ----------------------------------------------
    B("MuscleBlaze", "mass-premium",
      "HealthKart's house giant; Biozyme is the default first tub, priced deliberately "
      "below the imports it is compared against",
      ["fitness_session", "daily_regimen"]),
    B("Optimum Nutrition", "premium",
      "ON Gold Standard; the imported aspiration standard, and counterfeit anxiety "
      "pushes buyers to official channels",
      ["fitness_session", "daily_regimen"]),
    B("AS-IT-IS", "d2c-disruptor",
      "unflavoured raw whey concentrate; tastes like milk powder but is the cheapest per "
      "day, and is the student and beginner value pick",
      ["fitness_session", "daily_regimen"]),
    B("Fast&Up", "premium",
      "effervescent-first sports nutrition; European-coded recovery bought by runners "
      "and cyclists, not by bodybuilders",
      ["fitness_session", "daily_regimen", "recovery_and_care"]),
    B("OZiva", "mass-premium",
      "plant protein and collagen builder; Instagram-led clean-label women's wellness "
      "sold on a routine rather than on a gym",
      ["daily_regimen", "fitness_session"]),
    B("Plix", "d2c-disruptor",
      "vegan collagen and plant protein; content-first, aimed young, and bought from a "
      "reel rather than from a shelf",
      ["daily_regimen"]),

    # ---- PHARMACY REGIMEN AND RECOVERY -------------------------------------
    B("Revital H", "mass-premium",
      "the middle-class parent's energy ritual; bought at the chemist counter on a "
      "pharmacist's word, never researched online",
      ["daily_regimen"]),
    B("Zincovit", "mass",
      "the GP's and the pharmacist's reflex multivitamin, and the cheapest legitimate "
      "daily supplement in India",
      ["daily_regimen", "recovery_and_care"]),
    B("Shelcal", "mass",
      "calcium and vitamin D prescribed to women over 35 and to the elderly; "
      "near-universal in Indian medicine cabinets",
      ["daily_regimen"]),
    B("Neurobion Forte", "mass",
      "a ₹1.5-a-day B-complex embedded in general-practitioner prescribing for weakness "
      "and tingling; taken because a doctor said so",
      ["daily_regimen"]),
    B("Electral", "mass",
      "so default at the chemist that the brand functions as the generic word for ORS; "
      "a remedy purchase, not a beverage occasion",
      ["recovery_and_care", "hydration"]),
    B("ORSL", "mass-premium",
      "ready-to-drink rehydration that moved ORS out of the sickbed and into the fridge "
      "and the gym bag",
      ["recovery_and_care", "hydration", "fitness_session"]),

    # ---- BISCUITS AND RUSK -------------------------------------------------
    B("Parle-G", "mass",
      "the ₹5 glucose biscuit that indexes the bottom of the entire packaged market; "
      "bought by everyone, signals nothing, displaces hunger and not indulgence",
      ["first_cup", "mid_morning_break", "afternoon_dip", "at_home_tea_or_snack",
       "after_school_feed", "household_stock_up"]),
    B("Britannia Good Day", "mass-premium",
      "visible-cashew butter cookie; the 'guests are here' upgrade from Marie, still "
      "bought at the kirana",
      ["at_home_tea_or_snack", "afternoon_dip", "hosting", "household_stock_up"]),
    B("Britannia Marie Gold", "mass",
      "the tea-dunking default of middle-class kitchens; reads light and almost "
      "virtuous, and competes with rusk more than with cookies",
      ["first_cup", "at_home_tea_or_snack", "household_stock_up"]),
    B("Britannia 50-50", "mass",
      "salty-sweet cracker occupying the snack slot rather than the tea slot; households "
      "with children buy it",
      ["at_home_tea_or_snack", "after_school_feed", "household_stock_up"]),
    B("Britannia Bourbon", "mass",
      "cream-filled chocolate biscuit; children's currency and the cheapest thing on the "
      "shelf that reads as dessert",
      ["after_school_feed", "at_home_tea_or_snack", "household_stock_up"]),
    B("Sunfeast Dark Fantasy", "premium",
      "molten-centre cookie priced and shot as dessert; competes with a chocolate bar "
      "rather than with a biscuit",
      ["late_night", "at_home_tea_or_snack", "hosting"]),
    B("Britannia Toastea", "mass",
      "packaged rusk for the chai dunk; the organised replacement for loose bakery toast",
      ["first_cup", "at_home_tea_or_snack", "household_stock_up"]),

    # ---- NAMKEEN AND REGIONAL SAVOURY ⭐ ~43% of the organised savoury market -
    B("Haldiram's", "mass-premium",
      "the default trusted name in ethnic snacks and mithai; signals hygiene and "
      "displaces the local halwai's loose namkeen",
      ["at_home_tea_or_snack", "afternoon_dip", "hosting", "journey",
       "festival_and_gifting", "household_stock_up"]),
    B("Bikaji", "mass",
      "the Bikaner bhujia major gone national; the branded namkeen that legitimised "
      "sweet-shop product inside the kirana",
      ["at_home_tea_or_snack", "afternoon_dip", "hosting", "household_stock_up"]),
    B("Bikano", "mass",
      "Bikanervala's packaged arm; rides the halwai name into the kirana and sits just "
      "under Haldiram's on both trust and price",
      ["hosting", "festival_and_gifting", "household_stock_up"]),
    B("Balaji", "regional",
      "Gujarat and Maharashtra powerhouse in wafers and namkeen; beats Lay's on grammage "
      "per rupee in its home states",
      ["afternoon_dip", "at_home_tea_or_snack", "household_stock_up"]),
    B("Induben Khakhrawala", "regional",
      "the Ahmedabad khakhra institution; handmade, carried out of Gujarat as a gift, "
      "and priced near twice the supermarket version",
      ["breakfast_sat_down", "at_home_tea_or_snack", "journey", "festival_and_gifting"]),
    B("KMA Khakhra", "mass-premium",
      "supermarket khakhra for urban Gujaratis; sold as the guilt-free evening snack "
      "against fried namkeen",
      ["breakfast_sat_down", "at_home_tea_or_snack", "midday_meal", "journey"]),
    B("Chitale Bandhu", "regional",
      "the Pune institution for bakarwadi and chivda; a pride purchase that travels as a "
      "gift",
      ["at_home_tea_or_snack", "hosting", "festival_and_gifting", "journey"]),

    # ---- CHIPS AND EXTRUDED ------------------------------------------------
    B("Lay's", "mass-premium",
      "the aspirational chip; ₹20 is the impulse unit, bought for the brand and the "
      "flavour name rather than for grammage",
      ["afternoon_dip", "late_night", "evening_out_of_home", "journey", "hosting"]),
    B("Kurkure", "mass",
      "extruded corn snack with no western equivalent; loud, spicy, shared from the "
      "packet, and displaces nothing traditional",
      ["afternoon_dip", "after_school_feed", "late_night"]),
    B("Bingo", "mass",
      "the ITC challenger built on flavour novelty; wins trial and loses the habit back "
      "to Lay's",
      ["afternoon_dip", "late_night", "evening_out_of_home"]),

    # ---- INSTANT NOODLES AND QUICK FOOD ------------------------------------
    B("Maggi", "mass",
      "the category synonym and a verb; the hostel, the after-school and the 2am meal — "
      "it displaces cooking, not snacking",
      ["late_night", "at_home_tea_or_snack", "after_school_feed", "evening_meal",
       "household_stock_up"]),
    B("Sunfeast Yippee", "mass",
      "ITC's non-sticky round cake; the deliberate second choice, priced at or just "
      "under Maggi",
      ["late_night", "after_school_feed", "household_stock_up"]),
    B("Maggi Cuppa Noodles", "mass-premium",
      "the cup format at a premium for the office desk and the railway platform; "
      "convenience is the entire product",
      ["mid_morning_break", "journey", "late_night"]),
    B("Knorr", "mass-premium",
      "winter-evening soup treated by urban households as a light dinner rather than as "
      "a snack",
      ["evening_meal", "recovery_and_care"]),

    # ---- CHOCOLATE AND CONFECTIONERY ---------------------------------------
    B("Cadbury Dairy Milk", "mass",
      "the default chocolate and the default small gift; the ₹10 bar is impulse and the "
      "large bar is an occasion",
      ["afternoon_dip", "late_night", "after_school_feed", "celebration",
       "festival_and_gifting"]),
    B("Cadbury Silk", "mass-premium",
      "softer Dairy Milk at a markup; the self-treat and everyday-gifting tier",
      ["late_night", "celebration", "festival_and_gifting"]),
    B("KitKat", "mass",
      "break-time framing, wafer-led and cheaper per gram than solid chocolate; India is "
      "now its largest market in the world",
      ["mid_morning_break", "afternoon_dip", "after_school_feed"]),
    B("Cadbury 5 Star", "mass",
      "chewy caramel bar with heft; sold as filling and competing with a snack more than "
      "with a chocolate",
      ["afternoon_dip", "evening_out_of_home", "after_school_feed"]),
    B("Munch", "mass",
      "the cheapest crunchy wafer bar at the ₹5-₹10 point; schoolbag and chai-shop "
      "staple with no aspiration attached",
      ["afternoon_dip", "after_school_feed", "mid_morning_break"]),
    B("Snickers", "mass-premium",
      "the peanut bar sold as almost-a-meal at the counter; the closest mainstream "
      "analogue to a protein bar's own pitch",
      ["afternoon_dip", "journey", "breakfast_in_motion", "fitness_session"]),
    B("Ferrero Rocher", "premium",
      "the gold-wrapped gifting unit; rarely self-consumed, and its whole value is what "
      "it says when it is handed over",
      ["festival_and_gifting", "hosting"]),
    B("Cadbury Celebrations", "mass-premium",
      "the assembled box that replaced mithai for urban middle-class Diwali; safe, "
      "tiered and risk-free",
      ["festival_and_gifting", "hosting"]),

    # ---- ICE CREAM ---------------------------------------------------------
    B("Amul", "mass",
      "the cooperative trust mark across milk, butter and ice cream; the real-milk claim "
      "weaponised against 'frozen dessert' rivals",
      ["late_night", "evening_out_of_home", "hosting", "celebration",
       "household_stock_up", "breakfast_sat_down"]),
    B("Kwality Wall's", "mass-premium",
      "strongest on impulse formats at the cart and the freezer — the cone and the bar, "
      "not the family tub",
      ["evening_out_of_home", "late_night", "after_school_feed"]),
    B("Vadilal", "mass",
      "Gujarat-origin national player; the family-pack value buy across west and north "
      "India",
      ["hosting", "celebration", "household_stock_up"]),
    B("Naturals", "premium",
      "Mumbai fruit-forward chain; the no-essence positioning makes it a destination and "
      "a small indulgence rather than a freezer item",
      ["evening_out_of_home", "celebration"]),

    # ---- BREAKFAST, BREAD AND SPREADS --------------------------------------
    B("Kellogg's", "mass-premium",
      "corn flakes as the modern light breakfast; urban families buy it and then add "
      "milk and sugar anyway",
      ["breakfast_sat_down", "household_stock_up"]),
    B("Saffola Oats", "mass-premium",
      "the masala-oats format that made oats edible as Indian food; the category's one "
      "successful indianisation",
      ["breakfast_sat_down", "evening_meal", "daily_regimen"]),
    B("Bagrry's", "premium",
      "muesli and oats specialist with a health-first shelf presence; an older, "
      "income-heavy urban buyer",
      ["breakfast_sat_down", "daily_regimen", "household_stock_up"]),
    B("MTR", "mass",
      "instant idli, dosa and gulab jamun mixes; bought for the weekday shortcut and by "
      "households living abroad",
      ["breakfast_sat_down", "hosting", "household_stock_up"]),
    B("Britannia bread", "mass",
      "the ₹40-60 loaf; toast-and-jam breakfast and the base for every street sandwich",
      ["breakfast_sat_down", "at_home_tea_or_snack", "household_stock_up"]),
    B("Kissan", "mass",
      "mixed-fruit jam as the child's breakfast sweetener; a near-monopoly in the mind "
      "if not on the shelf",
      ["breakfast_sat_down", "at_home_tea_or_snack", "after_school_feed",
       "household_stock_up"]),
]


# --------------------------------------------------------------------------
# PRICES. ⭐ The spread is the point: ₹2 for a Parle-G mini pouch to ₹560 for a
# venti frappuccino, both real, both 2026, both observed in the five real days
# (`docs/fnb_real_events.md`) at their two extremes — P2 and P5 drink ₹12 tapri
# chai; P4 drinks a Starbucks frappuccino at 4pm.
# ⚠ Anything the research could not confirm is in `open_questions`, NOT here.
# --------------------------------------------------------------------------

_PRICES = [
    # the floor
    P("Parle-G mini pouch", "₹2-₹3 for a 25g pouch", "kirana"),
    P("Electral ORS small sachet", "₹4.40 for a 4.4g sachet", "chemist"),
    P("Britannia Marie Gold", "₹5 for a 43g pouch", "kirana"),
    P("Haldiram's Aloo Bhujia", "₹5 for a 25g pouch", "kirana"),
    P("Campa Cola", "₹10 for a 200ml PET", "kirana"),
    P("Haldiram's Bhujia Sev", "₹10 for a 40g pouch", "kirana"),
    P("cutting chai at a tapri", "₹10-₹18 for a small glass", "street stall"),
    P("Sunfeast Yippee Magic Masala", "₹12 for a 70g pack", "kirana"),
    P("Maggi 2-Minute Masala", "₹14-₹15 for a 70g pouch", "kirana"),
    P("samosa at a tapri", "₹7-₹10 each", "street stall"),
    P("vada pav", "₹15-₹30 each in Mumbai", "street stall"),
    P("Amul Masti Chaas", "₹15-₹18 for a 200ml pouch", "kirana"),
    P("Cadbury Dairy Milk", "₹18 for a 23-24g pouch", "supermarket"),
    P("Sting", "₹20 for a 250ml PET", "kirana"),
    P("Charged by Thums Up", "₹19-₹20 for a 250ml PET", "quick commerce"),
    P("Lay's India's Magic Masala", "₹20 for a 48-52g pouch", "kirana"),
    P("packaged water — Bisleri, Kinley", "₹16-₹20 for a 1L PET, MRP ₹20", "kirana"),
    P("Electral ORS", "₹22-₹23 for a 21.8g sachet", "chemist"),
    P("Amul Kool Kesar flavoured milk", "₹25 for a 180ml bottle", "kirana"),
    P("Amul Sweet Lassi", "₹25 for a 250ml tetra pack", "quick commerce"),
    P("Amul Calci+ High Protein Milk", "₹26 for a 250ml pack", "quick commerce"),
    P("momo plate at a street stall", "₹30-₹50 for 6-8 pieces", "street stall"),
    P("Maaza", "₹34-₹38 for a 600ml PET, MRP ₹40", "quick commerce"),
    P("Britannia Bake Rusk Toast", "₹35 for a 183-200g pack", "supermarket"),
    P("Amul Gold Butterscotch Tricone", "₹35 for one cone", "quick commerce"),
    P("Thums Up", "₹35-₹40 for a 750ml PET, MRP ₹40-₹45", "kirana"),
    P("Neurobion Forte", "₹47 for a strip of 30 tablets", "chemist"),
    P("Too Yumm protein chips", "₹47 for a 60g pack", "quick commerce"),
    P("Gatorade", "₹49-₹50 for a 500ml bottle", "quick commerce"),
    P("pav bhaji at a stall", "~₹50 a plate", "street stall"),
    P("Britannia Milk Bread", "₹55 for a 400g loaf", "supermarket"),
    P("Haldiram's Bhujia Sev", "₹59 for a 150g pouch", "supermarket"),
    P("SuperYou protein wafer bar", "₹60 for a 40g bar", "quick commerce"),
    P("tender coconut on the street", "₹50-₹70 each", "street vendor"),
    P("Milky Mist SKYR high-protein yogurt", "₹65 for a 100g cup, MRP ₹75", "quick commerce"),
    P("KMA Khakhra Masala", "₹75 for a 200g pouch", "supermarket"),
    P("Provilac 25g High Protein Milk, lactose-free", "₹75 for a 250ml bottle, MRP ₹90",
      "quick commerce"),
    P("RiteBite Max Protein Daily bar", "₹80 for a 50g bar", "quick commerce"),
    P("Parle-G family pouch", "₹93 for 800g", "supermarket"),
    P("abCoffee latte", "₹101 for a standard latte", "café kiosk"),
    P("Yogabar 20g protein bar", "₹101 for a single bar", "quick commerce"),
    P("The Whole Truth protein bar", "₹104 for a 52g bar", "quick commerce"),
    P("Epigamia Turbo 25g protein milkshake", "₹113-₹127 for a 250ml bottle", "quick commerce"),
    P("Red Bull", "₹125-₹127 for a 250ml can", "kirana"),
    P("Café Coffee Day cappuccino", "₹143", "café"),
    P("Induben handmade methi khakhra", "₹150 for 200g", "brand store"),
    P("Complan Kesar Badam", "₹182 MRP for a 500g refill", "kirana"),
    P("Kellogg's Corn Flakes", "₹186 for a 475g carton", "supermarket"),
    P("Bournvita", "₹214-₹307 for a 500g pack", "kirana"),
    P("Revital H", "₹245 for 30 capsules", "chemist"),
    P("Starbucks tall Americano", "₹270", "café"),
    P("Tata Tea Premium", "₹336-₹368 for a 1kg pouch", "kirana"),
    P("Starbucks latte", "₹367 tall, ₹425 venti", "café"),
    P("Nescafé Classic", "₹416-₹430 for a 90g jar", "quick commerce"),
    P("Starbucks Frappuccino", "₹425 tall to ₹560 venti", "café"),
    P("MuscleBlaze Biozyme whey", "from ₹3,099 for a 2kg tub", "supplement specialist"),
]


PACK = CategoryArtifactPack(
    category="fnb_world",
    market_name="Indian urban food and beverage",
    brand_landscape=_BRANDS,
    price_points=_PRICES,
    retail_channels=[
        "kirana counter — the shop downstairs; single bars, single biscuit packs, the "
        "₹5 and ₹10 coin price points that exist nowhere else; bought in seconds, often "
        "on the way past, often on a running tab",
        "supermarket aisle — the weekly or monthly shop; family packs and tins; a planned "
        "list with room for one or two additions",
        "quick commerce — Blinkit, Zepto, Swiggy Instamart, BigBasket — ten-minute "
        "delivery; a top-up mission, not a browse; the shopper arrives already knowing "
        "what they want and is gone in under five minutes. ⚠ larger and more premium "
        "packs than the shop downstairs, and the smallest coin packs are largely absent. "
        "handling and delivery fees are now normal and differ by app",
        "food delivery — Swiggy and Zomato; the ordered-in meal, whether it is a Friday "
        "treat or a Tuesday because nobody cooked; discounts and the ₹100-₹200 order "
        "band are actively fought over",
        "street cart and chai stall — samosa, vada pav, momos, chaat, cutting chai; hot, "
        "immediate, and cheaper than almost anything packaged",
        "bhojanalay, mess or dhaba — the bought everyday meal for people without a "
        "kitchen; necessity rather than a night out",
        "office pantry or canteen — free or near-free, immediate, hot; the thing an "
        "afternoon snack is really competing with at work",
        "tiffin from home — packed by someone else, costs the eater nothing, and still "
        "wins the moment",
        "local bakery and farsan shop — khaari, rusk, fafda, dhokla and thepla sold loose "
        "by weight, unbranded and undated, hot before eleven in the morning",
        "café — seating, air-conditioning and somewhere to sit as much as a drink",
        "online marketplace — the price-comparison and review-reading surface for tubs, "
        "boxes and multipacks; not where a single bar is bought",
        "pharmacy — prescribed daily tablets, doctor-named brands, refills of a course",
        "gym counter — post-workout, captive, marked up",
        "airport, station and highway stop — captive pricing and travel formats",
    ],
    communities=[
        # ⚠ Harvested from packs/health_nutrition_snacking.py, which is unmodified.
        Community("FoodPharmer", "creator-activist",
                  "turn-the-pack-over label reading; drove a mainstream habit of "
                  "checking the ingredient list and the sugar position"),
        Community("Fittuber", "youtuber",
                  "product-ingredient debunks; the 'is this brand clean' review that "
                  "decides a purchase for a lot of people"),
        Community("Tarun Gill", "youtuber",
                  "supplement reviews and authenticity exposes; the serious lifter's "
                  "reference point"),
        Community("Lovneet Batra", "nutritionist-creator",
                  "clean-label women's wellness; the trigger for a lot of plant-protein "
                  "and collagen buying"),
        Community("Kunal Vijayakar and the food-vlog circuit", "youtuber",
                  "street and regional food as entertainment; makes a vada pav or a "
                  "fafda a thing worth travelling for rather than a default"),
        Community("family WhatsApp group", "whatsapp",
                  "forwarded diet advice, sugar scares and a relative's diagnosis; "
                  "changes more shelves than any advertisement"),
    ],
    cultural_references=[
        # ⚠⚠ THE STALE ONE, CORRECTED. `health_nutrition_snacking` carries
        # "shrinkflation as betrayal — the pack costs the same and holds less". That
        # was true and is now BACKWARDS: GST 2.0 (22 Sept 2025) cut biscuits, namkeen,
        # chips, noodles, bakery, jams and ice cream from 12-18% to 5%, and companies
        # HELD the ₹5/₹10 MRP and put grammage back in. Do not carry the old line
        # forward; it would teach personas a grievance that has been reversed.
        "the ₹5 and ₹10 pack IS the market — roughly 62% of Britannia's packs sit at one "
        "of those two coins, and the price point is defended ahead of the grammage",
        "shrinkflation running BACKWARDS since the September 2025 tax cut — the same "
        "coin now buys more grams, and the packs that shrank for two years quietly "
        "refilled instead of dropping their price",
        "the ₹20 energy drink as ordinary working fuel for a driver or a rider, and the "
        "₹125 can as a different product for a different life",
        "chai at the stall as a BREAK rather than a drink — bought for the five minutes "
        "and the company, and competing with no packaged product at all",
        "the café bill as a class marker; paying three hundred rupees for somewhere to "
        "sit, and knowing that is what you are paying for",
        "protein on everything — protein biscuits, protein chips, protein water; the "
        "claim has spread far enough that it now reads as packaging rather than a reason",
        "the doubt about whether the protein number on the pack is real at all, after "
        "lab testing found widespread mislabelling",
        "food-first counter-narrative — ghee, dal, rice and 'my grandmother never took a "
        "pill'; packaged nutrition as anxiety sold back to you",
        "the mithai-versus-chocolate question every festival — what you gift, what you "
        "keep, and what sits in the fridge for a week afterwards",
        "diabetes in the family as the thing that actually changes a shelf; a reading on "
        "a report does more than any advertisement",
        "the office or the site providing the food — a spread laid on, a boss's lunch, a "
        "tiffin packed at home — and nobody deciding anything at all",
    ],
    voice_samples=[
        "chai to peene ka bahana hai, break chahiye bas. paanch minute baahar khade rehna",
        "ek Parle-G ka packet ab thoda bada aa raha hai, dus rupaye mein hi. pehle chhota "
        "kar diya tha inhone",
        "sting le leta hoon, bees rupaye. red bull sau se upar ka hai, kaun deta hai itna",
        "starbucks is a status symbol for people who can't afford a bmw. 292 rupees to "
        "look cool, that's the whole thing",
        "office pantry pe bru se acchi chai banti hai honestly, chaayos ka ninety rupaye "
        "ka sugar water hai",
        "i take the protein milk every morning, 25g, it just fits into the routine. i'm "
        "not going to sit and eat paneer at 8am",
        "boss ne khana diya tha site pe, roti sabji aur frooti. paisa nahi lagta usme",
        "ghar se dabba aata hai, bahar ka khaane ka sawaal hi nahi",
        "2 baje maggi bana li, kuch aur tha hi nahi ghar mein. zepto se le aaya tha",
        "MRP ₹500 dikha rahe hain aur same product ₹220 mein milta hai. 60% off ka chakkar hai",
        "doctor ne bola hai roz lena hai, toh le raha hoon. taste ka sawaal nahi hai",
        "everything is protein now, protein chips protein biscuit. matlab kuch bhi",
    ],
    behavioral_priors=(
        "⭐⭐ THE PRICE STEP IS THE WHOLE COMPETITIVE STORY, AND IT IS BIGGER THAN ANY "
        "BRAND DIFFERENCE. A ₹104 protein bar or a ₹110 high-protein dairy pack is not "
        "competing with a ₹3,099 tub of whey. It is competing with a ₹25 lassi, a ₹15 "
        "vada pav, a ₹12 cutting chai and a ₹47 packet of chips — a four-to-nine-times "
        "price step for the SAME eating moment. Anyone weighing one against the other is "
        "weighing a multiple, not a preference. And ₹23 Electral or ₹47 Neurobion show "
        "what 'functional' costs when a pharmacist sets the price instead of a marketer.\n"
        "⚠ Price, not brand, has decided whole categories here: a ₹20 energy drink took "
        "the volume a ₹125 one never could, and a ₹10 cola reset what an entry cola "
        "costs. Volume arrived at the bottom, so category value grew far slower than "
        "category consumption.\n"
        "⚠⚠ AND MOST FOOD IS NOT BOUGHT BY THE PERSON WHO EATS IT. Measured on five real "
        "days: a boss provided lunch on a site, a mother packed a college tiffin, a wife "
        "decided twelve of one man's fourteen items, an employer laid on an office "
        "spread. Only one person in five bought everything he ate. Provided food costs "
        "the eater nothing and still consumes the appetite a brand wanted."
    ),
    default_chaos_distribution=_chaos(),
    # ---- document projection; reaches no prompt ----------------------------
    market_stats=[
        {"stat": "12 of 52 items across five real Indian days were beverages, and all "
                 "five people had at least one",
         "source": "docs/fnb_real_events.md, 2026-08-21 — the only primary consumption "
                   "data this project holds"},
        {"stat": "GST 2.0, effective 22 Sept 2025, moved biscuits, namkeen, chips, "
                 "extruded snacks, instant noodles, bakery, jams and ice cream from "
                 "12-18% GST to 5%; companies largely held the ₹5/₹10 MRP and added "
                 "grammage instead of cutting price",
         "source": "https://www.caclubindia.com/news/gst-2-0-rollout-fmcg-and-consumer-"
                   "goods-makers-announce-price-cuts-upgrade-systems-25510.asp"},
        {"stat": "roughly 62% of Britannia's packs sit at ₹5 or ₹10",
         "source": "https://a2ztaxcorp.net/slice-of-gst-from-chips-to-shampoo-fmcg-cos-"
                   "plan-to-stuff-more-into-rs-5-and-rs-10-packs/"},
        {"stat": "ethnic bhujia (₹6,700cr) plus other traditional namkeen, dried samosa "
                 "and kachori (₹11,400cr) is ~43% of the ₹42,300cr organised savoury "
                 "market — traditional is the bigger half, not the niche",
         "source": "https://theprint.in/economy/nachos-over-bhujia-chips-over-kachori-"
                   "western-snacks-dominate-indian-market-but-that-might-change-soon/"
                   "1518479/"},
        {"stat": "Sting at ₹20/250ml holds ~90% of energy-drink VOLUME; Red Bull at ₹125 "
                 "fell from ~75% share (2018) to ~7% (2023). ⚠ figures are 2023-24 "
                 "vintage",
         "source": "https://the-ken.com/story/red-bull-is-the-energy-drink-of-the-world-"
                   "how-did-pepsico-make-sting-the-energy-drink-of-india/"},
        {"stat": "energy-drink market value ~$0.82bn (2026) rising to only ~$0.94bn by "
                 "2031, a 2.25% CAGR, despite consumption reportedly up 30x — value "
                 "lags volume badly because the volume arrived at ₹20",
         "source": "https://www.mordorintelligence.com/industry-reports/india-energy-"
                   "drink-market"},
        {"stat": "Campa Cola at ₹10/200ml moved from ~2% to over 7% national share by "
                 "early 2026 on a ₹8,000cr capacity plan",
         "source": "https://www.business-standard.com/companies/news/campa-cola-s-"
                   "comeback-how-reliance-is-shaking-up-india-s-drink-market-"
                   "124101900625_1.html"},
        {"stat": "tea is DEFLATING, rare in Indian FMCG: north Indian bulk tea averaged "
                 "₹205.50/kg to Aug 2025 vs ₹222.37 a year earlier (-8% YoY); Tata "
                 "Consumer cut MRPs across most tea brands in Sept 2025",
         "source": "https://www.business-standard.com/markets/news/tata-consumer-rallies-"
                   "4-on-heavy-volumes-on-price-reduction-of-tea-brands-"
                   "125091700722_1.html"},
        {"stat": "73% of Indians eat below the 60-70g/day protein guideline — the "
                 "category's entire pitch is a deficit, and consumption is moving from "
                 "gym-centric to mainstream",
         "source": "https://www.mordorintelligence.com/industry-reports/india-protein-"
                   "market"},
        {"stat": "quick commerce crossed food delivery: Blinkit GOV ₹11,821cr in the "
                 "June-2025 quarter against Zomato food delivery's ₹10,769cr; India "
                 "q-commerce has passed ₹50,000cr GMV with Blinkit ~46%, Instamart ~24%, "
                 "Zepto ~22%",
         "source": "https://www.storyboard18.com/brand-marketing/blinkit-zepto-instamart-"
                   "raise-fees-as-quick-commerce-goes-mainstream-ws-l-99758.htm"},
        {"stat": "the free-delivery era is over and fees now diverge — Blinkit ₹4-11 "
                 "handling, Instamart ₹9.8 + ₹30 under ₹199, Zepto at zero. Single-serve "
                 "protein formats are rising at ~40% higher cost per gram: the trial "
                 "barrier is being lowered on TICKET SIZE, not on value",
         "source": "https://www.storyboard18.com/brand-marketing/blinkit-zepto-instamart-"
                   "raise-fees-as-quick-commerce-goes-mainstream-ws-l-99758.htm"},
        {"stat": "Starbucks India took a 5-10% price rise in early 2026; abCoffee sells a "
                 "latte at ₹101 against Starbucks' ₹367, growing on grab-and-go kiosks "
                 "with no seating",
         "source": "https://www.worldcoffeeportal.com/news/indias-abcoffee-expands-market-"
                   "share-with-focus-on-value-and-loyalty/"},
    ],
    open_questions=[
        "⚠⚠ THE BHOJANALAY / MESS THALI PRICE IS UNKNOWN AND WAS DELIBERATELY NOT "
        "GUESSED. No credible 2026 figure surfaced; the ₹300-500 'thali' numbers in "
        "search results are wedding catering and the wrong context. Practitioner range "
        "is roughly ₹60-120, unsourced. ⭐ This matters because P2 in "
        "docs/fnb_real_events.md eats there EVERY NIGHT — the user can simply ask him.",
        "⚠ Starbucks India menu prices are contested between aggregators: magicpin (May "
        "2026) gives a ₹367 tall latte and ₹425-560 frappuccinos; menupricesindia gives "
        "₹270 and ₹300-330. The higher set is used here because its ₹270 tall Americano "
        "was independently corroborated. Treat the lower set as likely stale.",
        "⚠ Parle-G grammage at the ₹5 and ₹10 points is in flux post-GST (50g vs 70g, "
        "120g vs 140g). Direction of travel is UP. Do not state a fixed gram figure.",
        "⚠ No reliable 2026 India price found for: Boost, Bailley, Subko, Epigamia "
        "single unit, Milky Mist beyond the SKYR cup, and the full Third Wave, Chaayos "
        "and Chai Point menus. Brand notes only — do not invent a number.",
        "⚠⚠ THE PACK IS LARGE — 104 brands against the 45 of a single-category pack, "
        "because it spans what used to be four packs. render._vocab_tokens builds the "
        "invented-brand guardrail from TitleCase tokens, so a wider world makes that "
        "check WEAKER for every run. artifact_pack.cut_to_moments() exists to narrow it "
        "at read time and is NOT yet wired into the read path. Wire it before this pack "
        "carries a customer-facing read.",
        "Occasion SIZING is still unpurchased. No published occasion segmentation for "
        "India exists in open sources; the real answer sits in Kantar's occasion panel. "
        "The map is a design artifact, exactly as the grid was — defensible, testable "
        "against ads, and not measured.",
        "Regional coverage is thin outside the north and west. South Indian filter "
        "coffee, Tamil and Kerala snack formats and the eastern sweet economy are "
        "represented by one or two brands each and deserve their own pass.",
    ],
    sources=[
        {"what": "prices and brand notes",
         "how": "researched 2026-08-21 in three bounded web-research passes, ~60 "
                "searches; every price traces to a retrieved listing or report, nothing "
                "invented, everything unconfirmed left in open_questions",
         "notes": "scratchpad/research/beverages.md, protein_channels.md"},
        {"what": "harvested brand notes",
         "how": "chocolate, biscuits, namkeen, chips, whey and pharmacy notes copied "
                "from packs/health_nutrition_snacking.py; tea, coffee and malted notes "
                "partly from health_nutrition_snacking_bev.py and coffee.py",
         "notes": "⚠ all three source packs are UNMODIFIED and remain evidence"},
        {"what": "moment subscriptions",
         "how": "AUTHORED, not sourced — a design judgement about where each brand "
                "competes",
         "notes": "⚠ this is the part the first generated region actually tests"},
        {"what": "the beverage gap that forced this pack",
         "how": "counted on five real days: 12 of 52 items were drinks, all five people "
                "affected, both existing packs contain zero",
         "notes": "docs/fnb_real_events.md"},
    ],
)
