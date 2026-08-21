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
import re
from dataclasses import asdict, dataclass, field, replace

from agent.vectors import ChaosDistribution

# Tokeniser for `cut_to_moments`. Keeps accented and possessive brand tokens
# together — Nescafé, Haldiram's, Lay's — so they match their price anchors.
_WORD_RE = re.compile(r"[A-Za-z0-9&'éÉ]+")


@dataclass
class BrandLandscapeEntry:
    """One brand in the category and where it sits.

    ⭐⭐ `moments` IS THE SUBSCRIPTION LIST — added 2026-08-21 for the F&B demand
    map. A brand does not belong to a category any more; it competes in MOMENTS,
    and Parle-G, a protein bar and a cup of Bru all meet at the afternoon dip
    because that is where they meet in life. Values are `FNB_MAP` keys.

    ⚠ DELIBERATELY LOWERCASE snake_case, and that is load-bearing, not cosmetic.
    `render._vocab_tokens` builds the invented-brand guardrail from every
    TitleCase token in this object, so anything TitleCase added here WIDENS the
    set of brand names a persona may invent without being caught. Moment keys
    add none.

    ⚠ Empty by default and `from_dict` tolerates its absence, so every pack
    written before the map still loads unchanged.
    """

    name: str
    tier: str  # e.g. "mass" / "mass-premium" / "premium" / "d2c-disruptor"
    note: str
    moments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BrandLandscapeEntry":
        return cls(name=data["name"], tier=data["tier"], note=data["note"],
                   moments=list(data.get("moments", [])))


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
    # ⚠⚠ `category` IS A MACHINE IDENTIFIER AND NOTHING ELSE. It names the module
    # (`packs/<category>.py`), keys the render cache, and gates the install guard.
    # ⭐⭐ IT MUST NEVER REACH A MODEL OR A CUSTOMER. Measured 2026-08-22: the slug
    # `fnb_world` was interpolated into the persona-facing context prose and a model
    # read it as "international food and drink" — for an INDIAN F&B pack — and every
    # agent in a $3.85 run was told the ad was for a foreign category.
    # ⭐ `market_name` is the prose half, and the pattern is already proven: the
    # demand grids have carried `market` ("Indian urban food and beverage") since
    # `#69`, and `_grid_brief` has always used it rather than the slug.
    # Pinned by `tests/test_identifiers_never_reach_a_reader.py`.
    market_name: str = ""
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
            "market_name": self.market_name,
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
            market_name=data.get("market_name", ""),
            market_stats=[dict(s) for s in data.get("market_stats", [])],
            occasions=[dict(o) for o in data.get("occasions", [])],
            journeys=[dict(j) for j in data.get("journeys", [])],
            price_architecture=[
                dict(p) for p in data.get("price_architecture", [])
            ],
            sources=[dict(s) for s in data.get("sources", [])],
            open_questions=list(data.get("open_questions", [])),
        )


def cut_to_moments(pack: CategoryArtifactPack,
                   moments: list[str] | set[str]) -> CategoryArtifactPack:
    """The world pack, narrowed to the moments actually in play.

    ⭐⭐ WHY THIS EXISTS. The F&B map is built once per market and is deliberately
    wide — all of food and beverage. But no brand ever faces the whole map: it
    subscribes to the handful of moments it competes in, and a persona reasoning
    about the 4pm dip has no business being handed a list of gifting hampers and
    infant formula. The map's own proposal puts it plainly: *"a 200-brand list
    would just become a menu."*

    ⚠⚠ AND THE SHARPER REASON, WHICH IS A GUARDRAIL ONE. `render._vocab_tokens`
    builds the invented-brand check out of every TitleCase token in the pack, so
    a wider brand list literally makes it EASIER for a persona to name something
    fabricated without being caught. Cutting the world to the moments in play
    tightens that check at the same time as it shortens the prompt.

    ⚠⚠ NOT WIRED INTO GENERATION, AND THAT IS DELIBERATE — 2026-08-21. Two
    documented mechanics forbid it there:

      1. `generate_audience._build` puts pack + grid + region in a CACHED prefix
         because they "never change across batches of one generation". Cutting
         per batch would change that prefix every batch and throw the cache away.
      2. `_cells()` walks moment-major on purpose, so a batch deliberately spans
         several moments; one-moment batches are the near-duplicate anti-pattern
         its own docstring warns about.

    ⭐ So the shape that shipped is: **subscribed per moment, whole world at
    generation, cut available at read time** — where a panel IS assembled for one
    ad and one set of moments. Pure function, no mutation, `replace`-based like
    `packs/health_nutrition_snacking_bev.py`, so "only the brand list differs" is
    true by construction rather than by a claim about a copy.

    ⚠ FAIL-OPEN ON UNSUBSCRIBED BRANDS. A brand with an empty `moments` list is
    KEPT, never dropped — silently deleting a brand because its author forgot to
    subscribe it would shrink the world invisibly, which is exactly the class of
    bug that produced the SuperYou failure. A pack that intends to be cut should
    assert its own brands are all subscribed; `tests/test_fnb_world.py` does.
    """
    wanted = set(moments)
    kept = [b for b in pack.brand_landscape
            if not b.moments or (set(b.moments) & wanted)]
    kept_names = {b.name for b in kept}
    dropped = [b for b in pack.brand_landscape if b.name not in kept_names]

    # A price anchor for a brand no longer in the world is incoherent — "₹425 for
    # a Starbucks frappuccino" in a pack with no Starbucks invites the persona to
    # name it anyway, and `render` would then flag a brand the pack itself
    # suggested. Anchors naming no dropped brand survive: they are the price
    # architecture, not brand facts.
    #
    # ⚠ MATCHING ON THE FULL BRAND NAME DOES NOT WORK, and a test caught it: the
    # brand is "Starbucks India" while the anchor reads "Starbucks tall
    # Americano", so the substring never matches. Match on TOKENS instead, and
    # subtract the tokens of surviving brands so a shared word cannot over-drop —
    # cutting "Amul Masti Chaas" must not also delete the "Amul Gold Tricone"
    # anchor when the Amul brand itself survives.
    # ⚠ Match on the brand's HEAD token, not on every token it contains. Matching
    # every token over-drops through generic words: "Britannia Marie Gold" would
    # take the "Amul Gold Butterscotch Tricone" anchor with it on the word "Gold".
    # The head is the brand a price anchor is actually about.
    def _head(name: str) -> str:
        for w in _WORD_RE.findall(name):
            if len(w) > 2 and w[0].isupper():
                return w
        return ""

    def _tokens(text: str) -> set[str]:
        return {w for w in _WORD_RE.findall(text) if len(w) > 2 and w[0].isupper()}

    exclusive = {_head(b.name) for b in dropped} - {_head(b.name) for b in kept} - {""}
    prices = [pp for pp in pack.price_points
              if not (_tokens(pp.item) | _tokens(pp.channel)) & exclusive]
    return replace(pack, brand_landscape=kept, price_points=prices)


def market_name_for(category: str) -> str:
    """The PROSE name of a market, for anything a model or a customer reads.

    ⚠⚠ Call this instead of interpolating `category` into a prompt or a screen.
    `category` is a module name; this is English. Falls back to the humanised
    slug only if a pack forgot to set one — and
    `tests/test_identifiers_never_reach_a_reader.py` asserts none has."""
    try:
        return load_pack(category).market_name or category.replace("_", " ")
    except ValueError:
        return category.replace("_", " ")


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
