"""Credits — minimal filesystem-backed debit hook for the two-phase run.

v1 had no credit system. v2 needs the credit debit to happen at COMMIT,
never at prepare — so an abandoned prepare costs the customer nothing.

This is deliberately minimal: a per-account append-only ledger plus a
per-run `committed` marker file. The marker makes commit idempotent —
calling commit() twice on the same run debits exactly once. A real billing
backend (Stripe metered, per the pricing memo) replaces this later; the
debit *timing* and the idempotency guarantee are what matter and are
locked here.

1 credit = 1 Creative Read (the locked pricing unit).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent.telemetry import RUNS_DIR, run_dir


def _ledger_path(account_id: str) -> Path:
    return RUNS_DIR / account_id / "credits_ledger.jsonl"


def _committed_marker(
    run_id: str, account_id: str, brand_profile_id: str
) -> Path:
    return run_dir(
        run_id, account_id=account_id, brand_profile_id=brand_profile_id
    ) / "committed.marker"


def is_committed(run_id: str, account_id: str, brand_profile_id: str) -> bool:
    """True if this run has already had its credit debited."""
    return _committed_marker(run_id, account_id, brand_profile_id).exists()


def debit_for_run(
    run_id: str,
    account_id: str,
    brand_profile_id: str,
    *,
    credits: int = 1,
) -> bool:
    """Debit `credits` for a run, idempotently.

    Returns True if a debit was recorded, False if the run was already
    committed (no double-debit). Writes one ledger line on a real debit and
    drops a `committed` marker so a re-run / retry never debits twice.
    """
    marker = _committed_marker(run_id, account_id, brand_profile_id)
    if marker.exists():
        return False

    ledger = _ledger_path(account_id)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "brand_profile_id": brand_profile_id,
        "credits": credits,
        "unit": "creative_read",
    }
    with ledger.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({"committed_at": entry["timestamp"], "credits": credits})
    )
    return True


def account_debits(account_id: str) -> int:
    """Total credits debited for an account (sum of the ledger)."""
    ledger = _ledger_path(account_id)
    if not ledger.exists():
        return 0
    total = 0
    for line in ledger.read_text().splitlines():
        if line.strip():
            total += int(json.loads(line).get("credits", 0))
    return total
