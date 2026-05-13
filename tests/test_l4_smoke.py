"""Step-3 smoke test: L4 strategic memo produces a valid Report from the
hand-typed L3 + target_classification fixtures.

Costs ~$0.30 per run (Opus 4.7). Re-run 3x to confirm parse retry handles
flakes. Skips automatically without ANTHROPIC_API_KEY.

Run: python tests/test_l4_smoke.py [--once]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent.config import AssetSpec, RunConfig
from agent.schema import Report, validate_report
from agent.synthesis_l4 import synthesize_memo
from agent.synthesis_types import L3Summary, TargetClassification


_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixtures() -> tuple[L3Summary, TargetClassification, RunConfig]:
    l3 = L3Summary.from_dict(json.loads((_FIXTURE_DIR / "l3_summary_boat.json").read_text()))
    tc = TargetClassification.from_dict(
        json.loads((_FIXTURE_DIR / "target_classification_boat.json").read_text())
    )
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512 — ₹1,199 Special Deal"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
        dispositions_per_run=5,
        contexts_per_run=3,
        seeds_per_cell=1,
    )
    cfg.validate()
    return l3, tc, cfg


def _one_run(idx: int) -> Report:
    l3, tc, cfg = _load_fixtures()
    t0 = time.time()
    report = synthesize_memo(l3, tc, cfg)
    elapsed = time.time() - t0
    validate_report(report)
    print(f"\n--- run {idx}: verdict={report.verdict} confidence={report.confidence} ({elapsed:.1f}s) ---")
    print(f"  top_3_changes: {len(report.top_3_changes)}")
    for i, ch in enumerate(report.top_3_changes, 1):
        print(f"    {i}. {ch.change[:80]}")
    print(f"  strengths: {len(report.strengths_to_preserve)}")
    print(f"  context_fit_map keys: {sorted(report.context_fit_map.keys())}")
    print(f"  verbatim_consumer_voice: {len(report.verbatim_consumer_voice)} quotes")
    # spot-check: at least one within-target disposition reached
    reached_labels = [d.disposition for d in report.target_match.reached]
    print(f"  reached: {reached_labels}")
    print(f"  missed:  {[d.disposition for d in report.target_match.missed]}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run only once (default: 3 times)")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    print("=== L4 smoke test (3x default for retry-flake coverage) ===")
    n_runs = 1 if args.once else 3

    reports: list[Report] = []
    for i in range(1, n_runs + 1):
        report = _one_run(i)
        reports.append(report)

    print(f"\n=== Summary across {len(reports)} runs ===")
    verdicts = [r.verdict for r in reports]
    confs = [r.confidence for r in reports]
    print(f"  verdicts: {verdicts}")
    print(f"  confidence range: {min(confs)}-{max(confs)}")

    # Acceptance asserts
    for i, report in enumerate(reports, 1):
        assert report.verdict in ("WORKING", "MIXED", "FAILING", "METHODOLOGY_GAP"), (
            f"run {i}: bad verdict {report.verdict}"
        )
        if report.verdict != "METHODOLOGY_GAP":
            assert len(report.top_3_changes) == 3, (
                f"run {i}: top_3_changes len {len(report.top_3_changes)}"
            )
        assert sorted(report.context_fit_map.keys()) == [
            "commute_scroll", "late_night_wind_down", "pre_purchase_research"
        ], f"run {i}: context_fit_map keys mismatch: {sorted(report.context_fit_map.keys())}"
        assert 5 <= len(report.verbatim_consumer_voice) <= 12, (
            f"run {i}: verbatim_consumer_voice len {len(report.verbatim_consumer_voice)}"
        )
        # 1.2.0: methodology_flags is a list; can be empty when data is clean.
        # When verdict is METHODOLOGY_GAP, at least one trigger flag must be set
        # (pool_archetype_mismatch or target_unsignaled) since those are the
        # only two conditions that produce GAP under the new logic.
        assert isinstance(report.methodology_flags, list), (
            f"run {i}: methodology_flags must be a list"
        )
        if report.verdict == "METHODOLOGY_GAP":
            gap_triggers = {"pool_archetype_mismatch", "target_unsignaled"}
            assert any(f in gap_triggers for f in report.methodology_flags), (
                f"run {i}: METHODOLOGY_GAP without a trigger flag in "
                f"methodology_flags={report.methodology_flags}"
            )
    print("\nPASS — L4 produces valid Reports.")


if __name__ == "__main__":
    main()
