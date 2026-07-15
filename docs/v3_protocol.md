# Rocket v3 — Reaction & Decision Protocol Spec (Week-1 frozen contract)

**Version marker:** `rocket-3.0.0-dev`  ·  **Date:** 2026-07-14  ·  **Status:** FROZEN for Week-1 implementation (Tasks W1·A1–A8, E1–E2)
**Supersedes:** the v2.4 reaction protocol (`rocket-2.4.0`) — the R1–R7 single-emission-in-reflection design.
**Provenance:** the external architecture review + `REVIEW_DOSSIER.md` + `ARCHITECTURE.md` §7; this doc is Task **W1·0** (design-first) and is the blueprint every Week-1 code task is built to.

> **Why this doc exists.** We are redefining the single signal the whole engine reads
> (the "would they act" number) and where in the encounter it is captured. Almost every
> downstream layer depends on it. This spec locks the contract *once*, so implementation
> never builds on a half-changed surface and never needs re-work. It was written after
> reading the current code end-to-end and pressure-tested with the advisor; five
> cross-feature interactions ("Catches" below) are designed out here, not deferred.

---

## 0. Scope — what this doc freezes vs. defers

**FROZEN (Week 1 builds exactly to this):**
- the two-call reaction structure (Call A Encounter / Call B Reflection) — §2
- the output **signal schema**: the `action` enum, the `next_step` enum, the `BehavioralSignal`/`BehavioralSignalDistribution` shapes — §3
- the per-purpose **headline-metric mapping** and the buy-vs-research split — §4
- the **purchase-cycle** model + its reporting contract — §5
- the **coherence-guard** trigger shape and its mechanism — §6
- the **SCALE** gate change — §7
- the **panel-design-warning** seam — §8
- the **voice-anchor** contract (render-6 structure) — §9
- the **version scheme**, including the Week-3 arm markers — §10

**PROVISIONAL (documented best-guesses, fail-conservative, recalibrated by anchor/σ runs — same posture as the per-purpose floors):** the cycle-mix default (§5), the coherence-guard threshold (§6), the assess pain-count guidance wording (§7), the exact voice-anchor wording (§9).

**DEFERRED to Week 3+ (explicitly not this week):** the exact reaction *prompt wording* (Week-3 A/B arms vary voice/wording/two-pass — never the signal shape), the two-pass protocol, funnel fitting, informer/retain validation. See §11.

---

## 1. The problem being fixed (one paragraph)

The v2.4 headline number, `would_act_within_week`, is (a) **semantically undefined** — the agent is never told what "act" means, so each persona invents it (one counts "I'd Google the price," another "I'd buy"); (b) **emitted in the wrong place** — it, and the in-feed `action`, are produced in the Reflection call framed *"a day or two later,"* although `scroll_past`/`tap_cta`/`linger` are things you do *in the feed, in the moment*; and (c) it conditions the action token on six sections of System-2 self-analysis — the same replay mechanism documented in the `brand_recall` known-limitation. v3 fixes all three at the source: the **in-feed action is captured at the encounter (Call A)**, and a **defined follow-through intent (`next_step`)** is captured in reflection (Call B). This also fixes the register artifact at its structural root (`ARCHITECTURE.md` §7) — the action is no longer the product of maximal deliberation.

---

## 2. The v3 two-call reaction protocol (frozen surface)

The panel stays **purpose-blind** (the persona never learns the declared job). Two calls, sharing the cached persona-core + image prefix exactly as today.

### 2.1 Call A — Encounter (System-1, the glance)
Sections R1–R3 (unchanged in spirit — 1–2 plain sentences each), **then a terminal action line**. The action is emitted *here*, at the encounter, conditioned only on the immediate impression.

```
R1 GUT · R2 COMPREHENSION · R3 EMOTION        (1–2 plain sentences each)
ACTION: emit exactly ONE line of JSON and nothing after it:
{"action": "<scroll_past|linger|tap_cta|save|share>", "reasoning": "<one short in-character sentence, anchored to the creative>"}
```

**`action` enum (in-feed behaviour — what the thumb does in ~1–2s):**

| action | meaning |
|---|---|
| `scroll_past` | kept scrolling; the ad did not stop them |
| `linger` | stopped and looked (no tap) |
| `tap_cta` | tapped the ad / CTA to go through |
| `save` | bookmarked / saved for later |
| `share` | sent it to someone / posted it |

> **`seek_info` is REMOVED from the action enum.** It conflated two different things: an in-feed "tap to learn more" (which *is* `tap_cta`) and a later "I'll look it up" (which is a follow-through — now `next_step = research_first`). Splitting them is strictly more information and is the crux of the reviewer's fix (Record A vs Record B disambiguate cleanly). See Catch 5 (§12) — every hard-coded `seek_info` reference must be found and migrated, because a stale string literal matches nothing *silently*.

### 2.2 Call B — Reflection (follow-through, "a day or two later")
Sections R4–R6 (unchanged), then **[conditional probes]**, then a terminal `next_step` line. Reflection is where a *considered* follow-through judgement belongs — so conditioning it on R4–R6 is correct (unlike the action, which must not be).

```
R4 STICKINESS · R5 SOCIAL · R6 FRICTION       (1–2 plain sentences each)
[R8 NEW-TO-YOU]   — only if the purpose scores novelty (informer)
[R9 BRAND CHECK]  — only if the purpose scores brand_attribution (brand-building)
NEXT_STEP: emit exactly ONE line of JSON and nothing after it:
{"next_step": "<buy_now|buy_at_restock|research_first|mention_to_someone|nothing>", "reasoning": "<one short in-character sentence>"[, "novelty": <bool>][, "brand_recall": "<confident|unsure|none>"]}
```

**`next_step` enum (defined follow-through intent):**

| next_step | meaning (told to the agent, plainly) |
|---|---|
| `buy_now` | would buy / order it right away |
| `buy_at_restock` | would buy it when they next need/restock (the reorder path — deliberately distinct from `buy_now`) |
| `research_first` | would look it up / compare before deciding (interest, not a commitment) |
| `mention_to_someone` | wouldn't buy but would tell / recommend to someone |
| `nothing` | would do nothing further |

**Conditional-probe rule (unchanged from v2.4 P8, and re-affirmed):** a probe is asked **only** on the purpose whose metric reads it (`novelty`→informer, `brand_recall`→brand-building). The would-act/action jobs (direct-sell, cold-hook, retain) get the probe-free reflection. This is why v2.4's always-on probes contaminated intent (68→26). The conditional rule is preserved; the *base* wording changes for v3 (next_step), so the old byte-identity guard is retired and a new one added (§10, §12).

### 2.3 Frozen vs. provisional inside the protocol
The **JSON output shape and the two-call structure are the frozen surface.** The exact *prose wording* of R1–R6 and the section labels are **provisional** — the Week-3 A/B varies wording, voice anchors, and (as an escalation only) a two-pass split. **No arm may change the signal shape**, because that shape is also what the Week-2 human instrument mirrors (§11).

### 2.4 Replay & blindness rules
- Call B replays Call A's assistant turn (the persona's own R1–R3 + action) — this is **intentional and benign**: `next_step` is a follow-on intent that legitimately builds on "I tapped / I scrolled." It does **not** reveal the ad's purpose, so blindness holds.
- **Protocol design rule (codify — the E4 principle):** never let a *memory* or *attribution* probe read the persona's own prior words (that is the `brand_recall` degeneracy). `next_step` is exempt because it is a stated intent, not a claimed recollection — it is *supposed* to be informed by the encounter.

---

## 3. The signal schema (v3) — `agent/schema.py`

Clean, version-stamped break. **No back-compat shim.** Pre-v3 raw signals will not deserialize — this is an accepted, stated consequence (we never compare *behaviour* across the version boundary; the new `PROTOCOL_VERSION` marks the discontinuity). See §12 for the fixture/test split.

```python
BEHAVIORAL_ACTION = Literal["scroll_past", "linger", "tap_cta", "save", "share"]   # seek_info removed
NEXT_STEP        = Literal["buy_now", "buy_at_restock", "research_first", "mention_to_someone", "nothing"]

@dataclass
class BehavioralSignal:
    action: BEHAVIORAL_ACTION          # from Call A (the encounter)
    action_reasoning: str              # Call A reasoning
    next_step: NEXT_STEP               # from Call B (reflection)
    next_step_reasoning: str           # Call B reasoning
    # would_act_within_week: REMOVED
```

- `BehavioralSignalDistribution`: keep `counts` (action histogram); **replace `would_act_within_week_count` with `next_step_counts: dict[str,int]`** (a histogram over the next_step enum). Buy-intent rate, research rate, etc. are pure Python counts derived from `next_step_counts` — the "distributions are Python, not the model" invariant holds.
- `ProbeSignal`: unchanged shape; **fix the stale docstring** ("always-on" → conditional).
- **Parsing** (`agent/runtime.py`): split `parse_r7_signal` into `parse_encounter_action(encoding_text)` (Call A terminal JSON) and `parse_next_step(reflection_text)` (Call B terminal JSON); assemble `BehavioralSignal` from both. Each parser **validates against its enum and fails loud** on an unknown string (the backstop for Catch 5). Probe parsing unchanged (reads the Call B terminal JSON).

---

## 4. Headline metric mapping + the buy/research split (A3) — `agent/decision.py`, `agent/purpose.py`

Definitions used everywhere: **buy-intent** = `next_step ∈ {buy_now, buy_at_restock}`; **research** = `next_step == research_first`; **advocacy** = `next_step == mention_to_someone`.

| purpose | headline "win" predicate | companion read (reported, never folded into the headline) |
|---|---|---|
| `direct_sell` | within-target **buy-intent** rate | **research rate** (the honest "would look it up" number) |
| `cold_hook` | `action != scroll_past` over the cold frame (stop set = {linger,tap_cta,save,share}) | buy-intent rate |
| `retain_winback` | **buy-intent** among existing-customer stances (`buy_at_restock` is the core reorder signal) | research rate |
| `brand_building` | resonance (`action != scroll_past`) **×** attribution (`brand_recall == confident`) — *unchanged; attribution is the known-limitation* | resonance-only rate |
| `awareness_informer` | novelty-breadth across dispositions (R8) — *unchanged* | — |

**A3 — the split is non-negotiable honesty:** the headline for a buy job is buy-intent **only**; `research_first` is reported as its own labelled number and never inflates the headline. This kills the "63% = buyers + info-seekers" error at the source (`decision.py within_target_action_rate` is re-keyed off `next_step`; `Decision` gains a companion-rate field for the research number).

`agent/purpose.py`: update each preset's `headline_metric` key + `metric_label` (e.g. direct-sell "would act this week" → "would buy"); bump `PURPOSE_VERSION → purpose-2`. Fix the stale "all probes asked on every run" docstring.

---

## 5. Purchase-cycle position (A4) — with Catch 2 designed out

**The model.** A per-agent sampled state on `PanelAgent`: `cycle_position ∈ {just_bought, mid_cycle, running_low}`.
- Sampled deterministically from the run seed at panel-build (like the chaos band).
- **Excluded** from `persona_core_hash` and from `segment_key` — so it does **not** fragment the render cache and does **not** explode the L2 fan-out.
- Rendered as a **deterministic templated sentence** appended to the **uncached** `context_block` in `runtime.py` (NOT via the model-rendered `render_context`, NOT inside `ContextVector`). It is a factual state line, so no model call and no cache impact. Example: *"Where they are in their <category> cycle right now: running low — nearly out, will restock soon."*
- Recorded on the agent + transcript so the decision layer can break down by it.

| state | meaning |
|---|---|
| `just_bought` | recently purchased; well-stocked; no near-term need |
| `mid_cycle` | partway through; not thinking about restocking |
| `running_low` | nearly out; will need to restock soon |

**Catch 2 — the cycle mix must not become a new "invented baseline."** A single blended headline is a weighted average over the sampled mix, and that mix swings the number by several points — comparable to `_RETARGET_GAP` (0.15) and to the σ we are about to measure. A hard-coded mix is *the same sin D4 removes from the funnel*. Therefore the reporting contract is:

1. **The by-cycle breakdown is the PRIMARY, mix-independent read** — e.g. "running-low buyers X%; mid-cycle Y%; just-bought Z%." This is the honest number.
2. **The blended headline always carries its mix assumption visibly** — "blended over an assumed 25/50/25 cycle mix."
3. **The mix is spec-declarable** (`AudienceSpec`/`RunConfig`) with a **documented provisional default** (`{just_bought: 0.25, mid_cycle: 0.50, running_low: 0.25}` — a best-guess, fail-conservative, recalibrated later; category-aware defaults are future work). Never a bare constant buried in code.

---

## 6. The coherence guard (A7) — with Catch 1 & 3 designed out

**Catch 1: A7 must not fight A4.** A4 *deliberately* creates a legitimate scroll-past reorderer — a loyalist who is running low, sees a brand they know, does **not** tap, and intends `buy_at_restock`. A naive A7 ("buy-intent + no in-feed hand-raise → penalise") would fire on exactly that coherent pattern, and — because the loosened SCALE requires HIGH trust — would suppress the SCALE we are trying to make reachable. So A7 is scoped to the incoherence that `next_step` does **not** already dissolve.

**What `next_step` already fixes structurally:** the original bug (`would_act` inflated by `seek_info`) is *gone* — `research_first` is split out of buy. So A7's residual job is narrow.

**A7 locked trigger (the residual incoherence) — refined post-implementation (advisor):** scoped to **direct-sell only** — the acquisition job whose headline IS buy-intent. (retain is existing-customer and reorders without engaging *this* ad; **cold-hook's headline is the STOP, not the buy**, so a buy-coherence guard there keys on a metric cold-hook doesn't report and could only ever *false-block* it.) Fire when `buy_now` intent is present yet **not one of those claimers actually engaged with the ad in-feed** — they all scrolled past. **"Engaged" = any NON-scroll action (`linger`/`tap_cta`/`save`/`share`)**: stopping to look *is* engagement, so *"lingered, then would buy"* is COHERENT and does not fire (an earlier draft used `{tap_cta,save,share}` and wrongly flagged linger-then-buy). Only *"scrolled past without stopping, yet would buy right now"* is the hollow signal this catches. It **cannot** fire on the A4 reorder pattern (`buy_at_restock` + scroll_past — keyed on `buy_now`, not `buy_at_restock`).
- **Trigger:** `buy_now_count > 0` **AND** `engaged_buy_now_count == 0` (every `buy_now` claimer scrolled past) within the direct-sell frame.

**Catch 3: mechanism.** A7 sets its **own methodology flag** — `intent_action_incoherent` (add to `_VALID_METHODOLOGY_FLAGS`). It does **not** launder through `trust`. `trust` keeps its single meaning: *evidence sufficiency* (§7). The SCALE branch checks the A7 flag **directly**. A7 also annotates the decision rationale and (via the flag being in `_THIN_EVIDENCE`-adjacent handling) is surfaced to the brand as a caveat.

---

## 7. SCALE reachability (A5) — `agent/decision.py`, `agent/synthesis_assess.py`

**The change.** Today branch 5 requires `load_bearing_pain is None` — i.e. **zero** within-target pains of any severity — while `assess` is told to find 5–9. SCALE is therefore structurally near-unreachable (the engine almost always says ITERATE). Fix, in two parts:

1. **Gate on no *structural* within pain, not no pain.** Branch 4 already returns REBUILD for a structural within pain, so by branch 5 any load-bearing pain is execution-severity. Branch 5 becomes:
   ```
   SCALE  ⇔  a_within >= scale_floor  AND  trust == "HIGH"  AND  NOT intent_action_incoherent
   ```
   Execution pains now **coexist** with SCALE — "scale while iterating," as real media buying does. `DECISION_VERSION → decision-3`.
2. **Give assess permission to emit few/zero pains for a working ad.** Reword the "Aim for the 5–9 pains" instruction to: surface the pains that actually move the read — *typically* 5–9 for a leaky ad, but **as few as 1–2, or none within-target, for a genuinely working one; never invent pains to hit a count.** `ASSESS_PROMPT_VERSION → assess-3`.

> **This is a deliberate policy loosening, flagged to the user — not a pure bug-fix.** It trades away a fail-conservative margin the team chose on purpose. Its safety now rests on three independent guards: the provisional floor (per-purpose), the **HIGH-trust** requirement (§ trust = ≥2 within dispositions, no thin-evidence flag), and the **A7 coherence flag** (§6). The σ study (A8) informs whether `0.75` is right; until then it fails toward ITERATE.

---

## 8. Panel-design warning (A6) — with Catch 6 designed out

**Seam (verified in code):** within-target classification comes from `target_id` (the Opus vision call, run against the creative). In `run_service`, both `build_panel` **and** `target_id` run in **Phase A — the pre-run "prepare"/confirmation surface, before the paid commit.** So within-target count is known there, but **not** at bare `build_panel`. Therefore the warning lives in the **Phase-A prepare surface**, beside the existing demographic-mismatch guard and cost estimate — deterministic, pre-paid, **non-blocking**.

**Rule:** if the panel carries **< 2 within-target dispositions**, emit an advisory: *"This panel has N within-target disposition(s); a HIGH-trust verdict — and therefore a SCALE 'ship it' — is unreachable regardless of ad quality. Add ≥2 within-target dispositions to the audience spec for a confident read."* Stamp it in `run.json`.

---

## 9. Voice at the source (C1/C3) — render-6, `agent/render.py`

**Contract (structure is frozen; wording is provisional/A-B-able):**
- **C3:** de-literarise `_PERSONA_SYSTEM` — the persona core stops being "vivid" writerly prose (the register leak sits in the *system block* of every reaction call; a user-turn "you are NOT a writer" cannot outweigh a literary identity document).
- **C1:** the persona core **must include a short "how they actually talk" block — 2–3 sample utterances** in this person's real register (clipped, plain, in-voice), as an in-context register anchor for Calls A/B. Models match a *shown* register far better than a *described* one.
- `RENDER_PROMPT_VERSION → render-6`. This changes the cached prefix, so it must land **before** the σ study (A8). Week-2 real human verbatims later become the strongest anchors (C2), but that is post-data.

---

## 10. Versioning (with Catch 4 — the arm scheme)

| constant | v2.4 | v3 Week-1 | v3 Week-3 arms | v3 final |
|---|---|---|---|---|
| `PROTOCOL_VERSION` (config.py) | `rocket-2.4.0` | `rocket-3.0.0-dev` | `rocket-3.0.0-rc1/rc2/rc3` | `rocket-3.0.0` |
| `REACTION_PROTOCOL_VERSION` (runtime.py, **new**) | — | `reaction-v3` | `reaction-v3-rc{n}` | `reaction-v3` |
| `DECISION_VERSION` | `decision-2` | `decision-3` | — | — |
| `PURPOSE_VERSION` | `purpose-1` | `purpose-2` | — | — |
| `ASSESS_PROMPT_VERSION` | `assess-2` | `assess-3` | — | — |
| `RENDER_PROMPT_VERSION` | `render-5` | `render-6` | `render-6-rc{n}` | `render-6` |

- Introduce an explicit `REACTION_PROTOCOL_VERSION` in `runtime.py` so the byte-identity guards pin the new reaction surface (there is no such constant today).
- **Every `run.json` stamps all of these** (via `run_service` — confirm during implementation). The `-rc{n}` scheme exists so the Week-3 A/B can label arms without re-zeroing the schema or the human comparison.
- **Old-run replay breaks** under the clean schema break — accepted and stated (no silent surprise).

---

## 11. The frozen surface & the Week-2 human-instrument mirror (Catch 4)

The **output schema + two-call structure (§2, §3)** is exactly what the Week-2 human session mirrors: a **~2-second exposure → pick an `action`**, then **later → a `next_step`** + the reflection questions. This apples-to-apples match is the whole point of freezing the schema now. Week-3 arms vary wording/voice/two-pass, never the signal shape — so neither the calibration nor the human comparison is re-zeroed by the arm chosen.

The Week-3 acceptance targets this protocol is judged against (reference; `v3_one_month_plan`): register ≥ 4.0; engine action-mix inside the human 95% CI per cell; dispersion ≥ ~70% of inter-human variance; **pain-overlap ≥ 2 of 3** (the existential one).

---

## 12. Ripple / impact map (the implementation checklist for W1·A1–A8, E1–E2)

Catch 5 rule for all of these: **enumerate and update every hard-coded action/next_step string** (a removed literal matches nothing *silently*); parse-time enum validation is the loud backstop.

| file | change |
|---|---|
| `agent/schema.py` | new `BEHAVIORAL_ACTION` (drop `seek_info`) + `NEXT_STEP` enums; `BehavioralSignal` (action+reasoning / next_step+reasoning, drop would_act); `BehavioralSignalDistribution` (next_step_counts); `Decision` companion-rate + `by_cycle_position` + `intent_action_incoherent` flag; `validate_report` invariants; fix ProbeSignal docstring |
| `agent/runtime.py` | Call A emits terminal action JSON; Call B emits next_step JSON; split parsers (loud-validating); new `REACTION_PROTOCOL_VERSION`; append the deterministic cycle-position line to the uncached `context_block`; sanity-check `_MAX_TOKENS=1250` doesn't truncate either call (both carry a terminal JSON now) |
| `agent/decision.py` | re-key metric off `next_step`; A3 buy/research split + companion rate; A7 coherence flag; A5 SCALE gate (`decision-3`); per-cycle breakdown; keep trust = evidence-sufficiency only |
| `agent/purpose.py` | `headline_metric`/`metric_label` per preset; `PURPOSE_VERSION → purpose-2`; docstring de-stale |
| `agent/panel.py` | `PanelAgent.cycle_position` (sampled, seeded; to_dict/from_dict; **not** in persona_core_hash/segment_key); the cycle-mix parameter (spec-declarable, provisional default) |
| `agent/config.py` | `PROTOCOL_VERSION → rocket-3.0.0-dev`; cycle-mix on `RunConfig`/spec; funnel-off-by-default (D4) |
| `agent/synthesis_assess.py` | `assess-3` pain-count permission |
| `agent/synthesis_l2.py` | E1: fix stale prompt (R2/R3 = 1–2 sentences; probes conditional; next_step not would_act); update any would_act read |
| `agent/synthesis_l3.py` | update would_act read (context only) |
| `agent/projection_l35.py` | **prime Catch-5 suspect** — reads both `would_act` AND `seek_info`; re-map to the new schema so it does not silently mis-count; keep gated OFF by default (D4) |
| `agent/run_service.py` | A6 warning in Phase-A prepare surface; confirm all version stamps land in `run.json` |
| `batch_run.py` | render the buy/research split + per-cycle breakdown; E3 "model-inferred" labels on every quote surface; F3 launch scope (direct_sell + cold_hook active; brand-building beta; informer/retain parked) |
| `tests/*` + `tests/fixtures/decision/*` | E2: retire the old reflection byte-identity guard, add Call-A + Call-B/next_step guards; **pure-scalar** decision tests just change numbers; **raw-transcript** tests + the 3 painmap fixtures need new-protocol samples (re-derive from the new semantics — do **not** preserve the old numbers) |

---

## 13. Open decisions locked here (so nothing is a silent shortcut later)

- **Removing `seek_info`** from in-feed actions (→ `research_first`): **locked.**
- **Cycle-position as a per-agent field, not a fifth axis and not inside `ContextVector`:** **locked** (an axis would explode cells; `ContextVector` is attention-state and adding a required dim breaks every existing spec).
- **A7 scoped to `buy_now`+no-hand-raise on the acquisition frame, via its own flag, SCALE checks it directly:** **locked** (resolves the A4/A7 fight and keeps `trust` single-meaning).
- **By-cycle breakdown is the primary read; blended headline shows its mix; mix is spec-declarable:** **locked** (avoids re-inventing the invented baseline).
- **A6 warning in the Phase-A prepare surface, post-`target_id`:** **locked** (within-target count is not known at `build_panel`).
- **Clean, version-stamped schema break; old-run replay breaks:** **locked & stated.**
- **Provisional, to recalibrate:** cycle-mix default, A7 threshold, per-purpose floors, assess wording, voice wording. Each fails toward the conservative decision.

*End of spec. Implementation proceeds W1·A1+A2 (schema+runtime) → A3+A7 (decision) → A5+A6 → A4 → C1+C3 → E1/E3/D4/F3 → E2 (green) → A8 (σ). The parallel Week-2-readiness track (human instrument) mirrors §2/§3/§11.*
