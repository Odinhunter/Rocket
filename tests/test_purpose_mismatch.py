"""Offline test: the v2.4 declared-vs-apparent purpose mismatch guard.

Pins detect_purpose_mismatch — the load-bearing guardrail for the common case
(a default-purpose run of an off-job ad). Warn-not-block, conservative on
'unclear', with the direction-of-error note that direct-sell (the default)
understates a softer job. Also pins TargetClassification round-trips the new
inferred_purpose field legacy-safe. No API calls.

Run: python tests/test_purpose_mismatch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.synthesis_types import TargetClassification
from agent.target_id import detect_purpose_mismatch


def test_default_vs_awareness_fires_and_understates() -> None:
    # THE case v2.4 exists to catch: marketer leaves purpose on the default
    # (direct-sell), the ad is actually an awareness/informer ad.
    m = detect_purpose_mismatch("direct_sell", "awareness_informer",
                                "no CTA, shows the whole range, educational tone")
    assert m is not None
    assert m.declared_purpose == "direct_sell"
    assert m.apparent_purpose == "awareness_informer"
    assert m.suggested_flag == "--purpose awareness_informer"
    # the message must carry the understate direction + the re-grade path + the
    # apparent-purpose reasoning (surface the read, not just warn).
    assert "UNDERSTATE" in m.message
    assert "--purpose awareness_informer" in m.message
    assert "educational tone" in m.message
    print("  OK  default direct-sell vs apparent awareness → fires + understate note")


def test_unclear_never_fires() -> None:
    assert detect_purpose_mismatch("direct_sell", "unclear") is None
    assert detect_purpose_mismatch("direct_sell", "") is None
    assert detect_purpose_mismatch("cold_hook", "unclear") is None
    print("  OK  'unclear'/empty apparent purpose never fires (conservative)")


def test_match_never_fires() -> None:
    for p in ("direct_sell", "cold_hook", "brand_building", "awareness_informer"):
        assert detect_purpose_mismatch(p, p) is None, p
    print("  OK  apparent == declared → no mismatch")


def test_non_default_declared_generic_note() -> None:
    # declared a non-default job, apparent differs → fires with the generic
    # (non-understate) framing since the ruler asymmetry isn't direct-sell's.
    m = detect_purpose_mismatch("brand_building", "direct_sell")
    assert m is not None
    assert "UNDERSTATE" not in m.message
    assert "different rulers" in m.message
    assert m.suggested_flag == "--purpose direct_sell"
    print("  OK  non-default declared vs apparent → fires with generic ruler note")


def test_target_classification_purpose_roundtrip_legacy_safe() -> None:
    tc = TargetClassification(
        inferred_target_description="d", target_reasoning="r",
        disposition_classifications=[], inferred_purpose="cold_hook",
        purpose_reasoning="hooky teaser",
    )
    back = TargetClassification.from_dict(tc.to_dict())
    assert back.inferred_purpose == "cold_hook"
    assert back.purpose_reasoning == "hooky teaser"
    # a pre-v2.4 artifact (no purpose keys) loads → 'unclear', no crash.
    legacy = TargetClassification.from_dict({
        "inferred_target_description": "d", "target_reasoning": "r",
        "disposition_classifications": [],
    })
    assert legacy.inferred_purpose == "unclear"
    assert legacy.purpose_reasoning == ""
    print("  OK  TargetClassification inferred_purpose round-trips + legacy-safe")


def main() -> None:
    print("=== purpose mismatch guard (v2.4) ===")
    test_default_vs_awareness_fires_and_understates()
    test_unclear_never_fires()
    test_match_never_fires()
    test_non_default_declared_generic_note()
    test_target_classification_purpose_roundtrip_legacy_safe()
    print("PASS — purpose mismatch guard fires where it must, stays quiet elsewhere.")


if __name__ == "__main__":
    main()
