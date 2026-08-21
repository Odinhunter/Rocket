# F&B world probe — PRE-REGISTERED BEFORE THE RUN

**2026-08-22. ~$0.30. Written and committed BEFORE any money was spent** — the standing rule
after `#58`, `#61` and `#63`, and after the 2026-08-19 probe that was validated for one thing and
then installed as another.

## THE RIG

```
scripts/generate_audience.py --market fnb --category fnb_world \
  --occasion afternoon_dip --gender any --age 25-40 --tier tier-1 --count 8
```

**ONE moment, ALL EIGHT stances, one region.** `--occasion` pins the moment and walks the stances
inside it — confirmed by `--dry-run`: *"afternoon_dip — PINNED, walking all 8 stances inside it"*.

⚠⚠ **WHY PINNED AND NOT `--count 21`.** `_cells()` is **occasion-major**, so a naive small count
buys one loyalist per moment and nothing else. **That is exactly how the 2026-08-19 probe came
back as 8 loyalists + 2 switchers and was then installed as an audience.** See memory
`a_probe_is_not_an_audience`.

## ⭐⭐ CAN THIS SAMPLE PHYSICALLY EXHIBIT WHAT I AM MEASURING?

**The question the last probe failed.** Answered per criterion below, before the run.

| I am measuring | can 8 people at ONE moment show it? |
|---|---|
| stance diversity of OPINION | ✅ **YES — the rig buys all 8 stances by construction.** This is the whole reason for pinning |
| whether the new world reaches the output | ✅ yes — every type must name alternatives |
| whether the question-not-vignette fix works | ✅ yes — the moment says *away from home*, so non-desk people are now admissible |
| whether people hold together across moments | ❌ **NO — one moment. Do not read coherence into this.** |
| how common any of this is | ❌ **NO. 8 types is not a rate.** |
| the other 20 moments | ❌ **NO.** A probe validates only what it was designed to validate |

## THE FIVE PRE-REGISTERED CRITERIA

⚠ **Thresholds fixed now. Do not move them after reading the output.**

### 1. ⭐⭐ THE PRIMARY ONE — DO THEY DISAGREE?
**PASS: at least 5 of 8 types would plausibly react DIFFERENTLY to the same afternoon-snack ad**,
judged on `l4_stance` (what they want and what they REJECT). **FAIL: 4 or fewer.**
⭐ This is the standing directive — *diversity of OPINION is the deliverable* — and it is the only
criterion that can kill the world pack.

### 2. ⭐ DOES THE BEVERAGE WORLD ACTUALLY REACH THE OUTPUT?
**PASS: ≥3 of 8 types name a BEVERAGE among what they buy or reject.**
Justification for the threshold: three of five real people had chai at this exact moment
(`docs/fnb_real_events.md` 4f, 5e, 7i), and `afternoon_dip.competes_with` names chai first.
⚠ **FAIL at 0-2 means the pack is in the prompt but not in the reasoning** — which would be the
`#59`/`#62` finding a third time (*the pack is not the lever*).

### 3. ⭐⭐ DOES THE QUESTION-NOT-VIGNETTE FIX SURVIVE INTO GENERATION?
**PASS: at least 2 of 8 types are NOT desk/office workers.**
The old grid said *"the afternoon dip **at a desk**"* and that one phrase cost three of five real
people their afternoon moment. The new question says *away from home*. ⚠ **If all 8 come back at
desks, the fix exists in the cell definition and not in the model's head**, and `#69` is cosmetic.

### 4. THE PRICE STEP
**PASS: ≥2 types reason about cost in a way that reflects the 4-9x step** (a ₹10-20 street or
stall item against a ₹60-105 packaged one). **Soft criterion — reported, does not gate.**

### 5. ABSENCE
**Any refused cell is a PASS signal, not a failure** — rule 6 exists so the generator can decline.
⚠ Refusals are read and reported, never re-prompted.

## WHAT WOULD MAKE ME SAY THE WORLD PACK IS NOT READY

- Criterion 1 fails → **the panel does not argue; do not buy the full region.**
- Criterion 2 fails at 0 → **the beverages are decoration; the pack is not the lever.**
- Criterion 3 fails → `#69`'s question field is not doing work at generation time.

⚠ **A pass on all five does NOT authorise the full 168-cell region.** It authorises *proposing* it.

## COST AND CONTAINMENT

**8 types, 2 batches, ~$0.30.** Output to `generated_audience_fnb_probe.json`.
⚠ **Nothing is installed.** ⚠ **No existing region file is touched.**
