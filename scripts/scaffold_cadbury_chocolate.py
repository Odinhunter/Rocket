"""Scaffold a starter disposition library + AudienceSpec for the
chocolate category, anchored to Cadbury's India buyer base.

────────────────────────────────────────────────────────────────────────
DISPOSITIONS WIPED 2026-05-26 — REWRITE UNDER PROTOCOL v2 BEFORE USE.
────────────────────────────────────────────────────────────────────────

All 6 prior dispositions (loyalist_dairymilk, upgrader_premium,
gifter_festive, skeptic_health_dark, gifter_silk_dating,
loyalist_nostalgic) were retired alongside boat_audio / bru_coffee
under the cross-library wipe — they share the same consultant-voice
risk pattern (anchor prose drifts to 99th-percentile behaviors).

NEXT STEPS:
  1. Read docs/disposition_protocol_v2.md (the active protocol)
  2. Create data/voice_samples/chocolate.md (manual mini-corpus —
     ~20-30 real Indian chocolate-buyer voices from Amazon India /
     Reddit / YouTube comments under FoodFood / unboxing channels;
     ~1-2 hr of curation)
  3. Rewrite the 6 dispositions below under the 5-line format
  4. Re-run this scaffold to regenerate runs/demo/cadbury_chocolate/
     entities/library.json
  5. Run a validation cadbury_ad against the new library

This file's structure (3 demographic frames, 4 context envelope, baseline
funnel) is preserved.

Old commit reference: git show 46c8f84:scripts/scaffold_cadbury_chocolate.py
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


# ---- Dispositions: WIPED 2026-05-26 — rewrite under protocol v2 ----
#
# See module docstring above for context. Old anchors at git rev 46c8f84.
#
# Stance labels to populate (drawn from wiped v1 set):
#   - loyalist_dairymilk          (low involvement, brand-loyal habit)
#   - upgrader_premium            (medium, identity-driven, skeptical of Cadbury)
#   - gifter_festive              (high involvement, occasion-driven, family stage)
#   - skeptic_health_dark         (medium, function-driven, anti-mass-market)
#   - gifter_silk_dating          (low/occasional, social-proof, young-adult)
#   - loyalist_nostalgic          (low/occasional, memory-anchored, identity)
#
# Per protocol v2 §5 Lever 3: chocolate library distribution is OK with
# more low-involvement than personal_audio — chocolate is a low-engagement
# CPG category by nature. But still avoid all-loyalist composition;
# include at least 1 skeptic + 1 upgrader/switcher voice.

def _library() -> DispositionLibrary:
    dispositions: list[NamedDisposition] = [
        # TODO(protocol_v2): rewrite 6 cadbury_chocolate dispositions here.
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
    """Cold acquisition traffic AudienceSpec for Cadbury chocolate.

    disposition_labels EMPTY until dispositions are rewritten under
    protocol v2 (see module docstring). Per protocol v2 §5 Lever 3,
    chocolate is OK with more low-involvement than personal_audio
    but should still include at least one skeptic + one upgrader voice."""
    pack = load_pack("chocolate")
    return AudienceSpec(
        demographics=[_DEMO_DATING_YOUNG, _DEMO_YOUNG_FAMILY, _DEMO_HOUSEHOLD],
        disposition_labels=[],  # populate after dispositions are written
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
    # Guard: refuse to run while dispositions are empty.
    # Remove this block once dispositions are rewritten under protocol v2.
    library = _library()
    if not library.dispositions:
        print("=== ABORT — cadbury_chocolate dispositions are wiped ===")
        print()
        print("This scaffold cannot run until 6 dispositions are")
        print("rewritten under docs/disposition_protocol_v2.md.")
        print()
        print("See module docstring for the rewrite checklist.")
        sys.exit(1)

    print("=== scaffolding cadbury_chocolate starter ===")

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
