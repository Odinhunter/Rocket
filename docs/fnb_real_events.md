# Real consumption events — supplied by the USER, not written by the map's author

**Started 2026-08-20 (session 46). Event 1 of 5 recorded; four more are coming from the user's
friends.** This file exists to fix `docs/fnb_map_router_test.md`'s own stated flaw: **all twenty
events there were written by whoever wrote the map.**

⚠⚠ **WHAT THIS FIXES AND WHAT IT DOES NOT.** The EVENTS are now the user's — that half of the
bias is gone. **The ROUTING is still mine**, so the router's authorship flaw stands. ⭐ Which is
why every routing below is **recorded BEFORE the remaining four events arrive**, and dated, so the
map cannot be quietly tuned to fit the data and then declared to fit it.

⚠ **One caveat on event 1, stated by me and not by the user:** it is the user's own day, and they
know this map. They supplied **behaviour**, not routings, so the risk is small — but the four
friends' days are cleaner evidence and should carry more weight.

---

# EVENT 1 — the user's own day, a metro office worker with a protein goal

⭐ **Note who this is: exactly the population the design doc's beverage claim is about, and the
one `#62` generated 25 of.**

| # | when | item | as described |
|---|---|---|---|
| 1a | morning, home | **upma** | sat down, home food |
| 1b | morning, home, same sitting | **Provelac high-protein milk** | 25-30g protein, ultra-filtered, no fat, lactose-free. ⭐ *"I have become habitual because it helps me achieve my protein goal"* — a standing daily habit, recently started |
| 1c | ~11:00am, office | **a cup of black coffee** | ⭐ *"I don't have anything in between except a cup of black coffee"* — the only thing between breakfast and 1pm |
| 1d | 1:00-1:30pm, office canteen | **roti + subji + salad, or rice + rajma/chole** | eaten with the team |
| 1e | evening, office canteen | **samosas, chaat, pav bhaji** | an Independence Day spread **arranged by the office** |
| 1f | dinner, home | **roti + subji** | |
| 1g | dinner, home, same sitting | **a cup of Diet Coke** | *"and that is all for the day"* |

---

## ⭐ FIRST-PASS ROUTING — recorded 2026-08-20, before events 2-5 exist

**Both maps, side by side.** ✓ clean · ⚠ needs a modifier · ❌ no moment exists

| item | current 8-occasion grid | proposed 22-moment map |
|---|---|---|
| 1a upma | ❌ — `breakfast_on_the_run` is explicitly *"will not sit down to eat"*, and he did | **Breakfast sat down** ✓ |
| 1b Provelac | `daily_health_routine` ✓ | **Daily regimen** ✓ |
| 1c 11am black coffee | ❌ — **there is no mid-morning moment at all** | **Mid-morning break** ✓ |
| 1d canteen lunch | ❌ — the grid has no meal moments | **Midday meal** ✓ |
| 1e office festival spread | ❌ — `guilt_free_treat` is a reason, not this | **Evening / Afternoon dip + `Celebration` modifier** ⚠ |
| 1f dinner | ❌ — no meal moments | **Dinner at home** ✓ |
| 1g Diet Coke with dinner | ❌ — and the pack has no beverages | **Dinner at home** ✓ *(beverage inside a food moment routes to the food moment)* |

⚠⚠ **THE FAIR COMPARISON, BECAUSE THE HEADLINE NUMBER IS UNFAIR.** *"The grid routes 1 of 7"* is
true and misleading: the grid is a **snacking and nutrition** grid and never claimed to route
meals. **In-scope items are 1b, 1c, 1e and 1g** — and of those the grid routes **1 of 4** while
the map routes **4 of 4** (one carrying a modifier). ⭐ That is the honest measurement, and it is
still decisive.

---

## ⭐⭐ THE FOUR THINGS THIS ONE DAY ESTABLISHES

### 1. ⭐⭐ THE 11AM BLACK COFFEE IS THE SUBSTITUTION WE SPENT $1.14 HUNTING AT 4PM

*"I don't have anything in between except a cup of black coffee."* **A beverage occupying a
snacking gap, in a real metro office worker** — the exact person the design doc's claim is about.

⚠ **But it is at 11am, and we looked at 4pm. Twice.** Part A's pre-registration named this as
**route 3, "the weight-conscious skip"** — *"black coffee now, stopped the biscuit"* — and the
generated panel produced **ZERO** instances of it. Here it is in the first real day anyone looked
at. ⚠ **And the current grid has no mid-morning moment**, so this behaviour has nowhere to live
even if a persona wrote it.

⭐ **What it does NOT overturn:** `#62` found the substitution among **cash-constrained** workers
and none among desk workers. This is a desk worker substituting for a **goal**, not a price. ⭐ So
the finding widens rather than reverses: **at the snacking end substitution is driven by PRICE; at
the nutrition end it is driven by a GOAL.** ⚠ n=1, and this person is unusually goal-directed.

### 2. ⭐⭐ PROVELAC IS A BEVERAGE DOING THE JOB OF THE CLIENT'S OWN PRODUCT — AND NO PACK CAN NAME IT

A 25-30g-protein, ultra-filtered, lactose-free milk, drunk **every morning, for a protein goal.**
That is a **beverage competing directly with protein bars and powders** — inside the exact
category this instrument was built for.

| pack | beverages | high-protein dairy |
|---|---|---|
| `health_nutrition_snacking` (45 brands) | **0** | **0** |
| `health_wellness_nutrition` (20 brands) | **0** | **0** |

⭐⭐ **This is the SuperYou failure a FOURTH time, and the sharpest instance yet.** `#48`: the pack
had no confectionery. `#58`: no beverages. `#62`: the pack was not the lever. Now: **a real
buyer's actual protein incumbent is a product category neither pack can name at all.** ⚠ A panel
built from either pack cannot represent this man's morning, and he is squarely the target buyer.

### 3. ⭐ ONE SITTING, TWO MOMENTS — THE PROCEDURE FIX CONFIRMED ON A REAL EVENT

**1a and 1b are the same sitting** and route to two different moments — breakfast and a regimen.
⭐ That is exactly hypothetical event #6 (*"a man takes his statin and vitamin D with breakfast"*),
which forced the router test's procedure fix: **route the ITEM, not the sitting.** **First
real-world confirmation that the fix was needed and works.**

### 4. ⚠⚠ A FREE OFFICE SPREAD IS CONSUMPTION WITH NO PURCHASE DECISION AT ALL

Nobody bought 1e — the office arranged it. **The entire grid is built on *"what they actually
buy"***, and `everyday_alternatives` is headed *"WHAT THEY ACTUALLY BUY MOST OF THE TIME."*
⚠ **And it displaced a purchase**: it is the reason there is no bought evening snack in this day.

⭐ **Why it matters for an ad-reading instrument, not just for tidiness:** a panel cannot be asked
*"what would you buy here"* about a moment where nothing is bought — but the moment still consumes
the appetite that a competing product wanted. **Provided-and-free is a real competitor and it is
currently unrepresentable.** ⚠ It also carries the `Celebration` modifier the router test flagged
as *a reason, not a moment* — ⭐ **the first real instance of that modifier, and it arrived
attached to a moment exactly as the proposed split predicts.**

---

## ⚠ WHAT ONE DAY CANNOT DO

- **n = 1 person, 1 day, 7 items.** Nothing here is a rate.
- It cannot test the map's **tail**, its **sizing**, or the moments this day does not contain
  (After-school feed, Fitness session, Journey, Stock-up, Hosting, Recovery & care, Bedtime cup).
- ⚠ **It cannot settle decision 3 by itself** — but it is the first evidence about the map that
  did not come from the map's own author, and it points one way.

---

# EVENT 2 — the SAME user's IDEAL day. ⚠⚠ ASPIRATIONAL, NOT OBSERVED.

⚠⚠ **THIS IS NOT A CONSUMPTION EVENT AND MUST NOT BE POOLED WITH ONE.** It did not happen. It
cannot be routed as evidence that a moment *occurs*, only as evidence of what this person *wants*
a moment to contain. ⭐ **Counted separately: the tally of real observed days is still 1, and the
four friends' days are still owed.**

⭐⭐ **But it is worth more than a third real day, for a different question** — because it is the
**same person as event 1**, so actual and ideal can be diffed with everything else held constant.
That pair is rare and it is the thing an ad actually addresses.

⚠ **A hard constraint stated by the user and shaping every line: he is VEGETARIAN.**

| # | when | ideal item |
|---|---|---|
| 2a | morning | **a cup of milk + sunflower and pumpkin seeds** |
| 2b | office | **a cup of black coffee** |
| 2c | lunch | **a high-protein meal — paneer and roti, or a Lebanese wrap** |
| 2d | 4-5pm | **100g Greek yogurt + edamame beans**, *"along with, say, a cup of coffee"* |
| 2e | dinner | **a tempeh sandwich, or protein hara bhara kebab** |
| 2f | conditional | **a protein supplement — plant or whey — IF he has gone to the gym** |

---

## ⭐⭐ WHAT THE IDEAL DAY ESTABLISHES

### 1. ⭐⭐ SEVEN PROTEIN DECISIONS, AND NOT ONE PACKAGED PROTEIN SNACK

Every eating moment in this day is a protein decision — milk and seeds, paneer, Greek yogurt,
edamame, tempeh, kebab. **The most protein-motivated buyer imaginable, who has organised his
entire ideal day around the goal, wants a protein BAR at none of them.**

⭐ The single exception is **2f, the post-gym supplement** — and it is conditional. ⭐⭐ **So
packaged protein wins exactly ONE moment out of seven for this buyer, and it is the one moment
where whole food genuinely cannot compete on speed.** That moment is `post_workout`, which the
grid already has and where the pack's brands actually live.

⚠⚠ **THE CONSEQUENCE FOR THE PRODUCT, AND IT IS UNCOMFORTABLE:** this buyer's real competitors
are **paneer, Greek yogurt, edamame, tempeh and seeds** — mostly unbranded, several with no brand
at all. **Ring 4 ("same moment, anything") is the DOMINANT ring for the most engaged buyer**,
which inverts the usual assumption that engaged buyers shop inside the category. A pack of 45
brands describes a world he has opted out of.

### 2. ⭐⭐ THE SAME BEVERAGE PLAYS TWO ROLES IN ONE DAY, AND THE MOMENT DECIDES WHICH

- **2b, the office coffee** — the same 11am black coffee as event 1c, where it **REPLACES** food.
  ⭐ It survives into the ideal day unchanged, so it is a **chosen habit, not a compromise.**
- **2d, the 4-5pm coffee** — *"along with"* Greek yogurt and edamame. **A COMPANION.**

⭐⭐ **One person, one drink, one day: substitute at 11am, companion at 4pm.** Put beside the rest
of the evidence — tier-3 women 100% companion at 4pm (`#60`), metro men companion at 4pm (`#62`) —
**the pattern is that the MOMENT determines the role, not the product and not the person.**
⭐ That is a direct argument for a moment-based map over a category-based one, and it is the
cleanest instance of it we have.

### 3. ⭐⭐ THE ACTUAL-VS-IDEAL GAP IS WIDEST EXACTLY WHERE SOMEONE ELSE PROVIDES THE FOOD

| moment | actual (event 1) | ideal (event 2) | who controls it |
|---|---|---|---|
| morning | upma + **Provelac** (packaged) | milk + seeds (whole food) | him — ⚠ **and the ideal is LESS packaged than the actual** |
| 11am | black coffee | black coffee | him — **no gap at all** |
| lunch | canteen roti/subji/rajma | paneer, Lebanese wrap | ❌ **the office canteen** — widest gap |
| 4-5pm | office samosas, chaat, pav bhaji (free) | Greek yogurt + edamame | ❌ **the office** — widest gap |
| dinner | roti + subji + Diet Coke | tempeh sandwich, kebab | him — moderate gap |

⭐⭐ **THE MOMENTS AN AD CAN MOVE ARE THE MOMENTS THE PERSON CONTROLS.** The canteen lunch is not
winnable by a brand at any creative quality; the morning and the 4pm are. ⚠ **Nothing in the
instrument currently distinguishes a self-provisioned moment from a provided one** — and event 1e
already showed provided-and-free displacing a purchase.

⭐ **And note the direction of 2a:** the packaged product he actually uses (Provelac) is the
**compromise**, and the whole food is the aspiration. ⚠ A persona generator that treats packaged
nutrition as the aspirational choice has this backwards for this buyer.

### 4. ⚠⚠ "I AM A VEGETARIAN" IS LOAD-BEARING AND NO AXIS CARRIES IT

**Verified in code:** the eight vector axes are `brand_stance`, `category_involvement`,
`category_relationship`, `channel_behavior`, `decision_driver`, `life_stage`, `price_orientation`,
`prior_experience_valence` — **none is diet.** The person fields are gender, age, income,
geography, `occupation_hint`, `household_hint` — **none is diet.**

⚠ In an Indian food market, vegetarian/non-vegetarian determines more of what a person will eat
than income does. It can appear in anchor prose by accident, but it **cannot be selected on,
counted, or guaranteed** — ⭐ **the same defect class as the incumbent-is-prose gap from the ring
test.** Every protein source in this ideal day is vegetarian, and that is not a coincidence; it is
the constraint doing the work.

### 5. ⭐ "EVENT BEATS CLOCK" CONFIRMED AGAIN — 2f is conditional on the gym, not on a time

*"I would have a protein supplement if I have gone to the gym."* Not a clock moment; a
**triggered** one. ⭐ The router test's tie-break (*event beats clock*) handles it, and this is the
second real-world confirmation of a procedure rule after event 1's one-sitting-two-moments.

---

# EVENTS 3-6 — awaited from the user (four friends' days)

⚠ **Record them here verbatim-first, route them second, and do not revise any routing above.**
⭐ **Still owed: four OBSERVED days.** Event 2 is aspirational and does not substitute for one.

---
---

# ⭐⭐ EVENTS 3-7 — FIVE REAL DAYS FROM FIVE PEOPLE WHO ARE NOT THE USER

**Collected by the user on the sheet at `docs/fnb_field_collection.md`, delivered 2026-08-21
(session 47).** ⚠ **Transcribed verbatim BELOW BEFORE ANY ROUTING WAS WRITTEN**, the same
discipline events 1-2 were held to. The map used is the published one
(https://claude.ai/code/artifact/e6332193-5226-40ac-916f-89ccb9f6cbc8), **fetched and re-read in
full before routing** — 22 spaces, each with its discriminating question, plus the four-step
tie-break (event beats clock · clock beats habit · deciding-for beats setting · buying beats
eating). ⚠ Nothing in the map was edited during routing. Every proposed edit is recorded as a
FINDING at the foot, for the user's decision.

## ⚠⚠ COLLECTION CAVEATS — STATED BY ME, BEFORE THE DATA IS USED

| caveat | why it matters |
|---|---|
| ⚠⚠ **"Nearly had instead?" is filled on 19 of 22 rows** although the sheet marked it **volunteer-only** | It was almost certainly **prompted**. So the substitution data is **softer evidence than the consumption data**. ⭐ The tell is P5 row 4, where the answer is *"average indian meal"* — not an alternative at all, which is what a pushed column looks like |
| ⚠ **P5 is 45**, the brief said 50+ | Kept. He takes medicines twice daily, so a condition exists |
| ⚠ **P5's row 2 says "12AM"** | Read as **noon** — it sits between an 8AM and a 5PM row and he is at the factory. His words are kept in the verbatim block |
| ⚠⚠ **P3 came back protein-leaning** — protein cereal, protein chips, and protein bars named as near-misses twice | **The unlike-the-user goal is only PARTIALLY met.** P3 is a second protein-optimiser. ⭐ **P2 and P4 carry the diversity load**, exactly as the sheet predicted they would have to |
| ⚠⚠ **SIX of the sheet's free-text boxes came back blank** | Listed at the foot under WHAT IS STILL OWED. Two of them (P5's doctor fields) are the reason P5 cannot yet do the restriction-vs-preference job he was recruited for |
| ⚠ **Nobody was asked whether they drank anything before their first recorded row** | So **moment 01 `First cup` is UNVERIFIABLE for all five**, not empty. See finding 8 |

---

## THE FIVE DAYS, VERBATIM

### EVENT 3 — a woman who runs a household
**46 · Mumbai · cooking, cleaning, helping the kids study, "regular household stuff" · husband,
2 kids (M15, F18), husband's mother · vegetarian · yesterday was normal**

| # | when | item | where | bought / made / given | with | nearly had |
|---|---|---|---|---|---|---|
| 3a | 9AM | **poha** | home | made by her | with family | upma |
| 3b | 9AM | **fruit** | home | made by her | with family | upma |
| 3c | 9AM | **chai** | home | made by her | with family | upma |
| 3d | 12:30PM | **2 rotis with sabji** | home | made by her | **by herself** | rice and rajma |
| 3e | 12:30PM | **dahi** | home | made by her | **by herself** | rice and rajma |
| 3f | 3PM | **chai** | home | made by her | **by herself** | *"nothing instead"* |
| 3g | 3PM | **biscuit** | home | bought from supermarket | **by herself** | *"nothing instead"* |
| 3h | 3PM | **khaari** | home | bought from supermarket | **by herself** | *"nothing instead"* |
| 3i | 5PM | **bread with jam** | home | bought from quick commerce — blinkit, zepto | **by herself** | sandwich |
| 3j | 5PM | **maggi** | home | bought from quick commerce | **by herself** | sandwich |
| 3k | 6PM | **bread, paneer, pasta, vegetables and fruits** | *"bought from nearby grocery store"* | bought from supermarket | **by herself** | tacos and pizza bases |
| 3l | 8PM | **roti sabji** | home | made by herself | with family | pav bhaji |

⚠ **3k is a SHOPPING TRIP, not a consumption event.** Recorded as one item under tie-break 4.

### EVENT 4 — a construction worker
**32 · Delhi · day shift 9AM-7PM at a construction site · his mother, wife and kids live in the
village · non-vegetarian · yesterday was normal**

| # | when | item | where | bought / made / given | with | nearly had |
|---|---|---|---|---|---|---|
| 4a | 8AM | **chai** | nearby snack shop | bought | fellow labourers | samosa, chicken patty |
| 4b | 8AM | **biscuits** | nearby snack shop | bought | fellow labourers | samosa, chicken patty |
| 4c | 8AM | **aloo patty** | nearby snack shop | bought | fellow labourers | samosa, chicken patty |
| 4d | 2PM | **roti sabji meal** | construction site | ⭐ **given — provided by boss** | other labourers | *"nothing else"* |
| 4e | 2PM | **Frooti** | construction site | ⭐ **given — provided by boss** | other labourers | *"nothing else"* |
| 4f | 5PM | **chai** | nearby snack shop | bought | fellow labourers | packet of chips / kurkure |
| 4g | 5PM | **biscuits** | nearby snack shop | bought | fellow labourers | packet of chips / kurkure |
| 4h | 8PM | **rice with dal** | bhojanalay | bought | **alone** | *"nothing else"* |
| 4i | 8PM | **Sprite** | bhojanalay | bought | **alone** | *"nothing else"* |

⚠⚠ **8AM → 2PM is SIX HOURS with nothing at all.**

### EVENT 5 — a student
**19F · Bangalore · studying · Mom, Dad, brother · vegetarian · yesterday was normal**

| # | when | item | where | bought / made / given | with | nearly had |
|---|---|---|---|---|---|---|
| 5a | 9AM | **a fruit** | home | bought | brother and mom | protein bar, smoothie bowl |
| 5b | 9AM | **protein cereal** | home | bought | brother and mom | protein bar, smoothie bowl |
| 5c | 1PM | **vegetable salad** | college | ⭐ **given by mom** | college friends | fried rice, protein bar from canteen |
| 5d | 1PM | **rice with chole** | college | ⭐ **given by mom** | college friends | fried rice, protein bar from canteen |
| 5e | 3PM | **green tea** | college canteen | bought | college friends | vada pav, chaat |
| 5f | 3PM | **protein chips** | college canteen | bought | college friends | vada pav, chaat |
| 5g | 7:30PM | **mexican paneer burrito** | home | ordered from zomato/swiggy | with family | pizza, mexican rice bowl |

### EVENT 6 — a content creator who does not optimise for health
**26 · Pune · content creator making gaming and chess content · 2 friend room-mates ·
non-vegetarian · yesterday was normal**

| # | when | item | where | bought / made / given | with | nearly had |
|---|---|---|---|---|---|---|
| 6a | 1PM | **chicken burger** | home | zomato / big basket, *"wherever the most discounts are"* | room-mates | mutton biryani, lays chips, doughnut |
| 6b | 1PM | **Amul Masti chaas** | home | zomato / big basket | room-mates | as above |
| 6c | 1PM | **momos** | home | zomato / big basket | room-mates | as above |
| 6d | 1PM | **brownie** | home | zomato / big basket | room-mates | as above |
| 6e | 4PM | **frappuccino from Starbucks** | Starbucks | bought | **alone** | cooler from Chaayos |
| 6f | 9PM | **pizza** | **friend's home** | bought | with friend | taco bell tacos, quesadillas, diet coke |
| 6g | 9PM | **Red Bull** | **friend's home** | bought | with friend | as above |
| 6h | 9PM | ⭐⭐ **a SuperYou protein bar** | **friend's home** | bought | with friend | ⚠ **no alternative named** |
| 6i | 2AM (next day) | **maggi** | home | bought from zepto/blinkit, made at home | **alone** | pasta and fries from zomato |
| 6j | 2AM (next day) | **chips** | home | bought from zepto/blinkit | **alone** | pasta and fries from zomato |

⚠⚠ **NO BREAKFAST. His first item of the day is at 1PM.**

### EVENT 7 — a factory supervisor managing a condition
**45 · Surat · temple in the morning, then the factory where he is supervisor · his mother, wife
and 2 sons · vegetarian · yesterday was normal**
⚠⚠ **Both doctor questions on the sheet came back BLANK.** He takes medicines twice daily.

| # | when | item | where | bought / made / given | with | nearly had |
|---|---|---|---|---|---|---|
| 7a | 8AM | **tea** | home | made by wife | with sons | samosas instead of paratha |
| 7b | 8AM | **khaari** | home | made by wife | with sons | as above |
| 7c | 8AM | **biscuits** | home | made by wife | with sons | as above |
| 7d | 8AM | **paratha** | home | made by wife | with sons | samosas |
| 7e | 8AM | ⭐ **medicines, after** | home | — | with sons | — |
| 7f | *"12AM"* (noon) | **khichdi** | factory | ⭐ **packed by wife** | factory workers | *"this is the only option"* |
| 7g | noon | **packet of khakra** | factory | ⭐ **packed by wife** | factory workers | *"this is the only option"* |
| 7h | noon | ⚠ **jalebi** | factory | ⭐ **packed by wife** | factory workers | *"this is the only option"* |
| 7i | 5PM | **chai** | chai tapri outside factory | bought | other factory supervisors | patra or khandvi |
| 7j | 5PM | **fafda** | chai tapri outside factory | bought | other factory supervisors | patra or khandvi |
| 7k | 8PM | **khaman dhokla** | home | made by wife | with family | *"average indian meal"* |
| 7l | 8PM | **pakoda** | home | made by wife | with family | *"average indian meal"* |
| 7m | 8PM | **kadhi and rice** | home | made by wife | with family | *"average indian meal"* |
| 7n | 8PM | ⭐ **medicines, after** | home | — | with family | — |

⚠ **He personally bought TWO of his fourteen items** (7i, 7j). His **wife or his doctor** decided the other twelve.

---

# ⭐ THE ROUTING — recorded 2026-08-21, AFTER the verbatim block above and not before

✓ clean · ~ marginal · ⚠ strained (routes, but for the wrong reasons) · ❌ no moment exists

| # | item | 8-occasion grid | 22-moment map | |
|---|---|---|---|---|
| 3a | poha, 9AM, home, family | ❌ `breakfast_on_the_run` says *"will not sit down to eat"* | **Breakfast, sat down** | ✓ |
| 3b | fruit, same sitting | ❌ | **Breakfast, sat down** | ✓ |
| 3c | chai, same sitting | ❌ no beverages in the pack | **Breakfast, sat down** *(beverage in a food moment)* | ✓ |
| 3d | roti + sabji, 12:30PM | ❌ no meal moments | **Midday meal** | ✓ |
| 3e | dahi, same sitting | ❌ | **Midday meal** | ✓ |
| 3f | **chai, 3PM, home, ALONE** | ❌ `desk_slump_4pm` — she has no desk | ❌❌ **NO MOMENT EXISTS** | ⚠ |
| 3g | **biscuit, 3PM, home, alone** | ❌ | ❌❌ **NO MOMENT EXISTS** | ⚠ |
| 3h | **khaari, 3PM, home, alone** | ❌ | ❌❌ **NO MOMENT EXISTS** | ⚠ |
| 3i | **bread + jam, 5PM, home, alone** | ❌ | ❌❌ **NO MOMENT EXISTS** | ⚠ |
| 3j | **maggi, 5PM, home, alone** | ❌ | ❌❌ **NO MOMENT EXISTS** | ⚠ |
| 3k | the grocery shop, 6PM | ⭐ `household_stock_up` ✓ | **Household stock-up** *(tie-break 4)* | ✓ |
| 3l | roti sabji, 8PM, family | ❌ | **Dinner at home** | ✓ |
| 4a | chai, 8AM, snack shop | ⚠ `breakfast_on_the_run` only if you ignore its *"leaving late"* story | **Breakfast, in motion** | ~ |
| 4b | biscuits, same | ⚠ same | **Breakfast, in motion** | ~ |
| 4c | aloo patty, same | ⚠ same | **Breakfast, in motion** | ~ |
| 4d | **roti sabji GIVEN BY BOSS**, 2PM | ❌ grid is built on *"what they actually buy"* — he bought nothing | **Midday meal** | ✓ |
| 4e | **Frooti, given by boss** | ❌ | **Midday meal** | ✓ |
| 4f | **chai, 5PM, snack shop** | ❌ `desk_slump_4pm` — ⭐ **no desk** | **The afternoon dip** *(away from home)* | ✓ |
| 4g | biscuits, same | ❌ | **The afternoon dip** | ✓ |
| 4h | rice + dal, 8PM, bhojanalay, alone | ❌ | **Dinner brought in** | ⚠ |
| 4i | Sprite, same sitting | ❌ | **Dinner brought in** | ⚠ |
| 5a | fruit, 9AM, home, family | ❌ | **Breakfast, sat down** | ✓ |
| 5b | ⭐ **protein cereal**, 9AM, sat down | ❌ she sat down | **Breakfast, sat down** | ✓ |
| 5c | salad, 1PM, ⭐ **mom's tiffin** | ❌ | **Midday meal** | ✓ |
| 5d | rice + chole, same | ❌ | **Midday meal** | ✓ |
| 5e | green tea, 3PM, college canteen | ❌ no beverages | **The afternoon dip** | ✓ |
| 5f | ⭐ **protein chips**, 3PM, canteen | ~ `desk_slump_4pm` — a canteen, not a desk | **The afternoon dip** | ✓ |
| 5g | burrito, 7:30PM, Zomato | ❌ | **Dinner brought in** | ✓ |
| 6a | chicken burger, 1PM, ordered | ❌ | **Midday meal** | ✓ |
| 6b | Amul Masti chaas, same | ❌ | **Midday meal** *(not Hydration — clock beats habit)* | ✓ |
| 6c | momos, same | ❌ | **Midday meal** | ✓ |
| 6d | brownie, same | ❌ | **Midday meal** | ✓ |
| 6e | **frappuccino, 4PM, Starbucks, alone** | ❌ no desk, and it is not guilt-free | **The afternoon dip** ⚠ *Evening-out-of-home also passes; no tie-break separates them* | ~ |
| 6f | pizza, 9PM, **friend's home** | ❌ | **Dinner brought in** ⚠ *he is the GUEST; Hosting is written host-side only* | ⚠ |
| 6g | Red Bull, same | ❌ | **Dinner brought in** | ⚠ |
| 6h | ⭐⭐ **SuperYou protein bar**, 9PM, friend's home | ❌ | **Dinner brought in** — ⚠⚠ **a moment the map lists SuperYou as SILENT on** | ⚠ |
| 6i | **maggi, 2AM, home, alone** | ❌ `late_night_craving` says *"wants something sweet"* — ⭐ **maggi is savoury** | **Late-night** *("after 10pm, unplanned, usually alone")* | ✓ |
| 6j | chips, same | ❌ same | **Late-night** | ✓ |
| 7a | tea, 8AM, home, family | ❌ | **Breakfast, sat down** | ✓ |
| 7b | khaari, same | ❌ | **Breakfast, sat down** | ✓ |
| 7c | biscuits, same | ❌ | **Breakfast, sat down** | ✓ |
| 7d | paratha, same | ❌ | **Breakfast, sat down** | ✓ |
| 7e | ⭐ **medicines, after breakfast** | ⭐ `daily_health_routine` ✓ ⚠ but it says *"a habit someone has DECIDED to keep"* | **Daily regimen** *(route the ITEM, not the sitting)* | ✓ |
| 7f | khichdi, noon, ⭐ **wife's tiffin** | ❌ | **Midday meal** | ✓ |
| 7g | ⭐ **packet of khakra**, wife's tiffin | ❌ | **Midday meal** ⭐ *(bought by the wife on a stock-up; eaten by him at lunch — tie-break 4 in real life)* | ✓ |
| 7h | ⚠ **jalebi**, wife's tiffin | ❌ | **Midday meal** | ✓ |
| 7i | **chai, 5PM, chai tapri** | ❌ `desk_slump_4pm` — ⭐ **no desk** | **The afternoon dip** | ✓ |
| 7j | fafda, same | ❌ | **The afternoon dip** | ✓ |
| 7k | khaman dhokla, 8PM, home | ❌ | **Dinner at home** | ✓ |
| 7l | pakoda, same | ❌ | **Dinner at home** | ✓ |
| 7m | kadhi and rice, same | ❌ | **Dinner at home** | ✓ |
| 7n | ⭐ **medicines, after dinner** | ⭐ `daily_health_routine` ✓ | **Daily regimen** *(second occurrence, same day)* | ✓ |

## THE HEADLINE COUNTS — shape, not rate

| | grid | map |
|---|---|---|
| **all 52 items** | **3** | **47** |
| ⭐ **the FAIR comparison — the 34 items a snacking-and-nutrition grid actually claims** (non-meal food + all beverages; meals excluded because the grid never claimed them) | **3 of 34** | **29 of 34** |
| items **neither** map can place | — | **5**, and all five are ONE person in ONE hole |

⚠⚠ **DO NOT TURN ANY OF THESE INTO A PERCENTAGE OF ANYTHING.** Five people, one day each.
This settles STRUCTURE. It cannot size a single moment.

---

# ⭐⭐ WHAT THE FIVE DAYS ESTABLISH — twelve findings, roughly by how much they change

## 1. ⭐⭐⭐ THE INCOME CLAIM IS DEAD IN ITS STRONG FORM. IT SURVIVES IN A BETTER ONE.

**This was the whole reason for the exercise (`#64`, part B): simulated people said the three
highest earners held all three moments and the two lowest held one.** Five real days:

| person | distinct moments occupied |
|---|---|
| P1 · housewife, Mumbai | **4** (+2 items in a hole the map has no cell for) |
| P2 · **construction labourer, Delhi** | **4** |
| P3 · student, Bangalore | **4** |
| P4 · content creator, Pune | **4** |
| P5 · factory supervisor, Surat | **5** |
| *(event 1 · the user, metro office)* | *6* |

⚠⚠ **THE CONSTRUCTION LABOURER HAS AS MANY MOMENTS AS THE BANGALORE STUDENT AND THE PUNE CONTENT
CREATOR.** The simulated spread was 1 → 3. The real spread is **4 → 5.**

⭐⭐ **THE CLAIM THAT SURVIVES, AND IT IS MORE USEFUL:** income does not change **how many**
moments a person has. It changes **which ones, where they happen, and who pays.** P2 has four
moments — they are just a snack shop, a construction site, a snack shop and a bhojanalay, and two
of his nine items were bought by his employer.

⚠ **Direction, not magnitude, survives one way:** P2 has a **six-hour hole from 8AM to 2PM**, the
longest empty stretch in the data. So the *"fewer moments"* intuition was pointing at something
real — it just wasn't the count.

⭐⭐ **CONSEQUENCE FOR DECISION 4:** the map does **not** need to shrink for low-income regions.
The argument that a smaller map is enough because poor people have fewer moments **is not
supported by the only real evidence anyone has collected.**

## 2. ⭐⭐⭐ THE GRID'S OCCASIONS FAIL BECAUSE THEY ARE STORIES, NOT QUESTIONS

Every single grid failure in this dataset has the same shape: the moment is **right** and an
**incidental piece of narrative prose acts as an exclusion criterion.**

| the grid says | the real item it excluded |
|---|---|
| `desk_slump_4pm` — *"the afternoon dip **at a desk**"* | 4f/4g chai at a snack shop · 7i/7j chai at a tapri · 5e/5f at a college canteen. ⭐ **Three of the five people had a 3-6pm away-from-home moment and NOT ONE was at a desk** |
| `late_night_craving` — *"wants something **sweet**"* | 6i/6j **maggi and chips at 2AM** — savoury |
| `breakfast_on_the_run` — *"**leaving late**, will not sit down to eat"* | 3a/3b/3c, 5a/5b, 7a-7d — **four of six people ate breakfast sitting down**, and 4a-4c was routine, not a rush |
| `daily_health_routine` — *"a habit someone has **DECIDED** to keep"* | 7e/7n — ⚠ **a doctor decided, not him.** The exact restriction-vs-preference distinction P5 was recruited to test |

⭐⭐ **The map's equivalents catch all of them**, because they are written as the **minimum
discriminating question**: *"Is this the 3-6pm energy trough, away from home?"* · *"Is this after
10pm, unplanned, and usually alone?"* · *"Is this taken on a schedule, whether or not anyone is
hungry?"*

⭐⭐⭐ **THIS IS THE MOST TRANSFERABLE FINDING IN THE WHOLE EXERCISE, AND IT IS NOT ABOUT F&B.**
It is a rule for authoring any cell in this system: **a cell must be a question, not a vignette.**
Colour belongs in the anchor, where it describes one person. In the cell definition it silently
becomes a filter. ⚠ Worth checking the nine stances and the disposition format against it.

## 3. ⭐⭐⭐ ONE HOLE IN THE MAP, AND IT SWALLOWED FIVE OF ONE WOMAN'S TWELVE ITEMS

**P1 at 3PM: chai, biscuit, khaari — at home, alone. P1 at 5PM: bread-and-jam, maggi — at home,
alone.** Apply every question:

- `The afternoon dip` — *"3-6pm energy trough, **away from home**"* → ❌ she is at home
- `Evening tea` — *"Is **the household sitting down together** with tea?"* → ❌ she is alone
- `After-school feed` — *"an adult deciding what **a child** eats"* → ❌ her children are 15 and 18

⭐⭐ **THE CAUSE IS EXACT AND IT IS A ONE-WORD CLASS OF ERROR: two adjacent cells discriminate on
two DIFFERENT AXES.** The afternoon dip splits on **location** (away from home). Evening tea
splits on **company** (household together). Two neighbouring cells cutting on different axes
leaves a hole, and the hole is **at home + alone** — which is where a housewife spends her entire
afternoon.

⚠⚠ **And she is the ONE population we have actually built** — 192 generated women, judged not
representative, never checked against a real day. **This is the first real day of hers anyone has
looked at, and the map cannot hold 5 of her 12 items.**

⭐⭐ **THE FIX IS TO LOOSEN A QUESTION, NOT TO ADD A MOMENT.** Re-cut the pair on ONE axis —
location — so `Evening tea` becomes *"Is this an at-home tea or snack between lunch and dinner?"*
✓ **Checked against every other item in the dataset: it catches 3f-3j and wrongly catches
nothing** (P2's and P5's 5PM chai are both away from home and stay in the afternoon dip).
⚠ **Not applied. It is the user's decision 4.**

## 4. ⭐⭐⭐ MOST OF THIS FOOD WAS NOT BOUGHT BY THE PERSON WHO ATE IT — AND BOTH MAPS ARE BLIND TO IT

| person | items they personally chose and paid for |
|---|---|
| P5 · factory supervisor | ⚠⚠ **2 of 14.** His **wife or his doctor** decided the other twelve |
| P2 · construction labourer | 7 of 9 — **his boss provided lunch and the drink** |
| P3 · student | 5 of 7 — **her mother packed lunch** |
| P1 · housewife | she is the **provider**; she cooked nine of her own twelve |
| P4 · content creator | ⭐ **10 of 10 — the only person who bought everything he ate** |

⚠⚠ **THE ENTIRE GRID IS BUILT ON *"WHAT THEY ACTUALLY BUY"*** — `everyday_alternatives` is headed
*"WHAT THEY ACTUALLY BUY MOST OF THE TIME."* **A panel of P5 answering *"what would you buy
here"* is answering about one-seventh of his day.**

⭐⭐ Session 46 saw this ONCE (event 1e, a free office spread) and filed it as an edge case.
**Five real days say it is not an edge case — it is most of the food**, and it arrives in four
distinct forms: an **employer** (4d/4e), a **mother** (5c/5d), a **wife** (10 of P5's 14), and a
**host** (6f-6h). ⭐ The only person free of it is a 26-year-old man living with flatmates.

⚠ **This affects the grid and the map EQUALLY** — neither distinguishes *"I chose this"* from
*"this appeared."* It is not an argument for either side of decision 3; it is a **third thing that
needs building whichever way that decision goes.**

## 5. ⭐⭐ A QUARTER OF EVERYTHING THEY CONSUMED IS A BEVERAGE, AND THE PACK CONTAINS ZERO

**12 of 52 items are drinks**, and **five of five people had at least one**: chai ×5, green tea,
Frooti, Sprite, Amul Masti chaas, a Starbucks frappuccino, Red Bull.

| pack | beverages |
|---|---|
| `health_nutrition_snacking` (45 brands) | **0** |
| `health_wellness_nutrition` (20 brands) | **0** |

⭐⭐ **This is the SuperYou failure a FIFTH time — and the first time it is COUNTED rather than
argued.** `#48`: no confectionery. `#58`: no beverages. `#62`: the pack was not the lever. Event
1b: a real buyer's protein incumbent was a milk. Now: **a pack that cannot name a single one of
them is missing a quarter of everything five real people put in their mouths.**

## 6. ⭐⭐ THE ONE REAL SUPERYOU EVENT WE HAVE ROUTES TO A MOMENT THE MAP SAYS SUPERYOU IS SILENT ON

**6h — a SuperYou protein bar, 9PM, at a friend's home, with a pizza and a Red Bull**, eaten by
the person recruited precisely because he does not optimise for health.

The map's own validation table pre-registers SuperYou's subscriptions as
**afternoon dip · late-night · breakfast in motion · fitness session**, and lists it as silent on
**hosting · gifting · dinner · hydration.** ⚠⚠ **The single observed event routes to `Dinner
brought in` — one of the four it is silent on.**

⚠ **n = 1. It is not a rate and it does not falsify the subscription list.** But it was written
down before anyone looked, and it is a direct hit. ⭐ Note also that he named alternatives for the
pizza and the Red Bull and **named none for the bar** — so the bar was **additive, not
substitutive**, which is not how any competitive-set model in this system represents it.

## 7. ⭐⭐ ELEVEN OF TWENTY-TWO MOMENTS WERE NEVER OBSERVED — AND SEVEN OF THOSE PROVE NOTHING

| | moments | occupied in six real days |
|---|---|---|
| **The clock** (13) — a single day **can** test these | | |
| | Midday meal | **6 of 6 people** |
| | The afternoon dip | **5** |
| | Breakfast, sat down | **4** |
| | Dinner at home · Dinner brought in | 3 each |
| | Breakfast in motion · Mid-morning break · Late-night | 1 each |
| | ⚠ **Evening tea · After-school feed · Evening out of home · Bedtime cup** | **0** |
| | ⚠ First cup | **unverifiable — never asked** |
| **The event** (6) — a single day **cannot** test these | Journey · Hosting · Festival & gifting · Recovery & care · Fitness session | **0** |
| | Celebration | 1 *(event 1e, as a modifier)* |
| **Standing habit** (3) | Daily regimen | 2 |
| | Household stock-up | 1 |
| | ⚠ Hydration | **0 — and almost certainly a collection failure; nobody writes down water** |

⚠⚠ **THE FAIRNESS RULE, AND IT IS THE ONE THIS PROJECT KEEPS RE-LEARNING:** the event band is
**episodic by construction** — the map's own words, *"triggered by the calendar or by life."*
**Asking five people about ONE day cannot observe an episodic moment.** An empty Journey cell is
evidence about the **method**, not the map. ⭐ *Can this sample physically exhibit what I am
measuring?* — **no, for 7 of the 11**: the five event-band zeros, `Hydration` (a collection
failure — nobody writes down water) and `First cup` (never asked).
⚠⚠ **THE ARITHMETIC, STATED SO IT CANNOT BE MISQUOTED: 22 moments · 11 never observed (10 zeros +
`First cup` unverifiable) · 7 of those 11 UNOBSERVABLE by this method · so FOUR count.**

⭐⭐ **SO THE ONLY EMPTIES THAT COUNT ARE FOUR CLOCK CELLS: Evening tea, After-school feed,
Evening out of home, Bedtime cup.** Two of those (Evening tea, After-school feed) are **the map's
own named merge candidates** — and finding 3 says Evening tea is empty because its **question** is
wrong, not because the moment is absent. ⚠ **Do not delete a cell that is empty because it is
mis-worded.**

## 8. ⭐⭐ FIVE REAL DAYS INVERT SESSION 46'S OWN MID-MORNING FINDING

`#65` made the 11am black coffee a centrepiece: *"the grid has no mid-morning moment"*, offered as
evidence for the map. ⚠⚠ **Not one of the five friends has a mid-morning break.** P1 goes 9AM →
12:30PM, P2 8AM → 2PM, P3 9AM → 1PM, P5 8AM → noon, P4 has no morning at all.

⭐ **`Mid-morning break` is occupied by exactly one person in six, and he is the metro desk
worker whose day generated the criticism.** The moment is real; it may be a **metro-office-worker
moment specifically.** ⚠ This is precisely the blind spot the field sheet was written to catch —
*"if every day we collect looks like that, we'll have built our own blind spot into the evidence
and then confirmed it"* — and it caught one on its first outing.

## 9. ⭐⭐ THE MAP'S TIE-BREAK ORDER HAS NO RULE FOR TWO CLOCK MOMENTS, AND IT COST AN ITEM

**6e — a frappuccino at 4PM at a Starbucks, alone.** Both pass:
- `The afternoon dip` — *"the 3-6pm energy trough, away from home?"* ✓
- `Evening, out of home` — *"bought and eaten outside, before dinner?"* ✓

All four tie-breaks are silent: neither is an event, neither is a habit, nobody is deciding for
anyone, nothing is being bought for later. ⭐ It resolves only by noticing that **#06 states a
window (3-6pm) and #09 only implies one** — which is not a written rule. **The router test hit the
same shape at its event #4** (evening tea vs afternoon dip). Two independent collisions, same
cause.

⭐ **PROPOSED FIFTH TIE-BREAK: the narrower stated window wins.** ⚠ **Not applied** — recorded for
the user.

## 10. ⭐⭐ THE MAP HAS A HOST AND NO GUEST

`Hosting` asks *"Is food being put out because someone else is in the house?"* — written entirely
from the **provider's** side, with chips *host* and *decides for others.* **P4 at 9PM is the
guest** (6f, 6g, 6h — including the SuperYou bar), and there is no cell for him. He falls to
`Dinner brought in`, whose chips are *app · household · indulge*, none of which describe a friend's
living room.

⭐ This is **finding 4 wearing a different costume**: the guest's appetite is consumed by food he
did not buy, displacing a purchase he would otherwise have made. ⭐⭐ **Three of the map's
strains — 4h/4i, 6f-6h, and the whole of finding 4 — collapse into one missing distinction:
WHO PROVIDED THIS.**

## 11. ⭐ "DINNER BROUGHT IN" HOLDS TWO OPPOSITE ECONOMIES, AND LUNCH IS NOT SPLIT AT ALL

- **4h/4i** — a migrant labourer eating dal-chawal alone at a bhojanalay because he has no
  kitchen. **Necessity, every night.**
- **5g / 6f** — a Bangalore family's Zomato burrito, a Pune flat's pizza. **Indulgence.**

Same cell. The moment's own description (*"Swiggy · Zomato · the restaurant downstairs"*, chips
*app · household · indulge*) describes only the second. ⚠ **The man who eats out most often is
invisible inside the cell built for eating out.**

⭐ **And note the asymmetry it exposes:** dinner gets two cells (at home / brought in); **lunch
gets one**, though 6a is an ordered-in lunch that is economically identical to an ordered-in
dinner. ⚠ Whatever decision 4 concludes, **the current cut is inconsistent between lunch and
dinner** — split both or merge both.

## 12. ⭐ THREE SMALLER THINGS, EACH CONFIRMED ON REAL BEHAVIOUR FOR THE FIRST TIME

- ⭐⭐ **The moment decides the role — replicated on a SECOND product.** Session 46 proved it on
  the user's coffee (substitute at 11am, companion at 4pm). **6b, Amul Masti chaas, routes to
  `Midday meal`; the router test's own event #7 routed buttermilk at 2pm to `Hydration`.** One
  product, two moments, two roles — now shown on a drink nobody in this project chose.
- ⭐⭐ **"Route the ITEM, not the sitting" confirmed a THIRD time, and first on a PRESCRIPTION.**
  7e and 7n are medicines taken inside a meal and routing to `Daily regimen`. ⚠ And **`Daily
  regimen` occurs TWICE in P5's day** — both maps treat a moment as a slot, not a count, which
  matters to anyone selling a twice-daily product.
- ⭐⭐ **Tie-break 4 has a real-world instance at last.** 7g, a **packet of khakra**: bought by the
  wife on a household shop, eaten by him at the factory at noon. **One purchase, two moments,
  two different people** — exactly what *"buying beats eating; the same biscuit eaten later routes
  on its own moment"* was written for.
- ⚠ **A rule that is right for routing and wrong for visibility.** *"A beverage inside a food
  moment routes to the food moment"* generalises to **dessert**: 6c momos and 6d brownie are
  discretionary impulse buys that vanish inside `Midday meal`. A snacking brand subscribed to
  `afternoon dip` and `late-night` would **never see that brownie.** ⭐ Not a routing failure —
  a **subscription** failure, and a different thing.
- ⚠ **"Non-veg" did not predict non-veg.** P2 declares non-vegetarian and ate none all day
  (aloo patty, roti-sabji, dal-chawal). ⭐ For him the constraint looks economic, not dietary —
  so the axis event 2 said was missing is **two axes**, preference and affordability.

---

# ⚠ WHAT IS STILL OWED — six blank boxes on the sheet

| table | blank field | what it blocks |
|---|---|---|
| ⚠⚠ **5** | *what the doctor told him to change, and roughly when* | **P5 cannot do the restriction-vs-preference job he was recruited for.** He was sent to work with **jalebi** by his wife — that is either fine or it is the whole finding, and we cannot tell |
| ⚠⚠ **5** | *what he stopped eating, and what took its place* | The only forced-substitution evidence in the set |
| ⚠ **1** | *anything she bought or cooked for someone else* | **She is the provider** — this is the field that measures finding 4 from the supply side |
| ⚠ **4** | *if any "healthy" product came up, even refused* | ⭐ Partly answered by the rows themselves: **a SuperYou bar (6h)** — but we do not know if it was habit, a one-off, or the friend's |
| **3** | *who paid for the app order* | Minor |
| **2** | *was there a canteen* | ⭐ Answered by the rows: **no canteen, the boss provides** |

⭐ **All six are factual, on-sheet questions and none of them requires a new interview design.**
