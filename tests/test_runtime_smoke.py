"""API smoke: the agent runtime fires one PanelAgent end-to-end — renders
the persona core + context, runs bundled Encoding + Reflection, emits
R1-R7, parses the R7 behavioral signal, and holds the prompt-caching
invariant (Encoding writes the cache, Reflection reads it, the pair matches).

Also re-measures the cache-prefix token floor against the rendered-prose
prefix.

Cost: ~4 Sonnet calls (2 render + 2 agent), ~$0.03.

Run: pytest tests/test_runtime_smoke.py --paid   (or: python tests/test_runtime_smoke.py)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from dotenv import load_dotenv

load_dotenv()

from agent.artifact_pack import load_pack
from agent.config import AssetSpec, RunConfig
from agent.panel import PanelAgent
from agent.runtime import run_agent
from agent.telemetry import (
    current_account_id,
    current_brand_profile_id,
    current_run_id,
    run_dir,
)
from agent.vectors import (
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)

_ACCOUNT, _BRAND, _RUN = "_test_runtime", "runtime", "smoke_run"
_RENDER_CACHE = Path(f"runs/{_ACCOUNT}/{_BRAND}/library_renders")


def _panel_agent() -> PanelAgent:
    return PanelAgent(
        agent_id=0,
        demographic=DemographicPoint(
            gender="male", age_band="25_34", income_tier="upper_mid",
            geography="Bangalore / metro tier-1",
            occupation_hint="software engineer at a mid-stage SaaS startup",
        ),
        disposition=NamedDisposition(
            label="pragmatist_office_bru",
            vector=DispositionVector(
                category_relationship="regular", brand_stance="neutral",
                price_orientation="price_first", decision_driver="function",
                category_involvement="low", prior_experience_valence="neutral",
                channel_behavior="offline_first", life_stage="early_career",
            ),
        ),
        context=NamedContext(
            label="commute_scroll",
            vector=ContextVector(
                attention_level="low", device_posture="commute",
                intent_state="killing_time", energy_state="drained",
                social_setting="public",
            ),
        ),
        chaos=ChaosProfile(
            label="moderate",
            vector=ChaosVector(
                decision_velocity="moderate", suggestibility="medium",
                consistency="variable", risk_tolerance="balanced",
            ),
        ),
        category="coffee",
    )


def _cleanup() -> None:
    p = Path(f"runs/{_ACCOUNT}")
    if p.exists():
        shutil.rmtree(p)


def main() -> None:
    print("=== runtime API smoke ===")
    _cleanup()
    asset_path = Path("assets/sample_creative.png")
    if not asset_path.exists():
        raise SystemExit(f"missing test asset: {asset_path}")

    config = RunConfig(
        asset=AssetSpec(image_path=str(asset_path), label="Boat smoke asset"),
        archetype="urban_indian_male_22_30",  # legacy field, unused by runtime
        category="coffee",
        account_id=_ACCOUNT,
        brand_profile_id=_BRAND,
    )
    current_account_id.set(_ACCOUNT)
    current_brand_profile_id.set(_BRAND)
    current_run_id.set(_RUN)

    pack = load_pack("coffee")
    agent = _panel_agent()

    try:
        transcript = run_agent(
            agent, config, pack, run_id=_RUN, render_cache_dir=_RENDER_CACHE,
        )

        # R1-R6 labels present (the model reliably labels these).
        enc, ref = transcript.encoding_text, transcript.reflection_text
        for label in ("R1", "R2", "R3"):
            assert label in enc, f"{label} missing from encoding text"
        for label in ("R4", "R5", "R6"):
            assert label in ref, f"{label} missing from reflection text"
        print("  OK  R1-R3 in encoding, R4-R6 in reflection")

        # v3 two-call signal parsed: in-feed action from Call A, follow-through
        # next_step from Call B. The model may emit each JSON line without its
        # label — what matters is parse_behavioral_signal finds both.
        sig = transcript.behavioral_signal
        assert sig is not None, "v3 behavioral_signal did not parse"
        assert sig.action in (
            "scroll_past", "linger", "tap_cta", "save", "share"
        ), f"bad Call A action: {sig.action}"
        assert sig.next_step in (
            "buy_now", "buy_at_restock", "research_first", "mention_to_someone", "nothing"
        ), f"bad Call B next_step: {sig.next_step}"
        print(f"  OK  signal parsed: action={sig.action!r} next_step={sig.next_step!r}")
        print(f"      action_reasoning: {sig.action_reasoning}")
        print(f"      next_step_reasoning: {sig.next_step_reasoning}")

        # Idempotent resume: a second call loads artifacts, fires no API calls.
        rd = run_dir(_RUN, account_id=_ACCOUNT, brand_profile_id=_BRAND)
        tele_lines_before = len((rd / "telemetry.jsonl").read_text().splitlines())
        run_agent(agent, config, pack, run_id=_RUN, render_cache_dir=_RENDER_CACHE)
        tele_lines_after = len((rd / "telemetry.jsonl").read_text().splitlines())
        assert tele_lines_after == tele_lines_before, (
            "idempotent resume fired new API calls"
        )
        print("  OK  idempotent resume — re-run fired zero new agent calls")

        # Caching invariant — re-measure the floor against the rendered prefix.
        events = [
            json.loads(line)
            for line in (rd / "telemetry.jsonl").read_text().splitlines()
            if line.strip()
        ]
        agent_events = [e for e in events if e.get("layer") == "agent"]
        enc_ev = next(e for e in agent_events if e.get("round_num") == 1)
        ref_ev = next(e for e in agent_events if e.get("round_num") == 4)
        cw = enc_ev.get("cache_creation_tokens") or 0
        cr = ref_ev.get("cache_read_tokens") or 0
        assert cw >= 1500, f"Encoding cache_creation_tokens too low: {cw}"
        assert cr >= 1500, f"Reflection cache_read_tokens too low: {cr}"
        assert abs(cw - cr) <= 100, (
            f"cache-pair mismatch: creation={cw} read={cr} (diff {abs(cw - cr)})"
        )
        print(f"  OK  caching invariant holds — Encoding writes {cw} tokens, "
              f"Reflection reads {cr} (re-measured floor)")

        # Output budget.
        for e in agent_events:
            out = e.get("output_tokens") or 0
            assert out <= 1300, f"output_tokens {out} over budget"
        print("  OK  output token budget held (<= 1300 with R7)")

        print("PASS — runtime emits R1-R7, parses R7, caches, resumes idempotently.")
    finally:
        _cleanup()


@pytest.mark.paid
def test_runtime_fires_one_agent_end_to_end() -> None:
    """Costs ~$0.03 of real API calls. Skipped unless --paid is passed.

    ⚠ Until 2026-08-22 this file had no `test_` function at all: pytest
    collected zero from it while it sat in tests/ named test_*.py. It was
    run by hand, which means in practice it was not run."""
    main()


if __name__ == "__main__":
    main()
