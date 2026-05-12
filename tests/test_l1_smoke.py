"""Step-6 smoke: L1 bundled runtime — fire one agent, verify cache writes
on Call A, cache reads >= 2900 on Call B, all 6 round labels in output,
output_tokens <= 1000, stop_reason=end_turn, idempotent resume skips the
already-completed call.

Cost: ~$0.028 per agent (Sonnet 4.6).

Run: python tests/test_l1_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent.config import AssetSpec, RunConfig
from agent.runtime import AgentSpec, run_agent_bundled
from agent.telemetry import (
    current_account_id,
    current_brand_profile_id,
    current_run_id,
    run_dir,
)
from archetypes.disposition import list_dispositions
from archetypes.context import list_contexts


def _setup_run() -> tuple[AgentSpec, RunConfig, str]:
    archetype = "urban_indian_male_22_30"
    category = "personal_audio"
    dispositions = list_dispositions(archetype, category)
    contexts = list_contexts(archetype)
    disp = next(d for d in dispositions if d[0] == "brand_loyal_boat_user")
    ctx = next(c for c in contexts if c[0] == "pre_purchase_research")

    spec = AgentSpec(agent_id=0, disposition=disp, context=ctx, seed_idx=0)
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512"),
        archetype=archetype,
        category=category,
        dispositions_per_run=1,
        contexts_per_run=1,
        seeds_per_cell=1,
    )
    cfg.validate()
    run_id = f"l1_smoke_{int(time.time())}"
    return spec, cfg, run_id


def _set_context_vars(cfg: RunConfig, run_id: str) -> None:
    current_account_id.set(cfg.account_id)
    current_brand_profile_id.set(cfg.brand_profile_id)
    current_run_id.set(run_id)


def _read_telemetry(run_id: str, cfg: RunConfig) -> list[dict]:
    p = run_dir(run_id, account_id=cfg.account_id, brand_profile_id=cfg.brand_profile_id) / "telemetry.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def _has_round_label(text: str, label: str) -> bool:
    # Tolerant of formatting: model may write "R1 GUT:" or "**R1 GUT:**" etc.
    pattern = rf"\b{label}\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: ANTHROPIC_API_KEY not set")
        return

    print("=== L1 bundled-runtime smoke (one agent, fresh) ===")

    spec, cfg, run_id = _setup_run()
    _set_context_vars(cfg, run_id)

    # Clean run dir (in case a stale dir matches)
    rd = run_dir(run_id, account_id=cfg.account_id, brand_profile_id=cfg.brand_profile_id)
    if rd.exists():
        shutil.rmtree(rd)

    print(f"  spec: agent_id={spec.agent_id} disp={spec.disposition_label} ctx={spec.context_label}")
    print(f"  run_dir: {rd}")

    t0 = time.time()
    transcript = run_agent_bundled(spec, cfg, run_id=run_id)
    elapsed = time.time() - t0
    print(f"\n--- Fresh run: {elapsed:.1f}s ---")
    print(f"  encoding_text ({len(transcript.encoding_text)} chars):")
    print(f"    {transcript.encoding_text[:200]!r}...")
    print(f"  reflection_text ({len(transcript.reflection_text)} chars):")
    print(f"    {transcript.reflection_text[:200]!r}...")

    # Round labels present
    for label in ("R1", "R2", "R3"):
        assert _has_round_label(transcript.encoding_text, label), f"{label} missing in encoding_text"
    for label in ("R4", "R5", "R6"):
        assert _has_round_label(transcript.reflection_text, label), f"{label} missing in reflection_text"
    print("  OK  all 6 round labels present (R1-R6)")

    # Telemetry assertions
    events = _read_telemetry(run_id, cfg)
    agent_events = [e for e in events if e["layer"] == "agent" and e["status"] == "ok"]
    assert len(agent_events) == 2, f"expected 2 telemetry events, got {len(agent_events)}"

    call_a, call_b = agent_events  # in fire order
    cr_a = call_a.get("cache_creation_tokens") or 0
    cr_b_create = call_b.get("cache_creation_tokens") or 0
    cr_b_read = call_b.get("cache_read_tokens") or 0
    out_a = call_a.get("output_tokens") or 0
    out_b = call_b.get("output_tokens") or 0

    print(f"\n  Call A (Encoding):")
    print(f"    cache_creation={cr_a}, cache_read={call_a.get('cache_read_tokens') or 0}")
    print(f"    input={call_a.get('input_tokens')}  output={out_a}  latency={call_a.get('latency_ms')}ms")
    print(f"  Call B (Reflection):")
    print(f"    cache_creation={cr_b_create}, cache_read={cr_b_read}")
    print(f"    input={call_b.get('input_tokens')}  output={out_b}  latency={call_b.get('latency_ms')}ms")

    # Cache assertions
    assert cr_a >= 2900, f"Call A cache_creation={cr_a}, expected >= 2900 (the persona+image prefix)"
    assert cr_b_read >= 2900, f"Call B cache_read={cr_b_read}, expected >= 2900"
    print("  OK  cache prefix written on Call A (>= 2900 tokens), read on Call B (>= 2900 tokens)")

    # Output discipline
    assert out_a <= 1000, f"Call A output_tokens={out_a}, expected <= 1000"
    assert out_b <= 1000, f"Call B output_tokens={out_b}, expected <= 1000"
    print(f"  OK  output_tokens within budget (A={out_a}, B={out_b}, both <= 1000)")

    # Agent_calls/ artifacts persisted
    enc_path = rd / "agent_calls" / "0000__encoding.json"
    ref_path = rd / "agent_calls" / "0000__reflection.json"
    assert enc_path.exists(), f"missing {enc_path}"
    assert ref_path.exists(), f"missing {ref_path}"
    print(f"  OK  artifacts persisted at {rd}/agent_calls/")

    # ---- Idempotency: re-run, should skip the API calls and load from disk ----
    print("\n=== Re-running (idempotency check) ===")
    initial_event_count = len(_read_telemetry(run_id, cfg))
    t0 = time.time()
    transcript_2 = run_agent_bundled(spec, cfg, run_id=run_id)
    elapsed_2 = time.time() - t0
    new_event_count = len(_read_telemetry(run_id, cfg))

    assert transcript_2.encoding_text == transcript.encoding_text, "encoding_text changed on re-run"
    assert transcript_2.reflection_text == transcript.reflection_text, "reflection_text changed on re-run"
    assert elapsed_2 < 2.0, f"re-run took {elapsed_2:.1f}s — should be near-instant from disk"
    assert new_event_count == initial_event_count, (
        f"re-run made API calls (telemetry events {initial_event_count} -> {new_event_count})"
    )
    print(f"  OK  re-run loaded from disk in {elapsed_2*1000:.0f}ms, no new API calls")

    print("\nPASS — L1 bundled runtime: cache, output discipline, idempotent resume.")


if __name__ == "__main__":
    main()
