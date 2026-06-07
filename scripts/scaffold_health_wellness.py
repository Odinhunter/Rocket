"""Scaffold the disposition library + AudienceSpec for the
`health_wellness_nutrition` category — India D2C supplements / protein /
wellness, the first category built fresh under Protocol v2.

────────────────────────────────────────────────────────────────────────
7 dispositions authored 2026-06-02 under docs/disposition_protocol_v2.md.
Grounded in data/voice_samples/health_wellness_nutrition.md (live web
research: Amazon.in / Nykaa / Flipkart / HealthKart / Quora / Practo
reviews + market reports). PENDING ISHAN REVIEW (Protocol v2 §5 Lever 5).
────────────────────────────────────────────────────────────────────────

Design frame (see `dispositions_are_tg_gateways` memory): each disposition
is a GATEWAY to one attitudinal target group — the runtime render +
reaction AI does the rest of the lifting. The library deliberately spans
sub-categories (whey / plant protein / gummies / vitamins / bars), because
the unit of design is the TG, not the SKU. Cohort spread per Protocol v2
§5 Lever 3: 1 obsessive, 2 high, 1 medium, 3 low — load-bearing on the
scroll-past / reject voices so the audience isn't "engaged buyers only".

  1. enthusiast_macros_lifter   OBSESSIVE — serious gym lifter, Biozyme-loyal
  2. aspirant_clean_label       HIGH      — Insta-discovered clean-label buyer
  3. switcher_results_chaser    HIGH      — serial trier, switches on no-result
  4. doctor_triggered_vitamin   MEDIUM    — deficiency cohort, "medicine not lifestyle"
  5. skeptic_lapsed_protein     LOW       — bought once, "did nothing", lapsed
  6. pragmatist_protein_snacker LOW       — "snack, not supplement" (Yogabar)
  7. purist_food_first          LOW       — "dal-rice-ghee is enough", anti-supplement

IMPORTANT — anchors are DEMOGRAPHIC-FREE by design. Gender / age / city /
income / occupation come from the AudienceSpec.demographics axis (the
render engine cross-products demographic × disposition × context, and
render.py:222 requires the persona's gender/age/identity to come from the
demographic axis — the anchor "must not assume a gender or assign a name").
The anchor pins the *object* of the stance (the SKU, the behaviour, the
knowledge ceiling) — not who the person is. This matches the shipped
bru_coffee / personal_audio pattern, and the gateway reframe, and OVERRIDES
the literal "L1 = demographics" wording in disposition_protocol_v2.md §3
(that doc text predates the gateway steer; flag for a doc update).

REMAINING BEFORE A LIVE RUN (not in this file):
  - packs/health_wellness_nutrition.py  (brand landscape + price points +
    voice samples + chaos; ~20-25 brands. Reuse data/voice_samples/ +
    the pack-construction notes in the prior plan.)
  - then re-run this scaffold to also write the AudienceSpec + specs JSON.

Run: python scripts/scaffold_health_wellness.py
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
BRAND_PROFILE_ID = "health_wellness_demo"
LIBRARY_ID = "health_wellness_nutrition_lib_v1"
AUDIENCE_ID = "cold_traffic_v1"
CATEGORY = "health_wellness_nutrition"


# ---- The 7 hand-mapped health_wellness_nutrition dispositions ----
#
# Each anchor is 5 lines (L1 CONTEXT / L2 CATEGORY / L3 KNOWLEDGE /
# L4 STANCE / L5 ANCHOR-BEHAVIOR), separated by blank lines so the render
# engine reads them as discrete clauses, and treated as a HARD CONSTRAINT.
# Demographic-free + gender-neutral ("they") — see module note above.

def _library() -> DispositionLibrary:
    dispositions = [
        # 1 — OBSESSIVE. Coherence: loyalist + value_calculator + function +
        # obsessive all pull toward "I know what works, the math justifies
        # the brand, I'm not switching."
        NamedDisposition(
            label="enthusiast_macros_lifter",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="obsessive",
                prior_experience_valence="positive",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Three years into a structured 5-day push/pull/legs gym "
                "routine; treats supplements as tracked engineering inputs, "
                "not a lifestyle.\n\n"
                "Buys MuscleBlaze Biozyme Performance Whey 1kg chocolate at "
                "₹2,699 on HealthKart every six-to-seven weeks; the same cart "
                "adds creatine monohydrate and an omega-3.\n\n"
                "Knows protein-per-rupee and the Labdoor / Informed-Choice "
                "seals cold; does NOT lab-test, does NOT read the trials "
                "behind '50% better absorption', is NOT a nutritionist.\n\n"
                "Wants a consistent 25g per scoop, no added sugar, and a real "
                "authenticity seal; rejects loose 'imported' tubs and "
                "'proprietary blends' that hide the macros.\n\n"
                "Watches one Tarun Gill or Guru Mann video before any "
                "first-time brand switch, then defaults to Biozyme for the "
                "fourth tub running — 'I'm not changing what works.'"
            ),
        ),
        # 2 — HIGH. Coherence: favorable (not loyalist — they'd switch) +
        # identity + value_calculator + mixed valence = Insta-discovered,
        # switches when the next aesthetic clean brand drops.
        NamedDisposition(
            label="aspirant_clean_label",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="favorable",
                price_orientation="value_calculator",
                decision_driver="identity",
                category_involvement="high",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Came to wellness through Instagram in the post-COVID "
                "self-care wave; supplements are part of a clean-living "
                "identity, not performance.\n\n"
                "Rotates a Plix or OZiva plant protein (~₹2,000 on Nykaa), "
                "Power Gummies biotin (₹699), and a magnesium for sleep; "
                "₹2-3K a month on Nykaa and brand DTC.\n\n"
                "Scans for 'plant-based', 'clean', 'no maltodextrin'; does "
                "NOT track clinical dosages, does NOT know what inositol "
                "does, does NOT tell Type I from Type III collagen.\n\n"
                "Wants clean labels and Insta-coded brand aesthetics; rejects "
                "MuscleBlaze ('gym-bro stuff, not for me') and opaque white "
                "tubs; trusts a nutritionist's tag over an ad.\n\n"
                "Bought OZiva collagen last month at ₹1,499 after a Lovneet "
                "Batra reel; mixes a scoop into oat milk before yoga; would "
                "switch for a cleaner brand under ₹1,500."
            ),
        ),
        # 3 — HIGH, skeptical. Coherence: skeptical + value_calculator +
        # function + mixed = serial switching driven by lack of visible proof.
        NamedDisposition(
            label="switcher_results_chaser",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="high",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Started taking hair and skin supplements after visible "
                "shedding during a stressful stretch; two years in, still "
                "chasing a brand that visibly works.\n\n"
                "Has cycled OZiva → Power Gummies → Plix collagen → Setu → "
                "HK Vitals; switches when a brand 'does nothing visible after "
                "three months'; spends ₹1.5-2.5K a month.\n\n"
                "Knows what biotin and collagen 'are supposed to do' and "
                "reads back-of-pack lists; does NOT see a dermatologist "
                "first, does NOT track a baseline, does NOT distinguish "
                "collagen types.\n\n"
                "Wants a visible result inside 90 days and high Nykaa "
                "verified-review density (500+ reviews at 4 stars); rejects "
                "brands that 'look pretty on Insta but did nothing'.\n\n"
                "Six weeks into a Plix collagen at ₹1,499 on Nykaa; will give "
                "it eight more weeks, then switch to HK Vitals or Setu if the "
                "shedding doesn't visibly slow."
            ),
        ),
        # 4 — MEDIUM. Coherence: neutral + price_first + function + family =
        # brand-indifferent, doctor-driven, "medicine not lifestyle".
        # EXCLUDED from the cold-traffic audience below (ignores every
        # wellness-brand ad); belongs in a deficiency/medical audience.
        NamedDisposition(
            label="doctor_triggered_vitamin",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="function",
                category_involvement="medium",
                prior_experience_valence="neutral",
                channel_behavior="quick_commerce",
                life_stage="family",
            ),
            anchor=(
                "Does not think of themselves as a 'supplements person', yet "
                "takes three daily — all because a blood test flagged a "
                "deficiency and a doctor named them.\n\n"
                "Takes a Calcirol 60K weekly sachet (~₹35), a Livogen iron "
                "tablet, and a Shelcal calcium; reorders on 1mg the week one "
                "runs out.\n\n"
                "Knows the deficiency number and that they take Calcirol "
                "'because the doctor said'; does NOT know what an IU is, does "
                "NOT compare brands, does NOT consider Plix or OZiva.\n\n"
                "Wants prescription-grade reliability, the doctor-named "
                "brand, and pharmacy convenience; rejects supplements that "
                "'feel marketed at gym types or influencers' — this is "
                "medicine, not lifestyle.\n\n"
                "Reorders the sachet the week the last one runs out; scrolls "
                "straight past a wellness-brand reel without registering it "
                "as relevant to them."
            ),
        ),
        # 5 — LOW, burned. Coherence: lapsed + skeptical + burned + low =
        # the structurally honest scroll-past buyer. Load-bearing.
        NamedDisposition(
            label="skeptic_lapsed_protein",
            vector=DispositionVector(
                category_relationship="lapsed",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="low",
                prior_experience_valence="burned",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Joined a gym once on a motivation spike and bought protein "
                "to match; quit within six months; now reflexively distrusts "
                "the whole supplement pitch.\n\n"
                "Bought a ₹1,599 tub of whey his gym trainer pushed on him "
                "off Amazon in 2024; used about 60%, the rest sat in the "
                "cupboard until it got binned.\n\n"
                "Knows whey is 'for muscle' and 'you have to actually work "
                "out for it to do anything'; does NOT think supplements alone "
                "do anything, does NOT tell concentrate from isolate.\n\n"
                "Wants proof something measurably works; rejects ad copy "
                "promising 'muscle gain' or 'fat loss' without conditions; "
                "half-remembers that 'most Indian protein is adulterated'.\n\n"
                "Sees a protein-powder ad and thinks only 'yeah, it did "
                "nothing when I tried it'; would scroll past unless it named "
                "the exact failure they lived."
            ),
        ),
        # 6 — LOW/occasional. Coherence: occasional + neutral + price_first +
        # habit = the "snack not supplement" mental model. Load-bearing.
        NamedDisposition(
            label="pragmatist_protein_snacker",
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="habit",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="quick_commerce",
                life_stage="early_career",
            ),
            anchor=(
                "Would never call themselves 'into fitness', but keeps a "
                "protein bar around as a less-guilty snack; the supplements "
                "world feels like someone else's.\n\n"
                "Grabs Yogabar 20g protein bars from Blinkit (~₹625 for five) "
                "or the airport store; reaches for one instead of a biscuit "
                "during a 4pm crash about three times a week.\n\n"
                "Knows the bars have 'more protein than a chocolate bar'; "
                "does NOT see them as 'supplements', does NOT read past the "
                "front of the pack, does NOT track macros.\n\n"
                "Wants taste, portability, and 'feeling less guilty than a "
                "Snickers'; rejects whey powder and the whole visible "
                "gym-supplements aisle — not their world.\n\n"
                "Sees a wellness-supplement ad and barely registers it, "
                "because none of it feels made for someone who just wants a "
                "non-junky snack between meetings."
            ),
        ),
        # 7 — LOW, hostile-to-category. Coherence: never + hostile +
        # quality_first(food) + identity + low = the food-first rejecter who
        # actively resents the wellness shelf. Distinct from #5 (disappointed)
        # — this one thinks the whole category is a scam on principle.
        NamedDisposition(
            label="purist_food_first",
            vector=DispositionVector(
                category_relationship="never",
                brand_stance="hostile",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="offline_first",
                life_stage="settled",
            ),
            anchor=(
                "Buys no supplements on principle; believes a home kitchen of "
                "dal, rice, ghee, eggs and milk already does everything a "
                "powder claims.\n\n"
                "The only pill in the house is a doctor-prescribed vitamin-D "
                "someone takes; the D2C wellness shelf has never entered the "
                "monthly shop.\n\n"
                "Has absorbed the headlines — 'most Indian protein is "
                "adulterated', 'multivitamins are a waste' — but does NOT "
                "read the studies; anti-supplement, not anti-medicine.\n\n"
                "Believes real food and a grandmother's wisdom beat any "
                "powder; sees the wellness shelf as marketing that "
                "manufactures anxiety; quotes Rujuta Diwekar and the Liver "
                "Doc.\n\n"
                "Sees a protein or collagen ad and actively rolls their "
                "eyes — 'ghee and dal did the job for generations'; the more "
                "'scientific' the claim, the more they distrust it."
            ),
        ),
    ]
    return DispositionLibrary(
        library_id=LIBRARY_ID,
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        dispositions=dispositions,
    )


# ---- Demographics: 3 addressability frames spanning the buyer reality ----
#
# These own gender / age / income / geography / occupation. They cross-
# product with the (now demographic-free) dispositions, so some atypical
# cells appear (e.g. a female macros-lifter, a male clean-label buyer) —
# valid panel members, and how the engine is designed to work (panel.py).

_DEMO_MALE_PERFORMANCE = DemographicPoint(
    gender="male",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Bangalore / metro tier-1",
    occupation_hint="software engineer at a mid-stage SaaS startup",
    household_hint="shares a 2-3BHK with flatmates; sends money home monthly",
)

_DEMO_FEMALE_WELLNESS = DemographicPoint(
    gender="female",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Mumbai / Bangalore metro",
    occupation_hint="early/mid-career — marketing, design, product",
    household_hint="single or recently married; 1-2BHK in the metro core",
)

_DEMO_METRO_SETTLED = DemographicPoint(
    gender="any",
    age_band="35_44",
    income_tier="affluent",
    geography="metro tier-1 (Chennai / Pune / Delhi)",
    occupation_hint="settled professional — finance, corporate, family head",
    household_hint="married with kids; runs the household shop",
)


# ---- Context envelope: 4 attention states where a wellness ad is met ----

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
        label="pre_purchase_research",
        vector=ContextVector(
            attention_level="high", device_posture="desk",
            intent_state="actively_shopping", energy_state="alert",
            social_setting="alone",
        ),
    ),
    NamedContext(
        label="late_night_wind_down",
        vector=ContextVector(
            attention_level="low", device_posture="lying_down",
            intent_state="killing_time", energy_state="drained",
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


def _audience_spec(pack) -> AudienceSpec:
    """Cold acquisition traffic — health_wellness_nutrition.

    6 of the 7 dispositions (obsessive → high → high → low → low → low),
    deliberately scroll-past-heavy so the panel isn't engaged-buyers-only.
    doctor_triggered_vitamin is EXCLUDED — they ignore every wellness-brand
    ad; that disposition belongs in a separate deficiency/medical audience
    for vitamin-positioning brands.
    """
    return AudienceSpec(
        demographics=[
            _DEMO_MALE_PERFORMANCE,
            _DEMO_FEMALE_WELLNESS,
            _DEMO_METRO_SETTLED,
        ],
        disposition_labels=[
            "enthusiast_macros_lifter",
            "aspirant_clean_label",
            "switcher_results_chaser",
            "skeptic_lapsed_protein",
            "pragmatist_protein_snacker",
            "purist_food_first",
        ],
        context_envelope=_CONTEXT_ENVELOPE,
        chaos_distribution=pack.default_chaos_distribution,
        panel_size=100,
    )


# Conservative D2C-wellness-on-Meta baseline placeholders. Supplement
# conversion runs a touch higher than CPG (considered purchase, review-led)
# but trust friction is high. Replace with the customer's real numbers.
_BASELINE_FUNNEL = {
    "stop_rate": 0.11,
    "click_rate": 0.020,
    "visit_rate": 0.012,
    "convert_rate": 0.006,
}


def main() -> None:
    print("=== scaffolding health_wellness_nutrition starter ===")

    # 1. Entity model on disk — the disposition library does NOT depend on
    #    the artifact pack, so it always materializes.
    account = Account(account_id=ACCOUNT_ID, name="Demo — Health & Wellness Nutrition")
    account.validate()
    account.save()

    library = _library()
    library.validate()
    lib_path = library.save()
    print(f"  disposition library: {len(library.dispositions)} hand-mapped "
          f"dispositions -> {lib_path}")

    # 2. The AudienceSpec + BrandProfile need the artifact pack (chaos mix +
    #    brand-name validation at render time). If it isn't built yet, save
    #    the library and stop with a clear next step.
    try:
        pack = load_pack(CATEGORY)
    except Exception as exc:  # noqa: BLE001 — pack module not built yet
        print()
        print(f"  artifact pack '{CATEGORY}' not found ({exc.__class__.__name__}).")
        print("  Library is saved. Build packs/health_wellness_nutrition.py")
        print("  next (brand landscape + price points + voice samples +")
        print("  chaos), then re-run this scaffold for the AudienceSpec.")
        print()
        print("PARTIAL — library scaffolded; pack + audience pending.")
        return

    print(f"  artifact pack OK — {len(pack.brand_landscape)} brands, "
          f"{len(pack.price_points)} price points")

    brand = BrandProfile(
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        categories=[CATEGORY],
        library_id=LIBRARY_ID,
        audience_ids=[AUDIENCE_ID],
    )
    brand.validate()
    brand.save()

    spec = _audience_spec(pack)
    spec.validate()
    audience = SavedAudience(
        audience_id=AUDIENCE_ID,
        name="Cold acquisition traffic — health & wellness nutrition",
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
    spec_path = specs_dir / "health_wellness_cold_traffic.json"
    spec_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))
    baseline_path = specs_dir / "health_wellness_baseline.json"
    baseline_path.write_text(json.dumps(_BASELINE_FUNNEL, indent=2))
    print(f"  standalone audience spec -> {spec_path}")
    print(f"  sample baseline funnel  -> {baseline_path}")

    print()
    print("PASS — health_wellness_nutrition starter scaffolded.")


if __name__ == "__main__":
    main()
