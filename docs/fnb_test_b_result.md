# Part B result — people survive transplantation; their OPINIONS do not travel with them.

**2026-08-20, session 46. ~$0.25 paid** (Opus 5, 2 blind calls, 16 person×moment asks, well
inside the approved ~$1.00). Criterion and rig pre-registered and committed as `#63`
(`docs/fnb_test_b_preregistration.md`, `scripts/test_shared_people.py`) **before the run existed.**

**Artifact: `generated_audience_m2540_t1_testB_shared.json`. ⚠ NEVER OVERWRITE, and ⚠⚠ IT NEVER
INSTALLS** — no grid coverage, and the five gates do not apply to a person-reuse experiment.

---

## THE VERDICT, by the rules as committed

| | outcome |
|---|---|
| **PRIMARY — does one person hold together across moments?** | ⚠ **WEAK / INCONCLUSIVE.** 5 COHERENT · **1 CONTRADICTED** · 2 not evaluable. PASS needed ≥6 coherent and 0 contradicted |
| **THE INDEPENDENT KILL — invention** | ✅ **DOES NOT FIRE. 0 INVENTED of 9 written** (8 GENUINE, 1 STRAINED). Threshold was ≥4 |
| **SECONDARY — does the stance travel?** | ❌ **NO — only 1 of 6 people held one stance.** And the pre-registration says a mismatch is the *strong* direction |

⭐⭐ **The two failures are the SAME failure, and it names a cheap fix rather than killing the
design** — see *what this actually found*, below.

---

## ⭐⭐ WHAT ACTUALLY HAPPENED: THE PERSON SURVIVES, THE HISTORY DOES NOT

The rig shared **only the biography** — age, income, city, work, household — and wrote each
moment **blind to every other moment**. Under that constraint:

- ⭐ **The people came back as themselves.** A ₹3.1L press operator with no delivery app, a
  delivery rider who refuses to pay delivery charges, a welder whose only pharmacy money is his
  father's monthly strip. **Nothing was invented against a given fact, once.**
- ❌ **But their purchase history did not travel**, and it broke exactly where you would predict:
  **P3 reorders boxes of The Whole Truth at ~₹100 a bar in his native anchor, and the transplant
  says he "does NOT know what The Whole Truth costs or where it is sold."**

⚠ **The Whole Truth is in the pack, present in BOTH calls** — so the model was not missing the
brand. It was missing **this man's history with it**, which lives in the anchor the rig withheld.

⭐⭐ **AND THE STANCE RESULT SAYS THE SAME THING FROM THE OTHER SIDE.** Asked to derive each
person's stance from their biography, the model landed on the native stance **once in six**:

| person | native (4pm) | regimen | 11pm |
|---|---|---|---|
| P1 press operator | loyalist | *declined* | **pragmatist** |
| P2 QA tester | switcher | **skeptic** | switcher ✓ |
| P3 procurement | upgrader | **pragmatist** | **pragmatist** |
| P5 welder | skeptic | **purist** | *declined* |
| P7 delivery rider | pragmatist | *declined* | pragmatist ✅ |
| P8 hotel front desk | gifter | **aspirant** | **pragmatist** |

⭐⭐ **BOTH RESULTS CONVERGE ON ONE SENTENCE: THE BIOGRAPHY IS NOT ENOUGH. A shared population
store keyed on demographics alone cannot carry a person across moments — the ANCHOR has to travel
with them.** That is a **cheap fix, not a dead design**: the store holds people *and their written
history*, and each new moment is written with both in hand.

⚠⚠ **AND NOTE WHAT THIS DOES NOT LICENSE.** The blind rig was the hard TEST, not a constraint on
the product. Production may legitimately hand the model a person's prior anchors — that is not
cheating, it is the design. **What the blind rig proves is the floor: with biography alone it is
5-of-6 with one hard clash. With anchors carried, it can only get better, and the next test should
measure exactly that.**

---

## ⚠ The stance reading has a fair alternative, and it changes what to conclude

**Two readings of 1-in-6, and they are not the same:**

1. **Stance genuinely varies by moment** — a man is a loyalist about his 4pm bar and a pragmatist
   at 11pm. ⚠ If true it contradicts the grid's own comment (*"what changes per occasion is what
   they are skeptical OF, not that they are a skeptic"*) and the ring test's *a stance is a
   property of the person alone.*
2. ⭐ **The stance was never recoverable from a biography in the first place** — it lives in the
   anchor, which the rig withheld. So the model picked plausibly and arbitrarily.

⭐ **Reading 2 is the more parsimonious**, and it is the same finding as the P3 contradiction:
**the biography does not carry the opinion.** ⚠ **So do NOT record this as "stance varies by
moment" and do NOT reopen the ring test's conclusion on it.** The honest statement is: **a stance
cannot be reconstructed from demographics** — which is a fact about the store's schema, not about
stances.

---

## Every classification, quoted

### Per anchor — 9 written, 0 INVENTED

| person · moment | class | why |
|---|---|---|
| P1 · 11pm | **GENUINE** | *"Does NOT have any delivery app installed"* · *"Dipped Parle-G into tea standing by the door… rather than open the son's Milk Bikis"* — respects ₹3.1L, one room, the four-year-old, the second shift |
| P2 · regimen | **GENUINE** | *"a Calcirol sachet in milk on Sundays… nothing else daily, no subscription"* · *"has never opened HealthKart"* — a doctor's slip, not a wellness habit |
| P2 · 11pm | **GENUINE** | *"Two or three nights a week on Zepto, ₹100-₹200 basket"* — plausible for a single man on ₹7.5L splitting delivery with flatmates |
| P3 · regimen | **GENUINE** | *"One Uprise-D3 sachet weekly plus a multivitamin"* · *"Rejects wellness brands with pastel pouches"* |
| P3 · 11pm | ⚠ **STRAINED** | *"His father's sugar reading changed what stays in the fridge"* — the given household is wife + son in nursery. A father elsewhere is not impossible, so nothing given is *broken*; but it **adds a relative as the motive** when the man's own health check was already established |
| P5 · regimen | **GENUINE** | ⭐ the best line in the run: *"the only pharmacy money that leaves the house is his father's strip"* · *"walked past the counter's vitamin display"* — **he occupies the moment by NOT buying**, which the rig allowed and the model took |
| P7 · 11pm | **GENUINE** | ⭐ *"Rejects paying delivery charges on food when he is the one who delivers it"* — the rejection is derived from his job |
| P8 · regimen | **GENUINE** | *"a small daily thing that feels like looking after himself while his wife is away"* — uses the given household fact |
| P8 · 11pm | **GENUINE** | *"leftover mithai from the hotel's festival boxes"* — uses the given job |

### Per person — 5 COHERENT, 1 CONTRADICTED, 2 not evaluable

- ✅ **P1, P5, P7, P8 COHERENT.** Same economic reality and same register across moments — P1's
  ₹20/₹17 coins and refusal to spend on himself; P7's cheap-and-now logic in both; P8's
  buys-for-others at 4pm and buys-for-himself at 11pm, which is a **who-for** difference, not a
  drift (exactly the axis `#56` identified).
- ✅ **P2 COHERENT**, with a caveat: the protein-mislabelling scepticism recurs across his
  moments, **but that story is in the PACK and was in both calls** — ⚠ **world-driven continuity,
  not person-driven. Do not score it as coherence.** He is coherent on other grounds: ₹20-₹80 at
  4pm, ₹100-₹200 at 11pm, no subscription anywhere.
- ❌ **P3 CONTRADICTED.** Native: *"Reordered the box of eight Whole Truth bars"*, *"around ₹100 a
  bar and he has stopped flinching at it"*. Transplant: *"Does NOT know what The Whole Truth costs
  or where it is sold."* **A repeat customer written as unaware of the brand.**
- ⚪ **P4 and P6 NOT EVALUABLE** — declined at both transplant moments, so they have one moment
  each and coherence across moments cannot be read. **This is not a failure; it is the decline
  mechanism working.**

⚠ **P5's roasted chana appears in both his moments and is NOT in the pack** — so it is
person-driven. ⭐ But both anchors were written by the same model from the same biography, so call
it **convergent from the biography**, not carried across. It is suggestive, not evidence.

---

## ⚠⚠ A DEFECT IN MY OWN PRE-REGISTRATION, REPORTED NOT PAPERED OVER

**The primary threshold was "≥6 of 8 COHERENT", written assuming all 8 people would receive
transplants.** The decline mechanism — which the design *wanted*, and which fired 7 times — left
**2 people unevaluable**, making ≥6-of-8 unreachable in principle.

⭐ **Applied as written, that makes the bar STRICTER, not looser:** with 6 evaluable people, PASS
required **all six** coherent. Five were. **So the verdict stands as WEAK either way**, and the
rule is being applied as committed rather than rewritten after the fact.

⚠ **The generalisable fix, for the next pre-registration:** when a criterion counts people and the
rig can *remove* people, **state the denominator rule before the run** — evaluable-only, or a
minimum evaluable count. Same family as *"can this sample exhibit the behaviour"*: a criterion has
to survive its own instrument.

---

## ⭐⭐ THE FINDING WITH THE MOST MONEY IN IT: A 22-MOMENT MAP IS NOT 22 MOMENTS FOR EVERYONE

**Occupancy tracked income almost perfectly, and the pre-registration predicted it 4 for 4.**

| occupied | people |
|---|---|
| **3 of 3** | P3 (₹22.0L) · P8 (₹13.5L) · P2 (₹7.5L) — ⭐ **the three highest incomes in the sample** |
| 2 of 3 | P1 (₹3.1L) · P5 (₹5.2L) · P7 (₹4.6L) |
| **1 of 3** | P4 (₹3.6L) · P6 (₹3.1L) |

⭐ The pre-registration named **P1, P4, P6, P7** as where `daily_health_routine` would fail if it
failed — **all four were declined, and no one else was.** The declines name the missing channel,
price or time rather than a generality:

> P4: *"On lift sites daily and unmarried; his 'routine' is eggs and the canteen — no
> prescription, no HealthKart account, no ₹600 bottle enters his month."*
> P6: *"lights out early in two rooms shared with mother-in-law and a four-year-old; late-night
> sweet buying does not exist at ₹3.1L with no app on the phone."*

⭐⭐ **So moment occupancy is a function of income, and the map's cost is not 22 × 8 for every
region.** For a low-income region most moments are empty, and **empty is the correct answer**, not
a coverage gap to fill. ⚠ **That cuts BOTH ways on the refactor's budget** — fewer real cells than
22 × 8 = 176 suggests, but also **a thin panel for exactly the buyers a mass-market F&B brand most
needs to hear from**. Put it to decision 4 (*22 moments or fewer*) as a real input.

## ⭐ AND THE DECLINE OPTION WORKS — WHICH `#62` SAID IT WOULD NOT

The metro run produced **0 refusals across 16 types**; this run **declined 7 of 16**. The
difference is not the model, it is the ask: here the decline had **its own schema field, a reason
field, and a system prompt saying a decline is the right answer more often than it feels.**
⭐ **Generalises: "the model always fills the cell" is a property of how the cell was asked for,
not of the model.** ⚠ Worth carrying into the generator, where refusals are rare and grid
coverage is treated as a virtue.

---

## ⚠ Limits

- **n = 8 people, 9 written transplants, 6 evaluable.** ⚠ **One contradicted person is one person
  you can name — P3 — not "17% contradiction".** Same discipline as `#62`.
- One region, one gender, one tier, **three moments of eight**, one pack.
- **The rig is not the production prompt** — trimmed system prompt, same world.
- The people carry the **tier-1-label defect** from `#62`. Irrelevant to coherence, read within a
  person.

## What decision 5 gets

**Not a yes and not a no — a specification.** Shared people are viable, but **the store must hold
the anchors, not just the biography.** ⭐ The cheapest next step is the same rig re-run with each
person's prior anchors included, ~$0.25: if P3's contradiction disappears and stance stability
rises, shared-people is answered and costs one field on the store. ⚠ **If it does NOT — if a
person still fragments with their own history in hand — then person-per-cell stays, and that is
worth knowing before 176 cells are built.**
