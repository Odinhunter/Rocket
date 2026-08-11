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

import agent.render as render_mod
from agent.artifact_pack import load_pack
from agent.render import (
    RENDER_PROMPT_VERSION,
    _cache_load,
    _cache_store,
    _CONTEXT_SYSTEM,
    _PERSONA_SYSTEM,
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
    dm2.age_min, dm2.age_max = 35, 44
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


def test_prompt_version_invalidates_cache() -> None:
    """A render-prompt bump MUST change every persona_core_hash, or render-6
    cores would be served from the render-5 cache and the C1/C3 change would
    silently never reach the agents. This is what makes a bump safe."""
    base = persona_core_hash(_demo(), _disposition(), _chaos(), "coffee")
    original = render_mod.RENDER_PROMPT_VERSION
    try:
        render_mod.RENDER_PROMPT_VERSION = "render-not-a-real-version"
        assert persona_core_hash(_demo(), _disposition(), _chaos(), "coffee") != base, (
            "persona_core_hash ignored RENDER_PROMPT_VERSION — a prompt bump "
            "would reuse stale cached cores"
        )
    finally:
        render_mod.RENDER_PROMPT_VERSION = original
    assert persona_core_hash(_demo(), _disposition(), _chaos(), "coffee") == base
    print("  OK  a RENDER_PROMPT_VERSION bump invalidates cached persona cores")


def test_persona_system_render_6_contract() -> None:
    """render-6 = C1 + C3 (docs/v3_protocol.md §9). The persona core is the
    system block of every reaction call, so its register is what the agent
    inherits. Offline can only pin the CONTRACT — that the instructions are
    present. Whether the register actually lands is a LIVE check
    (test_render_smoke); whether it stays un-parroted is the 2-persona live
    check that gates this step).

    ⚠ The version is render-10, but every assertion below is still the render-6
    contract and must keep passing: render-7 (§2.6, income withheld from the
    persona writer) changed the USER PAYLOAD only, render-8 changed the
    ADDRESS of the rendered output (second person), and render-10 reworded the
    pack brief's brand/platform headers from a mandate to a landscape — none
    of them dropped a single register or anti-homogenization win. If a later
    bump ever makes one of these fail, that is a real regression, not a
    version-number chore.

    ⚠ One literal moved with render-8 and it is not cosmetic: the block is now
    `HOW YOU TALK`, because its caption is read by the person it describes.
    The UTTERANCES inside it are still first person — see
    `test_the_utterances_stay_first_person_while_the_frame_moved`."""
    assert RENDER_PROMPT_VERSION == "render-10", RENDER_PROMPT_VERSION

    # C3 — BOTH leaking registers are banned. NOTE: the banned analyst words
    # ("aspirational", "gateway brand", ...) appear in _PERSONA_SYSTEM ON
    # PURPOSE, as negative examples — so their absence can only be asserted of
    # the rendered OUTPUT (the live check), never of the instruction itself.
    assert "vivid" not in _PERSONA_SYSTEM.lower(), (
        "C3: 'vivid' still primes the literary register that leaks into "
        "every reaction"
    )
    assert "NOT literature" in _PERSONA_SYSTEM
    assert "NOT market research" in _PERSONA_SYSTEM, (
        "C3: the analyst register is the subtler leak — 'consumer research' "
        "as the render engine's own identity is what produced 'trading on "
        "the logo' out of a real person's 'paying for the logo'"
    )
    assert "downgrade analysis into speech" in _PERSONA_SYSTEM
    # The render-3 guard on the register ban itself: strip jargon, KEEP the
    # concrete specifics — plain must not decay into vague.
    assert "Plain is NOT vague" in _PERSONA_SYSTEM

    # C1 — the shown-register block, and the caption the AGENT reads.
    # ⚠ The full template line, not the bare label — "HOW YOU TALK" occurs
    # twice (heading + template) and a bare-label assertion goes vacuous.
    assert "HOW YOU TALK (register only" in _PERSONA_SYSTEM, (
        "render-8: the caption is read by the person it describes, so it is "
        "second person like every other agent-facing string"
    )
    assert "register only" in _PERSONA_SYSTEM
    assert "Never repeat these lines" in _PERSONA_SYSTEM, (
        "C1: the agent must be told the utterances are register, not a script"
    )

    # C1 guard — the planted-words seam. Cores are cached and replayed across
    # ads, so an utterance that is a verdict on a product becomes a scripted
    # answer. This is the guard 4cbcca9 established for R1-R6; it must hold
    # in the system block too.
    # ⚠ render-9 REPLACED the phrase "ad-agnostic" with an enumerated ban plus a
    # per-line final check — the soft one-liner was in place for render-8 and 2
    # of 6 rendered personas emitted an advertising utterance anyway. The guard
    # is STRONGER, not gone; the literal moved. Full pins live in
    # tests/test_second_person_address.py::
    # test_the_utterances_are_banned_from_mentioning_advertising.
    assert "NOTHING ABOUT ADVERTISING" in _PERSONA_SYSTEM, (
        "C1 guard: the planted-words seam. Cores are cached and replayed "
        "across ads, so an utterance about advertising is a pre-written "
        "stance toward the stimulus."
    )
    assert "anchored in something they DO" in _PERSONA_SYSTEM

    # render-3/4/5 wins must survive the rewrite (anti-homogenization).
    assert "SPINE" in _PERSONA_SYSTEM, "render-3 win lost"
    assert "HARD CONSTRAINT" in _PERSONA_SYSTEM, "render-4 anchor win lost"
    assert "Niche enthusiast communities" in _PERSONA_SYSTEM, "render-5 win lost"

    # Input-audit finding §3 — expertise gated to involvement (generalises the
    # render-5 community gate). The average buyer is NOT a category expert.
    assert "EXPERTISE SCALES WITH category_involvement" in _PERSONA_SYSTEM, (
        "the expertise gate is the fix for personas reading as product "
        "catalogues — a medium/low buyer must not know varietals/estates/V60"
    )
    print("  OK  _PERSONA_SYSTEM: render-6 C1+C3 + expertise gate, render-3/4/5 intact")


def test_render_7_withholds_income_from_the_persona_writer() -> None:
    """§2.6. SimBench measures a per-axis penalty for conditioning a simulated
    persona on a demographic axis: income −4.51, against age −1.50 and gender
    −1.24 (the safest two). Every persona we rendered carried an LPA band.

    ⚠ Three separate things have to be true at once, and each is a way this
    change could be real in one place and undone in another:
      1. the WRITER's payload carries no income;
      2. `DemographicPoint.to_dict()` still DOES — it is the serialization
         contract for panel.json, persona_core_hash and the from_dict round
         trip, so narrowing it would break panel selection and replay;
      3. income still KEYS the cache, so two people who differ only in what
         they earn cannot collapse onto one cached core."""
    demo = _demo()
    payload = render_mod._persona_user_payload(
        demo, _disposition(), _chaos(), load_pack("coffee")
    )

    # 1 — nothing income-shaped reaches the writer.
    for token in ("income", "lpa", "LPA"):
        assert token not in payload, (
            f"§2.6: {token!r} still reaches the persona writer:\n{payload[:400]}"
        )
    # ...while the axes SimBench found safest are untouched. Without this, a
    # redaction that stripped the whole demographic block would pass above.
    assert "gender" in payload and "age_min" in payload, (
        "§2.6 withholds INCOME only — age and gender are the two safest axes "
        "and removing them would be a different, unmeasured change"
    )

    # 2 — the serialization contract is intact.
    full = demo.to_dict()
    assert "income_lpa_min" in full and "income_lpa_max" in full, (
        "DemographicPoint.to_dict() must keep income: panel.json, "
        "persona_core_hash and every replay of a run on disk depend on it"
    )

    # 3 — income still keys the cache (over-keying is harmless; under-keying
    # would serve one core for two different people).
    poor = DemographicPoint(**{**full, "income_lpa_min": 2.0, "income_lpa_max": 5.0})
    rich = DemographicPoint(**{**full, "income_lpa_min": 60.0, "income_lpa_max": 90.0})
    assert (persona_core_hash(poor, _disposition(), _chaos(), "coffee")
            != persona_core_hash(rich, _disposition(), _chaos(), "coffee")), (
        "income dropped out of persona_core_hash — two different people would "
        "now share one cached persona core"
    )
    print("  OK  render-7 withholds income from the writer, keeps it for "
          "selection, replay and the cache key")


def test_context_system_de_literarised() -> None:
    """Input-audit finding 3.3 — the context block is read by the very person
    it describes, so its register imprints on the reaction the same way the
    core's does. It must not be literary either."""
    assert "NO literary phrasing" in _CONTEXT_SYSTEM
    assert "vivid" not in _CONTEXT_SYSTEM.lower(), (
        "'vivid' primes the literary register in the context prose"
    )
    print("  OK  _CONTEXT_SYSTEM: de-literarised (3.3)")


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
    test_prompt_version_invalidates_cache()
    test_persona_system_render_6_contract()
    test_render_7_withholds_income_from_the_persona_writer()
    test_context_system_de_literarised()
    test_context_render_hash_sensitive()
    test_cache_roundtrip()
    test_compose_persona_prompt()
    test_validate_no_invented_artifacts()
    test_count_pack_artifacts_used()
    print("PASS — render cache key, store/load, compose, and integrity check.")


if __name__ == "__main__":
    main()
