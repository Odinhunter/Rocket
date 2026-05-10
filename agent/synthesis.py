"""Population-level synthesis layer.

Takes a population of completed agent runs across two stimuli (focal + anchor)
and produces a structured PopulationReport with three consumer-facing pieces:

- WithinCellDescription: within-cell vs across-cell variance, per round, per
  stimulus. Numeric for R3, categorical for R1, theme-Jaccard for R2/R4/R5/R6.
- ComparativeMetrics: focal vs anchor framed as deltas/ratios; per-round
  comparative narrative for free-text rounds.
- StructuredFindings: consensus, disagreement axes (with the disposition lines
  they split along), outliers (one-of-N statements).

And one QA-facing piece:

- MethodologyDiagnostics: homogenization flags, parse failure rates, dropouts,
  sample-size warnings. Kept separate so the strategist downstream layer never
  has to read diagnostics to do its job.

Above the population layer sits a target-aware strategist pipeline:

- identify_target_audience(): a separate Opus vision call sees the focal +
  anchor images and the run's disposition pool, and classifies each disposition
  as within / outside / ambiguous against the focal ad's inferred target. This
  call deliberately does NOT see population reactions — target is a property
  of the ad, not of who happened to react.
- synthesize_strategic_critique(): the prose memo, with verdict logic
  (WORKING / MIXED / FAILING / methodology pivot) anchored on the within-target
  subset rather than population-wide patterns.

The two are split so a strategist-memo failure preserves the target
classification on the caller's side; persist target_cls before invoking the
memo synthesis.

Implementation strategy
-----------------------
Numeric/categorical (R1, R3): direct stats over scores and category fields,
no LLM. Uses range (max−min within cell), not std-dev — with S=3 std-dev has
~70% relative error and isn't a stable threshold target.

Free-text (R2/R4/R5/R6): one Opus tool-use call per round (4 calls total)
ingesting all outputs and emitting structured JSON via a strict tool schema.
Per-round flat schema is more reliable than one megacall with deeply-nested
JSON.

Free-text variance: Jaccard similarity over LLM-extracted themes. Within-cell
mean Jaccard vs across-cell mean. TODO: embedding-cosine variant on a
separate-from-generation embedder is the principled v2 — sidesteps the
circular concern of asking the same model whose homogenization we're
measuring to judge same-ness.

Homogenization threshold: within-cell metric exceeds across-cell mean + 2σ
of the across-cell distribution (anchored to population baseline; sidesteps
small-S noise on raw within-cell numbers).

Defaults to Opus 4.7 throughout the synthesis stack (per-round, target ID,
strategist memo). R1-R6 elicitation runs on Sonnet 4.6 because consumer
voice doesn't need Opus reasoning, but synthesis is where reasoning quality
matters most.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import anthropic

from agent.runner import RunResult, _image_block
from agent.telemetry import call_with_telemetry


_MODEL = "claude-opus-4-7"
_log = logging.getLogger(__name__)

_R3_DIMENSIONS = ("relevance", "trust", "curiosity", "irritation", "aspiration")
_FREE_TEXT_ROUNDS = (2, 4, 5, 6)
_R1_FIELDS = ("attention", "time", "action", "signal_category")


# ---- Dataclasses ----


@dataclass
class HomogenizationFlag:
    cell: tuple[str, str]
    stimulus: str
    round_num: int
    metric: str
    detail: str


@dataclass
class MethodologyDiagnostics:
    homogenization_flags: list[HomogenizationFlag]
    parse_failure_rate: dict[str, float]
    dropouts: list[dict]
    sample_size_warning: str | None


@dataclass
class WithinCellDescription:
    round_3_per_dimension: dict[str, dict] = field(default_factory=dict)
    round_1_categorical: dict[str, dict] = field(default_factory=dict)
    free_text_jaccard: dict[int, dict] = field(default_factory=dict)


@dataclass
class ComparativeMetrics:
    round_3_deltas: dict[str, dict] = field(default_factory=dict)
    round_1_attention_dist: dict[str, dict] = field(default_factory=dict)
    per_round_narrative: dict[int, str] = field(default_factory=dict)


@dataclass
class Finding:
    statement: str
    support: list[str]
    rounds: list[int]
    stimulus_scope: str  # "focal" | "anchor" | "both"


@dataclass
class DisagreementAxis:
    axis: str
    splits_along: str  # "disposition" | "context" | "stimulus" | "seed" | "other"
    sides: list[dict]


@dataclass
class OutlierFinding:
    agent_id: str
    round_num: int
    stimulus: str
    statement: str
    why_outlier: str


@dataclass
class StructuredFindings:
    consensus: list[Finding] = field(default_factory=list)
    disagreement_axes: list[DisagreementAxis] = field(default_factory=list)
    outliers: list[OutlierFinding] = field(default_factory=list)


@dataclass
class PopulationReport:
    diagnostics: MethodologyDiagnostics
    within_cell: WithinCellDescription
    comparative: ComparativeMetrics
    findings: StructuredFindings
    # Carried so the downstream strategist layer can quote consumers verbatim
    # and attribute by disposition. Without these, synthesize_strategic_critique
    # falls back to theme codes — which fails the Bain/Kantar memo bar.
    verbatim_archive: dict[tuple[int, str, int], str] = field(default_factory=dict)
    spec_by_agent: dict[int, dict] = field(default_factory=dict)


# ---- Strategist critique ----


@dataclass
class DispositionTarget:
    """Per-disposition classification against the focal ad's inferred target."""
    disposition_label: str
    classification: str  # "within" | "outside" | "ambiguous"
    reasoning: str       # specific creative-evidence trace


@dataclass
class TargetClassification:
    """Result of pre-synthesis target identification on the focal ad.

    Produced by a separate Opus call that sees the focal image, anchor image
    (for category context), and disposition descriptions — but no agent
    reactions. Target is a property of the ad, not of who happened to react;
    keeping population data out of this call prevents the model from
    rationalizing target to fit who responded.
    """
    inferred_target_description: str
    target_reasoning: str
    disposition_classifications: list[DispositionTarget]
    ambiguity_note: str | None = None
    no_match_note: str | None = None


@dataclass
class StrategicCritique:
    """Single prose memo produced by the strategist synthesis layer.

    The four coverage requirements (headline finding, deeper misunderstanding,
    single most important change, confidence framing) are woven into 4-6
    paragraphs of prose, not split into separate fields. Splitting them would
    fragment the connective tissue that makes the memo read like a strategist
    rather than a data dump.

    `target_classification` is produced by a pre-synthesis target identification
    pass. Carried on the critique so the user can audit the classification
    independent of the prose verdict.

    `verdict_band` is the structured-field equivalent of the verdict committed
    in the opening paragraph: WORKING / MIXED / FAILING / METHODOLOGY_GAP.
    None when the strategist API call failed (infrastructure failure is
    distinct from the methodology-gap finding — downstream tooling can
    `if critique.verdict_band:` to detect this case).
    """
    memo: str
    model: str
    target_classification: TargetClassification | None = None
    verdict_band: str | None = None


_VALID_VERDICT_BANDS = {"WORKING", "MIXED", "FAILING", "METHODOLOGY_GAP"}


_STRATEGIST_TOOL_SCHEMA = {
    "name": "report_strategist_verdict",
    "description": (
        "Report the strategist verdict band and full prose memo. The "
        "verdict_band MUST match the verdict committed in the opening "
        "paragraph of the memo prose — these two fields cannot disagree."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict_band": {
                "type": "string",
                "enum": ["WORKING", "MIXED", "FAILING", "METHODOLOGY_GAP"],
                "description": (
                    "WORKING: within-target dispositions show no broad "
                    "negative consensus, no structural damage. MIXED: "
                    "within-target shows real trade-offs but no fundamental "
                    "damage; recommendation is friction resolution. FAILING: "
                    "within-target shows structural damage to trust / brand "
                    "permission / category fit. METHODOLOGY_GAP: no "
                    "dispositions match inferred target, or all are "
                    "ambiguous — pivot to methodology paragraph."
                ),
            },
            "memo": {
                "type": "string",
                "description": (
                    "4-6 paragraphs of flowing prose. No headers, no bullets, "
                    "no enumerations. Verdict commitment in the opening "
                    "paragraph (woven into prose, not as a label). Quote "
                    "consumers directly with disposition attribution and "
                    "explicit within / outside qualifier the first time each "
                    "disposition is referenced. Match prose strength to "
                    "evidence strength."
                ),
            },
        },
        "required": ["verdict_band", "memo"],
    },
}


# Aligned with _MODEL; kept as a separate constant so the strategist + target-ID
# layer can diverge in future if synthesis-layer reasoning needs ever differ
# from prose-judgment needs. Both currently use Opus 4.7.
_STRATEGIST_MODEL = "claude-opus-4-7"


# ---- Target identification (pre-synthesis) ----


_TARGET_ID_TOOL_SCHEMA = {
    "name": "classify_ad_target",
    "description": (
        "Identify the focal ad's target audience from creative cues alone, "
        "and classify each disposition in the population pool as within, "
        "outside, or ambiguous against that target. The classification must "
        "be evidence-anchored to specific creative elements — visual, copy, "
        "occasion, brand positioning, demographic signals — not vibes."
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
                    "brand positioning cues, demographic signals. Avoid "
                    "vibes ('looks Indian, must be mass-market') — name the "
                    "specific cues."
                ),
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
                        "reasoning": {
                            "type": "string",
                            "description": (
                                "Why this disposition is classified this way. "
                                "Tie to specific elements of the disposition "
                                "description and specific creative cues."
                            ),
                        },
                    },
                    "required": ["disposition_label", "classification", "reasoning"],
                },
            },
            "ambiguity_note": {
                "type": ["string", "null"],
                "description": (
                    "Set if the focal ad's creative does not clearly signal a "
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
        },
        "required": [
            "inferred_target_description",
            "target_reasoning",
            "disposition_classifications",
        ],
    },
}


_TARGET_ID_SYSTEM = """\
You are a senior consumer-research analyst doing target identification on a \
single ad. You will be shown two images: a FOCAL ad and an ANCHOR ad. Your \
job is to identify the target audience of the FOCAL ad only. The anchor is \
provided for category context (so you can calibrate "what does premium look \
like in this category vs mass-market," etc.) — do not classify the anchor's \
target.

You will also be given a list of dispositions describing distinct consumer \
types within a single archetype. For each disposition, classify it as \
within, outside, or ambiguous against the focal ad's inferred target.

# How to read the focal ad

Examine the creative for these specific cues. Every claim about target must \
trace to one or more of these — no vibes, no stereotypes:

- **Visual palette** — colors, lighting, contrast, polish vs grain
- **Models or no models** — if models, their age range, gender, dress, \
demographic and aspirational signals; if none, what that itself says
- **Setting and props** — kitchen vs office vs cafe vs home; festive items, \
furniture tier, location class
- **Copy tone and language register** — English / Hinglish / regional, \
formal / casual / aspirational, claim style (price-led / quality-led / \
emotion-led / occasion-led)
- **Occasion framing** — festive (Diwali, Valentine's, Raksha Bandhan, \
wedding), everyday utility, gifting, indulgence, performance / fitness, \
celebration / ritual
- **Brand positioning cues** — mass-market / premium / D2C-disruptor / \
legacy-incumbent. Look at logo prominence, packaging shown, retail context \
(Flipkart badge → online grocery; standalone → brand-direct), price \
disclosure
- **Demographic signals** — age, income tier, household role, regional / \
cultural context where signaled

# Within / outside / ambiguous

- **within** — the disposition fits the inferred target on the load-bearing \
dimensions (life stage, household role, income tier, attitudinal stance, \
occasion-relevance). Multiple match-points; few or no contradictions.
- **outside** — the disposition fails the target on a load-bearing \
dimension. The household role is wrong, the income tier mismatches, the \
occasion is irrelevant to their life, the attitudinal stance puts them in \
a different segment entirely.
- **ambiguous** — partial match. Some dimensions fit, others don't. Use \
this when the disposition could plausibly be in target depending on \
unspecified context (e.g., D2C-skeptical might be value-conscious-target \
or premium-target-rejector). Don't use ambiguous as a safe default — pick \
within or outside when the evidence supports a clean call.

# Edge cases

- If the creative does not clearly signal a target — generic mass-market \
ad, category-only, multiple competing targets — set `ambiguity_note` and \
classify dispositions liberally as ambiguous. The unsignaled target is \
itself a finding.
- If no dispositions in the pool match the inferred target — e.g., the ad \
targets household buyers and the pool is all young single males — set \
`no_match_note` with the archetype that would fit better. All \
classifications can be "outside" in this case.
- The brand or product positioning may target a wider audience than this \
specific ad does. Classify against this *ad's* target as expressed in the \
creative, not the brand's overall positioning. (Continental's general \
brand reaches all coffee buyers; a specific Continental Diwali-sale ad \
with a 60% off festive frame is targeting a narrower slice.)

# Output

Use the classify_ad_target tool. Be specific. Brand managers will read \
your classification reasoning and judge whether you've called the target \
correctly — vague reasoning ("the visual feels mass-market") will be \
dismissed; specific reasoning ("the Flipkart 'Big Diwali Sale' badge plus \
the 60% off claim plus the festive orange-brown rangoli backdrop signal \
online-grocery festive-stockup, which is a household-buyer occasion") \
holds up.
"""


# Note on belt-and-suspenders prompt restatement:
# Several rules below (verdict-band cross-check, structural-vs-execution
# distinction, single-within caveat, METHODOLOGY_GAP pivot triggers) are
# also restated in the TASK closer assembled by _build_strategist_payload.
# The duplication is intentional: an earlier iteration found the closer
# would override the system prompt when the two diverged. Edit prompt
# rules in BOTH sites in lockstep — do not delete one half thinking it's
# redundant.
_STRATEGIST_SYSTEM = """\
You are a senior consumer research strategist. The audience is a brand team \
that has paid for real strategic insight and will discard another AI-summary \
memo on sight. You write like someone who has lived in the data — confident, \
specific, calibrated, traceable to evidence.

You will receive (a) a TARGET CLASSIFICATION produced by a separate analyst \
who looked at the focal ad's creative cues alone and classified each \
disposition in the population as within, outside, or ambiguous against the \
ad's inferred target, and (b) structured population-research output from a \
multi-agent simulation that ran the same six-round protocol on the focal \
ad and a comparative anchor ad in the same category. The data includes \
comparative numeric deltas (R3 emotional dimensions), attention \
distributions (R1), free-text consensus and disagreement axes, outlier \
verbatims, full per-agent verbatim archives across all six rounds, and \
methodology diagnostics including homogenization flags.

Your output is a single prose memo of 4-6 paragraphs. The shape of the memo \
follows the diagnostic verdict you commit to in the opening paragraph, and \
the verdict is determined by *target-audience effectiveness* — not by \
population-wide pattern.

# How target classification governs the memo

The target classification is authoritative. Apply the framework against the \
classification as given. Within-target reactions are load-bearing for the \
verdict; outside-target reactions are informational context. If the \
classification looks wrong on the population data — e.g., a disposition \
classified outside reads as fully engaged — surface that in confidence \
framing as a flag ("the ad's apparent creative target is X, but Y \
disposition reads as engaged — could indicate wider effective target than \
the ad signals"). Do not redefine target mid-memo.

If `no_match_note` is set or all dispositions are classified outside, \
pivot to a methodology paragraph: this run cannot land an effectiveness \
verdict because the disposition pool tested does not include the ad's \
apparent target audience. The reactions captured are informational about \
cross-segment brand presence; recommend re-test against the archetype \
named in the no_match_note. Set `verdict_band="METHODOLOGY_GAP"`. This \
is itself a useful output — it tells the brand the population was wrong \
for this ad.

If every disposition is classified ambiguous (no within, no outside, no \
no_match_note), the creative does not signal target sharply enough for \
the population pool to be classified clearly. Pivot to a methodology \
paragraph framed as "the ad's target signals are too soft for this \
population to be classified — the creative ambiguity is itself the \
finding." Set `verdict_band="METHODOLOGY_GAP"`. Recommend the brand \
clarify the intended target before a verdict can land.

If only one disposition is classified within target, the verdict lands \
but the opening paragraph MUST contain an explicit confidence caveat \
("the verdict rests on a single within-target disposition; treat with \
appropriate care") and a closing recommendation to re-test with broader \
within-target coverage. Single-within is enough evidence to identify \
direction but not enough to ship the verdict without that caveat.

If `ambiguity_note` is set, flag in confidence framing — the methodology \
cannot land a confident verdict without a clear target. An ad that does \
not signal target *has* a creative problem; that itself is a finding.

# Diagnostic-first structure

Open the memo by committing to one of three verdicts, woven into prose. \
The verdict is not a label or header — it is the orientation of the first \
paragraph. Verdicts are evaluated against the within-target subset of the \
population:

- **WORKING.** Within-target dispositions show no broad negative \
consensus, no structural trust/relevance damage. R6 friction surfaced by \
within-target agents is execution-level (price disclosure, pack size, \
distribution), not positioning-level. Outside-target reactions are not \
damaging the brand for its target.
- **MIXED.** Within-target dispositions show real trade-offs but no \
fundamental damage to the target. Some within-target convert; others \
surface friction worth resolving. The recommendation focuses on within-\
target trade-off resolution — sharpening the claim, fixing the price \
chip, tightening the occasion frame.
- **FAILING.** Within-target dispositions show structural damage to \
trust, brand permission, or category fit. Outside-target reactions are \
informational, not verdict drivers. Even one within-target structural \
rejection tips FAILING if the rejection is on grounds the brand cannot \
easily address.

# The structural / execution distinction (this is the calibration mechanism)

This is how you tell creative failure from execution friction. Read it \
carefully and apply it strictly.

- **Structural** = damage that persists after the obvious fix. \
MRP-inflation suspicion remains even after the price is shown. \
"Cannes-intern framing" reads as out-of-touch even after copy edits. \
The brand-product gap persists even after positioning tweaks. The \
disposition's distrust isn't about a missing detail — it's about what \
the ad reveals about how the brand is thinking.
- **Execution-level** = friction the obvious fix removes. Missing price \
chip → add the price. Unclear pack size → add the gram count. Discount \
asterisk → spell out the base. The disposition would buy if the missing \
piece were filled in.
- **If you cannot tell which, that's MIXED, not FAILING.** Don't pick \
FAILING as a safe rhetorical default; the verdict comes from the \
durability of the damage.

# The counterweight rule (don't over-fire on FAILING)

Within-target rejection on concrete-resolvable grounds — price chip, \
pack size, claim specificity, discount-anchor disclosure — does not tip \
FAILING even if multiple within-target agents flag it. Those are MIXED \
with a clear recommendation. The asymmetry: structural damage is rare \
but decisive; execution friction is common and recoverable. Both halves \
hold.

# Body shape per verdict

- **If WORKING:** what's working for the within-target dispositions, \
the evidence that says so, what specific creative or strategic choice is \
doing the work, what trade-offs the brand has accepted that are worth \
keeping. Outside-target reactions appear as informational footnote — \
"the specialty enthusiast, outside target, found the festive frame off-\
key; this is informational about brand-extension headwinds, not a \
verdict driver." The recommendation may be "protect X, change nothing" \
or "the next conversation is about reach, not creative."
- **If MIXED:** where the within-target lands, where it doesn't, the \
trade-off the brand is implicitly making, the conditional \
recommendation. Outside-target reactions appear as context, not as the \
core split. Distinguish the trade-off from the targeting: a trade-off \
within a coherent target audience is MIXED-with-resolvable-friction; a \
split between within and outside dispositions is targeting truth, not \
a memo on the creative.
- **If FAILING:** the structural damage to within-target trust or \
permission, the deeper misunderstanding the brand likely doesn't see \
from inside, the single most important change. The "remove X because N \
of M within-target agents independently flagged it on grounds Y, and \
the comparative shows this hurts focal more than anchor" template \
applies — but only when N is within-target and Y is structural.

Throughout, mark which claims are well-grounded versus tentative. \
Single-disposition support, partial target coverage, homogenization \
flags, weak comparative signal — surface all of these as confidence \
caveats inline.

# Examples of each verdict mode

**WORKING (illustrative):** "On the within-target dispositions this ad \
does what it's asking to do. The two within-target agents — the everyday-\
utility buyer and the brand-loyal repeat purchaser — both score focal \
relevance at or above 7 and surface no trust friction; their R6 \
friction is execution-level (the unclear pack size, the half-shown \
distribution channel) and would be removed by a single creative tweak. \
The single ambiguous disposition (value-skeptical scroller) lands neutral \
rather than negative. The two outside-target dispositions produce \
irritation, but they are reading the ad as cross-segment exposure — \
their reactions are informational about brand-extension headwinds, not \
verdict drivers. What's worth protecting is the deliberate absence of a \
celebrity face: the everyday-utility buyer surfaced it in R5 as the \
reason he'd take the brand seriously, and the loyal repeater echoed the \
read by R4. The brand should resist the urge to retouch this; the next \
conversation is about reach, not creative."

**MIXED (illustrative):** "Within the gifting-occasion target this ad \
works as designed but ships with friction the brand can resolve. Both \
within-target dispositions — the relationship-buyer and the romantic-\
gifter — convert on R6, with focal trust beating anchor by 1.1 across \
the within-target subset. But both also flag the same execution problem: \
the price tier is implied through visual cues rather than stated, which \
leaves the relationship-buyer 'doing math I don't want to do' and the \
romantic-gifter unsure whether the SKU on screen is the ₹400 or the \
₹1200 box. This is concrete-resolvable, not structural — the obvious fix \
removes the friction, and these two dispositions become unblocked \
buyers. The two outside-target dispositions (single observer, foreign-\
chocolate snob) produce irritation rather than rejection, and their \
reads are informational ('the pyramid is more wedding-table than gift-\
shop' is a useful brand cue, not a verdict input). The single most \
important change is the price tier disclosure within the within-target \
frame; protect everything else."

**FAILING (illustrative):** "Within the value-conscious-household target \
this ad does structural damage to brand trust. The two within-target \
dispositions — the everyday-grocery-buyer and the value-skeptical \
household — independently surface MRP-inflation suspicion as the read \
they take away from the '60% off*' claim with no anchor price visible. \
This is not the missing-price-chip kind of friction that fixing the on-\
ad disclosure would remove; it's a brand-trust read on the discount \
mechanic itself. The everyday-grocery-buyer put it bluntly: 'this is the \
inflated-MRP game, the asterisk tells me everything I need to know about \
how this brand thinks about my intelligence.' The value-skeptical \
household echoed it independently and refused to convert on R6. Adding a \
landing price would not undo the read; the read *is* the discount \
mechanic. The deeper misunderstanding is that the brand has confused \
attention-grabbing with conversion-ready, and the within-target \
audience reads the asterisk as evidence the brand isn't on their side. \
The single most important change is to lead with the actual price, drop \
the percentage entirely, and let the rupee number do the work."

**SINGLE-WITHIN MIXED (illustrative; weak-evidence caveat):** "On the \
single within-target disposition this run captured this ad reads MIXED \
— the verdict rests on one voice, treat with appropriate care. The \
within-target everyday-utility buyer engages the format claim and \
scores focal relevance at 7, but flags that the discount math doesn't \
clear in his head ('I'd have to do the per-cup before I'd believe \
this'). That's execution-level friction, not structural damage; \
resolvable with a price-per-cup chip. The four outside-target \
dispositions react with various flavors of category-irritation that \
are informational about cross-segment brand presence, not verdict \
input. Because only one within-target disposition supports the read, \
the next conversation should be a re-test against a broader within-\
target sample — confirming the price-math friction surfaces in two or \
three more value-conscious profiles before treating the recommendation \
as load-bearing."

**METHODOLOGY_GAP (illustrative; all-ambiguous case):** "The creative \
does not signal target sharply enough for this disposition pool to \
land an effectiveness verdict. Every disposition the run tested came \
back ambiguous against the inferred target — not because the pool \
mismatches the ad, but because the ad itself is hedging across two \
targets that don't share creative signals. The reactions captured are \
informational about how each disposition tries (and fails) to map the \
ad to itself, but the verdict cannot run without a clear target the \
ad is committed to. The recommendation is for the brand: pick the \
target the ad is for, sharpen the creative against that target's \
signals, and re-test against a within-target pool. The current \
ambiguity is the finding."

# Voice and format rules — non-negotiable

- Quote agent verbatims directly with disposition attribution. Write 'the \
within-target everyday-utility buyer put it bluntly: "X"' or 'the \
outside-target snob said: "Y"'. Brand managers care which kind of \
consumer said what — disposition is the load-bearing attribution, not \
agent ID. Within / outside qualifier is mandatory the first time a \
disposition is referenced.
- Reference comparative metrics in context where they support a point \
(e.g. "trails the anchor by 1.4 on relevance among within-target \
agents"). Never list them as a table. Never enumerate scores in a row.
- 4-6 paragraphs of flowing prose. No headers. No bullets. No section \
labels. No "Finding 1 / Finding 2." No "In conclusion" or "In summary." \
The verdict commitment is part of the prose, not a label.
- No generic strategy advice. No "the brand should consider X." No \
"messaging needs to be sharpened." No "leverage the strength." Every \
sentence specific to this ad in this category, traceable to evidence in \
the data.
- No McKinsey-deck mannerisms — strike "compelling," "robust," \
"leverage," "double-click," "unpack," "synergy," "go-to-market," "white \
space."
- **Match prose strength to evidence strength.** Reserve language like \
"actively counterproductive," "fundamentally broken," "structural \
failure," "wrong frame," "category violation" for the FAILING band — \
when within-target dispositions show structural damage. Outside-target \
irritation does not justify this language. A 6/10 irritation score \
among outside-target dispositions is "informational about brand-\
extension headwinds," not "actively counterproductive." Use the \
strongest language the within-target evidence actually supports — and \
no stronger.
- **Permission to under-recommend.** A WORKING verdict may end with \
"protect X, change nothing" or "the question is reach, not creative." Do \
not invent friction to justify a recommendation. Critique that the \
within-target evidence does not support is the failure mode that \
invalidates the memo on first read.
- **Targeting truth is not creative failure.** A clean within-target / \
outside-target split is *targeting evidence*, not a memo on the creative. \
If outside-target dispositions reject the ad and within-target accept it, \
the ad is doing its job; the friction is in the architecture's mismatch \
between target and pool, not in the creative.
- Confident but not overclaiming. If only 1 of 2 within-target \
dispositions support a point, say so in the same sentence that \
introduces it. Partial target coverage is a confidence caveat that \
should appear in the opening paragraph if the within-target sample is 1.
- When data is missing for a (round, stimulus) slice — read the per-\
round completion counts in the diagnostics block — claims about that \
slice must reflect the *completed* agent count, not the population size. \
A sharp brand manager catches loose population claims in 30 seconds and \
uses them to dismiss the rest of the analysis.
- The reader should be able to ask "what supports that?" of any sentence \
and find the answer already embedded in the prose.

# Output format

Use the report_strategist_verdict tool. Two fields:
- `verdict_band`: one of WORKING / MIXED / FAILING / METHODOLOGY_GAP
- `memo`: the 4-6 paragraph prose

**Cross-check before submitting.** The verdict you commit to in the \
opening paragraph of `memo` MUST match `verdict_band`. If your prose \
opens "Within the value-conscious household target this ad does \
structural damage to brand trust" — verdict_band is FAILING. If your \
prose opens "On the within-target dispositions this ad does what it's \
asking to do" — verdict_band is WORKING. If `no_match_note` is set or \
you pivot to a methodology paragraph — verdict_band is METHODOLOGY_GAP. \
The two fields cannot disagree; downstream tooling reads both.
"""


def identify_target_audience(
    report: PopulationReport,
    *,
    focal_label: str,
    anchor_label: str,
    focal_image_path: str,
    anchor_image_path: str,
    category: str,
    archetype: str,
    model: str = _STRATEGIST_MODEL,
) -> TargetClassification:
    """Identify the focal ad's target and classify each disposition against it.

    Vision call. Sees focal image + anchor image (category context) +
    disposition descriptions extracted from `report.spec_by_agent`. Does NOT
    see population reactions — keeping population data out prevents the model
    from rationalizing target to fit who responded.

    Public so callers can persist the classification before invoking the
    strategist memo. If the memo call fails, the classification survives.
    """
    return _identify_ad_target(
        focal_image_path=focal_image_path,
        focal_label=focal_label,
        anchor_image_path=anchor_image_path,
        anchor_label=anchor_label,
        dispositions=_unique_dispositions_from_report(report),
        category=category,
        archetype=archetype,
        model=model,
    )


def synthesize_strategic_critique(
    report: PopulationReport,
    *,
    focal_label: str,
    anchor_label: str,
    category: str,
    target_classification: TargetClassification,
    model: str = _STRATEGIST_MODEL,
) -> StrategicCritique:
    """Produce a strategist memo from a PopulationReport + target classification.

    The target classification is now produced upstream by
    `identify_target_audience` and threaded in. This split makes the target
    classification durable across a strategist-memo failure: if the memo API
    call crashes, the caller still has a TargetClassification to persist.

    Verdict logic is target-effectiveness — within-target reactions are
    load-bearing; outside-target reactions are informational context.

    Verbatim quoting requires report.verbatim_archive and report.spec_by_agent
    populated; synthesize_population_report does this automatically.
    """
    payload = _build_strategist_payload(
        report, focal_label, anchor_label, category, target_classification,
    )

    try:
        client = anthropic.Anthropic(max_retries=5)
        response = call_with_telemetry(
            client,
            layer="strategist",
            model=model,
            max_tokens=2000,
            thinking={"type": "disabled"},
            system=_STRATEGIST_SYSTEM,
            tools=[_STRATEGIST_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "report_strategist_verdict"},
            messages=[{"role": "user", "content": payload}],
        )
    except Exception as exc:
        _log.error("Strategist memo API call failed: %s", exc)
        return StrategicCritique(
            memo=(
                f"(strategist call failed: {type(exc).__name__}: {exc}. "
                "Target classification is preserved on this critique object; "
                "rerun the memo synthesis from the persisted state.)"
            ),
            model=model,
            target_classification=target_classification,
            verdict_band=None,
        )

    memo = ""
    verdict_band: str | None = None
    stop_reason = getattr(response, "stop_reason", None)
    for block in response.content:
        if block.type == "tool_use":
            data = dict(block.input)
            memo = (data.get("memo") or "").strip()
            band = data.get("verdict_band")
            if band in _VALID_VERDICT_BANDS:
                verdict_band = band
            else:
                _log.warning(
                    "Strategist tool returned invalid verdict_band %r; "
                    "leaving verdict_band=None.", band,
                )
            break

    if not memo:
        _log.error(
            "Strategist memo: no tool_use block in response "
            "(stop_reason=%s)", stop_reason,
        )
        memo = (
            f"(strategist call returned no tool_use block; "
            f"stop_reason={stop_reason}. Target classification is preserved; "
            "check for content-filter or max_tokens truncation and rerun.)"
        )

    return StrategicCritique(
        memo=memo,
        model=model,
        target_classification=target_classification,
        verdict_band=verdict_band,
    )


def _unique_dispositions_from_report(report: PopulationReport) -> list[tuple[str, str]]:
    """Extract unique (label, full_text) pairs from the report's spec_by_agent.

    Multiple agents can share a disposition (S>1 within-cell replication).
    Dedupe on label, preserving the first text encountered.
    """
    seen: dict[str, str] = {}
    for spec in report.spec_by_agent.values():
        disp = spec.get("disposition")
        if not disp:
            continue
        label, text = disp[0], disp[1] if len(disp) > 1 else ""
        if label not in seen:
            seen[label] = text
    return list(seen.items())


def _identify_ad_target(
    *,
    focal_image_path: str,
    focal_label: str,
    anchor_image_path: str,
    anchor_label: str,
    dispositions: list[tuple[str, str]],
    category: str,
    archetype: str,
    model: str,
) -> TargetClassification:
    """Classify the focal ad's target audience and each disposition against it.

    Vision call. Sees focal image + anchor image (category context) +
    disposition descriptions. Does NOT see population reactions — keeping
    population data out prevents the model from rationalizing target to fit
    who responded.
    """
    disp_block_lines = [
        f"# Disposition pool tested ({archetype} × {category})",
        "",
        f"This run sampled {len(dispositions)} dispositions from the "
        f"{archetype} archetype's {category} pool. For each, classify within "
        "/ outside / ambiguous against the focal ad's inferred target. Use "
        "the disposition_label string verbatim in your output.",
        "",
    ]
    for label, text in dispositions:
        disp_block_lines.append(f"## {label}")
        disp_block_lines.append(text or "(no description provided)")
        disp_block_lines.append("")
    disp_block = "\n".join(disp_block_lines)

    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"FOCAL ad — classify this ad's target. Label: **{focal_label}**"
            ),
        },
        _image_block(focal_image_path),
        {
            "type": "text",
            "text": (
                f"ANCHOR ad — provided for category context only; do not "
                f"classify the anchor's target. Label: **{anchor_label}**"
            ),
        },
        _image_block(anchor_image_path),
        {"type": "text", "text": disp_block},
        {
            "type": "text",
            "text": (
                "Use the classify_ad_target tool. Every classification must "
                "trace to specific creative cues. Set ambiguity_note if the "
                "focal creative does not signal a clear target. Set "
                "no_match_note if no dispositions match the inferred target, "
                "and name the archetype that would fit better."
            ),
        },
    ]

    client = anthropic.Anthropic(max_retries=5)
    try:
        response = call_with_telemetry(
            client,
            layer="target_id",
            model=model,
            max_tokens=4000,
            thinking={"type": "disabled"},
            system=_TARGET_ID_SYSTEM,
            tools=[_TARGET_ID_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "classify_ad_target"},
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as exc:
        _log.error("Target identification API call failed: %s", exc)
        return _empty_target_classification(dispositions)

    for block in response.content:
        if block.type == "tool_use":
            data = dict(block.input)
            return _build_target_classification(data, dispositions)

    _log.error("Target identification: no tool_use block in response")
    return _empty_target_classification(dispositions)


_VALID_CLASSIFICATIONS = {"within", "outside", "ambiguous"}


def _normalize_label(s: str) -> str:
    """Normalize for fuzzy match: lowercase, hyphen↔underscore folded.

    Used to recover from cases where the model emits a hyphenated variant
    of an underscore-canonical pool label (e.g. office-bru-pragmatist for
    office_bru_pragmatist). Strict-equality is tried first; this is the
    fallback. We do NOT do Levenshtein-style fuzzy matching — silent
    corrections on substantive label drift are worse than dropped entries.
    """
    return s.lower().replace("-", "_")


def _build_target_classification(
    data: dict, pool: list[tuple[str, str]],
) -> TargetClassification:
    """Map raw tool-use JSON into the TargetClassification dataclass.

    Validates emitted disposition_labels against the input pool:
    - Strict-equality match: pass through.
    - Normalized match (case-insensitive, hyphen↔underscore folded):
      replace with canonical pool label, log info.
    - No match: drop the entry, log warn (substantive drift is a
      classification miss, not a typo — better to land short than wrong).

    Invalid classification enums are coerced to "ambiguous" with a warn —
    better to land safely than to crash on an unexpected value.
    """
    canonical_labels = {label for label, _ in pool}
    normalized_to_canonical = {_normalize_label(label): label for label, _ in pool}

    classifications = []
    for item in data.get("disposition_classifications", []):
        emitted_label = item.get("disposition_label", "") or ""

        # Label resolution
        if emitted_label in canonical_labels:
            label = emitted_label
        else:
            normalized = _normalize_label(emitted_label)
            if normalized in normalized_to_canonical:
                canonical = normalized_to_canonical[normalized]
                _log.info(
                    "Target ID emitted non-canonical disposition_label %r; "
                    "normalized to canonical %r.",
                    emitted_label, canonical,
                )
                label = canonical
            else:
                _log.warning(
                    "Target ID emitted disposition_label %r not in input "
                    "pool; dropping entry. Pool: %s",
                    emitted_label, sorted(canonical_labels),
                )
                continue

        # Classification validation
        cls = item.get("classification", "ambiguous")
        if cls not in _VALID_CLASSIFICATIONS:
            _log.warning(
                "Target ID returned invalid classification %r for %r; "
                "coercing to 'ambiguous'.",
                cls, label,
            )
            cls = "ambiguous"

        classifications.append(DispositionTarget(
            disposition_label=label,
            classification=cls,
            reasoning=item.get("reasoning", ""),
        ))

    return TargetClassification(
        inferred_target_description=data.get("inferred_target_description", ""),
        target_reasoning=data.get("target_reasoning", ""),
        disposition_classifications=classifications,
        ambiguity_note=data.get("ambiguity_note"),
        no_match_note=data.get("no_match_note"),
    )


def _empty_target_classification(pool: list[tuple[str, str]]) -> TargetClassification:
    """Fallback when the target ID call fails — synthesis still runs but with
    every disposition flagged ambiguous so the strategist treats them as
    informational rather than load-bearing.
    """
    return TargetClassification(
        inferred_target_description="(target identification call failed; treat all dispositions as ambiguous)",
        target_reasoning="(no target reasoning available — API call did not return a classification)",
        disposition_classifications=[
            DispositionTarget(
                disposition_label=label,
                classification="ambiguous",
                reasoning="(no classification available — fallback to ambiguous)",
            )
            for label, _ in pool
        ],
        ambiguity_note="Target identification failed; verdict should explicitly flag this as a methodology limitation.",
        no_match_note=None,
    )


def _build_strategist_payload(
    report: PopulationReport,
    focal_label: str,
    anchor_label: str,
    category: str,
    target_cls: TargetClassification,
) -> str:
    L: list[str] = []
    L.append(f"# Stimuli ({category})")
    L.append(f"- Focal: **{focal_label}**")
    L.append(f"- Anchor: **{anchor_label}**")
    L.append("")

    # ---- Target classification (load-bearing for verdict logic) ----
    L.append("# TARGET CLASSIFICATION (creative-cue analysis, no population data)")
    L.append("")
    L.append(
        "This classification was produced by a separate analyst pass that "
        "saw the focal ad image, the anchor image (for category context), "
        "and the disposition descriptions — but no agent reactions. It is "
        "authoritative for verdict logic. Apply the framework against it; do "
        "not redefine target mid-memo."
    )
    L.append("")
    L.append(f"**Inferred target:** {target_cls.inferred_target_description}")
    L.append("")
    L.append(f"**Target reasoning:** {target_cls.target_reasoning}")
    L.append("")
    if target_cls.ambiguity_note:
        L.append(f"**Ambiguity flag:** {target_cls.ambiguity_note}")
        L.append("")
    if target_cls.no_match_note:
        L.append(f"**No-match flag:** {target_cls.no_match_note}")
        L.append("")
    L.append("**Per-disposition classification:**")
    for dc in target_cls.disposition_classifications:
        L.append(
            f"- `{dc.disposition_label}` — **{dc.classification}**: "
            f"{dc.reasoning}"
        )
    within = [d.disposition_label for d in target_cls.disposition_classifications if d.classification == "within"]
    outside = [d.disposition_label for d in target_cls.disposition_classifications if d.classification == "outside"]
    ambiguous = [d.disposition_label for d in target_cls.disposition_classifications if d.classification == "ambiguous"]
    L.append("")
    L.append(
        f"**Summary:** {len(within)} within target · {len(outside)} outside · "
        f"{len(ambiguous)} ambiguous"
    )
    if not within and not target_cls.no_match_note:
        L.append(
            "  (No within-target dispositions but no_match_note not set — "
            "treat as methodology-gap case unless the strategist sees clear "
            "evidence of broader effective target.)"
        )
    if ambiguous and not within and not outside and not target_cls.no_match_note:
        L.append(
            "  (Every disposition classified ambiguous — the creative does "
            "not signal target sharply enough for the population to be "
            "classified clearly. Pivot to METHODOLOGY_GAP per the system "
            "prompt's all-ambiguous rule.)"
        )
    if len(within) == 1:
        L.append(
            "  (Only one within-target disposition — the opening paragraph "
            "MUST contain an explicit single-within confidence caveat and a "
            "closing recommendation to re-test with broader within-target "
            "coverage, per the system prompt's weak-evidence rule.)"
        )
    L.append("")

    # ---- Failed rounds (free-text synthesis API failures) ----
    failed_rounds = [
        rnd for rnd in (2, 4, 5, 6)
        if (report.comparative.per_round_narrative.get(rnd, "") or "").startswith(
            "(synthesis call failed)"
        )
    ]
    if failed_rounds:
        L.append("# FAILED ROUNDS")
        L.append(
            "The free-text synthesis Opus call(s) for the following round(s) "
            "did not return — the per-round consensus, disagreement, outlier, "
            "and comparative narrative findings for these rounds are "
            "unavailable. Do NOT cite findings from these rounds; flag in "
            "confidence framing as 'R{n} synthesis unavailable.'"
        )
        for rnd in failed_rounds:
            L.append(f"- R{rnd} synthesis unavailable")
        L.append("")

    L.append("# Population")
    if report.spec_by_agent:
        for aid in sorted(report.spec_by_agent.keys()):
            spec = report.spec_by_agent[aid]
            disp = spec["disposition"][0] if spec.get("disposition") else "?"
            ctx = spec["context"][0] if spec.get("context") else "?"
            L.append(
                f"- agent_{aid:02d}: disposition={disp}, context={ctx}, "
                f"seed_idx={spec.get('seed_idx', '?')}"
            )
    else:
        L.append("(no spec data — disposition attribution will be unavailable)")
    L.append("")

    # ---- R3 comparative deltas ----
    L.append(
        "# R3 Emotional Mapping — Comparative (focal mean vs anchor mean, "
        "1-10 scale)"
    )
    for dim, data in report.comparative.round_3_deltas.items():
        f_mean = data.get("focal_mean")
        a_mean = data.get("anchor_mean")
        d_abs = data.get("delta_abs")
        direction = data.get("direction", "n/a")
        if f_mean is None or a_mean is None:
            L.append(f"- {dim}: insufficient data")
        else:
            L.append(
                f"- {dim}: focal={f_mean:.2f}, anchor={a_mean:.2f}, "
                f"Δ={d_abs:+.2f} ({direction})"
            )
    L.append("")

    # ---- R3 within-cell variance ----
    # Detect S=1 (no replication): every cell has at most 1 agent, so cell_ranges
    # is empty everywhere. In that case within-cell range is structurally 0 and
    # would mislead the strategist into reading "low noise" — suppress and say so.
    has_replication = any(
        len(per_dim.get(stim_id, {}).get("cell_ranges", [])) > 0
        for per_dim in report.within_cell.round_3_per_dimension.values()
        for stim_id in ("focal", "anchor")
    )
    if has_replication:
        L.append("# R3 Within-Cell Variance (range = max − min within a cell)")
        L.append(
            "Low within-cell range = the same disposition×context produces "
            "near-identical scores on replication; high = real noise inside the "
            "cell, treat numeric findings on that dimension with care."
        )
        for dim, per_dim in report.within_cell.round_3_per_dimension.items():
            for stim_id in ("focal", "anchor"):
                data = per_dim.get(stim_id, {})
                wc = data.get("within_cell_mean_range", 0)
                ac = data.get("across_cell_range", 0)
                L.append(
                    f"- {dim} [{stim_id}]: within-cell mean range={wc:.2f}, "
                    f"across-cell range={ac:.2f}"
                )
    else:
        L.append("# R3 Across-Cell Range (no within-cell replication this run)")
        L.append(
            "S=1: only one agent per cell, so within-cell variance is not "
            "measured. Across-cell range below = max − min of the singleton "
            "scores across dispositions; treat it as a spread indicator only, "
            "not a homogenization signal."
        )
        for dim, per_dim in report.within_cell.round_3_per_dimension.items():
            for stim_id in ("focal", "anchor"):
                data = per_dim.get(stim_id, {})
                ac = data.get("across_cell_range", 0)
                L.append(f"- {dim} [{stim_id}]: across-cell range={ac:.2f}")
    L.append("")

    # ---- R1 attention ----
    L.append("# R1 Attention Distribution (population-wide)")
    for stim_id in ("focal", "anchor"):
        dist = report.comparative.round_1_attention_dist.get(stim_id, {})
        if dist:
            dist_str = ", ".join(
                f"{k}={v:.0%}" for k, v in sorted(dist.items(), key=lambda x: -x[1])
            )
            L.append(f"- {stim_id}: {dist_str}")
        else:
            L.append(f"- {stim_id}: (no data)")
    L.append("")

    # ---- Homogenization flags (load-bearing for confidence framing) ----
    L.append("# Methodology Diagnostics — read these before claiming confidence")
    if report.diagnostics.sample_size_warning:
        L.append(f"- ⚠ {report.diagnostics.sample_size_warning}")
    if report.diagnostics.homogenization_flags:
        L.append("- Homogenization flags (model may be giving the same answer "
                 "across cells — interpret findings on these axes cautiously):")
        for f in report.diagnostics.homogenization_flags:
            L.append(
                f"    - [{f.stimulus}] R{f.round_num} {f.metric}: {f.detail}"
            )
    else:
        L.append("- No homogenization flags raised.")

    # Per-(round, stimulus) completion counts. The strategist must use these,
    # not the population size, when characterizing support. Built from
    # verbatim_archive — an entry exists iff that (agent, stim, round) ran.
    n_pop = len(report.spec_by_agent) if report.spec_by_agent else 0
    if n_pop and report.verbatim_archive is not None:
        completion: dict[tuple[int, str], set[int]] = {}
        for (aid, stim, rnd) in report.verbatim_archive.keys():
            completion.setdefault((rnd, stim), set()).add(aid)
        all_agents = set(report.spec_by_agent.keys())
        L.append(
            "- Per-(round, stimulus) completion counts. Use these, NOT the "
            f"population size of {n_pop}, when characterizing how broadly a "
            "finding is supported on a given slice:"
        )
        for stim_id in ("focal", "anchor"):
            for rnd in (1, 2, 3, 4, 5, 6):
                done = completion.get((rnd, stim_id), set())
                missing = sorted(all_agents - done)
                missing_str = (
                    "complete"
                    if not missing
                    else "missing " + ", ".join(f"agent_{a:02d}" for a in missing)
                )
                L.append(
                    f"    - {stim_id} R{rnd}: {len(done)} of {n_pop} ({missing_str})"
                )
    elif report.diagnostics.dropouts:
        L.append(
            f"- Dropouts: {len(report.diagnostics.dropouts)} conversation(s) "
            "did not complete all six rounds (per-round breakdown unavailable)."
        )
    L.append("")

    # ---- Per-round comparative narratives ----
    L.append("# Per-Round Comparative Narrative (focal vs anchor)")
    round_labels = {
        2: "comprehension audit",
        4: "stickiness — recall two days later",
        5: "social calculus — would they share, mention, or post",
        6: "purchase friction — what stands between attention and wallet",
    }
    for round_num in (2, 4, 5, 6):
        narrative = report.comparative.per_round_narrative.get(round_num, "(none)")
        L.append(f"\n**R{round_num} ({round_labels[round_num]}):** {narrative}")
    L.append("")

    # ---- Consensus ----
    L.append(
        "# Consensus Findings (themes appearing in ≥70% of agents on at "
        "least one stimulus)"
    )
    if report.findings.consensus:
        for f in report.findings.consensus:
            r = f.rounds[0] if f.rounds else "?"
            L.append(
                f"- [R{r} / scope={f.stimulus_scope}] {f.statement} "
                f"(supported by {len(f.support)}: {', '.join(f.support)})"
            )
    else:
        L.append("- (no consensus themes surfaced)")
    L.append("")

    # ---- Disagreement axes ----
    L.append(
        "# Disagreement Axes (where the population splits — disposition "
        "splits are the most strategically loaded)"
    )
    if report.findings.disagreement_axes:
        for d in report.findings.disagreement_axes:
            L.append(f"\n**{d.axis}** (splits along: {d.splits_along})")
            for side in d.sides:
                ag_ids = side.get("agent_ids", [])
                ag_with_disp = []
                for aid in ag_ids:
                    spec = report.spec_by_agent.get(aid, {})
                    disp = spec["disposition"][0] if spec.get("disposition") else "?"
                    ag_with_disp.append(f"agent_{aid:02d} ({disp})")
                L.append(
                    f"- [{side.get('label','')}] {side.get('stance','')} — "
                    f"{', '.join(ag_with_disp)}"
                )
    else:
        L.append("- (no disagreement axes surfaced)")
    L.append("")

    # ---- Outliers ----
    L.append(
        "# Outliers (statements made by exactly one agent — minority "
        "voices that consensus would have buried)"
    )
    if report.findings.outliers:
        for o in report.findings.outliers:
            try:
                aid = int(str(o.agent_id).replace("agent_", ""))
            except (ValueError, AttributeError):
                aid = None
            disp = "?"
            if aid is not None:
                spec = report.spec_by_agent.get(aid, {})
                disp = spec["disposition"][0] if spec.get("disposition") else "?"
            L.append(
                f"- agent_{aid:02d} ({disp}) [R{o.round_num}/{o.stimulus}]: "
                f"{o.statement}"
            )
            L.append(f"    ↳ outlier because: {o.why_outlier}")
    else:
        L.append("- (no outliers surfaced)")
    L.append("")

    # ---- Verbatim archive ----
    L.append("# Verbatim Archive — full per-agent per-round responses")
    L.append("")
    L.append(
        "Use these to quote consumers directly. Always attribute by "
        "disposition (not agent_id) in the memo. R3 outputs are JSON with "
        "scores and one-sentence reasons per dimension — quote the reasons, "
        "not the JSON. The [within|outside|ambiguous] tag in each block "
        "header is the target classification — within-target verbatims are "
        "load-bearing for the verdict; outside-target are informational; "
        "ambiguous are supporting context."
    )
    L.append("")

    # Map disposition_label → target classification for header annotation.
    target_status_by_disp = {
        dc.disposition_label: dc.classification
        for dc in target_cls.disposition_classifications
    }

    if report.verbatim_archive and report.spec_by_agent:
        for aid in sorted(report.spec_by_agent.keys()):
            spec = report.spec_by_agent[aid]
            disp = spec["disposition"][0] if spec.get("disposition") else "?"
            ctx = spec["context"][0] if spec.get("context") else "?"
            seed = spec.get("seed_idx", "?")
            target_status = target_status_by_disp.get(disp, "ambiguous")
            for stim_id in ("focal", "anchor"):
                L.append(
                    f"\n## agent_{aid:02d} [{stim_id}] [{target_status}] · "
                    f"disp={disp} · ctx={ctx} · seed_idx={seed}"
                )
                for round_num in (1, 2, 3, 4, 5, 6):
                    output = report.verbatim_archive.get((aid, stim_id, round_num))
                    if output:
                        L.append(f"\n**R{round_num}:** {output}")
    else:
        L.append("(no verbatim archive available)")

    L.append("")
    L.append("---")
    L.append("")
    # Belt-and-suspenders restatement: several rules here (verdict-first,
    # structural-vs-execution, counterweight, verdict_band tool field) are
    # also stated in _STRATEGIST_SYSTEM. Edit BOTH sites in lockstep. An
    # earlier iteration found the TASK closer would override the system
    # prompt when the two diverged.
    L.append("# TASK")
    L.append("")
    L.append(
        f"Write the strategist memo for **{focal_label}** based on the "
        "target classification and population analysis above. Begin by "
        "committing to a verdict — WORKING, MIXED, or FAILING — in the "
        "opening paragraph, woven into prose. The verdict must be evaluated "
        "against the within-target subset, not against the population as a "
        "whole. If `no_match_note` is set or no dispositions are classified "
        "within target, do not force a verdict — pivot to a methodology "
        "paragraph and recommend a re-test against the named archetype.\n\n"
        "Apply the structural-vs-execution distinction strictly: structural "
        "damage persists after the obvious fix (MRP-inflation suspicion, "
        "Cannes-intern read, brand-product gap); execution friction is "
        "removed by the obvious fix (price chip, pack size, claim "
        "specificity). Multiple within-target rejections on concrete-"
        "resolvable grounds do not tip FAILING — those are MIXED with a "
        "clear recommendation. Even one within-target structural rejection "
        "tips FAILING.\n\n"
        "Within-target reactions are load-bearing; outside-target reactions "
        "are informational context. Frame outside-target friction as "
        "informational (e.g., 'the specialty enthusiast, outside target, "
        "also flagged this — informational, not weight on the verdict'). "
        "Match the strength of your prose to the strength of evidence — "
        "reserve sharpest critique language ('actively counterproductive,' "
        "'structural failure,' 'category violation') for evidence-supported "
        "FAILING reads on within-target dispositions, and accept that a "
        "WORKING verdict may end with 'protect X, change nothing.'\n\n"
        "4-6 paragraphs of flowing prose. No headers, no bullets, no "
        "enumerations, no verdict label as a header — commit in the prose "
        "itself. Quote consumers directly with disposition attribution and "
        "an explicit within / outside qualifier the first time each "
        f"disposition is referenced. Every sentence specific to this ad in "
        f"{category}.\n\n"
        "Use the report_strategist_verdict tool. The verdict_band field "
        "MUST match the verdict committed in the opening paragraph of "
        "memo — they cannot disagree. WORKING / MIXED / FAILING / "
        "METHODOLOGY_GAP."
    )

    return "\n".join(L)


# ---- Free-text Opus tool schema ----


_FREE_TEXT_TOOL_SCHEMA = {
    "name": "report_round_synthesis",
    "description": (
        "Report structured synthesis of free-text round outputs across the "
        "population, comparing focal vs anchor stimulus."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "themes_per_agent": {
                "type": "array",
                "description": (
                    "For each (agent_id, stimulus), list 1-3 short hyphen-"
                    "separated theme codes (e.g. 'price-opacity', 'milk-line-"
                    "skepticism', 'brand-trust-spillover'). Same idea = same "
                    "code across agents."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "integer"},
                        "stimulus": {"type": "string", "enum": ["focal", "anchor"]},
                        "themes": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["agent_id", "stimulus", "themes"],
                },
            },
            "consensus": {
                "type": "array",
                "description": (
                    "Themes appearing in >=70% of agents on at least one "
                    "stimulus. Be conservative; weak themes do not belong here."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "support_agent_ids": {"type": "array", "items": {"type": "integer"}},
                        "stimulus_scope": {"type": "string", "enum": ["focal", "anchor", "both"]},
                    },
                    "required": ["statement", "support_agent_ids", "stimulus_scope"],
                },
            },
            "disagreement_axes": {
                "type": "array",
                "description": (
                    "Axes along which the population splits. Tag what it splits "
                    "along: disposition, context, stimulus, seed (within-cell), "
                    "or other. If two seeds within the same cell disagree but "
                    "cells agree, that's 'seed'."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "axis": {"type": "string"},
                        "splits_along": {"type": "string", "enum": ["disposition", "context", "stimulus", "seed", "other"]},
                        "sides": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "agent_ids": {"type": "array", "items": {"type": "integer"}},
                                    "stance": {"type": "string"},
                                },
                                "required": ["label", "agent_ids", "stance"],
                            },
                        },
                    },
                    "required": ["axis", "splits_along", "sides"],
                },
            },
            "outliers": {
                "type": "array",
                "description": (
                    "Statements made by exactly one agent that nobody else made "
                    "(in either stimulus). Be strict — only true one-of-N. If "
                    "none, return empty array."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "integer"},
                        "stimulus": {"type": "string", "enum": ["focal", "anchor"]},
                        "statement": {"type": "string"},
                        "why_outlier": {"type": "string"},
                    },
                    "required": ["agent_id", "stimulus", "statement", "why_outlier"],
                },
            },
            "comparative_narrative": {
                "type": "string",
                "description": (
                    "2-4 sentences. How does the focal ad fare vs the anchor "
                    "on this round's dimension? Stay grounded in the actual "
                    "responses, no marketing fluff."
                ),
            },
        },
        "required": [
            "themes_per_agent", "consensus", "disagreement_axes",
            "outliers", "comparative_narrative",
        ],
    },
}


# ---- Public API ----


def synthesize_population_report(
    histories: dict[tuple[int, str], list[RunResult]],
    failures: dict[tuple[int, str], list[tuple[int, str]]],
    agent_specs: list[dict],
    *,
    model: str = _MODEL,
    focal_label: str = "the focal stimulus",
    anchor_label: str = "the anchor stimulus",
) -> PopulationReport:
    """Produce a PopulationReport from completed agent runs.

    histories: keyed by (agent_id, stim_id), value is list[RunResult] in
        round order. A length-N list means rounds 1..N succeeded.
    failures: same key, value is list of (round_num, error_message).
    agent_specs: list of dicts with agent_id, disposition (label, text),
        context (label, text), seed_idx, cell_key.
    """
    cell_to_agents: dict[tuple[str, str], list[int]] = defaultdict(list)
    for spec in agent_specs:
        cell_to_agents[spec["cell_key"]].append(spec["agent_id"])

    diagnostics = _compute_diagnostics(histories, failures, agent_specs)
    within_cell, num_cat_flags = _compute_within_cell_numeric_categorical(
        histories, agent_specs, cell_to_agents
    )
    diagnostics.homogenization_flags.extend(num_cat_flags)
    comparative = _compute_comparative_numeric(histories, agent_specs)

    free_text_results: dict[int, dict] = {}
    for round_num in _FREE_TEXT_ROUNDS:
        _log.info("Synthesis: Opus call for round %d ...", round_num)
        free_text_results[round_num] = _opus_free_text_synthesis(
            histories, agent_specs, round_num, model,
            focal_label=focal_label, anchor_label=anchor_label,
        )

    for round_num, res in free_text_results.items():
        comparative.per_round_narrative[round_num] = res.get(
            "comparative_narrative", "(no narrative)"
        )
        within_cell.free_text_jaccard[round_num] = _compute_jaccard_from_themes(
            res.get("themes_per_agent", []), agent_specs
        )
        for stim_id, jdata in within_cell.free_text_jaccard[round_num].items():
            if jdata.get("homogenization_flag"):
                diagnostics.homogenization_flags.append(HomogenizationFlag(
                    cell=("ALL_CELLS", ""),
                    stimulus=stim_id,
                    round_num=round_num,
                    metric="free_text_jaccard_excess",
                    detail=(
                        f"Within-cell Jaccard {jdata['within_cell_mean_jaccard']:.2f} "
                        f"exceeds across-cell mean {jdata['across_cell_mean_jaccard']:.2f} "
                        f"by {jdata['excess']:.2f} (>2σ of across-cell distribution)"
                    ),
                ))

    findings = _aggregate_findings(free_text_results)

    verbatim_archive: dict[tuple[int, str, int], str] = {}
    for (aid, stim_id), hist in histories.items():
        for idx, result in enumerate(hist):
            verbatim_archive[(aid, stim_id, idx + 1)] = result.output

    spec_by_agent = {s["agent_id"]: s for s in agent_specs}

    return PopulationReport(
        diagnostics=diagnostics,
        within_cell=within_cell,
        comparative=comparative,
        findings=findings,
        verbatim_archive=verbatim_archive,
        spec_by_agent=spec_by_agent,
    )


# ---- Numeric / categorical computation ----


def _compute_diagnostics(histories, failures, agent_specs):
    parse_failure_rate: dict[str, float] = {}
    for stim in ("focal", "anchor"):
        keys = [k for k in histories.keys() if k[1] == stim]
        n_total = len(keys)
        # An R3 parse failure leaves the conversation at len(hist) == 2 and a
        # failure entry at round 3.
        n_failed_r3 = sum(
            1
            for k in keys
            if len(histories[k]) == 2
            and any(r == 3 for r, _ in failures.get(k, []))
        )
        parse_failure_rate[f"{stim}_round_3"] = (
            n_failed_r3 / n_total if n_total else 0.0
        )

    dropouts = []
    for k, hist in histories.items():
        if len(hist) < 6:
            last_fail = failures.get(k, [(None, "?")])[-1]
            dropouts.append({
                "agent_id": k[0],
                "stim_id": k[1],
                "rounds_completed": len(hist),
                "failed_at_round": last_fail[0],
                "reason": last_fail[1],
            })

    cell_sizes: dict[tuple, int] = defaultdict(int)
    for s in agent_specs:
        cell_sizes[s["cell_key"]] += 1
    sample_size_warning = None
    if cell_sizes:
        min_S = min(cell_sizes.values())
        max_S = max(cell_sizes.values())
        if min_S != max_S:
            sample_size_warning = (
                f"Uneven seeds-per-cell ({min_S}..{max_S}); within-cell variance "
                "estimates are unreliable when cell sizes differ. Audit the spec "
                "build."
            )
        elif min_S < 3:
            sample_size_warning = (
                f"Only {min_S} seed(s) per cell; within-cell variance "
                "estimates are unreliable. Recommend S>=3."
            )

    return MethodologyDiagnostics(
        homogenization_flags=[],
        parse_failure_rate=parse_failure_rate,
        dropouts=dropouts,
        sample_size_warning=sample_size_warning,
    )


def _compute_within_cell_numeric_categorical(histories, agent_specs, cell_to_agents):
    within = WithinCellDescription()
    flags: list[HomogenizationFlag] = []

    # ---- Round 3 numeric ----
    for dim in _R3_DIMENSIONS:
        per_dim = {}
        for stim_id in ("focal", "anchor"):
            cell_ranges = []
            cell_means = []
            singleton_scores = []  # for across-cell range when S=1 makes cell_means empty
            for cell_key, agent_ids in cell_to_agents.items():
                scores = []
                for aid in agent_ids:
                    hist = histories.get((aid, stim_id), [])
                    if len(hist) >= 3 and hist[2].parsed:
                        scores.append(hist[2].parsed[dim]["score"])
                if len(scores) >= 2:
                    rng = max(scores) - min(scores)
                    mean = sum(scores) / len(scores)
                    cell_ranges.append({
                        "cell": cell_key,
                        "scores": scores,
                        "range": rng,
                        "mean": mean,
                    })
                    cell_means.append(mean)
                elif len(scores) == 1:
                    singleton_scores.append(scores[0])

            if len(cell_means) >= 2:
                across_cell_range = max(cell_means) - min(cell_means)
            elif len(singleton_scores) >= 2:
                # S=1 path: each cell is a singleton, treat scores directly as cell points
                across_cell_range = max(singleton_scores) - min(singleton_scores)
            else:
                across_cell_range = 0
            within_cell_mean_range = (
                sum(c["range"] for c in cell_ranges) / len(cell_ranges)
                if cell_ranges else 0
            )
            per_dim[stim_id] = {
                "cell_ranges": cell_ranges,
                "across_cell_range": across_cell_range,
                "within_cell_mean_range": within_cell_mean_range,
            }
            if cell_ranges and all(c["range"] == 0 for c in cell_ranges):
                flags.append(HomogenizationFlag(
                    cell=("ALL_CELLS", ""),
                    stimulus=stim_id,
                    round_num=3,
                    metric=f"R3_{dim}_range",
                    detail=(
                        f"All {len(cell_ranges)} cells gave identical scores "
                        f"on {dim} (within-cell range = 0)"
                    ),
                ))
        within.round_3_per_dimension[dim] = per_dim

    # ---- Round 1 categorical ----
    for field_name in _R1_FIELDS:
        per_field = {}
        for stim_id in ("focal", "anchor"):
            unanimous = 0
            evaluated = 0
            distribution: dict[str, int] = defaultdict(int)
            for cell_key, agent_ids in cell_to_agents.items():
                values = []
                for aid in agent_ids:
                    hist = histories.get((aid, stim_id), [])
                    if hist:
                        v = _extract_r1_field(hist[0], field_name)
                        if v:
                            values.append(v)
                            distribution[v] += 1
                if len(values) >= 2:
                    evaluated += 1
                    if len(set(values)) == 1:
                        unanimous += 1
            unanimity_rate = unanimous / evaluated if evaluated else 0.0
            total = sum(distribution.values())
            dist_pct = (
                {k: v / total for k, v in distribution.items()} if total else {}
            )
            per_field[stim_id] = {
                "unanimity_rate": unanimity_rate,
                "cells_unanimous": unanimous,
                "cells_total": evaluated,
                "distribution": dist_pct,
            }
            # Flag: every cell unanimous AND only one value seen population-wide
            if unanimity_rate == 1.0 and evaluated >= 2 and len(dist_pct) == 1:
                flags.append(HomogenizationFlag(
                    cell=("ALL_CELLS", ""),
                    stimulus=stim_id,
                    round_num=1,
                    metric=f"R1_{field_name}_unanimity",
                    detail=(
                        f"All cells unanimous on {field_name}="
                        f"{list(dist_pct.keys())[0]} — no inter-cell variance"
                    ),
                ))
        within.round_1_categorical[field_name] = per_field

    return within, flags


def _extract_r1_field(round_1_result: RunResult, field_name: str) -> str | None:
    """R1 output looks like:
        attention: pause
        time: 0.5-2s
        action: none
        signal: search — wonder what 5 sachets cost

    For `signal_category`, the field is meaningful only when attention is
    pause / stop / scroll-back — those signals are the constrained enum
    {screenshot, search, group-chat, nothing}. When attention is scroll-
    past, signal is a free-form 1-3 word reason ('boomer brand', 'silk',
    'lover-feeding-lover'); bucketing those alongside the constrained
    enum produces a meaningless distribution. Return None for scroll-past
    so the categorical homogenization check operates only on engaged
    consumers' constrained-enum responses.
    """
    fields: dict[str, str] = {}
    for line in round_1_result.output.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        fields[key.strip().lower()] = val.strip()

    if field_name == "signal_category":
        attention = fields.get("attention", "")
        if attention == "scroll-past":
            return None
        signal = fields.get("signal", "")
        if not signal:
            return None
        first = signal.split("—")[0].strip()
        return first.split()[0] if first else None
    return fields.get(field_name)


def _compute_comparative_numeric(histories, agent_specs):
    comp = ComparativeMetrics()

    for dim in _R3_DIMENSIONS:
        focal_scores, anchor_scores = [], []
        for spec in agent_specs:
            for stim_id, target in (("focal", focal_scores), ("anchor", anchor_scores)):
                hist = histories.get((spec["agent_id"], stim_id), [])
                if len(hist) >= 3 and hist[2].parsed:
                    target.append(hist[2].parsed[dim]["score"])
        f_mean = sum(focal_scores) / len(focal_scores) if focal_scores else None
        a_mean = sum(anchor_scores) / len(anchor_scores) if anchor_scores else None
        delta_abs = (f_mean - a_mean) if (f_mean is not None and a_mean is not None) else None
        delta_pct = (
            (delta_abs / a_mean * 100)
            if (delta_abs is not None and a_mean not in (None, 0)) else None
        )
        if delta_abs is None:
            direction = "n/a"
        elif delta_abs > 0.05:
            direction = "focal_higher"
        elif delta_abs < -0.05:
            direction = "anchor_higher"
        else:
            direction = "tied"
        comp.round_3_deltas[dim] = {
            "focal_mean": f_mean,
            "anchor_mean": a_mean,
            "delta_abs": delta_abs,
            "delta_pct": delta_pct,
            "direction": direction,
        }

    for stim_id in ("focal", "anchor"):
        dist: dict[str, int] = defaultdict(int)
        total = 0
        for spec in agent_specs:
            hist = histories.get((spec["agent_id"], stim_id), [])
            if hist:
                v = _extract_r1_field(hist[0], "attention")
                if v:
                    dist[v] += 1
                    total += 1
        comp.round_1_attention_dist[stim_id] = (
            {k: v / total for k, v in dist.items()} if total else {}
        )

    return comp


# ---- Free-text synthesis (per-round Opus tool-use) ----


def _opus_free_text_synthesis(
    histories, agent_specs, round_num, model,
    *,
    focal_label: str = "the focal stimulus",
    anchor_label: str = "the anchor stimulus",
) -> dict:
    payload_lines = [
        f"# Round {round_num} ({_round_label(round_num)}) outputs",
        "",
        "Each agent has a disposition (category-stance), a context (attention "
        "state), and a seed_idx (replication label within cell). Within-cell "
        "agents share disposition + context; differences should reflect natural "
        "variance, not new persona.",
        "",
        "## Agent specs",
    ]
    for spec in agent_specs:
        payload_lines.append(
            f"  agent {spec['agent_id']:02d}: disposition={spec['disposition'][0]}, "
            f"context={spec['context'][0]}, seed_idx={spec['seed_idx']}"
        )
    payload_lines.append("")
    payload_lines.append(
        f"## Round {round_num} outputs (focal = {focal_label}, "
        f"anchor = {anchor_label})"
    )
    for spec in agent_specs:
        for stim_id in ("focal", "anchor"):
            hist = histories.get((spec["agent_id"], stim_id), [])
            if len(hist) >= round_num:
                payload_lines.append(
                    f"\n### agent {spec['agent_id']:02d} [{stim_id}] "
                    f"[{spec['disposition'][0]}]"
                )
                payload_lines.append(hist[round_num - 1].output)

    payload = "\n".join(payload_lines)

    instructions = (
        f"You are synthesizing population-level signal from a market-research "
        f"protocol. Round {round_num} ({_round_label(round_num)}) outputs are "
        "below.\n\n"
        "Use the report_round_synthesis tool to return structured JSON. "
        "Required:\n\n"
        "1. **themes_per_agent**: For each agent×stimulus, extract 1-3 short "
        "theme codes (lowercase, hyphen-separated, e.g. 'price-opacity'). Same "
        "idea must use the same code across agents.\n"
        "2. **consensus**: Themes appearing in >=70% of agents on at least one "
        "stimulus. Be conservative.\n"
        "3. **disagreement_axes**: Where the population splits. Tag what it "
        "splits along: disposition / context / stimulus / seed / other. If two "
        "seeds within the same cell disagree, that's 'seed'.\n"
        "4. **outliers**: A statement is an outlier ONLY if exactly one agent "
        "says it (in either stimulus) and nobody else does. Be strict.\n"
        "5. **comparative_narrative**: 2-4 sentences. How does focal compare "
        "to anchor on this round's dimension? Ground in the actual responses, "
        "no marketing fluff.\n\n"
        "Be honest where evidence is thin. Don't invent disagreement to "
        "satisfy the schema."
    )

    client = anthropic.Anthropic(max_retries=5)
    try:
        response = call_with_telemetry(
            client,
            layer="per_round_synthesis",
            model=model,
            round_num=round_num,
            max_tokens=4000,
            thinking={"type": "disabled"},
            tools=[_FREE_TEXT_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "report_round_synthesis"},
            messages=[
                {"role": "user", "content": instructions + "\n\n---\n\n" + payload},
            ],
        )
    except Exception as exc:
        _log.error("Round %d synthesis API call failed: %s", round_num, exc)
        return _empty_round_result()

    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)

    _log.error("Round %d synthesis: no tool_use block in response", round_num)
    return _empty_round_result()


def _round_label(round_num: int) -> str:
    return {
        2: "comprehension audit",
        4: "stickiness",
        5: "social calculus",
        6: "purchase friction",
    }.get(round_num, f"round {round_num}")


def _empty_round_result() -> dict:
    return {
        "themes_per_agent": [],
        "consensus": [],
        "disagreement_axes": [],
        "outliers": [],
        "comparative_narrative": "(synthesis call failed)",
    }


def _compute_jaccard_from_themes(themes_per_agent, agent_specs) -> dict[str, dict]:
    """Within-cell mean pairwise Jaccard vs across-cell mean pairwise Jaccard.

    TODO: replace Jaccard with embedding cosine on a separate-from-generation
    embedder; sidesteps the circular concern of asking the same model whose
    homogenization we're measuring to judge same-ness.
    """
    spec_by_id = {s["agent_id"]: s for s in agent_specs}
    by_cell_stim: dict[tuple, list[set]] = defaultdict(list)
    for entry in themes_per_agent:
        spec = spec_by_id.get(entry.get("agent_id"))
        if not spec:
            continue
        themes = set(entry.get("themes", []))
        by_cell_stim[(spec["cell_key"], entry.get("stimulus"))].append(themes)

    out: dict[str, dict] = {}
    for stim_id in ("focal", "anchor"):
        within_jaccards = []
        cell_unions = []
        for (cell_key, stim), theme_lists in by_cell_stim.items():
            if stim != stim_id:
                continue
            if len(theme_lists) >= 2:
                pair_js = []
                for i in range(len(theme_lists)):
                    for j in range(i + 1, len(theme_lists)):
                        pair_js.append(_jaccard(theme_lists[i], theme_lists[j]))
                if pair_js:
                    within_jaccards.append(sum(pair_js) / len(pair_js))
            cell_unions.append(set().union(*theme_lists) if theme_lists else set())

        across_jaccards = []
        for i in range(len(cell_unions)):
            for j in range(i + 1, len(cell_unions)):
                across_jaccards.append(_jaccard(cell_unions[i], cell_unions[j]))

        within_mean = sum(within_jaccards) / len(within_jaccards) if within_jaccards else 0.0
        across_mean = sum(across_jaccards) / len(across_jaccards) if across_jaccards else 0.0
        across_std = statistics.stdev(across_jaccards) if len(across_jaccards) >= 2 else 0.0
        excess = within_mean - across_mean
        # Threshold: excess > max(2σ_across, 0.10) — second floor protects
        # against degenerate σ when across-cell similarity is very tight.
        flag = excess > max(2 * across_std, 0.10)
        out[stim_id] = {
            "within_cell_mean_jaccard": within_mean,
            "across_cell_mean_jaccard": across_mean,
            "across_cell_std": across_std,
            "excess": excess,
            "homogenization_flag": flag,
            "n_cells": len(cell_unions),
        }
    return out


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _aggregate_findings(free_text_results) -> StructuredFindings:
    consensus = []
    disagreement = []
    outliers = []
    for round_num, res in free_text_results.items():
        for item in res.get("consensus", []):
            consensus.append(Finding(
                statement=item["statement"],
                support=[f"agent_{i:02d}" for i in item["support_agent_ids"]],
                rounds=[round_num],
                stimulus_scope=item["stimulus_scope"],
            ))
        for item in res.get("disagreement_axes", []):
            disagreement.append(DisagreementAxis(
                axis=f"R{round_num}: {item['axis']}",
                splits_along=item["splits_along"],
                sides=item["sides"],
            ))
        for item in res.get("outliers", []):
            outliers.append(OutlierFinding(
                agent_id=f"agent_{item['agent_id']:02d}",
                round_num=round_num,
                stimulus=item["stimulus"],
                statement=item["statement"],
                why_outlier=item["why_outlier"],
            ))
    return StructuredFindings(
        consensus=consensus,
        disagreement_axes=disagreement,
        outliers=outliers,
    )


# ---- Formatter ----


def format_target_classification(target_cls: TargetClassification) -> str:
    """Render a TargetClassification as a printable block.

    Used so the user sees the classification independently of the strategist
    memo prose — useful for auditing whether target ID got the target right
    before judging the verdict that flows from it.
    """
    lines = []
    lines.append("=" * 78)
    lines.append("TARGET CLASSIFICATION")
    lines.append("=" * 78)
    lines.append("")
    lines.append(f"Inferred target: {target_cls.inferred_target_description}")
    lines.append("")
    lines.append("Target reasoning:")
    lines.append(f"  {target_cls.target_reasoning}")
    lines.append("")
    if target_cls.ambiguity_note:
        lines.append(f"⚠ Ambiguity flag: {target_cls.ambiguity_note}")
        lines.append("")
    if target_cls.no_match_note:
        lines.append(f"⚠ No-match flag: {target_cls.no_match_note}")
        lines.append("")
    lines.append("Per-disposition classification:")
    for dc in target_cls.disposition_classifications:
        lines.append(f"  [{dc.classification:9s}] {dc.disposition_label}")
        lines.append(f"      ↳ {dc.reasoning}")
    within = sum(1 for d in target_cls.disposition_classifications if d.classification == "within")
    outside = sum(1 for d in target_cls.disposition_classifications if d.classification == "outside")
    ambiguous = sum(1 for d in target_cls.disposition_classifications if d.classification == "ambiguous")
    lines.append("")
    lines.append(f"Summary: {within} within · {outside} outside · {ambiguous} ambiguous")
    return "\n".join(lines)


def format_population_report(report: PopulationReport) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append("POPULATION REPORT")
    lines.append("=" * 78)

    # ---- Diagnostics ----
    lines.append("\n## METHODOLOGY DIAGNOSTICS\n")
    if report.diagnostics.sample_size_warning:
        lines.append(f"⚠ {report.diagnostics.sample_size_warning}")
    lines.append(f"Dropouts: {len(report.diagnostics.dropouts)}")
    for d in report.diagnostics.dropouts:
        lines.append(
            f"  - agent {d['agent_id']:02d} [{d['stim_id']}]: "
            f"{d['rounds_completed']}/6 rounds (failed R{d['failed_at_round']}: {d['reason']})"
        )
    lines.append("Parse failure rate (R3 strict-JSON):")
    for k, v in report.diagnostics.parse_failure_rate.items():
        lines.append(f"  {k}: {v:.0%}")

    if report.diagnostics.homogenization_flags:
        lines.append(f"\nHomogenization flags ({len(report.diagnostics.homogenization_flags)}):")
        for f in report.diagnostics.homogenization_flags:
            cell_str = (
                "ALL CELLS" if f.cell == ("ALL_CELLS", "")
                else "/".join(c for c in f.cell if c)
            )
            lines.append(
                f"  ⚠ [{f.stimulus}] R{f.round_num} {f.metric} ({cell_str})"
            )
            lines.append(f"      ↳ {f.detail}")
    else:
        lines.append("\nNo homogenization flags raised.")

    # ---- Within-cell ----
    lines.append("\n## WITHIN-CELL VARIANCE\n")
    lines.append("### Round 3 numeric (range = max − min within cell, scores 1-10)")
    lines.append("")
    header = f"{'Dimension':<14} {'Stim':<8} {'WC mean range':<16} {'AC range':<12} {'Cells':<6}"
    lines.append(header)
    lines.append("-" * len(header))
    for dim, per_dim in report.within_cell.round_3_per_dimension.items():
        for stim_id in ("focal", "anchor"):
            data = per_dim.get(stim_id, {})
            wc = data.get("within_cell_mean_range", 0)
            ac = data.get("across_cell_range", 0)
            n_cells = len(data.get("cell_ranges", []))
            lines.append(f"{dim:<14} {stim_id:<8} {wc:<16.2f} {ac:<12.2f} {n_cells:<6}")

    lines.append("\n### Round 1 categorical (cell unanimity rate)")
    lines.append("")
    header = f"{'Field':<18} {'Stim':<8} {'Unanimous':<12} {'Distribution'}"
    lines.append(header)
    lines.append("-" * len(header))
    for field_name, per_field in report.within_cell.round_1_categorical.items():
        for stim_id in ("focal", "anchor"):
            data = per_field.get(stim_id, {})
            unan_str = f"{data.get('cells_unanimous', 0)}/{data.get('cells_total', 0)}"
            dist = data.get("distribution", {})
            dist_str = ", ".join(
                f"{k}={v:.0%}" for k, v in sorted(dist.items(), key=lambda x: -x[1])
            )
            lines.append(f"{field_name:<18} {stim_id:<8} {unan_str:<12} {dist_str}")

    lines.append("\n### Free-text Jaccard (within-cell vs across-cell theme overlap)")
    lines.append("")
    header = f"{'Round':<8} {'Stim':<8} {'WC mean':<10} {'AC mean':<10} {'Excess':<10} {'Flag':<6}"
    lines.append(header)
    lines.append("-" * len(header))
    for round_num in _FREE_TEXT_ROUNDS:
        per_round = report.within_cell.free_text_jaccard.get(round_num, {})
        for stim_id in ("focal", "anchor"):
            data = per_round.get(stim_id, {})
            wc = data.get("within_cell_mean_jaccard", 0)
            ac = data.get("across_cell_mean_jaccard", 0)
            ex = data.get("excess", 0)
            flag = "⚠" if data.get("homogenization_flag") else ""
            lines.append(
                f"R{round_num:<7} {stim_id:<8} {wc:<10.3f} {ac:<10.3f} {ex:<10.3f} {flag:<6}"
            )

    # ---- Comparative ----
    lines.append("\n## COMPARATIVE METRICS (focal vs anchor)\n")
    lines.append("### Round 3 score deltas (focal − anchor)")
    lines.append("")
    header = f"{'Dimension':<14} {'Focal':<8} {'Anchor':<8} {'Δ abs':<10} {'Δ %':<10} {'Direction'}"
    lines.append(header)
    lines.append("-" * len(header))
    for dim, data in report.comparative.round_3_deltas.items():
        f_mean = data.get("focal_mean")
        a_mean = data.get("anchor_mean")
        d_abs = data.get("delta_abs")
        d_pct = data.get("delta_pct")
        f_str = f"{f_mean:.2f}" if f_mean is not None else "n/a"
        a_str = f"{a_mean:.2f}" if a_mean is not None else "n/a"
        d_abs_str = f"{d_abs:+.2f}" if d_abs is not None else "n/a"
        d_pct_str = f"{d_pct:+.1f}%" if d_pct is not None else "n/a"
        lines.append(
            f"{dim:<14} {f_str:<8} {a_str:<8} {d_abs_str:<10} {d_pct_str:<10} {data['direction']}"
        )

    lines.append("\n### Round 1 attention distribution (population-wide)")
    lines.append("")
    for stim_id in ("focal", "anchor"):
        dist = report.comparative.round_1_attention_dist.get(stim_id, {})
        dist_str = ", ".join(
            f"{k}={v:.0%}" for k, v in sorted(dist.items(), key=lambda x: -x[1])
        )
        lines.append(f"  {stim_id:<8} {dist_str}")

    lines.append("\n### Per-round comparative narrative")
    for round_num in _FREE_TEXT_ROUNDS:
        narrative = report.comparative.per_round_narrative.get(round_num, "(none)")
        lines.append(f"\n**R{round_num} ({_round_label(round_num)}):**")
        lines.append(narrative)

    # ---- Findings ----
    lines.append("\n\n## STRUCTURED FINDINGS")

    lines.append("\n### CONSENSUS")
    if report.findings.consensus:
        for f in report.findings.consensus:
            scope = f.stimulus_scope
            r = f.rounds[0]
            lines.append(f"  • [R{r}/{scope}] {f.statement}")
            lines.append(f"      ↳ supported by {len(f.support)}: {', '.join(f.support)}")
    else:
        lines.append("  (none surfaced)")

    lines.append("\n### DISAGREEMENT AXES")
    if report.findings.disagreement_axes:
        for d in report.findings.disagreement_axes:
            lines.append(f"  • {d.axis}")
            lines.append(f"      splits along: {d.splits_along}")
            for side in d.sides:
                ag = ", ".join(f"agent_{i:02d}" for i in side.get("agent_ids", []))
                lines.append(f"      [{side.get('label','')}] {side.get('stance','')} ({ag})")
    else:
        lines.append("  (none surfaced)")

    lines.append("\n### OUTLIERS")
    if report.findings.outliers:
        for o in report.findings.outliers:
            lines.append(f"  • {o.agent_id} R{o.round_num} [{o.stimulus}]: {o.statement}")
            lines.append(f"      ↳ outlier because: {o.why_outlier}")
    else:
        lines.append("  (none surfaced)")

    return "\n".join(lines)
