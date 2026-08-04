"""The terminal report's guardrails — the operator-facing half of the vocabulary.

`batch_run._print_report` and the HTML read are two surfaces over one Report.
Section ORDER is legitimately per-surface; the guardrail VOCABULARY is not, and
a guardrail that reaches only one of them is how the two quietly start telling
different stories about the same run.

This file covers the two the CLI can lose independently: the prevalence floor
(its change list is NUMBERED, which is what makes it a ranking) and the caveats
attached to numbers it prints.

Offline. No API calls.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import batch_run  # noqa: E402
from agent.read_model import (  # noqa: E402
    HEADLINE_CAVEAT,
    OUT_OF_TARGET_ONLY_NOTE,
    SEGMENT_CAVEAT,
)
from agent.schema import (  # noqa: E402
    Decision,
    Pain,
    Report,
    TargetMatch,
    TopChange,
)


def _report(**kw) -> Report:
    base = dict(
        verdict="MIXED", confidence=76, target_match=TargetMatch(),
        top_3_changes=[
            TopChange(change="fix for the target", why="w", derives_from_pains=["P1"]),
            TopChange(change="fix for outsiders only", why="w", derives_from_pains=["P2"]),
        ],
        strengths_to_preserve=[], context_fit_map={}, verbatim_consumer_voice=[],
        methodology_flags=[],
        pain_map=[
            Pain(id="P1", pain="in-target problem", funnel_stage="conversion",
                 severity="execution", within_target=True),
            Pain(id="P2", pain="outsider problem", funnel_stage="attention",
                 severity="execution", within_target=False),
        ],
        decision=Decision(
            decision="ITERATE", target_action_rate=0.1111, trust="DIRECTIONAL",
            target_action_num=2, target_action_denom=18,
            within_dispositions=["enthusiast_macros_lifter"],
            load_bearing_pain_id="P1", rationale="P1 is fixable"),
    )
    base.update(kw)
    return Report(**base)


def _printed(fn, *args) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def test_cli_applies_the_same_ranking_floor_as_the_read() -> None:
    """The CLI numbers its change list 1., 2., 3. — that IS a ranking. Leaving
    it to rank a fix the read demotes would put two different recommendations
    in front of the same operator on the same run."""
    out = _printed(batch_run._print_report, _report())

    assert "fix for the target" in out and "fix for outsiders only" in out, \
        "the CLI dropped a change instead of demoting it"
    assert "NOT RANKED" in out, "the outsider-only fix was not demoted"
    assert OUT_OF_TARGET_ONLY_NOTE in out, "demoted without saying why"
    assert out.index("fix for the target") < out.index("NOT RANKED") \
        < out.index("fix for outsiders only"), \
        "the demoted fix is still inside the numbered list"
    # It must not carry a rank number of its own once demoted.
    demoted = out[out.index("NOT RANKED"):]
    assert "1." not in demoted.split("fix for outsiders only")[0], \
        "the demoted fix was renumbered rather than unranked"
    print("  CLI applies the same ranking floor as the read ✓")


def test_cli_carries_the_caveats_for_the_numbers_it_prints() -> None:
    """Same constants, not restated copies — a second wording would drift."""
    out = _printed(batch_run._print_decision_headline, _report())
    assert "11% of your target" in out, "headline missing — the test would be vacuous"
    assert HEADLINE_CAVEAT in out, "the CLI prints the buy figure with no caveat"

    champ = _report(decision=Decision(
        decision="RETARGET", target_action_rate=0.05, trust="DIRECTIONAL",
        target_action_num=1, target_action_denom=18,
        within_dispositions=["enthusiast_macros_lifter"],
        champion_disposition="aspirant_clean_label", champion_action_rate=0.42,
        load_bearing_pain_id="P1", rationale="wrong audience"))
    out = _printed(batch_run._print_decision_headline, champ)
    assert "Right ad, wrong person." in out, "champion line missing — test vacuous"
    assert SEGMENT_CAVEAT in out, "a between-segment claim printed with no caveat"
    print("  CLI carries the headline and segment caveats ✓")


def main() -> None:
    print("=== the terminal report's guardrails ===")
    test_cli_applies_the_same_ranking_floor_as_the_read()
    test_cli_carries_the_caveats_for_the_numbers_it_prints()
    print("PASS — the CLI and the read share one guardrail vocabulary.")


if __name__ == "__main__":
    main()
