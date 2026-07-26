"""report_html — the guardrails must reach the PAGE, not just the model.

A guardrail that lives in ReadModel but never renders is not a guardrail.
These tests assert the honesty surfaces appear in the emitted HTML under the
condition that triggers them, plus the properties the artifact must hold:
self-contained (no external requests) and correctly escaped.

Offline: synthetic reports, no API, no runs/ dependency.
"""

from __future__ import annotations

import re
from html import escape as html_escape

from agent.read_model import ReadModel
from agent.report_html import _split_lead, render_html
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
    from agent.read_model import build_read_model
    import json, tempfile
    from pathlib import Path
    report = report or _report()
    purpose = kw.pop("purpose", report.decision.purpose if report.decision else "direct_sell")
    td = tempfile.mkdtemp()
    rd = Path(td) / "r"
    rd.mkdir()
    (rd / "run.json").write_text(json.dumps({
        "run_id": "run_x", "status": "complete",
        "panel_health": kw.pop("panel_health", None),
        "config": {
            "asset": {"image_path": "", "label": kw.pop("label", "Test Creative")},
            "category": "health_wellness_nutrition", "account_id": "demo",
            "brand_profile_id": "b", "creative_inputs": {"purpose": purpose},
            "audience_spec": {"panel_size": 100},
        },
        "report": report.to_dict(),
    }))
    if "l3" in kw:
        (rd / "l3_summary.json").write_text(json.dumps(kw.pop("l3")))
    m = build_read_model(rd)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def _html(report: Report | None = None, **kw) -> str:
    return render_html(_model(report, **kw), embed_image=False)


# ---- properties of the artifact ---------------------------------------


def test_page_is_self_contained() -> None:
    """No external CSS, font, script or image request — the page must render
    identically served, opened from disk, or published."""
    html = _html()
    for pattern in (r'src="https?://', r'href="https?://', r'@import',
                    r'<script'):
        assert not re.search(pattern, html), f"external/dynamic resource: {pattern}"
    assert "<style>" in html and "prefers-color-scheme" in html
    print("  page is self-contained + theme-aware ✓")


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


def test_split_lead_does_not_split_on_abbreviations_or_decimals() -> None:
    lead, rest = _split_lead("The seal flickers. It never lands.")
    assert lead == "The seal flickers." and rest == "It never lands."
    lead2, rest2 = _split_lead("Costs 1.5x more e.g. per serving here.")
    assert rest2 == "" and lead2.startswith("Costs 1.5x")
    print("  lead/body split is sentence-accurate ✓")


# ---- the guardrails, on the page --------------------------------------


def test_disclaimer_always_renders() -> None:
    """E3: one prominent, honest disclaimer on every read."""
    html = _html()
    assert "simulated persona" in html and "not a survey" in html
    print("  E3: model-inferred disclaimer on the page ✓")


def test_inconclusive_page_shows_no_action_rate() -> None:
    """The strongest rule: an untrustworthy read shows no confident number."""
    d = _decision(decision="INCONCLUSIVE", target_action_rate=0.42,
                  target_action_num=8, target_action_denom=19,
                  by_cycle_position={"mid_cycle": {"rate": .5, "num": 4, "denom": 8}},
                  research_rate=0.3, research_num=6, research_denom=19)
    html = _html(_report(d, methodology_flags=["pool_archetype_mismatch"]))
    assert "INCONCLUSIVE" in html
    for forbidden in ("42%", "8 of 19", "would buy", "The 2-second glance",
                      "buying cycle", "30%"):
        assert forbidden not in html, f"INCONCLUSIVE page leaked {forbidden!r}"
    assert "isn&#x27;t represented in your disposition library" in html
    print("  A: INCONCLUSIVE page shows no action rate, tiles, glance or cycle ✓")


def test_a4_cycle_table_renders() -> None:
    d = _decision(by_cycle_position={
        "running_low": {"rate": 0.0, "num": 0, "denom": 5},
        "mid_cycle": {"rate": 0.222, "num": 2, "denom": 9},
        "just_bought": {"rate": 0.0, "num": 0, "denom": 4},
    })
    html = _html(_report(d))
    assert "buying cycle" in html
    assert "running low" in html and "0 of 5" in html and "2 of 9" in html
    # the honest caveat that the headline is a blend
    assert "read the rows, not just the blend" in html
    print("  A4: per-cycle table renders with the blend caveat ✓")


def test_a3_research_tile_is_labelled_not_a_sale() -> None:
    html = _html(_report(_decision(
        research_rate=0.2222, research_num=4, research_denom=18)))
    assert "Would research first" in html
    assert "never counted as a sale" in html
    print("  A3: research rendered separately, labelled not-a-sale ✓")


def test_a7_coherence_warning_renders() -> None:
    html = _html(_report(_decision(coherence_incoherent=True)))
    assert "Coherence check" in html and "caution" in html
    print("  A7: coherence warning renders ✓")


def test_f3_scope_note_renders_for_unanchored_jobs() -> None:
    html = _html(_report(_decision(purpose="brand_building")),
                 purpose="brand_building")
    assert "BETA" in html and "How much to trust the headline" in html
    # ...and does NOT appear for an anchored job
    assert "BETA" not in _html()
    print("  F3: launch-scope caveat renders only for unanchored jobs ✓")


def test_flags_and_provisional_dispositions_reach_the_footer() -> None:
    rep = _report(provisional_dispositions=["skeptic_new_thing"])
    html = _html(rep)
    assert "single_within_target" in html
    assert "provisional dispositions" in html and "skeptic_new_thing" in html
    assert "MIXED" in html and "76/100" in html
    print("  methodology flags + provisional dispositions in the footer ✓")


def test_audience_mismatch_warning_renders() -> None:
    """v2.1: a confident headline must never sit over a silent mismatch."""
    from agent.schema import AudienceMatch
    rep = _report()
    rep.audience_match = AudienceMatch(
        verdict="mismatched", declared_summary="men 18-24",
        inferred_summary="women 35-54",
        message="The creative's apparent target (women 35-54) does not match the "
                "declared audience (men 18-24).")
    html = _html(rep)
    assert "Audience mismatch" in html
    assert "women 35-54" in html and "men 18-24" in html
    # ...and an aligned read does not cry wolf
    rep2 = _report()
    rep2.audience_match = AudienceMatch(
        verdict="aligned", declared_summary="adults 25-44",
        inferred_summary="adults 25-44", message="consistent")
    assert "Audience mismatch" not in _html(rep2)
    print("  v2.1: audience-mismatch warning renders; aligned stays quiet ✓")


def test_funnel_projection_is_explained_not_dropped() -> None:
    from agent.schema import FunnelProjection, FunnelRates
    rep = _report()
    rep.funnel_projection = FunnelProjection(overall=FunnelRates(
        stop_rate=.1, stop_band=(.05,.15), click_rate=.01, click_band=(.005,.02),
        visit_rate=.008, visit_band=(.004,.012), convert_rate=.001,
        convert_band=(.0005,.002)))
    assert "not charted here" in _html(rep)
    assert "not fitted to in-market outcomes" in _html()
    print("  D4: funnel explained whether off or computed-but-withheld ✓")


def test_pain_lead_stays_short_enough_to_read_as_a_headline() -> None:
    """The lead is set at display weight; a 40-word first sentence becomes a
    wall of bold. Long leads fall back to body text."""
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
    # scope to the diagnosis section so a strength/fix card can't satisfy this
    section = html.split("the diagnosis")[1]
    lead = re.search(r'<div class="t">(.*?)</div>', section, re.S)
    assert lead, "pain card rendered no lead"
    n = len(lead.group(1).split())
    assert n <= 24, f"pain lead is {n} words — too long for display weight"
    # nothing is lost: the clipped words and the second sentence both survive
    assert "worth paying more for" in section
    assert "Second sentence here." in section
    print(f"  pain lead capped at {n} words for display weight; full text kept ✓")


def test_panel_degradation_renders() -> None:
    html = _html(panel_health={"degraded": True, "succeeded": 96, "expected": 100})
    assert "Sample note" in html and "96 of 100" in html
    print("  panel degradation renders ✓")


def test_load_bearing_pain_is_marked_and_ordered_first() -> None:
    rep = _report()
    rep.pain_map = [
        Pain(id="P9", pain="An outside-target pain. Second sentence.",
             funnel_stage="attention", severity="execution", within_target=False),
        Pain(id="P1", pain="The load-bearing one. Second sentence.",
             funnel_stage="conversion", severity="execution", within_target=True),
    ]
    html = _html(rep)
    assert "the one to fix first" in html
    assert html.index("The load-bearing one") < html.index("An outside-target pain"), \
        "within-target load-bearing pain must lead the diagnosis"
    assert "outside target" in html
    print("  load-bearing pain marked + ordered first; outside-target labelled ✓")


# ---- page order — the five-beat story ----------------------------------
#
# The client page tells one story, in the order the brand manager reads it:
#
#     result -> diagnosis -> problems -> solutions -> extras
#
# Two placements inside that carry honesty weight and are pinned here:
#   * the caveats render ABOVE the result — three of the four qualify the
#     NUMBERS (coherence, launch scope, panel degradation), so below the
#     result band they would each arrive after the number they qualify;
#   * the verdict bucket CLOSES the result beat rather than heading it. It is
#     the element that scored a deliberately-bad control the same as real ads
#     (docs/v3_discriminant_check.md), so it summarises the measured mix
#     rather than standing in for it, and it carries its own caveat.
#
# These are cross-section order assertions; before them the suite had none,
# so nothing verified the layout at all.


_DIAG_H = "Why they're not buying — the diagnosis"
_PAINS_H = "The problems in detail"
_FIXES_H = "The fixes in detail"
_NUMBERS_H = "The numbers that matter"
_VERDICT_MARK = '<div class="decision">'


def _one_pain() -> list:
    return [Pain(id="P1", pain="The load-bearing one. Second sentence.",
                 funnel_stage="conversion", severity="execution",
                 within_target=True)]


def test_page_tells_the_five_beat_story_in_order() -> None:
    """result -> diagnosis -> problems -> solutions -> extras."""
    rep = _report(bet_ranking=["lever one"])
    rep.pain_map = _one_pain()
    html = _html(rep)
    for heading in (_DIAG_H, _PAINS_H, _FIXES_H, _NUMBERS_H):
        assert heading in html, f"missing section: {heading}"
    beats = [
        ("result (verdict)", html.index(_VERDICT_MARK)),
        ("result (numbers)", html.index(_NUMBERS_H)),
        ("diagnosis", html.index(_DIAG_H)),
        ("problems", html.index(_PAINS_H)),
        ("solutions", html.index(_FIXES_H)),
        ("extras", html.index("Simulated consumer voice")),
    ]
    for (name_a, at_a), (name_b, at_b) in zip(beats, beats[1:]):
        assert at_a < at_b, f"{name_b} must follow {name_a}, not precede it"
    print("  result -> diagnosis -> problems -> solutions -> extras ✓")


def test_verdict_leads_the_page_and_never_without_its_caveat() -> None:
    """The verdict opens the report (the user's call). That makes the caveat
    inside it the ONLY thing qualifying the page's headline claim for a reader
    who goes no further — the bucket scored a deliberately-bad control the
    same as real ads. So the caveat must render inside the block, above the
    numbers, on every read: it is what pays for leading with the bucket.
    """
    from agent.read_model import VERDICT_CAVEAT
    rep = _report()
    rep.pain_map = _one_pain()
    html = _html(rep)
    assert html.index(_VERDICT_MARK) < html.index(_NUMBERS_H), \
        "the verdict must lead the result beat"
    assert html.index(_VERDICT_MARK) < html.index(_DIAG_H), \
        "the verdict belongs to the result beat, above the diagnosis"
    # The caveat contains an apostrophe, so match the ESCAPED form the page
    # actually emits — matching the raw constant would silently never be found.
    caveat_at = html.index(html_escape(VERDICT_CAVEAT))
    assert html.index(_VERDICT_MARK) < caveat_at < html.index(_NUMBERS_H), \
        "the known-bad-control caveat must sit inside the verdict block itself"


def test_verdict_caveat_survives_every_decision_state() -> None:
    """A guardrail that is conditional on state is a guardrail that gets
    missed. The bucket now leads the page in every state, so its caveat rides
    with it in every state — including INCONCLUSIVE, where the block renders
    without its tagline."""
    from agent.read_model import VERDICT_CAVEAT
    escaped = html_escape(VERDICT_CAVEAT)
    for decision in ("ITERATE", "SCALE", "RETARGET", "REBUILD", "INCONCLUSIVE"):
        rate = None if decision == "INCONCLUSIVE" else 0.11
        rep = _report(_decision(decision=decision, target_action_rate=rate,
                                within_dispositions=[] if rate is None
                                else ["enthusiast_macros_lifter"]))
        rep.pain_map = _one_pain()
        html = _html(rep)
        assert escaped in html, f"verdict caveat missing on {decision}"
        assert html.index(_VERDICT_MARK) < html.index(escaped), \
            f"caveat escaped its block on {decision}"
    print("  verdict leads the page and never renders without its caveat ✓")


def test_ranked_levers_stay_adjacent_to_the_fixes_they_summarise() -> None:
    """_bets is the ranked lever list, _fixes is the detail behind it — both
    are prescription and must stay together. _bets' heading is decision-keyed
    call-to-action copy ("TO GET A TRUSTWORTHY READ:" on INCONCLUSIVE), so
    separating them reads as two competing fixes sections.
    """
    rep = _report(bet_ranking=["lever one", "lever two"])
    rep.pain_map = _one_pain()
    html = _html(rep)
    bets_at = html.index("highest-leverage first")
    assert html.index(_PAINS_H) < bets_at < html.index(_FIXES_H), \
        "ranked levers must sit between the problems and the detailed fixes"
    print("  ranked levers stay adjacent to the fixes they summarise ✓")


def test_every_caveat_precedes_the_result_it_qualifies() -> None:
    """A caveat read after the number is not a caveat. Three of these four
    qualify the NUMBERS, not the diagnosis — the coherence check qualifies the
    buy tile, launch scope the headline metric, panel degradation every
    denominator — so asserting only that they precede the pain cards would
    pass while each still arrived after the figure it exists to qualify.
    """
    from agent.schema import AudienceMatch
    rep = _report()
    rep.audience_match = AudienceMatch(
        verdict="mismatched", declared_summary="men 18-24",
        inferred_summary="women 35-54",
        message="The creative's apparent target does not match the declared audience.")
    rep.pain_map = _one_pain()
    html = _html(rep, panel_health={"degraded": True, "succeeded": 96, "expected": 100},
                 scope_note="brand-building is BETA", coherence_warning="A7: mismatch")
    numbers_at, pains_at = html.index(_NUMBERS_H), html.index(_PAINS_H)
    verdict_at = html.index(_VERDICT_MARK)
    for label in ("Audience mismatch", "How much to trust the headline",
                  "Coherence check", "Sample note"):
        assert label in html, f"warning missing entirely: {label}"
        assert html.index(label) < verdict_at, \
            f"{label!r} rendered after the verdict it qualifies"
        assert html.index(label) < numbers_at, \
            f"{label!r} rendered after the numbers it qualifies"
        assert html.index(label) < pains_at, \
            f"{label!r} rendered after the diagnosis it qualifies"
    print("  all four caveats precede the verdict, numbers AND diagnosis ✓")


def test_inconclusive_says_so_before_any_diagnosis() -> None:
    """The sharpest case for the reorder: when the engine does not trust its
    own read, 'lead with the diagnosis' is actively wrong. The untrustworthy
    notice must come first, and no action rate may appear at all."""
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
    assert html.index(notice) < html.index(_PAINS_H), \
        "INCONCLUSIVE must be stated before the diagnosis is read"
    assert _NUMBERS_H not in html, "INCONCLUSIVE must not render an action rate"
    # The tagline reads "…see why below", and the why now lives at the TOP of
    # the page. It must appear exactly once — repeating it in the bucket would
    # point at nothing. (html.index alone can't catch this: it returns the
    # first hit and says nothing about a second.)
    assert html.count(notice) == 1, \
        "INCONCLUSIVE tagline rendered twice — the second points 'below' at nothing"
    tail = html[html.index(_VERDICT_MARK):]
    assert notice not in tail[:tail.index("</div>") + 6], \
        "the bucket repeats the 'see why below' tagline with no reasons under it"
    print("  INCONCLUSIVE notice precedes the diagnosis, renders once, no numbers ✓")


def test_empty_diagnosis_drops_both_of_its_beats_cleanly() -> None:
    """No pains means BOTH the diagnosis overview and the problem cards
    vanish — the overview is derived from the same pain_map, so an empty one
    must not leave a heading over an empty panel. The story closes up from
    result straight to solutions rather than leaving a shell."""
    rep = _report()
    rep.pain_map = []
    html = _html(rep)
    assert _DIAG_H not in html, "diagnosis overview left a heading with no problems"
    assert _PAINS_H not in html, "problem section left a shell"
    assert _FIXES_H in html, "the solutions beat must survive an empty diagnosis"
    assert html.index(_VERDICT_MARK) < html.index(_NUMBERS_H) < html.index(_FIXES_H), \
        "with no diagnosis the order is still result -> solutions"
    print("  empty diagnosis drops both beats cleanly, story still ordered ✓")


def test_diagnosis_overview_counts_the_problems_before_the_detail() -> None:
    """The overview is the beat that makes the pattern visible: how many
    problems, how many land on the audience being bought, how many are
    structural. It must render those counts, and point at the one to fix."""
    rep = _report()
    rep.pain_map = [
        Pain(id="P1", pain="Generic stock opening. Second sentence.",
             funnel_stage="attention", severity="execution", within_target=True,
             cited_by=["enthusiast_macros_lifter", "aspirant_clean_label"]),
        Pain(id="P2", pain="Price framing misreads. Second sentence.",
             funnel_stage="comprehension", severity="execution", within_target=True),
        Pain(id="P3", pain="No reason to switch brands. Second sentence.",
             funnel_stage="consideration", severity="structural", within_target=False),
    ]
    html = _html(rep)
    assert "3 problems, leaking at 3 stages of the funnel." in html
    assert "2 hit the audience you&#x27;re buying; 1 land" in html
    assert "1 is structural" in html, "the structural count must be stated"
    assert "raised by 2 different buyer types" in html, "breadth must render"
    # load_bearing_pain_id is P1 on the shared fixture decision.
    assert "Start with <b>P1</b>" in html, "the one to fix first must be named"
    # Every funnel stage renders; only the leaking ones are marked.
    assert html.count('class="st ') + html.count('class="st st--leak"') >= 4
    assert 'class="st st--leak">attention' in html
    assert 'class="st">conversion' in html, \
        "a stage with no problems must render unmarked, not vanish"
    print("  diagnosis overview counts, marks leaking stages, names the lead ✓")


_PANEL_H = "Who else responded — every consumer type"


def _panel_html(within, dists, **kw):
    rep = _report(_decision(within_dispositions=within, **kw))
    rep.pain_map = _one_pain()
    return _html(rep, l3={"segment_behavioral_distributions": dists})


_PANEL_DISTS = {
    "enthusiast_macros_lifter::moderate": {
        "counts": {"scroll_past": 14, "linger": 4},
        "next_step_counts": {"nothing": 12, "buy_at_restock": 2, "research_first": 4}},
    "skeptic_lapsed_protein::moderate": {
        "counts": {"scroll_past": 12, "linger": 2, "save": 1},
        "next_step_counts": {"nothing": 12, "mention_to_someone": 3}},
}


def test_panel_table_shows_out_of_target_types_the_headline_hides() -> None:
    """The table exists because the in-target slice cannot answer 'who else
    responded'. Out-of-target rows, their counts and their next steps must all
    reach the page."""
    html = _panel_html(["enthusiast_macros_lifter"], _PANEL_DISTS)
    assert _PANEL_H in html
    assert "enthusiast macros lifter" in html and "skeptic lapsed protein" in html
    assert "your target" in html and "not targeted" in html, "in/out must be marked"
    assert "would mention it to someone" in html, \
        "an out-of-target next step must reach the page — it is word of mouth"
    assert "All 33 people in the panel" in html, "the real denominator"
    print("  panel table renders out-of-target types + their next steps ✓")


def test_panel_table_is_suppressed_on_an_inconclusive_read() -> None:
    """An untrustworthy read must not show response rates by ANY route. The
    table is a second door onto the same numbers the headline hides."""
    html = _panel_html([], _PANEL_DISTS, decision="INCONCLUSIVE",
                       target_action_rate=None, rationale="no within-target read")
    assert _PANEL_H not in html, "INCONCLUSIVE must not render the panel table"
    assert 'class="ptab"' not in html, "no response-rate table by any route"
    print("  panel table suppressed on INCONCLUSIVE ✓")


def test_panel_table_vanishes_cleanly_with_no_l3() -> None:
    """Same empty-case contract as the diagnosis overview: no heading over an
    empty panel."""
    rep = _report()
    rep.pain_map = _one_pain()
    html = _html(rep)                     # no l3 at all
    assert _PANEL_H not in html and 'class="ptab"' not in html
    assert _NUMBERS_H in html, "the rest of the result beat still renders"
    print("  panel table vanishes cleanly when there is no L3 ✓")


def test_panel_table_sits_in_the_result_beat_after_the_numbers() -> None:
    """It reframes the headline, so it must follow it — you need to have read
    '2 of 18' before 'and here is the other 81' — and still precede the
    diagnosis."""
    html = _panel_html(["enthusiast_macros_lifter"], _PANEL_DISTS)
    assert html.index(_VERDICT_MARK) < html.index(_NUMBERS_H) < html.index(_PANEL_H), \
        "the panel table must follow the numbers it reframes"
    assert html.index(_PANEL_H) < html.index(_DIAG_H), \
        "the panel table belongs to the result beat, above the diagnosis"
    print("  panel table sits in the result beat, after the numbers ✓")


def test_reach_row_makes_the_denominator_legible() -> None:
    html = _html()
    assert "1 of 2 audience types" in html
    assert "enthusiast macros lifter" in html and "aspirant clean label" in html
    print("  who-it-reached row renders (denominator legible) ✓")


# ---- empty / degenerate shapes ----------------------------------------


def test_empty_sections_are_omitted_not_broken() -> None:
    rep = _report(
        top_3_changes=[], strengths_to_preserve=[], context_fit_map={},
        verbatim_consumer_voice=[], bet_ranking=[],
    )
    rep.pain_map = []
    rep.target_match = TargetMatch()
    html = _html(rep)
    for absent in ("The fixes in detail", "What's working", "Where it lands",
                   "Simulated consumer voice", "Who it reached"):
        assert absent not in html, f"empty section rendered a shell: {absent}"
    assert "ITERATE" in html and "simulated persona" in html
    print("  empty sections omitted; decision + disclaimer still render ✓")


def test_no_glance_data_means_no_glance_bar() -> None:
    """An empty glance is 'no data', never a 0% bar."""
    html = _html()  # no l3_summary.json written
    assert "The 2-second glance" not in html
    print("  missing glance data -> no bar (not a false 0%) ✓")


def test_retarget_champion_line_renders_and_handles_null_rate() -> None:
    d = _decision(decision="RETARGET", champion_disposition="switcher_results_chaser",
                  champion_action_rate=None)
    html = _html(_report(d))
    assert "Right ad, wrong person" in html
    assert "switcher results chaser" in html
    assert "None" not in html.split("Right ad, wrong person")[1][:200]
    print("  RETARGET champion line renders, null rate handled ✓")
