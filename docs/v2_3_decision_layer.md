# v2.3 — The Decision Layer

*Replacing "MIXED @ 72" with a call a brand manager can act on.*

Status: **BUILT + merged** (P1–P3, 2026-07-10; `rocket-2.3.0`). Advisor-reviewed.
SCALE was gated (§7) and is now un-gated behind a **provisional** desk-research bar
(§7a, `decision-2`) — a documented, user-accepted **known risk**, to be recalibrated
against the deliberately-strong anchor run after v2.4 locks.

---

## 1. The problem (proven, not asserted)

Across **42 stored runs** spanning every category (protein, coffee, audio,
chocolate, personal-care), the top verdict `WORKING` has fired **zero times**:

| verdict | share |
|---|---|
| WORKING | **0 %** |
| MIXED | 62 % |
| FAILING | 24 % |
| METHODOLOGY_GAP | 14 % |

`MIXED` is not a signal; it is the base rate. And it is squeezed from **both**
sides by design:

- It cannot rise to `WORKING`, whose definition ("no broad negative consensus,
  friction is execution-level only") is effectively unreachable once we simulate
  a real audience across 4 scroll-moments × 3 decision-styles — *some of the
  target always defers or scrolls*, so the MIXED clause "some convert, others
  surface resolvable friction" is nearly always true.
- It is deliberately kept from falling to `FAILING`: the counterweight rule
  routes resolvable (in-scope) friction to "MIXED with a recommendation," so
  fixable-but-weak ads pool in MIXED too.

**The killer evidence** — four ads, the label vs. the truth underneath it:

| Ad | Label | % of **target** who'd act | Top target-pain |
|---|---|---|---|
| MB whey | MIXED 82 | **68 %** | execution (fixable) |
| Buzzword (Herbyvore) | MIXED 76 | **25 %** | execution |
| TWT pack | MIXED 74 | **0 %** (skeptic) — 9 others engaged | structural |
| ProSki cereal | FAILING 82 | 9 % | structural |

Three ads all read "MIXED," within 8 confidence points — while the fraction of
their **intended audience** that would actually move ranges **0 % → 68 %**. The
label hides the only number that matters.

**The mandate (from the user):** a brand manager is trusting us with their time;
*every word they read must be helpful.* "MIXED @ 72" is not help. Only a decision
and a solid insight are.

---

## 2. Principle: split DIAGNOSIS from DECISION

The verdict isn't broken — it discriminates fine at FAILING, and the PainMap
beneath it is already the real product. The defect is that **one word is doing a
diagnosis job and a decision job at once.**

So we split them:

- **Diagnosis** (`WORKING`/`MIXED`/`FAILING`/`METHODOLOGY_GAP`) stays — but becomes
  an **internal** clinical read. It feeds the decision, lives in `run.json` and
  logs, and is never the headline a marketer reads.
- **Decision** (new) is what the brand manager reads: a call, the one number that
  matters, the highest-leverage lever, and how much to trust it.

The brand manager never reads "MIXED @ 72" again.

---

## 3. The headline metric — within-target action rate

**Definition:** of the agents whose disposition is classified `within` (the
people this ad is *for*), the fraction with `would_act_within_week = true`.

It is computed purely in Python from signals we already have
(`behavioral_distribution.would_act_within_week_count` summed over within-target
segments ÷ their n). No new model output.

**Why it's the right number:** it discriminates a 0→68 % spread where the label
gives three identical "MIXED"s (see §1 table). It is a **direct** behavioral
signal (what the agents said they'd *do*), not the derived `heuristic_v1` funnel
multipliers — so it is honest to headline today, while the funnel projection is
not (see §7).

**How it's framed** (never a naked number):

> *"This ad reaches the serious lifter — and **68 % of them would act**. It reaches
> no one else; everyone else scrolls, which is expected — tighten targeting."*

For a RETARGET ad the same metric tells the re-aim story:

> *"**0 %** of the lapsed skeptic you're aiming at would act — but the on-spec
> lifter, whom you're **not** targeting, engaged. You're pitching the right ad to
> the wrong person."*

The metric is always **decision-framed** — the decision (§4) gives it its meaning.

---

## 4. The Decision axis

Five states. Four are fully definable today; SCALE's threshold is gated (§7).

| Decision | Meaning | Budget action |
|---|---|---|
| **SCALE** | Target converts strongly; no in-scope lever would materially lift it. | Put spend behind it. |
| **ITERATE** | Target responds, but a specific in-scope lever is leaking conversion. | Fix the lever, re-run, then scale. |
| **RETARGET** | The creative works — for a different/narrower audience than it's aimed at. | Fix the buy, not the ad. |
| **REBUILD** | The target rejects it on grounds no in-scope lever fixes. | Don't run as-is; start over (we say whether a rebuild can win). |
| **INCONCLUSIVE** | The read isn't trustworthy (pool mismatch / ambiguous target). | We say why, and what to change to get a real read. |

### The decision function (deterministic, first-match)

Inputs — all already computed by the assess pass:
- `A_within` — within-target action rate (§3)
- action **by disposition** (to detect "works for someone else")
- `top_within_pain.severity` ∈ {execution, structural} — already tagged per pain
- `audience_match` ∈ {aligned, mismatched}
- `verdict` / `methodology_flags` (the internal diagnosis)

```
0. verdict == METHODOLOGY_GAP                          -> INCONCLUSIVE
1. audience_match == mismatched
   OR (A_within low  AND some outside/ambiguous
       disposition acts materially more)               -> RETARGET
2. load-bearing within-target pain is STRUCTURAL
   AND no reachable target elsewhere                   -> REBUILD
3. load-bearing within-target pain is EXECUTION
   AND A_within is meaningful                          -> ITERATE
4. A_within strong AND no material in-scope lever left -> SCALE   [threshold gated §7]
```

- **ITERATE** carries an **effort read** = number of material in-scope levers, and
  ranks them by the within-target prevalence of the pain each resolves ("this
  lever unblocks 6 of your 19 target buyers — fix it first").
- **RETARGET** names *who* it actually resonates with.
- **REBUILD** states *whether a rebuild can win* and on what.

### Worked on your real data

| Ad | A_within | severity | audience | → Decision | Headline the marketer reads |
|---|---|---|---|---|---|
| **MB whey** | 68 % | execution | aligned | **ITERATE** (1 lever) | "68 % of your lifters would act — one fix (show ₹/serving) stands between this and scale." |
| **Buzzword** | 25 % | execution | aligned | **ITERATE** (3 levers) | "Only 25 % of your target would act; three fixes needed — kill the AI-headline, add a credibility marker, hide the parent-co footer." |
| **TWT pack** | 0 % (skeptic) | structural | aligned* | **RETARGET** (+iterate) | "0 % of the lapsed skeptic you're aiming at would act — their block is behavioural, not trust. Re-aim at the on-spec lifter, who engaged." |
| **ProSki** | 9 % | structural | aligned | **REBUILD** | "Only 9 % would act, no audience champions it. The concept has legs; this execution loses on a format wall a tweak won't fix." |

Every output is a distinct, actionable call. None is "MIXED @ 7x."

\* TWT is demographically "aligned" yet mis-targeted at the *disposition* level —
which is exactly why RETARGET must trigger on the disposition-level action gap,
not only on `audience_match`.

---

## 5. Trust, reframed (confidence → plain language)

The `confidence` number is an internal QA gate; it is not help. Translate it:

- **HIGH** — "19 target buyers, consistent across all 4 scroll-moments."
- **DIRECTIONAL** — "only one narrow audience engaged; thin evidence — treat as a lead, not a verdict."

The number stays in the data; the brand manager reads the sentence.

---

## 6. Before / after (what the brand manager actually reads)

**Before**
```
MIXED 82
flags: single_within_target
[6 pains listed]
[bet ranking]
```

**After**
```
ITERATE — one fix stands between this and scale.

68% of your target (the serious lifter) would act. It reaches no one else
(everyone else scrolls — expected; tighten targeting).

THE ONE FIX:  Put ₹-per-serving on the creative.
  6 of your 19 target buyers stall here — they defer to a HealthKart price-check
  and reorder-inertia eats the decision. This is the lever between 68% and scale.
THEN: source the "50% absorption" claim in-frame.

Trust: HIGH — 19 target buyers, consistent across all four scroll-moments.
─────────────────────────────────────────────────────────────
[full PainMap + funnel below, for those who want the depth]
```

Every line is a decision or an action.

---

## 7. The no-shortcut boundary

Buildable **now** (no new data needed — all signals exist):
- within-target action rate + disposition-level action gap
- the ITERATE / RETARGET / REBUILD / INCONCLUSIVE decisions
- the trust reframe
- demoting the categorical verdict to internal

**Gated** — do **not** guess these:
- **The SCALE threshold**, and any recalibration of the internal `WORKING` bar.
  We have **zero** upper-anchor observations (0/42). Setting "how strong is
  ship-it strong" from theory risks stamping mediocre ads SCALE and destroying
  the FAILING/REBUILD discrimination that already works — the same unreachable-
  ceiling bug, moved up one level.
  **Prerequisite:** one **deliberately-strong creative** (~$2.50) engineered to
  satisfy every recurring within-target pain — price shown, claim certified, one
  clean target, no positioning break. It anchors where "strong" actually is.
  - Still MIXED internally but high A_within → we've proven the bar *and* own the
    anchor; set SCALE there.
  - Comes back genuinely strong → we learn the bar is fine; our four ads had real
    flaws. Either way we **learn**, not guess.

**UPDATE (2026-07-10):** §7 is now superseded by §7a — SCALE is un-gated behind a
**provisional** bar (an accepted, documented risk) rather than waiting on the run.

---

## 7a. The provisional SCALE bar (un-gated — KNOWN RISK, decision-2)

**Status:** LIVE but PROVISIONAL. `decision-2` un-gates SCALE behind a documented
best-guess bar. The empirical anchor run of §7 is **deferred to after v2.4 locks**;
until then this is a **known, user-accepted risk**, not a calibrated threshold.
Recalibrate against the deliberately-strong anchor run once v2.4 is done.

**The rule (composite — the magnitude is a backstop, not the driver):**

```
SCALE  iff  A_within >= _SCALE_FLOOR   (provisional 0.75, agent/decision.py)
       AND  no in-target lever is left  (no within-target pain survives to the
            SCALE branch: step 4 already excluded a structural within pain, so a
            None load-bearing pain here means zero within-target pains)
       AND  trust == HIGH               (>=2 within dispositions, no thin-evidence
            flag) — the anti-thin-evidence guard, see below
```

The "no lever left" clause does the real discrimination (it is why none of the four
flawed anchors can reach SCALE regardless of the number); the floor only stops a
*clean-but-weak* read from slipping through. Ordering is unchanged — SCALE sits
between REBUILD (step 4) and the ITERATE catch-all (step 6), so a mismatch, a
champion re-aim, an untrustworthy read, or a structural block all still win first.

**The HIGH-trust guard is load-bearing, not decoration.** Without it, the composite
fires *most easily* on the thinnest evidence: `A_within >= 0.75` is cheap on a small
within denominator (4/5 = 80%), and "no within pain survived" is *easier* when few
transcripts surface few pains — so a single-persona, DIRECTIONAL read would be the
path of least resistance into SCALE, inverting the very "fails toward ITERATE, never
false-SCALE" posture this provisional bar is sold on. Requiring HIGH trust (≥2 within
dispositions, no thin-evidence flag) closes that. **Consequence:** on today's
predominantly single-within-persona panels (e.g. MB whey's lone `enthusiast_macros_lifter`),
provisional SCALE will **rarely fire** — which is the intended *mild* failure
(understatement), not the costly one. Real SCALE coverage arrives with the post-v2.4
calibration (multi-persona targets + the measured floor).

**Why `_SCALE_FLOOR = 0.75` (the best guess, not a measured ceiling):**
- **Our own distribution.** The best *flawed* anchor (MB whey) tops out at **68%**
  within-target action *with three fixable execution pains*. A clean SCALE ad must
  clear our best flawed ad with margin → the floor sits above 68%.
- **Copy-testing norms, scaled up.** Industry "strong consideration" is a top-2-box
  purchase-intent **>40%** on a *general* sample. Our metric is (a) filtered to the
  *target persona* (not a general sample) and (b) a *simulated top-box*, which
  overstates real behaviour (only ~63% of "definitely would buy" actually convert;
  the Juster-scale literature documents the same inflation). Both effects push the
  equivalent bar well above 40% — 0.75 is a conservative landing between "clearly
  beats our best flawed ad" and "not so high it can never fire."
- **"Strong" is industry-defined as a *relative index to a norm*** (Kantar STSL 133
  vs 100 average; System1 above-average Star = 6× action-intent lift), not an
  absolute — which is exactly why the bar is anchored to *our* distribution, with
  the research only sizing the margin.

**Direction of error is deliberate.** Too-high only *understates* a great ad
(ITERATE instead of SCALE — a mild miss). Too-low stamps a mediocre ad SCALE and
tells a brand manager to put budget behind it — the costly error, and the whole
reason §7 gated it. So the bar fails toward ITERATE.

**What un-gating changed (code):** `_SCALE_FLOOR` + the SCALE branch in
`resolve_decision` (single source of truth for the number); `DECISION_VERSION →
decision-2`; `validate_report` now enforces SCALE's *structural* invariant (carries
a within-target rate, no load-bearing pain) instead of hard-rejecting it. Render was
already SCALE-ready (P3). Tests: `test_scale_branch` + updated schema invariants.

**Known seam (untested, don't chase now):** `validate_report` requires exactly 3
`top_3_changes` for a non-GAP report, but a true SCALE has nothing *in-target* to
fix. It will *probably* still carry 3 changes drawn from outside-target pains (as MB
whey does — P4/P5/P6), so it should validate — but the first real SCALE run is the
first live exercise of that path. Watch it there; do not special-case it pre-emptively.

**Calibration plan (unchanged intent, deferred timing):** after v2.4 locks, run the
deliberately-strong creative (a controlled edit of MB whey — show ₹/serving, give a
real reason-to-switch, substantiate the absorption claim, one clean target, no
positioning break) across a few seeds, read where A_within lands, and replace this
provisional floor (and possibly relax "no within pain at all" to "no *execution*
within pain") with a measured value. Bump to `decision-3` then.

---

## 8. Implementation sketch (phased, testable, commit-per-phase)

- **P1 — signals.** `within_target_action_rate()` + `action_by_disposition()` in a
  pure module over `AgentTranscript`/`behavioral_distribution`. Offline test.
- **P2 — decision function.** `resolve_decision(...)` mirroring the existing
  `resolve_verdict`/`compute_methodology_flags` pattern (deterministic, offline).
  Fixture the 4 stored runs; assert MB→ITERATE, TWT→RETARGET, ProSki→REBUILD,
  buzzword→ITERATE(3). Add `Report.decision` + `Report.target_action_rate`.
  Possibly add a `load_bearing: bool` tag to the top within pain (small assess
  addition) so "which pain drives the call" is explicit, not inferred from order.
- **P3 — render.** New brand-facing top-of-report (§6); move verdict/confidence to
  an internal "engine read" appendix. This is where "every word helps" is enforced.
- **P4 — anchor run + SCALE.** Run the deliberately-strong creative; set the SCALE
  threshold; decide whether to recalibrate the internal verdict.
- Version: `PROTOCOL_VERSION -> rocket-2.3.0`; new `DECISION_VERSION`.

---

## 9. Decisions (locked 2026-07-07)

1. **DROP the categorical verdict from the brand-facing view.** WORKING/MIXED/
   FAILING survives only as an internal "engine read" (in `run.json` + logs + an
   optional appendix), never as a headline. The brand manager reads the Decision
   (§4) + the within-target action rate (§3) + the trust line (§5).
2. **State names LOCKED for now:** SCALE / ITERATE / RETARGET / REBUILD (+
   INCONCLUSIVE). Revisit only if a real output reads awkwardly.
3. **Anchor-run gate CONFIRMED.** The deliberately-strong creative runs *later*,
   before SCALE's threshold or any internal-verdict recalibration is set. P1–P3
   (signals, decision function, render) proceed now; P4 (SCALE) waits on it.
