"""Phase 1 offline test: the render cache key is stable and sensitive, the
cache store/load round-trips, compose_persona_prompt assembles correctly,
and the artifact-integrity check flags an invented brand.

No API calls — exercises only the pure helpers in agent/render.py.
Run: python tests/test_render_cache.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack
from agent.render import (
    _cache_load,
    _cache_store,
    _validate_no_invented_artifacts,
    compose_persona_prompt,
    context_render_hash,
    count_pack_artifacts_used,
    persona_core_hash,
)
from agent.vectors import (
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
)

_TMP = Path("runs/_test_render_cache")


def _demo() -> DemographicPoint:
    return DemographicPoint(
        gender="male", age_band="25_34", income_tier="upper_mid",
        geography="Bangalore / metro tier-1",
    )


def _disposition() -> DispositionVector:
    return DispositionVector(
        category_relationship="regular", brand_stance="skeptical",
        price_orientation="value_calculator", decision_driver="function",
        category_involvement="high", prior_experience_valence="mixed",
        channel_behavior="quick_commerce", life_stage="early_career",
    )


def _chaos() -> ChaosVector:
    return ChaosVector(
        decision_velocity="impulsive", suggestibility="high",
        consistency="erratic", risk_tolerance="seeking",
    )


def _context() -> ContextVector:
    return ContextVector(
        attention_level="low", device_posture="commute",
        intent_state="killing_time", energy_state="drained",
        social_setting="public",
    )


def test_persona_core_hash_stable() -> None:
    h1 = persona_core_hash(_demo(), _disposition(), _chaos(), "coffee")
    h2 = persona_core_hash(_demo(), _disposition(), _chaos(), "coffee")
    assert h1 == h2, "persona_core_hash not stable for identical inputs"
    print("  OK  persona_core_hash is stable for identical vectors")


def test_persona_core_hash_sensitive() -> None:
    base = persona_core_hash(_demo(), _disposition(), _chaos(), "coffee")
    # Change one disposition field.
    d2 = _disposition()
    d2.brand_stance = "loyalist"
    assert persona_core_hash(_demo(), d2, _chaos(), "coffee") != base, (
        "hash did not change on a disposition field change"
    )
    # Change one chaos field.
    c2 = _chaos()
    c2.decision_velocity = "deliberate"
    assert persona_core_hash(_demo(), _disposition(), c2, "coffee") != base, (
        "hash did not change on a chaos field change"
    )
    # Change category.
    assert persona_core_hash(_demo(), _disposition(), _chaos(), "chocolate") != base, (
        "hash did not change on a category change"
    )
    # Change a demographic field.
    dm2 = _demo()
    dm2.age_band = "35_44"
    assert persona_core_hash(dm2, _disposition(), _chaos(), "coffee") != base, (
        "hash did not change on a demographic field change"
    )
    # Change the anchor.
    assert persona_core_hash(
        _demo(), _disposition(), _chaos(), "coffee", "traditional filter coffee"
    ) != base, "hash did not change on an anchor change"
    print("  OK  persona_core_hash changes on any vector / anchor / category change")


def test_context_render_hash_sensitive() -> None:
    base = context_render_hash(_context(), "coffee")
    c2 = _context()
    c2.attention_level = "high"
    assert context_render_hash(c2, "coffee") != base
    assert context_render_hash(_context(), "wellness") != base
    print("  OK  context_render_hash changes on any context / category change")


def test_cache_roundtrip() -> None:
    if _TMP.exists():
        shutil.rmtree(_TMP)
    try:
        key = persona_core_hash(_demo(), _disposition(), _chaos(), "coffee")
        assert _cache_load(_TMP, key) is None, "cache hit on an empty dir"
        _cache_store(_TMP, key, "rendered persona prose here", kind="persona_core")
        assert _cache_load(_TMP, key) == "rendered persona prose here", (
            "cache load did not return the stored prose"
        )
        # A different key is still a miss.
        assert _cache_load(_TMP, "deadbeef") is None
        # cache_dir=None is always a no-op miss.
        assert _cache_load(None, key) is None
        print("  OK  render cache store/load round-trips; cache_dir=None is a no-op")
    finally:
        if _TMP.exists():
            shutil.rmtree(_TMP)


def test_compose_persona_prompt() -> None:
    prompt = compose_persona_prompt("CORE PROSE", "CONTEXT PROSE")
    assert "CORE PROSE" in prompt and "CONTEXT PROSE" in prompt
    assert prompt.index("CORE PROSE") < prompt.index("CONTEXT PROSE"), (
        "context must come after the persona core"
    )
    assert "Attention gates everything" in prompt
    print("  OK  compose_persona_prompt assembles core + context in order")


def test_validate_no_invented_artifacts() -> None:
    pack = load_pack("coffee")
    # Clean prose: uses only pack brands.
    clean = (
        "He drinks Blue Tokai cold brew at the cafe twice a week and keeps a "
        "Bru jar at home for his parents. He price-checks against Nescafe."
    )
    warnings = _validate_no_invented_artifacts(clean, pack)
    assert warnings == [], f"clean prose flagged: {warnings}"
    # Dirty prose: invents a brand not in the coffee pack.
    dirty = clean + " He recently tried Starbucks Verismo pods from Zarafshan Roasters."
    warnings = _validate_no_invented_artifacts(dirty, pack)
    assert any("Zarafshan" in w for w in warnings), (
        f"invented brand 'Zarafshan' not flagged; warnings={warnings}"
    )
    print("  OK  _validate_no_invented_artifacts: clean passes, invented brand flagged")


def test_count_pack_artifacts_used() -> None:
    pack = load_pack("coffee")
    prose = "He drinks Blue Tokai and keeps Bru at home; Nescafe at the office."
    n = count_pack_artifacts_used(prose, pack)
    assert n >= 3, f"expected >=3 pack brands counted, got {n}"
    assert count_pack_artifacts_used("no brands here at all", pack) == 0
    print(f"  OK  count_pack_artifacts_used counts pack brands ({n} in fixture prose)")


def main() -> None:
    print("=== render cache + helpers smoke ===")
    test_persona_core_hash_stable()
    test_persona_core_hash_sensitive()
    test_context_render_hash_sensitive()
    test_cache_roundtrip()
    test_compose_persona_prompt()
    test_validate_no_invented_artifacts()
    test_count_pack_artifacts_used()
    print("PASS — render cache key, store/load, compose, and integrity check.")


if __name__ == "__main__":
    main()
