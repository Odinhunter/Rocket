# Is a MODIFIER just a STANCE? — the $0 check that gates the F&B refactor

**2026-08-19, session 45. $0, offline, by hand. Re-runnable — every command is below.**

The F&B design doc proposes splitting the 22 demand spaces into **moments** (where/when) and
**modifiers** (why/who-for), because `Celebration` and `Recovery & care` are reasons, not
moments. The user's objection is that this **adds a concept**. `HANDOFF.md` item 0 flags the
cheap way out twice: *"a modifier looks much closer to a STANCE than to a moment, so it may
cost nothing structurally."*

This is that check. **The answer is no — and the reason is more useful than a yes would have
been.**

⚠ **THIS IS INPUT TO THE USER'S DECISION #1, NOT THE DECISION.** Nothing here is built,
nothing is deleted, and the generation mechanism is deliberately not designed.

---

## The result in one line

**A modifier is not a stance — but the system has been carrying one anyway, misfiled in TWO
places at once, and 15 of the 64 cells in the current grid are already paying for it.**

| | |
|---|---|
| does the stance axis already encode a modifier? | **No.** 7 of 8 stances are durable attitudes; `gifter` is not one |
| so does the split add a concept? | **No — it re-files one the grid already has.** `gifter` (a stance) and `household_stock_up` (an occasion) are both who-for wearing other costumes |
| does it cost nothing, then? | **Not nothing.** It costs one explicit axis and refunds two misfilings. Roughly flat |
| what would make it expensive? | **Making modifiers a DIMENSION.** 22 × 8 × 5 = 880 types/region kills the refactor. As an optional FLAG the count stays 22 × 8 = 176 and the $5–6 estimate holds |
| ⭐ decided by the user, 2026-08-19 | **"why" and "who-for" are ONE axis** — *"makes it simpler and both elicit similar behaviour."* See the foot of this doc |

---

## The test

Not durable-vs-episodic. That test has a hole: in this population a grandmother whose whole
relationship to the category is feeding other people is arguably a **durable** gifter, so
"episodes" cannot separate the axes cleanly. The airtight test is **orthogonality — which
QUESTION does the axis answer?**

- The seven stances answer **"what does she want, and what does she reject?"**
- `gifter` answers **"who is it for?"**

Two different questions is two axes, whatever their lifespans.

⭐ Durable-vs-episodic still works for the MAP, where the objects are events rather than
people: `Celebration` and `Recovery & care` are states the same unchanged person is in on
Tuesday and not on Wednesday. Both are modifiers. Keep that test for the router; use
orthogonality here.

### Procedure

```
.venv/bin/python -c "import json,textwrap; d=json.load(open('generated_audience_w4560_t3_v2.json')); \
[print(textwrap.fill(f\"[{t['stance']} / {t['occasion']}] {t['l4_stance']}\",104)) for t in d['raw']]"
```

Read the `l4_stance` line of all 64 buyer types in the v2 region (women 45-60, tier-3,
`health_nutrition_snacking`) and ask of each: **is the other person in this sentence the MOUTH
the food goes into, or the source of approval?**

⚠⚠ **A KEYWORD SWEEP CANNOT ANSWER THIS AND THE FIRST PASS HERE GOT IT WRONG.** A regex for
husband/son/grandchild/family scored `aspirant` at **5 of 8** — as high as `gifter` — and the
finding looked dead. Reading the eight aspirant lines shows every one of those people is an
**authority or an audience**, never a recipient: *"whatever the doctor or her niece would
approve of"*, *"without her daughter-in-law commenting"*, *"explain to her husband as her own
expense"*. One line even runs the other way — *"ask her son to buy for her."* ⭐ **Mentioning
another person is not buying for them, and no pattern match can tell the two apart.** The
same trap as the audit's `_report_mix`: a keyword counter drifts the moment the prose moves
off the wordings it was built from.

---

## What the 64 lines say

### The seven stances are one kind of object

Across all eight occasions, every one of `loyalist`, `switcher`, `upgrader`, `aspirant`,
`skeptic`, `purist`, `pragmatist` describes **what SHE wants and what SHE rejects**. The
occasion supplies what she is reacting to; the attitude is hers and travels with her. That is
exactly what the code comment beside the enum claims — *"what changes per occasion is what
they are skeptical OF, not that they are a skeptic"* — and it holds on inspection.

| stance | 4pm dip | post-workout |
|---|---|---|
| skeptic | *rejects the claim that a factory-made thing beats what she cooks* | *rejects powders outright as a young men's gym thing dressed up for women* |
| purist | *rejects any wrapper at teatime… bought snacks taste of the packet* | *rejects the idea that a tin can do what a kitchen does* |
| pragmatist | *"I cannot plan my four o'clock a week ahead"* | *rejects anything that must be mixed, shaken or bought in a big tin* |

Same woman, same objection, different target. The axis works.

### `gifter` is a different kind of object — 8 of 8

In every one of the eight, the product ends up **in someone else's hands**: a table of eight ·
the grandchild · the son · the husband at the site · a guest · strangers on a journey · her
mother-in-law · six people who dropped in.

> *"Wants him fed and the tin honest."*
> *"Wants the child's face to light up and the mother not to scold her for it."*
> *"Wants food that lasts two days and can be offered to strangers without shame."*

⚠ **THEY ARE NOT OPINION-LESS, AND SAYING SO WOULD BE THE OVERCLAIM.** Each improvises an
attitude — *"she will not fund a wrapper"* is pragmatist-shaped, *"rejects anything a relative
recommends off a phone screen"* is skeptic-shaped, *"without shame"* is aspirant-shaped. The
damage is subtler and worse:

⭐⭐ **THE ATTITUDE IN THOSE EIGHT CELLS IS UNCONTROLLED AND UNREQUESTABLE.** You cannot ask
this grid for a *skeptic gifter* or a *loyalist gifter*, because the who-for occupies the slot
the attitude was supposed to sit in. Whatever attitude appears was never specified, never
spread, and cannot be varied. **One axis ate the other.**

### And `household_stock_up` carries who-for too — also 8 of 8

Every stance at that occasion is about feeding the household: *"the whole house will finish"* ·
*"one packet everyone will actually finish"* · *"the children"* · *"the family"* · *"seven
people for the week"* · *"feed everyone for a month"* · *"six people who dropped in"*.

⭐⭐ **AND THIS IS THE ASYMMETRY THAT DECIDES WHERE A MODIFIER BELONGS.** When who-for rides on
the OCCASION, **the stance survives intact** — all eight attitudes are present and distinct in
the stock-up column, and the skeptic there is unmistakably a skeptic (*"the same biscuit with a
sticker and a higher price"*). When who-for rides on the STANCE, the attitude is consumed.

**So a modifier can sit beside a moment. It cannot sit inside the attitude axis.**

### The arithmetic

| carrier | cells | what it costs |
|---|---|---|
| `gifter` stance | 8 | attitude unrequestable in all 8 |
| `household_stock_up` occasion | 8 | nothing structural — stance survives |
| overlap (`gifter` × `household_stock_up`) | 1 | counted once |
| **total cells already carrying who-for** | **15 of 64 (23%)** | **with no axis to declare it on** |

⭐ **TWO OF THE DESIGN DOC'S THREE NAMED GRID DEFECTS TURN OUT TO BE ONE DEFECT.** The doc
flags `household_stock_up` as *"a PURCHASE, not a moment"* on independent grounds. It is
misfiled for the same reason `gifter` is: **who-for has nowhere to live, so it colonises
whatever axis is nearest.**

---

## What this means for the decision

1. **The split is not an addition.** The grid already has a modifier; it is filed in two wrong
   drawers. Making it explicit is a correction, and it closes two known defects.
2. ⚠⚠ **A MODIFIER MUST BE A FLAG ON A CELL, NEVER A DIMENSION OF THE GRID.** This is the
   whole cost question. As a dimension: 22 moments × 8 stances × ~5 modifier states ≈ **880
   types/region**, which kills the refactor outright. As an optional flag on the cells where it
   matters: **22 × 8 = 176**, and the design doc's $5–6 estimate stands unchanged.
3. **It refunds two slots.** `gifter` leaving the enum returns the attitude axis to seven clean
   stances with room for a genuine eighth; `household_stock_up` leaving the occasion list frees
   a moment.
4. ⭐⭐ **DECIDED BY THE USER, 2026-08-19: ONE AXIS.** *"we can keep why and who-for the same,
   makes it simpler and both elicit similar behaviour."* ⭐ **The data agrees** — the eight
   gifter lines already blend the two without strain: *"a box that looks like a gift and does
   not embarrass her"* carries a recipient and a social reason in one sentence, and reads as one
   thought rather than two crossed axes. Behaviourally they converge too: gifting, hosting and
   celebrating all push toward share-size formats, presentable packaging, generosity signalling,
   and outright rejection of the single wrapped bar (*"a guest cannot be handed one wrapper"*).
   ⚠ **The accepted loss, recorded so nobody rediscovers it as a bug:** a gift box **for a
   birthday** cannot be expressed as gift × celebration. It gets ONE modifier value, and the
   second reason is invisible to the grid. ⚠ **Do not re-propose the split.**

---

## ⚠ What this test did NOT establish

- **It read ONE region.** Women 45-60, tier-3, snacking pack. In this population provisioning
  others is a large part of the role, which plausibly inflates who-for language everywhere. ⚠ A
  men-25-34-metro region could read differently, and `gifter` there might be a thinner column
  rather than a misfiled axis. **The finding is that who-for is structurally homeless, which
  does not depend on the region; the 15-of-64 count does.**
- **Nothing about the RINGS.** Whether the stance axis already encodes the competitive rings
  (upgrader = ring 3 → ring 2, and so on) is a separate $0 check and has not been run.
- **Nothing about the map's 22 spaces.** Only the 8-occasion grid on disk was read.
- **Nothing empirical about modifiers themselves** — no modifier has ever been generated,
  because none exists. This reads the shape of the hole, not the thing that fills it.
