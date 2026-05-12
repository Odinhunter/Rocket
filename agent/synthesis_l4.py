"""L4 — Strategic memo synthesis.

Single Opus call. Reads (L3Summary, TargetClassification, RunConfig); emits
a Report in the response body as JSON. No tool-use mode — tool-use
truncation was the empirical failure mode in the pre-refactor strategist.

Failure mode and retry:
  - Model may emit JSON with parse / validate errors despite the strict
    prompt. Retry up to 3 times with a strict suffix appended each time.
  - If all 3 attempts fail, raise — the run is broken and the caller must
    decide whether to drop the asset or rerun.

This module owns the verdict-logic prompt that was previously in
`synthesis.py:_STRATEGIST_SYSTEM`. Reshaped from tool-use to response-body
JSON against the locked 7-field schema. Verdict logic (WORKING / MIXED /
FAILING / METHODOLOGY_GAP, structural-vs-execution, counterweight rule,
single-within caveat) preserved verbatim — it's the methodology, not the
format.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.schema import Report, SchemaError, validate_report
from agent.synthesis_types import L3Summary, TargetClassification
from agent.telemetry import call_with_telemetry


_log = logging.getLogger(__name__)


# ---- Prompt ----


_REPORT_SCHEMA_TEMPLATE = """\
{
  "verdict": "WORKING" | "MIXED" | "FAILING" | "METHODOLOGY_GAP",
  "confidence": <integer 0-100>,
  "target_match": {
    "reached": [{"disposition": "<label>", "classification": "within" | "ambiguous"}, ...],
    "missed":  [{"disposition": "<label>", "classification": "outside" | "ambiguous"}, ...]
  },
  "top_3_changes": [
    {
      "change": "<one-sentence specific change>",
      "why": "<one-sentence reason traced to within-target evidence>",
      "evidence_quotes": [{"quote": "<verbatim>", "disposition": "<label>", "round": <1-6>, "context": "<label>"}, ...],
      "within_target_corroboration": "<one sentence: 'N of M within-target dispositions flagged this on grounds X'>"
    },
    ... (EXACTLY 3 entries unless verdict == METHODOLOGY_GAP, in which case use an empty list [])
  ],
  "strengths_to_preserve": [
    {
      "strength": "<one-sentence specific strength>",
      "evidence_quotes": [{"quote": "<verbatim>", "disposition": "<label>", "round": <1-6>, "context": "<label>"}, ...]
    },
    ... (>= 1 entry if verdict == WORKING; may be empty for FAILING / METHODOLOGY_GAP)
  ],
  "context_fit_map": {
    "<context_label>": {
      "verdict": "working" | "mixed" | "failing",
      "friction_summary": "<one sentence on what works or breaks in this attention state>"
    },
    ... (one entry per context label provided in the L3 context_fit input)
  },
  "verbatim_consumer_voice": [
    {"quote": "<verbatim>", "disposition": "<label>", "round": <1-6>, "context": "<label>"},
    ... (5-10 quotes, drawn from the L3 representative_quotes pool, sampled across within-target AND outside-target dispositions, sampled across rounds)
  ]
}
"""


_L4_SYSTEM = """\
You are a senior consumer-research strategist writing the structured \
output of a Creative Read for a brand team. The audience is a D2C \
performance marketer who has paid for real strategic insight and will \
discard another AI-summary memo on sight. Your output is JSON, not \
prose — but the *thinking* behind the JSON is strategist-grade: \
confident, specific, calibrated, traceable to evidence.

You will receive three inputs:
(a) a TARGET CLASSIFICATION — a separate analyst's read of the ad's \
inferred target audience plus a per-disposition classification \
(within / outside / ambiguous).
(b) an L3 POPULATION SUMMARY — robust themes, fragile themes, \
within-target and outside-target findings, a per-context fit map, \
representative verbatim quotes, and confidence signals.
(c) the RUN CONFIG — to inform the context labels you must use as keys \
in context_fit_map.

Your output is a single JSON document matching the report schema below \
exactly. **No prose before or after.** No markdown fences. No \
explanation. Just the JSON.

# How target classification governs the verdict

The target classification is authoritative. Apply the framework against \
the classification as given. Within-target reactions are load-bearing \
for the verdict; outside-target reactions are informational context.

- If `no_match_note` is set OR every within-target list is empty (no \
dispositions classified "within"): set verdict = "METHODOLOGY_GAP". The \
run cannot land an effectiveness verdict because the disposition pool \
tested does not include the ad's apparent target. top_3_changes MUST be \
an empty list []. confidence MUST be <= 20.

- If every disposition is "ambiguous" (no "within", no "outside"): \
set verdict = "METHODOLOGY_GAP". The creative does not signal target \
sharply enough for the pool to be classified. top_3_changes = [], \
confidence <= 20.

- If only one disposition is "within": the verdict lands but confidence \
MUST be <= 50. The brand needs broader within-target coverage before \
the recommendation is load-bearing.

Otherwise, evaluate against the within-target subset.

# Verdict framework

- **WORKING.** Within-target dispositions show no broad negative \
consensus, no structural trust/relevance damage. R6 friction among \
within-target agents is execution-level, not positioning-level. \
Outside-target reactions are informational, not damaging. \
strengths_to_preserve MUST have >= 1 entry. top_3_changes are \
sharpening moves, not damage repair.

- **MIXED.** Within-target dispositions show real trade-offs but no \
fundamental damage. Some within-target convert; others surface friction \
worth resolving. top_3_changes focus on within-target trade-off \
resolution.

- **FAILING.** Within-target dispositions show structural damage to \
trust, brand permission, or category fit. Even one within-target \
structural rejection on grounds the brand cannot easily address tips \
FAILING. top_3_changes name the structural damage and the most \
important remedial move.

# The structural vs execution distinction (the calibration mechanism)

This is how you tell creative failure from execution friction.

- **Structural** = damage that persists after the obvious fix. \
MRP-inflation suspicion remains even after the price is shown. Brand-\
permission gaps persist even after positioning tweaks. Distrust is not \
about a missing detail — it's about what the ad reveals.
- **Execution-level** = friction the obvious fix removes. Missing \
price chip, unclear pack size, discount asterisk without anchor. The \
disposition would buy if the missing piece were filled in.
- **If you cannot tell which, it's MIXED, not FAILING.** Do not pick \
FAILING as a safe rhetorical default; the verdict comes from the \
durability of the damage.

# The counterweight rule (don't over-fire on FAILING)

Within-target rejection on concrete-resolvable grounds — price chip, \
pack size, claim specificity — does not tip FAILING even if multiple \
within-target agents flag it. Those are MIXED with a clear \
recommendation. The asymmetry: structural damage is rare but decisive; \
execution friction is common and recoverable.

# Confidence anchors (use these to land the number, not a vibes scale)

- **90-100**: robust within-target consensus across >= 3 dispositions; \
all contexts in agreement; no homogenization flags; no METHODOLOGY_GAP \
triggers; the verdict is unambiguous.
- **70-89**: solid within-target signal across 2-3 dispositions; most \
contexts agree; minor caveats.
- **50-69**: mixed within-target signal, or 2 dispositions disagree on \
the verdict mode, or single-context-only corroboration of the headline \
finding.
- **30-49**: single within-target disposition only, OR significant \
internal disagreement, OR multiple homogenization flags.
- **0-19**: METHODOLOGY_GAP territory — pool mismatch, target ambiguity, \
or no within-target dispositions.

# Field-by-field rules

- `verdict`: exactly one of WORKING / MIXED / FAILING / METHODOLOGY_GAP. \
ALL CAPS, no other values.

- `confidence`: integer 0-100 from the anchors above. Don't be modest or \
brave; pick the anchor that actually fits the evidence.

- `target_match.reached`: dispositions from the target classification \
with `classification == "within"`. Use the exact disposition_label string. \
Classification field is "within" (or "ambiguous" if you're including an \
ambiguous disposition you judge as effectively reached).
- `target_match.missed`: dispositions with `classification == "outside"`. \
Use exact label string.

- `top_3_changes`: EXACTLY 3 entries unless verdict == METHODOLOGY_GAP \
(then empty). Each change must be specific to THIS ad: not "improve \
messaging," not "leverage the strength," not "sharpen the proposition." \
Something like: "Add the original price next to the deal price." Each \
`why` traces back to specific within-target evidence. **Each \
`evidence_quotes` array MUST contain 1-3 quotes pulled from the L3 \
representative_quotes pool.** DO NOT invent quotes. If no quote in the \
pool directly supports a change you want to make, pick a different \
change — the changes must be evidence-backed. \
`within_target_corroboration` is a one-sentence summary like "2 of 2 \
within-target dispositions flagged this on R6 friction grounds."

- `strengths_to_preserve`: features the brand should not change. WORKING \
verdict requires >= 1 entry. MIXED can have 0-3. FAILING usually has 0, \
but include 1-2 if there's a clear protect-this finding even amid \
structural damage. METHODOLOGY_GAP usually empty.

- `context_fit_map`: ONE entry per context label that appears in the L3 \
input's `context_fit`. Use the exact context labels as keys (e.g. \
"pre_purchase_research"). verdict is lowercase: working / mixed / \
failing. friction_summary is ONE sentence on what makes the ad work or \
break in that attention state.

- `verbatim_consumer_voice`: **REQUIRED 5-10 quotes** drawn from the L3 \
representative_quotes pool. Sample across rounds (don't all be R6). \
Sample across within-target AND outside-target dispositions (outside is \
informational context, not a verdict driver — but they are real consumer \
voice and the report should include them). Each quote MUST be an exact \
verbatim from the input; do not paraphrase, do not invent. If the input \
quote pool has fewer than 5 entries, copy them all. **Empty array is \
never acceptable when the input pool has quotes.**

# Anti-patterns — automatic rewrite if you find yourself doing these

- Generic strategy advice ("improve messaging," "sharpen positioning," \
"clearer proposition") → replace with a specific creative change.
- Listing the within-target dispositions as a feature reach metric \
("appeals to value-conscious millennials") → describe what those \
dispositions actually said.
- Citing comparative metrics as bullet points or tables → use them \
only as evidence in `why` fields, not as standalone findings.
- Inventing quotes that weren't in the L3 input → only use provided \
verbatims. If you need a stronger quote and the input doesn't have one, \
your `evidence_quotes` array can be empty for that change — that's \
honest.
- Overclaiming on confidence when the L3 input flags weak signal — \
use the anchors, not your read of the prose.

# Report schema (your output must match this exactly)

""" + _REPORT_SCHEMA_TEMPLATE + """

Emit ONLY the JSON. Begin your response with `{` and end with `}`. No \
preamble, no explanation, no fences."""


_PARSE_RETRY_SUFFIX_TEMPLATE = (
    "\n\nYour previous response could not be parsed as the required JSON "
    "schema. Return EXACTLY one JSON object matching the schema, starting "
    "with an opening brace and ending with a closing brace. No prose "
    "before or after. No markdown fences. No commentary. The schema is "
    "non-negotiable.\n\n"
    "Validation feedback from the prior attempt: __FEEDBACK__"
)


def _retry_suffix(feedback: str) -> str:
    return _PARSE_RETRY_SUFFIX_TEMPLATE.replace("__FEEDBACK__", feedback)


# ---- Public entry point ----


def synthesize_memo(
    l3_summary: L3Summary,
    target_classification: TargetClassification,
    config: RunConfig,
    *,
    max_attempts: int = 3,
) -> Report:
    """Run L4: produce a validated Report from L3 + target classification.

    Raises if all parse-retry attempts fail. The caller (RunService) catches
    and decides whether to mark the run as failed or attempt one outer-loop
    retry.
    """
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["l4"]
    user_payload = _build_user_payload(l3_summary, target_classification, config)
    pool_size = len(l3_summary.representative_quotes)

    last_feedback: str = ""
    last_raw: str = ""
    for attempt in range(max_attempts):
        prompt = _L4_SYSTEM
        if attempt > 0:
            user_text = user_payload + _retry_suffix(last_feedback)
        else:
            user_text = user_payload

        response = call_with_telemetry(
            client,
            layer="strategist",
            model=model,
            retries=attempt,
            max_tokens=4000,
            system=prompt,
            messages=[{"role": "user", "content": user_text}],
        )
        raw = _extract_text(response)
        last_raw = raw

        try:
            report_json = _strip_to_json(raw)
            parsed = json.loads(report_json)
            report = Report.from_dict(parsed)
            validate_report(report)
            _validate_l4_coverage(report, pool_size)
            return report
        except (json.JSONDecodeError, KeyError, TypeError, SchemaError) as exc:
            last_feedback = f"{type(exc).__name__}: {exc}"
            _log.warning(
                "L4 parse/validate failed (attempt %d/%d): %s. Raw head: %r",
                attempt + 1, max_attempts, last_feedback, raw[:500],
            )

    raise RuntimeError(
        f"L4 synthesis failed after {max_attempts} attempts. "
        f"Last feedback: {last_feedback}. Raw output head: {last_raw[:500]!r}"
    )


def _validate_l4_coverage(report: Report, l3_pool_size: int) -> None:
    """Coverage assertions that go beyond schema validity.

    These enforce what the L4 prompt promised about evidence backing. They
    are NOT part of the locked schema (a Report with empty quotes is still
    structurally valid JSON) — they are runtime quality gates the L4 retry
    loop catches.
    """
    # verbatim_consumer_voice: 5-10 when the pool has them.
    if l3_pool_size >= 5:
        if len(report.verbatim_consumer_voice) < 5:
            raise SchemaError(
                f"verbatim_consumer_voice has {len(report.verbatim_consumer_voice)} "
                f"quotes; need >= 5 (L3 quote pool has {l3_pool_size} entries to draw from)"
            )
    elif l3_pool_size > 0 and len(report.verbatim_consumer_voice) == 0:
        raise SchemaError(
            f"verbatim_consumer_voice is empty but L3 pool has {l3_pool_size} quotes"
        )

    # Evidence quotes on top_3_changes: at least 2 of 3 should carry a quote
    # if the pool has quotes to spare.
    if report.verdict != "METHODOLOGY_GAP" and l3_pool_size >= 5:
        changes_with_evidence = sum(
            1 for c in report.top_3_changes if len(c.evidence_quotes) > 0
        )
        if changes_with_evidence < 2:
            raise SchemaError(
                f"Only {changes_with_evidence}/3 top_3_changes carry evidence_quotes; "
                f"need >= 2 (L3 pool has {l3_pool_size} quotes available)"
            )


# ---- Internals ----


def _extract_text(response: Any) -> str:
    """Pull the text out of a non-tool-use response."""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


# Match the first balanced JSON object in the response. Sonnet/Opus
# sometimes wraps with stray whitespace or a leading note despite the
# strict prompt; this strips back to {…}.
_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _strip_to_json(raw: str) -> str:
    """Strip prose / markdown fences from the model output, leaving only the
    JSON document. If the model emitted a fenced block (```json … ```),
    grab the contents."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        # ```json\n...\n```
        # Find the first newline after the fence and the last fence.
        first_newline = stripped.find("\n")
        if first_newline > 0:
            stripped = stripped[first_newline + 1:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()
    # Now find the JSON object boundary
    m = _JSON_RE.search(stripped)
    if not m:
        raise json.JSONDecodeError("no JSON object found in response", raw, 0)
    return m.group(0)


def _build_user_payload(
    l3: L3Summary,
    tc: TargetClassification,
    config: RunConfig,
) -> str:
    """Assemble the L3 + target classification + run context as the user
    message to the L4 prompt. Compact JSON keeps token cost down while
    preserving all evidence."""
    payload = {
        "asset_label": config.asset.label,
        "category": config.category,
        "archetype": config.archetype,
        "context_labels_in_run": sorted(l3.context_fit.keys()),
        "target_classification": tc.to_dict(),
        "l3_summary": l3.to_dict(),
    }
    return (
        "INPUTS FOR STRATEGIC MEMO\n"
        "===========================\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + "\n\nReturn the Report JSON now. No prose, no fences."
    )
