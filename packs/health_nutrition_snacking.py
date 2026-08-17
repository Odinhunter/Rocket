"""Category artifact pack: health_nutrition_snacking — the world an Indian
urban buyer of protein, supplements and everyday snacks actually lives in.

WHY THIS PACK EXISTS, AND WHY IT IS NOT `health_wellness_nutrition`
------------------------------------------------------------------
The SuperYou PB Bar run (2026-08-13) returned FAILING/REBUILD at trust HIGH.
`target_id` had described the buyer correctly before the panel ran — "protein-
curious snackers who like chocolate/wafer formats" — and then the panel could
not contain one. `health_wellness_nutrition` holds 20 brands and ZERO
confectionery; every price point in it is a ₹1,250-4,800 tub. The ad's whole
pitch was "better than your 4pm chocolate bar", and the thing it asked the
buyer to trade up FROM did not exist in that buyer's world.

⚠ `health_wellness_nutrition` is NOT edited and NOT superseded. It is the
control: the only pack that has ever run a paid panel, and every existing
baseline came from it. It must stay byte-identical for the two to be
comparable. This pack is a SUPERSET of that world plus the everyday shelf the
same person chooses between.

⚠ THIS IS A NEW, UNVALIDATED CATEGORY under the category gate. Only
`health_wellness_nutrition` is validated. An out-of-category ad does not fail
gracefully — it emits a confident-but-wrong read. Nothing here changes that,
and a run against this pack is a first, not a certification.

PROVENANCE
----------
Curated 2026-08-14 from `docs/research/snacking_pack/` — six research lanes,
~2,100 lines, every number carrying a source URL, a date and the verbatim
sentence it came from. The rule the research was run under: no working URL
means the number does not exist. Aggregator pages (IMARC, Mordor, TechSci)
support nothing here. What could not be sourced is in `open_questions` rather
than filled with a plausible guess.

⚠ THE FABRICATION GUARD, and it is load-bearing. `price_points` below carries
ONLY prices read off a page that was actually opened. Deliberately absent, and
they must stay absent until someone verifies them: any ice cream price, any
Kurkure or Bingo price, the 13.2g/₹10 Dairy Milk (widely cited, never
openable — a listing rendered it as "132 Gm ... ₹10", a dropped decimal that
would have poisoned the pack), and any 2026 grammage-cut figure.

TWO PROJECTIONS — see the CategoryArtifactPack docstring
--------------------------------------------------------
Only seven fields reach a model. Everything from `market_stats` down is for
the brand-facing document and is consumed by nothing at runtime. That split is
why `cultural_references` and `behavioral_priors` below stay in CONSUMER
register — what is in the air for a shopper — while the citations, the
statistics and their sources live in the document layer. A persona should
sound like someone who buys snacks, not someone who reads Kantar.
"""

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos() -> ChaosDistribution:
    # Sits between the two packs it merges, and NOT where you would guess.
    #
    # The obvious move is to skew hard impulsive, because confectionery is the
    # textbook impulse category (packs/chocolate.py uses 0.35/0.45/0.20). The
    # research says don't: Kantar India finds 75%+ of purchases in exactly
    # these categories — chocolate, confectionery, cookies, salty snacks — are
    # now decided BEFORE entering a shop, with "the moment of impulse moved
    # from the store to the screen". The decision did not become deliberate;
    # it moved upstream, off the shelf and onto a feed.
    #
    # So: a touch more impulsive than the supplements pack (0.25/0.45/0.30),
    # well short of the old chocolate pack, and with the deliberate band kept
    # heavy because the supplement half of this world genuinely reads labels,
    # compares macros and checks authenticity seals.
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
        weighted=[(impulsive, 0.30), (moderate, 0.45), (deliberate, 0.25)]
    )


PACK = CategoryArtifactPack(
    category="health_nutrition_snacking",
    brand_landscape=[
        # ---------------------------------------------------------------
        # THE EVERYDAY SHELF — the half that did not exist before, and the
        # reason this pack was built. These are what the protein bar loses
        # to, most of the time, for most people.
        # ---------------------------------------------------------------
        BrandLandscapeEntry(
            name="Cadbury Dairy Milk", tier="mass",
            note="the default sweet thing in India; the single bar is the reference price everything else is judged against",
        ),
        BrandLandscapeEntry(
            name="Cadbury Silk", tier="mass-premium",
            note="softer Dairy Milk at a markup; the self-treat and everyday-gifting tier",
        ),
        BrandLandscapeEntry(
            name="Cadbury Milkinis", tier="mass",
            note="milk creme format launched 2025 aimed at younger buyers; entered at a higher coin than the old impulse point",
        ),
        BrandLandscapeEntry(
            name="Cadbury 5 Star", tier="mass",
            note="chewy caramel bar; the pocket-money and counter-grab tier",
        ),
        BrandLandscapeEntry(
            name="Cadbury Perk", tier="mass",
            note="the thin wafer chocolate; the lightest, cheapest chocolate habit",
        ),
        BrandLandscapeEntry(
            name="Cadbury Bournville", tier="premium",
            note="dark chocolate; the 'grown-up, less sweet' step-up within the same family",
        ),
        BrandLandscapeEntry(
            name="KitKat", tier="mass",
            note="wafer-and-chocolate finger; India is now its largest market in the world; the break-time ritual",
        ),
        BrandLandscapeEntry(
            name="Munch", tier="mass",
            note="the cheapest wafer chocolate bar; schoolbag and chai-shop staple",
        ),
        BrandLandscapeEntry(
            name="Snickers", tier="mass-premium",
            note="the peanut bar sold as almost-a-meal at the counter; the closest mainstream analogue to a protein bar's pitch",
        ),
        BrandLandscapeEntry(
            name="Parle-G", tier="mass",
            note="the floor of the entire packaged snack market; the glucose biscuit everyone has eaten and prices everything against",
        ),
        BrandLandscapeEntry(
            name="Britannia Good Day", tier="mass",
            note="cookie with visible cashew or butter; the tin-in-the-kitchen biscuit",
        ),
        BrandLandscapeEntry(
            name="Britannia Marie Gold", tier="mass",
            note="the plain tea biscuit; reads as the sensible, almost-not-a-treat option",
        ),
        BrandLandscapeEntry(
            name="Britannia 50-50", tier="mass",
            note="salty-sweet cracker; the savoury end of the biscuit shelf",
        ),
        BrandLandscapeEntry(
            name="Britannia Bourbon", tier="mass",
            note="chocolate cream sandwich biscuit; the childhood-indulgence biscuit",
        ),
        BrandLandscapeEntry(
            name="Britannia Milk Bikis", tier="mass",
            note="milk biscuit bought for children; the 'growing kids need it' purchase",
        ),
        BrandLandscapeEntry(
            name="Sunfeast Dark Fantasy", tier="mass-premium",
            note="molten-centre choco-filled cookie; the premium indulgent biscuit and a genuine dessert substitute",
        ),
        BrandLandscapeEntry(
            name="Oreo", tier="mass-premium",
            note="the imported-feeling cream sandwich; kids' pester-power biscuit",
        ),
        BrandLandscapeEntry(
            name="Lay's", tier="mass",
            note="potato chips; the default salty-snack reach in an office or a train",
        ),
        BrandLandscapeEntry(
            name="Kurkure", tier="mass",
            note="extruded masala snack; loud, spicy, shared from the packet",
        ),
        BrandLandscapeEntry(
            name="Bingo", tier="mass",
            note="chips and the bridges format; the challenger on the same rack",
        ),
        BrandLandscapeEntry(
            name="Haldiram's", tier="mass-premium",
            note="the namkeen benchmark; both the small travel pack and the family tin that lives on top of the fridge",
        ),
        BrandLandscapeEntry(
            name="Bikaji", tier="mass",
            note="ethnic namkeen and bhujia; the strong regional challenger with a family-pack skew",
        ),
        BrandLandscapeEntry(
            name="Balaji", tier="mass",
            note="regional wafers and namkeen; wins on price per gram where it is distributed",
        ),
        BrandLandscapeEntry(
            name="Amul", tier="mass",
            note="dairy and ice cream; the trusted-by-default cooperative brand",
        ),
        BrandLandscapeEntry(
            name="Kwality Wall's", tier="mass-premium",
            note="ice cream; separated from its old parent and now its own listed company, pushing single-serve premium formats",
        ),
        # ---------------------------------------------------------------
        # PERFORMANCE / GYM PROTEIN — carried from health_wellness_nutrition
        # ---------------------------------------------------------------
        BrandLandscapeEntry(
            name="MuscleBlaze", tier="mass-premium",
            note="HealthKart house brand; Biozyme Performance Whey is a leading serious-lifter pick",
        ),
        BrandLandscapeEntry(
            name="Optimum Nutrition", tier="premium",
            note="ON Gold Standard; the imported aspirational tier",
        ),
        BrandLandscapeEntry(
            name="AS-IT-IS", tier="d2c-disruptor",
            note="unflavoured raw whey concentrate; 'tastes like milk powder' but the cheapest per day; student/beginner value pick",
        ),
        BrandLandscapeEntry(
            name="MyProtein", tier="d2c-disruptor",
            note="imported whey / creatine; sale-event buying",
        ),
        BrandLandscapeEntry(
            name="Fast&Up", tier="mass-premium",
            note="effervescent tablets, plant protein; urban functional",
        ),
        # ---------------------------------------------------------------
        # PLANT / LIFESTYLE / FUNCTIONAL WELLNESS
        # ---------------------------------------------------------------
        BrandLandscapeEntry(
            name="OZiva", tier="mass-premium",
            note="plant protein and collagen builder; Instagram-led clean-label women's wellness",
        ),
        BrandLandscapeEntry(
            name="Plix", tier="d2c-disruptor",
            note="The Plant Fix; vegan collagen and plant protein; content-first, aimed young",
        ),
        BrandLandscapeEntry(
            name="Power Gummies", tier="d2c-disruptor",
            note="biotin hair and nails gummies; the gateway beauty-supplement",
        ),
        BrandLandscapeEntry(
            name="Setu", tier="mass-premium",
            note="marine collagen and hair vitamins; 'fishy aftertaste if not masked'",
        ),
        BrandLandscapeEntry(
            name="HK Vitals", tier="mass-premium",
            note="HealthKart house wellness brand; value collagen and multivitamins",
        ),
        BrandLandscapeEntry(
            name="Wellbeing Nutrition", tier="premium",
            note="'slow' clean-label capsules and melts; premium functional",
        ),
        BrandLandscapeEntry(
            name="Carbamide Forte", tier="mass",
            note="marketplace-native value multivitamin and supplements",
        ),
        BrandLandscapeEntry(
            name="TrueBasics", tier="premium",
            note="premium clinical-leaning supplements",
        ),
        # ---------------------------------------------------------------
        # BETTER-FOR-YOU SNACKING — the bridge, and the contested ground
        # ---------------------------------------------------------------
        BrandLandscapeEntry(
            name="Yogabar", tier="mass-premium",
            note="protein bars, wafers and oats; 'snack not supplement' framing; majority-held by a large listed foods group",
        ),
        BrandLandscapeEntry(
            name="RiteBite Max Protein", tier="mass-premium",
            note="protein bars and cookies; 'guilt-free snack' framing; the one better-for-you brand that reliably sells a single bar",
        ),
        BrandLandscapeEntry(
            name="The Whole Truth", tier="premium",
            note="dates-sweetened, few recognisable ingredients; radical-transparency premium bar, sold in boxes rather than singles",
        ),
        # ---------------------------------------------------------------
        # DOCTOR-PRESCRIBED / PHARMACY
        # ---------------------------------------------------------------
        BrandLandscapeEntry(
            name="Calcirol", tier="pharmacy",
            note="vitamin-D sachet; doctor-prescribed, mixed in milk; 'the vitamin-D one'",
        ),
        BrandLandscapeEntry(
            name="Livogen", tier="pharmacy",
            note="iron tablet; 'the iron one'; pregnancy and anaemia; constipation gripe",
        ),
        BrandLandscapeEntry(
            name="Shelcal", tier="pharmacy",
            note="calcium and vitamin-D; the gynae and ortho postpartum default",
        ),
        BrandLandscapeEntry(
            name="Uprise-D3", tier="pharmacy",
            note="alternative prescribed vitamin-D3 sachet or drops",
        ),
    ],
    # ⚠ EVERY PRICE BELOW WAS READ OFF A PAGE THAT WAS OPENED. See the module
    # docstring for what is deliberately missing and must not be added from
    # memory. Observation dates are in `price_architecture` in the document
    # layer, deliberately not here — this field feeds a prompt and should
    # carry the shopper's mental price, not an audit trail.
    price_points=[
        # --- the everyday shelf ---
        PricePoint(item="Parle-G 90g pack", price_inr="₹10", channel="kirana / any grocery"),
        PricePoint(item="Cadbury Dairy Milk 24g bar", price_inr="₹17", channel="kirana / pharmacy counter"),
        PricePoint(item="Cadbury Dairy Milk Milkinis 17g", price_inr="₹20", channel="kirana / supermarket"),
        PricePoint(item="Lay's India's Magic Masala 90g", price_inr="₹35", channel="kirana / supermarket"),
        PricePoint(item="Britannia Marie Gold 213.5g", price_inr="₹40", channel="supermarket / grocery"),
        PricePoint(item="Britannia Good Day Cashew 250g", price_inr="₹55", channel="supermarket / grocery"),
        PricePoint(item="Haldiram's Aloo Bhujia 400g family pack", price_inr="₹110", channel="supermarket / quick commerce"),
        PricePoint(item="KitKat 126g multipack", price_inr="₹160", channel="supermarket / online"),
        PricePoint(item="Sunfeast Dark Fantasy Choco Fills 230g", price_inr="₹205", channel="supermarket / quick commerce"),
        PricePoint(item="Cadbury Oreo 459.25g pack", price_inr="₹283", channel="supermarket / online"),
        PricePoint(item="Cadbury Dairy Milk Silk 140.5g", price_inr="₹399", channel="supermarket / quick commerce"),
        # --- better-for-you snacking ---
        PricePoint(item="RiteBite Max Protein Roots bar 45g, single", price_inr="₹80", channel="brand website / quick commerce"),
        PricePoint(item="Yogabar Power Up bar 70g, 20g protein", price_inr="₹125", channel="brand website"),
        PricePoint(item="The Whole Truth protein bar 52g, sold in a box of 8", price_inr="₹836 the box (about ₹105 a bar)", channel="brand website"),
        PricePoint(item="Yogabar protein wafer, box of 10", price_inr="₹399", channel="brand website / online"),
        PricePoint(item="Yogabar 20g Protein Bar variety pack of 5", price_inr="₹625", channel="online / quick commerce"),
        PricePoint(item="The Whole Truth Protein Bar, single", price_inr="₹96", channel="quick commerce"),
        # --- supplements and pharmacy ---
        PricePoint(item="MuscleBlaze Biozyme Performance Whey 1kg chocolate", price_inr="₹2,699", channel="HealthKart"),
        PricePoint(item="MuscleBlaze Beginner's Whey 1kg", price_inr="₹1,599", channel="online marketplace"),
        PricePoint(item="Optimum Nutrition Gold Standard 2.27kg", price_inr="₹4,200-4,800", channel="online marketplace"),
        PricePoint(item="AS-IT-IS Whey Concentrate 1kg unflavoured", price_inr="about ₹1,250", channel="online marketplace / brand website"),
        PricePoint(item="OZiva Plant-Based Collagen Builder", price_inr="₹1,499", channel="beauty marketplace"),
        PricePoint(item="OZiva Plant Protein 1kg", price_inr="about ₹1,699", channel="beauty marketplace / brand website"),
        PricePoint(item="Plix Plant Protein vanilla 1kg", price_inr="about ₹2,000", channel="beauty marketplace / brand website"),
        PricePoint(item="Power Gummies Hair & Nails biotin, 60-day", price_inr="₹699", channel="online marketplace / brand website"),
        PricePoint(item="HK Vitals Skin Radiance Collagen", price_inr="about ₹599-899", channel="HealthKart"),
        PricePoint(item="Calcirol vitamin-D sachet", price_inr="about ₹35 a sachet", channel="pharmacy"),
        PricePoint(item="Livogen XT iron tablets, 10s", price_inr="about ₹80", channel="pharmacy"),
    ],
    # ⚠ Keep these notes lowercase and generic — render.py feeds this list into
    # _vocab_tokens, so every TitleCase word here joins the set of names a
    # persona is allowed to say and weakens the invented-artifact check.
    #
    # ⚠ The note on each channel now carries WHAT THE DECISION IS LIKE there,
    # not just what it stocks. That is the finding this pack exists to encode:
    # the same person shops three different ways depending on the moment.
    retail_channels=[
        "kirana counter — the shop downstairs; single bars, single biscuit "
        "packs, the small-coin price points that exist nowhere else; bought "
        "in seconds, often on the way past, often on a running tab",
        "supermarket aisle — the weekly or monthly shop; family packs and "
        "tins; a planned list with room for one or two additions",
        "quick commerce — ten-minute delivery; a top-up mission, not a browse; "
        "the shopper arrives already knowing what they want, searches for it, "
        "and is gone in under five minutes; larger and more premium packs "
        "than the shop downstairs, and the smallest coin packs are simply "
        "absent",
        "online marketplace — everything; the price-comparison and "
        "review-reading surface for tubs, boxes and multipacks; not where a "
        "single bar is bought",
        "HealthKart — sports nutrition specialist; whey, gainers, creatine; "
        "authenticity-seal scanning",
        "beauty marketplace — beauty and personal care first; collagen, "
        "biotin, hair and skin supplements, clean-label wellness. not where "
        "whey, gainers or protein bars are bought",
        "pharmacy — prescribed deficiency supplements, doctor-named brands, "
        "refills of a course; also one of the few counters selling genuine "
        "single-serve chocolate",
        "brand website — the brand's own store; subscription and launches; "
        "for better-for-you bars this is usually a BOX, rarely a single",
        "office pantry or canteen — free or near-free, immediate, hot; the "
        "thing an afternoon snack is really competing with at a desk",
        "gym counter — post-workout, captive, marked up",
        "airport and highway stop — captive pricing, travel formats, the "
        "namkeen tin and the counter chocolate",
        "street cart and chai stall — samosa, vada pav, cutting chai; hot, "
        "immediate, cheaper than almost anything packaged",
    ],
    communities=[
        Community(
            name="Tarun Gill", kind="youtuber",
            note="supplement reviews and authenticity exposes; the serious lifter's reference",
        ),
        Community(
            name="Guru Mann", kind="youtuber",
            note="credentialed fitness and nutrition plans",
        ),
        Community(
            name="Fittuber", kind="youtuber",
            note="product-ingredient debunks; 'is this brand clean' reviews",
        ),
        Community(
            name="FoodPharmer", kind="creator-activist",
            note="turn-the-pack-over label reading; drove a mainstream habit of checking the ingredient list and calling out claims",
        ),
        Community(
            name="Lovneet Batra", kind="nutritionist-creator",
            note="clean-label women's wellness trigger",
        ),
        Community(
            name="Rashi Chowdhary", kind="nutritionist-creator",
            note="PCOS and clean-supplement guidance",
        ),
        Community(
            name="Rujuta Diwekar", kind="nutritionist-author",
            note="food-first wisdom; eat local and seasonal; anti-supplement-dependence",
        ),
        Community(
            name="The Liver Doc", kind="doctor-influencer",
            note="evidence-skeptic; ran the lab testing that found widespread mislabelling in Indian protein powders",
        ),
        Community(
            name="office group chats", kind="whatsapp",
            note="where the 4pm order gets pooled and where someone's new snack gets passed around",
        ),
        Community(
            name="family WhatsApp groups", kind="whatsapp",
            note="where sugar, diabetes and what-the-kids-are-eating get argued about",
        ),
    ],
    # ⚠ CONSUMER REGISTER ONLY. These are things in the air for a shopper, not
    # citations. The statistics and their sources live in the document layer
    # below, on purpose — a persona should sound like someone who buys snacks,
    # not someone who reads market research.
    cultural_references=[
        "shrinkflation as betrayal — the pack costs the same and holds less, "
        "the bag is still puffed up with air, and the standard pack sizes that "
        "used to be law are gone; people notice the biscuit count, not the price",
        "the turn-the-pack-over habit — checking the ingredient list and the "
        "sugar position, driven by label-reading creators, and mostly performed "
        "on other people's food rather than one's own",
        "'no added sugar' read as a warning about taste rather than a promise "
        "about health — the learned expectation that the healthy version is the "
        "disappointing version",
        "protein on everything — protein biscuits, protein chips, protein "
        "water; the claim has spread far enough that it now reads as packaging "
        "rather than as a reason",
        "the doubt about whether the protein number on the pack is real at all, "
        "after lab testing found widespread mislabelling",
        "food-first counter-narrative — ghee, dal, rice and 'my grandmother "
        "never took a pill'; supplements as anxiety sold back to you",
        "the mithai-versus-chocolate question every festival — what you gift, "
        "what you keep, and what sits in the fridge for a week afterwards",
        "diabetes in the family as the thing that actually changes a shelf; a "
        "reading on a report does more than any ad",
        "the ten-minute app as both convenience and small guilt — 'I ordered "
        "ice cream at 11pm because I could'",
        "the desk drawer and the office jar as real places with real politics — "
        "what you keep for yourself and what gets eaten by everyone",
        "growing kids need it — the household argument that justifies the "
        "biscuit and the milk drink, made by whoever does the monthly shop",
        "gym-bro tubs versus pastel clean-label pouches as two different "
        "identities that barely share a shelf",
        "the annual health check as a trigger event — a number on a report "
        "starting a diet, a habit, or a switch",
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
    # ⚠ Carried from health_wellness_nutrition, where they came from genuine
    # voice research (Amazon / Nykaa / HealthKart / Quora / Practo reviews).
    # They cover the SUPPLEMENT half of this world well and the everyday-snack
    # half not at all — see `open_questions`. The snacking voice lane failed to
    # collect verbatim quotes (every consumer platform blocks automated
    # fetching) and DID NOT fabricate replacements, which was the right call:
    # an invented voice sample is indistinguishable from a real one downstream.
    voice_samples=[
        "biozyme just works for me, 25g per scoop, no added sugar, i check the healthkart QR every time, not switching",
        "ON gold standard is the gold standard but for the price biozyme does 80% of the job honestly",
        "looking for something plant based and clean, no maltodextrin filler, saw a nutritionist recommend it on her reel",
        "not buying muscleblaze, that's gym bro stuff, i want something that fits my routine and looks good on the shelf",
        "i intake this product from last 2 and half month, not a single change i have seen on my face and body",
        "giving it 3 months then switching, the reviews for the other one look better honestly",
        "doctor said my vitamin D is 8, take calcirol sachet once a week in milk, reorder on the pharmacy app",
        "used 60% of the tub then it just sat in the cupboard, didnt do anything, you still have to actually work out",
        "after that whole thing about most of them being fake i just stopped trusting all these protein brands",
        "tastes good and keeps me full, travel friendly, better than reaching for a biscuit at 4pm",
        "ghee dal rice did the job for generations, this is just marketing to make you anxious, eat real food",
    ],
    behavioral_priors=(
        "This is one shelf with two halves that barely speak to each other, and "
        "the buyer moves between them without noticing. The supplement half is "
        "identity-loaded and trust-fractured: a loud protein-gap narrative "
        "pushing a vague 'I should be taking something', set against a loud "
        "counter-narrative that most Indian protein is mislabelled and that "
        "real food did the job for generations. The everyday half — chocolate, "
        "biscuits, namkeen, chips, ice cream — is where almost all the volume "
        "actually is, at coin prices, and it is what any better-for-you product "
        "is really competing with.\n\n"
        "THE FOUR THINGS THAT MOST CHANGE HOW SOMEONE HERE BEHAVES.\n\n"
        "First, the snack decision has moved off the shelf. Most purchases in "
        "these categories are settled before the shopper reaches any shop or "
        "opens any app — decided on a feed, in a conversation, or by a habit "
        "already formed. The counter-grab still happens, but it is no longer "
        "where most choices are made. On a ten-minute app the shopper arrives "
        "knowing what they want, searches for it, and is gone in under five "
        "minutes; they do not browse. Anything that has to be discovered "
        "during the purchase has already lost.\n\n"
        "Second, the coin price and the box price are two different worlds, "
        "and better-for-you products live in the second one. Everyday snacking "
        "runs on single units at small round prices; the shop downstairs is "
        "the only place several of those prices exist at all, and they are "
        "simply absent from the apps. Better-for-you bars are mostly not sold "
        "as singles — they come as boxes of five to twelve. So the choice a "
        "health bar actually asks for is not 'this bar instead of that bar'; "
        "it is a considered, planned, boxed purchase instead of an unplanned "
        "coin. A person can want the bar and still balk at the size of the "
        "decision, and that hesitation is about commitment, not about health.\n\n"
        "Third, a health promise changes what people expect food to TASTE "
        "like, and often not helpfully. 'No added sugar', 'guilt-free' and "
        "'high protein' are read by many buyers as a warning that the thing "
        "will be disappointing — a learned reflex from years of healthy "
        "versions that were worse. In a treat moment that reflex can repel the "
        "very person the product was built for. It does not repel everyone: "
        "some read the same words as permission, and the reflex is learned "
        "rather than universal. Which way it lands is exactly what the "
        "creative decides.\n\n"
        "Fourth, price rises arrive as less food rather than more money. At "
        "the smallest price points the number on the pack does not change; the "
        "pack shrinks. People experience this as being quietly cheated, notice "
        "it through the count rather than the till, and respond by moving to "
        "loose or unbranded product rather than by paying more.\n\n"
        "Occasions, not demographics, do most of the work here. The same "
        "person is a different buyer at 4pm at a desk, at 11pm in bed, "
        "post-workout, on a station platform, and doing the monthly shop for a "
        "household — and in several of those moments the real competitor is "
        "the canteen samosa, the office jar, or eating nothing at all. Buying "
        "for other people, especially children, is a large share of household "
        "snacking and follows completely different rules from buying for "
        "oneself. Most of the time, most of these people buy the everyday "
        "thing; a persona whose whole world is protein cannot explain why.\n\n"
        "On a feed, the brand's face, palette and claim trigger an immediate "
        "stance-driven reaction. 'Clinically proven', '20g protein' and 'no "
        "added sugar' read as a green flag or a red flag depending entirely on "
        "which half of this shelf the viewer lives on — and a claim that "
        "matches what a mainstream incumbent already offers does the "
        "comparison work for the incumbent."
    ),
    default_chaos_distribution=_chaos(),

    # =====================================================================
    # THE DOCUMENT PROJECTION — reaches no prompt. For the brand-facing
    # artifact and for wiring not yet built. Every entry carries its source.
    # =====================================================================
    market_stats=[
        {
            "claim": "Indian adults who snack once a day or more",
            "value": "41% (25% once, 12% twice, 4% three or more)",
            "source": "Mondelez / Mintel, State of Snacking 2026, p.12",
            "period": "fieldwork Jan 2025, base 3,000 Indian adults 18+",
            "tier": "primary",
            "caution": "Do NOT compare with the US 66%. India's base is all adults, "
                       "offline face-to-face; other markets' bases are recent snackers, "
                       "online. The comparison is invalid and checkable.",
        },
        {
            "claim": "Indian snack consumers who replace a meal with snacks",
            "value": "22%",
            "source": "Mondelez / Mintel, State of Snacking 2026, p.40",
            "period": "base 2,632 Indian adults 18+, Dec 2025",
            "tier": "primary",
        },
        {
            "claim": "Purchases in traditional impulse categories (chocolate, "
                     "confectionery, cookies, salty snacks, fizzy drinks) that are "
                     "planned BEFORE entering a store",
            "value": "over 75%",
            "source": "Kantar India — Sreyoshi Maitra, EVP Insights, 9 Jul 2025",
            "period": "2025",
            "tier": "primary-but-unmethodologised",
            "caution": "⚠ THE MOST LOAD-BEARING AND LEAST VERIFIABLE NUMBER IN THIS PACK. "
                       "Kantar names no panel, sample, period or underlying report. "
                       "Attribute to Kantar India; never state as an industry constant. "
                       "Worth asking Kantar directly before a brand's team asks us.",
        },
        {
            "claim": "Quick-commerce session length and conversion vs e-retail",
            "value": "under 5 minutes vs over 10; 8x visit-to-order conversion; "
                     "fewer product pages per order",
            "source": "Bain & Company x Flipkart, How India Shops Online 2026",
            "period": "CY2025",
            "tier": "primary",
        },
        {
            "claim": "E-commerce share of FMCG — urban India vs top 8 metros",
            "value": "6% urban India; 18% top 8 metros; quick commerce is over "
                     "three-fourths of that e-commerce",
            "source": "NielsenIQ, 13 Mar 2026",
            "period": "OND 2025",
            "tier": "primary",
            "caution": "The derived ~13-14% q-commerce share of metro FMCG is arithmetic "
                       "on two sourced numbers and is a FLOOR, not a midpoint.",
        },
        {
            "claim": "Quick commerce share of Britannia's online business",
            "value": "about 70%, expected to reach 85%; e-commerce is 6% of its "
                     "domestic business",
            "source": "Britannia FY26 earnings call, reported by Storyboard18",
            "period": "FY26",
            "tier": "company-commentary-via-press",
        },
        {
            "claim": "Traditional trade share of out-of-home salty snack value — RISING",
            "value": "31% to 35%",
            "source": "Kantar Worldpanel, OOH Barometer",
            "period": "Q1 2023 to Q1 2024",
            "tier": "primary",
            "caution": "Oldest data in the pack. Cuts against the 'q-commerce is eating "
                       "kirana' narrative: the occasion splits the channel.",
        },
        {
            "claim": "Where snacks are actually EATEN vs where value is transacted",
            "value": "consumption location 78-94% at home (urban); Kantar's 71% "
                     "'out-of-home' is a purchase-channel value share",
            "source": "J Nutr 2023; Kantar Worldpanel OOH Barometer",
            "period": "2023-24",
            "tier": "primary",
            "caution": "Both are correct and they measure different things. Reading "
                       "'71% out-of-home' as 'eaten on the street' is the trap.",
        },
        {
            "claim": "There is NO national Indian daypart curve",
            "value": "urban Vizag 96.7% evening / 13.4% afternoon; urban Sonipat "
                     "85.2% morning / 31.8% evening",
            "source": "J Nutr 2023, Table 2",
            "period": "2023",
            "tier": "primary",
            "caution": "Two Indian cities, nearly inverted. Daypart must be a REGIONAL "
                       "persona variable, never a national constant.",
        },
        {
            "claim": "Savoury snacks market size and organised share",
            "value": "₹796bn FY23E growing ~11% to ₹1,217bn FY27F; organised "
                     "only 57%. Packaged food overall is 81% UNORGANISED",
            "source": "Frost & Sullivan, Feb 2024, in the SEBI-filed Gopal Snacks "
                      "IPO industry report",
            "period": "FY2023E",
            "tier": "primary",
            "caution": "FY23 estimates published Feb 2024 — use for structure and "
                       "relative size, not as a current-year figure.",
        },
        {
            "claim": "Organised market shares — ethnic savouries and western snacks",
            "value": "ethnic: Haldiram 36%, Balaji 9%, Bikaji 9%. western: "
                     "PepsiCo 22%, ITC 13%, Balaji 10%",
            "source": "Frost & Sullivan, Feb 2024",
            "period": "FY2023E",
            "tier": "primary",
        },
        {
            "claim": "Distribution reach — availability is the binding constraint",
            "value": "Britannia 2.87m direct outlets against a ~9m category "
                     "universe (6.5m direct+indirect); ITC ~7m outlets, over a "
                     "third direct; Bikaji 0.33m direct, 1.23m total",
            "source": "Britannia Q4 FY25 call; ITC Report and Accounts 2025; "
                      "Bikaji Q1 FY26 investor presentation",
            "period": "FY25 / Jun 2025",
            "tier": "primary",
        },
        {
            "claim": "GST cut on snack foods",
            "value": "namkeen, chocolate, biscuits, extruded snacks and ice cream "
                     "cut from 12% or 18% to 5%",
            "source": "56th GST Council, Ministry of Finance",
            "period": "effective 22 Sep 2025",
            "tier": "primary",
            "caution": "It BROKE market-share measurement — Britannia has stopped "
                       "publishing its biscuit share (Nielsen panel rebuild plus GST "
                       "dual pricing). Do not quote a 2025-26 biscuit share for anyone.",
        },
        {
            "claim": "Who decides household snacking",
            "value": "youth 34%, children 27%, adults 22%, seniors 12%; "
                     "regionally East 40% to South 32%",
            "source": "Godrej Yummiez consumer report via InQognito, n=2,004, 16 cities",
            "period": "2025-26",
            "tier": "brand-commissioned",
            "caution": "The eater is frequently not the chooser.",
        },
        {
            "claim": "ICMR-NIN on fortifying processed food",
            "value": "\"If the foods are ultra-processed or high in fat/sugar/salt, "
                     "then enriching them with nutrients or fortifying cannot make "
                     "them wholesome or healthy.\"",
            "source": "ICMR-NIN, Dietary Guidelines for Indians 2024, p.113",
            "period": "2024",
            "tier": "primary",
            "caution": "The national nutrition authority pre-emptively rejecting the "
                       "added-protein playbook. Guideline 9 also says avoid protein "
                       "supplements to build muscle mass.",
        },
        {
            "claim": "ICMR-NIN HFSS threshold for added sugar in solids",
            "value": "3g per 100g",
            "source": "ICMR-NIN, Dietary Guidelines for Indians 2024, Table 15.1",
            "period": "2024",
            "tier": "primary",
            "caution": "At this threshold essentially every sweet packaged snack — "
                       "INCLUDING the healthy bars — is HFSS by the authority's own "
                       "definition. Added sugars explicitly include jaggery and honey, "
                       "which matters for 'natural sweetener' positioning.",
        },
        {
            "claim": "The protein-gap statistic is industry-funded",
            "value": "Right To Protein states it is \"powered by the U.S. Soybean "
                     "Export Council\". The academic position is that Indian protein "
                     "QUANTITY is roughly adequate (~1g/kg/day) and the real deficit "
                     "is QUALITY, with about a third of a sedentary rural population "
                     "at risk",
            "source": "righttoprotein.com; Swaminathan, Vaz & Kurpad, Br J Nutr 2012",
            "period": "2012-2026",
            "tier": "primary",
            "caution": "⚠ NEVER repeat '73% of Indians are protein deficient' as fact. "
                       "The health_wellness_nutrition pack currently carries a claim "
                       "from this same family and it should be re-checked.",
        },
        {
            "claim": "Health framing vs taste framing on identical food",
            "value": "taste-focused labels increased selection 29% over "
                     "health-focused labels, mediated by taste expectations",
            "source": "Turnwald et al., Psychological Science 2019 — preregistered, "
                      "137,842 diner decisions, five sites",
            "period": "2019",
            "tier": "primary",
            "caution": "⚠ A WELL-EVIDENCED MECHANISM WITH UNESTABLISHED INDIAN "
                       "MAGNITUDE AND DIRECTION. The unhealthy=tasty intuition is "
                       "culturally learned and REVERSES in France. There is no "
                       "India-specific experimental evidence either way, and no study "
                       "anywhere isolates a 'no added sugar' claim. A hypothesis to "
                       "test, not a finding to assert.",
        },
        {
            "claim": "Indian label-reading behaviour",
            "value": "only a small proportion use labels consistently; \"taste, "
                     "price, peer influence, media exposure, and celebrity "
                     "endorsements\" are stronger drivers than labels",
            "source": "Pahlani et al., Global Health Action 2025 — scoping review "
                      "of 32 India studies, 2014-2024",
            "period": "2025",
            "tier": "primary",
            "caution": "Cuts BOTH ways: if labels are read less, both the positive "
                       "effect of a health claim and the negative taste effect may be "
                       "smaller in India than the US literature implies.",
        },
        {
            "claim": "Front-of-pack labelling status in India",
            "value": "STILL NOT LAW. The Indian Nutrition Rating star scheme has "
                     "been draft since Sept 2022. The Supreme Court gave the Union "
                     "two weeks on 13 Aug 2026",
            "source": "Supreme Court proceedings via Bar and Bench, LiveLaw",
            "period": "as at 14 Aug 2026",
            "tier": "primary",
            "caution": "⚠ LIVE AND MOVING. Re-check before showing any client.",
        },
    ],
    # ⚠ THE OCCASIONS ARE OURS, NOT ANYONE'S PUBLISHED SEGMENTATION, AND THEIR
    # SIZES ARE NOT KNOWN. Lane 2 searched specifically and established that no
    # published source sizes Indian snacking occasions — that data sits in
    # Kantar's commercial occasion panel and paywalled Mintel reports. Any
    # weight here is a MODELLING ASSUMPTION and must be labelled one. They are
    # carried at equal weight today because that is what the generator did, by
    # accident of its loop rather than by any claim about the market.
    occasions=[
        {
            "key": "desk_slump_4pm",
            "moment": "the afternoon dip at a desk — hungry, flagging, hours from dinner",
            "competes_with": "biscuits from the office jar, a chocolate bar, canteen "
                             "samosa or vada pav, chai, a banana, or nothing",
            "decided_by": "speed, taste, what is within arm's reach, mild guilt",
            "channel": "office pantry, the desk drawer stocked earlier, the shop downstairs",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "late_night_craving",
            "moment": "late evening, scrolling in bed, wants something sweet",
            "competes_with": "chocolate, ice cream, leftover mithai, biscuits, nothing",
            "decided_by": "craving, what is already in the fridge, ten-minute delivery",
            "channel": "quick commerce, the kitchen cupboard",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "post_workout",
            "moment": "straight after the gym, before a proper meal",
            "competes_with": "a whey shake, eggs, a banana, dal-chawal at home, nothing",
            "decided_by": "protein per serving, habit, what the trainer said",
            "channel": "gym counter, specialist online, the gym bag",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "breakfast_on_the_run",
            "moment": "leaving late, will not sit down to eat",
            "competes_with": "toast, poha, cereal, a bought sandwich, coffee alone, skipping",
            "decided_by": "one hand, no crumbs, lasts until mid-morning",
            "channel": "kitchen counter, station kiosk, the monthly grocery order",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "guilt_free_treat",
            "moment": "a weekend or a bad day — wants a treat but not to feel bad",
            "competes_with": "dark chocolate, a 'healthy' dessert, regular chocolate "
                             "anyway, fruit",
            "decided_by": "permission — whether it reads as a treat or as a compromise",
            "channel": "quick commerce, supermarket aisle, a cafe",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "travel_and_commute",
            "moment": "airport, long drive, or a long commute with no meal in sight",
            "competes_with": "a bought sandwich, chips, nuts, counter chocolate, nothing",
            "decided_by": "portability, shelf life, what the counter is selling",
            "channel": "airport store, highway stop, packed from home",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "daily_health_routine",
            "moment": "a standing daily habit someone has decided to keep",
            "competes_with": "a powder, gummies, a multivitamin, real food, nothing",
            "decided_by": "routine, whether it seems to be working, cost per day",
            "channel": "subscription, specialist online, the pharmacy",
            "weight": "unknown — modelling assumption",
        },
        {
            "key": "household_stock_up",
            "moment": "the monthly or weekly shop — buying for other people too",
            "competes_with": "biscuit packs, namkeen, cereal, whatever the children will eat",
            "decided_by": "price per unit, family acceptance, keeps in the cupboard",
            "channel": "supermarket, online grocery, the local kirana",
            "weight": "unknown — modelling assumption",
            "note": "⚠ The eater is frequently not the chooser here — see market_stats.",
        },
    ],
    journeys=[
        {
            "stage": "trigger",
            "what_happens": "Happens off-channel, on a screen, and usually days before "
                            "the purchase. Most choices in these categories are settled "
                            "before the shopper reaches a shop or opens an app.",
            "source": "Kantar India 2025; Bain x Flipkart HISO 2026",
        },
        {
            "stage": "consideration",
            "what_happens": "Compressed to almost nothing on quick commerce — under "
                            "five minutes, search-led, few product pages viewed. Longer "
                            "and more comparison-driven on marketplaces for tubs and boxes.",
            "source": "Bain x Flipkart HISO 2026",
        },
        {
            "stage": "purchase",
            "what_happens": "Eight times the visit-to-order conversion of ordinary "
                            "e-retail. The single-coin pack is a kirana object and is "
                            "absent from the apps entirely.",
            "source": "Bain x Flipkart HISO 2026; Britannia FY26 commentary",
        },
        {
            "stage": "repeat_or_lapse",
            "what_happens": "No published trial-to-repeat data exists for Indian D2C or "
                            "better-for-you snack brands. Platform retention is a "
                            "different construct and must not be presented as brand repeat.",
            "source": "lane 3 open question",
        },
    ],
    price_architecture=[
        {
            "rung": "₹5",
            "what_it_buys": "the defended floor — small biscuit and namkeen packs only. "
                            "No mainstream chocolate bar remains here.",
            "mechanism": "held by shrinking the pack, never by moving the price",
        },
        {
            "rung": "₹10",
            "what_it_buys": "the pivot of the entire shelf — Parle-G 90g, the impulse "
                            "chocolate unit, a cutting chai. Reads as 'one small thing', "
                            "not as a decision.",
            "mechanism": "at this point and below, price cannot move; grammage does. "
                         "₹5 and ₹10 packs are roughly half of Britannia's mix.",
        },
        {
            "rung": "₹20",
            "what_it_buys": "the new-launch rung — a 2025 chocolate format entered here "
                            "at 17g rather than at the old coin point",
        },
        {
            "rung": "₹30-40",
            "what_it_buys": "one proper pack — a 90g chips packet, a 213g biscuit pack. "
                            "Where price increases are actually taken.",
        },
        {
            "rung": "₹50-60",
            "what_it_buys": "the family or sharing pack — and this rung is being vacated "
                            "upward as family packs move past ₹100",
        },
        {
            "rung": "₹80-110",
            "what_it_buys": "where better-for-you BEGINS and mainstream ends. The "
                            "cheapest single protein bar costs about the same as a 400g "
                            "family tin of namkeen.",
        },
        {
            "rung": "₹100+",
            "what_it_buys": "premium indulgence and the protein-bar mainstream. A single "
                            "better-for-you bar sits at the same rung as an entire "
                            "premium biscuit pack or a large sharing chocolate bar.",
        },
        {
            "rung": "THE TRADE-UP GAP",
            "what_it_buys": "about 2.5x per gram and roughly 5x per unit against a "
                            "mainstream chocolate bar. But most better-for-you brands do "
                            "not sell singles at all — boxes of 5 to 12 — so the real "
                            "minimum ticket is ₹400-950 against a ₹10-17 coin.",
            "mechanism": "⚠ THE CENTRAL FINDING. A protein bar is not competing on the "
                         "impulse shelf; it was never on it. At ₹80-125 it competes "
                         "with a family tin of namkeen or a premium biscuit pack — a "
                         "household's snack, not one person's treat. Different occasion, "
                         "different mental account, and price is the reason.",
        },
        {
            "rung": "SHRINKFLATION",
            "what_it_buys": "nothing — this is the mechanism, not a rung",
            "mechanism": "Standard pack sizes stopped being mandated in Oct 2022. At the "
                         "coin points the pack shrinks instead of the price moving, and "
                         "buyers respond by switching to loose or unbranded product "
                         "rather than paying more. They experience inflation as less "
                         "food, and as being quietly cheated.",
        },
    ],
    sources=[
        {"name": "Mondelez / Mintel, State of Snacking 2026", "tier": "primary",
         "used_for": "snacking frequency, meal replacement, daypart, social trial"},
        {"name": "Kantar India — impulse buying is now planned (Jul 2025)",
         "tier": "primary-but-unmethodologised",
         "used_for": "the 75% pre-planned finding — the pack's most load-bearing claim"},
        {"name": "Kantar Worldpanel OOH Barometer", "tier": "primary",
         "used_for": "out-of-home value share, traditional trade gaining in salty snacks"},
        {"name": "Bain & Company x Flipkart, How India Shops Online 2026",
         "tier": "primary",
         "used_for": "quick-commerce sizing, session length, conversion, basket"},
        {"name": "NielsenIQ, GST 2.0 transition release (Mar 2026)", "tier": "primary",
         "used_for": "e-commerce share of FMCG, urban vs metro"},
        {"name": "Eternal (Blinkit) Q1FY27 and Swiggy (Instamart) Q1FY27 letters",
         "tier": "primary", "used_for": "quick-commerce scale, dark stores, AOV, retention"},
        {"name": "Frost & Sullivan Feb 2024, in the Gopal Snacks IPO industry report",
         "tier": "primary", "used_for": "savoury snacks sizing, organised split, shares"},
        {"name": "Britannia Q4 FY25 call, Q3 FY26 deck", "tier": "primary",
         "used_for": "distribution reach, price-point mechanics, biscuit share withdrawal"},
        {"name": "ITC Report and Accounts 2025", "tier": "primary",
         "used_for": "distribution reach, Yogabar shareholding, category positions"},
        {"name": "Bikaji Q1 FY26 investor presentation", "tier": "primary",
         "used_for": "regional reach, family vs impulse pack mix"},
        {"name": "Kwality Wall's (India) Ltd exchange filing, Mar 2026", "tier": "primary",
         "used_for": "the ice-cream demerger and current ownership"},
        {"name": "56th GST Council press release", "tier": "primary",
         "used_for": "the Sept 2025 snack-food GST cut"},
        {"name": "ICMR-NIN, Dietary Guidelines for Indians 2024", "tier": "primary",
         "used_for": "HFSS thresholds, fortification, protein supplements, added sugar"},
        {"name": "Swaminathan, Vaz & Kurpad, Br J Nutr 2012", "tier": "primary",
         "used_for": "the credible counterweight to the protein-gap narrative"},
        {"name": "Turnwald et al., Psychological Science 2019", "tier": "primary",
         "used_for": "health vs taste framing, and its Indian unknowns"},
        {"name": "Pahlani et al., Global Health Action 2025", "tier": "primary",
         "used_for": "Indian label-reading behaviour and claim scepticism"},
        {"name": "MoSPI Household Consumption Expenditure Survey 2023-24",
         "tier": "primary", "used_for": "urban processed-food expenditure share"},
        {"name": "docs/research/snacking_pack/ — six lane files",
         "tier": "working-notes",
         "used_for": "everything above, with URLs, dates and verbatim sentences"},
    ],
    open_questions=[
        "VOICE SAMPLES FOR THE EVERYDAY-SNACK HALF. The 11 voice samples here cover "
        "supplements only. The snacking voice research failed — Reddit, Amazon, "
        "YouTube and Quora all block automated fetching — and deliberately returned "
        "nothing rather than inventing quotes. A brand's own social listening is the "
        "fastest fix, and this is the single best thing a brand can hand us.",
        "OCCASION SIZES. Nobody publishes them for India. How big is the afternoon "
        "slump against the late-night craving against the monthly stock-up, in this "
        "brand's own category? A brand with household-panel or occasion data can "
        "answer this and it is the highest-value thing they own.",
        "DAYPART BY CITY. Published data shows two Indian cities almost inverted on "
        "when people snack. Which cities does this brand actually sell in, and when?",
        "CATEGORY SIZES for chocolate, biscuits, ice cream and protein bars were "
        "never sourced at citable quality. Only savoury snacks has a defensible "
        "public number.",
        "THE D2C BETTER-FOR-YOU COHORT — Whole Truth, MuscleBlaze, RiteBite, Open "
        "Secret, Farmley — has no sourced revenue, share or repeat data. The largest "
        "single research gap.",
        "TRIAL-TO-REPEAT for better-for-you snack brands in India. No public data. "
        "Brands know their own and it would sharpen every read.",
        "SNACKING CHANNEL SPLIT — how much of THIS brand's category moves through "
        "quick commerce vs kirana vs modern trade. Not public; brands know it.",
        "PRICES NOT VERIFIED and deliberately absent: any ice cream price, Kurkure "
        "and Bingo, the small Dairy Milk unit ladder, Haldiram's small packs, "
        "Britannia 50-50 / Bourbon / Milk Bikis singles, and current-cycle grammage "
        "changes. A brand can confirm these in minutes.",
        "IS THE HEALTH-FRAMING EFFECT REAL IN INDIA? The evidence that a health "
        "promise damages taste expectations is strong, large-scale and preregistered "
        "— and entirely non-Indian, with the opposite result in France. Nobody has "
        "tested it here, and no study anywhere isolates 'no added sugar'.",
        "FRONT-OF-PACK LABELLING is live litigation as at 14 Aug 2026. Re-check "
        "before this pack is shown to any client.",
    ],
)
