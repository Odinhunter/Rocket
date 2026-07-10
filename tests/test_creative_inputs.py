"""Offline test: CreativeInputs + the agent copy-feed block.

Pins that (a) RunConfig.provided_inputs() maps copy→"ad_copy", offer→"offer",
(b) the runtime copy block renders the provided copy/offer (so it reaches the
agent's reaction — the price-feed fix), and (c) an empty CreativeInputs yields
an empty block (image-only runs are prompt-unchanged). No API calls.

Run: python tests/test_creative_inputs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import AssetSpec, CreativeInputs, RunConfig
from agent.runtime import _creative_copy_block


def test_provided_inputs_mapping() -> None:
    assert CreativeInputs().has_ad_copy() is False
    assert CreativeInputs(headline="Buy now").has_ad_copy() is True
    assert CreativeInputs(primary_text="body only").has_ad_copy() is True
    assert CreativeInputs(offer="₹2,699").has_offer() is True
    # whitespace-only does not count
    assert CreativeInputs(offer="   ").has_offer() is False

    # RunConfig.provided_inputs() maps to the gating keys L3.5 reads.
    def _cfg(ci: CreativeInputs) -> RunConfig:
        return RunConfig(asset=AssetSpec("x.png", "x"), archetype="unspecified",
                         category="c", creative_inputs=ci)
    assert _cfg(CreativeInputs()).provided_inputs() == []
    assert _cfg(CreativeInputs(headline="h")).provided_inputs() == ["ad_copy"]
    assert _cfg(CreativeInputs(offer="₹9")).provided_inputs() == ["offer"]
    assert _cfg(CreativeInputs(headline="h", offer="₹9")).provided_inputs() == ["ad_copy", "offer"]
    print("  OK  has_ad_copy / has_offer + RunConfig.provided_inputs() mapping")


def test_copy_block_contains_provided_text() -> None:
    ci = CreativeInputs(
        headline="AI-designed protein",
        primary_text="Clinically inspired, backed by science.",
        offer="₹2,699, 20% off first order",
    )
    block = _creative_copy_block(ci)
    assert "AD COPY & OFFER" in block
    assert "AI-designed protein" in block
    assert "Clinically inspired" in block
    assert "₹2,699" in block  # the price reaches the agent — the gap we fixed
    # Offer-only still renders (price gating depends on this).
    assert "₹99" in _creative_copy_block(CreativeInputs(offer="₹99"))
    print("  OK  copy block carries headline / body / offer (incl. the price)")


def test_empty_copy_block_is_blank() -> None:
    assert _creative_copy_block(CreativeInputs()) == ""
    assert _creative_copy_block(CreativeInputs(headline="   ")) == ""
    print("  OK  empty CreativeInputs → empty block (image-only runs unchanged)")


def test_purpose_field_roundtrip_and_default() -> None:
    # v2.4: default is direct-sell (= v2.3 behaviour, D2C ICP common case).
    assert CreativeInputs().purpose == "direct_sell"
    # explicit purpose survives to_dict/from_dict.
    ci = CreativeInputs(purpose="cold_hook")
    assert CreativeInputs.from_dict(ci.to_dict()).purpose == "cold_hook"
    # legacy artifacts (no "purpose" key) resolve to the default → old runs
    # round-trip unchanged.
    assert CreativeInputs.from_dict({"primary_text": "x"}).purpose == "direct_sell"
    assert CreativeInputs.from_dict({"purpose": None}).purpose == "direct_sell"
    # a typo'd purpose fails loud rather than silently scoring on a wrong ruler.
    try:
        CreativeInputs(purpose="conversion")  # not a valid job name
        raise AssertionError("bogus purpose should raise")
    except ValueError:
        pass
    print("  OK  purpose field: default direct_sell, roundtrip, legacy-safe, typo-guarded")


def main() -> None:
    print("=== creative inputs + agent copy feed ===")
    test_provided_inputs_mapping()
    test_copy_block_contains_provided_text()
    test_empty_copy_block_is_blank()
    test_purpose_field_roundtrip_and_default()
    print("PASS — creative copy/offer reach the agent payload.")


if __name__ == "__main__":
    main()
