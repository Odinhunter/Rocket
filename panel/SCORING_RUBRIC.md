# Panel Scoring Rubric — judging Rocket's persona reactions

**Why this exists.** Rocket's whole value rests on one untested assumption: *that its simulated buyers react the way real buyers would.* This panel is the ground truth. You read each generated reaction and judge: **would a real person of this type actually react this way?** Your scores are the validation signal.

---

## What you score
For **every persona × ad reaction** in the reaction sheets (e.g. `panel/mb_biozyme_reactions.md`), give:

### 1. Realism score (1–5) — the core judgment
> *"Would a real [this persona] in India react to this ad like this?"*

| Score | Meaning |
|---|---|
| **5** | Nails it. Sounds like a real person of this type — right knowledge, right reaction, right action. I know people who'd say this. |
| **4** | Believable, minor off-notes. |
| **3** | Plausible but generic — could be lots of people, not *specifically* this type. |
| **2** | Off. Wrong knowledge level, out of character, or a reaction this person wouldn't have. |
| **1** | Not a real consumer. Reads like a marketer/analyst/AI, or flatly wrong. |

### 2. "What rings false" — one line
The most useful field. If it's not a 5, say *why* in a few words (e.g. *"too articulate," "a real gym guy wouldn't notice the cert," "wrong — she'd never consider whey at all," "sounds like a brand manager"*).

---

## What "realistic" actually means — check these
- **Right knowledge level** — does this person know *as much as they should, and no more*? (A casual snacker shouldn't talk like a nutritionist; a macros lifter shouldn't read clinical trials.)
- **In-character reaction** — does the *objection / interest* fit who they are? (A clean-label woman rejecting "gym-bro" ✓; a lapsed skeptic doubting it ✓.)
- **Right action (R7)** — would they actually *do* that (scroll / seek info / buy)? Does the action match the words?
- **Real-buyer voice** — does it sound like an actual Indian consumer, or like a consultant/AI describing one?

## Red flags — dock points for these
- 🚩 **Consultant/marketer voice** — "this creative leverages…", segmentation-speak, too analytical.
- 🚩 **Too articulate / too thorough** — a real person scrolling wouldn't write an essay or notice everything.
- 🚩 **Wrong knowledge level** — expertise the person wouldn't have (or missing what they obviously would).
- 🚩 **Out of character** — engaging when they'd scroll, or vice versa.
- 🚩 **Generic** — would fit any persona equally → it's not really *this* one.

---

## Two ways to run it (your call)
- **Labelled (default):** persona type is shown. Faster; you judge type-fit directly.
- **Blind (stronger):** cover the persona label, read only the reaction, then guess *what kind of buyer* this is and whether it's a real person. If panelists can't tell the personas apart, or can't tell it's a real consumer — that's a finding.

---

## How to read the results
- **Average realism per persona** (across ads). A persona averaging **≥4** is validated; **<3** needs the disposition reworked.
- **Average realism per ad.** Low scores on a *specific ad* → the ad may be confusing the model, not the persona.
- **Read every "what rings false" note** — the pattern in *why* it's off tells us what to fix (the disposition, the voice corpus, or the prompt).
- **The bar that matters:** not "do they sound nice," but "**would a real buyer of this type genuinely react this way.**" Be a harsh judge — generous scores hide the problems we're trying to find.
