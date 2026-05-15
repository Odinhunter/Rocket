"""Phase 4 offline test: the L3.5 funnel projection layer. Pins the
honesty contract — rates are baseline-multiplier-derived (never bare
absolutes), bands are present and ordered, basis == 'heuristic_v1', small
segments get wider bands, and the projection validates against the Report
schema's funnel-projection invariants. No API calls.

Run: python tests/test_l35_projection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.projection_l35 import (
    DEFAULT_BASELINE_FUNNEL,
    MULTIPLIER_TABLE_VERSION,
    project_funnel,
)
from agent.schema import BehavioralSignalDistribution, _validate_funnel_projection
from agent.synthesis_types import L3Summary


def _dist(counts: dict[str, int], would_act: int, n: int) -> BehavioralSignalDistribution:
    return BehavioralSignalDistribution(
        counts=counts, would_act_within_week_count=would_act, n=n
    )


def _l3(pop: BehavioralSignalDistribution, segments: dict) -> L3Summary:
    return L3Summary(
        population_behavioral_distribution=pop,
        segment_behavioral_distributions=segments,
    )


def test_rates_are_baseline_multiples() -> None:
    """Every rate must be the baseline rate times a multiplier — never a
    bare invented absolute. A high-engagement distribution lifts click
    above baseline; a scroll-heavy one pushes stop below baseline."""
    baseline = {"stop_rate": 0.10, "click_rate": 0.02, "visit_rate": 0.015,
                "convert_rate": 0.006}
    hot = _dist({"tap_cta": 10, "seek_info": 8, "linger": 2}, would_act=10, n=20)
    cold = _dist({"scroll_past": 18, "linger": 2}, would_act=0, n=20)
    proj_hot = project_funnel(_l3(hot, {}), baseline)
    proj_cold = project_funnel(_l3(cold, {}), baseline)

    # Hot: high tap_cta + seek_info -> click ABOVE baseline.
    assert proj_hot.overall.click_rate > baseline["click_rate"], (
        f"hot click {proj_hot.overall.click_rate} not above baseline"
    )
    # Cold: scroll-heavy -> stop BELOW baseline; no would_act -> convert below.
    assert proj_cold.overall.stop_rate < baseline["stop_rate"], (
        f"cold stop {proj_cold.overall.stop_rate} not below baseline"
    )
    assert proj_cold.overall.convert_rate < baseline["convert_rate"]
    print("  OK  rates are baseline multiples — hot lifts, cold suppresses")


def test_bands_present_and_ordered() -> None:
    baseline = dict(DEFAULT_BASELINE_FUNNEL)
    d = _dist({"tap_cta": 5, "seek_info": 5, "scroll_past": 10}, would_act=5, n=20)
    proj = project_funnel(_l3(d, {"disp_a::moderate": d}), baseline)
    for fr in (proj.overall, proj.by_segment[0].funnel_rates):
        for stage in ("stop", "click", "visit", "convert"):
            rate = getattr(fr, f"{stage}_rate")
            lo, hi = getattr(fr, f"{stage}_band")
            assert lo <= rate <= hi, f"{stage}: {rate} not within [{lo}, {hi}]"
            assert lo >= 0.0, f"{stage}: band low {lo} is negative"
    print("  OK  every rate sits inside an ordered, non-negative band")


def test_basis_names_the_regime() -> None:
    proj = project_funnel(_l3(_dist({"linger": 5}, 1, 5), {}), None)
    assert proj.overall.basis == "heuristic_v1" == MULTIPLIER_TABLE_VERSION
    assert "heuristic_v1" in proj.calibration_note
    assert "not fitted" in proj.calibration_note.lower()
    # No customer baseline -> baseline_source says so explicitly.
    assert "default baseline" in proj.overall.baseline_source.lower()
    print("  OK  basis == 'heuristic_v1'; calibration_note carries the hedge")


def test_small_segments_get_wider_bands() -> None:
    """A 2-agent segment must get a wider fractional band than a 200-agent
    one — the heuristic must not pretend a tiny segment is precise."""
    counts_big = {"tap_cta": 100, "scroll_past": 100}
    counts_small = {"tap_cta": 1, "scroll_past": 1}
    big = _dist(counts_big, would_act=100, n=200)
    small = _dist(counts_small, would_act=1, n=2)
    big_fr = project_funnel(_l3(big, {}), None).overall
    small_fr = project_funnel(_l3(small, {}), None).overall

    def frac(fr) -> float:
        lo, hi = fr.click_band
        return (hi - lo) / fr.click_rate if fr.click_rate else 0.0

    assert frac(small_fr) > frac(big_fr), (
        f"small-segment band fraction {frac(small_fr):.3f} not wider than "
        f"big-segment {frac(big_fr):.3f}"
    )
    print(f"  OK  small segments get wider bands "
          f"({frac(small_fr):.2f} vs {frac(big_fr):.2f} fractional half-span x2)")


def test_per_segment_projection() -> None:
    pop = _dist({"tap_cta": 6, "scroll_past": 9, "linger": 5}, would_act=6, n=20)
    seg_hot = _dist({"tap_cta": 8, "seek_info": 2}, would_act=8, n=10)
    seg_cold = _dist({"scroll_past": 9, "linger": 1}, would_act=0, n=10)
    proj = project_funnel(
        _l3(pop, {"disp_a::impulsive": seg_hot, "disp_a::deliberate": seg_cold}),
        None,
    )
    assert len(proj.by_segment) == 2
    labels = {s.segment_label for s in proj.by_segment}
    assert labels == {"disp_a::impulsive", "disp_a::deliberate"}
    hot = next(s for s in proj.by_segment if s.segment_label == "disp_a::impulsive")
    cold = next(s for s in proj.by_segment if s.segment_label == "disp_a::deliberate")
    # The hot segment should out-convert the cold one.
    assert hot.funnel_rates.convert_rate > cold.funnel_rates.convert_rate
    print("  OK  per-segment projections differentiate hot vs cold segments")


def test_projection_validates_against_schema() -> None:
    pop = _dist({"tap_cta": 6, "scroll_past": 9, "linger": 5}, would_act=6, n=20)
    seg = _dist({"tap_cta": 3, "scroll_past": 2}, would_act=3, n=5)
    proj = project_funnel(_l3(pop, {"disp_a::moderate": seg}), None)
    _validate_funnel_projection(proj)  # raises SchemaError on any violation
    print("  OK  the projection passes _validate_funnel_projection")


def test_rejects_incomplete_baseline() -> None:
    try:
        project_funnel(_l3(_dist({"linger": 5}, 1, 5), {}), {"stop_rate": 0.1})
    except ValueError as e:
        assert "missing required keys" in str(e)
        print("  OK  project_funnel rejects an incomplete baseline_funnel:", e)
        return
    raise AssertionError("project_funnel should reject an incomplete baseline")


def main() -> None:
    print("=== L3.5 funnel projection smoke ===")
    test_rates_are_baseline_multiples()
    test_bands_present_and_ordered()
    test_basis_names_the_regime()
    test_small_segments_get_wider_bands()
    test_per_segment_projection()
    test_projection_validates_against_schema()
    test_rejects_incomplete_baseline()
    print("PASS — L3.5 honesty contract pinned: baseline multiples, bands, basis.")


if __name__ == "__main__":
    main()
