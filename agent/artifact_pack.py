"""Category Artifact Pack — the hand-curated moat.

A pack is a hand-curated knowledge object *per category* — real brands,
real prices, real retail channels, real communities, cultural references,
voice samples, behavioral priors, and the category's default chaos
distribution.

The Render Engine (agent/render.py) weaves artifacts FROM a pack into
persona prose. Hard rule: it may only use artifacts present in the pack —
it never invents brands, prices, or communities. That constraint is what
keeps vector-rendered personas vivid.

A pack lives in packs/<category>.py and exposes a module-level `PACK`
constant. load_pack(category) imports it.
"""

from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass, field

from agent.vectors import ChaosDistribution


@dataclass
class BrandLandscapeEntry:
    """One brand in the category and where it sits."""

    name: str
    tier: str  # e.g. "mass" / "mass-premium" / "premium" / "d2c-disruptor"
    note: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BrandLandscapeEntry":
        return cls(name=data["name"], tier=data["tier"], note=data["note"])


@dataclass
class PricePoint:
    """A real, concrete price anchor — the kind of detail that makes a
    persona read like a real person ('₹310 for a 200g Bru jar at the
    kirana')."""

    item: str
    price_inr: str  # string, not number — carries units/pack-size context
    channel: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PricePoint":
        return cls(item=data["item"], price_inr=data["price_inr"], channel=data["channel"])


@dataclass
class Community:
    """A real community / media surface where this category is discussed."""

    name: str
    kind: str  # e.g. "subreddit" / "youtuber" / "whatsapp" / "forum"
    note: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Community":
        return cls(name=data["name"], kind=data["kind"], note=data["note"])


@dataclass
class CategoryArtifactPack:
    """The hand-curated knowledge object for one category."""

    category: str
    brand_landscape: list[BrandLandscapeEntry] = field(default_factory=list)
    price_points: list[PricePoint] = field(default_factory=list)
    retail_channels: list[str] = field(default_factory=list)
    communities: list[Community] = field(default_factory=list)
    cultural_references: list[str] = field(default_factory=list)
    demographic_defaults: dict = field(default_factory=dict)
    voice_samples: list[str] = field(default_factory=list)
    behavioral_priors: str = ""
    default_chaos_distribution: ChaosDistribution | None = None

    def validate(self) -> None:
        if not self.category or not self.category.strip():
            raise ValueError("CategoryArtifactPack.category must be non-empty")
        if not self.brand_landscape:
            raise ValueError(
                f"pack {self.category!r} has empty brand_landscape — "
                "the render engine has nothing to weave"
            )
        if not self.price_points:
            raise ValueError(f"pack {self.category!r} has empty price_points")
        if not self.communities:
            raise ValueError(f"pack {self.category!r} has empty communities")
        if self.default_chaos_distribution is None:
            raise ValueError(
                f"pack {self.category!r} has no default_chaos_distribution"
            )
        self.default_chaos_distribution.validate()

    def brand_names(self) -> set[str]:
        """The set of brand-name tokens the render engine is allowed to use.
        agent/render.py:_validate_no_invented_artifacts checks against this."""
        return {b.name for b in self.brand_landscape}

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "brand_landscape": [b.to_dict() for b in self.brand_landscape],
            "price_points": [p.to_dict() for p in self.price_points],
            "retail_channels": list(self.retail_channels),
            "communities": [c.to_dict() for c in self.communities],
            "cultural_references": list(self.cultural_references),
            "demographic_defaults": dict(self.demographic_defaults),
            "voice_samples": list(self.voice_samples),
            "behavioral_priors": self.behavioral_priors,
            "default_chaos_distribution": (
                self.default_chaos_distribution.to_dict()
                if self.default_chaos_distribution is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CategoryArtifactPack":
        dcd = data.get("default_chaos_distribution")
        return cls(
            category=data["category"],
            brand_landscape=[
                BrandLandscapeEntry.from_dict(b)
                for b in data.get("brand_landscape", [])
            ],
            price_points=[
                PricePoint.from_dict(p) for p in data.get("price_points", [])
            ],
            retail_channels=list(data.get("retail_channels", [])),
            communities=[
                Community.from_dict(c) for c in data.get("communities", [])
            ],
            cultural_references=list(data.get("cultural_references", [])),
            demographic_defaults=dict(data.get("demographic_defaults", {})),
            voice_samples=list(data.get("voice_samples", [])),
            behavioral_priors=data.get("behavioral_priors", ""),
            default_chaos_distribution=(
                ChaosDistribution.from_dict(dcd) if dcd is not None else None
            ),
        )


def load_pack(category: str) -> CategoryArtifactPack:
    """Import packs/<category>.py and return its module-level PACK constant.

    Raises ValueError if the pack module is missing or malformed.
    """
    try:
        module = importlib.import_module(f"packs.{category}")
    except ModuleNotFoundError as exc:
        raise ValueError(
            f"no artifact pack for category {category!r} "
            f"(expected packs/{category}.py)"
        ) from exc
    pack = getattr(module, "PACK", None)
    if pack is None:
        raise ValueError(
            f"packs/{category}.py does not define a module-level PACK constant"
        )
    if not isinstance(pack, CategoryArtifactPack):
        raise ValueError(
            f"packs/{category}.py PACK is {type(pack)!r}, expected CategoryArtifactPack"
        )
    pack.validate()
    return pack
