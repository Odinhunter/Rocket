# Audit of the generated people — women 45-60, tier-3, `health_nutrition_snacking`

**2026-08-18.** Prompted by the user reading the review page and catching one thing:
*"a 55-year-old woman cannot have a son who is training for the police force right now."*
They were right, and it generalises. This is the full read of all 192 people in
`generated_audience_w4560_t3_v2.json`, with `generated_audience_w4560_t3.json` (v1) as the
comparison.

Instrument: **`scripts/audit_generated_people.py`** — $0, offline, re-runnable.
⚠ **It reports and must never become a gate** — every check rests on a fuzzy semantic map,
and gating on one teaches the generator to write around it. Same reasoning as `_report_mix`.

---

## The one-line cause

**Nothing in the generation prompt does arithmetic, and nothing in it describes this
population's family life.** `household_hint` — the field that carries every relative — was
described to the model in **twenty-three characters**: `"ONE household detail. Same bans."`
The `occupation_hint` beside it carries ~700 characters, because that is the field we fixed
for the homemaker gap. Each household line was written on its own and never checked against
the woman's own age.

---

## FINDING 1 — age at first birth is systematically late, and has no left tail

34 of the 192 have a household line that pins when she had her **first** child (an only
child, or an explicitly eldest one, at a datable life stage). Every life-stage bound below is
the **oldest** the child could plausibly be, so these are **floors** — the real figures are
worse.

| | generous reading | central reading |
|---|---|---|
| median age at first birth | **28** | **31** |
| earliest in the entire set | **23** | 26 |
| first birth at 30+ | 18% | 56% |

⭐ **The tell is not the median, it is the missing left tail.** Not one woman of 192 had her
first child before 23 even on the reading most favourable to the generator. These women were
born 1966-1981 and married in small towns; first births at 19-22 should be the single largest
group and there are **zero**.

⚠ **v1 measures the same** (median 28, earliest 22). This predates the homemaker fix and is
independent of it — that fix neither caused nor cured this.

## FINDING 2 — the same defect runs the other way at the grandmother end

23 women have a datable grandchild. Reading those *backwards* (assuming her own child became a
parent at 24) gives a median first birth of **25** — and **two arithmetically impossible
cases**: 49-year-olds with school-age grandchildren, which needs her to have given birth at
**16**.

⭐ **So the population is incoherent in BOTH directions at once** — some women are mothers far
too late, a few are grandmothers far too early. That is the signature of no age model at all,
rather than of a wrong one.

## FINDING 3 — "190 distinct occupations of 192" was string distinctness, not job diversity

⚠ **This corrects a claim in the handoff.** The strings are distinct. The jobs are not:
**132 of 192 people (69%) hold one of ten jobs.**

| count | share | job |
|---|---|---|
| 22 | 11.5% | stitching / tailoring |
| 18 | 9.4% | tiffin / cooking for sale |
| 18 | 9.4% | home tuition |
| 16 | 8.3% | unpaid bookkeeping at the family shop |
| 13 | 6.8% | beauty parlour |
| 12 | 6.2% | shop counter, family shop |
| 12 | 6.2% | nurse / lab / health worker |
| 12 | 6.2% | anganwadi / ASHA |
| 11 | 5.7% | buffalo / milk round |
| 6 | 3.1% | school teacher |

⭐ **And the list is the prompt's own exemplar list.** `_SYSTEM` says: *"Running a shop,
tailoring at home, a tiffin or catering setup, tuition, a beauty parlour, dairy or a bit of
land…"* — the six home-based items in that sentence account for **94 of 192 people (49%)**.
The model read an illustrative list as a menu.

⚠ **This is worse in v2 than v1** (69% vs 43%). Partly bucket bias — the buckets were derived
by reading v2 — but the two biggest v2 buckets are near-zero in v1 (unpaid bookkeeping 0%,
tiffin 0.5%), and both are phrases the homemaker fix introduced as exemplars. **The homemaker
fix bought participation realism and paid for it in job variety.**

## FINDING 4 — whole classes of working woman are missing

Across 192 small-town women aged 45-60:

| count | occupation class |
|---|---|
| **0** | agricultural / farm / land labour |
| **0** | construction or manual labour |
| **0** | factory or mill work |
| 2 | domestic work in other people's houses |
| 2 | piece-rate home work (embroidery, papad) |

The panel is wholly a small-business and services panel. `agent/demography.py` already flags
the adjacent risk in its own words — *"tier → urban is a modelling assumption… for tier-3 the
urban column likely UNDER-counts who works"* — and this is the same seam.

⚠⚠ **DIRECTION CERTAIN, MAGNITUDE NOT SOURCED — do not repeat "agriculture is the largest
employer of women in India" as the target.** That figure is all-India and rural-dominated,
and this region is labelled urban; using it as the goal is exactly the different-quantities
error the demography module already warns about for 37%-vs-69%. **No sectoral split exists on
disk** — the UNFPA paper's work-shape figures cover self-employed/salaried/casual, not
industry. Zero farm workers in 192 town women is still wrong. The right target is the
**town/urban** sector split and it has to be fetched.

⚠ Related floor effect: only **4 of 192 (2%)** are under ₹2L household income (range ₹1.9L-
₹18L, median ₹5.5L). The poorest working women are missing along with the manual work.

## FINDING 5 — she is never a widow, though the women around her are

**2 of 192 (1%)** are widowed. In the same file, **8 households contain someone else who is
widowed** — a sister, a sister-in-law, a mother.

⭐ **That gap is the finding.** The generator can write widowhood perfectly well; it just
cannot write it for the woman the panel is about. This is the **third instance of one defect**:
it could not write a woman with no paid work (the homemaker gap), it could not write a retired
person with no second income (11 of 12 were re-employed), and now it cannot write a woman with
no living husband. **Absence, for the protagonist, is the thing it will not write.**
⚠ Direction certain, magnitude pending source — widowhood by age band, to be fetched.

## FINDING 6 — one-child families are over-represented

**54 of 192 (28%)** imply exactly one child; 78 (41%) imply two or more; 60 (31%) mention
none. A single-child family was uncommon in this cohort's childbearing years, and it
**compounds Finding 1** — a lone child still in college at 55 is implausible twice over.
⚠ **Direction from common knowledge; magnitude pending source.** NFHS-5's *children ever born
to women 40-49* table IS this number and has to be fetched, not recalled.

## FINDING 7 — religious community is near-uniform. ⚠ THE USER'S CALL, NOT OURS

| count | marker |
|---|---|
| 21 | Hindu — bhajan, temple committee, satsang, puja, tulsi, mahila mandal |
| 1 | Sikh — a gurudwara in Sirsa |
| 1 | Christian — a church women's group in Palakkad |
| **0** | **Muslim — no marker of any kind** |

Several of the towns generated into (Deoria, Purnia, Bhusawal, Barpeta, Bharuch) have
substantial Muslim populations. **Reported, not fixed.** ⚠ Whether the panel should carry
community at all is a product decision that is the user's, and any fix has to avoid the
obvious failure mode of costume markers — a name and a garment standing in for a person.
The Hindu texture in this file is good precisely because it is specific and ordinary
(a bachat gat register, a Tuesday satsang); anything added must clear the same bar.

## FINDING 8 — small arithmetic and labelling errors

- **Retirement before the retirement age.** Four women are described as already retired below
  58: three at 56 (municipal school, government school, district cooperative bank) and one at
  **52** (cooperative bank branch). ⚠ The 58-60 threshold is common knowledge, not a fetched
  citation; treat the direction as sound and confirm the number if it ever gates anything.
- **One straightforwardly wrong sum.** A 57-year-old bank clerk is *"ten years from
  retirement"* — she retires at **67**.
- **The tier label is noise.** 12 people are in a *"tier-3 city"* and 180 in a *"tier-3
  town"*, but **all 8 of those towns are labelled both ways** elsewhere in the same file
  (Nanded, Bharuch, Karimnagar, Bilaspur, Bhilwara, Erode, Karnal, Rewa).
- **7 people share an (age, income, town) slot** with someone else — three of them are
  54y / ₹3.2L / Bhadrak.
- **Repeated supporting characters**: 8 husbands drive a school van, 21 households contain a
  mother-in-law, 15 women attend a bhajan/satsang/mahila group, 11 have a bedridden relative.

---

## What is NOT wrong — worth recording so nobody "fixes" it

- **Regional and cultural texture is good and specific.** *Mahila bachat gat* in Beed,
  *satsang at the gurudwara* in Sirsa, payasam jaggery in Palakkad, slokas in Kumbakonam, a
  church women's group in Palakkad. None of it is generic and none of it is misplaced.
- **69 distinct towns**, real ones, correctly small.
- **Age spread is even** — 16 distinct ages, 8-14 people at each.
- **The homemaker fix held.** 71 of 192 unpaid/household-centred days, against 1 of 194 in v1.
  Nothing here argues for reverting it; Finding 3 argues for widening its exemplars.
- **Husband-side arithmetic is clean.** No woman aged ≤52 has a husband described as already
  retired — checked, zero violations.

---

## Where the fixes belong

⚠ **Nothing may be typed in from memory** — the same rule that governs the PLFS table.

| finding | fix | where |
|---|---|---|
| 1, 2, 5, 6 | sourced age-at-first-birth / age-at-marriage / children-ever-born / widowhood figures, keyed to geography, fed into the cached brief | `agent/demography.py` + `demography.brief` |
| 1, 8 | the household field gets real instructions: every named relative's life stage must be arithmetically consistent with her age | `household_hint` schema description ⚠ **field KEY unchanged** — `persona_core_hash` digests it |
| 3, 4 | ⚠ **NOT a richer exemplar list** — see below | `_SYSTEM` "ON HOW THESE PEOPLE SPEND THEIR DAYS" |
| 7 | user's decision first | — |
| all | re-run `scripts/audit_generated_people.py` before/after | — |

⭐⭐ **THE MECHANISM FOR FINDING 3, AND IT IS THE OPPOSITE OF THE OBVIOUS FIX.** The file
itself shows which half of the prompt the model obeys: the stated **proportion** was hit (37%
unpaid, against a target it was told), while the **exemplar list** was copied wholesale (six
nouns → 49% of the panel). ⚠ **So every concrete noun added to that prompt is a future
cluster.** The fix is more sourced distributional fact and FEWER named examples — not a longer
menu. Where exemplars must remain, mutation-prove that the clustering report in
`audit_generated_people.py` catches a menu regression.

## The sourcing list — fetch, never recall

- **NFHS-5** median age at first birth, by **cohort** (the women 40-49 / 45-49 row, not the
  all-women median) and by **residence**.
- **NFHS-5** children ever born to women 40-49 → Finding 6.
- Marital status / **widowhood by age band** → Finding 5.
- **Sector of work** for urban/town women → Finding 4.
- ⚠ `mospi.gov.in` and `pib.gov.in` fail from this machine (memory
  `india_stats_sources_blocked`). NFHS-5 is a DHS survey — try `rchiips.org/nfhs` and
  `dhsprogram.com`. WebFetch saves the PDF binary even when extraction fails; Read it.
- ⚠ If only an all-women median is fetchable, record it as an **upper bound** for a 45-60
  cohort and say so in the module, the way the tier→urban assumption is recorded.

⚠⚠ **THE FIX ROUTE CHANGED THE SAME DAY THIS AUDIT WAS WRITTEN.** The user's call, 2026-08-18:
personas are now written by **Fable in cloud chat on their own credits**, not by our paid API
calls. So the fixes above land in a **prompt we hand over**, not in `generate_audience.py`'s
call path, and the result comes back through the existing `$0` `--from-raw` → 5 gates → this
audit chain. ⚠ **The prompt must be REGION-GENERAL** — young tier-1 as readily as older
tier-3. See `THE METHOD, AS OF 2026-08-18` at the top of `HANDOFF.md` and memory
`personas_written_by_fable_in_chat`.
⚠ **And the before/after comparison breaks**: a Fable-authored region changes model AND prompt
at once, so never call the delta attributable. The checks in this document are absolute rather
than comparative, which is why they still work.

**Cost, as originally scoped (now superseded):** building and rehearsing all of it is **$0**;
seeing it land would have cost **one regeneration, ~$1.30**, to a **new `_v3` file**.
⚠ **v1 stays pinned as the homemaker before-evidence; v2 becomes this fix's before-evidence.**
⚠ **v3 must still clear the ≥40-unpaid floor** — Finding 3's fix must not undo the homemaker fix.
