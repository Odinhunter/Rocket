"""Entry point: run the gut-reaction agent against the Blue Tokai Drop ad."""

import json

from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env into os.environ

from agent.runner import run_agent


# Kept for the text-only fallback path; not used when an image is provided.
BLUE_TOKAI_DROP_AD = (
    "Blue Tokai has launched a specialty coffee concentrate called Drop. "
    "You pour one sachet into milk and get cafe-quality coffee in seconds. "
    "The packaging is a teal sachet with a peacock illustration, warm yellow "
    'photography, and the tagline "Tastes best with milk." Positioned as '
    "premium but accessible, ₹35-50 per cup equivalent."
)

AD_IMAGE_PATH = "assets/bt_image.png"


def main() -> None:
    archetype = "urban_indian_male_22_30"
    print(f"Archetype: {archetype}")
    print(f"Ad image:  {AD_IMAGE_PATH}\n")

    print("--- Round 1: Gut reaction ---")
    r1 = run_agent(
        archetype,
        BLUE_TOKAI_DROP_AD,
        round_num=1,
        image_path=AD_IMAGE_PATH,
        category="coffee",
    )
    print(f"[disposition: {r1.disposition_label}]")
    print(f"[context:     {r1.context_label}]")
    print(r1.output)

    print("\n--- Round 2: Comprehension audit ---")
    r2 = run_agent(
        archetype,
        BLUE_TOKAI_DROP_AD,
        round_num=2,
        image_path=AD_IMAGE_PATH,
        prior=r1,
    )
    print(f"[disposition: {r2.disposition_label}]")
    print(f"[context:     {r2.context_label}]")
    print(r2.output)

    print("\n--- Round 3: Emotional mapping ---")
    r3 = run_agent(
        archetype,
        BLUE_TOKAI_DROP_AD,
        round_num=3,
        image_path=AD_IMAGE_PATH,
        prior=r2,
    )
    if r3 is None:
        print("[round 3 failed all 3 attempts — see logs; skipping round 4]")
        return
    print(f"[disposition: {r3.disposition_label}]")
    print(f"[context:     {r3.context_label}]")
    print(json.dumps(r3.parsed, indent=2))

    print("\n--- Round 4: Stickiness (two days later) ---")
    r4 = run_agent(
        archetype,
        BLUE_TOKAI_DROP_AD,
        round_num=4,
        image_path=AD_IMAGE_PATH,
        prior=r3,
    )
    print(f"[disposition: {r4.disposition_label}]")
    print(f"[context:     {r4.context_label}]")
    print(r4.output)

    print("\n--- Round 5: Social calculus ---")
    r5 = run_agent(
        archetype,
        BLUE_TOKAI_DROP_AD,
        round_num=5,
        image_path=AD_IMAGE_PATH,
        prior=r4,
    )
    print(f"[disposition: {r5.disposition_label}]")
    print(f"[context:     {r5.context_label}]")
    print(r5.output)

    print("\n--- Round 6: Purchase friction mapping ---")
    r6 = run_agent(
        archetype,
        BLUE_TOKAI_DROP_AD,
        round_num=6,
        image_path=AD_IMAGE_PATH,
        prior=r5,
    )
    print(f"[disposition: {r6.disposition_label}]")
    print(f"[context:     {r6.context_label}]")
    print(r6.output)


if __name__ == "__main__":
    main()
