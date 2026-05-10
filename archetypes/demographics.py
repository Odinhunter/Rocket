"""Demographic anchors for archetypes.

Each archetype maps to a statistical descriptor: age range, income band,
city tier, occupation profile. Stub here is hardcoded; later this can be
swapped for a real implementation (e.g. census-derived sampling) without
touching callers.
"""


_ANCHORS: dict[str, dict] = {
    "urban_indian_male_22_30": {
        "age": 26,
        "gender": "male",
        "city": "Bangalore",
        "neighborhood": "Indiranagar",
        "city_tier": 1,
        "occupation": "Software engineer at a mid-stage SaaS startup",
        "income_inr_annual": 1_800_000,
        "living_situation": "Shares a 3BHK with 2 flatmates",
        "education": "BTech, Tier-2 engineering college",
        "marital_status": "Single, on Hinge and Bumble",
        "household_obligations": "Sends ~₹30k/month to parents",
        "tech_signals": "iPhone 14, work MacBook, Boat headphones, Mi Band",
        "discretionary_spend_inr_monthly": 25_000,
    },
    "middle_class_indian_homemaker_38_55": {
        "age": 46,
        "gender": "female",
        "city": "Pune",
        "neighborhood": "Aundh",
        "city_tier": 1,
        "occupation": "Homemaker; tutors neighborhood kids in Hindi 2x/week (~₹8k/month)",
        "income_inr_annual": 1_140_000,  # household — husband is regional sales manager at FMCG distributor
        "living_situation": "Owned 2BHK with husband, son (2nd-year engineering at COEP, lives at home), daughter (Class 12)",
        "education": "BCom, Pune University",
        "marital_status": "Married 22 years",
        "household_obligations": "Manages all groceries, kids' tuition fees (~₹18k/month), monthly money to husband's mother in Nashik",
        "tech_signals": "Samsung Galaxy M-series, ~3yr-old laptop she rarely uses, JBL bluetooth speaker on the kitchen counter, the husband's old iPad for recipe videos",
        "discretionary_spend_inr_monthly": 12_000,
    },
}


def get_demographic_anchor(archetype: str) -> dict:
    """Return a statistical descriptor for the given archetype.

    Raises KeyError if the archetype is unknown.
    """
    return _ANCHORS[archetype]
