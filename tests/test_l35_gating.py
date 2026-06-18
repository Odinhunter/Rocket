"""Offline test: funnel stage→observable mapping + input gating.

Pins that (a) stages map to the right observable + measurement_basis, (b) a
stage is "grounded" only when its causal inputs were provided, else
"scenario", (c) gating is DISPLAY-ONLY — the numeric rates never depend on
which inputs were provided, (d) `stop` is always grounded+modeled, and (e)
stage_meta round-trips and defaults empty for legacy run.json. No API calls.

Run: python tests/test_l35_gating.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.projection_l35 import project_funnel
from agent.schema import (
    BehavioralSignalDistribution,
    FunnelProjection,
    FunnelStageMeta,
    _validate_funnel_projection,
)
from agent.synthesis_types import L3Summary

_BASELINE = {"stop_rate": 0.10, "click_rate": 0.02, "visit_rate": 0.015,
             "convert_rate": 0.006}


def _l3() -> L3Summary:
    pop = BehavioralSignalDistribution(
        counts={"tap_cta": 6, "seek_info": 4, "scroll_past": 6, "linger": 4},
        would_act_within_week_count=5, n=20,
    )
    seg = BehavioralSignalDistribution(
        counts={"tap_cta": 3, "scroll_past": 2}, would_act_within_week_count=2, n=5,
    )
    return L3Summary(
        population_behavioral_distribution=pop,
        segment_behavioral_distributions={"disp_a::moderate": seg},
    )


def _meta(proj: FunnelProjection) -> dict[str, FunnelStageMeta]:
    return {m.stage_key: m for m in proj.stage_meta}


def test_default_gating_status() -> None:
    """No inputs (every current run): stop+visit grounded(modeled),
    click+convert scenario(direct_observable)."""
    proj = project_funnel(_l3(), _BASELINE)
    m = _meta(proj)
    assert [x.stage_key for x in proj.stage_meta] == ["stop", "click", "visit", "convert"]
    assert m["stop"].measurement_basis == "modeled" and m["stop"].status == "grounded"
    assert m["visit"].measurement_basis == "modeled" and m["visit"].status == "grounded"
    assert m["click"].measurement_basis == "direct_observable" and m["click"].status == "scenario"
    assert m["convert"].measurement_basis == "direct_observable" and m["convert"].status == "scenario"
    assert m["click"].required_inputs == ["ad_copy"]
    assert m["convert"].required_inputs == ["offer"]
    assert proj.provided_inputs == []
    print("  OK  default no-inputs: stop/visit grounded(modeled), click/convert scenario")


def test_grounded_when_inputs_provided() -> None:
    proj = project_funnel(_l3(), _BASELINE, provided_inputs=["ad_copy", "offer"])
    m = _meta(proj)
    assert m["click"].status == "grounded"
    assert m["convert"].status == "grounded"
    assert sorted(proj.provided_inputs) == ["ad_copy", "offer"]
    # Only copy → click grounded, convert still scenario.
    proj2 = project_funnel(_l3(), _BASELINE, provided_inputs=["ad_copy"])
    m2 = _meta(proj2)
    assert m2["click"].status == "grounded" and m2["convert"].status == "scenario"
    print("  OK  inputs ground their stages (ad_copy→click, offer→convert)")


def test_gating_is_display_only() -> None:
    """The numbers must be identical with vs without inputs — gating only sets
    status. Pins that providing copy/offer never silently moves the rates."""
    without = project_funnel(_l3(), _BASELINE)
    with_inputs = project_funnel(_l3(), _BASELINE, provided_inputs=["ad_copy", "offer"])
    for stage in ("stop", "click", "visit", "convert"):
        assert getattr(without.overall, f"{stage}_rate") == getattr(
            with_inputs.overall, f"{stage}_rate"
        ), f"{stage}_rate changed with inputs — gating must be display-only"
    assert [s.funnel_rates.convert_rate for s in without.by_segment] == [
        s.funnel_rates.convert_rate for s in with_inputs.by_segment
    ]
    print("  OK  gating is display-only: all rates identical with/without inputs")


def test_stop_always_grounded() -> None:
    proj = project_funnel(_l3(), _BASELINE, provided_inputs=[])
    assert _meta(proj)["stop"].status == "grounded"
    assert _meta(proj)["stop"].measurement_basis == "modeled"
    print("  OK  stop is always grounded+modeled (creative always present)")


def test_validation_accepts_and_rejects() -> None:
    proj = project_funnel(_l3(), _BASELINE)
    _validate_funnel_projection(proj)  # must not raise
    # Tamper: stop flipped to scenario must be rejected.
    proj.stage_meta[0].status = "scenario"
    try:
        _validate_funnel_projection(proj)
    except Exception as e:
        assert "stop stage must be modeled+grounded" in str(e)
        print("  OK  validator passes valid stage_meta, rejects stop=scenario")
        return
    raise AssertionError("validator should reject a scenario stop stage")


def test_stage_meta_roundtrip_and_legacy_default() -> None:
    proj = project_funnel(_l3(), _BASELINE, provided_inputs=["ad_copy"])
    rt = FunnelProjection.from_dict(proj.to_dict())
    assert [m.to_dict() for m in rt.stage_meta] == [m.to_dict() for m in proj.stage_meta]
    assert rt.provided_inputs == ["ad_copy"]
    # Legacy run.json with no stage_meta → empty list, no crash.
    legacy = proj.to_dict()
    del legacy["stage_meta"]
    del legacy["provided_inputs"]
    rt2 = FunnelProjection.from_dict(legacy)
    assert rt2.stage_meta == [] and rt2.provided_inputs == []
    _validate_funnel_projection(rt2)  # empty stage_meta skips the new invariants
    print("  OK  stage_meta round-trips; legacy run.json (no stage_meta) loads to []")


def main() -> None:
    print("=== funnel stage-gating + observable mapping ===")
    test_default_gating_status()
    test_grounded_when_inputs_provided()
    test_gating_is_display_only()
    test_stop_always_grounded()
    test_validation_accepts_and_rejects()
    test_stage_meta_roundtrip_and_legacy_default()
    print("PASS — stages map to observables and gate on their causal inputs.")


if __name__ == "__main__":
    main()
