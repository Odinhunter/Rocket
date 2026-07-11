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

The SCALE branch is un-gated with a PROVISIONAL bar (decision-2): we still
have zero empirical upper-anchor runs, so `_SCALE_FLOOR` is a documented
best-guess set from desk research + our own anchor distribution — NOT an
anchor run. It is a KNOWN, ACCEPTED RISK, to be recalibrated after v2.4 locks
(the deliberately-strong anchor run, spec §7 / §7a). The bar is deliberately
conservative: SCALE fails toward ITERATE (a mild understatement) rather than
stamping a mediocre ad SCALE (the costly error). See docs/v2_3_decision_layer.md §7a.
"""

from __future__ import annotations

from agent.purpose import (
    AWARENESS_INFORMER,
    DIRECT_SELL,
    RETAIN_WINBACK,
    PurposePreset,
    resolve_purpose,
)
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
#   decision-2 — SCALE un-gated behind a PROVISIONAL desk-research bar
#                (_SCALE_FLOOR); a documented best-guess, not an anchor run.
#                KNOWN RISK — recalibrate after v2.4 locks (spec §7a).
DECISION_VERSION = "decision-2"

# ---- The provisional SCALE bar (KNOWN RISK — recalibrate post-v2.4) ----
#
# SCALE is a COMPOSITE call: the within target must act at/above this floor AND
# the assess pass must leave no in-target lever (no within-target pain survives
# to the SCALE branch). The composite does the real discrimination — the floor
# is only a magnitude backstop against a clean-but-weak read slipping through.
#
# The floor is a DOCUMENTED BEST-GUESS, not an empirical anchor run — we still
# have 0/42 upper-anchor observations. It is set from:
#   - our own distribution: the best *flawed* anchor (MB whey) tops out at 68%
#     within-target action WITH three fixable execution pains, so a clean SCALE
#     ad must clear it with margin;
#   - copy-testing norms (top-2-box >40% = "strong consideration"), scaled UP
#     because our metric is (a) filtered to the target persona, not a general
#     sample, and (b) a simulated top-box, which overstates real behaviour
#     (~63% of "definitely would buy" actually convert). Both push the bar high.
# Direction is deliberately conservative: too-high only *understates* a great ad
# (ITERATE instead of SCALE — mild); too-low stamps a mediocre ad SCALE (costly).
# KNOWN RISK, accepted by the user for now; recalibrate against the deliberately-
# strong anchor run once v2.4 is locked. See docs/v2_3_decision_layer.md §7a.
#
# v2.4: the per-purpose floors live in the purpose registry (single source of
# truth). This module constant is the DIRECT-SELL floor, read from there so the
# two never drift; resolve_decision takes the applicable floor per purpose.
_SCALE_FLOOR = resolve_purpose(DIRECT_SELL).provisional_scale_floor

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


# ---- v2.4: per-purpose primary metric (the seam) ----
#
# The decision STRUCTURE (resolve_decision's branches) is metric-agnostic — only
# three points touch the number: the headline, the RETARGET base, and the SCALE
# floor. So a purpose swaps in (a) a per-agent "win" predicate and (b) the frame
# it counts over; the branch logic transfers unchanged. Every metric stays a
# Python count over parsed signals (the "distributions are Python" invariant).


# Disposition stance prefixes that denote an EXISTING/LAPSED customer of the
# brand — the audience a retain/win-back ad targets. Extends the acquisition
# stance vocab (loyalist is the one already in it); a brand library must author
# such personas before retain can be scored (see docs/v2_4 §4.5). Until then a
# retain run finds none and is honestly dormant (INCONCLUSIVE), never scoring
# cold prospects as if they were existing customers.
_EXISTING_CUSTOMER_STANCES = frozenset({"loyalist", "lapsed", "subscriber", "winback"})


def _is_existing_customer(disposition_label: str) -> bool:
    return disposition_label.split("_", 1)[0] in _EXISTING_CUSTOMER_STANCES


def _existing_customer_labels(transcripts: list[AgentTranscript]) -> list[str]:
    return sorted({
        t.disposition_label for t in transcripts
        if _is_existing_customer(t.disposition_label)
    })


def _agent_win(t: AgentTranscript, preset: PurposePreset) -> bool | None:
    """Did this agent's terminal signal count as a WIN for this purpose? None
    when the agent has no usable signal (excluded from the denominator, exactly
    like a missing R7 in within_target_action_rate)."""
    metric = preset.headline_metric
    if metric == "breadth_registration":
        # informer: did this agent learn something new about the brand (R8
        # novelty)? The cognitive ruler — deliberately DISJOINT from
        # brand-building's affective (engagement + attribution) ruler, so the two
        # purposes stay distinct. Needs the probe; no probe -> exclude.
        return None if t.probe_signal is None else t.probe_signal.novelty
    bs = t.behavioral_signal
    if metric == "resonance_brand_memory":
        # brand-building: resonance (a lean-in, not a scroll) AND the brand stuck
        # (confident R9 attribution). This is meant to catch "loved the ad, forgot
        # the brand" — engaged but mis-attributed does NOT count.
        # ⚠ KNOWN LIMITATION (2026-07-12, docs/v2_4 §brand_recall): the recall gate is
        # UNVALIDATED and near-degenerate on logo-in-frame creatives — R2 makes the blind
        # reaction name the brand and it is replayed into reflection, so `brand_recall`
        # reads prior words, not memory (99/99 "confident" on the Starbucks anchor). The
        # metric then collapses to its resonance (engaged) half. Genuine attribution needs
        # a probe redesign + a mark-absent creative (parked). Needs the probe; without it
        # (pre-v2.4 transcript) there is no signal -> exclude.
        if bs is None or t.probe_signal is None:
            return None
        engaged = bs.action != "scroll_past"
        recalled = t.probe_signal.brand_recall == "confident"
        return engaged and recalled
    if bs is None:
        return None
    if metric == "cold_stop_lean_in":
        # Stop-and-lean-in: anything other than a scroll-past (linger / seek_info
        # / save / tap / share). The cold-hook job is the stop, not the sale.
        return bs.action != "scroll_past"
    # direct_sell + retain (reorder/return framing) both key off would-act.
    # awareness/informer is a breadth read handled on its own path (P6).
    return bs.would_act_within_week


def _frame_subset(
    transcripts: list[AgentTranscript],
    target_classification: TargetClassification,
    preset: PurposePreset,
) -> list[AgentTranscript]:
    """The transcripts the headline metric is computed over. narrow / existing
    -> the within-target dispositions; broad / broad_cold -> the whole panel
    (a cold-hook run is meant to be run against a cold-context envelope, so the
    panel already IS the cold audience)."""
    if preset.audience_frame == "existing":
        # retain: the frame is existing/lapsed-customer dispositions, NOT the
        # demographic within-target (which cuts a different way).
        return [t for t in transcripts if _is_existing_customer(t.disposition_label)]
    if preset.audience_frame == "narrow":
        within = set(target_classification.within_target_labels())
        return [t for t in transcripts if t.disposition_label in within]
    return list(transcripts)


def _rate_of(transcripts: list[AgentTranscript], preset: PurposePreset,
             *, none_on_empty: bool) -> tuple[float | None, int, int]:
    wins = denom = 0
    for t in transcripts:
        w = _agent_win(t, preset)
        if w is None:
            continue
        denom += 1
        if w:
            wins += 1
    if denom == 0:
        return (None if none_on_empty else 0.0), 0, 0
    return wins / denom, wins, denom


def purpose_primary_metric(
    transcripts: list[AgentTranscript],
    target_classification: TargetClassification,
    preset: PurposePreset,
) -> tuple[tuple[float | None, int, int], dict[str, tuple[float, int, int]]]:
    """(headline (rate,num,denom) over the purpose frame, per-disposition dict).
    Deterministic. Delegates direct-sell to the v2.3 functions byte-for-byte so
    the four anchors cannot move; other purposes use the generic predicate."""
    if preset.name == DIRECT_SELL:
        return (
            within_target_action_rate(transcripts, target_classification),
            action_by_disposition(transcripts),
        )
    headline = _rate_of(
        _frame_subset(transcripts, target_classification, preset),
        preset, none_on_empty=True,
    )
    by_label: dict[str, tuple[float, int, int]] = {}
    labels = {t.disposition_label for t in transcripts}
    for label in labels:
        ts = [t for t in transcripts if t.disposition_label == label]
        by_label[label] = _rate_of(ts, preset, none_on_empty=False)
    return headline, by_label


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


# A broad-reach job (brand-building, informer) earns HIGH trust by BREADTH — this
# many distinct dispositions actually registering the signal — not by one narrow
# group registering strongly. This is the v2.3 SCALE trust guard ported to a
# broad frame (skip it and the provisional bar fires easiest on the thinnest,
# single-group evidence — the exact hole caught in v2.3).
_BROAD_MIN_DISPOSITIONS = 3


def _broad_trust(
    by_disposition: dict[str, tuple[float, int, int]], flags: list[str]
) -> str:
    registered = sum(1 for (_r, num, _d) in by_disposition.values() if num > 0)
    if registered >= _BROAD_MIN_DISPOSITIONS and not (_THIN_EVIDENCE_FLAGS & set(flags)):
        return "HIGH"
    return "DIRECTIONAL"


# Awareness/informer is a BREADTH read: how many distinct audience TYPES
# registered the ad as news (R8 novelty), not an agent-level rate. A disposition
# "registers" when at least this fraction of its agents reported novelty. A
# PROVISIONAL threshold (like the SCALE floors) — recalibrate against an informer
# anchor run.
_INFORMER_REGISTER_THRESHOLD = 0.5


def _resolve_informer(
    by_disposition: dict[str, tuple[float, int, int]],
    load_bearing_pain: Pain | None,
    verdict: str,
    methodology_flags: list[str],
    scale_floor: float,
) -> Decision:
    """The informer decision, on a DISPOSITION-COUNT breadth (not an agent rate).
    breadth = (dispositions that registered the news) / (dispositions with a
    novelty signal). SCALE = broad registration + memorable; ITERATE = noticed
    but narrow/unclear; REBUILD = a structural attention block; INCONCLUSIVE =
    no signal. There is no RETARGET — a broad-reach informer has no 'wrong
    person' story."""
    total = [lab for lab, (_r, _n, denom) in by_disposition.items() if denom > 0]
    registered = [
        lab for lab, (rate, _n, denom) in by_disposition.items()
        if denom > 0 and rate >= _INFORMER_REGISTER_THRESHOLD
    ]
    trust = _broad_trust(by_disposition, methodology_flags)
    n_reg, n_total = len(registered), len(total)
    breadth = (n_reg / n_total) if n_total else None

    def make(decision: str, rationale: str) -> Decision:
        d = Decision(
            decision=decision, target_action_rate=breadth, trust=trust,
            target_action_num=n_reg, target_action_denom=n_total,
            within_dispositions=sorted(registered),
            load_bearing_pain_id=(load_bearing_pain.id if load_bearing_pain else ""),
            rationale=rationale,
        )
        d.purpose = AWARENESS_INFORMER
        return d

    if verdict == "METHODOLOGY_GAP":
        return make("INCONCLUSIVE", "verdict is METHODOLOGY_GAP (data quality)")
    if n_total == 0 or breadth is None:
        return make("INCONCLUSIVE", "no novelty signal to read breadth from")
    if load_bearing_pain is not None and load_bearing_pain.severity == "structural":
        return make("REBUILD", f"structural attention block {load_bearing_pain.id} — few notice it")
    if breadth >= scale_floor and trust == "HIGH" and load_bearing_pain is None:
        return make(
            "SCALE",
            f"{n_reg} of {n_total} audience types registered it as news "
            f">= provisional breadth bar {scale_floor:.0%}, HIGH trust",
        )
    return make("ITERATE", f"only {n_reg} of {n_total} audience types registered the news")


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
    scale_floor: float = _SCALE_FLOOR,
    within_rate: float | None = None,
    trust_override: str | None = None,
) -> Decision:
    """Map already-computed signals to a brand-facing DECISION. Deterministic,
    first-match, severity + disposition-gap driven — A_within is the headline
    number and (only at the SCALE branch) a magnitude backstop, never the sole
    driver, which is what keeps this from overfitting the four calibration
    anchors. SCALE is un-gated behind a PROVISIONAL floor (see _SCALE_FLOOR):
    it fires only for a clean, strong read and fails toward ITERATE otherwise.

        0. METHODOLOGY_GAP                               -> INCONCLUSIVE
        1. audience_match == mismatched                  -> RETARGET
        2. a non-within champion beats A_within by >=G   -> RETARGET
           and clears the absolute floor F
        3. no within-target evidence at all              -> INCONCLUSIVE
        4. load-bearing within pain is STRUCTURAL        -> REBUILD
        5. A_within >= _SCALE_FLOOR AND no in-target      -> SCALE  [provisional]
           lever left AND trust == HIGH
        6. else (execution / fixable)                    -> ITERATE
    """
    trust = trust_override if trust_override is not None else _trust(within_labels, methodology_flags)
    champion = _best_champion(action_by_disp, classification_map)
    lb_id = load_bearing_pain.id if load_bearing_pain is not None else ""
    # a_within is the HEADLINE metric (broad for a broad-frame job); within_rate
    # is the WITHIN-target performance that drives the "wrong crowd" and
    # "no within evidence" branches. They are the same for direct-sell (narrow
    # frame), so within_rate defaults to a_within.
    if within_rate is None:
        within_rate = a_within

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
    base = within_rate if within_rate is not None else 0.0
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
    if not within_labels or within_rate is None:
        return make("INCONCLUSIVE", "no within-target evidence to decide on")

    # 4. The load-bearing within-target block is structural — no in-scope lever
    #    fixes it. (If there is no diagnosed within pain, treat as fixable.)
    if load_bearing_pain is not None and load_bearing_pain.severity == "structural":
        return make("REBUILD", f"load-bearing within pain {lb_id} is structural")

    # 5. Strong, clean, WELL-EVIDENCED read -> SCALE (PROVISIONAL bar, decision-2).
    #    Three conditions, ALL required:
    #      (a) the within target acts at/above the provisional floor;
    #      (b) no in-target lever is left — step 4 already excluded a structural
    #          within pain, so a None load-bearing pain here means zero within
    #          pains survive;
    #      (c) trust is HIGH (>=2 within dispositions, no thin-evidence flag).
    #    (c) is load-bearing, not decoration: WITHOUT it the branch fires most
    #    easily on THIN, single-persona reads (a_within is cheap on a small
    #    denominator — 4/5 = 80% — and "no within pain" is easier when few
    #    transcripts surface few pains), which would invert the "fails toward
    #    ITERATE, never false-SCALE" posture the provisional bar is sold on. With
    #    today's single-within-persona panels this means provisional SCALE rarely
    #    fires — by design, that is the mild (understatement) failure. The floor
    #    is a documented best-guess (see _SCALE_FLOOR), NOT an anchor run — KNOWN
    #    RISK, recalibrate post-v2.4. Fails toward ITERATE (step 6).
    if (
        a_within is not None
        and a_within >= scale_floor
        and load_bearing_pain is None
        and trust == "HIGH"
    ):
        return make(
            "SCALE",
            f"metric at {a_within:.0%} >= provisional bar {scale_floor:.0%}, "
            f"no in-target lever left, HIGH trust",
        )

    # 6. The block is execution-level — a specific in-scope lever is leaking.
    return make("ITERATE", f"load-bearing within pain {lb_id or '(none)'} is fixable")


def build_decision(
    transcripts: list[AgentTranscript],
    target_classification: TargetClassification,
    audience_match: AudienceMatch | None,
    verdict: str,
    methodology_flags: list[str],
    pain_map: list[Pain],
    purpose: str = DIRECT_SELL,
) -> Decision:
    """Extract the signals from the raw run artifacts and resolve the decision.
    The single orchestrator called from synthesize_report; keeps
    resolve_decision a pure function of scalars for cheap fixture testing.

    v2.4: `purpose` selects the headline metric + the SCALE floor (the seam).
    direct-sell is byte-for-byte v2.3; other jobs swap the metric, the frame,
    and the floor while the branch structure transfers."""
    preset = resolve_purpose(purpose)

    if preset.name == AWARENESS_INFORMER:
        # A disposition-count breadth read, not an agent rate — resolved on its
        # own path (no RETARGET; SCALE/ITERATE/REBUILD/INCONCLUSIVE only).
        _headline, by_disp = purpose_primary_metric(
            transcripts, target_classification, preset
        )
        load_bearing = load_bearing_within_pain(pain_map)
        return _resolve_informer(
            by_disp, load_bearing, verdict, methodology_flags,
            preset.provisional_scale_floor,
        )

    if preset.name == RETAIN_WINBACK:
        # retain's relevant audience is existing/lapsed customers, cutting across
        # the demographic within/outside axis. With no such personas in the panel
        # the ad cannot be judged -> honestly dormant, NOT a faked reorder rate.
        existing = _existing_customer_labels(transcripts)
        if not existing:
            dormant = Decision(
                decision="INCONCLUSIVE",
                target_action_rate=None,
                trust="DIRECTIONAL",
                rationale=(
                    "retain/win-back needs existing-customer personas "
                    "(loyalist/lapsed/subscriber) in the panel; none were present"
                ),
            )
            dormant.purpose = preset.name
            return dormant
        # existing customers ARE the "within" for a retain decision; recast the
        # classification map so champion detection means "lands better on
        # non-existing prospects" (the retain 'wrong audience' story).
        within_labels = existing
        existing_set = set(existing)
        classification_map = {
            t.disposition_label: ("within" if t.disposition_label in existing_set else "outside")
            for t in transcripts
        }
    else:
        classification_map = {
            d.disposition_label: d.classification
            for d in target_classification.disposition_classifications
        }
        within_labels = target_classification.within_target_labels()

    (a_within, num, denom), action_by_disp = purpose_primary_metric(
        transcripts, target_classification, preset
    )
    # The within-target performance (for the "wrong crowd" / "no within evidence"
    # branches). Equals the headline for direct-sell (narrow frame); for a
    # broad-frame job it is the same win predicate restricted to within-target.
    if preset.name == DIRECT_SELL:
        within_rate = a_within
    else:
        within_subset = [
            t for t in transcripts if t.disposition_label in set(within_labels)
        ]
        within_rate = _rate_of(within_subset, preset, none_on_empty=True)[0]
    load_bearing = load_bearing_within_pain(pain_map)
    am_verdict = audience_match.verdict if audience_match is not None else None
    # Broad-reach jobs earn trust by breadth of registration, not within-count.
    trust_override = (
        _broad_trust(action_by_disp, methodology_flags)
        if preset.multi_target else None
    )
    decision = resolve_decision(
        a_within,
        action_by_disp,
        classification_map,
        within_labels,
        load_bearing,
        am_verdict,
        verdict,
        methodology_flags,
        scale_floor=preset.provisional_scale_floor,
        within_rate=within_rate,
        trust_override=trust_override,
    )
    # Enrich with the raw counts behind the metric (for an honest render) + the
    # purpose (so the render/artifact phrases the headline correctly); the
    # decision itself never depends on these.
    decision.target_action_num = num
    decision.target_action_denom = denom
    decision.purpose = preset.name
    return decision
