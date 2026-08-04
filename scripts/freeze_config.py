#!/usr/bin/env python3
"""Print the frozen configuration of a finished run — §5.1 of the engine plan.

    .venv/bin/python scripts/freeze_config.py <run_dir> [--json]

$0. Reads what the run already recorded; computes nothing and calls nothing.

WHY THIS EXISTS
---------------
Across 66 defensible configurations of ONE task on ONE dataset, published
human-vs-silicon correlations ranged r = .23 to .84. The configuration swamps
the effect. We have made dozens of those choices — model per layer, temperature,
panel size and composition, disposition text, prompt wording, which purpose
preset scores the run — so any comparison against real people is worthless
unless the configuration that produced it is written down BEFORE the comparison
and published WITH the result. Otherwise we tune until the number flatters us
and learn nothing.

This is the thing you attach to the result.

⚠ IT READS THE RUN, NEVER HEAD. A configuration reconstructed from today's
source is not the configuration that produced a run made weeks ago — that is
precisely the drift the freeze exists to detect. Fields a run did not record
print as `(not recorded)`. Older runs will show several: `prompt_fingerprints`,
`panel_version`, `funnel_enabled` and a real `disposition_version` were only
added on 2026-08-04. **Do not back-fill them.** Absent is honest; a value
inferred from current source is a fabrication that defeats the whole point.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_MISSING = "(not recorded)"

# (label, dotted path into run.json). Order is the reading order: what was read,
# then who read it, then with what instructions.
_FIELDS: tuple[tuple[str, str], ...] = (
    ("run id", "run_id"),
    ("status", "status"),
    ("recorded at", "updated_at"),
    ("asset", "config.asset.label"),
    ("category", "config.category"),
    ("account / brand", "config.account_id"),
    ("brand profile", "config.brand_profile_id"),
    ("ad job (purpose)", "config.creative_inputs.purpose"),
    ("declared targeting", "config.declared_targeting"),
    ("panel size", "config.audience_spec.panel_size"),
    ("agents run (D x C x S)", "config.total_agents"),
    ("marketer-led composition", "config.marketer_led"),
    ("tail fraction", "config.tail_fraction"),
    ("segment granularity", "config.segment_granularity"),
    ("seed", "config.seed"),
    ("disposition library", "config.library_id"),
    ("audience spec", "config.audience_id"),
    ("funnel projection attached", "config.funnel_enabled"),
    ("protocol version", "protocol_version"),
    ("reaction protocol", "reaction_protocol_version"),
    ("render prompt", "render_prompt_version"),
    ("assess prompt", "assess_prompt_version"),
    ("prescribe prompt", "prescribe_prompt_version"),
    ("l4 prompt (legacy)", "l4_prompt_version"),
    ("decision layer", "decision_version"),
    ("purpose layer", "purpose_version"),
    ("vector schema", "config.vector_schema_version"),
    ("disposition content hash", "config.disposition_version"),
    ("panel composition hash", "config.panel_version"),
)


def _dig(raw: dict, path: str):
    cur = raw
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _show(value) -> str:
    if value is None or value == "":
        return _MISSING
    if value == "auto":
        return "auto  ⚠ never computed — this run predates the fix"
    return str(value)


def freeze(run_dir: Path) -> dict:
    """The full frozen record as a dict, exactly as the run stored it."""
    raw = json.loads((run_dir / "run.json").read_text())
    return {
        "fields": {label: _dig(raw, path) for label, path in _FIELDS},
        "model_versions": _dig(raw, "config.model_versions") or {},
        "temperatures": _dig(raw, "config.temperatures") or {},
        "efforts": _dig(raw, "config.efforts") or {},
        "prompt_fingerprints": raw.get("prompt_fingerprints") or {},
    }


def _print_human(frozen: dict) -> None:
    print("=" * 78)
    print("FROZEN CONFIGURATION — publish this beside the result")
    print("=" * 78)
    width = max(len(k) for k in frozen["fields"])
    for label, value in frozen["fields"].items():
        print(f"  {label:<{width}}  {_show(value)}")

    for title, key in (("MODELS", "model_versions"),
                       ("TEMPERATURES", "temperatures"),
                       ("REASONING EFFORT", "efforts")):
        table = frozen[key]
        print(f"\n{title}")
        if not table:
            print(f"  {_MISSING}")
            continue
        for layer, value in sorted(table.items()):
            print(f"  {layer:<12}  {'(sdk default)' if value is None else value}")

    print("\nPROMPT TEXT FINGERPRINTS")
    fp = frozen["prompt_fingerprints"]
    if not fp:
        print(f"  {_MISSING} — this run predates prompt fingerprinting (2026-08-04).")
        print("  The version strings above are hand-bumped, so for this run they are")
        print("  a CLAIM about the prompts, not a measurement of them.")
    else:
        for label, digest in sorted(fp.items()):
            print(f"  {label:<28}  {digest}")

    print("\n" + "-" * 78)
    print("Read from the run's own record. Nothing here was reconstructed from")
    print("current source: a config rebuilt from HEAD is not the config that")
    print("produced the run, and telling them apart is the point.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--json", action="store_true",
                    help="emit the record as JSON (for attaching to a result)")
    args = ap.parse_args()

    if not (args.run_dir / "run.json").exists():
        raise SystemExit(f"no run.json in {args.run_dir} — not a run directory")

    frozen = freeze(args.run_dir)
    if args.json:
        print(json.dumps(frozen, indent=2, sort_keys=True))
    else:
        _print_human(frozen)


if __name__ == "__main__":
    main()
