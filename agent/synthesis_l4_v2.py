"""L4 v2 — strategic memo synthesis (rocket-2.0.0).

Adapted from agent/synthesis_l4.py. The verdict cascade, structural-vs-
execution distinction, counterweight rule, confidence anchors, and the
3-attempt parse-retry-with-feedback loop are carried over verbatim — that
is the methodology, not the format.

Three changes:
  1. The headline is now `bet_ranking` — an ordered list of strategic bets,
     highest expected marketing-ROI payoff first. Verdict / confidence /
     flags become supporting metadata.
  2. L4 receives the L3.5 FunnelProjection as an INPUT. It may reference it
     in `why` fields and to inform the bet ranking, but the prompt forbids
     it from emitting or altering any funnel rate. The FunnelProjection is
     attached to the Report deterministically by synthesize_memo_v2, not by
     the model.
  3. `provisional_dispositions` and the `provisional_disposition_present`
     methodology flag are attached deterministically in Python from the
     run inputs — also not the model's job.
"""

from __future__ import annotations

import json
import logging

import anthropic

from agent.config import RunConfig
from agent.schema import (
    FunnelProjection,
    Report,
    SchemaError,
    validate_report,
)
from agent.synthesis_l4 import (
    _PARSE_RETRY_SUFFIX_TEMPLATE,  # noqa: F401  (kept for parity / future use)
    _REPORT_SCHEMA_TEMPLATE,
    _L4_SYSTEM,
    _extract_text,
    _retry_suffix,
    _strip_to_json,
    _validate_l4_coverage,
)
from agent.synthesis_types import L3Summary, TargetClassification
from agent.telemetry import call_with_telemetry

_log = logging.getLogger(__name__)


# The v2 schema template = v1 template + bet_ranking. funnel_projection and
# provisional_dispositions are NOT in the template — they are attached in
# Python, not emitted by the model.
_REPORT_SCHEMA_TEMPLATE_V2 = _REPORT_SCHEMA_TEMPLATE.rstrip().rstrip("}").rstrip() + """,
  "bet_ranking": [
    "<one-sentence strategic bet a performance marketer can act on>",
    ... (ordered list, highest expected marketing-ROI payoff first;
         non-empty for every verdict except METHODOLOGY_GAP)
  ]
}
"""

_V2_ADDITIONS = """\
# rocket-2.0.0: the bet ranking is the headline

You also receive a FUNNEL PROJECTION — projected stop / click / visit / \
convert rates, overall and per segment, derived from the agents' R7 \
behavioral signals applied as multipliers to the customer's own baseline \
funnel. It is an INPUT. You must NOT emit it, alter it, or invent any \
funnel rate, percentage, or absolute number. Reference it ONLY as \
evidence inside `why` fields and to inform the bet ranking. The funnel \
numbers are heuristic and directional — never present them as precise.

`bet_ranking` is the NEW HEADLINE of the report — an ordered list of \
strategic bets, highest expected marketing-ROI payoff first. Each entry \
is one concrete sentence a D2C performance marketer can act on, grounded \
in the within-target evidence AND the funnel projection — e.g. "Put cold-\
traffic spend behind the impulsive segment: its projected click lift is \
the strongest in the run; hold the deliberate-retarget budget until the \
comprehension fix lands." Non-empty for every verdict except \
METHODOLOGY_GAP. The verdict, confidence and methodology_flags are \
supporting metadata now — the bet ranking is what the brand manager reads \
first, so it must carry the real decision.

# Report schema"""

# Inject the v2 sections right before the schema, and swap in the v2 schema
# template — no need to retype the verdict framework.
_L4_V2_SYSTEM = _L4_SYSTEM.replace(
    _REPORT_SCHEMA_TEMPLATE, _REPORT_SCHEMA_TEMPLATE_V2
).replace("# Report schema", _V2_ADDITIONS, 1)


# ---- Public entry point ----


def synthesize_memo_v2(
    l3_summary: L3Summary,
    target_classification: TargetClassification,
    funnel_projection: FunnelProjection,
    config: RunConfig,
    *,
    provisional_dispositions: list[str] | None = None,
    max_attempts: int = 3,
) -> Report:
    """Run L4 v2: produce a validated Report with a bet_ranking headline and
    the L3.5 funnel projection attached.

    The model emits the strategic content (verdict, changes, bet_ranking,
    etc.). The funnel_projection and provisional_dispositions are attached
    deterministically in Python — the model never touches a funnel rate.
    """
    provisional = list(provisional_dispositions or [])
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["l4"]
    user_payload = _build_user_payload(
        l3_summary, target_classification, funnel_projection, config
    )
    pool_size = len(l3_summary.representative_quotes)

    last_feedback, last_raw = "", ""
    for attempt in range(max_attempts):
        if attempt > 0:
            user_text = user_payload + _retry_suffix(last_feedback, last_raw)
        else:
            user_text = user_payload

        response = call_with_telemetry(
            client,
            layer="strategist",
            model=model,
            retries=attempt,
            max_tokens=8000,
            system=_L4_V2_SYSTEM,
            messages=[{"role": "user", "content": user_text}],
        )
        raw = _extract_text(response)
        last_raw = raw

        try:
            parsed = json.loads(_strip_to_json(raw))
            report = Report.from_dict(parsed)
            # Attach the deterministic, non-model pieces BEFORE validation so
            # validate_report sees the complete v2 Report.
            report.funnel_projection = funnel_projection
            report.provisional_dispositions = provisional
            if provisional and "provisional_disposition_present" not in report.methodology_flags:
                report.methodology_flags.append("provisional_disposition_present")
            validate_report(report)
            _validate_l4_coverage(report, pool_size)
            _validate_l4_coverage_v2(report)
            return report
        except (json.JSONDecodeError, KeyError, TypeError, SchemaError) as exc:
            last_feedback = f"{type(exc).__name__}: {exc}"
            _log.warning(
                "L4 v2 parse/validate failed (attempt %d/%d): %s. Raw head: %r",
                attempt + 1, max_attempts, last_feedback, raw[:500],
            )

    raise RuntimeError(
        f"L4 v2 synthesis failed after {max_attempts} attempts. "
        f"Last feedback: {last_feedback}. Raw output head: {last_raw[:500]!r}"
    )


def _validate_l4_coverage_v2(report: Report) -> None:
    """v2-only coverage gate: bet_ranking must be non-empty for any verdict
    that is not METHODOLOGY_GAP — the bet ranking IS the deliverable."""
    if report.verdict != "METHODOLOGY_GAP" and not report.bet_ranking:
        raise SchemaError(
            "bet_ranking is empty; it is the report headline and must be "
            "non-empty for a non-METHODOLOGY_GAP verdict"
        )


def _build_user_payload(
    l3: L3Summary,
    tc: TargetClassification,
    funnel_projection: FunnelProjection,
    config: RunConfig,
) -> str:
    payload = {
        "asset_label": config.asset.label,
        "category": config.category,
        "context_labels_in_run": sorted(l3.context_fit.keys()),
        "target_classification": tc.to_dict(),
        "l3_summary": l3.to_dict(),
        "funnel_projection": funnel_projection.to_dict(),
    }
    return (
        "INPUTS FOR STRATEGIC MEMO\n"
        "===========================\n\n"
        "The funnel_projection is an INPUT — heuristic, directional. Do not "
        "emit it or any funnel rate; reference it only in `why` fields and "
        "to inform bet_ranking.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\n\nReturn the Report JSON now (including bet_ranking). "
        "No prose, no fences."
    )
