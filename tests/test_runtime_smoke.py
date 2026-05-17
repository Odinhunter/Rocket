"""API smoke: the agent runtime fires one PanelAgent end-to-end — renders
the persona core + context, runs bundled Encoding + Reflection, emits
R1-R7, parses the R7 behavioral signal, and holds the prompt-caching
invariant (Encoding writes the cache, Reflection reads it, the pair matches).

Also re-measures the cache-prefix token floor against the rendered-prose
prefix.

Cost: ~4 Sonnet calls (2 render + 2 agent), ~$0.03.

Run: python tests/test_runtime_smoke.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
            label="office_bru_pragmatist",
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
    asset_path = Path("assets/boat_ad.png")
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

        # R7 behavioral signal parsed. The model may emit the JSON line
        # without an "R7 ACTION:" label — what matters is parse_r7_signal
        # finds it, which is exactly what this asserts.
        sig = transcript.behavioral_signal
        assert sig is not None, "R7 behavioral_signal did not parse"
        assert sig.action in (
            "scroll_past", "linger", "tap_cta", "save", "share", "seek_info"
        ), f"bad R7 action: {sig.action}"
        assert isinstance(sig.would_act_within_week, bool)
        print(f"  OK  R7 parsed: action={sig.action!r} "
              f"would_act_within_week={sig.would_act_within_week}")
        print(f"      reasoning: {sig.reasoning}")

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


if __name__ == "__main__":
    main()
