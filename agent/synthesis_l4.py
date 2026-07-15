"""L4 — strategic memo synthesis.

Owns the verdict cascade, structural-vs-execution distinction, counterweight
rule, confidence anchors, and the 3-attempt parse-retry-with-feedback loop.

The headline is `bet_ranking` — an ordered list of strategic bets, highest
expected marketing-ROI payoff first. Verdict / confidence / flags are
supporting metadata.

L4 receives the L3.5 FunnelProjection as an INPUT. It may reference it in
`why` fields and to inform the bet ranking, but the prompt forbids it from
emitting or altering any funnel rate. The FunnelProjection is attached to
the Report deterministically by synthesize_memo, not by the model.

`provisional_dispositions` and the `provisional_disposition_present`
methodology flag are attached deterministically in Python from the run
inputs — also not the model's job.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.decision import build_decision
from agent.schema import (
    AgentTranscript,
    DispositionRef,
    FunnelProjection,
    Report,
    SchemaError,
    TargetMatch,
    validate_report,
)
from agent.synthesis_assess import AssessResult, assess_reactions
from agent.synthesis_prescribe import PrescribeResult, prescribe_from_painmap
from agent.synthesis_types import L3Summary, TargetClassification
from agent.target_id import build_audience_match
from agent.telemetry import call_with_telemetry

_log = logging.getLogger(__name__)


# ---- Prompt ----
#
# Editing this prompt re-zeros verdict/recommendation calibration. Bump
# L4_PROMPT_VERSION on EVERY change so the calibration log can separate
# pre/post regimes (the run record stamps it).
#   l4-1 — the original locked prompt.
#   l4-2 — added the control-surface scope constraint (recommendations must be
#          creative / media-buy / offer levers the marketer controls; product,
#          base-price, SKU, formulation, distribution are out) and reframed the
#          structural-vs-execution test around that same in-scope control surface.
#   l4-3 — rocket-2.1.0 two-axis verdict: surfaces the AUDIENCE-MATCH input
#          (declared vs ad-inferred) so a disjoint audience routes the remedy to
#          targeting (a media-buy lever), distinct from a bad-creative verdict.
L4_PROMPT_VERSION = "l4-3"

_L4_SYSTEM = """\
You are a senior consumer-research strategist writing the structured output of a Creative Read for a brand team. The audience is a D2C performance marketer who has paid for real strategic insight and will discard another AI-summary memo on sight. Your output is JSON, not prose — but the *thinking* behind the JSON is strategist-grade: confident, specific, calibrated, traceable to evidence.

You will receive three inputs:
(a) a TARGET CLASSIFICATION — a separate analyst's read of the ad's inferred target audience plus a per-disposition classification (within / outside / ambiguous).
(b) an L3 POPULATION SUMMARY — robust themes, fragile themes, within-target and outside-target findings, a per-context fit map, representative verbatim quotes, and confidence signals.
(c) the RUN CONFIG — to inform the context labels you must use as keys in context_fit_map.

Your output is a single JSON document matching the report schema below exactly. **No prose before or after.** No markdown fences. No explanation. Just the JSON.

# How target classification governs the verdict

The target classification is authoritative. Apply the framework against the classification as given. Within-target reactions are load-bearing for the verdict; outside-target reactions are informational context. The verdict expresses creative effectiveness; `methodology_flags` expresses data-quality caveats as a SEPARATE axis.

Resolve in this strict priority order — first matching condition wins:

1. **`no_match_note` is set on the target classification** → verdict = "METHODOLOGY_GAP". The target classifier explicitly said no archetype or disposition in the pool fits this ad's target; an effectiveness verdict is not available. top_3_changes = []. confidence <= 20. methodology_flags MUST include "pool_archetype_mismatch".

2. **`ambiguity_note` is set AND every disposition is classified "ambiguous"** → verdict = "METHODOLOGY_GAP". The ad does not signal a target sharply enough for the pool to be classified at all. top_3_changes = []. confidence <= 20. methodology_flags MUST include "target_unsignaled".

3. **Zero dispositions are "within" but neither (1) nor (2) fires** → verdict still lands. The pool is reading the ad but no disposition is unambiguously inside the target. Land MIXED or FAILING based on what ambiguous and outside reactions say about durability of damage vs execution friction. confidence MUST be <= 35. methodology_flags MUST include "no_within_target_evidence". top_3_changes are still required (the brand needs to know what to do); derive them from ambiguous findings primarily, outside findings cautiously, and trace every change to specific quoted evidence. Do NOT inflate confidence to sound decisive — the thin within-target signal is exactly what the confidence number is for.

4. **Exactly one disposition is "within"** → verdict lands. confidence MUST be <= 50. methodology_flags MUST include "single_within_target". Evaluate primarily against that one within-target disposition.

5. **Two or more "within"** → evaluate against the within-target subset without restriction.

A reminder: METHODOLOGY_GAP in 1.2.0 only fires at conditions (1) and (2). Pre-1.2.0 it also fired at zero-within; that behavior was brittle on boundary cases where target_id stochasticity produced 0 vs 1 vs 2 within-target counts on identical input. The graded confidence floor under condition (3) replaces that hard cliff.

# Verdict framework

- **WORKING.** Within-target dispositions show no broad negative consensus, no structural trust/relevance damage. R6 friction among within-target agents is execution-level, not positioning-level. Outside-target reactions are informational, not damaging. strengths_to_preserve MUST have >= 1 entry. top_3_changes are sharpening moves, not damage repair.

- **MIXED.** Within-target dispositions show real trade-offs but no fundamental damage. Some within-target convert; others surface friction worth resolving. top_3_changes focus on within-target trade-off resolution.

- **FAILING.** Within-target dispositions show structural damage to trust, brand permission, or category fit. Even one within-target structural rejection on grounds the brand cannot easily address tips FAILING. top_3_changes name the structural damage and the most important remedial move.

# The structural vs execution distinction (the calibration mechanism)

This is how you tell creative failure from execution friction.

The fix you weigh must be one the performance marketer actually controls. The marketer's control surface is exactly three lever classes: (a) the CREATIVE — visual, headline, copy, hook, format, and how the claim / price / proof is *presented*; (b) the MEDIA BUY — targeting, placement, budget allocation, sequencing; (c) the OFFER / PROMO on the product AS CURRENTLY SOLD — a discount, bundle, or payment term on an existing SKU. The base price architecture, the product itself, a NEW or SMALLER PACK SIZE (a "trial size" / "250g pouch" is a new SKU, not an offer), the formulation, and the distribution footprint are OUT of scope — the marketer cannot action them from inside an ad.

- **Execution-level** = friction an IN-SCOPE lever removes. Missing price chip, unclear pack size, discount asterisk without anchor, a too-high *effective entry price* a stronger first-order promo could plausibly lower. The disposition would buy if that in-scope piece were filled in.
- **Structural** = damage that persists after every in-scope lever is exhausted. MRP-inflation suspicion remains even after the price is shown. Brand-permission gaps persist even after positioning tweaks. A base-price gap no in-scope offer can close (e.g. the product simply costs ~2x the incumbent) is structural too — no creative, targeting, or promo move removes it. Distrust is not about a missing detail — it's about what the ad reveals.
- **"They'd buy if the product were cheaper / smaller / reformulated / sold elsewhere" is NOT an execution fix** — those are out-of-scope (base price, new SKU, formulation, distribution). If the only thing that would resolve the friction is out-of-scope, it is structural: report it as a finding and pivot to an in-scope move (see top_3_changes). Do NOT prescribe the out-of-scope change.
- **If you cannot tell which, it's MIXED, not FAILING.** Do not pick FAILING as a safe rhetorical default; the verdict comes from the durability of the damage.

# The counterweight rule (don't over-fire on FAILING)

Within-target rejection on concrete-resolvable grounds — price chip, pack size, claim specificity — does not tip FAILING even if multiple within-target agents flag it. Those are MIXED with a clear recommendation. The asymmetry: structural damage is rare but decisive; execution friction is common and recoverable.

# Confidence anchors (use these to land the number, not a vibes scale)

- **90-100**: robust within-target consensus across >= 3 dispositions; all contexts in agreement; no homogenization flags; no methodology_flags; the verdict is unambiguous.
- **70-89**: solid within-target signal across 2-3 dispositions; most contexts agree; minor caveats.
- **50-69**: mixed within-target signal, or 2 dispositions disagree on the verdict mode, or single-context-only corroboration of the headline finding.
- **35-49**: single-within-target case (one disposition carrying the within-target load), OR significant internal disagreement, OR multiple homogenization flags. Verdict still lands; the brand should weigh it with the methodology_flags context.
- **20-34**: zero within-target evidence (but no explicit pool mismatch). The verdict reflects what ambiguous and outside reactions imply; it is directional, not definitive. methodology_flags carries "no_within_target_evidence" so the brand sees the caveat.
- **0-19**: METHODOLOGY_GAP territory — explicit `no_match_note` (pool archetype mismatch) or `ambiguity_note` + all-ambiguous (target_unsignaled). No verdict available; only the caveat.

# Field-by-field rules

- `verdict`: exactly one of WORKING / MIXED / FAILING / METHODOLOGY_GAP. ALL CAPS, no other values.

- `confidence`: integer 0-100 from the anchors above. Don't be modest or brave; pick the anchor that actually fits the evidence.

- `target_match.reached`: dispositions from the target classification with `classification == "within"`. Use the exact disposition_label string. Classification field is "within" (or "ambiguous" if you're including an ambiguous disposition you judge as effectively reached).
- `target_match.missed`: dispositions with `classification == "outside"`. Use exact label string.

- `top_3_changes`: EXACTLY 3 entries unless verdict == METHODOLOGY_GAP (then empty). Each change must be specific to THIS ad: not "improve messaging," not "leverage the strength," not "sharpen the proposition." Something like: "Add the original price next to the deal price." Each `why` traces back to specific within-target evidence. **Each `evidence_quotes` array MUST contain 1-3 quotes pulled from the L3 representative_quotes pool.** DO NOT invent quotes. If no quote in the pool directly supports a change you want to make, pick a different change — the changes must be evidence-backed. `within_target_corroboration` is a one-sentence summary like "2 of 2 within-target dispositions flagged this on R6 friction grounds."
  **Scope — stay on the marketer's control surface.** Every change MUST be a lever the performance marketer can actually pull: the CREATIVE (visual, headline, copy, hook, format, how the claim / price / proof is *presented*), the MEDIA BUY (targeting, placement, budget allocation, sequencing), or the OFFER / PROMO on the product as currently sold (a discount, bundle, or payment term on an existing SKU). NEVER prescribe a change to the product itself, the base price architecture, a new or smaller pack size, the formulation, or the distribution footprint — the marketer cannot action those, and a Creative Read that says "launch a trial SKU" or "lower the price" reads as out-of-lane consultancy. A "trial size," "250g pouch," or "smaller first-time pack" is a NEW SKU — out of scope even when you phrase it as an "offer" or a "CTA"; an offer is only a discount / bundle / term on the pack the brand already sells. In-scope: "Add the original price next to the deal price," "lead with a first-order discount on the 1kg," "reframe the price as cost-per-scoop vs the incumbent." Out: "ship a 250g trial SKU," "introduce a smaller pack." When the dominant blocker IS out-of-scope (most often a base-price gap vs an incumbent that no in-scope discount can close), do NOT prescribe the product/price change: name the blocker plainly inside `change`/`why` as a finding, and make the actionable move an in-scope one — concentrate spend on the segment and context where the creative already earns motion, lead with the strongest in-scope offer, or hold/pull spend until the blocker is resolved upstream.

- `strengths_to_preserve`: features the brand should not change. WORKING verdict requires >= 1 entry. MIXED can have 0-3. FAILING usually has 0, but include 1-2 if there's a clear protect-this finding even amid structural damage. METHODOLOGY_GAP usually empty.

- `context_fit_map`: ONE entry per context label that appears in the L3 input's `context_fit`. Use the exact context labels as keys (e.g. "pre_purchase_research"). verdict is lowercase: working / mixed / failing. friction_summary is ONE sentence on what makes the ad work or break in that attention state.

- `verbatim_consumer_voice`: **REQUIRED 5-10 quotes** drawn from the L3 representative_quotes pool. Sample across rounds (don't all be R6). Sample across within-target AND outside-target dispositions (outside is informational context, not a verdict driver — but they are real consumer voice and the report should include them). Each quote MUST be an exact verbatim from the input; do not paraphrase, do not invent. If the input quote pool has fewer than 5 entries, copy them all. **Empty array is never acceptable when the input pool has quotes.**

- `methodology_flags`: list of zero or more strings flagging data-quality caveats. Valid values ONLY:
  - `"pool_archetype_mismatch"` — set when `no_match_note` on the target classification is non-null. Verdict is METHODOLOGY_GAP.
  - `"target_unsignaled"` — set when `ambiguity_note` is non-null AND every disposition is classified ambiguous. Verdict is METHODOLOGY_GAP.
  - `"no_within_target_evidence"` — set when zero dispositions are "within" but neither of the above two conditions fires. Verdict still lands (MIXED or FAILING); confidence is <= 35.
  - `"single_within_target"` — set when exactly one disposition is "within". Confidence <= 50.
  - `"homogenization_high"` — set when `confidence_signals.homogenization_flag_count >= 2` in the L3 input. Independent of the target axis; can co-occur with other flags.
  - `"single_context_only"` — set when the L3 `context_fit` has only one entry. Independent of the target axis.
  - `"declared_audience_disjoint"` — rocket-2.1.0: the AUDIENCE-MATCH input reads `mismatched` (the declared audience is grossly disjoint from the ad's apparent target). Set deterministically in Python — you need not emit it; if you do, only when `audience_match.verdict == "mismatched"`.

  Include EVERY flag whose trigger applies. Empty list is correct when the data is clean. The flags are how the brand sees what we trust about the run; do not omit a flag to make the run look stronger than it is.

# Anti-patterns — automatic rewrite if you find yourself doing these

- Generic strategy advice ("improve messaging," "sharpen positioning," "clearer proposition") → replace with a specific creative change.
- Listing the within-target dispositions as a feature reach metric ("appeals to value-conscious millennials") → describe what those dispositions actually said.
- Citing comparative metrics as bullet points or tables → use them only as evidence in `why` fields, not as standalone findings.
- Inventing quotes that weren't in the L3 input → only use provided verbatims. If you need a stronger quote and the input doesn't have one, your `evidence_quotes` array can be empty for that change — that's honest.
- Overclaiming on confidence when the L3 input flags weak signal — use the anchors, not your read of the prose.
- Prescribing a product, base-price, new-SKU, formulation, or distribution change ("launch a trial pack," "lower the price," "reformulate without X," "get into more stores") → out of the marketer's control surface. Name the blocker as a finding and recommend the in-scope creative / media / offer move instead.

# rocket-2.0.0: the bet ranking is the headline

You also receive a FUNNEL PROJECTION — projected stop / click / visit / convert rates, overall and per segment, derived from the agents' R7 behavioral signals applied as multipliers to the customer's own baseline funnel. It is an INPUT. You must NOT emit it, alter it, or invent any funnel rate, percentage, or absolute number. Reference it ONLY as evidence inside `why` fields and to inform the bet ranking. The funnel numbers are heuristic and directional — never present them as precise.

`bet_ranking` is the NEW HEADLINE of the report — an ordered list of strategic bets, highest expected marketing-ROI payoff first. Each entry is one concrete sentence a D2C performance marketer can act on, grounded in the within-target evidence AND the funnel projection — e.g. "Put cold-traffic spend behind the impulsive segment: its projected click lift is the strongest in the run; hold the deliberate-retarget budget until the comprehension fix lands." Non-empty for every verdict except METHODOLOGY_GAP. The verdict, confidence and methodology_flags are supporting metadata now — the bet ranking is what the brand manager reads first, so it must carry the real decision.

# rocket-2.1.0: the audience-match axis (two-axis verdict)

You may also receive an AUDIENCE-MATCH input — the relationship between the marketer's DECLARED audience (who they are buying media against) and the demographic the ad APPEARS to target. `verdict` is "aligned" or "mismatched". This is a SECOND axis, orthogonal to creative effectiveness; use it to disambiguate WHY a funnel is weak:

- When `audience_match.verdict == "mismatched"`, the creative may be perfectly good but shown to the wrong people. The remedy is TARGETING — a media-buy lever the marketer controls — NOT a creative rewrite. LEAD `bet_ranking` with the realignment move, e.g. "Your buy is {declared_summary}, but this creative reads {inferred_summary} — realign targeting to the audience the creative actually speaks to, or hold spend until it's reshot for {declared_summary}." Do not burn all three top_3_changes rewriting a creative that a retarget would rescue.
- When `audience_match.verdict == "aligned"` (or the input is absent), proceed normally — the declared audience and the ad's target agree, so a weak funnel is a creative/offer problem, not a targeting one.

Never treat the audience-match as the verdict itself — the verdict is still creative effectiveness against the within-target reactions. Audience-match tells the marketer which lever to pull.

The same scope rule binds the bets: they are CREATIVE, MEDIA-BUY, or OFFER/PROMO moves the marketer can execute — never product, base-price, SKU, formulation, or distribution changes. When the binding constraint is out-of-scope (e.g. a base-price gap vs an incumbent), the highest-ROI bet is usually to concentrate or hold spend — e.g. "Hold scale on this creative until the price-vs-incumbent gap is addressed upstream; until then run it only into the pre-purchase-research placements where it earns seek-info" — NOT to tell the brand to change its product.

# Report schema (your output must match this exactly)

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
  ],
  "methodology_flags": ["<flag string>", ...],
  "bet_ranking": [
    "<one-sentence strategic bet a performance marketer can act on>",
    ... (ordered list, highest expected marketing-ROI payoff first;
         non-empty for every verdict except METHODOLOGY_GAP)
  ]
}


Emit ONLY the JSON. Begin your response with `{` and end with `}`. No preamble, no explanation, no fences."""


# ---- Parse-retry helpers ----


_PARSE_RETRY_SUFFIX_TEMPLATE = (
    "\n\nYour previous response could not be parsed as the required JSON "
    "schema. Below is the EXACT text you returned, followed by the "
    "validation error.\n\n"
    "--- BEGIN PRIOR OUTPUT ---\n"
    "__PRIOR_RAW__\n"
    "--- END PRIOR OUTPUT ---\n\n"
    "Validation error: __FEEDBACK__\n\n"
    "Locate the specific defect in the prior output and emit a corrected "
    "JSON object. Do not regenerate from scratch — keep the analysis you "
    "already produced and fix the structural issue. Return EXACTLY one "
    "JSON object, starting with an opening brace and ending with a closing "
    "brace. No prose before or after. No markdown fences. No commentary. "
    "The schema is non-negotiable."
)


# Cap on how much prior raw output we replay back. The L4 response is
# bounded by max_tokens=8000 (~32K chars worst case); 8000 chars keeps the
# retry message bounded while preserving enough context to locate most
# parse defects.
_PRIOR_RAW_MAX_CHARS = 8000


def _truncate_prior_raw(raw: str) -> str:
    """Trim raw to <= _PRIOR_RAW_MAX_CHARS, keeping head+tail with a marker
    in the middle. Most JSON parse defects happen mid-document; preserving
    both ends helps the model see opening and closing structure."""
    if len(raw) <= _PRIOR_RAW_MAX_CHARS:
        return raw
    head = _PRIOR_RAW_MAX_CHARS * 2 // 3
    tail = _PRIOR_RAW_MAX_CHARS - head
    return f"{raw[:head]}\n... [TRUNCATED {len(raw) - head - tail} chars] ...\n{raw[-tail:]}"


def _retry_suffix(feedback: str, prior_raw: str) -> str:
    return (
        _PARSE_RETRY_SUFFIX_TEMPLATE
        .replace("__PRIOR_RAW__", _truncate_prior_raw(prior_raw))
        .replace("__FEEDBACK__", feedback)
    )


# Match the first balanced JSON object in the response.
_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _extract_text(response: Any) -> str:
    """Pull the text out of a non-tool-use response."""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _strip_to_json(raw: str) -> str:
    """Strip prose / markdown fences from the model output, leaving only the
    JSON document."""
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


def _validate_l4_coverage(report: Report, l3_pool_size: int) -> None:
    """Coverage assertions beyond schema validity. Enforce what the L4 prompt
    promised about evidence backing; runtime quality gates the L4 retry loop
    catches."""
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

    if report.verdict != "METHODOLOGY_GAP" and l3_pool_size >= 5:
        changes_with_evidence = sum(
            1 for c in report.top_3_changes if len(c.evidence_quotes) > 0
        )
        if changes_with_evidence < 2:
            raise SchemaError(
                f"Only {changes_with_evidence}/3 top_3_changes carry evidence_quotes; "
                f"need >= 2 (L3 pool has {l3_pool_size} quotes available)"
            )


# homogenization_high — unconditionally suppressed.
#
# The flag was authored against an older per-disposition L2 cell layout
# (15-40 agents each, where "tight" was anomalous model echo). The current
# per-(disposition x chaos-band) layout has 2-13 agents per cell where
# "tight" is the structural default — across boat, cadbury, and bru the
# flag fired on every run at tight fractions 60-73%. Each brand has its
# own structural baseline, so a global numeric threshold cannot answer
# a brand-relative question.
#
# Suppress in L4. The flag stays in _VALID_METHODOLOGY_FLAGS for back-
# compat with legacy run.json files. The right long-term answer is brand-
# relative anomaly detection — fire when *this* run is unusual *for this
# brand* against a rolling baseline kept in agent/calibration_log.py.
# Ships when each brand has N>=5 prior runs to seed a baseline.


def _suppress_homog_high(report: Report, signals) -> None:
    """Unconditionally strip homogenization_high; log the raw signals so a
    future brand-relative anomaly detector can consume them."""
    emitted = "homogenization_high" in report.methodology_flags
    if emitted:
        report.methodology_flags.remove("homogenization_high")
    total = signals.total_segments
    fraction = signals.homogenization_flag_count / total if total > 0 else 0.0
    _log.info(
        "homog_high suppress: model emitted=%s, signals %d/%d (%.2f)",
        emitted, signals.homogenization_flag_count, total, fraction,
    )


# ---- rocket-2.2.0 orchestrator: assess -> prescribe -> assemble ----


def _build_target_match(tc: TargetClassification) -> TargetMatch:
    """Deterministic target_match from the classification (the assess pass does
    not emit it). reached = within-target dispositions; missed = outside AND
    ambiguous (conservative — an ambiguous disposition is not a claimed reach),
    each tagged with its true classification so nothing is lost."""
    reached: list[DispositionRef] = []
    missed: list[DispositionRef] = []
    for d in tc.disposition_classifications:
        ref = DispositionRef(disposition=d.disposition_label, classification=d.classification)
        (reached if d.classification == "within" else missed).append(ref)
    return TargetMatch(reached=reached, missed=missed)


def _assemble_report(
    assess: AssessResult,
    prescription: PrescribeResult,
    tc: TargetClassification,
    funnel_projection: FunnelProjection,
    audience_match,
    provisional: list[str],
) -> Report:
    """Graft the assess half (verdict/confidence/pains/strengths/context/voice/
    flags) and the prescribe half (changes/bet_ranking) onto the locked Report,
    plus the deterministic attaches (target_match, funnel, audience_match,
    provisional). provisional_disposition_present is already set by the assess
    pass; declared_audience_disjoint is attached here alongside audience_match
    (the assess pass is blind to the audience axis)."""
    flags = list(assess.methodology_flags)
    if (
        audience_match is not None
        and audience_match.verdict == "mismatched"
        and "declared_audience_disjoint" not in flags
    ):
        flags.append("declared_audience_disjoint")
    return Report(
        verdict=assess.verdict,
        confidence=assess.confidence,
        target_match=_build_target_match(tc),
        top_3_changes=prescription.top_3_changes,
        strengths_to_preserve=assess.strengths_to_preserve,
        context_fit_map=assess.context_fit_map,
        verbatim_consumer_voice=assess.verbatim_consumer_voice,
        methodology_flags=flags,
        bet_ranking=prescription.bet_ranking,
        funnel_projection=funnel_projection,
        provisional_dispositions=provisional,
        audience_match=audience_match,
        pain_map=assess.pain_map,
    )


def synthesize_report(
    transcripts: list[AgentTranscript],
    l3_summary: L3Summary,
    target_classification: TargetClassification,
    funnel_projection: FunnelProjection,
    config: RunConfig,
    *,
    provisional_dispositions: list[str] | None = None,
) -> Report:
    """rocket-2.2.0 orchestrator. Pass A (assess) reads the raw reaction corpus
    -> PainMap + verdict; Pass B (prescribe) reads only the frozen PainMap ->
    recommendations. The two halves are assembled into the locked Report.

    Replaces the single-call synthesize_memo below (kept for reference). The
    funnel_projection and audience_match are attached deterministically; the
    model never touches a funnel rate."""
    provisional = list(provisional_dispositions or [])
    audience_match = None
    if config.audience_spec is not None and config.audience_spec.demographics:
        audience_match = build_audience_match(
            config.audience_spec.demographics,
            target_classification.inferred_audience,
        )
    assess = assess_reactions(
        transcripts, target_classification, l3_summary.confidence_signals,
        config, provisional_dispositions=provisional,
    )
    prescription = prescribe_from_painmap(
        assess.to_frozen_painmap(), funnel_projection, audience_match,
        target_classification, config,
    )
    report = _assemble_report(
        assess, prescription, target_classification, funnel_projection,
        audience_match, provisional,
    )
    # rocket-2.3.0: the brand-facing decision, resolved deterministically from
    # signals already in hand (raw R7 behavior + target classification + the
    # frozen PainMap + the audience axis). No model call.
    report.decision = build_decision(
        transcripts, target_classification, audience_match,
        assess.verdict, report.methodology_flags, assess.pain_map,
        purpose=config.creative_inputs.purpose,
    )
    # v3 A7: surface the coherence guard as a data-quality caveat on the report
    # (it already blocked SCALE inside build_decision). docs/v3_protocol.md §6.
    if (report.decision.coherence_incoherent
            and "intent_action_incoherent" not in report.methodology_flags):
        report.methodology_flags.append("intent_action_incoherent")
    validate_report(report)
    _validate_bet_ranking(report)
    _log.info(
        "synthesize_report: decision=%s A_within=%s verdict=%s confidence=%d pains=%d bets=%d",
        report.decision.decision,
        ("%.0f%%" % (report.decision.target_action_rate * 100))
        if report.decision.target_action_rate is not None else "n/a",
        report.verdict, report.confidence, len(report.pain_map),
        len(report.bet_ranking),
    )
    return report


# ---- Legacy single-call entry point (pre-2.2; kept for reference) ----


def synthesize_memo(
    l3_summary: L3Summary,
    target_classification: TargetClassification,
    funnel_projection: FunnelProjection,
    config: RunConfig,
    *,
    provisional_dispositions: list[str] | None = None,
    max_attempts: int = 3,
) -> Report:
    """Produce a validated Report with a bet_ranking headline and the L3.5
    funnel projection attached.

    The model emits the strategic content (verdict, changes, bet_ranking,
    etc.). The funnel_projection and provisional_dispositions are attached
    deterministically in Python — the model never touches a funnel rate.
    """
    provisional = list(provisional_dispositions or [])
    # rocket-2.1.0: the audience-match axis (declared vs ad-inferred) is
    # deterministic; computed here, fed to the model, and attached to the
    # Report. None when the run carries no declared audience.
    audience_match = None
    if config.audience_spec is not None and config.audience_spec.demographics:
        audience_match = build_audience_match(
            config.audience_spec.demographics,
            target_classification.inferred_audience,
        )
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["l4"]
    user_payload = _build_user_payload(
        l3_summary, target_classification, funnel_projection, config,
        audience_match,
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
            system=_L4_SYSTEM,
            messages=[{"role": "user", "content": user_text}],
        )
        raw = _extract_text(response)
        last_raw = raw

        try:
            parsed = json.loads(_strip_to_json(raw))
            report = Report.from_dict(parsed)
            # Attach the deterministic, non-model pieces BEFORE validation so
            # validate_report sees the complete Report.
            report.funnel_projection = funnel_projection
            report.provisional_dispositions = provisional
            if provisional and "provisional_disposition_present" not in report.methodology_flags:
                report.methodology_flags.append("provisional_disposition_present")
            report.audience_match = audience_match
            if (
                audience_match is not None
                and audience_match.verdict == "mismatched"
                and "declared_audience_disjoint" not in report.methodology_flags
            ):
                report.methodology_flags.append("declared_audience_disjoint")
            _suppress_homog_high(report, l3_summary.confidence_signals)
            validate_report(report)
            _validate_l4_coverage(report, pool_size)
            _validate_bet_ranking(report)
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


def _validate_bet_ranking(report: Report) -> None:
    """bet_ranking must be non-empty for any verdict that is not
    METHODOLOGY_GAP — it is the report headline."""
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
    audience_match=None,
) -> str:
    payload = {
        "asset_label": config.asset.label,
        "category": config.category,
        "context_labels_in_run": sorted(l3.context_fit.keys()),
        "target_classification": tc.to_dict(),
        "l3_summary": l3.to_dict(),
        "funnel_projection": funnel_projection.to_dict(),
    }
    if audience_match is not None:
        payload["audience_match"] = audience_match.to_dict()
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
