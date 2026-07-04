"""L4b — the prescribe pass (the action rung).

rocket-2.2.0 Pass B. It reads ONLY the FROZEN PainMap produced by the assess
pass (agent/synthesis_assess.py) — never the raw reactions. This blindness is
the point (locked decision 1): a prescriber that cannot see the raw testimony
cannot motivated-reason its diagnosis toward a pet fix, and the PainMap becomes
an auditable, standalone brand-manager deliverable.

It derives top_3_changes (each `derives_from_pains` — many pains -> one fix; a
one-pain-one-fix list is the failure mode) + bet_ranking. Grounding moved up a
level: a recommendation is grounded by the pains it cites, and each pain was
grounded in verbatim quotes back in the assess pass. So prescribe enforces:
  * referential integrity — every derives_from_pains id exists in the PainMap.
  * lever space — recommendations stay on the marketer control surface.

Preserves the l4-3 audience-match routing: when audience_match is "mismatched",
the remedy is TARGETING (a media-buy lever), led in bet_ranking — not a creative
rewrite. That routing moved here from _L4_SYSTEM because prescribe owns
bet_ranking; audience_match is fed in deterministically.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.grounding import check_lever_space, verify_pain_references
from agent.schema import FunnelProjection, Quote, TopChange
from agent.synthesis_types import TargetClassification
from agent.telemetry import call_with_telemetry

_log = logging.getLogger(__name__)


# ---- Prompt ----
#
# Bump PRESCRIBE_PROMPT_VERSION on EVERY change (the run record stamps it).
#   prescribe-1 — first production port of the painmap prototype's prescribe
#                 pass. Carries the l4-3 audience-match routing (mismatched ->
#                 lead bet_ranking with targeting) preserved from _L4_SYSTEM.
PRESCRIBE_PROMPT_VERSION = "prescribe-1"


_PRESCRIBE_SYSTEM = """\
You are a senior D2C performance-marketing strategist writing the ACTION half
of a Creative Read. You did NOT see the raw consumer reactions — deliberately.
You are handed a DIAGNOSED PAIN MAP (root-cause pains, each with mechanism,
funnel stage, severity, prevalence, within-target flag, and grounding quotes),
plus the verdict, the funnel projection, the audience-match, and the target
classification. You reason from diagnosed pains, not from what any single
consumer said.

Produce top_3_changes and bet_ranking.

- Each recommendation must DERIVE from one or more pains — cite their ids in
  derives_from_pains. The best recommendations resolve MULTIPLE pains at once;
  a one-pain-one-fix list is a failure mode. Prioritise by how much brand cost
  the addressed pains carry (severity x prevalence x within-target).
- SCOPE — stay on the marketer's control surface. Every change is a CREATIVE
  (visual, headline, copy, hook, format, how claim/price/proof is presented),
  a MEDIA-BUY (targeting, placement, budget, sequencing), or an OFFER/PROMO on
  the product AS CURRENTLY SOLD (discount, bundle, term on an existing SKU).
  NEVER prescribe a change to the product, base price, a new or smaller pack
  size / trial size (that is a new SKU), the formulation, or distribution. When
  a binding pain is structural / out-of-scope, name it as a finding and pivot
  the action to an in-scope move (concentrate or hold spend on the segment and
  context where the creative earns motion; lead with the strongest in-scope
  offer).
- AUDIENCE-MATCH routing: if audience_match.verdict == "mismatched", the
  creative may be fine but shown to the wrong people — LEAD bet_ranking with
  the targeting realignment. If "aligned" (or absent), a weak funnel is a
  creative/offer problem, not a targeting one.
- bet_ranking is the HEADLINE: an ordered list, highest expected marketing-ROI
  first, each one concrete sentence a marketer can act on.

Each change must be specific to THIS ad (not "improve messaging"). The funnel
projection is heuristic/directional — reference it in reasoning, never emit a
rate. lever_class is one of: creative | media_buy | offer.

Output a single JSON object, no prose, no fences, matching exactly:

{
  "top_3_changes": [
    {
      "change":"<one specific in-scope move>",
      "why":"<the strategic reasoning, derived from the pains>",
      "derives_from_pains":["P1","P3"],
      "lever_class":"creative|media_buy|offer",
      "within_target_corroboration":"<one sentence>"
    }
  ],
  "bet_ranking": ["<bet 1>", "<bet 2>", ...]
}

Begin with { and end with }. No preamble, no fences."""


# ---- Result type ----


@dataclass
class PrescribeResult:
    """Pass B output. Phase 4 grafts these onto the Report alongside the assess
    fields. On a METHODOLOGY_GAP diagnosis both are empty (nothing coherent to
    prescribe from)."""
    top_3_changes: list[TopChange]
    bet_ranking: list[str]


# ---- Model-call plumbing (local, per codebase convention) ----


_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _extract_text(response: Any) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _strip_to_json(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline > 0:
            stripped = stripped[first_newline + 1:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()
    m = _JSON_RE.search(stripped)
    if not m:
        raise json.JSONDecodeError("no JSON object found in response", raw, 0)
    return m.group(0)


def _overall_rates(fp: FunnelProjection | None) -> dict:
    """The directional funnel signal prescribe may reference (never emit). Only
    the scalar rates — bands and per-segment detail are noise for lever choice."""
    if fp is None:
        return {}
    o = fp.overall
    return {
        "stop_rate": round(o.stop_rate, 4),
        "click_rate": round(o.click_rate, 4),
        "visit_rate": round(o.visit_rate, 4),
        "convert_rate": round(o.convert_rate, 4),
    }


def _build_prescribe_payload(
    frozen_painmap: dict,
    fp: FunnelProjection | None,
    audience_match,  # AudienceMatch | None
    tc: TargetClassification,
) -> str:
    am = audience_match.to_dict() if audience_match is not None else None
    lever_slice = {
        "inferred_audience": tc.inferred_audience.to_dict(),
        "disposition_classifications": [
            {"disposition": d.disposition_label, "classification": d.classification}
            for d in tc.disposition_classifications
        ],
    }
    return (
        "DIAGNOSED PAIN MAP + VERDICT:\n"
        + json.dumps(frozen_painmap, indent=2, ensure_ascii=False)
        + "\n\nFUNNEL PROJECTION (heuristic, directional):\n"
        + json.dumps({"overall": _overall_rates(fp)}, indent=2)
        + "\n\nAUDIENCE MATCH:\n"
        + json.dumps(am, indent=2, ensure_ascii=False)
        + "\n\nTARGET CLASSIFICATION (for lever routing):\n"
        + json.dumps(lever_slice, indent=2, ensure_ascii=False)
        + "\n\nDerive top_3_changes + bet_ranking now. Return the JSON."
    )


def _parse_changes(parsed: dict) -> tuple[list[TopChange], list[str]]:
    changes = [
        TopChange(
            change=c["change"],
            why=c["why"],
            evidence_quotes=[Quote(**q) for q in c.get("evidence_quotes", [])],
            within_target_corroboration=c.get("within_target_corroboration", ""),
            derives_from_pains=list(c.get("derives_from_pains", [])),
            lever_class=c.get("lever_class", ""),
        )
        for c in parsed.get("top_3_changes", [])
    ]
    bet_ranking = list(parsed.get("bet_ranking", []))
    return changes, bet_ranking


# ---- Public entry point ----


def prescribe_from_painmap(
    frozen_painmap: dict,
    funnel_projection: FunnelProjection | None,
    audience_match,  # AudienceMatch | None
    target_classification: TargetClassification,
    config: RunConfig,
    *,
    max_attempts: int = 3,
) -> PrescribeResult:
    """Pass B: derive top_3_changes + bet_ranking from the frozen PainMap only.

    METHODOLOGY_GAP short-circuit: a can't-assess diagnosis has nothing coherent
    to prescribe from — return empties WITHOUT a model call (mirrors the old
    single-call behaviour where METHODOLOGY_GAP carried 0 changes).
    """
    if frozen_painmap.get("verdict") == "METHODOLOGY_GAP":
        _log.info("prescribe short-circuit: METHODOLOGY_GAP -> empty recommendations")
        return PrescribeResult(top_3_changes=[], bet_ranking=[])

    pain_map = frozen_painmap.get("pain_map", [])
    base_payload = _build_prescribe_payload(
        frozen_painmap, funnel_projection, audience_match, target_classification
    )
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["prescribe"]

    last_feedback, last_raw = "", ""
    for attempt in range(max_attempts):
        if attempt > 0:
            user_text = (
                base_payload
                + f"\n\nYour previous output was rejected: {last_feedback}\n"
                "Return ONE corrected JSON object matching the schema exactly. "
                "No prose, no fences."
            )
        else:
            user_text = base_payload

        response = call_with_telemetry(
            client,
            layer="prescriber",
            model=model,
            retries=attempt,
            max_tokens=4000,
            system=_PRESCRIBE_SYSTEM,
            messages=[{"role": "user", "content": user_text}],
        )
        raw = _extract_text(response)
        last_raw = raw

        try:
            parsed = json.loads(_strip_to_json(raw))
            changes, bet_ranking = _parse_changes(parsed)
            problems = _validate_prescription(changes, bet_ranking, pain_map)
            if problems:
                raise ValueError(problems)
            return PrescribeResult(top_3_changes=changes, bet_ranking=bet_ranking)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            last_feedback = f"{type(exc).__name__}: {exc}"
            _log.warning(
                "prescribe parse/validate failed (attempt %d/%d): %s. Raw head: %r",
                attempt + 1, max_attempts, last_feedback, raw[:400],
            )

    raise RuntimeError(
        f"prescribe pass failed after {max_attempts} attempts. "
        f"Last feedback: {last_feedback}. Raw head: {last_raw[:400]!r}"
    )


def _validate_prescription(changes: list[TopChange], bet_ranking: list[str], pain_map: list) -> str:
    """Return a human-readable problem string (empty == clean) for the retry
    loop. Enforces: exactly 3 changes, a non-empty bet_ranking, rec->pain
    referential integrity, and the in-scope lever surface."""
    if len(changes) != 3:
        return f"top_3_changes must have exactly 3 entries, got {len(changes)}"
    if not bet_ranking:
        return "bet_ranking is empty; it is the report headline and must be non-empty"
    for c in changes:
        if not c.derives_from_pains:
            return (
                f"change {c.change[:50]!r} cites no pains — every recommendation "
                "must derive from >= 1 pain id"
            )
    dangling = verify_pain_references(changes, pain_map)
    if dangling:
        known = [p.get("id") if isinstance(p, dict) else getattr(p, "id", None) for p in pain_map]
        return f"derives_from_pains references unknown pain id(s) {dangling}; known: {known}"
    lever_hits = check_lever_space(changes, bet_ranking)
    if lever_hits:
        return f"out-of-scope lever(s) — recommend only creative/media-buy/offer moves: {lever_hits[:2]}"
    return ""
