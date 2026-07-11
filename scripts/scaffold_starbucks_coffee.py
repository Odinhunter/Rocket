"""Scaffold the disposition library + AudienceSpec for `starbucks_coffee` —
the café / premium out-of-home end of the `coffee` category, anchored to
Starbucks India's competitive set (Starbucks / CCD / Costa / Blue Tokai /
Third Wave, plus the instant + filter poles).

────────────────────────────────────────────────────────────────────────
6 dispositions authored 2026-07-11 under docs/disposition_protocol_v2.md.
Grounded in data/voice_samples/coffee.md (live web research: Redseer /
Forbes India / onmanorama / Medium / thebetterindia + Starbucks India
menu). ALL marked provisional=True — PENDING ISHAN REVIEW (Protocol v2 §5
Lever 5) before the paid brand-building anchor run.
────────────────────────────────────────────────────────────────────────

Why this library exists: the v2.4 brand-building purpose needs an anchor
run on a *brand-subtle* emotional creative (Starbucks "The world has a
pause button") against a panel that SPANS engaged→scroll-past, so the
`brand_recall` probe can be shown to split ("loved the ad, forgot the
brand"). See HANDOFF Session 15 + docs/v2_4_purpose_taxonomy.md.

Design frame (see `dispositions_are_tg_gateways` memory): each disposition
gateways one attitudinal TG; the runtime render + reaction AI does the
rest. Cohort spread per Protocol v2 §5 Lever 3 — 2 HIGH-engage, 1 MEDIUM,
3 LOW/scroll-past — load-bearing on the reject voices so the panel isn't
"engaged buyers only", and broad enough for a brand-building BREADTH read:

  1. loyalist_starbucks_regular  HIGH   — third-place regular, the "usual"
  2. aspirant_cafe_culture       HIGH   — occasion/status-driven café-goer
  3. enthusiast_third_wave       MEDIUM — specialty snob, Starbucks-cool but craft-moved
  4. pragmatist_instant          LOW    — coffee = caffeine, café is someone else's world
  5. purist_filter               LOW    — South-Indian degree-kaapi loyalist
  6. skeptic_overpriced          LOW    — "status symbol", active price rejection

IMPORTANT — anchors are DEMOGRAPHIC-FREE + gender-neutral ("they"). Gender /
age / city / income / occupation come from the AudienceSpec.demographics
axis (render.py cross-products demographic × disposition × context and
requires identity to come from the demographic axis). The anchor pins the
*object* of the stance (the SKU, the price, the behaviour, the knowledge
ceiling) — not who the person is. Matches the health_wellness / bru pattern.

Run: python scripts/scaffold_starbucks_coffee.py
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
BRAND_PROFILE_ID = "starbucks_coffee"
LIBRARY_ID = "starbucks_coffee_lib_v1"
AUDIENCE_ID = "broad_reach_v1"        # brand-building uses a BROAD frame, not cold-acquisition
CATEGORY = "coffee"                    # reuses packs/coffee.py (café brands added 2026-07-11)


# ---- The 6 hand-mapped café / premium-coffee dispositions ----
#
# Each anchor is 5 lines (L1 CONTEXT / L2 CATEGORY / L3 KNOWLEDGE /
# L4 STANCE / L5 ANCHOR-BEHAVIOR), separated by blank lines, treated as a
# HARD CONSTRAINT by the render engine. Demographic-free, gender-neutral.
# Three DISTINCT rejection axes keep the LOW cohort non-overlapping:
# enthusiast = quality/craft snobbery · purist = tradition/culture · skeptic
# = price/status economics.

def _library() -> DispositionLibrary:
    dispositions = [
        # 1 — HIGH engage. Coherence: regular + loyalist + price_blind + habit
        # + medium involvement + positive = "my spot, my usual, I don't think
        # about the price." Cares about the PLACE, not the bean.
        NamedDisposition(
            label="loyalist_starbucks_regular",
            provisional=True,
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="loyalist",
                price_orientation="price_blind",
                decision_driver="habit",
                category_involvement="medium",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="early_career",
            ),
            anchor=(
                "Treats one particular Starbucks as a second office and living "
                "room — the barista half-knows the order and the week runs "
                "through that store.\n\n"
                "Goes two-to-four times a week for a fixed 'usual' — a Grande "
                "latte or cold brew — ordered on the app for the stars; picks "
                "the store for wifi, AC, and a corner seat.\n\n"
                "Knows their drink and the store vibe cold; does NOT care about "
                "bean origin, roast, or tasting notes, is NOT chasing 'the best "
                "coffee in the city' — the reliability and the place ARE the "
                "value.\n\n"
                "Wants a dependable spot to work, meet, and decompress; happily "
                "pays the premium because it buys the room, not just the cup; "
                "rejects 'it's just overpriced coffee' — they're buying time and "
                "space.\n\n"
                "Reorders the same Grande latte (~₹330 with the size bump) three "
                "mornings a week on the Starbucks app, collects the stars, and "
                "settles into the usual corner to take standups."
            ),
        ),
        # 2 — HIGH engage, the emotionally most-reachable. Coherence: occasional
        # + favorable + value_calculator + identity + low involvement + positive
        # = "café coffee is an aspirational treat; a small price to feel part of
        # it." A 'café person', not a 'coffee person'.
        NamedDisposition(
            label="aspirant_cafe_culture",
            provisional=True,
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="favorable",
                price_orientation="value_calculator",
                decision_driver="identity",
                category_involvement="low",
                prior_experience_valence="positive",
                channel_behavior="offline_first",
                life_stage="student",
            ),
            anchor=(
                "Café coffee is a treat and a small badge of arrival, not a "
                "daily habit; the outing itself is the plan and coffee is just "
                "the reason to gather.\n\n"
                "Goes once or twice a month, almost always with someone; orders "
                "the sweet blended end — a caramel frappuccino or a cold coffee "
                "— and photographs the cup and interior for stories.\n\n"
                "Knows the aspirational chains by name and which mall has one; "
                "does NOT know or care about roast or brew method; would call "
                "themselves a 'café person', not a 'coffee person'.\n\n"
                "Wants the feeling of the lifestyle the brand sells — "
                "sophisticated, unhurried, a little aspirational; sees ~₹300 as "
                "a small price to feel part of it; rejects nothing, just wants "
                "in.\n\n"
                "Built a weekend plan around a Starbucks caramel frappuccino "
                "(~₹320), posted the cup to a close-friends story, and lingered "
                "an hour because the café was the whole point."
            ),
        ),
        # 3 — MEDIUM. Coherence: regular + skeptical(of Starbucks) + quality_first
        # + function + obsessive + mixed = coffee snob who buys Blue Tokai and
        # side-eyes the chain, but can be genuinely craft-moved by a coffee-ritual
        # film. The interesting cell for a brand-building emotional ad.
        NamedDisposition(
            label="enthusiast_third_wave",
            provisional=True,
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="skeptical",
                price_orientation="quality_first",
                decision_driver="function",
                category_involvement="obsessive",
                prior_experience_valence="mixed",
                channel_behavior="d2c_direct",
                life_stage="early_career",
            ),
            anchor=(
                "Cares about the coffee itself — origin, roast, brew — and keeps "
                "a home setup; quietly thinks the big chains are over-roasted, "
                "over-sweet, and corporate.\n\n"
                "Drinks specialty daily: a Blue Tokai or Subko single-origin bag "
                "(~₹550 / 250g) on an AeroPress at home, plus a loyal third-wave "
                "café where they order a flat white and silently grade it.\n\n"
                "Knows origin, roast levels, and the major Indian roasters; does "
                "NOT cup professionally, does NOT roast at home, is NOT a barista "
                "— the enthusiastic hobbyist, not the trade.\n\n"
                "Wants provenance and craft in the cup; rejects 'you're paying "
                "for the logo, not the coffee'; will still grant a beautiful "
                "coffee-ritual ad real emotional credit while side-eyeing the "
                "chain behind it.\n\n"
                "Buys a Blue Tokai Vienna-roast 250g (~₹550) monthly and brews "
                "it at home, but will admit a genuinely lovely coffee film moved "
                "them — then note the beans were probably nothing special."
            ),
        ),
        # 4 — LOW, indifferent. Coherence: regular(instant) + neutral +
        # price_first + habit + low + neutral = "coffee is my morning Nescafé;
        # café coffee is someone else's ₹300 thing." Load-bearing scroll-past.
        NamedDisposition(
            label="pragmatist_instant",
            provisional=True,
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="price_first",
                decision_driver="habit",
                category_involvement="low",
                prior_experience_valence="neutral",
                channel_behavior="quick_commerce",
                life_stage="family",
            ),
            anchor=(
                "Coffee is a function — the cup that switches the morning on; the "
                "café world reads as someone else's ₹300 ritual, met without any "
                "resentment.\n\n"
                "Drinks one or two instant cups a day at home or the office "
                "pantry; a Nescafé or Bru jar (~₹300–600) topped up on the "
                "monthly grocery run or Blinkit; enters a café only when someone "
                "else suggests it.\n\n"
                "Knows their instant brand and 'strong versus milky'; does NOT "
                "tell a latte from a flat white, does NOT care about beans; not "
                "hostile to cafés, just not their thing.\n\n"
                "Wants cheap, fast, reliable caffeine; sees café coffee as a "
                "rare, slightly baffling splurge — 'that's ₹300 for a coffee I "
                "make for ₹5'; rejects the idea that coffee has to be an "
                "event.\n\n"
                "Refills a Nescafé Classic jar (~₹300) on the Blinkit grocery "
                "order, drinks it black at the desk, and scrolls straight past a "
                "café ad without registering the brand."
            ),
        ),
        # 5 — LOW, traditional. Coherence: regular(filter) + neutral +
        # quality_first + identity + medium + neutral = degree-kaapi cultural
        # pride; cafés are a pricey novelty. Objection is CULTURAL (distinct from
        # #6's economic one). Load-bearing scroll-past.
        NamedDisposition(
            label="purist_filter",
            provisional=True,
            vector=DispositionVector(
                category_relationship="regular",
                brand_stance="neutral",
                price_orientation="quality_first",
                decision_driver="identity",
                category_involvement="medium",
                prior_experience_valence="neutral",
                channel_behavior="offline_first",
                life_stage="settled",
            ),
            anchor=(
                "Filter 'degree' kaapi is the real thing — a daily ritual tied "
                "to family and morning; the café world is a pricey novelty held "
                "at a proud arm's length.\n\n"
                "Sets the decoction overnight in a steel filter and serves it in "
                "a davara-tumbler each morning; buys a chicory-forward filter "
                "powder (Cothas or a trusted local roaster) by the kilo.\n\n"
                "Deep on filter coffee — decoction strength, the chicory ratio, "
                "the pour; does NOT track café menus or espresso drinks, does "
                "NOT see the point of ₹300 cups; anti-café-price, not "
                "anti-coffee.\n\n"
                "Believes real coffee is made at home the way it always has "
                "been; sees the cappuccino chains as a 'bloated price tag' on "
                "the actual thing; a café visit is a rare social concession, "
                "ordered with mild disapproval.\n\n"
                "Makes two davara-tumblers of filter kaapi before 8am from a "
                "~₹400/kg Cothas blend, and would sooner skip coffee than pay "
                "café prices for a weaker cup."
            ),
        ),
        # 6 — LOW, hostile-to-premium. Coherence: occasional + skeptical +
        # value_calculator + function + low + mixed = "₹300 for oversweet coffee
        # is a status scam." Objection is ECONOMIC/status (distinct from #5's
        # cultural one and #3's quality one). The emotional pitch may irritate.
        NamedDisposition(
            label="skeptic_overpriced",
            provisional=True,
            vector=DispositionVector(
                category_relationship="occasional",
                brand_stance="skeptical",
                price_orientation="value_calculator",
                decision_driver="function",
                category_involvement="low",
                prior_experience_valence="mixed",
                channel_behavior="offline_first",
                life_stage="early_career",
            ),
            anchor=(
                "Has sharp opinions about the big coffee chains and a low "
                "tolerance for the status game; recognises the brand instantly "
                "and rejects the premium on principle.\n\n"
                "Goes only when dragged — a friend's plan or a meeting — and "
                "orders the cheapest thing on the board or complains about the "
                "bill; would never initiate a café visit.\n\n"
                "Knows the pricing and the status game cold; does NOT engage "
                "with roast or craft — that isn't the objection; the problem is "
                "economic and cultural, not the coffee's quality per se.\n\n"
                "Wants coffee, not a lifestyle tax; treats 'pay a premium to "
                "feel sophisticated' as exactly the thing being refused; an "
                "emotional 'slow down and connect' café pitch mostly "
                "irritates.\n\n"
                "Got dragged to a Starbucks, clocked ₹300 on a latte pricier "
                "than in the US, ordered a plain americano, and spent the visit "
                "calling it 'a status symbol for people who can't afford a BMW'."
            ),
        ),
    ]
    return DispositionLibrary(
        library_id=LIBRARY_ID,
        brand_profile_id=BRAND_PROFILE_ID,
        account_id=ACCOUNT_ID,
        dispositions=dispositions,
    )


# ---- Demographics: 3 addressability frames spanning the café-coffee buyer ----
#
# They own gender / age / income / geography / occupation and cross-product
# with the (demographic-free) dispositions, so some atypical cells appear
# (e.g. a filter-purist metro-professional) — valid panel members, and how
# the engine is designed to work (panel.py).

_DEMO_METRO_PROFESSIONAL = DemographicPoint(
    gender="any",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Mumbai / Bangalore / Delhi metro",
    occupation_hint="early/mid-career — corporate, startup, consulting",
    household_hint="single or dating; 1-2BHK in the metro core",
)

_DEMO_ASPIRING_YOUNG = DemographicPoint(
    gender="any",
    age_band="18_24",
    income_tier="lower_mid",
    geography="tier-1 / tier-2 city",
    occupation_hint="college student or early-career; stretches for the café outing",
    household_hint="lives with family or flatmates; limited spare cash",
)

_DEMO_SETTLED_SOUTH = DemographicPoint(
    gender="any",
    age_band="35_44",
    income_tier="affluent",
    geography="Chennai / Bangalore / Hyderabad metro",
    occupation_hint="settled professional; runs a household",
    household_hint="married with 1-2 kids; owns a home; filter-coffee kitchen",
)


# ---- Context envelope: 4 passive-scroll states where a brand film is met ----
#
# Brand-building leans on a BROAD, fair-attention read (not the direct-sell
# 'actively_shopping' frame). A mix from a relaxed weekend scroll (fair
# resonance read) to a drained commute (the suppressed-attention case that
# feeds the 'engaged-but-forgot-the-brand' recall cell).

_CONTEXT_ENVELOPE = [
    NamedContext(
        label="evening_couch_scroll",
        vector=ContextVector(
            attention_level="low", device_posture="couch",
            intent_state="passive_browse", energy_state="neutral",
            social_setting="family_present",
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
    NamedContext(
        label="commute_scroll",
        vector=ContextVector(
            attention_level="low", device_posture="commute",
            intent_state="killing_time", energy_state="drained",
            social_setting="public",
        ),
    ),
    NamedContext(
        label="lazy_morning_scroll",
        vector=ContextVector(
            attention_level="medium", device_posture="lying_down",
            intent_state="killing_time", energy_state="neutral",
            social_setting="alone",
        ),
    ),
]


def _audience_spec(pack) -> AudienceSpec:
    """Broad-reach brand-building panel — starbucks_coffee.

    All 6 dispositions (2 HIGH-engage, 1 MEDIUM, 3 LOW/scroll-past),
    deliberately reject-heavy so the panel isn't engaged-buyers-only and
    broad enough for the brand-building BREADTH read (resonance × brand
    recall over the whole panel, per agent/decision.py resonance_brand_memory).
    """
    return AudienceSpec(
        demographics=[
            _DEMO_METRO_PROFESSIONAL,
            _DEMO_ASPIRING_YOUNG,
            _DEMO_SETTLED_SOUTH,
        ],
        disposition_labels=[
            "loyalist_starbucks_regular",
            "aspirant_cafe_culture",
            "enthusiast_third_wave",
            "pragmatist_instant",
            "purist_filter",
            "skeptic_overpriced",
        ],
        context_envelope=_CONTEXT_ENVELOPE,
        chaos_distribution=pack.default_chaos_distribution,
        panel_size=100,
    )


# Conservative café/brand-ad-on-Meta baseline placeholders. A brand film's
# direct-response funnel is intentionally weak (it isn't a direct-sell ad);
# these exist only so the run has a funnel scaffold. Not load-bearing for the
# brand-building metric.
_BASELINE_FUNNEL = {
    "stop_rate": 0.10,
    "click_rate": 0.014,
    "visit_rate": 0.007,
    "convert_rate": 0.003,
}


def main() -> None:
    print("=== scaffolding starbucks_coffee (café / premium) starter ===")

    # 1. Entity model on disk — the library does NOT depend on the pack.
    account = Account(account_id=ACCOUNT_ID, name="Demo — Starbucks Coffee (café)")
    account.validate()
    account.save()

    library = _library()
    library.validate()
    lib_path = library.save()
    print(f"  disposition library: {len(library.dispositions)} hand-mapped "
          f"dispositions (all provisional) -> {lib_path}")

    # 2. AudienceSpec + BrandProfile need the artifact pack.
    try:
        pack = load_pack(CATEGORY)
    except Exception as exc:  # noqa: BLE001
        print()
        print(f"  artifact pack '{CATEGORY}' not found ({exc.__class__.__name__}).")
        print("  Library is saved. packs/coffee.py must exist (it does).")
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
        name="Broad reach (brand-building) — starbucks coffee",
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
    spec_path = specs_dir / "starbucks_coffee_broad_reach.json"
    spec_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))
    baseline_path = specs_dir / "starbucks_coffee_baseline.json"
    baseline_path.write_text(json.dumps(_BASELINE_FUNNEL, indent=2))
    print(f"  standalone audience spec -> {spec_path}")
    print(f"  sample baseline funnel  -> {baseline_path}")

    print()
    print("PASS — starbucks_coffee starter scaffolded (dispositions PROVISIONAL,")
    print("pending review before the paid brand-building anchor run).")


if __name__ == "__main__":
    main()
