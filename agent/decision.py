"""rocket-2.3.0 — the decision layer.

Splits DIAGNOSIS from DECISION. The categorical verdict (WORKING/MIXED/
FAILING/METHODOLOGY_GAP) stays but becomes an internal clinical read; the
brand manager reads a DECISION — SCALE / ITERATE / RETARGET / REBUILD /
INCONCLUSIVE — plus the one number that matters (the within-target action
rate) and a plain-language trust line.

Everything here is DETERMINISTIC Python over signals the assess pass already
produced. The model emits no decision; `resolve_decision` is a pure function
of extracted scalars/enums, mirroring `resolve_verdict`. See
docs/v2_3_decision_layer.md.

The SCALE branch is deliberately GATED (§7 of the spec): we have zero
upper-anchor observations (0/42 runs read WORKING), so `resolve_decision`
cannot emit SCALE — it fails safe to ITERATE — until a deliberately-strong
anchor run sets the threshold (P4). validate_report enforces the invariant.
"""

from __future__ import annotations

from agent.schema import (
    AgentTranscript,
    AudienceMatch,
    Decision,
    Pain,
)
from agent.synthesis_l2 import compute_behavioral_distribution
from agent.synthesis_types import TargetClassification

# Bump on any change to the decision logic so the calibration log can separate
# pre/post regimes (stamped into run.json).
#   decision-1 — the original locked decision function (P1-P3; SCALE gated).
DECISION_VERSION = "decision-1"

# Funnel-stage precedence for the load-bearing within-target pain. The earliest
# stage a within-target pain bites gates everything downstream, so it — not the
# most-cited pain — carries the ITERATE-vs-REBUILD severity. (Most-cited breaks
# on ProSki, whose most-cited within pain is a downstream execution pain while
# the real wall is a structural attention-stage pain. See docs/v2_3 §Design.)
_FUNNEL_STAGE_ORDER = {
    "attention": 0,
    "comprehension": 1,
    "consideration": 2,
    "conversion": 3,
    "recall": 4,
}

# RETARGET step-2 thresholds: a non-within disposition must beat the within-
# target action rate by >= _RETARGET_GAP AND clear _RETARGET_FLOOR in absolute
# terms before we call "right ad, wrong person". Anchored to fire on TWT (a
# 32%-vs-0% champion gap) and NOT on ProSki (a 5% champion below its 9% within
# rate). Four-point-thin — documented as such; the direction fails safe (a miss
# falls through to the severity read, never fabricates a RETARGET).
_RETARGET_GAP = 0.15
_RETARGET_FLOOR = 0.20

# methodology_flags that mean the read rests on thin/instrumentally-weak
# evidence -> trust is DIRECTIONAL regardless of how vivid the reactions read.
_THIN_EVIDENCE_FLAGS = {
    "single_within_target",
    "no_within_target_evidence",
    "target_unsignaled",
    "pool_archetype_mismatch",
}


# ---- Signals (pure, offline) ----


def within_target_action_rate(
    transcripts: list[AgentTranscript],
    target_classification: TargetClassification,
) -> tuple[float | None, int, int]:
    """The headline metric: of agents whose disposition is classified `within`,
    the fraction with would_act_within_week == True. Returns (rate, num, denom)
    where rate is 0-1, or (None, 0, 0) when no within-target agent has a parsed
    signal (0/0 — never divide by zero). Denominator counts only parsed signals
    (reuses compute_behavioral_distribution, so it stays consistent with the
    funnel layer)."""
    within = set(target_classification.within_target_labels())
    subset = [t for t in transcripts if t.disposition_label in within]
    dist = compute_behavioral_distribution(subset)
    if dist.n == 0:
        return None, 0, 0
    return dist.would_act_within_week_count / dist.n, dist.would_act_within_week_count, dist.n


def action_by_disposition(
    transcripts: list[AgentTranscript],
) -> dict[str, tuple[float, int, int]]:
    """Per-disposition would-act rate -> {label: (rate, num, denom)}. Used to
    detect a champion (an outside/ambiguous disposition that acts materially
    more than the target) and to name who a RETARGET creative resonates with."""
    by_label: dict[str, list[AgentTranscript]] = {}
    for t in transcripts:
        by_label.setdefault(t.disposition_label, []).append(t)
    out: dict[str, tuple[float, int, int]] = {}
    for label, ts in by_label.items():
        dist = compute_behavioral_distribution(ts)
        rate = dist.would_act_within_week_count / dist.n if dist.n else 0.0
        out[label] = (rate, dist.would_act_within_week_count, dist.n)
    return out


def load_bearing_within_pain(pain_map: list[Pain]) -> Pain | None:
    """The within-target pain that carries the decision: the one at the earliest
    funnel stage (it gates everything after it), tie-broken by citation breadth,
    then id for determinism. Its severity drives ITERATE (execution) vs REBUILD
    (structural). None when there is no within-target pain."""
    within = [p for p in pain_map if p.within_target]
    if not within:
        return None
    return min(
        within,
        key=lambda p: (
            _FUNNEL_STAGE_ORDER.get(p.funnel_stage, 99),
            -len(p.cited_by),
            p.id,
        ),
    )


# ---- The decision function (pure, deterministic, first-match) ----


def _trust(within_labels: list[str], flags: list[str]) -> str:
    """HIGH only when the read rests on >= 2 within-target dispositions with no
    thin-evidence flag; otherwise DIRECTIONAL ('treat as a lead, not a verdict')."""
    if len(within_labels) >= 2 and not (_THIN_EVIDENCE_FLAGS & set(flags)):
        return "HIGH"
    return "DIRECTIONAL"


def _best_champion(
    action_by_disp: dict[str, tuple[float, int, int]],
    classification_map: dict[str, str],
) -> tuple[str, float] | None:
    """The non-within disposition with the highest action rate (the audience the
    ad may actually be FOR). None when there is no outside/ambiguous disposition
    with a parsed signal."""
    candidates = [
        (label, rate)
        for label, (rate, _num, denom) in action_by_disp.items()
        if denom > 0 and classification_map.get(label) != "within"
    ]
    if not candidates:
        return None
    # Highest action rate; tie-break by name so a RETARGET's named champion is
    # deterministic across runs (dict/transcript order must not decide it).
    return sorted(candidates, key=lambda x: (-x[1], x[0]))[0]


def resolve_decision(
    a_within: float | None,
    action_by_disp: dict[str, tuple[float, int, int]],
    classification_map: dict[str, str],
    within_labels: list[str],
    load_bearing_pain: Pain | None,
    audience_match_verdict: str | None,
    verdict: str,
    methodology_flags: list[str],
) -> Decision:
    """Map already-computed signals to a brand-facing DECISION. Deterministic,
    first-match, severity + disposition-gap driven — A_within is the headline
    number, NOT a magnitude gate (that is what keeps this from overfitting the
    four calibration anchors). SCALE is unreachable here (gated, v2.3 P4): the
    logic falls through to ITERATE rather than ever emitting it.

        0. METHODOLOGY_GAP                               -> INCONCLUSIVE
        1. audience_match == mismatched                  -> RETARGET
        2. a non-within champion beats A_within by >=G   -> RETARGET
           and clears the absolute floor F
        3. no within-target evidence at all              -> INCONCLUSIVE
        4. load-bearing within pain is STRUCTURAL        -> REBUILD
        5. else (execution / fixable)                    -> ITERATE
    """
    trust = _trust(within_labels, methodology_flags)
    champion = _best_champion(action_by_disp, classification_map)
    lb_id = load_bearing_pain.id if load_bearing_pain is not None else ""

    def make(decision: str, rationale: str, *, use_champion: bool = False) -> Decision:
        return Decision(
            decision=decision,
            target_action_rate=a_within,
            trust=trust,
            within_dispositions=list(within_labels),
            champion_disposition=(champion[0] if (use_champion and champion) else ""),
            champion_action_rate=(champion[1] if (use_champion and champion) else None),
            load_bearing_pain_id=lb_id,
            rationale=rationale,
        )

    # 0. Untrustworthy read — pool mismatch or all-ambiguous target.
    if verdict == "METHODOLOGY_GAP":
        return make("INCONCLUSIVE", "verdict is METHODOLOGY_GAP (data quality)")

    # 1. Declared audience grossly disjoint from the ad's apparent target.
    if audience_match_verdict == "mismatched":
        return make("RETARGET", "declared audience mismatched to the ad", use_champion=True)

    # 2. Disposition-level mis-aim: someone the ad ISN'T aimed at acts materially
    #    more than the target (the TWT case — right ad, wrong person).
    base = a_within if a_within is not None else 0.0
    if (
        champion is not None
        and champion[1] >= base + _RETARGET_GAP
        and champion[1] >= _RETARGET_FLOOR
    ):
        return make(
            "RETARGET",
            f"champion {champion[0]} acts at {champion[1]:.0%} vs within {base:.0%}",
            use_champion=True,
        )

    # 3. No within-target evidence at all — the verdict rests on outside reactions.
    if not within_labels or a_within is None:
        return make("INCONCLUSIVE", "no within-target evidence to decide on")

    # 4. The load-bearing within-target block is structural — no in-scope lever
    #    fixes it. (If there is no diagnosed within pain, treat as fixable.)
    if load_bearing_pain is not None and load_bearing_pain.severity == "structural":
        return make("REBUILD", f"load-bearing within pain {lb_id} is structural")

    # 5. The block is execution-level — a specific in-scope lever is leaking.
    return make("ITERATE", f"load-bearing within pain {lb_id or '(none)'} is fixable")


def build_decision(
    transcripts: list[AgentTranscript],
    target_classification: TargetClassification,
    audience_match: AudienceMatch | None,
    verdict: str,
    methodology_flags: list[str],
    pain_map: list[Pain],
) -> Decision:
    """Extract the signals from the raw run artifacts and resolve the decision.
    The single orchestrator called from synthesize_report; keeps
    resolve_decision a pure function of scalars for cheap fixture testing."""
    classification_map = {
        d.disposition_label: d.classification
        for d in target_classification.disposition_classifications
    }
    within_labels = target_classification.within_target_labels()
    a_within, num, denom = within_target_action_rate(transcripts, target_classification)
    action_by_disp = action_by_disposition(transcripts)
    load_bearing = load_bearing_within_pain(pain_map)
    am_verdict = audience_match.verdict if audience_match is not None else None
    decision = resolve_decision(
        a_within,
        action_by_disp,
        classification_map,
        within_labels,
        load_bearing,
        am_verdict,
        verdict,
        methodology_flags,
    )
    # Enrich with the raw counts behind A_within (for an honest render); the
    # decision itself never depends on them.
    decision.target_action_num = num
    decision.target_action_denom = denom
    return decision
