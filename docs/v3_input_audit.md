# What we actually send the agents — a humanness audit

**Date:** 2026-07-17 · **Branch:** `v3` · **Status:** audited → free fixes APPLIED (uncommitted, folded into render-6)

**Update (same day):** the **free-fix batch is now applied**, plus the expertise gate (§3) was reclassified from arm → now, because "knowledge scales with involvement" is *correctness*, not a two-option calibration — it generalises render-5's community gate, an already-validated pattern. Applied and live-verified two-sided (mid-involvement went hazy + jargon-free; the obsessive kept its estates). What is **still deferred:** the R-section **label** rename (STICKINESS/FRICTION/COMPREHENSION) → **#7**, because `synthesis_l2.py` reads those labels by name and renaming them without the L2 sync desyncs the read; the genuine **arms** → **Week-3 A/B**; the exact **brand-count** calibration → arm (the gate fixed expertise, not count). See §4 for the applied/deferred split.

---

Commissioned after the render-6 live check, on this observation:

> "we haven't been treating agents as real humans and hence they are not responding as real humans... it does not seem like they are responding as humans because our inputs are not treating them as humans"

This document prints the **exact bytes we send one agent**, in order, and judges each block. Nothing here is speculative — every quoted string is copied from a real assembled prompt (`scratchpad/agent_inputs_dump.txt`, reproducible offline at $0 via the deterministic assembly in `runtime.run_agent`).

---

## 1. The question this audit asks

"Is it human enough?" is unfalsifiable — every prompt is artificial somewhere, and that framing licenses an endless rewrite. The sharp version is already the spine of the v3 plan:

> **Does a real person in the Week-2 panel receive this too?**

That splits everything we send into two layers, judged by **different rules**:

| Layer | What it is | Does the panelist get it? | The rule |
|---|---|---|---|
| **Instrument** | The ad, the "what did your thumb do" pick, the reflection questions | **Yes** | **MATCH.** Any divergence breaks the apples-to-apples the whole plan rests on. |
| **Prosthetic** | The persona core, the context moment | **No** — they already *are* that person, with a real history | **BE, DON'T PERFORM.** It substitutes for a real life. It must read as a real self and never announce the substitution. |

This matters because it kills a tempting wrong answer. **The JSON and the enums are not the problem.** A human panelist also picks an action from a list — that is the instrument, and it is *supposed* to be shared. The problem is the jargon *around* the pick.

**The unifying defect is the fourth-wall break:** every place the prompt reminds the agent it is a simulation. Ranked by how hard each one shoves it from *being* toward *performing*.

---

## 2. The exact thing we send, block by block

### BLOCK 1 — SYSTEM (the whole system prompt: the persona core)

> She buys Bru or Nescafe Classic for the flat — whichever is cheaper when she checks Blinkit... She doesn't have a strong feeling about either brand; Bru is slightly stronger, Nescafe is fine, both work... that's someone else's Saturday project.
>
> **HOW THEY TALK (register only — how this person's sentences sound. Never repeat these lines.)**
> "blinkit pe bru ₹245 mein mila tha last time, so i just reordered that..."

*(This is a mid-involvement persona — an ordinary person with no strong opinions about coffee. Deliberately not the obsessive tail.)*

| # | Finding | Bucket |
|---|---|---|
| 1.1 | **Written in third person.** The agent reads a description of *someone else* and is asked to become them. This is the deepest framing question in the whole system, and it is exactly what an actor gets handed. | **Arm** |
| 1.2 | **`HOW THEY TALK (register only... Never repeat these lines.)` is a stage direction.** I added this caption deliberately, to stop parroting — and it works. But no real person has a caption above their own speech explaining that it's a register sample. It is an anti-parroting guard bought with a fourth-wall break. Honest tension, not a clean win. | **Arm** |
| 1.3 | **Seven brands for a woman with no opinions** — Bru, Nescafe Classic, Blinkit, Third Wave, Blue Tokai, Subko, Nescafe Gold. Nothing in the system permits her to *forget* one. See §3; this is an incentive we created, not a wording slip. | **Arm** |

### BLOCK 3 — USER: the context block

> **THE EXACT MOMENT THIS AD APPEARS IN THEIR FEED**
> It's mid-afternoon or early evening, and **they're** stretched out on the couch... the feed becomes **a soft conveyor belt of images and text** they're only half-reading... it drifts past in **the same gentle blur** as everything else.
> **WHERE THEY ARE IN THEIR BUYING CYCLE RIGHT NOW:** nearly out of coffee...
> Attention gates everything that follows... regardless of whether **the persona** would be interested in a more alert moment.

| # | Finding | Bucket |
|---|---|---|
| 3.1 | **"the persona."** We call the agent "the persona" *in its own prompt*. The single most explicit fourth-wall break in the system. | **Free fix** |
| 3.2 | **"BUYING CYCLE."** Nobody has ever thought "I am currently in the running-low phase of my buying cycle." The *fact* is fine and useful — the framing is a marketer's. | **Free fix** |
| 3.3 | **The context prose is still literary.** "A soft conveyor belt," "the same gentle blur." This is the exact register C3 just removed from the persona core — still here, because C3 was scoped to `_PERSONA_SYSTEM` only (spec §9). It sits ~200 words from the line telling the agent not to be literary. | **Free fix** |
| 3.4 | **Third person about itself** — "they're stretched out." The agent is told what *they* are doing, then asked to be them. Same root as 1.1. | **Arm** |
| 3.5 | **"THE EXACT MOMENT THIS AD APPEARS"** — the agent is told an ad is coming *before it sees one*. Real people don't know, and pre-announcing primes evaluation mode rather than scrolling. Filed must-keep because the panelist is also in a study and also knows — but that rests on a **panel-design choice we haven't made yet** (#10). If we decide not to pre-announce to humans, this becomes an arm. | **Must-keep** *(provisional — depends on #10)* |

### BLOCK 4 — USER: the ad copy block

> **AD COPY & OFFER** accompanying this image (read it as you would in feed, alongside **the visual**):
> **Headline:** The world has a pause button.
> **Body:** Find your moment at Starbucks.

| # | Finding | Bucket |
|---|---|---|
| 4.1 | **"AD COPY & OFFER", "the visual", "Headline:", "Body:"** — this is the Meta Ads Manager form, not what a person sees. A person sees words on a picture. We hand the agent a marketer's data structure and ask it to react as a consumer. | **Free fix** |
| 4.2 | **"read it as you would in feed"** — a stage direction. You only tell an actor how to read something. | **Free fix** |

### BLOCK 5 — USER: the Call A questions

> **ENCODING PHASE** — **you are a real person** glancing at an ad, **NOT a writer**... never eloquent, thorough, or clever — **no literary phrasing, no neat metaphors, no tidy summaries**. Three labelled sections.
> **R1 GUT:** ... **R2 COMPREHENSION:** ... **R3 INTEREST:** ...
> ACTION: ... `{"action": "...", "reasoning": "<one short **in-character** sentence, anchored to **the creative**>"}`
> ... **Never a funnel rate or a percentage.**

| # | Finding | Bucket |
|---|---|---|
| 5.1 | **"the creative."** Ad-industry jargon — and it **provably leaks**: the agent wrote *"nothing in the creative gives me a reason to stop."* No human says this. Already approved for fixing. | **Free fix** |
| 5.2 | **"in-character."** We explicitly instruct it to *act*. This is the thesis of this audit in two words. | **Free fix** |
| 5.3 | **"you are a real person... NOT a writer."** You only tell an **actor** to be real. And these are *negative* instructions, which prime the very thing they forbid — saying "no metaphors, no literary phrasing" puts literary phrasing in the room. render-6 fixed the persona core by changing **who the writer is** (a friend describing someone) rather than by adding prohibitions. The same lesson applies here and we haven't applied it. | **Arm** |
| 5.4 | **"Never a funnel rate or a percentage."** You only say this to something that might emit a funnel rate. A pure model-wrangling artifact sitting in a human's prompt. | **Arm** |
| 5.5 | **"ENCODING PHASE"**, **"Three labelled sections"** — research-instrument scaffolding. Low harm (doesn't leak into output), but it frames the whole exchange as a lab procedure. | **Free fix** |
| 5.6 | **`R1 GUT` / `R2 COMPREHENSION` / `R3 INTEREST`** — the *questions* were already de-jargoned in `4cbcca9` and are good. The **labels** are still ours, not a person's. The panel mirrors this structure, so the questions must match; the labels are cosmetic and could go either way. | **Must-keep** (questions) |
| 5.7 | **JSON + the action enum.** Not a defect. The panelist picks from the same list. This is the instrument working as designed. | **Must-keep** |

### BLOCK 6 — CALL B: the reflection

> **REFLECTION PHASE** — a day or two later, **still a real person**, still plain and short... If an ad left almost nothing behind, say so plainly — **don't manufacture depth**.
> **R4 STICKINESS:** ... **R5 SOCIAL:** ... **R6 FRICTION:** ...

| # | Finding | Bucket |
|---|---|---|
| 6.1 | **"still a real person."** Same defect as 5.3, and the word "still" makes it worse — it implies the agent has been drifting out of being one. | **Free fix** |
| 6.2 | **"don't manufacture depth."** Only a model manufactures depth. A person cannot be instructed not to. | **Arm** |
| 6.3 | **"STICKINESS" / "FRICTION"** — marketing words used as labels for a human's experience. Nobody has ever been asked what their "friction" was. Questions themselves are fine. | **Free fix** |
| 6.4 | **next_step enum** (`buy_at_restock`, `mention_to_someone`) — instrument; the panel mirrors it. | **Must-keep** |

---

## 3. The separate finding: we pay them to be product catalogues

This is not a wording bug. It is an **incentive we built**, and it is the thing the user caught by eye.

**First, a correction — the obvious suspect is innocent.** My initial draft of this section blamed the test suite. It is worth stating what the check actually says, because it points the fix somewhere else:

```python
assert n_artifacts >= 2, f"persona core wove only {n_artifacts} pack brands — too flat"
```

A floor of **two**. Two brands is not a catalogue — it is almost exactly the "few, known well" target. The test is a **floor, not a target**, and nothing in it pushes a persona *above* two. It is fine as it stands and should not be touched.

**The actual driver is the prompt.** `_PERSONA_SYSTEM` tells the render engine:

> *"Concrete over abstract. Real brand + real price + real channel beats a generic phrase."*

...while `_pack_brief` hands over the pack's **entire** brand list, and render-3's anti-homogenization rule instructs it to *"Scan the WHOLE pack and select only the brands... that fit THIS vector."* Every one of those pressures rewards naming more, and nothing anywhere rewards a person **forgetting**. So the result is a woman with **no strong feelings about coffee** name-checking seven brands with exact prices.

Real people know two or three brands well and are **hazy about the rest** — they misremember prices, confuse sub-brands, forget names entirely. **We have no instruction that permits vagueness**, and that absence is the finding.

**Do not fix this by loosening render-3.** That rule exists because it fixed a real and worse failure: personas going flat and homogenizing into the same generic person. The target is not *fewer artifacts* — it is **"a few, known well, vague elsewhere,"** which is a *calibration between two failure modes*, and calibrations get measured, not guessed. → **Arm.**

Note the tail-vs-middle distinction: the "Attikan estate vs Bibi Plantation for a V60" persona was an **obsessive** — an extreme I built to test differentiation. A real obsessive *does* talk that way. But the mid-involvement persona above shows the same density at the middle, where most of a real panel lives, and that is where it distorts the aggregate number.

---

## 4. What I recommend

**Free fixes — jargon and stage directions, no change to the shape of what is measured.** These land on **two different surfaces**, which must not be conflated:

| Surface | Items | Consequence |
|---|---|---|
| **The reaction prompt** (`runtime.py` — the frozen reaction-v3 contract) | 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 5.5, 6.1, 6.3 | Batch into **one** change so the frozen contract moves exactly once, **before #8 pins it** with byte-identity guards and before #10's panel mirrors it. Per spec §10 a wording change needs no version bump (structure is unchanged). |
| **The render prompt** (`render.py` — `_CONTEXT_SYSTEM`) | 3.3 only | This is *not* the reaction surface. It is the same file and versioning story as render-6, and changing it busts the **context render cache** (`context_render_hash` includes `RENDER_PROMPT_VERSION`). Cheap — contexts are few and re-render for cents. Naturally folds into the uncommitted render-6 work. |

**Arms — do NOT fix by hand.**
Items 1.1, 1.2, 1.3, 3.4, 5.3, 5.4, 6.2, and §3. Every one changes *how the persona fundamentally engages*, and the honest answer to each is empirical. Week 3 exists precisely to A/B these against the human panel on frozen seeds. **Rewriting them now, on intuition, right before the instrument first touches reality, is the one move that could poison both the σ study (#9) and the human comparison.** The strongest single arm candidate: **second-person persona framing** (*"You buy Bru or Nescafe..."*) versus today's third person.

**Must-keep — and say why in the report.**
Items 3.5, 5.6, 5.7, 6.4. The scaffolding the panel mirrors. Shared artificiality is not a defect; it is what makes the comparison valid.

---

## 5. The honest summary

The observation that prompted this audit is **correct, and stronger than it first looked.** We tell the agent it is "the persona," instruct it to write "in-character," hand it a Meta Ads Manager form, tell it where it is in its "buying cycle," ask it about its "friction," and then — three separate times — tell it to be a real person and not a writer. Then we are surprised it answers like a marketer playing a consumer.

But the fix is **not** one big humanising rewrite. Half of these are free and should go now; the other half are real design questions whose answers are unknown, and the v3 plan already has the machinery pointed at them. The failure mode to avoid is fixing the deep ones by fiat and arriving at Week 2 with an instrument that *feels* more human and is measurably unanchored.

**One caveat on the whole exercise, stated plainly:** every judgement in this document is mine. That is the same weakness the v3 plan exists to fix — the loop closing on the engine's own opinion of itself. The Week-2 panel is what settles it.
