# Recovered findings — from the ten agents that died before writing up

**2026-08-04.** The ten agents killed by the session limit produced almost no prose, but they had
already **fetched 2.1 million characters of pages**. This file is what was mined back out of those
raw transcripts.

⚠ **Status of everything below: RECOVERED, NOT WRITTEN UP BY A RESEARCHER.** Much of it is
search-result summaries rather than primary sources the agent read and judged. Numbers are quoted
as the page stated them. **Verify before any of it is used in a decision or shown to a customer.**
Where a claim is a vendor's own marketing, it is labelled as such.

---

## 1. ⭐ SimBench — the benchmark that answers "which model"

**SimBench: Benchmarking the Ability of Large Language Models to Simulate Human Behaviors**
(April 2026) — https://arxiv.org/html/2510.17516v4

This is the paper that was being hunted when the model-choice agent died. Recovered findings:

- **All evaluated models show negative mean ΔS** when simulating specific demographic groups —
  degradation ranged from **−1.27 (DeepSeek-V3-0324)** to **−4.61 (Claude-3.7-Sonnet-4000)**.
- ⚠⚠ **THIS READING WAS WRONG — see `04_simbench_read.md`, the paper has now been read.**
  ΔS is **not** a quality score: it is `S_grouped − S_ungrouped`, the *penalty* a model takes when
  conditioned on a demographic group. On the actual benchmark **Claude-3.7-Sonnet is the
  TOP-SCORING model of all 45, at 40.80/100.** The recovered search summary listed ΔS values with
  no overall scores beside them and this note misread them as a ranking. There is no case here for
  moving off Claude. Left in place as a record of how the error happened.
- **GPT-4.1 is called out as "a notable outlier"** — performing differently from other LLMs on
  simulation tasks. Direction unstated in the recovered text.
- ⚠ **Models fail worst on traits that conflict with alignment objectives** — "even the best LLMs
  often performing worse than a uniform baseline on datasets measuring Machiavellianism,
  conspiratorial beliefs, or humor rating." Relevant to us: cynical, dismissive, or contrarian
  consumers are exactly the register an aligned model will flatten.

Related recovered lead: **"Instruction-tuned models outperform base variants at >10B parameters but
invert at smaller scales."** So the "use a base model for diversity" idea is not free advice — it
appears to depend on scale.

---

## 2. ⭐ Confirmation bias INCREASES diversity — a concrete mechanism

**Törnberg, Valeeva, Uitermark & Bail** (arXiv:2310.05984) plus a related opinion-dynamics paper
recovered in the same thread:

- **Diversity (D) rose from 0.60 → 1.24** under false framing with **strong confirmation bias**
  (cumulative memory).
- *"Introducing confirmation bias in the prompt leads to less ultimate consensus (i.e., greater
  diversity D) across LLM agents."*
- ⚠ **Without cognitive bias, "opinion trajectories quickly converge towards the truth after social
  interactions"** — for both true AND false framings.

⭐ **This nuances the headline in `02_social_layers_and_finetuning.md`.** Agents converge not merely
because they interact, but because **they lack the cognitive biases that keep real people apart**.
That is a mechanism we can act on — and it is stimulus/persona-side, not social-layer-side, so it
does not contradict the "prompt-side realism is theatre" warning: a confirmation-bias *disposition*
changes what evidence an agent accepts, not merely how it narrates.

---

## 3. The competitor landscape — claims, and what they actually mean

⚠ **Everything in this section is vendor marketing unless stated otherwise.** The pattern worth
noticing: the impressive headline number is almost always a *directional replication* rate, while
the *correlation* — the number that matters for ranking creative — is far lower when disclosed.

### Synthetic Users (syntheticusers.com)
- **"93% replication accuracy against real human behavior"**, "validated against **350+ published
  human studies** across 20+ domains", "**417 replicated study runs**".
- ⭐ **Their own definition, recovered:** *"93% is replication accuracy: how often simulated studies
  reproduce the **direction and outcome** of the original human studies."* That is a
  **sign-agreement** rate, not accuracy in any sense a marketer would assume.
- ⭐ **The number they do not lead with:** *"0.55 rank correlation across approximately 300
  replications, with 0.73 on the 43 passing design filters."* And for one conjoint replication:
  **0.64 rank correlation, 73% sign agreement.**
- Also claims "85 to 92% parity with real human insights for usability-focused research."

**Read:** a 0.55 rank correlation is the honest figure for "can it rank things correctly." That is
the number our own product should be compared against, not 93%.

### Aaru (aaru.com)
- Predicted a **New York Democratic primary within 371 votes** without surveying real people.
- ⚠ **But: "Aaru's 2024 presidential election prediction was largely inaccurate compared to its
  earlier success with the New York primary."** The famous hit is followed by a public miss.
- To their credit, recovered from their own material: *"A close fit to historical data does not
  prove the model will hold."*

### Evidenza
- Founders claim **"95 percent accurate customer responses"**; also "95% Accuracy Compared to human
  self-replication", "90% persona internal coherence", "95% opinion distribution accuracy".
- **EY case study: median Spearman correlation 0.90** across **3,600 affluent investors**, with
  **7.1 percentage points average difference per question**. "100+ validation tests."
- Salesforce testimonial: "correlation was very strong at 0.81".

### Artificial Societies
- **"86% accuracy"**, positioned around instant access to "Fortune 500 executives, rare specialists,
  and hyper-specific demographics."

### Fairgen (fairgen.ai)
- **"Average 3× boost"** in effective sample, validated across "hundreds of parallel tests" and
  "10,000+ concurrent boosts".
- ⭐ **The caveat that matters: "but only below 15% segment size."** Their method augments *small
  segments* of a real survey — it does not replace the survey. Different product from ours.
- Framing worth stealing: improving accuracy "from ±7% to ±5% is like doubling the sample."

### Roundtable (roundtable.ai)
- Actually a **bot-detection** company in what was recovered: "Proof of Human 86.7%" vs reCAPTCHA v3
  69.3%, hCaptcha 64.7%, FingerprintJS Pro 36.0%, Cloudflare Turnstile 33.3%. Adjacent, not a
  competitor.

### ⚠ Viewpoints AI
The agent confirmed before dying that **the validation paper's authors ARE the company's own
founders**. Do not treat that ~88% figure as independent validation.

---

## 4. ⚠ The incumbents are already shipping synthetic AD pre-testing

This is the competitive fact we did not have.

- **Zappi — "Creative Pre-Test Instant"**, verbatim: *"combines synthetic personas with validated
  benchmarks to deliver ad testing results **more than 120× faster**."* ⭐ **This is our product
  category, from an established player, already launched.**
- **Qualtrics Edge** (launched March 2025; synthetic panels announced at X4, March 2026): claims
  **"12 times better accuracy in matching human responses than general-purpose AI"** — and,
  importantly, the model *"was trained on millions of validated human responses and hundreds of
  thousands of distinct research questions."* ⭐ **That is the grounding strategy, at a scale we
  cannot match by scraping.** Expanding to UK, Canada, Australia, NZ.
  - Offers **100% synthetic, 100% human, or blended** — synthetic for fast concept screening, human
    panels for high-stakes validation.
- **Toluna HarmonAIze Personas** — "Access 200+ global markets through traditional panels or
  research-grade synthetic respondents."

⭐ **The strategic read:** the incumbents are converging on **blended** — synthetic for screening,
human for the decision. Nobody credible is selling pure synthetic as a decision instrument. That is
consistent with everything in reports 01 and 02, and it is an argument for our diagnosis-not-
prediction positioning rather than against it.

---

## 5. India / adjacent players
- **Entropik** (Bengaluru, founded 2016, Series B) — multimodal emotion AI; "Decode" platform
  claims to accelerate research 6×; Fortune 500 customers.
- **Listen Labs** — $27M, Sequoia-backed, AI market research.
- Market research sector sized at **$140 billion** in the recovered material.
- One source identified two India-specific opportunities: a **"panel-aggregation layer"** over
  consumer-tech behavioural data (purchase patterns, price sensitivity), and an **"AI-native
  services firm"** consolidating outsourced back-office research work.

---

## 6. Diversity engineering — additional recovered detail

Beyond what is already in report 02:

- **Verbalized Sampling** is **orthogonal to sampling parameters** — the paper's own ablation
  (§F.3) tested temperature, top-p and min-p and concluded VS *"can be combined with them to
  further enhance the diversity-quality trade-off."* ⭐ So we do not have to choose between VS and
  temperature tuning.
- **Bigger models benefit more:** *"Larger models (GPT-4.1, Gemini-2.5-Pro) achieve diversity gains
  1.5 to 2 times greater than smaller models."*
- Reported as **2–3× diversity improvement while maintaining quality** across creative writing,
  **social simulation**, and synthetic data generation.
- The verbalized distribution aligns with a pre-training-corpus proxy at **KL = 0.12**.
- **min-p sampling** ("Turning Up the Heat", 2024) is a further lever claiming better
  quality *and* diversity than top-k/top-p. ⚠ Anthropic's API does not expose min_p.
- ⭐ **Persona conditioning has a hard ceiling, restated from two independent sources:**
  *"Sociodemographic summaries alone explain only about 1.5% of variance in human behavioral
  responses"*; *"persona variables account for just 1.4%–10.6% of the total variance."* But
  *"adding structured values, identity narratives, and personality measures amplifies behavioral
  fidelity and reduces demographic over-accentuation."*
  **Translation for us: our disposition anchors are the right idea; more demographic detail is not.**

---

## 7. What is still genuinely missing

The fetched pages cover these thinly or not at all, because the agents died mid-search:

- **Model comparison with real numbers** — SimBench is identified but not read. This is the biggest
  remaining gap, and it bears directly on whether we should move off Claude for the agent layer.
- **Fine-tuning cost/feasibility detail** beyond what report 02 already carries.
- **Mistral / Qwen / Llama API specifics** — three agents were mid-flight on these.
- **ESOMAR / MRS / Greenbook formal guidance** on synthetic respondents — only one Greenbook
  fragment was recovered.
- **Independent (non-vendor) evaluation of any commercial synthetic panel** — the agents found
  vendor claims and academic critique, but nothing in between.
