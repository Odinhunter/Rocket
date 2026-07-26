# v3 discriminant check — does the engine tell a bad ad from a real one?

**Date:** 2026-07-26 · **Branch:** `v3` · **Cost:** $0 (all runs already on disk) · **Status:** complete

Closes the open question the σ study left in `docs/v3_sigma_study.md` §4:

> the AI-buzzword *control* — built to be a bad ad — lands the **same** MIXED / ITERATE
> as the real MB creative. […] **Whether the *pains* separate them is the open question.**

**Answer: yes, the pain layer separates them. The headline does not — but the precise
defect is narrower and nastier than "the headline has no discriminating power": it
correctly fails a genuinely weak real ad (ProSki → REBUILD / FAILING 82) while producing a
**false negative on the deliberately-bad control** (MIXED 74 / ITERATE, same as the real
ads). Discrimination on the control rests entirely on the diagnosis, not on the score.

---

## 1. The comparison had to be re-paired first

The σ study framed this as **CONTROL vs MB**. That pair is not interpretable, because
the target classifier does not read the two ads as aimed at the same people:

| run | within-target disposition(s) |
|---|---|
| MB whey (×4 repeats) | `enthusiast_macros_lifter` |
| AI-buzzword CONTROL | `aspirant_clean_label` |
| The Whole Truth (TWT) | `aspirant_clean_label` |
| ProSki cereal | `aspirant_clean_label`, `pragmatist_protein_snacker` |

Pains stated against different audiences differ for audience reasons, which would
confound any "are these the same diagnosis" read. So the comparison used here is
**CONTROL vs TWT** — a deliberately-bad ad and a real, well-regarded ad that the engine
independently read as targeting the *same* buyer. **This substitution is what makes the
comparison mean anything**; it is a departure from the question as originally posed.

Note that the re-pairing is itself a result: **target ID discriminates.** Reading the
per-disposition `reasoning` in `target_classification.json`, the classifier rejects
`enthusiast_macros_lifter` for the control on stated grounds ("pink pastel wellness
aesthetic … 'AI-designed for Longevity' with no macro-per-rupee proof reads as marketing
puff to him") — a defensible call, not a coin flip.

---

## 2. Result: three layers, not one

| layer | discriminates? | evidence |
|---|---|---|
| **Target ID** | **yes** | different within-target audience per ad, with stated reasoning |
| **Pain layer** | **yes** | CONTROL vs TWT share 2/6 pains, both generic; the distinguishing pains are ad-specific and correct |
| **Headline bucket** | **false negative on the control** | ProSki (real, weak) = FAILING 82 / REBUILD — correctly separated. But CONTROL = MIXED 74 / ITERATE, indistinguishable from MB (MIXED 74–78) and TWT (MIXED 74) |

The headline is not inert — it fails ProSki decisively. What it does is **miss this
particular bad ad**, which is the more dangerous shape of error: a confident non-alarming
score on a creative built to be bad.

**The 2 shared pains are the generic ones** — "no price on the creative" and "brand name
doesn't encode." Those apply to most weak ads and carry no diagnostic signal.

**The distinguishing pains are ad-specific:**
- **CONTROL** uniquely names the planted defect — *"the 'AI-designed' hero claim is a net
  trust-subtractor … the flagship claim is doing negative work."* Its #1 prescribed fix is
  "Replace the 'AI-designed' hero line."
- **TWT** uniquely names two **structural** product-market facts — unflavoured format as a
  pre-emptive disqualifier, and whey-vs-plant-based as a category boundary the target has
  pre-committed against. Neither appears anywhere in the control's map.

The prescriptions are correspondingly non-transferable: you could not paste the control's
fixes onto TWT, or vice versa.

---

## 3. The strongest evidence: the planted defect replicates across three protocol generations

The control ad is a **known-ground-truth artifact** — it was built bad on purpose, and we
know exactly how: the hero line reads *"AI-designed Functional Protein for Longevity /
Clinically-inspired. Backed by Nutritional Science."* Content-free buzzwords over a pastel
range shot, no price, no CTA.

Every independent run of this creative names that defect:

| run | protocol | headline | names the planted defect? |
|---|---|---|---|
| `20260609_232243` | `rocket-2.0.0` | **FAILING 45** | ✓ fix #1 = *"Kill 'AI-designed' as the lead claim"* |
| `20260707_010253` | `rocket-2.2.0` | MIXED 76 | ✓ P2 = *"'AI-designed' headline is a net trust-negative … hollow tech buzzword"* |
| `20260721_023238` | `rocket-3.0.0-dev` | MIXED 74 | ✓ P2 = *"net trust-subtractor … the flagship claim is doing negative work"* |

Three separate draws, three protocol generations, same finding. This is stronger evidence
than any text-similarity metric, because the ground truth is known rather than inferred.

---

## 4. Grounding check — the *panel* earned this, not the vision model

**This check was necessary and nearly got skipped.** The planted defect is *legible text in
the ad*. A vision model reading the image could produce "AI-designed reads as buzzword
filler" with no panel at all. That would make the finding a property of the pipeline's
image-reading, not of the simulated consumers — and the simulated consumers are what the
product sells.

There is a second contamination risk that had to be ruled out, and it is the exact
mechanism that killed `brand_recall` in v2.4: **Call A's R2 asks "What is this selling, and
who do you think it's for"** (`agent/runtime.py:125`). A persona naming "AI-designed" in
answer to that question is *reading the headline back*, not reacting to it. So a raw
mention count is not evidence. Splitting mentions by reaction section decides it:

| where the AI claim is named | agents (n=100) | is it readback? |
|---|---|---|
| **R2** — "what is this selling" | **7** | ← the readback slot, and it is nearly empty |
| **R1** — gut, *"the first thing that goes through your head"* | **20** | no — precedes any "what is it" question |
| **R3** — *"did any of it catch your interest"* | **39** | no — evaluative, not descriptive |
| **named in an explicitly skeptical/evaluative sentence** | **40** | **no — a judgment cannot be readback** |

**The readback hypothesis is falsified.** Mentions cluster in the gut and interest
sections and are almost absent from the comprehension question that would have produced
readback. The load-bearing number is **40 of 100 agents naming the AI claim in an
evaluative sentence** — not the 79 who mention it at all.

Two precision notes on those counts. **The 40 is a lower bound, not a measurement** — it
comes from a hand-built keyword pattern for skeptical language, and it moved from 33 to 40
when the pattern was widened, so the true figure is somewhere at or above 40. And the
section counts do not sum to 79 because the remainder name the claim in the **terminal
action JSON's `reasoning`** rather than in an R-section (e.g. *"too tired to even process
what 'AI-designed' means"*), which is also not readback.

Also verified:
- **All 4 evidence quotes for P2 are verbatim agent output.** Not paraphrase, not invention.
- **It crosses dispositions** (any mention): `skeptic_lapsed_protein` 15/15,
  `aspirant_clean_label` 21/24, `enthusiast_macros_lifter` 17/19,
  `pragmatist_protein_snacker` 17/23, `switcher_results_chaser` 9/19.
- Sample verbatims: *"'AI-designed' didn't make me trust it more, it made me trust it
  less"* · *"the AI angle felt a bit try-hard, so it kind of washed over after that"* ·
  *"'AI-designed' is giving me marketing speak"*.

**Positive control** — TWT's structural pains are *not* fully legible from the image, so
they must come from the agents, and they do: all quotes verbatim; **54/100** agents raised
"unflavoured," **43/100** raised the whey-vs-plant-based boundary. Sample: *"it's whey, not
plant-based, so it's basically already disqualified for me."*

So the pain layer is distilling something the panel actually produced.

---

## 5. A regression this surfaced: the headline used to separate, and stopped

`rocket-2.0.0` scored this control **FAILING 45** against real creatives at MIXED 58 and
MIXED 62 — the discriminant-validity control recorded as *passed* in memory
(`health_wellness_first_test_pending`, 2026-06-09). **Verified on disk, not taken from
memory:** `20260609_232243` = FAILING 45; `20260607_145758` (Plix biotin) = MIXED 58;
`20260608_234535` (Wellbeing collagen) = MIXED 62.

**The original pass was already thinner than the one-line summary suggests, and the
long-form record says so.** Under v2.0 the MB ad itself scored **MIXED 45 / 48** — the same
number as the control's 45. The separation was carried by the **verdict label** (FAILING vs
MIXED), not the confidence score. The 2026-06-09 note in
`health_wellness_first_test_pending` states this explicitly ("the real discriminator is the
VERDICT BUCKET … confidence 45 coincidentally equals MB Biozyme's MIXED@45 — it's the
`single_within_target` ceiling, not a discriminating signal") and flags itself as N=1. So
what v3 lost is the *label* separation, which was the whole of the original signal.

**That pass no longer holds at the headline layer**: from `rocket-2.2.0` onward the same ad
scores MIXED 76 / 74 — level with the two real ads it should have been separated from (MB,
TWT), though still below ProSki's FAILING 82.

This is consistent with the v3 honesty rework compressing the headline's range (the same
family of change as MB `would_act` 0.68 → buy-intent 0.03). The number got more honest and,
on this creative, lost its alarm at the same time.

**Stated precisely:** the headline did not lose discriminating power in general — it still
fails ProSki at FAILING 82 / REBUILD. It lost it *on this control*, i.e. it now emits a
**false negative on a known-bad ad**. That is a specific, nameable defect worth carrying
forward, not a blanket verdict on the metric. **On this creative the pain layer carries
discrimination by itself.** Whether the headline should be re-widened is a separate, open
decision — not resolved here.

---

## 6. Limitations — state these, don't smooth them

1. **No measured noise floor for the discriminating pair.** The repeat-draw baseline is
   MB-only — all 4 v3 draws inspected, and the pattern is *stable core, rotating tail*:
   two within-target pains recur in **4/4** draws (no reason-to-switch / "variant not
   upgrade"; missing price-per-serving), as do both outside-target pains (lapsed-buyer
   brand scar; gym-bro semiotics). The remaining ~2 within-target slots rotate across
   ~4 themes (seal under-leveraged, self-narrowing to cutting/lactose, restock-timing
   mismatch, zero net-new information). So the *load-bearing* diagnosis is reproducible
   and the tail is not. But there is **no repeat-draw baseline for an
   `aspirant_clean_label` ad**, so it cannot be claimed as *measured* that the CONTROL/TWT
   gap exceeds within-creative noise. The planted-defect replication carries the
   conclusion; the signal-to-noise comparison was not run.
2. **The qualitative "these are different diagnoses" read is a judgment**, made by a model
   that knew which ad was which. The objective legs are the replication (§3) and the
   grounding counts (§4); the qualitative diff (§2) is supporting, not load-bearing.
3. **n=1 control run per protocol generation.** Replication is across generations, not
   across draws within v3.
4. **This is discriminant validity, not criterion validity.** It shows the engine
   distinguishes a bad ad from a real one on named, grounded mechanisms. It does **not**
   show the named pains are the pains real consumers have — only the consumer panel
   (pain-overlap kill-criterion) can do that, and it remains paused.

---

## 7. Consequences

**For the deliverable — the finding stands; the page order it first produced did not.**

⚠ **SUPERSEDED (2026-07-27) — read this before citing the order below.** The first response
to this finding was to demote the verdict bucket to the back half of the page, behind the
diagnosis and the fixes. That over-corrected. On the client page it produced a report that
opened on caveats and prose and never told the brand manager what happened — the user's
verdict on it was that it "looks terrible and doesn't inform the brand manager of anything."
**The finding was right; the remedy was wrong.** Burying the bucket does not make it more
reliable, and it makes the reader hunt for an answer and read the page backwards to find it.

**Current order (2026-07-27, the user's specified narrative), five beats:**

    header → warnings → RESULT (verdict → numbers) → DIAGNOSIS → PROBLEMS
           → SOLUTIONS (levers → fixes) → EXTRAS (strengths, context, voice, notes, footer)

**The verdict LEADS the page — the user's explicit call, asked twice** (*"Isn't this the
verdict we want to claim?"*). An intermediate version placed it after the numbers so the
bucket would read as a summary of a mix already seen; the user overruled that. **This is
their product decision and it is recorded as such — do not quietly re-demote it.**

**How the finding is honoured now that burial is off the table — three things:**
1. **`VERDICT_CAVEAT` is load-bearing, not decoration.** *"Didn't separate a known-bad
   control — tiebreaker, not gate"* renders INSIDE the verdict block, in every decision
   state including INCONCLUSIVE. With the bucket leading the page, a reader who goes no
   further has read the bucket and this line and nothing else — so this line is the entire
   honesty budget of the opening screen. It must not migrate to a footnote, become
   conditional, or be dropped in a restyle. Two tests pin it, both mutation-proved.
2. **The caveat is verified to sit between the bucket and the numbers on all 56 runs**, not
   merely to be present somewhere on the page.
3. **The diagnosis got its own beat, ahead of the problems.** A derived overview
   (`build_diagnosis_overview`) counts the problems, how many land in-target, how many are
   structural, which funnel stages leak, and names the load-bearing one. It is the layer
   that *did* discriminate, so it is stated as a pattern before the cards, where the reader
   can act on it — rather than having to infer it by reading six cards in sequence.

Implementation notes that still matter:
- **The warnings stay pinned ABOVE the result, and this is load-bearing.** The tempting move
  was to file them under the user's five beats and let them ride below the result band.
  Three of the four qualify **the numbers, not the diagnosis** — coherence qualifies the buy
  tile, launch scope the headline metric, panel degradation every denominator on the page —
  so below the band each would arrive *after* the figure it exists to qualify. They are
  empty on most runs (3 fired across all 56 on disk), so the page still opens on the result.
  ⚠ The pre-existing test asserted only that caveats precede the *pain cards*, which stays
  true under the wrong placement — it would have passed green while the guardrail was gone.
  It now asserts precedence over the numbers too.
- **The ranked levers stay adjacent to the fixes they summarise.** Unchanged and still true:
  `_bets`' heading is decision-keyed call-to-action copy (`"TO GET A TRUSTWORTHY READ:"` on
  INCONCLUSIVE), so separating the two reads as two competing fixes sections.
- **INCONCLUSIVE is unchanged and still leads with the notice.** `_numbers` renders nothing
  in that state, so "lead with the result" is vacuous there and the untrustworthy-read
  notice takes the top naturally — the sharpest case, still handled.
- **`batch_run._print_report` was deliberately left alone,** and this reorder converges it
  toward the terminal view rather than away (both are now bucket-early). Presentation order
  is legitimately per-surface; the shared *vocabulary* in `read_model.py` still has exactly
  one definition, which is the drift that actually matters.

Verified: 7 cross-section order tests (suite 297 → 302), **each proven non-vacuous by
mutation** — every mutation was caught by the test claiming to pin it, and every restore
recovered. Then asserted on real data: all **56** finished runs across every brand and
protocol version render *and* satisfy the five-beat order contract (16 carry a diagnosis
section, 11 a numbers section, 3 fire a warning surface); the 9 incomplete runs still refuse
loudly.

**⚠ A SECOND REAL BUG FELL OUT OF THIS — the renderer's funnel was missing a stage.**
`report_html._STAGE_ORDER` listed **four** stages; `schema._VALID_FUNNEL_STAGES` has **five**
— `recall` was absent, and **9 pains on disk use it**. It never errored: unknown stages sort
last, so pain-card ordering was accidentally correct and nothing surfaced. The new diagnosis
overview is what made it matter — its stage row would have rendered four chips and implied
the funnel *has* four stages and that recall is not somewhere a creative can leak. Fixed by
making `read_model.FUNNEL_STAGE_ORDER` the single five-stage definition both surfaces use,
**pinned by an anti-drift test against the schema's own enum** (mutation-proved: deleting
`recall` fails it). Pain-card sort order is byte-identical before and after — `recall` sorted
last as an unknown and still sorts last as a known. Same family as the glance bug: *a fixed
list of enum members, hand-maintained in a renderer, silently under-reports.*

⚠ One false positive worth recording from that real-data sweep: an INCONCLUSIVE run tripped
a "still shows a rate" check because a persona verbatim contained the words *"something
Amma would buy for guests."* The guardrail was intact — the check was grepping prose. **Any
assertion that a suppressed surface is absent must match structural markers, not text**, or
model-authored copy will keep firing it. Same family as the §5 readback rule.

⚠ Testing gotcha hit while proving non-vacuity: reverting a mutation by copying a file back
produced **identical size within the same second**, so Python reused the stale `.pyc` and
the test kept failing after a correct restore. `find . -name __pycache__ -prune -exec rm -rf
{} +` before re-running.

**For Track 2 brand-manager sessions:** the decoy in `brand_manager_sessions.md` is marked
"optional but powerful" — on this evidence it is **not optional**, and it must be judged on
the right axis. Not "did they like it" (a fluent report reads the same whether right or
wrong), but **"can they tell the two diagnoses apart?"** Sharpest form: hand them their real
report plus one from a different ad, unlabeled, and see if they can pick theirs and say why.
That puts a human judge on the discrimination question instead of us.

**Still open:** the SCALE-candidate anchor (§3 of the σ study) and the consumer pain-overlap
check. Neither is touched by this.
