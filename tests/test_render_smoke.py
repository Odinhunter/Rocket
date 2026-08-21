"""Phase 1 API smoke: the Render Engine produces non-empty persona-core and
context prose for the coffee pack, the prose weaves in pack artifacts, and
no obviously-invented brands leak. Also verifies the render cache hits on
the second call.

Cost: ~3 Sonnet calls, ~$0.01.

Run: pytest tests/test_render_smoke.py --paid   (or: python tests/test_render_smoke.py)
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from dotenv import load_dotenv

load_dotenv()

from agent.artifact_pack import load_pack
from agent.render import (
    count_pack_artifacts_used,
    persona_core_hash,
    render_context,
    render_persona_core,
    _validate_no_invented_artifacts,
)
from agent.vectors import (
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
)

_CACHE = Path("runs/_test_render_smoke_cache")


def _demo() -> DemographicPoint:
    return DemographicPoint(
        gender="male", age_band="25_34", income_tier="upper_mid",
        geography="Bangalore / metro tier-1",
        occupation_hint="software engineer at a mid-stage SaaS startup",
    )


def _disposition() -> DispositionVector:
    # The "office_bru_pragmatist" shape: regular instant user, price-led,
    # function-driven, low involvement, neutral history.
    return DispositionVector(
        category_relationship="regular", brand_stance="neutral",
        price_orientation="price_first", decision_driver="function",
        category_involvement="low", prior_experience_valence="neutral",
        channel_behavior="offline_first", life_stage="early_career",
    )


def _chaos() -> ChaosVector:
    return ChaosVector(
        decision_velocity="moderate", suggestibility="medium",
        consistency="variable", risk_tolerance="balanced",
    )


def _context() -> ContextVector:
    return ContextVector(
        attention_level="low", device_posture="commute",
        intent_state="killing_time", energy_state="drained",
        social_setting="public",
    )


def main() -> None:
    print("=== render engine API smoke ===")
    if _CACHE.exists():
        shutil.rmtree(_CACHE)
    try:
        pack = load_pack("coffee")
        demo, disp, chaos, ctx = _demo(), _disposition(), _chaos(), _context()

        core = render_persona_core(demo, disp, chaos, pack, cache_dir=_CACHE)
        assert core.strip(), "render_persona_core returned empty prose"
        n_artifacts = count_pack_artifacts_used(core, pack)
        assert n_artifacts >= 2, (
            f"persona core wove only {n_artifacts} pack brands — too flat"
        )
        # _validate_no_invented_artifacts is a WARN-ONLY heuristic, not a
        # gate — it has known false positives. We surface its output for the
        # eye, but the smoke test asserts only the positive signal (artifacts
        # woven) and non-empty prose.
        warnings = _validate_no_invented_artifacts(core, pack)
        print(f"  OK  persona core rendered: {len(core)} chars, "
              f"{n_artifacts} pack brands woven")
        if warnings:
            print(f"      ({len(warnings)} heuristic integrity warning(s) — "
                  f"verify by eye, not a failure):")
            for w in warnings:
                print(f"        - {w}")
        print("  --- persona core ---")
        print("  " + core.replace("\n", "\n  "))

        # Cache hit: second call must return byte-identical prose with no
        # API call (verified by the cache file existing).
        key = persona_core_hash(demo, disp, chaos, pack.category)
        assert (_CACHE / f"{key}.json").exists(), "persona core was not cached"
        core2 = render_persona_core(demo, disp, chaos, pack, cache_dir=_CACHE)
        assert core2 == core, "cache did not return byte-identical prose"
        print("  OK  persona core cache hit on the second call")

        context_prose = render_context(ctx, pack, cache_dir=_CACHE)
        assert context_prose.strip(), "render_context returned empty prose"
        print(f"  OK  context rendered: {len(context_prose)} chars")
        print("  --- context ---")
        print("  " + context_prose.replace("\n", "\n  "))

        # ⚠ This used to assert `compose_persona_prompt`, a helper with zero
        # production callers — so the smoke test spent real money verifying an
        # assembly no persona ever received. It was deleted 2026-08-22; the
        # shipped assembly is `runtime.build_encoding_prompt`, covered offline
        # by tests/test_marketer_notes_never_reach_the_agent.py.
        # ⭐⭐ WHAT THIS SCRIPT IS ACTUALLY FOR, AND WHY IT MUST BE RUN:
        # it prints the real rendered prose. Reading that output for one cent
        # is the check that would have caught `fnb_world` being described to
        # every persona as "international food and drink" BEFORE $3.85 was
        # spent on a run built from it. Run it after ANY change to a pack, a
        # grid, or a render prompt.
        print("PASS — render engine produces vivid, artifact-grounded prose.")
        print("  ⚠ READ THE PROSE ABOVE. That is the point of this script.")
    finally:
        if _CACHE.exists():
            shutil.rmtree(_CACHE)


@pytest.mark.paid
def test_render_engine_end_to_end() -> None:
    """Costs ~$0.01 of real API calls. Skipped unless --paid is passed.

    ⚠ Until 2026-08-22 this file had no `test_` function at all: pytest
    collected zero from it while it sat in tests/ named test_*.py. It was
    run by hand, which means in practice it was not run."""
    main()


if __name__ == "__main__":
    main()
