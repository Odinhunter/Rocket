"""Offline guard: the frozen v3 reaction surface (docs/v3_protocol.md §2, §10).

This is the structural companion to test_reflection_prompt.py (which owns the
Call-B conditional-probe assembly). Here we pin the invariants that must hold
for BOTH calls of the two-call reaction, and that Week-3 wording arms
(reaction-v3-rc{n}) must NOT be allowed to break silently:

  1. REACTION_PROTOCOL_VERSION is the pinned surface tag — a deliberate-bump
     tripwire, and it must actually LAND in run.json (that stamp test lives in
     test_report_assembly; this file guards the constant).
  2. Call A (encoding) emits a terminal `action` JSON; Call B a terminal
     `next_step` JSON — neither leaks the other's key, and neither leaks a probe.
  3. THE HIGH-VALUE GUARD — prompt <-> parser enum consistency. The action /
     next_step enums ADVERTISED in the prompt must exactly equal the enums the
     PARSER accepts (agent.schema). A drift either way is silent: a prompt enum
     the parser rejects loses signals; a parser enum the prompt never offers is
     dead. This is the Catch-5 failure class the whole v3 plan warns about.

We deliberately do NOT byte-golden the wording: §10 says wording is A/B-able
(the -rc{n} arms), so a byte-exact pin would false-fail on every legitimate arm.
Structure + enums + version is the real frozen surface.

No API calls. Run: python tests/test_reaction_surface.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.runtime import (
    REACTION_PROTOCOL_VERSION,
    _ENCODING_USER,
    _NEXT_STEP_CORE,
    _reflection_user_for,
)
from agent.schema import _VALID_BEHAVIORAL_ACTIONS, _VALID_NEXT_STEPS

# Probe wording that must NEVER appear on a Call-A prompt or a core-job Call-B
# prompt (the conditional-probe contamination guard — cf. test_reflection_prompt).
_PROBE_MARKERS = ("NEW-TO-YOU", "BRAND CHECK", "novelty", "brand_recall")


def _enum_options(prompt: str, key: str) -> set[str]:
    """Extract the `<a|b|c>` option set advertised for `key` in a prompt's
    terminal JSON. Anchored to the key so a stray <...> elsewhere can't capture
    the wrong group."""
    m = re.search(rf'"{re.escape(key)}":\s*"<([^>]+)>"', prompt)
    assert m is not None, f"no {key!r} enum group found in prompt"
    return {tok.strip() for tok in m.group(1).split("|")}


def test_reaction_protocol_version_pinned() -> None:
    # A deliberate-bump tripwire: the surface tag changes only on purpose (a
    # structural change, or a -rc{n} Week-3 arm), never by accident.
    assert REACTION_PROTOCOL_VERSION == "reaction-v3", REACTION_PROTOCOL_VERSION
    print("  OK  REACTION_PROTOCOL_VERSION pinned to reaction-v3")


def test_call_a_is_a_terminal_action_json() -> None:
    got = _ENCODING_USER
    # The three encoding sections + the terminal action line.
    for section in ("R1 GUT", "R2 COMPREHENSION", "R3 INTEREST"):
        assert section in got, f"Call A missing {section}"
    assert '"action":' in got and '"reasoning":' in got
    # Call A carries the action, NOT the next_step (that is Call B).
    assert '"next_step":' not in got, "next_step leaked into Call A"
    # No probe ever rides on the glance.
    for marker in _PROBE_MARKERS:
        assert marker not in got, f"probe marker {marker!r} leaked into Call A"
    print("  OK  Call A = R1-R3 + a terminal action JSON, no next_step / no probe")


def test_call_b_is_a_terminal_next_step_json() -> None:
    # The core (probe-free) reflection carries next_step, never an action key.
    got = _reflection_user_for("direct_sell")
    assert '"next_step":' in got
    assert '"action":' not in got, "action key leaked into Call B"
    print("  OK  Call B core = a terminal next_step JSON, no action key")


def test_action_enums_match_parser_both_directions() -> None:
    advertised = _enum_options(_ENCODING_USER, "action")
    assert advertised == _VALID_BEHAVIORAL_ACTIONS, (
        "Call-A action enums drifted from the parser's accepted set:\n"
        f"  prompt offers : {sorted(advertised)}\n"
        f"  parser accepts: {sorted(_VALID_BEHAVIORAL_ACTIONS)}\n"
        "A prompt-only enum silently loses signals; a parser-only enum is dead."
    )
    print(f"  OK  Call-A action enums == parser set ({len(advertised)} actions)")


def test_next_step_enums_match_parser_both_directions() -> None:
    advertised = _enum_options(_NEXT_STEP_CORE, "next_step")
    assert advertised == _VALID_NEXT_STEPS, (
        "Call-B next_step enums drifted from the parser's accepted set:\n"
        f"  prompt offers : {sorted(advertised)}\n"
        f"  parser accepts: {sorted(_VALID_NEXT_STEPS)}"
    )
    print(f"  OK  Call-B next_step enums == parser set ({len(advertised)} steps)")


def main() -> None:
    print("=== frozen v3 reaction surface (§2, §10) ===")
    test_reaction_protocol_version_pinned()
    test_call_a_is_a_terminal_action_json()
    test_call_b_is_a_terminal_next_step_json()
    test_action_enums_match_parser_both_directions()
    test_next_step_enums_match_parser_both_directions()
    print("PASS — version pinned, two calls separated, prompt<->parser enums consistent.")


if __name__ == "__main__":
    main()
