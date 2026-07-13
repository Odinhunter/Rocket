"""Offline test: the v3 two-call signal parsers (docs/v3_protocol.md §2, §3).

The in-feed `action` is parsed from Call A (encoding); the follow-through
`next_step` from Call B (reflection). parse_behavioral_signal assembles both
and degrades to None (never raises) if EITHER is missing or malformed. Probes
are parsed off the same Call B terminal JSON. Enum membership is the LOUD
backstop against a stale/removed literal matching silently. No API calls.

Run: python tests/test_runtime_r7_parse.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.runtime import (
    parse_behavioral_signal,
    parse_encounter_action,
    parse_probe_signal,
    parse_reflection_obj,
)
from agent.schema import AgentTranscript, ProbeSignal

_ENC = (
    "R1 GUT: bold pack.\n\nR2 COMPREHENSION: whey isolate, for lifters.\n\n"
    "R3 EMOTION: mild interest.\n\n"
    'ACTION: {"action": "tap_cta", "reasoning": "the ₹1,199 deal price is a concrete hook"}'
)
_REF = (
    "R4 STICKINESS: the price stuck.\n\nR5 SOCIAL: wouldn't share.\n\n"
    "R6 FRICTION: the asterisk on the discount.\n\n"
    'NEXT_STEP: {"next_step": "buy_now", "reasoning": "cheap enough to just order"}'
)


def test_clean_signal() -> None:
    sig = parse_behavioral_signal(_ENC, _REF)
    assert sig is not None
    assert sig.action == "tap_cta"
    assert "1,199" in sig.action_reasoning
    assert sig.next_step == "buy_now"
    assert "order" in sig.next_step_reasoning
    print("  OK  clean two-call signal parses (action from A, next_step from B)")


def test_brace_bleed() -> None:
    """Prose braces earlier in a call must not capture — each parser takes the
    LAST valid {...} block whose key is in-enum."""
    enc = ('R2: the copy said {something} vague.\n\n'
           'ACTION: {"action": "scroll_past", "reasoning": "nothing held me"}')
    ref = ('R6: a {stray} brace.\n\n'
           'NEXT_STEP: {"next_step": "nothing", "reasoning": "not for me"}')
    sig = parse_behavioral_signal(enc, ref)
    assert sig is not None and sig.action == "scroll_past" and sig.next_step == "nothing"
    print("  OK  parsed despite stray braces in earlier prose")


def test_missing_action_returns_none() -> None:
    assert parse_behavioral_signal("R1 ... no action json here", _REF) is None
    print("  OK  missing Call A action -> None (no raise)")


def test_missing_next_step_returns_none() -> None:
    assert parse_behavioral_signal(_ENC, "R4 ... the model forgot the next_step") is None
    print("  OK  missing Call B next_step -> None (no raise)")


def test_bad_action_enum_returns_none() -> None:
    enc = 'ACTION: {"action": "buy_immediately", "reasoning": "x"}'
    assert parse_encounter_action(enc) is None
    assert parse_behavioral_signal(enc, _REF) is None
    print("  OK  out-of-enum action -> None (loud backstop)")


def test_bad_next_step_enum_returns_none() -> None:
    ref = 'NEXT_STEP: {"next_step": "maybe_later", "reasoning": "x"}'
    assert parse_reflection_obj(ref) is None
    assert parse_behavioral_signal(_ENC, ref) is None
    print("  OK  out-of-enum next_step -> None (loud backstop)")


def test_seek_info_no_longer_an_action() -> None:
    # the removed literal must NOT parse as an action (Catch 5: no silent match).
    enc = 'ACTION: {"action": "seek_info", "reasoning": "x"}'
    assert parse_encounter_action(enc) is None
    print("  OK  removed 'seek_info' action -> None (migrated to next_step)")


def test_malformed_json_returns_none() -> None:
    ref = 'NEXT_STEP: {"next_step": "buy_now", "reasoning": "unterminated'
    assert parse_behavioral_signal(_ENC, ref) is None
    print("  OK  malformed JSON -> None (no raise)")


# ---- conditional probes off the Call B terminal JSON ----

_REF_PROBED = (
    "R4 STICKINESS: the price stuck.\n\nR8 NEW-TO-YOU: didn't know they did isolate.\n\n"
    "R9 BRAND CHECK: pretty sure MuscleBlaze.\n\n"
    'NEXT_STEP: {"next_step": "buy_now", "reasoning": "hooked", '
    '"novelty": true, "brand_recall": "confident"}'
)


def test_probe_parses_from_terminal_json() -> None:
    ps = parse_probe_signal(_REF_PROBED)
    assert ps is not None and ps.novelty is True and ps.brand_recall == "confident"
    # the signal still parses cleanly alongside the probe keys.
    sig = parse_behavioral_signal(_ENC, _REF_PROBED)
    assert sig is not None and sig.next_step == "buy_now"
    print("  OK  probe parses from the same Call B JSON as next_step")


def test_probe_absent_is_none() -> None:
    assert parse_probe_signal(_REF) is None              # terminal JSON, no probe keys
    assert parse_probe_signal("R4 ... no json here") is None  # no terminal JSON
    print("  OK  no probe keys / no terminal JSON -> None")


def test_probe_bad_brand_recall_normalized() -> None:
    ref = ('NEXT_STEP: {"next_step": "nothing", "reasoning": "x", '
           '"novelty": "yes", "brand_recall": "maybe"}')
    ps = parse_probe_signal(ref)
    assert ps is not None and ps.novelty is True and ps.brand_recall == "none"
    print("  OK  bad brand_recall -> 'none'; truthy novelty coerced")


def test_probe_roundtrip_and_transcript() -> None:
    ps = ProbeSignal(novelty=True, brand_recall="unsure")
    assert ProbeSignal.from_dict(ps.to_dict()) == ps
    t = AgentTranscript(
        agent_id=1, disposition_label="d", context_label="c", seed_idx=0,
        encoding_text="e", reflection_text="r", probe_signal=ps,
    )
    back = AgentTranscript.from_dict(t.to_dict())
    assert back.probe_signal == ps
    print("  OK  ProbeSignal + AgentTranscript round-trip")


def main() -> None:
    print("=== v3 two-call signal parser smoke ===")
    test_clean_signal()
    test_brace_bleed()
    test_missing_action_returns_none()
    test_missing_next_step_returns_none()
    test_bad_action_enum_returns_none()
    test_bad_next_step_enum_returns_none()
    test_seek_info_no_longer_an_action()
    test_malformed_json_returns_none()
    test_probe_parses_from_terminal_json()
    test_probe_absent_is_none()
    test_probe_bad_brand_recall_normalized()
    test_probe_roundtrip_and_transcript()
    print("PASS — v3 parsers robust; degrade cleanly; probes confined + legacy-safe.")


if __name__ == "__main__":
    main()
