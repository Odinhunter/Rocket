"""Offline guard: the purpose-conditional Call B (reflection) prompt (v3).

Retires the v2.3 byte-identity (v3 emits `next_step`, not an R7 action). Pins
the v3 assembly: the three would-act/action jobs (direct-sell, cold-hook,
retain) get a probe-FREE reflection; informer adds ONLY novelty; brand-building
adds ONLY brand_recall — the conditional-probe rule that prevents the
68->26 contamination (docs/v3_protocol.md §2.2). Byte-identity is asserted
against the runtime's own assembled constants (no hand-transcription), so any
drift in _reflection_user_for's assembly or a probe leaking into a core job
fails here. The reaction-surface VERSION pin + the Call-A guard land in W1·E2.
No API calls.

Run: python tests/test_reflection_prompt.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.runtime import (
    _NEXT_STEP_CORE,
    _NEXT_STEP_HEAD,
    _NEXT_STEP_NOTE,
    _REFLECTION_BASE,
    _reflection_user_for,
)

# The probe-free v3 core-three prompt, assembled from the frozen pieces. This
# pins the ASSEMBLY (what drifts) exactly, without a hand-typed golden.
_V3_CORE = _REFLECTION_BASE + _NEXT_STEP_HEAD + _NEXT_STEP_CORE + "}\n" + _NEXT_STEP_NOTE


def test_core_jobs_get_the_probe_free_prompt() -> None:
    for purpose in ("direct_sell", "cold_hook", "retain_winback"):
        got = _reflection_user_for(purpose)
        assert got == _V3_CORE, f"{purpose}: reflection prompt drifted"
        # contamination-free: no probe ever mentioned to a would-act/action job.
        assert "novelty" not in got and "brand_recall" not in got
        assert "NEW-TO-YOU" not in got and "BRAND CHECK" not in got
    print("  OK  direct-sell / cold-hook / retain == the probe-free v3 prompt")


def test_terminal_is_next_step_not_r7() -> None:
    # v3: the terminal JSON emits next_step; the old R7 action / would_act keys
    # are gone from the reflection prompt (action moved to Call A).
    got = _reflection_user_for("direct_sell")
    assert '"next_step":' in got
    assert '"would_act_within_week"' not in got
    assert "R7 ACTION" not in got
    print("  OK  terminal reflection JSON is next_step (R7/would_act retired)")


def test_informer_adds_only_novelty() -> None:
    got = _reflection_user_for("awareness_informer")
    assert "R8 NEW-TO-YOU" in got and '"novelty": <true|false>' in got
    assert "R9 BRAND CHECK" not in got and "brand_recall" not in got
    print("  OK  informer adds ONLY the novelty probe")


def test_brand_building_adds_only_brand_recall() -> None:
    got = _reflection_user_for("brand_building")
    assert "R9 BRAND CHECK" in got and '"brand_recall": "<confident|unsure|none>"' in got
    assert "R8 NEW-TO-YOU" not in got and "novelty" not in got
    print("  OK  brand-building adds ONLY the brand_recall probe")


def test_probe_prompts_keep_one_terminal_json() -> None:
    # the probe versions fold their field into the single terminal next_step
    # object (parse relies on the last {...}); still exactly one next_step key.
    for purpose in ("awareness_informer", "brand_building"):
        got = _reflection_user_for(purpose)
        assert got.count('"next_step":') == 1
        assert got.rstrip().count("}") == 1
    print("  OK  probe prompts keep a single terminal next_step JSON object")


def main() -> None:
    print("=== purpose-conditional v3 reflection prompt ===")
    test_core_jobs_get_the_probe_free_prompt()
    test_terminal_is_next_step_not_r7()
    test_informer_adds_only_novelty()
    test_brand_building_adds_only_brand_recall()
    test_probe_prompts_keep_one_terminal_json()
    print("PASS — core jobs on the probe-free v3 prompt; probes confined to their purpose.")


if __name__ == "__main__":
    main()
