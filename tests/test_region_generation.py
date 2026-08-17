"""Region-scoped generation: people not bands, gender as an axis, honest refusals.

⚠ WHY THIS FILE EXISTS. The first generation was given no demographic brief, so
the model wrote everyone into the one world it could infer: oldest person 54,
zero tier-3. Measured against that library, a `women 45-60` buy reached 2 of 32
buyer types and `women 55-75` reached 0 — and the run built 100 agents anyway,
silently. A region is the fix, and each test below pins one way the fix can be
quietly undone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from agent.panel import demographic_overlap
from agent.vectors import DemographicPoint, _VALID_DISPOSITION
import check_generated_audience as CHECK
import generate_audience as G

def _type(label="loyalist_x", gender="female", age=52, income=5.4,
          occasion="desk_slump_4pm", stance="loyalist", **axes) -> dict:
    t = {
        "label": label, "occasion": occasion, "stance": stance,
        "l1_context": "came to the category through a family diabetes scare",
        "l2_category": "buys weekly off the corner shop",
        "l3_knowledge": "knows the shelf but does not read the back of the pack "
                        "and does not track macros",
        "l4_stance": "rejects anything that tastes like a compromise",
        "l5_behavior": "picked up a ₹10 pack on the way home last Tuesday",
        "bundles": [{
            "gender": gender, "age": age, "income_lpa": income,
            "geography": "Nagpur / tier-3 town",
            "occupation_hint": "runs a tailoring business from home",
            "household_hint": "two kids in college", "weight": 1.0}],
    }
    base = dict(category_relationship="regular", brand_stance="loyalist",
                price_orientation="price_first", decision_driver="habit",
                category_involvement="low", prior_experience_valence="positive",
                channel_behavior="offline_first", life_stage="settled")
    base.update(axes)
    t.update(base)
    return t

# ---- gender is a generation axis, and the old key would have eaten it ----

def test_a_mens_and_a_womens_version_of_one_cell_are_not_duplicates():
    """⚠ THE COLLISION THAT WOULD FIRE ON THE FIRST GENDERED RUN. `gender` is not
    one of the eight distinctness axes, so a men's and a women's loyalist at the
    4pm slump land on an IDENTICAL coordinate. Under the coordinate-only key the
    second is reported as a duplicate opinion and `--fill` re-rolls it — deleting
    exactly the difference the region was generated to capture."""
    assert "gender" not in _VALID_DISPOSITION, (
        "gender became a distinctness axis; this test's premise is stale")
    women = _type(label="loyalist_desk_w", gender="female")
    men = _type(label="loyalist_desk_m", gender="male")

    assert CHECK.distinctness_key(women) != CHECK.distinctness_key(men)
    keep, drop = G._triage([women, men])
    assert len(keep) == 2, f"a gendered pair was culled as duplicates: {drop}"

def test_the_coordinate_alone_would_have_called_them_the_same_person(monkeypatch):
    """MUTATION PROOF for the test above: with gender stripped back out of the
    key, the pair must be culled — otherwise something else is passing it."""
    monkeypatch.setattr(
        CHECK, "distinctness_key",
        lambda t: tuple(t[a] for a in CHECK._AXES))
    monkeypatch.setattr(G, "distinctness_key", CHECK.distinctness_key)
    keep, drop = G._triage([_type(label="w", gender="female"),
                            _type(label="m", gender="male")])
    assert len(keep) == 1 and len(drop) == 1
    assert "duplicate opinion" in drop[0][1]

def test_two_genuinely_identical_types_are_still_caught():
    """POSITIVE CONTROL — widening the key must not switch distinctness off."""
    keep, drop = G._triage([_type(label="a", gender="female"),
                            _type(label="b", gender="female")])
    assert len(keep) == 1, "an actual duplicate survived the widened key"

# ---- a person, not a band ------------------------------------------------

def test_a_generated_bundle_becomes_a_point_selectable_by_any_range():
    """The whole reason for the change: arbitrary customer-chosen ranges."""
    region = G.Region(gender="female", age_min=45, age_max=60)
    d = G._to_disposition(_type(age=52, income=5.4), region)
    point = d.demographic_bundles[0].point
    assert point.age_min == point.age_max == 52
    assert point.income_lpa_min == point.income_lpa_max == 5.4

    def frame(lo, hi):
        return DemographicPoint(gender="female", age_min=lo, age_max=hi,
                                income_lpa_min=0, income_lpa_max=100,
                                geography="any")
    for lo, hi in ((45, 60), (47, 63), (50, 55), (52, 52)):
        assert demographic_overlap(point, frame(lo, hi)) == 1.0
    # POSITIVE CONTROL — out really is out.
    assert demographic_overlap(point, frame(25, 44)) == 0.0

def test_the_career_and_city_are_carried_onto_every_person():
    region = G.Region(gender="female", age_min=45, age_max=60)
    p = G._to_disposition(_type(), region).demographic_bundles[0].point
    assert p.occupation_hint == "runs a tailoring business from home"
    assert p.geography == "Nagpur / tier-3 town"

# ---- the region is a boundary, not a suggestion --------------------------

def test_a_person_outside_the_region_is_dropped(capsys):
    """⚠ They could never be selected by the buy that paid to write them, and
    they still cost a render and still dilute the grid."""
    region = G.Region(gender="female", age_min=45, age_max=60)
    out = G._convert([_type(label="inside", age=52),
                      _type(label="too_young", age=30),
                      _type(label="wrong_gender", gender="male", age=52)], region)
    assert [d.label for d in out] == ["inside"]
    assert "OUTSIDE the declared region" in capsys.readouterr().out

def test_region_containment_matches_what_the_engine_will_do():
    """`Region.contains` must agree with `panel.demographic_overlap`, or the
    generator writes people the panel then refuses to select."""
    region = G.Region(gender="female", age_min=45, age_max=60,
                      income_min=3.0, income_max=17.0)
    frame = DemographicPoint(gender="female", age_min=45, age_max=60,
                             income_lpa_min=3.0, income_lpa_max=17.0,
                             geography="any")
    for gender, age, income in (("female", 52, 5.4), ("female", 44, 5.4),
                                ("female", 52, 2.0), ("male", 52, 5.4),
                                ("female", 61, 5.4), ("female", 45, 3.0)):
        point = DemographicPoint(gender=gender, age_min=age, age_max=age,
                                 income_lpa_min=income, income_lpa_max=income,
                                 geography="x")
        assert region.contains(gender, age, income) == (
            demographic_overlap(point, frame) > 0), (gender, age, income)

# ---- refusals are answers, not gaps -------------------------------------

def test_a_refused_cell_counts_as_addressed_not_missing():
    grid = {"occasions": [{"key": "a"}, {"key": "b"}], "stances": ["s1", "s2"]}
    raw = [_type(occasion="a", stance="s1")]
    refusals = [{"occasion": "b", "stance": "s2", "reason": "nobody here does this"}]
    assert CHECK.gate_grid(raw, grid, refusals) == 0

def test_a_cell_that_is_both_filled_and_refused_is_a_failure():
    """POSITIVE CONTROL — the refusal path must not become a way to pass gate 4
    while contradicting itself."""
    grid = {"occasions": [{"key": "a"}], "stances": ["s1"]}
    raw = [_type(occasion="a", stance="s1")]
    refusals = [{"occasion": "a", "stance": "s1", "reason": "..."}]
    assert CHECK.gate_grid(raw, grid, refusals) > 0

def test_gate_people_rejects_a_band():
    """POSITIVE CONTROL for gate 5: a band must not sneak through as a person."""
    band = _type()
    band["bundles"] = [{"gender": "female", "age_min": 45, "age_max": 54,
                        "income_lpa_min": 4.0, "income_lpa_max": 8.0,
                        "geography": "x", "occupation_hint": "y",
                        "household_hint": "z", "weight": 1.0}]
    assert CHECK.gate_people([band], None) > 0
    assert CHECK.gate_people([_type()], None) == 0

# ---- the notes format Stage 3 selection will parse -----------------------

def test_notes_round_trip():
    """⚠ LOAD-BEARING FORMAT. `NamedDisposition` has no structural field for
    occasion/stance — adding one would move `panel_version` for every library on
    disk — so panel selection stratifies across the grid by reading these back."""
    region = G.Region(gender="female", age_min=45, age_max=60, tier="tier-3")
    notes = G.notes_for("desk_slump_4pm", "purist", region.key)
    assert G.parse_notes(notes) == {
        "occasion": "desk_slump_4pm", "stance": "purist", "region": region.key}

def test_notes_parsing_ignores_a_note_it_did_not_write():
    assert G.parse_notes("hand-authored by a human, 2026-08-01") == {}
    assert G.parse_notes("") == {}

def test_a_generated_disposition_carries_parseable_notes():
    region = G.Region(gender="male", age_min=25, age_max=34)
    d = G._to_disposition(
        _type(gender="male", age=30, occasion="post_workout", stance="skeptic"),
        region)
    assert G.parse_notes(d.notes) == {
        "occasion": "post_workout", "stance": "skeptic", "region": region.key}

def test_region_keys_are_distinct_across_regions():
    """Two regions must not collide, or an accumulated population cannot say
    which slice a buyer type was written for."""
    keys = {G.Region(gender=g, age_min=lo, age_max=hi, tier=t).key
            for g in ("any", "female", "male")
            for lo, hi in ((18, 24), (45, 60))
            for t in ("any", "tier-3")}
    assert len(keys) == 12


def test_the_same_stance_in_two_different_moments_is_not_a_duplicate():
    """⚠ MEASURED 2026-08-16, twice in a row on a 64-cell region. The eight
    distinctness axes have NO occasion component, so a pragmatist at the 4pm
    slump and a pragmatist on the road are FORCED onto one coordinate however
    differently they are written — arithmetic, not sloppiness, once 64 cells are
    drawn from eight stances.

    Safe because nothing downstream keys on the coordinate: `segment_key` groups
    L2 by LABEL and `persona_core_hash` digests the ANCHOR, and each cell's
    anchor is written for its own moment."""
    desk = _type(label="pragmatist_desk", occasion="desk_slump_4pm",
                 stance="pragmatist")
    road = _type(label="pragmatist_road", occasion="travel_and_commute",
                 stance="pragmatist")
    assert CHECK.distinctness_key(desk) != CHECK.distinctness_key(road)
    keep, drop = G._triage([desk, road])
    assert len(keep) == 2, f"two moments were culled as one opinion: {drop}"


def test_it_stays_strict_INSIDE_one_occasion():
    """POSITIVE CONTROL — widening by occasion must not switch the gate off.
    Two types in ONE moment sharing a coordinate and a gender really is one
    opinion written twice."""
    a = _type(label="a", occasion="desk_slump_4pm", stance="pragmatist")
    b = _type(label="b", occasion="desk_slump_4pm", stance="loyalist")
    keep, drop = G._triage([a, b])
    assert len(keep) == 1 and "duplicate opinion" in drop[0][1]


def test_gender_still_separates_within_one_occasion():
    """POSITIVE CONTROL — the earlier widening must survive this one."""
    w = _type(label="w", gender="female", occasion="desk_slump_4pm")
    m = _type(label="m", gender="male", occasion="desk_slump_4pm")
    assert len(G._triage([w, m])[0]) == 2
