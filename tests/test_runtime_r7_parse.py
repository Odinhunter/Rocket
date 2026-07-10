"""Phase 3 offline test: parse_r7_signal extracts the R7 behavioral signal
from a reflection transcript, and degrades to None (never raises) on
missing or malformed R7. No API calls.

Run: python tests/test_runtime_r7_parse.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.runtime import parse_probe_signal, parse_r7_signal
from agent.schema import AgentTranscript, ProbeSignal


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


# ---- v2.4: R8/R9 probe parsing off the same terminal JSON ----

_PROBED = (
    "R4 STICKINESS: the price stuck.\n\n"
    "R8 NEW-TO-YOU: didn't know they did whey isolate.\n\n"
    "R9 BRAND CHECK: pretty sure it was MuscleBlaze.\n\n"
    'R7 ACTION: {"action": "tap_cta", "reasoning": "the deal price hooked me", '
    '"would_act_within_week": true, "novelty": true, "brand_recall": "confident"}'
)


def test_probe_parses_from_terminal_json() -> None:
    ps = parse_probe_signal(_PROBED)
    assert ps is not None
    assert ps.novelty is True
    assert ps.brand_recall == "confident"
    # R7 still parses cleanly alongside the probe keys (ignores the extras).
    sig = parse_r7_signal(_PROBED)
    assert sig is not None and sig.action == "tap_cta" and sig.would_act_within_week is True
    print("  OK  probe (novelty/brand_recall) parses from the same JSON as R7")


def test_probe_absent_is_none_legacy_safe() -> None:
    # a pre-v2.4 terminal JSON has NO probe keys -> None (not a false default),
    # so old transcripts read as no-probe-signal.
    legacy = (
        'R7 ACTION: {"action": "linger", "reasoning": "x", '
        '"would_act_within_week": false}'
    )
    assert parse_probe_signal(legacy) is None
    # no terminal signal at all -> None
    assert parse_probe_signal("R4 ... no json here") is None
    print("  OK  no probe keys / no terminal JSON -> None (legacy-safe)")


def test_probe_bad_brand_recall_normalized() -> None:
    text = (
        'R7 ACTION: {"action": "save", "reasoning": "x", '
        '"would_act_within_week": false, "novelty": "yes", '
        '"brand_recall": "maybe"}'
    )
    ps = parse_probe_signal(text)
    # novelty coerces truthy; an out-of-enum brand_recall degrades to "none".
    assert ps is not None and ps.novelty is True and ps.brand_recall == "none"
    print("  OK  bad brand_recall -> 'none'; truthy novelty coerced")


def test_probe_signal_and_transcript_roundtrip() -> None:
    ps = ProbeSignal(novelty=True, brand_recall="unsure")
    assert ProbeSignal.from_dict(ps.to_dict()) == ps
    t = AgentTranscript(
        agent_id=1, disposition_label="d", context_label="c", seed_idx=0,
        encoding_text="e", reflection_text="r", probe_signal=ps,
    )
    back = AgentTranscript.from_dict(t.to_dict())
    assert back.probe_signal == ps
    # a legacy transcript dict without probe_signal loads to None.
    legacy = AgentTranscript.from_dict({
        "agent_id": 2, "disposition_label": "d", "context_label": "c",
        "seed_idx": 0, "encoding_text": "e", "reflection_text": "r",
        "behavioral_signal": None,
    })
    assert legacy.probe_signal is None
    print("  OK  ProbeSignal + AgentTranscript round-trip; legacy dict -> None")


def main() -> None:
    print("=== runtime R7 parser smoke ===")
    test_clean_r7()
    test_r7_with_brace_bleed_in_r6()
    test_string_bool_tolerated()
    test_missing_r7_returns_none()
    test_malformed_json_returns_none()
    test_bad_action_enum_returns_none()
    test_bad_would_act_returns_none()
    test_probe_parses_from_terminal_json()
    test_probe_absent_is_none_legacy_safe()
    test_probe_bad_brand_recall_normalized()
    test_probe_signal_and_transcript_roundtrip()
    print("PASS — R7 parser is robust and degrades cleanly; probes parse + legacy-safe.")


if __name__ == "__main__":
    main()
