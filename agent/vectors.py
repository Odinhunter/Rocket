"""The four standardized population axes for Rocket.

Every agent in a panel is one point across four axes:

  1. Demographics  — addressability (gender, age, income, geography).
  2. Disposition   — category-attitudinal stance, an 8-dimension vector.
  3. Context       — attention state, a 5-dimension vector.
  4. Chaos         — behavioral style, a 4-dimension vector; a run carries a
                     *distribution* over named chaos profiles.

Structured vectors are comparable across runs (so a benchmark library and
calibration become possible), renderable on demand (so a customer can
compose an audience on the spot), and the substrate the funnel projection
is built on.

Every vector enum carries `"unspecified"` as an escape hatch so Phase 1
artifact-pack curation can surface a missing value without forcing a
schema re-lock. Geography is a free string for the same reason.

Serialization mirrors agent/schema.py: plain dict to_dict/from_dict, no
pydantic. validate() raises ValueError on a bad value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

# Render protocol version. Bumps when the vector schemas OR the render
# engine prompt change — both invalidate cached persona renders.
VECTOR_SCHEMA_VERSION = "rocket-2.0.0"

_ESCAPE = "unspecified"


# ---- Axis 1: Demographics (addressability) ----

Gender = Literal["male", "female", "nonbinary", "any", "unspecified"]
AgeBand = Literal["18_24", "25_34", "35_44", "45_54", "55_plus", "unspecified"]
IncomeTier = Literal[
    "mass", "lower_mid", "upper_mid", "affluent", "premium", "unspecified"
]

_VALID_GENDER = {"male", "female", "nonbinary", "any", _ESCAPE}
_VALID_AGE_BAND = {"18_24", "25_34", "35_44", "45_54", "55_plus", _ESCAPE}
_VALID_INCOME_TIER = {"mass", "lower_mid", "upper_mid", "affluent", "premium", _ESCAPE}


@dataclass
class DemographicPoint:
    """One addressability point. gender/age_band/income_tier are enumerated;
    geography is free string (region taxonomies vary too much to enumerate).
    occupation_hint / household_hint are optional render-engine seeds drawn
    from the artifact pack's demographic_defaults."""

    gender: Gender
    age_band: AgeBand
    income_tier: IncomeTier
    geography: str
    occupation_hint: str = ""
    household_hint: str = ""

    def validate(self) -> None:
        if self.gender not in _VALID_GENDER:
            raise ValueError(f"DemographicPoint.gender invalid: {self.gender!r}")
        if self.age_band not in _VALID_AGE_BAND:
            raise ValueError(f"DemographicPoint.age_band invalid: {self.age_band!r}")
        if self.income_tier not in _VALID_INCOME_TIER:
            raise ValueError(
                f"DemographicPoint.income_tier invalid: {self.income_tier!r}"
            )
        if not self.geography or not self.geography.strip():
            raise ValueError("DemographicPoint.geography must be a non-empty string")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DemographicPoint":
        return cls(
            gender=data["gender"],
            age_band=data["age_band"],
            income_tier=data["income_tier"],
            geography=data["geography"],
            occupation_hint=data.get("occupation_hint", ""),
            household_hint=data.get("household_hint", ""),
        )


# ---- Axis 2: Disposition (category-attitudinal) — 8-dimension vector ----

CategoryRelationship = Literal[
    "devotee", "regular", "occasional", "lapsed", "never", "unspecified"
]
BrandStance = Literal[
    "loyalist", "favorable", "neutral", "skeptical", "hostile", "unspecified"
]
PriceOrientation = Literal[
    "price_first", "value_calculator", "quality_first", "price_blind", "unspecified"
]
DecisionDriver = Literal[
    "function", "identity", "social_proof", "habit", "novelty", "unspecified"
]
CategoryInvolvement = Literal["low", "medium", "high", "obsessive", "unspecified"]
PriorExperienceValence = Literal[
    "burned", "mixed", "neutral", "positive", "delighted", "unspecified"
]
ChannelBehavior = Literal[
    "quick_commerce", "marketplace", "d2c_direct", "offline_first", "unspecified"
]
LifeStage = Literal[
    "student", "early_career", "settled", "family", "empty_nest", "unspecified"
]

_VALID_DISPOSITION: dict[str, set[str]] = {
    "category_relationship": {
        "devotee", "regular", "occasional", "lapsed", "never", _ESCAPE
    },
    "brand_stance": {
        "loyalist", "favorable", "neutral", "skeptical", "hostile", _ESCAPE
    },
    "price_orientation": {
        "price_first", "value_calculator", "quality_first", "price_blind", _ESCAPE
    },
    "decision_driver": {
        "function", "identity", "social_proof", "habit", "novelty", _ESCAPE
    },
    "category_involvement": {"low", "medium", "high", "obsessive", _ESCAPE},
    "prior_experience_valence": {
        "burned", "mixed", "neutral", "positive", "delighted", _ESCAPE
    },
    "channel_behavior": {
        "quick_commerce", "marketplace", "d2c_direct", "offline_first", _ESCAPE
    },
    "life_stage": {
        "student", "early_career", "settled", "family", "empty_nest", _ESCAPE
    },
}


@dataclass
class DispositionVector:
    """An 8-dimension point describing how a person relates to a product
    category. The render engine turns this (plus demographics, chaos, and
    the category artifact pack) into vivid first-person persona prose."""

    category_relationship: CategoryRelationship
    brand_stance: BrandStance
    price_orientation: PriceOrientation
    decision_driver: DecisionDriver
    category_involvement: CategoryInvolvement
    prior_experience_valence: PriorExperienceValence
    channel_behavior: ChannelBehavior
    life_stage: LifeStage

    def validate(self) -> None:
        for dim, valid in _VALID_DISPOSITION.items():
            value = getattr(self, dim)
            if value not in valid:
                raise ValueError(
                    f"DispositionVector.{dim} invalid: {value!r} "
                    f"(valid: {sorted(valid)})"
                )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DispositionVector":
        return cls(**{dim: data[dim] for dim in _VALID_DISPOSITION})


@dataclass
class NamedDisposition:
    """A library disposition: a named, coherent point in DispositionVector
    space. `provisional` marks an on-the-spot render awaiting team review.
    `notes` is a curator note — never fed to the render engine as artifact.

    `anchor` is an optional concrete pointer into the category — the
    specific brand, sub-category, or object this disposition's relationship
    is oriented around. The abstract 8-dimension vector captures *stance*
    (devotee, loyalist, skeptical) but not the *object* of that stance:
    "loyal to traditional filter coffee" and "loyal to a third-wave d2c
    roaster" are the same vector. When a disposition is defined by its
    relationship to a specific thing, the anchor pins it and the render
    engine treats it as a hard constraint. Empty when the vector alone is
    sufficient (most dispositions). Added after the Phase 1 vividness gate
    showed the vector could not, on its own, distinguish a filter-coffee
    loyalist from a specialty-bean loyalist."""

    label: str
    vector: DispositionVector
    provisional: bool = False
    notes: str = ""
    anchor: str = ""

    def validate(self) -> None:
        if not self.label or not self.label.strip():
            raise ValueError("NamedDisposition.label must be non-empty")
        self.vector.validate()

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "vector": self.vector.to_dict(),
            "provisional": self.provisional,
            "notes": self.notes,
            "anchor": self.anchor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NamedDisposition":
        return cls(
            label=data["label"],
            vector=DispositionVector.from_dict(data["vector"]),
            provisional=bool(data.get("provisional", False)),
            notes=data.get("notes", ""),
            anchor=data.get("anchor", ""),
        )


# ---- Axis 3: Context (attention state) — 5-dimension vector ----

AttentionLevel = Literal["absent", "low", "medium", "high", "unspecified"]
DevicePosture = Literal[
    "lying_down", "couch", "commute", "desk", "walking", "unspecified"
]
IntentState = Literal[
    "killing_time", "passive_browse", "task_focused", "actively_shopping",
    "unspecified",
]
EnergyState = Literal["drained", "low", "neutral", "alert", "wired", "unspecified"]
SocialSetting = Literal[
    "alone", "family_present", "public", "with_friends", "unspecified"
]

_VALID_CONTEXT: dict[str, set[str]] = {
    "attention_level": {"absent", "low", "medium", "high", _ESCAPE},
    "device_posture": {
        "lying_down", "couch", "commute", "desk", "walking", _ESCAPE
    },
    "intent_state": {
        "killing_time", "passive_browse", "task_focused", "actively_shopping",
        _ESCAPE,
    },
    "energy_state": {"drained", "low", "neutral", "alert", "wired", _ESCAPE},
    "social_setting": {
        "alone", "family_present", "public", "with_friends", _ESCAPE
    },
}


@dataclass
class ContextVector:
    """A 5-dimension point describing the attention state in which the ad is
    encountered. A run's 'context envelope' is 3-5 of these."""

    attention_level: AttentionLevel
    device_posture: DevicePosture
    intent_state: IntentState
    energy_state: EnergyState
    social_setting: SocialSetting

    def validate(self) -> None:
        for dim, valid in _VALID_CONTEXT.items():
            value = getattr(self, dim)
            if value not in valid:
                raise ValueError(
                    f"ContextVector.{dim} invalid: {value!r} "
                    f"(valid: {sorted(valid)})"
                )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ContextVector":
        return cls(**{dim: data[dim] for dim in _VALID_CONTEXT})


@dataclass
class NamedContext:
    """A named point in ContextVector space."""

    label: str
    vector: ContextVector

    def validate(self) -> None:
        if not self.label or not self.label.strip():
            raise ValueError("NamedContext.label must be non-empty")
        self.vector.validate()

    def to_dict(self) -> dict:
        return {"label": self.label, "vector": self.vector.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "NamedContext":
        return cls(
            label=data["label"],
            vector=ContextVector.from_dict(data["vector"]),
        )


# ---- Axis 4: Chaos (behavioral style) — 4-dimension vector ----

DecisionVelocity = Literal["impulsive", "moderate", "deliberate", "unspecified"]
Suggestibility = Literal["low", "medium", "high", "unspecified"]
Consistency = Literal["erratic", "variable", "steady", "unspecified"]
RiskTolerance = Literal["averse", "balanced", "seeking", "unspecified"]

_VALID_CHAOS: dict[str, set[str]] = {
    "decision_velocity": {"impulsive", "moderate", "deliberate", _ESCAPE},
    "suggestibility": {"low", "medium", "high", _ESCAPE},
    "consistency": {"erratic", "variable", "steady", _ESCAPE},
    "risk_tolerance": {"averse", "balanced", "seeking", _ESCAPE},
}


@dataclass
class ChaosVector:
    """A 4-dimension point describing decision-making style — separate from
    disposition (a filter-coffee loyalist can be impulsive or deliberate).
    Governs the R7 behavioral signal more than the qualitative reaction."""

    decision_velocity: DecisionVelocity
    suggestibility: Suggestibility
    consistency: Consistency
    risk_tolerance: RiskTolerance

    def validate(self) -> None:
        for dim, valid in _VALID_CHAOS.items():
            value = getattr(self, dim)
            if value not in valid:
                raise ValueError(
                    f"ChaosVector.{dim} invalid: {value!r} (valid: {sorted(valid)})"
                )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChaosVector":
        return cls(**{dim: data[dim] for dim in _VALID_CHAOS})


@dataclass
class ChaosProfile:
    """A named point in ChaosVector space. `label` doubles as the chaos-band
    key for L2 segment granularity (e.g. 'impulsive' / 'moderate' /
    'deliberate')."""

    label: str
    vector: ChaosVector

    def validate(self) -> None:
        if not self.label or not self.label.strip():
            raise ValueError("ChaosProfile.label must be non-empty")
        self.vector.validate()

    def to_dict(self) -> dict:
        return {"label": self.label, "vector": self.vector.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "ChaosProfile":
        return cls(
            label=data["label"],
            vector=ChaosVector.from_dict(data["vector"]),
        )


# Weights summing to within this tolerance of 1.0 are accepted.
_WEIGHT_TOLERANCE = 1e-6


@dataclass
class ChaosDistribution:
    """The mix of behavioral styles in a population. A real CPG audience is
    more impulsive; B2B is more deliberate. The artifact pack ships a
    per-category default; the customer can override in 'advanced' mode.

    weighted: list of (ChaosProfile, weight) — weights must sum to ~1.0.
    """

    weighted: list[tuple[ChaosProfile, float]] = field(default_factory=list)

    def validate(self) -> None:
        if not self.weighted:
            raise ValueError("ChaosDistribution must have at least one profile")
        labels = [p.label for p, _ in self.weighted]
        if len(labels) != len(set(labels)):
            raise ValueError(
                f"ChaosDistribution has duplicate profile labels: {labels}"
            )
        for profile, weight in self.weighted:
            profile.validate()
            if weight < 0:
                raise ValueError(
                    f"ChaosDistribution weight for {profile.label!r} is negative"
                )
        total = sum(w for _, w in self.weighted)
        if abs(total - 1.0) > _WEIGHT_TOLERANCE:
            raise ValueError(
                f"ChaosDistribution weights must sum to 1.0, got {total}"
            )

    def profile_for(self, label: str) -> ChaosProfile:
        for profile, _ in self.weighted:
            if profile.label == label:
                return profile
        raise KeyError(f"no chaos profile labelled {label!r}")

    def to_dict(self) -> dict:
        return {
            "weighted": [
                {"profile": p.to_dict(), "weight": w} for p, w in self.weighted
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChaosDistribution":
        return cls(
            weighted=[
                (ChaosProfile.from_dict(entry["profile"]), float(entry["weight"]))
                for entry in data.get("weighted", [])
            ]
        )
