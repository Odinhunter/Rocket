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

# WHAT IS LEFT, IN ORDER

| # | change | why now |
|---|---|---|
| 1 | ⚠⚠ **A counterfactual guard.** At scoring time, check whether a disposition's anchor names the advertised brand; exclude those from champion candidacy and from `retain` SCALE, or report them as retention | **Fixes F1 and F2 together.** They are one absence, not two bugs |
| 2 | ⚠ **Fix `tests/test_purpose_retain.py` and `test_dashboard_html.py:1204`** — both pin defects | Until they change, the fixes above look like regressions |
| 3 | **Content preflight.** We already refuse to spend without `preflight_cost.py`. Add the twin: render one persona + one context against the real pack, print, confirm. `$0.01` | Would have caught this week's live bug before `$3.85` |
| 4 | **Collect the smoke tier.** Give the five paid smokes pytest functions behind a `paid` marker → `pytest -m paid`, ~`$1.13`, one command | The tier exists and nothing runs it |
| 5 | **Seam tests for L2, L4, assess** | The three prompts that write the customer's report have zero |
| 6 | **Delete `compose_persona_prompt`** and its test, or wire it | Dead code with a green test is a lie the next session will believe |
| 7 | **Finish the class**: disposition labels on customer screens (`app_html.py:1109`, `read_model.py:1230`, `dashboard_html.py:1315`) need a `display_name` the same way | Same class, customer-facing half |
| 8 | `decision.py:170` parses `label.split("_")[0]` for stance — **the naming convention is load-bearing runtime logic** and fails closed, silently. The generated JSON already carries `stance` as a field | Same class, inverted |

**And two process rules, free:**

- ⭐ **A pre-registration must name its CONFOUNDS, not just its criteria.** `cycle_position` was
  sitting in `panel.json` for every agent. Had I been required to write down *"what else in this
  data could produce a high number"*, I would have caught the 7-of-8 myself.
- ⭐ **A headline must state its null.** *"7 of 8 bought at restock"* → *"7 of 8 existing customers
  said they would rebuy the brand they already buy"* — which is visibly not a result.
