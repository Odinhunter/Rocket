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
from agent.progress import ProgressWriter
from agent.projection_l35 import project_funnel
from agent.provenance import prompt_fingerprints
from agent.render import RENDER_PROMPT_VERSION, render_persona_core
from agent.runtime import REACTION_PROTOCOL_VERSION, run_agent_async
from agent.schema import AgentTranscript, Report
from agent.synthesis_assess import ASSESS_PROMPT_VERSION, frozen_painmap_from_report
from agent.synthesis_l2 import synthesize_segment_async
from agent.synthesis_l3 import synthesize_population
from agent.decision import DECISION_VERSION
from agent.purpose import PURPOSE_VERSION
from agent.synthesis_l4 import L4_PROMPT_VERSION, synthesize_report
from agent.synthesis_prescribe import PRESCRIBE_PROMPT_VERSION
from agent.synthesis_types import (
    CoverageWarning,
    DemographicMismatch,
    DispositionScopeWarning,
    PurposeMismatch,
    TargetClassification,
)
from agent.target_id import (
    detect_gross_demographic_mismatch,
    detect_out_of_scope_dispositions,
    detect_purpose_mismatch,
    detect_thin_coverage,
    identify_target,
)
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


# --- L1 panel resilience ---
# A run must keep at least this fraction of its panel — and never lose a whole
# segment — or the synthesized population is too gutted to score. At high
# concurrency a correlated 529 burst can knock out a whole disposition/segment;
# the semaphore no longer serialises those calls, so the L1 gather must survive
# stray failures yet REFUSE to synthesize a verdict on a mangled panel. Below
# the floor we abort loudly and leave the run at 'committed' — re-running the
# same command resumes from the per-agent artifacts (only the missing agents
# re-fire, no new debit).
_MIN_PANEL_COMPLETION = 0.95


class PanelDegradedError(RuntimeError):
    """L1 lost too many agents — or a whole segment — for the synthesized
    population to be trustworthy. Raised instead of scoring a gutted panel."""


def reconcile_l1_results(
    panel: list[PanelAgent],
    results: list,
    *,
    min_completion: float = _MIN_PANEL_COMPLETION,
) -> tuple[list[AgentTranscript], list[int]]:
    """Split the L1 gather output (``asyncio.gather(..., return_exceptions=True)``)
    into landed transcripts and dropped agent_ids, then enforce the survivor
    floor and per-segment integrity. Pure + deterministic, so it is unit-tested
    offline. Raises PanelDegradedError when the panel is too degraded to trust.
    ``results`` is aligned to ``panel`` order (gather preserves order)."""
    seg_of = {a.agent_id: a.segment_key for a in panel}
    transcripts: list[AgentTranscript] = []
    dropped: list[int] = []
    for agent, res in zip(panel, results):
        if isinstance(res, BaseException):
            dropped.append(agent.agent_id)
        else:
            transcripts.append(res)
    transcripts.sort(key=lambda t: t.agent_id)

    expected = len(panel)
    if expected == 0:
        raise PanelDegradedError("empty panel — nothing to synthesize")
    succeeded = len(transcripts)
    completion = succeeded / expected
    survived = {seg_of[t.agent_id] for t in transcripts}
    lost_segments = sorted(set(seg_of.values()) - survived)
    if completion < min_completion or lost_segments:
        raise PanelDegradedError(
            f"L1 panel too degraded to trust: {succeeded}/{expected} agents "
            f"landed ({completion:.0%}; floor {min_completion:.0%})"
            + (f"; segment(s) wiped out: {lost_segments}" if lost_segments else "")
            + f". Aborting instead of scoring a gutted panel — re-run the same "
            f"command to resume (re-fires only the {len(dropped)} missing "
            f"agents, no new charge)."
        )
    return transcripts, dropped


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
    # rocket-2.1.0: declared audience intersects too few personas for a diverse
    # marketer-led panel (advisory; also the white-glove authoring signal).
    coverage_warning: CoverageWarning | None = None
    # v2.4: the ad's apparent job differs from the declared one (advisory,
    # warn-not-block). The load-bearing guardrail for the default-purpose user.
    purpose_mismatch: PurposeMismatch | None = None
    # v3 (A6): the panel carries <2 within-target dispositions, so HIGH trust —
    # and therefore a SCALE 'ship it' — is unreachable regardless of ad quality.
    # Deterministic, advisory, non-blocking; computed post-target_id. A message
    # string (None when >=2 within-target dispositions). docs/v3_protocol.md §8.
    trust_ceiling_warning: str | None = None
    # §2.3: a disposition in the pool is being used outside the sub-category it
    # was authored for (deterministic, advisory, no model call). None when no
    # disposition in the pool declares a scope — see DispositionScopeWarning on
    # why absence must never read as a mismatch.
    disposition_scope_warning: DispositionScopeWarning | None = None

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
            "coverage_warning": (
                self.coverage_warning.to_dict()
                if self.coverage_warning is not None else None
            ),
            "purpose_mismatch": (
                self.purpose_mismatch.to_dict()
                if self.purpose_mismatch is not None else None
            ),
            "trust_ceiling_warning": self.trust_ceiling_warning,
            "disposition_scope_warning": (
                self.disposition_scope_warning.to_dict()
                if self.disposition_scope_warning is not None else None
            ),
        }


# ---- Helpers ----


def _trust_ceiling_warning(n_within: int) -> str | None:
    """v3 (A6): the advisory shown when a panel carries <2 within-target
    dispositions, so a HIGH-trust verdict — and therefore a SCALE 'ship it' —
    is unreachable regardless of ad quality. None when >=2 (no ceiling). Pure
    + deterministic so it is offline-testable. docs/v3_protocol.md §8."""
    if n_within >= 2:
        return None
    return (
        f"This panel has {n_within} within-target disposition"
        f"{'' if n_within == 1 else 's'}; a HIGH-trust verdict — and therefore a "
        "SCALE 'ship it' call — is unreachable regardless of ad quality. Add >=2 "
        "within-target dispositions to the audience spec for a confident read."
    )


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


def _run_json_payload(
    config: RunConfig, run_id: str, *, status: str,
    report: Report | None = None, panel_health: dict | None = None,
) -> dict:
    """Assemble the run.json payload. rocket-2.2.0 stamps both prompt versions
    (assess + prescribe); l4_prompt_version is retained for back-compat with
    pre-2.2 run records and readers. panel_health (set at 'complete') records
    how much of the panel actually landed, so a degraded run can't be mistaken
    for a clean deterministic one."""
    return {
        "run_id": run_id,
        "status": status,
        "protocol_version": config.protocol_version,
        "reaction_protocol_version": REACTION_PROTOCOL_VERSION,
        # render_prompt_version completes the §10 version table in run.json, so a
        # run is attributable to its render arm (render-6-rc{n}) the same way
        # reaction_protocol_version attributes the reaction arm. It also lives in
        # persona_core_hash (cache key); this is the run-record attribution copy.
        "render_prompt_version": RENDER_PROMPT_VERSION,
        "l4_prompt_version": L4_PROMPT_VERSION,
        "assess_prompt_version": ASSESS_PROMPT_VERSION,
        "prescribe_prompt_version": PRESCRIBE_PROMPT_VERSION,
        "decision_version": DECISION_VERSION,
        "purpose_version": PURPOSE_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # §5.1: what the prompts ACTUALLY said, not what a hand-bumped version
        # constant claims they said. See agent/provenance.py.
        #
        # ⚠ Best-effort by construction. This function is called at
        # status='complete', at the end of the paid path, and anything that can
        # raise there replaces the return value of a synthesis we already paid
        # ~$4 for. A run with no fingerprints is a small loss; a run discarded
        # because its provenance record failed to compute is a total one.
        "prompt_fingerprints": _safe_prompt_fingerprints(),
        "config": config.to_dict(),
        "panel_health": panel_health,
        "report": report.to_dict() if report is not None else None,
    }


def stamp_config_provenance(
    config: RunConfig, disposition_pool: list[tuple[str, str]], panel_version: str,
) -> None:
    """Record WHICH inputs this run actually read, on the config that gets
    serialised into run.json. Called once, from `prepare`, as soon as both are
    resolved.

    Two gaps, both real before §5.1:

    `disposition_version` — the field and its hash function have existed since
    1.x and nothing ever called it, so every run on disk records the literal
    string `"auto"`. Two runs whose disposition library text differs are
    indistinguishable in the record. That is precisely the undeclared
    researcher freedom §5.1 exists to close: across 66 defensible
    configurations of one task, human-vs-silicon correlation ranged r = .23 to
    .84, so a result without its configuration is not a result.

    `panel_version` — computed and written to preparation.json only, while
    run.json is the record that travels with the report and the one a reader of
    a finished run opens.

    ⚠ Safe to turn `disposition_version` on: nothing reads it. It is not an
    input to `persona_core_hash` or `compute_panel_version`, so no entry of the
    brand-level render cache is invalidated and no paid re-render is triggered.

    ⚠ Extracted so it can be tested. `RunService.prepare` itself cannot run
    offline — it makes model calls, and `tests/conftest.py` refuses it outright
    — so the behaviour below is pinned here while the single call site is not.
    """
    config.disposition_version = config.compute_disposition_version(disposition_pool)
    config.panel_version = panel_version


def _safe_prompt_fingerprints() -> dict | None:
    try:
        return prompt_fingerprints()
    except Exception:  # noqa: BLE001 — see the note above; never fail a paid run
        _log.warning("prompt fingerprints unavailable for this run", exc_info=True)
        return None


def _write_run_json(
    config: RunConfig, run_id: str, *, status: str,
    report: Report | None = None, panel_health: dict | None = None,
) -> None:
    rd = run_dir(
        run_id, account_id=config.account_id,
        brand_profile_id=config.brand_profile_id,
    )
    _persist_json(
        rd / "run.json",
        _run_json_payload(
            config, run_id, status=status, report=report,
            panel_health=panel_health,
        ),
    )


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

        # Build the panel (deterministic stratified allocation). Marketer-led
        # composition (rocket-2.1.0) is opt-in via config.marketer_led.
        panel = build_panel(
            spec, dispositions, category=config.category,
            segment_granularity=config.segment_granularity, seed=config.seed,
            marketer_led=config.marketer_led, tail_fraction=config.tail_fraction,
        )
        panel_version = compute_panel_version(
            spec, dispositions, category=config.category,
            segment_granularity=config.segment_granularity, seed=config.seed,
            marketer_led=config.marketer_led, tail_fraction=config.tail_fraction,
        )

        # Coverage guard (marketer-led only): does the declared audience
        # intersect enough personas to compose a diverse panel? Advisory.
        coverage_warning = (
            detect_thin_coverage(spec, dispositions)
            if config.marketer_led else None
        )
        if coverage_warning is not None:
            _log.warning("thin audience coverage: %s", coverage_warning.message)

        # target_id FIRST — classify each disposition against the ad.
        disposition_pool = [
            (d.label, _disposition_description(d)) for d in dispositions
        ]
        stamp_config_provenance(config, disposition_pool, panel_version)
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

        # v2.4 declared-vs-apparent purpose check (advisory, warn-not-block).
        # The load-bearing guardrail for the common case: a default-purpose
        # (direct-sell) run of an awareness/brand ad would otherwise be scored
        # on the wrong ruler. Fires even when purpose is left default.
        purpose_mismatch = detect_purpose_mismatch(
            config.creative_inputs.purpose,
            target_cls.inferred_purpose,
            target_cls.purpose_reasoning,
        )
        if purpose_mismatch is not None:
            _log.warning("purpose mismatch: %s", purpose_mismatch.message)

        # §2.3: is any disposition being used outside the sub-category it was
        # authored for? Deterministic, no model call, no cost — and computed
        # from the config alone (asset label + category) so it reads the same on
        # every re-run of the same setup. None when nothing in the pool declares
        # a scope, which is the state of every library until one is authored.
        disposition_scope_warning = detect_out_of_scope_dispositions(
            dispositions,
            asset_label=config.asset.label,
            category=config.category,
        )
        if disposition_scope_warning is not None:
            _log.warning(
                "disposition scope mismatch: %s", disposition_scope_warning.message
            )

        # v3 (A6): a HIGH-trust verdict needs >=2 within-target dispositions.
        # If the resolved panel has fewer, SCALE ('ship it') is unreachable
        # regardless of ad quality — disclose it now, on the pre-run surface,
        # so the marketer can broaden the audience spec. docs/v3_protocol.md §8.
        trust_ceiling_warning = _trust_ceiling_warning(
            len(target_cls.within_target_labels())
        )
        if trust_ceiling_warning is not None:
            _log.warning("trust ceiling: %s", trust_ceiling_warning)

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
            coverage_warning=coverage_warning,
            purpose_mismatch=purpose_mismatch,
            trust_ceiling_warning=trust_ceiling_warning,
            disposition_scope_warning=disposition_scope_warning,
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

        report, panel_health = asyncio.run(RunService._commit_async(prep, rd))
        _write_run_json(
            config, run_id, status="complete", report=report,
            panel_health=panel_health,
        )
        return report

    @staticmethod
    async def _commit_async(prep: RunPreparation, rd: Path) -> tuple[Report, dict]:
        config = prep.config
        pack = load_pack(config.category)
        cache_dir = _render_cache_dir(config)

        # ---- L1: bundled-agent fan-out ----
        l1_t0 = time.time()
        sem = asyncio.Semaphore(config.max_concurrent_agents)
        # The run's only report of life between 'committed' and 'complete'.
        # Advancing in `finally` counts an agent that RAISED as processed, which
        # is right: the denominator is work attempted, and a panel that loses
        # agents must not leave the counter stuck short of its total forever.
        progress = ProgressWriter(rd)
        progress.phase("reactions", total=len(prep.panel))

        async def _bounded(agent: PanelAgent) -> AgentTranscript:
            async with sem:
                try:
                    return await run_agent_async(
                        agent, config, pack, run_id=prep.run_id,
                        render_cache_dir=cache_dir,
                    )
                finally:
                    progress.advance()

        results = await asyncio.gather(
            *[_bounded(a) for a in prep.panel], return_exceptions=True
        )
        # Survive stray failures, but abort loudly on a gutted panel (floor +
        # per-segment integrity) rather than score an unrepresentative sample.
        transcripts, dropped_agent_ids = reconcile_l1_results(prep.panel, results)
        panel_health = {
            "expected": len(prep.panel),
            "succeeded": len(transcripts),
            "dropped": len(dropped_agent_ids),
            "dropped_agent_ids": dropped_agent_ids,
            "completion": round(len(transcripts) / len(prep.panel), 4),
            "degraded": bool(dropped_agent_ids),
        }
        _log.info(
            "L1 complete: %d/%d transcripts in %.1fs (%d dropped)",
            len(transcripts), len(prep.panel),
            time.time() - l1_t0, len(dropped_agent_ids),
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
                try:
                    return await synthesize_segment_async(label, ts, config)
                finally:
                    progress.advance()

        l2_labels = [label for label, _ in sorted(by_segment.items())]
        progress.phase("segments", total=len(l2_labels))
        l2_coros = [
            _bounded_l2(label, ts) for label, ts in sorted(by_segment.items())
        ]
        # Survive a stray per-segment failure (an API error, or an L2 output
        # shape the parser can't use) rather than crash the whole committed run
        # after the agent money is already spent — the same posture as L1. A
        # dropped segment loses its agents from the population distribution, so
        # it is recorded in panel_health (never silent), not swallowed.
        l2_results = await asyncio.gather(*l2_coros, return_exceptions=True)
        l2_summaries = []
        l2_failed_segments: list[str] = []
        for label, res in zip(l2_labels, l2_results):
            if isinstance(res, Exception):
                _log.warning("L2 segment %r failed: %s", label, res)
                l2_failed_segments.append(label)
            else:
                l2_summaries.append(res)
        if not l2_summaries:
            raise RuntimeError(
                "L2 produced zero usable segment summaries — the whole "
                "synthesis is gutted; aborting rather than scoring nothing."
            )
        l2_summaries = sorted(l2_summaries, key=lambda s: s.segment_label)
        panel_health["l2_segments_expected"] = len(l2_labels)
        panel_health["l2_segments_failed"] = len(l2_failed_segments)
        panel_health["l2_failed_segments"] = l2_failed_segments
        if l2_failed_segments:
            panel_health["degraded"] = True
        _persist_json(
            rd / "l2_summaries.json", [s.to_dict() for s in l2_summaries]
        )

        # ---- L3: population synthesis ----
        progress.phase("population")
        l3 = await asyncio.to_thread(
            synthesize_population, l2_summaries,
            prep.target_classification, config,
        )
        _persist_json(rd / "l3_summary.json", l3.to_dict())

        # ---- L3.5: funnel projection (deterministic Python) ----
        # Always compute + persist + log the prediction (so a future calibration
        # fit has the prediction/outcome pair once the customer reports real
        # numbers). But v3 D4: the projection is heuristic/unfitted, so unless
        # funnel_enabled it is NOT handed to L4 and NOT attached to the report —
        # the unfit numbers must not reach the customer or move the prescription.
        projection = project_funnel(
            l3, config.baseline_funnel, provided_inputs=config.provided_inputs()
        )
        _persist_json(rd / "l35_projection.json", projection.to_dict())
        calibration_log.record_prediction(
            prep.run_id, config.account_id, config.brand_profile_id,
            projection, config.baseline_funnel,
        )
        report_projection = projection if config.funnel_enabled else None

        # ---- L4: assess (raw corpus -> PainMap) -> prescribe (from PainMap) ----
        # on_phase fires from inside the to_thread worker, which is why
        # ProgressWriter locks with a threading.Lock and not an asyncio one.
        report = await asyncio.to_thread(
            synthesize_report, transcripts, l3, prep.target_classification,
            report_projection, config,
            provisional_dispositions=prep.provisional_dispositions,
            on_phase=progress.phase,
        )
        # The PainMap is a first-class, standalone brand-manager deliverable.
        _persist_json(rd / "painmap.json", frozen_painmap_from_report(report))
        _log.info(
            "L4 complete: verdict=%s confidence=%d pains=%d bets=%d",
            report.verdict, report.confidence, len(report.pain_map),
            len(report.bet_ranking),
        )
        progress.finish()
        return report, panel_health

    @staticmethod
    def run(config: RunConfig) -> Report:
        """Convenience: prepare + auto-confirm + commit. The interactive
        confirmation lives in batch_run.py; this is for tests and scripts."""
        prep = RunService.prepare(config)
        return RunService.commit(prep)
