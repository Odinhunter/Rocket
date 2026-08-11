"""Did the second-person cores actually produce first-person reactions — and did
anything parrot its own register block?

    .venv/bin/python scripts/check_persona_voice.py <run_dir> [--compare <run_dir>]

$0 — reads `agent_calls/*__encoding.json` off disk, no API calls.

This is the LIVE half of what `tests/test_second_person_address.py` can only pin
as instruction. Offline can assert that the render prompt DEMANDS second person;
only a finished run shows whether the agent, handed a "You are…" system block,
answers as itself.

Three checks, and the third is the one that matters most:

1. **Self-reference** — does the reaction speak as "i/me/my", or does it slip into
   third person ("she would probably scroll past")? A third-person reaction means
   the model is still narrating a character rather than being one.

2. **Length / register** — mean reaction length, against the comparison run.
   Included because a register change is the thing render-8/9 could plausibly
   move, and "it feels different" is not a measurement.

3. ⚠ **Parroting** — n-gram overlap between a reaction and the persona's OWN
   `HOW YOU TALK` utterances. Those exist to SHOW register, never to be reused;
   the caption says "Never repeat these lines" for exactly this reason. If a
   reaction replays its own sample quote, the register block has become a script
   and the reaction is not a reaction. Reported per disposition, because one
   persona parroting is an authoring problem and all of them parroting is a
   prompt problem.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

_FIRST = re.compile(r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself)\b", re.I)
_THIRD = re.compile(r"\b(he|she|him|her|his|hers|they|them|their)\b", re.I)
_STOP = {
    "the", "a", "an", "and", "or", "but", "is", "it", "to", "of", "in", "on",
    "for", "with", "that", "this", "at", "as", "so", "not", "just", "like",
}


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9₹']+", text.lower()) if w not in _STOP]


def _ngrams(text: str, n: int = 4) -> set[tuple[str, ...]]:
    w = _words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def _utterances(system_text: str) -> list[str]:
    """The HOW YOU TALK / HOW THEY TALK lines out of a persona core."""
    _, _, tail = system_text.partition("HOW ")
    return [
        ln.strip().strip('"')
        for ln in tail.split("\n")
        if ln.strip().startswith('"')
    ]


def _system_text(request: dict) -> str:
    s = request.get("system")
    if isinstance(s, list):
        return " ".join(b.get("text", "") for b in s)
    return s or ""


def load(run_dir: Path) -> dict[str, list[dict]]:
    """disposition -> [{reaction, utterances}] for every encoding call."""
    by: dict[str, list[dict]] = defaultdict(list)
    for f in sorted((run_dir / "agent_calls").glob("*__encoding.json")):
        d = json.loads(f.read_text())
        sys_text = _system_text(d.get("request", {}))
        # ⚠ Reflection calls carry the SAME system block; only encoding is read
        # so one persona is not counted twice.
        by[d.get("disposition_label", "?")].append({
            "reaction": d.get("response_text", ""),
            "utterances": _utterances(sys_text),
            "core_is_second_person": sys_text.strip().lower().startswith("you"),
        })
    return by


def report(run_dir: Path, label: str) -> dict:
    by = load(run_dir)
    if not by:
        raise SystemExit(f"{run_dir}: no encoding calls found")

    print(f"\n{'=' * 74}\n{label}: {run_dir.name}\n{'=' * 74}")
    print(f"{'disposition':30} {'n':>4} {'2p core':>8} {'1st-per':>8} "
          f"{'3rd-per':>8} {'chars':>7} {'parrot':>7}")

    totals = {"n": 0, "first": 0, "third": 0, "chars": 0, "parrot": 0, "2p": 0}
    for lab, rows in sorted(by.items()):
        n = len(rows)
        first = sum(1 for r in rows if _FIRST.search(r["reaction"]))
        third = sum(1 for r in rows if _THIRD.search(r["reaction"]))
        chars = sum(len(r["reaction"]) for r in rows) // max(n, 1)
        second_core = sum(1 for r in rows if r["core_is_second_person"])
        parrot = 0
        for r in rows:
            rg = _ngrams(r["reaction"])
            if any(rg & _ngrams(u) for u in r["utterances"] if u):
                parrot += 1
        print(f"{lab[:30]:30} {n:>4} {second_core:>8} {first:>8} "
              f"{third:>8} {chars:>7} {parrot:>7}")
        totals["n"] += n
        totals["first"] += first
        totals["third"] += third
        totals["chars"] += chars * n
        totals["parrot"] += parrot
        totals["2p"] += second_core

    n = totals["n"]
    print(f"{'-' * 74}")
    print(f"{'TOTAL':30} {n:>4} {totals['2p']:>8} {totals['first']:>8} "
          f"{totals['third']:>8} {totals['chars'] // max(n, 1):>7} "
          f"{totals['parrot']:>7}")
    print(f"\n  second-person cores : {totals['2p']}/{n}")
    print(f"  reactions in 1st person: {totals['first']}/{n} "
          f"({100 * totals['first'] // max(n, 1)}%)")
    print(f"  reactions w/ 3rd person: {totals['third']}/{n} "
          f"(may refer to brands/others — inspect before calling it a defect)")
    print(f"  ⚠ parroting own quotes : {totals['parrot']}/{n} "
          f"({100 * totals['parrot'] // max(n, 1)}%)")
    return {**totals, "total": n}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--compare", type=Path, default=None,
                    help="an earlier run to read the same way")
    ap.add_argument("--show", type=int, default=0,
                    help="print N sample reactions per disposition")
    args = ap.parse_args()

    new = report(args.run_dir, "NEW")
    if args.compare:
        old = report(args.compare, "COMPARE")
        print(f"\n{'=' * 74}\nDELTA\n{'=' * 74}")
        for key, name in (("first", "1st-person reactions"),
                          ("parrot", "parroting own quotes")):
            a = 100 * old[key] // max(old["total"], 1)
            b = 100 * new[key] // max(new["total"], 1)
            print(f"  {name:26} {a:>3}%  ->  {b:>3}%   ({b - a:+d} pts)")
        ca = old["chars"] // max(old["total"], 1)
        cb = new["chars"] // max(new["total"], 1)
        print(f"  {'mean reaction length':26} {ca:>3}   ->  {cb:>3}    "
              f"({cb - ca:+d} chars)")

    if args.show:
        by = load(args.run_dir)
        for lab, rows in sorted(by.items()):
            print(f"\n### {lab}")
            for r in rows[: args.show]:
                print("  " + r["reaction"].strip().replace("\n", "\n  ")[:700])
                print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
