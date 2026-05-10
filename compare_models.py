"""Side-by-side: Opus 4.7 vs Sonnet 4.6 across all 7 rounds, fixed persona.

Uses the same disposition × context for both runs so the only variable is
the model. Prints both runs sequentially for inspection.
"""

import json

from dotenv import load_dotenv

load_dotenv()

from agent.runner import run_agent
from archetypes.context import list_contexts
from archetypes.disposition import list_dispositions

ARCHETYPE = "urban_indian_male_22_30"
CATEGORY = "coffee"
AD_IMAGE_PATH = "assets/bt_image.png"
AD_TEXT = (
    "Blue Tokai has launched a specialty coffee concentrate called Drop. "
    "You pour one sachet into milk and get cafe-quality coffee in seconds. "
    "The packaging is a teal sachet with a peacock illustration, warm yellow "
    'photography, and the tagline "Tastes best with milk." Positioned as '
    "premium but accessible, ₹35-50 per cup equivalent."
)

DISPOSITION_LABEL = "cafe_regular_sachet_skeptical"
CONTEXT_LABEL = "sunday_hungover"

MODELS = [
    ("Opus 4.7", "claude-opus-4-7"),
    ("Sonnet 4.6", "claude-sonnet-4-6"),
]


def get_tuple(pool: list[tuple[str, str]], label: str) -> tuple[str, str]:
    for entry in pool:
        if entry[0] == label:
            return entry
    raise ValueError(f"{label!r} not found in pool")


def run_full_chain(model_name: str, model_id: str, disp, ctx) -> None:
    print(f"\n{'#' * 76}\n# {model_name}  ({model_id})\n{'#' * 76}")

    print("\n--- R1: Gut reaction ---")
    r1 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=1, image_path=AD_IMAGE_PATH,
        disposition=disp, context=ctx, model=model_id,
    )
    print(r1.output)

    print("\n--- R2: Comprehension audit ---")
    r2 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=2, image_path=AD_IMAGE_PATH,
        prior=r1, model=model_id,
    )
    print(r2.output)

    print("\n--- R3: Emotional mapping ---")
    r3 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=3, image_path=AD_IMAGE_PATH,
        prior=r2, model=model_id,
    )
    if r3 is None:
        print(f"[!! R3 FAILED ALL 3 ATTEMPTS on {model_name} — skipping R4-R7]")
        return
    print(json.dumps(r3.parsed, indent=2))

    print("\n--- R4: Stickiness ---")
    r4 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=4, image_path=AD_IMAGE_PATH,
        prior=r3, model=model_id,
    )
    print(r4.output)

    print("\n--- R5: Social calculus ---")
    r5 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=5, image_path=AD_IMAGE_PATH,
        prior=r4, model=model_id,
    )
    print(r5.output)

    print("\n--- R6: Purchase friction ---")
    r6 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=6, image_path=AD_IMAGE_PATH,
        prior=r5, model=model_id,
    )
    print(r6.output)

    print("\n--- R7: Insider critique ---")
    r7 = run_agent(
        ARCHETYPE, AD_TEXT, round_num=7, image_path=AD_IMAGE_PATH,
        prior=r6, model=model_id,
    )
    print(r7.output)


def main() -> None:
    disp = get_tuple(list_dispositions(ARCHETYPE, CATEGORY), DISPOSITION_LABEL)
    ctx = get_tuple(list_contexts(ARCHETYPE), CONTEXT_LABEL)

    print(f"Archetype:   {ARCHETYPE}")
    print(f"Disposition: {disp[0]}")
    print(f"Context:     {ctx[0]}")
    print(f"Ad:          Blue Tokai Drop ({AD_IMAGE_PATH})")

    for model_name, model_id in MODELS:
        run_full_chain(model_name, model_id, disp, ctx)


if __name__ == "__main__":
    main()
