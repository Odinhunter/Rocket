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
from agent.panel import PanelAgent, build_panel, compute_panel_version
from agent.vectors import (
    ChaosDistribution,
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)


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


def main() -> None:
    print("=== population construction (panel) smoke ===")
    test_panel_size_exact()
    test_chaos_distribution_matched()
    test_marginal_coverage_full()
    test_marginal_coverage_small()
    test_reproducible_same_seed()
    test_reproducible_diff_seed()
    test_segment_keys()
    test_panel_agent_roundtrip()
    test_compute_panel_version()
    test_build_panel_rejects_mismatched_dispositions()
    print("PASS — panels reproducibly match target distributions.")


if __name__ == "__main__":
    main()
