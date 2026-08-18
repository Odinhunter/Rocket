"""The assembled generation prompt, tested as one artifact.

⚠ WHY THIS FILE EXISTS. The prompt is composed from five pieces that live in
two modules — `_SYSTEM`, `_pack_brief`, `_grid_brief`, `_region_brief` and
`demography.brief` — and every defect in the audit of 2026-08-18 lived in the
SEAMS between them rather than inside any one piece. `tests/test_demography.py`
checks the demography half in isolation and passed throughout, while the same
six exemplar nouns were reaching the model three times over from three
different files. So these tests assemble the real thing and read it whole.

The audit: `docs/people_audit_w4560_t3.md`. 192 people, eight findings. The two
that shape this file:

  1. THE MODEL COPIES EXAMPLES AND OBEYS PROPORTIONS. Six illustrative nouns
     became 49% of the panel; the stated 37% homemaker proportion landed almost
     exactly. So a named example is a spec whether or not it was meant as one,
     and the tests below count them.
  2. IT WILL NOT WRITE ABSENCE FOR ITS PROTAGONIST. No job, no second income
     after retiring, no living husband — 191 of 192 employed, 11 of 12 retirees
     re-employed, 190 of 192 with a husband alive.

⚠ AND THE STANDING INSTRUCTION THESE ENFORCE: the prompt must be REGION-GENERAL
(the user's call, 2026-08-18). It has to write young tier-1 people as readily as
the 45-60 tier-3 women it was first built for, so nothing in it may assume
middle age, marriage, children or a small town.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from agent.artifact_pack import load_pack                      # noqa: E402
from generate_audience import (                                # noqa: E402
    GRIDS, Region, _build, _cells, _tool,
)

GRID = GRIDS["snacking"]
PACK = load_pack("health_wellness_nutrition")

OLD = Region(gender="female", age_min=45, age_max=60, tier="tier-3")
YOUNG = Region(gender="female", age_min=22, age_max=28, tier="tier-1")
MIXED = Region(gender="any", age_min=30, age_max=45, tier="tier-2")


def assembled(region: Region) -> str:
    """Every word the model is sent, in one string — system blocks and the user
    turn together. ⚠ The seams are the point; testing a block alone is what let
    the tripled exemplars through."""
    system, user = _build(GRID, PACK, _cells(GRID, 5), [], region)
    return "\n".join(b["text"] for b in system) + "\n" + user


# --------------------------------------------------------------------------
# FINDING 3 — the exemplar list that was read as a menu.
# --------------------------------------------------------------------------

# The six nouns `demography.brief` offered as illustration. Measured: they came
# back as 94 of 192 people. ⚠ This is the regression list — if a future session
# "helpfully" restores a richer set of examples, these fail.
MENU_NOUNS = ("tiffin", "beauty parlour", "tailoring", "tuition")


@pytest.mark.parametrize("region", [OLD, YOUNG, MIXED])
def test_the_six_noun_job_menu_is_gone(region):
    """The list that produced the clustering, in the place that produced it.

    ⚠ WORD BOUNDARIES, NOT `in`. The first version of this test used a plain
    substring and failed on the word INTUITION, which contains "tuition" — a
    test that fails for a reason unrelated to the thing it names is worse than
    no test, because the next session deletes it.
    """
    import re
    text = assembled(region).lower()
    found = [n for n in MENU_NOUNS
             if re.search(rf"\b{re.escape(n)}\b", text)]
    assert not found, (
        f"the job menu is back in the prompt: {found}. Every concrete trade "
        "named here becomes a cluster in the output — six of them were 49% of "
        "a 192-person panel. Fix a monoculture with sourced proportions, never "
        "with a longer list of examples.")


def test_the_sourced_industry_spread_replaced_it():
    """POSITIVE CONTROL for the test above — the menu is gone because
    something better is there, not because the paragraph was deleted."""
    text = assembled(OLD)
    assert "manual and production work" in text
    assert "agricultural and land labour" in text
    assert "27.9%" in text and "9.4%" in text, (
        "the NFHS occupation split is not reaching the model — without it the "
        "test above passes on an empty paragraph")


def test_no_exemplar_is_stated_twice_in_the_whole_prompt():
    """⚠ THE STRUCTURAL RULE, AND THE ONE NO SINGLE-MODULE TEST CAN SEE.

    The audit's mechanism: the same six nouns appeared in `demography.brief`,
    in the `occupation_hint` schema description AND in `_SYSTEM`'s "ON HOW
    THESE PEOPLE SPEND THEIR DAYS" — three times in one prompt. Repetition is
    emphasis, and emphasis on an example is an instruction to copy it.

    So: any exemplar that survives appears EXACTLY ONCE across the assembly.
    """
    text = assembled(OLD).lower()
    for phrase in ("runs the house", "takes no salary", "grandchildren after school",
                   "municipal school"):
        assert text.count(phrase) <= 1, (
            f"{phrase!r} appears {text.count(phrase)} times in one prompt. "
            "Two mentions of an example is a spec; see finding 3.")


def test_the_clustering_report_would_catch_a_menu_regression():
    """MUTATION PROOF, asked for by name in the audit's fix table.

    Thinning the exemplars is only worth doing if a relapse is visible. This
    feeds `audit_generated_people.py`'s clustering report a population that has
    relapsed — everyone holding one of the menu jobs — and asserts the report
    says so loudly. ⚠ If this ever passes on the CLEAN population too, the
    report has stopped discriminating and the audit is decorative.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_audit", pathlib.Path(__file__).resolve().parent.parent
        / "scripts" / "audit_generated_people.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

    import re

    def covered(hints: list[str]) -> float:
        idx: set[int] = set()
        for _name, pat in audit.OCCUPATION_BUCKETS:
            idx |= {i for i, h in enumerate(hints) if re.search(pat, h, re.I)}
        return len(idx) / len(hints)

    relapsed = ["runs a tiffin service from home", "takes in tailoring",
                "runs a small beauty parlour", "gives home tuition",
                "keeps the accounts at the family shop, unpaid"] * 8
    # A population written from the industry SPREAD instead of the menu.
    spread = ["packs cartons on the second shift at a biscuit unit",
              "loads and weighs at the grain market",
              "works the family's half-acre and sells at the Tuesday bazaar",
              "cleans and cooks in two houses in the colony",
              "sits at the panchayat office as a records clerk"] * 8

    assert covered(relapsed) > 0.9, (
        "the clustering report did not notice a population where every single "
        "person holds a menu job — it cannot catch the regression it exists "
        "for")
    assert covered(spread) < 0.5, (
        "the report flags a genuinely varied population as clustered, so its "
        "signal on the relapsed one means nothing")


# --------------------------------------------------------------------------
# FINDINGS 1, 2, 5, 6, 8 — the family half, and the arithmetic.
# --------------------------------------------------------------------------

def test_the_household_field_is_no_longer_specified_in_23_characters():
    """The one-line cause named at the top of the audit.

    `household_hint` carried "ONE household detail. Same bans." — 32 characters
    — while `occupation_hint` beside it carried ~700. Every family defect
    followed from that asymmetry.
    """
    import json
    blob = json.dumps(_tool(GRID)["input_schema"])
    props = _tool(GRID)["input_schema"]["properties"]["buyer_types"]["items"][
        "properties"]["bundles"]["items"]["properties"]
    house = props["household_hint"]["description"]
    job = props["occupation_hint"]["description"]

    assert '"household_hint"' in blob, "the field key moved — persona_core_hash moves with it"
    assert len(house) > 400, (
        f"household_hint is specified in {len(house)} characters against "
        f"occupation_hint's {len(job)}. That asymmetry IS the defect.")
    assert "arithmetic" in house.lower()
    assert "16" in house, "the impossible-grandmother worked example is gone"


def test_the_retirement_exemplar_no_longer_demonstrates_the_defect():
    """⚠ THE PROMPT WAS TEACHING THE BUG.

    `occupation_hint` offered "retired from the state transport depot, NOW DOES
    THE MORNING MARKET RUN" as a model answer — a retiree immediately handed a
    second occupation. Eleven of the twelve retired people in the audited
    region came back re-employed. The exemplar has to show the absence.
    """
    props = _tool(GRID)["input_schema"]["properties"]["buyer_types"]["items"][
        "properties"]["bundles"]["items"]["properties"]
    job = props["occupation_hint"]["description"]
    assert "now does the morning market run" not in job.lower()
    assert "has not worked since" in job.lower(), (
        "no exemplar demonstrates a person who retired and simply stopped")


def test_absence_is_one_rule_covering_all_three_faces():
    """The audit's second mechanism finding: no job, no income after retiring
    and no living husband are ONE defect. A prompt that fixes them separately
    fixes the three it names and none of the ones it does not."""
    text = assembled(OLD)
    assert "WRITE ABSENCE" in text
    lowered = text.lower()
    for face in ("no job", "no spouse", "no income of their own",
                 "no children"):
        assert face in lowered, f"the absence rule does not cover {face!r}"
    assert "one failure in three costumes" in lowered, (
        "the three faces are listed but not named as ONE defect — which is "
        "how the last two got fixed separately and the third stayed")


# --------------------------------------------------------------------------
# REGION-GENERALITY — the standing instruction, and the easiest thing to lose.
# --------------------------------------------------------------------------

def test_a_young_region_is_not_told_about_widows_and_grandchildren():
    """⚠ THE FAILURE MODE OF THE FIX ITSELF. Every number added for the 45-60
    women is a middle-age assumption if it goes out unconditionally. A region
    of 22-28-year-olds must hear about never-married women instead."""
    young = assembled(YOUNG)
    assert "never married" in young.lower()
    assert "do not write these as widows" in young.lower()
    assert "grandchildren after school" not in young, (
        "the unpaid-day exemplar still names grandchildren to a region of "
        "22-year-olds")
    assert "almost none of those are students" not in young, (
        "the over-30 student claim is being made about 22-year-olds")


def test_the_old_region_still_gets_the_widowhood_it_was_missing():
    """POSITIVE CONTROL for the test above. If the conditionals silenced the
    family half everywhere, the assertions there would pass on nothing."""
    old = assembled(OLD)
    assert "widowed" in old.lower()
    assert "11" in old and "1 in 9" in old, "the sourced widowhood share is gone"
    assert "grandchildren after school" in old, (
        "the age-gated exemplar has vanished from the region it was written "
        "for — the gate is stuck shut, not conditional")


def test_the_survey_ceiling_is_declared_to_the_model_not_hidden():
    """A 45-60 region is scored off a table that stops at 49. Clamping quietly
    would state a 45-49 figure as if it fitted, and nothing downstream would
    know. `cohort_note` says so in words."""
    assert "THE FAMILY FIGURES STOP AT 49" in assembled(OLD)
    assert "THE FAMILY FIGURES STOP AT 49" not in assembled(YOUNG), (
        "a region entirely inside the survey is being warned about a ceiling "
        "it never touches")


@pytest.mark.parametrize("region", [OLD, YOUNG, MIXED])
def test_no_region_is_told_its_people_are_middle_aged(region):
    """A blanket sweep for the assumption, across all three shapes."""
    text = assembled(region).lower()
    for leak in ("her grandchildren", "at her age she has", "by now her children"):
        assert leak not in text, f"unconditional middle-age phrasing: {leak!r}"


# --------------------------------------------------------------------------
# THE SEAM WHERE THE PROMPT AND THE GATES CAN COLLIDE.
# --------------------------------------------------------------------------

def _gate3_flags(text: str) -> bool:
    """Run the REAL gate-3 regexes over one hint. ⚠ Not a copy of them — a copy
    would keep passing after somebody edits the gate, which is the failure this
    whole file is about."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_chk", pathlib.Path(__file__).resolve().parent.parent
        / "scripts" / "check_generated_audience.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)
    return bool(chk._MONEY.search(chk._NO_SALARY.sub(" ", text)))


def test_the_absence_rule_does_not_steer_the_model_into_a_gate_failure():
    """⚠⚠ THIS EXACT COLLISION ALREADY COST A REGION, 2026-08-18.

    `demography.brief` offered "takes no salary from it" as an exemplar and
    gate 3 then failed eleven hints for containing "salar" — an otherwise-clean
    paid generation came back NOT ADMISSIBLE. The two guardrails were each
    correct and pointed at each other.

    Rule 6 now asks for absence — no job, no spouse, nothing of her own — and
    gate 3's `_MONEY` flags the bare words "income" and "earn". So the prompt
    has to ask for the absence in language the gate accepts, and this test is
    what proves it does rather than assuming it.
    """
    invited = [
        "has never worked outside the house",
        "her husband died four years ago and the shop went with him",
        "works unpaid in the family's trade and would not call it a job",
        "takes no salary from it",
        "retired from the municipal school two years ago and has not worked since",
        "her husband works in Surat and comes home twice a year",
        "nobody in the house between eight and six",
    ]
    flagged = [h for h in invited if _gate3_flags(h)]
    assert not flagged, (
        f"the prompt invites hints that gate 3 rejects: {flagged}. This is the "
        "2026-08-18 collision again — fix the PROMPT's wording, and only widen "
        "the gate if the phrase genuinely prices somebody.")


def test_the_gate_still_catches_a_hint_that_actually_prices_somebody():
    """POSITIVE CONTROL. Without this the test above passes on a gate that has
    been widened until it flags nothing, which is a worse outcome than the
    collision it was fixing."""
    for priced in ("draws a salary of ₹40,000 a month",
                   "a good salary at the bank",
                   "from an affluent household",
                   "her income is about 8 lakh"):
        assert _gate3_flags(priced), (
            f"gate 3 no longer flags {priced!r} — the income seam is open")


def test_rule_six_tells_the_model_which_words_will_fail():
    """The steer itself, not just its effect — so that a future edit to rule 6
    that drops the warning is visible."""
    text = assembled(OLD).lower()
    assert "never through a money word" in text
    assert '"has no income"' in text, (
        "rule 6 no longer shows the wrong phrasing beside the right one")


def test_the_industry_spread_is_restated_in_region_terms():
    """⚠ A MEASURED REGRESSION, FIXED BY ARITHMETIC — probe of 2026-08-19.

    The industry table is eleven vivid numeric lines sitting under ONE sentence
    of labour-force participation, and the generator anchored on the table: the
    unpaid share fell from 37% (v2) to ~27%. The percentages are of the women
    who WORK, and reading them as a distribution over the region silently
    employs everybody — which is the original defect this module exists for,
    arriving through the fix for a different one.

    So the brief now does the multiplication itself and puts both numbers in
    one sentence. ⚠ The largest group in the room must be named as the one with
    no job, or the table wins on vividness every time.
    """
    text = assembled(OLD)
    assert "NOW PUT THAT BACK INTO THE REGION" in text
    assert "69 with no job at all" in text, (
        "the region-terms restatement is not doing the arithmetic — without a "
        "number the sentence is a caveat, and a caveat does not outweigh a "
        "table")
    assert "THE LARGEST GROUP IN THE ROOM IS THE ONE WITH NO JOB" in text


def test_the_unpaid_classifier_catches_the_phrasings_the_probe_produced():
    """⚠ THE COUNTER DRIFTS WHEN THE PROMPT'S EXEMPLARS MOVE.

    `_report_mix` read 13% unpaid on the probe where a hand count of the same
    30 people found ~27%, because the output said "takes NOTHING from it" and
    the marker list only knew "takes no salary". Thinning the exemplars moved
    the output off the exact wordings the classifier was built from.

    ⚠ This widens a REPORT, never a gate — see the note in `demography.py`.
    """
    from agent import demography as demo
    for hint in ("keeps the ledgers and cash box at her husband's cycle-parts "
                 "shop, takes nothing from it",
                 "minds the family's grain shop counter, takes no money for it",
                 "runs the house and minds the shop counter unpaid"):
        assert demo.looks_unpaid(hint), f"still miscounted as paid work: {hint!r}"
    # NEGATIVE CONTROL — widening the list must not swallow real jobs.
    for job in ("branch operations officer at a cooperative bank",
                "sorts and bags chilli at a small spice unit, six days a week",
                "cooks and cleans in two houses in the officers' colony"):
        assert not demo.looks_unpaid(job), f"a paid job now reads as unpaid: {job!r}"
