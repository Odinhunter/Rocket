"""ReadModel — the guardrails a client-facing read must never lose.

The client artifact may curate which FINDINGS it shows; it may not drop a
GUARDRAIL. Each test below pins one guardrail to its triggering condition,
so a future renderer change that silently drops one fails here rather than
in front of a prospect.

Offline: builds synthetic run directories, never touches runs/ (gitignored)
and never calls the API.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent.read_model import (
    Glance,
    build_read_model,
    headline_metric_line,
    inconclusive_lines,
    purpose_scope_note,
    trust_line,
    within_target_glance,
)
from agent.schema import Decision, Report, TargetMatch, TopChange


def _decision(**kw) -> Decision:
    base = dict(
        decision="ITERATE", target_action_rate=0.1111, trust="DIRECTIONAL",
        target_action_num=2, target_action_denom=18,
        within_dispositions=["enthusiast_macros_lifter"],
        load_bearing_pain_id="P1", rationale="load-bearing within pain P1 is fixable",
    )
    base.update(kw)
    return Decision(**base)


def _report(decision: Decision | None = None, **kw) -> Report:
    base = dict(
        verdict="MIXED", confidence=76, target_match=TargetMatch(),
        top_3_changes=[TopChange(change=f"c{i}", why="w") for i in range(3)],
        strengths_to_preserve=[], context_fit_map={}, verbatim_consumer_voice=[],
        methodology_flags=["single_within_target"],
        decision=decision if decision is not None else _decision(),
    )
    base.update(kw)
    return Report(**base)


def _run_dir(
    report: Report | None, *, tmp: Path, status: str = "complete",
    purpose: str = "direct_sell", l3: dict | None = None,
    replay: Report | None = None, panel_health: dict | None = None,
) -> Path:
    rd = tmp / "run_x"
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "run.json").write_text(json.dumps({
        "run_id": "run_x", "status": status,
        "updated_at": "2026-07-25T00:00:00+00:00",
        "panel_health": panel_health,
        "config": {
            "asset": {"image_path": "assets/x.png", "label": "Test Creative"},
            "category": "health_wellness_nutrition",
            "account_id": "demo", "brand_profile_id": "b",
            "declared_targeting": "adults 25-44",
            "creative_inputs": {"purpose": purpose},
            "audience_spec": {"panel_size": 100},
        },
        "report": report.to_dict() if report is not None else None,
    }))
    if replay is not None:
        (rd / "replay_report.json").write_text(json.dumps(replay.to_dict()))
    if l3 is not None:
        (rd / "l3_summary.json").write_text(json.dumps(l3))
    return rd


# ---- the glance: exact segment matching -------------------------------


def test_glance_matches_disposition_exactly() -> None:
    """Segment keys are '<disposition>::<chaos_band>'. Prefix-matching would
    merge two dispositions sharing a prefix and silently inflate the sample."""
    segs = {
        "enthusiast_macros_lifter::deliberate": {
            "counts": {"scroll_past": 6}},
        "enthusiast_macros_lifter::moderate": {
            "counts": {"scroll_past": 5, "linger": 3}},
        # shares the 'enthusiast_macros' prefix — must NOT be counted
        "enthusiast_macros_lifter_lapsed::moderate": {
            "counts": {"scroll_past": 40, "linger": 20}},
    }
    g = within_target_glance(segs, ["enthusiast_macros_lifter"])
    assert g.scroll_past == 11 and g.linger == 3 and g.n == 14, g.to_dict()

    # bare disposition granularity (no '::') resolves too
    g2 = within_target_glance(
        {"enthusiast_macros_lifter": {"counts": {"scroll_past": 2, "tap_through": 1}}},
        ["enthusiast_macros_lifter"],
    )
    assert g2.n == 3 and g2.tap_through == 1

    # no within-target dispositions -> empty, NOT a 0% bar
    assert within_target_glance(segs, []).n == 0
    assert Glance().rate("linger") == 0.0
    print("  glance: exact '::' split, no prefix bleed, empty-set safe ✓")


# ---- report source resolution -----------------------------------------


def test_report_source_run_json_replay_and_loud_failure() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rd = _run_dir(_report(), tmp=tmp)
        assert build_read_model(rd).report_source == "run.json"

        # A crashed run recovered by replay_synthesis carries no report in
        # run.json but has replay_report.json.
        import shutil
        shutil.rmtree(rd)
        rd = _run_dir(None, tmp=tmp, status="committed", replay=_report())
        m = build_read_model(rd)
        assert m.report_source == "replay_report.json"
        assert m.decision_name == "ITERATE"

        # Neither -> fail LOUDLY. Rendering a blank read for a prospect is
        # far worse than an error.
        shutil.rmtree(rd)
        rd = _run_dir(None, tmp=tmp, status="committed")
        try:
            build_read_model(rd)
            raise AssertionError("expected a loud failure on a report-less run")
        except ValueError as exc:
            assert "replay_synthesis" in str(exc)
    print("  report source: run.json | replay_report.json | loud failure ✓")


# ---- the guardrails ----------------------------------------------------


def test_inconclusive_never_carries_an_action_rate() -> None:
    """spec §4: an untrustworthy read must NEVER show a confident action-rate
    headline — even when target_action_rate happens to be non-None."""
    d = _decision(decision="INCONCLUSIVE", target_action_rate=0.42,
                  rationale="the pool doesn't contain this ad's audience")
    rep = _report(d, methodology_flags=["pool_archetype_mismatch"])
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(rep, tmp=Path(td)))
    assert m.is_inconclusive
    assert m.headline is None, "INCONCLUSIVE must not produce a headline metric"
    assert m.inconclusive, "INCONCLUSIVE must explain why + what to change"
    body = " ".join(m.inconclusive)
    assert "42%" not in body and "0.42" not in body
    assert "isn't represented in your disposition library" in body
    print("  A: INCONCLUSIVE -> no action rate, explains why + the fix ✓")


def test_a4_cycle_rows_accompany_the_blended_headline() -> None:
    """A4: the blended headline must never hide its cycle-mix assumption."""
    d = _decision(by_cycle_position={
        "mid_cycle": {"rate": 0.222, "num": 2, "denom": 9},
        "running_low": {"rate": 0.0, "num": 0, "denom": 5},
        "just_bought": {"rate": 0.0, "num": 0, "denom": 4},
    })
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(d), tmp=Path(td)))
    assert [r["key"] for r in m.cycle_rows] == ["running_low", "mid_cycle", "just_bought"], \
        "cycle rows must render in buying-cycle order, not dict order"
    assert m.cycle_rows[0]["denom"] == 5
    print("  A4: per-cycle breakdown present, in cycle order ✓")


def test_a3_research_is_separate_and_only_on_buy_frame_jobs() -> None:
    """A3: 'would research' is reported separately, never folded into buy."""
    d = _decision(research_rate=0.2222, research_num=4, research_denom=18)
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(d), tmp=Path(td)))
        assert m.research_line and "22%" in m.research_line
        assert "research, not a purchase" in m.research_line
        assert "22%" not in (m.headline or ""), "research must not enter the buy headline"

        # cold_hook is not a buy-frame job: no research companion.
        d2 = _decision(purpose="cold_hook", research_rate=0.5,
                       research_num=9, research_denom=18)
        m2 = build_read_model(
            _run_dir(_report(d2), tmp=Path(td) / "b", purpose="cold_hook"))
        assert m2.research_line is None
    print("  A3: research reported separately, buy-frame jobs only ✓")


def test_a7_coherence_warning_surfaces() -> None:
    d = _decision(coherence_incoherent=True)
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(d), tmp=Path(td)))
    assert m.coherence_warning and "caution" in m.coherence_warning
    print("  A7: coherence warning surfaces ✓")


def test_f3_launch_scope_note_per_purpose() -> None:
    """F3: an unanchored per-purpose metric carries its caveat to the page."""
    assert purpose_scope_note("direct_sell") is None
    assert purpose_scope_note("cold_hook") is None
    assert "BETA" in purpose_scope_note("brand_building")
    assert "PARKED" in purpose_scope_note("awareness_informer")
    assert "PARKED" in purpose_scope_note("retain_winback")
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(
            _report(_decision(purpose="brand_building")), tmp=Path(td),
            purpose="brand_building"))
    assert m.scope_note and "BETA" in m.scope_note
    print("  F3: launch-scope caveat reaches the model for unanchored jobs ✓")


def test_a6_trust_line_reflects_within_disposition_count() -> None:
    assert "DIRECTIONAL" in trust_line(_decision(trust="DIRECTIONAL"))
    high = trust_line(_decision(
        trust="HIGH", within_dispositions=["a", "b"], target_action_denom=40))
    assert "HIGH" in high and "2 within-target dispositions agree" in high
    print("  A6: trust line reflects the within-disposition count ✓")


def test_panel_degradation_is_disclosed() -> None:
    """A read built on a partly-landed panel must not look clean."""
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(
            _report(), tmp=Path(td),
            panel_health={"degraded": True, "succeeded": 96, "expected": 100}))
    assert m.panel_degraded and "96 of 100" in m.panel_degraded
    print("  panel degradation disclosed ✓")


def test_funnel_note_present_whether_projection_exists_or_not() -> None:
    """D4: the funnel is off by default; say so rather than showing nothing.
    And when --funnel DID run, the projection must not silently vanish."""
    from agent.schema import FunnelProjection, FunnelRates
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(), tmp=Path(td)))
        assert m.funnel_note and "not fitted to in-market outcomes" in m.funnel_note

        rep = _report()
        rep.funnel_projection = FunnelProjection(overall=FunnelRates(
        stop_rate=.1, stop_band=(.05,.15), click_rate=.01, click_band=(.005,.02),
        visit_rate=.008, visit_band=(.004,.012), convert_rate=.001,
        convert_band=(.0005,.002)))
        m2 = build_read_model(_run_dir(rep, tmp=Path(td) / "f"))
        assert m2.funnel_note and "not charted here" in m2.funnel_note
    print("  D4: funnel note carried both ways (off, and computed-but-withheld) ✓")


def test_audience_mismatch_reaches_the_model() -> None:
    """v2.1: the creative reads as aimed at someone other than the audience
    being bought. It must qualify every number on the page, not vanish."""
    from agent.schema import AudienceMatch
    with tempfile.TemporaryDirectory() as td:
        aligned = _report()
        aligned.audience_match = AudienceMatch(
            verdict="aligned", declared_summary="all genders aged 25-44",
            inferred_summary="an unclear demographic", message="consistent")
        m = build_read_model(_run_dir(aligned, tmp=Path(td)))
        assert m.audience_mismatch is None
        assert m.declared_audience == "all genders aged 25-44"

        bad = _report()
        bad.audience_match = AudienceMatch(
            verdict="mismatched", declared_summary="men 18-24",
            inferred_summary="women 35-54",
            message="The creative's apparent target (women 35-54) does not match "
                    "the declared audience (men 18-24).")
        m2 = build_read_model(_run_dir(bad, tmp=Path(td) / "m"))
        assert m2.audience_mismatch and "women 35-54" in m2.audience_mismatch
    print("  v2.1: audience mismatch reaches the model; aligned stays quiet ✓")


def test_headline_metric_phrased_for_the_job() -> None:
    assert "would buy" in headline_metric_line(_decision())
    assert "stopped and leaned in" in headline_metric_line(_decision(purpose="cold_hook"))
    assert "remembered the brand" in headline_metric_line(
        _decision(purpose="brand_building"))
    assert "audience types" in headline_metric_line(
        _decision(purpose="awareness_informer"))
    print("  headline metric phrased per the ad's job ✓")


def test_legacy_report_without_decision_stays_honest() -> None:
    """A pre-2.3 report has no decision layer — don't invent one."""
    legacy = Report(
        verdict="MIXED", confidence=70, target_match=TargetMatch(),
        top_3_changes=[TopChange(change=f"c{i}", why="w") for i in range(3)],
        strengths_to_preserve=[], context_fit_map={}, verbatim_consumer_voice=[],
        methodology_flags=[], decision=None,
    )
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(legacy, tmp=Path(td)))
    assert m.decision_name == "INCONCLUSIVE" and m.headline is None
    assert m.inconclusive
    print("  legacy (decision-less) report renders as INCONCLUSIVE, not invented ✓")


def test_inconclusive_copy_branches_on_the_flag() -> None:
    unsignaled = " ".join(inconclusive_lines(
        _report(_decision(decision="INCONCLUSIVE"),
                methodology_flags=["target_unsignaled"])))
    assert "doesn't clearly signal who it's for" in unsignaled
    print("  INCONCLUSIVE copy branches on the methodology flag ✓")
