# SimBench, read properly — and a correction

**SimBench: Benchmarking the Ability of Large Language Models to Simulate Human Behaviors**
Tiancheng Hu, Joachim Baumann, Lorenzo Lupo, Nigel Collier, Dirk Hovy, Paul Röttger.
**Accepted at ICLR 2026.** v1 Oct 2025 → v4 Apr 2026. https://arxiv.org/abs/2510.17516

20 unified datasets, **45 models**, global participant pool, from moral decision-making to economic
choice. This is the real thing: a serious benchmark from serious NLP researchers, peer-reviewed.

---

## ⚠ CORRECTION to `03_recovered_from_dead_agents.md`

That file said: *"Claude-3.7-Sonnet scored worst of those named (−4.61)"* and treated it as a
reason to consider moving off Claude.

**That is wrong, and the paper says close to the opposite.**

**Claude-3.7-Sonnet is the TOP-SCORING model in SimBench, at 40.80/100.** It is the best human
simulator of the 45 tested.

The −4.61 figure is **ΔS**, which is a completely different quantity:

> **ΔS = S_grouped − S_ungrouped**

It measures **how much a model gets WORSE when you condition it on a demographic group**, not how
good it is. Every model has a negative ΔS. The recovered search summary listed ΔS values only, with
no overall scores next to them, and the earlier note read them as a quality ranking. They are not.

| model | **S (overall, higher = better)** | ΔS (demographic conditioning penalty) |
|---|---|---|
| **Claude-3.7-Sonnet** | **40.80 — best of 45** | −3.13 |
| Claude-3.7-Sonnet-4000 *(extended thinking)* | 39.46 | −4.61 |
| GPT-4.1 | 34.55 | −3.94 |
| DeepSeek-R1 | 34.52 | −3.79 |
| DeepSeek-V3-0324 | ~32.89–33.16 | **−1.27 (smallest penalty)** |
| o4-mini-high | 28.99 | — |
| Llama-3.1-405B-Instruct | 28.40 | — |
| Qwen2.5-72B-Instruct | 27.61 | — |
| OLMo-2-32B (base) | 15.90 | — |

So the honest reading: **Claude is the best overall simulator; DeepSeek-V3 is the most robust to
demographic conditioning while being ~8 points worse overall.** There is no case here for switching
the agent layer off Claude. (And DeepSeek cannot take images anyway — see the API report.)

**Definition of the score**, for the record:
> `S(P,Q) = 100(1 − TVD(P,Q)/TVD(P,U))` — P is human ground truth, Q the model, U uniform.
> 100 = perfect alignment, 0 = random guessing.

---

## 1. ⭐ The ceiling: 40.80 out of 100

The authors call the best result **"meaningful but modest"**, and are explicit about what it means:

> *"the best model's predictions remain closer to a uniform distribution than to the human ground
> truth, it nonetheless closes roughly **40% of the gap**"* between random guessing and perfect
> prediction.

**Read that twice.** The best available model, on the best available benchmark, is still closer to
*random* than to *right*. This is the state of the art, measured, peer-reviewed, in 2026.

It is not a reason to stop — 40% of the gap closed is real signal, and our product sells a
*diagnosis*, not a prediction. But it sets the ceiling for what any amount of prompt engineering,
persona work, or model switching can buy us, and it should govern how the read describes its own
confidence.

The authors' own caution:
> *"we caution against relying on LLM-powered simulations of human behavior for tasks where
> downstream harm is possible."*

---

## 2. ⭐⭐ The finding that most directly explains OUR problem

> *"base models consistently outperform their instruction-tuned counterparts on **high-entropy**
> questions, while the inverse is true for **low-entropy** questions"*

with **a near-perfect negative linear relationship, r = −0.942**, between instruction-tuning benefit
and response entropy. Concretely:

- On **low-entropy (consensus)** questions — where humans mostly agree — instruction tuning
  **improves scores by up to 40 points**.
- The benefit **erodes as human disagreement rises**, crossing zero at about **entropy 0.8**.
- On the **highest-disagreement** questions, instruction tuning is **"actively detrimental, making
  the aligned model a worse simulator than its base counterpart."**

⭐ **This is our homogeneity problem, named and quantified by an independent benchmark.** Reactions
to an ad are a high-entropy question — real people disagree wildly about whether an ad is for them.
That is precisely the regime where the RLHF/instruction tuning that makes Claude a good assistant
makes it a **worse** simulator. Our 57-of-100-identical-phrasing measurement is this effect showing
up in our own data.

It also explains why our register is *good* (fluent, plausible, well-behaved consumer voice) while
our *spread* is bad. Instruction tuning bought us the former at the cost of the latter.

**What it does NOT license:** the paper does not say "use a base model." Base models scored far
lower overall (OLMo-2-32B: 15.90), and the recovered note that *"instruction-tuned models outperform
base variants at >10B parameters but invert at smaller scales"* points the same way. The finding is
about **which questions** instruction tuning hurts on, not a blanket recommendation.

---

## 3. Where models are worst — and it is where we operate

**Best performance:** standard survey questions about opinions and self-assessments (OpinionQA,
Afrobarometer).

**Worst performance:**
- Behavioral choices in **risky decisions** (Choices13k)
- **Moral dilemmas** (MoralMachine)
- ⚠ **Traits that conflict with alignment objectives** — Machiavellianism, conspiratorial beliefs,
  humour ratings — where *"even the best LLMs often perform worse than a uniform baseline."*

⚠ **Worse than random.** For the dismissive, cynical, contemptuous or funny consumer, an aligned
model is not merely weak — it is anti-informative. That is a real slice of any ad audience, and it
is exactly the slice our panel renders as politely disengaged.

**Which demographic conditioning hurts most:**
| conditioning on | ΔS |
|---|---|
| Religiosity / practice | **−9.91** (worst) |
| Political affiliation | −4.97 |
| Religion | −4.83 |
| **Income** | **−4.51** |
| Age | −1.50 |
| Gender | −1.24 |

⭐ **Relevant to us:** our audience specs condition on **income bands** (`₹7–40 LPA` is in every
declared targeting string) — one of the more damaging axes. Age and gender, which we also use, are
the *safest*. This argues for keeping demographic conditioning light and leaning on the
disposition/values layer, which matches the "1.5% of variance" finding from the other reports.

---

## 4. What predicts simulation ability

> *"simulation ability correlates most strongly with knowledge-intensive reasoning
> (MMLU-Pro, r = 0.939)"*

Smarter models simulate better, and the correlation is very strong. Combined with the ranking, this
says: **stay on a frontier model.** Cost-saving by dropping to a small model for the agent layer
would directly cost simulation fidelity.

---

## 5. ⚠ How far this transfers to us — stated honestly

SimBench measures **distributional match on survey-type questions with defined response options**.
Our product is different in two ways:

1. **Our agents produce open-ended prose**, which SimBench does not score at all. The Stanford
   fine-tuning paper flagged the same gap ("closed-form questions only — open-ended untested").
2. **But our behavioural signal is exactly SimBench-shaped** — `scroll_past / linger / tap_cta /
   save / share` and `buy_now / research_first / nothing` are categorical distributions over a
   panel. That is precisely what S measures.

So the ceiling applies most directly to **the numbers we report** (action rates, next-step mix,
decision) and less directly to the qualitative pains. Which is the opposite of how a reader would
naturally assume the uncertainty distributes.

---

## 6. What this changes for us

1. **Do not switch models for the agent layer.** Claude is the benchmark leader. This closes the
   question the earlier note opened.
2. **Stop adding demographic conditioning; prefer income-free framing where possible.** Income is
   among the most damaging axes; age/gender are the least.
3. ⭐ **Accept an instruction-tuning ceiling on diversity, and route around it rather than
   prompt-engineer at it.** The measured fixes for high-entropy regimes are the sampling ones —
   Verbalized Sampling, distribution-first elicitation — not more persona prose.
4. **Our confidence language needs to survive a 40.80/100 state of the art.** `VERDICT_CAVEAT`
   already carries this spirit. Nothing in the product should imply precision the field does not
   have.
5. **The cynic and the joker are our blind spot**, and it is a measured one, not a hunch.
