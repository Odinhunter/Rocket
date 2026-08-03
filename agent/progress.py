"""Live progress for a committed run.

A run takes minutes — median 6.8, fastest 3.8 across the 33 completed runs on
disk — and until now the engine could report nothing at all between "committed"
and "complete". `run.json` is written exactly three times (run_service.py:472,
492, 496) and `panel_health` only lands at the end, so a browser watching a run
had one bit of information for six minutes.

This module is the missing middle. It writes a small `progress.json` beside
`run.json`: which of the five phases is running, and how far through the two
that have a countable denominator (L1 agents, L2 segments).

**Everything here is honest or absent.** There is no interpolation, no
estimated time remaining, and no bar that fills on a timer — the counter moves
when an agent actually finishes and not before. A progress display that
invents motion is worse than none, because the one thing it is for is telling
you whether the run is alive.

Two hazards shape the implementation:

**The write must be atomic.** The writer is the run's worker thread; the reader
is a sync route in Starlette's threadpool, and it can arrive mid-write. A plain
overwrite would let it read a truncated document — and `Launcher.status`
swallows `json.JSONDecodeError` into `{}`, so the failure would surface as a
run mysteriously reporting status `unknown` halfway through. Same fix the rest
of the engine already uses: write a temp file in the same directory, then
`replace()` it, which is atomic on POSIX.

**The writes must be throttled.** ~100 agent completions against a page that
reloads every 10 seconds does not need 100 writes to disk. Phase boundaries
always write (they are rare and they are the interesting events); counter
advances write at most every `min_interval` seconds, with the last one in a
phase always flushed so the display never sticks at 99/100.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

PROGRESS_FILENAME = "progress.json"

# The five phases of a committed run, in order, with the words the client-facing
# surface uses. Keyed labels rather than free strings so a renderer cannot drift
# from the engine: run_service calls these by key, the server renders the label.
PHASES: tuple[tuple[str, str], ...] = (
    ("reactions", "The panel is reacting"),
    ("segments", "Grouping by buyer type"),
    ("population", "Building the population picture"),
    ("diagnosis", "Diagnosing the problems"),
    ("prescription", "Ranking the fixes"),
)

PHASE_KEYS: tuple[str, ...] = tuple(key for key, _ in PHASES)
PHASE_LABELS: dict[str, str] = dict(PHASES)

# Written once the report exists. Not one of the five: it is the absence of a
# running phase, and the status page keys off run.json for "complete" anyway.
DONE = "complete"


def _atomic_write(path: Path, payload: dict) -> None:
    """Write so a concurrent reader sees either the old file or the new one.

    Mirrors run_service._persist_json rather than importing it: this module is
    imported *by* the runtime, and reaching back into run_service would make
    that a cycle.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)


@dataclass
class ProgressWriter:
    """Records phase and count for one run.

    Thread-safe by a plain `threading.Lock`, deliberately and not by an
    `asyncio.Lock`: `advance()` is called from coroutines on the run's event
    loop, but `phase()` is also called from `synthesize_report`, which runs
    under `asyncio.to_thread`. Two different threads touch this object, so the
    lock has to be a thread lock.
    """

    run_dir: Path
    min_interval: float = 2.0
    # Injected so the throttle is testable without sleeping. monotonic, not
    # wall-clock: this is measuring an interval, and a clock adjustment
    # mid-run must not stall or spam the writes.
    clock: object = time.monotonic

    phase_key: str = ""
    done: int = 0
    total: int | None = None
    started_at: float = field(default_factory=time.time)
    _last_write: float = field(default=0.0)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def path(self) -> Path:
        return self.run_dir / PROGRESS_FILENAME

    # ---- writing ----

    def phase(self, key: str, *, total: int | None = None) -> None:
        """Enter a phase. Always writes — boundaries are the rare, useful events.

        Resets the counter, so a caller cannot leave the previous phase's count
        showing under a new phase's label.
        """
        if key not in PHASE_LABELS and key != DONE:
            raise ValueError(
                f"unknown phase {key!r} — expected one of "
                f"{', '.join(PHASE_KEYS)} or {DONE!r}"
            )
        with self._lock:
            self.phase_key = key
            self.done = 0
            self.total = total
            self._write_locked()

    def advance(self, n: int = 1) -> None:
        """One more unit of the current phase finished.

        Throttled, EXCEPT when it completes the phase — otherwise the display
        can sit at 99/100 for as long as the next phase takes to start.
        """
        with self._lock:
            self.done += n
            complete = self.total is not None and self.done >= self.total
            now = float(self.clock())
            if complete or (now - self._last_write) >= self.min_interval:
                self._write_locked()

    def finish(self) -> None:
        """The report exists; no phase is running."""
        with self._lock:
            self.phase_key = DONE
            self.done = 0
            self.total = None
            self._write_locked()

    def _write_locked(self) -> None:
        """⚠ NEVER propagates an I/O failure. This is the load-bearing line of
        the module.

        `advance()` is called from a `finally` inside the L1 agent wrapper, so
        an exception raised here would REPLACE a successful agent's return
        value: `asyncio.gather(return_exceptions=True)` would see an exception,
        `reconcile_l1_results` would count the agent dropped, and a transcript
        we already paid for would be discarded. A full disk would do that to
        every agent at once and abort the whole committed run — losing ~$4 to a
        cosmetic status file.

        The engine's posture two functions down says it plainly: survive a
        stray failure rather than crash a run whose money is already spent. A
        progress file is the least important artifact here and must never be
        able to fail the most important one.
        """
        self._last_write = float(self.clock())
        try:
            self._write_payload()
        except OSError as exc:
            _log.warning("could not write %s: %s", self.path, exc)

    def _write_payload(self) -> None:
        _atomic_write(self.path, {
            "phase": self.phase_key,
            "phase_index": (
                PHASE_KEYS.index(self.phase_key) + 1
                if self.phase_key in PHASE_KEYS else len(PHASE_KEYS)
            ),
            "phase_count": len(PHASE_KEYS),
            "label": PHASE_LABELS.get(self.phase_key, ""),
            "done": self.done,
            "total": self.total,
            "started_at": self.started_at,
            "updated_at": time.time(),
        })


def read_progress(run_dir: Path) -> dict | None:
    """What the run last reported, or None.

    Returns None rather than raising for every reason a reader legitimately
    arrives early or late: no file yet (the run just committed), an unreadable
    one, or a document that is not an object. The caller is a status page; a
    missing progress file is a normal state, not an error.
    """
    path = Path(run_dir) / PROGRESS_FILENAME
    try:
        raw = json.loads(path.read_text())
    except (FileNotFoundError, NotADirectoryError, json.JSONDecodeError,
            UnicodeDecodeError, PermissionError, IsADirectoryError):
        return None
    return raw if isinstance(raw, dict) else None


def phase_view(progress: dict | None) -> list[dict]:
    """The five phases with each marked done / running / pending.

    Built here rather than in a template so the terminal, the operator page and
    the eventual client app cannot disagree about which phase a run is in.
    """
    key = (progress or {}).get("phase") or ""
    if key == DONE:
        here = len(PHASE_KEYS)
    elif key in PHASE_KEYS:
        here = PHASE_KEYS.index(key)
    else:
        here = -1

    out = []
    for i, (phase_key, label) in enumerate(PHASES):
        state = "pending"
        if here >= 0:
            state = "done" if i < here else ("running" if i == here else "pending")
        entry = {"key": phase_key, "label": label, "state": state}
        if state == "running" and progress:
            total = progress.get("total")
            if isinstance(total, int) and total > 0:
                done = progress.get("done")
                entry["done"] = done if isinstance(done, int) else 0
                entry["total"] = total
        out.append(entry)
    return out
