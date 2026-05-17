"""Phase 3 offline test: parse_r7_signal extracts the R7 behavioral signal
from a reflection transcript, and degrades to None (never raises) on
missing or malformed R7. No API calls.

Run: python tests/test_runtime_r7_parse.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.runtime import parse_r7_signal


def test_clean_r7() -> None:
    text = (
        "R4 STICKINESS: the price stuck.\n\n"
        "R5 SOCIAL: wouldn't share.\n\n"
        "R6 FRICTION: the asterisk on the discount.\n\n"
        'R7 ACTION: {"action": "tap_cta", "reasoning": "the ₹1,199 deal '
        'price is a concrete hook", "would_act_within_week": true}'
    )
    sig = parse_r7_signal(text)
    assert sig is not None
    assert sig.action == "tap_cta"
    assert sig.would_act_within_week is True
    assert "1,199" in sig.reasoning
    print("  OK  clean R7 line parses")


def test_r7_with_brace_bleed_in_r6() -> None:
    """R6 prose mentions a brace; the parser must still pick the real R7
    JSON (the LAST valid {...} block), not the stray one."""
    text = (
        "R6 FRICTION: the copy said {something} vague.\n\n"
        'R7 ACTION: {"action": "scroll_past", "reasoning": "nothing held '
        'me", "would_act_within_week": false}'
    )
    sig = parse_r7_signal(text)
    assert sig is not None and sig.action == "scroll_past"
    assert sig.would_act_within_week is False
    print("  OK  R7 parsed despite a stray brace in R6 prose")


def test_string_bool_tolerated() -> None:
    text = 'R7 ACTION: {"action": "save", "reasoning": "x", "would_act_within_week": "true"}'
    sig = parse_r7_signal(text)
    assert sig is not None and sig.would_act_within_week is True
    print("  OK  string 'true'/'false' tolerated for would_act_within_week")


def test_missing_r7_returns_none() -> None:
    text = "R4 ...\n\nR5 ...\n\nR6 ... (the model forgot R7 entirely)"
    assert parse_r7_signal(text) is None
    print("  OK  missing R7 -> None (no raise)")


def test_malformed_json_returns_none() -> None:
    text = 'R7 ACTION: {"action": "tap_cta", "reasoning": "unterminated'
    assert parse_r7_signal(text) is None
    print("  OK  malformed R7 JSON -> None (no raise)")


def test_bad_action_enum_returns_none() -> None:
    text = 'R7 ACTION: {"action": "buy_immediately", "reasoning": "x", "would_act_within_week": true}'
    assert parse_r7_signal(text) is None
    print("  OK  R7 with an out-of-enum action -> None")


def test_bad_would_act_returns_none() -> None:
    text = 'R7 ACTION: {"action": "linger", "reasoning": "x", "would_act_within_week": "maybe"}'
    assert parse_r7_signal(text) is None
    print("  OK  R7 with an unparseable would_act_within_week -> None")


def main() -> None:
    print("=== runtime R7 parser smoke ===")
    test_clean_r7()
    test_r7_with_brace_bleed_in_r6()
    test_string_bool_tolerated()
    test_missing_r7_returns_none()
    test_malformed_json_returns_none()
    test_bad_action_enum_returns_none()
    test_bad_would_act_returns_none()
    print("PASS — R7 parser is robust and degrades cleanly.")


if __name__ == "__main__":
    main()
