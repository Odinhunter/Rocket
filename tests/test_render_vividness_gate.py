"""Phase 1 MAKE-OR-BREAK GATE — the vividness gate.

This is the single highest-risk checkpoint in the v2 refactor: do
vector-rendered personas preserve the vividness of the v1 hand-written
disposition prose? If they don't, the whole "schematize the population
model" thesis is wrong and Phase 1 sends us back to Phase 0.

This gate CANNOT be automated. The script:
  1. Hand-translates the 7 (urban_indian_male_22_30, coffee) v1 dispositions
     into 8-dimension DispositionVector points. That translation is itself
     the deliverable — it proves the taxonomy is expressive enough.
  2. Renders each vector through the Render Engine.
  3. Writes a BLIND-PAIRED comparison file: for each disposition, the v1
     original and the v2 render are shown as "A" and "B" in a randomized
     order, with the un-blinding key written to a separate file.

The user then sits down and rates the 7 blind pairs on three axes:
vividness, specificity, and "would a real person be described this way".

PASS: the rendered version is rated equal-or-better on >= 5 of 7
dispositions on EACH axis.

Cost: ~7 Sonnet render calls, ~$0.03.

Run: python tests/test_render_vividness_gate.py
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agent.artifact_pack import load_pack
from agent.render import render_persona_core
from agent.vectors import ChaosVector, DemographicPoint, DispositionVector
from archetypes.disposition import list_dispositions

_OUT = Path("runs/_vividness_gate")

# The urban_indian_male_22_30 demographic anchor (from archetypes/demographics.py),
# expressed as a DemographicPoint. Held constant across all 7 dispositions so
# the only thing varying is the disposition vector — exactly what the gate tests.
_DEMO = DemographicPoint(
    gender="male",
    age_band="25_34",
    income_tier="upper_mid",
    geography="Bangalore / Indiranagar, metro tier-1",
    occupation_hint="software engineer at a mid-stage SaaS startup",
    household_hint="shares a 3BHK with two flatmates, sends money home monthly",
)

# A neutral mid-chaos profile, also held constant — the gate isolates the
# disposition axis.
_CHAOS = ChaosVector(
    decision_velocity="moderate",
    suggestibility="medium",
    consistency="variable",
    risk_tolerance="balanced",
)

# Optional concrete anchors. The 8-dim vector captures *stance* but not the
# *object* of that stance — a filter-coffee loyalist and a d2c-roaster
# loyalist are the same vector. The anchor pins the object. Most
# dispositions need no anchor (their vector alone is unambiguous); these
# two do. (Added after the first gate run rendered filter_coffee_loyalist
# as a third-wave bean loyalist — the Phase 0 re-open.)
_ANCHORS: dict[str, str] = {
    "filter_coffee_loyalist": (
        "traditional South Indian filter coffee — the steel filter, degree "
        "kapi in a davara-tumbler, a chicory blend like Cothas. Considers the "
        "whole third-wave / Blue Tokai / Subko scene a fad that lost the plot."
    ),
    "cafe_regular_sachet_skeptical": (
        "the Blue Tokai cafe cold-brew habit — the cafe IS the product. "
        "Skeptical specifically of the sachet / instant FORMAT, which reads "
        "as a downgrade and a step toward Bru."
    ),
}

# The deliverable: the 7 v1 (urban_indian_male_22_30, coffee) dispositions
# hand-translated into 8-dimension DispositionVector points. If the taxonomy
# could not express one of these even WITH an anchor, that is a Phase 0
# re-open signal.
_VECTORS: dict[str, DispositionVector] = {
    "cafe_regular_sachet_skeptical": DispositionVector(
        category_relationship="regular",
        brand_stance="skeptical",
        price_orientation="quality_first",
        decision_driver="identity",
        category_involvement="high",
        prior_experience_valence="positive",
        channel_behavior="offline_first",
        life_stage="early_career",
    ),
    "filter_coffee_loyalist": DispositionVector(
        category_relationship="devotee",
        brand_stance="loyalist",
        price_orientation="quality_first",
        decision_driver="habit",
        category_involvement="high",
        prior_experience_valence="positive",
        channel_behavior="offline_first",
        life_stage="early_career",
    ),
    "office_bru_pragmatist": DispositionVector(
        category_relationship="regular",
        brand_stance="neutral",
        price_orientation="price_first",
        decision_driver="function",
        category_involvement="low",
        prior_experience_valence="neutral",
        channel_behavior="offline_first",
        life_stage="early_career",
    ),
    "d2c_skeptical_fast_scroller": DispositionVector(
        category_relationship="occasional",
        brand_stance="hostile",
        price_orientation="value_calculator",
        decision_driver="function",
        category_involvement="low",
        prior_experience_valence="burned",
        channel_behavior="marketplace",
        life_stage="early_career",
    ),
    "specialty_coffee_enthusiast": DispositionVector(
        category_relationship="devotee",
        brand_stance="favorable",
        price_orientation="quality_first",
        decision_driver="identity",
        category_involvement="obsessive",
        prior_experience_valence="positive",
        channel_behavior="d2c_direct",
        life_stage="early_career",
    ),
    "convenience_optimizer": DispositionVector(
        category_relationship="regular",
        brand_stance="favorable",
        price_orientation="value_calculator",
        decision_driver="function",
        category_involvement="medium",
        prior_experience_valence="neutral",
        channel_behavior="quick_commerce",
        life_stage="early_career",
    ),
    "early_adopter_d2c_tryer": DispositionVector(
        category_relationship="occasional",
        brand_stance="favorable",
        price_orientation="price_blind",
        decision_driver="novelty",
        category_involvement="medium",
        prior_experience_valence="mixed",
        channel_behavior="d2c_direct",
        life_stage="early_career",
    ),
}


def main() -> None:
    print("=== Phase 1 vividness gate — render + blind-pair ===")
    pack = load_pack("coffee")
    originals = dict(list_dispositions("urban_indian_male_22_30", "coffee"))

    missing = set(_VECTORS) - set(originals)
    if missing:
        raise AssertionError(
            f"hand-translation drift — these labels are not in the v1 pool: {missing}"
        )

    if _OUT.exists():
        shutil.rmtree(_OUT)
    _OUT.mkdir(parents=True, exist_ok=True)

    rng = random.Random(71)
    comparison_lines: list[str] = [
        "# Phase 1 Vividness Gate — Blind Comparison",
        "",
        "For each disposition below you see two persona descriptions, **A** and **B**.",
        "One is the v1 hand-written original; one is the v2 vector-rendered version.",
        "The order is randomized per disposition — the un-blinding key is in `key.json`.",
        "",
        "Rate each pair on three axes — **vividness**, **specificity**, and",
        "**\"would a real person be described this way\"** — and note which of A / B",
        "is better (or 'equal') on each.",
        "",
        "**PASS:** the v2 render is rated equal-or-better on >= 5 of 7 dispositions",
        "on EACH of the three axes.",
        "",
        "---",
        "",
    ]
    key: dict[str, dict] = {}

    for i, (label, vector) in enumerate(_VECTORS.items(), start=1):
        vector.validate()
        original = originals[label]
        rendered = render_persona_core(
            _DEMO, vector, _CHAOS, pack, anchor=_ANCHORS.get(label, "")
        )
        # Blind: randomize which of A/B is the original.
        original_is_a = rng.random() < 0.5
        a_text = original if original_is_a else rendered
        b_text = rendered if original_is_a else original
        key[label] = {
            "A": "v1_original" if original_is_a else "v2_render",
            "B": "v2_render" if original_is_a else "v1_original",
        }
        comparison_lines += [
            f"## {i}. `{label}`",
            "",
            "**A.**",
            "",
            a_text.strip(),
            "",
            "**B.**",
            "",
            b_text.strip(),
            "",
            "Vividness: ___    Specificity: ___    Real-person: ___",
            "",
            "---",
            "",
        ]
        print(f"  rendered {i}/7  {label}  ({len(rendered)} chars)")

    (_OUT / "comparison.md").write_text("\n".join(comparison_lines))
    (_OUT / "key.json").write_text(json.dumps(key, indent=2))

    print()
    print("  Blind comparison written to:")
    print(f"    {_OUT / 'comparison.md'}   (review this)")
    print(f"    {_OUT / 'key.json'}        (un-blinding key — open AFTER rating)")
    print()
    print("  THIS GATE IS MANUAL. Rate the 7 blind pairs. PASS = v2 render rated")
    print("  equal-or-better on >= 5 of 7 dispositions on EACH of the three axes.")
    print("  If it fails: iterate the render prompt, then pack richness; if the")
    print("  taxonomy itself can't express a disposition, that is a Phase 0 re-open.")


if __name__ == "__main__":
    main()
