# Deeper dive — a second pass over the 11 MB

**2026-08-04.** The first pass (`03_recovered_from_dead_agents.md`) skimmed three transcripts. This
is a full sweep of all twenty, including four academic threads that had never been opened.

⚠ Same status caveat as file 03: **recovered from raw transcripts, not written up by a researcher
who read and judged the source.** Verify anything load-bearing. Vendor claims labelled as such.

---

## 1. ⭐⭐ The finding that describes our exact failure

> *"Without demographic grounding, models generated uniformly positive responses (mean 4.0 ± 0.1)
> that **perfectly matched human distribution shape but provided no discrimination between
> products**."*

And separately, on the same problem:

> *"Models systematically regressed to response '3' (the middle of the scale), described as a
> **'safe' regression to the center**. Nearly all responses clustered around this neutral anchor."*

⭐ **This is the failure mode our product cannot survive, stated precisely.** An instrument can
produce a distribution that *looks* human — right shape, plausible spread, fluent quotes — while
having **zero power to tell one ad from another**. That is not a cosmetic problem; it is the whole
product failing silently.

**It also gives us a test we do not currently run.** Our discriminant check
(`docs/v3_discriminant_check.md`) asks whether the engine separates a *known-bad control* from a
real ad. This suggests a sharper version: run **two genuinely different real ads** through the panel
and measure whether the output distributions differ **more than two runs of the same ad differ**.
If they don't, the numbers are decoration. We have the sigma study
(`docs/v3_sigma_study.md`) for run-to-run variance already — the comparison is buildable from
material we own.

---

## 2. ⭐⭐ Analytic flexibility — the result that should scare us most

> *"A 2025 paper examining analytic flexibility in silicon sampling found that **across 66
> configurations, the correlation between human and silicon Cramér's V values ranged from r = .23 to
> r = .84 (median r = .58)**, meaning the same human dataset using the same prediction task could
> imply either relatively [strong or weak validity]."*

⚠ **Same data, same task, 66 defensible analysis choices — and the answer ranges from "barely
works" to "works well."** The researcher's degrees of freedom swamp the effect being measured.

**Why this lands on us specifically:** we have made dozens of such choices — panel size 100,
seed 71, temperature 1.0, this disposition library, this context envelope, these seven questions,
this chaos distribution. Every one is defensible. **The literature says that set of choices can
move apparent validity from 0.23 to 0.84.**

The implication is not "give up." It is: **whatever we eventually measure against humans, we must
fix the configuration BEFORE we look at the result, and report the configuration with the number.**
Otherwise we will tune our way to a good score and learn nothing. This is pre-registration, and it
is cheap to do — a written-down config hash before the human panel runs.

---

## 3. CoMPosT — caricature has a name and a measurement

**CoMPosT: Characterizing and Evaluating Caricature in LLM Simulations** (Cheng, Durmus, Jurafsky —
EMNLP 2023), https://arxiv.org/abs/2310.11501

The framework decomposes an LLM simulation into **context, model, persona, topic** and measures
**caricature** — the degree to which a simulated persona collapses into an exaggerated stereotype
rather than a person. This is the formal name for what we observed as *"50 of 100 agents say
'feels like it's for someone else'"*.

Two related papers surfaced but not read:
- **"The Chameleon's Limit: Investigating Persona Collapse"** https://arxiv.org/pdf/2604.24698
- **"More Is Not More: What Matters for Diversity in LLM Opinions?"** https://arxiv.org/html/2607.20429v1
  — the title alone corroborates the "stop at ~15 conditioning variables" finding from three
  independent directions now.

---

## 4. ⭐ Verbalized Sampling matched a fine-tuned model

From the VS paper's own results, recovered verbatim:

> *"(1) on creative writing, Verbalized Sampling significantly improves output diversity; (2) **on
> social dialogue simulation, VS induces substantially more human-like behaviors, with some models
> performing on par with a dedicated fine-tuned model**"*

⭐ **A prompting change reached fine-tuning-level human-likeness on the task closest to ours.**
Combined with the cost picture (fine-tuning ~$75–450 plus an eval harness that is "the project"),
this makes VS the obvious first move rather than a fallback.

Mechanism, for the record — this is *why* it works, and it is not hand-waving:
> *"the representative outcome for an **instance** prompt is a single prototypical item, whereas the
> representative outcome for a **distribution** prompt is a sample that exhibits the diversity
> expected from a random process"*

Asking for one reaction gets the mode. Asking for the *distribution* of reactions gets the spread.
Our pipeline asks 100 agents for one reaction each — 100 draws at the mode.

⚠ **The tension to hold:** our per-agent qualitative quotes are a product feature, and VS is a
distribution-level technique. Report 01 already flagged the trade (individual-level ceiling
r ≈ 0.2). A hybrid — VS for the numbers, per-agent generation for the quotes — is the shape
suggested by both reports, and neither has tested it.

Also recovered: VS is **orthogonal to temperature/top-p/min-p** (paper's §F.3 ablation), and
**larger models gain 1.5–2× more from it** than small ones.

---

## 5. Törnberg's method — how to build personas from real data

The paper behind the confirmation-bias finding (arXiv:2310.05984) describes a persona-construction
method worth copying:

> *"To calibrate the model to the US electorate, we construct a persona for each agent using data
> from the **2020 American National Election Study**."*
>
> *"To provide a richer description of non-political interests and personality attributes than is
> available in the ANES data, we build upon the finding that LLMs can provide realistic responses
> based on existing survey data, and **prompt the models to add additional attributes for each
> agent**."*

⭐ **Seed each persona from a real survey respondent; let the model expand only the attributes the
survey doesn't carry.** That is materially different from what we do — our dispositions are
hand-authored archetypes, and every persona sharing a disposition inherits the same anchor text.
It is also the cheap end of the Park et al. finding (survey-only grounding: 82% vs 74% for
demographics alone).

Their simulation reproduced **three real, documented dysfunctions** — partisan echo chambers, elite
concentration of influence, and a "social media prism" amplifying polarised voices — which is a
genuinely successful social layer. ⚠ But note what they were validating against: *known qualitative
pathologies*, not point predictions. Their own caution: *"Generative simulations are even harder to
calibrate to empirical data than conventional ABMs."*

---

## 6. ⚠ Industry rules now exist, and we are subject to them

This is the compliance material the earlier pass missed entirely.

**ESOMAR** (the global market-research body):
- Defines a **synthetic persona** as *"a digital representation of a person generated to mimic the
  behaviours, preferences, and characteristics of real people or groups."*
- ⚠ **The ICC/ESOMAR Code explicitly distinguishes an "individual/person" from a "synthetic,
  virtual/digitally created persona or entity."** So calling our output "100 consumers" without
  qualification is against the code's own vocabulary. **Our read already says "100 simulated
  consumers" and stamps every quote "simulated"** — that was the right call and it is now
  externally required, not just good manners.
- The **2025 revision** emphasises *"ethical conduct, accountability, transparency, and the
  necessity for human oversight."*
- ESOMAR has published **buyer-side guidance**: questions to ask a synthetic-data supplier. Worth
  obtaining — it is effectively the checklist our prospects will be handed.

**MRS** (UK) launched AI/synthetic-data guidance on **1 May**, as part of its "Campaign for Better
Data". Principles recovered:
- ⭐ **"Synthetic data should complement, not replace, real human insight."**
- ⭐ **"Clear disclosure when AI is used in research outputs"** is required.
- Alignment with existing ethical codes and data-protection law.
- ⚠ *"the industry still lacks firm regulation"* — so this is guidance, not law, today.

**And the independent-critique line worth quoting back at any vendor claim:**
> *"The authors emphasize that 'synthetic data' should not replace human surveys due to
> **unpredictable error patterns**."*

Unpredictable is the operative word. An error you can characterise you can correct for; these are
not yet characterised.

---

## 7. The flattening, in one number

> *"every synthetic mean falls within one standard deviation of the ANES average"*

⭐ **A perfect one-line summary of the whole problem.** Real populations have subgroups that sit
*outside* one SD of the national average — that is what a subgroup *is*. A synthetic population
where nobody does has, by construction, no extremes, no outliers, and no genuinely different
segments. It has an average wearing a hundred costumes.

Ours has 29 distinct people wearing a hundred costumes, which is the same disease at a different
stage.

---

## 8. Fine-tuning — the number that reframes it

The earlier report said the successful fine-tunes used millions of labelled responses (SocSci210:
2.9M; Centaur: 10.7M choices), which put fine-tuning out of reach. Recovered detail complicates
that usefully:

- **OpenAI's own guidance: minimum 10 examples; "start with 50 well-crafted demonstrations."**
  Improvements appear *"from fine-tuning on 50–100 examples."*
- Together's minimum job fee is **$4**; training **$1/M tokens** at the low end.
- Provider training rates recovered: **Qwen 3.5 9B $1.463/M**, **Qwen 3.6 27B $4.103/M**,
  **Kimi K3 $32.55/M**. On-demand **H100/H200 $7.00/hr, B200 $10.00/hr, B300 $12.00/hr**.
- ⚠ **LoRA DPO pricing is double LoRA SFT** — and report 02 already says preference-based
  post-training is what *causes* diversity collapse. Paying twice to make the problem worse.
- ⚠ OpenAI fine-tuning is **text-only, 32K context**, vision "planned" — our agents need images.

⭐ **The reconciliation: 50–100 examples buys FORMAT and REGISTER. Millions buy BEHAVIOURAL
FIDELITY.** These are different products of the same verb, and conflating them is how a team spends
a month fine-tuning and discovers it changed the prose style and nothing else. Report 02's warning —
review-shaped text vs. consumer-shaped judgement — is exactly this distinction, and the cheap
fine-tune buys the side we don't need.

---

## 9. More vendor detail

**Yabble** (NZ, "Virtual Audiences", "Gigi"): claims **"90% similarity of insight when compared to
traditional methods."** Their validation method, recovered from their own PDF: they use a tool
called ARES to rate **each individual answer on a 5-point scale**, for both synthetic and real
datasets, then **average and compare the totals**, plus a topic-coverage check.

⚠ **Comparing averaged quality ratings is not a validity test.** Two datasets can score identically
on a 5-point "is this a good answer" scale while disagreeing completely about which ad works. It
measures plausibility, not correctness — the exact confusion §1 of this file warns about.

Case study claim: a QSR tested *"hero creative, a written manifesto, campaign moodboards, and
interactive in-store experiences… in under 24 hours."* Also relevant: their platform draws on
**26 million registered panel members** — real panel data at a scale we cannot approach.

---

## 10. What this pass changes

Nothing here reverses an earlier conclusion. Four things sharpen:

1. ⭐ **Add a discrimination test, not just a realism test.** "Do two different ads produce
   different outputs, by more than the same ad produces twice?" is buildable now from the sigma
   study, costs one paid run at most, and it is the test that catches the mean-4.0 failure.
2. ⭐ **Fix the configuration before the human panel runs, and publish it with the result.**
   66 defensible configs spanned r = .23 to .84. Without this, the eventual validation number is
   whatever we tuned toward.
3. **Verbalized Sampling moves to first in the queue** — it matched a fine-tuned model on social
   simulation, is training-free, and stacks with temperature.
4. **Seed personas from real survey respondents** rather than sharing hand-authored anchors, which
   is both the Park et al. cheap win and the Törnberg method, and directly attacks our
   "29 distinct people" measurement.

And one thing to put in the product now, because it is free: **MRS/ESOMAR require clear disclosure
that outputs are AI-generated, and distinguish a synthetic persona from a person.** Our read
already does this in three places. That is a competitive asset the moment a prospect's insights
team asks — several vendors above are marketing "93% accuracy" numbers that their own definitions
do not support.
