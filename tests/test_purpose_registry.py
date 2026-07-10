"""Offline test: the v2.4 purpose registry (agent/purpose.py).

Pins the five-job taxonomy, the preset invariants each downstream layer relies
on (a resolvable headline_metric key, a frame, a provisional floor in range),
resolve_purpose's default + typo behaviour, and the direct-sell/registry
consistency the decision layer will lean on. No API calls.

Run: python tests/test_purpose_registry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.purpose import (
    AWARENESS_INFORMER,
    BRAND_BUILDING,
    COLD_HOOK,
    DEFAULT_PURPOSE,
    DIRECT_SELL,
    PURPOSE_ORDER,
    PURPOSE_REGISTRY,
    RETAIN_WINBACK,
    VALID_PURPOSES,
    resolve_purpose,
)

_VALID_FRAMES = {"narrow", "broad_cold", "broad", "existing"}
_VALID_METRICS = {
    "within_target_action",
    "cold_stop_lean_in",
    "reengagement",
    "resonance_brand_memory",
    "breadth_registration",
}


def test_five_jobs_present_and_ordered() -> None:
    assert set(PURPOSE_REGISTRY) == {
        DIRECT_SELL, COLD_HOOK, AWARENESS_INFORMER, BRAND_BUILDING, RETAIN_WINBACK,
    }
    assert set(PURPOSE_ORDER) == set(PURPOSE_REGISTRY)
    assert PURPOSE_ORDER[0] == DIRECT_SELL          # default is first
    assert VALID_PURPOSES == frozenset(PURPOSE_REGISTRY)
    assert DEFAULT_PURPOSE == DIRECT_SELL
    print("  OK  five jobs present; direct-sell is the default + first")


def test_preset_invariants() -> None:
    for name, p in PURPOSE_REGISTRY.items():
        assert p.name == name, f"{name}: name mismatch"
        assert p.label, f"{name}: needs a human label"
        assert p.headline_metric in _VALID_METRICS, f"{name}: bad metric key"
        assert p.metric_label, f"{name}: needs a render label"
        assert p.audience_frame in _VALID_FRAMES, f"{name}: bad frame"
        assert 0.0 <= p.provisional_scale_floor <= 1.0, f"{name}: floor out of range"
        # scored_probes only ever names the two v2.4 probes.
        assert set(p.scored_probes) <= {"novelty", "brand_attribution"}
    # each headline metric is used by exactly one purpose (no ambiguous dispatch)
    metrics = [p.headline_metric for p in PURPOSE_REGISTRY.values()]
    assert len(metrics) == len(set(metrics)), "headline metrics must be unique"
    print("  OK  every preset has a valid metric/frame/floor; metrics unique")


def test_probe_wiring_matches_design() -> None:
    # informer scores novelty; brand-building scores brand-attribution; the
    # three purchase-shaped jobs score neither (they read behavioural signals).
    assert resolve_purpose(AWARENESS_INFORMER).scored_probes == ("novelty",)
    assert resolve_purpose(BRAND_BUILDING).scored_probes == ("brand_attribution",)
    for name in (DIRECT_SELL, COLD_HOOK, RETAIN_WINBACK):
        assert resolve_purpose(name).scored_probes == ()
    # the two broad-frame jobs are the multi-target (breadth) ones.
    assert resolve_purpose(AWARENESS_INFORMER).multi_target is True
    assert resolve_purpose(BRAND_BUILDING).multi_target is True
    assert resolve_purpose(DIRECT_SELL).multi_target is False
    # retain is flagged inert-until-library-has-existing-customers.
    assert resolve_purpose(RETAIN_WINBACK).requires_existing_customers is True
    print("  OK  probe wiring + multi-target + retain-inert flags match design")


def test_resolve_default_and_typo() -> None:
    assert resolve_purpose(None).name == DIRECT_SELL
    assert resolve_purpose("").name == DIRECT_SELL
    assert resolve_purpose("cold_hook").name == COLD_HOOK
    try:
        resolve_purpose("brand_awareness")  # not a valid job name
        raise AssertionError("unknown purpose should raise")
    except ValueError as e:
        assert "unknown purpose" in str(e)
    print("  OK  resolve_purpose: None/'' → direct-sell; typo raises")


def test_direct_sell_floor_matches_decision() -> None:
    # direct-sell's registry floor MUST equal the v2.3 SCALE floor until P3
    # unifies the source of truth (decision.py reads the registry after that).
    from agent.decision import _SCALE_FLOOR
    assert resolve_purpose(DIRECT_SELL).provisional_scale_floor == _SCALE_FLOOR
    print("  OK  direct-sell floor == decision._SCALE_FLOOR (single source, pre-P3)")


def main() -> None:
    print("=== purpose registry (v2.4) ===")
    test_five_jobs_present_and_ordered()
    test_preset_invariants()
    test_probe_wiring_matches_design()
    test_resolve_default_and_typo()
    test_direct_sell_floor_matches_decision()
    print("PASS — purpose registry is well-formed and design-consistent.")


if __name__ == "__main__":
    main()
