"""Phase 1 offline test: every category artifact pack loads, validates,
and is non-empty on the fields the render engine needs.

⚠ `health_wellness_nutrition` was MISSING from this list until 2026-08-12,
which meant the only pack that has ever run a paid panel was the one pack with
no load coverage at all. Any new pack under `packs/` belongs here.

Run: python tests/test_render_packs_load.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import CategoryArtifactPack, load_pack

_CATEGORIES = [
    "coffee", "chocolate", "personal_audio", "wellness",
    "health_wellness_nutrition",
]


def test_all_packs_load_and_validate() -> None:
    for cat in _CATEGORIES:
        pack = load_pack(cat)  # load_pack calls validate() internally
        assert isinstance(pack, CategoryArtifactPack)
        assert pack.category == cat
        assert len(pack.brand_landscape) >= 3, f"{cat}: thin brand_landscape"
        assert len(pack.price_points) >= 3, f"{cat}: thin price_points"
        assert len(pack.communities) >= 1, f"{cat}: no communities"
        assert pack.retail_channels, f"{cat}: no retail_channels"
        assert pack.behavioral_priors.strip(), f"{cat}: empty behavioral_priors"
        assert pack.default_chaos_distribution is not None
        pack.default_chaos_distribution.validate()
        print(
            f"  OK  {cat}: {len(pack.brand_landscape)} brands, "
            f"{len(pack.price_points)} prices, {len(pack.communities)} communities"
        )


def test_pack_roundtrips() -> None:
    for cat in _CATEGORIES:
        pack = load_pack(cat)
        pack2 = CategoryArtifactPack.from_dict(pack.to_dict())
        assert pack.to_dict() == pack2.to_dict(), f"{cat}: pack round-trip mismatch"
    print("  OK  all 4 packs round-trip through to_dict/from_dict")


def test_chaos_distributions_have_three_bands() -> None:
    """Every pack ships impulsive / moderate / deliberate — the three chaos
    bands L2 segment granularity fans out on."""
    for cat in _CATEGORIES:
        pack = load_pack(cat)
        labels = {p.label for p, _ in pack.default_chaos_distribution.weighted}
        assert labels == {"impulsive", "moderate", "deliberate"}, (
            f"{cat}: chaos bands are {labels}, expected impulsive/moderate/deliberate"
        )
    print("  OK  all 4 packs ship impulsive/moderate/deliberate chaos bands")


def test_load_pack_rejects_unknown_category() -> None:
    try:
        load_pack("__nonexistent_category__")
    except ValueError as e:
        assert "no artifact pack" in str(e)
        print("  OK  load_pack rejects an unknown category:", e)
        return
    raise AssertionError("load_pack should raise ValueError on an unknown category")


def main() -> None:
    print("=== render: artifact packs load smoke ===")
    test_all_packs_load_and_validate()
    test_pack_roundtrips()
    test_chaos_distributions_have_three_bands()
    test_load_pack_rejects_unknown_category()
    print("PASS — 4 category artifact packs curated and valid.")


if __name__ == "__main__":
    main()
