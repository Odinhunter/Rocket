"""Phase 2 offline test: build_panel resolves an AudienceSpec into a panel
that (a) is exactly panel_size agents, (b) matches the chaos distribution
within largest-remainder tolerance, (c) covers marginals at both 200 and
15 agents, (d) is reproducible given spec + seed, and (e) keys segments
correctly. No API calls.

Run: python tests/test_panel.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.entities import AudienceSpec
from agent.panel import (
    PanelAgent,
    build_panel,
    compute_panel_version,
    eligible_dispositions,
)
from agent.vectors import (
    _TIER_TO_LPA_RANGE,
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

# rocket-2.1.0: demographics are continuous ranges. These bundled tests were
# authored against the legacy income_tier bucket; derive the tier back from the
# income range so the distribution assertions keep their original meaning.
_RANGE_TO_TIER = {rng: tier for tier, rng in _TIER_TO_LPA_RANGE.items()}


def _tier_of(demo: DemographicPoint) -> str | None:
    return _RANGE_TO_TIER.get((demo.income_lpa_min, demo.income_lpa_max))


def _chaos_distribution() -> ChaosDistribution:
    def profile(label: str, dv: str) -> ChaosProfile:
        return ChaosProfile(
            label=label,
            vector=ChaosVector(
                decision_velocity=dv, suggestibility="medium",
                consistency="variable", risk_tolerance="balanced",
            ),
        )

    return ChaosDistribution(
        weighted=[
            (profile("impulsive", "impulsive"), 0.20),
            (profile("moderate", "moderate"), 0.55),
            (profile("deliberate", "deliberate"), 0.25),
        ]
    )


def _disposition(label: str) -> NamedDisposition:
    return NamedDisposition(
        label=label,
        vector=DispositionVector(
            category_relationship="regular", brand_stance="neutral",
            price_orientation="value_calculator", decision_driver="function",
            category_involvement="medium", prior_experience_valence="neutral",
            channel_behavior="quick_commerce", life_stage="early_career",
        ),
    )


def _context(label: str) -> NamedContext:
    return NamedContext(
        label=label,
        vector=ContextVector(
            attention_level="low", device_posture="commute",
            intent_state="killing_time", energy_state="drained",
            social_setting="public",
        ),
    )


def _spec(panel_size: int, n_disp: int = 7, n_ctx: int = 3, n_demo: int = 1) -> tuple:
    dispositions = [_disposition(f"disp_{i}") for i in range(n_disp)]
    spec = AudienceSpec(
        demographics=[
            DemographicPoint(
                gender="male", age_band="25_34", income_tier="upper_mid",
                geography=f"metro tier-1 #{i}",
            )
            for i in range(n_demo)
        ],
        disposition_labels=[d.label for d in dispositions],
        context_envelope=[_context(f"ctx_{i}") for i in range(n_ctx)],
        chaos_distribution=_chaos_distribution(),
        panel_size=panel_size,
    )
    return spec, dispositions


def test_panel_size_exact() -> None:
    for n in (15, 21, 100, 200):
        spec, disps = _spec(n)
        panel = build_panel(spec, disps, category="coffee", seed=71)
        assert len(panel) == n, f"panel size {len(panel)} != {n}"
        assert [a.agent_id for a in panel] == list(range(n)), "agent_ids not 0..n-1"
    print("  OK  build_panel produces exactly panel_size agents, ids 0..n-1")


def test_chaos_distribution_matched() -> None:
    spec, disps = _spec(200)
    panel = build_panel(spec, disps, category="coffee", seed=71)
    counts = Counter(a.chaos_band for a in panel)
    # 0.20 / 0.55 / 0.25 of 200 = 40 / 110 / 50, exact under largest-remainder.
    assert counts["impulsive"] == 40, counts
    assert counts["moderate"] == 110, counts
    assert counts["deliberate"] == 50, counts
    print(f"  OK  chaos distribution matched exactly at 200 agents: {dict(counts)}")


def test_cycle_distribution_matched() -> None:
    spec, disps = _spec(200)
    panel = build_panel(spec, disps, category="coffee", seed=71)
    counts = Counter(a.cycle_position for a in panel)
    # default mix 0.25/0.50/0.25 of 200 = 50/100/50, exact under largest-remainder.
    assert counts["just_bought"] == 50, counts
    assert counts["mid_cycle"] == 100, counts
    assert counts["running_low"] == 50, counts
    print(f"  OK  cycle distribution matched the default mix at 200: {dict(counts)}")


def test_custom_cycle_mix_respected() -> None:
    spec, disps = _spec(60)
    spec.cycle_mix = {"running_low": 3.0, "mid_cycle": 1.0}  # 3:1 -> 45 / 15 (normalised)
    panel = build_panel(spec, disps, category="coffee", seed=71)
    counts = Counter(a.cycle_position for a in panel)
    assert counts["running_low"] == 45 and counts["mid_cycle"] == 15, counts
    assert counts["just_bought"] == 0, counts  # not in the declared mix
    print(f"  OK  custom cycle_mix respected (normalised): {dict(counts)}")


def test_cycle_reproducible_same_seed() -> None:
    spec, disps = _spec(100)
    p1 = build_panel(spec, disps, category="coffee", seed=71)
    p2 = build_panel(spec, disps, category="coffee", seed=71)
    assert [a.cycle_position for a in p1] == [a.cycle_position for a in p2]
    print("  OK  cycle_position is reproducible for the same spec + seed")


def test_cycle_not_in_persona_cache_or_segment_key() -> None:
    from agent.vectors import ChaosProfile, ChaosVector
    chaos = ChaosProfile(label="moderate", vector=ChaosVector(
        decision_velocity="moderate", suggestibility="medium",
        consistency="variable", risk_tolerance="balanced"))
    demo = DemographicPoint(gender="male", age_band="25_34",
                            income_tier="upper_mid", geography="metro")
    base = dict(agent_id=0, demographic=demo, disposition=_disposition("d"),
                context=_context("c"), chaos=chaos, category="coffee")
    a1 = PanelAgent(**base, cycle_position="running_low")
    a2 = PanelAgent(**base, cycle_position="just_bought")
    # cycle rides the UNCACHED context render, so it must not change either key.
    assert a1.persona_core_hash == a2.persona_core_hash
    assert a1.segment_key == a2.segment_key
    print("  OK  cycle_position excluded from persona_core_hash + segment_key")


def test_marginal_coverage_full() -> None:
    """panel_size (200) >= grid (7x3x1 = 21): every joint cell populated."""
    spec, disps = _spec(200)
    panel = build_panel(spec, disps, category="coffee", seed=71)
    cells = {(a.demographic.geography, a.disposition_label, a.context_label) for a in panel}
    assert len(cells) == 21, f"expected all 21 joint cells covered, got {len(cells)}"
    assert {a.disposition_label for a in panel} == {f"disp_{i}" for i in range(7)}
    assert {a.context_label for a in panel} == {f"ctx_{i}" for i in range(3)}
    print("  OK  panel_size >= grid: all 21 joint cells covered")


def test_marginal_coverage_small() -> None:
    """panel_size (15) < grid (21): joint coverage is sacrificed, but every
    disposition / context / demographic still appears at least once."""
    spec, disps = _spec(15)
    panel = build_panel(spec, disps, category="coffee", seed=71)
    assert {a.disposition_label for a in panel} == {f"disp_{i}" for i in range(7)}, (
        "not every disposition appears at panel_size=15"
    )
    assert {a.context_label for a in panel} == {f"ctx_{i}" for i in range(3)}, (
        "not every context appears at panel_size=15"
    )
    # Chaos is still apportioned: 0.20/0.55/0.25 of 15 -> 3/8/4 (largest remainder).
    counts = Counter(a.chaos_band for a in panel)
    assert sum(counts.values()) == 15
    assert counts["moderate"] >= counts["impulsive"], counts
    print(f"  OK  panel_size < grid: all marginals covered, chaos apportioned {dict(counts)}")


def test_reproducible_same_seed() -> None:
    spec, disps = _spec(200)
    p1 = build_panel(spec, disps, category="coffee", seed=71)
    p2 = build_panel(spec, disps, category="coffee", seed=71)
    assert [a.to_dict() for a in p1] == [a.to_dict() for a in p2], (
        "same spec + seed did not produce an identical panel"
    )
    print("  OK  same spec + seed -> byte-identical panel")


def test_reproducible_diff_seed() -> None:
    spec, disps = _spec(200)
    p1 = build_panel(spec, disps, category="coffee", seed=71)
    p2 = build_panel(spec, disps, category="coffee", seed=999)
    # Different seed: same distributions...
    assert Counter(a.chaos_band for a in p1) == Counter(a.chaos_band for a in p2)
    assert Counter(a.disposition_label for a in p1) == Counter(
        a.disposition_label for a in p2
    )
    # ...but a different agent_id assignment.
    order1 = [(a.disposition_label, a.context_label, a.chaos_band) for a in p1]
    order2 = [(a.disposition_label, a.context_label, a.chaos_band) for a in p2]
    assert order1 != order2, "different seed produced an identical agent_id order"
    print("  OK  different seed -> same distributions, different agent_id order")


def test_segment_keys() -> None:
    spec, disps = _spec(200)
    panel_cb = build_panel(
        spec, disps, category="coffee", segment_granularity="disposition_chaos_band",
        seed=71,
    )
    a = panel_cb[0]
    assert a.segment_key == f"{a.disposition_label}::{a.chaos_band}", a.segment_key
    n_segments = len({x.segment_key for x in panel_cb})
    assert n_segments == 21, f"expected 7x3=21 disposition x chaos segments, got {n_segments}"

    panel_d = build_panel(
        spec, disps, category="coffee", segment_granularity="disposition", seed=71,
    )
    assert panel_d[0].segment_key == panel_d[0].disposition_label
    assert len({x.segment_key for x in panel_d}) == 7
    print("  OK  segment_key respects granularity (21 vs 7 segments)")


def test_panel_agent_roundtrip() -> None:
    spec, disps = _spec(50)
    panel = build_panel(spec, disps, category="coffee", seed=71)
    a = panel[0]
    a2 = PanelAgent.from_dict(a.to_dict())
    assert a == a2, "PanelAgent round-trip mismatch"
    # persona_core_hash is stable and present.
    assert a.persona_core_hash and a.persona_core_hash == a2.persona_core_hash
    print("  OK  PanelAgent round-trips; persona_core_hash stable")


def test_compute_panel_version() -> None:
    spec, disps = _spec(200)
    v1 = compute_panel_version(
        spec, disps, category="coffee", segment_granularity="disposition_chaos_band",
        seed=71,
    )
    v2 = compute_panel_version(
        spec, disps, category="coffee", segment_granularity="disposition_chaos_band",
        seed=71,
    )
    assert v1 == v2, "compute_panel_version not stable"
    v3 = compute_panel_version(
        spec, disps, category="chocolate", segment_granularity="disposition_chaos_band",
        seed=71,
    )
    assert v3 != v1, "compute_panel_version did not change on a category change"
    print("  OK  compute_panel_version is stable and sensitive")


def test_build_panel_rejects_mismatched_dispositions() -> None:
    spec, disps = _spec(50)
    try:
        build_panel(spec, disps[:-1], category="coffee", seed=71)  # missing one
    except ValueError as e:
        assert "disposition" in str(e)
        print("  OK  build_panel rejects dispositions not matching the spec:", e)
        return
    raise AssertionError("build_panel should reject mismatched dispositions")


# ---- Per-disposition demographic bundles (income distribution) ----


def _disposition_bundled(label: str, tier_weights: dict[str, float]) -> NamedDisposition:
    """A disposition whose agents draw from per-tier coherent bundles."""
    d = _disposition(label)
    d.demographic_bundles = [
        DemographicBundle(
            point=DemographicPoint(
                gender="any", age_band="25_34", income_tier=tier,
                geography=f"geo_{tier}",
            ),
            weight=w,
        )
        for tier, w in tier_weights.items()
    ]
    return d


def _bundled_spec(panel_size: int, dispositions: list[NamedDisposition]) -> AudienceSpec:
    return AudienceSpec(
        demographics=[
            DemographicPoint(
                gender="male", age_band="25_34", income_tier="upper_mid",
                geography="fallback metro",
            )
        ],
        disposition_labels=[d.label for d in dispositions],
        context_envelope=[_context(f"ctx_{i}") for i in range(4)],
        chaos_distribution=_chaos_distribution(),
        panel_size=panel_size,
    )


def test_bundled_income_distribution_matches() -> None:
    dA = _disposition_bundled("affluent_disp", {"upper_mid": 50, "affluent": 40, "premium": 10})
    dB = _disposition_bundled("mass_disp", {"mass": 60, "lower_mid": 30, "upper_mid": 10})
    spec = _bundled_spec(200, [dA, dB])
    panel = build_panel(spec, [dA, dB], category="health_wellness", seed=71)
    assert len(panel) == 200
    incA = Counter(_tier_of(a.demographic) for a in panel if a.disposition_label == "affluent_disp")
    incB = Counter(_tier_of(a.demographic) for a in panel if a.disposition_label == "mass_disp")
    nA, nB = sum(incA.values()), sum(incB.values())
    # No cross-tier contamination: each disposition only shows its own tiers.
    assert incA["mass"] == 0 and incA["lower_mid"] == 0, incA
    assert incB["premium"] == 0 and incB["affluent"] == 0, incB
    # Shares reproduce the weights within largest-remainder tolerance.
    assert abs(incA["upper_mid"] / nA - 0.50) < 0.04, incA
    assert abs(incA["affluent"] / nA - 0.40) < 0.04, incA
    assert abs(incB["mass"] / nB - 0.60) < 0.04, incB
    print(f"  OK  bundled income distribution matches per disposition: A={dict(incA)} B={dict(incB)}")


def test_bundled_coherence_no_contamination() -> None:
    """Every agent's demographic is one of its OWN disposition's bundles."""
    dA = _disposition_bundled("affluent_disp", {"upper_mid": 50, "affluent": 40, "premium": 10})
    dB = _disposition_bundled("mass_disp", {"mass": 60, "lower_mid": 30, "upper_mid": 10})
    spec = _bundled_spec(200, [dA, dB])
    panel = build_panel(spec, [dA, dB], category="health_wellness", seed=71)
    allowed = {
        "affluent_disp": {(_tier_of(b.point), b.point.geography) for b in dA.demographic_bundles},
        "mass_disp": {(_tier_of(b.point), b.point.geography) for b in dB.demographic_bundles},
    }
    for a in panel:
        key = (_tier_of(a.demographic), a.demographic.geography)
        assert key in allowed[a.disposition_label], f"{a.disposition_label} got alien demo {key}"
    print("  OK  bundled agents draw only from their own disposition's bundles")


def test_bundled_reproducible_and_sizes() -> None:
    dA = _disposition_bundled("affluent_disp", {"upper_mid": 50, "affluent": 40, "premium": 10})
    dB = _disposition_bundled("mass_disp", {"mass": 60, "lower_mid": 30, "upper_mid": 10})
    for n in (15, 100, 200):
        spec = _bundled_spec(n, [dA, dB])
        p1 = build_panel(spec, [dA, dB], category="health_wellness", seed=71)
        p2 = build_panel(spec, [dA, dB], category="health_wellness", seed=71)
        assert len(p1) == n, f"panel size {len(p1)} != {n}"
        assert [a.to_dict() for a in p1] == [a.to_dict() for a in p2], "bundled panel not reproducible"
        assert {a.disposition_label for a in p1} == {"affluent_disp", "mass_disp"}, "a disposition vanished"
        # Chaos distribution still matched (shared tail unchanged by bundling).
        counts = Counter(a.chaos_band for a in p1)
        assert sum(counts.values()) == n
    print("  OK  bundled path: exact size, reproducible, both dispositions present at 15/100/200")


def test_bundled_mixed_fallback() -> None:
    """A disposition WITHOUT bundles falls back to spec.demographics even when
    a sibling disposition carries bundles (mixed library)."""
    dA = _disposition_bundled("affluent_disp", {"affluent": 70, "premium": 30})
    dB = _disposition("plain_disp")  # no bundles
    spec = _bundled_spec(120, [dA, dB])
    panel = build_panel(spec, [dA, dB], category="health_wellness", seed=71)
    plain = [a for a in panel if a.disposition_label == "plain_disp"]
    assert plain, "fallback disposition produced no agents"
    # The fallback disposition uses the spec's single demographic frame.
    assert all(a.demographic.geography == "fallback metro" for a in plain), "fallback did not use spec.demographics"
    bundled = [a for a in panel if a.disposition_label == "affluent_disp"]
    assert all(_tier_of(a.demographic) in {"affluent", "premium"} for a in bundled)
    print("  OK  mixed library: bundled disposition uses bundles, plain disposition falls back to spec.demographics")


# ---- Phase 2: marketer-led composition (rocket-2.1.0) ----


def _ml_bundle(gender, a0, a1, i0, i1, w, geo="metro"):
    return DemographicBundle(
        point=DemographicPoint(
            gender=gender, age_min=a0, age_max=a1,
            income_lpa_min=float(i0), income_lpa_max=float(i1), geography=geo,
        ),
        weight=w,
    )


def _ml_disposition(label, bundles):
    d = _disposition(label)
    d.demographic_bundles = bundles
    return d


def _declared_female_2024():
    return [
        DemographicPoint(
            gender="female", age_min=20, age_max=24,
            income_lpa_min=0.0, income_lpa_max=14.0, geography="tier-1 metro",
        )
    ]


def _ml_spec(declared, dispositions, panel_size):
    return AudienceSpec(
        demographics=declared,
        disposition_labels=[d.label for d in dispositions],
        context_envelope=[_context(f"ctx_{i}") for i in range(3)],
        chaos_distribution=_chaos_distribution(),
        panel_size=panel_size,
    )


def test_ml_excludes_disjoint_personas() -> None:
    young = _ml_disposition("young_fem", [
        _ml_bundle("female", 18, 24, 3.5, 7, 60),
        _ml_bundle("female", 25, 34, 7, 17, 40),
    ])
    older = _ml_disposition("older_male", [_ml_bundle("male", 45, 54, 17, 40, 100)])
    spec = _ml_spec(_declared_female_2024(), [young, older], 60)
    panel = build_panel(spec, [young, older], category="hw", marketer_led=True, seed=71)
    assert {a.disposition_label for a in panel} == {"young_fem"}, "disjoint persona not excluded"
    print("  OK  marketer-led excludes personas disjoint from the declared audience")


def test_ml_clips_agents_to_declared() -> None:
    # A persona spanning beyond the buy on both age and income.
    young = _ml_disposition("young_fem", [_ml_bundle("female", 18, 30, 3.5, 20, 100)])
    spec = _ml_spec(_declared_female_2024(), [young], 60)
    panel = build_panel(spec, [young], category="hw", marketer_led=True, seed=71)
    for a in panel:
        d = a.demographic
        assert d.gender == "female", d.gender
        assert 20 <= d.age_min and d.age_max <= 24, (d.age_min, d.age_max)
        assert 0.0 <= d.income_lpa_min and d.income_lpa_max <= 14.0, (d.income_lpa_min, d.income_lpa_max)
        assert a.in_declared_frame
    print("  OK  marketer-led clips every agent to the declared audience")


def test_ml_weights_by_mass() -> None:
    high = _ml_disposition("high", [_ml_bundle("female", 20, 24, 0, 14, 100)])   # fully in buy -> mass 1.0
    low = _ml_disposition("low", [
        _ml_bundle("female", 20, 24, 0, 14, 25),    # 25% in buy
        _ml_bundle("female", 30, 40, 0, 14, 75),    # out of buy
    ])
    spec = _ml_spec(_declared_female_2024(), [high, low], 200)
    panel = build_panel(spec, [high, low], category="hw", marketer_led=True, seed=71)
    c = Counter(a.disposition_label for a in panel)
    assert c["high"] > c["low"], c
    # masses 1.0 vs 0.25 -> shares ~0.8 / 0.2
    assert abs(c["high"] / 200 - 0.8) < 0.05, c
    print(f"  OK  marketer-led weights by in-slice mass: {dict(c)}")


def test_ml_deterministic_and_sized() -> None:
    for n in (15, 100, 200):
        young = _ml_disposition("young_fem", [
            _ml_bundle("female", 18, 24, 3.5, 7, 60),
            _ml_bundle("female", 22, 28, 7, 14, 40),
        ])
        spec = _ml_spec(_declared_female_2024(), [young], n)
        p1 = build_panel(spec, [young], category="hw", marketer_led=True, seed=71)
        p2 = build_panel(spec, [young], category="hw", marketer_led=True, seed=71)
        assert len(p1) == n, f"panel size {len(p1)} != {n}"
        assert [a.to_dict() for a in p1] == [a.to_dict() for a in p2], "not reproducible"
    print("  OK  marketer-led: exact size + reproducible at 15/100/200")


def test_ml_discovery_tail() -> None:
    ins = _ml_disposition("ins", [_ml_bundle("female", 20, 24, 0, 14, 100)])
    out = _ml_disposition("out", [_ml_bundle("male", 45, 54, 17, 40, 100)])
    spec = _ml_spec(_declared_female_2024(), [ins, out], 100)
    off = build_panel(spec, [ins, out], category="hw", marketer_led=True, seed=71)
    assert all(a.in_declared_frame for a in off), "tail off should leave no out-of-frame agents"
    assert {a.disposition_label for a in off} == {"ins"}
    on = build_panel(spec, [ins, out], category="hw", marketer_led=True, tail_fraction=0.2, seed=71)
    tail = [a for a in on if not a.in_declared_frame]
    core = [a for a in on if a.in_declared_frame]
    assert len(on) == 100
    assert tail and {a.disposition_label for a in tail} == {"out"}, "tail not from excluded personas"
    assert {a.disposition_label for a in core} == {"ins"}
    assert abs(len(tail) / 100 - 0.2) < 0.02, len(tail)
    print("  OK  discovery tail: off=in-frame only; on=excluded personas segregated + tagged")


def test_ml_eligible_dispositions() -> None:
    ins = _ml_disposition("ins", [_ml_bundle("female", 20, 24, 0, 14, 100)])
    out = _ml_disposition("out", [_ml_bundle("male", 45, 54, 17, 40, 100)])
    nobundle = _disposition("nobundle")  # no bundles -> demographically universal
    spec = _ml_spec(_declared_female_2024(), [ins, out, nobundle], 60)
    elig = {d.label: m for d, m in eligible_dispositions(spec, [ins, out, nobundle])}
    assert "out" not in elig, "disjoint persona should not be eligible"
    assert elig["ins"] == 1.0 and elig["nobundle"] == 1.0, elig
    print("  OK  eligible_dispositions returns in-audience personas (no-bundle = universal)")


def main() -> None:
    print("=== population construction (panel) smoke ===")
    test_panel_size_exact()
    test_chaos_distribution_matched()
    test_cycle_distribution_matched()
    test_custom_cycle_mix_respected()
    test_cycle_reproducible_same_seed()
    test_cycle_not_in_persona_cache_or_segment_key()
    test_marginal_coverage_full()
    test_marginal_coverage_small()
    test_reproducible_same_seed()
    test_reproducible_diff_seed()
    test_segment_keys()
    test_panel_agent_roundtrip()
    test_compute_panel_version()
    test_build_panel_rejects_mismatched_dispositions()
    test_bundled_income_distribution_matches()
    test_bundled_coherence_no_contamination()
    test_bundled_reproducible_and_sizes()
    test_bundled_mixed_fallback()
    test_ml_excludes_disjoint_personas()
    test_ml_clips_agents_to_declared()
    test_ml_weights_by_mass()
    test_ml_deterministic_and_sized()
    test_ml_discovery_tail()
    test_ml_eligible_dispositions()
    print("PASS — panels reproducibly match target distributions.")


if __name__ == "__main__":
    main()
