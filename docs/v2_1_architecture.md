# Rocket v2.1 — Marketer-Led Composition + Two-Axis Verdict

**Status:** code complete on branch `v2.1-marketer-led` (7 commits off `main`), offline suite 18/18. **Not merged.** Live validation + bundle-span authoring are the remaining human steps (see *Handoff*). `PROTOCOL_VERSION = rocket-2.1.0`, `L4_PROMPT_VERSION = l4-3`, `VECTOR_SCHEMA_VERSION = rocket-2.1.0`.

## Why

Rocket is an ad-audience simulator for the D2C **performance marketer**, who buys media against a **declared demographic audience**. Two defects made v2.0 *not* marketer-led:

1. **The declared audience was overridden.** Panel composition crossed dispositions with demographics; when a disposition carried `demographic_bundles`, those *silently overrode* the customer's declared `spec.demographics`. Disposition prevalence was also flat (1/D), unrelated to the buy.
2. **Demographics were coarse buckets.** `age_band` (`18_24`…) and `income_tier` (`mass`…) snapped "20-24" to 18-24 and "≤14 LPA" across three tiers — a fidelity hole in a product whose pitch is "we honor *your* audience."

## Core model

- **Demographics = the sampling frame** — the declared audience defines *who is in the simulated room* (the marketer's call).
- **Disposition = the response model** — within that room, *attitude* drives reaction (unchanged). This preserves the product's edge and avoids demographic determinism.
- **Two target axes, intersected.** The ad's *inferred* target (the classifier, unchanged) and the marketer's *declared* audience (the panel). `within-target` = their intersection, which **emerges from composition** (once the panel *is* the declared audience, the classifier's "within" is automatically declared ∩ inferred). The *delta* between them is the first-class **audience-match** output.
- The customer brings **audience + ad** (+ copy/offer). Never personas or habits.

## What changed

### 1. Range-based demographics (`agent/vectors.py`)
`DemographicPoint` now stores continuous ranges: `age_min/age_max` (years), `income_lpa_min/income_lpa_max` (LPA — annual household income, lakhs/yr, matching how marketers and pack `demographic_defaults` think). Gender stays enumerated.

Back-compat is total: an `InitVar` shim converts legacy `age_band=`/`income_tier=` construction, and `from_dict` dual-reads legacy JSON via `_BAND_TO_AGE_RANGE` / `_TIER_TO_LPA_RANGE`. Every stored library/spec/run loads unmigrated. Render is unaffected — `render.py` dumps `demo.to_dict()` raw and the demographic-fit lens is prompt-level; only `VECTOR_SCHEMA_VERSION` bumps (render-cache invalidation).

### 2. Marketer-led composition (`agent/panel.py`)
`build_panel(..., marketer_led=True, tail_fraction=0.0)` — opt-in; legacy uniform/bundled paths unchanged when off.
- `demographic_overlap(persona, declared)` — gender-gated × age-overlap × income-overlap, in [0,1].
- `audience_mass(disposition, declared)` — the fraction of a disposition's buyers inside the declared audience (weighted-avg overlap; a no-bundle disposition is "universal" = 1.0). This is the marketer-led weight.
- `_choose_cells_marketer_led` — drop personas with zero mass; weight survivors by in-slice mass; **clip** each agent's demographics to the buy (`bundle ∩ declared`); optional **discovery tail** (off by default) draws excluded personas at natural demographics, **segregated + frame-tagged** (`PanelAgent.in_declared_frame`).
- Degenerate case (no persona overlaps the buy) → compose all dispositions at the declared demographics; the coverage guard flags it hard.

### 3. Guards (`agent/target_id.py`, `agent/synthesis_types.py`)
- **Mismatch band↔range bridge.** The inferred audience stays a band (vision output); it's bridged to a range and compared to the range-declared audience via a year-gap metric (`_AGE_GROSS_GAP_YEARS=18`, reproducing the old "3 bands apart"). Without this the guard silently lost the age axis.
- **Coverage guard (new).** `detect_thin_coverage` → `CoverageWarning` when the declared audience intersects `< 2` personas — a library-coverage gap, doubling as the white-glove authoring signal. Surfaced in `RunPreparation.coverage_warning` + `batch_run` prep banner (marketer-led runs only).

### 4. Two-axis verdict (`agent/schema.py`, `agent/synthesis_l4.py`)
- `Report.audience_match: AudienceMatch | None` — `aligned` / `mismatched`, promoting the mismatch guard. Attached **deterministically** in `synthesize_memo` (like `funnel_projection`) whenever a declared audience is present, **fed to the L4 model**, and enforced via the `declared_audience_disjoint` methodology flag.
- L4 (`l4-3`) guidance: on a mismatched audience, the remedy is **targeting** (a media-buy lever), not a creative rewrite — lead `bet_ranking` with the realignment move; don't burn `top_3_changes` rewriting a creative a retarget would rescue. The within/outside cascade is otherwise untouched (intersection emerges from composition).

## Using it

```
batch_run.py ... --audience-spec <spec.json> --marketer-led [--tail-fraction 0.15]
```
`audience_match` populates on **any** run with `--audience-spec` (even without `--marketer-led`); the marketer-led *composition* is the opt-in part. `disposition_labels` is still a required input (auto-suggest-from-audience is factory-adjacent, deferred).

## Deferred (by decision, not omission)
- **Persona factory** (auto-generating personas per arbitrary audience) — the long-term goal; needs a validated MVP first.
- **Auto-derived `disposition_labels`** — that's a factory slice; white-glove curates from a suggested default.
- **`prevalence` field** — held because an authored value would be a Medium-confidence guess (fake precision); in-slice-mass weighting is the MVP weight.
- **Always-on discovery tail** — off by default; on → segregated from the primary funnel.
- **Interest/behavior targeting** — beyond the demographic frame; later.

## Handoff (the human steps)
1. **Bundle-span authoring.** The current `health_wellness` bundles were authored for a general 25-44/upper-mid audience, so a narrow declared slice (e.g. women 20-24, ≤14 LPA) yields **0 eligible personas** and the coverage guard fires. Extend each persona's `demographic_bundles` to span the demographic ranges customers actually target. The coverage guard shows where the gaps are.
2. **Live validation.** A `batch_run --marketer-led` + `replay_synthesis.py` pass; the buzzword discriminant re-check on `l4-3`; human panel scoring. (Reaction-level realism is composition-independent and unaffected.)

## Phase → commit
| Commit | Phase |
|---|---|
| `58c7f4b` | 1 — range-based `DemographicPoint` |
| `a633a39` | 2 — marketer-led composition |
| `2311e4b` | 3 — mismatch bridge + coverage guard |
| `6979ba5` | 4 — two-axis verdict (`audience_match`, `l4-3`, `rocket-2.1.0`) |
| `b736e90` | run.json `l4_prompt_version` stamp |
| `3380599` | 5 — migrate specs + demo entities to ranges |
| `775a040` | 6 — wire marketer-led into the run flow + coverage guard |

## Key decisions (with rationale)
- **Frame vs response split** is the north star — reconciles customer-first with the attitudinal thesis without demographic determinism.
- **Intersect, don't collapse** the two target axes — collapsing loses the signal that tells a *bad creative* (fix creative) from a *good creative, wrong buy* (fix targeting), which is what makes the in-scope recommendations actionable.
- **Author the conditional, don't Bayes-invert** — the bundles are Med-confidence hand guesses and there is no base-rate field; inverting would stack estimation error under a rigorous coat. In-slice-mass weighting uses the bundles for robust *selection*, not fake precision.
- **Reweight-toward, don't hard-filter** — keep a (default-off) discovery tail so "your ad resonates outside your target" survives.
- **Verdict cascade near-intact** — the only verdict-logic change is the audience-match promotion + the `declared_audience_disjoint` flag; the `l4-3` re-zero of verdict validation was accepted, kept minimal.

> Note: the earlier in-scope-recommendation work (`l4-2`) was never committed to `main`; it rode into this branch and is folded into `l4-3`. Fix #1 merges *with* v2.1.
