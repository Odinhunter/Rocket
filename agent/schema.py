"""Locked report schema for Rocket Creative Reads.

This module is the contract everything serializes to. L4 writes a Report
in this shape; L3 produces what L4 needs; L2 produces what L3 needs; L1
produces what L2 needs. The schema is the deliverable; the architecture
flows backward from it.

Do not add fields to Report without bumping protocol_version. Do not
silently change field names — every persisted run.json out there is bound
to these names.

Also defined here: AgentTranscript, the input contract L2 reads from.
AgentTranscript is format-agnostic — both the new bundled L1 runtime and
the pre-refactor checkpoint.json adapter produce it. L2 should not know
which produced it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


VERDICT = Literal["WORKING", "MIXED", "FAILING", "METHODOLOGY_GAP"]
CLASSIFICATION = Literal["within", "outside", "ambiguous"]
CONTEXT_VERDICT = Literal["working", "mixed", "failing"]

# Data-quality caveats reported alongside the verdict. METHODOLOGY_GAP used
# to overload the verdict enum to express both "creative is broken" and "we
# can't trust the data" — these are different axes. In 1.2.0 the verdict
# expresses creative effectiveness; methodology_flags expresses data quality.
# METHODOLOGY_GAP stays in the enum but only fires for explicit pool-target
# mismatch (no_match_note) or all-ambiguous (target_unsignaled) — the cases
# where a creative effectiveness call is genuinely unavailable.
METHODOLOGY_FLAG = Literal[
    "pool_archetype_mismatch",       # no_match_note set on target classification
    "target_unsignaled",             # ambiguity_note + every disposition ambiguous
    "no_within_target_evidence",     # 0 within but no explicit mismatch — graded
    "single_within_target",          # exactly 1 within disposition
    "homogenization_high",           # L3 reported many tight-variance cells
    "single_context_only",           # only one context label in the run
    "provisional_disposition_present",  # rocket-2.0.0: an on-the-spot disposition
]
_VALID_METHODOLOGY_FLAGS = {
    "pool_archetype_mismatch",
    "target_unsignaled",
    "no_within_target_evidence",
    "single_within_target",
    "homogenization_high",
    "single_context_only",
    "provisional_disposition_present",
}

# rocket-2.0.0: R7 behavioral signal action enum. The agent emits one of
# these as its terminal in-character action — never a funnel rate.
BEHAVIORAL_ACTION = Literal[
    "scroll_past", "linger", "tap_cta", "save", "share", "seek_info"
]
_VALID_BEHAVIORAL_ACTIONS = {
    "scroll_past", "linger", "tap_cta", "save", "share", "seek_info"
}


# ---- Consumer-facing report ----


@dataclass
class Quote:
    quote: str
    disposition: str
    round: int
    context: str


@dataclass
class DispositionRef:
    disposition: str
    classification: CLASSIFICATION


@dataclass
class TargetMatch:
    reached: list[DispositionRef] = field(default_factory=list)
    missed: list[DispositionRef] = field(default_factory=list)


@dataclass
class TopChange:
    change: str
    why: str
    evidence_quotes: list[Quote] = field(default_factory=list)
    within_target_corroboration: str = ""


@dataclass
class Strength:
    strength: str
    evidence_quotes: list[Quote] = field(default_factory=list)


@dataclass
class ContextFitEntry:
    verdict: CONTEXT_VERDICT
    friction_summary: str


# ---- rocket-2.0.0: R7 behavioral signal + funnel projection ----


@dataclass
class BehavioralSignal:
    """R7 — one agent's terminal in-character behavioral signal. The agent
    emits an action + creative-anchored reasoning + a would-act-this-week
    flag. It NEVER emits a funnel rate; turning signals into rates is the
    job of the L3.5 projection layer."""
    action: BEHAVIORAL_ACTION
    reasoning: str
    would_act_within_week: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BehavioralSignal":
        return cls(
            action=data["action"],
            reasoning=data["reasoning"],
            would_act_within_week=bool(data["would_act_within_week"]),
        )


@dataclass
class BehavioralSignalDistribution:
    """Aggregate of BehavioralSignal.action over a segment or the whole
    population. Counts, not rates — computed deterministically in Python
    (the locked 'distributions are Python, not the model' pattern). L3.5
    turns counts into rates."""
    counts: dict[str, int] = field(default_factory=dict)
    would_act_within_week_count: int = 0
    n: int = 0

    def to_dict(self) -> dict:
        return {
            "counts": dict(self.counts),
            "would_act_within_week_count": self.would_act_within_week_count,
            "n": self.n,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BehavioralSignalDistribution":
        return cls(
            counts={str(k): int(v) for k, v in data.get("counts", {}).items()},
            would_act_within_week_count=int(
                data.get("would_act_within_week_count", 0)
            ),
            n=int(data.get("n", 0)),
        )


@dataclass
class FunnelRates:
    """L3.5 output. Each rate is multiplier-derived from the customer's own
    baseline funnel and is NEVER presented bare — always with its band.
    `basis` literally names the calibration regime so the buyer knows what
    they're reading."""
    stop_rate: float
    stop_band: tuple[float, float]
    click_rate: float
    click_band: tuple[float, float]
    visit_rate: float
    visit_band: tuple[float, float]
    convert_rate: float
    convert_band: tuple[float, float]
    basis: str = "heuristic_v1"
    baseline_source: str = ""

    def to_dict(self) -> dict:
        return {
            "stop_rate": self.stop_rate,
            "stop_band": list(self.stop_band),
            "click_rate": self.click_rate,
            "click_band": list(self.click_band),
            "visit_rate": self.visit_rate,
            "visit_band": list(self.visit_band),
            "convert_rate": self.convert_rate,
            "convert_band": list(self.convert_band),
            "basis": self.basis,
            "baseline_source": self.baseline_source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FunnelRates":
        def _band(key: str) -> tuple[float, float]:
            lo, hi = data[key]
            return (float(lo), float(hi))

        return cls(
            stop_rate=float(data["stop_rate"]),
            stop_band=_band("stop_band"),
            click_rate=float(data["click_rate"]),
            click_band=_band("click_band"),
            visit_rate=float(data["visit_rate"]),
            visit_band=_band("visit_band"),
            convert_rate=float(data["convert_rate"]),
            convert_band=_band("convert_band"),
            basis=data.get("basis", "heuristic_v1"),
            baseline_source=data.get("baseline_source", ""),
        )


@dataclass
class SegmentProjection:
    """One segment's funnel projection — segment is a disposition or a
    disposition x chaos-band, per RunConfig.segment_granularity."""
    segment_label: str
    behavioral_distribution: BehavioralSignalDistribution
    funnel_rates: FunnelRates

    def to_dict(self) -> dict:
        return {
            "segment_label": self.segment_label,
            "behavioral_distribution": self.behavioral_distribution.to_dict(),
            "funnel_rates": self.funnel_rates.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SegmentProjection":
        return cls(
            segment_label=data["segment_label"],
            behavioral_distribution=BehavioralSignalDistribution.from_dict(
                data["behavioral_distribution"]
            ),
            funnel_rates=FunnelRates.from_dict(data["funnel_rates"]),
        )


@dataclass
class FunnelStageMeta:
    """Run-level (NOT per-segment) mapping of one funnel stage to the real
    ad-platform observable it predicts, plus whether the stage's causal
    inputs were provided this run. Identical for `overall` and every segment,
    so it lives once on FunnelProjection.

    `measurement_basis` is "direct_observable" (the stage maps to a metric the
    customer can read in Ads Manager — CTR, LP-view rate, purchase rate) or
    "modeled" (no direct observable for a static creative — stop/thumbstop;
    and `visit` until landing-page analysis is wired). `status` is "grounded"
    when every required input was supplied, else "scenario" (image-only).
    NOTE: this is `measurement_basis`, distinct from FunnelRates.basis which
    names the calibration regime ("heuristic_v1")."""
    stage_key: str
    observable_label: str
    measurement_basis: str  # "modeled" | "direct_observable"
    required_inputs: list[str] = field(default_factory=list)
    status: str = "grounded"  # "grounded" | "scenario"

    def to_dict(self) -> dict:
        return {
            "stage_key": self.stage_key,
            "observable_label": self.observable_label,
            "measurement_basis": self.measurement_basis,
            "required_inputs": list(self.required_inputs),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FunnelStageMeta":
        return cls(
            stage_key=data["stage_key"],
            observable_label=data["observable_label"],
            measurement_basis=data["measurement_basis"],
            required_inputs=list(data.get("required_inputs", [])),
            status=data.get("status", "grounded"),
        )


@dataclass
class FunnelProjection:
    """The rocket-2.0.0 ROI block on the Report. Overall + per-segment funnel
    rates, the population behavioral distribution, and the honesty-contract
    text the buyer reads."""
    overall: FunnelRates
    by_segment: list[SegmentProjection] = field(default_factory=list)
    population_behavioral_distribution: BehavioralSignalDistribution = field(
        default_factory=BehavioralSignalDistribution
    )
    calibration_note: str = ""
    # Run-level stage→observable mapping + input gating. Empty on legacy runs.
    provided_inputs: list[str] = field(default_factory=list)
    stage_meta: list[FunnelStageMeta] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall.to_dict(),
            "by_segment": [s.to_dict() for s in self.by_segment],
            "population_behavioral_distribution": (
                self.population_behavioral_distribution.to_dict()
            ),
            "calibration_note": self.calibration_note,
            "provided_inputs": list(self.provided_inputs),
            "stage_meta": [m.to_dict() for m in self.stage_meta],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FunnelProjection":
        return cls(
            overall=FunnelRates.from_dict(data["overall"]),
            by_segment=[
                SegmentProjection.from_dict(s) for s in data.get("by_segment", [])
            ],
            population_behavioral_distribution=(
                BehavioralSignalDistribution.from_dict(
                    data.get("population_behavioral_distribution", {})
                )
            ),
            calibration_note=data.get("calibration_note", ""),
            provided_inputs=list(data.get("provided_inputs", [])),
            stage_meta=[
                FunnelStageMeta.from_dict(m) for m in data.get("stage_meta", [])
            ],
        )


@dataclass
class Report:
    """The locked consumer-facing schema. All four synthesis layers serialize
    to this; brand managers read this; PDF/HTML renderers in Week 2 produce
    from this. Do not add fields without bumping protocol_version.
    """
    verdict: VERDICT
    confidence: int
    target_match: TargetMatch
    top_3_changes: list[TopChange]
    strengths_to_preserve: list[Strength]
    context_fit_map: dict[str, ContextFitEntry]
    verbatim_consumer_voice: list[Quote]
    methodology_flags: list[str] = field(default_factory=list)
    # Defaults let legacy Reports round-trip cleanly when the new fields
    # weren't populated: bet_ranking=[], funnel_projection=None,
    # provisional_dispositions=[].
    bet_ranking: list[str] = field(default_factory=list)
    funnel_projection: "FunnelProjection | None" = None
    provisional_dispositions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "target_match": {
                "reached": [asdict(d) for d in self.target_match.reached],
                "missed": [asdict(d) for d in self.target_match.missed],
            },
            "top_3_changes": [
                {
                    "change": c.change,
                    "why": c.why,
                    "evidence_quotes": [asdict(q) for q in c.evidence_quotes],
                    "within_target_corroboration": c.within_target_corroboration,
                }
                for c in self.top_3_changes
            ],
            "strengths_to_preserve": [
                {
                    "strength": s.strength,
                    "evidence_quotes": [asdict(q) for q in s.evidence_quotes],
                }
                for s in self.strengths_to_preserve
            ],
            "context_fit_map": {
                k: {"verdict": v.verdict, "friction_summary": v.friction_summary}
                for k, v in self.context_fit_map.items()
            },
            "verbatim_consumer_voice": [asdict(q) for q in self.verbatim_consumer_voice],
            "methodology_flags": list(self.methodology_flags),
            "bet_ranking": list(self.bet_ranking),
            "funnel_projection": (
                self.funnel_projection.to_dict()
                if self.funnel_projection is not None
                else None
            ),
            "provisional_dispositions": list(self.provisional_dispositions),
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Report":
        tm = data["target_match"]
        return cls(
            verdict=data["verdict"],
            confidence=int(data["confidence"]),
            target_match=TargetMatch(
                reached=[DispositionRef(**d) for d in tm.get("reached", [])],
                missed=[DispositionRef(**d) for d in tm.get("missed", [])],
            ),
            top_3_changes=[
                TopChange(
                    change=c["change"],
                    why=c["why"],
                    evidence_quotes=[Quote(**q) for q in c.get("evidence_quotes", [])],
                    within_target_corroboration=c.get("within_target_corroboration", ""),
                )
                for c in data.get("top_3_changes", [])
            ],
            strengths_to_preserve=[
                Strength(
                    strength=s["strength"],
                    evidence_quotes=[Quote(**q) for q in s.get("evidence_quotes", [])],
                )
                for s in data.get("strengths_to_preserve", [])
            ],
            context_fit_map={
                k: ContextFitEntry(verdict=v["verdict"], friction_summary=v["friction_summary"])
                for k, v in data.get("context_fit_map", {}).items()
            },
            verbatim_consumer_voice=[
                Quote(**q) for q in data.get("verbatim_consumer_voice", [])
            ],
            methodology_flags=list(data.get("methodology_flags", [])),
            bet_ranking=list(data.get("bet_ranking", [])),
            funnel_projection=(
                FunnelProjection.from_dict(data["funnel_projection"])
                if data.get("funnel_projection") is not None
                else None
            ),
            provisional_dispositions=list(data.get("provisional_dispositions", [])),
        )

    @classmethod
    def from_json(cls, raw: str) -> "Report":
        return cls.from_dict(json.loads(raw))


# ---- Validation ----


class SchemaError(ValueError):
    """Raised when a Report violates the locked-schema invariants. Used by L4
    parse-retry to decide whether to retry with the strict suffix."""


def validate_report(report: Report) -> None:
    """Enforce the structural invariants the schema demands but the dataclass
    typing cannot. Called after L4 deserializes the model's JSON. On failure,
    raises SchemaError — L4 catches and retries.
    """
    if report.verdict not in ("WORKING", "MIXED", "FAILING", "METHODOLOGY_GAP"):
        raise SchemaError(f"verdict must be one of WORKING/MIXED/FAILING/METHODOLOGY_GAP, got {report.verdict!r}")
    if not (0 <= report.confidence <= 100):
        raise SchemaError(f"confidence must be 0-100, got {report.confidence}")
    # METHODOLOGY_GAP: 0 changes allowed; other verdicts require exactly 3.
    if report.verdict == "METHODOLOGY_GAP":
        if len(report.top_3_changes) > 0:
            raise SchemaError(
                f"METHODOLOGY_GAP run must have 0 top_3_changes, got {len(report.top_3_changes)}"
            )
    else:
        if len(report.top_3_changes) != 3:
            raise SchemaError(
                f"top_3_changes must have exactly 3 entries for {report.verdict}, "
                f"got {len(report.top_3_changes)}"
            )
    for cfe in report.context_fit_map.values():
        if cfe.verdict not in ("working", "mixed", "failing"):
            raise SchemaError(
                f"context_fit_map verdict must be working/mixed/failing, got {cfe.verdict!r}"
            )
    for dr in report.target_match.reached + report.target_match.missed:
        if dr.classification not in ("within", "outside", "ambiguous"):
            raise SchemaError(
                f"DispositionRef.classification must be within/outside/ambiguous, "
                f"got {dr.classification!r}"
            )
    for flag in report.methodology_flags:
        if flag not in _VALID_METHODOLOGY_FLAGS:
            raise SchemaError(
                f"methodology_flags entry {flag!r} is not in the valid set: "
                f"{sorted(_VALID_METHODOLOGY_FLAGS)}"
            )
    # rocket-2.0.0: funnel projection internal consistency, when present.
    if report.funnel_projection is not None:
        _validate_funnel_projection(report.funnel_projection)


def _validate_funnel_rates(fr: "FunnelRates", where: str) -> None:
    for name in ("stop", "click", "visit", "convert"):
        rate = getattr(fr, f"{name}_rate")
        lo, hi = getattr(fr, f"{name}_band")
        if rate < 0:
            raise SchemaError(f"{where}: {name}_rate is negative ({rate})")
        if lo > hi:
            raise SchemaError(
                f"{where}: {name}_band is inverted (lo={lo} > hi={hi})"
            )
        if not (lo <= rate <= hi):
            raise SchemaError(
                f"{where}: {name}_rate {rate} not within its band [{lo}, {hi}]"
            )
    if not fr.basis:
        raise SchemaError(f"{where}: FunnelRates.basis must be non-empty")


def _validate_funnel_projection(fp: "FunnelProjection") -> None:
    _validate_funnel_rates(fp.overall, "funnel_projection.overall")
    for seg in fp.by_segment:
        if not seg.segment_label:
            raise SchemaError("funnel_projection segment has empty segment_label")
        _validate_funnel_rates(
            seg.funnel_rates, f"funnel_projection.by_segment[{seg.segment_label}]"
        )
        for action in seg.behavioral_distribution.counts:
            if action not in _VALID_BEHAVIORAL_ACTIONS:
                raise SchemaError(
                    f"behavioral_distribution for {seg.segment_label!r} has "
                    f"unknown action {action!r}"
                )
    # Stage gating metadata — only enforced when present (legacy/recomputed-
    # without-meta projections leave it empty and skip these checks).
    if fp.stage_meta:
        keys = [m.stage_key for m in fp.stage_meta]
        if keys != ["stop", "click", "visit", "convert"]:
            raise SchemaError(
                f"funnel stage_meta must cover the 4 stages in order, got {keys}"
            )
        for m in fp.stage_meta:
            if m.measurement_basis not in ("modeled", "direct_observable"):
                raise SchemaError(
                    f"stage_meta[{m.stage_key}]: bad measurement_basis "
                    f"{m.measurement_basis!r}"
                )
            if m.status not in ("grounded", "scenario"):
                raise SchemaError(
                    f"stage_meta[{m.stage_key}]: bad status {m.status!r}"
                )
        stop_meta = fp.stage_meta[0]
        if stop_meta.measurement_basis != "modeled" or stop_meta.status != "grounded":
            raise SchemaError(
                "stop stage must be modeled+grounded regardless of inputs "
                "(the creative is always present)"
            )


# ---- L1 → L2 contract: AgentTranscript ----


@dataclass
class AgentTranscript:
    """One agent's full output for a single asset, in the bundled-call shape.

    Both the new bundled L1 runtime and the legacy checkpoint.json adapter
    produce this. L2 reads it without knowing which source.

    `encoding_text` and `reflection_text` are the raw model outputs, each
    containing labelled sections (R1 GUT: ..., R2 COMPREHENSION: ...,
    R3 EMOTION: ... for encoding; R4, R5, R6 for reflection). L2 splits
    them via section-header regex.

    `behavioral_signal` carries the parsed R7 action. It defaults to None
    when R7 failed to parse (or for legacy transcripts predating R7); L2
    handles the gap.
    """
    agent_id: int
    disposition_label: str
    context_label: str
    seed_idx: int
    encoding_text: str
    reflection_text: str
    behavioral_signal: "BehavioralSignal | None" = None

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "disposition_label": self.disposition_label,
            "context_label": self.context_label,
            "seed_idx": self.seed_idx,
            "encoding_text": self.encoding_text,
            "reflection_text": self.reflection_text,
            "behavioral_signal": (
                self.behavioral_signal.to_dict()
                if self.behavioral_signal is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentTranscript":
        bs = data.get("behavioral_signal")
        return cls(
            agent_id=int(data["agent_id"]),
            disposition_label=data["disposition_label"],
            context_label=data["context_label"],
            seed_idx=int(data["seed_idx"]),
            encoding_text=data["encoding_text"],
            reflection_text=data["reflection_text"],
            behavioral_signal=(
                BehavioralSignal.from_dict(bs) if bs is not None else None
            ),
        )
