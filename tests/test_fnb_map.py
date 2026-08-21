"""The F&B demand map — 21 moments — and the seam that carries it into the prompt.

⭐⭐ WHY THIS FILE EXISTS. The user settled decision 3 on 2026-08-21: the map
replaces the 8-occasion grid. The evidence is `docs/fnb_real_events.md` — five
real days, 52 items routed by hand; on the 34 items a snacking-and-nutrition
grid actually claims, `SNACKING_GRID` placed 3 and this map placed 29.

⚠⚠ THE DEFECT THESE TESTS PIN IS A WRITING DEFECT, NOT A DATA ONE. Every single
grid failure in those five days had the same shape: incidental scene-setting in
the occasion's prose acting as an exclusion criterion.

  - "the afternoon dip AT A DESK"        threw out three real people's 3-6pm
                                          chai. None of the three was at a desk:
                                          a building site, a chai tapri and a
                                          college canteen.
  - "wants something SWEET"               threw out Maggi and chips at 2am.
  - "LEAVING LATE, will not sit down"     threw out four sat-down breakfasts.
  - "a habit someone has DECIDED to keep" threw out a twice-daily prescription.

So the map's discriminating QUESTIONS — the things that won 29-3 — must survive
all the way into the assembled prompt, and must not themselves acquire the
qualifiers that did the damage. That is what most of this file checks.
See memory `cell_is_a_question_not_a_vignette`.

⚠ Every absence test here was mutation-proved (memory `vacuous_test_shapes`):
the map was broken on purpose and each one failed as intended before being
committed.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from agent.artifact_pack import load_pack                      # noqa: E402
from generate_audience import (                                # noqa: E402
    FNB_MAP, GRIDS, SNACKING_GRID, Region, _build, _grid_brief,
)

MAP = GRIDS["fnb"]
REGION = Region(gender="any", age_min=25, age_max=40, tier="tier-1")


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------

def test_the_map_is_twenty_one_moments_in_three_bands():
    """21 unique keys, banded 12 clock / 6 event / 3 habit.

    ⭐ 21, not the published 22: the user merged the two dinner cells on
    2026-08-21. See `evening_meal` for why.

    ⚠ The band is not decoration — it drives the map's own tie-break order
    (event beats clock; clock beats habit), so a mis-banded moment routes
    wrongly. A name-only reconstruction has already put Stock-up in the wrong
    band once, which is why the counts are pinned rather than just the total.
    """
    occ = MAP["occasions"]
    assert len(occ) == 21
    assert len({o["key"] for o in occ}) == 21, "duplicate moment key"
    keys = {o["key"] for o in occ}
    # ⚠ The merge, pinned: neither published dinner cell may come back.
    assert "evening_meal" in keys
    assert not {"dinner_at_home", "dinner_brought_in"} & keys
    bands = [o["band"] for o in occ]
    assert bands.count("clock") == 12
    assert bands.count("event") == 6
    assert bands.count("habit") == 3
    assert set(bands) == {"clock", "event", "habit"}


def test_every_moment_carries_a_discriminating_question():
    """The question IS the definition. A moment without one is unroutable."""
    for o in MAP["occasions"]:
        q = o.get("question", "")
        assert q.strip(), f"{o['key']} has no question"
        assert q.rstrip().endswith("?"), f"{o['key']}'s question is not a question: {q!r}"


def test_the_grid_is_still_eight_by_eight_and_untouched():
    """⚠ `SNACKING_GRID` is BEFORE-EVIDENCE and must not be edited.

    It is the measured comparison in `docs/fnb_real_events.md` (3 of 34). If it
    drifts, that number stops being reproducible.
    """
    assert len(SNACKING_GRID["occasions"]) == 8
    assert not any(o.get("question") for o in SNACKING_GRID["occasions"])
    assert not any(o.get("band") for o in SNACKING_GRID["occasions"])


# --------------------------------------------------------------------------
# The four measured wording defects, pinned so they cannot come back
# --------------------------------------------------------------------------

def _question(key: str) -> str:
    return next(o["question"] for o in MAP["occasions"] if o["key"] == key)


def test_the_afternoon_moment_is_defined_by_place_not_by_a_desk():
    """⚠⚠ THE MOST EXPENSIVE SINGLE WORD IN THE OLD GRID.

    `desk_slump_4pm` cost three of five real people their afternoon moment.
    The map's question must say "away from home" and must never say "desk".
    """
    q = _question("afternoon_dip").lower()
    assert "away from home" in q
    assert "desk" not in q


def test_the_late_night_moment_does_not_require_something_sweet():
    """`late_night_craving` said "wants something sweet" and lost a real 2am
    plate of Maggi and chips."""
    q = _question("late_night").lower()
    assert "sweet" not in q
    assert "after 10pm" in q


def test_the_regimen_moment_does_not_require_the_person_to_have_chosen_it():
    """`daily_health_routine` said "a habit someone has DECIDED to keep" — but a
    doctor decides some of them, and that wording put a real twice-daily
    prescription outside the cell. ⭐ This is the restriction-vs-preference
    distinction the instrument otherwise cannot make."""
    q = _question("daily_regimen").lower()
    assert "schedule" in q
    assert "decid" not in q, "the regimen question must not require a chosen habit"


def test_a_setting_may_widen_a_question_but_never_narrow_it():
    """⭐⭐ THE GENERAL FORM OF THE RULE, and it is sharper than the four known
    instances — this test is what sharpened it.

    A first draft banned "desk" outright and failed on `breakfast_in_motion`,
    whose published question is *"eaten standing, travelling, OR AT A DESK?"*.
    That is the same word doing the opposite job:

      - `desk_slump_4pm` — "the afternoon dip AT A DESK" is CONJUNCTIVE. It is
        an extra condition, so it NARROWS the cell and throws out a building
        site, a chai tapri and a college canteen.
      - `breakfast_in_motion` — "standing, travelling, OR at a desk" is
        DISJUNCTIVE. It is one more way to qualify, so it WIDENS the cell.

    ⭐ So the law is not "never name a place". It is **a setting may widen a
    question, never narrow it** — and the tell is whether it is joined by "or".
    """
    narrowing = ("desk", "office jar", "scrolling in bed", "cubicle")
    for o in MAP["occasions"]:
        low = o["question"].lower()
        for word in narrowing:
            if word not in low:
                continue
            # "or" within the same clause, not merely somewhere in the sentence.
            before = low.split(word)[0][-25:]
            assert " or " in before, (
                f"{o['key']}'s question narrows on {word!r} instead of widening: "
                f"{o['question']!r}"
            )
    # And the one place it legitimately appears is the one that widens.
    assert "desk" in _question("breakfast_in_motion").lower()
    assert "desk" not in _question("afternoon_dip").lower()


# --------------------------------------------------------------------------
# The counted beverage defect
# --------------------------------------------------------------------------

def test_the_map_names_beverages_in_its_competitive_sets():
    """⚠⚠ 12 of 52 items across five real days were drinks, and all five people
    had at least one — while BOTH packs contain zero beverages. The map cannot
    fix the pack (see `_pack_brief`'s "use ONLY these"), but a map whose
    competitive sets are also beverage-free would guarantee the failure.

    ⭐ Pinned at half the map because a drink genuinely does not belong in every
    moment — `festival_and_gifting` and `household_stock_up` are purchases.
    """
    drinks = ("chai", "coffee", "buttermilk", "doodh", "tea",
              "juice", "cold drink", "electrolyte", "milk", "water")
    named = [o["key"] for o in MAP["occasions"]
             if any(d in o["competes_with"].lower() for d in drinks)]
    assert len(named) >= 10, f"only {len(named)} of 21 moments name a drink: {named}"
    # The four where a drink is the whole moment must be among them.
    for key in ("first_cup", "hydration", "bedtime_cup", "afternoon_dip"):
        assert key in named, f"{key} must name a beverage in its competitive set"


def test_the_alternatives_do_not_assume_the_eater_paid():
    """⭐ Five real days: four of five people ate substantial food they did not
    buy — a boss, a mother, a wife, a host. One man chose 2 of his 14 items.
    `SNACKING_GRID`'s heading is "WHAT THEY ACTUALLY BUY MOST OF THE TIME",
    which cannot see most of the food."""
    assert "ACTUALLY BUY" not in MAP["alternatives_heading"].upper()
    joined = " ".join(MAP["everyday_alternatives"]).lower()
    assert "someone else cooked or packed" in joined


# --------------------------------------------------------------------------
# The seam — does any of it reach the model?
# --------------------------------------------------------------------------

def _prompt_for(grid) -> str:
    system, user = _build(grid, load_pack("health_wellness_nutrition"),
                          [(grid["occasions"][0]["key"], "loyalist")], [], REGION)
    return "\n".join(b["text"] for b in system) + "\n" + user


def test_every_question_survives_into_the_assembled_prompt():
    """⭐⭐ THE TEST THAT MATTERS. The questions are what routed 29 of 34 real
    items. If they live in a doc and not in the prompt, the generator never sees
    them and the vignette defect is reproduced at 176-cell scale."""
    prompt = _prompt_for(MAP)
    for o in MAP["occasions"]:
        assert o["question"] in prompt, f"{o['key']}'s question never reaches the model"


def test_the_prompt_tells_the_model_the_question_is_the_definition():
    """A question the model reads as decoration is a question that does nothing."""
    prompt = _prompt_for(MAP)
    assert "DEFINED BY ITS QUESTION" in prompt
    assert "Never treat that example as a" in prompt


def test_the_old_grids_prompt_did_not_move():
    """⚠⚠ REGRESSION PIN. `_grid_brief` now serves two grid shapes. Every new
    branch is opt-in on a key `SNACKING_GRID` does not have, so its brief must
    be byte-identical to the pre-map version. If this fails, the 3-of-34
    measurement in `docs/fnb_real_events.md` is no longer reproducible.
    """
    brief = _grid_brief(SNACKING_GRID)
    assert "DEFINED BY" not in brief
    assert "BAND" not in brief
    assert "WHAT THEY ACTUALLY BUY MOST OF THE TIME" in brief
    assert brief.startswith("THE DEMAND SPACE — Indian urban snacking and nutrition.")


def test_the_map_is_registered_and_costs_one_hundred_and_sixty_eight_cells():
    """⚠ 21 x 8 = 168 against the old 64. This is the number that sets the spend,
    so it is pinned rather than assumed. ⚠⚠ Do NOT quote the old $1.59 — that was
    the 64-cell run, which decision 3 supersedes."""
    assert GRIDS["fnb"] is FNB_MAP
    assert len(MAP["occasions"]) * len(MAP["stances"]) == 168
    # The stance grammar is deliberately unchanged — a stance is category- and
    # moment-independent by design. See `docs/stance_vs_modifier_test.md`.
    assert MAP["stances"] == SNACKING_GRID["stances"]


def test_the_evening_meal_question_is_source_agnostic_like_lunch():
    """⭐⭐ THE POINT OF THE MERGE (user decision, 2026-08-21).

    The published map split dinner by provenance — cooked at home vs ordered in —
    while leaving lunch whole, though a delivered lunch behaves exactly like a
    delivered dinner. Asked to split lunch or merge dinner, the user merged. So
    the evening question must mirror the midday one: it asks WHETHER this is the
    meal, never WHERE it came from.

    ⚠ Mutation-proved by restoring "Is this the main COOKED evening meal?", which
    fails here on `cooked`.
    """
    evening = _question("evening_meal").lower()
    midday = _question("midday_meal").lower()
    for source_word in ("cooked", "ordered", "at home", "brought in", "delivered"):
        assert source_word not in evening, (
            f"the evening meal question narrows on {source_word!r}: {evening!r}"
        )
    # Both meals ask the same shape of question.
    assert "however it arrived" in evening
    assert "wherever it came from" in midday


def test_the_merge_did_not_quietly_drop_either_dinners_competition():
    """⚠ A merge that loses half its competitive set is a deletion wearing a
    merge's clothes. Both economies must survive in one cell: a family's Zomato
    order AND a migrant worker's bhojanalay."""
    competes = next(o["competes_with"] for o in MAP["occasions"]
                    if o["key"] == "evening_meal").lower()
    for survivor in ("roti-sabzi", "rice-dal", "zomato", "bhojanalay", "takeaway"):
        assert survivor in competes, f"{survivor!r} lost in the merge"
