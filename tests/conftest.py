"""Suite-wide guards. Both are about money and about real client data.

`server/app.py` has carried the sentence "Nothing in the offline suite may
reach RunService" since the app was built. It was a comment, and on
2026-08-04 it turned out to be false: three tests in test_server_runs.py
called the real `Launcher.commit`, which spawned a thread into the real
`RunService.commit`, which wrote real directories under `runs/`.

It cost nothing, but only by accident — that fixture's panel is empty, so no
agent was ever dispatched. Nothing pinned that. A fixture with a populated
panel would have started a paid run from `pytest`.

So the sentence is executable now. A comment cannot fail; this can.
"""

from __future__ import annotations

import pytest

from agent import run_service

# --------------------------------------------------------------------------
# The paid tier
# --------------------------------------------------------------------------
#
# ⚠⚠ WHY THIS EXISTS. Seven files in tests/ were named `test_*.py`, lived in
# this directory, and pytest collected ZERO functions from any of them — they
# were `main()` scripts run by hand and, in practice, never run. `pytest tests/`
# reported success over a suite that silently excluded them.
#
#   FIVE ARE PAID (they call the real API): render, runtime, synthesis,
#   run_service_minimal, target_id_effort.
#   ⚠⚠ ~$3.50-4.00 THE LOT, not the ~$1.93 quoted until 2026-08-22. The old
#   number took test_run_service_minimal's own docstring at its word, and that
#   docstring priced ONE end-to-end run while the test performs TWO (commit,
#   then RunService.run). Corrected at both sites. This repo quotes costs
#   honestly on principle — the probe that was quoted $0.30 and cost $0.38 is
#   written up for the same reason.
#   TWO WERE FREE AND SIMPLY NEVER RAN: test_panel_resilience.py (guards against
#   synthesizing a verdict on a gutted panel) and test_l4_homog_guard.py. Both
#   say "Offline" in their own docstrings. Those are now plain collected tests.
#
# ⭐ THE PAID FIVE ARE SKIPPED, NOT DESELECTED. `addopts = -m "not paid"` would
# hide them from the summary line, which recreates "looks covered, isn't" in a
# new form — the exact defect this is fixing. A visible `5 skipped` on every run
# is the point.


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--paid", action="store_true", default=False,
        help="run the tests that call the real API and cost real money (~$3.50-4.00)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "paid: calls the real API and spends real money; needs --paid",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    if config.getoption("--paid"):
        return
    skip = pytest.mark.skip(reason="paid: pass --paid to run, costs real money")
    for item in items:
        if "paid" in item.keywords:
            item.add_marker(skip)


class PaidEngineReached(AssertionError):
    """A test called the thing that spends ~$4."""


# Appended to from whichever thread made the call. A plain list is enough:
# list.append is atomic under the GIL, and this only ever needs to answer
# "did anything reach it during this test".
_REACHED: list[str] = []


@pytest.fixture(autouse=True)
def never_reach_the_paid_engine(monkeypatch: pytest.MonkeyPatch, request):
    """Replace `RunService.commit` for every test in the suite, and FAIL if a
    test reaches it.

    Autouse and unconditional: an opt-in guard protects the tests that
    remembered to ask for it, which are not the ones that need it.

    ⚠ Raising is not sufficient on its own, and this was verified rather than
    assumed. `Launcher.commit` runs the engine on a worker thread and records
    exceptions on `job.error` instead of propagating them — so with only the
    raise, the three offending tests went green while still having ATTEMPTED
    the paid path. A guard that silently succeeds is how the next person
    reintroduces the bug. Hence the post-test assertion below: the attempt
    itself fails the test that made it, wherever it was made from.

    A test that genuinely needs commit's machinery should override
    `Launcher._run_engine`, which is the seam that exists for exactly that.
    """
    # ⚠⚠ THE ONE EXEMPTION, AND IT IS DELIBERATELY NARROW. `test_run_service_
    # minimal.py` IS the end-to-end paid smoke: reaching prepare() and commit()
    # is the whole thing it tests, so under this guard it could never pass even
    # with --paid. It is exempt only when BOTH conditions hold — the test carries
    # @pytest.mark.paid AND the operator passed --paid. Either alone keeps the
    # guard on, so a stray marker cannot open the door by itself.
    #
    # ⭐ For every other test the guard stays exactly as unconditional as it was:
    # autouse, no opt-in, because an opt-in guard protects the tests that
    # remembered to ask for it, which are not the ones that need it.
    if "paid" in request.keywords and request.config.getoption("--paid"):
        yield
        return

    def _refuse(prep):  # noqa: ANN001 — signature mirrors the real one
        _REACHED.append(getattr(prep, "run_id", "<unknown run>"))
        raise PaidEngineReached(
            "RunService.commit was called from the test suite. That is the "
            "~$4 paid path and it writes into the real runs/ directory. "
            "Override Launcher._run_engine in your test double instead."
        )

    monkeypatch.setattr(run_service.RunService, "commit", staticmethod(_refuse))
    # prepare() is the cheaper paid call (~$0.15) and nothing in the suite
    # reaches it today — the whole run is offline in ~2.6s. Guarded anyway:
    # commit was also "obviously" unreachable until it wasn't.
    monkeypatch.setattr(run_service.RunService, "prepare", staticmethod(_refuse))
    _REACHED.clear()
    yield
    reached = list(_REACHED)
    _REACHED.clear()
    assert not reached, (
        f"this test reached the paid engine for {reached}. The call was "
        f"blocked, but Launcher.commit swallows worker-thread exceptions onto "
        f"job.error, so nothing else here would have failed. Override "
        f"Launcher._run_engine in the test double instead."
    )


@pytest.fixture(autouse=True)
def runs_root_is_absolute() -> None:
    """The engine's runs directory must never be cwd-relative again.

    `RUNS_DIR = Path("runs")` was resolved against the working directory, so
    `create_app(runs_root=tmp_path)` did not move where the engine WROTE — it
    only moved where the server READ. Tests polluted real client runs, and in
    production a container started outside the repo root would have completed
    a paid run into a directory the app never reads.
    """
    from agent.telemetry import runs_root

    assert runs_root().is_absolute(), (
        "agent.telemetry.runs_root() is relative — it resolves against the "
        "working directory, which is how the suite wrote into the real runs/"
    )
