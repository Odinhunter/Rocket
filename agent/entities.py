"""Entity model: Account -> Brand Profile -> {Disposition Library,
Saved Audiences} -> Run.

Filesystem-backed (no DB), matching the runs/<account>/<brand>/ multi-
tenant convention. A Run resolves an AudienceSpec into a panel.

Layout:
  runs/<account_id>/account.json
  runs/<account_id>/<brand_profile_id>/entities/brand_profile.json
  runs/<account_id>/<brand_profile_id>/entities/library.json
  runs/<account_id>/<brand_profile_id>/entities/audiences/<audience_id>.json

The disposition library is uncapped — a customer can hand-map 100
dispositions — but a single run's AudienceSpec selects at most 7
(AUDIENCE_DISPOSITION_CAP), because L2 fan-out (per-disposition x
chaos-band) is the per-run cost lever, not the library size.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agent.telemetry import RUNS_DIR
from agent.vectors import (
    ChaosDistribution,
    DemographicPoint,
    NamedContext,
    NamedDisposition,
)

# A single run's audience may select at most this many dispositions. L2
# fan-out is per-(disposition x chaos-band); 7 x 3 = 21 L2 calls is the
# ceiling that keeps per-run cost bounded.
AUDIENCE_DISPOSITION_CAP = 7

# A run's context envelope must be 3-5 attention states.
_CONTEXT_ENVELOPE_MIN = 3
_CONTEXT_ENVELOPE_MAX = 5

# Hard ceiling on panel size.
_PANEL_SIZE_CEILING = 200


# ---- Filesystem path helpers ----


def _account_dir(account_id: str) -> Path:
    return RUNS_DIR / account_id


def _entities_dir(account_id: str, brand_profile_id: str) -> Path:
    return RUNS_DIR / account_id / brand_profile_id / "entities"


def _persist_json(path: Path, payload: object) -> None:
    """Atomic write, mirroring run_service.py:_persist_json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)


# ---- AudienceSpec — what a Run resolves into a panel ----


@dataclass
class AudienceSpec:
    """The customer-composed targeting for one run. Resolved into a panel of
    PanelAgents by agent/panel.py:build_panel.

    - demographics: addressability points, always customer-set.
    - disposition_labels: references into the Brand Profile's library
      (<= AUDIENCE_DISPOSITION_CAP).
    - context_envelope: 3-5 attention states.
    - chaos_distribution: behavioral-style mix; defaults to the category
      artifact pack's, overridable in 'advanced' mode.
    - panel_size: total agents (<= 200).
    """

    demographics: list[DemographicPoint] = field(default_factory=list)
    disposition_labels: list[str] = field(default_factory=list)
    context_envelope: list[NamedContext] = field(default_factory=list)
    chaos_distribution: ChaosDistribution | None = None
    panel_size: int = 200

    def validate(self) -> None:
        if not self.demographics:
            raise ValueError("AudienceSpec.demographics must have >= 1 point")
        for d in self.demographics:
            d.validate()
        if not self.disposition_labels:
            raise ValueError("AudienceSpec.disposition_labels must have >= 1 entry")
        if len(self.disposition_labels) > AUDIENCE_DISPOSITION_CAP:
            raise ValueError(
                f"AudienceSpec selects {len(self.disposition_labels)} dispositions; "
                f"the per-run cap is {AUDIENCE_DISPOSITION_CAP}"
            )
        if len(self.disposition_labels) != len(set(self.disposition_labels)):
            raise ValueError("AudienceSpec.disposition_labels has duplicates")
        if not (
            _CONTEXT_ENVELOPE_MIN
            <= len(self.context_envelope)
            <= _CONTEXT_ENVELOPE_MAX
        ):
            raise ValueError(
                f"AudienceSpec.context_envelope must have "
                f"{_CONTEXT_ENVELOPE_MIN}-{_CONTEXT_ENVELOPE_MAX} contexts, "
                f"got {len(self.context_envelope)}"
            )
        ctx_labels = [c.label for c in self.context_envelope]
        if len(ctx_labels) != len(set(ctx_labels)):
            raise ValueError("AudienceSpec.context_envelope has duplicate labels")
        for c in self.context_envelope:
            c.validate()
        if self.chaos_distribution is None:
            raise ValueError("AudienceSpec.chaos_distribution must be set")
        self.chaos_distribution.validate()
        if not (1 <= self.panel_size <= _PANEL_SIZE_CEILING):
            raise ValueError(
                f"AudienceSpec.panel_size must be 1-{_PANEL_SIZE_CEILING}, "
                f"got {self.panel_size}"
            )

    def to_dict(self) -> dict:
        return {
            "demographics": [d.to_dict() for d in self.demographics],
            "disposition_labels": list(self.disposition_labels),
            "context_envelope": [c.to_dict() for c in self.context_envelope],
            "chaos_distribution": (
                self.chaos_distribution.to_dict()
                if self.chaos_distribution is not None
                else None
            ),
            "panel_size": self.panel_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudienceSpec":
        cd = data.get("chaos_distribution")
        return cls(
            demographics=[
                DemographicPoint.from_dict(d) for d in data.get("demographics", [])
            ],
            disposition_labels=list(data.get("disposition_labels", [])),
            context_envelope=[
                NamedContext.from_dict(c) for c in data.get("context_envelope", [])
            ],
            chaos_distribution=(
                ChaosDistribution.from_dict(cd) if cd is not None else None
            ),
            panel_size=int(data.get("panel_size", 200)),
        )


# ---- Account ----


@dataclass
class Account:
    """The billing entity."""

    account_id: str
    name: str

    def validate(self) -> None:
        if not self.account_id or not self.account_id.strip():
            raise ValueError("Account.account_id must be non-empty")

    def to_dict(self) -> dict:
        return {"account_id": self.account_id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        return cls(account_id=data["account_id"], name=data.get("name", ""))

    def save(self) -> Path:
        path = _account_dir(self.account_id) / "account.json"
        _persist_json(path, self.to_dict())
        return path

    @classmethod
    def load(cls, account_id: str) -> "Account":
        path = _account_dir(account_id) / "account.json"
        return cls.from_dict(json.loads(path.read_text()))


# ---- Brand Profile ----


@dataclass
class BrandProfile:
    """A tenant inside an account. Binds one+ categories, owns a disposition
    library and a set of saved audiences."""

    brand_profile_id: str
    account_id: str
    categories: list[str] = field(default_factory=list)
    library_id: str = ""
    audience_ids: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.brand_profile_id or not self.brand_profile_id.strip():
            raise ValueError("BrandProfile.brand_profile_id must be non-empty")
        if not self.account_id or not self.account_id.strip():
            raise ValueError("BrandProfile.account_id must be non-empty")
        if not self.categories:
            raise ValueError("BrandProfile.categories must have >= 1 category")

    def to_dict(self) -> dict:
        return {
            "brand_profile_id": self.brand_profile_id,
            "account_id": self.account_id,
            "categories": list(self.categories),
            "library_id": self.library_id,
            "audience_ids": list(self.audience_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrandProfile":
        return cls(
            brand_profile_id=data["brand_profile_id"],
            account_id=data["account_id"],
            categories=list(data.get("categories", [])),
            library_id=data.get("library_id", ""),
            audience_ids=list(data.get("audience_ids", [])),
        )

    def save(self) -> Path:
        path = (
            _entities_dir(self.account_id, self.brand_profile_id)
            / "brand_profile.json"
        )
        _persist_json(path, self.to_dict())
        return path

    @classmethod
    def load(cls, account_id: str, brand_profile_id: str) -> "BrandProfile":
        path = _entities_dir(account_id, brand_profile_id) / "brand_profile.json"
        return cls.from_dict(json.loads(path.read_text()))


# ---- Disposition Library ----


@dataclass
class DispositionLibrary:
    """The Brand Profile's pool of hand-mapped (and on-the-spot provisional)
    dispositions. Uncapped — a customer may have 100. A run selects from it
    via AudienceSpec.disposition_labels (capped at AUDIENCE_DISPOSITION_CAP)."""

    library_id: str
    brand_profile_id: str
    account_id: str
    dispositions: list[NamedDisposition] = field(default_factory=list)

    def validate(self) -> None:
        if not self.library_id or not self.library_id.strip():
            raise ValueError("DispositionLibrary.library_id must be non-empty")
        labels = [d.label for d in self.dispositions]
        if len(labels) != len(set(labels)):
            raise ValueError("DispositionLibrary has duplicate disposition labels")
        for d in self.dispositions:
            d.validate()

    def get(self, label: str) -> NamedDisposition:
        for d in self.dispositions:
            if d.label == label:
                return d
        raise KeyError(f"no disposition labelled {label!r} in library {self.library_id!r}")

    def resolve(self, labels: list[str]) -> list[NamedDisposition]:
        """Resolve a list of labels into NamedDispositions, in label order."""
        return [self.get(label) for label in labels]

    def to_dict(self) -> dict:
        return {
            "library_id": self.library_id,
            "brand_profile_id": self.brand_profile_id,
            "account_id": self.account_id,
            "dispositions": [d.to_dict() for d in self.dispositions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DispositionLibrary":
        return cls(
            library_id=data["library_id"],
            brand_profile_id=data["brand_profile_id"],
            account_id=data["account_id"],
            dispositions=[
                NamedDisposition.from_dict(d) for d in data.get("dispositions", [])
            ],
        )

    def save(self) -> Path:
        path = (
            _entities_dir(self.account_id, self.brand_profile_id) / "library.json"
        )
        _persist_json(path, self.to_dict())
        return path

    @classmethod
    def load(cls, account_id: str, brand_profile_id: str) -> "DispositionLibrary":
        path = _entities_dir(account_id, brand_profile_id) / "library.json"
        return cls.from_dict(json.loads(path.read_text()))


# ---- Saved Audience ----


@dataclass
class SavedAudience:
    """A named, reusable AudienceSpec belonging to a Brand Profile."""

    audience_id: str
    name: str
    brand_profile_id: str
    account_id: str
    spec: AudienceSpec

    def validate(self) -> None:
        if not self.audience_id or not self.audience_id.strip():
            raise ValueError("SavedAudience.audience_id must be non-empty")
        self.spec.validate()

    def to_dict(self) -> dict:
        return {
            "audience_id": self.audience_id,
            "name": self.name,
            "brand_profile_id": self.brand_profile_id,
            "account_id": self.account_id,
            "spec": self.spec.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SavedAudience":
        return cls(
            audience_id=data["audience_id"],
            name=data.get("name", ""),
            brand_profile_id=data["brand_profile_id"],
            account_id=data["account_id"],
            spec=AudienceSpec.from_dict(data["spec"]),
        )

    def save(self) -> Path:
        path = (
            _entities_dir(self.account_id, self.brand_profile_id)
            / "audiences"
            / f"{self.audience_id}.json"
        )
        _persist_json(path, self.to_dict())
        return path

    @classmethod
    def load(
        cls, account_id: str, brand_profile_id: str, audience_id: str
    ) -> "SavedAudience":
        path = (
            _entities_dir(account_id, brand_profile_id)
            / "audiences"
            / f"{audience_id}.json"
        )
        return cls.from_dict(json.loads(path.read_text()))
