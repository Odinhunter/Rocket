"""Purpose registry — the v2.4 "purpose layer".

An ad has a *job*. Direct-sell (make a new prospect buy now) is one job;
awareness/informer (make people notice + understand) is another; judging the
second by the first's ruler ("would you buy this week") is a category error the
whole effectiveness field warns against (95:5 rule, See-Think-Do-Care, Binet &
Field, System1 Star/Spike). See docs/v2_4_purpose_taxonomy.md.

This module is the single source of truth for the five jobs and what each one
means for scoring. A purpose is a *preset* over a handful of knobs; the reaction
layer stays purpose-BLIND (the panel never learns the declared job — telling it
would inflate the grade by construction). Purpose only selects which
already-captured signals get scored and where the bar sits.

Consumption:
  - agent/decision.py maps `headline_metric` (a string key, not a callable —
    keeps this module free of a decision.py import) to a metric function and
    reads `provisional_scale_floor` for the per-purpose SCALE bar.
  - agent/target_id.py infers the ad's *apparent* purpose and compares it to the
    declared one (the mismatch guard).
  - batch_run.py renders `metric_label` / `label` in the brand-facing headline.

Calibration honesty: every `provisional_scale_floor` here is a desk-research
best-guess, NOT an anchor run (same posture as v2.3's _SCALE_FLOOR=0.75, a
documented known risk). direct-sell's 0.75 is the only one clearing even a
*flawed* anchor. cold-hook reuses observed signals over a proven decision
structure, so its provisional bar is relatively safe; brand-building and
informer have NO reference point and a novel output shape, so their bars lean
deliberately conservative (fail toward ITERATE, never false-SCALE). All are
replaced by measured values once per-purpose anchor runs exist.
"""

from __future__ import annotations

from dataclasses import dataclass


# Bump when the preset table (metrics, frames, floors, probe wiring) changes.
# Owns the per-purpose metric selection + per-purpose provisional floors —
# kept separate from DECISION_VERSION (direct-sell SCALE-floor lineage) so the
# two calibration histories don't collide.
PURPOSE_VERSION = "purpose-1"


# Purpose identifiers (the declared job). direct_sell is the default — the D2C
# ICP's common case and the only job anchored today (= v2.3).
DIRECT_SELL = "direct_sell"
COLD_HOOK = "cold_hook"
AWARENESS_INFORMER = "awareness_informer"
BRAND_BUILDING = "brand_building"
RETAIN_WINBACK = "retain_winback"


@dataclass(frozen=True)
class PurposePreset:
    """One job's scoring ruler. These knobs ARE the design (taxonomy §5)."""

    name: str                       # the declared-job identifier (above)
    label: str                      # human-readable, for render + mismatch copy
    # headline_metric: a string KEY resolved to a function in decision.py. The
    # metric computed as the brand-facing headline for this job.
    headline_metric: str
    metric_label: str               # render phrasing, e.g. "stop-and-lean-in rate"
    # audience_frame: who the metric is computed over.
    #   narrow      -> within-target dispositions (new prospects)
    #   broad_cold  -> the whole cold panel / low-intent contexts
    #   broad       -> the whole category-buyer population
    #   existing    -> existing / lapsed-customer dispositions
    audience_frame: str
    # scored_probes: which ALWAYS-ON self-report probes this job's metric reads.
    # (All probes are asked on every run regardless; this is about scoring, not
    # capture.) "novelty" for informer, "brand_attribution" for brand-building.
    scored_probes: tuple[str, ...] = ()
    # provisional_scale_floor: the per-purpose SCALE bar. Desk-research
    # best-guess (see module docstring); recalibrated by anchor runs.
    provisional_scale_floor: float = 0.75
    # win_direction: what an R7 "win" means for this job (render + docs).
    win_direction: str = "buy"
    # decision_basis: one-liner on what SCALE/ITERATE/RETARGET/REBUILD keys off.
    decision_basis: str = ""
    # requires_existing_customers: retain is INERT until the library carries
    # loyalist/lapsed dispositions; flag it so callers never imply it "works".
    requires_existing_customers: bool = False
    # multi_target: the metric is a breadth read across dispositions, not a
    # single within/outside/ambiguous rate (informer; brand-building leans broad
    # too). Signals the render + aggregation that the output shape differs.
    multi_target: bool = False


PURPOSE_REGISTRY: dict[str, PurposePreset] = {
    DIRECT_SELL: PurposePreset(
        name=DIRECT_SELL,
        label="Direct-sell",
        headline_metric="within_target_action",
        metric_label="would act this week",
        audience_frame="narrow",
        scored_probes=(),
        # MUST match decision._SCALE_FLOOR until P3 unifies the source of truth
        # (decision.py will read this value once the dispatcher lands).
        provisional_scale_floor=0.75,
        win_direction="buy",
        decision_basis="within-target action rate + load-bearing pain (= v2.3)",
    ),
    COLD_HOOK: PurposePreset(
        name=COLD_HOOK,
        label="Cold-hook",
        headline_metric="cold_stop_lean_in",
        metric_label="stop-and-lean-in rate (cold)",
        audience_frame="broad_cold",
        scored_probes=(),
        # Reuses observed action signals over the proven decision structure, so
        # a relatively safe provisional bar. Placeholder set here; the metric +
        # any tuning land in P3.
        provisional_scale_floor=0.55,
        win_direction="curiosity",
        decision_basis="stop-and-lean-in over a cold frame + attention-stage pain",
    ),
    RETAIN_WINBACK: PurposePreset(
        name=RETAIN_WINBACK,
        label="Retain / win-back",
        headline_metric="reengagement",
        metric_label="would re-engage (reorder / return)",
        audience_frame="existing",
        scored_probes=(),
        provisional_scale_floor=0.75,   # metric ≈ direct-sell; same bar shape
        win_direction="reorder",
        decision_basis="re-engagement among existing/lapsed + reorder friction",
        requires_existing_customers=True,
    ),
    BRAND_BUILDING: PurposePreset(
        name=BRAND_BUILDING,
        label="Brand-building",
        headline_metric="resonance_brand_memory",
        metric_label="resonance × brand-memorability",
        audience_frame="broad",
        scored_probes=("brand_attribution",),
        # ⚠ KNOWN LIMITATION (2026-07-12 Starbucks anchor run, docs/v2_4 §brand_recall):
        # the ATTRIBUTION half (brand_recall) is UNVALIDATED and near-degenerate on any
        # logo-in-frame creative. R2 comprehension makes the blind reaction NAME the
        # brand (100% did on the anchor), and that text is replayed into the reflection
        # turn, so brand_recall reads the persona's own prior words, not memory. On such
        # creatives the metric effectively COLLAPSES to its resonance half. A genuine
        # attribution read needs a probe REDESIGN (attribution off R1/R2) + a mark-absent
        # / logo-late creative — parked. Ship brand-building on its resonance half; treat
        # the attribution gate as provisional.
        # NO reference point + a broad frame → deliberately conservative.
        provisional_scale_floor=0.60,
        win_direction="n/a",
        decision_basis="broad positive-emotion breadth + correct brand attribution",
        multi_target=True,
    ),
    AWARENESS_INFORMER: PurposePreset(
        name=AWARENESS_INFORMER,
        label="Awareness / informer",
        headline_metric="breadth_registration",
        # Honesty: this measures breadth of NOTICING / NEWS (R8 novelty across
        # distinct dispositions), NOT R2 comprehension — comprehension is prose
        # we do not structurally read; true-comprehension breadth is deferred to
        # the informer anchor run.
        metric_label="breadth of noticing / news",
        audience_frame="broad",
        scored_probes=("novelty",),
        # A breadth COUNT over distinct dispositions, not an agent rate — the
        # provisional bar is a coverage fraction (how many audience types
        # registered the news). See decision._resolve_informer.
        provisional_scale_floor=0.60,
        win_direction="n/a",
        decision_basis="how many distinct audience types registered the ad as news (novelty)",
        multi_target=True,
    ),
}


# Deterministic order for iteration / CLI help / the target_id enum.
PURPOSE_ORDER: tuple[str, ...] = (
    DIRECT_SELL,
    COLD_HOOK,
    AWARENESS_INFORMER,
    BRAND_BUILDING,
    RETAIN_WINBACK,
)

VALID_PURPOSES: frozenset[str] = frozenset(PURPOSE_REGISTRY)

DEFAULT_PURPOSE = DIRECT_SELL


def resolve_purpose(name: str | None) -> PurposePreset:
    """Return the preset for a declared purpose; default to direct-sell.

    None / empty string → direct-sell (the default, and how legacy runs that
    never set a purpose resolve). Raises ValueError on an unknown non-empty name
    so a typo'd spec fails loud rather than silently scoring on the wrong ruler.
    """
    if not name:
        return PURPOSE_REGISTRY[DEFAULT_PURPOSE]
    preset = PURPOSE_REGISTRY.get(name)
    if preset is None:
        valid = ", ".join(PURPOSE_ORDER)
        raise ValueError(f"unknown purpose {name!r}; valid: {valid}")
    return preset
