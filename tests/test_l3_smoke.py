"""Step-4 smoke: L3 takes hand-typed L2 summaries + target_classification,
emits L3Summary; we feed it into L4 to confirm end-to-end synthesis works
on synthetic fixtures.

Cost: ~$0.05 (L3 Sonnet) + ~$0.30 (L4 Opus) = ~$0.35.

Run: python tests/test_l3_smoke.py
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
from agent.schema import validate_report
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import synthesize_memo
from agent.synthesis_types import L2Summary, TargetClassification


_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixtures() -> tuple[list[L2Summary], TargetClassification, RunConfig]:
    l2 = [L2Summary.from_dict(d) for d in json.loads((_FIXTURE_DIR / "l2_summaries_boat.json").read_text())]
    tc = TargetClassification.from_dict(json.loads((_FIXTURE_DIR / "target_classification_boat.json").read_text()))
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512 — ₹1,199 Special Deal"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    cfg.validate()
    return l2, tc, cfg


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    print("=== L3 + L4 stack smoke (hand-typed L2 fixtures) ===")

    l2, tc, cfg = _load_fixtures()
    print(f"  inputs: {len(l2)} L2 summaries, {len(tc.disposition_classifications)} disp classifications")
    print(f"  within-target: {tc.within_target_labels()}")
    print(f"  outside-target: {tc.outside_target_labels()}")
    print(f"  ambiguous: {tc.ambiguous_labels()}")

    # ---- L3 ----
    t0 = time.time()
    l3 = synthesize_population(l2, tc, cfg)
    t_l3 = time.time() - t0

    print(f"\n--- L3 ({t_l3:.1f}s) ---")
    print(f"  robust_themes: {len(l3.robust_themes)}")
    for t in l3.robust_themes:
        print(f"    - {t.statement[:90]} (cited_by={t.cited_by}, rounds={t.rounds})")
    print(f"  fragile_themes: {len(l3.fragile_themes)}")
    print(f"  within_target_findings: {len(l3.within_target_findings)}")
    print(f"  outside_target_findings: {len(l3.outside_target_findings)}")
    print(f"  context_fit keys: {sorted(l3.context_fit.keys())}")
    for k, v in l3.context_fit.items():
        print(f"    [{k}] {v.verdict}: {v.friction_summary[:80]}")
    print(f"  representative_quotes: {len(l3.representative_quotes)}")
    print(f"  confidence_signals: {l3.confidence_signals}")

    # Sanity checks on L3
    assert len(l3.context_fit) == 3, f"expected 3 contexts, got {len(l3.context_fit)}"
    assert sorted(l3.context_fit.keys()) == ["commute_scroll", "late_night_wind_down", "pre_purchase_research"], \
        f"context keys: {sorted(l3.context_fit.keys())}"
    assert l3.confidence_signals.within_target_disposition_count == 2, \
        f"expected within_target=2, got {l3.confidence_signals.within_target_disposition_count}"
    assert l3.confidence_signals.total_contexts == 3
    assert 8 <= len(l3.representative_quotes) <= 22, \
        f"representative_quotes len {len(l3.representative_quotes)} outside expected 10-20"

    # ---- L4 chained off L3 output ----
    t0 = time.time()
    report = synthesize_memo(l3, tc, cfg)
    t_l4 = time.time() - t0
    validate_report(report)

    print(f"\n--- L4 chained off L3 ({t_l4:.1f}s) ---")
    print(f"  verdict={report.verdict} confidence={report.confidence}")
    print(f"  top_3_changes ({len(report.top_3_changes)}):")
    for i, c in enumerate(report.top_3_changes, 1):
        print(f"    {i}. {c.change[:90]}")
    print(f"  strengths_to_preserve: {len(report.strengths_to_preserve)}")
    print(f"  context_fit_map keys: {sorted(report.context_fit_map.keys())}")
    print(f"  verbatim_consumer_voice: {len(report.verbatim_consumer_voice)}")
    print(f"  reached: {[d.disposition for d in report.target_match.reached]}")
    print(f"  missed:  {[d.disposition for d in report.target_match.missed]}")

    print("\nPASS — L3 -> L4 stack produces a valid Report.")


if __name__ == "__main__":
    main()
