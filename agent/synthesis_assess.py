"""L4a — the assess pass (the diagnosis rung).

rocket-2.2.0 splits the old single L4 memo into two passes. This is Pass A: it
reads the FULL raw reaction corpus (~100 reactions labelled by disposition /
within-outside / context) and produces a PainMap (root-cause pains) together
with the verdict, confidence, strengths, context_fit, and verbatim_voice —
diagnosis and verdict are the same cognitive act, kept together. It does NOT
write recommendations; Pass B (prescribe) derives those from the frozen PainMap.

Confidence discipline lives here + in schema.validate_report:
  * methodology_flags are computed DETERMINISTICALLY in Python from the target
    classification + confidence_signals (the model emits none). The flags
    finally have teeth — they were prompt-only in the old L4.
  * structural verdicts are hard-capped: METHODOLOGY_GAP <= 20, zero-within
    (no_within_target_evidence) <= 35. single-within is NOT capped (rocket-2.2
    decision: the flag fires for transparency, the number is earned). The cap is
    applied here (a clamp — the flag is deterministic, so re-prompting the model
    to lower a number it cannot move is pointless) and re-enforced as an
    invariant in schema.validate_report.

The confidence ANCHORS in _VERDICT_FRAMEWORK are still the pre-v2.2
(summarized-engine) numbers; Phase 5 re-anchors them for raw-corpus reading.
The hard caps above are stable across that re-anchoring.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.grounding import verify_quote_authenticity
from agent.schema import (
    AgentTranscript,
    ContextFitEntry,
    Pain,
    Quote,
    Strength,
    VERDICT,
)
from agent.synthesis_types import ConfidenceSignals, TargetClassification
from agent.telemetry import call_with_telemetry

_log = logging.getLogger(__name__)


# ---- Prompt ----
#
# Editing this prompt re-zeros verdict/diagnosis calibration. Bump
# ASSESS_PROMPT_VERSION on EVERY change so the calibration log can separate
# pre/post regimes (the run record stamps it).
#   assess-1 — first production port of the painmap prototype's assess pass.
#              Confidence anchors were the pre-v2.2 (summarized-engine) numbers.
#   assess-2 — Phase 5 re-anchor for raw-corpus reading. Removed the stale
#              "single-within <= 50" cap text (it contradicted decision 2 and
#              the code, which the model ignored — landing single-within at 74);
#              rewrote the anchor ladder so a single audience is placed by how
#              vivid/unanimous ITS evidence is (thin ~45-57, vivid ~70-84) and
#              only multi-audience consensus earns 85+. Kept the zero-within
#              <=35 and METHODOLOGY_GAP <=20 anchors (those caps stand). Added a
#              structural example: a parent-company reveal that breaks an
#              indie-DTC brand's permission is structural, not execution.
ASSESS_PROMPT_VERSION = "assess-2"


_VERDICT_FRAMEWORK = """\
# How the target classification governs the verdict

The target classification is authoritative. Within-target reactions are
load-bearing for the verdict; outside-target reactions are informational
context. Resolve in this strict priority order — first match wins:

1. `no_match_note` set -> verdict = "METHODOLOGY_GAP", confidence <= 20.
2. `ambiguity_note` set AND every disposition classified "ambiguous" ->
   verdict = "METHODOLOGY_GAP", confidence <= 20.
3. Zero dispositions "within" (but neither 1 nor 2) -> verdict still lands
   (MIXED or FAILING on durability of damage), confidence <= 35.
4. Exactly one "within" -> verdict lands; confidence is EARNED by the vividness
   and internal consistency of that single audience's signal (see the anchors),
   NOT capped at a fixed number.
5. Two or more "within" -> evaluate against the within-target subset; this is
   what earns the high-confidence band.

# Verdict definitions

- WORKING: within-target dispositions show no broad negative consensus, no
  structural trust/relevance damage; within-target R6 friction is execution-
  level, not positioning-level.
- MIXED: within-target dispositions show real trade-offs but no fundamental
  damage; some convert, others surface resolvable friction.
- FAILING: within-target dispositions show structural damage to trust, brand
  permission, or category fit. Even one within-target structural rejection on
  grounds the brand cannot address tips FAILING.

# Structural vs execution (the calibration mechanism)

The fix you weigh must be one the performance marketer controls: (a) CREATIVE
(visual, headline, copy, hook, format, how claim/price/proof is presented),
(b) MEDIA BUY (targeting, placement, budget, sequencing), (c) OFFER/PROMO on
the product AS CURRENTLY SOLD (discount, bundle, term on an existing SKU).
Base price, the product itself, a NEW or SMALLER pack size (a "trial size" is
a new SKU), formulation, and distribution are OUT of scope.

- Execution-level = friction an in-scope lever removes (missing price chip,
  unclear pack size). The buyer would act if that in-scope piece were filled.
- Structural = damage that persists after every in-scope lever is exhausted
  (MRP-inflation suspicion after price is shown; a base-price gap no in-scope
  offer can close; brand-permission gaps — e.g. a parent-company / conglomerate
  reveal that breaks an indie clean-label / DTC brand's permission is
  structural, not execution). "They'd buy if it were cheaper / smaller /
  reformulated / sold elsewhere" is NOT an execution fix — it is structural,
  because the resolving move is out of scope.
- If you cannot tell which, it is MIXED, not FAILING.

# The counterweight rule (don't over-fire FAILING)

Within-target rejection on concrete-resolvable grounds (price chip, pack size,
claim specificity) does NOT tip FAILING even if several within-target agents
flag it — that is MIXED with a clear recommendation. Structural damage is rare
but decisive; execution friction is common and recoverable.

# Confidence anchors

You read the FULL raw corpus, not a thrice-distilled summary — so you may
justify more conviction than a summarized read could. But confidence is EARNED
by the evidence in front of you, never defaulted. Confidence answers "how sure
am I of the VERDICT," which is separate from "is the ad good": a vivid,
near-unanimous rejection warrants HIGH confidence in a FAILING verdict.

- 85-100: strong within-target consensus across >= 2 distinct dispositions, most
  or all contexts agree, the signal is vivid and internally consistent.
- 70-84: a clear read — EITHER multi-disposition agreement with some friction,
  OR a SINGLE within-target disposition whose signal is vivid, high-volume, and
  internally consistent across contexts. One audience reaches this band only
  when its evidence is genuinely rich and unanimous.
- 58-69: a solid but qualified read — a single within-target audience with
  consistent-but-thinner signal, or two dispositions that disagree on mode, or a
  headline resting on a single context.
- 45-57: a single within-target audience whose signal is thin, mixed, or
  ambiguous — the verdict lands but rests on limited evidence.
- 20-34: zero within-target evidence (graded on outside-target reactions only,
  no explicit pool mismatch). Capped here no matter how vivid the outside
  reactions read — they are not verdict-load-bearing.
- 0-19: METHODOLOGY_GAP (pool mismatch or a fully unsignaled target).

A single within-target disposition does NOT sit at the ceiling by default: place
it by how rich and unanimous THAT audience's evidence is. Multi-audience
consensus is what earns the top band.
"""


_ASSESS_SYSTEM = """\
You are a senior consumer-research strategist performing the DIAGNOSIS half of
a Creative Read for a D2C performance marketer. You are handed the raw,
unedited reactions of ~100 simulated consumers who each saw one ad and reacted
across seven beats: R1 gut, R2 comprehension, R3 emotion, R4 stickiness, R5
social, R6 friction, R7 action. Each reaction is labelled with the consumer's
disposition, whether that disposition is WITHIN or OUTSIDE the ad's target, and
the feed context.

Your job is NOT to recommend fixes. Your job is to DIAGNOSE.

Consumers testify to symptoms — what they noticed, felt, misread, ignored, or
bounced off. You name the disease. A PAIN is a root-cause account of why the ad
loses (or nearly loses) a buyer: the latent friction, unmet need, or
trust/relevance gap underneath the surface complaints. You produce it by
SYNTHESIZING across many reactions — never by restating one.

The difference, concretely:
- Restated symptom (BAD): "Consumers don't know the price."
- Diagnosed pain (GOOD): "The creative opens a consideration loop it cannot
  close on-surface: every engaged buyer reaches an unanswered 'what does this
  cost / is it worth it' question and defers to an off-ad search that mostly
  never happens — earned interest leaks between comprehension and
  consideration." (mechanism + funnel stage + why it costs the brand)

Rules for the PainMap:
- Each pain is a root-cause DIAGNOSIS with a mechanism, not a symptom, not a
  quote, NEVER a fix.
- SYNTHESIZE: each pain accounts for a PATTERN across multiple reactions /
  dispositions where one exists. Merge symptoms that share a root cause into
  ONE pain; do not split one cause into three. Aim for the 5-9 pains that
  actually move the read, ordered by how much they cost the brand.
- GROUND every pain in 1-4 VERBATIM quotes copied exactly from the reactions
  (exact substrings; never paraphrase, never invent). Record cited_by
  (disposition labels), prevalence (roughly how widespread), and contexts.
- Tag within_target: true if the pain is felt by dispositions marked WITHIN.
  Within-target pain is load-bearing for the verdict; outside is context.
- Tag severity: 'structural' or 'execution' per the framework below.
- Tag funnel_stage: attention | comprehension | consideration | conversion |
  recall.

""" + _VERDICT_FRAMEWORK + """

From the SAME reading you also produce: verdict, confidence,
strengths_to_preserve, context_fit (one per context label present), and a
verbatim_voice sample (5-10 exact quotes across rounds and within/outside).
You do NOT write recommendations — a separate strategist derives those from
your PainMap. You do NOT emit methodology_flags — those are computed
deterministically from the target classification.

Output a single JSON object, no prose, no fences, matching exactly:

{
  "verdict": "WORKING|MIXED|FAILING|METHODOLOGY_GAP",
  "confidence": <int 0-100>,
  "pain_map": [
    {
      "id": "P1",
      "pain": "<root-cause diagnosis: mechanism + why it costs the brand>",
      "funnel_stage": "attention|comprehension|consideration|conversion|recall",
      "severity": "structural|execution",
      "within_target": true,
      "prevalence": "<how widespread, which dispositions/contexts>",
      "cited_by": ["<disposition_label>", ...],
      "evidence_quotes": [
        {"quote":"<verbatim>","disposition":"<label>","round":<1-7>,"context":"<label>"}
      ]
    }
  ],
  "strengths_to_preserve": [
    {"strength":"<one sentence>","evidence_quotes":[{"quote":"<verbatim>","disposition":"<label>","round":<1-7>,"context":"<label>"}]}
  ],
  "context_fit": {
    "<context_label>": {"verdict":"working|mixed|failing","friction_summary":"<one sentence>"}
  },
  "verbatim_voice": [
    {"quote":"<verbatim>","disposition":"<label>","round":<1-7>,"context":"<label>"}
  ]
}

Begin with { and end with }. No preamble, no fences."""


# ---- Result type ----


@dataclass
class AssessResult:
    """Pass A output: the diagnosed PainMap + the verdict half of the report.
    Pass B (prescribe) reads only the FROZEN painmap (see to_frozen_painmap) —
    never the raw reactions. Phase 4 maps these fields onto the locked Report."""
    verdict: VERDICT
    confidence: int
    pain_map: list[Pain]
    strengths_to_preserve: list[Strength]
    context_fit_map: dict[str, ContextFitEntry]
    verbatim_consumer_voice: list[Quote]
    methodology_flags: list[str] = field(default_factory=list)

    def to_frozen_painmap(self) -> dict:
        """The exact, minimal object the prescribe pass is allowed to see. No
        raw reactions — only the diagnosis. This is also the standalone,
        shippable brand-manager deliverable (painmap.json)."""
        return _frozen_painmap_dict(
            self.verdict, self.confidence, self.pain_map,
            self.strengths_to_preserve, self.context_fit_map,
        )


def _frozen_painmap_dict(verdict, confidence, pain_map, strengths, context_fit_map) -> dict:
    """The frozen-painmap shape — shared by AssessResult (for the prescribe
    handoff) and frozen_painmap_from_report (for persisting painmap.json off the
    assembled Report), so the deliverable and the handoff never drift."""
    return {
        "verdict": verdict,
        "confidence": confidence,
        "pain_map": [p.to_dict() for p in pain_map],
        "strengths_to_preserve": [asdict(s) for s in strengths],
        "context_fit": {
            k: {"verdict": v.verdict, "friction_summary": v.friction_summary}
            for k, v in context_fit_map.items()
        },
    }


def frozen_painmap_from_report(report) -> dict:
    """Reconstruct the frozen-painmap deliverable (painmap.json) from an
    assembled Report — the report already carries every field."""
    return _frozen_painmap_dict(
        report.verdict, report.confidence, report.pain_map,
        report.strengths_to_preserve, report.context_fit_map,
    )


# ---- Deterministic confidence machinery ----


def compute_methodology_flags(
    tc: TargetClassification,
    signals: ConfidenceSignals,
    provisional_dispositions: list[str],
) -> list[str]:
    """Compute the reaction-derived methodology flags DETERMINISTICALLY. The
    assess model emits none of these — Python owns them, so they finally have
    teeth (they were prompt-only, model-emitted-and-trusted in the old L4).

    (declared_audience_disjoint is NOT computed here — it derives from the
    audience_match axis, which is attached at report-assembly time alongside
    audience_match itself, exactly as in the pre-v2.2 pipeline.)
    """
    flags: list[str] = []
    no_match = bool(tc.no_match_note)
    all_ambiguous = (
        bool(tc.ambiguity_note)
        and len(tc.disposition_classifications) > 0
        and len(tc.ambiguous_labels()) == len(tc.disposition_classifications)
    )
    within_count = signals.within_target_disposition_count

    if no_match:
        flags.append("pool_archetype_mismatch")
    if all_ambiguous:
        flags.append("target_unsignaled")
    if not no_match and not all_ambiguous:
        if within_count == 0:
            flags.append("no_within_target_evidence")
        elif within_count == 1:
            flags.append("single_within_target")
    if provisional_dispositions:
        flags.append("provisional_disposition_present")
    if signals.total_contexts == 1:
        flags.append("single_context_only")
    # homogenization_high is never added — it is structurally the default under
    # the per-(disposition x chaos-band) layout and is suppressed. We keep the
    # raw ratio in an observability log for a future brand-relative detector.
    total = signals.total_segments
    fraction = signals.homogenization_flag_count / total if total > 0 else 0.0
    _log.info(
        "homog_high observability: signals %d/%d (%.2f) — not flagged",
        signals.homogenization_flag_count, total, fraction,
    )
    return flags


# Hard structural ceilings — where low confidence is principle, not evidence.
# single-within is deliberately absent (rocket-2.2 decision 2: uncapped).
_STRUCTURAL_CAPS = {
    "no_within_target_evidence": 35,
}
_METHODOLOGY_GAP_CAP = 20


# Pool-quality flags describe the POOL, not the creative — when either fires the
# reactions come from the wrong audience, so no creative-effectiveness verdict is
# available. Force METHODOLOGY_GAP (framework rules 1/2) deterministically rather
# than trusting the model, which will over-read the raw reactions and grade a
# creative it should decline to grade (observed: plix_acv, male pool vs a
# women's ad, read MIXED 42 despite a legit no_match_note).
_GAP_FORCING_FLAGS = {"pool_archetype_mismatch", "target_unsignaled"}


def resolve_verdict(model_verdict: str, flags: list[str]) -> str:
    """Force METHODOLOGY_GAP when a pool-quality flag fires; otherwise keep the
    model's verdict. Called before apply_confidence_caps so the <=20 cap kicks
    in and (via the orchestrator) prescribe short-circuits to empty changes."""
    if _GAP_FORCING_FLAGS & set(flags):
        return "METHODOLOGY_GAP"
    return model_verdict


def apply_confidence_caps(verdict: str, confidence: int, flags: list[str]) -> int:
    """Clamp confidence to the structural ceiling implied by the verdict/flags.
    Clamp (not retry): the flags are deterministic, so the model cannot move
    them — re-prompting it to lower a number under a ceiling it does not control
    is wasted. schema.validate_report re-enforces these as a hard invariant."""
    cap = 100
    if verdict == "METHODOLOGY_GAP":
        cap = min(cap, _METHODOLOGY_GAP_CAP)
    for flag, ceiling in _STRUCTURAL_CAPS.items():
        if flag in flags:
            cap = min(cap, ceiling)
    return min(confidence, cap)


# ---- Corpus assembly ----


def _classification_map(tc: TargetClassification) -> dict[str, str]:
    return {d.disposition_label: d.classification for d in tc.disposition_classifications}


def build_corpus(transcripts: list[AgentTranscript], cls: dict[str, str]) -> str:
    """Render all raw reactions, labelled by disposition / within-outside /
    context. This is what the assess pass reads — the whole point of v2.2 is
    that the diagnosis reasons over the raw corpus, not a thrice-distilled
    summary."""
    blocks: list[str] = []
    for t in transcripts:
        disp = t.disposition_label
        tag = cls.get(disp, "unclassified").upper()
        blocks.append(
            f"--- agent {t.agent_id:03d} | {disp} [{tag}-TARGET] | "
            f"context={t.context_label} ---\n"
            f"{t.encoding_text.strip()}\n{t.reflection_text.strip()}"
        )
    return "\n\n".join(blocks)


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


def _build_assess_payload(tc: TargetClassification, corpus: str) -> str:
    tc_compact = {
        "inferred_target_description": tc.inferred_target_description,
        "inferred_audience": tc.inferred_audience.to_dict(),
        "disposition_classifications": [
            {"disposition": d.disposition_label, "classification": d.classification}
            for d in tc.disposition_classifications
        ],
        "ambiguity_note": tc.ambiguity_note,
        "no_match_note": tc.no_match_note,
    }
    return (
        "TARGET CLASSIFICATION:\n"
        + json.dumps(tc_compact, indent=2, ensure_ascii=False)
        + "\n\nRAW CONSUMER REACTIONS (all agents):\n\n"
        + corpus
        + "\n\nDiagnose the PainMap and the verdict now. Return the JSON."
    )


def _parse_assess(parsed: dict) -> tuple[VERDICT, int, list[Pain], list[Strength], dict, list[Quote]]:
    verdict = parsed["verdict"]
    confidence = int(parsed["confidence"])
    pain_map = [Pain.from_dict(p) for p in parsed.get("pain_map", [])]
    strengths = [
        Strength(
            strength=s["strength"],
            evidence_quotes=[Quote(**q) for q in s.get("evidence_quotes", [])],
        )
        for s in parsed.get("strengths_to_preserve", [])
    ]
    context_fit = {
        k: ContextFitEntry(verdict=v["verdict"], friction_summary=v["friction_summary"])
        for k, v in parsed.get("context_fit", {}).items()
    }
    verbatim = [Quote(**q) for q in parsed.get("verbatim_voice", [])]
    return verdict, confidence, pain_map, strengths, context_fit, verbatim


def _all_quotes(pain_map: list[Pain], strengths: list[Strength], verbatim: list[Quote]) -> list[Quote]:
    """Every quote the report will surface — pain evidence, strength evidence,
    and the verbatim_voice deliverable. All are grounding-checked (the prototype
    only checked pain quotes; verbatim_voice is the customer-facing 'room's
    voice' where a hallucination is worst)."""
    out: list[Quote] = []
    for p in pain_map:
        out.extend(p.evidence_quotes)
    for s in strengths:
        out.extend(s.evidence_quotes)
    out.extend(verbatim)
    return out


# If MORE than this fraction of surfaced quotes cannot be traced to the corpus,
# it is wholesale invention (not the light paraphrase opus does) — a real
# failure, not something to degrade past.
_FABRICATION_TRIPWIRE = 0.5


def _keep_grounded(quotes: list[Quote], corpus: str) -> list[Quote]:
    """Drop the quotes that don't trace to the corpus, keep the rest. Grounding
    is a filter: we never reword a quote, we only remove one we can't verify."""
    return [q for q in quotes if not verify_quote_authenticity([q], corpus)]


def _drop_unverifiable(pain_map: list[Pain], strengths: list[Strength], corpus: str) -> None:
    """Filter each pain's / strength's evidence to grounded quotes only, in
    place. A pain that loses ALL its quotes is KEPT (a diagnosis stands on its
    own) but logged loudly — that is the signal to watch."""
    for p in pain_map:
        kept = _keep_grounded(p.evidence_quotes, corpus)
        if not kept and p.evidence_quotes:
            _log.warning("assess: pain %s lost ALL evidence quotes to grounding", p.id)
        p.evidence_quotes = kept
    for s in strengths:
        s.evidence_quotes = _keep_grounded(s.evidence_quotes, corpus)


# ---- Public entry point ----


def assess_reactions(
    transcripts: list[AgentTranscript],
    target_classification: TargetClassification,
    confidence_signals: ConfidenceSignals,
    config: RunConfig,
    *,
    provisional_dispositions: list[str] | None = None,
    max_attempts: int = 3,
) -> AssessResult:
    """Pass A: read the raw reaction corpus -> PainMap + verdict + confidence +
    strengths + context_fit + verbatim_voice. methodology_flags and the
    structural confidence caps are applied deterministically in Python.
    """
    provisional = list(provisional_dispositions or [])
    cls = _classification_map(target_classification)
    corpus = build_corpus(transcripts, cls)
    base_payload = _build_assess_payload(target_classification, corpus)
    flags = compute_methodology_flags(
        target_classification, confidence_signals, provisional
    )

    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["assess"]

    last_feedback, last_raw = "", ""
    for attempt in range(max_attempts):
        if attempt > 0:
            user_text = (
                base_payload
                + f"\n\nYour previous output was rejected: {last_feedback}\n"
                "Return ONE corrected JSON object matching the schema exactly. "
                "Every evidence quote must be an EXACT substring of the reactions "
                "above — copy, do not paraphrase. No prose, no fences."
            )
        else:
            user_text = base_payload

        response = call_with_telemetry(
            client,
            layer="assessor",
            model=model,
            retries=attempt,
            max_tokens=8000,
            system=_ASSESS_SYSTEM,
            messages=[{"role": "user", "content": user_text}],
        )
        raw = _extract_text(response)
        last_raw = raw

        try:
            parsed = json.loads(_strip_to_json(raw))
            verdict, confidence, pain_map, strengths, context_fit, verbatim = _parse_assess(parsed)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            last_feedback = f"{type(exc).__name__}: {exc}"
            _log.warning(
                "assess parse/build failed (attempt %d/%d): %s. Raw head: %r",
                attempt + 1, max_attempts, last_feedback, raw[:500],
            )
            continue

        # Grounding is a FILTER, not a gate. Retry a couple of times to coax
        # fully-verbatim quotes; on the final attempt, DROP the residual
        # unverifiable ones and continue — a few reworded quotes must never kill
        # a completed diagnosis. Wholesale invention (> tripwire) is the one
        # exception: that is a real failure.
        all_q = _all_quotes(pain_map, strengths, verbatim)
        fabricated = verify_quote_authenticity(all_q, corpus)
        last_attempt = attempt == max_attempts - 1
        if fabricated and not last_attempt:
            preview = "; ".join(q[:60] for q in fabricated[:3])
            last_feedback = (
                f"{len(fabricated)} evidence quote(s) are not verbatim substrings "
                f"of the reactions (e.g. {preview!r})"
            )
            _log.warning(
                "assess grounding retry (attempt %d/%d): %s",
                attempt + 1, max_attempts, last_feedback,
            )
            continue
        if fabricated:  # last attempt with residual unverifiable quotes
            frac = len(fabricated) / max(1, len(all_q))
            if frac > _FABRICATION_TRIPWIRE:
                raise RuntimeError(
                    f"assess: {len(fabricated)}/{len(all_q)} quotes ({frac:.0%}) not "
                    f"traceable to the corpus — wholesale fabrication, not paraphrase"
                )
            _drop_unverifiable(pain_map, strengths, corpus)
            verbatim = _keep_grounded(verbatim, corpus)
            _log.warning(
                "assess: dropped %d/%d unverifiable (paraphrased) quotes; pains retained",
                len(fabricated), len(all_q),
            )

        verdict = resolve_verdict(verdict, flags)
        confidence = apply_confidence_caps(verdict, confidence, flags)
        return AssessResult(
            verdict=verdict,
            confidence=confidence,
            pain_map=pain_map,
            strengths_to_preserve=strengths,
            context_fit_map=context_fit,
            verbatim_consumer_voice=verbatim,
            methodology_flags=list(flags),
        )

    raise RuntimeError(
        f"assess pass failed after {max_attempts} attempts. "
        f"Last feedback: {last_feedback}. Raw head: {last_raw[:500]!r}"
    )
