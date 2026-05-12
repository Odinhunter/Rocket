# Rocket

A pre-publish synthetic-audience Creative Read for paid-social ads. Upload one finished ad creative; the engine returns a structured strategic memo — verdict, target match, top 3 changes, context-fit map, strengths, verbatim consumer quotes — in under 5 minutes, for ~$1-2 of API cost on the default matrix.

Designed to fit a D2C performance marketer's Monday-morning workflow: triage new ad variants before they ship to Meta, kill the bottom half, save the wasted exploration spend.

## Architecture

Four hierarchical synthesis layers, anchored on a locked report schema:

- **L1 — Bundled agent panel**: each agent = one `(disposition, context, seed)` cell. Two API calls per agent (Encoding R1+R2+R3, Reflection R4+R5+R6) on Sonnet 4.6 with prompt caching on the persona+image prefix (~3,099 tokens cached, 90% read discount on Reflection).
- **L2 — Per-disposition aggregation**: one Sonnet call per disposition. Compresses raw L1 transcripts into a within-disposition read with representative quotes per round.
- **L3 — Population synthesis**: one Sonnet call. Reads L2 summaries; emits robust themes, within-target vs outside-target findings, per-context fit, and a global quote pool.
- **L4 — Strategic memo**: one Opus call. Reads L3 + target classification; emits the locked 7-field report schema as JSON in the response body (no tool-use mode).
- **Target classification**: one Opus vision call, runs parallel to L2/L3. Classifies each disposition in the pool as within / outside / ambiguous against the ad's inferred target.

Default mode is **single-asset + context envelope** — one creative, evaluated across multiple attention states (commute scroll, pre-purchase research, late-evening unwind). The "comparison" texture comes from intra-creative across contexts, not from a competitor anchor.

See `docs/ARCHITECTURE.md` for the full design.

## Repo layout

```
agent/                       core pipeline
  schema.py                  locked Report + AgentTranscript dataclasses + validate_report
  config.py                  RunConfig (matrix size, models, versions, tenant ids)
  prompt.py                  system-prompt assembly (persona prefix, cacheable)
  runtime.py                 L1 bundled-call runtime (Encoding + Reflection, idempotent)
  synthesis_l2.py            L2 per-disposition (Sonnet, tool-use)
  synthesis_l3.py            L3 population synthesis (Sonnet, tool-use)
  synthesis_l4.py            L4 strategic memo (Opus, response-body JSON)
  synthesis_types.py         L2Summary, L3Summary, TargetClassification (intermediate types)
  target_id.py               Opus vision call — single-asset target classification
  run_service.py             RunService orchestrator: wires all layers
  telemetry.py               per-call cost/latency/cache telemetry + multi-tenant run_dir
archetypes/                  archetype priming (untouched)
  demographics.py            who they are
  culture.py                 cultural reference points
  behavior.py                behavioral patterns
  voice.py                   speech register
  disposition.py             hand-mapped, per (archetype × category)
  context.py                 attention-state contexts per archetype
assets/                      ad images
tests/                       smoke tests for each layer
  test_schema_roundtrip.py   schema lock
  test_run_config.py         RunConfig + multi-tenant paths
  test_l1_smoke.py           L1 bundled runtime, cache, idempotent resume
  test_l2_smoke.py           L2 -> L3 -> L4 end-to-end on real adapted transcripts
  test_l3_smoke.py           L3 + L4 on hand-typed L2 fixtures
  test_l4_smoke.py           L4 isolation on hand-typed L3 fixture
  test_target_id_smoke.py    Target classification on boat_ad.png
  test_run_service_minimal.py  Full RunService on a 1x1x1 = 1 agent run
  fixtures/                  hand-typed L2/L3/target_classification fixtures
scripts/
  adapt_checkpoint_to_transcripts.py  one-shot: legacy checkpoint.json -> AgentTranscript[]
  cache_validation_test.py            v1 cache validation (initial baseline)
  cache_validation_test_v2.py         v2: strict-prompt bundled rounds (validated 2026-05-12)
batch_run.py                 CLI entry point (argparse -> RunConfig -> RunService.run)
replay_synthesis.py          L2->L3->L4 replay on a stored run (skip L1)
docs/
  ARCHITECTURE.md            forward-looking design doc (the contract)
runs/<account_id>/<brand_profile_id>/<run_id>/    multi-tenant run artifacts
  run.json                   config + final Report
  telemetry.jsonl            per-call observability
  transcripts.json           AgentTranscript[]
  l2_summaries.json          L2Summary[]
  l3_summary.json            L3Summary
  l4 in run.json             (the consumer-facing Report)
  target_classification.json
  invariants.json            cache/output/cost assertions
  agent_calls/               per-bundled-call artifacts for idempotent resume
    NNNN__encoding.json
    NNNN__reflection.json
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

## Run

Single-asset Creative Read on the default 5 × 3 × 1 = 15-agent matrix:

```bash
python batch_run.py --asset assets/boat_ad.png
```

Smaller smoke / cheaper iteration:

```bash
python batch_run.py --asset assets/boat_ad.png --dispositions 3 --contexts 2 --seeds 1
```

Resume a partially-completed run (per-bundled-call idempotency means existing artifacts are loaded from disk, only missing calls fire):

```bash
python batch_run.py --asset assets/boat_ad.png --resume <run_id>
```

Replay L2→L3→L4 on a stored run (skip the agent layer entirely — fast iteration on synthesis prompts):

```bash
python replay_synthesis.py runs/internal/default/<run_id>
```

## Smoke tests

Each synthesis layer is independently testable against a fixture from the layer below.

```bash
python tests/test_schema_roundtrip.py        # no API cost
python tests/test_run_config.py              # no API cost
python tests/test_l4_smoke.py --once         # ~$0.30 (Opus)
python tests/test_l3_smoke.py                # ~$0.35
python tests/test_l2_smoke.py                # ~$0.50 (uses real adapted L1 transcripts)
python tests/test_l1_smoke.py                # ~$0.03 (one agent, validates cache)
python tests/test_target_id_smoke.py         # ~$0.10
python tests/test_run_service_minimal.py     # ~$0.50 (one full 1x1x1 run end-to-end)
```

## Notes

- **Concurrency default = 4** (`max_concurrent_agents`). At the 30K ITPM Anthropic tier, each Encoding+Reflection pair costs ~6.8K ITPM tokens; 4 concurrent stays within the per-minute budget. Raise once you measure your tier ceiling. The cache prefix is single-marker on the system block + image block; no secondary marker on Reflection.
- **Dispositions cap at 7** per Brand Profile (L2 fan-out scales linearly; the cap is part of the cost lock).
- `seed_idx` is a label, not a deterministic control — Anthropic SDK has no `seed` parameter, so within-cell variance is API stochasticity at temperature=1.0.
- **Idempotent per-call resume**: every successful Encoding/Reflection writes `agent_calls/<aid>__<phase>.json`. On `--resume`, completed calls are loaded from disk and skipped. Replays inside the cache TTL (5 min) hit the cache cheaply.
- **Protocol lock**: any prompt change to the agent layer or L2-L4 means bumping `PROTOCOL_VERSION` in `agent/config.py` — every run that survived past the change becomes a different benchmark.
