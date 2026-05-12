"""RunConfig — the single source of run-level configuration.

Replaces the module-level constants in the pre-refactor `batch_run.py`.
Carries the multi-tenant identifiers (account_id, brand_profile_id), the
agent matrix sizing, the model versions for each layer, and the protocol
version. Everything that needs to know "what run is this" reads from
RunConfig.

The asset model in Week 1 is single-asset only. Focal+anchor returns as
a `list[AssetSpec]` field when the upsell mode ships in a later tier.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal


# Protocol version bumps when any agent or synthesis prompt changes.
# Required because the long-term moat (benchmark library, predictive
# in-market calibration) depends on protocol stability — every prompt
# change re-zeros prior runs as comparison data.
PROTOCOL_VERSION = "rocket-1.0.0"


# Default model assignments per layer. Locked after 2026-05-12 telemetry +
# cache validation. Haiku-on-Call-1 was explicitly rejected: cross-model
# caching breaks (cache is per-model), first-impression voice is exactly
# where Haiku underperforms, marginal savings don't justify methodology risk.
DEFAULT_MODEL_VERSIONS: dict[str, str] = {
    "agent": "claude-sonnet-4-6",       # L1 Encoding + Reflection
    "l2": "claude-sonnet-4-6",          # L2 per-disposition
    "l3": "claude-sonnet-4-6",          # L3 population
    "l4": "claude-opus-4-7",            # L4 strategic memo
    "target_id": "claude-opus-4-7",     # Opus vision target classification
}


@dataclass
class AssetSpec:
    image_path: str
    label: str                          # human caption used in headers and quotes


@dataclass
class RunConfig:
    """Single source of truth for a Creative Read run.

    Defaults sized for the 15-agent smoke run (5 dispositions × 3 contexts ×
    1 seed). 200 agents is the ceiling, not the start — confirmed against
    measured cost and tier-limit caution.
    """

    asset: AssetSpec
    archetype: str
    category: str

    # Multi-tenant identifiers. Filesystem-only scaffolding in Week 1;
    # entity model arrives Week 2/3 with the onboarding wizard.
    account_id: str = "internal"
    brand_profile_id: str = "default"

    # Matrix sizing. Total agents = D × C × S, must stay <= 200.
    dispositions_per_run: int = 5
    contexts_per_run: int = 3
    seeds_per_cell: int = 1

    # Concurrency. At the 30K ITPM tier, each Encoding+Reflection pair costs
    # ~6800 ITPM tokens spread across ~26s. 4 concurrent stays within budget.
    # Bump only after measuring against your actual tier ceiling.
    max_concurrent_agents: int = 4

    # Mode is locked single-asset for Week 1; carrying the field so the
    # focal+anchor upsell can land without a schema change later.
    mode: Literal["single_asset"] = "single_asset"

    # Versioning. protocol_version bumps on any prompt change.
    # disposition_version is the SHA-1 of the disposition pool at run time;
    # set by RunService at run start so a re-run with a changed pool is
    # detectable downstream.
    protocol_version: str = PROTOCOL_VERSION
    disposition_version: str = "auto"
    model_versions: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_MODEL_VERSIONS)
    )

    # Sampling seed for which dispositions / contexts get drawn from the pool.
    # Anthropic SDK has no `seed` parameter, so within-cell variance is API
    # stochasticity at temperature=1.0, not deterministic.
    seed: int = 71

    def total_agents(self) -> int:
        return self.dispositions_per_run * self.contexts_per_run * self.seeds_per_cell

    def validate(self) -> None:
        if self.total_agents() > 200:
            raise ValueError(
                f"Total agents {self.total_agents()} exceeds 200-agent ceiling. "
                f"D={self.dispositions_per_run} C={self.contexts_per_run} "
                f"S={self.seeds_per_cell}"
            )
        if self.dispositions_per_run > 7:
            # Memory says dispositions per Brand Profile cap at <=7. L2 fan-out
            # scales linearly with this; the cap is part of the cost lock.
            raise ValueError(
                f"dispositions_per_run={self.dispositions_per_run} exceeds the "
                "Brand Profile cap of 7"
            )
        if self.dispositions_per_run < 1 or self.contexts_per_run < 1 or self.seeds_per_cell < 1:
            raise ValueError("D, C, S must all be >= 1")
        if self.max_concurrent_agents < 1:
            raise ValueError("max_concurrent_agents must be >= 1")

    def compute_disposition_version(self, disposition_pool: list[tuple[str, str]]) -> str:
        """SHA-1 of the disposition pool (label + description text), so a re-run
        with a changed pool is detectable in the run record.
        """
        h = hashlib.sha1()
        for label, desc in sorted(disposition_pool):
            h.update(label.encode("utf-8"))
            h.update(b"\x00")
            h.update(desc.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "asset": {"image_path": self.asset.image_path, "label": self.asset.label},
            "archetype": self.archetype,
            "category": self.category,
            "account_id": self.account_id,
            "brand_profile_id": self.brand_profile_id,
            "dispositions_per_run": self.dispositions_per_run,
            "contexts_per_run": self.contexts_per_run,
            "seeds_per_cell": self.seeds_per_cell,
            "max_concurrent_agents": self.max_concurrent_agents,
            "mode": self.mode,
            "protocol_version": self.protocol_version,
            "disposition_version": self.disposition_version,
            "model_versions": dict(self.model_versions),
            "seed": self.seed,
            "total_agents": self.total_agents(),
        }
