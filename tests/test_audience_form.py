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


def _seated(brand, spec):
    """The dispositions the spec actually names, in its own order.

    ⚠ Since 2026-08-16 `build_spec` SELECTS: a library is uncapped and grows
    with every generated region, while a run carries at most
    `AUDIENCE_DISPOSITION_CAP` buyer types, so the spec names the seats rather
    than the whole library. `build_panel` refuses a disposition list that does
    not match those labels, and this is the same resolve step
    `RunService.prepare` does via `DispositionLibrary.resolve`. A test handing
    it the full library is testing a call the product never makes.
    """
    by_label = {d.label: d for d in brand.dispositions}
    return [by_label[label] for label in spec.disposition_labels]


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
        spec = audience_form.build_spec(brand.template, parsed, brand.dispositions)
        return build_panel(spec, _seated(brand, spec),
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

    spec = audience_form.build_spec(brand.template, parsed, brand.dispositions)
    agents = build_panel(spec, _seated(brand, spec),
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
        {**ANSWERS, "age_from": "18", "age_to": "24"}), brand.dispositions)
    assert json.dumps(brand.template.to_dict(), sort_keys=True) == before, \
        "build_spec mutated the brand's saved audience"
    print("  the saved audience survives a run being composed from it ✓")


def test_the_spec_inherits_everything_the_customer_cannot_author(world) -> None:
    """The split the design turns on: they supply demographics, the brand
    supplies the rest. A regression either way is serious — inheriting
    demographics ignores their answers, and asking for the rest asks them to do
    our research."""
    brand = _brand(world)
    spec = audience_form.build_spec(brand.template, audience_form.parse(ANSWERS),
                                    brand.dispositions)
    assert len(spec.demographics) == 1, "one buy, one declared frame"
    for field in ("context_envelope", "panel_size", "cycle_mix"):
        assert getattr(spec, field) == getattr(brand.template, field), \
            f"{field} was not inherited from the brand's saved audience"
    # ⚠ `disposition_labels` is deliberately NOT inherited since 2026-08-16. The
    # template lists what the brand HAS; the spec lists who this BUY reaches,
    # capped at the seats a run carries. Inheriting it is how a growing
    # population would have shipped a spec naming the entire library.
    assert set(spec.disposition_labels) <= set(brand.template.disposition_labels)
    assert spec.disposition_labels, "a buy with people in it named none of them"
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
    # ⚠ Open-ended phrasing is for the CEILING only, since 2026-08-16. It used
    # to be hard-coded to 75 — the old dropdown's top value — but age is free
    # entry now, so "45-63" must read as itself and only a buy that really runs
    # to the ceiling gets a "+". Describing a 63 buy as "65+" would mislead
    # `target_id` as much as the reader.
    assert sentence(age_to=str(audience_form.AGE_MAX)).startswith(
        f"adults 25-{audience_form.AGE_MAX}+")
    assert sentence(age_to="63").startswith("adults 25-63")
    assert sentence(age_to="75").startswith("adults 25-75")
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
        # ⚠ NOT "an age off the list" any more. Age became FREE ENTRY on
        # 2026-08-16 — 31 and 47 are ordinary buys and are asserted valid
        # below — so what is still rejected is a non-number, a reversed range,
        # and anything outside the sanity bounds.
        "an age below the floor": {"age_from": "12"},
        "an age above the ceiling": {"age_to": "140"},
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

    # POSITIVE CONTROL — the point of free entry. An age that is NOT one of the
    # five old dropdown boundaries must now be accepted, or the rejection loop
    # above is passing because everything is rejected.
    # ⚠ 47-63 is the exact buy that used to be unexpressible, and it is the one
    # that returned ZERO buyer types against a banded library.
    for ok in ({"age_from": "31", "age_to": "44"},
               {"age_from": "47", "age_to": "63"},
               {"age_from": "18", "age_to": "99"}):
        parsed = audience_form.parse({**ANSWERS, **ok})
        assert parsed.age_from == int(ok["age_from"])
        assert parsed.age_to == int(ok["age_to"])

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
        spec = audience_form.build_spec(brand.template, parsed, brand.dispositions)
        promised = audience_form.reach(spec, list(brand.dispositions))
        actual = {a.disposition.label for a in build_panel(
            spec, _seated(brand, spec),
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
            audience_form.build_spec(brand.template, parsed, brand.dispositions),
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
    line = audience_form.reach(audience_form.build_spec(brand.template, parsed, brand.dispositions),
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


# ---- the population a buy selects from --------------------------------

def test_a_buy_selects_from_the_whole_library_not_the_saved_audience(world: Path):
    """⚠⚠ THE DEFECT THAT MADE A NEWLY GENERATED REGION UNREACHABLE — fixed
    2026-08-19, and invisible until the day a second region existed.

    `BrandChoice.dispositions` carried `library.resolve(saved.spec.
    disposition_labels)` — the seats a saved audience named ONCE, chosen
    against whatever demographic frame the template happened to hold. But
    `build_spec` documents in its own signature that this argument "is the
    brand's WHOLE population — not the template's label list", because a
    library GROWS every time a region is generated while a saved audience is
    written once and frozen.

    So a buy could only ever reach people who had already won a seat in a
    selection made BEFORE they existed. Measured through the app the day it
    first mattered: after appending a 45-60/tier-3 region, a 45-60/tier-3 buy
    reported reaching **1 of 1** consumer types, while the same buy over the
    real library reached **7 of 50**.

    ⚠ This is the whole point of an accumulating population — `--append` and
    `_merge` in `install_generated_audience.py` exist so a brand's population
    is the union of every region anyone has bought against. A frozen seat list
    silently undoes that.
    """
    entities = world / "runs" / "demo" / BRAND / "entities"
    library = DispositionLibrary.from_dict(
        json.loads((entities / "library.json").read_text()))

    # Shrink the SAVED AUDIENCE to one seat, leaving the library untouched —
    # exactly the shape a freshly appended region produces.
    audience_path = next((entities / "audiences").glob("*.json"))
    saved = json.loads(audience_path.read_text())
    kept = saved["spec"]["disposition_labels"][0]
    saved["spec"]["disposition_labels"] = [kept]
    audience_path.write_text(json.dumps(saved))

    brand = _brand(world)
    assert len(brand.dispositions) == len(library.dispositions), (
        f"the brand offers {len(brand.dispositions)} consumer types but its "
        f"library holds {len(library.dispositions)} — the saved audience is "
        "capping the population again, and every region generated after it "
        "was written is unreachable")

    # ⚠ POSITIVE CONTROL, AND IT IS THE SHARP ONE: a buy must be able to seat
    # a type the saved audience NEVER NAMED. A bigger pool that still cannot
    # reach past the frozen list would satisfy the count assertion above and
    # fix nothing. The buy is deliberately wide — the fixture's default answers
    # reach exactly one of its three types on demographics alone, so a narrow
    # buy could not tell the two failures apart.
    parsed = audience_form.parse({**ANSWERS, "age_from": "18", "age_to": "75",
                                  "gender": "any", "income": "0:100",
                                  "geography": "all india"})
    spec = audience_form.build_spec(brand.template, parsed, brand.dispositions)
    assert len(spec.disposition_labels) > 1, (
        "the buy still seats only the one type the saved audience named, so "
        "widening the pool changed nothing that reaches a panel")
    assert set(spec.disposition_labels) - {kept}, (
        f"every seated type came from the saved audience's frozen list "
        f"({kept!r}) — a region installed after that list was written is "
        "still unreachable")


def test_a_saved_audience_naming_a_missing_type_is_still_refused(world: Path):
    """⚠ NEGATIVE CONTROL for the widening above.

    The resolve of the saved audience's labels is still performed — it is just
    discarded afterwards. It is the check that keeps a brand whose audience
    names a dropped type OUT of the picker, because that combination dies
    inside `RunService.prepare`, after the creative is uploaded. Widening the
    pool must not have quietly deleted that guard.
    """
    entities = world / "runs" / "demo" / BRAND / "entities"
    audience_path = next((entities / "audiences").glob("*.json"))
    saved = json.loads(audience_path.read_text())
    saved["spec"]["disposition_labels"] = ["a_type_that_was_dropped"]
    audience_path.write_text(json.dumps(saved))

    assert not discover_brands(world / "runs", account="demo"), (
        "a brand whose saved audience names a type its library does not hold "
        "is being offered — that fails after the upload, inside prepare")
