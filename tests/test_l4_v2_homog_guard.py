"""Offline test: _suppress_homog_high_v2 unconditionally removes
`homogenization_high` from report.methodology_flags in v2's L4 path.

Path 1 supersedes the prior fractional-guard approach. The flag's v1
concept (rare model echo across big cells) does not translate to v2's
locked-disposition x small-cell segmentation where "tight" is the
structural default. The model still emits the flag (it sees the v1
prompt rule); v2 strips it unconditionally. See the block comment in
agent/synthesis_l4_v2.py for full reasoning.

Run: python tests/test_l4_v2_homog_guard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import Report
from agent.synthesis_l4_v2 import _suppress_homog_high_v2
from agent.synthesis_types import ConfidenceSignals


def _report_with_flags(*flags: str) -> Report:
    # Minimal valid-shape Report; suppressor only reads/mutates methodology_flags.
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
    _suppress_homog_high_v2(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=12))
    assert r.methodology_flags == ["single_within_target"], "no-op when flag absent"

    # Case 2: flag present at high fraction (would have been "eligible" under old guard) → strip
    r = _report_with_flags("homogenization_high")
    _suppress_homog_high_v2(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=15))
    assert r.methodology_flags == [], "must strip even at 100% tight"

    # Case 3: flag present at low fraction → strip (same outcome; suppression is unconditional)
    r = _report_with_flags("homogenization_high")
    _suppress_homog_high_v2(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=2))
    assert r.methodology_flags == [], "must strip even at 13% tight"

    # Case 4: flag present at the boat-observed boundary (12/15 = 80%) → strip
    r = _report_with_flags("homogenization_high")
    _suppress_homog_high_v2(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=12))
    assert r.methodology_flags == [], "must strip at the 80% boundary that motivated Path 1"

    # Case 5: empty signals (total_segments=0, legacy run shape) → strip without zero-division
    r = _report_with_flags("homogenization_high")
    _suppress_homog_high_v2(r, ConfidenceSignals(total_segments=0, homogenization_flag_count=0))
    assert r.methodology_flags == [], "must strip safely when total_segments is 0"

    # Case 6: other flags preserved when homog stripped, order intact
    r = _report_with_flags("single_within_target", "homogenization_high", "provisional_disposition_present")
    _suppress_homog_high_v2(r, ConfidenceSignals(total_segments=15, homogenization_flag_count=9))
    assert r.methodology_flags == ["single_within_target", "provisional_disposition_present"], (
        "other flags preserved with order intact"
    )

    print("PASS: all suppression cases")


if __name__ == "__main__":
    main()
