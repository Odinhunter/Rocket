"""Scaffold a starter v2 disposition library + AudienceSpec for the
chocolate category, anchored to Cadbury's actual India buyer base.

This is the "hand-mapping" onboarding step the v2 plan describes — done
once, by hand, here: 6 NamedDispositions covering Cadbury's category-
spanning buyer reality (Dairy Milk impulse loyalist, premium upgrader,
festive household gifter, health-conscious dark-chocolate buyer, Silk
dating-gesture, millennial nostalgia).

Each disposition is an 8-dimension DispositionVector + concrete anchor.
The cold_traffic_v1 audience splits across three demographic frames
(~67% weight on 25-34, ~33% on 35-44 household decision-maker) —
approximating the 70/30 split Mondelez India's dual playbook implies,
research-backed against Business Standard, Mordor, WARC, and thecore.in
interviews with Mondelez India's CMO (see HANDOFF for source list).

Running this script materializes, idempotently:
  runs/demo/cadbury_chocolate/entities/account.json
  runs/demo/cadbury_chocolate/entities/brand_profile.json
  runs/demo/cadbury_chocolate/entities/library.json            (6 dispositions)
  runs/demo/cadbury_chocolate/entities/audiences/<id>.json     (one SavedAudience)
  specs/cadbury_chocolate_cold_traffic.json                    (standalone AudienceSpec)
  specs/cadbury_chocolate_baseline.json                        (sample baseline funnel)

Then a v2 Creative Read on the cadbury ad is one command (see the
printout at the end).

Run: python scripts/scaffold_cadbury_chocolate.py
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
BRAND_PROFILE_ID = "cadbury_chocolate"
LIBRARY_ID = "cadbury_chocolate_lib_v1"
AUDIENCE_ID = "cold_traffic_v1"


# ---- The 6 hand-mapped Cadbury chocolate dispositions ----
#
# Each is a v1-style category-attitudinal cell translated into the 8-
# dimension vector. The `anchor` pins the specific object of each
# disposition's stance — the lesson from the Phase 1 vividness gate that
# an abstract vector cannot, on its own, distinguish "loyalty to mass
# chocolate" from "loyalty to premium dark" or "loyalty to a specific
# SKU." The brand name appears explicitly in every anchor so the render
# engine's artifact validator (agent/render.py:_validate_no_invented_
# artifacts) credits it as pack-grounded.

def _library() -> DispositionLibrary:
    dispositions = [
        NamedDisposition(
            label="loyalist_dairymilk",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="value_calculator",
                decision_driver="habit",
                category_involvement="low",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="settled",
            ),
            anchor=(
                "Cadbury Dairy Milk as the default home sweet — there's a "
                "half-finished slab in the fridge right now from a kirana "
                "run two days ago, ₹50 of habit. Eats it absentmindedly "
                "while watching reels; doesn't see 'chocolate' as a category "
                "to compare across — Cadbury Dairy Milk just IS chocolate "
                "the way Maggi IS noodles. Treats Cadbury Silk as 'Dairy "
                "Milk for gifting at 1.5x' and won't pay the markup at "
                "home. Has never read the back of the wrapper. If Cadbury "
                "Dairy Milk vanished off shelves tomorrow the substitute "
                "pick would be panicked, not researched."
            ),
        ),
        NamedDisposition(
            label="upgrader_premium",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="medium",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="settled",
            ),
            anchor=(
                "Cadbury Dairy Milk feels juvenile now — at the Lindt "
                "Excellence 70% / Ferrero Rocher tier, picks up a bar at "
                "Nature's Basket or Amazon weekly. Has opinions about "
                "ganache, knows which Toblerone batch tastes nuttier. Posts "
                "the Lindt packaging on stories with no caption. Treats "
                "Cadbury as the floor of the category — 'Cadbury Silk is "
                "just marketing applied to Dairy Milk; same Thane factory.' "
                "Will still buy a Cadbury Celebrations box for the office "
                "Diwali pool, never for the home shelf. Tracks the 24-pc "
                "Ferrero Rocher price drop window on Blinkit before "
                "Valentine's and waits the three days."
            ),
        ),
        NamedDisposition(
            label="gifter_festive",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="favorable",
                price_orientation="value_calculator",
                decision_driver="social_proof",
                category_involvement="high",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="family",
            ),
            anchor=(
                "Three weeks before every gifting occasion the mental "
                "spreadsheet opens — Raksha Bandhan for the brother-in-law, "
                "Diwali stacks for the maid and the building staff, "
                "Valentine's for the husband if reminded. Walks Nature's "
                "Basket and supermarket aisles physically to size up "
                "Cadbury Celebrations stacks against Ferrero Rocher "
                "pyramids. Knows the per-piece math: Cadbury Silk Heart at "
                "₹550 reads more like effort than Cadbury Dairy Milk "
                "Celebrations at the same per-gram math, even though the "
                "chocolate is from the same Thane plant. WhatsApp aunty "
                "groups polling 'silk heart box or ferrero 24-pc?' hit "
                "weekly every February. Treats chocolate as logistics, not "
                "indulgence — the chocolate inside IS structural support "
                "for the gift act."
            ),
        ),
        NamedDisposition(
            label="skeptic_health_dark",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="quality_first",
                decision_driver="function",
                category_involvement="medium",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Dark chocolate as the 'acceptable sweet' — 70%+ cacao, low "
                "sugar, fits the 1g-per-square macro budget. Buys Lindt "
                "Excellence 70% on Amazon subscription, occasionally a "
                "Toblerone dark variant at Nature's Basket. Tracks every "
                "gram in MyFitnessPal or HealthifyMe (sourced from the "
                "category's wellness culture, not the pack). Reads back-of-"
                "pack sugar per 100g before anything else, will pay 3x for "
                "half the sugar. Cynical about Cadbury Dairy Milk — 'milk "
                "chocolate' is 'kids' sugar water with cocoa added.' Posts "
                "the Lindt Excellence 90% wrapper to stories with no "
                "caption; the percentage is the caption."
            ),
        ),
        NamedDisposition(
            label="gifter_silk_dating",
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="favorable",
                price_orientation="value_calculator",
                decision_driver="social_proof",
                category_involvement="low",
                prior_experience_valence="positive",
                channel_behavior="quick_commerce",
                life_stage="early_career",
            ),
            anchor=(
                "Cadbury Silk as the 'I brought you something' prop on a "
                "third Bumble date or a relationship anniversary. Knows "
                "Cadbury Silk is Dairy Milk at a markup with a softer "
                "texture and a wrapper that does the work — accepts the "
                "math because the heart-shaped box does ₹300 worth of 'I "
                "thought about you' in a single visible object. Wouldn't "
                "be caught with a Ferrero Rocher pyramid (too aunty, reads "
                "as a wedding gift), wouldn't show up empty-handed (too "
                "callow). Picks it up at Blinkit on the way over; arrives "
                "with the receipt still warm. Doesn't buy chocolate any "
                "other time of year."
            ),
        ),
        NamedDisposition(
            label="loyalist_nostalgic",
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="loyalist",
                price_orientation="value_calculator",
                decision_driver="identity",
                category_involvement="low",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="early_career",
            ),
            anchor=(
                "Cadbury Dairy Milk codes as 1990s/early-2000s childhood — "
                "the school tuck-shop slab, the Diwali bonus from "
                "grandparents, the school-fete prize. Eats one occasionally "
                "and the first bite triggers the memory layer before the "
                "taste layer. Doesn't buy chocolate the rest of the year. "
                "Treats Cadbury Silk as a betrayal of the original — too "
                "soft, not 'chocolate-y' the way the old foil wrapper was. "
                "Won't engage with new SKUs — they're not THE Cadbury Dairy "
                "Milk. Buys at the kirana the way it was bought at age 9, "
                "not Blinkit."
            ),
        ),
    ]
    return DispositionLibrary(
        library_id=LIBRARY_ID,
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        dispositions=dispositions,
    )


# ---- Demographics: 3 frames giving ~67/33 weight 25-34 vs 35-44 ----
#
# The audience-spec list is unweighted — every demographic gets equal
# allocation in the panel allocator. We approximate the research-backed
# 70/30 split toward 25-34 by listing two distinct 25-34 frames (dating/
# single + young-family) and one 35-44 household frame. Each is
# meaningfully different so the render engine produces three genuinely
# distinct persona compositions rather than duplicated cells.

_DEMO_DATING_YOUNG = DemographicPoint(
    gender="any",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Bangalore / Mumbai / Delhi metro",
    occupation_hint="early/mid-career — startup, consulting, design",
    household_hint="single or dating; lives with flatmates or partner",
)

_DEMO_YOUNG_FAMILY = DemographicPoint(
    gender="any",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Bangalore / Mumbai / Pune metro",
    occupation_hint="early/mid-career — corporate, startup",
    household_hint="recently married or new parent; own 2BHK",
)

_DEMO_HOUSEHOLD = DemographicPoint(
    gender="female",
    age_band="35_44",
    income_tier="upper_mid",
    geography="Pune / Mumbai / Indore tier-1 + tier-2",
    occupation_hint="household decision-maker; part-time work or full-time-mom",
    household_hint="married with 1-2 school-age kids; 3BHK; runs household",
)


# ---- Context envelope: 4 attention states ad-relevant for CPG chocolate ----

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
    """A 'cold acquisition traffic' audience for Cadbury chocolate. All 6
    dispositions, three demographics (~67% 25-34 / ~33% 35-44), the
    chocolate pack's default chaos mix (35/45/20 — chocolate skews
    impulsive), panel_size 100 for L2 cells averaging ~5-6 agents each
    (boat-comparable density).

    Edit specs/cadbury_chocolate_cold_traffic.json to narrow the
    disposition set or change panel_size."""
    pack = load_pack("chocolate")
    return AudienceSpec(
        demographics=[_DEMO_DATING_YOUNG, _DEMO_YOUNG_FAMILY, _DEMO_HOUSEHOLD],
        disposition_labels=[
            "loyalist_dairymilk",
            "upgrader_premium",
            "gifter_festive",
            "skeptic_health_dark",
            "gifter_silk_dating",
            "loyalist_nostalgic",
        ],
        context_envelope=_CONTEXT_ENVELOPE,
        chaos_distribution=pack.default_chaos_distribution,
        panel_size=100,
    )


# Conservative CPG-on-Meta baseline placeholders. Chocolate is largely an
# offline purchase that ads attribution-trail-influence rather than
# direct-convert online, so click/visit/convert rates are lower than the
# D2C tech baseline used for boat. Replace with the customer's real
# account numbers when available.
_BASELINE_FUNNEL = {
    "stop_rate": 0.10,
    "click_rate": 0.015,
    "visit_rate": 0.008,
    "convert_rate": 0.004,
}


def main() -> None:
    print("=== scaffolding cadbury_chocolate v2 starter ===")

    # 1. Validate the artifact pack exists.
    pack = load_pack("chocolate")
    print(f"  artifact pack OK — {len(pack.brand_landscape)} brands, "
          f"{len(pack.price_points)} price points")

    # 2. Entity model on disk.
    account = Account(account_id=ACCOUNT_ID, name="Demo — Cadbury Chocolate")
    account.validate()
    account.save()

    brand = BrandProfile(
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        categories=["chocolate"],
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
        name="Cold acquisition traffic — cadbury chocolate",
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
    spec_path = specs_dir / "cadbury_chocolate_cold_traffic.json"
    spec_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))
    baseline_path = specs_dir / "cadbury_chocolate_baseline.json"
    baseline_path.write_text(json.dumps(_BASELINE_FUNNEL, indent=2))
    print(f"  standalone audience spec -> {spec_path}")
    print(f"  sample baseline funnel  -> {baseline_path}")

    print()
    print("Run a v2 Creative Read on the cadbury ad:")
    print()
    print("  .venv/bin/python batch_run.py \\")
    print("      --asset assets/cadbury_ad.png \\")
    print(f"      --audience-spec {spec_path.relative_to(specs_dir.parent)} \\")
    print(f"      --baseline-funnel {baseline_path.relative_to(specs_dir.parent)} \\")
    print("      --category chocolate \\")
    print(f"      --account {ACCOUNT_ID} --brand-profile {BRAND_PROFILE_ID} \\")
    print(f"      --library-id {LIBRARY_ID} --audience-id {AUDIENCE_ID}")
    print()
    print("  (drop --yes off to see the confirmation surface before the "
          "credit debits; add it to auto-commit)")
    print()
    print("PASS — cadbury_chocolate v2 starter scaffolded.")


if __name__ == "__main__":
    main()
