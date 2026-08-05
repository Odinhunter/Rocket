#!/usr/bin/env python3
"""The gate test — does this instrument tell one ad from another?  ($0)

    .venv/bin/python scripts/gate_test.py [--runs-root runs]

Re-runs the two measurements in `docs/v3_engine_improvement_plan.md` §0 against
whatever is on disk. No API calls, no cost. Run it after any engine change: it
is the only check we have that answers "did that help?" rather than "does that
render?".

THE QUESTION
------------
A panel can produce output that matches the human distribution beautifully and
still have NO power to tell one product from another — fluent, plausible, and
decoration. So before improving anything, measure whether the numbers move with
the AD or only with the RUN.

  0a  the headline buy-intent rate:  spread across re-runs of ONE ad
                                     vs spread across DIFFERENT ads
  0b  the problem map:               pain-vocabulary overlap for re-runs of ONE
                                     ad vs for DIFFERENT ads

If re-runs of one ad disagree as much as different ads do, the number is noise.

⚠ reaction-v3 ONLY. An earlier pass pooled the v2 runs — a different protocol —
and got a scarier, wrong answer. Runs are grouped by asset label; the
"different ads" set takes the EARLIEST run of each distinct asset, so no ad is
represented twice.

⚠ 0b HAS NO SINGLE RIGHT TOKENIZATION, so this reports four. That is deliberate:
the same class of choice moved published human-vs-silicon correlations from
r = .23 to .84, and a result that survives only one arbitrary definition is not
a result. The conclusion here holds under all four; the headline figures in the
plan doc correspond to the stop+len4 row.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Common English words plus this domain's connective tissue. Only used by the
# two "stop" variants below — the unfiltered variants are reported beside them
# precisely so this list cannot quietly become the finding.
_STOP = set(
    "the a an and or but of to in on for with is are was were be been it its this "
    "that as at by from not no nothing they them their there then than so if which "
    "who what when where how why all any both each more most other some such only "
    "own same too very can will just do does did doing i you he she we our your his "
    "her me my one two".split()
)

_TOKEN = re.compile(r"[a-z']+")

_VARIANTS = (
    ("every word", lambda t: True),
    ("minus stopwords", lambda t: t not in _STOP),
    ("longer than 3", lambda t: len(t) > 3),
    ("stop + len>3", lambda t: len(t) > 3 and t not in _STOP),
)


def load_runs(runs_root: Path) -> dict[str, tuple[str, list]]:
    """Every finished reaction-v3 run: path -> (asset label, pain_map)."""
    out: dict[str, tuple[str, list]] = {}
    for run_json in sorted(runs_root.glob("*/*/*/run.json")):
        try:
            raw = json.loads(run_json.read_text())
        except (OSError, ValueError):
            continue
        if raw.get("reaction_protocol_version") != "reaction-v3":
            continue
        report = raw.get("report")
        if not report:
            continue
        label = ((raw.get("config") or {}).get("asset") or {}).get("label") or "(unlabelled)"
        out[str(run_json.parent)] = (label, report.get("pain_map") or [])
    return out


def _headline(run_path: str) -> tuple[float | None, int, int]:
    raw = json.loads((Path(run_path) / "run.json").read_text())
    d = (raw.get("report") or {}).get("decision") or {}
    return (d.get("target_action_rate"), d.get("target_action_num") or 0,
            d.get("target_action_denom") or 0)


def _vocab(pains: list, keep) -> set[str]:
    text = " ".join((p.get("pain") or "") for p in pains).lower()
    return {t for t in _TOKEN.findall(text) if keep(t)}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def _spread(values: list[float]) -> float:
    return max(values) - min(values) if values else 0.0


# ---- 0c: the convex-combination check (Neumann et al. QC1/QC2) ----
#
# A panel-wide average MUST be a weighted mean of its subgroups' averages. ~80%
# of tested models fail this when the "average" is GENERATED rather than
# counted: they emit a panel number more extreme than every subgroup inside it,
# which is geometrically impossible. This engine's stated invariant is that
# every distribution is a Python count over parsed signals
# (`agent/decision.py`, "distributions are Python"). This check is what proves
# that invariant still holds after a change instead of trusting the comment.
#
# ⚠ It reads the SIDECARS, not run.json. `report.funnel_projection` is None
# unless the run was made with `--funnel`, but the projection is computed and
# persisted either way — the real numbers live in `l35_projection.json` and
# `l3_summary.json`. Checking run.json alone silently checks nothing.

_FUNNEL_STAGES = ("stop_rate", "click_rate", "visit_rate", "convert_rate")

# Rates are floats derived by two different routes (pooled-then-multiplied vs
# per-segment), so exact equality is the wrong bar for the range comparison.
# Counts are integers and are compared exactly.
_RATE_TOL = 1e-9


def load_projections(runs_root: Path) -> dict[str, tuple[dict, dict]]:
    """Every finished reaction-v3 run that persisted both sidecars:
    path -> (l35_projection, l3_summary). Runs missing either are omitted, and
    the caller reports how many that was — a check whose denominator is
    invisible reads as coverage it does not have."""
    out: dict[str, tuple[dict, dict]] = {}
    for run_json in sorted(runs_root.glob("*/*/*/run.json")):
        rd = run_json.parent
        try:
            raw = json.loads(run_json.read_text())
        except (OSError, ValueError):
            continue
        if raw.get("reaction_protocol_version") != "reaction-v3":
            continue
        try:
            l35 = json.loads((rd / "l35_projection.json").read_text())
            l3 = json.loads((rd / "l3_summary.json").read_text())
        except (OSError, ValueError):
            continue
        out[str(rd)] = (l35, l3)
    return out


def load_decisions(runs_root: Path) -> dict[str, dict]:
    """Every finished reaction-v3 run's decision block: path -> decision dict.
    Separate from `load_runs` because that one is 0a/0b's shape and widening it
    would change what its callers unpack."""
    out: dict[str, dict] = {}
    for run_json in sorted(runs_root.glob("*/*/*/run.json")):
        try:
            raw = json.loads(run_json.read_text())
        except (OSError, ValueError):
            continue
        if raw.get("reaction_protocol_version") != "reaction-v3":
            continue
        decision = ((raw.get("report") or {}).get("decision")) or {}
        if decision:
            out[str(run_json.parent)] = decision
    return out


def _pooled_distribution(segments: list[dict]) -> dict:
    """Element-wise sum of the segment behavioural distributions — what the
    population distribution has to equal if it was pooled rather than
    invented."""
    counts: dict[str, int] = {}
    next_steps: dict[str, int] = {}
    n = 0
    for seg in segments:
        dist = seg.get("behavioral_distribution") or {}
        for key, val in (dist.get("counts") or {}).items():
            counts[key] = counts.get(key, 0) + val
        for key, val in (dist.get("next_step_counts") or {}).items():
            next_steps[key] = next_steps.get(key, 0) + val
        n += dist.get("n") or 0
    return {"counts": counts, "next_step_counts": next_steps, "n": n}


def qc1_pooling_identity(l35: dict, l3: dict) -> list[str]:
    """QC1 — is the population distribution the SUM of its segments? An
    integer identity, so any discrepancy is a defect and not a rounding
    artifact. This is the stronger half: if pooling holds, no downstream
    average computed from it can be out of range by construction."""
    segments = l35.get("by_segment") or []
    if not segments:
        return []
    pooled = _pooled_distribution(segments)
    population = l3.get("population_behavioral_distribution") or {}
    problems: list[str] = []
    if population.get("n") != pooled["n"]:
        problems.append(
            f"population n={population.get('n')} != sum of segment n={pooled['n']}"
        )
    for field in ("counts", "next_step_counts"):
        if (population.get(field) or {}) != pooled[field]:
            problems.append(
                f"population {field} != summed segment {field}: "
                f"{population.get(field)} vs {pooled[field]}"
            )
    return problems


def qc2_convexity(l35: dict) -> list[str]:
    """QC2 — does every overall funnel rate lie inside the range its segments
    span? A weighted mean cannot exceed its own maximum or fall below its own
    minimum; an overall outside that band means the panel number was not
    derived from the subgroups it claims to summarise.

    ⚠ The BANDS are deliberately not checked. `_band_halfwidth_fraction` widens
    with a small n, so the pooled panel's band is legitimately TIGHTER than
    every segment's — that is more evidence, not a violation. A future session
    adding a band check here would be adding a permanent false alarm."""
    segments = l35.get("by_segment") or []
    overall = l35.get("overall") or {}
    if len(segments) < 2 or not overall:
        return []
    problems: list[str] = []
    for stage in _FUNNEL_STAGES:
        values = [
            (seg.get("funnel_rates") or {}).get(stage)
            for seg in segments
        ]
        values = [v for v in values if v is not None]
        got = overall.get(stage)
        if got is None or not values:
            continue
        lo, hi = min(values), max(values)
        tol = _RATE_TOL * max(1.0, abs(hi))
        if not (lo - tol <= got <= hi + tol):
            problems.append(
                f"{stage}: overall {got:.6f} is outside the segment range "
                f"[{lo:.6f}, {hi:.6f}] spanned by {len(values)} segments"
            )
    return problems


def qc3_cycle_identity(decision: dict) -> list[str] | None:
    """QC3 — the same question asked of the DECISION layer, where the headline
    the read leads with is produced. `_buy_intent_by_cycle` and the headline are
    two independent implementations of one count over one frame, and
    `agent/decision.py` states the headline "is a weighted average over the
    panel's realised cycle mix". Because both partition the same frame this is
    an exact integer identity, not a range — a strictly stronger test than QC2.

    None when the run carries no cycle breakdown to check against (it is only
    built for the buy-frame purposes), which the caller counts as a SKIP rather
    than a pass."""
    by_cycle = decision.get("by_cycle_position") or {}
    if not by_cycle:
        return None
    num = sum(cell.get("num") or 0 for cell in by_cycle.values())
    denom = sum(cell.get("denom") or 0 for cell in by_cycle.values())
    problems: list[str] = []
    if num != decision.get("target_action_num"):
        problems.append(
            f"headline numerator {decision.get('target_action_num')} != "
            f"{num} summed over cycle positions"
        )
    if denom != decision.get("target_action_denom"):
        problems.append(
            f"headline denominator {decision.get('target_action_denom')} != "
            f"{denom} summed over cycle positions"
        )
    return problems


def main() -> None:
    from agent.telemetry import runs_root as _default_runs_root

    ap = argparse.ArgumentParser(description=__doc__)
    # ⚠ NOT Path("runs"). That is cwd-relative, and a relative runs path is a
    # bug this project has already paid for once: the engine wrote to
    # <cwd>/runs while the server read REPO_ROOT/runs. `runs_root()` returns an
    # absolute path and honours ROCKET_RUNS_DIR, which is how P6 points at the
    # mounted volume — so the gate test reads the same disk the runs are on.
    ap.add_argument("--runs-root", type=Path, default=_default_runs_root())
    args = ap.parse_args()

    runs = load_runs(args.runs_root)
    if not runs:
        raise SystemExit(f"no finished reaction-v3 runs under {args.runs_root}")

    by_asset: dict[str, list[str]] = defaultdict(list)
    for path, (label, _) in sorted(runs.items()):
        by_asset[label].append(path)

    # The repeated ad: whichever asset has the most re-runs. The comparison
    # needs at least two of the same thing to have any within-ad term at all.
    repeated_label, repeats = max(by_asset.items(), key=lambda kv: len(kv[1]))
    distinct = [paths[0] for _, paths in sorted(by_asset.items())]

    print("=" * 78)
    print("THE GATE TEST — does the instrument tell one ad from another?")
    print("=" * 78)
    print(f"  reaction-v3 runs with a report : {len(runs)}")
    print(f"  distinct ads                   : {len(by_asset)}")
    print(f"  repeated ad                    : {repeated_label} x{len(repeats)}")

    if len(repeats) < 2 or len(distinct) < 2:
        raise SystemExit("\nNot enough runs to compare — need one ad run twice "
                         "and at least two distinct ads.")

    # ---- 0a: the headline number ----
    print("\n" + "-" * 78)
    print("0a  THE HEADLINE BUY-INTENT NUMBER")
    print("-" * 78)
    within = [r for r in (_headline(p)[0] for p in repeats) if r is not None]
    between = [r for r in (_headline(p)[0] for p in distinct) if r is not None]
    print(f"  same ad, {len(within)} re-runs : "
          + ", ".join(f"{v:.1%}" for v in within))
    print(f"  {len(between)} different ads   : "
          + ", ".join(f"{v:.1%}" for v in between))
    print(f"  denominators              : "
          + ", ".join(str(_headline(p)[2]) for p in distinct))
    noise, signal = _spread(within), _spread(between)
    print(f"\n  within-ad noise (spread)  : {noise:.3f}")
    print(f"  between-ad signal (spread): {signal:.3f}")
    if noise > 0:
        ratio = signal / noise
        print(f"  SIGNAL-TO-NOISE           : {ratio:.2f}")
        print("  → " + ("the number does NOT discriminate between ads; it must never "
                        "lead a recommendation." if ratio <= 1.2 else
                        "the number carries signal beyond its own run-to-run noise."))
    else:
        print("  within-ad noise is zero — no ratio to report.")

    # ---- 0b: the problem map ----
    print("\n" + "-" * 78)
    print("0b  THE PROBLEM MAP (pain-vocabulary overlap, Jaccard)")
    print("-" * 78)
    print(f"  {'tokens':<16} {'same ad':>22}   {'different ads':>22}   verdict")
    verdicts = []
    for name, keep in _VARIANTS:
        vocabs = {p: _vocab(runs[p][1], keep) for p in set(repeats) | set(distinct)}
        same = [_jaccard(vocabs[a], vocabs[b])
                for a, b in itertools.combinations(repeats, 2)]
        diff = [_jaccard(vocabs[a], vocabs[b])
                for a, b in itertools.combinations(distinct, 2)]
        separated = min(same) > max(diff)
        verdicts.append(separated)
        print(f"  {name:<16} "
              f"{statistics.mean(same):.3f} [{min(same):.3f}-{max(same):.3f}] n={len(same):<2}  "
              f"{statistics.mean(diff):.3f} [{min(diff):.3f}-{max(diff):.3f}] n={len(diff):<2}  "
              f"{'SEPARATES' if separated else 'overlaps'}")

    print()
    if all(verdicts):
        print("  → The diagnosis IS ad-specific: under every tokenization the WORST")
        print("    same-ad pair still overlaps more than the BEST different-ad pair.")
        print("    ⚠ But same-ad overlap is only ~0.23 — two runs of one ad share")
        print("    under a quarter of their pain vocabulary. It discriminates; it is")
        print("    not yet repeatable. Both are true and a read should reflect both.")
    elif any(verdicts):
        print("  ⚠ MIXED: the separation depends on the tokenization, which means it")
        print("    is not established. Do not report it as a finding.")
    else:
        print("  ⚠ The problem map does NOT separate re-runs from different ads.")

    # ---- 0c: the convex-combination check ----
    print("\n" + "-" * 78)
    print("0c  CONVEX COMBINATION — is a panel number a mean of its subgroups?")
    print("-" * 78)

    projections = load_projections(args.runs_root)
    decisions = load_decisions(args.runs_root)
    violations: list[str] = []
    qc1_n = qc2_n = qc3_n = qc3_skipped = 0
    segment_counts: list[int] = []

    for path, (l35, l3) in sorted(projections.items()):
        name = Path(path).name
        segments = l35.get("by_segment") or []
        if segments:
            segment_counts.append(len(segments))
            qc1_n += 1
            for problem in qc1_pooling_identity(l35, l3):
                violations.append(f"QC1 {name}: {problem}")
        if len(segments) >= 2:
            qc2_n += 1
            for problem in qc2_convexity(l35):
                violations.append(f"QC2 {name}: {problem}")

    for path, decision in sorted(decisions.items()):
        problems = qc3_cycle_identity(decision)
        if problems is None:
            qc3_skipped += 1
            continue
        qc3_n += 1
        for problem in problems:
            violations.append(f"QC3 {Path(path).name}: {problem}")

    # ⚠ The coverage line is not decoration. One subgroup satisfies convexity
    # trivially and zero satisfies it vacuously, so "no violations" means
    # nothing until you can see how many runs and subgroups were actually
    # tested.
    span = (f"{min(segment_counts)}-{max(segment_counts)}"
            if segment_counts else "0")
    print(f"  QC1 pooling identity  : {qc1_n} runs, {span} segments each")
    print(f"  QC2 funnel convexity  : {qc2_n} runs (needs >= 2 segments)")
    print(f"  QC3 headline vs cycle : {qc3_n} runs checked, "
          f"{qc3_skipped} skipped (no cycle breakdown)")

    if not (qc1_n or qc2_n or qc3_n):
        print("\n  ⚠ NOTHING CHECKED — no run carried the sidecars this reads.")
    elif violations:
        print(f"\n  ⚠ {len(violations)} VIOLATION(S) — a panel number is not a mean")
        print("    of the subgroups it summarises. This is a BUG, not a finding:")
        for line in violations:
            print(f"      {line}")
    else:
        print("\n  → No violation on either surface this can reach: the FUNNEL")
        print("    PROJECTION (QC1/QC2) and the DECISION HEADLINE (QC3). Both are")
        print("    genuine weighted means of their subgroups, so the 'distributions")
        print("    are Python' invariant holds — the point being that ~80% of tested")
        print("    models fail this when the average is generated, not counted.")
        print("    ⚠ NOT a statement about every aggregate in the engine. The third")
        print("    one, panel.audience_mass, is never persisted and so cannot be")
        print("    checked from disk — it is convex BY CONSTRUCTION instead")
        print("    (DemographicBundle.validate enforces weight > 0).")

    print("\n" + "=" * 78)
    print("Method: docs/v3_engine_improvement_plan.md §0. Re-run after any engine")
    print("change — this is the check that answers 'did it help?'.")


if __name__ == "__main__":
    main()
