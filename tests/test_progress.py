"""Progress reporting — the middle of a run.

The two properties worth testing are the two hazards the module exists to
handle: a reader must never catch a half-written file, and the writes must be
throttled without letting the counter stick short of its total.
"""

from __future__ import annotations

import json
import threading

import pytest

from agent.progress import (
    DONE, PHASE_KEYS, ProgressWriter, phase_view, read_progress,
)


class FakeClock:
    """Injected so the throttle is testable without sleeping."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _writer(tmp_path, **kw) -> ProgressWriter:
    return ProgressWriter(tmp_path, clock=FakeClock(), **kw)


# ---- phases ----


def test_phase_writes_immediately(tmp_path):
    w = _writer(tmp_path)
    w.phase("reactions", total=100)
    p = read_progress(tmp_path)
    assert p["phase"] == "reactions"
    assert p["label"] == "The panel is reacting"
    assert p["total"] == 100
    assert p["done"] == 0
    assert p["phase_index"] == 1
    assert p["phase_count"] == len(PHASE_KEYS)


def test_unknown_phase_is_refused(tmp_path):
    """A typo'd phase key must fail loudly rather than write a blank label —
    the label is what the client-facing surface renders."""
    w = _writer(tmp_path)
    with pytest.raises(ValueError, match="unknown phase"):
        w.phase("reacting")


def test_entering_a_phase_resets_the_counter(tmp_path):
    """Otherwise the previous phase's count shows under the new phase's label:
    'Grouping by buyer type — 100 of 15'."""
    w = _writer(tmp_path)
    w.phase("reactions", total=100)
    for _ in range(40):
        w.advance()
    w.phase("segments", total=15)
    p = read_progress(tmp_path)
    assert p["done"] == 0
    assert p["total"] == 15


def test_finish_marks_complete(tmp_path):
    w = _writer(tmp_path)
    w.phase("prescription")
    w.finish()
    assert read_progress(tmp_path)["phase"] == DONE


# ---- throttling ----


def test_advance_is_throttled_between_phase_boundaries(tmp_path):
    """~100 agent completions must not mean 100 writes for a page that
    reloads every 10 seconds."""
    clock = FakeClock()
    w = ProgressWriter(tmp_path, clock=clock, min_interval=2.0)
    w.phase("reactions", total=100)
    for _ in range(50):
        clock.now += 0.1          # 5 seconds of work, no boundary crossed
        w.advance()
    # 5s at a 2s interval: writes at 2s and 4s. The counter is behind on disk,
    # which is the trade, but it is never AHEAD and never invented.
    assert read_progress(tmp_path)["done"] < 50


def test_the_last_unit_of_a_phase_always_flushes(tmp_path):
    """Without this the display sits at 99/100 for as long as the next phase
    takes to start — which for L1->L2 is the whole of L2."""
    clock = FakeClock()
    w = ProgressWriter(tmp_path, clock=clock, min_interval=1_000_000.0)
    w.phase("reactions", total=3)
    w.advance()
    w.advance()
    assert read_progress(tmp_path)["done"] == 0   # throttled hard
    w.advance()                                    # completes the phase
    assert read_progress(tmp_path)["done"] == 3


def test_a_phase_with_no_total_never_forces_a_flush(tmp_path):
    """population/diagnosis/prescription have no denominator; `done >= total`
    must not be evaluated against None."""
    clock = FakeClock()
    w = ProgressWriter(tmp_path, clock=clock, min_interval=1_000_000.0)
    w.phase("population")
    w.advance()
    assert read_progress(tmp_path)["done"] == 0


# ---- a status file must never be able to fail a paid run ----


def test_a_failing_write_never_escapes(tmp_path):
    """⚠ advance() is called from a `finally` in the L1 agent wrapper, so an
    exception here would REPLACE a successful agent's return value: gather
    would see an exception, reconcile_l1_results would count the agent
    dropped, and a transcript we already paid for would be thrown away. On a
    full disk that happens to every agent at once and aborts the whole
    committed run — ~$4 lost to a cosmetic file."""
    from unittest.mock import patch

    w = ProgressWriter(tmp_path, min_interval=0.0)
    with patch("agent.progress._atomic_write",
               side_effect=OSError("No space left on device")):
        w.phase("reactions", total=10)   # must not raise
        w.advance()                       # must not raise
        w.finish()                        # must not raise


def test_a_failing_write_does_not_break_a_committed_run(tmp_path):
    """The same property, driven through the real run path."""
    from unittest.mock import patch

    import agent.run_service as rs

    with patch("agent.progress._atomic_write", side_effect=OSError("disk full")):
        report = _drive_commit(rs, tmp_path)
    assert report.verdict == "MIXED"     # the run finished anyway


# ---- atomicity ----


def test_a_reader_never_catches_a_half_written_file(tmp_path):
    """The writer is the run's worker thread; the reader is a sync route in
    Starlette's threadpool. A plain overwrite lets the reader see a truncated
    document — and Launcher.status swallows JSONDecodeError into {}, so the
    failure would surface as a run reporting status 'unknown' mid-flight.
    """
    w = ProgressWriter(tmp_path, min_interval=0.0)
    w.phase("reactions", total=2000)
    stop = threading.Event()
    failures: list[str] = []

    def _write() -> None:
        for _ in range(2000):
            w.advance()
        stop.set()

    def _read() -> None:
        while not stop.is_set():
            if read_progress(tmp_path) is None:
                # None here can only mean unreadable or invalid JSON: the file
                # already exists, because phase() wrote it before this started.
                failures.append("read a corrupt or missing progress.json")
                return

    t_w = threading.Thread(target=_write)
    t_r = threading.Thread(target=_read)
    t_r.start(); t_w.start()
    t_w.join(); t_r.join(timeout=5)
    assert not failures


def test_no_tmp_file_is_left_behind(tmp_path):
    w = _writer(tmp_path)
    w.phase("reactions", total=1)
    w.advance()
    assert [p.name for p in tmp_path.iterdir()] == ["progress.json"]


# ---- reading ----


def test_read_progress_is_none_when_absent(tmp_path):
    assert read_progress(tmp_path) is None


def test_read_progress_is_none_when_corrupt(tmp_path):
    (tmp_path / "progress.json").write_text("{not json")
    assert read_progress(tmp_path) is None


def test_read_progress_is_none_when_not_an_object(tmp_path):
    """json.loads succeeds on a bare list; every caller does .get() on it."""
    (tmp_path / "progress.json").write_text("[1, 2, 3]")
    assert read_progress(tmp_path) is None


# ---- the view ----


def test_phase_view_marks_done_running_and_pending(tmp_path):
    w = _writer(tmp_path)
    w.phase("population")
    view = phase_view(read_progress(tmp_path))
    assert [e["state"] for e in view] == [
        "done", "done", "running", "pending", "pending",
    ]


def test_phase_view_carries_the_count_only_on_the_running_phase(tmp_path):
    # min_interval=0 so the advance is not throttled: the frozen fake clock
    # never moves, so any positive interval would suppress the write.
    w = ProgressWriter(tmp_path, clock=FakeClock(), min_interval=0.0)
    w.phase("reactions", total=100)
    w.advance(63)
    view = phase_view(read_progress(tmp_path))
    assert view[0]["done"] == 63 and view[0]["total"] == 100
    assert all("total" not in e for e in view[1:])


def test_phase_view_of_nothing_is_all_pending(tmp_path):
    """A committed run whose first phase has not reported yet must not show a
    phase already running."""
    assert [e["state"] for e in phase_view(None)] == ["pending"] * 5


def test_phase_view_after_finish_marks_every_phase_done(tmp_path):
    w = _writer(tmp_path)
    w.phase("reactions", total=1)
    w.finish()
    assert [e["state"] for e in phase_view(read_progress(tmp_path))] == ["done"] * 5


def test_phase_view_survives_a_progress_file_from_another_version(tmp_path):
    """An unrecognised phase key must not raise on a page that is only trying
    to say what the run is doing."""
    assert [e["state"] for e in phase_view({"phase": "quantum_leap"})] == \
        ["pending"] * 5


def test_phase_view_ignores_a_non_integer_total(tmp_path):
    """total arrives from a file on disk, so it is not trusted to be an int."""
    view = phase_view({"phase": "reactions", "done": 3, "total": "lots"})
    assert "total" not in view[0]


# ---- the server surfaces it ----


def _committed_run(tmp_path, status="committed"):
    """A runs_root holding one run at the given status."""
    rd = tmp_path / "acct" / "brand" / "run1"
    rd.mkdir(parents=True)
    (rd / "run.json").write_text(json.dumps({
        "run_id": "run1", "status": status, "updated_at": "2026-08-02T00:00:00",
    }))
    return tmp_path, rd


def test_launcher_status_carries_the_progress_file(tmp_path):
    from server.launcher import Launcher

    runs_root, rd = _committed_run(tmp_path)
    w = ProgressWriter(rd, min_interval=0.0)
    w.phase("reactions", total=100)
    w.advance(41)

    status = Launcher().status(runs_root, "acct/brand/run1")
    assert status["progress"]["phase"] == "reactions"
    assert status["progress"]["done"] == 41


def test_launcher_status_is_fine_with_no_progress_file(tmp_path):
    """A run committed a second ago has not written a phase yet."""
    from server.launcher import Launcher

    runs_root, _ = _committed_run(tmp_path)
    assert Launcher().status(runs_root, "acct/brand/run1")["progress"] is None


def test_the_status_page_shows_the_phases_while_running(tmp_path):
    from server import pages

    runs_root, rd = _committed_run(tmp_path)
    w = ProgressWriter(rd, min_interval=0.0)
    w.phase("reactions", total=100)
    w.advance(63)
    from server.launcher import Launcher
    html = pages.run_status_page(Launcher().status(runs_root, "acct/brand/run1"))

    assert "The panel is reacting" in html
    assert "63" in html and "100" in html
    assert "Ranking the fixes" in html          # the phases still to come


def test_the_status_page_does_not_show_phases_once_complete(tmp_path):
    """Five ticks under the word 'Done.' say nothing the word does not, and a
    stale running phase would contradict it."""
    from server import pages
    from server.launcher import Launcher

    runs_root, rd = _committed_run(tmp_path, status="complete")
    ProgressWriter(rd, min_interval=0.0).phase("reactions", total=100)
    html = pages.run_status_page(Launcher().status(runs_root, "acct/brand/run1"))
    assert "The panel is reacting" not in html


def test_a_dead_run_shows_where_it_stopped(tmp_path):
    """The launcher keeps progress on a failed run precisely so this page can
    say WHERE — it decides whether replay_synthesis can recover the run."""
    from server import pages
    from server.launcher import Launcher

    runs_root, rd = _committed_run(tmp_path, status="interrupted")
    ProgressWriter(rd, min_interval=0.0).phase("segments", total=15)
    html = pages.run_status_page(Launcher().status(runs_root, "acct/brand/run1"))

    assert "Grouping by buyer type" in html
    assert "stopped here" in html
    # and it must not read as still in flight
    assert 'class="running"' not in html


def test_a_running_run_is_not_marked_stopped(tmp_path):
    from server import pages
    from server.launcher import Launcher

    runs_root, rd = _committed_run(tmp_path)
    ProgressWriter(rd, min_interval=0.0).phase("segments", total=15)
    html = pages.run_status_page(Launcher().status(runs_root, "acct/brand/run1"))
    assert "stopped here" not in html
    assert 'class="running"' in html


def test_the_status_page_says_so_when_nothing_has_reported_yet(tmp_path):
    from server import pages
    from server.launcher import Launcher

    runs_root, _ = _committed_run(tmp_path)
    html = pages.run_status_page(Launcher().status(runs_root, "acct/brand/run1"))
    assert "Waiting for the first phase" in html


# ---- the engine's contract with this module ----


N_AGENTS, N_SEGMENTS = 10, 4


def _drive_commit(rs, tmp_path, spy=None):
    """Run the real `_commit_async` with every model call stubbed out.

    Every third agent RAISES, so any test using this also exercises the
    partial-panel path.
    """
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import patch

    panel = [SimpleNamespace(agent_id=i, segment_key=f"seg{i % N_SEGMENTS}")
             for i in range(N_AGENTS)]
    config = SimpleNamespace(
        category="c", max_concurrent_agents=4, account_id="a",
        brand_profile_id="b", funnel_enabled=False, baseline_funnel=None,
        provided_inputs=lambda: {},
        creative_inputs=SimpleNamespace(purpose="direct_sell"),
    )
    prep = SimpleNamespace(
        config=config, panel=panel, run_id="r1",
        target_classification=None, provisional_dispositions=[],
    )
    async def _agent(agent, *a, **kw):
        # Every third agent fails. The counter must still reach its total —
        # the denominator is work attempted, and a panel that loses agents
        # must not leave the display stuck below 100% forever.
        if agent.agent_id % 3 == 0:
            raise RuntimeError("agent died")
        return SimpleNamespace(agent_id=agent.agent_id, to_dict=lambda: {})

    def _report(*a, on_phase=None, **kw):
        if on_phase is not None:
            on_phase("diagnosis")
            on_phase("prescription")
        return SimpleNamespace(
            verdict="MIXED", confidence=70, pain_map=[], bet_ranking=[],
        )

    real_phase = rs.ProgressWriter.phase

    def _phase(self, key, *, total=None):
        # Capture the OUTGOING phase's counter as the next one starts — after
        # phase() runs it has been reset, so this is the only moment the L1
        # total is observable.
        if spy is not None:
            spy.append((key, self.done, self.total))
        return real_phase(self, key, total=total)

    with patch.object(rs, "load_pack", return_value=None), \
         patch.object(rs, "_render_cache_dir", return_value=tmp_path), \
         patch.object(rs, "run_agent_async", _agent), \
         patch.object(rs, "reconcile_l1_results",
                      lambda p, r, **k: ([x for x in r
                                          if not isinstance(x, Exception)], [])), \
         patch.object(rs, "synthesize_segment_async",
                      lambda label, ts, cfg: _done(SimpleNamespace(
                          segment_label=label, to_dict=lambda: {}))), \
         patch.object(rs, "synthesize_population",
                      lambda *a, **k: SimpleNamespace(to_dict=lambda: {})), \
         patch.object(rs, "project_funnel",
                      lambda *a, **k: SimpleNamespace(to_dict=lambda: {})), \
         patch.object(rs.calibration_log, "record_prediction", lambda *a, **k: None), \
         patch.object(rs, "synthesize_report", _report), \
         patch.object(rs, "frozen_painmap_from_report", lambda r: {}), \
         patch.object(rs.ProgressWriter, "phase", _phase):
        report, _health = asyncio.run(rs.RunService._commit_async(prep, tmp_path))
    return report


def test_the_whole_run_reports_its_phases_in_order(tmp_path):
    """Drives the real `_commit_async` with the model calls stubbed out.

    ⚠ This replaces a source-text assertion that looked fine and was VACUOUS:
    it matched `finally:\\n<20 spaces>progress.advance()`, which is ALSO the
    shape of the L2 block, so breaking the L1 one left it green. The mutation
    harness caught it. Text assertions on a pattern that appears twice in a
    file test nothing — so this drives the behaviour instead.
    """
    import agent.run_service as rs

    seen: list[tuple] = []
    _drive_commit(rs, tmp_path, spy=seen)

    assert [key for key, _, _ in seen] == [
        "reactions", "segments", "population", "diagnosis", "prescription",
    ]
    # finish() does not route through phase(), so it is checked on disk.
    assert read_progress(tmp_path)["phase"] == DONE
    # ⭐ The assertion the vacuous source-text test was reaching for: when the
    # segments phase begins, all 10 agents are counted even though 4 of them
    # RAISED. Without the `finally`, this reads 6 and the display would stick
    # at 6/10 for the rest of the run.
    _, l1_done, l1_total = seen[1]
    assert (l1_done, l1_total) == (N_AGENTS, N_AGENTS)
    # And the L2 counter closed out too.
    _, l2_done, l2_total = seen[2]
    assert (l2_done, l2_total) == (N_SEGMENTS, N_SEGMENTS)


async def _done(value):
    return value


def test_a_failing_agent_still_advances_the_counter(tmp_path):
    """The L1 wrapper advances in a `finally`. Tested directly on the writer,
    because the property is 'a raise does not skip the advance'."""
    w = ProgressWriter(tmp_path, min_interval=0.0)
    w.phase("reactions", total=3)

    def _one(should_raise):
        try:
            if should_raise:
                raise RuntimeError("agent died")
        finally:
            w.advance()

    for raises in (True, False, True):
        try:
            _one(raises)
        except RuntimeError:
            pass
    assert read_progress(tmp_path)["done"] == 3


def test_synthesize_report_reports_both_of_its_passes():
    """assess and prescribe are separately reportable only from inside
    synthesize_report — from the caller they are one to_thread call, and
    together they are the last minutes of a run."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    import agent.synthesis_l4 as l4
    seen: list[str] = []
    config = SimpleNamespace(audience_spec=None)
    l3 = SimpleNamespace(confidence_signals=None)
    with patch.object(l4, "assess_reactions", return_value=MagicMock()), \
         patch.object(l4, "prescribe_from_painmap",
                      side_effect=RuntimeError("stop here")):
        with pytest.raises(RuntimeError, match="stop here"):
            l4.synthesize_report(
                [], l3, None, None, config, on_phase=seen.append,
            )
    # Order matters: each fires BEFORE the pass it names, so the page says
    # what is happening now rather than what just finished.
    assert seen == ["diagnosis", "prescription"]
