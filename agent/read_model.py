"""ReadModel — the presentation-neutral view of a finished Creative Read.

One source of truth for every line a brand manager reads, so the terminal
report (batch_run.py) and the client-facing HTML (agent/report_html.py)
cannot drift apart on the honesty surfaces. The rule that motivates this
module: the client artifact may curate which FINDINGS it shows; it may
never drop a GUARDRAIL.

The guardrails carried here — each one exists because a specific way of
misreading the number was found in testing:

  * INCONCLUSIVE never shows an action rate       (spec §4)
  * A3  "would research" is reported separately, never folded into buy
  * A4  the per-cycle breakdown accompanies the blended headline, so the
        headline never hides its cycle-mix assumption
  * A7  the coherence warning when stated buy-intent contradicts the glance
  * A6  trust: HIGH needs >=2 within-target dispositions, else DIRECTIONAL
  * F3  the per-purpose launch-scope caveat (BETA / PARKED)
  * E3  the model-inferred disclaimer
  *     methodology flags, provisional dispositions, panel degradation

build_read_model() reads a finished run directory. It touches exactly:

    run.json            — config + the persisted Report (status='complete')
    replay_report.json  — the Report when the run was recovered by
                          replay_synthesis after a mid-run crash
    l3_summary.json     — segment behavioural distributions (the glance);
                          this is NOT carried on the Report

docs/v3_protocol.md is the protocol these numbers come from.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agent.purpose import resolve_purpose
from agent.schema import Report

# ---- Shared presentation vocabulary -------------------------------------
# Imported by batch_run.py (terminal) and agent/report_html.py (client HTML).
# Changing a string here changes both renderers, which is the point.

DECISION_TAGLINE = {
    "SCALE": "Put spend behind it — no in-scope lever would materially lift it.",
    "ITERATE": "Target responds; a specific in-scope fix is leaking conversion. "
               "Fix it, re-run, then scale.",
    "RETARGET": "The creative works — for a different audience than it's aimed at. "
                "Fix the buy, not the ad.",
    "REBUILD": "The target rejects it on grounds no in-scope tweak fixes. "
               "Don't run as-is.",
    "INCONCLUSIVE": "The read isn't trustworthy yet — see why below.",
}

LEVER_HEADING = {
    "ITERATE": "THE FIX(ES)  (highest-leverage first):",
    "RETARGET": "RE-AIM + FIX  (highest-leverage first):",
    "REBUILD": "IF YOU REBUILD, what has to change:",
    "INCONCLUSIVE": "TO GET A TRUSTWORTHY READ:",
    "SCALE": "PROTECT ON SCALE-UP:",
}

CYCLE_LABEL = {
    "running_low": "running low",
    "mid_cycle": "mid-cycle",
    "just_bought": "just bought",
}
CYCLE_ORDER = ("running_low", "mid_cycle", "just_bought")

# v3 F3 — launch scope. Per-purpose scoring is validated to different depths:
# direct_sell + cold_hook are anchored; the rest run but their headline metric
# is not yet anchored by a per-purpose calibration run. We WARN, never block.
PURPOSE_SCOPE_NOTE = {
    "brand_building": (
        "BETA — brand-building scoring is provisional (resonance half only; "
        "brand-attribution is a known, flagged limitation). Trust the pains "
        "and the voice; treat the headline metric as directional."
    ),
    "awareness_informer": (
        "PARKED — informer scoring is not yet anchored by a per-purpose "
        "calibration run. The reactions are sound; the headline metric is "
        "unvalidated. Trust the pains and the voice, not the number."
    ),
    "retain_winback": (
        "PARKED — retain/win-back needs existing-customer (loyalist/lapsed) "
        "dispositions to score honestly; scoring is unvalidated. Trust the "
        "pains and the voice, not the number."
    ),
}

# The decision bucket is the LEAST reliable element on a read: in the
# discriminant check (docs/v3_discriminant_check.md) it scored a
# deliberately-bad control ad the same as the real ads, while the pain layer
# separated them cleanly. The bucket stays on the page — a brand manager
# opening a report needs an answer, and burying it just makes them read the
# page backwards hunting for one — but it must wear its own limitation, so
# the caveat travels with the claim instead of sitting in a block above it.
# Wording is the user's own, from the report design they specified. Keep it.
VERDICT_CAVEAT = "Didn't separate a known-bad control — tiebreaker, not gate."

# The stages of the funnel, in the order a buyer moves through them. Defined
# here rather than in a renderer: both the diagnosis overview and the pain
# card ordering sort by it, and two copies is how the two surfaces drift.
#
# MUST cover schema._VALID_FUNNEL_STAGES — pinned by a test, because a stage
# missing here doesn't error, it silently under-reports. `recall` was absent
# from the renderer's copy of this list for exactly that reason: it is a real
# stage (9 pains on disk use it) that sorted into the unknown bucket, and the
# overview's stage row would have implied the funnel has four stages and that
# recall is not somewhere a creative can leak.
FUNNEL_STAGE_ORDER = (
    "attention", "comprehension", "consideration", "conversion", "recall",
)

# v3 E3 — the one prominent, honest disclaimer. Every quote in a read is
# generated by a simulated persona reacting to the creative.
DISCLAIMER = (
    "Model-inferred read: every reaction and quote here is generated by a "
    "simulated persona, not collected from a real consumer. Read it as a "
    "pre-flight diagnostic, not a survey."
)

FUNNEL_OFF_NOTE = (
    "Projected funnel: off — heuristic_v1, not fitted to in-market outcomes. "
    "It is computed and logged for future calibration either way; re-run with "
    "--funnel to see the directional estimate."
)

# When --funnel was on, the projection exists but this view deliberately does
# not chart it: the numbers are heuristic_v1 and unfitted, so putting a funnel
# chart in front of a client would read as a forecast. Say so rather than
# letting the projection vanish without explanation.
FUNNEL_WITHHELD_NOTE = (
    "Projected funnel: computed for this run, but not charted here — "
    "heuristic_v1 is not fitted to in-market outcomes, so it is a directional "
    "estimate, not a forecast. It is in the run's l35_projection.json."
)

# Methodology flags in the words a brand manager reads. The flags themselves
# are engine tokens (schema._VALID_METHODOLOGY_FLAGS) and printing them raw is
# the same class of leak as the OUTSIDE-TARGET prefix below: correct, and
# meaningless to the person paying for the read.
#
# A flag with no entry here renders as its raw token rather than vanishing — an
# unrecognised flag is a reporting gap, not a licence to drop a caveat, and
# this map is exactly the kind of hand-maintained list that goes stale when the
# schema gains a member. tests/test_read_model.py pins it against the schema.
METHODOLOGY_FLAG_TEXT = {
    "single_within_target":
        "Only one consumer type fell within the declared target — evidence is "
        "thin.",
    "no_within_target_evidence":
        "No consumer type read as a clean match for this creative, and it is "
        "not a clean mismatch either — the read rests on weak ground.",
    "pool_archetype_mismatch":
        "Nobody in this audience fits the ad. The read rests on the wrong "
        "people.",
    "target_unsignaled":
        "The ad doesn't clearly signal who it's for — every audience type read "
        "as a maybe.",
    "homogenization_high":
        "Too many slices of the audience reacted almost identically — some of "
        "this may be echo rather than measurement.",
    "single_context_only":
        "Only one browsing context was tested, so how it lands elsewhere in "
        "the feed is unknown.",
    "provisional_disposition_present":
        "One of the audience types in this read was drafted during the run and "
        "has not been reviewed.",
    "declared_audience_disjoint":
        "The audience declared for this buy does not overlap the people the "
        "creative reads as aimed at.",
    "intent_action_incoherent":
        "Stated intent and in-feed behaviour disagree on this run — treat the "
        "intent numbers with caution.",
}

# The assess pass prefixes an out-of-target pain with its own scoping note. The
# page already carries within/outside as a first-class visual state, so the
# prefix is a duplicate — and it is engine vocabulary, verbatim, at the top of
# a sentence a client reads. Same bug class as the "unclassified" glance legend.
_ENGINE_PAIN_PREFIX = "OUTSIDE-TARGET CONTEXT (not verdict-load-bearing):"


def humanize(label: str) -> str:
    return label.replace("_", " ")


def flag_text(flag: str) -> str:
    """A methodology flag in plain words, or the raw token when unmapped."""
    return METHODOLOGY_FLAG_TEXT.get(flag, flag)


def client_pain_text(text: str) -> str:
    """A pain as a client should read it — engine scoping vocabulary removed.

    Strips the assess pass's OUTSIDE-TARGET prefix and restores the sentence
    capital it swallowed (the text after the colon starts lowercase, because
    the model wrote it as a continuation). Any other text is returned
    unchanged.
    """
    text = (text or "").strip()
    if not text.lower().startswith(_ENGINE_PAIN_PREFIX.lower()):
        return text
    rest = text[len(_ENGINE_PAIN_PREFIX):].lstrip()
    return (rest[:1].upper() + rest[1:]) if rest else text


def purpose_scope_note(purpose: str) -> str | None:
    """v3 F3: the launch-scope caveat for a purpose, or None when the purpose
    is active (direct_sell / cold_hook)."""
    return PURPOSE_SCOPE_NOTE.get(purpose)


def headline_metric_line(d) -> str:
    """The one number the brand manager reads, phrased for the ad's JOB.
    Direct-sell is byte-for-byte the v2.3 line; other jobs swap metric+frame."""
    preset = resolve_purpose(getattr(d, "purpose", "direct_sell") or "direct_sell")
    rate = f"{d.target_action_rate:.0%}"
    tail = (f"  —  {d.target_action_num} of {d.target_action_denom}"
            if d.target_action_denom else "")
    if preset.name == "direct_sell":
        who = (humanize(", ".join(d.within_dispositions))
               if d.within_dispositions else "your target")
        return f"  {rate} of your target ({who}) would buy{tail}."
    if preset.name == "cold_hook":
        return (f"  {rate} of a cold audience stopped and leaned in{tail}  "
                f"(vs scrolling past — the hook, not the sale).")
    if preset.name == "brand_building":
        return (f"  {rate} both felt it AND remembered the brand{tail}  "
                f"(engaged but mis-attributed doesn't count).")
    if preset.name == "awareness_informer":
        # breadth is a disposition COUNT: num of denom audience TYPES registered.
        return (f"  {d.target_action_num} of {d.target_action_denom} audience types "
                f"registered it as news ({rate})  (breadth of noticing, not sales).")
    # retain / others: a generic metric-labelled line.
    return f"  {rate} — {preset.metric_label}{tail}."


def trust_line(d) -> str:
    if d.trust == "HIGH":
        line = "Trust: HIGH"
        if len(d.within_dispositions) >= 2:
            line += f" — {len(d.within_dispositions)} within-target dispositions agree"
        if d.target_action_denom:
            line += f" ({d.target_action_denom} in the target sample)"
        return line + "."
    return ("Trust: DIRECTIONAL — thin evidence (one narrow audience engaged); "
            "treat as a lead, not a verdict.")


def inconclusive_lines(report: Report) -> list[str]:
    """Plain-language why + what-to-change for an INCONCLUSIVE read (spec §4).
    An untrustworthy read must NEVER show a confident action-rate headline —
    the number rests on the wrong people or an unreadable target."""
    flags = set(report.methodology_flags)
    if "pool_archetype_mismatch" in flags:
        why = ("the audience this ad targets isn't represented in your "
               "disposition library, so the read rests on the wrong people")
        fix = ("add a disposition profile that matches this ad's audience, "
               "then re-run")
    elif "target_unsignaled" in flags:
        why = ("the ad doesn't clearly signal who it's for — every audience "
               "read as a maybe")
        fix = ("clarify the creative's target, or declare the audience you're "
               "buying against, then re-run")
    else:
        why = (report.decision.rationale if report.decision else
               "the read isn't trustworthy on this pool")
        fix = "check that the audience you declared matches who the ad is for"
    return [
        "  We can't give you a trustworthy read on this creative yet.",
        f"  Why: {why}.",
        f"  To get a real read: {fix}.",
    ]


# ---- Glance -------------------------------------------------------------


# The in-feed actions a glance can contain, ordered by escalating engagement
# (which is also the order the bar segments read in). The v3 enum is
# scroll_past|linger|tap_cta|save|share (agent/schema.py, pinned by
# tests/test_reaction_surface.py). `seek_info` is the v2.x action and appears
# only in pre-v3 runs on disk — kept so historical reads still render honestly.
GLANCE_SEGMENTS: tuple[tuple[str, str], ...] = (
    ("scroll_past", "Scrolled past"),
    ("seek_info", "Sought more info"),
    ("linger", "Stopped to look"),
    ("save", "Saved it"),
    ("share", "Sent it to someone"),
    ("tap_cta", "Tapped through"),
)
_GLANCE_ORDER = {k: i for i, (k, _) in enumerate(GLANCE_SEGMENTS)}


@dataclass
class Glance:
    """What the thumb did in the 2-second encounter, for the within-target
    audience only. Sourced from L3 segment distributions, because the Report
    carries the decision numbers but not the raw action mix.

    Holds a raw counts map rather than fixed fields. Fixed fields are how the
    original version silently lost data: it summed `tap_through`, which is not
    in the action enum and therefore was structurally always 0, while `save`
    and `share` were dropped from the denominator entirely — so a saver was
    erased from the panel and every percentage was computed over a short n.
    Counting whatever the run actually emitted means no respondent can ever
    fall out of the total, including from older protocol versions.
    """

    counts: dict[str, int] = field(default_factory=dict)

    def add(self, action: str, k: int) -> None:
        if k:
            self.counts[action] = self.counts.get(action, 0) + k

    def count(self, key: str) -> int:
        return self.counts.get(key, 0)

    @property
    def n(self) -> int:
        """Every respondent, whatever they did — never a filtered subtotal."""
        return sum(self.counts.values())

    @property
    def scroll_past(self) -> int:
        return self.count("scroll_past")

    @property
    def linger(self) -> int:
        return self.count("linger")

    @property
    def tap_cta(self) -> int:
        return self.count("tap_cta")

    @property
    def save(self) -> int:
        return self.count("save")

    @property
    def share(self) -> int:
        return self.count("share")

    @property
    def engaged(self) -> int:
        """Anyone who did something other than scroll past."""
        return self.n - self.scroll_past

    def rate(self, key: str) -> float:
        return (self.count(key) / self.n) if self.n else 0.0

    def segments(self) -> list[tuple[str, str, int, float]]:
        """(key, label, count, rate) for actions actually present, in
        engagement order. Unknown actions sort last under their raw key rather
        than being dropped — an unrecognised action is a reporting gap, not a
        licence to lose the respondent."""
        known = dict(GLANCE_SEGMENTS)
        return [
            (k, known.get(k, k.replace("_", " ").capitalize()), c, self.rate(k))
            for k, c in sorted(
                self.counts.items(),
                key=lambda kv: (_GLANCE_ORDER.get(kv[0], len(_GLANCE_ORDER)), kv[0]),
            )
            if c
        ]

    def to_dict(self) -> dict:
        return {**self.counts, "n": self.n}


def _disposition_of_segment(segment_key: str) -> str:
    """Segment keys are '<disposition>::<chaos_band>' at the default
    disposition_chaos_band granularity, or a bare '<disposition>' at
    disposition granularity. Split exactly — never prefix-match, or two
    dispositions sharing a prefix silently merge."""
    return segment_key.split("::", 1)[0]


def within_target_glance(
    segment_distributions: dict, within_dispositions: list[str]
) -> Glance:
    """Sum the action mix across segments belonging to the within-target
    dispositions. An empty within-set yields an empty Glance (n=0), which
    every renderer must treat as 'no glance bar', not as 0%."""
    wanted = set(within_dispositions)
    g = Glance()
    for seg_key, dist in segment_distributions.items():
        if _disposition_of_segment(seg_key) not in wanted:
            continue
        # Take every action the segment reports, not a hand-listed subset —
        # an action absent from the list would otherwise vanish from n.
        for action, k in ((dist or {}).get("counts", {}) or {}).items():
            g.add(str(action), int(k))
    return g


# ---- Panel response — every consumer type, in and out of target ---------

# What a person said they'd do next, in plain words. Ordered by how much the
# brand should care, strongest first.
NEXT_STEP_LABEL = {
    "buy_now": "would buy now",
    "buy_at_restock": "would buy when they restock",
    "research_first": "would look it up first",
    "mention_to_someone": "would mention it to someone",
    "nothing": "did nothing",
}
NEXT_STEP_ORDER = ("buy_now", "buy_at_restock", "research_first",
                   "mention_to_someone", "nothing")

# The next steps that are worth something to the brand — everything except
# "nothing". Kept as a set rather than "not nothing" so a new step added to the
# protocol has to be classified deliberately instead of counting by default.
NEXT_STEP_POSITIVE = frozenset(NEXT_STEP_ORDER) - {"nothing"}


@dataclass
class ConsumerTypeResponse:
    """What one consumer type did — whether or not they were the target.

    The in-target filter answers "did the people we bought respond". It cannot
    answer "who else responded", and those come apart in real runs: a type can
    be classified in-target and do nothing while an out-of-target type acts.
    """

    disposition: str
    within_target: bool
    glance: Glance = field(default_factory=Glance)
    next_steps: dict[str, int] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return humanize(self.disposition)

    @property
    def n(self) -> int:
        return self.glance.n

    @property
    def engaged(self) -> int:
        """Did anything other than scroll past."""
        return self.glance.engaged

    @property
    def engaged_rate(self) -> float:
        return (self.engaged / self.n) if self.n else 0.0

    def step(self, key: str) -> int:
        return self.next_steps.get(key, 0)

    @property
    def acted(self) -> int:
        """Said they'd do something next — buy, look it up, or tell someone."""
        return sum(v for k, v in self.next_steps.items() if k in NEXT_STEP_POSITIVE)

    @property
    def buyers(self) -> int:
        return self.step("buy_now") + self.step("buy_at_restock")

    def step_rows(self) -> list[tuple[str, str, int]]:
        """(key, label, count) for the next steps actually taken, strongest
        first. Unknown steps sort last under their raw key rather than being
        dropped — losing one would understate what the panel did."""
        order = {k: i for i, k in enumerate(NEXT_STEP_ORDER)}
        return [
            (k, NEXT_STEP_LABEL.get(k, k.replace("_", " ")), v)
            for k, v in sorted(self.next_steps.items(),
                               key=lambda kv: (order.get(kv[0], len(order)), kv[0]))
            if v
        ]


@dataclass
class PanelResponse:
    """The whole panel, not the target slice — the answer to 'who else'."""

    types: list[ConsumerTypeResponse] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.types

    @property
    def panel_n(self) -> int:
        return sum(t.n for t in self.types)

    @property
    def in_types(self) -> list[ConsumerTypeResponse]:
        return [t for t in self.types if t.within_target]

    @property
    def out_types(self) -> list[ConsumerTypeResponse]:
        return [t for t in self.types if not t.within_target]

    def _tally(self, types: list[ConsumerTypeResponse]) -> tuple[int, int]:
        return sum(t.n for t in types), sum(t.engaged for t in types)

    @property
    def in_tally(self) -> tuple[int, int]:
        return self._tally(self.in_types)

    @property
    def out_tally(self) -> tuple[int, int]:
        return self._tally(self.out_types)

    @property
    def summary(self) -> str:
        """States the denominator the rest of the page is measured against."""
        if self.is_empty:
            return ""
        in_n, _ = self.in_tally
        if not in_n:
            return (f"All {self.panel_n} people in the panel. No audience type "
                    f"was read as the target for this creative.")
        return (f"All {self.panel_n} people in the panel — not just the {in_n} "
                f"you're buying. Every number above is measured on those "
                f"{in_n}; this is everyone who saw it.")

    def next_steps_in_target(self) -> list[tuple[str, str, int, int]]:
        """(key, label, count, denominator) for what the TARGET said they'd do
        next — strongest first, in-target types only.

        In-target only, and named so, deliberately. This is a panel-wide
        aggregate, and pooling one across the whole panel is the mistake that
        has cost this project a rebuild twice: on a narrow ad the out-of-target
        majority swamps the signal (19 in target against 81 outside), so a
        pooled "did nothing: 95 of 100" would read as a catastrophe on a
        creative that worked exactly as aimed. See docs/v3_out_of_target_
        response.md. Anything wanting the outside slice must ask for it.
        """
        totals: dict[str, int] = {}
        for t in self.in_types:
            for step, k in t.next_steps.items():
                if k:
                    totals[step] = totals.get(step, 0) + int(k)
        denom = self.in_tally[0]
        order = {k: i for i, k in enumerate(NEXT_STEP_ORDER)}
        return [
            (k, NEXT_STEP_LABEL.get(k, humanize(k)), v, denom)
            for k, v in sorted(totals.items(),
                               key=lambda kv: (order.get(kv[0], len(order)), kv[0]))
            if v
        ]

    @property
    def decoupling_note(self) -> str | None:
        """Fires when the people NOT being bought responded at a higher rate
        than the people being bought.

        This is a real pattern in the runs, not a hypothetical, and it is
        invisible on any in-target-only view — which is the entire reason this
        table exists. It is a lead worth chasing, not a verdict: the rates it
        compares are usually over small samples.
        """
        in_n, in_e = self.in_tally
        out_n, out_e = self.out_tally
        if not in_n or not out_n:
            return None
        in_rate, out_rate = in_e / in_n, out_e / out_n
        if out_rate <= in_rate or not out_e:
            return None
        return (
            f"The people you are NOT buying responded more than the people you "
            f"are — {out_rate:.0%} of the {out_n} outside your target did "
            f"something, against {in_rate:.0%} of the {in_n} inside it. Worth a "
            f"look at who this creative is actually landing with."
        )


def build_panel_response(
    segment_distributions: dict, within_dispositions: list[str]
) -> PanelResponse:
    """Roll the L3 segment distributions up to one row per consumer type.

    Segments are '<disposition>::<chaos_band>'; the bands are collapsed here
    because the brand-facing question is about the consumer type. Order is
    in-target first, then out — each group by response rate, strongest first,
    so the types that actually did something lead their group.
    """
    wanted = set(within_dispositions)
    by: dict[str, ConsumerTypeResponse] = {}
    for seg_key, dist in (segment_distributions or {}).items():
        disp = _disposition_of_segment(seg_key)
        row = by.get(disp)
        if row is None:
            row = by[disp] = ConsumerTypeResponse(
                disposition=disp, within_target=disp in wanted
            )
        for action, k in ((dist or {}).get("counts", {}) or {}).items():
            row.glance.add(str(action), int(k))
        for step, k in ((dist or {}).get("next_step_counts", {}) or {}).items():
            if k:
                row.next_steps[str(step)] = row.next_steps.get(str(step), 0) + int(k)

    types = sorted(
        by.values(),
        key=lambda t: (0 if t.within_target else 1, -t.engaged_rate, -t.n,
                       t.disposition),
    )
    return PanelResponse(types=types)


# ---- Diagnosis overview -------------------------------------------------


@dataclass
class DiagnosisOverview:
    """The shape of the diagnosis, before any single problem is read.

    Derived entirely from `pain_map` — it asserts nothing the problem cards
    don't already say. It exists because the pattern across the problems is
    invisible while you are reading them one at a time: that four of six land
    on the audience being bought, or that two are structural and no creative
    edit touches them, is the part a brand manager acts on, and it can only
    be seen by counting. Counting is the renderer's job to show, not the
    reader's job to do.
    """

    total: int = 0
    within: int = 0
    outside: int = 0
    structural: int = 0
    execution: int = 0
    stages: list[str] = field(default_factory=list)   # present only, funnel order
    load_bearing_id: str = ""
    load_bearing_stage: str = ""
    widest_breadth: int = 0      # most consumer types to raise any one problem

    @property
    def is_empty(self) -> bool:
        return self.total == 0

    @property
    def summary(self) -> str:
        """One plain sentence, read before the detail. Empty when there are no
        problems — the section vanishes rather than announcing a zero."""
        if not self.total:
            return ""
        noun = "problem" if self.total == 1 else "problems"
        stage_noun = "stage" if len(self.stages) == 1 else "stages"
        bits = [f"{self.total} {noun}, leaking at {len(self.stages)} "
                f"{stage_noun} of the funnel."]
        if self.within and self.outside:
            bits.append(f"{self.within} hit the audience you're buying; "
                        f"{self.outside} land outside it.")
        elif self.within:
            bits.append(f"All {self.within} hit the audience you're buying."
                        if self.within > 1
                        else "It hits the audience you're buying.")
        elif self.outside:
            bits.append("None of them land on the audience you're buying — "
                        "every one comes from people outside your target.")
        if self.structural:
            n = self.structural
            bits.append(f"{n} {'is' if n == 1 else 'are'} structural — no change "
                        f"to the creative fixes {'that one' if n == 1 else 'those'}.")
        return " ".join(bits)


def build_diagnosis_overview(report: Report) -> DiagnosisOverview:
    """Count the diagnosis. Unknown funnel stages are kept and sorted last
    rather than dropped — a stage this build doesn't recognise is a reporting
    gap, not a licence to under-report how many stages leak."""
    pains = list(report.pain_map)
    ov = DiagnosisOverview(total=len(pains))
    if not pains:
        return ov

    seen: set[str] = set()
    for p in pains:
        if p.within_target:
            ov.within += 1
        else:
            ov.outside += 1
        if (p.severity or "").lower() == "structural":
            ov.structural += 1
        else:
            ov.execution += 1
        stage = (p.funnel_stage or "").strip().lower()
        if stage:
            seen.add(stage)
        ov.widest_breadth = max(ov.widest_breadth, len(p.cited_by))

    ov.stages = ([s for s in FUNNEL_STAGE_ORDER if s in seen]
                 + sorted(s for s in seen if s not in FUNNEL_STAGE_ORDER))

    lb_id = (report.decision.load_bearing_pain_id if report.decision else "") or ""
    lb = next((p for p in pains if p.id == lb_id), None) if lb_id else None
    if lb is not None:
        ov.load_bearing_id = lb.id
        ov.load_bearing_stage = lb.funnel_stage or ""
    return ov


# ---- The model ----------------------------------------------------------


@dataclass
class ReadModel:
    """Everything a renderer needs, already resolved. No renderer should
    reach past this into raw JSON — that is how guardrails get dropped."""

    # provenance
    run_id: str
    run_dir: Path
    report: Report
    report_source: str            # 'run.json' | 'replay_report.json'
    generated_at: str = ""

    # what was read
    asset_label: str = ""
    asset_path: Path | None = None
    category: str = ""
    account_id: str = ""
    brand_profile_id: str = ""
    declared_targeting: str = ""
    panel_size: int = 0

    # the job it was graded against
    purpose: str = "direct_sell"
    purpose_label: str = ""
    purpose_metric_label: str = ""
    scope_note: str | None = None          # F3

    # the decision surface
    decision_name: str = "INCONCLUSIVE"
    tagline: str = ""
    is_inconclusive: bool = True
    headline: str | None = None            # None when INCONCLUSIVE
    inconclusive: list[str] = field(default_factory=list)
    research_line: str | None = None       # A3
    coherence_warning: str | None = None   # A7
    cycle_rows: list[dict] = field(default_factory=list)   # A4
    champion_line: str | None = None
    narrow_frame_line: str | None = None
    trust: str = "DIRECTIONAL"
    trust_note: str = ""
    lever_heading: str = ""

    # the numbers
    glance: Glance = field(default_factory=Glance)
    within_dispositions: list[str] = field(default_factory=list)

    # the diagnosis, counted (derived from report.pain_map)
    diagnosis: DiagnosisOverview = field(default_factory=DiagnosisOverview)

    # every consumer type in the panel, in AND out of target (from L3)
    panel: PanelResponse = field(default_factory=PanelResponse)

    # honesty surfaces
    disclaimer: str = DISCLAIMER
    funnel_note: str | None = FUNNEL_OFF_NOTE
    panel_degraded: str | None = None
    # v2.1 two-axis audience match. declared_* / inferred_* are context; the
    # WARNING is the guardrail — the creative reads as aimed at someone other
    # than the audience being bought. On a brand manager's own ad the declared
    # targeting is real and often off, and a confident headline printed over a
    # silent mismatch is exactly the failure this exists to prevent.
    audience_mismatch: str | None = None
    # The other half of the two-axis verdict. `audience_mismatch` is the
    # guardrail and fires only on a gross gap; this is the same check passing,
    # and it is worth stating rather than leaving as silence — "we checked who
    # this ad reads as aimed at, and it matches your buy" is a claim, and a
    # blank space where a mismatch warning would have been is not.
    audience_aligned: str | None = None
    declared_audience: str = ""
    inferred_audience: str = ""

    @property
    def within_label(self) -> str:
        return (humanize(", ".join(self.within_dispositions))
                if self.within_dispositions else "your target")

    @property
    def target_n(self) -> int:
        """People in the panel read as the target.

        Sourced from the panel tally rather than glance.n. The two agree by
        construction today — both filter the same L3 distributions by the same
        within-target set — but they answer different questions: the glance is
        "what did the thumb do", the tally is "how many people are we talking
        about". The zone labels on the problem map ask the second one.
        """
        return self.panel.in_tally[0]

    @property
    def outside_n(self) -> int:
        return self.panel.out_tally[0]

    @property
    def flag_lines(self) -> list[str]:
        """Methodology flags in plain words, for a surface a client reads."""
        return [flag_text(f) for f in self.report.methodology_flags]


def _load_report(run_dir: Path) -> tuple[Report, dict, str]:
    """Resolve the Report from a finished run directory.

    Two legitimate sources: the normal path writes it into run.json at
    status='complete'; a run recovered by replay_synthesis after a mid-run
    crash writes replay_report.json instead. Fail LOUDLY when neither
    exists — rendering a blank report for a prospect is far worse than an
    error, and a crashed run is exactly the case that produces one.
    """
    run_json = run_dir / "run.json"
    if not run_json.exists():
        raise FileNotFoundError(f"no run.json in {run_dir} — not a run directory")
    raw = json.loads(run_json.read_text())

    payload = raw.get("report")
    if payload:
        return Report.from_dict(payload), raw, "run.json"

    replay = run_dir / "replay_report.json"
    if replay.exists():
        return Report.from_dict(json.loads(replay.read_text())), raw, "replay_report.json"

    raise ValueError(
        f"run {run_dir.name} carries no Report (status={raw.get('status')!r}). "
        "The run did not reach 'complete' and no replay_report.json exists. "
        "Recover it with replay_synthesis before rendering — do NOT render a "
        "partial read."
    )


def build_read_model(run_dir: str | Path) -> ReadModel:
    """Build the presentation model from a finished run directory."""
    run_dir = Path(run_dir)
    report, raw, source = _load_report(run_dir)
    config = raw.get("config", {}) or {}
    d = report.decision

    asset = config.get("asset", {}) or {}
    asset_path = Path(asset["image_path"]) if asset.get("image_path") else None
    spec = config.get("audience_spec", {}) or {}
    creative = config.get("creative_inputs", {}) or {}

    purpose = creative.get("purpose") or "direct_sell"
    preset = resolve_purpose(purpose)

    model = ReadModel(
        run_id=raw.get("run_id", run_dir.name),
        run_dir=run_dir,
        report=report,
        report_source=source,
        generated_at=raw.get("updated_at", ""),
        asset_label=asset.get("label", ""),
        asset_path=asset_path,
        category=config.get("category", ""),
        account_id=config.get("account_id", ""),
        brand_profile_id=config.get("brand_profile_id", ""),
        declared_targeting=config.get("declared_targeting", ""),
        panel_size=int(spec.get("panel_size") or 0),
        purpose=purpose,
        purpose_label=preset.label,
        purpose_metric_label=preset.metric_label,
        scope_note=purpose_scope_note(purpose),
        funnel_note=(FUNNEL_WITHHELD_NOTE if report.funnel_projection is not None
                     else FUNNEL_OFF_NOTE),
    )

    # Set before the legacy early-return below: a pre-2.3 report has no
    # decision layer but still carries a pain_map, and the diagnosis is
    # exactly the layer that survives when the decision one doesn't.
    model.diagnosis = build_diagnosis_overview(report)

    am = report.audience_match
    if am is not None:
        model.declared_audience = am.declared_summary or ""
        model.inferred_audience = am.inferred_summary or ""
        if am.verdict == "mismatched":
            model.audience_mismatch = am.message
        elif am.verdict == "aligned":
            # Synthesised when the model left `message` empty rather than
            # rendering an alignment chip with nothing next to it.
            model.audience_aligned = am.message or (
                f"The creative's apparent target ({am.inferred_summary}) is "
                f"consistent with the declared audience ({am.declared_summary})."
                if am.inferred_summary and am.declared_summary else
                "The creative's apparent target is consistent with the "
                "declared audience."
            )

    # Panel degradation is honesty-relevant on a client artifact: a read built
    # on a partially-landed panel must not look like a clean deterministic one.
    health = raw.get("panel_health") or {}
    if health.get("degraded"):
        model.panel_degraded = (
            f"{health.get('succeeded', '?')} of {health.get('expected', '?')} "
            "simulated respondents completed; a few dropped out mid-run. The "
            "read stands, but it rests on a slightly smaller sample than planned."
        )

    if d is None:
        # Legacy pre-2.3 report: no decision layer. Keep it honest rather than
        # inventing a decision — the bet ranking is all there is.
        model.decision_name = "INCONCLUSIVE"
        model.tagline = DECISION_TAGLINE["INCONCLUSIVE"]
        model.inconclusive = inconclusive_lines(report)
        model.lever_heading = LEVER_HEADING["INCONCLUSIVE"]
        return model

    model.decision_name = d.decision
    model.tagline = DECISION_TAGLINE.get(d.decision, "")
    model.trust = d.trust
    model.trust_note = trust_line(d)
    model.lever_heading = LEVER_HEADING.get(d.decision, "ACTIONS:")
    model.within_dispositions = list(d.within_dispositions)
    model.is_inconclusive = d.decision == "INCONCLUSIVE"

    if model.is_inconclusive:
        # Never surface an action rate here — the read is untrustworthy by
        # definition, even when target_action_rate happens to be non-None.
        model.inconclusive = inconclusive_lines(report)
    elif d.target_action_rate is not None:
        model.headline = headline_metric_line(d)
        # A3: the "would research" companion — reported SEPARATELY, never
        # folded into the buy headline. Buy-frame jobs only.
        if (d.research_rate is not None and d.research_denom
                and preset.name in ("direct_sell", "retain_winback")):
            model.research_line = (
                f"Separately, {d.research_rate:.0%} would look it up first "
                f"({d.research_num} of {d.research_denom}) — research, not a purchase."
            )
        if d.coherence_incoherent:
            model.coherence_warning = (
                "Coherence check: buy-now intent was stated, but every one of "
                "those people scrolled past without even stopping on the ad — "
                "treat the buy number with caution."
            )
        # A4: the mix-independent read — the per-cycle breakdown so the blended
        # headline never hides its cycle-mix assumption.
        for pos in CYCLE_ORDER:
            c = (d.by_cycle_position or {}).get(pos)
            if c:
                model.cycle_rows.append({
                    "key": pos, "label": CYCLE_LABEL[pos], "rate": c["rate"],
                    "num": c["num"], "denom": c["denom"],
                })
        if d.decision == "RETARGET" and d.champion_disposition:
            rate = (f"{d.champion_action_rate:.0%}"
                    if d.champion_action_rate is not None else "a higher rate")
            model.champion_line = (
                f"But the {humanize(d.champion_disposition)} — whom you are NOT "
                f"targeting — acts at {rate}. Right ad, wrong person."
            )
        elif d.decision in ("ITERATE", "REBUILD") and preset.audience_frame == "narrow":
            model.narrow_frame_line = (
                "It reaches no one else (everyone else scrolls — expected; "
                "tighten targeting)."
            )
    else:
        model.headline = None
        model.inconclusive = [f"  No trustworthy within-target read — {d.rationale}."]

    # The behavioural data needs L3 — it is not carried on the Report.
    #
    # Read it whenever it exists, NOT only when there is a within-target set.
    # The old condition made every out-of-target respondent unreachable on any
    # run with no target set, and unreachable full stop for the panel table:
    # who ELSE responded is exactly the question the in-target filter hides.
    l3_path = run_dir / "l3_summary.json"
    if l3_path.exists():
        l3 = json.loads(l3_path.read_text())
        dists = l3.get("segment_behavioral_distributions", {}) or {}
        if model.within_dispositions:
            model.glance = within_target_glance(dists, model.within_dispositions)
        model.panel = build_panel_response(dists, model.within_dispositions)

    return model
