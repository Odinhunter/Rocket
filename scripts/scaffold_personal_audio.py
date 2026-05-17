"""Scaffold a starter v2 disposition library + AudienceSpec for the
personal_audio category.

This is the "hand-mapping" onboarding step the v2 plan describes — done
once, by hand, here: the 7 v1 (urban_indian_male_22_30, personal_audio)
dispositions translated into 8-dimension DispositionVectors, with anchors
where the abstract vector alone can't pin the object of the stance.

Running this script materializes, idempotently:
  runs/<account>/<account>/<brand>/entities/account.json
  runs/<account>/<brand>/entities/brand_profile.json
  runs/<account>/<brand>/entities/library.json          (7 dispositions)
  runs/<account>/<brand>/entities/audiences/<id>.json   (one SavedAudience)
  specs/personal_audio_cold_traffic.json                (standalone AudienceSpec)
  specs/personal_audio_baseline.json                    (sample baseline funnel)

Then a v2 Creative Read is one command (see the printout at the end).

Run: python scripts/scaffold_personal_audio.py
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
BRAND_PROFILE_ID = "boat_audio"
LIBRARY_ID = "personal_audio_lib_v1"
AUDIENCE_ID = "cold_traffic_v1"


# ---- The 7 hand-mapped personal_audio dispositions ----
# Each is a v1 disposition.py prose block translated into the 8-dimension
# vector. The `anchor` is set wherever the abstract vector can't, on its
# own, pin WHAT the stance is about (the filter-coffee-vs-d2c-roaster
# lesson from the Phase 1 vividness gate).

def _library() -> DispositionLibrary:
    dispositions = [
        NamedDisposition(
            label="loyalist_airdopes",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="value_calculator",
                decision_driver="habit",
                category_involvement="high",
                prior_experience_valence="positive",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "Boat — specifically the ₹1,000-2,500 Airdopes line; on his "
                "third pair, buys by default, knows the lineup by SKU, reads "
                "'AI-ENx' as 'Boat being Boat'. Sees CMF/Nothing as 'a phones "
                "brand doing earbuds for show'."
            ),
        ),
        NamedDisposition(
            label="enthusiast_specs",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="quality_first",
                decision_driver="function",
                category_involvement="obsessive",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "the published spec sheet itself — driver size in mm, ANC "
                "depth in dB, codec list (AAC / aptX / LDAC), multipoint "
                "support, mic pickup pattern. Treats any TWS ad that leads "
                "with marketing shorthand like 'AI-ENx' or '4 mics' without "
                "published measurements as a non-signal regardless of price "
                "— will not click. Brand-agnostic; keeps a Notion comparison "
                "doc; watches Geekyranjit before any purchase above ₹1,000."
            ),
        ),
        NamedDisposition(
            label="aspirant_airpods",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="high",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "the aspiration gap — AirPods Pro 2 tabbed open for months, "
                "knows the markup by heart. Treats the ₹1,000-3,000 "
                "Indian-brand tier as a compromise zone; CMF / Nothing Ear (a) "
                "are the 'bridge tier' that lets him not feel like he's "
                "buying down. Uses a gifted Boat pair but won't post a photo "
                "of it."
            ),
        ),
        NamedDisposition(
            label="enthusiast_nothing_design",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="high",
                prior_experience_valence="positive",
                channel_behavior="d2c_direct",
                life_stage="early_career",
            ),
            anchor=(
                "the Nothing / CMF design ecosystem — bought the Phone (2a) on "
                "launch day, follows Carl Pei, watches the keynotes. Earbuds "
                "are a style object as much as audio gear; Boat is 'what "
                "people who don't care buy' and he wouldn't be caught with a "
                "Boat case visible in a Saturday photo."
            ),
        ),
        NamedDisposition(
            label="pragmatist_urgent_replacement",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="function",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="quick_commerce",
                life_stage="early_career",
            ),
            anchor=(
                "an urgent unplanned replacement — lost an earbud on the "
                "Metro, has a 10:30am standup tomorrow, ₹2,000 budget cap "
                "because this is unplanned cost. Brand barely matters; needs "
                "whatever ships same-day with 4+ stars on 50,000+ reviews."
            ),
        ),
        NamedDisposition(
            label="skeptic_warranty",
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="medium",
                prior_experience_valence="mixed",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "service and the return-window — believes every sub-₹3,000 "
                "TWS is the same Chinese OEM hardware with a different logo "
                "and 'AI-ENx Technology' is three syllables of nothing. The "
                "only real differentiator is whether the brand replaces it "
                "when it dies in month 9 — Boat did, after a tweet."
            ),
        ),
        NamedDisposition(
            label="purist_wired",
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="function",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="marketplace",
                life_stage="early_career",
            ),
            anchor=(
                "TWS as a throwaway utility category — his real audio life is "
                "wired (Moondrop Aria 2 IEMs into a Topping DAC, Sennheiser "
                "HD 560S). TWS earbuds are only for podcasts on the walk, "
                "calls, and the gym; replaced with 'whatever is cheapest and "
                "reliable', zero feelings about the current pair."
            ),
        ),
    ]
    return DispositionLibrary(
        library_id=LIBRARY_ID,
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        dispositions=dispositions,
    )


# ---- Demographics + context envelope for the starter audience ----

_DEMOGRAPHIC = DemographicPoint(
    gender="male",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Bangalore / metro tier-1",
    occupation_hint="software engineer at a mid-stage SaaS startup",
    household_hint="shares a 3BHK with flatmates, sends money home monthly",
)

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


def _audience_spec() -> AudienceSpec:
    """A 'cold acquisition traffic' cut: 5 of the 7 dispositions (the ones a
    cold-traffic acquisition ad realistically reaches — drops the urgent
    replacement_buyer and the barely-in-category wired_audio_purist), a
    4-context envelope, the personal_audio pack's default chaos mix, and a
    modest panel_size for an affordable first breadth-eval run.

    Edit specs/personal_audio_cold_traffic.json to add the other two
    dispositions or raise panel_size toward the 200 ceiling."""
    pack = load_pack("personal_audio")
    return AudienceSpec(
        demographics=[_DEMOGRAPHIC],
        disposition_labels=[
            "loyalist_airdopes",
            "enthusiast_specs",
            "aspirant_airpods",
            "enthusiast_nothing_design",
            "skeptic_warranty",
        ],
        context_envelope=_CONTEXT_ENVELOPE,
        chaos_distribution=pack.default_chaos_distribution,
        panel_size=60,
    )


# Sample baseline funnel — conservative mid-market D2C-on-Meta placeholders.
# Replace with the customer's real account numbers when available.
_BASELINE_FUNNEL = {
    "stop_rate": 0.12,
    "click_rate": 0.020,
    "visit_rate": 0.016,
    "convert_rate": 0.006,
}


def main() -> None:
    print("=== scaffolding personal_audio v2 starter ===")

    # 1. Validate the artifact pack exists (the render engine needs it).
    pack = load_pack("personal_audio")
    print(f"  artifact pack OK — {len(pack.brand_landscape)} brands, "
          f"{len(pack.price_points)} price points")

    # 2. Entity model on disk.
    account = Account(account_id=ACCOUNT_ID, name="Demo — Boat Audio")
    account.validate()
    account.save()

    brand = BrandProfile(
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        categories=["personal_audio"],
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
        name="Cold acquisition traffic — personal audio",
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        spec=spec,
    )
    audience.validate()
    aud_path = audience.save()
    print(f"  saved audience: {len(spec.disposition_labels)} dispositions x "
          f"{len(spec.context_envelope)} contexts, panel_size="
          f"{spec.panel_size} -> {aud_path}")

    # 3. Standalone spec + baseline JSON for the batch_run.py --audience-spec flag.
    specs_dir = Path(__file__).resolve().parent.parent / "specs"
    specs_dir.mkdir(exist_ok=True)
    spec_path = specs_dir / "personal_audio_cold_traffic.json"
    spec_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))
    baseline_path = specs_dir / "personal_audio_baseline.json"
    baseline_path.write_text(json.dumps(_BASELINE_FUNNEL, indent=2))
    print(f"  standalone audience spec -> {spec_path}")
    print(f"  sample baseline funnel  -> {baseline_path}")

    print()
    print("Run a v2 Creative Read on the boat ad:")
    print()
    print("  .venv/bin/python batch_run.py \\")
    print("      --asset assets/boat_ad.png \\")
    print(f"      --audience-spec {spec_path.relative_to(specs_dir.parent)} \\")
    print(f"      --baseline-funnel {baseline_path.relative_to(specs_dir.parent)} \\")
    print("      --category personal_audio \\")
    print(f"      --account {ACCOUNT_ID} --brand-profile {BRAND_PROFILE_ID} \\")
    print(f"      --library-id {LIBRARY_ID} --audience-id {AUDIENCE_ID}")
    print()
    print("  (drop --yes off to see the confirmation surface before the credit "
          "debits; add it to auto-commit)")
    print()
    print("To use all 7 dispositions or a larger panel, edit "
          f"{spec_path.relative_to(specs_dir.parent)} directly.")
    print("PASS — personal_audio v2 starter scaffolded.")


if __name__ == "__main__":
    main()
