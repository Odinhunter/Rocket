"""Replay strategist synthesis on a prior batch run.

Two modes:

1. **--run-id <id>** (preferred) — load `runs/<run_id>/run.json` written by
   batch_run.py, regenerate target ID + strategist memo only. Skips the
   4 free-text Opus calls because the PopulationReport is already
   persisted. Used for fast prompt iteration on the strategist layer.

2. **--log-file <path>** (legacy) — parse a captured stdout transcript
   from before persistence existed, reconstruct (specs, histories,
   failures), re-run synthesize_population_report (4 Opus 4.7 calls,
   ~$0.30), then identify_target_audience + synthesize_strategic_critique.

Mode 2 is lossy in one way: RunResult.messages is empty.
synthesize_population_report does not consume that field, so this is safe.

Usage (run-id mode):
    python replay_synthesis.py --run-id <run_id>

Usage (log-file mode):
    python replay_synthesis.py --log-file <stdout_file> \\
        --archetype urban_indian_male_22_30 --category chocolate \\
        --focal-image assets/cadbury_ad.png \\
        --focal-label "Cadbury Dairy Milk Silk — How far will you go for love?" \\
        --anchor-image assets/fr_ad.png \\
        --anchor-label "Ferrero Rocher Valentine's Day — Add your golden touch"
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")

from agent.persistence import current_run_id, load_run, telemetry_summary
from agent.runner import RunResult
from agent.synthesis import (
    format_population_report,
    format_target_classification,
    identify_target_audience,
    synthesize_population_report,
    synthesize_strategic_critique,
)
from archetypes.context import list_contexts
from archetypes.disposition import list_dispositions


# Header inside a round block: "[agent 03] [focal] disp=... | ctx=... | seed_idx=N"
_AGENT_HEADER_RE = re.compile(
    r"^\[agent\s+(\d+)\]\s+\[(focal|anchor)\][^\n]*$",
    re.MULTILINE,
)

# Round divider: "==== \nROUND N · ... \n===="
_ROUND_RE = re.compile(
    r"={5,}\s*\nROUND\s+(\d+)\s*·[^\n]*\n={5,}",
    re.MULTILINE,
)


def _resolve_disp(label: str, archetype: str, category: str) -> tuple[str, str]:
    for d in list_dispositions(archetype, category):
        if d[0] == label:
            return d
    return (label, "")


def _resolve_ctx(label: str, archetype: str) -> tuple[str, str]:
    for c in list_contexts(archetype):
        if c[0] == label:
            return c
    return (label, "")


def strip_log_noise(text: str) -> str:
    """Strip httpx/anthropic logging lines from a captured stdout transcript.

    When batch_run.py is run with `> run.log 2>&1`, the SDK's HTTP-request
    and rate-limit-retry log lines interleave with the print() output. They
    do not match the agent-block regex, but they will get sucked into agent
    body text by the next-marker bounding logic. Strip them up front.
    """
    skip_prefixes = ("HTTP Request: ", "Retrying request to ")
    return "\n".join(
        line for line in text.split("\n")
        if not any(line.startswith(p) for p in skip_prefixes)
    )


def parse_specs(text: str, archetype: str, category: str) -> list[dict]:
    """Parse the 'Agent specs:' block at the top of a batch_run.py stdout."""
    anchor = text.find("Agent specs:")
    if anchor == -1:
        block = text
    else:
        # bound at the next '====' divider after the specs block
        next_eq = text.find("\n==", anchor)
        block = text[anchor: next_eq if next_eq != -1 else len(text)]

    spec_re = re.compile(
        r"^\s*agent\s+(\d+):\s*disp=(\S+)\s+ctx=(\S+)\s+seed_idx=(\d+)\s*$",
        re.MULTILINE,
    )
    specs: list[dict] = []
    seen: set[int] = set()
    for m in spec_re.finditer(block):
        aid = int(m.group(1))
        if aid in seen:
            continue
        seen.add(aid)
        disp_label = m.group(2)
        ctx_label = m.group(3)
        seed_idx = int(m.group(4))
        specs.append({
            "agent_id": aid,
            "disposition": _resolve_disp(disp_label, archetype, category),
            "context": _resolve_ctx(ctx_label, archetype),
            "seed_idx": seed_idx,
            "cell_key": (disp_label, ctx_label),
        })
    specs.sort(key=lambda s: s["agent_id"])
    return specs


def _split_round_segments(text: str) -> dict[int, str]:
    matches = list(_ROUND_RE.finditer(text))
    out: dict[int, str] = {}
    for i, m in enumerate(matches):
        round_num = int(m.group(1))
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Stop at the round-by-round completion summary if it falls inside this slice
        completion = text.find("ROUND-BY-ROUND COMPLETION", body_start)
        if completion != -1 and completion < body_end:
            body_end = completion
        out[round_num] = text[body_start:body_end]
    return out


def _split_agent_blocks(round_body: str) -> list[tuple[int, str, str]]:
    """Return list of (agent_id, stim_id, output_text) inside a round."""
    headers = list(_AGENT_HEADER_RE.finditer(round_body))
    blocks: list[tuple[int, str, str]] = []
    for i, m in enumerate(headers):
        aid = int(m.group(1))
        stim = m.group(2)
        body_start = m.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(round_body)
        for terminator in ("\n  ... draining", "\n==", "\nROUND-BY-ROUND"):
            idx = round_body.find(terminator, body_start)
            if idx != -1 and idx < body_end:
                body_end = idx
        body = round_body[body_start:body_end].strip()
        blocks.append((aid, stim, body))
    return blocks


def reconstruct_histories(
    text: str,
    specs: list[dict],
) -> tuple[dict, dict]:
    spec_by_id = {s["agent_id"]: s for s in specs}
    histories: dict = defaultdict(list)
    failures: dict = defaultdict(list)

    round_segments = _split_round_segments(text)
    for round_num in sorted(round_segments.keys()):
        body = round_segments[round_num]
        for aid, stim, output in _split_agent_blocks(body):
            if not output:
                continue
            spec = spec_by_id.get(aid)
            if spec is None:
                logging.warning("agent %d has no spec; skipping its R%d block", aid, round_num)
                continue

            if output.startswith("!! FAILED:"):
                reason = output[len("!! FAILED:"):].strip().split("\n", 1)[0]
                failures[(aid, stim)].append((round_num, reason))
                continue

            parsed = None
            if round_num == 3:
                try:
                    parsed = json.loads(output)
                except json.JSONDecodeError:
                    failures[(aid, stim)].append((round_num, "JSON parse failed in replay"))
                    continue
                # Schema check: five expected dimensions, each {score:int, reason:str}
                expected = ("relevance", "trust", "curiosity", "irritation", "aspiration")
                if not all(
                    isinstance(parsed.get(d), dict)
                    and isinstance(parsed[d].get("score"), int)
                    and isinstance(parsed[d].get("reason"), str)
                    for d in expected
                ):
                    failures[(aid, stim)].append((round_num, "R3 schema mismatch in replay"))
                    continue

            histories[(aid, stim)].append(RunResult(
                output=output,
                disposition=spec["disposition"],
                context=spec["context"],
                messages=[],
                round_num=round_num,
                parsed=parsed,
            ))

    return dict(histories), dict(failures)


def _replay_from_run_id(run_id: str) -> None:
    """Load the persisted PopulationReport and regenerate the target-aware
    strategist layer. Skips the 4 free-text Opus calls (already done)."""
    current_run_id.set(run_id + "_replay")
    loaded = load_run(run_id)
    config = loaded["config"]
    report = loaded["population_report"]
    if report is None:
        print(
            f"# ERROR: runs/{run_id}/run.json has no population_report. "
            "Use --log-file mode if you only have a stdout transcript.",
            file=sys.stderr,
        )
        sys.exit(3)

    focal_cfg = config["stimuli"]["focal"]
    anchor_cfg = config["stimuli"]["anchor"]

    print(f"# Replay run_id={run_id} (skipping 4 free-text Opus calls)", flush=True)
    print()
    print(format_population_report(report))

    print("\n" + "=" * 78)
    print("TARGET IDENTIFICATION  ·  vision Opus call on focal+anchor")
    print("=" * 78)
    target_cls = identify_target_audience(
        report,
        focal_label=focal_cfg["label"],
        anchor_label=anchor_cfg["label"],
        focal_image_path=focal_cfg["image_path"],
        anchor_image_path=anchor_cfg["image_path"],
        category=config["category"],
        archetype=config["archetype"],
    )
    print()
    print(format_target_classification(target_cls))

    print("\n" + "=" * 78)
    print("STRATEGIST MEMO  ·  Opus prose synthesis over population + target")
    print("=" * 78)
    critique = synthesize_strategic_critique(
        report,
        focal_label=focal_cfg["label"],
        anchor_label=anchor_cfg["label"],
        category=config["category"],
        target_classification=target_cls,
    )
    print(f"\n[model: {critique.model} · verdict: {critique.verdict_band or 'n/a'}]\n")
    print(critique.memo)
    print()
    print(telemetry_summary(run_id + "_replay"))


def _replay_from_log_file(args: argparse.Namespace) -> None:
    """Legacy mode: parse stdout transcript, re-run full synthesis."""
    for img in (args.focal_image, args.anchor_image):
        if not img.exists():
            print(f"# ERROR: image not found: {img}", file=sys.stderr)
            sys.exit(1)

    text = strip_log_noise(args.log_file.read_text())

    print(f"# Replay synthesis from {args.log_file}", flush=True)

    specs = parse_specs(text, args.archetype, args.category)
    print(f"# Parsed {len(specs)} agent specs", flush=True)
    if not specs:
        print(
            "# ERROR: no specs parsed — is this a batch_run.py stdout transcript?",
            file=sys.stderr,
        )
        sys.exit(2)

    histories, failures = reconstruct_histories(text, specs)
    n_conv = len(histories)
    completed = sum(1 for h in histories.values() if len(h) == 6)
    n_fail = sum(len(v) for v in failures.values())
    print(
        f"# Reconstructed {n_conv} conversations, "
        f"{completed} completing all 6 rounds, {n_fail} failures",
        flush=True,
    )

    print("\n# Running synthesize_population_report (4 Opus 4.7 calls) ...", flush=True)
    report = synthesize_population_report(
        histories=histories,
        failures=failures,
        agent_specs=specs,
        focal_label=args.focal_label,
        anchor_label=args.anchor_label,
    )

    print()
    print(format_population_report(report))

    print("\n" + "=" * 78)
    print("TARGET IDENTIFICATION  ·  vision Opus call on focal+anchor")
    print("=" * 78)
    target_cls = identify_target_audience(
        report,
        focal_label=args.focal_label,
        anchor_label=args.anchor_label,
        focal_image_path=str(args.focal_image),
        anchor_image_path=str(args.anchor_image),
        category=args.category,
        archetype=args.archetype,
    )
    print()
    print(format_target_classification(target_cls))

    print("\n" + "=" * 78)
    print("STRATEGIST MEMO  ·  Opus prose synthesis over population + target")
    print("=" * 78)
    critique = synthesize_strategic_critique(
        report,
        focal_label=args.focal_label,
        anchor_label=args.anchor_label,
        category=args.category,
        target_classification=target_cls,
    )
    print(f"\n[model: {critique.model} · verdict: {critique.verdict_band or 'n/a'}]\n")
    print(critique.memo)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Replay strategist synthesis on a prior batch run. Use --run-id "
            "for runs persisted by batch_run.py (fast, skips free-text Opus "
            "calls), or --log-file for legacy stdout transcripts (slower, "
            "regenerates the full PopulationReport)."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run-id", dest="run_id", help="A run id under runs/<run_id>/")
    mode.add_argument("--log-file", dest="log_file", type=Path,
                      help="Path to a captured batch_run.py stdout transcript")

    # Required only in --log-file mode; validated below.
    parser.add_argument("--archetype", help="e.g. urban_indian_male_22_30")
    parser.add_argument("--category", help="e.g. chocolate, coffee, wellness")
    parser.add_argument("--focal-image", type=Path, help="Path to the focal ad image")
    parser.add_argument("--focal-label", help="Display label for the focal ad")
    parser.add_argument("--anchor-image", type=Path, help="Path to the anchor ad image")
    parser.add_argument("--anchor-label", help="Display label for the anchor ad")
    args = parser.parse_args()

    if args.run_id:
        _replay_from_run_id(args.run_id)
    else:
        missing = [
            n for n in ("archetype", "category", "focal_image", "focal_label",
                        "anchor_image", "anchor_label")
            if getattr(args, n) is None
        ]
        if missing:
            parser.error(
                "--log-file mode requires: --" + ", --".join(
                    n.replace("_", "-") for n in missing
                )
            )
        _replay_from_log_file(args)


if __name__ == "__main__":
    main()
