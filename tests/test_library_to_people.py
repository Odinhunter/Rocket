"""The band -> people conversion, pinned by BEHAVIOUR.

⚠ WHY THIS FILE EXISTS. `scripts/convert_library_to_people.py` is what makes an
arbitrary customer-chosen age range work. The property that matters is not "the
output has point ranges" — it is that a buy which SHIFTS BY TWO YEARS still finds
the same people. The library's only two 45-plus women sat at 45 and 46, so a
`women 47-63` brief returned ZERO buyer types while `women 45-60` returned two.
Every test here drives `panel.audience_mass` rather than inspecting the shape,
because the shape is the means and selection is the end.

⚠ Every absence assertion below carries a POSITIVE CONTROL — an absence test on a
typo'd field name passes forever otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from agent.panel import audience_mass
from agent.vectors import (
    DemographicBundle, DemographicPoint, DispositionVector, NamedDisposition,
)
from convert_library_to_people import convert, to_people, _headcount


def _vec(**over) -> DispositionVector:
    base = dict(
        category_relationship="regular", brand_stance="loyalist",
        price_orientation="price_first", decision_driver="habit",
        category_involvement="low", prior_experience_valence="positive",
        channel_behavior="offline_first", life_stage="settled",
    )
    base.update(over)
    return DispositionVector(**base)


def _banded(age=(41, 50), income=(6.0, 12.0), gender="female") -> NamedDisposition:
    """One disposition holding one BAND — the shape the generator emits today."""
    return NamedDisposition(
        label="loyalist_monthly_tin", vector=_vec(), notes="occasion=x stance=y",
        anchor="a\n\nb\n\nc\n\nd\n\ne",
        demographic_bundles=[DemographicBundle(
            point=DemographicPoint(
                gender=gender, age_min=age[0], age_max=age[1],
                income_lpa_min=income[0], income_lpa_max=income[1],
                geography="Indore / tier-2 city",
                occupation_hint="runs the family stationery shop",
                household_hint="two kids in college"),
            weight=1.0)])


def _frame(gender="female", age=(45, 60), income=(0.0, 100.0)) -> DemographicPoint:
    return DemographicPoint(gender=gender, age_min=age[0], age_max=age[1],
                            income_lpa_min=income[0], income_lpa_max=income[1],
                            geography="any")


# ---- the property the whole conversion exists for -----------------------

def test_a_two_year_shift_in_the_brief_no_longer_empties_the_panel():
    """The measured defect: `women 45-60` reached 2 types and `women 47-63`
    reached 0, because the only 45-plus women in the library sat at 45 and 46.
    A band asserting 41-50 must be reachable from anywhere inside 41-50."""
    people = convert(_banded(age=(41, 50)))

    for lo, hi in ((41, 50), (45, 60), (47, 63), (43, 46), (48, 55)):
        assert audience_mass(people, [_frame(age=(lo, hi))]) > 0, (
            f"a 41-50 band produced nobody reachable from {lo}-{hi}")

    # POSITIVE CONTROL — the filter is real, not a function that says yes.
    assert audience_mass(people, [_frame(age=(18, 24))]) == 0
    assert audience_mass(people, [_frame(age=(60, 75))]) == 0
    assert audience_mass(people, [_frame(gender="male")]) == 0


def test_one_person_per_band_would_fail_that(monkeypatch):
    """MUTATION PROOF. Collapse the band to a single person and the shift test
    above must break — otherwise it is passing for some unrelated reason."""
    monkeypatch.setattr("convert_library_to_people._headcount", lambda lo, hi: 1)
    people = convert(_banded(age=(41, 50)))
    reachable = [
        (lo, hi) for lo, hi in ((41, 50), (45, 60), (47, 63), (43, 46), (48, 55))
        if audience_mass(people, [_frame(age=(lo, hi))]) > 0
    ]
    assert len(reachable) < 5, (
        "a single person covered every sub-range of a 10-year band, so the "
        "stratification this file pins is not what makes the shift test pass")


# ---- the invariants a conversion must not break -------------------------

def test_every_produced_demographic_is_a_person_not_a_band():
    people = convert(_banded())
    assert people.demographic_bundles
    for b in people.demographic_bundles:
        assert b.point.age_min == b.point.age_max
        assert b.point.income_lpa_min == b.point.income_lpa_max
    # POSITIVE CONTROL — the input really was a band, so this could have failed.
    src = _banded().demographic_bundles[0].point
    assert src.age_min != src.age_max


def test_the_disposition_s_total_weight_is_unchanged():
    """This redistributes a population; it must never re-weight one. A band
    split into three people that each kept weight 1.0 would triple that
    opinion's share of the panel."""
    src = _banded()
    out = convert(src)
    assert sum(b.weight for b in out.demographic_bundles) == sum(
        b.weight for b in src.demographic_bundles)
    assert len(out.demographic_bundles) > len(src.demographic_bundles)


def test_the_opinion_itself_is_never_touched():
    """WHO holds an opinion changes here; WHAT the opinion is must not — else a
    conversion could move a verdict by editing what the panel thinks."""
    src = _banded()
    out = convert(src)
    assert out.anchor == src.anchor
    assert out.vector.to_dict() == src.vector.to_dict()
    assert out.notes == src.notes
    assert out.label == src.label
    assert out.authored_for == src.authored_for


def test_the_career_and_household_survive_the_conversion():
    """`_clip_point` used to strand these; a point makes clipping the identity,
    but only if the conversion carries them across."""
    for b in convert(_banded()).demographic_bundles:
        assert b.point.occupation_hint == "runs the family stationery shop"
        assert b.point.household_hint == "two kids in college"
        assert b.point.geography == "Indore / tier-2 city"


def test_conversion_is_deterministic():
    """Two runs over one input must install one library, or no run made against
    it can ever be reproduced."""
    a = [b.point.to_dict() for b in convert(_banded()).demographic_bundles]
    b = [x.point.to_dict() for x in convert(_banded()).demographic_bundles]
    assert a == b


def test_age_and_income_move_together_within_a_band():
    """`DemographicBundle`'s contract is internal coherence. Drawing age and
    income independently mints the 49-year-old on a starter salary inside the
    same career as the 43-year-old at the top of the band."""
    people = to_people(_banded(age=(41, 50), income=(6.0, 12.0))
                       .demographic_bundles[0], "lbl", 0)
    assert len(people) >= 3
    by_age = sorted(people, key=lambda b: b.point.age_min)
    incomes = [b.point.income_lpa_min for b in by_age]
    assert incomes == sorted(incomes), (
        f"income does not rise with age inside one career: {incomes}")


def test_people_from_one_band_are_distinct_and_stay_inside_it():
    src = _banded(age=(41, 50)).demographic_bundles[0]
    people = to_people(src, "lbl", 0)
    ages = [b.point.age_min for b in people]
    assert len(set(ages)) == len(ages), f"two people share an age: {ages}"
    assert all(41 <= a <= 50 for a in ages), f"someone escaped the band: {ages}"


def test_a_narrow_band_yields_one_person_and_a_wide_one_yields_several():
    assert _headcount(30, 32) == 1
    assert _headcount(41, 50) >= 3
    assert _headcount(18, 75) <= 4, "headcount must stay bounded"


# ---- the integration: does the PRODUCT build a panel of these people? ----

def _runnable_spec(dispositions, frame):
    """The smallest spec `build_panel` will accept, aimed at one frame."""
    from agent.entities import AudienceSpec
    from agent.vectors import (
        ChaosDistribution, ChaosProfile, ChaosVector, ContextVector, NamedContext,
    )
    chaos = ChaosDistribution(weighted=[
        (ChaosProfile(label=n, vector=ChaosVector(
            decision_velocity=n, suggestibility="medium",
            consistency="variable", risk_tolerance="balanced")), w)
        for n, w in (("impulsive", 0.2), ("moderate", 0.5), ("deliberate", 0.3))])
    ctxs = [NamedContext(label=f"ctx_{i}", vector=ContextVector(
        attention_level="low", device_posture="commute",
        intent_state="killing_time", energy_state="drained",
        social_setting="public")) for i in range(3)]
    return AudienceSpec(
        demographics=[frame],
        disposition_labels=[d.label for d in dispositions],
        context_envelope=ctxs, chaos_distribution=chaos, panel_size=60)


def test_build_panel_over_point_people_clips_nobody_and_strands_no_career():
    """⚠ THE INTEGRATION NOTHING ELSE COVERS. Every other test here checks
    selection arithmetic (`audience_mass`, `demographic_overlap`); this drives
    the real panel builder, which is where `_clip_point` used to turn a person
    into a band and strand their career outside the buy."""
    from agent.panel import audience_mass, build_panel

    dispositions = [convert(_banded(age=(41, 50))),
                    convert(_banded(age=(24, 33), gender="male"))]
    dispositions[1].label = "loyalist_other"

    for lo, hi, gender in ((45, 60, "female"), (47, 63, "female"), (24, 33, "male")):
        frame = _frame(gender=gender, age=(lo, hi))
        spec = _runnable_spec(dispositions, frame)
        reach = sum(1 for d in dispositions if audience_mass(d, [frame]) > 0)
        panel = build_panel(spec, dispositions, category="coffee", seed=71,
                            marketer_led=True)

        assert len({a.disposition.label for a in panel}) == reach, (
            f"the panel disagrees with the reach number shown before paying "
            f"({lo}-{hi})")
        for a in panel:
            p = a.demographic
            assert p.age_min == p.age_max, "an agent was clipped back into a band"
            assert lo <= p.age_min <= hi, "an agent sits outside the declared buy"
            assert p.occupation_hint, "a career was stranded off the agent"
            assert p.geography == "Indore / tier-2 city"
