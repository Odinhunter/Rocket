"""Phase 3 offline tests (rocket-2.1.0): the demographic-overlap primitives,
the range-based mismatch guard (declared range vs inferred band), and the
thin-coverage guard.

Run: python tests/test_marketer_led_guards.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.entities import AudienceSpec
from agent.panel import demographic_overlap
from agent.synthesis_types import CoverageWarning, InferredAudience
from agent.target_id import (
    detect_gross_demographic_mismatch,
    detect_thin_coverage,
)
from agent.vectors import (
    ChaosDistribution,
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicBundle,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)


def _dp(gender, a0, a1, i0, i1, geo="metro"):
    return DemographicPoint(
        gender=gender, age_min=a0, age_max=a1,
        income_lpa_min=float(i0), income_lpa_max=float(i1), geography=geo,
    )


def _dv():
    return DispositionVector(
        category_relationship="regular", brand_stance="neutral",
        price_orientation="value_calculator", decision_driver="function",
        category_involvement="high", prior_experience_valence="mixed",
        channel_behavior="quick_commerce", life_stage="early_career",
    )


def _disp(label, bundles=None):
    return NamedDisposition(label=label, vector=_dv(), demographic_bundles=bundles or [])


def _bundle(gender, a0, a1, i0, i1, w):
    return DemographicBundle(point=_dp(gender, a0, a1, i0, i1), weight=w)


def _ctx(n=3):
    return [
        NamedContext(
            label=f"c{i}",
            vector=ContextVector(
                attention_level="low", device_posture="commute",
                intent_state="killing_time", energy_state="drained",
                social_setting="public",
            ),
        )
        for i in range(n)
    ]


def _chaos():
    return ChaosDistribution(weighted=[(
        ChaosProfile(label="moderate", vector=ChaosVector(
            decision_velocity="moderate", suggestibility="medium",
            consistency="variable", risk_tolerance="balanced",
        )), 1.0,
    )])


def _spec(declared, dispositions, n=30):
    return AudienceSpec(
        demographics=declared,
        disposition_labels=[d.label for d in dispositions],
        context_envelope=_ctx(),
        chaos_distribution=_chaos(),
        panel_size=n,
    )


# ---- demographic_overlap primitive ----

def test_overlap_disjoint_partial_full() -> None:
    declared = _dp("female", 20, 24, 0, 14)
    # disjoint age
    assert demographic_overlap(_dp("female", 30, 40, 0, 14), declared) == 0.0
    # incompatible gender gates to 0 even with full age/income overlap
    assert demographic_overlap(_dp("male", 20, 24, 0, 14), declared) == 0.0
    # full containment -> 1.0
    assert demographic_overlap(_dp("female", 20, 24, 0, 14), declared) == 1.0
    # partial age overlap: persona 18-24 vs declared 20-24 -> 4/6 on age
    ov = demographic_overlap(_dp("female", 18, 24, 0, 14), declared)
    assert abs(ov - (4 / 6)) < 1e-9, ov
    # gender wildcard on either side is compatible
    assert demographic_overlap(_dp("any", 20, 24, 0, 14), declared) == 1.0
    print("  OK  demographic_overlap: disjoint/partial/full + gender gate + wildcard")


# ---- mismatch guard: declared range vs inferred band ----

def test_mismatch_age_gross() -> None:
    declared = [_dp("female", 20, 24, 0, 14)]
    m = detect_gross_demographic_mismatch(declared, InferredAudience(gender="female", age_band="45_54"))
    assert m is not None and "age" in m.axes, m
    assert "45-54" in m.message and "20-24" in m.message, m.message
    print("  OK  mismatch fires on gross age gap (declared 20-24 vs ad 45-54)")


def test_mismatch_age_aligned_no_fire() -> None:
    declared = [_dp("female", 20, 24, 0, 14)]
    # 18_24 overlaps 20-24 -> no fire; 25_34 is only 1yr off -> no fire.
    assert detect_gross_demographic_mismatch(declared, InferredAudience(gender="female", age_band="18_24")) is None
    assert detect_gross_demographic_mismatch(declared, InferredAudience(gender="female", age_band="25_34")) is None
    # unclear/mixed never fire
    assert detect_gross_demographic_mismatch(declared, InferredAudience(gender="unclear", age_band="unclear")) is None
    print("  OK  mismatch does not fire on aligned/near/unclear age")


def test_mismatch_gender() -> None:
    declared = [_dp("female", 25, 34, 0, 14)]
    m = detect_gross_demographic_mismatch(declared, InferredAudience(gender="male", age_band="25_34"))
    assert m is not None and "gender" in m.axes, m
    # a wildcard declared frame absorbs the gender mismatch
    mixed = [_dp("any", 25, 34, 0, 14)]
    assert detect_gross_demographic_mismatch(mixed, InferredAudience(gender="male", age_band="25_34")) is None
    print("  OK  mismatch fires on opposite gender; wildcard declared absorbs it")


# ---- coverage guard ----

def test_coverage_thin_and_healthy() -> None:
    declared = [_dp("female", 20, 24, 0, 14)]
    ins = _disp("ins", [_bundle("female", 20, 24, 0, 14, 100)])
    out = _disp("out", [_bundle("male", 45, 54, 17, 40, 100)])
    # only 1 eligible -> warning
    w = detect_thin_coverage(_spec(declared, [ins, out]), [ins, out])
    assert w is not None and w.eligible_count == 1 and w.eligible_labels == ["ins"], w
    # 2 eligible -> None
    ins2 = _disp("ins2", [_bundle("female", 20, 24, 0, 14, 100)])
    assert detect_thin_coverage(_spec(declared, [ins, ins2]), [ins, ins2]) is None
    # 0 eligible -> warning (degenerate)
    w0 = detect_thin_coverage(_spec(declared, [out]), [out])
    assert w0 is not None and w0.eligible_count == 0, w0
    assert "No library persona" in w0.message, w0.message
    print("  OK  coverage guard: 0/1 eligible -> warn, >=2 -> None")


def test_coverage_warning_roundtrip() -> None:
    w = CoverageWarning(eligible_count=1, total_count=6, eligible_labels=["a"], message="m")
    assert CoverageWarning.from_dict(w.to_dict()) == w
    print("  OK  CoverageWarning round-trips")


def main() -> None:
    print("=== marketer-led guards (rocket-2.1.0) ===")
    test_overlap_disjoint_partial_full()
    test_mismatch_age_gross()
    test_mismatch_age_aligned_no_fire()
    test_mismatch_gender()
    test_coverage_thin_and_healthy()
    test_coverage_warning_roundtrip()
    print("PASS — range-based guards hold.")


if __name__ == "__main__":
    main()
