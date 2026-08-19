# Part B — does one person hold together across moments? PRE-REGISTERED CRITERION

**Written 2026-08-19/20 (session 46, across midnight) BEFORE the run, and committed before the run, on purpose.**
The result does not exist yet. ⚠ If you are reading this after the result, the criterion below is
what it must be judged against — do not adjust it to fit.

**The question it answers is decision 5:** *are people generated ONCE for a region and held
across many moments, or written fresh per (moment × stance) cell?* ⚠ The recorded
**"do not propose a shared population store"** decision was scoped **ACROSS categories**; this is
**WITHIN one map**, and the user explicitly invited the refactor. This test does not reopen that.

⭐ **Why it is worth $1 before it is worth a refactor:** if people fragment, shared-people dies
and person-per-cell stays — **a perfectly good outcome**, and far cheaper to learn here than
after 176 cells are built on it.

---

## ⚠⚠ THE OBVIOUS RIG IS VACUOUS, AND THIS IS WHY THE TEST IS SHAPED ODDLY

**Hand the model one person and ask for three moments in one conversation, and it will keep her
consistent — the person is sitting in its context.** That measures context retention, not the
concept. See `vacuous_test_shapes`.

⭐⭐ **So the rig is deliberately the HARD version: three blind calls, moment-major.** One call
per moment, each given all 8 people, **none of them able to see any other moment's output.** That
is also the **production shape** — a 22-moment map cannot be one context, so a shared store means
anchors written at different times onto the same skeleton. ⭐ **A coherence pass under this rig
generalises upward to any richer store; a pass under the easy rig would generalise nowhere.**

⭐ **And what is shared is the PERSON, not the opinion** — the demographic bundle only: age,
income, city, occupation, household. Anchors (l1-l5) and the stance are written per moment. That
is the split the codebase already has (`persona_biography_layer`: *WHO a persona is lives in
`demographic_bundles`, NOT the anchor*), so the test is faithful to the architecture it is
testing.

---

## The rig

**8 people, taken deterministically** — the **first bundle of each of the 8 types**, in stance
order, from `generated_audience_m2540_t1_testA_metro_control.json` (paid `#62`, admissible on all
five gates). ⚠ **No cherry-picking**: first bundle, every type, no substitutions.

| | person | native stance |
|---|---|---|
| P1 | 31, ₹3.1L, Pune — runs the second shift press at an auto-components unit | loyalist |
| P2 | 26, ₹7.5L, Hyderabad — junior QA tester at an IT services vendor | switcher |
| P3 | 36, ₹22.0L, Gurugram — manages vendor contracts for a hospital chain | upgrader |
| P4 | 25, ₹3.6L, Jaipur — helper-turned-assistant fitter, on sites most days | aspirant |
| P5 | 35, ₹5.2L, Nagpur — welder at a railway wagon repair workshop | skeptic |
| P6 | 34, ₹3.1L, Kanpur — runs a hand press at a leather goods unit | purist |
| P7 | 26, ₹4.6L, Pune — delivery rider on a food app | pragmatist |
| P8 | 33, ₹13.5L, Noida — front-desk and rostering at a mid-size hotel | gifter |

**Three moments, and the asymmetry is deliberate and pre-registered:**

| moment | status | cost |
|---|---|---|
| `desk_slump_4pm` | ⭐ **NATIVE — already paid for in `#62`.** These people were BORN here; their existing anchor is the fixed reference | $0 |
| `daily_health_routine` | **TRANSPLANT** — 8 anchors, one blind call | paid |
| `late_night_craving` | **TRANSPLANT** — 8 anchors, one blind call | paid |

⭐ **16 new anchors, inside the approved ~$1.00.** ⚠ **The asymmetry is the point:** moment 1 is
where the person and the opinion were co-authored; moments 2 and 3 are written onto a fixed
skeleton. **The test is whether they survive TRANSPLANTATION**, which is exactly what decision 5
asks and exactly what a store seeded from existing generations (the `--append` world) would face.

⚠ **The stance is NOT given to the model.** It is asked for, per anchor, so stance stability can
be read (secondary, below).

---

## ⭐⭐ CAN THIS SAMPLE PHYSICALLY EXHIBIT FRAGMENTATION?

**The mandatory section. A pre-registration without it is what misfired at `#59`** — it listed
limits and never asked whether the sample could produce the behaviour being hunted.

**Yes, and occupancy variance is designed in by choosing moments at different distances:**

- ⭐ **`daily_health_routine` is structurally distant for half these people.** Its channels are
  *"Amazon subscribe, HealthKart, the pharmacy, D2C"* and it is decided by *"cost per day"* —
  against **P1 (₹3.1L press operator), P4 (₹3.6L lift fitter), P6 (₹3.1L leather-press operator)
  and P7 (₹4.6L delivery rider)**. If reuse forces a moment onto a person who has no business in
  it, **these four are where it will show.**
- ⭐ **And natural for the other half** — P3 (₹22L, procurement at a hospital chain) and P2 (₹7.5L
  QA tester) are exactly who subscribes to a daily thing. **So the moment can be occupied AND
  unoccupied within one sample**, which is what makes occupancy readable rather than uniform.
- **`late_night_craving`** (*11pm, scrolling in bed, wants something sweet*) is broadly available
  across incomes — the control against which the hard moment is read.
- **Coherence** is measurable on any output: 8 people × up to 3 anchors each, read side by side.

⚠ **What could still make it unanswerable:** if the model declines so many transplants that
fewer than 4 people have 2+ occupied moments, coherence has too little to read — reported as
inconclusive with the declines quoted, not as a FAIL.

---

## ⭐ THE CRITERION

### PRIMARY — per person, across native + transplants. 8 people.

| class | means |
|---|---|
| **COHERENT** | one recognisable human across their occupied moments: same economic reality, same relationship to the category, same register |
| **DRIFTED** | recognisably related, but circumstances or attitude shift with no cause — suddenly comfortable, suddenly label-literate, suddenly a different kind of shopper |
| **CONTRADICTED** | a hard clash with the native anchor or with the given demographics |

**Pre-committed thresholds:**

| outcome | rule |
|---|---|
| ✅ **PASS — people can be shared** | **≥6 of 8 COHERENT and 0 CONTRADICTED** |
| ⚠ **WEAK — inconclusive** | 4–5 COHERENT, or exactly 1 CONTRADICTED |
| ❌ **FAIL — person-per-cell stays** | ≤3 COHERENT, or ≥2 CONTRADICTED |

### ⚠⚠ THE INDEPENDENT KILL — per anchor, on the 16 transplants.

| class | means |
|---|---|
| **GENUINE** | the person plausibly has this moment, and the anchor respects every given fact |
| **STRAINED** | the moment is a stretch; the anchor hedges or the behaviour is thin, but nothing given is broken |
| **INVENTED** | the anchor asserts what the person's given facts make implausible — the ₹3.1L press operator with a HealthKart subscription, a monthly D2C order on a daily-wage income |

❌ **≥4 of 16 INVENTED fails the design on its own, whatever the coherence count says.**

⭐⭐ **Why invention outranks coherence: in production nobody reads the declines.** A reuse
design that quietly fabricates a moment for someone who does not have it puts a person in the
room who does not exist — and the panel's whole value is that its people are real. **A design
that declines honestly is better than one that fills beautifully.**

### Declines are DATA, not the instrument

The schema carries an explicit decline with a reason, and the model is told a person who does not
genuinely have the moment must be declined. ⚠ **But the metro run produced 0 refusals across 16
types — this generator fills cells.** So occupancy is measured by the **hand-read
GENUINE/STRAINED/INVENTED classification**, and the model's own declines are reported beside it.
⭐ **Whether the decline option gets used at all is itself a finding.**

### SECONDARY / EXPLORATORY — does the STANCE travel?

Count how many of the 8 hold **one stance across their occupied moments**. The grid's own comment
predicts stability (*"what changes per occasion is what they are skeptical OF, not that they are
a skeptic"*) and so does the ring test (*a stance is a property of the person alone*). **This is
the first empirical check of that claim**, and if it fails the economics of 176 cells change.

⚠⚠ **AND IT IS WEAK EVIDENCE IN ONE DIRECTION ONLY.** Each person's demographics were authored
*inside* a stance cell, so **some stance information leaks through the biography**. A stance
**match** is therefore weak evidence; a stance **MISmatch** is strong evidence. ⚠ **Secondary.
Do not let it colonise the verdict.**

### ⚠ Explicitly NOT the criterion

- **Whether the writing is good.** Unfalsifiable.
- **Whether these are the right three moments** for the 22-moment map.
- **Anything about the other five occasions, other regions, or women.**
- **Persona quality, the tail, sizing, or the map's shape.**

---

## Judged by

Reading all 8 people's native + transplant anchors side by side, by hand, person by person.
⚠ **Not by keyword count.** Every classification — including every STRAINED and INVENTED call and
every rejected candidate — gets quoted in the result doc so it can be argued with.

---

## ⚠ Limits, stated before the result exists

- **n = 8 people, 16 transplants.** ⚠ **Two drifted people is not "25% fragmentation" — it is two
  people you can name and quote.** Same bare-honesty discipline as `#62`.
- **This tests the CONCEPT, not the production prompt.** The rig uses a trimmed system prompt
  (most of `_SYSTEM` is about inventing people and does not apply) with the same world —
  `_pack_brief` + `_grid_brief` + `_region_brief` verbatim — and the same register rules
  (disagreement, the L3/L4 ceilings, the price-comparison ban, write-the-experience).
- **One region, one gender, one tier, three moments of eight.**
- ⚠ **The people inherit the tier-1-label defect** measured in `#62` — some "tier-1" cities are
  tier-2. Irrelevant to coherence, which is read within a person.
- ⚠⚠ **THE OUTPUT FILE NEVER INSTALLS.** `generated_audience_m2540_t1_testB_shared.json` is a
  person-reuse experiment, not an audience: it has no grid coverage and the five gates do not
  apply to it. ⭐ **Do not "fix" it into a library.**

## The rig, exactly

```
# ~$0.60-0.90, 16 anchors, 2 blind calls  — inside the approved $1
.venv/bin/python scripts/test_shared_people.py \
    --people generated_audience_m2540_t1_testA_metro_control.json \
    --native desk_slump_4pm \
    --moments daily_health_routine,late_night_craving \
    --category health_nutrition_snacking \
    --out generated_audience_m2540_t1_testB_shared.json
```

⚠ **`--category health_nutrition_snacking` is not optional** — the default is the supplements
pack, and the people were born under the snacking pack.
⚠ **Each moment call is checkpointed to disk the instant it lands.** Money in memory is the
mistake this repo has already paid for twice.
⚠ **Never overwrite** the `#62` artifacts the people are read from.
