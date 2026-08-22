"""F3 — the funnel projection must SPLIT in- and out-of-target, never pool.

The rule this file pins is stated twice in this repo's own source
(`read_model.next_steps_in_target`, `docs/v3_out_of_target_response.md`) and
recorded in memory as having cost the project a rebuild TWICE: any panel-wide
aggregate must split on target membership. The L3.5 projection was the last
one that did not.

The fixture is the review's own worked example — 19 in target converting, 81
outside converting at zero — because that is where the defect is visible and
harmless-looking at the same time: the pooled number is arithmetically correct
and tells the customer their working ad DROPPED conversion.

⚠ Every test here asserts against ASSEMBLED output (a projected FunnelProjection,
or the printed CLI report), not against an intermediate. Session 48's whole
finding was that piece-level tests were green while the assembled artifact was
wrong.

Run: .venv/bin/python -m pytest tests/test_funnel_target_split.py -q
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agent.decision import within_target_action_rate
from agent.projection_l35 import project_funnel
from agent.schema import (
    AgentTranscript,
    BehavioralSignal,
    BehavioralSignalDistribution,
    Report,
    SchemaError,
    TargetMatch,
    _validate_funnel_projection,
)
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_types import (
    DispositionTarget,
    L2Summary,
    L3Summary,
    TargetClassification,
)

_BASELINE = {"stop_rate": 0.10, "click_rate": 0.02,
             "visit_rate": 0.015, "convert_rate": 0.006}


def _dist(n: int, buy_intent: int, action: str = "linger"
          ) -> BehavioralSignalDistribution:
    """One segment's R7 aggregate: n parsed signals, `buy_intent` of them a
    purchase next_step, the rest inert."""
    ns: dict[str, int] = {}
    if buy_intent:
        ns["buy_now"] = buy_intent
    if n - buy_intent > 0:
        ns["nothing"] = n - buy_intent
    return BehavioralSignalDistribution(
        counts={action: n}, next_step_counts=ns, n=n
    )


def _l2(label: str, dist: BehavioralSignalDistribution) -> L2Summary:
    return L2Summary(
        disposition_label=label,
        summary_paragraph=f"{label} summary.",
        within_cell_variance="spread",
        outlier_note=None,
        segment_label=label,
        behavioral_distribution=dist,
    )


def _transcript(label: str, next_step: str) -> AgentTranscript:
    return AgentTranscript(
        agent_id=0, disposition_label=label, context_label="c", seed_idx=0,
        encoding_text="", reflection_text="",
        behavioral_signal=BehavioralSignal(
            action="linger", action_reasoning="r",
            next_step=next_step, next_step_reasoning="r",
        ),
    )


def _report(projection) -> Report:
    """A minimal Report carrying nothing but the projection under test."""
    return Report(
        verdict="MIXED", confidence=60, target_match=TargetMatch(),
        top_3_changes=[], strengths_to_preserve=[], context_fit_map={},
        verbatim_consumer_voice=[], funnel_projection=projection,
    )


def _tc(**classifications: str) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="a narrow buyer",
        target_reasoning="the creative names one buyer.",
        disposition_classifications=[
            DispositionTarget(disposition_label=label, classification=cls,
                              reasoning="fixture")
            for label, cls in classifications.items()
        ],
    )


def _narrow_ad() -> tuple[L3Summary, TargetClassification]:
    """THE REVIEW'S FIXTURE. A narrow ad: 19 people in target, 6 of whom would
    buy (~32%), against 81 outside it who would not. Pooled, that is 6 of 100."""
    tc = _tc(target_buyer="within", bystander_a="outside", bystander_b="outside")
    l2s = [
        _l2("target_buyer", _dist(19, buy_intent=6)),
        _l2("bystander_a", _dist(41, buy_intent=0, action="scroll_past")),
        _l2("bystander_b", _dist(40, buy_intent=0, action="scroll_past")),
    ]
    return synthesize_population(l2s, tc), tc


# ---- The defect itself ----


def test_the_pooled_funnel_reads_a_working_ad_as_a_collapse() -> None:
    """The reason this split exists. On the review's own fixture the pooled
    convert rate lands BELOW the customer's baseline — "your ad lowers
    conversion" — while the people the ad was actually aimed at convert well
    above it. Both numbers are arithmetically correct; only one is the read."""
    l3, _ = _narrow_ad()
    proj = project_funnel(l3, _BASELINE)

    assert proj.within_target is not None, "in-target projection missing"
    in_target = proj.within_target.funnel_rates.convert_rate
    pooled = proj.overall.convert_rate

    assert in_target > _BASELINE["convert_rate"], (
        f"in-target convert {in_target} should beat the baseline "
        f"{_BASELINE['convert_rate']} — 6 of 19 said they would buy"
    )
    assert pooled < _BASELINE["convert_rate"], (
        f"pooled convert {pooled} should sit BELOW baseline — that is the "
        "defect this test exists to make visible"
    )
    assert in_target > pooled * 1.5, (
        f"in-target {in_target} vs pooled {pooled}: the split must move the "
        "number materially or it is decoration"
    )
    print(f"  OK  in-target {in_target*100:.3f}% vs pooled {pooled*100:.3f}% "
          f"(baseline {_BASELINE['convert_rate']*100:.3f}%) ✓")


def test_outside_target_is_reported_separately_and_is_not_the_read() -> None:
    """The out-of-target slice is not deleted — it is reported, named, and kept
    out of the headline. Memory `out_of_target_response_bimodal`: in-target and
    actually-responding are decoupled, so BOTH have to be visible."""
    l3, _ = _narrow_ad()
    proj = project_funnel(l3, _BASELINE)

    assert proj.outside_target is not None
    assert proj.outside_target.behavioral_distribution.n == 81
    assert proj.within_target.behavioral_distribution.n == 19
    assert (proj.outside_target.funnel_rates.convert_rate
            < proj.within_target.funnel_rates.convert_rate)
    print("  OK  outside target present, separate, and lower ✓")


# ---- The identity ----


def test_the_split_sums_to_the_population_exactly() -> None:
    """An INTEGER identity: every parsed signal is on exactly one side of the
    target line. A discrepancy means a persona was double-counted or dropped,
    so it is a defect and never a rounding artifact."""
    l3, _ = _narrow_ad()
    within = l3.within_target_behavioral_distribution
    outside = l3.outside_target_behavioral_distribution
    pop = l3.population_behavioral_distribution

    assert within.n + outside.n == pop.n == 100
    for field in ("counts", "next_step_counts"):
        summed: dict[str, int] = {}
        for d in (within, outside):
            for k, v in getattr(d, field).items():
                summed[k] = summed.get(k, 0) + v
        assert summed == getattr(pop, field), (
            f"{field}: split {summed} != population {getattr(pop, field)}"
        )
    print("  OK  within + outside == population, exactly ✓")


def test_the_validator_rejects_a_split_that_does_not_sum() -> None:
    """The identity is ENFORCED at the schema boundary, not merely asserted
    here — otherwise a future change to the split rule ships silently."""
    l3, _ = _narrow_ad()
    proj = project_funnel(l3, _BASELINE)
    _validate_funnel_projection(proj)          # clean projection must pass

    proj.within_target.behavioral_distribution = _dist(18, buy_intent=6)  # 18+81 != 100
    with pytest.raises(SchemaError, match="target split"):
        _validate_funnel_projection(proj)
    print("  OK  schema validator catches a split that loses a person ✓")


# ---- The n=0 trap ----


def test_a_side_with_no_signal_is_not_projected_at_all() -> None:
    """⚠ n=0 must yield None, never a projection. `_funnel_rates` on an empty
    distribution returns the baseline times a floor multiplier with a
    100%-wide band — a confident-looking number about nobody. Both directions
    are reachable: decision.py has a `no_within_target_evidence` flag, and an
    all-in-target panel is ordinary on a broad ad."""
    tc = _tc(target_buyer="within", bystander="outside")

    all_in = synthesize_population([_l2("target_buyer", _dist(10, 4))], tc)
    proj_in = project_funnel(all_in, _BASELINE)
    assert proj_in.within_target is not None
    assert proj_in.outside_target is None, "empty outside side must not project"

    none_in = synthesize_population([_l2("bystander", _dist(10, 0))], tc)
    proj_out = project_funnel(none_in, _BASELINE)
    assert proj_out.within_target is None, "empty in-target side must not project"
    assert proj_out.outside_target is not None
    _validate_funnel_projection(proj_in)
    _validate_funnel_projection(proj_out)
    print("  OK  an empty side projects to None, both directions ✓")


# ---- The rule is the SAME rule as the headline metric ----


def test_ambiguous_falls_outside_exactly_as_the_headline_metric_does() -> None:
    """The split uses tc.within_target_labels() — byte-for-byte the rule
    decision.within_target_action_rate uses. ⚠ If these two ever disagree, the
    funnel and the headline are describing different people on the same page.
    An `ambiguous` disposition falls OUTSIDE in both."""
    tc = _tc(sure_thing="within", maybe="ambiguous", not_them="outside")
    l3 = synthesize_population(
        [_l2("sure_thing", _dist(10, 5)),
         _l2("maybe", _dist(10, 5)),
         _l2("not_them", _dist(10, 0))],
        tc,
    )
    assert l3.within_target_behavioral_distribution.n == 10, (
        "ambiguous must NOT be counted as within — the headline metric's "
        "denominator does not count it either"
    )
    assert l3.outside_target_behavioral_distribution.n == 20

    # And the denominators genuinely agree, computed independently through the
    # decision layer's own function on real transcripts.
    transcripts = ([_transcript("sure_thing", "buy_now")] * 5
                   + [_transcript("sure_thing", "nothing")] * 5
                   + [_transcript("maybe", "buy_now")] * 5
                   + [_transcript("maybe", "nothing")] * 5
                   + [_transcript("not_them", "nothing")] * 10)
    _, _, denom = within_target_action_rate(transcripts, tc)
    assert denom == l3.within_target_behavioral_distribution.n, (
        f"headline denominator {denom} != funnel in-target n "
        f"{l3.within_target_behavioral_distribution.n} — the two aggregates "
        "must describe the same people"
    )
    print("  OK  ambiguous falls outside in the funnel and the headline alike ✓")


# ---- The assembled customer surface ----


def _printed_report() -> str:
    """The CLI report as a customer sees it, on the narrow-ad fixture. This is
    the only production surface that renders funnel numbers (the HTML read
    deliberately withholds them — read_model.FUNNEL_WITHHELD_NOTE)."""
    import batch_run

    l3, _ = _narrow_ad()
    buf = io.StringIO()
    with redirect_stdout(buf):
        batch_run._print_report(_report(project_funnel(l3, _BASELINE)))
    return buf.getvalue()


def test_the_printed_report_leads_with_in_target_and_names_it() -> None:
    """⚠ ASSEMBLED OUTPUT, not a field read. The in-target block must come
    FIRST and be labelled, and the pooled block must be labelled as panel
    arithmetic — an unlabelled pooled number is the defect wearing a hat."""
    out = _printed_report()

    assert "IN TARGET" in out, "the funnel header must name the in-target split"
    i_in = out.index("IN TARGET")
    i_pooled = out.index("Whole panel pooled")
    assert i_in < i_pooled, "in-target must be printed ABOVE the pooled block"
    assert "Outside target" in out, "the outside slice must be shown, not dropped"
    assert "n=19" in out and "n=81" in out, "each side must carry its own N"
    print("  OK  printed report leads with in-target, names both sides ✓")


def test_a_legacy_projection_still_prints_its_pooled_funnel() -> None:
    """A run.json written before the split has no in-target projection. It must
    still render — and must NOT claim an in-target read it does not have."""
    import batch_run
    from agent.schema import FunnelProjection

    l3, _ = _narrow_ad()
    legacy = FunnelProjection.from_dict({
        k: v for k, v in project_funnel(l3, _BASELINE).to_dict().items()
        if k not in ("within_target", "outside_target")
    })
    assert legacy.within_target is None and legacy.outside_target is None
    _validate_funnel_projection(legacy)   # the identity check must SKIP, not fail

    buf = io.StringIO()
    with redirect_stdout(buf):
        batch_run._print_report(_report(legacy))
    out = buf.getvalue()
    assert "PROJECTED FUNNEL  (overall" in out
    assert "IN TARGET" not in out, "a legacy projection must not claim a split"
    print("  OK  legacy projection round-trips and prints without a split ✓")


def test_a_panel_with_no_in_target_signal_says_so_on_the_page() -> None:
    """⚠ The branch that fires when the in-target side is empty. A pooled
    funnel printed with no warning reads as "your audience" when every person
    in it is outside the target."""
    import batch_run

    tc = _tc(target_buyer="within", bystander="outside")
    l3 = synthesize_population([_l2("bystander", _dist(10, 3))], tc)
    buf = io.StringIO()
    with redirect_stdout(buf):
        batch_run._print_report(_report(project_funnel(l3, _BASELINE)))
    out = buf.getvalue()
    assert "NO IN-TARGET SIGNAL" in out, (
        "an all-outside panel must say so above its rates"
    )
    print("  OK  an all-outside panel is labelled as one ✓")


def main() -> None:
    print("=== F3: the funnel projection splits in/out of target ===")
    test_the_pooled_funnel_reads_a_working_ad_as_a_collapse()
    test_outside_target_is_reported_separately_and_is_not_the_read()
    test_the_split_sums_to_the_population_exactly()
    test_the_validator_rejects_a_split_that_does_not_sum()
    test_a_side_with_no_signal_is_not_projected_at_all()
    test_ambiguous_falls_outside_exactly_as_the_headline_metric_does()
    test_the_printed_report_leads_with_in_target_and_names_it()
    test_a_legacy_projection_still_prints_its_pooled_funnel()
    test_a_panel_with_no_in_target_signal_says_so_on_the_page()
    print("PASS — the last unsplit panel-wide aggregate is split.")


if __name__ == "__main__":
    main()
