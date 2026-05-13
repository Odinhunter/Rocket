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
    "pool_archetype_mismatch",      # no_match_note set on target classification
    "target_unsignaled",            # ambiguity_note + every disposition ambiguous
    "no_within_target_evidence",    # 0 within but no explicit mismatch — graded
    "single_within_target",         # exactly 1 within disposition
    "homogenization_high",          # L3 reported many tight-variance cells
    "single_context_only",          # only one context label in the run
]
_VALID_METHODOLOGY_FLAGS = {
    "pool_archetype_mismatch",
    "target_unsignaled",
    "no_within_target_evidence",
    "single_within_target",
    "homogenization_high",
    "single_context_only",
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
    """
    agent_id: int
    disposition_label: str
    context_label: str
    seed_idx: int
    encoding_text: str
    reflection_text: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentTranscript":
        return cls(
            agent_id=int(data["agent_id"]),
            disposition_label=data["disposition_label"],
            context_label=data["context_label"],
            seed_idx=int(data["seed_idx"]),
            encoding_text=data["encoding_text"],
            reflection_text=data["reflection_text"],
        )
