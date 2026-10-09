"""A read narrows the world to the moments its panel occupies.

⚠⚠ WHY. `packs/fnb_world.py` carries 105 brands, and its own source records the
cost: `render._vocab_tokens` builds the invented-brand guardrail out of every
TitleCase token in the pack, so a WIDER world makes that check WEAKER on every
run. `cut_to_moments` was written for this in `#71` and then had ZERO production
callers until 2026-08-22 — the same shape as `render.compose_persona_prompt`,
the assembler nothing calls.

⭐⭐ THE INVARIANT THIS FILE DEFENDS: everything that sees the world sees the
SAME world. The preflight, the persona render, the context render, the agent and
the invented-brand validator are all handed one pack. A validator that knows a
smaller world than the prompt handed the persona flags brands the pack itself
supplied — the cry-wolf failure `preflight._slug_forms` was rewritten twice to
avoid, and a guard that cries wolf gets bypassed.

⚠ Two traps this covers, both of which would have shipped silently:
  1. `persona_core_hash` keys on `category`, which names the pack but says
     nothing about how much of it the persona was shown. Cut and uncut renders
     would have shared a cache entry.
  2. All seven installed libraries predate the `moment` field. If it serialised
     when empty, every panel version on disk would move and announce a
     composition change that did not happen.

Offline. No API calls.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from agent.artifact_pack import cut_to_moments, load_pack
from agent.render import context_render_hash, persona_core_hash
from agent.run_service import _moments_in_play
from agent.vectors import (
    ChaosVector, ContextVector, DemographicPoint, DispositionVector,
    NamedDisposition,
)

WORLD = load_pack("fnb_world")


def _disp(label: str, moment: str = "") -> NamedDisposition:
    return NamedDisposition(
        label=label, moment=moment,
        vector=DispositionVector(
            category_relationship="regular", brand_stance="neutral",
            price_orientation="price_first", decision_driver="function",
            category_involvement="low", prior_experience_valence="neutral",
            channel_behavior="offline_first", life_stage="early_career"),
    )


# ---- The derivation: all-or-nothing, union, fail open ----


def test_a_panel_that_all_declares_its_moments_cuts_to_their_union() -> None:
    moments = _moments_in_play([
        _disp("a", "afternoon_dip"), _disp("b", "bedtime_cup"),
        _disp("c", "afternoon_dip"),
    ])
    assert moments == ["afternoon_dip", "bedtime_cup"], moments
    print(f"  OK  three types, two distinct moments -> {moments} ✓")


def test_one_undeclared_moment_disables_the_cut_entirely() -> None:
    """⚠⚠ ALL-OR-NOTHING, AND THE SAFE DIRECTION. A partial cut would delete the
    brands belonging to the undeclared types — silently shrinking the world for
    exactly the personas we know least about."""
    assert _moments_in_play([_disp("a", "afternoon_dip"), _disp("b", "")]) == []
    assert _moments_in_play([]) == []
    print("  OK  one blank moment keeps the whole world ✓")


def test_an_unreadable_panel_widens_the_world_rather_than_raising() -> None:
    """The commit path passes whatever the panel holds. Anything this cannot
    read a moment from must fail OPEN — a stub, a None, a disposition from a
    library that predates the field."""
    class _Stub:
        pass
    assert _moments_in_play([None, _disp("a", "afternoon_dip")]) == []
    assert _moments_in_play([_Stub()]) == []
    print("  OK  unreadable panel -> no cut, no exception ✓")


@pytest.mark.local_data
def test_every_installed_library_keeps_the_whole_world() -> None:
    """⭐ THE ZERO-REGRESSION CLAIM, CHECKED RATHER THAN ASSERTED. All seven
    libraries on disk predate `moment`, so every one of them must still be
    handed the entire pack — this change can only affect newly generated
    audiences."""
    checked = 0
    for lib in sorted(pathlib.Path("runs").rglob("entities/library.json")):
        disps = json.loads(lib.read_text()).get("dispositions") or []
        if not disps:
            continue
        checked += 1
        named = [NamedDisposition.from_dict(d) for d in disps]
        assert _moments_in_play(named) == [], (
            f"{lib.parent.parent.name} would now be cut — this change was "
            "supposed to leave every existing library untouched"
        )
    assert checked >= 5, f"only {checked} libraries found; expected the 7 on disk"
    print(f"  OK  all {checked} installed libraries keep the whole world ✓")


# ---- The cut itself ----


def test_cutting_shrinks_the_world_and_stamps_what_it_cut_to() -> None:
    cut = cut_to_moments(WORLD, ["bedtime_cup"])
    assert len(cut.brand_landscape) < len(WORLD.brand_landscape), (
        "cutting to one moment did not narrow a 105-brand world"
    )
    assert cut.cut_moments == ("bedtime_cup",), cut.cut_moments
    assert WORLD.cut_moments == (), "cut_to_moments mutated the shared pack"
    print(f"  OK  {len(WORLD.brand_landscape)} brands -> "
          f"{len(cut.brand_landscape)}, stamped {cut.cut_moments} ✓")


# ---- The cry-wolf pair: the guard must tighten, never misfire ----


def test_a_brand_the_cut_kept_is_never_flagged_as_invented() -> None:
    """⚠⚠ THE CRY-WOLF HALF, AND IT IS THE ONE THAT MATTERS. The guardrail is
    built from the pack the persona was shown. If a brand survives the cut, the
    persona may legitimately name it and must not be flagged."""
    from agent.render import _validate_no_invented_artifacts

    cut = cut_to_moments(WORLD, ["bedtime_cup"])
    kept = [b.name for b in cut.brand_landscape]
    assert kept, "the cut kept no brands at all"
    prose = f"You keep a pack of {kept[0]} in the kitchen and reach for it at night."
    warnings = _validate_no_invented_artifacts(prose, cut)
    assert not warnings, (
        f"a brand the cut KEPT was flagged as invented: {warnings}. A guard "
        "that cries wolf on legitimate output gets bypassed."
    )
    print(f"  OK  kept brand {kept[0]!r} passes the guard ✓")


def test_a_brand_the_cut_dropped_is_now_caught() -> None:
    """The other half — the tightening this was done for. A brand outside the
    panel's moments is no longer in the persona's world, so naming it is
    exactly what the guardrail should catch."""
    from agent.render import _validate_no_invented_artifacts

    cut = cut_to_moments(WORLD, ["bedtime_cup"])
    kept = {b.name for b in cut.brand_landscape}
    dropped = [b.name for b in WORLD.brand_landscape if b.name not in kept]
    assert dropped, "the cut dropped nothing, so there is nothing to catch"
    # A single-token brand, so the TitleCase scan has one clean token to find.
    single = next((d for d in dropped if len(d.split()) == 1), None)
    if single is None:
        print("  --  no single-token dropped brand in this pack; skipped")
        return
    prose = f"At night you reach for a {single} instead of anything else."
    assert _validate_no_invented_artifacts(prose, cut), (
        f"{single!r} was cut from the world but naming it raised no warning — "
        "the guardrail did not tighten"
    )
    print(f"  OK  dropped brand {single!r} is now flagged ✓")


# ---- The cache key ----


def test_a_cut_read_does_not_reuse_a_whole_world_render() -> None:
    """⚠⚠ THE SILENT ONE. `persona_core_hash` keys on `category`, which names
    the pack but not how much of it the persona saw. Without the cut in the
    payload, a core rendered against 105 brands and one rendered against 12
    share a cache entry and the wrong world is served."""
    demo = DemographicPoint(gender="male", age_band="25_34",
                            income_tier="upper_mid", geography="Indore / tier-1")
    dv = _disp("x").vector
    cv = ChaosVector(decision_velocity="moderate", suggestibility="medium",
                     consistency="variable", risk_tolerance="balanced")

    whole = persona_core_hash(demo, dv, cv, "fnb_world", "anchor")
    cut = persona_core_hash(demo, dv, cv, "fnb_world", "anchor",
                            cut_moments=["bedtime_cup"])
    other = persona_core_hash(demo, dv, cv, "fnb_world", "anchor",
                              cut_moments=["afternoon_dip"])
    assert whole != cut, "a cut render shares a cache key with an uncut one"
    assert cut != other, "two different cuts share a cache key"
    print("  OK  whole / cut / other-cut are three distinct keys ✓")


def test_no_cut_leaves_every_existing_cache_entry_valid() -> None:
    """⭐ OMITTED WHEN ABSENT, so nothing cached before 2026-08-22 is
    invalidated — no library re-renders, and no before/after comparison
    silently breaks."""
    demo = DemographicPoint(gender="male", age_band="25_34",
                            income_tier="upper_mid", geography="Indore / tier-1")
    dv = _disp("x").vector
    cv = ChaosVector(decision_velocity="moderate", suggestibility="medium",
                     consistency="variable", risk_tolerance="balanced")
    ctx = ContextVector(attention_level="low", device_posture="desk",
                        intent_state="killing_time", energy_state="low",
                        social_setting="alone")
    assert (persona_core_hash(demo, dv, cv, "fnb_world", "a")
            == persona_core_hash(demo, dv, cv, "fnb_world", "a", cut_moments=[]))
    assert (context_render_hash(ctx, "fnb_world")
            == context_render_hash(ctx, "fnb_world", cut_moments=[]))
    print("  OK  no cut -> byte-identical keys, nothing invalidated ✓")


def test_the_moment_field_is_omitted_when_empty() -> None:
    """⚠⚠ Emitting `"moment": ""` would move `compute_panel_version` for every
    library on disk and announce a composition change that did not happen — the
    same rule `display_name` and `authored_for` already follow."""
    plain = _disp("loyalist_x").to_dict()
    assert "moment" not in plain, plain
    assert NamedDisposition.from_dict(plain).moment == ""

    declared = _disp("loyalist_x", "afternoon_dip").to_dict()
    assert declared["moment"] == "afternoon_dip"
    assert NamedDisposition.from_dict(declared).moment == "afternoon_dip"
    print("  OK  moment omitted when empty, round-trips when set ✓")


@pytest.mark.local_data
def test_installed_libraries_serialise_byte_identically() -> None:
    """The strongest form of the claim above: re-serialising every disposition
    on disk must reproduce its stored bytes exactly."""
    checked = 0
    for lib in sorted(pathlib.Path("runs").rglob("entities/library.json")):
        for stored in json.loads(lib.read_text()).get("dispositions") or []:
            assert NamedDisposition.from_dict(stored).to_dict() == stored, (
                f"{lib.parent.parent.name}/{stored['label']} does not "
                "round-trip byte-identically — a panel version just moved"
            )
            checked += 1
    assert checked > 50, f"only {checked} dispositions checked"
    print(f"  OK  {checked} installed dispositions round-trip unchanged ✓")


def main() -> None:
    print("=== a read cuts the world to the moments in play ===")
    test_a_panel_that_all_declares_its_moments_cuts_to_their_union()
    test_one_undeclared_moment_disables_the_cut_entirely()
    test_an_unreadable_panel_widens_the_world_rather_than_raising()
    test_every_installed_library_keeps_the_whole_world()
    test_cutting_shrinks_the_world_and_stamps_what_it_cut_to()
    test_a_brand_the_cut_kept_is_never_flagged_as_invented()
    test_a_brand_the_cut_dropped_is_now_caught()
    test_a_cut_read_does_not_reuse_a_whole_world_render()
    test_no_cut_leaves_every_existing_cache_entry_valid()
    test_the_moment_field_is_omitted_when_empty()
    test_installed_libraries_serialise_byte_identically()
    print("PASS — one world, one key, and every existing library untouched.")


if __name__ == "__main__":
    main()
