# Rocket

**Pre-test a paid-social ad on a simulated Indian audience before you spend on it.**

A D2C growth team uploads one finished ad. Rocket shows it to a panel of AI-simulated
buyers, each one a specific person (age, income, city, job, household) holding a specific
stance toward the category, met in a specific moment (a 4 pm desk slump, a commute scroll,
pre-purchase research). Each person reacts in their own words and says what they would
actually do next. Rocket then aggregates the panel into a **Creative Read**: a verdict
(scale / iterate / retarget / rebuild), who the ad lands with and who it misses, the top
changes to make, and verbatim reactions.

The point is to triage 15–30 new variants a month before they go to Meta, and kill the
weak half before they burn exploration budget.

> **Status:** research prototype, built solo (Ishan Kabra), May–Aug 2026. Shelved in
> August 2026. Nothing here is a validated predictor of in-market performance; see
> *What the evidence says* below.

---

## How it works

```
ad creative ─┐
             ├─► target read ──────────────┐   (Opus, vision: who is this ad for?)
audience  ───┤                             │
(who, where, │   panel of buyer types ─────┤   each = person × stance × moment
 what stance)│   ├─ Encounter call         │   gut, comprehension, emotion  (Sonnet)
             │   └─ Reflection call        │   would they act? what next?   (Sonnet)
             │                             ▼
             └─► aggregation ──► diagnosis ──► prescription ──► Creative Read (HTML)
                 per-type, then             (what's wrong)   (what to change)
                 population                       Opus             Opus
```

Design choices worth knowing:

- **People, not averages.** An audience is a set of distinct buyer types written for a
  declared demographic region, so a "women 45–60, tier-3" buy gets people who actually
  live there, not metro defaults. `scripts/generate_audience.py` builds them;
  `agent/panel.py` selects the slice a given buy reaches.
- **Category knowledge lives in packs**, not prompts (`packs/`): real brands, prices,
  shelves and habits per category, so reactions name things a real buyer would.
- **The behavioural signal is a choice, not a score.** Each agent picks a concrete next
  step (`nothing`, `seek_info`, `buy_at_restock`, …) instead of rating the ad 1–10.
- **Cost is metered and confirmed before spending.** A run is two-phase: `prepare()`
  builds the panel and shows a confirmation surface, `commit()` spends. Prompt caching on the
  persona + image prefix cuts the reflection call's input cost by ~90%.
- **Every paid experiment is pre-registered.** The pass/fail criterion is committed to
  `docs/*_preregistration.md` before the run, and the outcome is written up against it
  in `docs/*_result.md`, including the inconclusive ones.

## What the evidence says (honestly)

- **Sharpest result:** on a real protein-bar ad, the one stance designed to want the
  product acted 7 times out of 8; every other stance acted 0 times out of 56
  (`docs/fnb_stance_discrimination_result.md`). One run, one category, ~$3.85.
- **Inconclusive or failed tests are kept, not buried:** `docs/fnb_test_a_result.md`
  (the test moved a lever that didn't control the outcome) and `docs/fnb_test_b_result.md`
  (people stay coherent across moments; their opinions don't).
- **Not yet shown:** that a verdict predicts how an ad does in-market. The human-panel
  and brand-manager backtest designs for that are in `panel/v3_human_panel/`.
- **A candid post-mortem:** `docs/why_we_keep_making_the_same_mistake.md`, a review of
  why the same defects kept returning and what changed in the test suite because of it.

## Repo layout

```
batch_run.py            CLI: run a Creative Read on one ad
render_read.py          turn a finished run into the client-facing HTML read ($0)
serve.py                operator web app (landing page + password-gated console)
replay_synthesis.py     re-run the synthesis layers on a stored run, skipping the panel

agent/                  the engine
  runtime.py              panel calls (Encounter + Reflection), caching, resume
  panel.py, population.py, demography.py   who is in the room
  synthesis_l2/l3.py      per-type and population aggregation
  synthesis_assess.py     diagnosis      synthesis_prescribe.py   prescription
  target_id.py            vision read of who the ad is for
  decision.py, purpose.py the verdict and the job the ad is meant to do
  read_model.py, render.py, dashboard_html.py   the report
  preflight.py, credits.py, telemetry.py        cost estimate, metering, observability
packs/                  category knowledge (snacking, coffee, chocolate, audio, wellness…)
server/                 FastAPI operator app (runs, sessions, audience form, auth)
scripts/                audience generation + install, audits, cost preflight, scaffolds
specs/                  sample audience specs and baseline funnels
panel/                  human-validation materials (scoring rubric, panel designs)
docs/                   architecture, protocol specs, pre-registrations and results
tests/                  ~830 offline tests; paid tests are opt-in
```

## Running it

Python 3.12+.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Offline test suite, $0. Three tests read locally installed audience
# libraries (gitignored), so deselect them on a fresh clone:
pytest -m "not local_data"          # 823 passed, 6 skipped (paid)

# Paid smoke tests call the real API (~$3.50–4.00 total):
pytest --paid
```

A paid Creative Read needs an `ANTHROPIC_API_KEY` in `.env` and an installed audience
library. Generate and install one, then run:

```bash
python scripts/generate_audience.py --dry-run            # $0: prints the plan
python scripts/generate_audience.py --market snacking    # ~$1: writes the people
python scripts/install_generated_audience.py --help      # install into runs/

python batch_run.py --asset assets/sample_creative.png --help
```

`assets/sample_creative.png` is a fictional ad used by the tests and examples. The real
brand creatives used during development are kept out of the repo (see `.gitignore`).

## A note on brand names

Some docs and panel sheets mention real brands because development runs used real,
publicly visible ads as inputs. Every reaction, score and verdict in this repo is
synthetic output from an unvalidated prototype. None of it is a judgement of those
brands, their products or how their ads performed.
