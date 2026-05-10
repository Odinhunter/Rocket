# Rocket

A simulated-audience pipeline for ad evaluation. Synthetic agents — primed with archetype, disposition, and viewing context — react to an ad image across a 6-round protocol. A population-level synthesis layer turns the reactions into a strategist memo: target classification, consensus/disagreement, and a single-biggest-friction read.

## What it does

Given a focal ad image (and an anchor ad for comparison), the pipeline:

1. **Samples a population** of agents across `D dispositions × C contexts × S seeds` cells for one archetype (e.g. `urban_indian_male_22_30`).
2. **Runs the 6-round protocol** against each (agent × stimulus) as an independent conversation:
   - R1 — gut reaction (4-field structured output: attention/time/action/signal)
   - R2 — comprehension audit (what claim is the brand making, do you buy it)
   - R3 — emotional mapping (relevance/trust/curiosity/irritation/aspiration, 1–10 + reason, strict JSON)
   - R4 — stickiness, two days later (free text)
   - R5 — social calculus: screenshot / mention / public post (free text)
   - R6 — purchase-friction map: condition for shortlist + single biggest friction (free text)
3. **Synthesizes a population report** (4 Opus tool-use calls, one per free-text round) covering within-cell vs across-cell variance, focal-vs-anchor deltas, consensus, disagreement axes, and outliers.
4. **Classifies disposition × target fit** from the focal image (separate vision call — does not see reactions).
5. **Generates a strategist memo** (WORKING / MIXED / FAILING verdict, anchored on the within-target subset).

## Repo layout

```
agent/             agent runtime
  prompt.py        system-prompt assembly from archetype + disposition + context
  runner.py        run_agent: per-round prompts, JSON retry loop for R3
  telemetry.py     call_with_telemetry: wraps Anthropic calls with logging
  persistence.py   run_id, checkpoints, run.json on disk
  synthesis.py     population report + target classification + strategist memo
archetypes/        archetype priming
  demographics.py  who they are
  culture.py       cultural reference points
  behavior.py      behavioral patterns
  voice.py         speech register
  disposition.py   sample_disposition(archetype, category)
  context.py       sample_context(archetype) — viewing situation
assets/            ad images (focal + anchors)
main.py            single-agent walkthrough (one archetype, one ad, all 6 rounds)
batch_run.py       population protocol v2 (parallel, throttled, checkpointed)
replay_synthesis.py  re-run synthesis on a saved run.json (or legacy stdout log)
eval.py            evaluation harness
compare_models.py  side-by-side model comparison
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

## Run

Single agent walkthrough on the Blue Tokai Drop ad:

```bash
python main.py
```

Population batch run (samples specs, runs 6 rounds × N conversations in parallel, persists checkpoints + final `runs/<run_id>/run.json`):

```bash
python batch_run.py
# resume an interrupted run:
python batch_run.py --resume <run_id>
```

Replay synthesis on a completed run (skips the 4 free-text Opus calls — use this for fast iteration on the strategist prompt):

```bash
python replay_synthesis.py --run-id <run_id>
```

## Notes

- Concurrency is hand-tuned to a 30K ITPM ceiling: `SEMAPHORE=2`, `INTER_ROUND_SLEEP_S=30`. At ~189-agent scale these need recomputing against measured tokens-per-call; per-conversation transcripts and synthesis chunking become mandatory at that scale.
- `seed_idx` is a label for pairing/replication, not a deterministic control — the Anthropic SDK has no `seed` parameter, so within-cell variance comes from `temperature=1.0` stochasticity at runtime.
- Round 3 has a 3-attempt JSON retry loop; on full failure the conversation is dropped and logged rather than crashing the batch.
- R2/R4/R5/R6 variance is currently Jaccard over LLM-extracted themes. Embedding-cosine on a separate-from-generation embedder is the principled v2 (sidesteps asking the same model to judge its own homogenization) — flagged in `agent/synthesis.py`.
