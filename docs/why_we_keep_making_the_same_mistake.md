# Why we keep making the same mistake — a codebase review

**2026-08-22. `$0`.** Written after the user asked why the same defects keep returning. Three
parallel audits covering every one of the repo's 10 production model call-sites and 6 human-facing
surfaces, plus the metric path end to end. **Everything below is verified against `file:line`.**

---

# THE ANSWER, IN THREE SENTENCES

1. **We have two test tiers and only one runs.** 696 free offline tests check *structure*; five paid
   smoke tests check *reality* — and **pytest collects zero test functions from any of the five.**
2. **One value does several jobs, and only the machine-facing ones are checked.** `category` is a
   module name, a cache key, an install guard **and** prose read by models and customers.
3. **When we learn a rule we write it in the memory file instead of the test suite**, so it protects
   the one case where we learned it and nothing else.

⭐⭐ **These are one disease: a fix gets applied to the INSTANCE, never to the CLASS.** That is why
the memory file reads *"measured twice"*, *"four instances of ONE defect"*, *"missed twice"*,
*"three measured cases"*. Those are not four failures. They are one failure, four times.

---

# THE EVIDENCE

## 1. The correct pattern was already here, every time

| what I "proposed" this week | where it already existed |
|---|---|
| a prose market name separate from the slug | ⭐ the demand grids have carried `market: "Indian urban food and beverage"` since `#69`, and `_grid_brief` has **always** used it instead of the slug |
| chaos as a per-exposure sampled state | ⭐ `cycle_position` — sampled per exposure, excluded from `persona_core_hash` **and** `segment_key`, spec-declarable mix, mix-independent breakdown on every surface |
| a differential test that varies one axis | ⭐ `scripts/render_persona_samples.py --old-library` — *"exactly one thing differs between the two sides"* |
| a smoke test that reads real output | ⭐ `tests/test_render_smoke.py`, `$0.01`, renders real prose |

**Four for four. I used none of them, and spent `$3.85` on a run whose defect a `$0.01` script
would have shown me.**

## 2. A prior instance of this exact class was found, named, fixed, and not swept

`agent/read_model.py:247-250`, in the codebase before this week:

> *"it is engine vocabulary, verbatim, at the top of a sentence a client reads.
> **Same bug class as the "unclassified" glance legend.**"*

⭐⭐ **The author identified the class, wrote it down in a comment, fixed the one instance, and moved
on.** Meanwhile the same class was live in seven other places, including the pre-commit screen a
customer reads **before a credit is debited** (`server/app_html.py:1109`, disposition slug rendered
with underscores intact) and the methodology block (`dashboard_html.py:1315`, **"Fnb world"**).

## 3. Two tests asserted the bug as correct output

- `tests/test_cycle_position.py:69` pinned `"recently stocked up on health wellness nutrition"`
- `tests/test_dashboard_html.py:1204` pins `"switcher results chaser" in html`

⚠⚠ **A test that ratifies a defect is a stronger blocker than no test at all** — fixing the bug
breaks the suite, so the fix looks like the regression. Confirmed empirically today: correcting the
cycle line turned the suite red on exactly that assertion.

## 4. A test guards code that has never run in production

`agent/render.py:737 compose_persona_prompt` has **zero production callers** — grep outside
`tests/` returns only its own definition. Its own docstring says *"runtime.run_agent does NOT use
this"*. The header it builds, `"WHO THIS PERSON IS"`, occurs at exactly one place in `agent/`:
inside that dead function. **No persona has ever seen it.** `tests/test_render_cache.py:303`
asserts its ordering, and passes.

## 5. Even our best seam test cannot see its own third seam

`tests/test_generation_prompt.py` exists precisely because defects lived in the seams. Its
`test_no_exemplar_is_stated_twice_in_the_whole_prompt` names three places the exemplars lived —
including *"the `occupation_hint` schema description"* — but `assembled()` joins only the system
blocks and the user turn. **The tool schema is a separate argument at the call site.** An exemplar
re-added there is invisible to the test written to catch exactly that.

## 6. Surface coverage: 17 surfaces, 8 with nothing

| tier | count | which |
|---|---|---|
| FULL assembled-output test | 5 | generation prompt, customer HTML, app screens, product pages, session export |
| one or two properties only | 4 | agent runtime *(asserts only that marketer notes are absent)*, prescribe, target_id, CLI report |
| ⚠⚠ **nothing** | **8** | **persona render · context render · L2 · L4 · assess** · lexicon ×2 · region_review |

⚠ `_L2_SYSTEM`, `_L4_SYSTEM`, `_ASSESS_SYSTEM` appear in **zero test files**. Those three prompts
write the customer's report. The L4 payload concatenates **seven modules** with no test reading the
result — and on retry it appends up to 8,000 characters of the model's own prior bad output.

## 7. And the counterfactual is missing entirely

⭐⭐⭐ **No code anywhere compares a persona's own anchor to the advertised brand at scoring time.**
`cycle_position` is consumed in exactly one place — as a *reported breakdown*. Never a filter, never
an adjustment, never an input to a verdict. **That single absence is the mechanism under the `$3.85`
run's wrong headline AND under both verdict-flipping bugs below.**

---

# ⚠⚠ THE TWO BUGS THAT CAN FLIP A CUSTOMER'S VERDICT

**F1 — a loyal customer can be crowned as "the audience the ad is really for."**
`decision.py:135-149 → :382-398 → :463-473`. `_best_champion` accepts `outside` **and** `ambiguous`
dispositions and nothing excludes existing-customer stances on a direct-sell run. A persona whose
own anchor names the advertised brand restocks at ~60% while prospects sit at 5% → the gap clears
`_RETARGET_GAP` and `_RETARGET_FLOOR` → **RETARGET replaces the true ITERATE/SCALE**, and the
customer is told *"Right ad, wrong person."* ⚠ Production data already contains such a persona:
`loyalist_kitkat_break_ritual`, whose L5 is *"Grabbed a KitKat at the kirana."* Classified `within`
instead, the same persona inflates the headline into a **false SCALE**. ⚠ **No test covers it.**

**F2 — a retention ad can be told to ship on zero measured lift.**
`decision.py:215-218`, `:557-584`. For `retain_winback`, a win is buy-intent — and
`_intent_action_incoherent` returns `False` for that purpose, **its own docstring explaining that
retain *"is existing-customer and legitimately reorders without engaging THIS ad."*** The code
documents the flaw and declines to compensate. `by_cycle_position` is attached at `:708` and no
branch reads it. Loyalists on a restock cadence → ~100% ≥ the 0.75 floor → **SCALE, "ship it."**
⚠⚠ **And `tests/test_purpose_retain.py:62-77` pins this as correct.**

**F3 — the funnel projection pools in- and out-of-target**, violating the rule this repo states in
its own source twice (*"pooling … is the mistake that has cost this project a rebuild twice"*).
Narrow ad, 19 in-target at 30% / 81 outside at 0% → pooled 5.7% → the customer is told conversion
**drops ~14%** on an ad that worked. Gated behind `--funnel`, so not live — but it is the only
surviving unsplit aggregate.

---

# WHAT I CHANGED TODAY, AND WHY THIS ONE

**The identifier-as-prose class — fixed as a class, not an instance. 731 tests green.**

| | |
|---|---|
| `CategoryArtifactPack.market_name` | the prose half. Set on **all 8 packs**; the derived `_bev` pack inherits it through `dataclasses.replace` |
| `artifact_pack.market_name_for()` | one call site for "tell a reader what market this is" |
| `render.py:500`, `:627` · `target_id.py:363` · `synthesis_l4.py:595` | now prose. `category` is machine-only |
| ⭐⭐ `runtime._cycle_line` | **the interpolation was DELETED, not fed a better value.** It reaches every agent in every run, and its template needs a mass noun — *"partway through your current Indian urban food and beverage"* is not English either. The persona's own core already names what they stock, so the noun was always redundant |
| `tests/test_cycle_position.py` | the test that **ratified the bug** now asserts the law |
| `tests/test_identifiers_never_reach_a_reader.py` | **34 tests, 3 mutation-proved** — a pack forgetting the name, a pack "fixing" it with the humanised slug, and the interpolation returning. All three caught |

⭐ **That last row is the point of the whole exercise: the law now lives in the repo instead of in a
memory file, so it is applied every time instead of when someone remembers.**

---

# ✅ CLOSED — `#78`, `#79`, `#80`. **750 tests green.**

| was | now | proved by |
|---|---|---|
| **identifier-as-prose** — `fnb_world` read to personas as *"international food and drink"* | `market_name` on all 8 packs, `market_name_for()` as the one prose call site, 4 model-facing sites routed through it. ⭐ The cycle-line interpolation **deleted, not re-valued** — a market description is not a mass noun either, and the persona's own core already names what they stock | 34 tests, 3 mutations: pack forgets the name · pack "fixes" it with the humanised slug · interpolation returns |
| ⚠⚠ **F1** — a brand's own loyalist crowned RETARGET champion, telling the customer *"Right ad, wrong person"* about people who already buy from them | existing-customer stances excluded from champion candidacy | mutation: remove the filter → the loyalist wins again |
| ⚠⚠ **F2** — retain SCALEs on reorders nobody engaged with | `_reorder_without_engagement`, keyed on the metric retain actually headlines, **and SCALE now gates on a SET of blocking flags** | 2 mutations, plus a control proving an engaged reorder still SCALEs |
| **a test asserting the bug as correct** | rewritten to assert the law | the fix turned the suite red first, which is how the bug had survived |
| **dead code with a green test** — `compose_persona_prompt`, third-person, header no persona ever saw | deleted, and the paid smoke test stopped spending money asserting it | — |
| **the label convention was runtime logic with nothing enforcing it** | `stance_of()` / `KNOWN_STANCES` / `unknown_stance_labels()` + a seam test that the generator and the decision layer still share a vocabulary | mutation: drop a stance → 2 tests fail |

⚠ **TWO HONEST NOTES.** A 4th mutation showed my first F1 fix carried a retain
opt-out that **changed no outcome** — retain already recasts the map, so the knob
could never act. **Deleted rather than kept as configuration that cannot do
anything**, and the test docstring now says what it really proves. And mid-fix I
added a guard flag that no branch read — *the exact shape of F2* — caught by the
mutation run before commit, which is why SCALE now reads the flag SET.

⭐ **One correction to the audit:** `tests/test_purpose_retain.py` does **not**
pin F2. Its agents use `tap_cta`, so they genuinely engaged; the test never
*covered* the defect rather than ratifying it. Only `test_dashboard_html.py:1204`
ratifies a defect, and it is still open below.

# ✅ CLOSED — `#81`, `#82`. **780 passed, 5 skipped.**

Items 1, 2, 3, 4, 6, 7 and 8 of the table below are done. What is worth keeping
from doing them is not the fixes — it is that **the review under-counted the
problem in four separate places**, and every one of those was found by trying to
close an item rather than by reading the code again.

| the review said | what was actually true |
|---|---|
| one test ratifies a defect (`test_dashboard_html.py:1204`) | **three** did. `test_cycle_position.py::test_cycle_line_prose` pinned the `$3.85` prose, and `test_server_runs.py:386` REQUIRED the raw underscore label on the pre-commit screen — so fixing the bug broke the suite and the fix looked like the regression |
| the smoke tier is 5 paid files nothing runs | **7** files collected zero. Two of them — `test_panel_resilience.py`, `test_l4_homog_guard.py` — say *"Offline"* in their own docstrings. They cost nothing, and they had never run. `test_panel_resilience` guards against synthesizing a confident verdict on a panel a 529 burst has gutted |
| item 7: customer screens need `display_name` | the read model was fixed in `#81`; **`server/app.py:581` was still passing the raw label** to the last screen before a credit is spent. I fixed the surfaces I had a failing test for and missed the one I did not — which is the exact behaviour this document is about, committed while writing the document about it |
| the fix is to stop the slug reaching a reader | a **live, shipped instance was still in the tree**: `packs/health_wellness_nutrition.py` opened its `behavioral_priors` with *"health_wellness_nutrition is identity-loaded and trust-fractured."* — the raw slug as the subject of a sentence every persona writer reads, in the pack behind the 50-label `hw_generated_v1` library. Found by the new preflight on its first run |

## The preflight, and why it is not a seventh advisory

`agent/preflight.py` runs at the TOP of `prepare()`, before `identify_target`
and `warm_render_cache` — the two calls in that function that cost money.

`RunPreparation` already carries six advisories, and **all six are computed
after the first model call**. A check that fires there cannot save the money it
exists to save. It also **blocks instead of warning**, which none of the six do:
those are marketer judgement calls (an off-demographic creative can be
deliberate, so `--acknowledge-...` proceeds), while a machine identifier in a
prompt is a mechanical defect nobody has ever wanted. There is no override flag.

⚠⚠ **Its precision cost three drafts, and that is the part to remember.** The
first flagged the `coffee` pack eleven times — for a single-token category the
identifier and the English word are the same string, so no defect is possible.
The second flagged `personal_audio`, whose `market_name` *is* "Indian personal
audio". The rule now uses **the pack's own authored `market_name` as the
oracle**: the underscore form is never English and is always caught; the
humanised form is caught only when it is absent from the market name.
Verified against the real matrix — **8 packs × 7 installed libraries, nothing
legitimate blocked.** A guard that cries wolf gets bypassed, and then it is not
there for the real one.

## The paid tier is skipped, never deselected

`pytest tests/` now reports **`780 passed, 5 skipped`**. `addopts = -m "not
paid"` would have hidden the five from the summary, which recreates
"looks covered, isn't" in a new form — the defect this whole review exists to
remove. The skip reason names the flag: `paid: pass --paid to run, costs real
money`.

    pytest tests/ --paid        # all five, ~$1.93

`tests/conftest.py`'s paid-engine guard is lifted for those five and **only**
when the test carries `@pytest.mark.paid` AND `--paid` was passed — either alone
keeps the guard on, so a stray marker cannot open the door by itself.
`test_run_service_minimal.py` reaches `prepare()` and `commit()` by design; under
the unmodified guard it could never have passed even with `--paid`.

## Mutation results

Thirteen mutations across the two commits. **Three found vacuous tests of mine
before they were committed**, which is the only reason to run them:

| | mutation | result |
|---|---|---|
| M3 | run header reverts to the slug | **8 passed ❌** — the parametrised list held two categories, neither of which was the fixture's. Now reads the category off the model |
| P1 | preflight moved below `identify_target` | ordering test pinned `render_persona_core` and `_warm_render`, **neither of which exists in `prepare()`**; `if at != -1` skipped both silently. Now asserts each name is PRESENT before asserting it is ordered |
| — | `load_pack` mutation leaked between tests | `load_pack(x) is load_pack(x)` — it returns a shared cached object. A test mutated it in place and the next test failed for an unrelated reason |

The other ten caught what they were aimed at: humanise reverts, an authored name
ignored, the `enthusiast` omission, the grandfathered-violation amnesty, the
`coffee`/`personal_audio` cry-wolf regressions, the slug-in-prose defect
restored, a renamed paid call, and the raw label back on the pre-commit screen.

---

# WHAT IS LEFT, IN ORDER

Items 1, 2, 3, 4, 6, 7, 8 are ✅ closed (`#81`, `#82`). **Item 5 and F3 closed 2026-08-22
in `#85` and `#84`.** What remains:

| # | change | why now |
|---|---|---|
| — | ⭐ **The prompt-side half of `#83`** | The render-seam fix repairs all 47 runs on disk, but L4 is still handed raw disposition labels. Handing it `display_name`s is the deeper fix and **needs a paid run to verify** |
| — | **`display_name` is required of the generator but absent from all 7 installed libraries** | They fall back to `stance · anchor`, which is correct and readable, so this is not urgent — but the authored name is the better surface and only new libraries will have it |
| — | ⚠ **`_choose_cells` pads over the GRID, not over the dispositions** | NEW, session 49, found while auditing the paid fixtures. When `panel_size < grid`, the marginal-coverage pass seats every disposition once and then pads **round-robin over the raw grid** — which is disposition-major, so the whole remainder lands on whichever type sorts first. ⭐ **Measured with real `build_panel` calls, 7 dispositions × 3 contexts:** `N=10 → [4,1,1,1,1,1,1]`, `N=15 → [4,4,3,1,1,1,1]`, `N=20 → [4,4,4,4,2,1,1]`. ⚠⚠ **SCOPE IS NARROW AND WAS OVERSTATED FIRST TIME:** it needs a **bundle-less library AND `panel_size < grid`**. Every generated library carries `demographic_bundles` and takes `_choose_cells_bundled` (verified: `hw_generated_v1` 50/50, `fnb_probe_v1` 8/8), and **every bundle-less spec on disk has N ≥ G**. Nothing in production reaches it today. ⚠ `test_marginal_coverage_small` asserts every disposition is PRESENT and never that seats are balanced — that is the coverage gap. **Fix: largest-remainder over dispositions, then contexts within each.** |
| — | ⚠ **`_L2_TOOL` has no `strict: true`** | Found while writing the seam tests. `scripts/generate_audience.py:634` carries it with a comment explaining why it is load-bearing (*"a non-strict schema is a request, not a contract"* — one batch emitted five types with no vector axes at all despite every field being `required`). L2's forced tool schema does not. ⚠ **NOT changed:** `strict` requires `additionalProperties: false` at every object level, and getting that wrong fails on a PAID call. It is a one-line change plus a schema sweep, and it wants a `--paid` run behind it |

### ✅ WHAT `#84` AND `#85` CLOSED

| | |
|---|---|
| ⭐⭐ **`#84` — F3, the last panel-wide aggregate that pooled** | The split is computed in **L3**, where disposition labels are DATA — deriving it in L3.5 would mean parsing `segment_label` strings, the defect class `#80` just closed. `within` is membership of `tc.within_target_labels()`, **byte-for-byte the rule `decision.within_target_action_rate` uses**, so the funnel and the headline can never disagree about who the target is; **ambiguous falls outside in both**. ⚠ Either side is **None at n=0**: `_funnel_rates` on an empty distribution returns baseline × a floor multiplier with a 100%-wide band — a confident number about nobody. ⭐ `_validate_funnel_projection` now validates **every** `SegmentProjection` on the object rather than only `by_segment`, and enforces **within + outside == population** as an integer identity. ⭐ Only ONE production surface renders funnel numbers (`batch_run._print_report`) — the HTML read withholds them by design (`FUNNEL_WITHHELD_NOTE`), so the blast radius was one file. |
| ⭐⭐ **`#85` — one assembler per prompt, and the tool schema is part of the artifact** | `build_l2_call` / `build_l4_call` / `build_assess_call` are what the real call sites consume and what the tests read. ⚠ **The class half:** `test_generation_prompt.assembled()` joined the system blocks and the user turn but **not the tool schema** — while its own `test_no_exemplar_is_stated_twice_in_the_whole_prompt` names the `occupation_hint` **schema description** as one of three places an exemplar lived. **The test written to catch that defect could not see the place it named.** Both assemblers now read system + user + schema; the existing 24 tests pass unchanged, so nothing is hiding there today. ⭐ assess's retry turn was an f-string **inline in the call loop** — unreachable from a test without re-typing it, and a re-typed prompt is a phantom. Extracted and proved byte-identical. |

⭐⭐ **TWO NEW VACUOUS SHAPES, BOTH CAUGHT BEFORE COMMIT AND BOTH MINE:**
1. ⚠ **A test that measures the code against the code.** The retry-cap test read
   `_PRIOR_RAW_MAX_CHARS` from the module — so the mutation that raised the constant raised the
   test's own bar with it and went **uncaught**. Fixed by pinning the literal `8000`.
2. ⚠ **A source-slice that runs to end-of-file.** The wiring test sliced from the caller's `def`
   to EOF and asked whether the assembler's name appeared — it always did, on the assembler's
   **own `def` line** further down. It would have passed on a codebase where the wiring did not
   exist. Rewritten with `ast`.

**And two process rules, free:**

- ⭐ **A pre-registration must name its CONFOUNDS, not just its criteria.** `cycle_position` was
  sitting in `panel.json` for every agent. Had I been required to write down *"what else in this
  data could produce a high number"*, I would have caught the 7-of-8 myself.
- ⭐ **A headline must state its null.** *"7 of 8 bought at restock"* → *"7 of 8 existing customers
  said they would rebuy the brand they already buy"* — which is visibly not a result.
