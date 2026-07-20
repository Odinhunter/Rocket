# v3 σ study (A8) — run-to-run variance + anchor re-verification

**Date:** 2026-07-21 · **Branch:** `v3` · **Cost:** $19.37 of $30 · **Status:** complete

The first paid, at-scale v3 run — everything before this was offline. It answers
three questions the plan set for #9: (1) how much does the headline metric wobble
run-to-run, (2) does the decision *bucket* stay stable, (3) do the four anchor
creatives still land the buckets we expect. It also, by design, stress-tested the
instrument with repeated sampling — and caught a real bug (§5).

All runs: `health_wellness_nutrition` library, `cold_traffic_v1` audience (100
agents, 5 within/adjacent dispositions × 4 contexts × chaos bands), `seed=71`
fixed, `reaction-v3` / `render-6` / `decision-3`, funnel off (D4). (Exception: MB
run 2 was recovered via `replay_synthesis`, which attaches the funnel — immaterial
to its headline rate and bucket, both read from the transcripts.)

---

## 1. The headline result — σ on MuscleBlaze whey (5 repeats)

Same spec, same fixed panel, 5 independent draws (4 fresh full runs + 1 recovered
via synthesis-replay of a genuine fresh L1 draw — see §5).

| Run | within-target buy-intent | research_first | decision |
|---|---|---|---|
| 1 | 2/18 = 0.111 | 0.22 | ITERATE / DIRECTIONAL |
| 2 | 0/19 = 0.000 | 0.47 | ITERATE / DIRECTIONAL |
| 3 | 0/19 = 0.000 | 0.26 | ITERATE / DIRECTIONAL |
| 4 | 1/19 = 0.053 | 0.37 | ITERATE / DIRECTIONAL |
| 5 | 0/19 = 0.000 | 0.42 | ITERATE / DIRECTIONAL |

- **Headline buy-intent: mean 0.033, σ = 0.049 (4.9 points), range 0–11 points.**
- **Parse rate: 99–100 / 100 on every run.** Both the Call-A `action` and the
  Call-B `next_step` terminal JSON parsed for ~all agents. The v3 two-call
  reaction surface holds at scale.
- **Decision bucket: ITERATE on all 5 — STABLE.** But read the mechanism honestly
  (see below): with buy-intent floored, the *headline did not drive the decision*.

**What the σ actually is, and what it isn't.** The panel is deterministic in the
spec, so all 5 repeats hit the **identical 19 within-target enthusiasts** — the
run-to-run movement is the *same people* sampled at temperature 1.0 giving
different answers. So this **is** model sampling noise, just quantized into ~5.3-pt
steps by n=19 (one agent = 1/19). Two consequences the raw σ hides:
- **σ is not constant across the metric's range.** We measured it at p≈0.03, where
  variance is tiny. Near the decision-relevant 0.75 floor, binomial SD alone is
  `sqrt(0.75·0.25/19) ≈ 9.9 pts` at n=19 — about **2× the floor-σ we observed**.
- **Panel-design finding for #10 (new):** at n≈19 within-target the headline is
  intrinsically **±~10 pts near any decision-relevant rate**. To seat a threshold
  on it you need within-target **n ≈ 75 (SD≈5 pts)** to **≈200 (SD≈3 pts)**. The
  current audience puts far too few agents in the within-target cell to calibrate
  a floor precisely — a concrete requirement to carry into panel design.

**The decision was independent of the headline here.** With buy-intent floored at
~0 for all five, SCALE and RETARGET are off the table by construction, so the
ITERATE call was driven entirely by the assess layer — "load-bearing within pain
is fixable" — not by the headline number. So the honest statement is **not** "the
number wobbles but the decision holds"; it is: **the study validated *pain-layer*
stability (the pain read was consistent enough to hold the bucket across 5 draws)
and showed the headline is floored for these creatives — it told us little about
how the headline behaves near a threshold.** That is the precise finding.

---

## 2. The honesty fix is visible and working

The whole v3 redesign exists because the old `would_act_within_week` conflated
buying with researching. This run shows the fix in the data:

| | old (2026-07-07, would_act) | v3 (buy-intent) |
|---|---|---|
| MB whey within-target headline | **0.684** | **0.033** (mean) |
| in-feed action mix | 85% scroll, 15% seek_info, **0% tap** | ~93% scroll, ~6% linger, 0% tap |

The old 0.68 was counting info-seekers as intenders while 85% of the same agents
scrolled straight past — the exact incoherence v3 was built to remove.
`research_first` is now reported *separately* (0.22–0.47 across the repeats), never
folded into the headline. The number got smaller because it got honest.

**One structural caveat on the headline itself:** across all ~800 agents in the
study, `buy_now` fired **zero** times — every single buy-intent signal was
`buy_at_restock` (3 total). So the buy-intent headline is, on this whole set,
carried entirely by `buy_at_restock`. That may be honest (a static protein ad
in-feed realistically produces "I'll get it next restock," not "buy right now"),
but a headline component that never fires on ~800 draws is worth stating plainly —
and worth checking against humans in #10, since if real consumers never
`buy_now`-in-feed either, the component is fine; if they do, the engine is
under-firing it.

---

## 3. The 0.75 SCALE floor — answered "no", but NOT calibrated

None of the four anchors is a SCALE candidate (all land ITERATE or REBUILD), and
buy-intent tops out at 11% — nowhere near 75%. So:

- **The floor is not spuriously cleared** — nothing gets remotely close. Good.
- **This does NOT positively calibrate 0.75.** The floor is only ever exercised
  from *below*; no creative in this set was expected to win. A genuine calibration
  point needs a SCALE-*candidate* creative we believe should scale — we do not
  have a validated one. **The deferred SCALE-anchor remains open** (a known,
  documented gap from decision-2, not closed here).

---

## 4. Anchor re-verification — a consistency check, not validation

**Frame this correctly.** These four anchors are regression fixtures from the *old*
protocol we are replacing *because it was wrong*. So bucket **agreement** is a
consistency check (does the new pipeline stay sane on known creatives), **not**
ground-truth validation — and the one flip (TWT) is not necessarily "worse" than
the three that held. Ground truth comes only from #10.

Live v3 re-runs of the four 2026-07-07 anchor creatives (this re-runs the *whole*
pipeline — target classification, reactions, decision — not just the decision
logic over frozen painmaps):

| Creative | old bucket | v3 bucket | held? |
|---|---|---|---|
| MuscleBlaze whey | ITERATE / DIRECTIONAL | ITERATE / DIRECTIONAL | ✓ |
| AI-buzzword control | ITERATE / DIRECTIONAL | ITERATE / DIRECTIONAL | ✓ |
| ProSki cereal | REBUILD / HIGH (FAILING) | REBUILD / HIGH (FAILING) | ✓ |
| The Whole Truth whey | RETARGET / DIRECTIONAL | **ITERATE / DIRECTIONAL** | ✗ |

**Why TWT flipped (principled, not noise) — two deliberate v3 changes:**
1. **Target classification re-read.** The Opus classifier now reads TWT's
   within-target as `aspirant_clean_label` (n=24), where the old anchor had
   `skeptic_lapsed_protein` (n=15). Different within-set → different decision path.
2. **Strict buy-intent kills the "champion elsewhere" signal.** The old RETARGET
   fired because an *outside* disposition (enthusiast) "would_act" at 32% while the
   within-target sat at 0 — "the creative works, for a different audience." Under
   v3 buy-intent, *no* disposition intends at a high rate, so there is no champion
   to retarget toward. The honest v3 read becomes "nobody's buying this yet, and
   the load-bearing within pain is fixable → ITERATE."

Both are direct consequences of the metric redefinition, the same family of change
as MB whey's 0.68 → 0.03. The buckets that should be stable were; the one that
moved, moved for a reason we can name.

**Two sub-findings this surfaced:**
- **Target classification was stable across the 5 MB repeats** — `within =
  [enthusiast_macros_lifter]`, denom 18–19, on every draw. A genuinely reassuring
  result: the Opus classifier (temp 0.0) did not wander run-to-run.
- **But target classification is itself a change/variance source**, and it is
  exercised on exactly one creative here (TWT), where it swapped the within-set vs
  the old protocol and flipped the bucket. It deserves its own repeat-stability
  check per creative before it is trusted as fixed.
- **Discriminant-validity flag for #10:** the AI-buzzword *control* — built to be a
  bad ad — lands the **same** MIXED / ITERATE as the real MB creative. That is
  consistent with the frozen anchor (so not a proven regression), but it means the
  headline does **not** separate a deliberately-bad ad from a real one on this
  library. Whether the *pains* separate them is the open question the human panel
  must probe.

---

## 5. A real robustness bug the study caught (this is what σ studies are for)

Repeated sampling surfaced a tail failure that the single offline runs never hit:
the L2 synthesis model occasionally emits `representative_quotes` as a bare
**string** instead of the `{round: Quote}` object the tool schema asks for.
`_build_l2_summary` assumed a dict and crashed — and because L2 fans out with
`asyncio.gather`, one bad segment killed a whole run *after* the agent money was
already spent (run 2 of the MB set, ~$1.7).

**Fixed three ways (offline suite 250 green):**
1. `_build_l2_summary` guards a non-dict `representative_quotes` → drops that
   segment's quotes with a warning, never crashes. Safe for σ: the behavioral
   distribution (the actual signal) is computed in Python from the transcripts and
   never touches these quotes.
2. The L2 fan-out in `run_service` now uses `return_exceptions=True` — one bad
   segment is recorded into `panel_health` (never silent) instead of gutting the
   run; a zero-usable-segment run still aborts loudly.
3. A deterministic unit test feeds `_build_l2_summary` a string / list / int and
   asserts it degrades, not crashes.

The crashed run was then recovered via `replay_synthesis.py` (synthesis-only, no
agent re-pay) rather than re-spent.

---

## 6. Cost

Warm render cache (persona cores are keyed on demo+disposition+chaos+category, not
the asset, so all four anchors share one cache) drove the marginal cost down:

- First run (cold cache): $3.19 incl. ~$0.73 one-time render of 29 cores + 4 contexts.
- Every subsequent run: **~$2.0, $0 render.**
- **Total study: $19.37 of the $30 budget.**

---

## 7. What this does and does not establish — and the Week-2 hook

**Establishes:** the v3 instrument runs clean at scale (100% parse across 8 runs);
the *pain layer* is stable enough to hold the decision bucket across 5 identical-
panel draws (the headline was floored and did not drive it); target classification
is stable run-to-run on the one creature tested (MB); the honesty fix is real in
the data; and — a concrete panel-design requirement — n≈19 within-target is too
small to calibrate a threshold (need n≈75–200). Anchor buckets are a consistency
check (3/4 agree, the 4th moved for a nameable reason), not validation.

**Does not establish:** that any of these numbers matches reality. Every loop here
still closes on the engine. In particular the striking finding — within-target
in-feed buy-intent of 0–11% even on the on-target creative — is either (a) the
honest truth that a static protein ad in-feed almost never produces immediate
purchase intent, or (b) the engine being too conservative. **Only the Week-2 human
panel (#10) can tell these apart.** If real gym/whey consumers, run through the
mirrored two-call protocol, also land in single-digit in-feed buy-intent, the
instrument is validated at the metric level; if they land much higher, the engine
is miscalibrated low. That comparison is now the load-bearing next step.
