"""Scaffold a starter v2 disposition library + AudienceSpec for the
coffee category, anchored to Bru (HUL India)'s actual buyer base.

This is the "hand-mapping" onboarding step the v2 plan describes — done
once, by hand, here: 6 NamedDispositions covering Bru's category-
spanning buyer reality: the South Indian household-jar buyer who is the
volume engine (Bru Instant 200g), the Nescafe switcher who left Bru
behind, the South Indian filter-coffee purist who treats instant as a
different category, the third-wave specialty drinker, the office-pantry
pragmatist, and the Bru Gold aspirational upgrader (the millennial
premium-instant buyer who is HUL's growth engine post the 2024 Sara Ali
Khan / Aditya Roy Kapur relaunch).

Each disposition is an 8-dimension DispositionVector + concrete anchor.
The cold_traffic_v1 audience splits across three demographic frames
(~67% weight on the 30-50 South/tier-2 household-jar buyer, ~33% on
the 25-34 metro millennial Bru Gold buyer) — approximating the 60/40
split HUL's two-buyer reality implies, research-backed against MMA
Global's Bru case study, Angel One's HUL coverage, and HUL's FY24-25
Foods segment commentary (see HANDOFF for source list).

Running this script materializes, idempotently:
  runs/demo/bru_coffee/entities/account.json
  runs/demo/bru_coffee/entities/brand_profile.json
  runs/demo/bru_coffee/entities/library.json            (6 dispositions)
  runs/demo/bru_coffee/entities/audiences/<id>.json     (one SavedAudience)
  specs/bru_coffee_cold_traffic.json                    (standalone AudienceSpec)
  specs/bru_coffee_baseline.json                        (sample baseline funnel)

Run: python scripts/scaffold_bru_coffee.py
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
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)

# --- target tenancy ---
ACCOUNT_ID = "demo"
BRAND_PROFILE_ID = "bru_coffee"
LIBRARY_ID = "bru_coffee_lib_v1"
AUDIENCE_ID = "cold_traffic_v1"


# ---- The 6 hand-mapped Bru coffee dispositions ----
#
# Ordered by volume importance so the panel allocator's disposition-major
# canonical order skews agent allocation toward the highest-revenue
# segments (Bru Instant household buyer + Nescafe switcher get the
# remainder agents, getting 24 agents each at panel=100; Bru Gold
# upgrader gets 16; filter purist / third-wave / office pragmatist get
# 12 each).

def _library() -> DispositionLibrary:
    dispositions = [
        NamedDisposition(
            label="loyalist_household_jar",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="value_calculator",
                decision_driver="habit",
                category_involvement="low",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="family",
            ),
            anchor=(
                "The green-jar Bru Instant 200g at ₹310 at the kirana, ₹245 "
                "when caught on Flipkart Grocery offer — there's always one "
                "on the kitchen shelf and a spare under the sink. Makes one "
                "cup with milk and two spoons of sugar at 7am, another at "
                "10am. Doesn't think about 'coffee' as a category to compare "
                "across; Bru just IS morning coffee. Treats Nescafe Classic "
                "as 'the guest jar' — fine in a pinch, not the default. Has "
                "never bought a Bru Gold jar — 'that's the special-occasion "
                "coffee, not daily.' Watches for the Diwali Big Billion Days "
                "drop on Bru and stocks up two jars at a time."
            ),
        ),
        NamedDisposition(
            label="switcher_nescafe",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="habit",
                category_involvement="medium",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Crossed over to Nescafe Classic three years ago — Bru "
                "tastes 'thin and chicory-heavy' and Nescafe is 'the proper "
                "one.' Treats Bru as 'mom's coffee' or 'the kirana "
                "fallback,' ungenerously. Buys the 200g Nescafe Classic on "
                "Amazon, occasionally treats self to a Nescafe Gold 100g at "
                "~₹600 when feeling fancy. Posts about chai-vs-coffee "
                "debates on family WhatsApp groups but never about coffee "
                "brands. Would never go back to Bru even if Nescafe ran out "
                "— would buy Tata Coffee Grand before reverting."
            ),
        ),
        NamedDisposition(
            label="upgrader_bru_gold",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="favorable",
                price_orientation="value_calculator",
                decision_driver="identity",
                category_involvement="medium",
                prior_experience_valence="positive",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "The Bru Gold 100g jar at ~₹600 — graduated up from Bru "
                "Instant during the WFH years, now keeps both: Bru Gold for "
                "the morning 'real' cup, Bru Instant for the second / third "
                "refill. Saw the 2024 Bru Gold relaunch ads and the home-"
                "café framing; knows the brand is making a play for that "
                "moment. Compares Bru Gold favorably to Nescafe Gold ('same "
                "tier, slightly cheaper, easier to find on Amazon') and "
                "treats specialty coffee as 'the next upgrade if I ever set "
                "up an AeroPress.' Will sometimes order a Blue Tokai cold "
                "brew kit but Bru Gold is the daily driver. Posts the Bru "
                "Gold jar on stories occasionally — the wrapper is part of "
                "the morning aesthetic."
            ),
        ),
        NamedDisposition(
            label="purist_filter",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="hostile",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="high",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="settled",
            ),
            anchor=(
                "Decoction set in the steel filter overnight, davara-tumbler "
                "ritual in the morning — the Cothas chicory blend or the "
                "local roaster's beans, never instant. Treats Bru, Nescafe, "
                "Tata Coffee Grand as 'the other category, not coffee' — "
                "would say so politely if asked but means it as a real "
                "category distinction. Will accept a Bru cup in someone "
                "else's home out of courtesy, but at home it's filter, full "
                "stop. Reads Subko and Blue Tokai as the same compromise "
                "category as instant — 'specialty machines making a brewed "
                "copy of filter coffee.' Hates being asked to make instant "
                "for guests. Wouldn't post about it; this is private "
                "practice, not signaling."
            ),
        ),
        NamedDisposition(
            label="enthusiast_third_wave",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="hostile",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="obsessive",
                prior_experience_valence="positive",
                channel_behavior="d2c_direct",
                life_stage="early_career",
            ),
            anchor=(
                "A Blue Tokai 200g single-origin bag (Vienna roast, ₹650) "
                "on the counter and an AeroPress next to the V60. Knows the "
                "grind size by feel, can taste a stale bean. Treats instant "
                "coffee — Bru, Nescafe, all of it — as 'industrial sludge' "
                "categorically. Browses /r/coffee for tasting notes and "
                "grind recommendations; bookmarked the Subko subscription. "
                "The third-wave cafe — Blue Tokai Indiranagar, Third Wave "
                "Coffee Roasters Koramangala — is the social meeting venue "
                "and the ₹280 cold brew is the standard order. Will mention "
                "the brewing method unprompted ('I do mine on a V60') and "
                "gets uncomfortable if someone offers instant."
            ),
        ),
        NamedDisposition(
            label="pragmatist_pantry",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="function",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="offline_first",
                life_stage="early_career",
            ),
            anchor=(
                "Coffee is pure caffeine delivery — the office pantry tin "
                "or sachet that's always there, brewed in 60 seconds with "
                "hot water and milk powder. Doesn't track brand. Whoever "
                "stocked the pantry stocked it; today it's Continental or "
                "Bru or sometimes a generic Tata Coffee Grand, doesn't "
                "matter. Drinks two cups a day, both at the desk, both for "
                "the function. Has never bought a coffee at a third-wave "
                "cafe and would not understand why anyone pays ₹380 for a "
                "latte. Doesn't see 'coffee' as a category to engage with; "
                "it's the same as the office water."
            ),
        ),
    ]
    return DispositionLibrary(
        library_id=LIBRARY_ID,
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        dispositions=dispositions,
    )


# ---- Demographics: 3 frames giving ~67/33 weight household vs millennial ----
#
# The audience-spec list is unweighted — every demographic gets equal
# allocation. We approximate the research-backed 60/40 split toward the
# household-jar buyer by listing two distinct household-jar frames
# (South tier-1 metro + North/West tier-2) and one metro-millennial
# frame. Each is meaningfully different so the render engine produces
# three genuinely distinct persona compositions.

_DEMO_SOUTH_HOUSEHOLD = DemographicPoint(
    gender="female",
    age_band="35_44",
    income_tier="upper_mid",
    geography="Chennai / Bangalore / Hyderabad metro",
    occupation_hint="household decision-maker; some part-time work",
    household_hint="married with 1-2 kids; 3BHK; runs household groceries",
)

_DEMO_TIER2_HOUSEHOLD = DemographicPoint(
    gender="female",
    age_band="35_44",
    income_tier="lower_mid",
    geography="Indore / Lucknow / Pune tier-2",
    occupation_hint="full-time homemaker or part-time work",
    household_hint="married with 1-2 school-age kids; 2BHK; tea-to-coffee converter household",
)

_DEMO_METRO_MILLENNIAL = DemographicPoint(
    gender="any",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Mumbai / Bangalore / Delhi metro",
    occupation_hint="early/mid-career — corporate, startup, consulting",
    household_hint="single, dating, or recently married; flat or 2BHK",
)


# ---- Context envelope: 4 attention states where a CPG coffee ad is encountered ----

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
        label="evening_couch_scroll",
        vector=ContextVector(
            attention_level="low", device_posture="couch",
            intent_state="passive_browse", energy_state="neutral",
            social_setting="family_present",
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
        label="weekend_afternoon_browse",
        vector=ContextVector(
            attention_level="medium", device_posture="couch",
            intent_state="passive_browse", energy_state="neutral",
            social_setting="alone",
        ),
    ),
]


def _audience_spec() -> AudienceSpec:
    """A 'cold acquisition traffic' audience for Bru coffee. All 6
    dispositions, three demographics (~67% household-jar / ~33% metro
    millennial), the coffee pack's default chaos mix (25/55/20 — coffee
    skews moderate because instant is habit-purchase autopilot but
    specialty buyers research), panel_size 100 for L2 cells averaging
    ~5-6 agents each (boat / cadbury comparable density)."""
    pack = load_pack("coffee")
    return AudienceSpec(
        demographics=[
            _DEMO_SOUTH_HOUSEHOLD,
            _DEMO_TIER2_HOUSEHOLD,
            _DEMO_METRO_MILLENNIAL,
        ],
        disposition_labels=[
            "loyalist_household_jar",
            "switcher_nescafe",
            "upgrader_bru_gold",
            "purist_filter",
            "enthusiast_third_wave",
            "pragmatist_pantry",
        ],
        context_envelope=_CONTEXT_ENVELOPE,
        chaos_distribution=pack.default_chaos_distribution,
        panel_size=100,
    )


# Conservative CPG-on-Meta baseline placeholders. Coffee online conversion
# is slightly higher than chocolate (jars are bought online more readily
# than chocolate bars) but still well below D2C tech. Replace with the
# customer's real account numbers when available.
_BASELINE_FUNNEL = {
    "stop_rate": 0.10,
    "click_rate": 0.018,
    "visit_rate": 0.010,
    "convert_rate": 0.005,
}


def main() -> None:
    print("=== scaffolding bru_coffee v2 starter ===")

    # 1. Validate the artifact pack exists.
    pack = load_pack("coffee")
    print(f"  artifact pack OK — {len(pack.brand_landscape)} brands, "
          f"{len(pack.price_points)} price points")

    # 2. Entity model on disk.
    account = Account(account_id=ACCOUNT_ID, name="Demo — Bru Coffee")
    account.validate()
    account.save()

    brand = BrandProfile(
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        categories=["coffee"],
        library_id=LIBRARY_ID,
        audience_ids=[AUDIENCE_ID],
    )
    brand.validate()
    brand.save()

    library = _library()
    library.validate()
    lib_path = library.save()
    print(f"  disposition library: {len(library.dispositions)} hand-mapped "
          f"dispositions -> {lib_path}")

    spec = _audience_spec()
    spec.validate()
    audience = SavedAudience(
        audience_id=AUDIENCE_ID,
        name="Cold acquisition traffic — bru coffee",
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
    spec_path = specs_dir / "bru_coffee_cold_traffic.json"
    spec_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))
    baseline_path = specs_dir / "bru_coffee_baseline.json"
    baseline_path.write_text(json.dumps(_BASELINE_FUNNEL, indent=2))
    print(f"  standalone audience spec -> {spec_path}")
    print(f"  sample baseline funnel  -> {baseline_path}")

    print()
    print("Run a v2 Creative Read on the bru ad:")
    print()
    print("  .venv/bin/python batch_run.py \\")
    print("      --asset assets/bru_ad.png \\")
    print(f"      --audience-spec {spec_path.relative_to(specs_dir.parent)} \\")
    print(f"      --baseline-funnel {baseline_path.relative_to(specs_dir.parent)} \\")
    print("      --category coffee \\")
    print(f"      --account {ACCOUNT_ID} --brand-profile {BRAND_PROFILE_ID} \\")
    print(f"      --library-id {LIBRARY_ID} --audience-id {AUDIENCE_ID}")
    print()
    print("  (drop --yes off to see the confirmation surface before the "
          "credit debits; add it to auto-commit)")
    print()
    print("PASS — bru_coffee v2 starter scaffolded.")


if __name__ == "__main__":
    main()
