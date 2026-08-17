"""The population layer: how many of a region actually hold a job.

⚠ THE DEFECT THESE TESTS GUARD. The first generated region — women 45-60 in
tier-3 towns — wrote 194 people and gave every single one a paid job, in a
slice that is roughly two-thirds homemaker in life. See `agent/demography.py`.

⚠ EVERY ABSENCE TEST HERE CARRIES A POSITIVE CONTROL. This harness has caught
eight tests that passed while asserting nothing, and "the male brief does not
claim a participation rate" is exactly the shape that goes vacuous when a
helper stops returning text at all.
"""

import json
import pathlib

import pytest

from agent import demography as demo


# --------------------------------------------------------------------------
# The rate itself.
# --------------------------------------------------------------------------

def test_exact_band_returns_the_surveyed_figure():
    # 45-59 urban is a band boundary, so no weighting is involved and the
    # number must come back untouched from the table. [PLFS 2023-24, Fig 2]
    assert demo.female_lfpr(45, 59, "tier-3") == 32.6
    assert demo.female_lfpr(30, 44, "tier-1") == 37.8


def test_a_region_spanning_two_bands_is_weighted_by_years_not_averaged():
    # Women 45-60 is fifteen years of the 45-59 band (32.6) and ONE year of
    # 60-74 (11.9). A naive mean of the two bands gives 22.3, which would
    # halve the working share and is the bug this asserts against.
    got = demo.female_lfpr(45, 60, "tier-3")
    assert got == pytest.approx(31.3, abs=0.1)
    naive_mean = (32.6 + 11.9) / 2
    assert abs(got - naive_mean) > 8, "bands were averaged, not year-weighted"


def test_rural_and_urban_are_different_columns():
    # Nearly twenty points apart at 45-59 — reading the wrong column would
    # double the working share, which is the kind of error that looks fine.
    assert demo.female_lfpr(45, 59, "rural district") == 66.5
    assert demo.female_lfpr(45, 59, "tier-3") == 32.6


def test_every_city_tier_is_urban():
    # The documented modelling assumption. If this ever changes it must change
    # deliberately, with the docstring, not by accident.
    for tier in ("tier-1", "tier-2", "tier-3", "any", "metro"):
        assert demo.settlement_for_tier(tier) == "urban"


def test_a_region_below_the_survey_floor_returns_zero_not_a_crash():
    assert demo.female_lfpr(5, 12, "tier-2") == 0.0


# --------------------------------------------------------------------------
# The brief that reaches the model.
# --------------------------------------------------------------------------

def test_female_brief_states_the_rate_and_its_complement():
    text = demo.brief("female", 45, 60, "tier-3")
    assert "31 in 100" in text, "the sourced participation rate never reached the prompt"
    assert "The other 69" in text, "the complement — the homemakers — is not stated"


def test_female_brief_says_self_employment_is_the_norm():
    # The second half of the fix: the generator did not only employ everyone,
    # it gave everyone a SALARY, which two thirds of women workers do not have.
    text = demo.brief("female", 45, 60, "tier-3")
    assert "67 of every 100" in text
    assert "self-employed" in text


def test_male_brief_makes_no_participation_claim():
    # No age-banded male table was ever sourced, so the module must not invent
    # one. POSITIVE CONTROL: the female brief DOES make the claim, proving the
    # assertion below can fail and is not passing on an empty string.
    male = demo.brief("male", 30, 50, "tier-2")
    female = demo.brief("female", 30, 50, "tier-2")
    assert "in the labour force at all" in female      # control
    assert "in the labour force at all" not in male
    assert len(male) > 200, "male brief is empty — the absence above proves nothing"
    assert "self-employed" in male, "men still need the work-shape facts"


def test_any_gender_carries_both_halves_and_still_no_invented_average():
    text = demo.brief("any", 30, 50, "tier-2")
    assert "MEN work in a wider mix" in text
    assert "working women in India are self-employed" in text
    # An "any" region must NOT state a blended participation rate: averaging a
    # sourced female number with an unsourced male one invents a third number.
    assert "in the labour force at all" not in text


def test_the_brief_redirects_the_occupation_field():
    text = demo.brief("female", 45, 60, "tier-3")
    assert "WHAT FILLS THIS PERSON'S DAY" in text
    assert "not necessarily a job" in text


# --------------------------------------------------------------------------
# Reading back what got written.
# --------------------------------------------------------------------------

def test_looks_unpaid_finds_household_days():
    for hint in ("Runs the house and minds the two grandchildren",
                 "Homemaker; her mornings go to the kitchen",
                 "Helps at her husband's hardware shop, takes no salary",
                 "Helps her husband with the grain shop's accounts"):
        assert demo.looks_unpaid(hint), hint


def test_looks_unpaid_does_not_swallow_actual_jobs():
    # POSITIVE CONTROL on the classifier: without these, a `looks_unpaid` that
    # returned True for everything would pass the test above.
    for hint in ("Staff nurse at a district hospital",
                 "Back-office operations team lead at a bank",
                 "Runs a tailoring unit with four machines and two women",
                 "Government school teacher, senior secondary"):
        assert not demo.looks_unpaid(hint), hint


def test_a_retiree_with_a_second_income_is_not_counted_as_unpaid():
    """⚠ The finding that set the classifier's shape — see agent/demography.py.

    The pre-fix generator wrote twelve retirees and gave eleven of them a fresh
    source of income. Counting "retired" as unpaid would have reported a 7%
    household share against a true share under 1%, i.e. it would have reported
    the defect as mostly fixed.
    """
    for hint in ("retired college lecturer now taking private tuitions",
                 "retired postmistress now teaching at a tuition centre",
                 "retired from the state electricity board office, now "
                 "manages two rented shops",
                 "ASHA worker doing household visits and immunisation records"):
        assert not demo.looks_unpaid(hint), hint
    # POSITIVE CONTROL: a retiree who is genuinely not working is still caught,
    # via the household half of the hint rather than the word "retired".
    assert demo.looks_unpaid("retired teacher, now runs the house for her son's family")


def test_achieved_mix_counts_people_not_types():
    bundles = [{"occupation_hint": "Runs the house"},
               {"occupation_hint": "Staff nurse at a district hospital"},
               {"occupation_hint": "Homemaker, two grown sons"}]
    assert demo.achieved_mix(bundles) == (2, 3)


# --------------------------------------------------------------------------
# The wiring. A perfect table that never reaches the model fixes nothing.
# --------------------------------------------------------------------------

def _system_blocks(region):
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
    from generate_audience import GRIDS, _build          # noqa: E402
    from agent.artifact_pack import load_pack            # noqa: E402
    blocks, _user = _build(GRIDS["snacking"],
                           load_pack("health_nutrition_snacking"),
                           [("desk_slump_4pm", "loyalist")], [], region)
    return blocks


def test_the_population_brief_reaches_the_cached_system_block():
    """⚠ It must be in the CACHED block, not the user turn.

    The region is constant across every batch of one generation, so it caches
    with the pack and the grid and a batch retry pays output only. Putting it
    in the user turn would re-bill this text on all thirteen batches.
    """
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
    from generate_audience import Region                 # noqa: E402

    region = Region(gender="female", age_min=45, age_max=60,
                    income_min=1.5, income_max=18.0, tier="tier-3")
    cached = [b for b in _system_blocks(region) if b.get("cache_control")]
    assert len(cached) == 1
    text = cached[0]["text"]
    assert "31 in 100 women this age are in the labour force" in text
    assert "67 of every 100" in text
    assert "WHAT FILLS THIS PERSON'S DAY" in text


def test_the_occupation_field_no_longer_asks_for_a_job():
    """MUTATION PROOF for the schema change that caused the defect.

    The field was described as "The job", and it produced 194 employed people
    in a majority-homemaker slice. The key must NOT change — it is digested by
    `persona_core_hash` — but the description must.
    """
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
    from generate_audience import GRIDS, _tool           # noqa: E402

    blob = json.dumps(_tool(GRIDS["snacking"])["input_schema"])
    assert '"occupation_hint"' in blob, "the field key moved — hashes will move with it"
    assert "The job, plainly" not in blob, "the old job-first framing is still live"
    assert "WHAT FILLS THIS PERSON'S DAY" in blob


def test_the_measured_defect_is_still_measurable():
    """The generated region on disk really does contain zero unpaid days.

    ⚠ THIS TEST IS EXPECTED TO CHANGE when that region is regenerated with the
    fixed prompt — and it should be UPDATED then, not deleted, because the
    number it asserts is the before-and-after evidence. It is here so that
    `looks_unpaid` is exercised against real generator output rather than only
    against hand-written strings that were chosen to pass.
    """
    path = pathlib.Path(__file__).resolve().parent.parent / "generated_audience_w4560_t3.json"
    if not path.exists():                       # not committed; skip cleanly
        pytest.skip("the pre-fix region is not on disk")
    raw = json.loads(path.read_text())["raw"]
    people = [b for t in raw for b in t["bundles"]]
    unpaid, total = demo.achieved_mix(people)
    assert total > 100, "the fixture is not the region this documents"
    # ONE of 194 — a woman who helps unpaid at her husband's grain shop. The
    # population says roughly 130 of 194. Against that, one is a zero.
    assert unpaid == 1, (
        f"{unpaid} of {total} now read as unpaid — if this region was "
        "regenerated, update the expected count and record the before/after")


def test_the_fix_landed_in_the_regenerated_region():
    """The AFTER half of the before/after. Same region, same grid, new prompt.

    ⚠ THIS IS THE ONLY EVIDENCE THE DEMOGRAPHY LAYER WORKS. Every other test
    here proves the words reach the model; none of them can prove the model
    obeyed. `generated_audience_w4560_t3_v2.json` was generated 2026-08-18 with
    byte-identical region and count to v1 — women / 45-60 / any income /
    tier-3, 64 types — so the prompt is the ONLY thing that differs between the
    two files and the difference between these two numbers is attributable.

    ⚠ THE ASSERTION IS "NOT A ZERO", NOT A RATIO. The achieved and expected
    shares are different quantities whose errors point in opposite directions
    (see the comment block above `looks_unpaid`), so pinning 71/192 against the
    population's 69% would be pinning a number nobody should tune toward. What
    is being defended here is the failure that actually happened: 1 of 194.
    """
    path = pathlib.Path(__file__).resolve().parent.parent / "generated_audience_w4560_t3_v2.json"
    if not path.exists():                       # not committed; skip cleanly
        pytest.skip("the regenerated region is not on disk")
    raw = json.loads(path.read_text())["raw"]
    people = [b for t in raw for b in t["bundles"]]
    unpaid, total = demo.achieved_mix(people)
    assert total > 100, "the fixture is not the region this documents"
    # Measured 2026-08-18: 71 of 192 (37%), against 1 of 194 (0.5%) in v1.
    # The floor is set well under the measured value on purpose — it is a
    # smoke alarm for a regression to zero, not a quota to hit.
    assert unpaid >= 40, (
        f"only {unpaid} of {total} read as unpaid — v1 scored 1 of 194 and the "
        "regenerated region scored 71 of 192. A drop back toward zero means "
        "the demography brief has stopped reaching the generator")


def test_an_unpaid_family_helper_is_not_an_income_leak():
    """⚠ THE TWO GUARDRAILS COLLIDED IN PRODUCTION, 2026-08-18, AND THIS PINS
    THE RESOLUTION.

    `demography.brief` offers "takes no salary from it" as a VERBATIM exemplar
    and the `occupation_hint` schema repeats it — then gate 3 of
    `check_generated_audience.py` failed 11 hints for containing "salar",
    marking an otherwise-clean paid region NOT ADMISSIBLE. The gate's own rule
    is "may say what someone does for a living, may not price them", and a
    negated salary prices nobody: it is an employment arrangement, and the
    woman who takes no salary from the family shop may live in a ₹2L or a ₹40L
    household. The redaction actually being guarded is over `income_lpa`.

    ⚠ NEGATED ONLY. If this test ever passes a priced salary, the carve-out has
    been widened too far and the seam is open.
    """
    import importlib.util
    import io
    from contextlib import redirect_stdout
    spec = importlib.util.spec_from_file_location(
        "_chk", pathlib.Path(__file__).resolve().parent.parent
        / "scripts" / "check_generated_audience.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)

    def flagged(s: str) -> bool:
        """⚠ CALLS THE REAL GATE, NOT A COPY OF ITS REGEXES.

        The first version of this test evaluated `_MONEY.search(_NO_SALARY.sub(
        ...))` itself, and reverting the gate to ignore `_NO_SALARY` entirely
        left it GREEN — it was asserting that two regexes compose, which no
        production code path had to agree with. Driving `gate_income_seam` is
        what makes the mutation fail."""
        raw = [{"label": "probe", "bundles": [
            {"occupation_hint": s, "household_hint": "two sons, one at home"}]}]
        with redirect_stdout(io.StringIO()):
            return chk.gate_income_seam(raw) > 0

    # The generator was TOLD to write these. They must survive the gate.
    for ok in ("keeps the accounts book for her husband's fertiliser shop, "
               "takes no salary",
               "helps at the family's saree shop from morning, sits at the "
               "billing counter, takes no salary",
               "sits at her husband's shop from nine, draws no salary",
               "helps at the grain shop, works without a salary",
               "unsalaried helper at the family kirana"):
        assert not flagged(ok), f"the gate still rejects an unpaid helper: {ok!r}"

    # ⚠ THE SEAM ITSELF. Each of these prices her and must still fail.
    for leak in ("schoolteacher on a salary of ₹40,000 a month",
                 "draws a good salary at the district office",
                 "salaried accountant at a textile trading firm",
                 "her salary is the larger of the two",
                 # ⚠ A negated salary in the SAME sentence as a real leak must
                 # not launder it — this is why the carve-out is a removal pass
                 # over the text and not a lookaround on the money pattern.
                 "helps at the shop, takes no salary; household earns ₹8L",
                 "comfortably well-off family",
                 "lives in an affluent colony"):
        assert flagged(leak), f"the income seam is open: {leak!r}"
