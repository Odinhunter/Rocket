"""A machine identifier must never be read by a model or by a customer.

⚠⚠ WHY THIS FILE EXISTS. `category` is the string `"fnb_world"`. It names the
module (`packs/fnb_world.py`), it keys the render cache, and it gates the
install guard — three machine jobs. It was ALSO interpolated into prose that a
model reads. On 2026-08-22 a model read that slug and described the market to
every persona in a $3.85 run as **"international food and drink"** — for an
INDIAN food and beverage pack. Nothing caught it, because the string was
structurally perfect: a valid value, in a valid field, of the correct type.

⭐⭐⭐ AND THE REASON IT SURVIVED IS THE PART WORTH REMEMBERING. A test existed
at that exact seam — `tests/test_cycle_position.py::test_cycle_line_prose` —
and it **asserted the defect as correct output**, pinning
`"recently stocked up on health wellness nutrition"`. A test that ratifies a
bug is a stronger blocker than no test at all, because fixing the bug breaks
the suite and the fix looks like the regression.

⭐ The correct pattern was already in the codebase the whole time: the demand
grids carry `market` ("Indian urban food and beverage") and `_grid_brief` has
always used it instead of the slug. It was written once, for one surface, and
never propagated — which is this project's characteristic failure, not a
one-off. See `docs/why_we_keep_making_the_same_mistake.md`.

THE LAW THESE TESTS ENFORCE:
  a value that identifies a thing to the machine is never the value that
  describes it to a reader. Two jobs, two fields.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from agent.artifact_pack import load_pack, market_name_for   # noqa: E402
from agent.render import _context_user_payload, _pack_brief  # noqa: E402
from agent.runtime import _cycle_line                        # noqa: E402
from agent.vectors import ContextVector                      # noqa: E402

# Every pack that ships. If you add one, add it here — the point of this file is
# that a NEW pack cannot quietly reintroduce the defect.
PACKS = [
    "fnb_world",
    "health_nutrition_snacking",
    "health_nutrition_snacking_bev",
    "health_wellness_nutrition",
    "coffee",
    "chocolate",
    "personal_audio",
    "wellness",
]


@pytest.mark.parametrize("category", PACKS)
def test_every_pack_names_its_market_in_english(category: str) -> None:
    """⭐ The fallbacks in `market_name_for` and `_pack_brief` exist so a missing
    name degrades instead of crashing. This test is what guarantees the fallback
    never actually fires — without it the degradation IS the bug, silently."""
    pack = load_pack(category)
    assert pack.market_name, f"{category} has no market_name — the slug will leak"
    assert pack.market_name != category
    assert pack.market_name != category.replace("_", " "), (
        f"{category}: market_name is just the humanised slug, which is the defect "
        f"with extra steps"
    )
    assert "_" not in pack.market_name, "a market name is prose, not an identifier"
    assert pack.market_name[0].isupper(), "prose, so it reads as prose"


@pytest.mark.parametrize("category", PACKS)
def test_the_slug_never_reaches_the_persona_writer(category: str) -> None:
    """`_pack_brief` is the block that tells the model what world it is writing
    a person into. It reaches the persona render prompt AND the generation
    prompt."""
    pack = load_pack(category)
    brief = _pack_brief(pack)
    assert pack.market_name in brief
    assert f"CATEGORY: {category}" not in brief


@pytest.mark.parametrize("category", PACKS)
def test_the_slug_never_reaches_the_context_writer(category: str) -> None:
    """The context render decides what a persona is told the ad is FOR. This is
    the exact hop that produced "international food and drink"."""
    pack = load_pack(category)
    payload = _context_user_payload(
        ContextVector(
            attention_level="high", device_posture="desk",
            intent_state="actively_shopping", energy_state="alert",
            social_setting="alone",
        ),
        pack,
    )
    assert pack.market_name in payload
    assert f"CATEGORY: {category}" not in payload


def test_the_cycle_line_carries_no_category_at_all() -> None:
    """⭐⭐ THE STRONGEST FORM OF THE FIX — the coupling was DELETED, not fed a
    better value. This line reaches every agent in every run, and its template
    needs a mass noun, which no market description can be ("partway through your
    current Indian urban food and beverage" is not English either). The persona's
    own core already names what they stock, so the noun was always redundant."""
    sentinel = "zzq_sentinel_category"
    for position in ("just_bought", "mid_cycle", "running_low", "unknown"):
        line = _cycle_line(position, sentinel)
        assert "zzq" not in line.lower()


@pytest.mark.parametrize("category", PACKS)
def test_market_name_for_is_the_one_call_site_for_prose(category: str) -> None:
    """The helper the rest of the codebase should reach for. Anything that needs
    to TELL someone what market this is calls this; anything that needs to LOOK
    SOMETHING UP uses `category` directly."""
    assert market_name_for(category) == load_pack(category).market_name


def test_an_unknown_category_degrades_instead_of_crashing() -> None:
    """⚠ A run must not die because a pack is missing — but the degraded value is
    still not allowed to be pretty. It is the humanised slug, which is visibly
    wrong, which is the point: fail visibly rather than plausibly."""
    assert market_name_for("no_such_pack_exists") == "no such pack exists"
