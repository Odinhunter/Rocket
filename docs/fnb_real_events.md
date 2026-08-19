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

# EVENTS 2-5 — awaited from the user (four friends' days)

⚠ **Record them here verbatim-first, route them second, and do not revise the routings above.**
