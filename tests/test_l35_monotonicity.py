"""Phase 4 offline test: L3.5 monotonicity sanity check. A strictly more
positive behavioral distribution must never produce a strictly lower
projected funnel — if it could, the heuristic would be incoherent. No API.

Run: python tests/test_l35_monotonicity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.projection_l35 import project_funnel
from agent.schema import BehavioralSignalDistribution
from agent.synthesis_types import L3Summary


def _dist(counts: dict[str, int], would_act: int, n: int) -> BehavioralSignalDistribution:
    return BehavioralSignalDistribution(
        counts=counts, would_act_within_week_count=would_act, n=n
    )


def _overall(dist: BehavioralSignalDistribution):
    return project_funnel(
        L3Summary(population_behavioral_distribution=dist), None
    ).overall


def test_more_positive_never_lowers_funnel() -> None:
    """Sweep from a scroll-heavy distribution to an engagement-heavy one;
    every step must hold or raise each funnel stage, never strictly lower
    all of them."""
    n = 20
    prev = None
    # Step k: k agents engage (tap_cta + would_act), the rest scroll past.
    for k in range(0, n + 1):
        dist = _dist(
            {"tap_cta": k, "scroll_past": n - k},
            would_act=k,
            n=n,
        )
        fr = _overall(dist)
        if prev is not None:
            assert fr.stop_rate >= prev.stop_rate - 1e-9, (
                f"stop_rate dropped as engagement rose (k={k})"
            )
            assert fr.click_rate >= prev.click_rate - 1e-9, (
                f"click_rate dropped as engagement rose (k={k})"
            )
            assert fr.visit_rate >= prev.visit_rate - 1e-9, (
                f"visit_rate dropped as engagement rose (k={k})"
            )
            assert fr.convert_rate >= prev.convert_rate - 1e-9, (
                f"convert_rate dropped as engagement rose (k={k})"
            )
        prev = fr
    print("  OK  every funnel stage is monotonic non-decreasing in engagement")


def test_strictly_better_distribution_dominates() -> None:
    """A distribution that is strictly better on every axis must produce a
    funnel that is >= on every stage."""
    worse = _dist({"scroll_past": 16, "linger": 4}, would_act=1, n=20)
    better = _dist({"tap_cta": 8, "seek_info": 6, "linger": 6}, would_act=12, n=20)
    fw, fb = _overall(worse), _overall(better)
    for stage in ("stop_rate", "click_rate", "visit_rate", "convert_rate"):
        assert getattr(fb, stage) >= getattr(fw, stage) - 1e-9, (
            f"{stage}: strictly-better distribution did not dominate"
        )
    print("  OK  a strictly-better distribution dominates on every funnel stage")


def main() -> None:
    print("=== L3.5 monotonicity smoke ===")
    test_more_positive_never_lowers_funnel()
    test_strictly_better_distribution_dominates()
    print("PASS — L3.5 funnel projection is monotonic and coherent.")


if __name__ == "__main__":
    main()
