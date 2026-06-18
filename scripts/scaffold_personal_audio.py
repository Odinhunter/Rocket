"""Scaffold a starter disposition library + AudienceSpec for the
personal_audio category.

────────────────────────────────────────────────────────────────────────
DISPOSITIONS WIPED 2026-05-26 — REWRITE UNDER PROTOCOL v2 BEFORE USE.
────────────────────────────────────────────────────────────────────────

All 7 prior dispositions (loyalist_airdopes, enthusiast_specs,
aspirant_airpods, enthusiast_nothing_design, pragmatist_urgent_replacement,
skeptic_warranty, purist_wired) were retired because they produced
consultant-voice agents under render-5 (see cmf_ad runs 2026-05-18 +
REVIEW.md §5 issue #1).

NEXT STEPS:
  1. Read docs/disposition_protocol_v2.md (the active protocol)
  2. Read data/voice_samples/personal_audio.md (manual mini-corpus —
     create this if not yet present; ~1-2 hr of curated Indian buyer
     voice from Amazon India / Reddit / YouTube)
  3. Rewrite the 6-7 dispositions below under the 5-line format
  4. Re-run this scaffold to regenerate runs/demo/boat_audio/
     entities/library.json
  5. Run a validation cmf_ad against the new library

This file's structure (entity tenancy IDs, demographic frame, context
envelope, baseline funnel) is preserved so the rewrite is plug-and-play
once new dispositions are authored.

Old commit reference: scaffold dispositions live at git rev 46c8f84
(personal_audio at lines 60-202) if you need to read them for the
rewrite — they describe the right stances even though the prose was
over-extreme.
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


# ---- Dispositions: WIPED 2026-05-26 — rewrite under protocol v2 ----
#
# See module docstring above for context. The 7 prior dispositions
# produced consultant-voice agents in cmf_ad runs and were all retired.
#
# To rewrite:
#   1. Read docs/disposition_protocol_v2.md (active protocol)
#   2. Curate data/voice_samples/personal_audio.md (manual mini-corpus,
#      ~20-30 real Indian buyer voice samples from Amazon India / Reddit
#      / YouTube — see protocol v2 §5 Lever 4)
#   3. Author 6-7 NamedDisposition entries in the dispositions list
#      below, following the 5-line format
#   4. Distribute across involvement tiers per protocol v2 §5 Lever 3
#      (~1 obsessive, ~2 high, ~1-2 medium, ~1-2 low — NOT all engaged)
#   5. Ishan reviews each disposition before commit (§5 Lever 5)
#
# Old anchors (for reference during rewrite) are at git rev 46c8f84:
#   git show 46c8f84:scripts/scaffold_personal_audio.py
# The stance/anchor-key LABELS were appropriate; the prose was extreme.

def _library() -> DispositionLibrary:
    dispositions: list[NamedDisposition] = [
        # TODO(protocol_v2): rewrite 6-7 personal_audio dispositions here.
        # Stance labels to populate (drawn from the wiped v1 set):
        #   - loyalist_airdopes              (high involvement, brand-loyal)
        #   - enthusiast_specs               (obsessive — rewrite carefully
        #                                     to avoid Notion-doc voice)
        #   - aspirant_airpods               (high involvement, identity-driven)
        #   - enthusiast_nothing_design      (high involvement, design-loyal)
        #   - pragmatist_urgent_replacement  (LOW — load-bearing for realism)
        #   - skeptic_warranty               (medium, value-skeptical)
        #   - purist_wired                   (LOW — the "this isn't for me" voice)
        # Per protocol v2, audience should NOT include all 7 — pick 6-ish
        # mixing involvement tiers per Lever 3.
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
    """Cold acquisition traffic AudienceSpec.

    disposition_labels EMPTY until dispositions are rewritten under
    protocol v2 (see module docstring). Per protocol v2 §5 Lever 3,
    the rewritten audience MUST mix involvement tiers — include at
    least one low-involvement disposition (pragmatist_urgent_replacement
    or purist_wired) so cold-traffic isn't over-indexed on engaged
    buyers."""
    pack = load_pack("personal_audio")
    return AudienceSpec(
        demographics=[_DEMOGRAPHIC],
        disposition_labels=[],  # populate after dispositions are written
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
    # Guard: refuse to run while dispositions are empty.
    # Remove this block once dispositions are rewritten under protocol v2.
    library = _library()
    if not library.dispositions:
        print("=== ABORT — personal_audio dispositions are wiped ===")
        print()
        print("This scaffold cannot run until 6-7 dispositions are")
        print("rewritten under docs/disposition_protocol_v2.md.")
        print()
        print("Running anyway would emit an empty library.json that")
        print("would break any subsequent audience build (panel.py")
        print("requires at least 1 NamedDisposition).")
        print()
        print("See module docstring for the rewrite checklist.")
        sys.exit(1)

    print("=== scaffolding personal_audio starter ===")

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
