"""dashboard_html — the guardrails must reach the PAGE, not just the model.

The port of the old renderer's test file onto the user's Claude Design layout
(`git show 298b60e:tests/test_report_html.py` — both are deleted at HEAD). A
guardrail that lives in ReadModel but never renders is not a guardrail, and a
redesign is exactly when one goes missing — so every honesty surface the old
renderer was pinned on is pinned here too, against the new markup. That
correspondence was checked name by name before the old file was removed.

Four assertions are NEW, because the design as delivered did not carry them:

  * the panel table is suppressed on INCONCLUSIVE (the design rendered it
    unconditionally — a second door onto the numbers the headline hides);
  * a problem's lead is a complete sentence and the body does not restate it;
  * engine scoping vocabulary never reaches client copy;
  * the panel table's fixed action columns cover every action in the data.

Offline: synthetic reports, no API, no runs/ dependency.
"""

from __future__ import annotations

import re
from html import escape as html_escape

from agent.dashboard_html import _split_lead, render_html
from agent.read_model import ReadModel
from agent.schema import (
    ContextFitEntry, Decision, DispositionRef, Pain, Quote, Report,
    Strength, TargetMatch, TopChange,
)


def _decision(**kw) -> Decision:
    base = dict(
        decision="ITERATE", target_action_rate=0.1111, trust="DIRECTIONAL",
        target_action_num=2, target_action_denom=18,
        within_dispositions=["enthusiast_macros_lifter"],
        load_bearing_pain_id="P1", rationale="load-bearing within pain P1 is fixable",
    )
    base.update(kw)
    return Decision(**base)


def _report(decision=None, **kw) -> Report:
    base = dict(
        verdict="MIXED", confidence=76,
        target_match=TargetMatch(
            reached=[DispositionRef(disposition="enthusiast_macros_lifter",
                                    classification="within")],
            missed=[DispositionRef(disposition="aspirant_clean_label",
                                   classification="outside")],
        ),
        top_3_changes=[TopChange(change=f"change {i}", why="because",
                                 derives_from_pains=["P1"], lever_class="creative")
                       for i in range(3)],
        strengths_to_preserve=[Strength(strength="They trust the brand.")],
        context_fit_map={"commute_scroll": ContextFitEntry(
            verdict="mixed", friction_summary="washes past mid-commute")},
        verbatim_consumer_voice=[Quote(quote="not for me", disposition="d",
                                       round=1, context="c")],
        methodology_flags=["single_within_target"],
        decision=decision if decision is not None else _decision(),
    )
    base.update(kw)
    return Report(**base)


def _model(report: Report | None = None, **kw) -> ReadModel:
    """Build a ReadModel the same way build_read_model does, without disk."""
    import json
    import tempfile
    from pathlib import Path

    from agent.read_model import build_read_model
    report = report or _report()
    purpose = kw.pop("purpose",
                     report.decision.purpose if report.decision else "direct_sell")
    td = tempfile.mkdtemp()
    rd = Path(td) / "r"
    rd.mkdir()
    (rd / "run.json").write_text(json.dumps({
        "run_id": "run_x", "status": "complete",
        "updated_at": "2026-07-25T00:00:00+00:00",
        "panel_health": kw.pop("panel_health", None),
        "config": {
            "asset": {"image_path": "", "label": kw.pop("label", "Test Creative")},
            "category": "health_wellness_nutrition", "account_id": "demo",
            "brand_profile_id": "b", "creative_inputs": {"purpose": purpose},
            "declared_targeting": kw.pop("declared_targeting", "adults 25-44"),
            "audience_spec": {"panel_size": 100},
        },
        "report": report.to_dict(),
    }))
    if "l3" in kw:
        (rd / "l3_summary.json").write_text(json.dumps(kw.pop("l3")))
    if "transcripts" in kw:
        (rd / "transcripts.json").write_text(json.dumps(kw.pop("transcripts")))
    m = build_read_model(rd)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def _html(report: Report | None = None, **kw) -> str:
    return render_html(_model(report, **kw), embed_image=False)


# Section markers, in the design's fixed order.
_VERDICT = 'class="rk-dec"'
_HEADLINE = 'class="rk-headline"'
_MAP = "PROBLEM MAP"
_PROBLEMS = "PROBLEMS — "
_LEVERS = "highest-leverage first"
_FIXES = "DETAILED CHANGES"
_WORKED = "WHAT WORKED"
_PANEL = " SIMULATED CONSUMERS"
_DISC = 'class="rk-disc"'
_VOICE = "SIMULATED CONSUMER VOICE"
# The collapsed block at the foot that now holds every qualifier — see the
# module docstring of agent/dashboard_html.py. `_MADE` is the <summary> a
# reader clicks; `_METHOD` is the run-configuration grid inside it.
_MADE = "How this read was made"
_METHOD = ">HOW IT WAS RUN<"
_KEEP_IN_MIND = ">WHAT TO KEEP IN MIND<"


def _in_collapsed_block(html: str, needle: str) -> bool:
    """Is `needle` present, exactly once, and inside the collapsed block?

    Both halves matter. Presence alone would pass if a qualifier were still
    rendered inline beside the number it qualifies; position alone would pass
    if it had been deleted outright, which is precisely what this change is
    NOT. Callers assert the count separately when a string may legitimately
    repeat.
    """
    at = html.find(needle)
    return at != -1 and at > html.index(_MADE)


def _one_pain() -> list:
    return [Pain(id="P1", pain="The load-bearing one. Second sentence.",
                 funnel_stage="conversion", severity="execution",
                 within_target=True)]


# ---- properties of the artifact ---------------------------------------


def test_page_is_self_contained() -> None:
    """No external CSS, font, script or image request — the page must render
    identically served, opened from disk, or emailed.

    The design linked Google Fonts and drove its interactions from a script;
    both are gone. `<script` is the one that matters most: every expand on
    this page is a <details>, and a script tag would mean the report silently
    stops working the moment it is opened somewhere with a strict CSP.
    """
    html = _html()
    for pattern in (r'src="https?://', r'href="https?://', r'@import', r'<script'):
        assert not re.search(pattern, html), f"external/dynamic resource: {pattern}"
    assert "<style>" in html
    assert "<details" in html, "the page must expand without JavaScript"
    print("  page is self-contained and zero-JS ✓")


def test_the_designed_typeface_travels_with_the_page() -> None:
    """The design is drawn in Instrument Sans and the self-contained rule
    forbids fetching it, so the face itself is embedded as a data URI.

    This one fails silently by construction. A page that has lost the font
    still renders, still passes every other test in this file, and is simply
    not the document the user approved — nothing but this assertion notices.
    """
    html = _html()
    assert "@font-face" in html, "the typeface is not declared at all"
    assert 'font-family:"Instrument Sans"' in html
    faces = re.findall(r"url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)", html)
    assert faces, "the typeface is declared but its bytes are not embedded"
    assert all(len(b) > 10_000 for b in faces), \
        f"a face carries no real font data: {[len(b) for b in faces]}"

    # PAGE_CSS is a SEPARATE stylesheet — the operator server's own console and
    # capture pages, the surface a prospect watches being driven. It shares the
    # font block with the report so tool and deliverable read as one product,
    # and it needs its own assertion: everything above this line renders through
    # _CSS, so unwiring PAGE_CSS alone would leave this test green.
    from agent.dashboard_html import PAGE_CSS
    assert PAGE_CSS.count("data:font/woff2;base64,") == 2, \
        "the operator's own pages lost the typeface the deliverable has"
    print(f"  Instrument Sans travels with the page and the console, "
          f"{sum(len(b) for b in faces) // 1024}KB ✓")


def test_each_font_subset_is_scoped_by_its_unicode_range() -> None:
    """Two subsets ship, and each must carry the range that scopes it.

    Both faces share one family, weight and style. That makes the ranges
    load-bearing rather than decorative: with them gone the last face declared
    wins outright, and since latin-ext holds no ASCII, every ordinary character
    on the page falls through to the system stack. The page still renders, so
    only this notices.

    latin is the subset that matters today — checked against the character
    inventory of all 56 runs on disk, it covers everything they contain except
    ₹, → ↔ ▴ ▾ and Devanagari, none of which Instrument Sans has a glyph for in
    ANY subset (read out of the cmap, not inferred from the declared range).
    Those fall back, and were eyeballed on screen: the macOS fallback sits with
    Instrument Sans without reading as an island. latin-ext contributes nothing
    to today's reports and ships as insurance against an accented name landing
    in a verbatim and changing typeface mid-word.
    """
    html = _html()
    faces = re.findall(r"@font-face\{[^}]*\}", html)
    assert len(faces) == 2, \
        f"expected the latin and latin-ext subsets, found {len(faces)}"
    assert all("unicode-range:" in f for f in faces), \
        "a face declares no range, so it wins outright over the other"
    ranges = " ".join(faces)
    assert "U+0000-00FF" in ranges, "latin is gone — ASCII would fall back"
    assert "U+0100-02BA" in ranges, "latin-ext is gone — accented names would"
    print("  both subsets ship, each scoped by its unicode-range ✓")


def test_the_read_renders_light_for_everyone() -> None:
    """The report is a client deliverable. It must look the same on the brand
    manager's laptop as it did on ours, so it does NOT follow the reader's OS
    appearance — a report that is beige here and near-black there is a
    variable, not a document. Light is also the design's own primary.

    The dark palette is kept and stays reachable via data-theme="dark"; what
    is forbidden is switching automatically.
    """
    html = _html()
    assert "prefers-color-scheme" not in html, \
        "the read follows the reader's OS appearance — it must not"
    # the light ground colour is unconditional...
    assert "--bg:#edebe6" in html
    # ...and the dark one exists only behind an explicit opt-in
    assert "--bg:#131416" in html, "the dark palette was deleted, not gated"

    # Every dark token must sit inside a rule whose SELECTOR carries the
    # opt-in. Checked by walking back to the enclosing `{` and reading the
    # selector — a per-line check passes by accident here, because the dark
    # palette is a multi-line block and its selector is on an earlier line.
    css = html.split("<style>")[1].split("</style>")[0]
    for hit in re.finditer(r"#131416|#1d1f23|#ececea", css):
        open_brace = css.rfind("{", 0, hit.start())
        assert open_brace != -1, "dark token outside any rule"
        start = max(css.rfind("}", 0, open_brace), css.rfind("*/", 0, open_brace))
        selector = css[start + 1:open_brace]
        assert 'data-theme="dark"' in selector, \
            f"a dark token applies without the opt-in: selector {selector.strip()!r}"
    print("  the read renders light for everyone; dark is opt-in only ✓")


def test_model_generated_text_is_escaped() -> None:
    """Pains and quotes are LLM-authored; they can contain markup."""
    rep = _report()
    rep.pain_map = [Pain(
        id="P1", pain="<script>alert('x')</script> & a \"quoted\" claim. Rest of it.",
        funnel_stage="conversion", severity="execution", within_target=True,
        evidence_quotes=[Quote(quote="<b>bold</b>", disposition="d", round=1,
                               context="c")],
    )]
    html = _html(rep)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "<b>bold</b>" not in html and "&lt;b&gt;bold" in html
    print("  model-generated text is escaped ✓")


def test_split_lead_is_a_whole_sentence_and_never_clips_mid_clause() -> None:
    """The old renderer clipped the lead at 22 words, which cut 4 of the 6
    pains on a real run mid-clause ("…and largely already uses — so…") and
    then repeated the entire text from the start in the body underneath. The
    lead is now always a complete sentence and the body is strictly what
    follows it; the map view shortens with CSS instead of scissors."""
    lead, rest = _split_lead("The seal flickers. It never lands.")
    assert lead == "The seal flickers." and rest == "It never lands."
    lead2, rest2 = _split_lead("Costs 1.5x more e.g. per serving here.")
    assert rest2 == "" and lead2.startswith("Costs 1.5x")

    long_first = (
        "The creative presents the isolate as a familiar line-extension of a "
        "brand the target already trusts and largely already uses — so "
        "within-target recognition is instant but the ad never dramatizes a "
        "switching trigger. And then a second sentence."
    )
    lead3, rest3 = _split_lead(long_first)
    assert lead3.endswith("switching trigger."), lead3
    assert "…" not in lead3 and not lead3.endswith("—"), "lead was clipped mid-clause"
    assert rest3 == "And then a second sentence."
    assert not rest3.startswith(lead3[:20]), "the body restates the lead"
    print("  lead is a whole sentence; the body never restates it ✓")


# ---- the guardrails, on the page --------------------------------------


def test_disclaimer_always_renders() -> None:
    """E3: one prominent, honest disclaimer on every read."""
    html = _html()
    assert "simulated persona" in html and "not a survey" in html
    assert _DISC in html, "the disclaimer must keep its own bordered block"
    print("  E3: model-inferred disclaimer on the page ✓")


def test_inconclusive_page_shows_no_action_rate() -> None:
    """The strongest rule: an untrustworthy read shows no confident number."""
    d = _decision(decision="INCONCLUSIVE", target_action_rate=0.42,
                  target_action_num=8, target_action_denom=19,
                  by_cycle_position={"mid_cycle": {"rate": .5, "num": 4, "denom": 8}},
                  research_rate=0.3, research_num=6, research_denom=19)
    html = _html(_report(d, methodology_flags=["pool_archetype_mismatch"]))
    assert "INCONCLUSIVE" in html
    for forbidden in ("42%", "8 of 19", "would buy", "GLANCE RESPONSE",
                      "PURCHASE CYCLE", "30%", _HEADLINE):
        assert forbidden not in html, f"INCONCLUSIVE page leaked {forbidden!r}"
    assert "isn&#x27;t represented in your disposition library" in html
    print("  INCONCLUSIVE page shows no rate, headline, glance or cycle ✓")


def test_a4_cycle_breakdown_renders_with_its_blend_caveat() -> None:
    """A4: the per-cycle breakdown accompanies the blended headline, so the
    headline never hides its cycle-mix assumption — the rows AND the reason
    they are there."""
    d = _decision(by_cycle_position={
        "running_low": {"rate": 0.0, "num": 0, "denom": 5},
        "mid_cycle": {"rate": 0.222, "num": 2, "denom": 9},
        "just_bought": {"rate": 0.0, "num": 0, "denom": 4},
    })
    html = _html(_report(d))
    assert "PURCHASE CYCLE" in html
    assert "Running low" in html and "0 of 5" in html and "2 of 9" in html
    assert "read the rows, not just the blend" in html
    print("  A4: per-cycle breakdown renders with the blend caveat ✓")


def test_a3_research_is_reported_separately_never_as_a_sale() -> None:
    html = _html(_report(_decision(
        research_rate=0.2222, research_num=4, research_denom=18)))
    assert "would look it up first" in html
    assert "research, not a purchase" in html
    # ...and it is not folded into the buy line. Scoped to the headline element
    # itself: a slice of the surrounding markup would swallow the separate line
    # this test exists to keep separate, and pass for the wrong reason.
    headline = re.search(r'<div class="rk-headline">(.*?)</div>', html, re.S)
    assert headline, "no headline rendered"
    assert "22%" not in headline.group(1), \
        "the research rate leaked into the buy headline"
    assert "11%" in headline.group(1), "the buy rate is the headline"
    print("  A3: research reported separately, labelled not-a-sale ✓")


def test_a7_coherence_warning_renders() -> None:
    html = _html(_report(_decision(coherence_incoherent=True)))
    assert "COHERENCE" in html and "caution" in html
    print("  A7: coherence warning renders ✓")


def test_f3_scope_note_renders_for_unanchored_jobs() -> None:
    html = _html(_report(_decision(purpose="brand_building")),
                 purpose="brand_building")
    assert "BETA" in html and "HOW FAR TO TRUST IT" in html
    assert "BETA" not in _html(), "an anchored job must not cry wolf"
    print("  F3: launch-scope caveat renders only for unanchored jobs ✓")


def test_flags_render_in_plain_words_not_engine_tokens() -> None:
    """The flag reaches the page — but as a sentence, not as the token. A
    brand manager cannot act on `single_within_target`."""
    html = _html()
    assert "Only one consumer type fell within the declared target" in html
    assert "single_within_target" not in html, "raw flag token leaked to the client"
    print("  methodology flags render in plain words ✓")


def test_panel_agreement_observation_reaches_the_collapsed_block() -> None:
    """How alike the panel's segments were, against this brand's own history.
    It is an observation and not a flag — a >2 sigma detector would never fire
    on the real distribution (mean 0.69, sd 0.16, max 0.87, bar 1.01), and a
    check that cannot fire reads as a check that passed."""
    note = "Segments in this run reacted alike 87% of the time, against 69% typical."
    html = _html(homogeneity_note=note)
    assert "PANEL AGREEMENT" in html, "the observation lost its label"
    assert html_escape(note) in html, "the observation never reached the page"
    assert html.index(_METHOD) < html.index(html_escape(note)), \
        "panel agreement belongs in the run-configuration grid, not up the page"
    assert _in_collapsed_block(html, html_escape(note)), \
        "panel agreement escaped the collapsed block"
    assert "homogenization_high" not in html, "the suppressed flag came back as a token"
    print("  panel-agreement observation reaches the collapsed block ✓")


def test_a_coverage_gap_is_disclosed_at_the_FOOT_and_nowhere_else() -> None:
    """⚠ The user's explicit decision, 2026-08-14, and it is the opposite of
    what the design book proposed: *"we are not showing coverage gaps at all -
    all of this goes into the how did the run happen part at the end of the
    results page."*

    So there is no pre-spend warning, no banner, no strip above the findings.
    A gap in who was in the room is disclosed exactly where every other
    qualification now lives — collapsed, at the bottom, after the read.

    The gap this exists for (SY PB Bar, 2026-08-13): the classifier described
    "protein-curious snackers who like chocolate/wafer formats", the panel held
    only supplement buyers, and the run returned trust HIGH / confidence 84.
    """
    html = _html(_report(methodology_flags=["pool_coverage_gap"]))
    line = "Part of the audience this ad is aimed at is not represented"
    assert line in html, "the coverage gap never reached the read at all"
    assert _in_collapsed_block(html, line), (
        "the coverage gap escaped the collapsed block — it must not render "
        "above the findings"
    )
    assert html.index(_HEADLINE) < html.index(line), (
        "the coverage gap renders ABOVE the headline; the reader must meet the "
        "result before a qualification of it"
    )
    assert "pool_coverage_gap" not in html, "raw flag token leaked to the client"
    print("  a coverage gap discloses at the foot, never up the page ✓")


def test_a_coverage_gap_does_not_touch_the_verdict() -> None:
    """It DISCLOSES; it does not adjudicate. `pool_archetype_mismatch` forces
    METHODOLOGY_GAP and caps confidence at 20 — wiring this flag the same way
    would override the user's "nothing pre-spend" decision through the back
    door, by turning every partial gap into a headline."""
    r = _report(methodology_flags=["pool_coverage_gap"])
    assert r.verdict != "METHODOLOGY_GAP"
    html = _html(r)
    assert "Nobody in this audience fits the ad" not in html, (
        "the coverage-gap flag rendered the archetype-mismatch copy — the two "
        "are different findings and only one of them forces a verdict"
    )
    print("  a coverage gap discloses without changing the verdict ✓")


def test_the_headline_number_leads_uncaveated_and_the_caveat_is_findable() -> None:
    """⚠ The user's explicit decision, 2026-08-04, and the direction is the
    OPPOSITE of what this test used to pin.

    The buy-intent number keeps its position at the top of the result card and
    renders with NO caveat line beneath it. They were shown the measurement
    (signal-to-noise 1.0 — same-ad re-runs move it as much as different ads do)
    and offered the alternative of leading with the problem map, which does
    discriminate; they chose to keep the number leading. So the assertion is
    two-sided, and both sides are load-bearing:

      * nothing between the number and the next claim, in every state — a
        reinstated caveat line fails here;
      * HEADLINE_CAVEAT still on the page, in the collapsed block — a DELETED
        caveat fails here too. Moved, not dropped.

    Imports the constant rather than restating it: a copy in the test would go
    on passing after the page's wording drifted.
    """
    from agent.read_model import HEADLINE_CAVEAT

    escaped = html_escape(HEADLINE_CAVEAT)
    for decision in ("ITERATE", "SCALE", "RETARGET", "REBUILD"):
        rep = _report(_decision(decision=decision))
        rep.pain_map = _one_pain()
        html = _html(rep)
        assert escaped in html, f"the caveat was DELETED, not moved, on {decision}"
        assert _in_collapsed_block(html, escaped), \
            f"the headline caveat is back on the visible page on {decision}"
        # Nothing at all between the number and the diagnosis that follows it.
        between = html[html.index(_HEADLINE):html.index(_MAP)]
        assert escaped not in between, \
            f"a caveat line reappeared beside the number on {decision}"

    # INCONCLUSIVE prints no action rate at all. The standing caveats are
    # stated once regardless of state, so the block still carries it — what
    # must not happen is a caveat rendering beside a number that isn't there.
    inc = _html(_report(_decision(decision="INCONCLUSIVE", target_action_rate=None)))
    assert _in_collapsed_block(inc, escaped), \
        "the collapsed block lost its standing caveats on INCONCLUSIVE"
    print("  the headline number leads uncaveated; the caveat stays findable ✓")


def test_segment_differences_are_stated_plainly_and_the_caveat_is_findable() -> None:
    """⚠ Inverted 2026-08-04 on the user's explicit decision. The caveat used
    to render on all three surfaces that report a between-segment difference —
    the panel table, the champion line, and the target-vs-everyone-else bars.
    Three copies of the same qualification on one page is the pattern they
    asked to be rid of.

    It is now stated ONCE, in the collapsed block. Both directions are pinned:
    each of the three surfaces still renders its finding, and none of them
    renders the caveat.
    """
    from agent.read_model import SEGMENT_CAVEAT

    escaped = html_escape(SEGMENT_CAVEAT)
    l3 = {"segment_behavioral_distributions": {
        "enthusiast_macros_lifter::moderate": {
            "counts": {"scroll_past": 8}, "next_step_counts": {"nothing": 8}},
        "aspirant_clean_label::moderate": {
            "counts": {"scroll_past": 4, "save": 3},
            "next_step_counts": {"nothing": 4, "buy_now": 3}},
    }}
    table = _html(_report(), l3=l3)
    assert '<table class="rk-tbl"' in table, "no panel table — this test is vacuous"
    assert table.count(escaped) == 1, \
        "the segment caveat must be stated exactly once, not per surface"
    assert _in_collapsed_block(table, escaped), \
        "the segment caveat is back above the panel table"

    champ = _html(_report(_decision(
        decision="RETARGET", champion_disposition="aspirant_clean_label",
        champion_action_rate=0.42)))
    assert "Right ad, wrong person." in champ, "champion line missing — test is vacuous"
    assert champ.count(escaped) == 1 and _in_collapsed_block(champ, escaped), \
        "the champion line grew its own copy of the caveat back"

    rep = _report()
    rep.pain_map = _one_pain()
    bars = _html(rep, l3=l3)
    assert "EVERYONE ELSE" in bars, "no outside bar — this branch is untested"
    result_card = bars[:bars.index(_MAP)]
    assert escaped not in result_card, \
        "a caveat reappeared inside the result card beside the bars"
    assert _in_collapsed_block(bars, escaped), "the caveat was deleted, not moved"
    print("  segment differences read as findings; the caveat is stated once ✓")


def test_an_outsider_only_fix_sorts_last_without_announcing_the_machinery() -> None:
    """⚠ Inverted 2026-08-04 on the user's explicit decision. The floor still
    RUNS — it just stops narrating itself.

    What it does to the page is now ordering and nothing else: an outsider-only
    fix sorts after the in-target ones, with no "NOT RANKED" heading and no
    reason attached. The customer sees three changes in a sensible order; the
    reasoning stays ours.

    ⚠ All three still render. `_validate_prescription` requires exactly three,
    so dropping the demoted one would show two with no explanation — a gap
    worse than the heading this replaces.

    Also pins that `bet_ranking` is passed through UNTOUCHED and in order. The
    bets carry no reference to any pain, so there is no deterministic way to
    demote one; reordering or dropping a numbered lever on a guess would be the
    read inventing a ranking the engine never produced."""
    from agent.read_model import OUT_OF_TARGET_ONLY_NOTE

    # ⚠ The outsider-only fix is listed FIRST on purpose. With the in-target
    # one first, "sort the demoted fix last" and "do not sort at all" emit
    # byte-identical pages, and the ordering assertion below passes without
    # testing anything — which is exactly what a mutation run caught.
    rep = _report(
        top_3_changes=[
            TopChange(change="fix for outsiders only", why="w",
                      derives_from_pains=["P2"], lever_class="media_buy"),
            TopChange(change="fix for the target", why="w",
                      derives_from_pains=["P1"], lever_class="creative"),
        ],
        bet_ranking=["bet one", "bet two", "bet three"],
    )
    rep.pain_map = [
        Pain(id="P1", pain="In-target problem. Second sentence.",
             funnel_stage="conversion", severity="execution", within_target=True),
        Pain(id="P2", pain="Outsider problem. Second sentence.",
             funnel_stage="attention", severity="execution", within_target=False),
    ]
    html = _html(rep)

    assert "NOT RANKED" not in html, "the demotion heading is back on the page"
    assert "fix for the target" in html and "fix for outsiders only" in html, \
        "a change was dropped — all three must render"
    assert html.index("fix for the target") < html.index("fix for outsiders only"), \
        "the floor stopped ordering: the outsider-only fix must sort last"
    # Moved, not deleted — and only surfaced when the floor actually moved
    # something, so it never describes machinery that did nothing.
    assert _in_collapsed_block(html, html_escape(OUT_OF_TARGET_ONLY_NOTE)), \
        "the reason was deleted rather than moved to the collapsed block"
    clean = _html(_report(top_3_changes=[
        TopChange(change="only fix", why="w", derives_from_pains=["P1"],
                  lever_class="creative")]))
    assert html_escape(OUT_OF_TARGET_ONLY_NOTE) not in clean, \
        "a run where nothing was demoted still explains the demotion rule"

    # bet_ranking: every bet, in the engine's order, numbered from 1.
    for i, bet in enumerate(["bet one", "bet two", "bet three"], 1):
        assert bet in html, f"lever {bet!r} was dropped"
    assert html.index("bet one") < html.index("bet two") < html.index("bet three"), \
        "the levers were reordered — the floor must not reach bet_ranking"
    print("  outsider-only fix demoted with its reason; bet_ranking untouched ✓")


def test_breadth_chip_reaches_both_problem_surfaces_with_its_denominator() -> None:
    """The chip is composed by `ReadModel.breadth_line` and rendered twice — the
    map card and the problem card. It must be the SAME string in both, and it
    must never regress to a bare "1 type", which had no denominator and no
    indication of how much evidence sat behind it.

    Driven through the rendered page rather than asserted against the source,
    because `_marker` feeds two call sites and pinning one would leave the other
    free to drift."""
    quote = "the big grey tub reads as gym-bro kit and that is not me"
    rep = _report()
    rep.pain_map = [Pain(
        id="P1", pain="The load-bearing one. Second sentence.",
        funnel_stage="conversion", severity="execution", within_target=True,
        cited_by=["enthusiast_macros_lifter"],
        evidence_quotes=[Quote(quote=quote, disposition="enthusiast_macros_lifter",
                               round=1, context="commute_scroll")])]
    html = _html(rep, l3={"segment_behavioral_distributions": {
        "enthusiast_macros_lifter::moderate": {"counts": {"scroll_past": 4}},
        "aspirant_clean_label::moderate": {"counts": {"scroll_past": 6}},
    }}, transcripts=[
        {"agent_id": 3, "encoding_text": f"R1 GUT: {quote}", "reflection_text": ""}])

    chip = "1 of 2 consumer types · quoted from 1 person"
    assert html.count(html_escape(chip)) == 2, \
        "the chip must render identically on the map card AND the problem card"
    assert ">1 type<" not in html, "the old denominator-free chip came back"
    print("  breadth chip reaches both problem surfaces, with its denominator ✓")


def test_provisional_dispositions_and_engine_read_reach_methodology() -> None:
    html = _html(_report(provisional_dispositions=["skeptic_new_thing"]))
    assert "PROVISIONAL DISPOSITIONS" in html and "skeptic new thing" in html
    assert "MIXED" in html and "76/100" in html
    print("  provisional dispositions + engine read reach methodology ✓")


def test_audience_verdict_renders_in_both_directions() -> None:
    """v2.1: a confident headline must never sit over a silent mismatch — and
    the check passing is a claim worth stating too."""
    from agent.schema import AudienceMatch
    rep = _report()
    rep.audience_match = AudienceMatch(
        verdict="mismatched", declared_summary="men 18-24",
        inferred_summary="women 35-54",
        message="The creative's apparent target (women 35-54) does not match the "
                "declared audience (men 18-24).")
    html = _html(rep)
    # ⚠ The mismatch is a FINDING ABOUT THE AD, not a qualification of our
    # instrument, so it is the one qualifier-shaped thing that stayed on the
    # visible page in the 2026-08-04 change. Pinned to the header, ABOVE the
    # diagnosis, and pinned to render exactly once.
    assert html.count("AUDIENCE MISMATCH") == 1, \
        "the mismatch is stated twice — it belongs in the header alone"
    assert html.index("AUDIENCE MISMATCH") < html.index(_VERDICT), \
        "the mismatch left the run header"
    assert "women 35-54" in html and "men 18-24" in html

    rep2 = _report()
    rep2.audience_match = AudienceMatch(
        verdict="aligned", declared_summary="adults 25-44",
        inferred_summary="adults 25-44", message="consistent with the buy")
    html2 = _html(rep2)
    assert "AUDIENCE MISMATCH" not in html2, "an aligned read must not cry wolf"
    assert "AUDIENCE ALIGNED" in html2 and "consistent with the buy" in html2
    print("  v2.1: mismatch warns, alignment is stated, neither is silent ✓")


def test_funnel_projection_is_explained_not_dropped() -> None:
    from agent.schema import FunnelProjection, FunnelRates
    rep = _report()
    rep.funnel_projection = FunnelProjection(overall=FunnelRates(
        stop_rate=.1, stop_band=(.05, .15), click_rate=.01, click_band=(.005, .02),
        visit_rate=.008, visit_band=(.004, .012), convert_rate=.001,
        convert_band=(.0005, .002)))
    assert "not charted here" in _html(rep)
    assert "not fitted to in-market outcomes" in _html()
    print("  funnel explained whether off or computed-but-withheld ✓")


def test_engine_scoping_vocabulary_never_reaches_the_page() -> None:
    """Out-of-target pains arrive prefixed with the assess pass's own scoping
    note. The page already carries within/outside as a visual state, so the
    prefix is a duplicate — and it is engine jargon, verbatim, opening a
    sentence a client reads."""
    rep = _report()
    rep.pain_map = [Pain(
        id="P5",
        pain=("OUTSIDE-TARGET CONTEXT (not verdict-load-bearing): among lapsed "
              "buyers the ad reactivates a filed negative memory. And more."),
        funnel_stage="attention", severity="structural", within_target=False)]
    html = _html(rep)
    assert "OUTSIDE-TARGET CONTEXT" not in html
    assert "verdict-load-bearing" not in html
    assert "Among lapsed buyers" in html, "the pain itself must survive the strip"
    assert "OUTSIDE TARGET" in html, "the scope is still carried — as a chip"
    print("  engine scoping vocabulary stripped; the scope stays as data ✓")


def test_pain_lead_is_whole_and_the_body_adds_rather_than_repeats() -> None:
    long_pain = (
        "The creative reaches its within-target audience as recognized-but-inert "
        "because every enthusiast already runs the sibling SKU and instantly "
        "frames this as a lateral variant rather than a genuine upgrade with a "
        "distinct payoff worth paying more for. Second sentence here."
    )
    rep = _report(strengths_to_preserve=[], top_3_changes=[])
    rep.pain_map = [Pain(id="P1", pain=long_pain, funnel_stage="consideration",
                         severity="execution", within_target=True)]
    html = _html(rep)
    section = html.split(_PROBLEMS)[1]
    lead = re.search(r'<div class="lead"[^>]*>(.*?)</div>', section, re.S)
    assert lead, "problem card rendered no lead"
    text = lead.group(1).strip()
    assert text.endswith("worth paying more for."), text[-60:]
    assert "…" not in text, "the lead was clipped mid-clause"
    # the second sentence survives, and the first is not printed twice
    assert "Second sentence here." in section
    assert section.count("recognized-but-inert") == 1, \
        "the expanded body repeats the lead it sits under"
    print("  pain lead is whole; the body adds instead of repeating ✓")


def test_panel_degradation_renders() -> None:
    html = _html(panel_health={"degraded": True, "succeeded": 96, "expected": 100})
    assert "PANEL" in html and "96 of 100" in html
    print("  panel degradation renders ✓")


def test_within_target_pains_lead_even_when_they_leak_later() -> None:
    """Within-target pains gate the decision, so they sort first — ahead of an
    out-of-target pain that leaks at an EARLIER funnel stage. The fixture
    deliberately carries no load-bearing pain: with one, load-bearing-first
    ordering satisfies this assertion on its own and the within-target rule
    goes untested.
    """
    rep = _report(_decision(load_bearing_pain_id=""))
    rep.pain_map = [
        Pain(id="P9", pain="An outside-target pain. Second sentence.",
             funnel_stage="attention", severity="execution", within_target=False),
        Pain(id="P1", pain="A within-target pain. Second sentence.",
             funnel_stage="conversion", severity="execution", within_target=True),
    ]
    cards = _html(rep).split(_PROBLEMS)[1]
    assert cards.index("A within-target pain") < cards.index("An outside-target pain"), \
        "a within-target pain must lead an earlier-stage outside-target one"
    assert "OUTSIDE TARGET" in cards and "WITHIN TARGET" in cards
    print("  within-target pains lead, even when they leak later ✓")


def test_load_bearing_pain_is_marked_on_the_card_not_only_the_map() -> None:
    """The map and the cards both mark it. Asserting page-wide passes on the
    map alone, so the card — the surface a reader actually opens — is checked
    on its own."""
    rep = _report()
    rep.pain_map = [
        Pain(id="P9", pain="An outside-target pain. Second sentence.",
             funnel_stage="attention", severity="execution", within_target=False),
        Pain(id="P1", pain="The load-bearing one. Second sentence.",
             funnel_stage="conversion", severity="execution", within_target=True),
    ]
    html = _html(rep)
    cards = html.split(_PROBLEMS)[1]
    assert "LOAD-BEARING" in cards, "the load-bearing marker never reached the cards"
    assert cards.index("The load-bearing one") < cards.index("An outside-target pain")
    print("  the load-bearing pain is marked on the card, and leads ✓")


# ---- page order — the design's fixed sequence --------------------------


def test_page_renders_the_designed_section_order() -> None:
    """header -> result -> problem map -> problems -> fixes -> what worked ->
    panel -> disclaimer -> extras -> how this read was made.

    This order is the user's design and is fixed. ⚠ The warnings strip that
    used to open the page is GONE by their explicit decision, 2026-08-04 — the
    page now opens on a finding, and every qualifier lives in the collapsed
    block that closes it.
    """
    rep = _report(bet_ranking=["lever one"])
    rep.pain_map = _one_pain()
    html = _html(rep, l3={"segment_behavioral_distributions": _PANEL_DISTS})
    assert 'class="rk-warn"' not in html, \
        "the warnings strip is back — the page opens on a qualification again"
    # Each marker must identify one element. The collapsed block also says
    # "N simulated consumers"; if the panel marker ever matched that instead,
    # this test would be asserting the order of the wrong thing and passing.
    for marker in (_VERDICT, _HEADLINE, _MAP, _PANEL, _DISC, _MADE, _METHOD):
        assert html.count(marker) == 1, f"ambiguous section marker: {marker!r}"
    beats = [
        ("result", html.index(_VERDICT)),
        ("problem map", html.index(_MAP)),
        ("problems", html.index(_PROBLEMS)),
        ("levers", html.index(_LEVERS)),
        ("detailed changes", html.index(_FIXES)),
        ("what worked", html.index(_WORKED)),
        ("panel", html.index(_PANEL)),
        ("disclaimer", html.index(_DISC)),
        ("extras", html.index(_VOICE)),
        ("how it was made", html.index(_MADE)),
    ]
    for (name_a, at_a), (name_b, at_b) in zip(beats, beats[1:]):
        assert at_a < at_b, f"{name_b} must follow {name_a}, not precede it"
    print("  the designed section order holds end to end ✓")


def test_the_problem_map_is_the_hero_and_leads_the_diagnosis() -> None:
    """The headline number cannot lead: under v3 buy-intent reads 0% on six of
    the last eight runs. The map is what actually differs between a good read
    and a bad one, so it comes before the problem cards it summarises."""
    rep = _report()
    rep.pain_map = _one_pain()
    html = _html(rep)
    assert html.index(_MAP) < html.index(_PROBLEMS)
    assert html.index(_HEADLINE) < html.index(_MAP), \
        "the map belongs to the diagnosis, after the result"
    print("  the problem map leads the diagnosis ✓")


def test_the_trust_chip_stays_and_the_apology_beneath_it_does_not() -> None:
    """⚠ 2026-08-04. `trust_note` used to render immediately under the decision
    — "thin evidence (one narrow audience engaged); treat as a lead, not a
    verdict" — which was the most self-undermining sentence on the page AND a
    duplicate: the collapsed block's WHY DIRECTIONAL row says the same thing
    with the reason attached.

    The line separating a signal from an apology: a one-word quality marker is
    a FINDING and stays visible; the sentence talking the reader out of the
    result is not, and moves. So this pins three things at once — chip present,
    note absent from the visible page, explanation still reachable.
    """
    rep = _report(_decision(decision="ITERATE",
                            within_dispositions=["enthusiast_macros_lifter"]))
    rep.pain_map = _one_pain()
    m = _model(rep)
    note = m.trust_note
    assert note, "no trust note on this fixture — the assertion below is vacuous"
    html = render_html(m, embed_image=False)

    assert "TRUST: DIRECTIONAL" in html, "the trust chip was removed with the note"
    assert html.index("TRUST: DIRECTIONAL") < html.index(_MAP), \
        "the chip is a finding and belongs on the visible page"
    assert html_escape(note) not in html, \
        "the trust note is back under the decision, apologising for the read"
    # The substance survives, with its reason, where someone can go and find it.
    assert _in_collapsed_block(html, "WHY DIRECTIONAL"), \
        "the note was dropped without its explanation surviving anywhere"
    print("  the trust chip stays; the sentence apologising for it does not ✓")


def test_the_verdict_states_itself_and_its_caveat_survives_every_state() -> None:
    """⚠ Inverted 2026-08-04 on the user's explicit decision. VERDICT_CAVEAT
    used to render under the decision chip in every state; the decision now
    states itself.

    The caveat is NOT gone — it keeps the user's own wording and is stated once
    in the collapsed block, unconditionally, in every state including
    INCONCLUSIVE where the card renders differently. A guardrail conditional on
    state is a guardrail that gets missed, and that half of the old contract
    still holds; only its position changed.
    """
    from agent.read_model import VERDICT_CAVEAT
    escaped = html_escape(VERDICT_CAVEAT)
    for decision in ("ITERATE", "SCALE", "RETARGET", "REBUILD", "INCONCLUSIVE"):
        rate = None if decision == "INCONCLUSIVE" else 0.11
        rep = _report(_decision(decision=decision, target_action_rate=rate,
                                within_dispositions=[] if rate is None
                                else ["enthusiast_macros_lifter"]))
        rep.pain_map = _one_pain()
        html = _html(rep)
        assert escaped in html, f"the verdict caveat was DELETED on {decision}"
        assert _in_collapsed_block(html, escaped), \
            f"the verdict caveat is back on the visible page on {decision}"
        decision_card = html[html.index(_VERDICT):html.index(_MAP)]
        assert escaped not in decision_card, \
            f"the caveat reappeared under the decision chip on {decision}"
    print("  the verdict states itself; its caveat survives in the block ✓")


def test_ranked_levers_stay_adjacent_to_the_fixes_they_summarise() -> None:
    """The lever list is the summary and the changes are the detail behind it.
    The heading is decision-keyed call-to-action copy ("TO GET A TRUSTWORTHY
    READ:" on INCONCLUSIVE), so separating them reads as two competing
    prescriptions."""
    rep = _report(bet_ranking=["lever one", "lever two"])
    rep.pain_map = _one_pain()
    html = _html(rep)
    assert html.index(_PROBLEMS) < html.index(_LEVERS) < html.index(_FIXES)
    between = html[html.index(_LEVERS):html.index(_FIXES)]
    assert _WORKED not in between and _PANEL not in between, \
        "a section wedged between the levers and the fixes they summarise"
    print("  ranked levers stay adjacent to the fixes they summarise ✓")


def test_every_qualifier_is_present_and_none_precedes_a_finding() -> None:
    """⚠ The exact inverse of what this test used to assert, and the single
    most important test of the 2026-08-04 change. It is deliberately two-sided,
    because each side alone is satisfiable by the wrong outcome:

      * PRESENT — every qualifier still reaches the page. Passing this half
        alone would be satisfied by leaving them scattered inline.
      * AFTER THE FINDINGS — none of them renders before the verdict, the
        number, or the diagnosis. Passing this half alone would be satisfied
        by deleting them outright, which is NOT what the user asked for: they
        asked for them to be separate and findable, not absent.

    A run is constructed with every qualifier firing at once, because the
    empty-strip case is the common one and would make this vacuous.
    """
    from agent.schema import AudienceMatch
    rep = _report()
    rep.audience_match = AudienceMatch(
        verdict="mismatched", declared_summary="men 18-24",
        inferred_summary="women 35-54",
        message="The creative's apparent target does not match the declared audience.")
    rep.pain_map = _one_pain()
    html = _html(rep, panel_health={"degraded": True, "succeeded": 96,
                                    "expected": 100},
                 scope_note="brand-building is BETA",
                 coherence_warning="buy intent contradicts the glance")
    made_at = html.index(_MADE)
    pains_at = html.index(_PROBLEMS)
    # "AUDIENCE MISMATCH" is deliberately absent from this list: it is a
    # finding about the creative, not a qualification of the instrument, and
    # `test_audience_verdict_renders_in_both_directions` pins it to the header.
    for label in ("HOW FAR TO TRUST IT", "COHERENCE",
                  "96 of 100", "Only one consumer type"):
        assert label in html, f"qualifier DELETED rather than moved: {label}"
        at = html.index(label)
        assert at > pains_at, f"{label!r} still renders before the diagnosis"
        assert at > made_at, f"{label!r} is outside the collapsed block"
    # The block must actually be collapsed. A <div> here would put all of it
    # back on the page while every assertion above still passed.
    assert '<details class="rk-card rk-made"' in html, \
        "the qualifiers are in the right place but nothing collapses them"
    print("  every qualifier survives, and none of them precedes a finding ✓")


def test_inconclusive_says_so_before_any_diagnosis() -> None:
    """When the engine does not trust its own read, leading with the diagnosis
    is actively wrong. The untrustworthy notice comes first, exactly once, and
    no action rate appears at all."""
    d = _decision(decision="INCONCLUSIVE", target_action_rate=None,
                  within_dispositions=[], rationale="no within-target read")
    rep = _report(d)
    rep.pain_map = [
        Pain(id="P1", pain="A pain the engine does not stand behind. Second.",
             funnel_stage="conversion", severity="execution", within_target=True),
    ]
    html = _html(rep)
    notice = "isn&#x27;t trustworthy yet"
    assert notice in html, "INCONCLUSIVE notice missing"
    assert html.index(notice) < html.index(_PROBLEMS), \
        "INCONCLUSIVE must be stated before the diagnosis is read"
    assert _HEADLINE not in html, "INCONCLUSIVE must not render an action rate"
    assert html.count(notice) == 1, \
        "INCONCLUSIVE tagline rendered twice — the second points at nothing"
    print("  INCONCLUSIVE notice precedes the diagnosis, once, with no numbers ✓")


def test_empty_diagnosis_drops_both_of_its_beats_cleanly() -> None:
    """No pains means BOTH the map and the problem cards vanish — the map is
    derived from the same pain_map, so an empty one must not leave a heading
    over an empty grid."""
    rep = _report()
    rep.pain_map = []
    html = _html(rep)
    assert _MAP not in html, "the problem map left a heading with no problems"
    assert _PROBLEMS not in html, "the problem section left a shell"
    assert _FIXES in html, "the solutions beat must survive an empty diagnosis"
    assert html.index(_VERDICT) < html.index(_HEADLINE) < html.index(_FIXES)
    print("  empty diagnosis drops both beats cleanly, story still ordered ✓")


def test_problem_map_counts_and_never_loses_a_funnel_stage() -> None:
    """The map is the beat that makes the pattern visible: how many problems,
    how many land on the audience being bought, how many are structural, and
    where in the funnel they sit. A stage with nothing wrong must read Clear
    rather than vanish — a renderer holding four stages against a schema of
    five silently dropped every `recall` pain once already."""
    rep = _report()
    rep.pain_map = [
        Pain(id="P1", pain="Generic stock opening. Second sentence.",
             funnel_stage="attention", severity="execution", within_target=True,
             cited_by=["enthusiast_macros_lifter", "aspirant_clean_label"]),
        Pain(id="P2", pain="Price framing misreads. Second sentence.",
             funnel_stage="comprehension", severity="execution", within_target=True),
        Pain(id="P3", pain="No reason to switch brands. Second sentence.",
             funnel_stage="recall", severity="structural", within_target=False),
    ]
    html = _html(rep)
    assert ("3 problems — 2 within target · 1 outside · 2 execution · 1 structural"
            in html)
    for stage in ("Attention", "Comprehension", "Consideration", "Conversion",
                  "Recall"):
        assert stage in html, f"funnel stage missing from the map: {stage}"
    assert html.count(">Clear</div>") == 2, \
        "stages with no problems must read Clear, not disappear"
    assert "2 types" in html, "breadth must render"
    assert "LOAD-BEARING" in html, "the one to fix first must be marked"
    print("  the map counts, keeps every stage, marks the load-bearing one ✓")


def test_every_map_card_opens_and_opening_lifts_the_clamp() -> None:
    """A map card shows two clamped lines of a pain whose shortest authored
    lead on disk is 121 characters — so every card is hiding text, and a card
    that cannot be opened is a dead end the reader can see into but not reach.

    Two halves, and the second is the one that rots: making the card a
    `<details>` is not enough on its own. If the clamp survives the open state
    the card expands and its first sentence stays cut off — a half-fix that a
    test asserting only "it is a details element" passes happily.
    """
    from agent.dashboard_html import _CSS

    long_lead = ("The creative reads its own audience as someone other than "
                 "the viewer, and within-target buyers slot it as adjacent "
                 "rather than for-me at the attention seam.")
    rest = "The packaging already speaks their language."
    rep = _report()
    rep.pain_map = [
        Pain(id="P1", pain=f"{long_lead} {rest}", funnel_stage="attention",
             severity="execution", within_target=True, cited_by=["a", "b"]),
        # Single sentence: 17 of 99 authored pains have no remainder. It must
        # still open (the lead alone overflows) but emit no empty detail box.
        Pain(id="P2", pain=long_lead, funnel_stage="recall",
             severity="structural", within_target=False),
    ]
    html = _html(rep)
    # Scoped to the map section. `<div class="detail">` is also what the full
    # problem cards below emit, so counting it page-wide measures those too —
    # the assert-on-a-pattern-that-appears-twice trap this repo keeps hitting.
    mapped = html[html.index(_MAP):html.index(_PROBLEMS)]
    assert _MAP not in mapped[len(_MAP):] and len(mapped) < len(html), \
        "the slice did not isolate the map — the rest of this proves nothing"

    assert mapped.count('<details class="rk-pcard"') == 2, \
        "a map card that is not a <details> cannot be opened without JavaScript"
    # The exact structure, not just the words. The open/shut labels are hidden
    # by the stylesheet's `details[open]>summary .shut` pair, so a card that
    # kept the text but lost the `shut`/`opened` classes would show "More ▾"
    # and "Less ▴" side by side — which is how this same affordance was broken
    # once already, and counting the strings cannot see it.
    affordance = ('<span class="rk-more" style="margin-left:auto;font-size:9.5px">'
                  '<span class="shut">More ▾</span>'
                  '<span class="opened">Less ▴</span></span>')
    assert mapped.count(affordance) == 2, \
        "the card must say it can be opened, with one label showing at a time"
    for rule in ("details[open]>summary .shut{display:none}",
                 "details:not([open])>summary .opened{display:none}"):
        assert rule in _CSS, f"nothing hides the other label: {rule}"

    # Half two: the open state has to remove the clamp, mask and all.
    rule = "details[open]>summary .rk-clamp{max-height:none"
    assert rule in _CSS, \
        "opening a card leaves its lead clamped — it expands but stays cut off"
    unclamp = _CSS[_CSS.index(rule):_CSS.index(rule) + 120]
    assert "mask-image:none" in unclamp, \
        "max-height alone leaves the fade-out mask over the last line"

    # The remainder travels with the card, and only when there is one.
    assert mapped.count('<div class="detail">') == 1, \
        "P2 has no second sentence and must not render an empty detail block"
    assert html_escape(rest) in mapped, "the remainder never reached the map card"
    print("  2 map cards open, the clamp lifts, and the empty one stays empty ✓")


# ---- the panel table ---------------------------------------------------


_PANEL_DISTS = {
    "enthusiast_macros_lifter::moderate": {
        "counts": {"scroll_past": 14, "linger": 4},
        "next_step_counts": {"nothing": 12, "buy_at_restock": 2, "research_first": 4}},
    "skeptic_lapsed_protein::moderate": {
        "counts": {"scroll_past": 12, "linger": 2, "save": 1},
        "next_step_counts": {"nothing": 12, "mention_to_someone": 3}},
}


def _panel_html(within, dists, **kw):
    rep = _report(_decision(within_dispositions=within, **kw))
    rep.pain_map = _one_pain()
    return _html(rep, l3={"segment_behavioral_distributions": dists})


def test_panel_table_shows_out_of_target_types_the_headline_hides() -> None:
    """The table exists because the in-target slice cannot answer 'who else
    responded'. Out-of-target rows, their counts and their next steps must all
    reach the page."""
    html = _panel_html(["enthusiast_macros_lifter"], _PANEL_DISTS)
    assert "enthusiast macros lifter" in html and "skeptic lapsed protein" in html
    assert "TARGET" in html, "the in-target row must be marked"
    assert "3 would mention it to someone" in html, \
        "an out-of-target next step must reach the page — it is word of mouth"
    assert "All 33 people in the panel" in html, "the real denominator"
    print("  panel table renders out-of-target types + their next steps ✓")


def test_panel_table_is_suppressed_on_an_inconclusive_read() -> None:
    """NEW against the design, which rendered this table unconditionally. An
    untrustworthy read must not show response rates by ANY route, and the
    table is a second door onto the numbers the headline hides."""
    html = _panel_html([], _PANEL_DISTS, decision="INCONCLUSIVE",
                       target_action_rate=None, rationale="no within-target read")
    assert 'class="rk-tbl"' not in html, "no response-rate table by any route"
    assert "skeptic lapsed protein" not in html, \
        "INCONCLUSIVE leaked per-type response data"
    print("  panel table suppressed on INCONCLUSIVE ✓")


def test_panel_table_vanishes_cleanly_with_no_l3() -> None:
    rep = _report()
    rep.pain_map = _one_pain()
    html = _html(rep)                     # no l3 at all
    assert 'class="rk-tbl"' not in html
    assert _HEADLINE in html, "the rest of the result beat still renders"
    print("  panel table vanishes cleanly when there is no L3 ✓")


def test_panel_columns_cover_every_action_or_say_so() -> None:
    """The table's action columns are a hand-maintained list inside a
    renderer — the exact shape that lost every saver from the denominator
    once before. An action with no column is reported underneath rather than
    silently dropped."""
    dists = {
        "enthusiast_macros_lifter::moderate": {
            "counts": {"scroll_past": 10, "linger": 3, "save": 1, "tap_cta": 2,
                       "share": 1},
            "next_step_counts": {"nothing": 12, "buy_at_restock": 5}},
    }
    html = _panel_html(["enthusiast_macros_lifter"], dists)
    assert "without a column above" in html
    assert "2 tap cta" in html and "1 share" in html, \
        "an uncovered action vanished from the page"
    # and the row's own n still counts everyone
    assert ">17<" in html, "the row total must include the uncovered actions"
    print("  actions with no column are reported, never dropped ✓")


def test_decoupling_note_renders_when_outsiders_out_respond_the_target() -> None:
    """Real on ProSki: an in-target type went 23/23 scroll-past while the
    outsiders out-responded them. It is invisible on every in-target-only
    view, which is the entire reason the table exists."""
    dists = {
        "enthusiast_macros_lifter::moderate": {
            "counts": {"scroll_past": 20},
            "next_step_counts": {"nothing": 20}},
        "switcher_results_chaser::moderate": {
            "counts": {"scroll_past": 12, "linger": 8},
            "next_step_counts": {"nothing": 12, "research_first": 8}},
    }
    html = _panel_html(["enthusiast_macros_lifter"], dists)
    assert "The people you are NOT buying responded more" in html
    # ...and the EVERYONE ELSE bar says so too. The design drew a flat block
    # there because everyone outside scrolled on the run it was built from; a
    # bar that cannot show the difference reports "nobody" on a run like this.
    assert "8 of 20 did something other than scroll past" in html
    assert "Scrolled past — 20 of 20" not in html, \
        "the outside bar claimed a clean scroll-past over 8 responders"
    # The bar itself is drawn from the OUTSIDE slice alone. Checking only the
    # legend leaves the segments free to be pooled across the whole panel,
    # which on a narrow ad is the outside bar plus the target's 20 scrollers.
    bar = html.split("EVERYONE ELSE")[1].split("did something other")[0]
    assert "flex:12" in bar and "flex:8" in bar, bar
    assert "flex:32" not in bar, "the target was pooled into the outside bar"
    print("  the decoupling note and the outside bar both reach the page ✓")


def test_the_denominator_stays_legible_on_the_page() -> None:
    """An 18-of-100 panel is not a small sample by accident — it is one
    audience type out of six. The old renderer said so with a 'who it reached'
    chip row; this design carries the same property in the map's zone labels
    and the panel table's TARGET badge, so the property is pinned, not the
    widget."""
    html = _panel_html(["enthusiast_macros_lifter"], _PANEL_DISTS)
    assert "WITHIN TARGET — 18 OF 33" in html
    assert "OUTSIDE — 15 OF 33" in html
    assert "not just the 18 you&#x27;re buying" in html
    print("  the in-target denominator is legible without the reach widget ✓")


# ---- empty / degenerate shapes ----------------------------------------


def test_empty_sections_are_omitted_not_broken() -> None:
    rep = _report(
        top_3_changes=[], strengths_to_preserve=[], context_fit_map={},
        verbatim_consumer_voice=[], bet_ranking=[],
    )
    rep.pain_map = []
    rep.target_match = TargetMatch()
    html = _html(rep)
    for absent in (_FIXES, _WORKED, _VOICE, _MAP, _PROBLEMS, "WHERE IT LANDS"):
        assert absent not in html, f"empty section rendered a shell: {absent}"
    assert "ITERATE" in html and "simulated persona" in html
    print("  empty sections omitted; decision + disclaimer still render ✓")


def test_no_glance_data_means_no_glance_bar() -> None:
    """An empty glance is 'no data', never a 0% bar."""
    html = _html()  # no l3_summary.json written
    assert "GLANCE RESPONSE" not in html
    print("  missing glance data -> no bar (not a false 0%) ✓")


def test_retarget_champion_line_renders_and_handles_null_rate() -> None:
    d = _decision(decision="RETARGET", champion_disposition="switcher_results_chaser",
                  champion_action_rate=None)
    html = _html(_report(d))
    assert "Right ad, wrong person" in html
    assert "switcher results chaser" in html
    assert "None" not in html.split("Right ad, wrong person")[1][:200]
    print("  RETARGET champion line renders, null rate handled ✓")


def test_blinded_shape_degrades_without_leaving_empty_furniture() -> None:
    """The decoy render strips the label, the creative, the run id and the
    declared targeting. Each of those has its own block in this header, and an
    empty block is both a visual defect and a hint."""
    m = _model(declared_targeting="")
    m.asset_label = "Read A"
    m.asset_path = None
    m.run_id = "read-a"
    m.declared_audience = ""
    m.audience_aligned = None
    html = render_html(m, embed_image=False)
    assert "DECLARED TARGETING" not in html, "empty targeting row rendered"
    assert "AUDIENCE ALIGNED" not in html and "AUDIENCE MISMATCH" not in html
    assert "data:image" not in html, "a creative was embedded into a blinded read"
    assert "Read A" in html and "simulated persona" in html, \
        "the diagnosis and its disclaimer must survive blinding"
    print("  blinded shape degrades cleanly, guardrails intact ✓")
