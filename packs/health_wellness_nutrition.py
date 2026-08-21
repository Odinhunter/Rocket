"""Category artifact pack: health_wellness_nutrition — India D2C
supplements / protein / functional wellness.

Hand-curated 2026-06-02 from data/voice_samples/health_wellness_nutrition.md
(live web research: Amazon.in / Nykaa / Flipkart / HealthKart / Quora /
Practo reviews + market reports). Distinct from the older packs/wellness.py,
which is the ayurveda / chyawanprash / Patanjali-Ramdev framing — this pack
is the modern protein + gummies + plant-wellness + prescribed-vitamin shelf.

The render engine may only weave artifacts present here. Every brand /
creator / channel named in the scaffold_health_wellness dispositions is
represented below so render output validates clean.
"""

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos() -> ChaosDistribution:
    # Wellness/supplements splits two ways: the deliberate evidence/review
    # reader (lifter checking macros, switcher reading 500 Nykaa reviews) and
    # the impulsive Insta-reel / Blinkit-grab buyer (clean-label reel trial,
    # 4pm protein-bar grab). Skews moderate, a touch more impulsive than
    # ayurveda-wellness because of the influencer-discovery + q-commerce pull.
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
        weighted=[(impulsive, 0.25), (moderate, 0.45), (deliberate, 0.30)]
    )


PACK = CategoryArtifactPack(
    category="health_wellness_nutrition",
    market_name="Indian D2C supplements, protein and wellness",
    brand_landscape=[
        # --- Performance / gym protein ---
        BrandLandscapeEntry(
            name="MuscleBlaze", tier="mass-premium",
            note="HealthKart house brand; Biozyme Performance Whey is a leading serious-lifter pick",
        ),
        BrandLandscapeEntry(
            name="Optimum Nutrition", tier="premium",
            note="ON Gold Standard; the imported aspirational tier at ~₹70-80/serving",
        ),
        BrandLandscapeEntry(
            name="AS-IT-IS", tier="d2c-disruptor",
            note="unflavoured raw whey concentrate; 'tastes like milk powder' but <₹50/day; student/beginner value pick; Labdoor + Trustified",
        ),
        BrandLandscapeEntry(
            name="MyProtein", tier="d2c-disruptor",
            note="imported whey / creatine; sale-event buying",
        ),
        BrandLandscapeEntry(
            name="Fast&Up", tier="mass-premium",
            note="effervescent tablets, plant protein; urban functional",
        ),
        # --- Plant / lifestyle / functional wellness ---
        BrandLandscapeEntry(
            name="OZiva", tier="mass-premium",
            note="HUL-owned (2023); plant protein + Plant-Based Collagen Builder; Instagram-led; clean-label women's wellness",
        ),
        BrandLandscapeEntry(
            name="Plix", tier="d2c-disruptor",
            note="The Plant Fix; Honasa/Mamaearth-incubated; vegan collagen + plant protein; Gen-Z/millennial content-first",
        ),
        BrandLandscapeEntry(
            name="Power Gummies", tier="d2c-disruptor",
            note="biotin hair & nails gummies; ₹699 60-day; the gateway beauty-supplement",
        ),
        BrandLandscapeEntry(
            name="Setu", tier="mass-premium",
            note="marine collagen + hair vitamins; 'fishy aftertaste if not masked'",
        ),
        BrandLandscapeEntry(
            name="HK Vitals", tier="mass-premium",
            note="HealthKart house wellness brand; value collagen + multivitamins; 'hairfall reduced' value pick",
        ),
        BrandLandscapeEntry(
            name="Wellbeing Nutrition", tier="premium",
            note="'slow' clean-label capsules, melts; premium functional",
        ),
        BrandLandscapeEntry(
            name="Carbamide Forte", tier="mass",
            note="Amazon-native value multivitamin / supplements",
        ),
        BrandLandscapeEntry(
            name="TrueBasics", tier="premium",
            note="HealthKart premium clinical-leaning supplements",
        ),
        # --- Healthy snacking ---
        BrandLandscapeEntry(
            name="Yogabar", tier="mass-premium",
            note="ITC-owned (2023); 20g protein bars + protein oats; 'snack not supplement'; Blinkit/airport",
        ),
        BrandLandscapeEntry(
            name="RiteBite Max Protein", tier="mass-premium",
            note="protein bars/cookies; 'guilt-free snack' framing",
        ),
        BrandLandscapeEntry(
            name="The Whole Truth", tier="premium",
            note="dates-sweetened, 5-6 recognisable ingredients; radical-transparency premium bar ~₹96",
        ),
        # --- Doctor-prescribed / pharmacy ---
        BrandLandscapeEntry(
            name="Calcirol", tier="pharmacy",
            note="60K IU vitamin-D sachet, ~₹35; doctor-prescribed, mixed in milk; 'the vitamin-D one'",
        ),
        BrandLandscapeEntry(
            name="Livogen", tier="pharmacy",
            note="ferrous fumarate + folic acid iron tablet; 'the iron one'; pregnancy/anaemia; constipation gripe",
        ),
        BrandLandscapeEntry(
            name="Shelcal", tier="pharmacy",
            note="calcium + vitamin-D; the gynae/ortho postpartum default",
        ),
        BrandLandscapeEntry(
            name="Uprise-D3", tier="pharmacy",
            note="alternative prescribed vitamin-D3 sachet/drops",
        ),
    ],
    price_points=[
        PricePoint(item="MuscleBlaze Biozyme Performance Whey 1kg chocolate (25g/scoop)", price_inr="₹2,699 (MRP ₹2,949)", channel="HealthKart"),
        PricePoint(item="MuscleBlaze Beginner's Whey 1kg", price_inr="₹1,599", channel="Amazon"),
        PricePoint(item="Optimum Nutrition Gold Standard 2.27kg", price_inr="₹4,200-4,800 (~₹70-80/serving)", channel="Amazon"),
        PricePoint(item="AS-IT-IS Whey Concentrate 1kg unflavoured", price_inr="~₹1,250 (<₹50/day)", channel="Amazon / DTC"),
        PricePoint(item="OZiva Plant-Based Collagen Builder", price_inr="₹1,499", channel="Nykaa"),
        PricePoint(item="OZiva Plant Protein 1kg", price_inr="~₹1,699 (~₹51.5/serving)", channel="Nykaa / DTC"),
        PricePoint(item="Plix Plant Protein vanilla 1kg", price_inr="~₹2,000", channel="Nykaa / DTC"),
        PricePoint(item="Power Gummies Hair & Nails biotin (60-day)", price_inr="₹699", channel="Amazon / DTC"),
        PricePoint(item="HK Vitals Skin Radiance Collagen", price_inr="~₹599-899", channel="HealthKart / Flipkart"),
        PricePoint(item="Yogabar 20g Protein Bar (variety pack of 5)", price_inr="₹625", channel="Flipkart / Blinkit"),
        PricePoint(item="The Whole Truth Protein Bar (single)", price_inr="₹96", channel="Blinkit / Zepto"),
        PricePoint(item="Calcirol 60K IU vitamin-D sachet", price_inr="~₹35/sachet", channel="1mg / Apollo"),
        PricePoint(item="Livogen XT iron tablet (10s)", price_inr="~₹80", channel="Apollo / PharmEasy"),
    ],
    # render-10: each channel carries WHAT IT ACTUALLY SELLS, because the
    # persona writer used to be handed a bare list and had no way to know
    # that a beauty marketplace is the wrong place to look for a protein
    # bar. The skew note is what lets a clean-label supplement buyer and a
    # bar buyer pick different shops from the same list.
    # ⚠ Keep these notes lowercase and generic — agent/render.py feeds this
    # list into _vocab_tokens, so every TitleCase word here joins the
    # allowed set for the invented-artifact check and weakens it.
    retail_channels=[
        "HealthKart — sports nutrition specialist; whey, mass gainers, "
        "creatine; authenticity-seal scanning",
        "Amazon — everything; the default price-comparison and review-reading "
        "surface for powders and tubs",
        "Flipkart — everything; big-billion-day discounting on tubs and bars",
        "Nykaa — beauty and personal care first; collagen, biotin, hair and "
        "skin supplements, clean-label wellness. NOT where whey, mass "
        "gainers or protein bars are bought",
        "Blinkit — 10-minute quick commerce; bars, single snacks, "
        "top-up buys",
        "Zepto — 10-minute quick commerce; bars, single snacks, top-up buys",
        "1mg — online pharmacy; prescribed deficiency supplements, "
        "doctor-named brands",
        "Apollo Pharmacy — pharmacy chain, online and offline; prescribed "
        "vitamins and minerals",
        "PharmEasy — online pharmacy; refills of prescribed courses",
        "brand DTC website — the brand's own site; subscription, launches "
        "and clean-label direct-to-consumer wellness",
    ],
    communities=[
        Community(
            name="Tarun Gill", kind="youtuber",
            note="1.4M+ subs; supplement reviews + authenticity exposes; the serious-lifter's reference",
        ),
        Community(
            name="Guru Mann", kind="youtuber",
            note="2.3M+ subs; biomechanics-credentialed fitness + nutrition plans",
        ),
        Community(
            name="Fittuber", kind="youtuber",
            note="Vivek Mittal; product-ingredient debunks; 'is this brand clean' reviews",
        ),
        Community(
            name="Lovneet Batra", kind="nutritionist-creator",
            note="Instagram nutritionist; clean-label women's wellness trigger",
        ),
        Community(
            name="Rashi Chowdhary", kind="nutritionist-creator",
            note="Instagram nutritionist/dietitian; PCOS + clean-supplement guidance",
        ),
        Community(
            name="Rujuta Diwekar", kind="nutritionist-author",
            note="food-first wisdom; 'ghee with dal and rice', eat local & seasonal, 'grandma knows best'; anti-supplement-dependence",
        ),
        Community(
            name="The Liver Doc", kind="doctor-influencer",
            note="Dr Cyriac Abby Philips; Citizens Protein Project; evidence-skeptic; Himalaya Liv.52 defamation row",
        ),
    ],
    cultural_references=[
        "the 'protein gap' narrative — 60% of urban India protein-deficient (LocalCircles/Country Delight, Feb 2026); Country Delight x HRX 'Mission Protein'",
        "the Citizens Protein Project — Liver Doc's team found ~70% of 36 Indian protein supplements had inaccurate protein info, 14% had toxins",
        "amino-spiking / proprietary-blend fear — trainers refilling tubs with cheaper weight-gainer; HealthKart QR authenticity seal as the antidote",
        "the gym-bro (MuscleBlaze, opaque white tubs) vs clean-label (OZiva, Plix, pastel DTC) identity split",
        "ghee-dal-rice food-first counter-narrative — 'my grandmother never took a pill', supplements as anxiety marketing",
        "beauty-supplement timeline anxiety — 'gave it 3 months, saw no result, switched' (biotin/collagen 8-12 week reality)",
        "doctor-prescribed deficiency cohort — Calcirol/Livogen/Shelcal as 'medicine to fix a number', not 'wellness lifestyle'",
        "protein bars as the mainstream on-ramp — ITC's Yogabar + 'less guilty than a Snickers' snacking",
    ],
    demographic_defaults={
        "urban_metro_male_lifter": {
            "city": "Bangalore", "occupation": "software engineer at a SaaS startup",
            "income_inr_annual": 1_800_000,
        },
        "urban_metro_female_wellness": {
            "city": "Mumbai", "occupation": "content marketer / designer",
            "income_inr_annual": 1_600_000,
        },
    },
    voice_samples=[
        # performance / obsessive
        "biozyme just works for me, 25g per scoop, no added sugar, i check the healthkart QR every time, not switching",
        "ON gold standard is the gold standard but for the price biozyme does 80% of the job honestly",
        # clean-label aspirant
        "looking for something plant based and clean, no maltodextrin filler, saw Lovneet recommend it on her reel",
        "not buying muscleblaze, that's gym bro stuff, i want something that fits my routine and looks good on the shelf",
        # results-chaser switcher
        "i intake this product from last 2 and half month, not a single change i have seen on my face and body",
        "giving it 3 months then switching, the nykaa reviews for HK vitals look better honestly",
        # doctor-triggered
        "doctor said my vitamin D is 8, take calcirol sachet once a week in milk, reorder on 1mg",
        # lapsed skeptic
        "used 60% of the tub then it just sat in the cupboard, didnt do anything, you still have to actually work out",
        "after that liver doc thing about 70% being fake i just stopped trusting all these protein brands",
        # snacker
        "tastes good and keeps me full, travel friendly, better than reaching for a biscuit at 4pm",
        # food-first purist
        "ghee dal rice did the job for generations, this is just marketing to make you anxious, eat real food",
    ],
    behavioral_priors=(
        # ⚠ Was "health_wellness_nutrition is identity-loaded..." — the raw slug as
        # the subject of a sentence every persona writer reads. Found by the
        # content preflight on 2026-08-22, live and unnoticed. Says "This
        # market" rather than the market name because _pack_brief prints
        # `CATEGORY: <market_name>` immediately above: no interpolation, so
        # the coupling is gone rather than given a better value.
        "This market is identity-loaded and trust-fractured. The "
        "shared backdrop: a loud 'protein gap' narrative (60% of urban India "
        "protein-deficient) pushing a vague 'I should take something' anxiety, "
        "set against a loud counter-narrative (the Liver Doc's finding that most "
        "Indian protein is mislabelled/adulterated, plus Rujuta Diwekar's "
        "food-first 'eat real food' message). Buyers cluster into near-separate "
        "sub-markets that barely share a shelf: the macros-tracking gym lifter "
        "(MuscleBlaze-loyal, certification-literate, value-calculating), the "
        "Insta-discovered clean-label woman (OZiva/Plix, 'plant-based' as filter, "
        "nutritionist-reel-led), the results-chasing serial switcher (gives every "
        "biotin/collagen brand 90 days then moves on no visible result), the "
        "doctor-prescribed deficiency cohort (Calcirol/Livogen, 'medicine not "
        "lifestyle', ignores every wellness-brand ad), the burned lapser (bought "
        "whey once, used 60%, never again), the convenience snacker (Yogabar as "
        "'snack not supplement'), and the food-first rejecter (ghee-dal-rice, "
        "actively resents the wellness shelf). Purchase splits between deliberate "
        "review-reading (500+ Nykaa reviews, macro math, HealthKart QR check) and "
        "impulsive Insta-reel / Blinkit-grab trial. On Instagram, the brand's "
        "face, palette and claim trigger an immediate stance-driven reaction; "
        "'clinically proven' and '50% better absorption' read as either a green "
        "flag or a red flag depending entirely on which sub-market is looking."
    ),
    default_chaos_distribution=_chaos(),
)
