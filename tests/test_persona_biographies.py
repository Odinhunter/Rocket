"""The demographic bundle is WHO THIS PERSON IS. The anchor is what they
think of the category. This file pins that seam.

THE DEFECT THIS EXISTS FOR, MEASURED 2026-08-13. Under the shipped
25-44 / ₹7-40L brief a 100-agent panel was backed by **10 biographies**, and
**15 agents shared the single most common one** — identical job, identical
household, identical everything the persona writer is handed except the chaos
vector. Five income rows per disposition are authored, but `demographic_
overlap` is gender × age × income only, so the three rows outside the brief
score zero and drop out: a "panel of 100" was 10 people at the layer that
decides who they are.

⚠ THE SPLIT IS SAFE ONLY BECAUSE OF THE ROW INVARIANT, and that is what
`test_income_rows_survive_being_split` exists to hold. Sub-bundles of one
documented income row share its gender, age band and SUMMED weight, and differ
only in geography / occupation_hint / household_hint. Because overlap ignores
all three of those, every sub-bundle of a row scores the identical overlap and
`audience_mass` — the marketer-led selection weight — is arithmetically
unchanged. Break the invariant and you have silently re-weighted which
dispositions get panel share, which is a different and much bigger decision
than "make the personas real".

⚠ `occupation_hint` and `household_hint` REACH THE PERSONA WRITER
(`render.persona_writer_demographics`), and unlike `income_lpa_*` they are NOT
redacted. That makes them a bypass around the §2.6 income redaction and a
second seam for the render-10 uniformity defect — every agent drawn from a
bundle gets its hint verbatim, so a hint carrying category content makes the
panel pre-agree about the very thing the run measures.

Offline. No API calls — `build_panel` is pure.
"""

from __future__ import annotations

import collections
import importlib.util
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack  # noqa: E402
from agent.panel import build_panel, demographic_overlap  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
_CATEGORY = "health_wellness_nutrition"

# The five income rows of docs/disposition_income_brackets.md, as the LPA
# ranges DemographicPoint actually stores (income_tier is an InitVar and is
# never persisted, so grouping by it would silently group everything into one
# bucket and pass vacuously).
_TIERS = [(0.0, 3.5), (3.5, 7.0), (7.0, 17.0), (17.0, 40.0), (40.0, 100.0)]

# docs/disposition_demographic_bundles.md — the research distribution each
# disposition's bundle weights must reproduce.
_DOCUMENTED_ROWS = {
    "enthusiast_macros_lifter":   [12, 26, 38, 18, 6],
    "aspirant_clean_label":       [5, 17, 45, 26, 7],
    "switcher_results_chaser":    [12, 30, 39, 16, 3],
    "skeptic_lapsed_protein":     [20, 32, 32, 12, 4],
    "pragmatist_protein_snacker": [6, 18, 40, 26, 10],
    "purist_food_first":          [12, 22, 34, 24, 8],
}


def _scaffold():
    """The scaffold is the SOURCE OF TRUTH — it regenerates library.json, and
    `runs/` is gitignored, so asserting on the JSON would assert on an artifact
    that need not exist in a clean checkout."""
    path = _REPO / "scripts" / "scaffold_health_wellness.py"
    spec = importlib.util.spec_from_file_location("_scaffold_hw_bio", path)
    mod = importlib.util.module_from_spec(spec)
    with redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


def _bundled_dispositions():
    return [d for d in _scaffold()._library().dispositions
            if d.demographic_bundles]


def _hints(point) -> str:
    return f"{point.occupation_hint} {point.household_hint}"


# --------------------------------------------------------------------------
# 1. The invariant that makes splitting a row safe
# --------------------------------------------------------------------------


def test_income_rows_survive_being_split():
    """Splitting a row must not move its weight, its gender or its age band —
    those three are exactly what `demographic_overlap` scores."""
    seen = set()
    for d in _bundled_dispositions():
        seen.add(d.label)
        rows = collections.defaultdict(
            lambda: {"weight": 0.0, "genders": set(), "ages": set()}
        )
        for b in d.demographic_bundles:
            key = (b.point.income_lpa_min, b.point.income_lpa_max)
            rows[key]["weight"] += b.weight
            rows[key]["genders"].add(b.point.gender)
            rows[key]["ages"].add((b.point.age_min, b.point.age_max))

        got = [int(rows[t]["weight"]) if t in rows else 0 for t in _TIERS]
        assert got == _DOCUMENTED_ROWS[d.label], (
            f"{d.label}: bundle weights no longer reproduce the research "
            f"income distribution — got {got}, "
            f"want {_DOCUMENTED_ROWS[d.label]}. Sub-bundles of one row must "
            f"sum to that row."
        )
        for t, row in rows.items():
            assert len(row["genders"]) == 1, (
                f"{d.label} row {t}: sub-bundles disagree on gender "
                f"{row['genders']} — this re-weights audience_mass"
            )
            assert len(row["ages"]) == 1, (
                f"{d.label} row {t}: sub-bundles disagree on age band "
                f"{row['ages']} — this re-weights audience_mass"
            )

    assert seen == set(_DOCUMENTED_ROWS), (
        "the set of bundled dispositions moved; update _DOCUMENTED_ROWS "
        f"deliberately — got {sorted(seen)}"
    )


def test_sub_bundles_of_a_row_are_interchangeable_to_the_matcher():
    """The mechanism behind the invariant, asserted directly rather than
    assumed: geography / occupation / household do not enter
    `demographic_overlap`, so every sub-bundle of a row scores identically
    against any frame. If this ever changes, splitting rows silently becomes a
    panel-composition change."""
    frames = _scaffold()._audience_spec(load_pack(_CATEGORY)).demographics
    for d in _bundled_dispositions():
        rows = collections.defaultdict(list)
        for b in d.demographic_bundles:
            rows[(b.point.income_lpa_min, b.point.income_lpa_max)].append(b.point)
        for key, points in rows.items():
            if len(points) < 2:
                continue
            for frame in frames:
                scores = {round(demographic_overlap(p, frame), 12) for p in points}
                assert len(scores) == 1, (
                    f"{d.label} row {key}: sub-bundles score differently "
                    f"({scores}) against a declared frame — the split changed "
                    f"panel composition instead of just the biography"
                )


# --------------------------------------------------------------------------
# 2. The hints are a prompt seam, not a spare text field
# --------------------------------------------------------------------------


_MONEY = re.compile(r"₹|\bLPA\b|\blakh|\bcrore|\brupee|\bincome\b", re.IGNORECASE)
_TIER_WORD = re.compile(
    r"\b(affluent|upper[-_ ]mid|lower[-_ ]mid|mass[-_ ]market)\b", re.IGNORECASE
)


def test_no_hint_smuggles_income_past_the_writer_redaction():
    """`income_lpa_min/max` are stripped at `_persona_user_payload` (§2.6) —
    the hints are not. A rupee figure or a tier word here walks straight past
    that redaction and hands the writer the number it is not supposed to see."""
    offenders = []
    for d in _bundled_dispositions():
        for b in d.demographic_bundles:
            text = _hints(b.point)
            if _MONEY.search(text) or _TIER_WORD.search(text):
                offenders.append((d.label, text))
    assert not offenders, (
        "a hint names income; the persona writer must never see it — "
        f"{offenders}"
    )


def test_an_any_gender_bundle_never_carries_a_gendered_pronoun():
    """A bundle whose gender is "any" is resolved to a side by the declared
    frame at `_clip_point`. A pronoun baked into the hint contradicts whichever
    side it lands on for half the panel."""
    pron = re.compile(r"\b(he|him|his|she|her|hers)\b", re.IGNORECASE)
    offenders = []
    for d in _bundled_dispositions():
        for b in d.demographic_bundles:
            if b.point.gender in ("any", "unspecified"):
                if pron.search(_hints(b.point)):
                    offenders.append((d.label, _hints(b.point)))
    assert not offenders, (
        'a gender-"any" bundle fixes a pronoun in its hint — the writer is '
        f"handed both and the pronoun wins: {offenders}"
    )


def test_every_bundle_actually_carries_a_biography():
    """The whole point of the layer. An empty hint hands the writer a bare
    age/gender/geography triple and it invents the rest — differently every
    render, and identically across everyone in the row."""
    thin = []
    for d in _bundled_dispositions():
        for b in d.demographic_bundles:
            occ, house = b.point.occupation_hint, b.point.household_hint
            if len(occ.split()) < 3 or len(house.split()) < 3:
                thin.append((d.label, occ, house))
    assert not thin, f"bundles with no real biography: {thin}"


# --------------------------------------------------------------------------
# 3. The deliverable itself
# --------------------------------------------------------------------------


def test_the_panel_is_not_fifteen_copies_of_one_person():
    """The measurement this thread exists for, run against the SHIPPED brief.

    ⚠ Bounds are deliberately looser than the measured result (25 biographies,
    largest cluster 5) so ordinary authoring edits do not fail the build —
    they fail on a REGRESSION toward the 10/15 that started this."""
    mod = _scaffold()
    pack = load_pack(_CATEGORY)
    spec = mod._audience_spec(pack)
    by_label = {d.label: d for d in mod._library().dispositions}
    disps = [by_label[l] for l in spec.disposition_labels]

    agents = build_panel(
        spec, disps,
        category=_CATEGORY,
        segment_granularity="disposition_chaos_band",
        seed=71,
        marketer_led=True,
        tail_fraction=0.0,
    )
    assert len(agents) == 100

    bios = collections.Counter(
        (a.disposition.label, a.demographic.occupation_hint,
         a.demographic.household_hint)
        for a in agents
    )
    biggest = bios.most_common(1)[0][1]

    assert len(bios) >= 20, (
        f"only {len(bios)} distinct biographies back 100 agents (was 10 before "
        "the 2026-08-13 re-authoring, target 25). The rows that overlap the "
        "declared brief have collapsed again."
    )
    assert biggest <= 7, (
        f"{biggest} agents share one identical biography (was 15 before the "
        "re-authoring, 5 after). Split the row that regressed."
    )
