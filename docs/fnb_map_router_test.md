# Router test — can the F&B demand map assign a real event to exactly one space?

**2026-08-19. $0, by hand, ~40 minutes. Re-runnable by anyone.**

The map is at
**https://claude.ai/code/artifact/e6332193-5226-40ac-916f-89ccb9f6cbc8** — 22 demand spaces
in three bands (clock / event / standing habit), each carrying a discriminating question, plus
a four-step tie-break order.

⚠ **THE TEST IS DESIGNED TO FAIL, NOT TO PASS.** Twenty events were written to stress the
seams I already suspected — evening tea vs after-school feed, regimen vs meal, celebration vs
channel — rather than to confirm the map. A router test made of easy events measures nothing
(see memory `vacuous_test_shapes`). Every event below is an ordinary thing an Indian household
actually does; the difficulty is in which ones sit on a boundary.

**Procedure.** For each event: apply every space's discriminating question. If exactly one
passes, that is the route. If two or more pass, apply the tie-break order (event beats clock;
clock beats habit; deciding-for beats setting; buying beats eating). Record anything still
unresolved.

---

## Result

| | count | |
|---|---|---|
| routed cleanly on the questions alone | **14** | |
| resolved once a procedure bug was fixed | **2** | see *Two procedure bugs* below |
| genuinely ambiguous — the map cannot resolve them | **2** | ⚠ real findings |
| marginal — resolvable but the boundary is fuzzy | **2** | worth watching, not fixing yet |

**16 of 20 clean, 2 fuzzy, 2 genuine failures.** The map holds. ⚠ **And both genuine failures
point at the same structural defect — the one this map was built to fix, reproduced inside it.**

---

## The twenty events

✓ clean · ⚙ procedure bug · ⚠ genuine failure · ~ marginal

| # | Event | Routes to | |
|---|---|---|---|
| 1 | A man in Pune, 6:45am, two cups of tea before he touches food | First cup | ✓ |
| 2 | A woman in Gurgaon eats a banana at her desk at 9:40am, having skipped breakfast | Breakfast in motion **or** Mid-morning break | ⚠ |
| 3 | A woman in Bhilwara gives her grandson two Parle-G and milk at 4:15pm as he gets in from school | After-school feed | ✓ |
| 4 | The same woman drinks her own tea at 4:15pm while he eats | Evening tea (early) **or** Afternoon dip | ~ |
| 5 | A student in Indore buys a vada pav from a cart outside college at 6:30pm | Evening, out of home | ✓ |
| 6 | A man takes his statin and vitamin D with breakfast every morning | Daily regimen **or** Breakfast sat down | ⚙ |
| 7 | A woman in Chennai drinks buttermilk at 2pm because it is hot | Hydration | ✓ |
| 8 | A traveller buys a Snickers at the airport at 11am before a flight | Journey *(event beats clock)* | ✓ |
| 9 | A family orders biryani on Swiggy on Friday night to celebrate a promotion | Celebration **or** Dinner brought in | ⚠ |
| 10 | A woman puts two packets of Good Day on the monthly kirana list | Stock-up *(buying beats eating)* | ✓ |
| 11 | A 26-year-old drinks a whey shake twenty minutes after the gym | Fitness session *(clock beats habit)* | ✓ |
| 12 | A man recovering from dengue is given ORS and khichdi by his wife | Recovery & care | ✓ |
| 13 | A woman eats leftover mithai from the fridge at 11:20pm during a serial | Late-night | ✓ |
| 14 | A mother gives her 8-year-old Bournvita in milk at 9:30pm before bed | Bedtime cup | ⚙ |
| 15 | Office colleagues send out for chai and samosas at 4pm | Afternoon dip | ✓ |
| 16 | A man buys a Diwali dry-fruit box for his boss | Festival & gifting | ✓ |
| 17 | A woman drinks haldi doodh at 10:45pm because her throat hurts | Bedtime cup **or** Recovery & care | ~ |
| 18 | A 19-year-old makes Maggi at 1am while studying for exams | Late-night | ✓ |
| 19 | A woman packs theplas for a six-hour bus ride to her daughter's town | Journey | ✓ |
| 20 | A man drinks a Coke with his lunch at a food court | Midday meal | ✓ |

⭐ **#20 is worth noting even though it routed cleanly:** a beverage inside a food moment routes
to the food moment. That is correct, and it confirms the subscription model — **Coca-Cola must
subscribe to Midday meal**, a space no beverage would ever have been filed under in a
category-shaped map. It is the beverage/snacking overlap resolving itself.

---

## Two procedure bugs — cheap fixes, not map problems

**⚙ #6 — the routing unit was never defined.** A statin taken with breakfast passes *both* the
regimen question and the breakfast question, because I was routing **the sitting** rather than
**the item**. Route the item and it is clean: the statin is a regimen, the poha is breakfast,
and they merely co-occur.
⭐ **Fix: the unit of routing is one ITEM consumed, not one eating episode.** One sitting can
contain items from two spaces, and that is normal rather than a contradiction.

**⚙ #14 — the tie-breaks were being applied too eagerly.** Bournvita at 9:30pm for a child:
"deciding-for beats setting" fires and sends it to After-school feed, which is plainly wrong at
half past nine. But the *questions* resolve it correctly on their own — After-school feed asks
"on getting home from school", and 9:30pm is not that.
⭐ **Fix: tie-breaks apply ONLY when two discriminating questions both genuinely pass.** They
are a last resort, not a first pass. The original write-up did not say so.

---

## ⚠ The two genuine failures, and they are the same failure

**#2 — breakfast in motion vs mid-morning break.** A banana at a desk at 9:40am after a skipped
breakfast passes both questions and no tie-break separates them: no event, both clock-driven,
nobody being decided for, nothing being bought. The seam is real. Options: bound the two by
clock time (before/after 10am), or define breakfast-in-motion by *intent* (it replaces a meal),
or merge them. Not resolved here.

**#9 — celebration vs dinner brought in.** A family ordering biryani to mark a promotion is
genuinely doing two things: the *trigger* is a celebration, the *channel* is a delivery dinner.
Forcing one loses the other, and a Swiggy ad and a Cadbury ad would each care about the half
that got dropped.

⭐⭐ **BOTH FAILURES ARE THE DEFECT THIS MAP WAS BUILT TO FIX, REPRODUCED INSIDE IT.** The
critique of the current grid was that `guilt_free_treat` is a **job** and not a moment, so it
overlaps every other row by construction. **Celebration is exactly the same kind of object** —
a reason that can attach to almost any moment. So is **Recovery & care** (a state, not a time),
and arguably **Hosting**. I criticised the mixing and then mixed, less.

### The structural question this raises

Splitting the 22 into two kinds of thing would resolve both failures:

- **Moments** — *where and when*: the thirteen clock spaces, plus journey, fitness session,
  hydration, daily regimen, stock-up.
- **Modifiers** — *why and who for*: celebrating · caring for someone unwell · hosting ·
  gifting · fasting or dieting.

An event is then **one moment, optionally carrying modifiers.** The biryani becomes *dinner
brought in + celebrating*. The khichdi becomes *dinner at home + caring*. Both halves survive.

⚠ **This is a real improvement and it also adds a concept**, which is exactly the complexity
the user is right to push back on. **Not decided here — it is the first thing to settle before
any generation.** The cheap way to settle it: the modifier set is small (about five), and it
maps onto something the panel already has — a modifier is much closer to a *stance* than to a
moment, so it may cost nothing structurally at all.

---

## What this test did NOT establish

- **Nothing about persona quality.** It tests whether the map can classify, not whether it
  produces better people. That is the ~$1.30 paid test: one moment generated with and without
  beverages, then three moments sharing one person.
- **Nothing about coverage of the tail.** Twenty events is a probe, not a census; all twenty
  were written by the same person who wrote the map, which is the obvious bias. ⭐ **A second
  pass should use events somebody else supplies.**
- **Nothing about sizing.** How *big* each space is remains unsourced — see the Kantar note in
  the design doc, and the finding that the Indian daypart curve inverts between cities.
