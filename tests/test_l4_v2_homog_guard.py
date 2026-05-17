"""Offline test: _apply_homog_high_guard strips homogenization_high from
report.methodology_flags when L3 confidence_signals don't justify it under
v2's fractional rule. The model owns nothing here — Python is authoritative.

Run: python tests/test_l4_v2_homog_guard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import Report
from agent.synthesis_l4_v2 import (
    _HOMOG_HIGH_FRACTION,
    _HOMOG_HIGH_MIN_TOTAL_SEGMENTS,
    _apply_homog_high_guard,
)
from agent.synthesis_types import ConfidenceSignals


def _report_with_flags(*flags: str) -> Report:
    # Minimal valid-shape Report; the guard only reads/mutates methodology_flags.
    return Report(
        verdict="MIXED",
        confidence=50,
        target_match="ambiguous",
        top_3_changes=[],
        strengths_to_preserve=[],
        context_fit_map={},
        verbatim_consumer_voice=[],
        methodology_flags=list(flags),
    )


def main() -> None:
    # Case 1: flag absent → no-op
    r = _report_with_flags("single_within_target")
    _apply_homog_high_guard(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=15))
    assert r.methodology_flags == ["single_within_target"], "no-op when flag absent"

    # Case 2: total_segments under floor → strip (guards small runs and legacy)
    r = _report_with_flags("homogenization_high")
    _apply_homog_high_guard(r, ConfidenceSignals(total_segments=4, homogenization_flag_count=4))
    assert "homogenization_high" not in r.methodology_flags, "must strip when total_segments under floor"

    # Case 3: fraction below threshold → strip (this is the observed v2 baseline case)
    r = _report_with_flags("homogenization_high")
    _apply_homog_high_guard(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=11))  # 73% — observed boat baseline
    assert "homogenization_high" not in r.methodology_flags, "must strip at 73% (below 80% threshold)"

    # Case 4: fraction at threshold → keep (boundary)
    r = _report_with_flags("homogenization_high")
    _apply_homog_high_guard(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=12))  # 80% exact
    assert "homogenization_high" in r.methodology_flags, "must keep at exactly 80%"

    # Case 5: fraction above threshold → keep (genuinely collapsed panel)
    r = _report_with_flags("homogenization_high")
    _apply_homog_high_guard(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=14))  # 93%
    assert "homogenization_high" in r.methodology_flags, "must keep at 93%"

    # Case 6: other flags preserved when homog is stripped
    r = _report_with_flags("single_within_target", "homogenization_high", "provisional_disposition_present")
    _apply_homog_high_guard(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=9))  # 60%
    assert r.methodology_flags == ["single_within_target", "provisional_disposition_present"], "other flags preserved, order intact"

    # Constants sanity
    assert _HOMOG_HIGH_FRACTION == 0.80
    assert _HOMOG_HIGH_MIN_TOTAL_SEGMENTS == 5

    print("PASS: all guard cases")


if __name__ == "__main__":
    main()
