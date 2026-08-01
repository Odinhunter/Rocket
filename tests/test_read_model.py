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
    build_diagnosis_overview,
    build_read_model,
    headline_metric_line,
    inconclusive_lines,
    purpose_scope_note,
    trust_line,
    within_target_glance,
)
from agent.schema import Decision, Pain, Report, TargetMatch, TopChange


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
        {"enthusiast_macros_lifter": {"counts": {"scroll_past": 2, "tap_cta": 1}}},
        ["enthusiast_macros_lifter"],
    )
    assert g2.n == 3 and g2.tap_cta == 1

    # no within-target dispositions -> empty, NOT a 0% bar
    assert within_target_glance(segs, []).n == 0
    assert Glance().rate("linger") == 0.0
    print("  glance: exact '::' split, no prefix bleed, empty-set safe ✓")


def test_glance_counts_every_action_never_shortens_the_denominator() -> None:
    """The original Glance summed a hand-listed three: scroll_past, linger and
    `tap_through` — which is NOT in the action enum (it is `tap_cta`), so that
    segment was structurally always 0, while `save` and `share` were dropped
    from n entirely. A saved ad is the strongest signal in the set and it was
    erasing the respondent, shortening every denominator on the page."""
    g = within_target_glance(
        {"d::moderate": {"counts": {
            "scroll_past": 11, "linger": 10, "save": 3, "share": 1, "tap_cta": 2}}},
        ["d"],
    )
    assert g.n == 27, f"every respondent must count: {g.to_dict()}"
    assert g.save == 3 and g.share == 1 and g.tap_cta == 2
    assert g.engaged == 16, "engaged = everyone who did not scroll past"
    # rates are over the true total, not a filtered subtotal
    assert abs(g.rate("save") - 3 / 27) < 1e-9

    # `tap_cta` is the real enum value; the dead `tap_through` name is gone
    assert not hasattr(g, "tap_through")

    # an action nobody anticipated still counts toward n rather than vanishing
    g2 = within_target_glance(
        {"d": {"counts": {"scroll_past": 5, "some_future_action": 2}}}, ["d"])
    assert g2.n == 7, "an unrecognised action must not drop the respondent"
    assert any(k == "some_future_action" for k, _, _, _ in g2.segments()), \
        "unknown actions must still render, not disappear"

    # legacy v2.x runs carry `seek_info` — historical reads must still total
    g3 = within_target_glance(
        {"d": {"counts": {"scroll_past": 8, "seek_info": 4}}}, ["d"])
    assert g3.n == 12 and g3.count("seek_info") == 4

    # segments come back in escalating-engagement order, zero-counts omitted
    keys = [k for k, _, _, _ in g.segments()]
    assert keys == ["scroll_past", "linger", "save", "share", "tap_cta"], keys
    print("  glance counts every action; no respondent leaves the denominator ✓")


# ---- report source resolution -----------------------------------------


def _pain(pid: str, stage: str, sev: str, within: bool, cited: int = 0) -> Pain:
    return Pain(id=pid, pain=f"{pid} pain.", funnel_stage=stage, severity=sev,
                within_target=within, cited_by=[f"d{i}" for i in range(cited)])


def _dists() -> dict:
    """Two chaos bands per type, so the roll-up is actually exercised."""
    return {
        "enthusiast_macros_lifter::moderate": {
            "counts": {"scroll_past": 5, "linger": 3},
            "next_step_counts": {"nothing": 6, "buy_at_restock": 2}},
        "enthusiast_macros_lifter::deliberate": {
            "counts": {"scroll_past": 10},
            "next_step_counts": {"nothing": 10}},
        "skeptic_lapsed_protein::impulsive": {
            "counts": {"scroll_past": 2, "linger": 2},
            "next_step_counts": {"nothing": 3, "research_first": 1}},
        "skeptic_lapsed_protein::moderate": {
            "counts": {"scroll_past": 4, "save": 1},
            "next_step_counts": {"nothing": 4, "mention_to_someone": 1}},
        "switcher_results_chaser::moderate": {
            "counts": {"scroll_past": 9},
            "next_step_counts": {"nothing": 9}},
    }


def test_panel_response_rolls_chaos_bands_up_per_consumer_type() -> None:
    from agent.read_model import build_panel_response
    p = build_panel_response(_dists(), ["enthusiast_macros_lifter"])
    assert [t.disposition for t in p.types][0] == "enthusiast_macros_lifter", \
        "the target type leads its group"
    by = {t.disposition: t for t in p.types}
    assert len(p.types) == 3, "one row per consumer type, bands collapsed"
    ent = by["enthusiast_macros_lifter"]
    assert ent.within_target and ent.n == 18 and ent.engaged == 3
    assert ent.buyers == 2 and ent.step("nothing") == 16
    skep = by["skeptic_lapsed_protein"]
    assert not skep.within_target, "out-of-target types must still be present"
    assert skep.n == 9 and skep.engaged == 3, "linger AND save both count"
    assert skep.acted == 2, "research + mention count as acting; nothing does not"
    assert p.panel_n == 36, "the panel total is everyone, not the target slice"
    assert p.in_tally == (18, 3) and p.out_tally == (18, 3)
    print("  panel response rolls bands up, keeps out-of-target types ✓")


def test_panel_response_sorts_responders_first_within_each_group() -> None:
    """Out-of-target types are ordered by response rate so the ones that
    actually did something lead — the whole point of showing them."""
    from agent.read_model import build_panel_response
    p = build_panel_response(_dists(), ["enthusiast_macros_lifter"])
    out = [t.disposition for t in p.out_types]
    assert out == ["skeptic_lapsed_protein", "switcher_results_chaser"], \
        "the out-of-target type that responded must lead the ones that didn't"
    assert all(t.within_target for t in p.types[:1]), "target group comes first"
    print("  responders lead their group; target group first ✓")


def test_decoupling_note_fires_only_when_outsiders_beat_the_target() -> None:
    """The finding this table exists for: in-target and actually-responding
    come apart. The note must fire on that shape and stay silent otherwise —
    a warning that always fires is not a warning."""
    from agent.read_model import build_panel_response
    d = _dists()
    # Equal rates (3/18 vs 3/18) -> silent.
    assert build_panel_response(d, ["enthusiast_macros_lifter"]).decoupling_note is None

    # Target does nothing, outsiders respond -> fires.
    d2 = dict(d)
    d2["enthusiast_macros_lifter::moderate"] = {
        "counts": {"scroll_past": 8}, "next_step_counts": {"nothing": 8}}
    note = build_panel_response(d2, ["enthusiast_macros_lifter"]).decoupling_note
    assert note and "NOT buying responded more" in note
    assert "17%" in note and "0%" in note, "the note must carry both real rates"

    # No target set at all -> silent (nothing to compare against).
    assert build_panel_response(d, []).decoupling_note is None
    # Outsiders present but inert -> silent.
    d3 = {k: v for k, v in d.items() if not k.startswith("skeptic")}
    assert build_panel_response(d3, ["enthusiast_macros_lifter"]).decoupling_note is None
    print("  decoupling note fires only on the real shape ✓")


def test_panel_response_summary_states_the_denominator() -> None:
    from agent.read_model import build_panel_response
    p = build_panel_response(_dists(), ["enthusiast_macros_lifter"])
    assert "All 36 people in the panel" in p.summary
    assert "not just the 18 you're buying" in p.summary
    empty = build_panel_response({}, [])
    assert empty.is_empty and empty.summary == "" and empty.panel_n == 0
    no_target = build_panel_response(_dists(), [])
    assert "No audience type was read as the target" in no_target.summary
    print("  panel summary states the denominator; empty stays silent ✓")


def test_l3_is_read_even_with_no_within_target_set() -> None:
    """Regression: the loader used to read l3_summary.json only when a
    within-target set existed, which made every out-of-target respondent
    unreachable — exactly the data the panel table exists to show."""
    d = _decision(within_dispositions=[], decision="ITERATE",
                  target_action_rate=0.1)
    with tempfile.TemporaryDirectory() as td:
        rd = _run_dir(_report(d), tmp=Path(td),
                      l3={"segment_behavioral_distributions": _dists()})
        m = build_read_model(rd)
    assert not m.within_dispositions
    assert m.panel.panel_n == 36, "panel data must load without a target set"
    assert m.glance.n == 0, "the in-target glance is still empty, correctly"
    print("  L3 loads without a within-target set ✓")


def test_funnel_stage_order_covers_every_stage_the_schema_allows() -> None:
    """Anti-drift pin. A stage the schema accepts but this tuple omits does
    NOT raise — it silently sorts into the unknown bucket and drops out of the
    diagnosis overview's stage row, so the page implies the funnel has fewer
    stages than it does. That is what happened to `recall`. Adding a stage to
    the schema must fail here until it is placed in buyer order.
    """
    from agent.read_model import FUNNEL_STAGE_ORDER
    from agent.schema import _VALID_FUNNEL_STAGES
    assert set(FUNNEL_STAGE_ORDER) == set(_VALID_FUNNEL_STAGES), (
        "FUNNEL_STAGE_ORDER is out of sync with the schema: "
        f"missing {sorted(set(_VALID_FUNNEL_STAGES) - set(FUNNEL_STAGE_ORDER))}, "
        f"extra {sorted(set(FUNNEL_STAGE_ORDER) - set(_VALID_FUNNEL_STAGES))}"
    )
    assert len(FUNNEL_STAGE_ORDER) == len(set(FUNNEL_STAGE_ORDER)), "duplicate stage"
    print("  funnel stage order covers the schema exactly ✓")


def test_diagnosis_overview_counts_without_asserting_anything_new() -> None:
    """Every field is a count off pain_map — the overview may summarise the
    problem cards, never add to them."""
    rep = _report()
    rep.pain_map = [
        _pain("P1", "attention", "execution", True, cited=3),
        _pain("P2", "attention", "execution", True, cited=1),
        _pain("P3", "conversion", "structural", False),
    ]
    ov = build_diagnosis_overview(rep)
    assert (ov.total, ov.within, ov.outside) == (3, 2, 1)
    assert (ov.execution, ov.structural) == (2, 1)
    assert ov.widest_breadth == 3
    # Stages are de-duplicated and returned in funnel order, not input order.
    assert ov.stages == ["attention", "conversion"]
    assert (ov.load_bearing_id, ov.load_bearing_stage) == ("P1", "attention")
    print("  diagnosis overview counts pains, stages, breadth, load-bearing ✓")


def test_diagnosis_overview_keeps_an_unknown_funnel_stage() -> None:
    """An unrecognised stage is a reporting gap, not a licence to under-report
    how many stages leak — the same failure shape as the glance dropping
    savers from its denominator. It sorts last rather than vanishing."""
    rep = _report()
    rep.pain_map = [
        _pain("P1", "conversion", "execution", True),
        _pain("P2", "post_purchase", "execution", True),
    ]
    ov = build_diagnosis_overview(rep)
    assert ov.stages == ["conversion", "post_purchase"], \
        "an unknown stage must be kept and sorted last, never dropped"
    assert "2 stages" in ov.summary
    print("  unknown funnel stage kept and counted, sorted last ✓")


def test_diagnosis_overview_summary_reads_correctly_at_the_edges() -> None:
    """Copy is client-facing: singulars, and the all-outside case, which is
    the one that changes what the brand manager should do."""
    rep = _report()
    rep.pain_map = [_pain("P1", "attention", "structural", False)]
    ov = build_diagnosis_overview(rep)
    s = ov.summary
    assert "1 problem, leaking at 1 stage of the funnel." in s
    assert "None of them land on the audience you're buying" in s
    assert "1 is structural" in s and "fixes that one" in s

    rep.pain_map = [_pain("P1", "attention", "execution", True),
                    _pain("P2", "conversion", "execution", True)]
    ov = build_diagnosis_overview(rep)
    assert "2 problems, leaking at 2 stages" in ov.summary
    assert "All 2 hit the audience you're buying." in ov.summary
    assert "structural" not in ov.summary, "no structural pains, no structural clause"

    rep.pain_map = []
    ov = build_diagnosis_overview(rep)
    assert ov.is_empty and ov.summary == "", "an empty diagnosis says nothing"
    print("  overview copy handles singular, all-outside, all-within, empty ✓")


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


# ---- the dashboard's additions -----------------------------------------


def _l3(counts: dict[str, dict]) -> dict:
    return {"segment_behavioral_distributions": counts}


def test_next_steps_in_target_never_pools_the_outside_majority() -> None:
    """The rule that has cost this project a rebuild twice: any aggregate
    across the panel must split in/out of target. On a narrow ad the outside
    majority swamps the signal — pooled, this run reads 'did nothing: 95 of
    100' for a creative that landed exactly as aimed on its 19."""
    l3 = _l3({
        "enthusiast_macros_lifter::moderate": {
            "counts": {"scroll_past": 14, "linger": 4, "save": 1},
            "next_step_counts": {"nothing": 14, "research_first": 5},
        },
        "aspirant_clean_label::moderate": {
            "counts": {"scroll_past": 81},
            "next_step_counts": {"nothing": 81},
        },
    })
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(), tmp=Path(td), l3=l3))

    rows = m.panel.next_steps_in_target()
    by_key = {k: (n, denom) for k, _, n, denom in rows}
    assert by_key["research_first"] == (5, 19), by_key
    assert by_key["nothing"] == (14, 19), by_key
    assert sum(n for _, _, n, _ in rows) == 19, "in-target rows must total the target"
    assert all(denom == 19 for *_, denom in rows), "denominator must be the target"
    # the outside 81 are reachable, but only by asking for them
    assert m.outside_n == 81 and m.target_n == 19
    print("  in-target next steps never pool the outside majority ✓")


def test_target_and_outside_counts_come_from_the_panel_not_thin_air() -> None:
    """With no l3_summary.json there is no panel, and the zone counts must be
    zero rather than falling back to the declared panel size — a label reading
    'WITHIN TARGET — 0 OF 100' is honest; one reading 100 is invented."""
    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(), tmp=Path(td)))
    assert m.target_n == 0 and m.outside_n == 0
    assert m.panel_size == 100, "the declared size is still known, just not claimed"
    assert m.panel.next_steps_in_target() == []
    print("  no L3 -> zone counts are 0, never the declared panel size ✓")


def test_audience_alignment_is_stated_not_left_as_silence() -> None:
    """`audience_mismatch` fires only on a gross gap. The check PASSING is a
    claim too, and a blank space where a warning would have been is not one."""
    from agent.schema import AudienceMatch

    aligned = _report(audience_match=AudienceMatch(
        verdict="aligned", declared_summary="all genders aged 25-44",
        inferred_summary="people aged 25-34",
        message="The creative's apparent target is consistent with the buy."))
    mismatched = _report(audience_match=AudienceMatch(
        verdict="mismatched", declared_summary="men 18-24",
        inferred_summary="women 35-54", axes=["gender", "age"],
        message="Reads as aimed at women 35-54, declared men 18-24."))

    with tempfile.TemporaryDirectory() as td:
        a = build_read_model(_run_dir(aligned, tmp=Path(td)))
    with tempfile.TemporaryDirectory() as td:
        b = build_read_model(_run_dir(mismatched, tmp=Path(td)))

    assert a.audience_aligned and "consistent" in a.audience_aligned
    assert a.audience_mismatch is None
    assert b.audience_mismatch and "women 35-54" in b.audience_mismatch
    assert b.audience_aligned is None, "a mismatch must never also read aligned"

    # an aligned verdict the model left unworded still gets a sentence, built
    # from the two summaries rather than rendering an empty chip
    silent = _report(audience_match=AudienceMatch(
        verdict="aligned", declared_summary="adults 25-44",
        inferred_summary="people aged 25-34", message=""))
    with tempfile.TemporaryDirectory() as td:
        c = build_read_model(_run_dir(silent, tmp=Path(td)))
    assert c.audience_aligned and "adults 25-44" in c.audience_aligned
    print("  audience alignment is stated in both directions ✓")


def test_every_methodology_flag_has_plain_words_and_none_can_vanish() -> None:
    """The flag tokens are engine vocabulary; a client reads sentences. This
    map is hand-maintained against the schema — exactly the shape that goes
    stale silently — so pin it, and make an unmapped flag fall back to its
    token rather than disappearing."""
    from agent.read_model import METHODOLOGY_FLAG_TEXT, flag_text
    from agent.schema import _VALID_METHODOLOGY_FLAGS

    missing = _VALID_METHODOLOGY_FLAGS - set(METHODOLOGY_FLAG_TEXT)
    assert not missing, f"methodology flags with no plain-words entry: {missing}"
    for flag, text in METHODOLOGY_FLAG_TEXT.items():
        assert text != flag and " " in text, f"{flag} is not plain words"
    assert flag_text("a_flag_from_the_future") == "a_flag_from_the_future"

    with tempfile.TemporaryDirectory() as td:
        m = build_read_model(_run_dir(_report(), tmp=Path(td)))
    assert m.flag_lines == [METHODOLOGY_FLAG_TEXT["single_within_target"]]
    print("  every methodology flag has plain words; unknown ones survive ✓")


def test_client_pain_text_strips_engine_scoping_vocabulary() -> None:
    """Out-of-target pains open with the assess pass's own scoping note, which
    is engine jargon duplicating the within/outside flag the page already
    carries as data."""
    from agent.read_model import client_pain_text

    raw = ("OUTSIDE-TARGET CONTEXT (not verdict-load-bearing): among lapsed "
           "protein buyers the ad reactivates a filed negative memory.")
    out = client_pain_text(raw)
    assert "OUTSIDE-TARGET" not in out and "verdict-load-bearing" not in out
    assert out.startswith("Among lapsed protein buyers"), out
    assert out.endswith("negative memory.")
    # a within-target pain is untouched, including its leading capital
    plain = "The creative presents the isolate as a line-extension."
    assert client_pain_text(plain) == plain
    assert client_pain_text("") == ""
    print("  engine scoping vocabulary never reaches client copy ✓")
