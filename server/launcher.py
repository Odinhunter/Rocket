"""Starting a run from the browser — the paid half of the operator tool.

Two things make this different from every other module here: it spends money,
and it takes minutes. Both shape the design.

**Money.** `prepare()` is not free — it fires the target classifier (~$0.15 on
a warm render cache, more when persona cores miss) — and `commit()` is the ~$4
one. So the flow is the same two phases the CLI uses: prepare, show what it
found and what it will cost, and commit only on an explicit second action.
`batch_run.py` refuses to auto-commit through a gross demographic mismatch even
with --yes; the same refusal is enforced here, because the browser form has no
--yes to override in the first place and a click is easier than a flag.

**Time.** `RunService.commit` calls `asyncio.run()` internally, so it cannot run
inside the server's event loop at all — it runs on a worker thread, and the
route that starts it returns immediately. Status is NOT a new job-tracking
layer: the engine already writes `status` into run.json at each phase
(`prepared` → `committed` → `complete`), so polling is a file read of something
that was being persisted anyway. The only thing this module keeps in memory is
the crash reason, which run.json has nowhere to record.
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path

from agent.progress import read_progress
from agent.run_service import RunPreparation, RunService
from agent.telemetry import run_dir

_log = logging.getLogger(__name__)

# Categories with a hand-built, validated disposition library. An ad outside
# these does NOT fail gracefully: target_id lands on no_match, every persona
# classifies "outside", and the engine emits a confident and WRONG read — the
# worst possible artifact to put in front of a prospect. Authoring a library is
# a multi-day, >=30-source hand-build (docs/disposition_protocol_v2.md), so
# this is a gate to respect, not a warning to click past.
VALIDATED_CATEGORIES = frozenset({"health_wellness_nutrition"})


@dataclass
class Job:
    """A committed run executing on a worker thread."""

    run_id: str
    account_id: str
    brand_profile_id: str
    thread: threading.Thread
    error: str | None = None

    @property
    def key(self) -> str:
        return f"{self.account_id}/{self.brand_profile_id}/{self.run_id}"


@dataclass
class Preparing:
    """A prepare running on its own thread. Under a minute, but not instant."""

    token: str
    thread: threading.Thread
    prep: RunPreparation | None = None
    error: str | None = None

    @property
    def done(self) -> bool:
        return self.prep is not None or self.error is not None


@dataclass
class Launcher:
    """Prepared-but-uncommitted runs, and the threads running committed ones."""

    prepared: dict[str, RunPreparation] = field(default_factory=dict)
    jobs: dict[str, Job] = field(default_factory=dict)
    preparing: dict[str, Preparing] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ---- phase A ----

    def prepare(self, config) -> RunPreparation:
        """PAID. Classifies the ad and resolves the panel; debits no credit."""
        prep = RunService.prepare(config)
        with self._lock:
            self.prepared[prep.run_id] = prep
        return prep

    def prepare_async(self, config) -> str:
        """The same paid call, off the request thread, keyed by a token.

        `prepare` fires the target classifier and resolves the panel — tens of
        seconds, sometimes more on a cold persona-core cache. Doing that inside
        the POST means a browser sitting on a blank tab with a spinner it owns,
        no way to say what is happening, and a proxy free to time the request
        out and leave the operator thinking nothing ran. Running it here lets
        the browser land on a page that can say "classifying the creative".

        The thread is a daemon, unlike `commit`'s: no credit has been debited,
        so losing a prepare to a shutdown costs ~$0.15 and a retry, where
        losing a commit costs the run.
        """
        token = secrets.token_urlsafe(8)
        state = Preparing(token=token, thread=threading.Thread(target=lambda: None))

        def _run() -> None:
            try:
                # Through self.prepare, not RunService directly: that keeps ONE
                # entry point to the paid call, so a test double substitutes in
                # one place and cannot be bypassed by the async path.
                prep = self.prepare(config)
            except Exception as exc:  # noqa: BLE001 — surfaced on the page
                state.error = f"{type(exc).__name__}: {exc}"
                _log.exception("prepare %s failed", token)
                return
            # Set LAST: `done` flips on this, and a reader that saw prep before
            # `prepare` had registered it would redirect to a review page that
            # cannot find it.
            state.prep = prep

        state.thread = threading.Thread(target=_run, name=f"rocket-prep-{token}",
                                        daemon=True)
        with self._lock:
            self.preparing[token] = state
        state.thread.start()
        return token

    def preparation(self, token: str) -> Preparing | None:
        with self._lock:
            return self.preparing.get(token)

    def take(self, run_id: str) -> RunPreparation | None:
        with self._lock:
            return self.prepared.get(run_id)

    # ---- phase B ----

    def commit(self, prep: RunPreparation) -> Job:
        """PAID (~$4). Runs L1→L4 on a worker thread and returns immediately.

        The thread is NOT a daemon: a committed run has already debited a
        credit and is spending real money by the second, so the process stays
        alive until it finishes rather than losing the run — and the report —
        to a shutdown.
        """
        key = (f"{prep.config.account_id}/{prep.config.brand_profile_id}/"
               f"{prep.run_id}")
        with self._lock:
            existing = self.jobs.get(key)
            if existing is not None and existing.thread.is_alive():
                return existing  # idempotent: never pay twice for one click

        job = Job(run_id=prep.run_id, account_id=prep.config.account_id,
                  brand_profile_id=prep.config.brand_profile_id,
                  thread=threading.Thread(target=lambda: None))

        def _run() -> None:
            try:
                # commit() re-establishes its own telemetry context vars from
                # prep (run_service.py:480), so nothing needs plumbing across
                # the thread boundary.
                RunService.commit(prep)
            except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
                job.error = f"{type(exc).__name__}: {exc}"
                _log.exception("run %s failed on the worker thread", prep.run_id)

        job.thread = threading.Thread(
            target=_run, name=f"rocket-run-{prep.run_id}", daemon=False,
        )
        with self._lock:
            self.jobs[key] = job
            self.prepared.pop(prep.run_id, None)
        job.thread.start()
        return job

    # ---- recovery ----

    def replay(self, run_dir: Path, key: str) -> Job:
        """Re-run L2→L4 on transcripts already on disk.

        Costs real money — the synthesis layers go through the model — but a
        fraction of a full run, because the 100 agent calls that dominate the
        bill are read back from disk instead of being paid for twice. No credit
        is debited: the credit was spent when the run was committed.

        Non-daemon like `commit`, and for the same reason: it is spending.
        """
        account, brand, run_id = (key.split("/") + ["", "", ""])[:3]
        job = Job(run_id=run_id, account_id=account, brand_profile_id=brand,
                  thread=threading.Thread(target=lambda: None))

        def _run() -> None:
            try:
                import asyncio

                # Imported here, not at module scope: replay_synthesis is a
                # top-level script that loads .env on import, and the server
                # must not fail to start because a recovery tool is missing.
                from replay_synthesis import _replay

                asyncio.run(_replay(run_dir))
            except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
                job.error = f"{type(exc).__name__}: {exc}"
                _log.exception("replay %s failed", key)

        job.thread = threading.Thread(target=_run, name=f"rocket-replay-{run_id}",
                                      daemon=False)
        with self._lock:
            existing = self.jobs.get(key)
            if existing is not None and existing.thread.is_alive():
                return existing  # idempotent: one recovery at a time
            self.jobs[key] = job
        job.thread.start()
        return job

    # ---- status ----

    def status(self, runs_root: Path, key: str) -> dict:
        """What phase a run is in, read from the artifact the engine already
        writes. Falls back to the in-memory crash reason, which is the one
        thing run.json cannot record — a run that dies mid-L1 leaves its
        status at 'committed' forever, and reporting that as 'still running'
        would have the operator waiting on a thread that is gone."""
        account, brand, run_id = (key.split("/") + ["", "", ""])[:3]
        rd = runs_root / account / brand / run_id
        raw: dict = {}
        run_json = rd / "run.json"
        if run_json.exists():
            try:
                raw = json.loads(run_json.read_text())
            except json.JSONDecodeError:
                raw = {}

        job = self.jobs.get(key)
        status = raw.get("status", "unknown")
        alive = bool(job and job.thread.is_alive())
        error = job.error if job else None
        if error and status != "complete":
            status = "failed"
        elif job and not alive and status == "committed" and not error:
            # Thread gone, run.json never reached 'complete': the process was
            # restarted, or the run died in a way that escaped the handler.
            status = "interrupted"

        return {
            "key": key, "run_id": run_id, "status": status,
            "running": alive, "error": error,
            "updated_at": raw.get("updated_at", ""),
            "panel_health": raw.get("panel_health"),
            # replay_report.json counts: a recovered run has a real report,
            # it just is not the one run.json holds. discover_runs already
            # treats the two the same, and a status page that disagreed would
            # keep offering "recover" for a run that had been recovered.
            "has_report": bool(raw.get("report"))
                          or (rd / "replay_report.json").exists(),
            # The middle of the run — the only thing that moves during the
            # minutes run.json says nothing about. None until the first phase
            # lands, and left as-is on a failed run so the status page can say
            # WHERE it stopped rather than only that it did.
            "progress": read_progress(rd),
        }


def prepared_run_dir(prep: RunPreparation) -> Path:
    return run_dir(prep.run_id, account_id=prep.config.account_id,
                   brand_profile_id=prep.config.brand_profile_id)
