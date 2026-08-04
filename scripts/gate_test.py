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

    print("\n" + "=" * 78)
    print("Method: docs/v3_engine_improvement_plan.md §0. Re-run after any engine")
    print("change — this is the check that answers 'did it help?'.")


if __name__ == "__main__":
    main()
