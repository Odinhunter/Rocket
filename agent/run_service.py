"""RunService — the two-phase orchestrator for a Creative Read.

The run is split so the credit is debited only after the customer confirms:

  prepare(config) -> RunPreparation
    Runs target_id FIRST, resolves the AudienceSpec into a panel, warms the
    render cache. Produces the confirmation surface — inferred target,
    resolved audience, panel composition, cost estimate, provisional
    dispositions. NO credit debited. NO L1 fired.

  [ customer reviews RunPreparation and confirms ]

  commit(prep) -> Report
    Debits the credit (idempotently), then runs L1 -> L2 -> L3 -> L3.5
    projection -> L4, and writes the artifacts.

  run(config) -> Report
    Convenience: prepare + auto-confirm + commit.

Filesystem:
  runs/<account>/<brand>/<run_id>/
    ├── run.json              — status: prepared -> committed -> complete
    ├── preparation.json      — the RunPreparation audit record
    ├── panel.json            — the resolved PanelAgent list
    ├── target_classification.json
    ├── transcripts.json
    ├── l2_summaries.json
    ├── l3_summary.json
    ├── l35_projection.json
    ├── committed.marker      — credit-debit idempotency guard
    ├── agent_calls/          — idempotent per-call L1 artifacts
    └── telemetry.jsonl
  runs/<account>/<brand>/library_renders/   — brand-level render cache
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from agent import calibration_log, credits
from agent.artifact_pack import load_pack
from agent.config import RunConfig
from agent.entities import DispositionLibrary
from agent.panel import PanelAgent, build_panel, compute_panel_version
from agent.projection_l35 import project_funnel
from agent.render import render_persona_core
from agent.runtime import run_agent_async
from agent.schema import AgentTranscript, Report
from agent.synthesis_l2 import synthesize_segment_async
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import L4_PROMPT_VERSION, synthesize_memo
from agent.synthesis_types import DemographicMismatch, TargetClassification
from agent.target_id import detect_gross_demographic_mismatch, identify_target
from agent.telemetry import (
    current_account_id,
    current_brand_profile_id,
    current_run_id,
    make_run_id,
    run_dir,
)
from agent.vectors import NamedDisposition

_log = logging.getLogger(__name__)

# Rough per-unit cost estimates (USD) for the prepare() estimate.
# Deliberately approximate — the estimate exists so the customer sees a
# number before committing a credit, not for billing.
_COST_PER_AGENT = 0.03
_COST_PER_L2_SEGMENT = 0.04
_COST_L3 = 0.06
_COST_L4 = 0.32
_COST_TARGET_ID = 0.15
_COST_PER_RENDER = 0.005


def _persist_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)


# ---- RunPreparation ----


from dataclasses import dataclass, field  # noqa: E402


@dataclass
class RunPreparation:
    """The confirmation surface. What the customer reviews before a credit
    is debited. Held in memory by run(); also written to preparation.json
    as an audit record."""

    run_id: str
    config: RunConfig
    target_classification: TargetClassification
    audience_summary: dict
    panel: list[PanelAgent]
    provisional_dispositions: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    persona_cores_rendered: int = 0
    panel_version: str = ""
    # Gross declared-vs-ad demographic mismatch (deterministic, advisory).
    # None when the ad's apparent demographic is consistent with / broad
    # enough for the declared audience. When set, batch_run overrides --yes.
    demographic_mismatch: DemographicMismatch | None = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "config": self.config.to_dict(),
            "target_classification": self.target_classification.to_dict(),
            "audience_summary": self.audience_summary,
            "panel": [a.to_dict() for a in self.panel],
            "provisional_dispositions": list(self.provisional_dispositions),
            "estimated_cost_usd": round(self.estimated_cost_usd, 3),
            "persona_cores_rendered": self.persona_cores_rendered,
            "panel_version": self.panel_version,
            "demographic_mismatch": (
                self.demographic_mismatch.to_dict()
                if self.demographic_mismatch is not None else None
            ),
        }


# ---- Helpers ----


def _render_cache_dir(config: RunConfig) -> Path:
    """Brand-level render cache — persona cores amortize across runs of the
    same brand's library."""
    return (
        run_dir("", account_id=config.account_id,
                brand_profile_id=config.brand_profile_id).parent
        / "library_renders"
    )


def _set_context_vars(config: RunConfig, run_id: str) -> None:
    current_account_id.set(config.account_id)
    current_brand_profile_id.set(config.brand_profile_id)
    current_run_id.set(run_id)


def _disposition_description(nd: NamedDisposition) -> str:
    """A readable textual description of a disposition for target_id.
    target_id (Opus vision) classifies each disposition against the ad;
    the disposition is a vector, so we render it to prose here."""
    v = nd.vector
    parts: list[str] = []
    if nd.anchor.strip():
        parts.append(f"Oriented around: {nd.anchor.strip()}")
    parts.append(
        f"Category relationship: {v.category_relationship}. "
        f"Brand stance: {v.brand_stance}. "
        f"Price orientation: {v.price_orientation}. "
        f"Decision driver: {v.decision_driver}. "
        f"Category involvement: {v.category_involvement}. "
        f"Prior experience: {v.prior_experience_valence}. "
        f"Channel behaviour: {v.channel_behavior}. "
        f"Life stage: {v.life_stage}."
    )
    return " ".join(parts)


def _write_run_json(
    config: RunConfig, run_id: str, *, status: str, report: Report | None = None
) -> None:
    rd = run_dir(
        run_id, account_id=config.account_id,
        brand_profile_id=config.brand_profile_id,
    )
    payload = {
        "run_id": run_id,
        "status": status,
        "protocol_version": config.protocol_version,
        "l4_prompt_version": L4_PROMPT_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
        "report": report.to_dict() if report is not None else None,
    }
    _persist_json(rd / "run.json", payload)


# ---- Public API ----


class RunService:
    """Two-phase orchestrator. prepare() -> confirm -> commit()."""

    @staticmethod
    def prepare(config: RunConfig) -> RunPreparation:
        """Phase A: classify the ad, resolve the audience into a panel, warm
        the render cache, estimate cost. No credit debited, no L1 fired."""
        config.validate()
        if config.audience_spec is None:
            raise ValueError(
                "RunService.prepare requires config.audience_spec to be set"
            )
        spec = config.audience_spec

        run_id = make_run_id(config.seed, config.asset.label)
        _set_context_vars(config, run_id)
        rd = run_dir(
            run_id, account_id=config.account_id,
            brand_profile_id=config.brand_profile_id,
        )
        rd.mkdir(parents=True, exist_ok=True)
        _log.info("RunService.prepare run_id=%s", run_id)

        pack = load_pack(config.category)

        # Resolve the disposition library -> the run's NamedDispositions.
        library = DispositionLibrary.load(
            config.account_id, config.brand_profile_id
        )
        dispositions = library.resolve(spec.disposition_labels)

        # Build the panel (deterministic stratified allocation).
        panel = build_panel(
            spec, dispositions, category=config.category,
            segment_granularity=config.segment_granularity, seed=config.seed,
        )
        panel_version = compute_panel_version(
            spec, dispositions, category=config.category,
            segment_granularity=config.segment_granularity, seed=config.seed,
        )

        # target_id FIRST — classify each disposition against the ad.
        disposition_pool = [
            (d.label, _disposition_description(d)) for d in dispositions
        ]
        target_cls = identify_target(disposition_pool, config)
        _persist_json(rd / "target_classification.json", target_cls.to_dict())

        # Deterministic gross declared-vs-ad demographic sanity check (advisory;
        # batch_run overrides --yes when this is set). Distinct from the
        # disposition-level pool mismatch carried in no_match_note.
        demographic_mismatch = detect_gross_demographic_mismatch(
            spec.demographics, target_cls.inferred_audience
        )
        if demographic_mismatch is not None:
            _log.warning("gross demographic mismatch: %s", demographic_mismatch.message)

        # Warm the render cache: render each unique persona core once.
        cache_dir = _render_cache_dir(config)
        seen: set[str] = set()
        rendered = 0
        for agent in panel:
            h = agent.persona_core_hash
            if h in seen:
                continue
            seen.add(h)
            render_persona_core(
                agent.demographic, agent.disposition.vector,
                agent.chaos.vector, pack, anchor=agent.disposition.anchor,
                cache_dir=cache_dir,
            )
            rendered += 1

        n_segments = len({a.segment_key for a in panel})
        estimated_cost = (
            len(panel) * _COST_PER_AGENT
            + n_segments * _COST_PER_L2_SEGMENT
            + _COST_L3 + _COST_L4 + _COST_TARGET_ID
            + rendered * _COST_PER_RENDER
        )

        provisional = sorted(d.label for d in dispositions if d.provisional)
        audience_summary = {
            "demographics": [d.to_dict() for d in spec.demographics],
            "disposition_labels": list(spec.disposition_labels),
            "context_envelope": [c.label for c in spec.context_envelope],
            "chaos_distribution": [
                {"profile": p.label, "weight": w}
                for p, w in spec.chaos_distribution.weighted
            ],
            "panel_size": spec.panel_size,
            "n_segments": n_segments,
            "segment_granularity": config.segment_granularity,
        }

        prep = RunPreparation(
            run_id=run_id, config=config, target_classification=target_cls,
            audience_summary=audience_summary, panel=panel,
            provisional_dispositions=provisional,
            estimated_cost_usd=estimated_cost,
            persona_cores_rendered=rendered, panel_version=panel_version,
            demographic_mismatch=demographic_mismatch,
        )
        _persist_json(rd / "preparation.json", prep.to_dict())
        _persist_json(rd / "panel.json", [a.to_dict() for a in panel])
        _write_run_json(config, run_id, status="prepared")
        return prep

    @staticmethod
    def commit(prep: RunPreparation) -> Report:
        """Phase B: debit the credit (idempotently), then run L1 -> L4."""
        config = prep.config
        run_id = prep.run_id
        _set_context_vars(config, run_id)
        rd = run_dir(
            run_id, account_id=config.account_id,
            brand_profile_id=config.brand_profile_id,
        )

        debited = credits.debit_for_run(
            run_id, config.account_id, config.brand_profile_id
        )
        _log.info(
            "RunService.commit run_id=%s credit_debited=%s", run_id, debited
        )
        _write_run_json(config, run_id, status="committed")

        report = asyncio.run(RunService._commit_async(prep, rd))
        _write_run_json(config, run_id, status="complete", report=report)
        return report

    @staticmethod
    async def _commit_async(prep: RunPreparation, rd: Path) -> Report:
        config = prep.config
        pack = load_pack(config.category)
        cache_dir = _render_cache_dir(config)

        # ---- L1: bundled-agent fan-out ----
        l1_t0 = time.time()
        sem = asyncio.Semaphore(config.max_concurrent_agents)

        async def _bounded(agent: PanelAgent) -> AgentTranscript:
            async with sem:
                return await run_agent_async(
                    agent, config, pack, run_id=prep.run_id,
                    render_cache_dir=cache_dir,
                )

        transcripts = await asyncio.gather(*[_bounded(a) for a in prep.panel])
        transcripts = sorted(transcripts, key=lambda t: t.agent_id)
        _log.info(
            "L1 complete: %d transcripts in %.1fs",
            len(transcripts), time.time() - l1_t0,
        )
        _persist_json(
            rd / "transcripts.json", [t.to_dict() for t in transcripts]
        )

        # ---- L2: per-segment fan-out ----
        # Semaphore-bounded. At disposition x chaos-band granularity there
        # can be ~15-21 segments; firing them all at once is a token burst
        # that trips the 30K ITPM tier's 529 cascade. L2 payloads carry
        # transcripts, so they are heavier than L1 calls;
        # max_concurrent_agents (default 4) is the conservative bound.
        segment_of = {a.agent_id: a.segment_key for a in prep.panel}
        by_segment: dict[str, list[AgentTranscript]] = defaultdict(list)
        for t in transcripts:
            by_segment[segment_of[t.agent_id]].append(t)

        l2_sem = asyncio.Semaphore(config.max_concurrent_agents)

        async def _bounded_l2(label: str, ts: list[AgentTranscript]):
            async with l2_sem:
                return await synthesize_segment_async(label, ts, config)

        l2_coros = [
            _bounded_l2(label, ts) for label, ts in sorted(by_segment.items())
        ]
        l2_summaries = await asyncio.gather(*l2_coros)
        l2_summaries = sorted(l2_summaries, key=lambda s: s.segment_label)
        _persist_json(
            rd / "l2_summaries.json", [s.to_dict() for s in l2_summaries]
        )

        # ---- L3: population synthesis ----
        l3 = await asyncio.to_thread(
            synthesize_population, l2_summaries,
            prep.target_classification, config,
        )
        _persist_json(rd / "l3_summary.json", l3.to_dict())

        # ---- L3.5: funnel projection (deterministic Python) ----
        projection = project_funnel(
            l3, config.baseline_funnel, provided_inputs=config.provided_inputs()
        )
        _persist_json(rd / "l35_projection.json", projection.to_dict())
        # Log the prediction so a future calibration fit has the
        # prediction/outcome pair once the customer reports real numbers.
        calibration_log.record_prediction(
            prep.run_id, config.account_id, config.brand_profile_id,
            projection, config.baseline_funnel,
        )

        # ---- L4: strategic memo ----
        report = await asyncio.to_thread(
            synthesize_memo, l3, prep.target_classification, projection,
            config, provisional_dispositions=prep.provisional_dispositions,
        )
        _log.info(
            "L4 complete: verdict=%s confidence=%d bets=%d",
            report.verdict, report.confidence, len(report.bet_ranking),
        )
        return report

    @staticmethod
    def run(config: RunConfig) -> Report:
        """Convenience: prepare + auto-confirm + commit. The interactive
        confirmation lives in batch_run.py; this is for tests and scripts."""
        prep = RunService.prepare(config)
        return RunService.commit(prep)
