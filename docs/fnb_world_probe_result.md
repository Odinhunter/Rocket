# F&B world probe — RESULT

**2026-08-22. Ran against the pre-registration in `docs/fnb_world_probe_preregistration.md`, which was
committed BEFORE any money was spent (`#72`).** ⚠ **No threshold was moved after reading the output.**

**Actual cost `$0.38`** — I estimated `~$0.30` to the user; the gap is the cache WRITE on batch 1
(25,579 tokens at 1.25x), which I left out of the estimate. ⭐ The prefix cached exactly as designed:
batches 2 and 3 each read 25,579 cached tokens at 0.1x. **8 types, 0 refused, all five gates pass.**

## THE VERDICT: ALL FIVE CRITERIA PASS. ⚠ One passes at the threshold, not comfortably.

| # | criterion | threshold | result | |
|---|---|---|---|---|
| 1 | ⭐⭐ **do they DISAGREE?** | ≥5 of 8 | **8 of 8** | ✅ **decisive** |
| 2 | beverages reach the output | ≥3 of 8 | **5 of 8** | ✅ |
| 3 | ⚠ question-not-vignette survives generation | ≥2 of 8 non-desk | **2 of 8** | ⚠ **passes AT the threshold** |
| 4 | price step reasoning *(soft)* | ≥2 | **4 of 8** | ✅ |
| 5 | absence | any refusal is a pass signal | **0 refused** | neutral |

---

## ⭐⭐⭐ CRITERION 1 — EIGHT PEOPLE, EIGHT DIFFERENT REASONS TO SAY NO

Against one afternoon protein-bar ad, the eight types reject or accept **for eight distinct
reasons**. This is the standing directive (*diversity of OPINION is the deliverable*) met properly
for the first time — the 2026-08-19 probe was 8 loyalists with one opinion between them.

| stance | what it does with the ad | the reason, and it is unlike every other |
|---|---|---|
| loyalist | rejects | ⭐ **RITUAL.** *"Wants five minutes standing outside with the same two people. Rejects anything that turns the break into a purchase decision."* He refused a colleague's Yogabar last Tuesday |
| switcher | rejects | ⭐ **PRICE CEILING.** *"Wants cold, quick and under twenty rupees"* — a ₹100 bar is 5x his ceiling, and he does not know bars are sold singly |
| upgrader | ⭐ **ACCEPTS** | **THE TARGET.** Already orders boxes on Zepto after a blood report; *"wants something that stops the 6pm samosa without being a meal"* |
| aspirant | indifferent | ⭐ **IRRELEVANCE.** *"Wants the place, not the beverage"* — he is buying a chair and air-conditioning. A bar ad does not address him at all |
| skeptic | rejects | **DISILLUSIONMENT.** Ate two bars in a fitness phase, found the rest past date. *"Knows the word protein is now on chips, biscuits and water"* |
| purist | rejects | **A CATEGORICAL RULE.** *"Rejects anything with a shelf life longer than a week, however healthy the pack claims"* — a stomach infection turned preference into rule |
| pragmatist | rejects | ⭐ **SATIETY, not price or health.** *"Wants to not be hungry at six. Rejects small expensive packs that leave the stomach the same"* |
| gifter | rejects | ⭐⭐ **FORMAT.** *"Rejects single-serve health bars — one bar for one person makes it a private thing, not a round."* Nothing to do with the product |

⚠⚠ **FOUR OF THESE REJECT FOR REASONS THE INSTRUMENT HAS NEVER SEEN BEFORE** — ritual, satiety,
shareability and irrelevance. A panel that only produced price and health objections would have
told the client to change the price or the claim. This one says the gifter needs a **multipack**
and the pragmatist needs **filling**, which are product decisions, not creative ones.

## ⭐⭐ CRITERION 2 — THE BEVERAGE WORLD IS BEING REASONED WITH, NOT JUST LISTED

**5 of 8** name a drink among what they buy or reject: cutting chai ₹12-15, Sting/Charged/Red Bull,
Third Wave cold coffee, *"bhujia with the afternoon chai"*, *"chai made at home before leaving"*.

⭐⭐ **And for TWO of them the beverage IS the type.** The loyalist's entire existence is a ₹12
cutting chai at the same stall six days a week; the aspirant's is a ₹150-250 café seat. **Neither
person could have been written against either old pack** — there was no chai and no café in the
world. `#71` is doing work at generation time, not just passing a test.

## ⚠ CRITERION 3 — PASSES, BUT AT THE THRESHOLD. READ THIS ONE HONESTLY.

Pre-registered: **≥2 of 8 NOT desk/office workers**, because `desk_slump_4pm`'s one phrase cost
three of five real people their afternoon moment (`#68` finding 2).

- ✅ **switcher** — *"the three o'clock slump **on a shift**"*, *"the shop near the gate"*
- ✅ **pragmatist** — *"the shop by the gate"*, *"most working days"* — **gate** is site/factory language
- ✗ **upgrader** and **gifter** are explicitly at desks
- ~ loyalist, aspirant, skeptic, purist are **ambiguous** — none says "desk", but none rules it out

⭐ **So the fix reached the model, but weakly: 2 unambiguous, 4 silent, 2 desk-bound.** The
question no longer FORBIDS the building site — that is the win, and it is real. But it does not yet
actively populate one either. ⚠ **Do not quote this as "the vignette fix works."** Quote it as
*"the fix removed the exclusion; it did not by itself create the diversity."*

## CRITERION 4 — THE PRICE STEP CAME BACK ALMOST VERBATIM

The `behavioral_priors` line I wrote into the pack was *"a ₹104 bar competes with a ₹12 chai and a
₹15 vada pav — a 4-9x step for the same moment."* The **skeptic** returned:

> *"Rejects paying near a hundred rupees for a wrapped bar when the same money is a proper plate at
> the stall downstairs."*

⭐ Also the pragmatist (*"bought a ₹18 Dairy Milk, was hungry again by five, went back for a vada
pav"* — value per satiety), the switcher (*"under twenty rupees"*) and the upgrader (*"₹100-a-bar
range"*). **4 of 8.**

⚠⚠ **AND THE HONEST CAVEAT: this is the pack's own sentence coming back.** It is evidence the
priors REACH the reasoning — which is what `#71` needed to prove — and it is **not** independent
evidence the economics are right. The five real days are where that came from.

## CRITERION 5 — NO REFUSALS, BUT THE ABSENCE WRITING IS GOOD

0 of 8 cells refused. ⭐ The L3 lines write absence well and **differentiate it by class**:
*"Does NOT know Blinkit sells anything at this hour"* (loyalist) · *"Does NOT know Blinkit or Zepto
sell food at all"* (purist) · *"Does NOT know what 'whey' is"* (pragmatist) · *"Does NOT know what
any of it costs per gram"* (gifter). That is rule 6 working.

---

## ⚠ THE DEFECT THE RUN EXPOSED, WHICH WAS NOT PRE-REGISTERED

**Batch 1 returned ONE type of five and had to re-ask for four** (`⚠ short batch — 4 cell(s)
unanswered`). It self-healed on retry and cost nothing extra beyond output tokens, but it is the
known L4-retry issue in `known_issues_pipeline` showing up on the very first `fnb` run. ⚠ **Watch
the short-batch line on the full 168-cell region — at 21x the scale this is 21x the retries.**

## ⭐ WHAT THIS AUTHORISES, AND WHAT IT DOES NOT

✅ **Authorises PROPOSING the full 168-cell region.** The world produces people who argue, the
beverages are load-bearing, and the priors reach the reasoning.

⚠⚠ **DOES NOT authorise the spend itself** — that is the user's, and it was pre-registered that
way. ⚠ **And it says nothing about the other 20 moments.** This probe bought one moment. `afternoon_dip`
is the best-resourced cell in the pack (30 brands); `bedtime_cup` has 5. **A probe validates only
what it was designed to validate** — the lesson of 2026-08-19, and it applies to this probe too.
