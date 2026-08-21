"""Offline: L1 panel-resilience reconciliation.

At conc=100 the whole L1 wave fires at once, so a single agent that exhausts its
retries must NOT throw away the other 99 (the old `gather` did). But the fix
can't just "drop and continue" — a run that quietly synthesizes a verdict on a
gutted, unrepresentative panel is worse than a clean crash. So `reconcile_l1_results`
tolerates a couple of stray drops yet ABORTS loudly when the panel falls below
the completion floor OR loses a whole segment (which a correlated 529 burst does).

Run: python tests/test_panel_resilience.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.run_service import PanelDegradedError, reconcile_l1_results


def _agent(aid: int, seg: str):
    # Duck-typed stand-in for PanelAgent (reconcile only reads these two attrs).
    return SimpleNamespace(agent_id=aid, segment_key=seg)


def _landed(aid: int):
    # Stand-in for a successful AgentTranscript (reconcile only reads agent_id).
    return SimpleNamespace(agent_id=aid)


def _panel(n: int, segments: list[str]):
    return [_agent(i, segments[i % len(segments)]) for i in range(n)]


def main() -> None:
    segs = ["seg_a", "seg_b", "seg_c", "seg_d"]

    # 1. Clean run — everything lands, agent_id-sorted, zero drops.
    panel = _panel(20, segs)
    ts, dropped = reconcile_l1_results(panel, [_landed(a.agent_id) for a in panel])
    assert len(ts) == 20 and dropped == [], "clean run keeps every agent"
    assert [t.agent_id for t in ts] == sorted(t.agent_id for t in ts), "sorted"

    # 2. One random drop, above the floor, its segment survives -> tolerated.
    panel = _panel(40, segs)  # 10 per segment
    results = [
        RuntimeError("529 overloaded") if a.agent_id == 5 else _landed(a.agent_id)
        for a in panel
    ]
    ts, dropped = reconcile_l1_results(panel, results)
    assert len(ts) == 39 and dropped == [5], "a single stray failure is tolerated"

    # 3. Below the completion floor -> abort loudly (17/20 = 85% < 95%).
    panel = _panel(20, segs)
    fail = {1, 2, 3}
    results = [
        RuntimeError("529") if a.agent_id in fail else _landed(a.agent_id)
        for a in panel
    ]
    try:
        reconcile_l1_results(panel, results)
        raise AssertionError("expected PanelDegradedError below the floor")
    except PanelDegradedError as exc:
        assert "17/20" in str(exc), f"error should report the count: {exc}"

    # 4. A whole segment wiped, even ABOVE the global floor -> abort.
    # 98 in 'big' + 2 in 'tiny'; fail both 'tiny' -> 98% completion but the
    # 'tiny' segment is gone, which would skew every downstream weight.
    panel = [_agent(i, "big") for i in range(98)] + [
        _agent(98, "tiny"), _agent(99, "tiny")
    ]
    results = [
        RuntimeError("529") if a.segment_key == "tiny" else _landed(a.agent_id)
        for a in panel
    ]
    try:
        reconcile_l1_results(panel, results)
        raise AssertionError("expected abort when a whole segment is wiped")
    except PanelDegradedError as exc:
        assert "tiny" in str(exc), f"error should name the wiped segment: {exc}"

    # 5. Exactly at the floor (19/20 = 95%) is allowed.
    panel = _panel(20, segs)
    results = [
        RuntimeError("x") if a.agent_id == 1 else _landed(a.agent_id)
        for a in panel
    ]
    ts, dropped = reconcile_l1_results(panel, results)
    assert len(ts) == 19 and dropped == [1], "exactly at the floor is allowed"

    # 6. Empty panel -> abort (nothing to synthesize).
    try:
        reconcile_l1_results([], [])
        raise AssertionError("empty panel should raise")
    except PanelDegradedError:
        pass

    print("PASS — L1 panel resilience: tolerates stray drops, aborts on a gutted panel.")


def test_l1_reconciliation_tolerates_drops_but_aborts_on_a_gutted_panel() -> None:
    """⭐ FREE AND OFFLINE, and it never ran until 2026-08-22 — the file had no
    `test_` function, so pytest collected nothing from it while it sat in
    tests/ looking covered. It guards the case where a correlated 529 burst
    guts a segment and the run synthesizes a confident verdict on what is left.

    ⚠ The body stays in main() unchanged rather than being split into
    granular tests — the conversion is about COLLECTION, and rewriting
    working assertions at the same time is how a green suite starts
    asserting something slightly different without anyone noticing."""
    main()


if __name__ == "__main__":
    main()
