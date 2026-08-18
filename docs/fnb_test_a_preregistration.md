# Part A — does adding beverages change the people? PRE-REGISTERED CRITERION

**Written 2026-08-19 BEFORE the run, and committed before the run, on purpose.**
The result does not exist yet. ⚠ If you are reading this after the result, the
criterion below is what it must be judged against — do not adjust it to fit.

---

## Why pre-register at all

Because **the obvious criterion is vacuous, and this repo has shipped that
shape before.** "Do beverages appear in the beverage arm?" cannot discriminate:
the grid's `competes_with` text names chai in **both** arms, so both prompts
already tell the model that the 4pm dip loses to chai.

⭐⭐ **AND THE CONTROL ARM HAS ALREADY PASSED THAT TEST ONCE, MEASURED.** The v2
region — generated against the **beverage-free** pack — contains:

> `skeptic_four_oclock_chai_enough` — *"Wants her tea and something with it;
> rejects paying a bar's price for one small piece and rejects the claim that a
> factory-made thing beats what she cooks."*

**Unbranded chai already shows up with zero beverages in the pack.** A criterion
that this line satisfies measures nothing. See memory `vacuous_test_shapes`.

---

## The two arms

Identical in every respect except the pack. Proven mechanically, not asserted:
`--dry-run` on both and diff the assembled prompts →
**13 added lines, all of them beverage brands or beverage prices**, and nothing
else changed.

| | arm A (control) | arm B (beverages) |
|---|---|---|
| pack | `health_nutrition_snacking` | `health_nutrition_snacking_bev` |
| brands | 45 | 52 (+7) |
| beverage price points | **0** | 6 |
| region | women 45-60, tier-3, no `--income` | same |
| occasion | `desk_slump_4pm`, all 8 stances | same |
| everything else | — | byte-identical |

---

## ⭐ THE CRITERION

**The claim under test:** a pack with no chai in it cannot represent the choice
a real Indian buyer makes at 4pm, so adding beverages should produce
*materially different people* — not merely people who mention beverages.

### PASSES if arm B shows all three, and arm A shows none or few

1. **A branded beverage is somebody's INCUMBENT.** Not mentioned — *held*. A
   named packet or tin appears in `l5_behavior` ("one recent thing they
   actually DID, at product and channel level") as the thing she actually buys:
   the Red Label packet, the Horlicks tin, the Nescafé jar.
2. **A rupee trade-off is made ACROSS the beverage/snack line.** Someone weighs
   a tin against a bar, or a monthly packet against a daily wrapper — the
   arithmetic a person does when both are real options. ⚠ Arm A cannot do this
   at all: it has no beverage price to weigh.
3. **At least one of the eight opinions is ORGANISED around a beverage** rather
   than decorated with one — her 4pm is the tea, and the snack is the
   negotiable part, not the other way round.

### FAILS if

- Arm B name-drops the new brands but the buying logic is unchanged — the same
  eight people, with "chai" swapped in for "biscuit" as scenery.
- Both arms are the same modulo proper nouns.

⚠ **A FAIL IS A REAL AND USEFUL OUTCOME.** The design doc says so itself: *"if
the beverage version does not produce visibly more real buyers, the central
claim of the whole refactor is wrong and it should stop there."* This is the
kill-switch. It is allowed to fire.

### ⚠ Explicitly NOT the criterion

- **Count of beverage mentions.** Both arms mention chai; a count rewards
  scenery.
- **Whether the people feel "better".** Unfalsifiable, and every previous fix
  here has felt better while costing something measured elsewhere.
- **Anything about the other seven moments.** One moment was generated. The 4pm
  dip is the moment where the design doc's own claim is strongest (*"chai wins
  the 4pm dip in India more often than any biscuit"*), which makes it the
  fairest place to test it and ⚠ **also the most favourable — a pass here does
  not generalise to `travel_and_commute` or `late_night_craving`.**

### ⚠ What this cannot establish either way

Sample is **8 types per arm, one moment, one region, one pack pair.** It cannot
speak to persona quality at scale, to the tail, to sizing, or to whether the
22-moment map is the right map. It answers one question: **does the pack's
beverage hole change who shows up.**

---

## Judged by

Reading all 16 `l1_context`/`l4_stance`/`l5_behavior` lines by hand, arm against
arm, stance by stance. ⚠ **Not by keyword count** — the stance-vs-modifier test
established in this same session that a regex conflates *mentioning* a thing
with *doing* it, and scored an unrelated stance as high as the real one.
