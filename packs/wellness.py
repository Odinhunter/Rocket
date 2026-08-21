"""Category artifact pack: wellness (ayurveda / supplements / chyawanprash).

Hand-curated for Rocket v2. Raw material mined from the v1
(urban_indian_male_22_30, wellness) disposition pool plus behavior.py /
demographics.py / voice.py / culture.py.

Note: the v1 wellness disposition prose carries fewer hard price anchors
than coffee or personal_audio. The price_points below are the ones the
prose states or strongly implies; a real onboarding curation pass for a
wellness customer would deepen this.
"""

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos() -> ChaosDistribution:
    # Wellness is a skeptical, identity-loaded category — politics, ingredient
    # research, dad-supplement associations. Buyers either grab on a Blinkit
    # deal (impulsive) or read the label and the evidence (deliberate). Skews
    # toward deliberate/moderate.
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
        weighted=[(impulsive, 0.20), (moderate, 0.50), (deliberate, 0.30)]
    )


PACK = CategoryArtifactPack(
    category="wellness",
    market_name="Indian everyday wellness",
    brand_landscape=[
        BrandLandscapeEntry(
            name="Patanjali", tier="mass",
            note="Dant Kanti, Aloe Vera juice, honey, ghee; Baba Ramdev brand baggage",
        ),
        BrandLandscapeEntry(
            name="Dabur", tier="mass",
            note="Chyawanprash in the giant glass jar; the 20-year kitchen-shelf default",
        ),
        BrandLandscapeEntry(
            name="Himalaya", tier="mass-premium",
            note="the 'no saffron-robed monk on the bottle' ayurveda alternative",
        ),
        BrandLandscapeEntry(
            name="MyProtein", tier="d2c-disruptor",
            note="whey, creatine, BCAAs; the gym-bro modern-supplement stack",
        ),
        BrandLandscapeEntry(
            name="Nutrabay", tier="d2c-disruptor",
            note="supplements marketplace; whey / creatine / fish oil",
        ),
        BrandLandscapeEntry(
            name="Amul", tier="mass",
            note="ghee price benchmark Patanjali ghee is compared against",
        ),
    ],
    price_points=[
        PricePoint(item="Patanjali ghee vs Amul ghee", price_inr="~₹40 cheaper than Amul", channel="Blinkit"),
        PricePoint(item="Dabur Chyawanprash 1kg glass jar", price_inr="~₹400-450", channel="kirana / supermarket"),
        PricePoint(item="Patanjali Aloe Vera juice", price_inr="~₹150-200", channel="Blinkit reorder"),
        PricePoint(item="whey protein 1kg", price_inr="~₹1,800-2,500", channel="MyProtein / Nutrabay"),
        PricePoint(item="creatine 250g", price_inr="~₹500-700", channel="Nutrabay"),
    ],
    retail_channels=[
        "kirana", "supermarket", "Blinkit", "Amazon", "MyProtein", "Nutrabay",
    ],
    communities=[
        Community(
            name="r/Supplements", kind="subreddit",
            note="ingredient-evidence discourse; the ayurveda-skeptic's reference",
        ),
        Community(
            name="Examine.com", kind="reference site",
            note="evidence database the ingredient-curious actually read",
        ),
        Community(
            name="Andrew Huberman", kind="podcast",
            note="the modern-supplement-stack cultural anchor",
        ),
        Community(
            name="r/india", kind="subreddit",
            note="where Patanjali / Ramdev politics gets argued",
        ),
    ],
    cultural_references=[
        "Baba Ramdev brand baggage — the 2020-21 Coronil episode, communal commentary, politics",
        "the saffron-robed monk on the bottle as a load-bearing signal, positive or negative",
        "'boost your immunity' chyawanprash framing read as grandparent / dad-supplement marketing",
        "private-use-public-denial — using Patanjali quietly while never admitting it to a Twitter circle",
        "ingredient-evidence skepticism — reading the label and Examine.com, not the ad copy",
        "the modern stack (whey, creatine, zinc, fish oil) positioned against amla-in-ghee",
    ],
    demographic_defaults={
        "urban_metro_male": {
            "city": "Bangalore", "occupation": "software engineer at a SaaS startup",
            "income_inr_annual": 1_800_000,
        },
    },
    voice_samples=[
        "another d2c brand selling moringa pasta for 800 rupees. india's middle class is being scammed by their own kind ngl",
        "i get my immunity from 8 hours of sleep, zinc tablets and 180g of protein a day, not amla paste suspended in ghee",
        "would read the ingredients label and Examine.com, not the ad copy",
        "this guy is somehow still on insta",
    ],
    behavioral_priors=(
        "Wellness is the most identity-loaded category here: a Patanjali ad lands "
        "differently on a household-loyal buyer, a politically-motivated rejecter, "
        "a private-user-public-denier, and an ingredient-curious ayurveda skeptic. "
        "Purchase happens either as a low-deliberation Blinkit deal-grab (ghee ₹40 "
        "cheaper than Amul, brand baggage doesn't enter the math) or as a "
        "label-and-evidence read (r/Supplements, Examine.com, Huberman). On "
        "Instagram, the brand's face and framing trigger an immediate "
        "stance-driven reaction; 'boost your immunity' copy reads as marketing to "
        "an older generation."
    ),
    default_chaos_distribution=_chaos(),
)
