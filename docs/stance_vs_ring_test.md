# Does the STANCE axis already encode the competitive RING? — the second $0 check

**2026-08-19, session 45. $0, offline, by hand.** Companion to
`docs/stance_vs_modifier_test.md`, same region, same method.

`HANDOFF.md` item 0 hoped for a shortcut: *"the STANCE axis may already encode the ring. An
upgrader moves ring 3 → ring 2 (Perk → Yogabar); a switcher moves within a ring; a loyalist is
anchored at their incumbent's ring; a purist rejects rings 1-3 entirely. If that holds, rings
need no new axis and cost nothing structurally."*

**Four predictions. One holds, one is true but empty, one is false, one is unreliable.**

⭐ **The practical answer is still "no new axis on the audience side" — but for a completely
different reason, and the difference matters.** Believing the shortcut would mean reading a
ring off a stance, and that reading is wrong most of the time.

---

## Result

| prediction | verdict | evidence |
|---|---|---|
| a **purist** rejects rings 1-3 entirely | ✅ **HOLDS, 8 of 8** | roasted chana · warm water with ajwain · soaked moong · home-made poha · til-gud laddoos · theplas (*refused the Haldiram's packet her son bought*) · soaked almonds (*gave the gummies away unopened*) · poha chivda. ⭐ The single packaged purchase in the whole column is *one Parle-G pack, **for guests*** — she rejects it for herself, so 8 of 8 stands, and the exception is **who-for**, the modifier finding surfacing through a third seam |
| a **loyalist** is anchored at their incumbent's ring | ⚠ **TRUE BUT EMPTY, 8 of 8** | anchored, yes — but at Marie Gold, Amul, Shelcal, Good Day, Bournville… **the ring comes from the incumbent, not from the stance** |
| an **upgrader** moves ring 3 → ring 2 | ❌ **FALSE — only 3 of 8** | **4 of 8 upgrade WITHIN ring 3 on price**: Marie Gold → Good Day cashew · Kurkure → Snickers · → Dark Fantasy · Bourbon-tier → Milk Bikis. Only 3 cross a claim tier (→ OZiva, → Yogabar/RiteBite, → OZiva) |
| a **switcher** moves within a ring | ⚠ **UNRELIABLE — 4 within, 3 cross, 1 unclassifiable** | crosses: biscuits → RiteBite protein bar · Marie Gold → a banana · Snickers → roasted chana. Within: milk → eggs → milk · Silk → Bournville → Silk · Power Gummies → Livogen · Bourbon → Milk Bikis. ⚠ A coin flip is not a rule |

⚠ **THE RING CLASSIFICATION OF A SWITCH IS SOFT AND THE FIRST COUNT HERE WAS WRONG** — written
as "5 of 8 cross" before recounting. Power Gummies → Livogen is arguably one supplement tier,
and the unnamed *"night sweet"* preceding Marie Gold cannot be placed at all. ⭐ **The verdict
survives either count** — at best the prediction holds half the time — **but lean on the
reversion pattern below, which needs no ring classification to see.**

---

## What the stance actually encodes

**The VECTOR, not the POSITION.** It tells you the direction and manner of movement. It does
not tell you where the person is standing when they move.

- **purist** — exits the packaged set entirely. ⭐ The one stance that *does* fix a position,
  because "rejects all of it" names an absolute place to be. That is why it is the only clean hit.
- **loyalist** — does not move. Position undetermined.
- **upgrader** — moves *up*. But "up" is **price** four times out of eight and **claim** three
  times. Direction determined, destination not.
- **switcher** — ⭐⭐ **the real pattern here is not lateral movement at all: 6 of 8 WENT BACK.**
  *"then went back to milk"* · *"went back to buying a banana"* · *"went back to Silk"* · *"went
  back to roasted chana"* · *"went back to the Livogen the doctor had written"*. The stance
  encodes **trial-and-reversion**, which no ring model describes.

### The structural reason, and it is the whole finding

⭐⭐ **A RING IS A PROPERTY OF THE (PERSON, FOCAL BRAND) PAIR. A STANCE IS A PROPERTY OF THE
PERSON ALONE.** The same woman is at ring 3 relative to SuperYou and at ring 1 relative to
Marie Gold. **A pair-property cannot be stored on one half of the pair**, so no amount of
stance vocabulary will ever encode a ring.

⭐ **Which means the handoff's own architecture was right and the shortcut was the wrong way to
reach it.** "Two lists, two owners" already puts rings 1-2 on the **BRAND PROFILE** and rings
3-4 in the **MOMENT**. Rings are **computed at read time, once a brand is named** — they are
not an attribute of the audience and never were. ✅ **No new axis on the audience side.
Confirmed — by the pair argument, not by the stance shortcut.**

---

## ⚠ THE GAP THIS OPENED — the incumbent is prose, not a field

To place a person on a ring at read time you need one fact: **what do they buy today?** That
fact is currently **only in `l5_behavior` prose** — *"sent the grandson for a Marie Gold pack,
as always"*.

⚠ **None of the eight vector axes carries it.** `brand_stance` is an attitude toward the focal
brand (favorable / hostile / loyalist / neutral / skeptical); `category_relationship` is
frequency (devotee / lapsed / never / occasional / regular). **Neither says what is in the tin.**

| | works today? |
|---|---|
| a model READING the persona and reasoning about rings | ✅ yes — the prose names the product |
| SELECTING or counting by incumbent (*"everyone whose 4pm is a plain glucose biscuit"*) | ❌ no — not queryable |

⭐ **So this is bounded, not fatal:** the read works, the analysis does not. Whether that earns
a structured `incumbent` field is a call for the user, and it is **one field, not an axis** —
see the decision register in `HANDOFF.md`.

---

## ⚠ What this test did NOT establish

- **One region, one pack.** Women 45-60, tier-3, `health_nutrition_snacking`. ⚠ The 4-of-8
  price-upgrade finding is a claim about *this* population, where an upgrade is affordable in
  biscuits and not in protein. A metro 25-34 region could upgrade on claim far more often.
- **32 of 64 types read** (all upgraders, switchers, purists, loyalists, plus both full
  occasion columns from the modifier test). The four stances tested are the four the prediction
  named; aspirant, skeptic, pragmatist and gifter were not classified by ring.
- **No focal brand was fixed.** Rings were read against the natural focal for each occasion. ⚠
  A ring assignment is only exactly defined once a brand is named — which is the finding, so
  this limit is the result rather than a flaw in it.
- **Nothing about whether rings 1-2 belong in onboarding.** That was already the user's call and
  is unchanged: ring-1 mapping is per-brand sales work, not map work.
