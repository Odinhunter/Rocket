"""Step-7 smoke: target classification on assets/boat_ad.png against
the personal_audio disposition pool.

Cost: ~$0.10 (Opus 4.7 vision).

Run: python tests/test_target_id_smoke.py
"""

from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent.config import AssetSpec, RunConfig
from agent.target_id import identify_target
from archetypes.disposition import list_dispositions


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    print("=== Target classification smoke ===")

    archetype = "urban_indian_male_22_30"
    category = "personal_audio"
    pool = list_dispositions(archetype, category)
    # Sample 5 dispositions
    rng = random.Random(71)
    pool = rng.sample(pool, 5)
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512 — ₹1,199 Special Deal"),
        archetype=archetype,
        category=category,
        dispositions_per_run=5,
        contexts_per_run=3,
        seeds_per_cell=1,
    )
    cfg.validate()
    print(f"  classifying {len(pool)} dispositions:")
    for label, _ in pool:
        print(f"    - {label}")

    t0 = time.time()
    tc = identify_target(pool, cfg)
    elapsed = time.time() - t0

    print(f"\n--- Result ({elapsed:.1f}s) ---")
    print(f"  inferred_target: {tc.inferred_target_description}")
    print(f"  target_reasoning: {tc.target_reasoning[:200]}...")
    print(f"  ambiguity_note: {tc.ambiguity_note}")
    print(f"  no_match_note:  {tc.no_match_note}")
    print(f"\n  per-disposition:")
    for d in tc.disposition_classifications:
        print(f"    [{d.classification:>9}] {d.disposition_label}")
        print(f"               reason: {d.reasoning[:140]}")

    # Validations
    assert len(tc.disposition_classifications) == len(pool), (
        f"expected {len(pool)} classifications, got {len(tc.disposition_classifications)}"
    )
    classifications = {d.classification for d in tc.disposition_classifications}
    assert classifications.issubset({"within", "outside", "ambiguous"}), (
        f"unexpected classifications: {classifications}"
    )
    # The Boat ad should produce at least 1 within and at least 1 outside (or ambiguous)
    within = [d for d in tc.disposition_classifications if d.classification == "within"]
    print(f"\n  within_count={len(within)}")
    # Soft assertion — the model could call all-ambiguous on a hedgy ad, but for boat we'd expect at least one within
    assert len(within) + sum(1 for d in tc.disposition_classifications if d.classification == "ambiguous") >= 1, (
        "expected at least one within or ambiguous classification"
    )

    print("\nPASS — target classification produces a valid TargetClassification.")


if __name__ == "__main__":
    main()
