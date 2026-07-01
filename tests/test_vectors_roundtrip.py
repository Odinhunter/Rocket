"""Phase 0 offline test: the four population-axis vector dataclasses
round-trip through to_dict / from_dict and validate() catches bad values.

Run: python tests/test_vectors_roundtrip.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.vectors import (
    _BAND_TO_AGE_RANGE,
    _TIER_TO_LPA_RANGE,
    ChaosDistribution,
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)


def _demo() -> DemographicPoint:
    return DemographicPoint(
        gender="male",
        age_band="25_34",
        income_tier="upper_mid",
        geography="Bangalore / metro tier-1",
        occupation_hint="software engineer at a mid-stage SaaS startup",
        household_hint="shares a 3BHK with two flatmates",
    )


def _disposition_vector() -> DispositionVector:
    return DispositionVector(
        category_relationship="regular",
        brand_stance="skeptical",
        price_orientation="value_calculator",
        decision_driver="function",
        category_involvement="high",
        prior_experience_valence="mixed",
        channel_behavior="quick_commerce",
        life_stage="early_career",
    )


def _context_vector() -> ContextVector:
    return ContextVector(
        attention_level="low",
        device_posture="commute",
        intent_state="killing_time",
        energy_state="drained",
        social_setting="public",
    )


def _chaos_distribution() -> ChaosDistribution:
    impulsive = ChaosProfile(
        label="impulsive",
        vector=ChaosVector(
            decision_velocity="impulsive",
            suggestibility="high",
            consistency="erratic",
            risk_tolerance="seeking",
        ),
    )
    moderate = ChaosProfile(
        label="moderate",
        vector=ChaosVector(
            decision_velocity="moderate",
            suggestibility="medium",
            consistency="variable",
            risk_tolerance="balanced",
        ),
    )
    deliberate = ChaosProfile(
        label="deliberate",
        vector=ChaosVector(
            decision_velocity="deliberate",
            suggestibility="low",
            consistency="steady",
            risk_tolerance="averse",
        ),
    )
    return ChaosDistribution(
        weighted=[(impulsive, 0.20), (moderate, 0.55), (deliberate, 0.25)]
    )


def test_demographic_roundtrip() -> None:
    d = _demo()
    d.validate()
    d2 = DemographicPoint.from_dict(d.to_dict())
    assert d == d2, "DemographicPoint round-trip mismatch"
    print("  OK  DemographicPoint round-trip")


def test_demographic_range_native() -> None:
    """rocket-2.1.0: age/income authored as continuous ranges."""
    d = DemographicPoint(
        gender="female",
        age_min=20, age_max=24,
        income_lpa_min=0.0, income_lpa_max=14.0,
        geography="tier-1 metro",
    )
    d.validate()
    dd = d.to_dict()
    assert "age_band" not in dd and "income_tier" not in dd, dd
    assert DemographicPoint.from_dict(dd) == d, "range-native round-trip mismatch"
    print("  OK  range-native DemographicPoint round-trip")


def test_demographic_legacy_dual_read() -> None:
    """Legacy band/tier JSON dual-reads into ranges and re-round-trips; the
    legacy kwarg constructor path converts identically."""
    legacy = {
        "gender": "male", "age_band": "55_plus", "income_tier": "affluent",
        "geography": "metro",
    }
    d = DemographicPoint.from_dict(legacy)
    assert (d.age_min, d.age_max) == (55, 75), d.to_dict()
    assert (d.income_lpa_min, d.income_lpa_max) == (17.0, 40.0), d.to_dict()
    dd = d.to_dict()
    assert "age_band" not in dd and "income_tier" not in dd, dd
    assert DemographicPoint.from_dict(dd) == d, "legacy -> range not stable"
    assert DemographicPoint(
        gender="male", age_band="55_plus", income_tier="affluent",
        geography="metro",
    ) == d, "legacy kwarg constructor diverged from legacy JSON"
    print("  OK  legacy band/tier dual-read -> ranges")


def test_demographic_conversion_maps() -> None:
    assert _BAND_TO_AGE_RANGE["18_24"] == (18, 24)
    assert _BAND_TO_AGE_RANGE["55_plus"][0] == 55
    assert _TIER_TO_LPA_RANGE["mass"] == (0.0, 3.5)
    assert _TIER_TO_LPA_RANGE["upper_mid"] == (7.0, 17.0)
    print("  OK  legacy band/tier -> range conversion maps")


def test_demographic_validate_rejects_bad_range() -> None:
    bad_age = DemographicPoint(
        gender="any", age_min=30, age_max=20,
        income_lpa_min=0.0, income_lpa_max=5.0, geography="x",
    )
    try:
        bad_age.validate()
    except ValueError as e:
        assert "age range" in str(e)
    else:
        raise AssertionError("validate should reject age_min > age_max")
    bad_income = DemographicPoint(
        gender="any", age_min=20, age_max=30,
        income_lpa_min=10.0, income_lpa_max=2.0, geography="x",
    )
    try:
        bad_income.validate()
    except ValueError as e:
        assert "income range" in str(e)
    else:
        raise AssertionError("validate should reject income min > max")
    print("  OK  validate rejects inverted age/income ranges")


def test_disposition_vector_roundtrip() -> None:
    v = _disposition_vector()
    v.validate()
    v2 = DispositionVector.from_dict(v.to_dict())
    assert v == v2, "DispositionVector round-trip mismatch"
    nd = NamedDisposition(
        label="value_calculating_skeptic", vector=v, provisional=True,
        notes="curator note, never an artifact",
        anchor="traditional filter coffee — steel filter, Cothas chicory blend",
    )
    nd.validate()
    nd2 = NamedDisposition.from_dict(nd.to_dict())
    assert nd == nd2, "NamedDisposition round-trip mismatch"
    assert nd2.provisional is True
    assert nd2.anchor == nd.anchor, "NamedDisposition.anchor did not round-trip"
    # anchor defaults to empty and still round-trips.
    nd_bare = NamedDisposition(label="bare", vector=v)
    assert NamedDisposition.from_dict(nd_bare.to_dict()) == nd_bare
    print("  OK  DispositionVector + NamedDisposition round-trip (incl. anchor)")


def test_context_vector_roundtrip() -> None:
    v = _context_vector()
    v.validate()
    v2 = ContextVector.from_dict(v.to_dict())
    assert v == v2, "ContextVector round-trip mismatch"
    nc = NamedContext(label="commute_scroll", vector=v)
    nc.validate()
    nc2 = NamedContext.from_dict(nc.to_dict())
    assert nc == nc2, "NamedContext round-trip mismatch"
    print("  OK  ContextVector + NamedContext round-trip")


def test_chaos_distribution_roundtrip() -> None:
    cd = _chaos_distribution()
    cd.validate()
    cd2 = ChaosDistribution.from_dict(cd.to_dict())
    assert cd == cd2, "ChaosDistribution round-trip mismatch"
    assert cd2.profile_for("impulsive").vector.decision_velocity == "impulsive"
    print("  OK  ChaosDistribution round-trip")


def test_chaos_distribution_rejects_bad_weights() -> None:
    cd = _chaos_distribution()
    # Tamper: weights now sum to 0.9, not 1.0.
    cd.weighted[0] = (cd.weighted[0][0], 0.10)
    try:
        cd.validate()
    except ValueError as e:
        assert "sum to 1.0" in str(e)
        print("  OK  ChaosDistribution rejects weights that don't sum to 1.0:", e)
        return
    raise AssertionError("ChaosDistribution.validate should reject bad weight sum")


def test_vector_validate_rejects_bad_enum() -> None:
    v = _disposition_vector()
    v.brand_stance = "ferocious"  # type: ignore[assignment]
    try:
        v.validate()
    except ValueError as e:
        assert "brand_stance" in str(e)
        print("  OK  DispositionVector.validate rejects bad enum value:", e)
        return
    raise AssertionError("DispositionVector.validate should reject bad enum")


def test_escape_hatch_value_accepted() -> None:
    """Every vector enum carries 'unspecified' so Phase 1 curation can't be
    blocked by a missing value."""
    v = ContextVector(
        attention_level="unspecified",
        device_posture="unspecified",
        intent_state="unspecified",
        energy_state="unspecified",
        social_setting="unspecified",
    )
    v.validate()
    print("  OK  'unspecified' escape hatch accepted on every context dim")


def main() -> None:
    print("=== vectors round-trip smoke ===")
    test_demographic_roundtrip()
    test_demographic_range_native()
    test_demographic_legacy_dual_read()
    test_demographic_conversion_maps()
    test_demographic_validate_rejects_bad_range()
    test_disposition_vector_roundtrip()
    test_context_vector_roundtrip()
    test_chaos_distribution_roundtrip()
    test_chaos_distribution_rejects_bad_weights()
    test_vector_validate_rejects_bad_enum()
    test_escape_hatch_value_accepted()
    print("PASS — population-axis vectors are locked.")


if __name__ == "__main__":
    main()
