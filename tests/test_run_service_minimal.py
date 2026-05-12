"""Step-8 smoke: RunService end-to-end with a tiny config (1 disposition
× 1 context × 1 seed = 1 agent). Proves the orchestrator wires every
layer correctly. The full 5×3×1 acceptance test is the Step-9 gate.

Cost: ~$0.50 (1 L1 agent + 1 L2 + 1 L3 + 1 L4 + 1 target_id).

Run: python tests/test_run_service_minimal.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent.config import AssetSpec, RunConfig
from agent.run_service import RunService
from agent.schema import validate_report
from agent.telemetry import run_dir


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    print("=== RunService minimal smoke (1x1x1 = 1 agent) ===")

    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512 — ₹1,199"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
        dispositions_per_run=1,
        contexts_per_run=1,
        seeds_per_cell=1,
    )
    cfg.validate()
    print(f"  config: {cfg.total_agents()} agent, mode={cfg.mode}")

    t0 = time.time()
    report = RunService.run(cfg)
    elapsed = time.time() - t0
    validate_report(report)

    print(f"\n--- Run complete in {elapsed:.1f}s ---")
    print(f"  verdict={report.verdict} confidence={report.confidence}")
    print(f"  top_3_changes: {len(report.top_3_changes)}")
    for i, c in enumerate(report.top_3_changes, 1):
        print(f"    {i}. {c.change[:90]}")
        print(f"       evidence_quotes: {len(c.evidence_quotes)}")
    print(f"  strengths_to_preserve: {len(report.strengths_to_preserve)}")
    print(f"  context_fit_map keys: {sorted(report.context_fit_map.keys())}")
    print(f"  verbatim_consumer_voice: {len(report.verbatim_consumer_voice)}")
    print(f"  reached: {[d.disposition for d in report.target_match.reached]}")
    print(f"  missed:  {[d.disposition for d in report.target_match.missed]}")

    # Find the run dir on disk
    rd_root = Path("runs") / cfg.account_id / cfg.brand_profile_id
    runs = sorted(rd_root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if runs:
        latest = runs[0]
        print(f"\n  run_dir: {latest}")
        artifacts = sorted(latest.rglob("*.json"))
        for a in artifacts:
            sz = a.stat().st_size
            print(f"    {a.relative_to(latest)}  ({sz:,} bytes)")

        # Check invariants
        inv_path = latest / "invariants.json"
        if inv_path.exists():
            inv = json.loads(inv_path.read_text())
            print(f"\n  invariants: all_passed={inv['all_passed']}")
            print(f"    n_l1_calls_checked={inv['n_l1_calls_checked']}")
            print(f"    estimated_cost_usd=${inv['estimated_cost_usd']:.3f}")
            if inv["failures"]:
                print(f"    FAILURES:")
                for f in inv["failures"]:
                    print(f"      {f}")
            assert inv["all_passed"], f"telemetry invariants failed: {inv['failures']}"
            print("  OK  all telemetry invariants pass")

    print("\nPASS — RunService minimal 1x1x1 end-to-end.")


if __name__ == "__main__":
    main()
