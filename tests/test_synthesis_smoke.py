"""API smoke: the full synthesis chain end-to-end — L2 (per-segment) -> L3
-> L3.5 projection -> L4 — on a small hand-written transcript set.
Validates the wiring, not the prose quality.

Asserts: L2 summaries carry a Python-computed behavioral_distribution; L3
carries the population + per-segment distributions; L3.5 produces a
FunnelProjection; L4 produces a validated Report with a non-empty
bet_ranking and the funnel_projection attached.

Cost: ~3 Sonnet calls (2x L2, 1x L3) + 1 Opus call (L4), ~$0.35.

Run: python tests/test_synthesis_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agent.config import AssetSpec, RunConfig
from agent.projection_l35 import project_funnel
from agent.schema import AgentTranscript, BehavioralSignal, validate_report
from agent.synthesis_l2 import synthesize_segment
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import synthesize_memo
from agent.synthesis_types import DispositionTarget, TargetClassification

# A boat-earbuds-style creative. Two segments, two transcripts each.
_SEGMENTS = {
    "office_bru_pragmatist::moderate": [
        AgentTranscript(
            agent_id=0, disposition_label="office_bru_pragmatist",
            context_label="commute_scroll", seed_idx=0,
            encoding_text=(
                "R1 GUT: A ₹1,199 deal price with a brown case, looks like a "
                "decent enough budget option.\n"
                "R2 COMPREHENSION: Boat earbuds on sale, the price is the "
                "headline, there's an asterisk next to it. The 'Prime' badge "
                "is doing a lot of work. It reads as a quick online buy.\n"
                "R3 EMOTION: Mildly interested, mostly because the number is "
                "concrete and I trust a price I can see. No real excitement, "
                "but no irritation either — it's a functional pitch and I "
                "respond to functional pitches."
            ),
            reflection_text=(
                "R4 STICKINESS: The ₹1,199 stuck, the asterisk stuck more — "
                "I remember wondering what it was hiding.\n"
                "R5 SOCIAL: Wouldn't share it, nothing to say about it.\n"
                "R6 FRICTION: The asterisk on the price. If the real price is "
                "₹1,199 all-in I'd consider it; if it's a bait number I'm out. "
                "The ad didn't resolve that.\n"
                'NEXT_STEP: {"next_step": "research_first", "reasoning": "the '
                'asterisk on ₹1,199 needs resolving before I would buy"}'
            ),
            behavioral_signal=BehavioralSignal(
                action="linger",
                action_reasoning="stopped on the ₹1,199 but the asterisk needs resolving",
                next_step="research_first",
                next_step_reasoning="the asterisk on ₹1,199 needs resolving before I would buy",
            ),
        ),
        AgentTranscript(
            agent_id=1, disposition_label="office_bru_pragmatist",
            context_label="pre_purchase_research", seed_idx=0,
            encoding_text=(
                "R1 GUT: Fine, a budget earbud deal, I've seen fifty of these.\n"
                "R2 COMPREHENSION: It's a price-led Boat ad. The deal price is "
                "the whole message. Comparison-shoppable.\n"
                "R3 EMOTION: Neutral leaning slightly positive — in research "
                "mode the price anchor is exactly what I want to see."
            ),
            reflection_text=(
                "R4 STICKINESS: The price and the brand. That's all I needed.\n"
                "R5 SOCIAL: No.\n"
                "R6 FRICTION: Still the asterisk — but in research mode I'll "
                "just go check the landing page, so it's lower friction here.\n"
                'NEXT_STEP: {"next_step": "buy_now", "reasoning": "in research '
                'mode the price is enough to tap through and just order"}'
            ),
            behavioral_signal=BehavioralSignal(
                action="tap_cta",
                action_reasoning="in research mode the price is enough to tap through",
                next_step="buy_now",
                next_step_reasoning="the price is enough to just order in research mode",
            ),
        ),
    ],
    "specialty_coffee_enthusiast::deliberate": [
        AgentTranscript(
            agent_id=2, disposition_label="specialty_coffee_enthusiast",
            context_label="commute_scroll", seed_idx=0,
            encoding_text=(
                "R1 GUT: Not for me, scrolling past.\n"
                "R2 COMPREHENSION: A cheap-earbuds price ad. The message is "
                "'cheap', and 'cheap' is not a category I shop. Nothing here.\n"
                "R3 EMOTION: Indifference bordering on mild contempt for the "
                "'Prime' badge — it reads as a sticker pretending to be a tier."
            ),
            reflection_text=(
                "R4 STICKINESS: Nothing stuck. Maybe the brown case.\n"
                "R5 SOCIAL: No.\n"
                "R6 FRICTION: The whole proposition — it's solving for a buyer "
                "who isn't me. No friction to act on because there's no intent.\n"
                'NEXT_STEP: {"next_step": "nothing", "reasoning": "budget '
                'earbuds are not a category I engage with at all"}'
            ),
            behavioral_signal=BehavioralSignal(
                action="scroll_past",
                action_reasoning="budget earbuds are not a category I engage with",
                next_step="nothing",
                next_step_reasoning="not a category I engage with",
            ),
        ),
        AgentTranscript(
            agent_id=3, disposition_label="specialty_coffee_enthusiast",
            context_label="late_night_wind_down", seed_idx=0,
            encoding_text=(
                "R1 GUT: Scroll.\n"
                "R2 COMPREHENSION: Boat deal ad. Read it in half a second, "
                "it's a price pitch for a tier I don't buy.\n"
                "R3 EMOTION: Flat. Late-night low-attention scroll, this never "
                "had a chance to register."
            ),
            reflection_text=(
                "R4 STICKINESS: Nothing.\n"
                "R5 SOCIAL: No.\n"
                "R6 FRICTION: N/A — no purchase consideration at all.\n"
                'NEXT_STEP: {"next_step": "nothing", "reasoning": "low '
                'attention and wrong category, gone in half a second"}'
            ),
            behavioral_signal=BehavioralSignal(
                action="scroll_past",
                action_reasoning="low attention and wrong category",
                next_step="nothing",
                next_step_reasoning="low attention and wrong category",
            ),
        ),
    ],
}

_TARGET = TargetClassification(
    inferred_target_description=(
        "Budget-conscious online earbud buyers; existing Boat-tier customers "
        "responding to a deal price."
    ),
    target_reasoning=(
        "The deal price is the headline, the 'Prime' badge and brown case "
        "signal a mass-market online purchase, the asterisk and 'Shop Now' "
        "framing target a quick-decision deal buyer."
    ),
    disposition_classifications=[
        DispositionTarget(
            disposition_label="office_bru_pragmatist", classification="within",
            reasoning="price-led functional buyer — exactly the deal-price target",
        ),
        DispositionTarget(
            disposition_label="specialty_coffee_enthusiast", classification="outside",
            reasoning="quality-first identity buyer — not a budget-deal target",
        ),
    ],
)

_BASELINE = {
    "stop_rate": 0.11, "click_rate": 0.018,
    "visit_rate": 0.014, "convert_rate": 0.005,
}


def main() -> None:
    print("=== synthesis chain API smoke (L2 -> L3 -> L3.5 -> L4) ===")
    config = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes deal"),
        archetype="urban_indian_male_22_30", category="personal_audio",
        baseline_funnel=_BASELINE,
    )

    # L2 — one call per segment.
    l2_summaries = []
    for segment_label, transcripts in _SEGMENTS.items():
        summary = synthesize_segment(segment_label, transcripts, config)
        assert summary.segment_label == segment_label
        bd = summary.behavioral_distribution
        assert bd.n == len(transcripts), f"{segment_label}: behavioral n {bd.n} != {len(transcripts)}"
        assert sum(bd.counts.values()) == bd.n
        l2_summaries.append(summary)
        print(f"  OK  L2 {segment_label}: summary + behavioral_distribution "
              f"{dict(bd.counts)} (buy_intent={bd.buy_intent_count})")

    # L3 — population synthesis + behavioral distributions.
    l3 = synthesize_population(l2_summaries, _TARGET, config)
    assert l3.population_behavioral_distribution.n == 4, (
        f"population n {l3.population_behavioral_distribution.n} != 4"
    )
    assert len(l3.segment_behavioral_distributions) == 2
    assert l3.representative_quotes, "L3 quote pool is empty"
    assert l3.confidence_signals.within_target_disposition_count == 1, (
        "expected exactly 1 distinct within-target disposition"
    )
    print(f"  OK  L3: population dist n={l3.population_behavioral_distribution.n}, "
          f"{len(l3.segment_behavioral_distributions)} segment dists, "
          f"{len(l3.representative_quotes)} quotes pooled")

    # L3.5 — funnel projection (deterministic Python).
    projection = project_funnel(l3, _BASELINE)
    assert projection.overall.basis == "heuristic_v1"
    assert len(projection.by_segment) == 2
    print(f"  OK  L3.5: overall click_rate={projection.overall.click_rate:.4f} "
          f"(band {projection.overall.click_band[0]:.4f}-"
          f"{projection.overall.click_band[1]:.4f}), "
          f"{len(projection.by_segment)} segment projections")

    # L4 — strategic memo with bet_ranking headline.
    report = synthesize_memo(
        l3, _TARGET, projection, config,
        provisional_dispositions=["office_bru_pragmatist"],
    )
    validate_report(report)
    assert report.bet_ranking, "bet_ranking is empty"
    assert report.funnel_projection is not None, "funnel_projection not attached"
    assert report.funnel_projection.overall.basis == "heuristic_v1"
    assert "office_bru_pragmatist" in report.provisional_dispositions
    assert "provisional_disposition_present" in report.methodology_flags, (
        "provisional flag not auto-added"
    )
    print(f"  OK  L4: verdict={report.verdict} confidence={report.confidence}")
    print(f"      bet_ranking ({len(report.bet_ranking)} bets):")
    for bet in report.bet_ranking:
        print(f"        - {bet}")
    print("PASS — synthesis chain produces a validated Report with funnel + bets.")


if __name__ == "__main__":
    main()
