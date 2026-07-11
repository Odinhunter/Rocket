"""Offline test: the purpose-conditional reflection prompt (v2.4 P8).

THE $0 re-validation. A paid anchor run (2026-07-11) proved that asking the R8
novelty probe before R7 contaminates purchase intent — within-target would_act
fell 68% -> 26% on the same MB ad, actions unchanged. The fix: ask a probe ONLY
on the purpose that reads it. This test is the guarantee that the three
would_act/action jobs (direct-sell, cold-hook, retain) run a reflection prompt
BYTE-IDENTICAL to the validated v2.3 prompt — so they are re-validated here for
$0, not with another paid run. No API calls.

Run: python tests/test_reflection_prompt.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.runtime import _reflection_user_for

# The exact v2.3 reflection prompt that produced the validated anchors (68% MB,
# etc.) — the golden string the core three MUST reproduce byte-for-byte.
_V23_REFLECTION = (
    "REFLECTION PHASE — a day or two later, still a real person, still "
    "plain and short. Keep every section to 1-2 sentences. If an ad left "
    "almost nothing behind, say so plainly — don't manufacture depth.\n\n"
    "R4 STICKINESS: 1-2 sentences. What, if anything, stuck.\n\n"
    "R5 SOCIAL: 1-2 sentences. Would you share or mention it, and why or "
    "why not?\n\n"
    "R6 FRICTION: 1-2 sentences. If you'd consider buying, the one thing "
    "that stops you. If the ad isn't aimed at someone like you, that's a "
    "fine reason — one factor, not a lecture.\n\n"
    "R7 ACTION: emit exactly ONE line of JSON and nothing after it:\n"
    '{"action": "<scroll_past|linger|tap_cta|save|share|seek_info>", '
    '"reasoning": "<one short in-character sentence, anchored to the '
    'creative>", "would_act_within_week": <true|false>}\n'
    "What you would actually DO. Never a funnel rate or percentage."
)


def test_core_jobs_get_the_validated_probe_free_prompt() -> None:
    for purpose in ("direct_sell", "cold_hook", "retain_winback"):
        got = _reflection_user_for(purpose)
        assert got == _V23_REFLECTION, f"{purpose}: reflection prompt drifted from v2.3"
        # contamination-free: no probe ever mentioned to a would_act/action job.
        assert "novelty" not in got and "brand_recall" not in got
        assert "NEW-TO-YOU" not in got and "BRAND CHECK" not in got
    print("  OK  direct-sell / cold-hook / retain == the byte-identical v2.3 prompt")


def test_informer_adds_only_novelty() -> None:
    got = _reflection_user_for("awareness_informer")
    assert "R8 NEW-TO-YOU" in got and '"novelty": <true|false>' in got
    # informer never asks the brand-attribution probe.
    assert "R9 BRAND CHECK" not in got and "brand_recall" not in got
    print("  OK  informer adds ONLY the novelty probe (not brand_recall)")


def test_brand_building_adds_only_brand_recall() -> None:
    got = _reflection_user_for("brand_building")
    assert "R9 BRAND CHECK" in got and '"brand_recall": "<confident|unsure|none>"' in got
    # brand-building never asks the novelty probe.
    assert "R8 NEW-TO-YOU" not in got and "novelty" not in got
    print("  OK  brand-building adds ONLY the brand_recall probe (not novelty)")


def test_probe_prompts_still_end_in_one_json_line() -> None:
    # the probe versions keep R7 as a single terminal JSON object (parse relies
    # on the last {...}); just with the extra field folded in.
    for purpose in ("awareness_informer", "brand_building"):
        got = _reflection_user_for(purpose)
        assert got.count('"action":') == 1
        assert got.rstrip().count("}") == 1
    print("  OK  probe prompts keep a single terminal R7 JSON object")


def main() -> None:
    print("=== purpose-conditional reflection prompt (v2.4 P8) ===")
    test_core_jobs_get_the_validated_probe_free_prompt()
    test_informer_adds_only_novelty()
    test_brand_building_adds_only_brand_recall()
    test_probe_prompts_still_end_in_one_json_line()
    print("PASS — core jobs on the validated prompt; probes confined to their purpose.")


if __name__ == "__main__":
    main()
