"""Phase 0 offline test: CategoryArtifactPack round-trips through
to_dict / from_dict and validate() catches an underpopulated pack.

This tests the SCHEMA only — no real pack data yet (that is Phase 1
curation). Run: python tests/test_artifact_pack_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import (
    BrandLandscapeEntry,
    CategoryArtifactPack,
    Community,
    PricePoint,
)
from agent.vectors import ChaosDistribution, ChaosProfile, ChaosVector


def _chaos_distribution() -> ChaosDistribution:
    def profile(label: str, dv: str) -> ChaosProfile:
        return ChaosProfile(
            label=label,
            vector=ChaosVector(
                decision_velocity=dv,
                suggestibility="medium",
                consistency="variable",
                risk_tolerance="balanced",
            ),
        )

    return ChaosDistribution(
        weighted=[
            (profile("impulsive", "impulsive"), 0.25),
            (profile("moderate", "moderate"), 0.50),
            (profile("deliberate", "deliberate"), 0.25),
        ]
    )


def _fixture_pack() -> CategoryArtifactPack:
    return CategoryArtifactPack(
        category="coffee",
        brand_landscape=[
            BrandLandscapeEntry(name="Bru", tier="mass", note="green-jar incumbent"),
            BrandLandscapeEntry(
                name="Blue Tokai", tier="d2c-disruptor", note="third-wave cafe + beans"
            ),
        ],
        price_points=[
            PricePoint(item="200g instant jar", price_inr="₹310", channel="kirana"),
            PricePoint(item="cold brew", price_inr="₹280", channel="Indiranagar cafe"),
        ],
        retail_channels=["kirana", "BigBasket", "Blinkit", "cafe"],
        communities=[
            Community(name="/r/coffee", kind="subreddit", note="pour-over discourse"),
        ],
        cultural_references=["third-wave coffee normalized in metros"],
        demographic_defaults={"city_tier_1_occupation": "software engineer"},
        voice_samples=["paying 380 for a latte in a wework-looking cafe"],
        behavioral_priors="fast-scrolls Instagram, suspicious of D2C visual language",
        default_chaos_distribution=_chaos_distribution(),
    )


def test_pack_roundtrip() -> None:
    pack = _fixture_pack()
    pack.validate()
    pack2 = CategoryArtifactPack.from_dict(pack.to_dict())
    assert pack.to_dict() == pack2.to_dict(), "CategoryArtifactPack round-trip mismatch"
    print("  OK  CategoryArtifactPack round-trip")


def test_pack_brand_names() -> None:
    pack = _fixture_pack()
    assert pack.brand_names() == {"Bru", "Blue Tokai"}
    print("  OK  CategoryArtifactPack.brand_names returns the allowed token set")


def test_validate_rejects_empty_brand_landscape() -> None:
    pack = _fixture_pack()
    pack.brand_landscape = []
    try:
        pack.validate()
    except ValueError as e:
        assert "brand_landscape" in str(e)
        print("  OK  validate rejects an empty brand_landscape:", e)
        return
    raise AssertionError("validate should reject an empty brand_landscape")


def test_validate_rejects_missing_chaos_distribution() -> None:
    pack = _fixture_pack()
    pack.default_chaos_distribution = None
    try:
        pack.validate()
    except ValueError as e:
        assert "default_chaos_distribution" in str(e)
        print("  OK  validate rejects a missing default_chaos_distribution:", e)
        return
    raise AssertionError("validate should reject a missing default_chaos_distribution")


def main() -> None:
    print("=== artifact pack schema smoke ===")
    test_pack_roundtrip()
    test_pack_brand_names()
    test_validate_rejects_empty_brand_landscape()
    test_validate_rejects_missing_chaos_distribution()
    print("PASS — artifact pack schema is locked.")


if __name__ == "__main__":
    main()
