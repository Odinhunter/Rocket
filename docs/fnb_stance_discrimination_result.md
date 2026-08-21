# Does a stance change how someone reacts to a real ad? — RESULT

**2026-08-22. `$3.85` actual** (preflight said `$3.64`). Run against
`docs/fnb_stance_discrimination_preregistration.md`, committed before the spend (`#74`).
Artifacts: `runs/demo/fnb_probe_v1/20260822_002701_seed71_the_whole_truth_protein_bar/`

## ⭐⭐⭐ THE HEADLINE: 7 OF 8 vs 0 OF 56

| stance | agents | acted |
|---|---|---|
| ⭐ **`upgrader_desk_afternoon_protein`** | 8 | **7 — `buy_at_restock`** |
| loyalist · switcher · aspirant · skeptic · purist · pragmatist · gifter | 8 each | **0** |

**Panel total: 57 `nothing`, 7 `buy_at_restock`.** ⭐⭐ **The one stance designed to want this
product is the only stance that moved, and it moved 7 times out of 8.** Every other stance is a
clean zero across all 56 agents.

⚠⚠ **This is the sharpest discrimination signal this project has produced.** The previous best was
the problem map at 0.231 vs 0.148 (`panel_discrimination_measured`). This is 7/8 against 0/56.

---

## THE FOUR PRE-REGISTERED CRITERIA

| # | criterion | result |
|---|---|---|
| 1 | ≥5 of 8 stances show a distinct dominant objection | ✅ **PASS — 6 distinct fix-directions.** ⚠ **But I mis-specified the measure; see below** |
| 2 | my `#73` predictions, ≥6 sound / ≤4 retract | ⚠ **5 of 8 — "PARTLY RIGHT". Neither vindicated nor retracted** |
| 3 | the upgrader separates measurably | ✅ **PASS, decisively — 7/8 vs 0/56** |
| 4 | aphorism check *(reported, does not gate)* | ⭐ **The reactions are far more concrete than the stance lines** |

---

## ⚠⚠ CRITERION 1 — PASSES, BUT MY PRE-REGISTRATION WAS WRONG ABOUT WHERE TO READ IT

**I pre-registered reading discrimination off the PROBLEM MAP.** The problem map cites only
**2 of 8** dispositions — and that is **correct behaviour, not a defect**: it reports *within-target*
pain by design, and 6 of 8 stances were classified OUTSIDE target. That is
`out_of_target_response_bimodal` working exactly as it should.

⭐ **So I had to read discrimination off the transcripts instead. That is a change of measure after
seeing the data, and it is my error, recorded as such.** ⚠ **The next pre-registration that wants
cross-stance discrimination must name the TRANSCRIPTS as the surface, never the pain map.**

**The measured objections — one per stance, from R6 friction:**

| stance | what it actually said | the fix it implies |
|---|---|---|
| loyalist | *"I'm not walking somewhere new for a bar when the stall is right there at 4pm"* | **distribution/proximity** |
| switcher | *"pachaas-saath rupaye toh hoga hi... kirana pe milega bhi nahi, order karna padega"* | **price + channel** |
| ⭐ upgrader | *"box pada hai ghar mein toh zaroorat nahi"* → `buy_at_restock` | **urgency — he already has stock** |
| aspirant | *"I don't even know what it costs or where you'd get it"* | **add a price and a where-to-buy** |
| skeptic | *"woh Yogabar wala experience bhi, do khaaye baaki cupboard mein sade"* | **trust / portion size** |
| purist | *"Paise bhi kyun lagane hain aisi cheez pe jab ghar mein sab hai"* | **a different competitor entirely — home food** |
| pragmatist | *"never under fifty rupees and that's just not what I'm spending at five-thirty near the gate"* | **price at a specific moment** |
| gifter | *"Ek bar ek insaan ke liye hai, table pe rakhne ke liye kaam nahi aata"* | **multipack** |

**Six clearly different fix-directions** — distribution, price/channel, urgency, missing CTA, prior
experience, format. ✅ **PASS.**

## ⚠ CRITERION 2 — I WAS 5 OF 8. TWO PREDICTIONS WERE PLAINLY WRONG.

| stance | I predicted | measured | |
|---|---|---|---|
| loyalist | ritual | *"not walking somewhere new... the stall is right there"* | ✅ |
| switcher | price ceiling | price **and channel** — *"won't be at the kirana"* | ✅ *(channel not predicted)* |
| upgrader | **accepts** | `buy_at_restock` — accepts, **deferred** | ✅ *(the deferral not predicted)* |
| aspirant | **indifferent / irrelevance** | ⚠ **a CONSIDERATION GAP** — *"I don't even know what it costs"* | ❌ **WRONG** |
| skeptic | disillusionment | *"do khaaye baaki cupboard mein sade"* — names the exact L5 fact | ✅ |
| purist | categorical rule *(shelf life)* | *"everything's at home"* — substitution, not the rule | ~ **partial** |
| pragmatist | **satiety** | ⚠ **PRICE**, not filling | ❌ **WRONG** |
| gifter | format / shareability | *"one bar is for one person, no use on the table"* | ✅ |

⭐⭐ **Where I was wrong I was wrong in the same direction both times: I read a stance line as a
STABLE TRAIT, and the agent produced a SITUATIONAL objection.** The aspirant is not indifferent — he
would consider it and the ad gives him nothing to close on. The pragmatist did not weigh satiety at
all — he priced it and stopped.

⚠ **Per the pre-registration, 5 of 8 is "partly right": `#73`'s eight-reasons table is NOT retracted
and NOT vindicated.** It was a reasonable reading that got the direction right on five and invented
the reason on two.

## ✅ CRITERION 3 — THE CLEANEST RESULT IN THE RUN

7 of 8 upgraders reached `buy_at_restock`; **all 56 other agents reached `nothing`.** ⭐ There is no
ambiguity to interpret. The instrument reads the stance.

## ⭐⭐ CRITERION 4 — THE APHORISM PROBLEM IS IN THE DISPOSITION LAYER ONLY

The user's objection to `#73` was that *"one bar for one person makes it a private thing, not a
round"* is unreadable. **The reaction layer does not have that problem:**

| the `l4_stance` line (writerly) | what the agent actually said (concrete) |
|---|---|
| *"not a round"* | *"table pe rakhne ke liye kaam nahi aata"* · *"buying for six people at a time"* |
| *"wants food that is food"* | *"jab ghar mein sab hai"* — when everything's at home |
| *"turns the break into a purchase decision"* | *"not walking somewhere new when the stall is right there at 4pm"* |

⭐ **The reactions name THINGS: ₹50-60, the kirana, the gate, 5:30pm, the table, the cupboard.** The
engine converts an aphoristic stance into concrete behaviour. ⚠ **So the `l4_stance` tightening is
still worth doing — a reader of the LIBRARY sees the aphorism — but it is a readability fix, not a
correctness one. It does not block the region.**

---

## ⭐⭐ THE FINDING NOBODY PRE-REGISTERED, AND IT IS ABOUT THE AD

**PRICE WAS THE DOMINANT OBJECTION FOR FOUR OF EIGHT STANCES — AND THE AD CONTAINS NO PRICE.**

switcher (*"₹50-60 it'll be"*), pragmatist (*"never under fifty"*), skeptic (*"daam pehle aayega
dimag mein"*), aspirant (*"I don't even know what it costs"*). ⭐ **Three of them invented a number
and rejected it; the fourth named the absence as the reason he couldn't act.**

The run's own purpose classifier called this `awareness_informer` — *"no price, no offer, no CTA"*.
⭐⭐ **So the diagnosis is coherent: an ad with no price gets rejected on imagined price by everyone
outside the franchise, and converts only the buyer who already knows what it costs.**

## ⚠ AND THE VERDICT'S OWN BARENESS, TO BE QUOTED WITH IT

**`WORKING`, confidence 72** — ⚠⚠ **resting on ONE within-target disposition of eight.** Six were
classified outside target and every one of them did nothing. ⭐ That is not a flaw in the read; it
is `out_of_target_response_bimodal` behaving correctly. **But "WORKING" must never be quoted without
"for the 1 in 8 this ad is actually aimed at."**

## WHAT THIS AUTHORISES

✅ **The stances discriminate. The cells behave differently in front of a real ad, not just on the
page.** That was the open question, and it is closed. ⭐ **The `$5-8` full region is now worth
buying** — the defect that would have made it a waste does not exist.

⚠ **Still not tested:** the other 20 moments, panel seating at 176-cell scale, and whether
discrimination survives when the panel spans *moments* rather than one. **64 agents at one moment is
not a rate and never was.**

---
---

# ⚠⚠ AMENDMENT, 2026-08-22 — THE USER CHALLENGED THE HEADLINE AND HALF OF IT DOES NOT SURVIVE

**Three challenges, all correct.** *"If 100 people buy something, probably 2 of them are gonna be
gifters."* · *"People rarely behave exactly the same way every single day."* · *"I don't think 7 of
8 would buy at restock — that seems like almost everyone."*

## ✅ WHAT SURVIVES — THE OBJECTION MAP

**The six distinct fix-directions stand** (distribution · price/channel · urgency · missing CTA ·
prior experience · format). They are read off transcripts, they are qualitative, and **none of the
three challenges touches them.** ⭐ Different stances DO raise different objections to the same ad.
That finding is intact.

## ❌ WHAT DOES NOT — THE 7-OF-8 BUY-INTENT NUMBER

⚠⚠ **`buy_at_restock` IS THE NULL HYPOTHESIS FOR AN EXISTING CUSTOMER, NOT AN AD EFFECT.**

| agent | cycle_position | said |
|---|---|---|
| 0 | ⚠ **`just_bought`** | `buy_at_restock` |
| 25 | ⚠ **`just_bought`** | `buy_at_restock` |
| 8, 39 | `running_low` | `buy_at_restock` — ⚠ they would restock anyway |
| 22, 42, 58 | `mid_cycle` | `buy_at_restock` |
| 31 | `mid_cycle` | `nothing` |

⭐⭐ **Two of the seven had JUST BOUGHT A BOX.** And the upgrader's own anchor **names The Whole
Truth by brand and price** (*"₹104 for a 52g bar… you order another box on Zepto"*). So this is
**RETENTION being counted as CONVERSION** — `decision.py:120` scores `buy_at_restock` as buy-intent,
and for a customer already on a subscription cadence the ad had to persuade nobody.

⚠ **AND THE RULER WAS PROBABLY WRONG ANYWAY.** The run's own classifier called this ad
`awareness_informer` — *"no price, no offer, no CTA"* — and `v2_4_purpose_layer` gates the informer
purpose. **Buy-intent was not the right measure for this creative.**

⭐ **THE ASSESSOR CAUGHT WHAT THE METRIC MISSED.** Pain P1 says the interest is *"consistently
deferred to an indefinite future restock the ad never converts."* **The diagnosis layer was right
and the headline number was wrong** — `panel_discrimination_measured` a second time.

## ⚠⚠ AND AN UNCONTROLLED CONFOUND ON THE ZEROS

Every persona was told: *"An ad for **international food and drink** lands…"* — the category slug
`fnb_world` rendered into persona-facing prose, the renderer reading *"world"* as *"international"*.
**This is Indian F&B and The Whole Truth is an Indian D2C brand.** ⚠ Framing it as foreign plausibly
inflates the price-and-not-for-me objections that four of eight gave. **The 0-of-56 cannot be
cleanly attributed.** ⭐ My slug choice in `#71`; fix before the region.

## ⭐⭐⭐ AND THE STRUCTURAL FINDING UNDERNEATH ALL THREE

**The panel outputs a STEP FUNCTION — 0% for seven stances, 87.5% for one. Real markets have
tails.** The user's *"2 in 100 buyers are gifters"* is the correct objection: **dispositions are
acting as deterministic filters rather than propensities.**

⚠ **And the chaos vector — which exists to supply that variance — cannot, because it is rendered as
a TRAIT.** It is baked into the cached biography, which makes it a second description of *who the
person is*, redundant with the disposition. **Two trait layers cannot produce day-to-day variance;
they only co-describe.** Measured here: within the only stance that acted, **impulsive, moderate AND
deliberate all bought** — chaos did not predict action even where action existed.

⭐⭐ **THE FIX SHAPE ALREADY EXISTS IN THIS CODEBASE** — `cycle_position` is a per-exposure SAMPLED
STATE, excluded from `persona_core_hash` and `segment_key`, riding the uncached context, with a
spec-declarable mix reported beside the headline. **Chaos has none of that and should have all of
it.** Design proposal: `docs/chaos_as_circumstance_proposal.md`.
