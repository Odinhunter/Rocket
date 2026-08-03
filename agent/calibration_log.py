"""Calibration scaffolding (rocket-2.0.0, Phase 7).

The L3.5 funnel projection ships as `heuristic_v1` — a multiplier table,
NOT fitted to real in-market outcomes. This module is the infrastructure
that makes a future fit possible: it logs, per run, the prediction inputs
and the predicted funnel, with a placeholder slot for the customer's real
outcome.

This is NOT the calibration itself (fitting the multiplier table to
outcomes needs N customers' worth of prediction/outcome pairs first). It
is the append-only ledger that accumulates those pairs.

Storage is brand-scoped — runs/<account>/<brand>/calibration_log.jsonl —
because the entries contain the customer's real baseline funnel and (once
record_outcome is called) their real in-market numbers. It must never live
in a shared location.

Append-only JSONL, two record types:
  {"type": "prediction", "run_id": ..., "multiplier_table_version": ...,
   "baseline_funnel": ..., "projection": ...}
  {"type": "outcome",    "run_id": ..., "actual_funnel": ...}
A reader joins them by run_id.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent.projection_l35 import MULTIPLIER_TABLE_VERSION
from agent.schema import FunnelProjection
from agent.telemetry import runs_root


def _log_path(account_id: str, brand_profile_id: str) -> Path:
    return runs_root() / account_id / brand_profile_id / "calibration_log.jsonl"


def _append(account_id: str, brand_profile_id: str, entry: dict) -> None:
    path = _log_path(account_id, brand_profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_prediction(
    run_id: str,
    account_id: str,
    brand_profile_id: str,
    projection: FunnelProjection,
    baseline_funnel: dict | None,
) -> None:
    """Log the L3.5 prediction for a run. Stamps MULTIPLIER_TABLE_VERSION so
    every logged prediction is attributable to a specific calibration
    regime — a later fit can filter to one regime's predictions."""
    _append(
        account_id, brand_profile_id,
        {
            "type": "prediction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "multiplier_table_version": MULTIPLIER_TABLE_VERSION,
            "baseline_funnel": baseline_funnel,
            "projection": projection.to_dict(),
        },
    )


def record_outcome(
    run_id: str,
    account_id: str,
    brand_profile_id: str,
    actual_funnel: dict,
) -> None:
    """Attach a run's real in-market funnel outcome. Called by a future
    customer-feedback flow once the creative has run on Meta and the real
    stop/click/visit/convert rates are known. Append-only — joins to the
    prediction record by run_id."""
    _append(
        account_id, brand_profile_id,
        {
            "type": "outcome",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "actual_funnel": actual_funnel,
        },
    )


def load_calibration_pairs(
    account_id: str, brand_profile_id: str
) -> list[dict]:
    """Read the log and join prediction + outcome records by run_id. Returns
    one dict per run that has a prediction: {run_id, multiplier_table_version,
    baseline_funnel, projection, actual_funnel|None}. This is the shape a
    future calibration fit consumes."""
    path = _log_path(account_id, brand_profile_id)
    if not path.exists():
        return []
    predictions: dict[str, dict] = {}
    outcomes: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("type") == "prediction":
            predictions[rec["run_id"]] = rec
        elif rec.get("type") == "outcome":
            outcomes[rec["run_id"]] = rec["actual_funnel"]
    pairs = []
    for run_id, pred in predictions.items():
        pairs.append(
            {
                "run_id": run_id,
                "multiplier_table_version": pred["multiplier_table_version"],
                "baseline_funnel": pred["baseline_funnel"],
                "projection": pred["projection"],
                "actual_funnel": outcomes.get(run_id),
            }
        )
    return pairs
