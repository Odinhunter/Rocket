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
from pathlib import Path
from typing import Literal

from agent.entities import AudienceSpec


# Anthropic API enforces 5 MB *after* base64 encoding. Base64 inflates by
# 4/3 + padding, so the max raw file size that survives is ~3.93 MB on disk.
# Verified empirically: patanjali_ad.png at 4.4 MB raw encoded to 5.9 MB and
# crashed with 400 BadRequestError after 15 agent specs were built.
_MAX_B64_BYTES = 5 * 1024 * 1024
_SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _base64_encoded_size(raw_bytes: int) -> int:
    """Exact byte count of standard base64 output (with padding) for a raw
    byte stream of length raw_bytes. No line breaks assumed.
    """
    return ((raw_bytes + 2) // 3) * 4


# Protocol version bumps when any agent or synthesis prompt changes OR
# when the temperature schedule changes — both are benchmark-invalidating.
# Required because the long-term moat (benchmark library, predictive
# in-market calibration) depends on protocol stability.
#
# 1.1.0: introduce DEFAULT_TEMPERATURES (target_id=0.0, l4=0.3, l2/l3=0.5,
#        agent=1.0). Pre-1.1.0 runs all ran at temperature=1.0 across every
#        layer, which produced verdict-bucket flips at the target_id
#        classification boundary and marketing-deck drift in L4.
# 1.2.0: soft-threshold L4 verdict logic. Remove the hard "0 within → GAP"
#        and "all-ambiguous → GAP" branches from the L4 prompt (they
#        collapsed legitimate verdicts into METHODOLOGY_GAP@<=20 on boundary
#        cases). METHODOLOGY_GAP now only fires on explicit `no_match_note`
#        from target_id. New `methodology_flags` list on Report carries the
#        data-quality caveats (pool_archetype_mismatch, target_unsignaled,
#        no_within_target_evidence, single_within_target, …) as a separate
#        axis from the creative-effectiveness verdict.
# 1.3.0: introduce DEFAULT_EFFORTS, set target_id to effort="low" on
#        claude-opus-4-7 (its `output_config.effort` knob). Empirical: 5/5
#        target_id calls on the bru boundary case landed byte-identical
#        classifications at effort=low vs the SDK-default stochasticity that
#        produced bucket flips. Cost dropped ~18% and latency ~30%. This
#        obsoletes the previously-planned ensemble-target_id lever — single
#        deterministic call is the right shape.
PROTOCOL_VERSION = "rocket-2.1.0"


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
    "render": "claude-sonnet-4-6",      # rocket-2.0.0 Render Engine (persona prose)
}


# Per-layer sampling temperature. Set in 1.1.0 after the 3-run bru
# stress-test revealed target_id classification stochasticity was the
# proximate cause of verdict bucket flips on identical input
# (METHODOLOGY_GAP@15 vs MIXED@45). L4 marketing-deck drift was the
# second symptom of unconstrained sampling on a single-shot strategist call.
#
# Constraint: claude-opus-4-7 has DEPRECATED the `temperature`, `top_p`,
# and `top_k` parameters — passing any of them returns 400. Opus 4.7
# replaces them with `thinking={"type": "adaptive", "effort": ...}`.
# So target_id and l4 entries are None here (we do not pass temperature
# at all on Opus calls); a separate `thinking_effort` knob is the right
# place to control their stochasticity if/when we wire it. Sonnet 4.6
# layers (agent/l2/l3) still accept temperature normally.
#
# L1 (agent) stays at 1.0 — consumer voice diversity is the product.
# Aggregation layers (L2/L3) drop to 0.5: stable synthesis, not generative.
DEFAULT_TEMPERATURES: dict[str, float | None] = {
    "agent":     1.0,
    "l2":        0.5,
    "l3":        0.5,
    "l4":        None,   # claude-opus-4-7: temperature deprecated, omit
    "target_id": None,   # claude-opus-4-7: temperature deprecated, omit
}


# Per-layer `output_config.effort` for the Anthropic API. Available on
# Sonnet 4.6 and Opus 4.7; replaces temperature as the primary token-spend
# control on Opus 4.7 (where temperature/top_p/top_k are deprecated).
#
# 1.3.0 setting: target_id="low" — empirically validated (tests/
# test_target_id_effort.py) to produce byte-identical classifications across
# 5 runs on the bru boundary case, where the SDK default (high) was flipping
# 0↔1↔2 within-target counts. Lower effort also cut cost (~18%) and latency
# (~30%) per target_id call.
#
# Other layers left at None (SDK default = "high"):
# - agent/l2/l3 (Sonnet): consumer voice and synthesis quality dominate;
#   effort tuning is a separate experiment.
# - l4 (Opus): the strategist memo benefits from full reasoning; trimming
#   effort here risks the marketing-deck drift we just fixed in 1.2.0.
DEFAULT_EFFORTS: dict[str, str | None] = {
    "agent":     None,
    "l2":        None,
    "l3":        None,
    "l4":        None,
    "target_id": "low",
}


@dataclass
class AssetSpec:
    image_path: str
    label: str                          # human caption used in headers and quotes

    def validate(self) -> None:
        path = Path(self.image_path)
        if not path.exists():
            raise ValueError(f"asset file not found: {self.image_path}")
        if path.suffix.lower() not in _SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(
                f"asset {self.image_path} has unsupported extension "
                f"{path.suffix!r}; supported: {sorted(_SUPPORTED_IMAGE_SUFFIXES)}"
            )
        raw_bytes = path.stat().st_size
        b64_bytes = _base64_encoded_size(raw_bytes)
        if b64_bytes > _MAX_B64_BYTES:
            raw_mb = raw_bytes / (1024 * 1024)
            b64_mb = b64_bytes / (1024 * 1024)
            raise ValueError(
                f"asset {self.image_path} exceeds Anthropic 5 MB post-base64 "
                f"limit: {raw_mb:.2f} MB raw → {b64_mb:.2f} MB encoded. "
                f"Re-export under ~3.75 MB raw (e.g. convert .png to .jpg, "
                f"or downscale)."
            )


@dataclass
class CreativeInputs:
    """The ad's accompanying copy + offer — the causal inputs that drive the
    lower funnel. `offer` carries price and any promo (e.g. "₹2,699, 20% off
    first order"). Optional and per-run (one creative test, one offer), so
    they live on RunConfig, not on AssetSpec (which is the image and may be
    multiple under the focal+anchor upsell). When provided, runtime feeds them
    to the agents, and the funnel's click/convert stages become grounded
    rather than image-only scenarios. See agent/projection_l35.STAGE_OBSERVABLES.
    """

    primary_text: str = ""   # the ad's body / primary caption
    headline: str = ""       # the ad's headline
    offer: str = ""          # price + promo, e.g. "₹2,699, 20% off first order"

    def has_ad_copy(self) -> bool:
        return bool(self.primary_text.strip() or self.headline.strip())

    def has_offer(self) -> bool:
        return bool(self.offer.strip())

    def to_dict(self) -> dict:
        return {
            "primary_text": self.primary_text,
            "headline": self.headline,
            "offer": self.offer,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "CreativeInputs":
        data = data or {}
        return cls(
            primary_text=data.get("primary_text", ""),
            headline=data.get("headline", ""),
            offer=data.get("offer", ""),
        )


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
    temperatures: dict[str, float | None] = field(
        default_factory=lambda: dict(DEFAULT_TEMPERATURES)
    )
    efforts: dict[str, str | None] = field(
        default_factory=lambda: dict(DEFAULT_EFFORTS)
    )

    # Sampling seed for which dispositions / contexts get drawn from the pool.
    # Anthropic SDK has no `seed` parameter, so within-cell variance is API
    # stochasticity at the configured per-layer temperature, not deterministic.
    seed: int = 71

    # audience_spec: the customer-composed targeting (demographics +
    # disposition selection + context envelope + chaos distribution).
    # Required for a real run; RunService.prepare raises if it is None.
    audience_spec: "AudienceSpec | None" = None
    # segment_granularity: the L2 fan-out key. "disposition_chaos_band" (the
    # user-decided default) fans L2 per disposition x chaos band — the richer,
    # ~3x-cost granularity that gives the funnel projection per-chaos-band teeth.
    segment_granularity: Literal[
        "disposition", "disposition_chaos_band"
    ] = "disposition_chaos_band"
    # baseline_funnel: the customer's real funnel rates, the anchor L3.5
    # projects multipliers against. Keys: stop_rate / click_rate / visit_rate /
    # convert_rate (all floats in 0..1). None until the customer supplies it.
    baseline_funnel: dict | None = None
    # Entity references for the two-phase run + filesystem entity model.
    library_id: str = ""
    audience_id: str = ""
    # creative_inputs: ad copy + offer accompanying the image. When present
    # they are fed to the agents and ground the funnel's lower stages.
    creative_inputs: CreativeInputs = field(default_factory=CreativeInputs)
    # declared_targeting: the customer's stated Meta audience (free text). A
    # hint to the target classifier ONLY — it must not override the creative-
    # derived inferred_audience the demographic-mismatch guard depends on.
    declared_targeting: str = ""
    # rocket-2.1.0 marketer-led composition. When True, the declared audience
    # (audience_spec.demographics) selects/weights which personas appear and
    # agents are simulated at the declared demographics. Off by default so
    # legacy runs are byte-unchanged. tail_fraction (0..1) reserves a segregated
    # discovery tail of out-of-frame personas.
    marketer_led: bool = False
    tail_fraction: float = 0.0

    def provided_inputs(self) -> list[str]:
        """The creative inputs supplied this run, as the keys L3.5 gates the
        funnel stages on (see agent/projection_l35.STAGE_OBSERVABLES)."""
        out: list[str] = []
        if self.creative_inputs.has_ad_copy():
            out.append("ad_copy")
        if self.creative_inputs.has_offer():
            out.append("offer")
        return out

    def total_agents(self) -> int:
        return self.dispositions_per_run * self.contexts_per_run * self.seeds_per_cell

    def validate(self) -> None:
        self.asset.validate()
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
            "temperatures": dict(self.temperatures),
            "efforts": dict(self.efforts),
            "seed": self.seed,
            "total_agents": self.total_agents(),
            "audience_spec": (
                self.audience_spec.to_dict()
                if self.audience_spec is not None
                else None
            ),
            "segment_granularity": self.segment_granularity,
            "baseline_funnel": (
                dict(self.baseline_funnel)
                if self.baseline_funnel is not None
                else None
            ),
            "library_id": self.library_id,
            "audience_id": self.audience_id,
            "creative_inputs": self.creative_inputs.to_dict(),
            "declared_targeting": self.declared_targeting,
            "marketer_led": self.marketer_led,
            "tail_fraction": self.tail_fraction,
        }
