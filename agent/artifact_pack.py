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
    """The hand-curated knowledge object for one category.

    ⚠ **THE PACK HAS TWO PROJECTIONS AND THEY ARE NOT THE SAME SET OF FIELDS.**

    1. **The prompt projection** — exactly seven fields reach a model:
       `brand_landscape`, `price_points`, `retail_channels`, `communities`,
       `cultural_references`, `voice_samples`, `behavioral_priors`. These are
       read by `render._persona_prompt`, by `render._vocab_tokens` (which is
       what the invented-artifact check is built from) and by
       `scripts/generate_audience.py:_pack_brief`. Keep them LEAN — every
       TitleCase token in them widens the set of brand names a persona is
       allowed to say, which weakens the check. That is why the
       `retail_channels` notes are deliberately lowercase.

    2. **The document projection** — everything below the marker. Sourced
       market facts, occasions, journeys, price architecture, provenance and
       the open questions. These exist for the artifact a brand team reads and
       argues with, and for wiring that has not been built yet. **They are
       consumed by NOTHING at runtime**, which is exactly why they can be as
       descriptive as they need to be without costing a token of prompt or
       loosening a guardrail.

    A pack is authored by us and then refined with the brand. `open_questions`
    is therefore a first-class field, not an apology: it is the agenda for that
    conversation, and a gap recorded there is worth more than a number guessed.
    """

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

    # ---- the document projection; reaches no prompt --------------------
    # Plain JSON-able structures on purpose: they round-trip through
    # to_dict/from_dict without a dataclass each, and nothing downstream
    # depends on their shape yet.
    market_stats: list[dict] = field(default_factory=list)
    occasions: list[dict] = field(default_factory=list)
    journeys: list[dict] = field(default_factory=list)
    price_architecture: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

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
            # document projection — see the class docstring
            "market_stats": [dict(s) for s in self.market_stats],
            "occasions": [dict(o) for o in self.occasions],
            "journeys": [dict(j) for j in self.journeys],
            "price_architecture": [dict(p) for p in self.price_architecture],
            "sources": [dict(s) for s in self.sources],
            "open_questions": list(self.open_questions),
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
            market_stats=[dict(s) for s in data.get("market_stats", [])],
            occasions=[dict(o) for o in data.get("occasions", [])],
            journeys=[dict(j) for j in data.get("journeys", [])],
            price_architecture=[
                dict(p) for p in data.get("price_architecture", [])
            ],
            sources=[dict(s) for s in data.get("sources", [])],
            open_questions=list(data.get("open_questions", [])),
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
