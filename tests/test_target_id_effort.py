"""Lever-4 investigation: does Opus 4.7 effort=low produce stable target_id
classifications on the bru boundary case?

NOTE: This test uses hand-written disposition descriptions that approximate
but do not match the canonical pool in `archetypes/disposition.py`. The
standalone result (5/5 byte-identical on these hand-written descriptions)
was a useful gating signal that effort=low reduces stochasticity, but full-
pipeline stability is the load-bearing measurement and is captured by
running batch_run.py on bru and inspecting target_classification.json
across runs. On the canonical disposition pool, full-pipeline runs at
1.3.0 stabilize the within-count (the verdict-load-bearing signal) at 1
across runs, where pre-Lever-4 runs flipped 0↔1.

Baseline (5 prior session runs at SDK default, no effort config):
- within-count flipped 0↔1↔2 across runs, driving the verdict bucket flip
  from METHODOLOGY_GAP@15 to MIXED@45.
- 3 of 5 dispositions stable (outside); 2 boundary dispositions tipped.

Cost: ~$0.74 total (5 calls × $0.15 each at effort=low).

Run: python tests/test_target_id_effort.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import anthropic

from agent.target_id import _TOOL, _SYSTEM, _MEDIA_TYPES, _extract_tool_use


# Replicate the bru run inputs exactly so we hit the same boundary case
# the prior 5-run experiment found.
_BRU_DISPOSITIONS: list[tuple[str, str]] = [
    (
        "office_bru_pragmatist",
        "Drinks Bru in the office pantry; treats coffee as a daily utility, "
        "not an aspirational object. Mildly skeptical of premium variants "
        "('Gold' SKUs, double-walled mugs, latte art on instant). 'Paying "
        "more for coffee is silly' is a baseline principle, but he'll cave "
        "for the right occasion — Diwali, a guest, a partner's preference."
    ),
    (
        "specialty_coffee_enthusiast",
        "Owns a V60, hand grinder, and a subscription to Subko / Blue Tokai "
        "beans. Considers freeze-dried instant for 'uneducated drinkers.' "
        "Identifies with Third Wave coffee culture; reads instant-coffee ads "
        "as actively repellant signals, regardless of how the format is "
        "dressed up."
    ),
    (
        "convenience_optimizer",
        "Format-agnostic; primary decision mechanism is per-cup math + "
        "delivery friction. Open to a good instant if the price-per-cup "
        "beats Nescafé Gold by a meaningful margin and a Blinkit jar "
        "delivers in 10 minutes. Persuasion-frame sensitive: rejects ads "
        "that lead with emotion instead of math."
    ),
    (
        "cafe_regular_sachet_skeptical",
        "Buys Blue Tokai cold brew twice a week at the cafe; treats it as "
        "ritual + class signal. A jar or sachet of Bru reads as a downgrade "
        "from his routine — a step in the wrong direction. Festive framing "
        "doesn't override the format objection."
    ),
    (
        "filter_coffee_loyalist",
        "South Indian; daily ritual is degree kapi with a metal filter, "
        "served in davara-tumbler. Identity is built around format + "
        "cultural register. Freeze-dried instant in glass latte mugs is "
        "neither his daily nor his festive ritual. North-Indian-coded "
        "Diwali iconography doesn't speak to his Tamil/Kannada coffee world."
    ),
]


def _image_block(image_path: str) -> dict:
    path = Path(image_path)
    media_type = _MEDIA_TYPES[path.suffix.lower()]
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _one_call(client: anthropic.Anthropic, idx: int) -> tuple[dict, float, dict]:
    """One target_id call with thinking=adaptive, effort=low.

    Returns (tool_input_dict, elapsed_seconds, usage_dict).
    """
    image_block = _image_block("assets/bru_ad.png")
    disposition_text = "\n\n".join(
        f"**{label}** — {desc}" for label, desc in _BRU_DISPOSITIONS
    )
    user_content = [
        image_block,
        {
            "type": "text",
            "text": (
                "AD CONTEXT: Bru Gold Festive\n"
                "Category: coffee\n"
                "Archetype: urban_indian_male_22_30\n\n"
                "DISPOSITIONS IN THE RUN POOL:\n\n"
                + disposition_text
                + "\n\nClassify each disposition above against the ad's "
                "inferred target. Use the classify_ad_target tool."
            ),
        },
    ]

    # Anthropic API constraint discovered: `thinking` cannot be enabled with
    # forced tool_choice. We use effort=low WITHOUT explicit thinking — on
    # Opus 4.7 this disables thinking by default and just controls output
    # verbosity. The question is whether the SDK default (high effort
    # implicit) was driving target_id's classification stochasticity, and
    # whether dropping to low effort makes it more deterministic.
    t0 = time.time()
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4000,
        output_config={"effort": "low"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "classify_ad_target"},
    )
    elapsed = time.time() - t0

    tool_input = _extract_tool_use(response, "classify_ad_target")
    usage = {
        "input_tokens": getattr(response.usage, "input_tokens", 0),
        "output_tokens": getattr(response.usage, "output_tokens", 0),
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    }
    return tool_input, elapsed, usage


def _summarize_classifications(tool_input: dict) -> dict[str, str]:
    """Map disposition_label -> classification, ignoring reasoning text."""
    return {
        d["disposition_label"]: d["classification"]
        for d in tool_input.get("disposition_classifications", [])
    }


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    n_runs = 5
    print(f"=== Lever 4: target_id × {n_runs} with effort=low, adaptive thinking ===\n")

    client = anthropic.Anthropic(max_retries=5)

    all_classifications: list[dict[str, str]] = []
    all_elapsed: list[float] = []
    total_input = 0
    total_output = 0

    for i in range(1, n_runs + 1):
        try:
            tool_input, elapsed, usage = _one_call(client, i)
        except Exception as e:
            print(f"  run {i}: FAILED — {type(e).__name__}: {e}")
            continue

        classifications = _summarize_classifications(tool_input)
        all_classifications.append(classifications)
        all_elapsed.append(elapsed)
        total_input += usage["input_tokens"]
        total_output += usage["output_tokens"]

        print(f"--- run {i} ({elapsed:.1f}s, in={usage['input_tokens']} out={usage['output_tokens']}) ---")
        for label, cls in classifications.items():
            print(f"  {cls:>10}  {label}")
        print()

    # Stability summary
    print("=" * 70)
    print("STABILITY SUMMARY")
    print("=" * 70)
    if not all_classifications:
        print("No successful runs.")
        return

    by_disposition: dict[str, list[str]] = {}
    for run in all_classifications:
        for label, cls in run.items():
            by_disposition.setdefault(label, []).append(cls)

    stable_count = 0
    for label, classes in by_disposition.items():
        unique = set(classes)
        if len(unique) == 1:
            stable_count += 1
            print(f"  STABLE   {label}: all {len(classes)} → {classes[0]}")
        else:
            counter = Counter(classes)
            print(f"  UNSTABLE {label}: {dict(counter)}")

    print()
    print(f"Stable dispositions: {stable_count}/{len(by_disposition)}")
    # Identical-run count: how many runs produced byte-identical class maps
    if len(all_classifications) > 1:
        signatures = [
            tuple(sorted(c.items())) for c in all_classifications
        ]
        sig_counts = Counter(signatures)
        most_common_sig, most_common_count = sig_counts.most_common(1)[0]
        print(f"Most-common classification signature: {most_common_count}/{len(all_classifications)} runs")
        if len(sig_counts) > 1:
            print(f"Distinct signatures seen: {len(sig_counts)}")

    # Cost: Opus 4.7 pricing input $15/MTok, output $75/MTok (approx)
    cost = total_input / 1_000_000 * 15 + total_output / 1_000_000 * 75
    print(f"\nCost: ~${cost:.3f} for {len(all_classifications)} successful runs")
    print(f"Latency p50: {sorted(all_elapsed)[len(all_elapsed)//2]:.1f}s  (range {min(all_elapsed):.1f}-{max(all_elapsed):.1f}s)")


if __name__ == "__main__":
    main()
