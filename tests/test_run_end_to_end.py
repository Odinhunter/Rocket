"""The paid path, driven end to end with only the model calls replaced.

Nothing had ever done this. On 2026-08-04 there were 66 runs on disk, two of
them started from the web form, and **zero** that finished through it — every
completed read had come from the CLI. So each link in the chain was tested and
the chain itself was not:

    upload → prepare → commit → worker thread → progress → complete → the read

What is REAL here: the routes, the auth, the form parsing and upload, the
Launcher's idempotency lock and non-daemon worker thread, `run_service`'s own
`_write_run_json`, `ProgressWriter`, `phase_view`, run-directory resolution,
`build_read_model`, and the renderer. What is faked is one method —
`Launcher._run_engine` — which in production is the single line that calls the
model ~100 times and spends ~$4.

The fake engine writes what the real one writes, through the same two writers
and in the same order (`committed` → phases → `complete` + Report), so the
states the app has to handle are produced rather than described.

⚠ It does NOT prove the model calls work. Those are proven by ~60 completed
CLI runs. It also does not reproduce the intermittent prepare failure of
2026-08-04 00:23, which is a separate open question.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.progress import PHASE_KEYS, ProgressWriter
from agent.run_service import _write_run_json
from agent.schema import Decision, Pain, Report, TargetMatch, TopChange
from agent.telemetry import run_dir, runs_root
from server.app import create_app
from server.launcher import Launcher
from tests.helpers_auth import demo_auth, sign_in
from tests.test_server_runs import StubLauncher, _prep

ACCOUNT, BRAND = "demo", "hw"


def _finished_report() -> Report:
    """Shaped like the real thing: a decision, a ranked change, a pain with
    evidence. The read surface refuses to render several of these as blanks,
    so a thinner fixture would prove the page renders rather than that it
    renders a read."""
    return Report(
        verdict="MIXED", confidence=74, target_match=TargetMatch(),
        top_3_changes=[TopChange(change="Put the price on the creative",
                                 why="nobody could tell what it costs")],
        strengths_to_preserve=[], context_fit_map={}, verbatim_consumer_voice=[],
        methodology_flags=["single_within_target"],
        pain_map=[Pain(id="P1", pain="No price anywhere on the frame. The "
                                     "engaged buyer defers the decision.",
                       funnel_stage="consider", severity="high",
                       within_target=True, cited_by=["a1", "a2"])],
        decision=Decision(
            decision="ITERATE", target_action_rate=0.1111, trust="DIRECTIONAL",
            target_action_num=2, target_action_denom=18,
            within_dispositions=["enthusiast_macros_lifter"],
            load_bearing_pain_id="P1", rationale="P1 is fixable"),
    )


class FakeEngine(StubLauncher):
    """The real Launcher, with only the ~$4 line replaced.

    `die_after` stops the worker mid-phase without ever writing `complete` —
    which is precisely the shape of a run whose process was killed, and the
    state that would strand a paid run if the app handled it badly.
    """

    def __init__(self, prep, *, report: Report | None = None,
                 die_after: str | None = None) -> None:
        super().__init__(prep)
        self.report = report
        self.die_after = die_after
        self.wrote_to: Path | None = None

    def _run_engine(self, prep) -> None:  # noqa: ANN001
        self.engine_calls.append(prep.run_id)
        config = prep.config
        rd = run_dir(prep.run_id, account_id=config.account_id,
                     brand_profile_id=config.brand_profile_id)
        rd.mkdir(parents=True, exist_ok=True)
        self.wrote_to = rd

        _write_run_json(config, prep.run_id, status="committed")
        # min_interval=0: the real writer throttles to one write every 2s, and
        # a test that honoured that would sleep for ten seconds to watch five
        # phases. The throttle itself is covered in test_progress.py.
        writer = ProgressWriter(run_dir=rd, min_interval=0.0)
        for key in PHASE_KEYS:
            writer.phase(key, total=2)
            writer.advance()
            if self.die_after == key:
                return          # thread exits; run.json is still "committed"
            writer.advance()
        _write_run_json(config, prep.run_id, status="complete",
                        report=self.report or _finished_report(),
                        panel_health={"succeeded": 100, "expected": 100,
                                      "degraded": False})


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo-shaped temp world whose runs directory is set the way P6 will
    set it in production — through the environment, not through an argument.

    `create_app` is deliberately NOT given `runs_root` below: the point is
    that the server and the engine derive it from one expression. Pass it
    explicitly and this test would keep passing while they diverged, which is
    the exact bug it exists to hold shut.
    """
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "hw_cold.json").write_text(
        (Path(__file__).resolve().parent.parent
         / "specs" / "health_wellness_cold_traffic.json").read_text())
    (tmp_path / "ad.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("ROCKET_RUNS_DIR", str(tmp_path / "runs"))
    return tmp_path


def _client(world: Path, launcher: Launcher) -> TestClient:
    return sign_in(TestClient(create_app(
        sessions_root=world / "sessions", base_dir=world,
        specs_dir=world / "specs", uploads_dir=world / "uploads",
        launcher=launcher, auth=demo_auth())))


def _drive(client: TestClient) -> str:
    """Upload → prepare → commit, exactly as a browser does it, and return the
    status URL the commit redirects to."""
    resp = client.post(
        "/reads/new",
        files={"asset": ("client_ad.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        data={"category": "health_wellness_nutrition",
              "audience_spec": "hw_cold.json"},
        follow_redirects=False)
    assert resp.status_code == 303, resp.text
    where = resp.headers["location"]
    for _ in range(300):                      # the prepare runs on a thread
        page = client.get(where, follow_redirects=False)
        if page.status_code == 303:
            where = page.headers["location"]
            continue
        if "Preparing the read" not in page.text:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("preparation never finished")

    run_id = client.app_run_id  # type: ignore[attr-defined]
    resp = client.post("/reads/prepared/commit", data={"run_id": run_id},
                       follow_redirects=False)
    assert resp.status_code == 303, resp.text
    return resp.headers["location"]


def _await(client: TestClient, url: str, marker: str, *, timeout: float = 10.0):
    """Poll the status page the way the browser's meta-refresh does."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(url)
        if marker in last.text:
            return last
        time.sleep(0.02)
    raise AssertionError(
        f"{marker!r} never appeared on {url}. Last page:\n{(last.text if last else '')[:1500]}")


def test_a_run_goes_from_upload_to_a_rendered_read(world: Path) -> None:
    """The whole chain, in one pass, on the real routes.

    This is the test that did not exist when the app was declared finished.
    """
    prep = _prep(world, spec_name="specs/hw_cold.json")
    launcher = FakeEngine(prep)
    client = _client(world, launcher)
    client.app_run_id = prep.run_id  # type: ignore[attr-defined]

    status_url = _drive(client)
    page = _await(client, status_url, "READ COMPLETE")

    # 1. The worker actually ran, and the ~$4 line was reached exactly once.
    assert launcher.engine_calls == [prep.run_id], launcher.engine_calls
    assert launcher.committed == [prep.run_id]

    # 2. ⚠ The run landed in the account/brand path, NOT the flat
    #    `runs/<run_id>` fallback telemetry.run_dir takes when either context
    #    var is unset. That fallback has already misfiled a run historically,
    #    and it is silent: the run completes and the app cannot see it.
    expected = runs_root() / prep.config.account_id / \
        prep.config.brand_profile_id / prep.run_id
    assert launcher.wrote_to == expected, launcher.wrote_to
    assert (expected / "run.json").exists()
    assert not (runs_root() / prep.run_id).exists(), "misfiled to the flat path"

    # ⚠ And it is inside THIS test's world. Without this, a runs_root() that
    # ignored ROCKET_RUNS_DIR would still satisfy every assertion above — both
    # sides would agree on the wrong directory — while this test quietly wrote
    # into the repo's real runs/, which is the bug it was written to close.
    assert world in expected.parents, (
        f"the run landed at {expected}, outside the test's world {world} — "
        f"ROCKET_RUNS_DIR was not honoured")

    # 3. The server READS the directory the engine WROTE. These were two
    #    different expressions until 2026-08-04.
    on_disk = json.loads((expected / "run.json").read_text())
    assert on_disk["status"] == "complete"
    assert on_disk["report"] is not None

    # 4. The completion screen, then the read itself.
    assert "ITERATE" in page.text
    key = f"{prep.config.account_id}/{prep.config.brand_profile_id}/{prep.run_id}"
    read = client.get(f"/reads/{key}")
    assert read.status_code == 200, read.text[:400]
    assert "PROBLEM MAP" in read.text, "the read did not render"
    assert "No price anywhere on the frame" in read.text, "the diagnosis is missing"
    # The guardrail that must survive every path to the page.
    from agent.read_model import VERDICT_CAVEAT
    from html import escape
    assert escape(VERDICT_CAVEAT, quote=True) in read.text
    print("  upload → prepare → commit → progress → complete → read ✓")


def test_the_status_page_reports_progress_while_the_run_is_alive(
        world: Path) -> None:
    """Between commit and completion the operator must see the run moving.

    The fake engine parks in the middle, so the assertion is made against a
    genuinely in-flight run rather than a hand-written progress.json.
    """
    import threading

    gate = threading.Event()
    prep = _prep(world, spec_name="specs/hw_cold.json")

    class Parked(FakeEngine):
        def _run_engine(self, p) -> None:  # noqa: ANN001
            rd = run_dir(p.run_id, account_id=p.config.account_id,
                         brand_profile_id=p.config.brand_profile_id)
            rd.mkdir(parents=True, exist_ok=True)
            _write_run_json(p.config, p.run_id, status="committed")
            ProgressWriter(run_dir=rd, min_interval=0.0).phase(
                PHASE_KEYS[1], total=100)
            gate.wait(timeout=5)
            super()._run_engine(p)

    launcher = Parked(prep)
    client = _client(world, launcher)
    client.app_run_id = prep.run_id  # type: ignore[attr-defined]
    try:
        status_url = _drive(client)
        live = _await(client, status_url, "RUNNING")
        assert "READ COMPLETE" not in live.text, \
            "a still-running run was reported as finished"
        assert (runs_root() / prep.config.account_id /
                prep.config.brand_profile_id / prep.run_id /
                "progress.json").exists(), "no progress was written"
    finally:
        gate.set()
    _await(client, status_url, "READ COMPLETE")
    print("  a live run reports progress, then completes ✓")


def test_a_run_whose_worker_dies_is_recoverable_not_lost(world: Path) -> None:
    """⚠ The state a killed process leaves: run.json stuck at `committed`,
    thread gone. ~$4 has been spent by this point, so the one thing the app
    must never do is call it "still running" forever or offer to pay again.

    It must say interrupted, and it must decide recoverability on whether the
    expensive half is on disk — transcripts — not on optimism.
    """
    prep = _prep(world, spec_name="specs/hw_cold.json")
    launcher = FakeEngine(prep, die_after=PHASE_KEYS[1])
    client = _client(world, launcher)
    client.app_run_id = prep.run_id  # type: ignore[attr-defined]

    status_url = _drive(client)
    for job in launcher.jobs.values():
        job.thread.join(timeout=5)

    rd = (runs_root() / prep.config.account_id /
          prep.config.brand_profile_id / prep.run_id)
    assert json.loads((rd / "run.json").read_text())["status"] == "committed", \
        "the fixture did not reproduce a dead worker"

    page = client.get(status_url)
    assert page.status_code == 200
    assert "interrupted" in page.text.lower(), \
        "a dead run still reads as running — the operator waits on nothing"
    # No transcripts on disk, so replay would spend money to fail.
    assert "paid for again" in page.text, \
        "an unrecoverable run must say so rather than offer a replay button"
    print("  a dead worker reads as interrupted, and does not offer a bad replay ✓")
