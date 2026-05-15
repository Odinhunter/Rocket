"""Intermediate synthesis types.

L2Summary and L3Summary are the layer-internal data shapes used between
synthesis layers. They are NOT part of the locked consumer schema (that
lives in `agent/schema.py`). Their shape can evolve as the synthesis
pipeline matures without bumping protocol_version — they're never read
by anyone outside the pipeline.

TargetClassification lives here too. It's an Opus-vision output consumed
by L4 (and audited on the run record by humans), but it's not the
consumer-facing Report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from agent.schema import BehavioralSignalDistribution, Quote


# ---- L2: per-disposition summary ----


@dataclass
class L2Summary:
    """One per disposition. Compresses 1..N agent transcripts within the
    same disposition (across contexts and seeds) into a tight read that
    L3 can fan into population-level findings.

    representative_quotes: one Quote per round (R1..R6) drawn from this
    disposition's transcripts. L4 pulls from these (combined with L3's
    global representative_quotes) to populate evidence_quotes and
    verbatim_consumer_voice in the final Report.
    """
    disposition_label: str
    summary_paragraph: str
    within_cell_variance: Literal["tight", "spread", "outlier_present"]
    outlier_note: str | None
    representative_quotes: dict[int, Quote] = field(default_factory=dict)
    emotional_read: str = ""        # synthesized from R3 prose across contexts
    friction_summary: str = ""      # synthesized from R6 across contexts
    # rocket-2.0.0: segment_label is the L2 fan-out key — a disposition label
    # in v1, a "disposition::chaos_band" key under per-(disp x chaos-band)
    # granularity. behavioral_distribution is the R7 signal aggregate,
    # computed deterministically in Python (never emitted by the model).
    segment_label: str = ""
    behavioral_distribution: BehavioralSignalDistribution = field(
        default_factory=BehavioralSignalDistribution
    )

    def to_dict(self) -> dict:
        return {
            "disposition_label": self.disposition_label,
            "summary_paragraph": self.summary_paragraph,
            "within_cell_variance": self.within_cell_variance,
            "outlier_note": self.outlier_note,
            "representative_quotes": {
                str(r): asdict(q) for r, q in self.representative_quotes.items()
            },
            "emotional_read": self.emotional_read,
            "friction_summary": self.friction_summary,
            "segment_label": self.segment_label,
            "behavioral_distribution": self.behavioral_distribution.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "L2Summary":
        return cls(
            disposition_label=data["disposition_label"],
            summary_paragraph=data["summary_paragraph"],
            within_cell_variance=data["within_cell_variance"],
            outlier_note=data.get("outlier_note"),
            representative_quotes={
                int(r): Quote(**q) for r, q in data.get("representative_quotes", {}).items()
            },
            emotional_read=data.get("emotional_read", ""),
            friction_summary=data.get("friction_summary", ""),
            segment_label=data.get("segment_label", ""),
            behavioral_distribution=BehavioralSignalDistribution.from_dict(
                data.get("behavioral_distribution", {})
            ),
        )


# ---- L3: population synthesis ----


@dataclass
class Theme:
    """A finding that surfaces across dispositions. statement = one-sentence
    claim. cited_by = disposition labels that surfaced it. rounds = which
    rounds it surfaced in. stimulus_scope: 'single' for single-asset mode."""
    statement: str
    cited_by: list[str] = field(default_factory=list)
    rounds: list[int] = field(default_factory=list)


@dataclass
class ContextFitFinding:
    """One per context label. L4 will copy this into the consumer-facing
    context_fit_map."""
    verdict: Literal["working", "mixed", "failing"]
    friction_summary: str


@dataclass
class ConfidenceSignals:
    """Quantitative signals L4 uses to land the confidence number against
    the anchors. Filled by L3 from the L2 summaries.

    within_target_disposition_count: how many dispositions classified within
        target are present in this run. Single-within → confidence caveat.
    contexts_in_agreement: how many of the contexts produced consistent
        within-target verdicts (working/mixed/failing align).
    homogenization_flag_count: number of within-cell variance="tight" L2s.
    """
    within_target_disposition_count: int = 0
    contexts_in_agreement: int = 0
    total_contexts: int = 0
    homogenization_flag_count: int = 0


@dataclass
class L3Summary:
    """Output of population synthesis. Read by L4 to write the strategic
    memo against the locked schema."""
    robust_themes: list[Theme] = field(default_factory=list)
    fragile_themes: list[Theme] = field(default_factory=list)
    within_target_findings: list[Theme] = field(default_factory=list)
    outside_target_findings: list[Theme] = field(default_factory=list)
    context_fit: dict[str, ContextFitFinding] = field(default_factory=dict)
    representative_quotes: list[Quote] = field(default_factory=list)
    confidence_signals: ConfidenceSignals = field(default_factory=ConfidenceSignals)
    # rocket-2.0.0: R7 behavioral signal aggregates, computed deterministically
    # in Python from the L2 summaries. L3.5 reads these to project the funnel.
    population_behavioral_distribution: BehavioralSignalDistribution = field(
        default_factory=BehavioralSignalDistribution
    )
    segment_behavioral_distributions: dict[str, BehavioralSignalDistribution] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict:
        return {
            "robust_themes": [asdict(t) for t in self.robust_themes],
            "fragile_themes": [asdict(t) for t in self.fragile_themes],
            "within_target_findings": [asdict(t) for t in self.within_target_findings],
            "outside_target_findings": [asdict(t) for t in self.outside_target_findings],
            "context_fit": {
                k: {"verdict": v.verdict, "friction_summary": v.friction_summary}
                for k, v in self.context_fit.items()
            },
            "representative_quotes": [asdict(q) for q in self.representative_quotes],
            "confidence_signals": asdict(self.confidence_signals),
            "population_behavioral_distribution": (
                self.population_behavioral_distribution.to_dict()
            ),
            "segment_behavioral_distributions": {
                k: v.to_dict()
                for k, v in self.segment_behavioral_distributions.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "L3Summary":
        return cls(
            robust_themes=[Theme(**t) for t in data.get("robust_themes", [])],
            fragile_themes=[Theme(**t) for t in data.get("fragile_themes", [])],
            within_target_findings=[Theme(**t) for t in data.get("within_target_findings", [])],
            outside_target_findings=[Theme(**t) for t in data.get("outside_target_findings", [])],
            context_fit={
                k: ContextFitFinding(verdict=v["verdict"], friction_summary=v["friction_summary"])
                for k, v in data.get("context_fit", {}).items()
            },
            representative_quotes=[Quote(**q) for q in data.get("representative_quotes", [])],
            confidence_signals=ConfidenceSignals(**data.get("confidence_signals", {})),
            population_behavioral_distribution=BehavioralSignalDistribution.from_dict(
                data.get("population_behavioral_distribution", {})
            ),
            segment_behavioral_distributions={
                k: BehavioralSignalDistribution.from_dict(v)
                for k, v in data.get("segment_behavioral_distributions", {}).items()
            },
        )


# ---- Target classification ----


@dataclass
class DispositionTarget:
    disposition_label: str
    classification: Literal["within", "outside", "ambiguous"]
    reasoning: str


@dataclass
class TargetClassification:
    """Produced by an Opus vision call that sees the asset + disposition pool
    but no agent reactions. Target is a property of the ad, not of who
    happened to react; keeping reactions out prevents the model from
    rationalizing target to fit who responded.
    """
    inferred_target_description: str
    target_reasoning: str
    disposition_classifications: list[DispositionTarget]
    ambiguity_note: str | None = None
    no_match_note: str | None = None

    def within_target_labels(self) -> list[str]:
        return [d.disposition_label for d in self.disposition_classifications if d.classification == "within"]

    def outside_target_labels(self) -> list[str]:
        return [d.disposition_label for d in self.disposition_classifications if d.classification == "outside"]

    def ambiguous_labels(self) -> list[str]:
        return [d.disposition_label for d in self.disposition_classifications if d.classification == "ambiguous"]

    def to_dict(self) -> dict:
        return {
            "inferred_target_description": self.inferred_target_description,
            "target_reasoning": self.target_reasoning,
            "disposition_classifications": [asdict(d) for d in self.disposition_classifications],
            "ambiguity_note": self.ambiguity_note,
            "no_match_note": self.no_match_note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TargetClassification":
        return cls(
            inferred_target_description=data["inferred_target_description"],
            target_reasoning=data["target_reasoning"],
            disposition_classifications=[
                DispositionTarget(**d) for d in data["disposition_classifications"]
            ],
            ambiguity_note=data.get("ambiguity_note"),
            no_match_note=data.get("no_match_note"),
        )
