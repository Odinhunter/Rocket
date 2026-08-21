"""The F&B world pack — does it actually contain the market the map describes?

⭐⭐ WHY THIS FILE EXISTS. `_pack_brief` hands the model *"THE BRANDS THAT EXIST IN THIS
MARKET (use ONLY these)"* and `_SYSTEM` adds *"never invent a brand"*. The pack is a
CLOSED UNIVERSE, so anything it cannot name is a thing no persona can weigh a decision
against. Five separate times this project has shipped a pack that could not name the
real competitor — `#48` no confectionery, `#58` no beverages, `#62` the pack was not the
lever, event 1b a real buyer's protein incumbent was a MILK, and `#68` counted 12 of 52
real items as drinks against two packs holding zero.

⭐⭐⭐ SO THE LOAD-BEARING TEST IN THIS FILE IS THE CLOSURE TEST: every branded thing five
real people actually consumed must be nameable by a persona built from this pack. That
is the only test here grounded in primary data rather than in design intent, and it is
the one to protect.

⚠ Absence tests were mutation-proved (memory `vacuous_test_shapes`) — the pack was
broken on purpose and each failed as intended before being committed.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from agent.artifact_pack import cut_to_moments, load_pack       # noqa: E402
from agent.render import _vocab_tokens                          # noqa: E402
from generate_audience import FNB_MAP, _pack_brief              # noqa: E402

WORLD = load_pack("fnb_world")
MOMENT_KEYS = {o["key"] for o in FNB_MAP["occasions"]}


# --------------------------------------------------------------------------
# The subscription contract
# --------------------------------------------------------------------------

def test_every_subscription_names_a_real_moment():
    """⚠ A typo here is silent: an unknown key simply never matches, so the brand
    quietly vanishes from every cut. Also catches anything still pointing at the two
    dinner cells the user merged in `#70`."""
    for b in WORLD.brand_landscape:
        unknown = set(b.moments) - MOMENT_KEYS
        assert not unknown, f"{b.name} subscribes to unknown moment(s): {unknown}"


def test_no_moment_is_a_brand_desert():
    """Every one of the 21 moments needs enough brands to make a real choice. A moment
    with one brand in it is a moment where the persona has nothing to decide."""
    counts = {k: 0 for k in MOMENT_KEYS}
    for b in WORLD.brand_landscape:
        for m in b.moments:
            counts[m] += 1
    thin = {k: n for k, n in counts.items() if n < 3}
    assert not thin, f"moments with fewer than 3 brands: {thin}"


def test_every_brand_is_subscribed():
    """⚠ `cut_to_moments` FAILS OPEN — an unsubscribed brand is kept in every cut rather
    than dropped, because silently deleting a brand is the SuperYou failure's own shape.
    That safety net only works if this pack never relies on it."""
    orphans = [b.name for b in WORLD.brand_landscape if not b.moments]
    assert not orphans, f"unsubscribed brands would survive every cut: {orphans}"


# --------------------------------------------------------------------------
# ⭐⭐⭐ THE CLOSURE TEST — grounded in the only real data this project holds
# --------------------------------------------------------------------------

def test_every_branded_thing_five_real_people_consumed_is_nameable():
    """⭐⭐ THE TEST THAT MATTERS. Each token below is a brand that appears in
    `docs/fnb_real_events.md` — something a real person actually put in their mouth or
    ordered on an app. If the pack cannot name it, a persona built from this pack cannot
    weigh a decision against it, and `render` would flag it as an invented artifact.

    ⚠ Provilac is the sharpest: a 25g-protein lactose-free milk drunk every morning FOR
    A PROTEIN GOAL — a real buyer's actual protein incumbent, and a product category
    neither earlier pack could name at all. This is the commit where it finally exists.
    """
    vocab = _vocab_tokens(WORLD)
    from_the_field = {
        "Provilac": "event 1b — the user's own morning protein milk",
        "Coke": "event 1g — Diet Coke with dinner",
        "Frooti": "event 4e — provided free by a construction boss",
        "Sprite": "event 4i — with dal-chawal at a bhojanalay",
        "Amul": "event 6b — Amul Masti chaas with an ordered-in lunch",
        "Starbucks": "event 6e — a 4pm frappuccino, alone",
        "Bull": "event 6g — Red Bull at a friend's house",
        "SuperYou": "event 6h — THE bar whose failed run caused this whole pivot",
        "Maggi": "events 3j and 6i — 5pm at home, and 2am alone",
        "Yumm": "event 5f — Too Yumm protein chips at a college canteen",
        "Neurobion": "events 7e/7n — a twice-daily prescription",
        "Electral": "the recovery moment nothing else can represent",
        "Zomato": "events 5g, 6a, 6f — three of five people ordered on an app",
        "Swiggy": "same",
        "Blinkit": "events 3i, 6i — quick commerce reached two of the five days",
        "Zepto": "same",
    }
    missing = {tok: why for tok, why in from_the_field.items() if tok not in vocab}
    assert not missing, (
        "the world cannot name things real people actually consumed: "
        + "; ".join(f"{t} ({w})" for t, w in missing.items())
    )


def test_the_counted_beverage_defect_is_closed():
    """⚠⚠ 12 of 52 real items were drinks and BOTH earlier packs held zero. Pinned by
    category, not by one brand, so removing any single drink cannot quietly reopen it."""
    names = " ".join(b.name for b in WORLD.brand_landscape)
    for drink in ("Tata Tea Premium", "Nescafé", "Bru", "Thums Up", "Sprite",
                  "Frooti", "Maaza", "Amul Masti Chaas", "Bisleri", "Sting",
                  "Red Bull", "Horlicks", "Provilac", "Starbucks India"):
        assert drink in names, f"{drink!r} missing — the beverage gap is not closed"
    # And they must reach the moments where a drink actually wins.
    for key in ("first_cup", "afternoon_dip", "hydration", "bedtime_cup",
                "mid_morning_break"):
        subs = [b.name for b in WORLD.brand_landscape if key in b.moments]
        assert len(subs) >= 3, f"{key} has too few brands: {subs}"


# --------------------------------------------------------------------------
# Things that must NOT have been carried forward
# --------------------------------------------------------------------------

def test_the_stale_shrinkflation_grievance_was_not_carried_forward():
    """⚠⚠ `health_nutrition_snacking` carries *"shrinkflation as betrayal — the pack
    costs the same and holds less"*. Researched 2026-08-21: that is now BACKWARDS. GST
    2.0 (22 Sept 2025) cut biscuits, namkeen, chips, noodles, bakery, jams and ice cream
    from 12-18% to 5%, and companies HELD the ₹5/₹10 price and put grammage back in.

    ⭐ Copying a pack forward copies its stale beliefs too. This pins the one we caught.
    """
    refs = " ".join(WORLD.cultural_references).lower()
    assert "shrinkflation as betrayal" not in refs
    assert "shrinkflation running backwards" in refs
    assert "62%" in refs or "₹5 and ₹10 pack is the market" in refs.lower()


def test_unbranded_street_and_home_food_stays_out_of_the_brand_list():
    """⭐ `render._vocab_tokens` builds the invented-brand guardrail from TitleCase
    tokens in the pack, so every brand added weakens it. Unbranded food — a samosa, a
    tiffin, cutting chai — belongs in prices and in the map's alternatives, where it
    costs the guardrail nothing."""
    names = [b.name.lower() for b in WORLD.brand_landscape]
    for unbranded in ("samosa", "vada pav", "cutting chai", "tiffin", "halwai",
                      "bhojanalay", "thali"):
        assert not any(unbranded in n for n in names), (
            f"{unbranded!r} is unbranded and must not sit in brand_landscape"
        )
    # But it must still be nameable somewhere the model reads.
    brief = _pack_brief(WORLD)
    for unbranded in ("cutting chai", "samosa", "vada pav"):
        assert unbranded in brief.lower(), f"{unbranded!r} unreachable by any persona"


def test_the_three_source_packs_are_untouched():
    """⚠ `health_nutrition_snacking` is the before-evidence for the map's 3-of-34;
    `health_nutrition_snacking_bev` says NOT FOR INSTALL on its own first line; `coffee`
    is hand-authored-era evidence. Notes were COPIED into the world, never moved."""
    assert len(load_pack("health_nutrition_snacking").brand_landscape) == 45
    assert len(load_pack("health_nutrition_snacking_bev").brand_landscape) == 52
    assert len(load_pack("coffee").brand_landscape) == 18
    for cat in ("health_nutrition_snacking", "coffee", "health_wellness_nutrition"):
        pack = load_pack(cat)
        assert not any(b.moments for b in pack.brand_landscape), (
            f"{cat} gained subscriptions — it is evidence and must not move"
        )


# --------------------------------------------------------------------------
# The cut
# --------------------------------------------------------------------------

def test_cutting_to_one_moment_narrows_the_world_and_mutates_nothing():
    """⭐ The cut is what pays for a 105-brand world: a panel assembled for one ad sees
    only the moments that ad competes in, which shortens the prompt AND tightens the
    invented-brand guardrail at the same time."""
    before = len(WORLD.brand_landscape)
    cut = cut_to_moments(WORLD, ["bedtime_cup"])
    assert 0 < len(cut.brand_landscape) < before
    assert all("bedtime_cup" in b.moments for b in cut.brand_landscape)
    # pure function — the world itself is unchanged
    assert len(WORLD.brand_landscape) == before


def test_the_cut_drops_price_anchors_for_brands_it_removed():
    """⚠ A ₹425 Starbucks anchor inside a world with no Starbucks invites the persona to
    name it anyway — and `render` would then flag a brand the pack itself suggested."""
    cut = cut_to_moments(WORLD, ["bedtime_cup"])
    kept = {b.name for b in cut.brand_landscape}
    assert "Starbucks India" not in kept
    assert not any("Starbucks" in pp.item for pp in cut.price_points)
    # anchors naming nobody are the price architecture and must survive
    assert any("chai" in pp.item.lower() for pp in cut.price_points)


def test_the_price_spread_spans_the_whole_market():
    """⭐ The spread IS the competitive story: a ₹104 bar competes with a ₹12 chai and a
    ₹15 vada pav — a 4-9x step for the same moment. Both ends were observed in the five
    real days, so both ends must be in the pack."""
    items = " ".join(f"{pp.item} {pp.price_inr}" for pp in WORLD.price_points)
    assert "₹2" in items          # Parle-G mini pouch, the floor
    assert "₹560" in items        # venti frappuccino, the ceiling
    assert "cutting chai" in items.lower()
    assert "vada pav" in items.lower()
    assert len(WORLD.price_points) >= 40


def test_the_pack_is_registered_under_a_stable_category_name():
    """⚠ `install_generated_audience.py` exits on a category mismatch between the
    generated file and the install flag, so this name is a contract. Pick it once."""
    assert WORLD.category == "fnb_world"
    assert len(WORLD.brand_landscape) >= 90, "the world should span all of F&B"
    assert WORLD.open_questions, "a pack with no open questions is a pack lying to you"
