# Part A result — the test misfired. It moved a lever that does not control the outcome.

**2026-08-19, session 45. ~$0.57 paid** (arm A $0.28 + arm B $0.29; Opus 5 at $5/$25 per
Mtok, two cache writes because two runs). Criterion pre-registered before the run in
`docs/fnb_test_a_preregistration.md` and committed as `#58`.

---

## ⚠⚠ THE VERDICT: INCONCLUSIVE — NOT A REFUTATION

Against the pre-registered criterion the beverage arm **fails all three checks.** But the
kill-switch did **not** fire. **Three explanations compete, and the third is the strongest:**

1. **The pack is the wrong lever** — incumbents come from the grid, not the pack (below).
2. **The design claim is weak** — the lines were in the prompt and went unused (below).
3. ⭐⭐ **THE TEST CELL WAS WRONG** — at this moment, for this population, tea is a **complement,
   not a competitor**, so no substitution exists to detect. **100% of tea mentions in both arms
   are companion-framed.** ⚠ **The user caught this; see below. It is the most parsimonious
   reading and it is directly visible in the output.**

⚠ **Do NOT record this as "beverages don't change the people."** That claim is not tested here.

---

## What the two arms produced

Both arms: 8 types, 0 refusals, `desk_slump_4pm`, women 45-60 tier-3.

| the criterion | arm B (beverages) |
|---|---|
| 1. a branded beverage is somebody's INCUMBENT | ❌ **zero.** Not one of Tata Tea, Red Label, Nescafé, Bru, Horlicks, Bournvita, Boost appears in **any field of any type** |
| 2. a rupee trade-off across the beverage/snack line | ❌ **zero.** None of the six added prices is used anywhere |
| 3. one opinion ORGANISED around a beverage | ⚠ the loyalist is (*"wants the afternoon tea and something to dip"*) — **but so is the control's loyalist** (*"wants tea to have something with it"*). No delta |

⭐⭐ **AND THE CONTROL ARM TALKS ABOUT TEA MORE THAN THE BEVERAGE ARM DOES.** Generic "tea":
**17 mentions in the control, 8 in the beverage arm.** Generic "chai": **1 in the control, 0 in
the beverage arm.** ⭐ **The only priced chai in the entire test is in the arm with no
beverages in its pack** — the control's pragmatist *"bought a Parle-G pack and a ₹10 chai at
the corner shop."*

---

## ⭐⭐ WHY — AND THIS IS THE FINDING WORTH THE $0.57

That ₹10 chai is not an accident, and it did not come from the pack. It came from the **grid**:

```
WHAT THEY ACTUALLY BUY MOST OF THE TIME — nameable, real, and usually
the thing that wins the occasion:
  - Cadbury Dairy Milk … Snickers … KitKat / Perk / Munch …
  - Britannia Good Day, Marie Gold, 50-50, Bourbon … Parle-G …
  - Haldiram's namkeen … Amul ice cream …
  - canteen samosa, vada pav, or chai — ₹10-₹25, hot and immediate
  - a banana or an apple … leftover mithai … nothing at all
```

That is `SNACKING_GRID["everyday_alternatives"]`, rendered by `_grid_brief` under a heading
that tells the model in the strongest available terms **what wins the occasion** — and it is
**byte-identical in both arms.** Fourteen entries, thirteen of them snacks, chai appearing as
one-third of one line with no brand and no packet price.

⭐ **Check the personas against it and the mapping is near-total.** Every incumbent in both
arms is either on that list or is home-made: Marie Gold ✓ · Good Day ✓ · Parle-G ✓ ·
Haldiram's bhujia ✓ · Snickers ✓ · Dark Fantasy ✓ · the ₹10 chai ✓ · roasted chana and
nankhatai (the "nothing at all" end). Only two — Bournville and RiteBite — come from the pack's
brand list at all.

### ⭐⭐ SO THE PACK SUPPLIES THE WORLD, AND THE GRID SUPPLIES WHAT WINS

| layer | what it does | did the test move it? |
|---|---|---|
| **pack** `brand_landscape` / `price_points` | the brands, prices and channels the opinions REASON INSIDE — reference material | ✅ **yes, +13 lines** |
| **grid** `everyday_alternatives` | *"usually the thing that wins the occasion"* — what people ACTUALLY BUY | ❌ **untouched** |
| **grid** `occasions[].competes_with` | what this moment loses to | ❌ **untouched** |

⚠⚠ **THE DESIGN DOC'S OWN TEST SPEC IS THEREFORE WRONG.** It says *"same region, same stances,
same prompt — only the pack moves, which is the attribution discipline this repo keeps
breaking."* The discipline was kept perfectly — proven mechanically, 13 lines, all beverages —
and it bought nothing, because **the pack is the wrong lever for this question.** The claim
*"chai wins the 4pm dip"* is a claim about `everyday_alternatives`, and that list already says
chai, in both arms, with no brand behind it.

⭐ **This is the SuperYou failure a third time, one level further in.** #48: the pack had no
confectionery, so the trade-up was unrepresentable. #58: the pack has no beverages. Now: **the
pack was never what decided it.**

---

## ⚠⚠ THE USER'S CATCH, 2026-08-19 — AND IT OUTRANKS BOTH READINGS ABOVE

**They asked: "whom did you test this with — it might just be that they don't drink as many
beverages."** ⭐⭐ **They are right, in a sharper way than the question puts it: this population
drinks enormous amounts of tea, but AT THIS MOMENT THE TEA IS NOT A CHOICE.**

⭐ **Measured, and it is unanimous: 100% of tea mentions in BOTH arms are companion-framed.**
Every one, without exception:

> *"wants tea to have something **with** it"* · *"knows which biscuit **softens in tea**"* ·
> *"the same tea **and** the same two biscuits"* · *"the afternoon tea **and something to dip**"* ·
> *"ate three **with** tea"* · *"the doctor said cut the sweet, **not the tea**"* ·
> *"kept in the steel dabba for the week's four o'clock tea"*

**Not one persona in sixteen treats tea as an alternative to the snack.** The tea is the fixed
ritual; the snack is the only variable. ⚠ **No substitution can be detected where none exists** —
so the criterion was looking for a behaviour this cell cannot produce.

### ⭐ Only two of the seven added brands were ever candidates here

| added | fit to women 45-60, tier-3, at 4pm |
|---|---|
| Tata Tea, Red Label | ⭐ **highly relevant** — ₹120-125 a 250g packet, bought monthly, completely ordinary. **But a complement at this moment, not a competitor** |
| Nescafé (₹230/50g), Bru | ❌ **wrong population.** Median household here is **₹3.0-3.2 lakh/yr**; the pragmatist's entire snack spend is ₹10-20 three or four times a week. A ₹230 coffee jar is weeks of it. Coffee also skews southern and metro |
| Horlicks (₹264), Bournvita, Boost | ❌ **wrong moment.** Malted milk is a bedtime, children's and convalescent drink — not a 4pm-dip item |

⭐ **THE MODEL WAS ARGUABLY RIGHT TO IGNORE FIVE OF THE SEVEN**, and to treat the other two as
the substrate rather than the choice.

### ⚠⚠ SO THE TEST CELL WAS WRONG, AND THAT IS THE LIKELIEST EXPLANATION OF ALL

`desk_slump_4pm × women 45-60 tier-3` is close to the **worst** cell in the grid for detecting
beverage-snack substitution, not the best. It was chosen because the design doc says *"chai wins
the 4pm dip in India more often than any biscuit"* — but ⚠ **that sentence describes a metro
office worker choosing chai INSTEAD of a snack. It does not describe a tier-3 homemaker who has
chai every day at 4pm regardless and decides only what goes with it.**

⚠ **AND THE PRE-REGISTRATION MISSED IT.** It listed limits about occasion-generality, sample
size and one-pack-pair — and never asked **whether this population could produce the behaviour
the criterion looks for.** ⭐ **Generalise: a pre-registered criterion is only as good as the
question "can the sample physically exhibit this?"** Same defect class as
`a_probe_is_not_an_audience` — validating something the sample was never able to show.

### ⭐ One real signal that WAS under-reported

The beverage arm's loyalist buys *"**the tea packet monthly at the kirana** and a small biscuit
pack every few days"*; the control's loyalist buys *"the ₹40 Marie Gold pack and a ₹10 Parle-G"*.
**One of eight types did shift its purchase pattern to carry a beverage staple** — unbranded, and
still a complement, but not nothing. ⚠ At n=8 it is one line, not a finding.

---

## ⚠ THE HONEST COUNTER-READING, WHICH THIS TEST CANNOT RULE OUT

The 13 beverage lines **were** in the prompt — verified in the dry-run diff before spending. The
model read *"Horlicks — the tin a woman is most likely to already own when a protein powder is
pitched to her"* and did not use it once. A fair reading of that is: **given the beverages, the
model judged them irrelevant to the 4pm dip, and the design claim is weak.**

⭐ **The two readings are separated by one asymmetry:** the pack list is reference material,
while `everyday_alternatives` is an explicit instruction about what wins, and it lists thirteen
snacks. The additions were arguing against a direct instruction. **That is the reason to call
this inconclusive rather than negative — but it is a reason, not a measurement.**

---

## What the corrected test is

⚠⚠ **CHANGE THE CELL FIRST — IT IS CHEAPER AND MORE DECISIVE THAN CHANGING THE LEVER.** Re-run
the same two arms at **`--occasion breakfast_on_the_run`**, same region, ~$0.57. ⭐ That moment's
`competes_with` **already names beverage-as-substitute in the grid text** — *"toast, poha,
cereal, a bought sandwich, **coffee alone**, skipping"* — so substitution is a behaviour the cell
can actually produce, and only ONE variable moves from this run. ⭐ A metro region at
`desk_slump_4pm` is the other candidate — it tests the design doc's claim about the person the
claim is actually about — but it moves the region instead, so run one or the other, not both.

**Then, only if that is also null,** move the beverages into the layer that decides:

1. add branded, priced beverages to `everyday_alternatives` — *"Tata Tea / Red Label — ₹120-₹125
   the 250g packet, made at home; the 4pm tea is the fixed point and the snack is what goes
   with it"*;
2. add them to `desk_slump_4pm.competes_with` as a **branded** option rather than the bare word
   "chai";
3. re-run both arms, ~$0.57.

⚠ **Keep the pack delta in place** so the arms differ in pack AND grid together. Attribution is
weaker, but the question being asked is now the right one, and a null result on the *combined*
change is a much stronger signal than a null on the pack alone.
⚠ **This is a GRID edit, which is what the refactor rebuilds** — so it is worth checking against
call 3 before spending. If the map replaces the grid anyway, run it on the new structure once.

---

## ⚠ What this run DOES establish, for free

- ⭐ **`--occasion` works.** 8 stances at one moment, 0 refusals, both arms. The flag and its
  `--fill` guard are proved on real output.
- ⭐ **The prompt-fix regression is NOT region-specific.** Unpaid share came back **24% (control)
  and 28% (beverages)** against a population figure of ~69% — the same shortfall the v3 probe
  showed at 27%. It reproduces at a second occasion under two different packs, so it is a live
  defect in the brief and not noise in one sample. ⚠ **It is identical in both arms, so it does
  not affect this comparison** — but it belongs on the judging list for the full region.
- ⭐ **Two clean artifacts** — `generated_audience_w4560_t3_testA_control.json` and
  `..._testA_bev.json`. ⚠ Never overwrite: they are the before-evidence for the corrected test.
