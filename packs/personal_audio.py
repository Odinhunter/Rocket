"""Category artifact pack: personal_audio (TWS earbuds / headphones).

Hand-curated for Rocket v2. Raw material mined from the v1
(urban_indian_male_22_30, personal_audio) disposition pool plus
behavior.py / demographics.py / voice.py / culture.py.
"""

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos() -> ChaosDistribution:
    # Personal audio is a considered electronics purchase — spec sheets,
    # YouTube reviews, Notion comparison docs. But the replacement-buyer
    # ("lost an earbud, need one before tomorrow's standup") is genuinely
    # impulsive. Skews more deliberate than CPG categories.
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
        weighted=[(impulsive, 0.20), (moderate, 0.45), (deliberate, 0.35)]
    )


PACK = CategoryArtifactPack(
    category="personal_audio",
    brand_landscape=[
        BrandLandscapeEntry(
            name="Boat", tier="mass",
            note="the ₹1,000-2,500 default; Airdopes 131/141/161/311 Pro/441 Pro/911 ANC, Nirvana Ion",
        ),
        BrandLandscapeEntry(
            name="OnePlus", tier="mass-premium",
            note="Nord Buds 2, Buds 3; spec-credible mid-tier",
        ),
        BrandLandscapeEntry(
            name="Nothing", tier="d2c-disruptor",
            note="Ear (a), Ear (Stick), Phone (2a); design-led, Carl Pei following",
        ),
        BrandLandscapeEntry(
            name="CMF", tier="d2c-disruptor",
            note="Nothing's sub-brand; Buds Pro 2 / Buds 2; design DNA at a lower price",
        ),
        BrandLandscapeEntry(
            name="Realme", tier="mass",
            note="Buds Q2, Buds Air 3 Neo, Buds Air 6 Pro; budget spec-sheet competitor",
        ),
        BrandLandscapeEntry(
            name="Noise", tier="mass",
            note="commodity-tier TWS brand, marketing-heavy",
        ),
        BrandLandscapeEntry(
            name="Sony", tier="premium",
            note="WF-1000XM5; the aspirational wishlist tier",
        ),
        BrandLandscapeEntry(
            name="Bose", tier="premium",
            note="QC Ultra; aspirational wishlist tier",
        ),
        BrandLandscapeEntry(
            name="AirPods Pro", tier="premium",
            note="AirPods Pro 2 at ₹26,999; the six-months-tabbed-open aspiration",
        ),
        BrandLandscapeEntry(
            name="Moondrop", tier="enthusiast",
            note="Aria 2 IEMs; wired-audiophile tier",
        ),
        BrandLandscapeEntry(
            name="Sennheiser", tier="enthusiast",
            note="HD 560S; desk-setup audiophile tier",
        ),
        BrandLandscapeEntry(
            name="Topping", tier="enthusiast",
            note="DX1 DAC; the wired-purist signal chain",
        ),
    ],
    price_points=[
        PricePoint(item="Boat Airdopes 131", price_inr="₹999", channel="Flipkart Big Billion Days"),
        PricePoint(item="Boat Airdopes 141 ANC", price_inr="₹1,799", channel="Flipkart / Amazon"),
        PricePoint(item="Boat earbuds (current-gen)", price_inr="₹1,199", channel="Amazon, same-day delivery"),
        PricePoint(item="Realme Buds Q2", price_inr="₹1,499", channel="Flipkart"),
        PricePoint(item="AirPods Pro 2", price_inr="₹26,999", channel="Apple India"),
        PricePoint(item="Nothing Ear (Stick)", price_inr="₹14,999", channel="Nothing online / Flipkart"),
        PricePoint(item="Nothing Phone (2a)", price_inr="₹25,999", channel="Flipkart"),
        PricePoint(item="Moondrop Aria 2 IEMs", price_inr="₹6,500", channel="AliExpress"),
        PricePoint(item="unplanned-replacement budget cap", price_inr="₹2,000", channel="Flipkart / Amazon"),
    ],
    retail_channels=[
        "Flipkart", "Amazon", "Blinkit", "Flipkart Big Billion Days",
        "Apple India", "AliExpress",
    ],
    communities=[
        Community(
            name="Geekyranjit", kind="youtuber",
            note="the default TWS review channel; watched twice before a purchase",
        ),
        Community(
            name="Trakin Tech", kind="youtuber",
            note="mainstream tech-review channel",
        ),
        Community(
            name="Beebom", kind="publication",
            note="TWS shootout / comparison articles",
        ),
        Community(
            name="r/IndianGaming", kind="subreddit",
            note="'best TWS under 5k' megathreads",
        ),
        Community(
            name="r/headphones", kind="subreddit",
            note="wired-audiophile discourse",
        ),
        Community(
            name="r/audiophile", kind="subreddit",
            note="wired-audiophile discourse",
        ),
    ],
    cultural_references=[
        "Boat as 'what people who don't care buy' vs Nothing/CMF as design-aware choices",
        "spec-sheet culture — driver size in mm, ANC depth in dB, AAC vs aptX vs LDAC, multipoint",
        "'AI-ENx Technology' / 'Hybrid ANC' marketing copy read as syllables of nothing",
        "the Notion comparison doc kept open for three weeks before a ₹2,000 purchase",
        "return-window and no-questions replacement reputation as the real differentiator at this tier",
        "Carl Pei / Nothing keynote-launch fandom; transparent-shell design as a style object",
    ],
    demographic_defaults={
        "urban_metro_male": {
            "city": "Bangalore", "occupation": "software engineer at a SaaS startup",
            "income_inr_annual": 1_800_000,
            "tech_signals": "iPhone or Nothing Phone, work MacBook, Mi Band",
        },
    },
    voice_samples=[
        "5500 for a tee from snitch?? bhai sasta china reseller hai literally. sab same factory se aata hai",
        "Boult earbuds at 1499 — almost bought, cross-checked Reddit, didn't",
        "another d2c brand selling moringa pasta for 800 rupees. india's middle class is being scammed",
        "every other brand on insta is the same chinese OEM with a different logo and a three-syllable feature name",
    ],
    behavioral_priors=(
        "Personal audio is a researched purchase for most of this set: a Notion "
        "doc comparing driver size, ANC depth, codecs and battery life; Geekyranjit "
        "and Trakin Tech watched twice; the r/IndianGaming 'best TWS under 5k' "
        "megathread bookmarked. The exception is the replacement-buyer — lost an "
        "earbud, has a 10:30 standup tomorrow, budget capped at ₹2,000, brand "
        "barely matters as long as it ships same-day with a high review count. On "
        "Instagram a concrete spec or a price that beats Reddit's known floor "
        "stops the thumb; lifestyle posing with no product detail does not."
    ),
    default_chaos_distribution=_chaos(),
)
