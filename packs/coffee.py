"""Category artifact pack: coffee.

Hand-curated for Rocket v2. Raw material mined from the v1 archetypes/
modules — the (urban_indian_male_22_30, coffee) and
(middle_class_indian_homemaker_38_55, coffee) disposition pools, plus
behavior.py / demographics.py / voice.py / culture.py.

This is the moat: real brands, real prices, real communities. The render
engine weaves ONLY from what is here.
"""

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos() -> ChaosDistribution:
    # Coffee is a habit-purchase category: instant coffee is bought on
    # near-autopilot (impulsive/moderate), while specialty/third-wave buyers
    # research and deliberate. Skews moderate.
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
        weighted=[(impulsive, 0.25), (moderate, 0.55), (deliberate, 0.20)]
    )


PACK = CategoryArtifactPack(
    category="coffee",
    brand_landscape=[
        BrandLandscapeEntry(
            name="Bru", tier="mass",
            note="green-jar instant incumbent; the kirana default for decades",
        ),
        BrandLandscapeEntry(
            name="Nescafe Classic", tier="mass",
            note="office-pantry and household instant; pure caffeine delivery",
        ),
        BrandLandscapeEntry(
            name="Nescafe Sunrise", tier="mass",
            note="chicory-blend instant, slightly cheaper tier",
        ),
        BrandLandscapeEntry(
            name="Nescafe Gold", tier="mass-premium",
            note="the 'graduated up' instant; ~₹600/100g, guests-and-occasions jar",
        ),
        BrandLandscapeEntry(
            name="Continental", tier="mass",
            note="Continental Xtra / South Blend; aggressive festive discounting",
        ),
        BrandLandscapeEntry(
            name="Tata Coffee Grand", tier="mass",
            note="mainstream instant, price-tracked against Bru and Nescafe",
        ),
        BrandLandscapeEntry(
            name="Tata Coffee Gold", tier="mass-premium",
            note="whole-bean and premium instant; aspirational-household tier",
        ),
        BrandLandscapeEntry(
            name="Cothas", tier="mass",
            note="South Indian filter-coffee chicory blend; steel-filter households",
        ),
        BrandLandscapeEntry(
            name="Blue Tokai", tier="d2c-disruptor",
            note="third-wave cafes + single-origin beans; metro class signal",
        ),
        BrandLandscapeEntry(
            name="Subko", tier="d2c-disruptor",
            note="specialty single-origin roaster; enthusiast shelf staple",
        ),
        BrandLandscapeEntry(
            name="Third Wave Coffee Roasters", tier="d2c-disruptor",
            note="specialty cafe chain; part of the normalised metro third-wave set",
        ),
        BrandLandscapeEntry(
            name="Curious Life", tier="d2c-disruptor",
            note="specialty single-origin roaster",
        ),
        BrandLandscapeEntry(
            name="Levista", tier="mass",
            note="instant-coffee capsule/subscription brand",
        ),
        BrandLandscapeEntry(
            name="Starbucks", tier="premium-cafe",
            note="Tata Starbucks; the aspirational urban-elite chain, ~500 stores; "
                 "'taught India to pay premium'; latte ~₹270-350; status-coded, the "
                 "café-as-third-place default",
        ),
        BrandLandscapeEntry(
            name="Cafe Coffee Day", tier="mid-cafe",
            note="CCD; the original mass bean-to-cup chain (1996), 'a lot can happen "
                 "over coffee'; ubiquitous, mid-range, in comeback",
        ),
        BrandLandscapeEntry(
            name="Costa Coffee", tier="premium-cafe",
            note="Coca-Cola-owned premium chain; the other urban-elite option beside "
                 "Starbucks",
        ),
        BrandLandscapeEntry(
            name="Barista", tier="mid-cafe",
            note="legacy pre-Starbucks mid-range café chain",
        ),
        BrandLandscapeEntry(
            name="AbCoffee", tier="d2c-disruptor",
            note="QSR-format affordable specialty coffee; grab-and-go third-wave",
        ),
    ],
    price_points=[
        PricePoint(item="Blue Tokai cold brew", price_inr="₹280", channel="Indiranagar cafe"),
        PricePoint(item="Bru 200g instant jar", price_inr="₹310", channel="kirana (normal price)"),
        PricePoint(item="Bru 200g instant jar", price_inr="₹245", channel="online, on offer"),
        PricePoint(item="Nescafe Gold 100g", price_inr="~₹600", channel="supermarket"),
        PricePoint(item="office-pantry instant cup", price_inr="effectively free / <₹15", channel="office pantry"),
        PricePoint(item="specialty single-origin beans 200g", price_inr="₹500-700", channel="Subko / Blue Tokai online"),
        PricePoint(item="cafe latte", price_inr="₹380", channel="metro chain cafe"),
        PricePoint(item="Starbucks Caffè Latte (Tall)", price_inr="₹270", channel="Starbucks; Grande +₹40-70"),
        PricePoint(item="Starbucks Cappuccino", price_inr="₹260", channel="Starbucks"),
        PricePoint(item="Starbucks Frappuccino", price_inr="₹300-320", channel="Starbucks"),
        PricePoint(item="CCD cappuccino", price_inr="~₹150-180", channel="Cafe Coffee Day"),
        PricePoint(item="Blue Tokai single-origin beans 250g", price_inr="₹450-650", channel="Blue Tokai online / cafe"),
    ],
    retail_channels=[
        "kirana", "Flipkart Grocery", "BigBasket", "Reliance Smart", "More",
        "Amazon", "Blinkit", "specialty cafe",
    ],
    communities=[
        Community(
            name="/r/coffee", kind="subreddit",
            note="pour-over / grind / single-origin discourse; enthusiast space",
        ),
        Community(
            name="WhatsApp family groups", kind="whatsapp",
            note="homemakers cross-check festive sale prices on staples here",
        ),
    ],
    cultural_references=[
        "third-wave coffee (Blue Tokai, Subko, Third Wave) normalised in metros but still a class signal",
        "Diwali stocking-up window — Flipkart Big Billion Days / Amazon Great Indian Sale notifications fire hourly",
        "MRP-inflation skepticism — '60% off' on an inflated MRP is a known marketing game",
        "South Indian filter-coffee ritual: steel filter, decoction set overnight, davara-tumbler",
        "office-pantry coffee as pure function; specialty coffee as hobby and identity",
    ],
    demographic_defaults={
        "urban_metro_male": {
            "city": "Bangalore", "occupation": "software engineer at a SaaS startup",
            "income_inr_annual": 1_800_000,
        },
        "homemaker": {
            "city": "Pune", "occupation": "homemaker managing household groceries",
            "household_income_inr_annual": 1_140_000,
        },
    },
    voice_samples=[
        "every starbucks in india looks like a wework now. paying 380 for a latte to take my standups in",
        "chaayos chai is sugar water with elaichi essence at 90 bucks. office pantry pe bru se acchi chai banti hai",
        "Bru se thoda strong taste hai, but family ko pasand aaya. 200g jar ₹245 ka mila on offer, normal time pe ₹310 hota hai.",
        "Yeh sab Tata Gold, Nescafe Gold types ka coffee mehnga hai 600 rupaye 100g ka — taste mein utna farak nahi padta honestly.",
        "MRP ₹500 dikha rahe hain aur same product ₹220 mein milta hai. 60% off ka chakkar hai.",
        "starbucks is a status symbol for people who can't afford a bmw. 292 rupees to look cool, that's the whole thing",
        "honestly i get more work done at starbucks than at home. wifi, ac, my corner seat, my usual grande — it's my third place",
        "degree kaapi at home every morning, steel filter, decoction set overnight. why would i pay 300 for a cappuccino with a bloated price tag",
        "blue tokai and third wave actually care about the bean. starbucks is over-roasted corporate syrup, you're paying for the logo",
    ],
    behavioral_priors=(
        "Coffee is bought on two very different loops. The instant-coffee loop is "
        "near-autopilot: a 15-second kirana errand or a Flipkart Grocery re-add, "
        "price-checked against memory, switching resisted because the family "
        "complains about taste changes. The specialty loop is a hobby: cafe "
        "visits, single-origin bags, /r/coffee browsing, grind and brew-method "
        "opinions. A festive sale compresses the instant loop's verification step. "
        "On Instagram, a specific rupee number on a known staple stops the thumb; "
        "'artisanal' visual language with no price makes it scroll faster."
    ),
    default_chaos_distribution=_chaos(),
)
