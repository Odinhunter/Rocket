# Rocket — Handoff for next session

**Date:** 2026-05-16 (session 2 — first real-scale v2 e2e + flag diagnosis)
**Status:** **First v2 e2e production run completed on the boat ad — clean, $2.85 (under the $4-5 envelope), 23 min wall-clock, zero retries.** Two methodology flags fired (`single_within_target`, `homogenization_high`); diagnosis below. One display-only fix shipped to `batch_run.py` for the per-segment funnel column. The bigger methodology-layer recalibrations are deferred to after the Phase 6 breadth eval (validated by advisor — N=1 evidence is not enough to change thresholds).

Read this doc **plus** the approved plan at `~/.claude/plans/just-one-more-question-purring-nova.md` and you're calibrated.

---

## Session 2 update — 2026-05-16

### What ran

`.venv/bin/python batch_run.py … --max-concurrent 2 --yes` on `assets/boat_ad.png` against `cold_traffic_v1` (5 of 7 personal_audio dispositions, panel 60, 4-context envelope). Artifacts at `runs/demo/boat_audio/20260515_234306_seed71_boat_ad/`.

| | |
|---|---|
| Verdict | MIXED @ confidence 45 |
| Methodology flags | `single_within_target`, `homogenization_high` |
| Wall-clock | ~23 min (L1 was 829s alone at conc=2; matches the conservative-conc projection) |
| Cost | **$2.85 actual** (estimate said $3.00; handoff envelope was $4-5) |
| Calls | 120 L1 + 15 L2 + 1 L3 + 1 target_id + 1 strategist = 157, **zero retries, zero failed** |
| Render quality at production scale | Held — render-5 voice ("Fabergé egg designed by someone who'd only heard earbuds described verbally", "Nobody sends each other Boat ads; you just quietly show up with them in your ears") survived 60 agents × 4 contexts |
| Strategist bet #1 | Put paid behind `specs_skeptical_pragmatist::deliberate` (would_act 0.75, the highest in the run) despite ambiguous-target — used ambiguous-segment signal correctly |

The conc=2 ceiling held cleanly. The L2 semaphore fix from session 1 was validated at production scale (15-way fan-out across heterogeneous segment sizes 2-6).

### Flag diagnosis (full investigation in session transcript)

**`single_within_target`** — literally correct (1 within, 2 outside, 2 ambiguous). Working as designed. The `synthesis_l4.py:138-140` rule caps confidence at 50 when exactly one disposition is within, and that's what landed the 45. **Advisor explicitly flagged: do NOT relax this** — its job is to caveat verdict confidence regardless of *why* the audience composition led to single-within. Cold-traffic audience design intent is not the system's problem to absorb.

**`homogenization_high`** — `homogenization_flag_count = 11/15` against threshold `>= 2`. **This flag is calibration-mismatched to v2's segmentation.** The L2 prompt defines `tight` as "agents in this cell said roughly the same thing across contexts (model echo rather than disposition signal)". That was authored for v1's per-disposition cells of 25-40 agents spanning contexts AND demographics, where tight was rare and meant echo. v2's `disposition_chaos_band` cells hold 2-6 agents with two dimensions locked — tight is the *structural default*, not anomalous echo. The L2 model is correctly applying the definition; the definition + threshold haven't moved with the segmentation change.

Concrete example: `design_led_nothing_enthusiast × all 3 chaos bands` all scroll_past=1.00, engage=0.00. Those agents *should* converge — the anchor pins them to the Nothing/CMF ecosystem; the brown-leather Boat case is its antithesis. Tight here is signal, not echo.

**The 0.420% identical-decimal floor (4 of 5 dispositions visually identical)** — math: `baseline.convert (0.006) × _convert_multiplier(would_act=0) = 0.006 × 0.70 = 0.0042`. With cell N=2-6 and integer counts, the moment `would_act_count = 0` the multiplier collapses to a constant; every such cell lands on identical 0.420%. Bands already differ across these cells (halfwidth scales with √N) — only the central decimal looks identical, which reads as a rendering bug to a customer scanning the per-segment column.

### What shipped this session

**Display-only fix in `batch_run.py:121-135`** (the per-segment convert-rate column under `By segment (convert rate):`):
- When `seg.behavioral_distribution.would_act_within_week_count == 0`: suppress the central decimal, show `—` and the band only (which differs by N), plus a footnote.
- When > 0: show both central rate AND band (the band wasn't shown before — additive readability improvement).
- Non-destructive: no version bump, no calibration_log regime change, no upstream impact. `MULTIPLIER_TABLE_VERSION` still `heuristic_v1`.

Verified by re-rendering the boat run.json — band-only rows now show e.g. `[0.289% – 0.551%]` (N=2 impulsive) vs `[0.315% – 0.525%]` (N=4-5), preserving the N-dependent variance the advisor noted.

### Deferred to Phase 6 breadth eval (NOT safe-from-N=1)

The advisor pushed back on shipping any methodology-threshold or multiplier-table change from one ad's evidence. Specifically:

1. **Recalibrate `homogenization_high`** — strongest candidate for a real methodology fix, but validate on 2-3 more ads first to see whether the 11/15 tight pattern generalizes or is boat-ad-specific. Two routes to evaluate after breadth eval has N≥3:
   - (a) **Threshold change** — move from absolute count (`>= 2`) to a fraction (e.g. `>= 80% tight`). Simpler; doesn't touch the L2 prompt.
   - (b) **Redefine `tight` in the L2 prompt** to mean language-level repetition rather than concept-level agreement, so cells with structurally-locked dispositions don't get tagged tight when the agents converge on the *correct* answer. Requires re-running the vividness-gate-equivalent for L2 to validate; bumps the L2 prompt version.
2. **Observe `single_within_target` confidence-ceiling interaction** during the breadth eval — does the 50-ceiling + homog-penalty combination consistently undershoot warranted confidence, or only on cold-traffic-style wide audiences? **Do not weaken the flag**; only observe whether the *combination* over-penalizes.
3. **Multiplier table changes** for the floor compression are not on the table from N=1 evidence — would require `MULTIPLIER_TABLE_VERSION` bump and segregates the calibration_log's regime filtering. Display-only fix above handles the customer-facing readability; the underlying floor is real signal ("no would-act in this segment = won't buy"), correctly identified by the strategist.

### Working tree state

`batch_run.py` is the only file changed this session (the display fix at lines 121-135). Everything else from the session-1 v2 build is still uncommitted in the same shape as the prior handoff. The boat run artifacts at `runs/demo/boat_audio/20260515_234306_seed71_boat_ad/` are untracked but on disk. The run log is at `runs/_boat_v2_e2e_20260515_234306.log` (per the `tee` in the kickoff command).

---

## What still needs the user (NOT incomplete Claude work)

1. ~~Decide whether to run the scaffolded v2 e2e~~ — **done 2026-05-16, see Session 2 update above.** Cost was $2.85, verdict MIXED@45, flags diagnosed.
2. **Phase 6 breadth eval** — running real test ads (boat, cadbury, cmf, patanjali, …) through v2 vs v1 and designating which are "stable" cases. Needs hand-mapped libraries for the other 3 categories too (chocolate, coffee, wellness — only `personal_audio` is scaffolded). ~$10. **Now also gathers evidence for the deferred methodology-layer recalibrations (see Session 2 update).**
3. **Phase 6 cutover** — flipping `PROTOCOL_VERSION` to `rocket-2.0.0` and deleting v1 + `archetypes/`. Destructive, last step, gated on the breadth eval passing AND your explicit OK. **Do not do this autonomously.**

Everything else is built and tested.

---

## Where every phase stands

| Phase | What | Tests | Status |
|---|---|---|---|
| 0 | Schema lock — `vectors.py` (4 axes), `artifact_pack.py`, `entities.py`; additive extensions to `schema.py`, `synthesis_types.py`, `config.py` | 4 offline | ✅ |
| 1 | Render engine + 4 hand-curated artifact packs (coffee, chocolate, personal_audio, wellness) | 2 offline + API smoke + **vividness gate rated 7/7** | ✅ |
| 2 | Population construction — `panel.py`, deterministic stratified allocation, chaos-distribution matching, marginal coverage | 1 offline (10 sub-tests) | ✅ |
| 3 | Agent runtime + R7 behavioral signal — `runtime_v2.py`; caching invariant holds (re-measured floor **1677 tokens**, exact pair-match) | offline R7 parser + API smoke + caching | ✅ |
| 4 | Synthesis + L3.5 projection — `synthesis_{l2,l3,l4}_v2.py` + `projection_l35.py` (`heuristic_v1` multiplier table, deterministic Python) | 3 offline + full-chain API smoke | ✅ |
| 5 | Two-phase run + entity model — `run_service_v2.py` (`prepare → commit`), `credits.py`, dispatcher in `run_service.py`, v2 `batch_run.py` CLI | offline credit-state + **full e2e API smoke** | ✅ |
| 6 | E2E validation + cutover | breadth eval + cutover **PENDING — needs user** | ⏳ |
| 7 | Calibration scaffolding — `calibration_log.py`, wired into `run_service_v2.commit()` | offline | ✅ |

---

## Locked design decisions (don't relitigate)

User-decided via `AskUserQuestion` during planning:

- **8-dimension disposition vector:** `category_relationship`, `brand_stance`, `price_orientation`, `decision_driver`, `category_involvement`, `prior_experience_valence`, `channel_behavior`, `life_stage`.
- **4-dimension chaos vector:** `decision_velocity`, `suggestibility`, `consistency`, `risk_tolerance`. Run carries a *distribution* over named chaos profiles.
- **L2 segment granularity = `disposition_chaos_band` by default** — ~3× the L2 fan-out vs v1, ~20-30% per-run cost increase, the dominant lever. This is what gives the funnel projection per-chaos-band teeth.
- **Ship `heuristic_v1` with bands** — funnel rates are multipliers on the customer's own baseline, always shown with confidence bands, `basis` field literally `"heuristic_v1"`. Strawman multiplier table is locked in `agent/projection_l35.py`.
- **Customization surface:** default screen = 4 demographics + audience picker + category default; advanced toggle exposes context envelope + chaos distribution + panel sizing.
- **On-the-spot dispositions:** render-now, marked `provisional`, team reviews async. The `provisional_disposition_present` methodology flag is auto-added.

Claude-decided (advisor-blessed) during build, user implicitly accepted via continued progress:

- **Parallel-modules migration**, dispatch on `protocol_version`. v1 is untouched until the Phase 6 cutover commit.
- **`NamedDisposition.anchor`** — a Phase-0 re-open. The vividness gate's first run revealed that the abstract vector captures *stance* (loyalist, devotee) but not the *object* of that stance — "loyal to filter coffee" and "loyal to a d2c roaster" were the same vector. The anchor (free-text concrete pointer into the pack) pins the object as a hard constraint. Optional; 5 of 7 personal_audio dispositions need it, the v1 coffee gate showed 2 of 7 needed it. **Without this, the gate would have failed.**
- **R7 as a parsed JSON line inside Reflection** (Call B), not a separate API call — keeps the bundled-call + caching pattern intact.
- **The deterministic-Python pattern (L3 quote pooling, confidence signals, behavioral distributions) extended, never moved to the model** — locked architectural commitment.
- **L2 fan-out semaphore-bounded at `max_concurrent_agents`** — fixed late in the session (see "Bugs caught & fixed" below). Without this, the v2 path would 529-cascade on the 30K ITPM tier with any non-trivial segment count.

User-requested sharpening after the vividness gate passed:

- **`render-5`:** niche enthusiast communities (subreddits, hobbyist forums) are gated to `high`/`obsessive` `category_involvement` only. Low/medium personas may be passively aware as a contrast marker but never active members. Generalises across categories.

---

## What is on disk right now

### Scaffolded `personal_audio` v2 starter (verified offline, ready to run)

**Entities** at `runs/demo/boat_audio/entities/`:
- `account.json` — Account `demo`
- `brand_profile.json` — BrandProfile `boat_audio`, bound to `personal_audio`
- `library.json` — DispositionLibrary `personal_audio_lib_v1` with **7 hand-mapped NamedDispositions** (all 7 v1 `urban_indian_male_22_30 × personal_audio` translated to 8-dim vectors, each carrying an `anchor`):

| Label | Vector spine | Anchor pin |
|---|---|---|
| brand_loyal_boat_user | loyalist · habit · high | ₹1k-2.5k Airdopes line |
| spec_led_upgrader | neutral · function · obsessive | the spec sheet itself |
| premium_audio_aspirant | skeptical · identity · high | AirPods aspiration gap |
| design_led_nothing_enthusiast | loyalist · identity · high | Nothing/CMF design ecosystem |
| replacement_buyer | neutral · function · low | urgent unplanned replacement |
| specs_skeptical_pragmatist | skeptical · function · medium | service & the return-window |
| wired_audio_purist | neutral · function · low (occasional) | TWS as throwaway utility |

- `audiences/cold_traffic_v1.json` — a SavedAudience using 5 of the 7 dispositions (drops urgent replacement_buyer + barely-in-category wired_audio_purist), panel_size 60, 4-context envelope, the pack's default chaos mix (20/45/35).

**Standalone JSONs** for the CLI at `specs/`:
- `specs/personal_audio_cold_traffic.json` — the AudienceSpec to pass via `--audience-spec`.
- `specs/personal_audio_baseline.json` — sample baseline funnel (conservative D2C-on-Meta placeholders; replace with real account numbers when available).

**The scaffold script** at `scripts/scaffold_personal_audio.py` is idempotent — re-running it overwrites cleanly. Use it as the template for scaffolding the other 3 categories.

### The vividness gate artifact

At `runs/_vividness_gate/`:
- `comparison.md` — the 7 blind pairs from the last gate run (on `render-5`).
- `key.json` — the un-blinding key.
- The official rating (yours): **7/7 on every axis** — v1 vs v2 on render-4 — see "Decisions journal" below.

---

## The ONE command to run a v2 read on the boat ad

```bash
.venv/bin/python batch_run.py \
    --asset assets/boat_ad.png \
    --audience-spec specs/personal_audio_cold_traffic.json \
    --baseline-funnel specs/personal_audio_baseline.json \
    --category personal_audio \
    --account demo --brand-profile boat_audio \
    --library-id personal_audio_lib_v1 --audience-id cold_traffic_v1
```

Without `--yes`, this stops at the confirmation surface (inferred target, resolved audience, cost estimate ~$4-5) before debiting the credit. Add `--yes` to auto-commit. Wall-clock ~10-14 min on the 30K ITPM tier (60 agents × 2 L1 calls at conc 4 + 15 sequential persona-core renders in `prepare()` + 15 L2 segments at conc 4 + L3 + L4). Long but safe.

To use **all 7** dispositions or a larger panel, edit `specs/personal_audio_cold_traffic.json` directly (`disposition_labels`, `panel_size`). Cap is 7 per run, 200 agents per panel.

---

## Test status

**14 offline test files, all green** under `.venv/bin/python`:

```
test_vectors_roundtrip          test_panel
test_artifact_pack_schema       test_runtime_v2_r7_parse
test_entities_roundtrip         test_l2_v2_behavioral_distribution
test_schema_roundtrip           test_l35_projection
test_run_config                 test_l35_monotonicity
test_render_packs_load          test_two_phase_state
test_render_cache               test_calibration_log
```

To run them all:

```bash
for t in test_vectors_roundtrip test_artifact_pack_schema test_entities_roundtrip \
         test_schema_roundtrip test_run_config test_render_packs_load \
         test_render_cache test_panel test_runtime_v2_r7_parse \
         test_l2_v2_behavioral_distribution test_l35_projection \
         test_l35_monotonicity test_two_phase_state test_calibration_log; do
  .venv/bin/python tests/$t.py >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"
done
```

**API smoke tests (4) — all passed during the session:**
- `test_render_smoke.py` — render engine produces vivid, artifact-grounded prose; cache hits.
- `test_runtime_v2_smoke.py` — R1-R7 emitted, R7 parsed, caching invariant (floor 1677 tokens, exact pair-match), idempotent resume.
- `test_synthesis_v2_smoke.py` — full L2→L3→L3.5→L4 chain produces a validated Report with `bet_ranking` + `funnel_projection`.
- `test_run_service_v2_minimal.py` — full prepare→commit e2e, twice (direct + via dispatcher); credit debited exactly once; re-commit didn't double-debit. **Note:** used `segment_granularity="disposition"` (only 2 L2 calls), so it did NOT exercise the 15-way L2 fan-out — that's why the L2 unbounded-gather bug survived to the user's question (see below).

---

## Bugs caught & fixed this session

1. **`count_pack_artifacts_used` too strict** — required full brand-name match, so "Nescafe" didn't credit "Nescafe Classic". Relaxed to also match first-word tokens for multi-word brands. (`agent/render.py`)
2. **Render engine emitted a proper name** ("Arjun") — added a rule to `_PERSONA_SYSTEM` that the persona must be referred to as he/she/they, not given a name. (`render-2`)
3. **Context render assumed a gender** ("She's…" with a male persona) — added a rule that context is composed onto any persona and must use "they." (`render-2`)
4. **Vividness-gate first pass homogenized 5 of 7 dispositions onto the same "third-wave cafe" persona** — the render engine was treating the artifact pack as a script. Rewrote `_PERSONA_SYSTEM` to make the disposition vector the SPINE and the pack a palette; added explicit instructions to pick the matching slice. (`render-3`)
5. **Taxonomy gap surfaced on `filter_coffee_loyalist`** — abstract vector couldn't distinguish "loyal to filter coffee" from "loyal to Blue Tokai." Phase-0 re-open: added `NamedDisposition.anchor` (optional concrete pointer). Render-4 then cleared the gate 7/7. (`render-4`)
6. **r/coffee leaked to low/medium-involvement personas** — your feedback after the official rating. Added a render-prompt rule gating niche enthusiast communities to high/obsessive involvement. (`render-5`)
7. **L2 fan-out was unbounded** — `_commit_async` fired all 15 segment calls via `asyncio.gather` with no semaphore. On the 30K ITPM tier this would have caused 529 cascades — exactly the failure class `known_issues_pipeline.md` flagged for v1's conc=20. **Now semaphore-bounded at `max_concurrent_agents`.** The user caught this with a single targeted question.

---

## Decisions journal (in order, with attribution)

1. **Build v2; treat 1.3.0 as throwaway** — user, explicit.
2. **Skip per-run cost analysis until the design is locked** — user, in plan mode.
3. **Disposition taxonomy: 8 dimensions** — user, via AskUserQuestion preview (chose "Richer 8-dimension" over the recommended 6).
4. **Chaos taxonomy: 4-dimension vector** — user, via AskUserQuestion.
5. **L2 segment granularity: per-(disposition × chaos-band)** — user, via AskUserQuestion (knowingly accepted ~20-30% cost lift for per-chaos-band funnel signal).
6. **ROI numbers: ship `heuristic_v1` with bands** — user, via AskUserQuestion preview of the strawman multiplier table.
7. **Customization surface: default + advanced toggle** — user, via AskUserQuestion.
8. **On-the-spot dispositions: render now, mark provisional** — user, via AskUserQuestion.
9. **Plan approved via ExitPlanMode.**
10. **`NamedDisposition.anchor`** — Claude+advisor, after the vividness gate's first pass exposed a real taxonomy gap (`filter_coffee_loyalist` rendered as a third-wave bean loyalist). User implicitly accepted via continued progress and a 7/7 rating on render-4.
11. **Vividness gate officially rated 7/7 on every axis** — user, blind rating: `1: B,B,B; 2: A,A,A; 3: B,B,B; 4: A,A,A; 5: A,A,A; 6: A,A,A; 7: B,B,B` against `runs/_vividness_gate/key.json`. The make-or-break gate cleared decisively.
12. **`render-5`: niche-community involvement gating** — user, request after the rating. Verified no over-correction (obsessive enthusiast still actively in /r/coffee; high-involvement cafe-loyalist now "passively aware" with a memorable "mirror" line; medium/low excluded).
13. **L2 semaphore fix** — Claude, in response to user's rate-limit question. The minimal e2e test passed but used `disposition` granularity, so the 15-way fan-out had never been exercised.
14. **Personal_audio scaffold built** — Claude, on user request. 7 dispositions hand-mapped, library + audience + standalone JSONs on disk. Offline-verified end-to-end (loads, resolves, builds a 60-agent panel with all dispositions covered and chaos mix matched).

---

## Pitfalls / what NOT to do

- **Use `.venv/bin/python`** — system `python3` lacks `anthropic`. Every test command in this doc assumes `.venv`.
- **Don't do the Phase 6 cutover** (flip `PROTOCOL_VERSION` to `rocket-2.0.0`, delete v1 modules, delete `archetypes/`) without breadth eval passing AND explicit user OK. The plan calls this out as the LAST step.
- **Don't re-render the vividness gate** unless making a render-prompt change you want re-validated. The gate passed 7/7 on `render-4`; `render-5` was verified offline (no over-correction). Re-running the gate would be ~$0.03 and require fresh blind rating.
- **Don't remove the L2 semaphore** in `_commit_async` — that bug bites at any meaningful segment count on the 30K ITPM tier.
- **Don't raise `max_concurrent_agents`** without confirming the user's actual Anthropic tier. The 30K tier was the cause of v1's 529 cascades; the default 4 is the v1-proven-safe envelope. If the user has bumped tiers, raise via `--max-concurrent` (CLI flag) — don't change the default.
- **Don't change the L3.5 multiplier table** without bumping `MULTIPLIER_TABLE_VERSION` — the calibration log stamps every prediction with this version so a future fit can filter to one regime.
- **Don't propose moving the deterministic-Python computations (quote pooling, confidence signals, behavioral distributions) into the model** — locked architectural commitment.
- **Don't commit work without explicit user request.** None of this session's changes are committed; the working tree has substantial uncommitted work.
- **Don't try to drive the breadth eval without per-brand disposition libraries** — only `personal_audio` is scaffolded. The other 3 categories (coffee, chocolate, wellness) need `scaffold_<category>.py` analogues (the script is the template; do the hand-mapping work the same way).
- **Don't change `RENDER_PROMPT_VERSION` casually** — bumping it invalidates the entire brand-level render cache. If you change a render prompt, bump it (the cache key requires it for correctness); if you don't, don't (you'd just re-pay).

---

## Files touched this session (complete catalogue)

**New v2 modules in `agent/`:**
- `vectors.py`, `artifact_pack.py`, `entities.py`, `render.py`, `panel.py`
- `runtime_v2.py`, `synthesis_l2_v2.py`, `synthesis_l3_v2.py`, `projection_l35.py`, `synthesis_l4_v2.py`
- `run_service_v2.py`, `credits.py`, `calibration_log.py`

**Edited in-place, additive only:**
- `agent/schema.py` — `BehavioralSignal`, `BehavioralSignalDistribution`, `FunnelRates`, `SegmentProjection`, `FunnelProjection`, Report+`bet_ranking`/`funnel_projection`/`provisional_dispositions`, AgentTranscript+`behavioral_signal`, validate_report extensions, `provisional_disposition_present` methodology flag.
- `agent/synthesis_types.py` — L2Summary+`segment_label`/`behavioral_distribution`, L3Summary+population/segment behavioral distributions.
- `agent/config.py` — RunConfig+`audience_spec`/`segment_granularity`/`baseline_funnel`/`library_id`/`audience_id`, DEFAULT_MODEL_VERSIONS+`"render"`.
- `agent/run_service.py` — dispatcher branch routing to RunServiceV2 on protocol_version == "rocket-2.0.0" or audience_spec set.
- `batch_run.py` — full v2 CLI path (`--audience-spec`, `--baseline-funnel`, `--segment-granularity`, `--library-id`, `--audience-id`, `--yes`); v1 path preserved.
- `replay_synthesis.py` — v2 branch (dispatches on `panel.json`).

**New `packs/` directory:**
- `__init__.py`, `coffee.py`, `chocolate.py`, `personal_audio.py`, `wellness.py`

**New `specs/` directory:**
- `personal_audio_cold_traffic.json`, `personal_audio_baseline.json`

**New `scripts/`:**
- `scaffold_personal_audio.py`

**New tests in `tests/`:**
- `test_vectors_roundtrip.py`, `test_artifact_pack_schema.py`, `test_entities_roundtrip.py` (extended `test_schema_roundtrip.py`)
- `test_render_packs_load.py`, `test_render_cache.py`, `test_render_smoke.py`, `test_render_vividness_gate.py`
- `test_panel.py`
- `test_runtime_v2_r7_parse.py`, `test_runtime_v2_smoke.py`
- `test_l2_v2_behavioral_distribution.py`, `test_l35_projection.py`, `test_l35_monotonicity.py`, `test_synthesis_v2_smoke.py`
- `test_two_phase_state.py`, `test_run_service_v2_minimal.py`
- `test_calibration_log.py`

**v1 files untouched** until the Phase 6 cutover commit: `agent/prompt.py`, `agent/runtime.py`, `agent/synthesis_{l2,l3,l4}.py`, the v1 path in `run_service.py`, `archetypes/*.py`, all v1 tests.

---

## Pickup options for the next session

If the user opens with **"let's continue"** the most natural picks are, in order:

1. **Scaffold the other 3 categories** (`coffee`, `chocolate`, `wellness`) — use `scripts/scaffold_personal_audio.py` as the template, hand-translate v1 dispositions for those categories into 8-dim vectors with anchors. The other 3 categories' artifact packs are already in `packs/`. This is the prerequisite for the breadth eval; without per-brand libraries for the other categories, the breadth eval can't run.
2. **Drive the Phase 6 breadth eval** — once at least 2-3 categories are scaffolded, run v2 + v1 on the existing test ads (`assets/boat_ad.png`, `cadbury_ad.png`, `bru_ad.png`, etc.) and tabulate verdict-bucket agreement on user-designated "stable" cases. Use this to (a) check verdict stability vs v1 and (b) gather the multi-ad evidence needed to decide between the two `homogenization_high` recalibration routes (see Session 2 update above). ~$10.
3. **Get the user's real baseline funnel numbers** for at least one Brand Profile, so L3.5 anchors against real account history rather than the conservative placeholders in `specs/personal_audio_baseline.json`. The boat run used the placeholders; convert rates are directionally honest but their absolute level inherits whatever the placeholder said.
4. **Re-run the boat ad** with all 7 personal_audio dispositions (vs the 5 in `cold_traffic_v1`) to see whether broadening the within-target set shifts the single_within_target dynamic. Cheap (~$4). Would help disambiguate whether the flag is firing on legitimate signal or on audience design choice — useful evidence for the deferred methodology-layer decisions.

If the user opens with **"is v2 ready to ship?"** — flag that (a) breadth eval hasn't been run, (b) only 1 of 4 categories has a hand-mapped library, (c) the L4 prompt change between v1 and v2 (adding `bet_ranking`, the new headline) is the kind of customer-facing change that benefits from at least one real v1→v2 comparison before the cutover.

If the user opens with **"cut over to v2"** — refuse until the breadth eval has passed. The cutover is destructive (deletes v1 modules + `archetypes/`); the plan explicitly says it's the LAST step.

---

## Open methodology questions (carried)

- **Multi-audience Brand Profile** — same question from prior handoffs. v2 makes this easier (an Account can have multiple Brand Profiles, a Brand Profile can have multiple SavedAudiences), but the architectural commitment is "1 credit = 1 Read" and a multi-audience test = multiple Reads = multiple credits. Not blocking; carries forward.
- **Render cache scope and lifecycle** — currently cached at `runs/<account>/<brand>/library_renders/`. If a `NamedDisposition` is edited in the library (vector or anchor changed), the cache key (`persona_core_hash`) changes automatically so the old render becomes orphaned. No garbage collection of orphan cache files yet; trivial future task.
- **What changes when the customer's baseline funnel is updated** — L3.5 should re-project against the new baseline, but the cached run.json `report.funnel_projection` is frozen at write time. A "re-project" CLI mode (similar to `replay_synthesis.py` but for L3.5 only) would be cheap and useful.
- **prepare() render warming is sequential** — safe but ~2-3 min for 15 cores. A future optimisation: parallelise inside the same `max_concurrent_agents` semaphore. Not done; explicitly safe-but-slow.

---

End of handoff. The v2 architecture is built, the vividness gate is officially cleared, the personal_audio scaffold is ready to run. Next session's immediate decision is whether to fire the first real-scale v2 e2e run, or build out scaffolds for the remaining categories first.
