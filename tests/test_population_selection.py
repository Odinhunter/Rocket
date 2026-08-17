"""Who is eligible for a buy, and who gets one of the run's limited seats.

⚠ WHY THIS FILE EXISTS. A library is uncapped; a run carries at most
`AUDIENCE_DISPOSITION_CAP` buyer types. Before `agent/population.py` nothing
chose between them — a saved audience listed the whole library, which only
worked while the library was small. Two things can go wrong quietly here: the
tier filter can be a no-op that nobody notices (geography was ignored entirely
until 2026-08-16), and selection can hand a whole run to one demand space.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import population
from agent.vectors import (
    DemographicBundle, DemographicPoint, DispositionVector, NamedDisposition,
)


def _vec(**over) -> DispositionVector:
    base = dict(category_relationship="regular", brand_stance="loyalist",
                price_orientation="price_first", decision_driver="habit",
                category_involvement="low", prior_experience_valence="positive",
                channel_behavior="offline_first", life_stage="settled")
    base.update(over)
    return DispositionVector(**base)


def _person(label, occasion="desk_slump_4pm", stance="loyalist", age=52,
            gender="female", income=5.4, geography="Nagpur / tier-3 town",
            region=None):
    # ⚠ The region key must AGREE with the geography, or the fixture is a person
    # who cannot exist: `population.region_tier` reads the tier a type was
    # written for and prefers it over parsing the city string, so a "Mumbai /
    # metro" person whose notes say `_t3` would be a test asserting on a
    # contradiction rather than on the filter.
    if region is None:
        tier = (population.tiers_in(geography) or {"a"}).pop()
        region = f"f45-60_0-100_t{tier}"
    return NamedDisposition(
        label=label, vector=_vec(), anchor="a\n\nb\n\nc\n\nd\n\ne",
        notes=population.notes_for(occasion, stance, region),
        demographic_bundles=[DemographicBundle(
            point=DemographicPoint(
                gender=gender, age_min=age, age_max=age,
                income_lpa_min=income, income_lpa_max=income,
                geography=geography, occupation_hint="tailor",
                household_hint="two kids"),
            weight=1.0)])


def _frame(geography="all india", gender="female", age=(45, 60)):
    return DemographicPoint(gender=gender, age_min=age[0], age_max=age[1],
                            income_lpa_min=0, income_lpa_max=100,
                            geography=geography)


# ---- tier: it was ignored entirely until 2026-08-16 ---------------------

def test_a_tier_3_buy_excludes_the_metro_person():
    """⚠ THE MEASURED DEFECT. `demographic_overlap` matches gender x age x
    income only, so 'women in tier-3 cities' selected metro people and the read
    then described the buy as tier-3. This is the check that it no longer does."""
    tier3 = _person("t3", geography="Nagpur / tier-3 town")
    metro = _person("metro", geography="Mumbai / metro")

    got = population.eligible([tier3, metro], [_frame("tier-2 and tier-3")])
    assert [d.label for d in got] == ["t3"]

    # POSITIVE CONTROL — both are otherwise perfectly eligible, so the filter
    # above is doing the work and not some unrelated exclusion.
    both = population.eligible([tier3, metro], [_frame("all india")])
    assert {d.label for d in both} == {"t3", "metro"}


def test_a_metro_buy_excludes_the_tier_3_person():
    got = population.eligible([_person("t3", geography="Nagpur / tier-3 town"),
                               _person("m", geography="Mumbai / metro")],
                              [_frame("metro tier-1")])
    assert [d.label for d in got] == ["m"], "a metro buy kept a tier-3 person"


def test_an_unknown_tier_fails_OPEN():
    """⚠ A person written as a bare city name has no tier token. Dropping them
    would shrink a panel because of how a generator phrased a string — so
    unknown passes, and only a DEFINITE mismatch excludes."""
    got = population.eligible([_person("bare", geography="Kanpur")],
                              [_frame("metro tier-1")])
    assert [d.label for d in got] == ["bare"]


def test_metro_counts_as_tier_1():
    assert population.tier_compatible("Mumbai / metro", "metro tier-1")
    assert population.tier_compatible("Pune / tier-1 city", "metro tier-1")
    assert not population.tier_compatible("Mumbai / metro", "tier-2 and tier-3")


def test_tier_never_overrides_the_demographic_frame():
    """POSITIVE CONTROL for the whole filter: tier is ADDITIONAL, never a way
    back in for someone the age/gender/income frame already excluded."""
    young = _person("young", age=28, geography="Nagpur / tier-3 town")
    assert population.eligible([young], [_frame("tier-2 and tier-3")]) == []


# ---- selection: seats spread across demand spaces -----------------------

OCCASIONS = ["desk_slump_4pm", "late_night_craving", "post_workout",
             "breakfast_on_the_run"]


def _library(per_occasion=5):
    return [_person(f"{o}_{i}", occasion=o, stance=f"s{i}")
            for o in OCCASIONS for i in range(per_occasion)]


def test_a_thin_buy_runs_as_is_and_is_never_padded_or_refused():
    """⚠ THE USER'S EXPLICIT CALL, 2026-08-15: we never tell a customer to widen
    the buy. Two eligible people is a two-person panel, not an error."""
    lib = _library()[:2]
    got = population.select(lib, [_frame()], budget=64)
    assert len(got) == 2
    assert population.select([], [_frame()], budget=64) == []


def test_seats_spread_across_occasions_rather_than_filling_one():
    """⚠ Taking the first N in library order hands a run to whichever occasions
    the generator wrote first — which is exactly how `--count 40` against a
    64-cell grid produced a library with no purist, pragmatist or gifter."""
    got = population.select(_library(per_occasion=5), [_frame()], budget=8)
    assert len(got) == 8
    by_occasion = {}
    for d in got:
        occ = population.parse_notes(d.notes)["occasion"]
        by_occasion[occ] = by_occasion.get(occ, 0) + 1
    assert set(by_occasion) == set(OCCASIONS), (
        f"an occasion got no seat at all: {by_occasion}")
    assert max(by_occasion.values()) - min(by_occasion.values()) <= 1, by_occasion


def test_library_order_alone_would_have_failed_that():
    """MUTATION PROOF — the naive selection this replaced."""
    naive = _library(per_occasion=5)[:8]
    occs = {population.parse_notes(d.notes)["occasion"] for d in naive}
    assert len(occs) < len(OCCASIONS), (
        "the fixture is not ordered by occasion, so the test above proves "
        "nothing about stratification")


def test_selection_is_deterministic_and_within_budget():
    lib = _library(per_occasion=5)
    a = [d.label for d in population.select(lib, [_frame()], budget=7)]
    b = [d.label for d in population.select(lib, [_frame()], budget=7)]
    assert a == b and len(a) == 7


def test_selection_only_ever_returns_eligible_people():
    """POSITIVE CONTROL — stratifying must not smuggle back someone the frame
    excluded."""
    lib = _library() + [_person("metro_guy", geography="Mumbai / metro"),
                        _person("too_young", age=28)]
    got = population.select(lib, [_frame("tier-2 and tier-3")], budget=64)
    labels = {d.label for d in got}
    assert "metro_guy" not in labels and "too_young" not in labels


def test_a_hand_authored_note_is_not_mis_parsed():
    """A library predating generated notes has a human's curator note; it must
    fall into the unknown bucket rather than being read as a grid position."""
    hand = _person("hand")
    hand.notes = "authored 2026-08-01 by a human; watch the price sensitivity"
    assert population.parse_notes(hand.notes) == {}
    got = population.select([hand] + _library(), [_frame()], budget=3)
    assert len(got) == 3


# ---- accumulation: a population grows, it is never replaced ---------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from install_generated_audience import _merge  # noqa: E402


def test_appending_a_region_keeps_the_one_already_there():
    """⚠ Each generation covers ONE demographic region, and a brand's population
    is the union of every region anyone has bought against. Replacing throws
    away the region the previous customer paid for."""
    metro = [_person("skeptic_no_sugar", geography="Mumbai / metro", age=28)]
    tier3 = [_person("loyalist_tin", geography="Nagpur / tier-3 town")]
    merged = _merge(metro, tier3)
    assert [d.label for d in merged] == ["skeptic_no_sugar", "loyalist_tin"]


def test_a_label_collision_across_regions_is_renamed_not_dropped():
    """⚠ `skeptic_no_sugar` is a good name for a 26-year-old in Mumbai AND for a
    52-year-old in Nagpur. They are the same stance in two different lives —
    which is the whole reason generation is region-scoped — but
    `DispositionLibrary.validate()` rejects duplicate labels."""
    existing = [_person("skeptic_no_sugar", geography="Mumbai / metro", age=28)]
    incoming = [_person("skeptic_no_sugar", geography="Nagpur / tier-3 town")]
    merged = _merge(existing, incoming)

    assert len(merged) == 2, "the second region's buyer type was dropped"
    labels = [d.label for d in merged]
    assert len(set(labels)) == 2, f"duplicate labels survived: {labels}"
    assert labels[0] == "skeptic_no_sugar"
    assert labels[1].startswith("skeptic_no_sugar__")

    # The renamed one must still be the tier-3 person, not a copy of the metro one.
    assert merged[1].demographic_bundles[0].point.geography == "Nagpur / tier-3 town"


def test_repeated_collisions_still_produce_unique_labels():
    """POSITIVE CONTROL — three regions with one shared name must give three
    labels, or `DispositionLibrary.validate()` refuses the whole population."""
    pop = []
    for geo in ("Mumbai / metro", "Nagpur / tier-3 town", "Pune / tier-1 city"):
        pop = _merge(pop, [_person("skeptic_no_sugar", geography=geo)])
    assert len({d.label for d in pop}) == 3, [d.label for d in pop]


def test_merging_into_an_empty_population_changes_nothing():
    incoming = [_person("a"), _person("b")]
    assert [d.label for d in _merge([], incoming)] == ["a", "b"]


# ---- the fabrication that used to fill an unmatched buy -------------------

def test_a_buy_that_matches_nobody_raises_instead_of_inventing_people():
    """⚠ THE WORST OF THE MEASURED DEFECTS. `women 55-75, tier-3` against a
    library whose oldest person was 53 used to build 100 agents across ALL 32
    buyer types — each one a blank shell carrying the declared FRAME as its
    identity, with no occupation, no household and no city. No error was raised,
    and the panel looked FULLER the worse the mismatch got, because a partial
    match excludes types while a total mismatch excluded none.

    Selection is what prevents it in practice; this pins the floor underneath.
    """
    from agent.entities import AudienceSpec
    from agent.panel import build_panel
    from agent.vectors import (
        ChaosDistribution, ChaosProfile, ChaosVector, ContextVector, NamedContext,
    )
    lib = _library()
    unmatched = _frame(age=(70, 75))           # nobody in the fixture is 70+
    assert population.select(lib, [unmatched], budget=64) == []

    spec = AudienceSpec(
        demographics=[unmatched],
        disposition_labels=[d.label for d in lib],
        context_envelope=[NamedContext(label=f"c{i}", vector=ContextVector(
            attention_level="low", device_posture="commute",
            intent_state="killing_time", energy_state="drained",
            social_setting="public")) for i in range(3)],
        chaos_distribution=ChaosDistribution(weighted=[
            (ChaosProfile(label=n, vector=ChaosVector(
                decision_velocity=n, suggestibility="medium",
                consistency="variable", risk_tolerance="balanced")), w)
            for n, w in (("impulsive", 0.2), ("moderate", 0.5), ("deliberate", 0.3))]),
        panel_size=30)

    try:
        panel = build_panel(spec, lib, category="coffee", seed=71, marketer_led=True)
    except ValueError as exc:
        assert "no real people" in str(exc)
        return
    blanks = [a for a in panel if not a.demographic.occupation_hint]
    raise AssertionError(
        f"a buy matching nobody built {len(panel)} agents, {len(blanks)} of them "
        f"blank shells, instead of refusing to invent them")


def test_a_library_with_no_bundles_at_all_still_runs():
    """POSITIVE CONTROL — a demographically UNSPECIFIED library legitimately
    lives everywhere, and the guard above must not break it. `audience_mass`
    returns 1.0 for those, and they are simulated at the declared frames."""
    from agent.panel import _clipped_bundle_points
    unspecified = NamedDisposition(label="anyone", vector=_vec(), anchor="a")
    points, weights = _clipped_bundle_points(unspecified, [_frame()])
    assert len(points) == 1 and weights == [1.0]


def test_a_type_holding_people_in_several_cities_brings_only_the_matching_ones():
    """⚠ MEASURED 2026-08-16. Gating the TYPE is not enough. A buyer type holds
    several people across several cities, so keeping the whole type because ONE
    of its people is tier-2 let every metro sibling into the room behind them —
    a "smaller towns" buy simulated a panel living in Mumbai and metro NCR while
    the report described the buy as tier-2/3."""
    mixed = _person("mixed", region="a18-75_0-100_ta")
    mixed.demographic_bundles = [
        _person("x", geography=g).demographic_bundles[0]
        for g in ("Nagpur / tier-3 town", "Mumbai / metro", "Indore / tier-2 city")
    ]
    got = population.eligible([mixed], [_frame("tier-2 and tier-3")])
    assert len(got) == 1, "the mixed type was dropped entirely"
    cities = [b.point.geography for b in got[0].demographic_bundles]
    assert len(cities) == 2, f"the metro person came along: {cities}"
    assert not any("metro" in c for c in cities), cities

    # POSITIVE CONTROL — an unscoped buy keeps all three.
    assert len(population.eligible([mixed], [_frame("all india")])[0]
               .demographic_bundles) == 3


def test_narrowing_never_mutates_the_library():
    """⚠ The library is a shared, loaded entity. Narrowing a copy is fine;
    narrowing in place would silently shrink the brand's population for every
    later buy in the same process."""
    mixed = _person("mixed", region="a18-75_0-100_ta")
    mixed.demographic_bundles = [
        _person("x", geography=g).demographic_bundles[0]
        for g in ("Nagpur / tier-3 town", "Mumbai / metro")
    ]
    population.eligible([mixed], [_frame("tier-2 and tier-3")])
    assert len(mixed.demographic_bundles) == 2, "the library itself was narrowed"


def test_the_region_a_type_was_written_for_beats_a_vague_city_string():
    """"Mumbai suburb" carries neither the word metro nor a tier token, so text
    parsing alone fails open and lets it into a smaller-towns buy. A type
    generated for a tier-1 region IS tier-1, whatever its author called the
    town."""
    vague = _person("vague", geography="Mumbai suburb", region="a18-75_0-100_t1")
    assert population.eligible([vague], [_frame("tier-2 and tier-3")]) == []
    # POSITIVE CONTROL — with no region recorded, the vague string fails open.
    legacy = _person("legacy", geography="Mumbai suburb")
    legacy.notes = "hand-authored"
    assert len(population.eligible([legacy], [_frame("tier-2 and tier-3")])) == 1
