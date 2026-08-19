# Part A, corrected cell — does a beverage ever WIN the 4pm moment? PRE-REGISTERED CRITERION

**Written 2026-08-19 (session 46) BEFORE the run, and committed before the run, on purpose.**
The result does not exist yet. ⚠ If you are reading this after the result, the criterion below
is what it must be judged against — do not adjust it to fit.

**Supersedes nothing.** `docs/fnb_test_a_preregistration.md`, `docs/fnb_test_a_result.md` and
the two `_testA_*` artifacts stand exactly as they are. This is a second cell, not a re-run of
the first, and it does not re-test or overturn anything measured there.

---

## Why there is a second run at all

Part A moved the pack at `desk_slump_4pm × women 45-60 tier-3` and came back **inconclusive**.
The user's diagnosis is the one this run acts on: ⭐ **the test cell was wrong.** In that
population, at that moment, **100% of tea mentions in both arms are companion-framed** — *"tea
to have something with it"*, *"which biscuit softens in tea"*, *"cut the sweet, not the tea"*.
The tea is the fixed ritual and the snack is the only variable. **No substitution can be
detected where none exists.**

⭐ The moment's own text says so too, and this was missed the first time:

> `[desk_slump_4pm]` **the 4pm dip at a desk** — hungry, flagging, two hours from dinner
> where: **office pantry, vending machine**, the desk drawer stocked on Blinkit

**That is a desk-worker's moment**, and it was generated for a population of tier-3 women aged
45-60 of whom two-thirds hold no job at all. The design doc's claim — *"chai wins the 4pm dip in
India more often than any biscuit"* — is a claim about **a metro office worker choosing chai
INSTEAD of a snack**. This run puts the moment in front of that person.

---

## The one variable that moves: THE REGION

| | part A (already run) | this run |
|---|---|---|
| region | women, 45-60, tier-3 | ⭐ **men, 25-40, tier-1** |
| occasion | `desk_slump_4pm`, all 8 stances | same |
| arms | `health_nutrition_snacking` vs `..._bev` | **same pack pair, byte-unchanged** |
| income | none passed (`0-100`) | same |
| count | 8 per arm | same |

⚠ **The pack pair is deliberately NOT touched.** Five of its seven added brands were judged
wrong-population or wrong-moment for tier-3 women, and it is tempting to swap in the single-serve
beverages a metro 4pm actually sells — a ₹10 cutting chai, vending-machine coffee, a cold-coffee
tetrapak. **That is tuning the stimulus toward the result the test is supposed to find out**,
and it would move two axes at once. It stays as it is, for three reasons:

1. ⭐ **The primary criterion below does not depend on the pack at all**, so a pack whose format
   is wrong for the moment cannot sink this run.
2. ⭐ Holding it fixed makes this a **clean replication of part A's mechanism finding at a second
   cell**: if substitution shows up and arm B *still* does not use the pack's brands, *"the pack
   supplies the world, the grid supplies what wins"* is confirmed twice — which is directly what
   decision 3 needs to know about where beverages have to live.
3. Metro men 25-40 include a real work-from-home and hybrid slice for whom the Nescafé jar and
   the Tata Tea packet genuinely **are** the 4pm incumbents, so the added set is not idle here
   the way it was in a tier-3 kitchen.

**Verified mechanically before spending, exactly as part A was:** `--dry-run` on both arms and
diff → **15 differing lines — 13 added, every one a beverage brand or a beverage price, plus the
two header lines naming the pack.** Nothing else moves.

---

## ⭐⭐ CAN THIS SAMPLE PHYSICALLY EXHIBIT THE BEHAVIOUR THE CRITERION LOOKS FOR?

**This section exists because part A's pre-registration did not have one, and that is the single
reason it misfired.** It listed limits on occasion, sample size and pack-pair, and never asked
whether the people could do the thing being looked for. ⭐ **Every future pre-registration in
this repo asks this question first.** Same defect class as `a_probe_is_not_an_audience`.

**The answer here is yes, by three independent routes** — the criterion does not depend on any
one of them landing:

1. **Pantry / vending, either-or.** A desk worker who has stopped eating at 4 and takes a coffee
   instead is an ordinary, extremely common metro pattern. Mild guilt is already in the moment's
   `decided_by`.
2. **Canteen, either-or on price.** ⚠ This is the route that survives the demography. Of every
   100 employed urban men, **38 do manual and production work and only ~17 are at a desk**
   (13.2% professional/managerial + 4.0% clerical). So some of these eight types will be counter,
   site and route workers — and for a price-constrained buyer at a thela, **₹15 buys the chai or
   the vada pav, not both.** That is substitution in a different sub-population, ⭐ **not a
   misfire** — do not read it as one.
3. **The weight-conscious skip.** "Black coffee at 4, I've stopped the biscuits" is the cleanest
   form of the behaviour and needs no price constraint at all.

⚠ **What could still make it unanswerable:** if the model resolves the desk/manual tension by
refusing cells (see the void condition below), or if metro men turn out to frame tea the same
companion way tier-3 women do — which would itself be the finding, and is what the FAIL branch
records.

---

## ⭐ THE CRITERION

⚠⚠ **PART A'S CRITERION HAD A DEFECT AND THIS FIXES IT.** Its first check required a *branded*
beverage incumbent — which welded the **premise** (*beverages compete with snacks inside a
moment*) to the **lever** (*the pack is what supplies brands*). Those are two different claims
and part A could not tell them apart. They are separated here.

### PRIMARY — the premise. Brand-agnostic, judged on the CONTROL arm.

**The question:** does anyone treat a beverage as **what wins the moment** — the chai or the
coffee **is** the 4pm, and the snack is skipped or explicitly displaced?

**Counts:**
- the 4pm resolves to a beverage and no food — *"goes down for a cutting chai and that is it"*
- an explicit either-or — *"₹15 is the chai or the vada, not both"*
- an explicit displacement — *"black coffee now, stopped the biscuit"*
- ⭐ **unbranded counts.** A ₹10 cutting chai and a vending-machine coffee are beverages winning
  the moment whether or not a brand is on them.

**Does NOT count — companion framing, which is what part A found 16 times out of 16:**
- *"tea with a biscuit"* · *"which biscuit softens in tea"* · *"the tea and something to dip"* ·
  a beverage present as scenery while the snack is the decision.

**Pre-committed thresholds — control arm, 8 types, with the pooled 16 reported beside them:**

| outcome | rule |
|---|---|
| ✅ **PASS — premise supported** | **≥2 of the control's 8 types** have a beverage winning the moment |
| ⚠ **WEAK — inconclusive** | exactly **1 of 8** in the control, **or** 0 in the control and ≥1 in the beverage arm |
| ❌ **FAIL — premise not supported** | **0 of 16 pooled** |

⭐ **Two, not one.** Part A's own warning applies: *"at n=8 it is one line, not a finding."*

⚠ **A FAIL IS A REAL RESULT AND IT IS ALLOWED TO FIRE.** The 4pm dip at a desk is the moment
where the design doc's beverage claim is **strongest**, and metro men are the population it is
**about**. The premise failing here, after failing at tier-3, is genuine evidence against the
map's central claim — not a third reason to move the cell again.

### ⭐⭐ THE BUILT-IN NEGATIVE CONTROL — why this criterion is not vacuous

The obvious objection is that the grid **tells** the model chai competes at 4pm
(`competes_with: "...samosa/vada from the canteen, chai, a banana..."`) and prices it in
`everyday_alternatives` (*"canteen samosa, vada pav, or chai — ₹10-₹25"*), so a pass would just
be the prompt talking back.

⭐ **Part A already ruled that out, and this is the strongest property of this design.** That
grid text was **byte-identical** in both of part A's arms, and it produced **zero** substitution
framing across 16 types — 100% companion. **The instruction demonstrably does not manufacture the
behaviour.** So if metro men show it, the thing that changed is the population.

### SECONDARY — the lever. Part A's three checks, carried VERBATIM for comparability.

Judged arm B against arm A. **Passes** if arm B shows all three and arm A shows none or few:

1. **A branded beverage is somebody's INCUMBENT** — held, not mentioned: a named packet, jar or
   tin appears in `l5_behavior` as the thing he actually buys.
2. **A rupee trade-off is made ACROSS the beverage/snack line** — a tin weighed against a bar, a
   monthly packet against a daily wrapper. ⚠ Arm A cannot do this: it has no beverage price.
3. **At least one of the eight opinions is ORGANISED around a beverage** rather than decorated
   with one.

⭐ **The secondary is expected to fail again**, on part A's mechanism finding — incumbents come
from `everyday_alternatives`, which is untouched in both arms. **A second failure is worth
having**: it turns "the pack is not the lever" from a one-cell reading into a replicated one,
which is what decides where beverages go if the refactor lands.

### ⚠ Explicitly NOT the criterion

- **Counts of beverage mentions.** Part A's control mentioned tea 17 times and its beverage arm
  8, and the number meant nothing. Framing is the measurement, not frequency.
- **Whether the people feel "better" or more real.** Unfalsifiable, and every fix in this repo
  has felt better while costing something measured elsewhere.
- **Anything about the other seven moments**, or about tier-2/3, or about women.
- **Persona quality, the tail, or sizing.**

### ⚠ VOID CONDITION, pre-committed

If **≥3 of the 8 cells are refused** in an arm, that arm is under-powered and its primary reading
is reported as **inconclusive with the refusal reasons quoted**, not as a FAIL. A refusal is
information about the cell, not a data point about beverages.

---

## Judged by

Reading all `l1_context` / `l4_stance` / `l5_behavior` lines by hand, arm against arm, stance by
stance. ⚠ **Not by keyword count** — the stance-vs-modifier test established that a regex
conflates *mentioning* a thing with *doing* it, and scored an unrelated stance as high as the
real one. Every claimed instance gets quoted in the result doc so it can be argued with.

---

## The rig, exactly

```
# ~$0.57 total, 8 types per arm, 2 batches per arm  — NEEDS A MONEY GO
.venv/bin/python scripts/generate_audience.py --count 8 \
    --occasion desk_slump_4pm \
    --gender male --age 25-40 --tier tier-1 \
    --category health_nutrition_snacking \
    --out generated_audience_m2540_t1_testA_metro_control.json

.venv/bin/python scripts/generate_audience.py --count 8 \
    --occasion desk_slump_4pm \
    --gender male --age 25-40 --tier tier-1 \
    --category health_nutrition_snacking_bev \
    --out generated_audience_m2540_t1_testA_metro_bev.json
```

⚠ **No `--income`.** The band would be invented, and it would move a second axis. The pinned
occasion does the selecting: eight types written for the 4pm dip are the people in this region
**for whom that moment is live**, not a proportional sample of the region.
⚠ **`--category` is not optional** — it defaults to the supplements pack.
⚠ **Never overwrite** `generated_audience_w4560_t3_testA_control.json` or `..._testA_bev.json`.

## ⭐ Free from the same run, and NOT part of the criterion

- **This is the first paid MALE region.** The male half of `agent/demography.py` — the 54/25/21
  self-employed/salaried/casual split, the 38% manual class, the 26-in-100 with no spouse — gets
  proved on real output for the first time. Report it; do not judge the test on it.
- **The first paid tier-1 region**, and the first outside 45-60. Region-generality of the
  rewritten prompt gets a second data point.
- **The unpaid-share regression** (24-28% against a population figure of ~69% at tier-3) can be
  checked at a third occasion in a region where the male figure is different. ⚠ Identical in both
  arms, so it cannot affect the comparison either way.
