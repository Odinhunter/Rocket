"""Offline: the persona-render warm-up in prepare() runs CONCURRENTLY and
carries the telemetry context across the thread hop.

Both properties are invisible in a green suite and expensive to get wrong.

CONCURRENCY. `warm_render_cache` was a plain serial `for` loop until
2026-08-13. It looked fine for months because the render cache was always
warm — a cold library is one ~13s API call per unique core, so session 38's
60-core panel turned prepare() into a 13-minute wait. That is what every new
category and every customer's FIRST read would pay.

CONTEXT. `record_telemetry` reads `current_run_id` from a contextvar and
RETURNS EARLY when it is unset. A worker thread starts with an EMPTY context,
so the obvious `pool.submit(render, a)` renders correctly, BILLS correctly,
and writes ZERO telemetry rows — a silent hole in the record of a paid run.
The fix is a fresh `copy_context()` per task; this pins it.

⚠ These tests use a stub renderer and spend NOTHING.

Run: .venv/bin/python -m pytest tests/test_render_cache_warming.py -q
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import run_service
from agent.panel import PanelAgent
from agent.telemetry import (
    current_account_id,
    current_brand_profile_id,
    current_run_id,
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

_GEOGRAPHIES = [
    "Bangalore / metro tier-1", "Mumbai / metro tier-1",
    "Delhi / metro tier-1", "Pune / metro tier-1",
    "Chennai / metro tier-1", "Hyderabad / metro tier-1",
]


def _agent(i: int, *, geography: str | None = None) -> PanelAgent:
    """One panel agent. `geography` feeds persona_core_hash, so distinct
    values give distinct cores and equal values collide — which is what makes
    the dedupe assertion below non-vacuous."""
    demo = DemographicPoint(
        gender="male", age_band="25_34", income_tier="upper_mid",
        geography=geography if geography is not None else _GEOGRAPHIES[i],
        occupation_hint="software engineer at a mid-stage SaaS startup",
    )
    disposition = NamedDisposition(
        label="pragmatist_protein_snacker",
        vector=DispositionVector(
            category_relationship="regular", brand_stance="neutral",
            price_orientation="price_first", decision_driver="function",
            category_involvement="low", prior_experience_valence="neutral",
            channel_behavior="offline_first", life_stage="early_career",
        ),
        anchor="You buy a protein bar when the vending machine has one.",
    )
    context = NamedContext(
        label="commute",
        vector=ContextVector(
            attention_level="low", device_posture="commute",
            intent_state="killing_time", energy_state="drained",
            social_setting="public",
        ),
    )
    chaos = ChaosProfile(
        label="moderate",
        vector=ChaosVector(
            decision_velocity="moderate", suggestibility="medium",
            consistency="variable", risk_tolerance="balanced",
        ),
    )
    return PanelAgent(
        agent_id=i, demographic=demo, disposition=disposition,
        context=context, chaos=chaos, category="health_wellness_nutrition",
    )


def test_warm_render_cache_renders_concurrently(monkeypatch, tmp_path) -> None:
    """Six cores with a blocking renderer must not take six sleeps.

    The assertion is on OVERLAP, not on wall-clock speed: a slow machine can
    make any duration bound flaky, but two renders being in flight at the same
    instant is a fact about the code, not about the hardware.
    """
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    def _stub(*_args, **_kwargs) -> str:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.05)
        with lock:
            in_flight -= 1
        return "prose"

    monkeypatch.setattr(run_service, "render_persona_core", _stub)
    panel = [_agent(i) for i in range(6)]

    n = run_service.warm_render_cache(
        panel, object(), tmp_path, max_concurrent=6
    )

    assert n == 6, f"expected 6 unique cores, got {n}"
    assert peak > 1, (
        "renders never overlapped — the warm-up is running SERIALLY. On a cold "
        "60-core library that is a 13-minute prepare()."
    )


def test_max_concurrent_is_respected(monkeypatch, tmp_path) -> None:
    """The bound is the same `max_concurrent_agents` the L1/L2 rounds use.
    Without it a 200-core library would open 200 sockets at once."""
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    def _stub(*_args, **_kwargs) -> str:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.05)
        with lock:
            in_flight -= 1
        return "prose"

    monkeypatch.setattr(run_service, "render_persona_core", _stub)
    panel = [_agent(i) for i in range(6)]

    run_service.warm_render_cache(panel, object(), tmp_path, max_concurrent=2)

    assert peak <= 2, f"ran {peak} at once with max_concurrent=2"


def test_workers_see_the_telemetry_context(monkeypatch, tmp_path) -> None:
    """⚠ THE ONE THAT MATTERS. Each render must observe the run/account/brand
    contextvars, or `record_telemetry` no-ops and a paid run records nothing.

    Mutation-proof: swap the `contextvars.copy_context().run` submit in
    `warm_render_cache` for a bare `pool.submit(_render, a)` and this test
    fails with every value None, while the two tests above still pass.
    """
    seen: list[tuple] = []
    lock = threading.Lock()

    def _stub(*_args, **_kwargs) -> str:
        with lock:
            seen.append((
                current_run_id.get(),
                current_account_id.get(),
                current_brand_profile_id.get(),
            ))
        return "prose"

    monkeypatch.setattr(run_service, "render_persona_core", _stub)

    current_run_id.set("20260813_test_run")
    current_account_id.set("demo")
    current_brand_profile_id.set("health_wellness_demo")

    panel = [_agent(i) for i in range(4)]
    run_service.warm_render_cache(panel, object(), tmp_path, max_concurrent=4)

    assert len(seen) == 4, f"expected 4 renders, saw {len(seen)}"
    for run_id, account_id, brand_id in seen:
        assert run_id == "20260813_test_run", (
            "a worker thread did NOT see current_run_id. record_telemetry "
            "returns early when it is None, so this run would bill in full "
            "and write an EMPTY telemetry.jsonl."
        )
        assert account_id == "demo", "worker lost current_account_id"
        assert brand_id == "health_wellness_demo", (
            "worker lost current_brand_profile_id — telemetry would be filed "
            "outside the account, at runs/<run_id>/"
        )


def test_unique_cores_are_rendered_once_each(monkeypatch, tmp_path) -> None:
    """Dedupe survived the rewrite: identical cores are one render, and the
    returned count is unique cores, not panel size."""
    calls = []
    lock = threading.Lock()

    def _stub(*_args, **_kwargs) -> str:
        with lock:
            calls.append(1)
        return "prose"

    monkeypatch.setattr(run_service, "render_persona_core", _stub)

    # Three distinct people, each appearing twice.
    panel = [
        _agent(i, geography=_GEOGRAPHIES[i % 3]) for i in range(6)
    ]
    hashes = {a.persona_core_hash for a in panel}
    assert len(hashes) == 3, (
        f"fixture is wrong: expected 3 distinct cores, got {len(hashes)}"
    )

    n = run_service.warm_render_cache(
        panel, object(), tmp_path, max_concurrent=6
    )

    assert n == 3, f"expected 3 unique cores, got {n}"
    assert len(calls) == 3, f"rendered {len(calls)} times, expected 3"


def test_a_failed_render_is_loud(monkeypatch, tmp_path) -> None:
    """A render that raises must propagate. Swallowing it would leave a
    half-warmed cache looking like a prepared run, and the missing core would
    only surface mid-way through the ~$4 paid round."""
    def _stub(*_args, **_kwargs) -> str:
        raise RuntimeError("render_persona_core: model returned empty prose")

    monkeypatch.setattr(run_service, "render_persona_core", _stub)
    panel = [_agent(i) for i in range(4)]

    with pytest.raises(RuntimeError, match="empty prose"):
        run_service.warm_render_cache(
            panel, object(), tmp_path, max_concurrent=4
        )


def test_empty_panel_renders_nothing(monkeypatch, tmp_path) -> None:
    """No panel, no pool, no crash."""
    def _stub(*_args, **_kwargs) -> str:  # pragma: no cover — must not run
        raise AssertionError("rendered something for an empty panel")

    monkeypatch.setattr(run_service, "render_persona_core", _stub)
    assert run_service.warm_render_cache(
        [], object(), tmp_path, max_concurrent=4
    ) == 0
