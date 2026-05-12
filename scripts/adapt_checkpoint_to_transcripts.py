"""Adapt the pre-refactor checkpoint.json into AgentTranscript[] for the
new bundled-shape synthesis pipeline.

The pre-refactor pipeline stored per-round outputs across focal+anchor.
The new pipeline expects one AgentTranscript per agent containing two
concatenated text blocks (encoding_text = R1+R2+R3, reflection_text = R4+R5+R6).

This adapter:
  - filters to focal-only (anchor dropped)
  - concatenates R1/R2/R3 outputs into encoding_text with the
    "R1 GUT: ... / R2 COMPREHENSION: ... / R3 EMOTION: ..." section
    labels the new pipeline expects
  - concatenates R4/R5/R6 outputs into reflection_text the same way
  - converts R3's JSON output into a prose paragraph by concatenating
    the per-dimension `reason` strings (numeric scores are dropped — they
    don't survive the bundled-prose architecture anyway)

This is throwaway glue, used once to feed L2/L3/L4 a real-data fixture
before L1 is built. Delete after L1 is live.

Usage:
    python scripts/adapt_checkpoint_to_transcripts.py \\
        runs/20260511_131330_seed71_boat_airdopes_prime_512_specia/checkpoint.json \\
        --out tests/fixtures/transcripts_boat.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import AgentTranscript


_R3_DIMENSIONS = ("relevance", "trust", "curiosity", "irritation", "aspiration")


def _r3_prose_from_parsed(parsed: dict) -> str:
    """Stitch R3's per-dimension reasons into one prose paragraph.

    Drops the numeric scores — the bundled architecture has R3 as free
    prose, no scores. Reads slightly less natural than a real bundled R3
    EMOTION output, but it's the load-bearing semantic content.
    """
    if not isinstance(parsed, dict):
        return "(R3 emotion data unavailable in source transcript.)"
    parts: list[str] = []
    for dim in _R3_DIMENSIONS:
        entry = parsed.get(dim)
        if isinstance(entry, dict) and "reason" in entry:
            parts.append(str(entry["reason"]).strip())
    return " ".join(parts) if parts else "(R3 emotion data unavailable.)"


def _format_encoding(r1: str, r2: str, r3_parsed: dict) -> str:
    r3_prose = _r3_prose_from_parsed(r3_parsed)
    return (
        f"R1 GUT: {r1.strip()}\n\n"
        f"R2 COMPREHENSION: {r2.strip()}\n\n"
        f"R3 EMOTION: {r3_prose}"
    )


def _format_reflection(r4: str, r5: str, r6: str) -> str:
    return (
        f"R4 STICKINESS: {r4.strip()}\n\n"
        f"R5 SOCIAL: {r5.strip()}\n\n"
        f"R6 FRICTION: {r6.strip()}"
    )


def adapt_checkpoint(checkpoint_path: Path, *, stimulus_id: str = "focal") -> list[AgentTranscript]:
    """Load a checkpoint.json and return AgentTranscript[] for the chosen
    stimulus (default: focal).

    Drops any agent that doesn't have all 6 rounds completed for the chosen
    stimulus — partial agents are unusable for L2 synthesis.
    """
    ck = json.loads(checkpoint_path.read_text())
    specs_by_id = {s["agent_id"]: s for s in ck["specs"]}

    transcripts: list[AgentTranscript] = []
    for key, hist in ck["histories"].items():
        aid_str, stim_id = key.split(":", 1)
        if stim_id != stimulus_id:
            continue
        if len(hist) < 6:
            continue
        # Order by round_num so we don't depend on history ordering.
        by_round: dict[int, dict] = {}
        for entry in hist:
            by_round[int(entry["round_num"])] = entry
        if any(r not in by_round for r in (1, 2, 3, 4, 5, 6)):
            continue

        spec = specs_by_id[int(aid_str)]
        encoding = _format_encoding(
            r1=by_round[1]["output"],
            r2=by_round[2]["output"],
            r3_parsed=by_round[3].get("parsed") or {},
        )
        reflection = _format_reflection(
            r4=by_round[4]["output"],
            r5=by_round[5]["output"],
            r6=by_round[6]["output"],
        )
        transcripts.append(AgentTranscript(
            agent_id=int(aid_str),
            disposition_label=spec["disposition"][0],
            context_label=spec["context"][0],
            seed_idx=spec.get("seed_idx", 0) or 0,
            encoding_text=encoding,
            reflection_text=reflection,
        ))

    transcripts.sort(key=lambda t: t.agent_id)
    return transcripts


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("checkpoint", type=Path)
    p.add_argument("--stimulus", default="focal")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    transcripts = adapt_checkpoint(args.checkpoint, stimulus_id=args.stimulus)
    print(f"Adapted {len(transcripts)} transcripts from {args.checkpoint}")
    for t in transcripts:
        print(f"  agent {t.agent_id:2d}: disposition={t.disposition_label} context={t.context_label}")
        print(f"    encoding_text ({len(t.encoding_text)} chars): {t.encoding_text[:140]!r}...")
        print(f"    reflection_text ({len(t.reflection_text)} chars): {t.reflection_text[:140]!r}...")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps([t.to_dict() for t in transcripts], indent=2, ensure_ascii=False)
    )
    print(f"\nWrote {args.out} ({args.out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
