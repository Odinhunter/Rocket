"""Phase 5 offline test: the credit-debit state machine. prepare() debits
nothing (no marker exists yet); commit() debits exactly once; a second
commit() does NOT double-debit. No API calls — this exercises agent/
credits.py directly, which is the load-bearing idempotency guarantee.

Run: python tests/test_two_phase_state.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import credits
from agent.telemetry import RUNS_DIR

_ACCOUNT = "_test_two_phase_acct"
_BRAND = "_test_two_phase_brand"


def _cleanup() -> None:
    p = RUNS_DIR / _ACCOUNT
    if p.exists():
        shutil.rmtree(p)


def test_prepare_state_debits_nothing() -> None:
    """Before any commit, is_committed is False and the account has 0
    debits — prepare() must never touch credits."""
    _cleanup()
    try:
        assert credits.is_committed("run_a", _ACCOUNT, _BRAND) is False
        assert credits.account_debits(_ACCOUNT) == 0
        print("  OK  pre-commit: is_committed False, account debits 0")
    finally:
        _cleanup()


def test_commit_debits_exactly_once() -> None:
    _cleanup()
    try:
        first = credits.debit_for_run("run_a", _ACCOUNT, _BRAND)
        assert first is True, "first debit should record"
        assert credits.is_committed("run_a", _ACCOUNT, _BRAND) is True
        assert credits.account_debits(_ACCOUNT) == 1

        # Second commit on the SAME run — must not double-debit.
        second = credits.debit_for_run("run_a", _ACCOUNT, _BRAND)
        assert second is False, "second debit should be a no-op"
        assert credits.account_debits(_ACCOUNT) == 1, "double-debit occurred!"
        print("  OK  commit debits exactly once; re-commit is a no-op")
    finally:
        _cleanup()


def test_distinct_runs_debit_separately() -> None:
    _cleanup()
    try:
        credits.debit_for_run("run_a", _ACCOUNT, _BRAND)
        credits.debit_for_run("run_b", _ACCOUNT, _BRAND)
        credits.debit_for_run("run_b", _ACCOUNT, _BRAND)  # idempotent no-op
        assert credits.account_debits(_ACCOUNT) == 2, (
            "two distinct runs should debit 2 credits total"
        )
        print("  OK  distinct runs debit separately; each is idempotent")
    finally:
        _cleanup()


def test_committed_marker_is_a_real_file() -> None:
    _cleanup()
    try:
        credits.debit_for_run("run_a", _ACCOUNT, _BRAND)
        marker = RUNS_DIR / _ACCOUNT / _BRAND / "run_a" / "committed.marker"
        assert marker.exists(), "committed.marker not written"
        ledger = RUNS_DIR / _ACCOUNT / "credits_ledger.jsonl"
        assert ledger.exists(), "credits ledger not written"
        print("  OK  committed.marker + credits_ledger.jsonl written on debit")
    finally:
        _cleanup()


def main() -> None:
    print("=== two-phase credit-debit state machine ===")
    test_prepare_state_debits_nothing()
    test_commit_debits_exactly_once()
    test_distinct_runs_debit_separately()
    test_committed_marker_is_a_real_file()
    print("PASS — credit is debited exactly once, at commit, idempotently.")


if __name__ == "__main__":
    main()
