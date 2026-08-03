# Social influence layers & fine-tuning for human-likeness

**Research report, 2026-08-04. Complete.** The second of two agents that finished.

Evidence labels: **[A]** researcher read the paper and pulled numbers directly · **[B]** real paper,
abstract/snippet only, numbers not independently verified · **[C]** plausible idea circulating with
**no** measured result — treat as untested.

---

## 0. ⭐ The headline finding — it inverts our premise

We want a social layer because our independent agents **converge too much**. The strongest evidence
says a naive social layer makes convergence **worse**, and the interventions that actually restore
heterogeneity are not social layers at all.

**Measured over-convergence when LLM agents talk to each other:**

| Finding | Number | Source |
|---|---|---|
| Role-playing agents over-converge vs. real humans | Humans: within-group ΔSD ≈ 0 on controversial topics (no convergence). LLM agents: substantially negative ΔSD on both public messages and private beliefs | DEBATE — 30,707 messages / 2,832 US participants / 708 groups / 107 topics — https://arxiv.org/html/2510.25110v5 **[A]** |
| Conformity of a neutral agent | **39.40% → 74.33%** when exposed to a higher-"intelligence" peer; 2,500+ simulations | https://arxiv.org/html/2506.01332 **[A]** |
| Herd effect vs. humans | LLM agents showed a **stronger** herd effect than humans (Muchnik et al. 2013 paradigm) | OASIS — https://arxiv.org/abs/2411.11581 **[A]** |
| Debate degrades accuracy | MMLU **−9.2 pts**, CommonSenseQA **−5.0 pts**; correct→incorrect transitions **outnumber** incorrect→correct | https://arxiv.org/html/2509.05396v1 **[A]** |
| Simulated graphs are structurally degenerate | Real Reddit: dense, repeated interaction, sentiment reversals. LLM-simulated: *"isolated linear chains with monotonic emotional trajectories"* | https://arxiv.org/abs/2512.21138 **[A]** |

**What does measurably restore heterogeneity (all non-social):**

| Intervention | Number | Source |
|---|---|---|
| Better conditioning variables | KL to real humans **2.72** (demographics) → **0.68** (15 theory-led vars) → **2.76** (59 vars — over-conditioning hurts). A 4-item validated instrument beat a 15-item one | https://arxiv.org/html/2604.06663v1 **[A]** |
| Verbalized Sampling (ask for N responses **with probabilities**) | 1.6–2.1× diversity gain; +25.7% human-rated diversity; **recovers 66.8% of base-model diversity**; training-free | https://arxiv.org/html/2510.01171v4 **[A]** |
| Grounding each agent in a real person's self-report | GSS accuracy **74%** (demographics) → **82%** (survey-only) → **83%** (interview-only) → **86%** (both) | Park et al., 1,052 Americans — https://arxiv.org/abs/2411.10109 **[A]** |

> **Practical read:** if our ~100 agents give too narrow a spread, the cheapest large win is in
> **conditioning and sampling**, not in wiring them together. Add a social layer because we want
> word-of-mouth **as a phenomenon** — a legitimately different goal — not because we expect it to
> widen the distribution. It will narrow it.

⭐ **The implication most people miss in Park et al.:** survey-only (82%) ≈ interview-only (83%).
We do **not** need expensive qualitative interviews. Structured self-reports from real people get
~95% of the way there, far cheaper. And that paper contains **no social layer at all** — the agents
are independent, and it is the highest-fidelity individual-level result in the literature.

⚠ The widely-cited "85%" figure from that paper is **stale**; the current version reports **86%**
(interview+survey). Code: https://github.com/joonspk-research/genagents

---

## 1. What each social framework actually demonstrated

**OASIS** (https://arxiv.org/abs/2411.11581, code https://github.com/camel-ai/oasis) **[A]** —
the most quantitatively validated social-layer system found.
- **Information spread:** ~**30% normalized RMSE** against 198 real Twitter cascades. Scale and
  breadth matched; **depth systematically underestimated**.
- ⚠ **No detectable herd effect at 100 agents; explicit herd effect at 10,000.**
- Cost: 10k agents = 0.2 h/timestep on 2×A100; 1M = 18 h/timestep on 27×A100.

⭐ **Directly relevant to us: at our panel size (~100), OASIS's own data says the social effect does
not emerge.** A social layer over 100 agents may produce nothing but noise — or, if we force
exposure, an artefact.

**Generative Agents / Smallville** (Park 2023, https://arxiv.org/abs/2304.03442) **[B]** — party
invitation reached **12 of 24** agents; 5 of 12 attended. ⚠ No comparison against a real human
diffusion curve. Existence proof that information spreads, not a calibrated rate.

**AgentSociety** (https://arxiv.org/abs/2502.08691) **[B]** — 10k+ agents, ~5M interactions;
quantitative validation not verified. **Concordia** (DeepMind,
https://github.com/google-deepmind/concordia) **[B]** — contribution is methodological; no headline
fidelity number. **S3** (https://arxiv.org/abs/2307.14984) **[B]** — one of the few combining
fine-tuning and prompting; "promising accuracy," metrics unverified.

⚠ **Marketing-specific prior art is thin to the point of absence.** https://arxiv.org/abs/2510.18155
**[B]** is only **11 agents, 10 locations, one week**, evidence anecdotal, **no validation against
real campaign data**. **No paper was found validating an LLM agent panel against real held-out
advertising or market outcomes. That gap is real.**

**Read before building:** *"AI Agents Are Not (Yet) a Panacea for Social Simulation"*
(https://arxiv.org/html/2603.00113v1) **[A]** — *"Role-playing plausibility does not imply faithful
human behavioral validity."* Documents that the field validates on curated transcripts with limited
run-to-run variance reporting and no baselines, and that *"small changes in persona wording, memory
format, or interaction protocol can flip conclusions."*

**And the one to keep quotable:** **Gao, Lee, Burtch & Fazelpour, PNAS 122(24), 2025**,
doi https://doi.org/10.1073/pnas.2501660122 **[A]**. Eight LLMs × 1,000 sessions, 11-20 money-request
game. LLMs reasoned at **level 0–1**; humans at **level 3**. All distributions diverged from human
ones (p<0.001). **GPT-4 was *less* human-like than GPT-3.5.** ⚠ **Chain-of-thought, RAG, and
fine-tuning all largely failed** to close the gap — the sole exception was a fine-tuned GPT-4o, which
the authors attribute to **memorisation of the human data, not human-like reasoning.**

---

## 2. Known failure modes of interaction, with numbers

1. **Sycophantic conformity** — 39.40% → 74.33%; peer "intelligence" mattered more (ηp² ≈ 0.1665)
   than **majority size** (ηp² ≈ 0.068). https://arxiv.org/html/2506.01332 **[A]**
2. **Correct→incorrect drift under peer exposure**, attributed to RLHF sycophancy.
   https://arxiv.org/html/2509.05396v1 **[A]**
3. **Over-convergence** (DEBATE) **[A]** — with one hopeful result: **supervised fine-tuning
   substantially reduced over-convergence** at both utterance and group level.
4. **Structural degeneracy of simulated graphs** https://arxiv.org/abs/2512.21138 **[A]**
5. **Asch-style conformity under uncertainty** — instruct-tuned models conform more when uncertain
   https://arxiv.org/pdf/2508.14918 **[B]**
6. **"Uncanny valley of social simulation"** — agents "too human to model"
   https://arxiv.org/abs/2507.06310 **[B]**

---

## 3. ⭐ The best positive result: hybrid, not pure-LLM

**FDE-LLM** (https://arxiv.org/html/2409.08717) **[A]**. A small set of **opinion leaders** are LLM
agents constrained by cellular-automata rules; the **followers** are pure CA + SIR with exponential
attitude decay. Opinion updates blend LLM output with the classical term via a tunable α.
- **Validation:** 4 real Weibo events, **255,176 posts**. DTW **0.36–0.37**, Pearson **0.88–0.97**
  against the real opinion trajectory — **outperforming both traditional ABM and pure-LLM baselines
  by 60–86%**.

⭐ **Direct measured evidence that the cheap route wins:** LLM for a few seed/leader agents,
classical dynamics for the crowd, beats spending LLM calls on everyone. α is exactly the dial for
controlling herding artefacts. ⚠ Failure mode: SIR/CA parameters need fitting to *something* —
without real trajectory data we would be inventing the diffusion curve.

Related: **LLM-AIDSim** https://www.mdpi.com/2079-8954/13/1/29 **[B]**; Bass model on networks
https://www.tandfonline.com/doi/full/10.1080/13873954.2024.2350244 **[B]**.

⚠ **Explicitly disclaimed [C]:** a claim that "LLM agents under DeGroot protocols exhibit
convergence consistent with graph-theoretic predictions" came from an aggregator topic page, not a
paper the researcher read. **Do not cite it.**

---

## 4. ⭐ Diagnostics we can run TODAY on the existing panel

**Neumann, De-Arteaga & Fazelpour, "Should you use LLMs to simulate opinions? Quality checks for
early-stage deliberation"** (https://arxiv.org/html/2504.08954v3) **[A]**. Two cheap checks:
- **QC1:** is the simulated *average* opinion a valid convex combination of the subgroup opinions?
- **QC2:** do subgroup differences match domain knowledge / small-sample real data?

Their result: ⚠ **~80% of tested models produced an "average" opinion more extreme than every
demographic-specific prediction** — a geometric impossibility — and only **20.3%** of
model×topic×prompt combinations passed the weak consistency threshold.

**This is a bug-finder for our current pipeline, independent of any social layer or fine-tune.
Run it first.**

⚠ **The hole that could not be filled: dose of exposure.** No ablation exists on how many peers,
how many rounds, or what tie strength produces realistic vs. artefactual influence. **[C]** Do not
accept "2–3 rounds is enough" — no number supports it.

---

## 5. Fine-tuning — what works

**Kolluri, Wu, Park & Bernstein (Stanford)** https://arxiv.org/html/2509.05830v1 **[A]** —
**SocSci210**: 2.9M individual responses, 400,491 participants, 210 studies.
- Distributional alignment **+30.1%** (LLaMA3-8B) and **+26.3%** (Qwen2.5-14B) over base.
- Fine-tuned **14B beat GPT-4o prompting by 13.2%**; the **8B beat GPT-4o by 12.1%**.
- ⚠ Authors' caveats: performance **plateaus** with model size; US-only; **closed-form questions
  only — open-ended responses untested.** That last one matters enormously for us: ad reactions are
  open-ended.

**Centaur** (Binz et al., **Nature** 2025, https://www.nature.com/articles/s41586-025-09215-4)
**[A setup / B effect size]** — QLoRA on Llama-3.1-70B over **10,681,650 choices**. Beats existing
cognitive models on held-out participants. ⚠ The quoted "10% to over 90% of variance" figure came
via a survey, not the paper — verify before quoting.

**SubPOP** (NAACL 2025, https://arxiv.org/abs/2502.07068) **[A]** — fine-tunes on **first-token
probabilities** to minimise divergence between predicted and actual **response distributions**, not
to imitate text. ⭐ **Design lesson: distribution-matching objectives beat text-imitation objectives.
If we fine-tune, fine-tune on the distribution of judgements, not on prose.**

**⭐ The result that should change the plan: Krsteski et al.** https://arxiv.org/html/2510.11408 **[A]**
- Average bias: demographic prompting **55.60%**, domain fine-tuning **34.66%**, SubPOP FT **86.23%**.
- With **rectification** (a small real human sample statistically correcting the synthetic
  estimates): domain-FT + rectification → **2.82% bias**; all methods under 5.5%.
- **As few as 100 real responses (~1% of a full survey) corrects estimates to within 5% bias.**
- Counterintuitive allocation: with a 1,000-response human budget, **~20% to fine-tuning and ~80% to
  rectification** minimises bias — the opposite of most teams' instinct.

⚠ **Counterweight:** Neumann et al. **[A]** found fine-tuning scored **100% on
alignment-with-expectations** while **degrading logical coherence**. Fine-tuning can buy the
right-looking answer and break the reasoning underneath.

---

## 6. ⚠ The risk we named — review-SHAPED text vs. consumer-SHAPED judgement

**Verdict: demonstrated, not speculative.**

**"Not-quite-human tastes: the stylized omnivorousness of LLM survey surrogates"** (NTU, June 2026,
https://arxiv.org/html/2606.30085v1) **[A]**. 277,470 synthetic responses vs. the real Survey of
Public Participation in the Arts, on liking 17 music genres:
- Real humans liked **24.18%** of genres. LLM surrogates: **+15.59 to +21.96 percentage points** —
  nearly double the apparent breadth of taste. **Systematic positivity inflation.**
- ⚠ **The correlational structure dissolved.** Blues↔classic-rock **0.40 → 0.04**. A spurious
  hip-hop↔bluegrass correlation appeared at **0.61** (real: 0.07).
- Fabricated class-taste hierarchies and invented race-taste correlations contradicting real data.

⭐ **This is precisely the worry, measured:** the surface (fluent, plausible opinions) is right; the
**joint distribution of preferences — which is what a marketer actually buys — is wrong, and wrong
in a confidently structured way.** Fine-tuning on review corpora makes the surface more convincing
while leaving the joint distribution unfixed.

Supporting:
- **PNAS 11-20 game [A]** — the only fine-tune that matched humans did so *"through human data
  memorization rather than genuine reasoning."* Register acquired, reasoning not.
- **"Catch Me If You Can? Not Yet"** (EMNLP 2025 Findings, https://arxiv.org/abs/2509.14543) **[A]** —
  40,000+ generations, 400+ real authors. LLMs approximate style in **structured** formats (news,
  email) but **fail on informal blogs and forums** — exactly the register of the Reddit/review data
  we would fine-tune on. ⚠ We may not even get the surface right.
- **Hu & Collier, ACL 2024** (https://arxiv.org/abs/2402.10811) **[A]** — persona variables explain
  **<10% of variance** in human annotations. A 70B with persona prompting reaches **81% of the
  variance a linear regression on ground-truth annotations achieves.** ⭐ The persona channel has a
  **low ceiling**, and prompting already gets most of it.
- LLM-generated reviews show systematically different rating/sentiment distributions from real ones
  **[B]**, while being **indistinguishable to humans and detectors** **[B]** — the trap in one
  sentence: undetectable surface, wrong distribution.

---

## 7. Catastrophic forgetting and diversity collapse (all **[B]** unless noted)

- Forgetting manifests primarily as **loss of instruction-following**. LoRA "learns less and forgets
  less" but does **not** eliminate it — notable degradation after a **single epoch**. Mitigation:
  PEFT + a small rehearsal set, or a distillation loss.
- ⚠ **Preference-based post-training (RLHF/DPO) reduces generation diversity** across lexical,
  syntactic, semantic and conceptual dimensions. Root cause: **typicality bias** in preference data.
  https://openreview.net/forum?id=3pDMYjpOxk, https://arxiv.org/html/2510.01171v4 **[A]**
- ⭐ **The trap specific to us:** our problem is *already* too little diversity. A poorly-run
  fine-tune — especially anything preference-based — is one of the most reliable ways to make it
  worse. Use **plain SFT**, hold out an instruction-following eval, and **gate on an output-diversity
  measurement**.

---

## 8. Cost & feasibility, 2026 (all **[A]**, from live pricing pages)

**Closed frontier models — mostly a closed door.**
- ⚠ **OpenAI**, verbatim: *"OpenAI is winding down the fine-tuning platform. The platform is no
  longer accessible to new users."* If we have never run a fine-tune, **this is not an option.**
- **Anthropic**: no fine-tuning via the API. Only path is **Claude 3 Haiku SFT on Amazon Bedrock**.
  **No frontier Claude model is fine-tunable.**

**Open-weight via managed APIs — the only realistic path.**

| | ≤16B | 17–69B | 70–100B | >100B |
|---|---|---|---|---|
| **Together** LoRA SFT | **$0.48/M** | $1.50/M | $2.90/M | Qwen3-235B $6/M; DeepSeek-R1 $10/M |
| **Fireworks** LoRA SFT | **$0.50/M** | $3.00/M | $6.00/M | $10/M |

⭐ **A serious consumer-language LoRA (50M tokens × 3 epochs = 150M) on a ≤16B model costs ~$72–75.
On a 70B, ~$435. Fine-tuning is NOT the expensive part.** The expensive parts are assembling a
licensed corpus, **building the eval that tells you whether it helped**, and hosting. **The compute
is rounding error; the evaluation harness is the project.**

⚠ **Data volume reality:** Centaur used 10.7M choices; SocSci210 2.9M responses. Far beyond what a
small team scrapes. And **none of the successful fine-tunes trained on review prose** — they trained
on **labelled human choices / response distributions.** That is the actual lesson.

---

## 9. Cheaper alternatives, ranked by evidence-per-dollar

1. ⭐ **Statistical rectification with ~100 real human responses.** Bias **34.66% → 2.82%**.
   Difficulty **low** (estimation code, not ML). **Highest evidence-per-dollar item in the report.**
2. **Better conditioning variables.** KL 2.72 → 0.68. Difficulty **low**. ⚠ Over-conditioning
   reverses the gain — a 4-item instrument beat a 15-item one.
3. **Verbalized Sampling.** Training-free, recovers 66.8% of base diversity. Difficulty **very low**.
4. **Ground agents in real self-reports.** 74% → 82% from survey-only. Difficulty **medium**;
   privacy/consent is a liability surface.
5. **Retrieval / few-shot with real exemplars.** Helps **modestly**. ⚠ Real exemplars in context
   also **prime** the model toward the exemplars' register — the same trap as fine-tuning, cheaper
   to undo. ⚠ The often-cited "retrieval beat fine-tuned Gemini" number is from **code vulnerability
   detection** — don't transfer it.
6. **Style-only conditioning.** Use to make output readable, **never** to claim improved fidelity.

---

## 10. What the researcher recommends for a ~100-agent ad panel

1. ⭐ **Run the QC1/QC2 diagnostics before building anything.** If our panel average is more extreme
   than every subgroup average (as in ~80% of tested models), we have a bug no social layer or
   fine-tune will fix.
2. **Fix convergence with conditioning + sampling, not interaction.** Days, not months.
3. ⭐ **Buy ~100 real human reactions per stimulus class and rectify.** Highest-leverage spend here.
4. **If we want word-of-mouth as a phenomenon**, build it FDE-LLM-style: a few LLM "opinion leader"
   agents, a classical (Bass/SIR/threshold) layer over the crowd, explicit α. **Do not run
   all-to-all LLM discussion rounds.** And remember: **no herd effect at 100 agents.**
5. **Treat fine-tuning as a later, targeted move** — on labelled human judgements (SubPOP-style),
   **not** review prose; plain SFT, not preference optimisation; gate on instruction-following and
   diversity.

⚠ **Two things NOT to assume:** (a) how many peers/rounds constitutes a realistic dose of social
exposure — no ablation found; (b) any validation of an LLM consumer panel against real held-out
advertising outcomes — **that paper does not appear to exist.** If our instrument has never been
checked against a real market outcome, neither a social layer nor a fine-tune changes that; **only
the check does.**
