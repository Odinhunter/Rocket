"""No machine identifier may appear on a page a customer pays to read.

⚠⚠ WHY THIS FILE EXISTS. On 2026-08-22 the single most important sentence on a
real, rendered customer report read:

    88% of your target (upgrader desk afternoon protein) would buy — 7 of 8

and its header line read `Fnb world`. Both are engine identifiers with their
underscores swapped for spaces — internal vocabulary wearing the grammar of
English. 751 tests were green at the time, and TWO of them asserted this output
as CORRECT (`test_dashboard_html.py:1204` pinned `"switcher results chaser"`).

⭐⭐ THE LAW IS NOT NEW. This repo already stated it, for one instance, at
`test_dashboard_html.py::test_engine_scoping_vocabulary_never_reaches_the_page`:
strip engine vocabulary from prose, keep the fact as DATA. It was written once,
for pain prefixes, and never applied to the other places with the same shape.
That is this project's characteristic failure — the fix goes to the instance,
never to the class — so this file generalises it.

⚠ AND THE PART THAT MATTERS MOST FOR THE NEXT SESSION: the defect was found by
rendering the real page and reading it, NOT by the suite. Even after fixing the
methodology block, `Fnb world` was still in the run header — caught only by
re-rendering and grepping the output again. **Render the artifact. Read it.**
"""

from __future__ import annotations

import html as html_lib
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from agent.artifact_pack import market_name_for            # noqa: E402
from agent.vectors import (                                # noqa: E402
    KNOWN_STANCES, disposition_display, stance_of,
)

# Reuse the rendering fixtures rather than build a second, drifting copy.
from test_dashboard_html import _html                      # noqa: E402


def _visible_text(markup: str) -> str:
    """What a human actually reads — tags, scripts and styles removed."""
    stripped = re.sub(r"<script.*?</script>|<style.*?</style>", " ", markup, flags=re.S)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", stripped)))


# --------------------------------------------------------------------------
# The naming helpers themselves
# --------------------------------------------------------------------------

def test_a_buyer_type_never_renders_as_a_bare_humanised_slug() -> None:
    """The exact production string, and the shape of every one like it."""
    assert disposition_display("upgrader_desk_afternoon_protein") \
        == "upgrader · desk afternoon protein"
    assert disposition_display("gifter_office_round_afternoon") \
        == "gifter · office round afternoon"
    # ⭐ The separator is the whole point: it reads as a compound identifier
    # rather than as a sentence, which is what "upgrader desk afternoon protein"
    # was pretending to be.
    for label in ("upgrader_desk_afternoon_protein", "gifter_office_round_afternoon"):
        assert disposition_display(label) != label.replace("_", " ")


def test_an_authored_display_name_wins_outright() -> None:
    """⚠ Without this the field is decoration. The generator now emits one per
    buyer type (`display_name` is REQUIRED in the emit schema), and
    `read_model.display_names_from_panel` carries it from the run's own
    panel.json to the page with no migration."""
    assert disposition_display(
        "upgrader_desk_afternoon_protein", "Desk worker who traded up from biscuits"
    ) == "Desk worker who traded up from biscuits"
    # whitespace-only is not a name
    assert disposition_display("gifter_office_round", "   ") == "gifter · office round"


def test_an_unknown_stance_is_shown_whole_rather_than_split_wrongly() -> None:
    """⚠ `doctor_triggered_vitamin` is a real installed label that violates the
    `<stance>_<anchor>` convention. Guessing a split on it would invent a stance
    that does not exist, so it is rendered whole."""
    assert not stance_of("doctor_triggered_vitamin")
    assert disposition_display("doctor_triggered_vitamin") == "doctor triggered vitamin"


def test_market_name_is_prose_and_the_category_is_not() -> None:
    assert market_name_for("fnb_world") == "Indian urban food and beverage"
    assert "fnb" not in market_name_for("fnb_world").lower()


# --------------------------------------------------------------------------
# The rendered page — the surface that actually matters
# --------------------------------------------------------------------------

def test_no_disposition_slug_reaches_the_rendered_page() -> None:
    """⭐⭐ THE SEAM TEST. Renders the real customer HTML and reads it, rather
    than asserting on a piece. Every defect in this class was invisible to the
    piece-level tests and obvious in the assembled output."""
    text = _visible_text(_html())
    # the fixtures use these labels; none may appear as a bare humanised slug
    for label in ("enthusiast_macros_lifter", "aspirant_clean_label",
                  "skeptic_lapsed_protein"):
        assert label not in text, "the raw label must never appear"
        assert label.replace("_", " ") not in text, (
            f"{label!r} rendered as a bare humanised slug — engine vocabulary "
            f"wearing the grammar of English"
        )


def test_a_stance_word_never_stands_alone_as_a_noun_on_the_page() -> None:
    """⚠ The weaker half of the same law, kept honest about its own limits.

    A stance word can legitimately appear inside model-authored prose ("the
    adjacent aspirant"), so this cannot ban the words outright. What it CAN pin
    is that wherever a stance introduces a buyer type, the separator is present —
    i.e. the type was rendered through `disposition_display` and not through
    `humanize`."""
    text = _visible_text(_html())
    for stance in KNOWN_STANCES:
        # a stance immediately followed by two-plus lowercase words and no
        # separator is the signature of a humanised label
        bad = re.search(rf"\b{stance} [a-z]+ [a-z]+ [a-z]+\b", text)
        assert bad is None, (
            f"looks like a humanised label on the page: {bad.group(0)!r}"
        )


def test_no_category_slug_reaches_the_rendered_page() -> None:
    """`Fnb world` survived in the RUN HEADER after the methodology block was
    fixed — two sites, one class, found only by re-reading the rendered output.

    ⚠⚠ A FIRST DRAFT OF THIS TEST WAS VACUOUS AND A MUTATION RUN CAUGHT IT. It
    parametrised over a hardcoded `["fnb_world", "health_nutrition_snacking"]`
    while the fixture's category is `health_wellness_nutrition` — so reverting
    the run header to the slug passed. **It now reads the category off the model
    under test**, which cannot drift out of coverage when a fixture changes."""
    from test_dashboard_html import _model

    model = _model()
    slug = model.category
    assert slug, "the fixture must carry a category or this guard is vacuous"
    text = _visible_text(_html())

    for form in (slug, slug.replace("_", " "), slug.replace("_", " ").title(),
                 slug.replace("_", " ").capitalize()):
        assert form not in text, f"category slug {form!r} reached the page"
    assert market_name_for(slug) in text, (
        "the prose market name must be there in its place"
    )
