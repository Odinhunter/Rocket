# Rocket — Architecture and Build Plan

Status as of 2026-05-12. Forward-looking — describes the post-refactor target architecture that the Week-1 work will land. Current `main` still reflects the pre-refactor protocol used in the methodology stress test.

## Product

A pre-publish synthetic-audience Creative Read for paid-social ads. The customer (a D2C performance marketer, or an agency operating on their behalf) uploads one finished ad creative; the engine returns a structured read with verdict, target classification, top-3 changes, context-fit map, strengths, and verbatim consumer quotes — in roughly under 5 minutes, for roughly $7-9 of API cost. Designed to fit a Monday-morning workflow: triage 15-30 new variants before they ship to Meta, kill the bottom half, save the wasted exploration spend.

## ICP and account model

- **Primary buyer**: in-house growth lead at a D2C brand ($1-5M ARR, $30-100K/month Meta spend, shipping 15-30 ad variants/month).
- **Day-1 secondary buyer**: agencies serving that customer. Supported through the data model, not feature flags.
- **Data model**: `Account → Brand Profile → Run`. An Account is the billing entity. A Brand Profile is a tenant with its own customer-specific disposition pool. A Run belongs to a Brand Profile. A D2C in-house team is an Account with one Brand Profile. An agency is an Account with many Brand Profiles. Same code path.

## Run architecture (post-refactor target)

### Default mode: single-asset + context envelope

One creative asset, evaluated across the full disposition × temperature × context × seed matrix. The "comparison" that gives the verdict its texture is intra-creative across attention states (commute scroll vs pre-purchase research vs late-evening unwind), not inter-creative against another ad. The focal+anchor "competitor benchmark" mode is preserved as an optional paid upsell at higher subscription tiers, not the default flow.

### Agent panel (Layer 1)

- Each agent = a single cell in the `(disposition, temperature, context, seed)` matrix.
- Production scale ceiling: 200 agents per run. Configurable per-run.
- Two bundled calls per agent:
  - **Call 1 — Encoding**: R1 gut + R2 comprehension + R3 emotion. Single prompt, structured output emitted as three named sections.
  - **Call 2 — Reflection**: R4 stickiness + R5 social + R6 friction. Same pattern.
- Model: Sonnet 4.6 on both calls. Haiku-on-Call-1 explicitly rejected (cross-model breaks caching, first-impression voice quality is exactly where Haiku underperforms, marginal savings don't justify the methodology risk).
- Prompt caching: `cache_control` marker on the system prompt + image block in user message. Single marker, no secondary on Call 2 (no third call to benefit from re-caching).
- `max_tokens=1100`. Prompt-level caps using **strict "exactly N sentences. Stop after the Nth period." language** do the actual rationing; max_tokens is a guillotine, not a budget.
- Inter-round sleep removed. Agents run fully parallel (subject to rate-limit queueing).

### Hierarchical synthesis (Layers 2-4)

Mirrors analyst → manager → partner workflow:

- **L2 — Per-disposition aggregation**: one Sonnet call per disposition cell. Computes within-disposition variance, flags within-cell outliers, selects representative quotes.
- **L3 — Population synthesis**: one Sonnet call. Reads compressed L2 summaries (not raw L1 transcripts). Cross-disposition variance, theme extraction, robust-vs-single-cell findings on the within-target subset.
- **L4 — Strategic memo**: one Opus call. Reads L3 + target classification. Emits structured JSON in the response body against the locked report schema. **No tool-use mode** — tool-use truncation was the failure mode in the pre-refactor pipeline.
- **Target classification**: one Opus vision call, runs parallel to L2/L3 because it needs the image independently.

Net call count per run: ~400 agent calls (200 × 2 bundled) + ~8 synthesis calls. Down from ~96 in the pre-refactor 14-agent run, would have been ~1206 at 200 agents in the old architecture.

### Report schema (the contract everything serializes to)

```
{
  verdict: WORKING | MIXED | FAILING,
  confidence: 0-100,
  target_match: { reached, missed },
  top_3_changes: [{ change, why, evidence_quotes, within_target_corroboration }],
  strengths_to_preserve: [{ strength, evidence_quotes }],
  context_fit_map: { [context]: { verdict, friction_summary } },
  verbatim_consumer_voice: [{ quote, disposition, round, context }]
}
```

Schema is locked before any agent or synthesis code is written. L4 writes to it, L3 produces what L4 needs, L2 produces what L3 needs, L1 produces what L2 needs. Architecture flows backward from the deliverable.

## Empirically validated cost (2026-05-12)

| Component | Value |
|---|---|
| Cache prefix size | 3,099 tokens (system prompt + image, Boat ad test case) |
| Per-agent measured cost | $0.028 (Call A: $0.018 with cache write + ~380 output; Call B: $0.011 with cache read + ~520 output) |
| 200-agent run total (projected) | ~$7.00-7.50 (~$5.70 agent + ~$1.30 synthesis) |
| Pre-refactor cost at 200 agents | ~$27-30 |
| Reduction | ~75% |
| Margin vs $10/run target | ~25-30% |
| Wall-clock at 200 parallel | 1.5-3 min (quote externally as "under 5 min") |

Test scripts: `scripts/cache_validation_test.py` and `scripts/cache_validation_test_v2.py`. The v2 run validated that all six rounds render cleanly under strict prompt discipline; `end_turn` stop reasons on both calls (no truncation).

## Methodological commitments — do not drift

- **Round bundling is methodology, not just compression.** Gut → comprehension → emotion is a natural cognitive arc; bundling preserves it. Serial separate calls break that flow.
- **Context is per-agent, not multiplexed within a call.** Different contexts = different agents in the matrix. Never ask an agent to "reset and forget" mid-conversation; real humans can't unsee, and LLMs asked to forget will performatively differ.
- **Schema-first sequencing.** Before any agent or synthesis code is written, the report JSON schema is locked. All four synthesis layers serialize to it.
- **Single-asset is the default.** Focal+anchor is the optional upsell mode, not the assumption.

## Operational requirements (load-bearing — violations breach budget)

1. **Output discipline via strict prompt language.** Each round has "exactly N sentences. Stop after the Nth period." constraints. R1 ~60 tok, R2 ~150 tok, R3 ~170 tok, R4 ~150 tok, R5 ~200 tok, R6 ~250 tok. Verify `output_tokens` in telemetry on first 2-3 runs; treat consistent drift above 1000 tok/call as P0.
2. **Disposition count capped at ≤7 per Brand Profile** at brand-brief intake. L2 fan-out scales with disposition count.
3. **Idempotent-keyed retry logic from Week 1.** Calls keyed on `(run_id, agent_id, call_phase)`. ~400 calls/run × ~0.5-1% failure rate = 2-4 retries/run typical.

## Pricing

Credit-based subscription, three tiers (Starter / Growth / Agency). One credit = one Creative Read. Two upgrade incentives baked into the math: effective $/read drops at higher tiers, and overage credit price drops at higher tiers. Credits do not roll over. Pay-as-you-go available for trials at a price higher than any subscription overage. Tier feature gating: brand profile count, seats, white-label exports, API access. **Specific numbers are deliberately not in this doc** — under active design and will be set after design-partner conversations.

## Dispositions

Hand-mapped per customer during onboarding through ~Q1. No disposition factory at MVP launch. Factory reopens at month 4-6 only if volume exceeds ~30 customers/month or long-tail category coverage outpaces hand-write capacity.

Onboarding: brand-brief intake → 60-90 min hand-writing session in established voice style (first-person, 5-8 sentences each, concrete artifacts) → customer reviews + approves → ready to test. Style guide maintained as a one-pager.

## 30-day MVP plan

- **Week 1 — Schema lock + architecture refactor**: Day-1 telemetry pull (done), schema lock, RunService refactor, single-asset + context envelope, bundled rounds, prompt caching, 4-layer synthesis, multi-tenant scaffolding, versioning, empirical validation (bundled vs serial + 120 vs 200 agent matrix), protocol lock end of week.
- **Week 2 — Deliverable + onboarding scaffold**: HTML/PDF report renderer, brand-brief intake form, disposition style guide, customer-approval workflow, resilience patterns (idempotent retry + quorum completion), Stripe metered billing backend.
- **Week 3 — Web UI + onboarding flow**: minimal web app, onboarding wizard, credit balance UI, overage purchase flow.
- **Week 4 — Design partner ROI proof**: sign 2 paying D2C design partners, onboard, run 10-20 of their ads each, track ship/kill decisions, compare 2-week CAC delta, document case study.

Non-goals for month 1 (resist scope creep, these are months 2-6): heatmapping, hook bank / copy testing, brand positioning audit, creator-fit score, channel-fit matrix, disposition factory, API tier, video parsing, custom benchmark library, predictive in-market score calibration.

## Empirical validations pending in Week 1

Same 3 ads, both architectures, both matrix sizes:

- **Bundled vs serial round comparison**: require ≥80% verbatim-quote overlap, friction-point overlap, and verdict consistency to ship bundled.
- **120-agent vs 200-agent matrix**: production locked at 200 on asymmetric-risk grounds. Silent downscale to 120 if 120 catches ≥90% of verdicts AND ≥80% of outlier flags across the 3 validation ads AND the first 5 paying-customer runs. Otherwise stay at 200.

Validation cost budget: ~$70 across both tests.

## Code layout (current and target)

```
agent/
  runner.py          # 6-round protocol invocation (pre-refactor; becomes bundled in Week 1)
  synthesis.py       # synthesis layer (pre-refactor; becomes hierarchical L2-L4 in Week 1)
  prompt.py          # system prompt builder
  persistence.py     # checkpoint + run.json
  telemetry.py       # per-call observability
archetypes/
  demographics.py    # PROFILE block source
  behavior.py        # BEHAVIOR block source
  voice.py           # VOICE SAMPLES block source
  culture.py         # CULTURE block source
  disposition.py     # category-conditional dispositions, hand-mapped per archetype × category
  context.py         # attention-state contexts per archetype
assets/              # ad images for testing
runs/                # per-run artifacts (checkpoint, run.json, telemetry.jsonl) — gitignored
scripts/
  cache_validation_test.py    # initial cache test
  cache_validation_test_v2.py # strict-prompt validation, confirmed 6-round rendering
batch_run.py         # current entry point (becomes RunService in Week 1)
replay_synthesis.py  # re-run synthesis from a persisted run.json
docs/
  ARCHITECTURE.md    # this file
```

In Week 1, `batch_run.py` and `runner.py` get refactored against the four-layer architecture, schema, and bundled-round design. Until that lands, the pre-refactor protocol remains the authoritative pipeline on `main`.
