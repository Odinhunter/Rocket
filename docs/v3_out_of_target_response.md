# Who else responded — out-of-target behaviour, and what the report throws away

**Date:** 2026-07-27 · **Cost:** $0 (all from runs already on disk) · **Status:** finding,
no code changed.

Prompted by the user's question: *"all of our stats are based on 18 instead of 100… out of
100, is it that only 18 even cared to look? Was this a one-off MuscleBlaze case?"*

---

## 1. The premise correction — 18 is not "who cared"

**18 is the size of the target group, not the number of people who responded.** All 99
agents saw the ad and produced a full reaction; every one is on disk in `transcripts.json`.
The 18 is the subset the *headline metric* is computed on — the people the classifier read
as the audience this creative is aimed at.

So "11% would buy" means **2 of the 18 in-target people**, not 2 of the 2 who bothered to
look. Within those 18, 4 stopped and 14 scrolled past.

The half of the user's worry that is **correct**: the client report currently shows the
18 and discards the other 81 entirely. That data exists and is not surfaced anywhere.

## 2. What the other 81 did — and whether MuscleBlaze is a one-off

**It is not a one-off, but it is also not universal.** Out-of-target response is
**bimodal**: an ad either gets literally zero from everyone outside its target, or it gets
~8–9%. Nothing in between.

Every run on disk carrying a real within-target set (an empty within-set makes the whole
panel read "outside", so those runs are not comparable and are excluded):

| ad | runs | out-of-target agents | engaged | rate |
|---|---|---|---|---|
| MuscleBlaze Biozyme Performance Whey | 6 | 486 | **0** | 0.0% |
| AI-hype protein (buzzword control) | 1 | 76 | **0** | 0.0% |
| Starbucks — pause button | 1 | 68 | **0** | 0.0% |
| The Whole Truth whey isolate | 1 | 76 | 6 | 7.9% |
| ProSki protein cereal | 1 | 53 | 5 | 9.4% |

"Engaged" = did anything other than scroll past.

**Three of five ads: exactly zero. Two of five: ~8–9%.** MuscleBlaze holds zero across
**486 out-of-target agent-reactions in 6 independent runs**, spanning two protocol versions
(`rocket-2.4.0` and `rocket-3.0.0-dev`) — so it is not a v3 artefact.

⚠ **Do not read this as "MB is anomalous."** Pooling the four non-MB runs gives 4.03% and
makes MB look like a 2×10⁻⁹ outlier, but that pooled figure averages a bimodal
distribution — two of those four ads are themselves at exactly 0%. The honest statement is
that MB sits in the zero mode along with two other ads, consistently.

## 3. The mechanism is not clamped, and the agents are not told

Two checks, both of which the "it's a bug" hypothesis had to survive:

**Out-of-target agents CAN respond** — TWT and ProSki prove the path is live. TWT's six
include one who would **mention it to someone**: word-of-mouth from outside the bought
audience, currently discarded by the report.

**Agents are blind to their target status** (`agent/runtime.py:326-420`). An agent receives
persona core (demographic + disposition vector + chaos vector + anchor), the browsing
context, cycle position, the image, and the creative copy. Nothing else. `within_target` /
`target_class` / `inferred_target` appear nowhere in `runtime.py`, `render.py` or
`panel.py`. The within/outside split is applied **afterwards, in reporting**, from the
classifier's read of the *ad*.

So the concentration is **emergent, not imposed** — which is a point in the classifier's
favour: it predicted from the creative alone who would respond, and blind agents agreed.

## 4. The chaos vector IS working

It produces a clear and consistent gradient — engagement concentrates in the `impulsive` and
`moderate` bands and is near-absent in `deliberate`:

| segment | n | actions |
|---|---|---|
| TWT · skeptic_lapsed_protein::**impulsive** (out) | 4 | 2 linger |
| TWT · skeptic_lapsed_protein::**moderate** (out) | 7 | 3 linger, 1 would mention it |
| TWT · skeptic_lapsed_protein::**deliberate** (out) | 4 | 0 |
| MB · enthusiast_macros_lifter::**deliberate** (in) | 6 | 0 linger |
| MB · enthusiast_macros_lifter::**moderate** (in) | 8 | 3 linger |

That is a coherent behavioural pattern, not noise. **It is not evidence the pattern matches
reality** — see §6.

## 5. The sharpest case for showing all 100 — ProSki

`pragmatist_protein_snacker` was classified **in-target**: 23 agents, **23 scrolled past,
zero engagement**. Meanwhile out-of-target `enthusiast_macros_lifter::moderate` produced 2
lingers + 2 research-first, and out-of-target `skeptic_lapsed_protein` produced 3 more.

**ProSki's out-of-target group engaged at 9.4% while its in-target group engaged at 4.3%** —
more than double. Being in-target and actually responding are **decoupled**, and the current
report shows only the first. This is the "right ad, wrong person" signal the RETARGET
decision exists to catch, visible in the raw data one layer below where the report reads it.

## 6. What this does NOT establish

**Whether 0% is realistic is unknown and unknowable from this data.** Whether a real
population of 81 people outside a whey ad's target would produce zero stops — or four, or
twelve — has never been checked against a human. The engine has **discriminant** validity
(it separates ads) but has never had **criterion** validity (it has never been ground-truthed
against real consumers). The chaos gradient in §4 is internal coherence, not external truth.

This is the same gap the σ study (`docs/v3_sigma_study.md`) and the discriminant check
(`docs/v3_discriminant_check.md`) both landed on, and it is what the paused Track-1 human
panel exists to close.

One thing that would be suspicious in a real population: **exactly zero** is a hard number.
Real behaviour is rarely a clean gate. Whether the model treats "not my type" as a hard gate
rather than a low probability is a real open question — and the bimodality in §2 is
consistent with a gate.

⚠ **A confound worth not overclaiming:** whole-panel engagement fell from ~29% (MB, v2.0) to
~4% (MB, v3). It is tempting to attribute this entirely to v3's reaction-question reframe,
but the v2 runs had **no within-target split at all**, so two things changed at once.
Engagement fell; the cause is not isolated.

## 7. What this implies for the product

The user's instinct is right, and for a stronger reason than "brand managers would want it":
**the target classifier can put someone in-target who does nothing, and out-of-target who
acts** (§5). A report built only on the in-target subset cannot show that.

The fix is the **per-consumer-type response panel** already flagged as missing in
`docs/v3_report_redesign_brief.md` §5 — every consumer type, its action mix and next step,
marked in- or out-of-target. All the data is on disk (`l3_summary.json`
`segment_behavioral_distributions`); none of it needs a new run. It is a `ReadModel` change,
in the same file the FastAPI wrapper is waiting on.

**BUILT 2026-07-27/28** — the panel table (`ReadModel.panel`, v3 #13) and, after the same
category error reappeared in the word cloud, the audience-split lexicon (v3 #16).

## 8. The same error, found twice — and what it cost the second time

The word cloud was built **pooled across all 100 people**, and the user caught it on sight:
*"there is nothing working because most of the people out of 100 are out of target."*

Measured: MuscleBlaze's "working against you" cloud was **78% out-of-target person-mentions,
and 19 of its 29 terms had ZERO in-target speakers** — "grey tub" (0 in / 52 out), "not for
me" (0/28), "gym bro" (0/14). Those are people the ad was never aimed at, correctly bouncing.
**Targeting working, rendered as the creative failing.**

**Re-running it per audience changed the finding, not just the layout** ($0.145 for both ads):

| | pooled (wrong) | split by audience (correct) |
|---|---|---|
| MuscleBlaze, positives | **0 of 37 terms** | **3 among its target** — `27g` at **78% of the 18**, plus the Informed Protein cert |
| The Whole Truth, positives | 16, but 7 with no in-target speakers | **12 among its target** — `made without` 58%, `no maltodextrin` 25% |

The pooled cloud said MuscleBlaze had *nothing* working. Its actual target read the 27g claim
positively at 78%. That is the opposite conclusion, and it was an artefact of counting 81
strangers.

**The lesson generalises past the cloud: any surface that aggregates across the panel must
split in/out of target, because on a narrow ad the out-of-target majority swamps the signal.**
The `l3_summary`-derived surfaces (panel table, glance) got this right; the lexicon did not,
because it was built from raw transcripts where the target flag had to be carried in
deliberately. **Check any future aggregate against this.**
