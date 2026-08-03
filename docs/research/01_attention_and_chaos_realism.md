# How ads are actually processed, and what that means for our panel

**Research report, 2026-08-04. Complete.** One of two agents that finished; the rest died on a
session limit and are recoverable from the raw transcripts (see `00_INDEX.md`).

Evidence labels used throughout: **[E]** follows from cited evidence · **[X]** the researcher's
extrapolation, no published precedent · **[E/X]** evidence-backed distribution, extrapolated mapping.

⚠ This report was NOT advisor-reviewed (the reviewer was rate-limited on all four attempts), and
its WebSearch budget ran out near the end. Two minor gaps are filled from secondary citations and
flagged inline. Treat the labels as the researcher's own, and re-verify anything load-bearing.

---

## 0. The headline, and it is not comfortable

> **There is essentially no published work that deliberately degrades an advertising stimulus, or
> an LLM agent's processing of it, in order to make simulated ad reactions more realistic.**

The literature validates the *problem* precisely and with numbers. The specific fix we are reaching
for is **unbuilt**. That is an opportunity, but it means we would be generating the evidence, not
importing it.

Everything demonstrated to work operates on **who the agents are** (persona, segmentation,
sampling). Everything on the **stimulus/exposure side is untested**.

---

## 1. The uniformity problem, measured

**Bisbee, Clinton, Dorff, Kenkel & Larson, "Synthetic Replacements for Human Survey Data? The
Perils of Large Language Models," *Political Analysis*** (peer-reviewed). 7,530 real ANES
respondents, 30 responses each = 3.6M synthetic responses.
- Variance so compressed that **33 synthetic respondents sufficed to detect an effect needing ~300
  real ones** — a ~9× false precision.
- **48% of regression coefficients** differed significantly from the real ANES counterpart; among
  those, **the sign flipped 32% of the time**.
- Identical prompts produced different distributions between April and July 2023 model versions.
- https://www.cambridge.org/core/journals/political-analysis/article/synthetic-replacements-for-human-survey-data-the-perils-of-large-language-models/B92267DC26195C7F36E63EA04A47D2FE

**"When Synthetic Users Fail: A Cross-Domain Benchmark" (2026).** Claude Haiku 4.5, Sonnet 4.6,
Llama-3.1-8B, Llama-3.3-70B over GSS (14,704 respondents) and WVS wave 7 (91,774).
- Models **fail to beat a trivial demographic lookup baseline**; on WVS every model was **11–22
  percentage points worse**.
- **Stereotyping index**: political views explain ~1.5% of real variance in confidence in banks but
  **up to ~67% in the models — a ~40× exaggeration**.
- Between-segment gaps inflate **2–4×**; models **pick the wrong segment in 50% of GSS pairs and
  72% of WVS pairs**, and **manufacture segment splits that do not exist in up to 41%** of
  cross-cultural cases.
- https://arxiv.org/html/2607.26348

⚠ **This is the most directly relevant paper to a marketer-facing product.** The failure is not
just "too uniform within a segment" — it is simultaneously **"too different between segments."**
LLM panels flatten individuals and caricature groups at the same time. Our product reports segment
differences. That is the number to worry about.

**Schröder et al., "Large Language Models Do Not Simulate Human Psychology" (2025).** 30 moral
scenarios, then semantically altered versions (sometimes one word).
- Original items: human–LLM correlation **r = .97–.99**. Reworded: **r collapsed to .46–.64**.
- Mean rating shift when meaning changed: **humans 2.20 points; GPT-4 0.42; Llama 1.18**.
- Changing "wrongfully convicted" to "rightfully convicted" moved humans substantially; the LLMs
  rated both about equally moral.
- https://arxiv.org/html/2508.06950v1

⚠ Evidence that LLM agents **under-react to changes in the stimulus's meaning** while over-reacting
to demographic labels — close to the exact opposite of the failure you want in an ad-testing
instrument. If we want agents to respond to a changed ad, the change must be **structural**
(present vs. absent in context), not merely semantic.

---

## 2. ⚠ The finding that should change our design

**"A Framework for Studying AI Agent Behavior: Evidence from Consumer Choice Experiments"
(ABxLab, 2026).** 17 models, **80,000+ trials**, real intercepted web content.
- Agent susceptibility to nudges ran **3–10× above human baselines**: humans showed 4pp (order),
  5pp (ratings), 9.4pp (price), 9.9pp (nudges); agents showed effects **up to 90pp**.
- Authors' conclusion, verbatim: **"Agents appear to reproduce human-like heuristics and biases
  without sharing the cognitive constraints that motivated such theories."** Importing constructs
  like *bounded rationality* or *limited attention* into the prompt **is not sufficient**.
- https://arxiv.org/html/2509.25609

**Read this as the central warning.** Telling an agent "you are scrolling quickly and barely glance
at this ad" produces a *performance* of inattention drawn from the training distribution of how
people describe being distracted — stereotyped, uniform, fluent. It does not produce inattention.
The model has already read every word of the ad.

> **The only intervention that creates a real information constraint is one that removes
> information from the context window.**

---

## 3. Demonstrated fixes (all persona-side)

| Fix | Measured effect | Source |
|---|---|---|
| **Audience segmentation identifiers** | KL to real humans **4.65** (demographics only) → **1.10** (15 theory-led identifiers) → **2.76** (59 identifiers — over-conditioning HURTS). Subgroup SD 0.24 → 0.63 → 0.54. *"Informative parsimony outperforms comprehensiveness."* | https://arxiv.org/html/2604.06663v1 |
| **Distribution-first / Verbalized Sampling** | Quantifies collapse: modal concentration **0.36 → 0.69**, entropy **1.46 → 0.77**, **85% of units collapse**, TVD **0.44**. Asking one call for the whole distribution with probabilities: **+6.8 to +10.1 points** fidelity at **O(1) not O(N)** cost | https://arxiv.org/html/2607.18310v1 |
| **Persona generators optimised for coverage** | Coverage **62.9%** vs 51.5% / 44.0% / 28.1% baselines; KL **0.99** vs 3.00–5.03; 99.2% judged realistic | https://arxiv.org/html/2602.03545v2 |
| **Interview-grounded agents** | Replicate GSS **85% as accurately as the participants replicate themselves** two weeks later; reduces accuracy bias across racial/ideological groups | https://arxiv.org/abs/2411.10109 |
| **Temperature > 0** | Improves distributional alignment; affects variance more than mean accuracy | https://arxiv.org/html/2603.28304v1 |

⚠ Two caveats on distribution-first: it **over-corrects dispersion** (SD-ratio 0.40–0.56 → 1.26–1.37),
and **survey fidelity transfers weakly to actual decisions** — individual-level prediction ceiling
**r ≈ 0.2**. Per-agent quotes are illustrative, never predictive. The UI must not imply otherwise.

**Marketing-specific validation, mixed:** replication of **133 published findings from 14 *Journal
of Marketing* papers** with ~19,447 AI personas reproduced **76% of main effects (84/111)** but only
**68% overall (90/133)** — interaction effects are where it breaks
(https://arxiv.org/pdf/2408.16073). PyMC Labs / Colgate-Palmolive report ~**90% of human
test-retest correlation** on purchase intent (57 surveys, 9,300 human responses) — industry-
published, promising not settled (https://www.pymc-labs.com/blog-posts/synthetic-consumers-a-practical-guide).

---

## 4. How ads are actually processed — the numbers to calibrate against

### Attention thresholds (Nelson-Field / Amplified Intelligence)

⚠ Commercial/trade research from an attention-measurement vendor. Large-scale and influential, not
peer-reviewed, proprietary data. Book is the closest citable primary:
https://link.springer.com/book/10.1007/978-981-15-1540-8

- **~2.5 seconds of active attention** is where advertising starts to affect memory. **~85% of
  digital ad impressions fail to reach it** (130,000 ad views, 1,150 brands).
- Active attention seconds ↔ short-term sales **r = .82, p < .001** *(reported-not-verified)*.
- Roughly **three days in memory per active attention second**.
- **Coverage** (share of screen): Facebook ~10% desktop / **~27% mobile**; YouTube ~30% / ~32%; TV 100%.
- Platform attention /100: BVOD **63**, Facebook **54**, YouTube **44**.
- **Decay from one exposure: TV 109 days, YouTube 8 days, Facebook 6 days.**
- Attention in **scrollable** environments drops sharply after **~2 seconds**; non-scrollable stays
  flat to 20 seconds.

**The 2025 update — 1.5 seconds with distinctive assets.** VCCP Media × Amplified × Nelson-Field,
*Hacking the Attention Economy* (May 2025). 72 digital video ads, 8 brands, each with a **"bad
twin"** stripped of distinctive assets; 20,000+ views tracked.
- With strong distinctive assets, **1.5 seconds** is enough to create memory — a full second below
  the 2.5s threshold.
- Best brand codes delivered **3.5× attention-adjusted ROI**; well-branded assets **2.5× more
  effective**. **66p in every £1** lost to poor branding.
- https://www.amplified.co/insight/vccp-research-amplified-distinctive-assets

⭐ **The most design-relevant finding here:** the threshold is not a property of the ad's duration,
it is a property of **how fast the brand is recognisable**. That is a simulatable construct, and it
maps onto our existing decoy/control methodology.

### Independent measurement (Lumen, dentsu)

**Lumen Research** (webcam eye-tracking; 766 respondents, 250,000+ ad impressions over five years):
- Only **~35% of digital display ads receive any views at all**.
- **9% receive more than one second.** **4% receive more than two seconds.**
- **Average dwell when noticed is 1–2 seconds.** A desktop ad has a **22% chance of being noticed**.
- https://www.jcdecaux.com/blog/attention-common-currency-media-lumen-research

**dentsu Attention Economy** (with Lumen) — cross-media norms:
- **6,501 APM** (attentive seconds per thousand impressions); **38% correct brand recall**;
  brand-choice uplift **6–7.25%**.

⭐ **The 38% norm is the number to hold onto.** In a well-measured cross-media benchmark, **fewer
than four in ten exposed people produce correct brand recall.** Our panel produces ~100%.

**Google: 56% of display ads are never seen by a human.**
**NN/g banner blindness:** *"Users almost never look at anything that looks like an advertisement."*
**Fixation ≠ encoding:** a YouTube ad-banner eye-tracking study found nearly all viewers fixated at
least once, yet **fewer than 10% could correctly recall its content**.

### The best peer-reviewed dwell anchor

**Epstein, Lin, Pennycook & Rand, "Quantifying attention via dwell time and engagement in a social
media browsing environment."** 644 recruited, 120 posts each, custom feed.
- **Two-stage structure: stage 1 (dwell) favours sensational content** (b = 0.04, p < .001;
  credible content *shorter*, b = −0.02, p = .017); **stage 2 (engagement) favours credible
  content** (credible b = 0.21; sensational b = −0.22, both p < .001).
- https://arxiv.org/abs/2209.10464

⭐ **Strongest justification for a two-stage architecture, and peer-reviewed.** Also a warning:
**what stops the scroll and what earns the response are driven by different, partly opposed
forces.** A single-stage panel conflates them.

---

## 5. Heath — why an attentive agent is the *wrong* model, not just an unrepresentative one

**Heath, Brandt & Nairn, "Brand Relationships: Strengthened by Emotion, Weakened by Attention,"
*Journal of Advertising Research* 46(4), 410–419 (2006).** US and UK markets.
- Brand favourability correlated strongly with **emotive power**; **cognitive power had little
  effect in either market**; attention was **negatively** associated with brand-relationship strength.
- https://www.journalofadvertisingresearch.com/content/46/4/410

**Low Attention Processing (Heath 2001, 2012):** at **high** attention, ads are examined,
counter-argued, and consigned to short-term memory. At **low** attention they **bypass evaluative
filters and form associations in long-term memory**.

⭐ **This is the load-bearing citation for the whole project.** It is the published, peer-reviewed
claim that an attentive, analytical viewer is the *wrong* model — not merely a rare one. Our agents
read carefully and evaluate rationally, which measures a process that mostly does not happen.

---

## 6. Ehrenberg-Bass — what advertising is doing at all

- **Sharp:** *"Advertising works largely by refreshing memory structures; occasionally it also
  builds memory structures and creates a preference or intention to purchase."*
- **Category Entry Points (Romaniuk & Sharp)** — measured on **mental penetration**, **mental
  market share**, **network size**. *"Category entry points are not about the brand, they're about
  the buyer."*
- ⚠ **Light buyers:** **~80% of a brand's buyers purchase it once a year or less**, contributing
  **~40% of sales**. The real Pareto is closer to **60/20 than 80/20**. **Coca-Cola: ~30% of its
  buyers don't buy it even once a year.** B2B analogue: **only ~5% of buyers are in-market** at any
  time. https://marketingscience.info/value-paretos-bottom-80/
- **Binet & Field** (IPA Databank, 996 campaigns 1980–2010): 60:40 brand:activation; emotional
  campaigns **almost twice as likely** to deliver top-box profit growth long-term.
- **Orlando Wood, *Lemon*** (100 UK/US ads): more left-brain features → lower Star Rating.

**The dissent, included for rigour:** Byron Sharp calls "attention is the new metric" *"nonsense"*
and attacks 60:40 as resting on *"a very weird data set… award submissions."* Note that Sharp and
Nelson-Field are **not opposed on the mechanism** — both say advertising works by refreshing memory
at low attention. For our purposes the disagreement is irrelevant: **both camps agree the consumer
is glancing, not studying**, which is the only premise the redesign needs.

---

## 7. Techniques we could build, honestly graded

| # | Technique | Status | Difficulty | Failure modes |
|---|---|---|---|---|
| A | **Stimulus truncation** — short-exposure agents get only a crop/thumbnail, not the full asset | **[X]** No published precedent for ads. Structurally sound: a real information constraint | Low–med | Truncation rules are arbitrary and become a hidden assumption; a "1-second crop" is a designer's guess; multimodal models may still read tiny text a human wouldn't |
| B | **Exposure-tier sampling** — draw attention-seconds per agent from a measured distribution | **[E/X]** distribution evidence-backed, mapping extrapolated | Low | Garbage-in if benchmarks come from the wrong platform/format; invites false precision ("2.3 seconds") in customer output |
| C | **Two-stage dwell-then-react gate** | **[E]** structure peer-reviewed (Epstein); no LLM implementation published | Medium | Stage-1 stop rates badly calibrated with no human anchor; two uncalibrated parameters |
| D | **Non-exposure agents in the denominator** | **[E]** strongly evidence-backed | Low | ⚠ Tempting to drop non-exposed agents from reporting, silently restoring inflated numbers — the same trap as our in-target/out-of-target bimodality |
| E | **Snap-judgement constraint** (no CoT, token cap) | **[X]** untested | Low | Shorter output is not less analytic; likely yields terse analysis, not System-1 reaction |
| F | **Feed-context injection** (surrounding organic posts) | **[X]** untested for LLM panels | Medium | Long context degrades model attention in ways unrelated to human attention; adding machine noise and calling it human noise |
| G | **Instructed inattention in the prompt** | ⚠ **ACTIVELY CONTRAINDICATED** by ABxLab | Trivial | Performed, not real. **The one to avoid** — highest-risk precisely because it is cheapest and looks most convincing |
| H | **Attention-weighted sampling by disposition** | **[X]** consistent with EB light-buyer evidence | Low | Correlating attention with disposition bakes in our hypothesis — assuming the answer |

---

## 8. Concrete encodings

**1. Replace uniform exposure with an exposure distribution [E/X]**

| State | Share | Basis |
|---|---|---|
| Never sees it | ~55–65% | **[E]** Lumen ~35% get any views; Google 56% never seen |
| Glance, <1s | ~26% | **[E]** Lumen: 9% exceed 1s, 4% exceed 2s |
| 1–2.5s | ~5% | **[E]** Lumen average dwell 1–2s when noticed |
| >2.5s (above memory threshold) | ~4% | **[E]** Nelson-Field ~85% below 2.5s |

The *distribution* is evidence-backed; these exact percentages for a specific client format are **[X]**.

**2. Truncate the stimulus by exposure tier [X]** — the only intervention creating real rather than
performed inattention. Suggested mapping (entirely the researcher's construction): <1s → brand mark
+ dominant colour + top ~15%, no copy; 1–2.5s → headline + primary visual + brand asset; >2.5s →
full asset. ⭐ The 1.5s distinctive-assets finding gives a **testable discriminant**: agents with
strong prior brand associations should identify the brand from the <1s crop, agents without should
not.

**3. Two-stage scroll-decision then reaction [E structure, X calibration]** — and do **not** reuse
the same scoring ruler across stages, since stopping and responding are driven by different features.

**4. Keep non-exposed agents in every denominator [E]** — structurally the same lesson as our
logged in-target/out-of-target bimodality.

**5. Change the question from evaluation to memory [E]** — ask *whose ad was that?* (brand
attribution speed), *what did it remind you of?* (associative), *when would something like that
come to mind?* (CEP linkage). Do **not** ask *what do you think of this ad* or *would you buy this*,
which recruit exactly the System-2 counter-argument real exposure bypasses. Consistent with what we
already logged about reaction-question framing and priming.

**6. Score against CEP linkage and brand-asset recognition, not persuasion [E].**

**7. Panel composition should be mostly light and non-buyers [E]** — if all 100 agents are
category-engaged we are simulating the ~4% heavy tail. ⭐ Skewing toward light/lapsed/non-buyers
would **by itself** flatten the over-eager responses, with no prompt trickery.

**8. Apply the demonstrated variance fixes** — segmentation identifiers but **stop at ~15**;
temperature > 0; distribution-first for aggregates while keeping per-agent generation for quotes.

**9. ⚠ Explicitly do NOT add "you are distracted / scrolling fast" to the persona prompt.**

**10. Calibration targets for the human panel:** ~38% correct brand recall among exposed · ~85% of
impressions below 2.5s · ~6–7% brand-choice uplift · <10% correct content recall for a
fixated-but-glanced banner. **If our simulated panel produces 90% recall and 40% consideration lift,
the gap against these norms is the size of our realism problem, quantified.**

---

## 9. Two flags before building

**The validation trap is the real risk.** Every technique above will make output *look* more
realistic. Without a human benchmark we cannot distinguish "more realistic" from "noisier in a way
that flatters our priors." The distribution-first paper is blunt: one of its own headline results
turned out to be **memorisation, not simulation** — an election backtest matched the official
result because the model *remembered* the election. **Build the human panel arm in parallel, not
after.**

**Prefer stimulus-side interventions to prompt-side ones, always.** Removing information from the
context is a real constraint; describing a constraint in the prompt is theatre. Build order by
evidential defensibility: **(4) denominators → (7) panel composition → (1) exposure distribution →
(5)+(6) question and ruler redesign → (2) stimulus truncation → (3) two-stage gate.** Items 2 and 3
are the novel ones and the ones most worth a human read.
