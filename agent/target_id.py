"""Target classification — Opus vision call, single-asset variant.

Identifies the ad's apparent target audience from creative cues alone,
then classifies each disposition in the run pool as within / outside /
ambiguous against that target.

Deliberately does NOT see population reactions. Target is a property of
the ad, not of who happened to react; keeping reactions out prevents the
model from rationalizing the target to fit who responded.

Single-asset variant: the anchor image from the pre-refactor focal+anchor
flow is gone. This means we lose the "what does premium look like in this
category" calibration; accept the loss for Week 1. If real customer runs
start drifting on target classification, reopen with a per-category text
exemplar.
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any

import anthropic

from agent.config import RunConfig
from agent.entities import AudienceSpec
from agent.purpose import DIRECT_SELL, PURPOSE_ORDER, resolve_purpose
from agent.synthesis_types import (
    CoverageWarning,
    DemographicMismatch,
    DispositionScopeWarning,
    DispositionTarget,
    InferredAudience,
    PurposeMismatch,
    TargetClassification,
)
from agent.telemetry import call_with_telemetry
from agent.vectors import _BAND_TO_AGE_RANGE, DemographicPoint, NamedDisposition


_log = logging.getLogger(__name__)


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


_TOOL = {
    "name": "classify_ad_target",
    "description": (
        "Identify the ad's target audience from creative cues alone, and "
        "classify each disposition in the population pool as within, "
        "outside, or ambiguous against that target. The classification "
        "must be evidence-anchored to specific creative elements — visual, "
        "copy, occasion, brand positioning, demographic signals — not vibes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "inferred_target_description": {
                "type": "string",
                "description": (
                    "One or two sentences describing who this ad is for. "
                    "Specific: age range, life stage, household role, income "
                    "tier, occasion, regional/cultural context where signaled."
                ),
            },
            "target_reasoning": {
                "type": "string",
                "description": (
                    "Trace the inferred target back to specific creative "
                    "evidence. Visual palette, models / no-models, settings, "
                    "props, language register, copy tone, occasion framing, "
                    "brand positioning cues, demographic signals. Avoid vibes "
                    "('looks Indian, must be mass-market') — name the "
                    "specific cues."
                ),
            },
            "inferred_audience": {
                "type": "object",
                "description": (
                    "The single demographic the ad APPEARS to target, read "
                    "from the creative. Be CONSERVATIVE: commit to a specific "
                    "gender or age band ONLY when the ad signals it clearly "
                    "and strongly (e.g. a male-vitality product; a hero model "
                    "of unmistakable age). When the ad is broad, mixed, or "
                    "unsignaled on an axis, use 'mixed' or 'unclear' — those "
                    "are the correct, safe defaults, not a cop-out. Feeds a "
                    "gross-mismatch sanity check, so over-committing causes "
                    "false alarms."
                ),
                "properties": {
                    "gender": {
                        "type": "string",
                        "enum": ["male", "female", "mixed", "unclear"],
                    },
                    "age_band": {
                        "type": "string",
                        "enum": ["18_24", "25_34", "35_44", "45_54",
                                 "55_plus", "mixed", "unclear"],
                    },
                },
                "required": ["gender", "age_band"],
            },
            "disposition_classifications": {
                "type": "array",
                "description": (
                    "One entry per disposition in the input pool. Use the "
                    "exact disposition_label string from the input."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "disposition_label": {"type": "string"},
                        "classification": {
                            "type": "string",
                            "enum": ["within", "outside", "ambiguous"],
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["disposition_label", "classification", "reasoning"],
                },
            },
            "inferred_purpose": {
                "type": "string",
                "enum": list(PURPOSE_ORDER) + ["unclear"],
                "description": (
                    "The ad's APPARENT job, read from the creative alone: "
                    "direct_sell (make a prospect buy one product now — price/"
                    "offer/CTA-led, single product, urgency); cold_hook (stop a "
                    "cold scroller, earn a click/curiosity, NOT a purchase — a "
                    "hooky top-of-funnel teaser); awareness_informer (make people "
                    "NOTICE + UNDERSTAND the brand/range — 'did you know we make "
                    "X', portfolio/educational, no single CTA); brand_building "
                    "(make people FEEL + REMEMBER the brand — emotional/story-led, "
                    "little product detail); retain_winback (re-engage EXISTING "
                    "customers — reorder/renew/'we miss you'/loyalty). Be "
                    "CONSERVATIVE: use 'unclear' when the ad does not clearly "
                    "signal one job. This feeds an advisory mismatch check, so "
                    "over-committing causes false alarms."
                ),
            },
            "purpose_reasoning": {
                "type": "string",
                "description": (
                    "One or two sentences tracing the inferred_purpose to "
                    "specific creative evidence (CTA presence/absence, price "
                    "disclosure, product-detail density, emotional vs "
                    "informational register, single-product vs range)."
                ),
            },
            "ambiguity_note": {
                "type": ["string", "null"],
                "description": (
                    "Set if the ad's creative does not clearly signal a "
                    "target audience (generic / category-only / multiple "
                    "competing targets). An ad that does not signal target "
                    "*has* a creative problem; flag it. Otherwise null."
                ),
            },
            "no_match_note": {
                "type": ["string", "null"],
                "description": (
                    "Set if no dispositions in the pool match the inferred "
                    "target. State which archetype or disposition pool would "
                    "be a better fit. Otherwise null."
                ),
            },
            "uncovered_target_note": {
                "type": ["string", "null"],
                "description": (
                    "Answer this EVEN IF some dispositions matched. Look at "
                    "the buyer you described in inferred_target_description "
                    "and ask: is any substantial part of that buyer missing "
                    "from this pool entirely? If the ad is aimed at someone "
                    "who buys in a different aisle, at a different moment, or "
                    "against a different alternative than anyone in the pool, "
                    "say so in one sentence and name the buyer who is absent. "
                    "Null ONLY if the pool genuinely covers the buyer you "
                    "described. A partial match is not coverage."
                ),
            },
        },
        # ⚠ `uncovered_target_note` is REQUIRED while no_match_note is not, and
        # that asymmetry is the fix. An optional field the model may omit was
        # read with a bare .get() and came back None on the run that needed it
        # most; requiring it forces the question to be answered rather than
        # skipped. It may still answer null — that is a judgement, not a
        # silence.
        "required": [
            "inferred_target_description",
            "target_reasoning",
            "inferred_audience",
            "inferred_purpose",
            "disposition_classifications",
            "uncovered_target_note",
        ],
    },
}


_SYSTEM = """\
You are a senior consumer-research analyst doing target identification on \
a single ad. You will be shown the ad image and a list of dispositions \
describing distinct consumer types within a single archetype. Your job:

1. Identify the target audience of the ad — who is it for.
2. For each disposition, classify it as within / outside / ambiguous \
against the ad's inferred target.
3. Record the ad's apparent demographic (gender skew + age band) in \
`inferred_audience` — CONSERVATIVELY. Use 'mixed'/'unclear' unless the \
creative signals the axis strongly; this field feeds a gross-mismatch \
sanity check, so over-committing causes false alarms.
4. Record the ad's apparent JOB in `inferred_purpose` — what is this ad \
trying to DO (sell now / hook a cold scroller / inform + build awareness / \
build brand feeling + memory / re-engage existing customers). Read it from \
the creative alone (CTA, price disclosure, product-detail density, emotional \
vs informational register, single-product vs range). Use 'unclear' unless the \
ad clearly signals one job — this too feeds an advisory check.

# How to read the ad

Examine the creative for these specific cues. Every claim about target \
must trace to one or more of these — no vibes, no stereotypes:

- **Visual palette** — colors, lighting, contrast, polish vs grain
- **Models or no models** — if models, their age range, gender, dress, \
demographic and aspirational signals; if none, what that itself says
- **Setting and props** — kitchen vs office vs cafe vs home; festive items, \
furniture tier, location class
- **Copy tone and language register** — English / Hinglish / regional, \
formal / casual / aspirational, claim style (price-led / quality-led / \
emotion-led / occasion-led)
- **Occasion framing** — festive (Diwali, Valentine's, Raksha Bandhan, \
wedding), everyday utility, gifting, indulgence, performance / fitness
- **Brand positioning cues** — mass-market / premium / D2C-disruptor / \
legacy-incumbent. Look at logo prominence, packaging shown, retail \
context, price disclosure
- **Demographic signals** — age, income tier, household role, regional / \
cultural context where signaled

# Within / outside / ambiguous

- **within** — the disposition fits the inferred target on the load-bearing \
dimensions (life stage, household role, income tier, attitudinal stance, \
occasion-relevance). Multiple match-points; few or no contradictions.
- **outside** — the disposition fails the target on a load-bearing \
dimension. The household role is wrong, the income tier mismatches, the \
occasion is irrelevant, the attitudinal stance puts them in a different \
segment entirely.
- **ambiguous** — partial match. Some dimensions fit, others don't. Use \
this when the disposition could plausibly be in target depending on \
unspecified context. Don't use ambiguous as a safe default — pick within \
or outside when the evidence supports a clean call.

# Edge cases

- If the creative does not clearly signal a target — generic mass-market \
ad, category-only, multiple competing targets — set `ambiguity_note` and \
classify dispositions liberally as ambiguous. The unsignaled target is \
itself a finding.
- If no dispositions in the pool match the inferred target, set \
`no_match_note` with the archetype that would fit better. All \
classifications can be "outside" in this case.
- The brand or product positioning may target a wider audience than this \
specific ad does. Classify against THIS ad's target as expressed in the \
creative, not the brand's overall positioning.

# Output

Use the classify_ad_target tool. Be specific. Brand managers read your \
classification reasoning and judge whether you've called the target \
correctly — vague reasoning will be dismissed; specific reasoning ("the \
deal price plus the no-model closed-case framing plus the 'Shop Now' CTA \
signal a quick-decision online purchase pitch for existing Boat-tier \
buyers") holds up."""


# The guard that keeps `inferred_audience` creative-derived. Every block of
# customer-supplied free text in this prompt carries it verbatim.
# ⚠ Delete it from one block and that block silently becomes able to steer the
# inference the mismatch guard checks AGAINST — a guard that stops guarding
# looks exactly like a guard. Pinned by
# tests/test_marketer_notes_never_reach_the_agent.py.
_NON_OVERRIDE = (
    "Use this only as context for classifying the dispositions. Do NOT let "
    "it override your inferred_audience — infer the ad's apparent audience "
    "strictly from the creative itself, even if it contradicts this line.\n"
)


def build_target_id_user_content(
    disposition_pool: list[tuple[str, str]],
    config: RunConfig,
) -> list[dict]:
    """Assemble the target-id user message. Pure — no API call, no client.

    ⚠ THIS IS THE ONLY PLACE MARKETER FREE TEXT IS ALLOWED TO REACH A MODEL.
    Extracted from `identify_target` so the seam can be tested without paying
    for a classification: `tests/test_marketer_notes_never_reach_the_agent.py`
    asserts the notes DO appear here (the positive control that proves the
    checker can fail) and do NOT appear in any agent-facing prompt.
    """
    image_block = _image_block(config.asset.image_path)
    disposition_text = "\n\n".join(
        f"**{label}** — {desc}" for label, desc in disposition_pool
    )

    # Archetype is an OPTIONAL hint. When unspecified, omit the line entirely
    # rather than injecting a stale/false pool claim — the classifier infers
    # the pool from the category + the dispositions it is already given.
    archetype = config.archetype.strip()
    archetype_line = (
        f"Archetype: {archetype}\n"
        if archetype and archetype.lower() != "unspecified"
        else ""
    )
    # Declared targeting is the customer's STATED Meta audience — a hint for
    # disposition classification ONLY. It must NOT drive inferred_audience,
    # which has to stay creative-derived so detect_gross_demographic_mismatch
    # compares the creative against the declared audience (not declared vs
    # declared, which would silently defeat the guard).
    declared = config.declared_targeting.strip()
    declared_line = (
        "Customer's DECLARED targeting (the audience they say they are buying "
        f"on Meta): {declared}\n"
        f"{_NON_OVERRIDE}"
        if declared
        else ""
    )
    # The brand manager's own words. A STRONGER customer claim than declared
    # targeting, so it gets the identical treatment and the identical
    # non-override sentence — otherwise someone who writes "our buyers are
    # affluent metro women who love this" shops for a flattering audience and
    # the mismatch chip never fires, because inferred_audience would have been
    # contaminated by the very claim it exists to check.
    notes = "\n".join(
        part for part in (
            config.brand_notes.strip(), config.marketer_notes.strip(),
        ) if part
    )
    notes_line = (
        "Brand manager's NOTES (context they gave us about their market and "
        f"this ad): {notes}\n"
        f"{_NON_OVERRIDE}"
        if notes
        else ""
    )
    return [
        image_block,
        {
            "type": "text",
            "text": (
                f"AD CONTEXT: {config.asset.label}\n"
                f"Category: {config.category}\n"
                f"{archetype_line}"
                f"{declared_line}"
                f"{notes_line}"
                "\n"
                "DISPOSITIONS IN THE RUN POOL:\n\n"
                + disposition_text
                + "\n\nClassify each disposition above against the ad's "
                "inferred target. Use the classify_ad_target tool."
            ),
        },
    ]


def identify_target(
    disposition_pool: list[tuple[str, str]],
    config: RunConfig,
) -> TargetClassification:
    """Run target classification on the asset against the disposition pool.

    disposition_pool: list of (label, description) tuples — the dispositions
    that will participate in this run. The model classifies each against
    the inferred target.
    """
    client = anthropic.Anthropic(max_retries=5)
    model = config.model_versions["target_id"]

    user_content = build_target_id_user_content(disposition_pool, config)

    # No temperature: claude-opus-4-7 deprecated the parameter. Determinism
    # for target_id comes from `output_config.effort` instead — empirically
    # validated (tests/test_target_id_effort.py) to produce byte-identical
    # classifications across 5 runs on the bru boundary case at effort=low.
    #
    # API constraint: `thinking` cannot be combined with forced tool_choice
    # (400: "Thinking may not be enabled when tool_choice forces tool use").
    # We therefore omit `thinking` and rely on effort alone — on Opus 4.7,
    # omitting thinking config disables thinking, and effort=low controls
    # output-token spend and stochasticity.
    create_kwargs: dict = {
        "max_tokens": 4000,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": user_content}],
        "tools": [_TOOL],
        "tool_choice": {"type": "tool", "name": "classify_ad_target"},
    }
    effort = config.efforts.get("target_id")
    if effort is not None:
        create_kwargs["output_config"] = {"effort": effort}

    response = call_with_telemetry(
        client,
        layer="target_id",
        model=model,
        **create_kwargs,
    )

    tool_input = _extract_tool_use(response, "classify_ad_target")
    return _build_target_classification(tool_input, disposition_pool)


def _build_target_classification(
    tool_input: dict,
    disposition_pool: list[tuple[str, str]],
) -> TargetClassification:
    """Normalize: if the model missed a disposition, add it as ambiguous so
    no entries vanish silently."""
    seen = {d["disposition_label"] for d in tool_input.get("disposition_classifications", [])}
    classifications = [DispositionTarget(**d) for d in tool_input["disposition_classifications"]]
    for label, _ in disposition_pool:
        if label not in seen:
            _log.warning("target_id model dropped disposition %r — coercing to ambiguous", label)
            classifications.append(DispositionTarget(
                disposition_label=label,
                classification="ambiguous",
                reasoning="(target classifier did not classify this disposition; defaulting to ambiguous)",
            ))
    # ⚠ THE DETERMINISTIC BACKSTOP. `no_match_note` is the only trigger for
    # `pool_archetype_mismatch`, and the model is asked for it only when
    # NOTHING matches — a precondition it decides for itself. If it classified
    # every disposition outside/ambiguous, that precondition is objectively
    # true whatever it wrote, so synthesize the note rather than trusting it to
    # have volunteered one. Python, not prose: a guard that depends on the
    # thing it is guarding is not a guard.
    uncovered = tool_input.get("uncovered_target_note")
    no_match = tool_input.get("no_match_note")
    if not any(c.classification == "within" for c in classifications):
        if not no_match:
            _log.warning(
                "target_id: no disposition classified within-target and the "
                "model volunteered no no_match_note — synthesizing one"
            )
            no_match = (
                "No consumer type in this pool sits inside the ad's target. "
                "The library does not cover the buyer this creative is aimed "
                "at."
            )
    if uncovered:
        _log.warning("target_id coverage gap: %s", uncovered)
    return TargetClassification(
        inferred_target_description=tool_input["inferred_target_description"],
        target_reasoning=tool_input["target_reasoning"],
        disposition_classifications=classifications,
        ambiguity_note=tool_input.get("ambiguity_note"),
        no_match_note=no_match,
        uncovered_target_note=uncovered,
        inferred_audience=InferredAudience.from_dict(tool_input.get("inferred_audience")),
        inferred_purpose=tool_input.get("inferred_purpose") or "unclear",
        purpose_reasoning=tool_input.get("purpose_reasoning", ""),
    )


def _extract_tool_use(response: Any, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(
        f"Expected tool_use block named {tool_name!r}, got blocks: "
        f"{[getattr(b, 'type', None) for b in response.content]}"
    )


def _image_block(image_path: str) -> dict:
    path = Path(image_path)
    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise ValueError(
            f"Unsupported image extension {path.suffix!r}. Supported: {sorted(_MEDIA_TYPES)}"
        )
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


# ---- Deterministic demographic sanity-check (gross mismatches only) ----
#
# Compares the brand's DECLARED audience demographics against the demographic
# the ad APPEARS to target (TargetClassification.inferred_audience). Pure
# Python — no model. Surfaced pre-commit as an advisory that overrides --yes.
# Intentionally CONSERVATIVE: fires only on gross, unambiguous mismatches
# (wrong-creative uploads, fundamentally misaimed campaigns), never on the
# subtle "declared 25-34, reads 30-45" kind. Distinct from the
# disposition-level pool mismatch (no_match_note).

# rocket-2.1.0: the declared audience is range-based; the inferred audience is
# still a band (vision output). Bridge the band to a range and compare ranges.
_AGE_GROSS_GAP_YEARS = 18  # nearest declared range this many years off = gross
# (18_24 vs 45_54 -> gap 21 fires; 18_24 vs 35_44 -> gap 11 does not — matching
# the pre-2.1 "3 bands apart" behaviour.)

_GENDER_WORD = {"male": "men", "female": "women"}
_AGE_WORD = {
    "18_24": "18-24", "25_34": "25-34", "35_44": "35-44",
    "45_54": "45-54", "55_plus": "55+",
}


def _range_gap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Years between two ranges; 0 if they overlap."""
    if a1 < b0:
        return b0 - a1
    if b1 < a0:
        return a0 - b1
    return 0.0


_SCOPE_NORMALIZE = re.compile(r"[^a-z0-9]+")


def _normalize_scope_text(text: str) -> str:
    """Lowercase, punctuation to single spaces, padded — so a whole-word test is
    a plain substring test. `"proski_protein_cereal"` -> `" proski protein
    cereal "`, in which `" protein "` matches and `" bar "` does not (which is
    the point: `"bar"` must not match `"barista"`)."""
    return f" {_SCOPE_NORMALIZE.sub(' ', text.lower()).strip()} "


def detect_out_of_scope_dispositions(
    dispositions: list[NamedDisposition],
    *,
    asset_label: str,
    category: str,
) -> "DispositionScopeWarning | None":
    """§2.3 — flag dispositions used outside the sub-category they were authored
    for. Deterministic, no model call, no cost. Returns None when nothing in the
    pool declares a scope, or when every declared scope matches the run.

    ⚠ Matched against the ASSET LABEL + CATEGORY, not against the target
    classifier's `inferred_target_description`. The classifier's read is richer
    and it is already computed by the time this runs — and it is MODEL OUTPUT,
    so the same library and the same ad could flag on one run and not the next.
    Every other pre-run guard here is reproducible from the config alone; a
    guard that flickers is one a marketer learns to ignore.

    ⚠ No new form field. The audience form's four questions are a shipped user
    decision (`v3 #38`); a fifth is theirs to authorize, not ours to add. The
    label the marketer already types is the signal."""
    scoped = [d for d in dispositions if d.authored_for]
    if not scoped:
        return None

    haystack_raw = f"{asset_label} {category}".strip()
    haystack = _normalize_scope_text(haystack_raw)
    out_of_scope = [
        (d.label, list(d.authored_for))
        for d in scoped
        # ⚠ BOTH sides stay PADDED. Stripping the needle is what makes "bar"
        # match inside "barista" — and a scope guard that passes on a
        # coincidence is worse than one that fires, because a silent guard is
        # never re-checked.
        if not any(
            _normalize_scope_text(scope) in haystack
            for scope in d.authored_for
        )
    ]
    if not out_of_scope:
        return None

    names = ", ".join(
        f"{label} (authored for {' / '.join(scopes)})"
        for label, scopes in out_of_scope
    )
    plural = "s" if len(out_of_scope) > 1 else ""
    # ⚠ WRITTEN FOR US, NOT FOR THE CUSTOMER — deliberately, and phrased so it
    # could never be mistaken for customer copy or pasted into a read.
    # The user's call, 2026-08-06: that a disposition was authored for another
    # product is OUR library problem, and the fix is to re-author or drop it —
    # not to disclose it to the buyer and let them discount the panel. It is an
    # AUTHORING signal, not a caveat that travels with the run.
    message = (
        f"LIBRARY FIX NEEDED — {len(out_of_scope)} disposition{plural} in this pool "
        f"{'are' if plural else 'is'} out of authored scope: {names}. "
        f"Nothing in \"{haystack_raw}\" matches. Re-author {'them' if plural else 'it'} "
        f"for this product or drop {'them' if plural else 'it'} from the audience "
        f"before this becomes a customer-facing run."
    )
    return DispositionScopeWarning(
        out_of_scope=out_of_scope,
        scoped_count=len(scoped),
        total_count=len(dispositions),
        haystack=haystack_raw,
        message=message,
    )


def detect_gross_demographic_mismatch(
    declared: list[DemographicPoint],
    inferred: InferredAudience,
) -> DemographicMismatch | None:
    """Return a DemographicMismatch iff the ad's apparent demographic grossly
    contradicts the declared audience; else None."""
    axes: list[str] = []

    # GENDER — fire only when the ad reads as one specific gender AND every
    # declared frame is the OPPOSITE specific gender (no 'any'/'unspecified'/
    # mixed-gender frame to absorb it).
    if inferred.gender in ("male", "female"):
        declared_genders = {d.gender for d in declared}
        wildcard = declared_genders & {"any", "unspecified"}
        opposite = "female" if inferred.gender == "male" else "male"
        if not wildcard and declared_genders == {opposite}:
            axes.append("gender")

    # AGE — bridge the inferred band to a range and compare against the
    # declared RANGE audience. Fire only when the nearest declared range is a
    # wide gap from the ad's apparent band (opposite ends of the age spectrum).
    # 'unspecified'/'mixed'/'unclear' inferred bands never fire.
    if inferred.age_band in _BAND_TO_AGE_RANGE and inferred.age_band != "unspecified":
        i0, i1 = _BAND_TO_AGE_RANGE[inferred.age_band]
        gaps = [_range_gap(i0, i1, d.age_min, d.age_max) for d in declared]
        if gaps and min(gaps) >= _AGE_GROSS_GAP_YEARS:
            axes.append("age")

    if not axes:
        return None

    declared_summary = _summarize_declared(declared)
    message = (
        f"The creative reads as targeting {_summarize_inferred(inferred)}, but "
        f"the declared audience is {declared_summary} (mismatch on "
        f"{', '.join(axes)}). Likely a wrong-creative upload or a "
        f"fundamentally misaimed campaign."
    )
    return DemographicMismatch(
        axes=axes,
        inferred_gender=inferred.gender,
        inferred_age_band=inferred.age_band,
        declared_summary=declared_summary,
        message=message,
    )


def _summarize_declared(declared: list[DemographicPoint]) -> str:
    genders = {d.gender for d in declared}
    if {"any", "unspecified"} & genders or genders == {"male", "female"}:
        g = "all genders"
    elif genders == {"male"}:
        g = "men"
    elif genders == {"female"}:
        g = "women"
    else:
        g = "/".join(sorted(genders))
    lo = min(d.age_min for d in declared)
    hi = max(d.age_max for d in declared)
    return f"{g} aged {lo}-{hi}"


def _summarize_inferred(inferred: InferredAudience) -> str:
    g = _GENDER_WORD.get(inferred.gender)
    a = _AGE_WORD.get(inferred.age_band)
    if g and a:
        return f"{g} aged {a}"
    if g:
        return g
    if a:
        return f"people aged {a}"
    return "an unclear demographic"


# ---- Deterministic declared-vs-apparent PURPOSE check (v2.4) ----
#
# Compares the marketer's DECLARED job (CreativeInputs.purpose) against the job
# the ad APPEARS to do (TargetClassification.inferred_purpose). Pure Python.
# Warn-not-block (softer than the demographic guard — purpose is fuzzier; an ad
# can serve two jobs) but LOUD: it is the load-bearing guardrail for the common
# case where a non-technical marketer leaves purpose on the default (direct-sell)
# and runs an awareness/brand ad the engine would otherwise score on the wrong
# ruler. 'unclear' never fires (conservative, like a 'mixed' demographic).

def detect_purpose_mismatch(
    declared_purpose: str,
    apparent_purpose: str,
    apparent_reasoning: str = "",
) -> PurposeMismatch | None:
    """Return a PurposeMismatch iff the ad's apparent job differs from the
    declared job (and the apparent job is confidently read); else None."""
    apparent = (apparent_purpose or "unclear").strip()
    if apparent in ("unclear", ""):
        return None
    declared = resolve_purpose(declared_purpose)  # validates; default-safe
    if apparent == declared.name:
        return None

    apparent_preset = resolve_purpose(apparent)
    suggested_flag = f"--purpose {apparent}"

    # direct-sell is the strictest ruler ("would they buy this week"), so
    # grading a softer/broader job by it UNDERSTATES the ad — call that out
    # explicitly since direct-sell is the default the common user leaves on.
    if declared.name == DIRECT_SELL:
        directional = (
            f"A direct-sell grade asks 'would the target buy this week' — the "
            f"wrong question for a {apparent_preset.label.lower()} ad, so the "
            f"result will likely UNDERSTATE it."
        )
    else:
        directional = (
            f"{apparent_preset.label} and {declared.label} ads are measured by "
            f"different rulers, so the grade may misjudge this ad."
        )

    message = (
        f"This ad reads as a {apparent_preset.label.upper()} ad, but you're "
        f"grading it as {declared.label.upper()}. {directional} "
        f"To grade it against its apparent job, re-run with {suggested_flag}."
    )
    if apparent_reasoning.strip():
        message += f"  (Why it reads that way: {apparent_reasoning.strip()})"

    return PurposeMismatch(
        declared_purpose=declared.name,
        apparent_purpose=apparent,
        declared_label=declared.label,
        apparent_label=apparent_preset.label,
        suggested_flag=suggested_flag,
        message=message,
    )


# ---- Coverage guard (rocket-2.1.0) — sibling of the mismatch guard ----

_MIN_ELIGIBLE_PERSONAS = 2  # below this, the declared slice has too few personas


def detect_thin_coverage(
    spec: AudienceSpec,
    dispositions: list[NamedDisposition],
) -> CoverageWarning | None:
    """Return a CoverageWarning iff the declared audience intersects too few
    library personas to compose a diverse marketer-led panel. Advisory (never
    blocks); doubles as the white-glove authoring signal for that slice."""
    from agent.panel import eligible_dispositions  # local: avoid import cycle

    eligible = eligible_dispositions(spec, dispositions)
    labels = [d.label for d, _ in eligible]
    if len(eligible) >= _MIN_ELIGIBLE_PERSONAS:
        return None

    declared = _summarize_declared(spec.demographics)
    if not eligible:
        message = (
            f"No library persona lives in the declared audience ({declared}). "
            f"The panel falls back to all dispositions at the declared "
            f"demographics — author personas for this slice before trusting "
            f"the read."
        )
    else:
        message = (
            f"Only 1 library persona ({labels[0]}) lives in the declared "
            f"audience ({declared}); the panel has no attitudinal diversity. "
            f"Author more personas for this slice."
        )
    return CoverageWarning(
        eligible_count=len(eligible),
        total_count=len(dispositions),
        eligible_labels=labels,
        message=message,
    )


def build_audience_match(
    declared: list[DemographicPoint],
    inferred: InferredAudience,
):
    """Promote the pre-run mismatch guard to the first-class audience-match
    axis: 'aligned' when the ad's apparent target is consistent with the
    declared buy, 'mismatched' on a gross gap (remedy = targeting, not the
    creative). Returns a schema.AudienceMatch."""
    from agent.schema import AudienceMatch  # local: schema is a leaf module

    declared_summary = _summarize_declared(declared)
    inferred_summary = _summarize_inferred(inferred)
    mm = detect_gross_demographic_mismatch(declared, inferred)
    if mm is None:
        return AudienceMatch(
            verdict="aligned",
            declared_summary=declared_summary,
            inferred_summary=inferred_summary,
            axes=[],
            message=(
                f"The creative's apparent target ({inferred_summary}) is "
                f"consistent with the declared audience ({declared_summary})."
            ),
        )
    return AudienceMatch(
        verdict="mismatched",
        declared_summary=declared_summary,
        inferred_summary=inferred_summary,
        axes=mm.axes,
        message=mm.message,
    )
