# The engine improvement plan

**2026-08-04.** Everything we now know to change, in the order the evidence supports. Assembled
from our own measurements (`HANDOFF.md`, and §0 below) and from `docs/research/`.

**Two labels on every item, and they are not the same thing:**
- **[MEASURED]** — observed in our own runs. Not an opinion.
- **[LITERATURE]** — recommended by outside research. Grade follows the source's own confidence.

**A third label says what it costs to know if it worked:** **[$0]** offline · **[$4]** one paid run
· **[$4×n]** more.

⚠ **Status, 2026-08-04: §1 and §5.1 are now BUILT — see "What shipped" below.**
Everything in §2, §3 and §4 is still plan, not changelog.

---

## ⭐ What shipped, 2026-08-04 — the whole `$0` tier

All of §1 and §5.1, plus the gate test as runnable code. No engine change, no
paid run, and every item is visible on the runs already on disk.

| item | what it does now |
|---|---|
| **§1.1** | The problem chip reads **"3 of 5 consumer types · quoted from 4 people"** instead of "3 types". `read_model.breadth_line` composes it; `grounding.attribute_quotes_to_agents` traces each pain's quotes back to the transcripts that contain them. |
| **§1.2** | `read_model.split_changes_by_target` — a fix resting **only** on out-of-target problems is shown under **NOT RANKED** with its reason, on the page and in the CLI. |
| **§1.3** | Brand-relative panel agreement as a **methodology row**, not a flag. See "why the flag stays suppressed" below. |
| **§1.4** | `read_model.SEGMENT_CAVEAT`, on the panel table and the champion line. |
| **§1.5** | `read_model.HEADLINE_CAVEAT`, directly under the number, in every state that renders one. The number **keeps its position** — the user's call, 2026-08-04. |
| **§5.1** | `run.json` now stamps `disposition_version` (was the literal `"auto"` on every run ever made), `panel_version`, `funnel_enabled`, `vector_schema_version` and **fingerprints of every static prompt template**. `scripts/freeze_config.py` prints the record to publish beside a result. |
| **§0a/§0b** | `scripts/gate_test.py` — the measurement below, re-runnable for `$0` after any engine change. It previously existed only as prose in this file. |

**Three things learned while building it, each of which changed the design:**

1. ⚠ **A per-pain count of PEOPLE cannot be derived from what the engine
   records, and must not be faked.** `cited_by` holds disposition *labels*;
   `Quote` carries no agent id; L2/L3 collapse agents to histograms.
   `synthesis_assess.py:424` is the last point at which agent identity exists,
   and it evaporates into prompt text. Dispositions are 15–24 agents each, so
   rendering "19 people" for a pain that 3 may have raised would inflate in the
   flattering direction — the very defect §1.1 exists to fix. **What ships is a
   count of consumer types with its denominator, plus a count of people whose
   own words are quoted.** The second number is **bounded by quotes emitted**
   (the distribution across 110 pains is 2 quotes: 9, 3: 64, 4: 37, so it is
   always 2–4). **It is a grounding count, not prevalence. Never promote it.**
   Emitting agent ids from the assess pass would fix this properly — a schema +
   prompt change, and therefore `$4` to see.
2. ⚠ **`cited_by` is never validated against the panel.** On 2 of 183 citations
   the assess pass named a consumer type **that was not in that run's panel at
   all**, inflating the chip by one. The chip now counts against the panel that
   really ran.
3. ⚠ **§1.2's "<5% of the panel" floor cannot bind and was replaced.** At 15–24
   agents per disposition, no pain cited by even one type falls under 5%. The
   rule that does bind — and is deterministic — is out-of-target-only, which
   catches 2 of 51 ranked changes on disk, with 8 more mixing insiders and
   outsiders. Mixed fixes stay ranked.

⚠ **Not closed: `bet_ranking` is exempt from the floor.** The numbered levers
are free text with **no reference to any pain id**, so there is no deterministic
way to tell whether a lever leans on a demoted fix. They are passed through
untouched and unreordered rather than filtered on a guess. Giving bets a
`derives_from_pains` field is the real fix, and it is an engine change.

### Why `homogenization_high` stays suppressed (§1.3)

`ROADMAP.md` proposed replacing the suppressed flag with a **>2σ brand-relative
detector**. Measured against the runs on disk, **that flag would never fire**:
health_wellness_demo across 15 v3 runs is mean **0.69**, sd **0.16**, max
**0.87** — against a 2σ bar of **1.01**. A guardrail that cannot fire is worse
than none, because it reads as a check that passed. So the number and its
context ship as an observation and **both suppression sites stay**. Baselines
are scoped by brand *and* protocol: v2 and v3 measure **0.60 vs 0.69** on the
same brand, so pooling them compares a run against a different instrument.

---

## §0 THE GATE — run this before building anything, and be willing to stop

The research's sharpest warning (`05_deeper_dive.md`): a panel can produce output that *perfectly
matches the human distribution shape* while having **no power to tell one product from another**.
Fluent, plausible, well-shaped — and decoration.

**Two of the three gate tests are already run.** Results below, from runs on disk, `$0`.

### 0a. Does the headline number discriminate? **[MEASURED] — NO** ⚠

Restricted to `reaction-v3` runs only (the v2 runs are a different protocol and were wrongly
included in a first pass):

| | spread |
|---|---|
| **Within-ad noise** — MuscleBlaze ×4, same ad, same protocol: `11.1%, 0%, 5.3%, 0%` | **0.111** |
| **Between-ad signal** — 6 different ads: `11.1%, 0%, 0%, 0%, 0%, 0%` | **0.111** |

**Signal-to-noise = 1.0.** Five of six different ads read **exactly 0%**, and the only non-zero ad
is the same one whose repeats span 0–11%. The entire between-ad "signal" is one ad's run-to-run
noise.

⚠ Caveats, stated honestly: denominators are small (5, 5, 18, 24, 24, 47) — `0/5` carries almost no
information, and those runs already fly `single_within_target`. But the direction is not in doubt,
and it corroborates what `HANDOFF.md` already said: *"buy-intent reads 0% on six of the last eight
runs, and a tile that says 0% every time cannot lead."*

**Consequence: the buy-intent headline is not a measurement. It must never be the basis of a
recommendation, and the read should stop presenting it as if it discriminates.**

### 0b. Does the PROBLEM MAP discriminate? **[MEASURED] — YES** ⭐

Jaccard overlap on pain vocabulary, `reaction-v3` runs:

| | mean | range |
|---|---|---|
| **Same ad, re-run** (n=6 pairs) | **0.231** | 0.201 – 0.277 |
| **Different ads** (n=15 pairs) | **0.148** | 0.106 – 0.176 |

**The ranges do not overlap.** The lowest same-ad pair (0.201) beats the highest different-ad pair
(0.176). The diagnosis is genuinely ad-specific, not boilerplate.

⭐ **This vindicates the design decision to make the problem map the hero instead of the number** —
and it is the first hard evidence that the instrument carries real signal at all.

⚠ **But same-ad stability is only 0.231.** Two runs of the *same* ad share under a quarter of their
pain vocabulary. It discriminates; it is not yet repeatable. Both facts are true and the read
should reflect both.

⭐ **Both are now runnable as code: `.venv/bin/python scripts/gate_test.py` ($0).**
It reproduces §0a exactly (0.111 / 0.111, signal-to-noise 1.00) and §0b to within
rounding. It also reports §0b under **four tokenizations** rather than one,
because there is no single right answer and the same class of arbitrary choice
moved published human-vs-silicon correlations from r = .23 to .84. **The
separation holds under all four** — which is a stronger result than the single
figure below. The numbers quoted here are the stop+len>3 row (that variant
measures 0.234 / 0.148 against the 0.231 / 0.148 published above; the difference
is a stopword-list detail, and it is a small live demonstration of exactly the
analytic-flexibility problem §5.1 is about).

### 0c. QC1/QC2 convex-combination check — **[MEASURED] 2026-08-06 — NO VIOLATION** ⭐
Neumann et al.: is the panel-wide average a valid convex combination of the subgroup averages?
**~80% of tested models fail this** — producing an "average" more extreme than every subgroup,
which is geometrically impossible. Free, and it is a bug-finder.

**Ran clean.** Now `scripts/gate_test.py` §0c, so it re-runs after every engine change at $0.

| check | what it asserts | coverage on disk |
|---|---|---|
| **QC1** pooling identity | the population distribution IS its segments summed — an **integer** identity, no rounding excuse | 9 runs × **15 segments** |
| **QC2** funnel convexity | every `overall` funnel rate lies inside the range its segments span, both directions | 9 runs |
| **QC3** headline vs cycle | `target_action_num/denom` equals the sum over `by_cycle_position` — an exact identity, **stronger than QC2** | 7 runs, 2 skipped |

⭐ **Why it passed, and why that is a real result rather than a null one:** the failure mode
Neumann measures needs the average to be **GENERATED**. This engine counts every distribution in
Python (`agent/decision.py`, the "distributions are Python" invariant) and the model emits no
number at all — so the only way convexity could break here is a **frame mismatch**: two code paths
counting over different populations while claiming to decompose each other. QC3 is the sharp
instrument for exactly that, because `within_target_action_rate` (via
`compute_behavioral_distribution`) and `_buy_intent_by_cycle` are **two independent
implementations** of one count, and they were verified to share both the frame and the
`_BUY_INTENT_NEXT_STEPS` predicate. **`decision.py`'s claim that the headline "is a weighted
average over the panel's realised cycle mix" is TRUE**, and now pinned.

⚠ **Checked and NOT defects, recorded so they are not re-investigated:**
- `l3_summary.context_fit` is `{}` and `confidence_signals.total_contexts` is `0` on every v3 run.
  **Intended** — L3 stopped making that call (rocket-2.2.0 Phase 7) and the assess pass owns
  `context_fit` now. `single_context_only` derives `n_contexts` **fresh from the transcripts**, so
  nothing consumes the dead counters.
- `report.funnel_projection` is `None` on every run while `l35_projection.json` holds a full
  projection. **Intended** — it attaches only under `--funnel`; the projection is computed and
  persisted either way, and `FUNNEL_OFF_NOTE` says so accurately.
- ⚠ **QC2 deliberately does not check the confidence BANDS.** `_band_halfwidth_fraction` widens
  with small `n`, so the pooled panel's band is legitimately **tighter** than every segment's —
  more evidence, not a violation. Extending QC2 over the bands would look like rigour and would
  false-fire on every healthy run. `test_qc2_deliberately_ignores_the_confidence_bands` pins it.

⚠ **The detectors are mutation-proved (7/7), and that is the load-bearing part.** 0c reports no
violation on disk — which is byte-identical to what a checker pointed at the wrong field would
report. `tests/test_gate_test.py` breaks each detector on purpose (one-sided QC2, `n`-only QC1,
numerator-only QC3, an unfiltered loader) and every mutation fails a test.

---

## §1 THE REPORTING LAYER — no engine change, no paid run

Highest value per unit of risk. Every item is **[$0]**.

**1.1 Count PEOPLE, not disposition labels.** **[MEASURED]**
`cited_by` stores disposition labels. A pain cited by 4 agents and one cited by 40 both render as
"1 type". **The Nykaa recommendation came from 5 agents out of 100** and shipped as a top-3 ranked
change. Carry the agent count through `PainMap` → `ReadModel` → the card.

**1.2 A prevalence floor before a signal can be ranked.** **[MEASURED]**
There is no numeric threshold anywhere in the pipeline today. Something said by <5% of the panel
must not become a ranked recommendation. Exact floor to be set with the user — it is a product
decision, not a technical one.

**1.3 Stop suppressing the homogeneity flag — and change what it measures.** **[MEASURED]**
`compute_methodology_flags` deliberately never emits `homogenization_high` because it is
"structurally the default." It computed 4–16 against a threshold of 2 on **28 of 28 runs**. The
honest fix is not to un-suppress it as-is but to make it **brand-relative** — flag a run whose
homogeneity exceeds this brand's own rolling baseline. The code already logs the raw ratio for
exactly this.

**1.4 Caveat segment differences.** **[LITERATURE, strong]**
LLM panels inflate between-segment gaps **2–4×**, pick the wrong segment in **50–72%** of pairwise
comparisons, and **manufacture splits that do not exist in up to 41%** of cases. Our dashboard
reports segment differences as findings. They need a standing caveat.

**1.5 Demote the buy-intent headline.** **[MEASURED, §0a]**
Signal-to-noise 1.0. Keep it visible for honesty; stop letting it lead.

---

## §2 PANEL COMPOSITION — cheap, and the indefensible stuff

**2.1 De-duplicate the persona cores.** **[MEASURED]** **[$4 to see]**
"100 simulated consumers" is **29 distinct persona cores**; 95 of 100 share theirs with someone
else; up to **6 agents are literally the same person**; 10 distinct demographic blocks.
⚠ **Do this because 6 identical people is indefensible, NOT because it will fix the spread.**
Conditioning has a hard ceiling (persona variables explain **1.4–10.6%** of variance) and past ~15
variables it actively hurts. Expect an honesty win, not a diversity win.

**2.2 Use the chaos space we already defined.** **[MEASURED]** **[$4]**
4 dimensions × 3 values = **81 combinations. The panel uses 3**, and all four dials move in
lockstep — nobody is impulsive *and* risk-averse. This is a 3-position switch, not a chaos model.

**2.3 Scope dispositions to the category they were authored for.** **[MEASURED]**
The Nykaa anchor was written for **collagen/biotin**, where it is correct, then applied unchanged
to a **protein bar**. 43 of 100 persona cores carried the word before seeing any ad. A disposition
needs a declared scope, and reuse outside it needs to be a deliberate act.

**2.4 Skew the panel to light and non-buyers.** **[LITERATURE, strong]** **[$4]**
**~80% of a brand's buyers purchase it once a year or less**; ~30% of Coca-Cola's buyers don't buy
annually; only ~5% of B2B buyers are in-market. A panel of category-engaged people simulates the
heavy tail. ⭐ This should flatten over-eager responses **by itself, with no prompt trickery**.

**2.5 Seed personas from real respondents.** **[LITERATURE, strong]** **[$4]**
Park et al.: demographics-only **74%** → survey-only grounding **82%** → interview **83%**.
Survey-only ≈ interview-only, so the expensive qualitative step is not required. Törnberg's method:
seed each agent from a real survey respondent, let the model expand only what the survey lacks.
Directly attacks 2.1. ⚠ Requires real respondent data we do not have — see §5.

**2.6 Lighten demographic conditioning, especially income.** **[LITERATURE, SimBench]**
Conditioning penalties: **income −4.51**, political −4.97, religiosity −9.91; **age −1.50 and
gender −1.24 are the safest**. Every targeting string we write carries `₹7–40 LPA`.

---

## §3 THE REACTION PROTOCOL — stimulus-side, and the novel part

⚠ **The governing principle** (ABxLab, 17 models, 80,000+ trials): *agents reproduce human
heuristics without the cognitive constraints that motivate them.* **Only removing information from
the context is a real constraint. Describing one in the prompt is theatre.**

**3.1 Fix the recall call.** **[MEASURED]** **[$4]**
Call B asks *"it's a day or two later, what do you remember?"* with **the ad image and the agent's
own fresh answers still in context**. It is reporting recall while looking at the ad.
⭐ **The cost objection is weaker than assumed:** telemetry shows the agent layer got **zero cache
reads on one of the two runs tonight** (328K input tokens, no cache) and 192K on the other. Caching
is already inconsistent, so dropping the image from Call B may be close to free. **Verify per-run
before deciding.**

**3.2 Exposure distribution — most agents never really see it.** **[LITERATURE, strong]** **[$4]**
Lumen: only **~35% of ads get any views**; **9% exceed 1 second**; **4% exceed 2 seconds**. Google:
**56% never seen by a human**. Today all 100 of our agents look properly.
**And keep non-exposed agents in every denominator** — dropping them silently restores the inflated
number, the same trap as our in/out-of-target bimodality.

**3.3 Truncate the stimulus by exposure tier.** **[LITERATURE — NO PUBLISHED PRECEDENT]** **[$4×2]**
The only intervention that creates *real* rather than performed inattention: short-exposure agents
see a crop, not the full asset. ⭐ Gives a **testable discriminant** via the 1.5-second
distinctive-assets finding: agents with strong prior brand associations should identify the brand
from the crop; agents without should not.
⚠ **We would be generating this evidence, not importing it.**

**3.4 Two-stage: scroll-decision, then reaction.** **[LITERATURE — structure peer-reviewed]** **[$4×2]**
Epstein et al.: **stage 1 (dwell) favours sensational content; stage 2 (engagement) favours
credible content** — partly opposed forces. A single-stage panel conflates them.
⚠ Do not reuse the same scoring ruler across the two stages.

**3.5 Move the questions from evaluation to memory.** **[LITERATURE, Heath 2006]** **[$4]**
Heath: attention is **negatively** associated with brand-relationship strength; cognitive content
has little effect, emotive content does. High attention recruits counter-argument — the process
real exposure bypasses. So ask *whose ad was that? what did it remind you of? when would something
like that come to mind?* rather than *what do you think of this ad.*
⚠ This interacts with the probe-contamination finding already in memory — any always-on reflection
question can prime the metric. **Change one question at a time.**

**3.6 Model the cynic.** **[LITERATURE, SimBench]**
Models score **worse than a uniform baseline** on traits conflicting with alignment —
Machiavellianism, conspiracy, humour. The dismissive or joking consumer is not weakly modelled, it
is **anti-informative**. We currently render that person as politely disengaged.

**3.7 Give agents confirmation bias.** **[LITERATURE, moderate]** **[$4]**
Diversity rose **0.60 → 1.24** with strong confirmation bias; without it, opinions *"quickly
converge towards the truth"* even under false framing. This is persona-side (what evidence an agent
accepts), not narration-side, so it survives the §3 principle.

---

## §4 SAMPLING — the cheapest real diversity win

**4.1 Verbalized Sampling.** **[LITERATURE, strong]** **[$4]**
Ask for a *distribution* of responses with probabilities rather than one response. Training-free.
Recovers **66.8% of base-model diversity**; **1.6–2.1×** diversity gain; ⭐ **"on social dialogue
simulation… some models performing on par with a dedicated fine-tuned model."**
Mechanism: an instance prompt returns the mode; a distribution prompt returns the spread.
**We ask 100 agents for one reaction each — 100 draws at the mode.**
Orthogonal to temperature/top-p; larger models gain 1.5–2× more.
⚠ Tension: it is distribution-level, and our per-agent quotes are a product feature. The hybrid —
VS for the numbers, per-agent generation for the quotes — is untested by anyone.

**4.2 Accept the instruction-tuning ceiling instead of prompt-engineering at it.** **[LITERATURE]**
SimBench, **r = −0.942**: instruction tuning helps up to **40 points** where humans agree and is
**"actively detrimental"** where they disagree most. **Ad reactions are a high-disagreement
question.** This is our homogeneity problem named by an independent benchmark, and it explains why
our register is good while our spread is bad. No amount of persona prose fixes it; sampling might.

---

## §5 VALIDATION — the only thing that converts any of this into truth

**5.1 Freeze the configuration BEFORE the human panel runs.** **[LITERATURE]** **[$0]**
⚠ Across **66 defensible configurations** of the same task on the same data, human-vs-silicon
correlation ranged **r = .23 to .84**. Researcher degrees of freedom swamp the effect. We have made
dozens of these choices. **Write down and publish the config with the result**, or we will tune our
way to a good number and learn nothing. This is free and it must happen first.

**5.2 ~100 real human reactions + statistical rectification.** **[LITERATURE, strongest]**
Bias **34.66% → 2.82%** with as few as ~100 real responses (~1% of a full survey). With a
1,000-response budget, **~20% to fine-tuning and ~80% to rectification** minimises bias — the
opposite of most teams' instinct. ⭐ **Highest evidence-per-dollar item in the entire research set**,
and the tooling already exists in `panel/v3_human_panel/`.

**5.3 Calibration targets to aim at.** **[LITERATURE]**
**~38%** correct brand recall among exposed · **~85%** of impressions below the 2.5s memory
threshold · **~6–7%** brand-choice uplift · **<10%** correct content recall for a glanced banner.
Our panel currently produces **100% comprehension**, including from the 87 who scrolled past.

**5.4 The ceiling to design around.** **[LITERATURE, SimBench]**
Best model in the field: **40.80/100** — *"closer to a uniform distribution than to the human
ground truth"*, closing ~40% of the gap to perfect. Nothing we do beats that ceiling. Our
confidence language must survive it. `VERDICT_CAVEAT` already carries the spirit.

**5.5 Disclosure is now an industry requirement — and an asset.** **[LITERATURE]** **[$0]**
The ICC/ESOMAR Code distinguishes a "person" from a "synthetic persona"; MRS guidance (1 May)
requires clear disclosure of AI-generated output and states synthetic data should **complement, not
replace** human insight. ⭐ **We already comply in three places.** Several competitors market
accuracy numbers their own published definitions do not support.

---

## §6 ⚠ DO NOT DO THESE

Every one is something a fresh session would propose on day one.

| don't | why |
|---|---|
| **Add a social/discussion layer between agents** | Makes convergence **worse**. Conformity 39%→74% beside one confident peer; debate *lowers* accuracy; OASIS found **no herd effect at 100 agents** — our size. |
| **Switch off Claude for the agent layer** | Claude-3.7-Sonnet is **top of all 45 models** on SimBench (40.80). The earlier "Claude scored worst" note was a misread of ΔS and is corrected in `04_simbench_read.md`. |
| **Fine-tune on reviews or forum posts** | Buys review-*shaped* text, not consumer-*shaped* judgement. Measured: surrogates inflate positivity by 15–22 points and **dissolve the correlational structure** (0.40 → 0.04). 50–100 examples buys format; millions buy fidelity. |
| **Use preference-tuning (DPO/RLHF) on anything** | It is what *causes* diversity collapse. Also costs 2× LoRA SFT. |
| **Put "you are distracted, you barely glance" in the prompt** | Actively contraindicated. Produces a *performance* of distraction — fluent, stereotyped, uniform. Highest-risk change precisely because it is cheapest and looks most convincing. |
| **Add more demographic conditioning** | Past ~15 variables it *hurts* (KL 1.10 → 2.76). Income is among the worst axes. |
| **Re-add the commit gates** | The user's explicit call, 2026-08-03. Unrelated to this plan; listed so it is not "fixed" back. |

---

## §7 SUGGESTED ORDER, AND WHAT IT COSTS

Ordered by evidential defensibility, which is not the same as impact.

| # | what | cost |
|---|---|---|
| 1 | §0c QC1/QC2 diagnostic | **$0** |
| 2 | §1 the whole reporting layer (count people, floor, homogeneity, caveats, demote headline) | **$0** |
| 3 | §5.1 freeze and publish the config | **$0** |
| 4 | §2.3 scope dispositions · §2.1 de-duplicate cores · §2.2 real chaos | **$4** (one run to see) |
| 5 | §2.4 light-buyer skew | **$4** |
| 6 | §4.1 Verbalized Sampling | **$4** |
| 7 | §3.1 fix the recall call | **$4** (verify cache first) |
| 8 | §3.2 exposure distribution + denominators | **$4** |
| 9 | §3.5 memory-shaped questions (**one at a time**) | **$4×n** |
| 10 | §3.3 truncation · §3.4 two-stage gate — **no published precedent** | **$4×2 each** |
| 11 | §5.2 human panel + rectification — **the one that converts this to truth** | recruiting |

⚠ **Roughly $40–60 of paid runs to see items 4–10, and that is the real cost of this plan — not the
implementation.** Items 1–3 are free and should happen regardless. **The order below item 3 is the
user's call, not the plan's.**

⭐ **If forced to pick three: §1 (free, fixes the Nykaa class of defect), §4.1 (cheapest real
diversity win, matched a fine-tuned model), §5.2 (the only item that turns any of this into
evidence).**
