"""The free, deterministic check that stands between a defect and a paid run.

⚠⚠ WHY. `agent/preflight.py` exists because a $3.85 run told every persona in it
that the market was "international food and drink" — a model reading the slug
`fnb_world`. The value was structurally perfect, so no schema could see it.

⭐ THESE TESTS CALL THE SAME FUNCTIONS THE RUNTIME CALLS. One implementation,
two consumers — the offline suite over the 8 shipped packs, and `prepare()` over
whatever data a real run actually resolves. A second copy of the rule is exactly
the drift that unparsed `enthusiast`.

⭐⭐ AND THE PRECISION HALF MATTERS AS MUCH AS THE CATCHING HALF. Two earlier
drafts of this check were too broad: one flagged the `coffee` pack eleven times,
one flagged `personal_audio` for its own correct market name. A guard that cries
wolf gets bypassed, and then it is not there for the real one. Half of the tests
below pin the exemptions.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack                          # noqa: E402
from agent.preflight import (                                      # noqa: E402
    PreflightError, _slug_forms, check_labels, check_pack, preflight_or_raise,
)

PACKS = [
    "fnb_world", "health_nutrition_snacking", "health_nutrition_snacking_bev",
    "health_wellness_nutrition", "coffee", "chocolate", "personal_audio",
    "wellness",
]


# --------------------------------------------------------------------------
# It catches
# --------------------------------------------------------------------------

@pytest.mark.parametrize("category", PACKS)
def test_every_shipped_pack_passes_its_own_preflight(category: str) -> None:
    """⚠ THIS FOUND A LIVE DEFECT THE DAY IT WAS WRITTEN. `packs/
    health_wellness_nutrition.py` opened its behavioral_priors with
    "health_wellness_nutrition is identity-loaded and trust-fractured." — the
    raw slug as the subject of a sentence every persona writer reads, shipped
    and unnoticed, in the pack behind the 50-label hw_generated_v1 library."""
    assert check_pack(load_pack(category)) == []


def test_the_underscore_form_is_always_a_defect() -> None:
    """No pack, ever, has a legitimate reason to put `a_b_c` in prose. This is
    the shape the real leak takes: an f-string interpolating `category`
    produces the underscore form, always."""
    assert "fnb_world" in _slug_forms("fnb_world", "Indian urban food and beverage")
    # even when the market name is the humanised slug itself, the raw form stays banned
    assert "some_cat" in _slug_forms("some_cat", "some cat")


def test_the_humanised_form_is_caught_when_it_is_not_the_market_name() -> None:
    """`Fnb world` — the run-header defect, in prompt form."""
    forms = _slug_forms("fnb_world", "Indian urban food and beverage")
    assert "fnb world" in forms and "Fnb world" in forms


def test_an_unparseable_label_is_a_defect() -> None:
    out = check_labels(["brand_loyalist_x", "upgrader_fine"])
    assert len(out) == 1 and "brand_loyalist_x" in out[0]


def test_preflight_reports_every_defect_at_once() -> None:
    """⚠ A run blocked twice, learning one reason at a time, wastes an
    afternoon. `PreflightError` carries them all."""
    # ⚠ `load_pack` returns a SHARED CACHED OBJECT — `load_pack(x) is
    # load_pack(x)`. A first draft of this test mutated it in place and the
    # blank market_name leaked into the next test, which failed for a reason
    # that had nothing to do with it. Copy, never mutate.
    pack = replace(load_pack("fnb_world"), market_name="")
    with pytest.raises(PreflightError) as exc:
        preflight_or_raise(pack, ["brand_loyalist_x"])
    assert len(exc.value.defects) >= 2
    assert any("market_name" in d for d in exc.value.defects)
    assert any("brand_loyalist_x" in d for d in exc.value.defects)


# --------------------------------------------------------------------------
# It does not cry wolf — the half that keeps it usable
# --------------------------------------------------------------------------

def test_a_single_token_category_is_exempt() -> None:
    """⭐ `coffee` in the coffee pack is not a defect and cannot be one: the
    identifier and the English word are the same string, so a model reading it
    understands exactly the right thing. The first draft flagged `CATEGORY:
    Indian coffee`, `Cafe Coffee Day` and `/r/coffee`."""
    assert _slug_forms("coffee", "Indian coffee, at home and in cafes") == []
    assert _slug_forms("chocolate", "x") == []


def test_the_market_name_is_the_oracle_for_the_humanised_form() -> None:
    """⭐ The second false positive. `personal_audio` humanises to "personal
    audio", which IS the real English name of the category — and the pack's own
    authored market_name ("Indian personal audio") is the evidence of that. The
    underscore form stays banned either way."""
    forms = _slug_forms("personal_audio", "Indian personal audio")
    assert forms == ["personal_audio"]
    assert "personal audio" not in forms


def test_the_grandfathered_violation_does_not_block_a_run() -> None:
    """⚠ `doctor_triggered_vitamin` is installed in health_wellness_demo.
    Blocking on it makes that library unrunnable; renaming it moves the panel
    version and invalidates saved audiences. It is exempted from ONE shared set
    in agent/vectors.py that this file and the preflight both read."""
    assert check_labels(["doctor_triggered_vitamin"]) == []


def test_display_name_is_not_required_at_runtime() -> None:
    """⚠⚠ HARD-FAILING ON IT WOULD BRICK ALL SEVEN INSTALLED LIBRARIES, which
    all predate the field. `disposition_display` falls back by design. It is
    REQUIRED of the GENERATOR going forward, which is where the requirement
    belongs — new data is born correct, old data keeps working."""
    preflight_or_raise(load_pack("fnb_world"), ["upgrader_desk_afternoon_protein"])


# --------------------------------------------------------------------------
# The ordering invariant — the whole reason it is not another advisory
# --------------------------------------------------------------------------

def _prepare_source() -> str:
    """The body of `RunService.prepare`, sliced out of the file on disk."""
    text = (pathlib.Path(__file__).resolve().parent.parent
            / "agent" / "run_service.py").read_text()
    start = text.index("    def prepare(config: RunConfig)")
    rest = text[start + 10:]
    end = rest.find("\n    def ")
    return rest[:end] if end != -1 else rest


def test_the_preflight_runs_before_the_first_model_call() -> None:
    """⭐⭐ THE INVARIANT THAT MAKES IT WORTH HAVING. RunPreparation's six other
    advisories are all computed AFTER `identify_target`, i.e. one model call and
    one bill in. A check that fires there cannot save the money it exists to
    save. This pins the preflight above every model call in `prepare()`."""
    # ⚠⚠ READ THE FILE, NOT THE ATTRIBUTE. `tests/conftest.py` monkeypatches
    # `RunService.prepare` to a refusing stub for every test in the suite (it is
    # the ~$0.15 paid call), so `inspect.getsource(RunService.prepare)` returns
    # the STUB's source — which contains no preflight, and the first draft of
    # this test failed with a confusing "substring not found".
    src = _prepare_source()
    guard = src.index("preflight_or_raise(")

    # ⚠⚠ THE `if at != -1: assert` SHAPE IS HOW THIS TEST WAS VACUOUS AT FIRST.
    # It pinned "render_persona_core" and "_warm_render", NEITHER of which
    # appears in prepare() — the real names are the two below. Both silently
    # skipped, so the test was pinning one call while claiming to pin three.
    # Each name is now asserted PRESENT before it is asserted ordered: a rename
    # fails this test loudly instead of quietly removing its own coverage.
    for model_call in ("identify_target(", "warm_render_cache("):
        at = src.find(model_call)
        assert at != -1, (
            f"{model_call} is no longer in prepare() — if it was renamed, "
            f"rename it here too; this guard is worthless pointing at nothing"
        )
        assert guard < at, (
            f"{model_call} happens before the preflight — money is spent "
            f"before the free check runs"
        )


def test_a_preflight_failure_is_not_a_traceback_at_the_cli() -> None:
    """⚠ An operator reading a stack trace at 2am fixes the wrong thing.
    batch_run catches it and prints the defect with the reason there is no
    override."""
    src = (pathlib.Path(__file__).resolve().parent.parent
           / "batch_run.py").read_text()
    assert "except PreflightError" in src
    assert "No credit debited" in src
