"""L3.5 — the funnel projection layer (rocket-2.0.0).

A NEW layer between L3 and L4. Deterministic Python, ZERO API calls. It
turns the R7 behavioral-signal distributions (computed by L2/L3) into a
projected marketing funnel — stop / click / visit / convert rates — by
segment and overall.

The honesty contract (user-decided, "Ship heuristic_v1 with bands"):
  - Every rate is a MULTIPLIER on the customer's OWN baseline funnel,
    never a bare invented absolute.
  - Every rate is shown WITH a confidence band; bands widen for small
    segments and carry a fixed heuristic-regime floor.
  - The `basis` field literally says "heuristic_v1" so the buyer knows
    this is not fitted to in-market outcomes.
  - calibration_note carries the plain-language hedge.

This layer is deliberately separate from the agent protocol and from
L2/L3/L4 so the multiplier table can later be FITTED to real customer
outcomes (Phase 7 logs the inputs) without touching anything upstream.
MULTIPLIER_TABLE_VERSION stamps every projection for that future fit.

The heuristic_v1 multiplier table (the strawman the user approved):
  tap_cta + seek_info combined >= 30%  -> click rate  x1.2-1.5
  tap_cta + seek_info combined < 10%   -> click rate  x0.6-0.8
  scroll_past >= 50%                   -> stop rate   x0.6-0.8
  would_act_within_week >= 25%         -> convert     x1.2-1.4
  band halfwidth = max(15%, 30%/sqrt(segment_n)) + 10% heuristic floor
"""

from __future__ import annotations

import math

from agent.schema import (
    BehavioralSignalDistribution,
    FunnelProjection,
    FunnelRates,
    FunnelStageMeta,
    SegmentProjection,
)
from agent.synthesis_types import L3Summary

# Bumps whenever the multiplier functions below change — so a logged
# prediction (Phase 7 calibration scaffolding) is always attributable to a
# specific calibration regime.
MULTIPLIER_TABLE_VERSION = "heuristic_v1"

# Stage -> (observable label, measurement_basis, inputs that GROUND it).
# Each funnel stage names the real ad-platform metric it predicts. A stage is
# "grounded" only when every required input was provided this run; otherwise
# it is a "scenario" (image-only) row. `stop` is MODELED for static creatives
# (no direct pre-click observable on a static image) and `visit` stays MODELED
# until landing-page analysis is wired — both have no required inputs, so they
# are always grounded. `click` needs the ad copy, `convert` needs the offer.
# NOTE for a future calibration fit: predictions whose stage status is
# "scenario" are image-only and MUST be filtered out before fitting that stage.
STAGE_OBSERVABLES: list[tuple[str, str, str, list[str]]] = [
    ("stop", "thumbstop / hook rate (modeled — no direct observable for a static creative)",
     "modeled", []),
    ("click", "CTR (link click-through rate)", "direct_observable", ["ad_copy"]),
    ("visit", "landing-page-view rate (modeled — landing-page analysis not yet wired)",
     "modeled", []),
    ("convert", "purchase rate", "direct_observable", ["offer"]),
]

# Used when the customer has not supplied their own baseline funnel. These
# are conservative mid-market D2C-on-Meta placeholders; baseline_source
# names them explicitly so the buyer is never misled into thinking the
# numbers are fitted to their account.
DEFAULT_BASELINE_FUNNEL: dict[str, float] = {
    "stop_rate": 0.10,     # impression -> stopped scroll
    "click_rate": 0.012,   # impression -> click
    "visit_rate": 0.010,   # impression -> landed + browsed
    "convert_rate": 0.004,  # impression -> bought within ~1 week
}

_CALIBRATION_NOTE = (
    "Directional estimate — basis: heuristic_v1. These rates are NOT fitted "
    "to in-market outcomes. They are multipliers applied to your baseline "
    "funnel, derived from how the simulated audience said it would behave. "
    "Read the per-segment direction and the relative spread, not the "
    "decimal places. Bands tighten as your account's real outcome history "
    "accrues."
)


# ---- Multiplier table (heuristic_v1) ----


def _lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """Linear interpolation, clamped to [y0, y1]."""
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    t = max(0.0, min(1.0, t))
    return y0 + t * (y1 - y0)


def _stop_multiplier(scroll_past_pct: float) -> float:
    """High scroll_past -> stop rate down. Monotonically non-increasing."""
    if scroll_past_pct >= 0.50:
        return _lerp(scroll_past_pct, 0.50, 1.00, 0.80, 0.60)
    return _lerp(scroll_past_pct, 0.00, 0.50, 1.20, 1.00)


def _click_multiplier(engage_pct: float) -> float:
    """engage_pct = (tap_cta + seek_info) share. Monotonically increasing."""
    if engage_pct >= 0.30:
        return _lerp(engage_pct, 0.30, 0.60, 1.20, 1.50)
    if engage_pct < 0.10:
        return _lerp(engage_pct, 0.00, 0.10, 0.60, 0.80)
    return _lerp(engage_pct, 0.10, 0.30, 0.80, 1.20)


def _visit_multiplier(engage_pct: float, save_pct: float) -> float:
    """Visit tracks click, damped, plus a small lift from 'save' (saved now,
    may browse later). Monotonically increasing in both inputs."""
    click = _click_multiplier(engage_pct)
    damped = 1.0 + (click - 1.0) * 0.8
    return damped + save_pct * 0.3


def _convert_multiplier(would_act_pct: float) -> float:
    """would_act_pct = share that said they'd act within the week.
    Monotonically increasing."""
    if would_act_pct >= 0.25:
        return _lerp(would_act_pct, 0.25, 0.60, 1.20, 1.40)
    return _lerp(would_act_pct, 0.00, 0.25, 0.70, 1.20)


def _band_halfwidth_fraction(n: int) -> float:
    """Fractional half-width of the confidence band. Small segments get
    wider bands; a fixed 10% floor reflects the heuristic_v1 regime's
    irreducible uncertainty."""
    if n <= 0:
        return 1.0
    return max(0.15, 0.30 / math.sqrt(n)) + 0.10


# ---- Projection ----


def _proportions(dist: BehavioralSignalDistribution) -> dict[str, float]:
    """Action -> share of the segment. Empty dist -> all zeros."""
    n = dist.n
    if n <= 0:
        return {
            "scroll_past": 0.0, "linger": 0.0, "tap_cta": 0.0,
            "save": 0.0, "share": 0.0, "seek_info": 0.0, "would_act": 0.0,
        }
    return {
        "scroll_past": dist.counts.get("scroll_past", 0) / n,
        "linger": dist.counts.get("linger", 0) / n,
        "tap_cta": dist.counts.get("tap_cta", 0) / n,
        "save": dist.counts.get("save", 0) / n,
        "share": dist.counts.get("share", 0) / n,
        "seek_info": dist.counts.get("seek_info", 0) / n,
        "would_act": dist.would_act_within_week_count / n,
    }


def _funnel_rates(
    dist: BehavioralSignalDistribution,
    baseline: dict[str, float],
    baseline_source: str,
) -> FunnelRates:
    """Project one FunnelRates from one behavioral distribution."""
    p = _proportions(dist)
    engage = p["tap_cta"] + p["seek_info"]

    stop = baseline["stop_rate"] * _stop_multiplier(p["scroll_past"])
    click = baseline["click_rate"] * _click_multiplier(engage)
    visit = baseline["visit_rate"] * _visit_multiplier(engage, p["save"])
    convert = baseline["convert_rate"] * _convert_multiplier(p["would_act"])

    hw = _band_halfwidth_fraction(dist.n)

    def band(rate: float) -> tuple[float, float]:
        lo = max(0.0, rate * (1.0 - hw))
        hi = rate * (1.0 + hw)
        return (lo, hi)

    return FunnelRates(
        stop_rate=stop, stop_band=band(stop),
        click_rate=click, click_band=band(click),
        visit_rate=visit, visit_band=band(visit),
        convert_rate=convert, convert_band=band(convert),
        basis=MULTIPLIER_TABLE_VERSION,
        baseline_source=baseline_source,
    )


def project_funnel(
    l3_summary: L3Summary,
    baseline_funnel: dict[str, float] | None = None,
    *,
    baseline_source: str | None = None,
    provided_inputs: list[str] | None = None,
) -> FunnelProjection:
    """Produce a FunnelProjection from L3's behavioral-signal distributions.

    baseline_funnel: the customer's real funnel rates (stop/click/visit/
    convert, each a float in 0..1). When None, DEFAULT_BASELINE_FUNNEL is
    used and baseline_source records that explicitly.

    provided_inputs: the creative inputs supplied this run (e.g. "ad_copy",
    "offer" — see RunConfig.provided_inputs()). Drives per-stage gating: a
    stage whose required inputs are all present is "grounded", else
    "scenario" (image-only). Rates are computed for all four stages
    regardless; gating only sets each stage's status (for display + a future
    calibration fit). Defaults to none provided (all stages that need an
    input render as scenario).
    """
    if baseline_funnel is None:
        baseline = dict(DEFAULT_BASELINE_FUNNEL)
        source = baseline_source or (
            "rocket default baseline (no customer baseline supplied)"
        )
    else:
        missing = {"stop_rate", "click_rate", "visit_rate", "convert_rate"} - set(
            baseline_funnel
        )
        if missing:
            raise ValueError(
                f"baseline_funnel is missing required keys: {sorted(missing)}"
            )
        baseline = {k: float(baseline_funnel[k]) for k in baseline_funnel}
        source = baseline_source or "customer-supplied baseline funnel"

    overall = _funnel_rates(
        l3_summary.population_behavioral_distribution, baseline, source
    )
    by_segment = [
        SegmentProjection(
            segment_label=label,
            behavioral_distribution=dist,
            funnel_rates=_funnel_rates(dist, baseline, source),
        )
        for label, dist in sorted(
            l3_summary.segment_behavioral_distributions.items()
        )
    ]
    provided = set(provided_inputs or [])
    stage_meta = [
        FunnelStageMeta(
            stage_key=key,
            observable_label=label,
            measurement_basis=basis,
            required_inputs=list(reqs),
            status="grounded" if set(reqs) <= provided else "scenario",
        )
        for key, label, basis, reqs in STAGE_OBSERVABLES
    ]
    return FunnelProjection(
        overall=overall,
        by_segment=by_segment,
        population_behavioral_distribution=(
            l3_summary.population_behavioral_distribution
        ),
        calibration_note=_CALIBRATION_NOTE,
        provided_inputs=sorted(provided),
        stage_meta=stage_meta,
    )
