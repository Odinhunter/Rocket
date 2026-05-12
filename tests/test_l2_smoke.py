"""Step-5 smoke: L2 (per-disposition) -> L3 -> L4 against the real
pre-refactor checkpoint data, adapted to AgentTranscript shape.

This is the end-to-end synthesis-stack proof using FREE REAL DATA — no
L1 code has been touched yet.

Cost: 7 L2 calls (Sonnet, ~$0.02 each) + 1 L3 (Sonnet, ~$0.05) +
1 L4 (Opus, ~$0.30) = ~$0.50.

The 7 dispositions in the source data come from the personal_audio
pre-refactor run (premium_audio_aspirant, replacement_buyer,
specs_skeptical_pragmatist, brand_loyal_boat_user, spec_led_upgrader,
design_led_nothing_enthusiast, wired_audio_purist). We pretend the first
2 (premium + replacement + brand-loyal) are "within target" for the
purposes of fitting the test fixture; in production target classification
comes from the Opus vision call.

Run: python tests/test_l2_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent.config import AssetSpec, RunConfig
from agent.schema import AgentTranscript, validate_report
from agent.synthesis_l2 import synthesize_disposition_async
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import synthesize_memo
from agent.synthesis_types import (
    DispositionTarget,
    L2Summary,
    TargetClassification,
)


_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_transcripts() -> list[AgentTranscript]:
    raw = json.loads((_FIXTURE_DIR / "transcripts_boat.json").read_text())
    return [AgentTranscript.from_dict(d) for d in raw]


def _hand_target_classification(disposition_labels: list[str]) -> TargetClassification:
    """For the test, hand-classify the 7 dispositions from the real source data.
    In production, this comes from the Opus vision call."""
    within = {"replacement_buyer", "brand_loyal_boat_user", "spec_led_upgrader"}
    outside = {"design_led_nothing_enthusiast", "wired_audio_purist"}
    classifications: list[DispositionTarget] = []
    for d in disposition_labels:
        if d in within:
            c = "within"
            reason = "Value-conscious Boat-tier buyer; the ad's price-led pitch matches their decision frame."
        elif d in outside:
            c = "outside"
            reason = "Design-led or wired-audio preference puts them out of this ad's apparent target."
        else:
            c = "ambiguous"
            reason = "Partially matches; could go either way depending on individual price-tier preference at the moment of decision."
        classifications.append(DispositionTarget(
            disposition_label=d,
            classification=c,
            reasoning=reason,
        ))
    return TargetClassification(
        inferred_target_description=(
            "Value-conscious 22-30 urban Indian male shopping for personal_audio "
            "under ₹2k, treats earbuds as utility-grade, price-sensitive, open to "
            "Boat upgrade if the deal mathematics check out."
        ),
        target_reasoning=(
            "The ₹1,199 'Special Deal Price' is the dominant visual hook, and the "
            "'Shop Now' CTA + closed-case product shot reads as a quick-decision "
            "online purchase pitch, not a premium audiophile pitch. The 'Prime' "
            "badge cosmetic-premium signal is aimed at existing Boat customers "
            "who'd recognize the lineage."
        ),
        disposition_classifications=classifications,
    )


async def _run_l2_parallel(
    transcripts_by_disposition: dict[str, list[AgentTranscript]],
    config: RunConfig,
) -> list[L2Summary]:
    coros = [
        synthesize_disposition_async(label, ts, config)
        for label, ts in transcripts_by_disposition.items()
    ]
    summaries = await asyncio.gather(*coros)
    summaries.sort(key=lambda s: s.disposition_label)
    return summaries


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    print("=== L2 -> L3 -> L4 stack smoke (real adapted transcripts) ===")

    transcripts = _load_transcripts()
    by_disposition: dict[str, list[AgentTranscript]] = defaultdict(list)
    for t in transcripts:
        by_disposition[t.disposition_label].append(t)

    disposition_labels = sorted(by_disposition.keys())
    print(f"  loaded {len(transcripts)} transcripts across {len(by_disposition)} dispositions:")
    for d in disposition_labels:
        print(f"    {d}: {len(by_disposition[d])} transcript(s)")

    tc = _hand_target_classification(disposition_labels)
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512 — ₹1,199 Special Deal"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
        dispositions_per_run=len(disposition_labels),
        contexts_per_run=1,
        seeds_per_cell=1,
    )
    # Override the brand_profile cap-of-7 validator since we're at the ceiling.
    cfg.validate()

    # ---- L2 fan-out (parallel) ----
    print(f"\n--- L2 (parallel, {len(by_disposition)} dispositions) ---")
    t0 = time.time()
    l2_summaries = asyncio.run(_run_l2_parallel(by_disposition, cfg))
    t_l2 = time.time() - t0
    print(f"  L2 completed in {t_l2:.1f}s")
    for s in l2_summaries:
        rep_keys = sorted(s.representative_quotes.keys())
        print(f"  [{s.disposition_label}] variance={s.within_cell_variance} quotes_rounds={rep_keys}")
        print(f"    summary: {s.summary_paragraph[:120]}...")
        if s.outlier_note:
            print(f"    OUTLIER: {s.outlier_note}")

    # Sanity check L2
    for s in l2_summaries:
        assert s.disposition_label in by_disposition, f"unexpected disposition {s.disposition_label}"
        assert s.within_cell_variance in ("tight", "spread", "outlier_present")
        assert len(s.summary_paragraph) > 50, "summary too short"
        assert len(s.representative_quotes) >= 4, f"too few rep quotes ({len(s.representative_quotes)}) for {s.disposition_label}"

    # ---- L3 ----
    print(f"\n--- L3 ---")
    t0 = time.time()
    l3 = synthesize_population(l2_summaries, tc, cfg)
    t_l3 = time.time() - t0
    print(f"  L3 completed in {t_l3:.1f}s")
    print(f"  robust_themes: {len(l3.robust_themes)}, fragile: {len(l3.fragile_themes)}")
    print(f"  within_target_findings: {len(l3.within_target_findings)}")
    print(f"  outside_target_findings: {len(l3.outside_target_findings)}")
    print(f"  context_fit: {sorted(l3.context_fit.keys())}")
    print(f"  representative_quotes: {len(l3.representative_quotes)}")
    print(f"  confidence_signals: {l3.confidence_signals}")

    # ---- L4 ----
    print(f"\n--- L4 ---")
    t0 = time.time()
    report = synthesize_memo(l3, tc, cfg)
    t_l4 = time.time() - t0
    validate_report(report)
    print(f"  L4 completed in {t_l4:.1f}s")
    print(f"  verdict={report.verdict} confidence={report.confidence}")
    print(f"  top_3_changes ({len(report.top_3_changes)}):")
    for i, c in enumerate(report.top_3_changes, 1):
        print(f"    {i}. {c.change[:90]}")
    print(f"  strengths_to_preserve: {len(report.strengths_to_preserve)}")
    print(f"  context_fit_map: {sorted(report.context_fit_map.keys())}")
    print(f"  verbatim_consumer_voice: {len(report.verbatim_consumer_voice)}")
    print(f"  reached: {[d.disposition for d in report.target_match.reached]}")

    print(f"\n=== END-TO-END SYNTHESIS STACK ===")
    print(f"  total elapsed: {t_l2 + t_l3 + t_l4:.1f}s")
    print(f"  L2 cost ~$0.{int(len(by_disposition)*2):02d}, L3 ~$0.05, L4 ~$0.30")
    print(f"\nPASS — L2 (real adapted transcripts) -> L3 -> L4 produces a valid Report.")

    # Save the report for visual inspection
    out_path = _FIXTURE_DIR / "smoke_report_boat.json"
    out_path.write_text(report.to_json())
    print(f"  Report saved to {out_path}")


if __name__ == "__main__":
    main()
