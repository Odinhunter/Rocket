"""The four questions a media buyer answers, and what they do to the panel.

⚠ The first test in this file is the one that matters. Before 2026-08-04 the
form asked for an audience `.json` filename; it now asks for an age range, a
gender, an income band and a location, and the entire justification for that is
that those answers CHANGE THE PANEL. If they did not, the form would be a
facade that collects input and discards it — a far worse honesty failure than
any of the caveats removed on the same day, because it only surfaces after a
customer has trusted a read.

So the propagation is pinned here as a permanent test rather than checked once
by hand while building it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.entities import AudienceSpec, DispositionLibrary
from agent.panel import build_panel
from server import audience_form
from server.app import create_app
from server.runs import discover_brands
from tests.helpers_auth import demo_auth, sign_in
from tests.helpers_brand import ANSWERS, BRAND, build_brand


@pytest.fixture
def world(tmp_path: Path) -> Path:
    build_brand(tmp_path / "runs")
    return tmp_path


def _brand(world: Path):
    brands = discover_brands(world / "runs", account="demo")
    assert brands, "fixture built no runnable brand"
    return brands[0]


# ---- the load-bearing one ---------------------------------------------


def test_the_answers_actually_change_who_gets_simulated(world) -> None:
    """⚠ The justification for the whole form. Two buys, identical but for the
    answers, must produce genuinely different panels.

    Asserted on the AGENTS `build_panel` returns, not on the spec that goes
    into it: a spec that carries the right demographics and a panel builder
    that ignores them is exactly the facade this rules out, and only the second
    half is visible from the agents.

    Four properties, because any one alone is weak — the consumer types
    simulated, their ages, their genders and their incomes.
    """
    brand = _brand(world)
    dispositions = list(brand.dispositions)

    def panel(**answers):
        parsed = audience_form.parse({**ANSWERS, **answers})
        spec = audience_form.build_spec(brand.template, parsed)
        return build_panel(spec, dispositions,
                           category="health_wellness_nutrition",
                           marketer_led=True, seed=71)

    young = panel(age_from="18", age_to="24", gender="male", income="0:3.5")
    older = panel(age_from="45", age_to="75", gender="female", income="40:100")

    assert {a.disposition.label for a in young} != {a.disposition.label
                                                    for a in older}, \
        "the same consumer types were simulated for two unrelated buys"
    assert {a.demographic.gender for a in young} == {"male"}
    assert {a.demographic.gender for a in older} == {"female"}
    assert max(a.demographic.age_max for a in young) <= 24
    assert min(a.demographic.age_min for a in older) >= 45
    assert max(a.demographic.income_lpa_max for a in young) <= 3.5
    assert min(a.demographic.income_lpa_min for a in older) >= 40.0
    print("  the four answers reach the simulated agents, not just the spec ✓")


def test_the_library_supplies_the_life_detail_the_form_never_asks_for(world) -> None:
    """The form asks four questions and no more, and this is why that is
    enough: occupation and household come from the brand's own hand-built
    bundles, through `panel._clip_point`, which takes them from the persona
    rather than from the declared frame.

    Pinned because the alternative that was seriously considered — a
    hand-authored hint table per age-band per income-band per category — would
    have been days of authoring per category, on the critical path, inventing
    a buyer's life on their behalf. It is unnecessary, and this is the fact
    that makes it unnecessary.
    """
    brand = _brand(world)
    parsed = audience_form.parse(ANSWERS)
    frame = parsed.to_point()
    assert frame.occupation_hint == "" and frame.household_hint == "", \
        "the form started asking for life detail it has no business asking for"

    agents = build_panel(audience_form.build_spec(brand.template, parsed),
                         list(brand.dispositions),
                         category="health_wellness_nutrition",
                         marketer_led=True, seed=71)
    assert all(a.demographic.occupation_hint for a in agents), \
        "agents lost their occupation — the personas are now blank"
    assert all(a.demographic.household_hint for a in agents)
    print("  occupation and household come from the library, not the form ✓")


def test_building_a_spec_does_not_re_aim_the_brands_saved_audience(world) -> None:
    """The template is a saved entity shared by every future run of the brand.
    Mutating it would quietly re-aim all of them at whatever the last person
    typed."""
    brand = _brand(world)
    before = json.dumps(brand.template.to_dict(), sort_keys=True)
    audience_form.build_spec(brand.template, audience_form.parse(
        {**ANSWERS, "age_from": "18", "age_to": "24"}))
    assert json.dumps(brand.template.to_dict(), sort_keys=True) == before, \
        "build_spec mutated the brand's saved audience"
    print("  the saved audience survives a run being composed from it ✓")


def test_the_spec_inherits_everything_the_customer_cannot_author(world) -> None:
    """The split the design turns on: they supply demographics, the brand
    supplies the rest. A regression either way is serious — inheriting
    demographics ignores their answers, and asking for the rest asks them to do
    our research."""
    brand = _brand(world)
    spec = audience_form.build_spec(brand.template, audience_form.parse(ANSWERS))
    assert len(spec.demographics) == 1, "one buy, one declared frame"
    for field in ("disposition_labels", "context_envelope", "panel_size",
                  "cycle_mix"):
        assert getattr(spec, field) == getattr(brand.template, field), \
            f"{field} was not inherited from the brand's saved audience"
    assert spec.chaos_distribution.to_dict() == \
        brand.template.chaos_distribution.to_dict()
    print("  demographics are theirs; everything else is the brand's ✓")


# ---- the sentence the classifier also reads ---------------------------


def test_the_targeting_sentence_reads_as_english_in_every_band() -> None:
    """`declared_targeting` is read by a person on the read AND by `target_id`
    when it classifies which consumer types the ad aims at, so a malformed one
    is not merely ugly.

    The open-ended bands are the cases that broke: formatting both bounds
    unconditionally produced "₹0-3.5 LPA" for the lowest and "₹40-40+ LPA" for
    the highest, which is not a range at all.
    """
    def sentence(**kw):
        return audience_form.parse({**ANSWERS, **kw}).declared_targeting()

    assert sentence() == "adults 25-44, metro tier-1, ₹7-17L household income"
    assert sentence(gender="female") .startswith("women 25-44")
    assert sentence(gender="male").startswith("men 25-44")
    # 65+ is a display convention: the oldest library bundle runs to 75, so the
    # value is 75 and only the wording says 65+.
    assert sentence(age_to="75").startswith("adults 25-65+")
    assert sentence(income="0:3.5").endswith("under ₹3.5L household income")
    assert sentence(income="40:100").endswith("₹40L+ household income")
    # "Any income" narrows nothing, so claiming an income band would be a lie
    # to the classifier as much as to the reader.
    assert "income" not in sentence(income="0:100")
    print("  the targeting sentence reads correctly in all five bands ✓")


# ---- answers that did not come from the dropdowns ---------------------


def test_answers_are_validated_against_the_vocabulary_not_merely_coerced() -> None:
    """These arrive from an HTTP POST. The `<select>` that constrains them in a
    browser is absent from a direct post, and every value below is one the form
    can never produce."""
    bad = {
        "an age off the list": {"age_from": "31"},
        "an age that is not a number": {"age_from": "old"},
        "a reversed range": {"age_from": "45", "age_to": "24"},
        "an invented gender": {"gender": "other-value"},
        "an invented income band": {"income": "0:999"},
        "an income that is not a band": {"income": "lots"},
        "an invented location": {"geography": "the moon"},
    }
    for name, answers in bad.items():
        with pytest.raises(audience_form.AudienceAnswerError):
            audience_form.parse({**ANSWERS, **answers})
    # And the message is written for the customer, not about a field id.
    try:
        audience_form.parse({**ANSWERS, "gender": "nonsense"})
    except audience_form.AudienceAnswerError as exc:
        assert "gender" in str(exc).lower() and "_" not in str(exc)
    print(f"  {len(bad)} hand-posted answers refused ✓")


def test_an_empty_answer_falls_back_rather_than_failing() -> None:
    """A missing field is not hostile input — it is a GET of the form, or a
    browser that omitted an untouched select. Defaults, not an error page."""
    parsed = audience_form.parse({})
    assert (parsed.age_from, parsed.age_to) == (25, 44)
    assert parsed.gender == "any"
    print("  empty answers fall back to the defaults ✓")


# ---- reach ------------------------------------------------------------


def test_reach_reports_what_the_panel_builder_will_actually_do(world) -> None:
    """The number shown before paying and the panel built afterwards must come
    from ONE calculation. Two would drift, and the drift would show up as a
    promise the run did not keep — so this asserts against `build_panel`'s own
    output rather than against a second implementation of the overlap.
    """
    brand = _brand(world)
    for answers in ({"age_from": "18", "age_to": "24", "gender": "male",
                     "income": "0:3.5"},
                    {"age_from": "18", "age_to": "75", "income": "0:100"}):
        parsed = audience_form.parse({**ANSWERS, **answers})
        spec = audience_form.build_spec(brand.template, parsed)
        promised = audience_form.reach(spec, list(brand.dispositions))
        actual = {a.disposition.label for a in build_panel(
            spec, list(brand.dispositions),
            category="health_wellness_nutrition", marketer_led=True, seed=71)}
        assert set(promised.labels) == actual, (
            f"promised {sorted(promised.labels)}, ran {sorted(actual)}")
    print("  the reach shown before paying is the panel that gets built ✓")


def test_a_narrow_buy_says_so_plainly_and_a_wide_one_does_not(world) -> None:
    """The narrow case is worth saying at the point of CHOOSING — a ~$4 read of
    a single consumer type is a poor use of the money, and saying so after the
    run costs them the run.

    In the neutral register the rest of the product now uses: a fact they can
    act on, never a warning. The absence of alarm words is asserted because the
    same sentence written as a flag is what the 2026-08-04 change removed
    everywhere else.
    """
    brand = _brand(world)

    def line(**kw):
        parsed = audience_form.parse({**ANSWERS, **kw})
        return audience_form.reach(
            audience_form.build_spec(brand.template, parsed),
            list(brand.dispositions)).sentence

    narrow = line(age_from="18", age_to="24", gender="male", income="0:3.5")
    assert "1 of 3 consumer types" in narrow
    assert "a wider buy gives you more to compare" in narrow

    wide = line(age_from="18", age_to="75", income="0:100")
    assert "3 of 3 consumer types" in wide
    assert "wider buy" not in wide, "a full-coverage buy was told to widen"

    for alarm in ("warning", "caution", "too narrow", "problem", "error"):
        assert alarm not in narrow.lower(), f"the reach line reads as a flag: {alarm!r}"
    print("  narrow buys are named plainly; wide ones are left alone ✓")


def test_a_buy_that_reaches_nobody_says_what_to_do(world) -> None:
    """Zero is the one answer the customer cannot act on without being told
    how. A bare "reaches 0 of 3" is a dead end."""
    brand = _brand(world)
    # Men, 45-65+, under ₹3.5L: no bundle in the fixture library overlaps it.
    parsed = audience_form.parse({**ANSWERS, "age_from": "45", "age_to": "75",
                                  "gender": "male", "income": "0:3.5"})
    line = audience_form.reach(audience_form.build_spec(brand.template, parsed),
                               list(brand.dispositions)).sentence
    assert "doesn't overlap" in line and "widen" in line, line
    print("  a buy that reaches nobody says how to fix it ✓")


# ---- the endpoint behind the live line --------------------------------


def test_the_reach_endpoint_answers_in_words_even_when_asked_badly(world) -> None:
    """It feeds one line of text beside a form. A 4xx here would replace
    guidance with nothing at the moment it is most useful, so every case
    answers 200 with something readable — including the hostile ones, which
    must not leak a stack trace or a path into that line."""
    client = sign_in(TestClient(create_app(
        runs_root=world / "runs", sessions_root=world / "s", base_dir=world,
        uploads_dir=world / "uploads", auth=demo_auth())))

    good = client.get("/reads/audience-reach", params=ANSWERS)
    assert good.status_code == 200
    assert "consumer types" in good.json()["sentence"]
    assert good.json()["targeting"].startswith("adults 25-44")

    for params in ({**ANSWERS, "gender": "nonsense"},
                   {**ANSWERS, "age_from": "999"},
                   {**ANSWERS, "brand": "../../etc"},
                   {}):
        resp = client.get("/reads/audience-reach", params=params)
        assert resp.status_code == 200, f"{params} produced {resp.status_code}"
        sentence = resp.json()["sentence"]
        assert "Traceback" not in sentence and "/" not in sentence, sentence
    print("  the reach endpoint always answers in words ✓")


def test_the_form_renders_the_reach_without_javascript(world) -> None:
    """Progressive enhancement, asserted. The live update is a nicety; the
    server renders the same sentence into the page so the fact survives with
    scripting blocked."""
    client = sign_in(TestClient(create_app(
        runs_root=world / "runs", sessions_root=world / "s", base_dir=world,
        uploads_dir=world / "uploads", auth=demo_auth())))
    page = client.get("/reads/new").text
    assert "consumer types" in page, \
        "the reach line exists only in JavaScript"
    assert 'id="reach"' in page
    print("  the reach line is server-rendered, not JS-only ✓")
