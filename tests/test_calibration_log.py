"""Phase 7 offline test: the calibration log records a prediction, accepts
an outcome later, and joins the pair by run_id — the infrastructure a
future calibration fit consumes. MULTIPLIER_TABLE_VERSION is stamped on
every prediction. No API calls.

Run: python tests/test_calibration_log.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import calibration_log
from agent.projection_l35 import MULTIPLIER_TABLE_VERSION, project_funnel
from agent.schema import BehavioralSignalDistribution
from agent.synthesis_types import L3Summary
from agent.telemetry import RUNS_DIR

_ACCOUNT = "_test_calib_acct"
_BRAND = "_test_calib_brand"


def _cleanup() -> None:
    p = RUNS_DIR / _ACCOUNT
    if p.exists():
        shutil.rmtree(p)


def _projection():
    dist = BehavioralSignalDistribution(
        counts={"tap_cta": 6, "scroll_past": 9, "linger": 5},
        would_act_within_week_count=6, n=20,
    )
    seg = BehavioralSignalDistribution(
        counts={"tap_cta": 3, "scroll_past": 2}, would_act_within_week_count=3, n=5,
    )
    l3 = L3Summary(
        population_behavioral_distribution=dist,
        segment_behavioral_distributions={"disp_a::moderate": seg},
    )
    return project_funnel(l3, {"stop_rate": 0.1, "click_rate": 0.02,
                               "visit_rate": 0.015, "convert_rate": 0.006})


def test_record_prediction_then_outcome() -> None:
    _cleanup()
    try:
        baseline = {"stop_rate": 0.1, "click_rate": 0.02,
                    "visit_rate": 0.015, "convert_rate": 0.006}
        calibration_log.record_prediction(
            "run_x", _ACCOUNT, _BRAND, _projection(), baseline
        )
        # Before the outcome: one pair, actual_funnel is None.
        pairs = calibration_log.load_calibration_pairs(_ACCOUNT, _BRAND)
        assert len(pairs) == 1
        pair = pairs[0]
        assert pair["run_id"] == "run_x"
        assert pair["multiplier_table_version"] == MULTIPLIER_TABLE_VERSION
        assert pair["actual_funnel"] is None, "actual_funnel should start as None"
        assert pair["projection"]["overall"]["basis"] == "heuristic_v1"
        # Stage gating is logged with the prediction, so a future fit can
        # filter out image-only SCENARIO stages before fitting them.
        stage_meta = pair["projection"]["stage_meta"]
        assert [m["stage_key"] for m in stage_meta] == ["stop", "click", "visit", "convert"]
        status = {m["stage_key"]: m["status"] for m in stage_meta}
        assert status["stop"] == "grounded"  # modeled, always grounded
        assert status["convert"] == "scenario"  # no offer provided in this fixture
        print("  OK  prediction logged with stage_meta gating; actual_funnel slot starts None")

        # Outcome arrives later (a future customer-feedback flow).
        actual = {"stop_rate": 0.12, "click_rate": 0.025,
                  "visit_rate": 0.02, "convert_rate": 0.007}
        calibration_log.record_outcome("run_x", _ACCOUNT, _BRAND, actual)
        pairs = calibration_log.load_calibration_pairs(_ACCOUNT, _BRAND)
        assert len(pairs) == 1, "outcome should join the existing prediction, not add a pair"
        assert pairs[0]["actual_funnel"] == actual, "outcome did not join by run_id"
        print("  OK  outcome joins the prediction by run_id")
    finally:
        _cleanup()


def test_multiple_runs_logged_independently() -> None:
    _cleanup()
    try:
        baseline = {"stop_rate": 0.1, "click_rate": 0.02,
                    "visit_rate": 0.015, "convert_rate": 0.006}
        calibration_log.record_prediction("run_a", _ACCOUNT, _BRAND, _projection(), baseline)
        calibration_log.record_prediction("run_b", _ACCOUNT, _BRAND, _projection(), baseline)
        calibration_log.record_outcome("run_b", _ACCOUNT, _BRAND,
                                       {"stop_rate": 0.09, "click_rate": 0.018,
                                        "visit_rate": 0.013, "convert_rate": 0.005})
        pairs = {p["run_id"]: p for p in
                 calibration_log.load_calibration_pairs(_ACCOUNT, _BRAND)}
        assert set(pairs) == {"run_a", "run_b"}
        assert pairs["run_a"]["actual_funnel"] is None
        assert pairs["run_b"]["actual_funnel"] is not None
        print("  OK  multiple runs logged independently; outcomes join correctly")
    finally:
        _cleanup()


def test_empty_log() -> None:
    _cleanup()
    assert calibration_log.load_calibration_pairs(_ACCOUNT, _BRAND) == []
    print("  OK  empty / missing log returns []")


def main() -> None:
    print("=== calibration log smoke ===")
    test_record_prediction_then_outcome()
    test_multiple_runs_logged_independently()
    test_empty_log()
    print("PASS — calibration scaffolding logs prediction/outcome pairs.")


if __name__ == "__main__":
    main()
