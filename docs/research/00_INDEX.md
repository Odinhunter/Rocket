# Agent-realism research — 2026-08-04

Commissioned after the user observed that panel agents kept wanting to "search for protein bars on
Nykaa," that reactions felt insufficiently human, and that there was no chaos and no social world.

## What is here

| file | what it is | status |
|---|---|---|
| `01_attention_and_chaos_realism.md` | How ads are ACTUALLY processed in-feed, and what that means for our panel. The Heath / Nelson-Field / Lumen / Ehrenberg-Bass evidence, plus 10 graded design encodings | ✅ complete |
| `02_social_layers_and_finetuning.md` | Whether to add a social layer (answer: not the way we assumed), and whether to fine-tune (answer: not on review prose) | ✅ complete |
| `03_recovered_from_dead_agents.md` | Mined back out of the ten dead agents' raw transcripts: SimBench, the competitor claims, the incumbents already shipping synthetic ad testing | ⚠ recovered, unverified |
| `04_simbench_read.md` | ⭐ The ICLR 2026 benchmark, read in full. Sets the ceiling for the whole field (best model = 40.80/100) and explains our homogeneity problem. **Corrects an error in file 03.** | ✅ primary source |
| `00_RAW_SOURCES.md` | 2,853 URLs the agents reached, indexed; plus the map of raw transcripts | ✅ index only |

**Ten further agents died on a session limit before writing up** — but they had already fetched
**2.1 million characters** of pages, and `03_recovered_from_dead_agents.md` is what was mined back
out. **SimBench has since been read in full — see `04_simbench_read.md`.** The remaining gap is
non-vendor evaluation of commercial panels.

## Two leads captured before those agents died — UNVERIFIED, chase before use

1. **Larooij & Törnberg (2025)** reportedly **contradicts** the naive reading of the social-
   simulation literature. The agent flagged it as a "major finding" against Chuang. Not yet read.
2. ⚠ A vendor's **~88% accuracy** validation claim where the agent confirmed **the paper's authors
   ARE the company's own founders** (Viewpoints AI). Exactly the kind of conflict worth catching —
   do not cite that number as independent validation.

---

## ⭐ The through-line across both completed reports

Three findings recur independently, which is why they are worth acting on:

**1. Prompt-side realism is theatre; stimulus-side realism is real.**
ABxLab (17 models, 80,000+ trials): *"Agents appear to reproduce human-like heuristics and biases
without sharing the cognitive constraints that motivated such theories."* Telling an agent it is
distracted produces a **performance of distraction** — fluent, stereotyped, uniform. The model has
already read the whole ad. **Only removing information from the context creates a real constraint.**

**2. A social layer would make our convergence problem worse, not better.**
Agents over-converge relative to real humans (DEBATE); conformity 39% → 74% next to one confident
peer; multi-agent debate *lowers* accuracy. And OASIS — the best-validated social simulator —
observed **no herd effect at 100 agents**, which is our panel size. What restores heterogeneity is
**conditioning and sampling**, not wiring agents together.

**3. Our current problem is the well-documented failure mode, and it has a second half we had not
measured.** LLM panels flatten individuals **and caricature groups at the same time**: between-
segment gaps inflate 2–4×, models pick the wrong segment in 50–72% of pairs, and **manufacture
segment splits that do not exist in up to 41%** of cases. Our product reports segment differences.

## What this implies for the Nykaa finding specifically

Our own diagnosis (see `HANDOFF.md`) found Nykaa was **planted by us** in the disposition anchors,
said by **5 of 100** agents, and promoted to a **top-3 ranked recommendation**. The literature says
that promotion path is the real defect: with no count of *people* behind a pain, an artefact of the
persona corpus becomes advice. The cheapest fixes the research supports are all things we can do
without any model change:

- ⭐ **Run the QC1/QC2 diagnostics** (Neumann et al.) on the existing panel first — ~80% of tested
  models failed a basic convex-combination check. Free, and it is a bug-finder.
- **Count people, not disposition labels**, before a signal becomes a pain.
- **Stop at ~15 conditioning variables** — 59 was *worse* than demographics alone.
- **Skew the panel toward light and non-buyers** (~80% of a brand's buyers buy once a year or less).
  This flattens over-eager responses by itself, with no prompt trickery.
- ⭐ **~100 real human reactions + statistical rectification** cuts bias 34.66% → 2.82%. Highest
  evidence-per-dollar item in the entire research set, and it points straight at the paused human
  panel (`panel/v3_human_panel/`).

## The uncomfortable part

**No paper was found validating an LLM consumer panel against real held-out advertising or market
outcomes.** That paper does not appear to exist. Neither a social layer nor a fine-tune changes
that — only the check does. This is the same conclusion the project already reached from the inside
(memory: `v3_one_month_plan`, "the instrument has still never touched reality"), now confirmed from
the outside.

Fine-tuning compute is **~$75–450** — rounding error. **The evaluation harness is the project.**
