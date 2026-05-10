"""Validation harness: behavioral schema + dispositional + contextual sampling.

For each ad, pre-builds stratified samples across both layers so every
disposition and every context appears at least once across n runs. Pairs
them randomly. Logs both labels per run, aggregates by overall, by
disposition, and by disposition × context.
"""

from __future__ import annotations

import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

from agent.runner import run_agent
from archetypes.context import list_contexts
from archetypes.disposition import list_dispositions


N_PER_AD = 10
ARCHETYPE = "urban_indian_male_22_30"

# (display name, image path, category for dispositional sampling).
# None category → no disposition pool, context-only run.
ADS: list[tuple[str, str, str | None]] = [
    ("Patanjali Chyawanprash", "assets/patanjali_ad.jpg", "wellness"),
    ("Dabur Chyawanprash", "assets/dabur_ad.jpg", "wellness"),
]


@dataclass
class ParsedRun:
    attention: str
    time: str
    action: str
    signal: str
    disposition: str | None
    context: str | None
    raw: str


_FIELD_RE = re.compile(r"^\s*(attention|time|action|signal)\s*:\s*(.+?)\s*$", re.I)


def parse(
    raw: str, disposition: str | None, context: str | None
) -> ParsedRun:
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        m = _FIELD_RE.match(line)
        if m:
            fields[m.group(1).lower()] = m.group(2).strip()
    return ParsedRun(
        attention=fields.get("attention", "<unparsed>"),
        time=fields.get("time", "<unparsed>"),
        action=fields.get("action", "<unparsed>"),
        signal=fields.get("signal", "<unparsed>"),
        disposition=disposition,
        context=context,
        raw=raw,
    )


def trajectory_bucket(signal: str) -> str:
    s = signal.lower()
    if "screenshot" in s:
        return "screenshot"
    if "search" in s or "blinkit" in s or "myntra" in s or "amazon" in s:
        return "search"
    if "group-chat" in s or "group chat" in s or "groupchat" in s:
        return "group-chat"
    if "nothing" in s:
        return "nothing"
    return "<other>"


def stratified_pairs(
    pool: list, n: int, rng: random.Random
) -> list:
    """Return n elements of pool with each element appearing at least once
    when n >= len(pool). Order is randomised. Empty pool → list of n Nones."""
    if not pool:
        return [None] * n
    if n <= len(pool):
        return rng.sample(pool, n)
    base = pool[:]
    rng.shuffle(base)
    extra = [rng.choice(pool) for _ in range(n - len(pool))]
    out = base + extra
    rng.shuffle(out)
    return out


def run_block(
    ad_name: str, image_path: str, category: str | None, n: int, seed: int
) -> list[ParsedRun]:
    rng = random.Random(seed)
    disp_pool = list_dispositions(ARCHETYPE, category) if category else []
    ctx_pool = list_contexts(ARCHETYPE)

    dispositions = stratified_pairs(disp_pool, n, rng)
    contexts = stratified_pairs(ctx_pool, n, rng)

    cat_label = category or "<no disposition pool>"
    print(
        f"\n{'=' * 76}\n{ad_name}  ({image_path})\n"
        f"category={cat_label}  ·  n={n}  ·  seed={seed}\n{'=' * 76}"
    )

    results: list[ParsedRun] = []
    for i in range(1, n + 1):
        disp = dispositions[i - 1]
        ctx = contexts[i - 1]
        result = run_agent(
            ARCHETYPE,
            "",
            round_num=1,
            image_path=image_path,
            category=category,
            disposition=disp,
            context=ctx,
        )
        p = parse(result.output, result.disposition_label, result.context_label)
        results.append(p)
        disp_lbl = p.disposition or "—"
        ctx_lbl = p.context or "—"
        print(
            f"\n[{i:02d}] disp={disp_lbl}\n"
            f"     ctx={ctx_lbl}\n"
            f"     attention={p.attention} | time={p.time} | action={p.action}\n"
            f"     signal: {p.signal}"
        )
    return results


def report(ad_name: str, runs: list[ParsedRun]) -> None:
    n = len(runs)
    print(f"\n--- AGGREGATE: {ad_name} (n={n}) ---")

    att = Counter(r.attention for r in runs)
    print(f"Attention: {dict(att)}")

    act = Counter(r.action for r in runs)
    print(f"Action: {dict(act)}")

    engaged = [r for r in runs if r.attention != "scroll-past"]
    skipped = [r for r in runs if r.attention == "scroll-past"]

    if engaged:
        traj = Counter(trajectory_bucket(r.signal) for r in engaged)
        print(f"Trajectory (engaged, n={len(engaged)}): {dict(traj)}")
    if skipped:
        reason_counts = Counter(r.signal for r in skipped)
        print(f"Non-engagement reasons (n={len(skipped)}):")
        for reason, c in reason_counts.most_common():
            print(f"  {c}× {reason}")

    if any(r.disposition for r in runs):
        print("\nBy disposition × context:")
        for r in runs:
            disp = r.disposition or "—"
            ctx = r.context or "—"
            print(
                f"  [{disp:36s} × {ctx:28s}] "
                f"attn={r.attention:<11s} signal={r.signal}"
            )
    elif any(r.context for r in runs):
        print("\nBy context:")
        for r in runs:
            ctx = r.context or "—"
            print(f"  [{ctx:28s}] attn={r.attention:<11s} signal={r.signal}")


def main() -> None:
    # A/B test: same seed for both ads → matched disposition × context pairings.
    # This makes the only variable the ad image itself.
    all_results: list[tuple[str, list[ParsedRun]]] = []
    for ad_name, image_path, category in ADS:
        runs = run_block(ad_name, image_path, category, N_PER_AD, seed=43)
        all_results.append((ad_name, runs))

    print(f"\n\n{'#' * 76}\n# AGGREGATES\n{'#' * 76}")
    for ad_name, runs in all_results:
        report(ad_name, runs)


if __name__ == "__main__":
    main()
