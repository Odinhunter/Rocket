"""Run state persistence for batch_run.py.

PopulationReport, TargetClassification, and StrategicCritique serialize
to `runs/<run_id>/run.json` after each meaningful state change. A crash
in any layer leaves a recoverable on-disk artifact. Per-round
checkpoint.json carries histories, failures, current_round, and specs
(explicit, not re-derived from SEED — robust to refactors of
build_agent_specs).

Telemetry primitives (`record_telemetry`, `current_run_id`,
`call_with_telemetry`, `make_run_id`, `run_dir`, `telemetry_summary`)
live in `agent/telemetry.py` and are re-exported here for
backward-import convenience. They are split out so runner / synthesis
can record telemetry without pulling in synthesis dataclasses (which
would create a circular import).

Schema notes:
- `verbatim_archive` keys (aid, stim, round) flatten to "aid:stim:round"
- `spec_by_agent` keys (int) → str(k); disposition/context/cell_key tuples → list
- `HomogenizationFlag.cell` (tuple) → list
- All int keys in dicts (per_round_narrative, free_text_jaccard) → str(k)
- Tuples-as-values are JSON-serialized as lists; load reconstructs explicitly
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from agent.runner import RunResult
from agent.synthesis import (
    ComparativeMetrics,
    DisagreementAxis,
    DispositionTarget,
    Finding,
    HomogenizationFlag,
    MethodologyDiagnostics,
    OutlierFinding,
    PopulationReport,
    StrategicCritique,
    StructuredFindings,
    TargetClassification,
    WithinCellDescription,
)
from agent.telemetry import (
    RUNS_DIR,
    call_with_telemetry,
    current_run_id,
    make_run_id,
    record_telemetry,
    run_dir,
    telemetry_summary,
)

_log = logging.getLogger(__name__)

__all__ = [
    "RUNS_DIR",
    "call_with_telemetry",
    "current_run_id",
    "dump_checkpoint",
    "dump_run",
    "load_checkpoint",
    "load_run",
    "make_run_id",
    "record_telemetry",
    "run_dir",
    "telemetry_summary",
]


# ---- Run state serialization ----


def dump_run(
    run_id: str,
    *,
    config: dict,
    population_report: PopulationReport | None = None,
    target_classification: TargetClassification | None = None,
    strategic_critique: StrategicCritique | None = None,
) -> None:
    """Atomically write runs/<run_id>/run.json with the latest state.

    Each call overwrites the prior file. Caller invokes after every
    meaningful state change so crash recovery has the most recent snapshot.
    """
    path = run_dir(run_id) / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "run_id": run_id,
        "config": config,
        "population_report": (
            _serialize_population_report(population_report) if population_report else None
        ),
        "target_classification": (
            _serialize_target_classification(target_classification)
            if target_classification else None
        ),
        "strategic_critique": (
            _serialize_strategic_critique(strategic_critique)
            if strategic_critique else None
        ),
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def load_run(run_id: str) -> dict:
    """Load runs/<run_id>/run.json into a dict with reconstructed dataclasses.

    Keys: 'run_id', 'config', 'population_report' (PopulationReport | None),
    'target_classification' (TargetClassification | None),
    'strategic_critique' (StrategicCritique | None).
    """
    path = run_dir(run_id) / "run.json"
    raw = json.loads(path.read_text())
    return {
        "run_id": raw["run_id"],
        "config": raw["config"],
        "population_report": (
            _deserialize_population_report(raw["population_report"])
            if raw.get("population_report") else None
        ),
        "target_classification": (
            _deserialize_target_classification(raw["target_classification"])
            if raw.get("target_classification") else None
        ),
        "strategic_critique": (
            _deserialize_strategic_critique(raw["strategic_critique"])
            if raw.get("strategic_critique") else None
        ),
    }


# ---- Checkpoint (per-round resume) ----


def dump_checkpoint(
    run_id: str,
    *,
    config: dict,
    specs: list[dict],
    histories: dict[tuple[int, str], list[RunResult]],
    failures: dict[tuple[int, str], list[tuple[int, str]]],
    current_round: int,
) -> None:
    """Write runs/<run_id>/checkpoint.json after a round completes.

    Serializes RunResult.messages so resume can chain prior= correctly.
    Specs persisted explicitly — resume does not re-derive from SEED.
    """
    path = run_dir(run_id) / "checkpoint.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "config": config,
        "current_round": current_round,
        "specs": [_serialize_spec(s) for s in specs],
        "histories": {
            f"{aid}:{stim}": [_serialize_run_result(r) for r in hist]
            for (aid, stim), hist in histories.items()
        },
        "failures": {
            f"{aid}:{stim}": list(items)
            for (aid, stim), items in failures.items()
        },
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def load_checkpoint(run_id: str) -> dict:
    """Load checkpoint into deserialized form for resume.

    Returns: {'config', 'current_round', 'specs', 'histories', 'failures'}
    where histories is dict[tuple[int, str], list[RunResult]] (tuple keys
    restored), failures is dict[tuple[int, str], list[tuple[int, str]]].
    """
    path = run_dir(run_id) / "checkpoint.json"
    raw = json.loads(path.read_text())

    histories: dict[tuple[int, str], list[RunResult]] = {}
    for key, results in raw["histories"].items():
        aid_str, stim = key.split(":", 1)
        histories[(int(aid_str), stim)] = [_deserialize_run_result(r) for r in results]

    failures: dict[tuple[int, str], list[tuple[int, str]]] = {}
    for key, items in raw["failures"].items():
        aid_str, stim = key.split(":", 1)
        failures[(int(aid_str), stim)] = [tuple(item) for item in items]

    specs = [_deserialize_spec(s) for s in raw["specs"]]

    return {
        "config": raw["config"],
        "current_round": raw["current_round"],
        "specs": specs,
        "histories": histories,
        "failures": failures,
    }


# ---- Internal: serialize ----


def _serialize_spec(spec: dict) -> dict:
    return {
        "agent_id": spec["agent_id"],
        "disposition": list(spec["disposition"]) if spec.get("disposition") else None,
        "context": list(spec["context"]) if spec.get("context") else None,
        "seed_idx": spec.get("seed_idx"),
        "cell_key": list(spec["cell_key"]) if spec.get("cell_key") else None,
    }


def _deserialize_spec(data: dict) -> dict:
    return {
        "agent_id": data["agent_id"],
        "disposition": tuple(data["disposition"]) if data.get("disposition") else None,
        "context": tuple(data["context"]) if data.get("context") else None,
        "seed_idx": data.get("seed_idx"),
        "cell_key": tuple(data["cell_key"]) if data.get("cell_key") else None,
    }


def _serialize_run_result(r: RunResult) -> dict:
    return {
        "output": r.output,
        "disposition": list(r.disposition) if r.disposition else None,
        "context": list(r.context) if r.context else None,
        "messages": r.messages,
        "round_num": r.round_num,
        "parsed": r.parsed,
    }


def _deserialize_run_result(data: dict) -> RunResult:
    return RunResult(
        output=data["output"],
        disposition=tuple(data["disposition"]) if data.get("disposition") else None,
        context=tuple(data["context"]) if data.get("context") else None,
        messages=data.get("messages") or [],
        round_num=data["round_num"],
        parsed=data.get("parsed"),
    )


def _serialize_population_report(report: PopulationReport) -> dict:
    return {
        "diagnostics": _serialize_diagnostics(report.diagnostics),
        "within_cell": _serialize_within_cell(report.within_cell),
        "comparative": _serialize_comparative(report.comparative),
        "findings": _serialize_findings(report.findings),
        "verbatim_archive": {
            f"{aid}:{stim}:{rnd}": text
            for (aid, stim, rnd), text in report.verbatim_archive.items()
        },
        "spec_by_agent": {
            str(aid): _serialize_spec(spec)
            for aid, spec in report.spec_by_agent.items()
        },
    }


def _serialize_diagnostics(d: MethodologyDiagnostics) -> dict:
    return {
        "homogenization_flags": [
            {
                "cell": list(f.cell),
                "stimulus": f.stimulus,
                "round_num": f.round_num,
                "metric": f.metric,
                "detail": f.detail,
            }
            for f in d.homogenization_flags
        ],
        "parse_failure_rate": dict(d.parse_failure_rate),
        "dropouts": list(d.dropouts),
        "sample_size_warning": d.sample_size_warning,
    }


def _serialize_within_cell(w: WithinCellDescription) -> dict:
    return {
        "round_3_per_dimension": _serialize_round_3_per_dimension(
            w.round_3_per_dimension
        ),
        "round_1_categorical": w.round_1_categorical,
        # int keys → str
        "free_text_jaccard": {
            str(rnd): per_stim for rnd, per_stim in w.free_text_jaccard.items()
        },
    }


def _serialize_round_3_per_dimension(per_dim: dict) -> dict:
    """cell_ranges[i]['cell'] is a tuple — convert to list for JSON."""
    out = {}
    for dim, stims in per_dim.items():
        out[dim] = {}
        for stim_id, data in stims.items():
            out[dim][stim_id] = {
                "across_cell_range": data.get("across_cell_range", 0),
                "within_cell_mean_range": data.get("within_cell_mean_range", 0),
                "cell_ranges": [
                    {
                        "cell": list(cr["cell"]),
                        "scores": list(cr["scores"]),
                        "range": cr["range"],
                        "mean": cr["mean"],
                    }
                    for cr in data.get("cell_ranges", [])
                ],
            }
    return out


def _serialize_comparative(c: ComparativeMetrics) -> dict:
    return {
        "round_3_deltas": c.round_3_deltas,
        "round_1_attention_dist": c.round_1_attention_dist,
        # int keys → str
        "per_round_narrative": {
            str(rnd): text for rnd, text in c.per_round_narrative.items()
        },
    }


def _serialize_findings(f: StructuredFindings) -> dict:
    return {
        "consensus": [asdict(x) for x in f.consensus],
        "disagreement_axes": [asdict(x) for x in f.disagreement_axes],
        "outliers": [asdict(x) for x in f.outliers],
    }


def _serialize_target_classification(tc: TargetClassification) -> dict:
    return {
        "inferred_target_description": tc.inferred_target_description,
        "target_reasoning": tc.target_reasoning,
        "disposition_classifications": [
            asdict(dc) for dc in tc.disposition_classifications
        ],
        "ambiguity_note": tc.ambiguity_note,
        "no_match_note": tc.no_match_note,
    }


def _serialize_strategic_critique(sc: StrategicCritique) -> dict:
    return {
        "memo": sc.memo,
        "model": sc.model,
        "verdict_band": sc.verdict_band,
        "target_classification": (
            _serialize_target_classification(sc.target_classification)
            if sc.target_classification else None
        ),
    }


# ---- Internal: deserialize ----


def _deserialize_population_report(data: dict) -> PopulationReport:
    verbatim: dict[tuple[int, str, int], str] = {}
    for key, text in data["verbatim_archive"].items():
        aid_str, stim, rnd_str = key.split(":")
        verbatim[(int(aid_str), stim, int(rnd_str))] = text

    return PopulationReport(
        diagnostics=_deserialize_diagnostics(data["diagnostics"]),
        within_cell=_deserialize_within_cell(data["within_cell"]),
        comparative=_deserialize_comparative(data["comparative"]),
        findings=_deserialize_findings(data["findings"]),
        verbatim_archive=verbatim,
        spec_by_agent={
            int(aid): _deserialize_spec(spec)
            for aid, spec in data["spec_by_agent"].items()
        },
    )


def _deserialize_diagnostics(data: dict) -> MethodologyDiagnostics:
    return MethodologyDiagnostics(
        homogenization_flags=[
            HomogenizationFlag(
                cell=tuple(f["cell"]),
                stimulus=f["stimulus"],
                round_num=f["round_num"],
                metric=f["metric"],
                detail=f["detail"],
            )
            for f in data["homogenization_flags"]
        ],
        parse_failure_rate=dict(data["parse_failure_rate"]),
        dropouts=list(data["dropouts"]),
        sample_size_warning=data.get("sample_size_warning"),
    )


def _deserialize_within_cell(data: dict) -> WithinCellDescription:
    out = WithinCellDescription()
    out.round_3_per_dimension = _deserialize_round_3_per_dimension(
        data["round_3_per_dimension"]
    )
    out.round_1_categorical = data["round_1_categorical"]
    out.free_text_jaccard = {
        int(rnd): per_stim for rnd, per_stim in data["free_text_jaccard"].items()
    }
    return out


def _deserialize_round_3_per_dimension(data: dict) -> dict:
    out = {}
    for dim, stims in data.items():
        out[dim] = {}
        for stim_id, sd in stims.items():
            out[dim][stim_id] = {
                "across_cell_range": sd.get("across_cell_range", 0),
                "within_cell_mean_range": sd.get("within_cell_mean_range", 0),
                "cell_ranges": [
                    {
                        "cell": tuple(cr["cell"]),
                        "scores": list(cr["scores"]),
                        "range": cr["range"],
                        "mean": cr["mean"],
                    }
                    for cr in sd.get("cell_ranges", [])
                ],
            }
    return out


def _deserialize_comparative(data: dict) -> ComparativeMetrics:
    out = ComparativeMetrics()
    out.round_3_deltas = data["round_3_deltas"]
    out.round_1_attention_dist = data["round_1_attention_dist"]
    out.per_round_narrative = {
        int(rnd): text for rnd, text in data["per_round_narrative"].items()
    }
    return out


def _deserialize_findings(data: dict) -> StructuredFindings:
    return StructuredFindings(
        consensus=[Finding(**x) for x in data["consensus"]],
        disagreement_axes=[DisagreementAxis(**x) for x in data["disagreement_axes"]],
        outliers=[OutlierFinding(**x) for x in data["outliers"]],
    )


def _deserialize_target_classification(data: dict) -> TargetClassification:
    return TargetClassification(
        inferred_target_description=data["inferred_target_description"],
        target_reasoning=data["target_reasoning"],
        disposition_classifications=[
            DispositionTarget(**dc) for dc in data["disposition_classifications"]
        ],
        ambiguity_note=data.get("ambiguity_note"),
        no_match_note=data.get("no_match_note"),
    )


def _deserialize_strategic_critique(data: dict) -> StrategicCritique:
    return StrategicCritique(
        memo=data["memo"],
        model=data["model"],
        verdict_band=data.get("verdict_band"),
        target_classification=(
            _deserialize_target_classification(data["target_classification"])
            if data.get("target_classification") else None
        ),
    )
