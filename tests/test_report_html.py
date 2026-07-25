"""report_html — the guardrails must reach the PAGE, not just the model.

A guardrail that lives in ReadModel but never renders is not a guardrail.
These tests assert the honesty surfaces appear in the emitted HTML under the
condition that triggers them, plus the properties the artifact must hold:
self-contained (no external requests) and correctly escaped.

Offline: synthetic reports, no API, no runs/ dependency.
"""

from __future__ import annotations

import re

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
