"""Scaffold a starter disposition library + AudienceSpec for the
coffee category, anchored to Bru (HUL India)'s buyer base.

────────────────────────────────────────────────────────────────────────
DISPOSITIONS WIPED 2026-05-26 — REWRITE UNDER PROTOCOL v2 BEFORE USE.
────────────────────────────────────────────────────────────────────────

All 6 prior dispositions (loyalist_household_jar, switcher_nescafe,
upgrader_bru_gold, purist_filter, enthusiast_third_wave,
pragmatist_pantry) were retired alongside boat_audio + cadbury_chocolate
under the cross-library wipe — they share the same consultant-voice
risk pattern (anchor prose drifts to 99th-percentile behaviors).

NEXT STEPS:
  1. Read docs/disposition_protocol_v2.md (the active protocol)
  2. Create data/voice_samples/coffee.md (manual mini-corpus —
     ~20-30 real Indian coffee-buyer voices from Amazon India,
     Reddit r/IndianFood / r/India, YouTube comments under Indian
     café reviewers; ~1-2 hr of curation)
  3. Rewrite the 6 dispositions below under the 5-line format
  4. Re-run this scaffold to regenerate runs/demo/bru_coffee/
     entities/library.json
  5. Run a validation bru_ad against the new library

This file's structure (3 demographic frames, 4 context envelope, baseline
funnel) is preserved.

Old commit reference: git show 46c8f84:scripts/scaffold_bru_coffee.py
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


# ---- Dispositions: WIPED 2026-05-26 — rewrite under protocol v2 ----
#
# See module docstring above for context. Old anchors at git rev 46c8f84.
#
# Stance labels to populate (drawn from wiped v1 set):
#   - loyalist_household_jar   (low involvement, brand-loyal volume driver)
#   - switcher_nescafe         (medium, brand-skeptical of Bru)
#   - upgrader_bru_gold        (medium, identity-driven premium upgrade)
#   - purist_filter            (high involvement, anti-instant)
#   - enthusiast_third_wave    (obsessive, anti-instant)
#   - pragmatist_pantry        (low, function-only office user)
#
# Per protocol v2 §5 Lever 3: coffee has natural cohort variance from
# instant-volume buyer to specialty obsessive. The audience composition
# is fine; the OLD anchors were the consultant-voice problem.

def _library() -> DispositionLibrary:
    dispositions: list[NamedDisposition] = [
        # TODO(protocol_v2): rewrite 6 bru_coffee dispositions here.
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
    """Cold acquisition traffic AudienceSpec for Bru coffee.

    disposition_labels EMPTY until dispositions are rewritten under
    protocol v2 (see module docstring). Coffee has natural cohort
    variance across instant-volume buyer / Bru Gold upgrader / filter
    purist / specialty obsessive — the 6 stance labels listed in the
    _library() comment are appropriate to retain when rewriting."""
    pack = load_pack("coffee")
    return AudienceSpec(
        demographics=[
            _DEMO_SOUTH_HOUSEHOLD,
            _DEMO_TIER2_HOUSEHOLD,
            _DEMO_METRO_MILLENNIAL,
        ],
        disposition_labels=[],  # populate after dispositions are written
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
    # Guard: refuse to run while dispositions are empty.
    # Remove this block once dispositions are rewritten under protocol v2.
    library = _library()
    if not library.dispositions:
        print("=== ABORT — bru_coffee dispositions are wiped ===")
        print()
        print("This scaffold cannot run until 6 dispositions are")
        print("rewritten under docs/disposition_protocol_v2.md.")
        print()
        print("See module docstring for the rewrite checklist.")
        sys.exit(1)

    print("=== scaffolding bru_coffee starter ===")

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
