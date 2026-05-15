"""Category artifact pack: chocolate.

Hand-curated for Rocket v2. Raw material mined from the v1
(urban_indian_male_22_30, chocolate) disposition pool plus behavior.py /
demographics.py / voice.py / culture.py.
"""

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos() -> ChaosDistribution:
    # Chocolate is an impulse + gifting category — checkout-counter Dairy
    # Milk, last-minute gifting decisions. Skews impulsive.
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
        weighted=[(impulsive, 0.35), (moderate, 0.45), (deliberate, 0.20)]
    )


PACK = CategoryArtifactPack(
    category="chocolate",
    brand_landscape=[
        BrandLandscapeEntry(
            name="Cadbury Dairy Milk", tier="mass",
            note="the blue-and-white wrapper that IS chocolate to most of India; checkout impulse",
        ),
        BrandLandscapeEntry(
            name="Cadbury Silk", tier="mass-premium",
            note="softer Dairy Milk at a markup; everyday-romantic gifting tier",
        ),
        BrandLandscapeEntry(
            name="Ferrero Rocher", tier="premium",
            note="formal/parents/anniversary gifting; the WhatsApp-aunty pyramid",
        ),
        BrandLandscapeEntry(
            name="Lindt", tier="premium",
            note="Excellence 70%/85% bars; milestone gifting and self-treat for the snob tier",
        ),
        BrandLandscapeEntry(
            name="Toblerone", tier="premium",
            note="imported, layover/duty-free associations",
        ),
        BrandLandscapeEntry(
            name="Nature's Basket", tier="retailer",
            note="premium grocer where the self-treat Lindt bar gets bought",
        ),
    ],
    price_points=[
        PricePoint(item="Cadbury Silk heart-shaped box", price_inr="₹240-550", channel="supermarket / quick-commerce"),
        PricePoint(item="Ferrero Rocher 16-pc", price_inr="₹650", channel="supermarket"),
        PricePoint(item="Ferrero Rocher 24-pc", price_inr="₹1,200", channel="supermarket"),
        PricePoint(item="Lindt Excellence 70% bar", price_inr="₹385", channel="Nature's Basket"),
        PricePoint(item="Cadbury Dairy Milk impulse bar", price_inr="₹50", channel="kirana checkout"),
        PricePoint(item="Silk vs Dairy Milk markup", price_inr="~₹40 extra", channel="any"),
    ],
    retail_channels=[
        "kirana checkout", "supermarket", "Nature's Basket", "Blinkit",
        "Zepto", "Amazon",
    ],
    communities=[
        Community(
            name="/r/india", kind="subreddit",
            note="mass-vs-premium chocolate cynicism ('Silk is Dairy Milk at 1.5x')",
        ),
        Community(
            name="WhatsApp aunty groups", kind="whatsapp",
            note="the Ferrero Rocher pyramid forwards spike every February",
        ),
        Community(
            name="college / office group chats", kind="whatsapp",
            note="gifting-indecision polls — 'silk heart box or ferrero 24-pc?'",
        ),
    ],
    cultural_references=[
        "Valentine's Day chocolate-gifting surge and the soft-focus romantic-couple ad trope",
        "Raksha Bandhan / Diwali / wedding gifting pyramids — 'the pyramid IS the product'",
        "the gifting ladder: Silk = romantic-but-affordable, Ferrero = formal/parents, Lindt = milestone",
        "Cadbury cynicism — 'same Thane factory, slightly softer, crafted on the wrapper'",
        "foreign-chocolate snobbery — Indian chocolate as 'sweet and grainy'",
    ],
    demographic_defaults={
        "urban_metro_male": {
            "city": "Bangalore", "occupation": "software engineer at a SaaS startup",
            "income_inr_annual": 1_800_000,
            "marital_status": "single or in a relationship; on Hinge/Bumble",
        },
    },
    voice_samples=[
        "silk is just dairy milk at 1.5x with 'crafted' on the wrapper. cadbury has trained india to pay extra for slightly softer chocolate from the same thane factory lmao",
        "every feb the ferrero rocher pyramid posts on whatsapp aunty groups go up 800%. the pyramid IS the product, the chocolate inside is just structural support",
        "yaar her bday in 2 days. between silk heart box (550) or ferrero 24-pc (1200), she said 'just something thoughtful' but i need to know which one is the move",
        "another d2c brand selling moringa pasta for 800 rupees. india's middle class is being scammed by their own kind ngl",
    ],
    behavioral_priors=(
        "Chocolate is bought in two modes: the ₹50 checkout-counter impulse "
        "(Dairy Milk, next to the cigarettes, zero deliberation) and the gifting "
        "decision (Silk / Ferrero / Lindt, mapped onto a relationship ladder, "
        "often a last-minute group-chat poll two days before a birthday). "
        "Romantic-couple ad framing reads as a buying prompt to people in "
        "relationships and as 'someone else's storyline' to single observers who "
        "evaluate the casting instead. On Instagram, a price and an occasion "
        "frame stop the thumb; a soft-focus couple with no product detail does not."
    ),
    default_chaos_distribution=_chaos(),
)
