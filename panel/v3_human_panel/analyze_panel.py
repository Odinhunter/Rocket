#!/usr/bin/env python3
"""
analyze_panel.py — human↔engine comparison harness for the v3 human panel (#10).

Everything the n=50 plan needs. Free (offline) checks run with the stdlib; the one
paid check (the pain-overlap kill-criterion) reuses the engine's OWN assess layer so
both pain sets come from one distiller — and is gated behind --run-assess.

The design decisions this encodes (from the chat + the advisor):
  * n=50 answers the go/no-go questions (pains + register), NOT a precise threshold.
  * A "pass" at 50 from a convenience sample is PROVISIONAL — so we also print the
    demographic composition (bias check) and run a split-half saturation test.
  * Action-mix at n=50 is asymmetric: engine INSIDE the wide human CI = weak evidence;
    engine OUTSIDE it = strong evidence of a gross miss. Reported that way.

Subcommands (run `python analyze_panel.py <cmd> -h`):
  decode          RXN answer-codes  -> joined human_records.json (Part 1 + Part 2)
  behavior        action-mix + Wilson CIs + dispersion + demographic composition
  rating-packet   blind human+engine reactions -> raters.csv (+ private key)
  score-register  raters' 1-5 scores -> register mean + inter-rater agreement
  pains           split-half saturation + human-vs-engine PainMap  (--run-assess = PAID)

No paid call happens without --run-assess. Everything else is $0.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

TARGET_DISPOSITION = "enthusiast_macros_lifter"

# The engine's five demographic bundles for the target (weights from the library
# definition) — the yardstick for the convenience-sample bias check.
ENGINE_BUNDLES = [
    ("under_3.5L / tier-2-3",  "18-24", 12.0),
    ("3.5-7L / tier-2",        "25-34", 26.0),
    ("7-17L / metro",          "25-34", 38.0),
    ("17-40L / metro",         "35-44", 18.0),
    ("40L+ / metro",           "35-44",  6.0),
]

ACTIONS = ["scroll_past", "linger", "tap_cta", "save", "share"]
NEXT_STEPS = ["buy_now", "buy_at_restock", "research_first", "mention_to_someone", "nothing"]


# --------------------------------------------------------------------------- #
#  small stats
# --------------------------------------------------------------------------- #
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(point, lo, hi) Wilson score interval — robust for small n / extreme p."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, center - half), min(1.0, center + half))


def gini_simpson(counts: Counter, cats: list[str]) -> float:
    """1 - Σpᵢ² — the chance two random picks differ. A natural 'how varied are
    people' for a categorical choice. 0 = everyone picked the same; →1 = spread."""
    n = sum(counts.get(c, 0) for c in cats)
    if n == 0:
        return 0.0
    return 1.0 - sum((counts.get(c, 0) / n) ** 2 for c in cats)


def norm_entropy(counts: Counter, cats: list[str]) -> float:
    n = sum(counts.get(c, 0) for c in cats)
    if n == 0:
        return 0.0
    h = 0.0
    for c in cats:
        p = counts.get(c, 0) / n
        if p > 0:
            h -= p * math.log(p)
    return h / math.log(len(cats)) if len(cats) > 1 else 0.0


# --------------------------------------------------------------------------- #
#  decode: RXN answer-codes -> joined human records
# --------------------------------------------------------------------------- #
def decode_one(code: str) -> dict | None:
    code = code.strip()
    for pre in ("RXN1-", "RXN2-"):
        if code.startswith(pre):
            code = code[len(pre):]
            break
    try:
        return json.loads(base64.b64decode(code).decode("utf-8"))
    except Exception:
        return None


def cmd_decode(args) -> None:
    raw = Path(args.codes).read_text()
    # accept: one code per line, OR a JSON array of {..} records (downloads)
    records: list[dict] = []
    stripped = raw.strip()
    if stripped.startswith("["):
        records = json.loads(stripped)
    else:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            rec = decode_one(line)
            if rec is None:
                print(f"  ! could not decode: {line[:24]}…", file=sys.stderr)
            else:
                records.append(rec)

    # The kiosk (one-shot, in-person) exports MERGED records — one per person,
    # with both picks + demographics already together. The older two-link flow
    # exported per-PART records joined by code. Handle both.
    merged: list[dict] = []
    by_code: dict[str, dict] = defaultdict(dict)
    for r in records:
        if r.get("action") and r.get("next_step") and ("r1" in r or "r4" in r):
            merged.append({
                "code": str(r.get("id") or r.get("code") or f"P{len(merged)+1:03d}").upper(),
                "exposure_ms": r.get("exposure_ms"),
                "age_band": r.get("age_band", ""), "city_tier": r.get("city_tier", ""),
                "income_band": r.get("income_band", ""),
                "r1": r.get("r1", ""), "r2": r.get("r2", ""), "r3": r.get("r3", ""),
                "action": r.get("action", ""), "action_why": r.get("action_why", ""),
                "r4": r.get("r4", ""), "r5": r.get("r5", ""), "r6": r.get("r6", ""),
                "next_step": r.get("next_step", ""), "next_step_why": r.get("next_step_why", ""),
            })
            continue
        part = int(r.get("part", 0))
        code = str(r.get("code", "")).strip().upper()
        if not code or part not in (1, 2):
            print(f"  ! skipping malformed record: {str(r)[:60]}", file=sys.stderr)
            continue
        by_code[code][f"part{part}"] = r

    joined, only1, only2 = list(merged), [], []
    for code, parts in sorted(by_code.items()):
        p1, p2 = parts.get("part1"), parts.get("part2")
        if p1 and p2:
            joined.append({
                "code": code,
                "exposure_ms": p1.get("exposure_ms"),
                "r1": p1.get("r1", ""), "r2": p1.get("r2", ""), "r3": p1.get("r3", ""),
                "action": p1.get("action", ""), "action_why": p1.get("action_why", ""),
                "r4": p2.get("r4", ""), "r5": p2.get("r5", ""), "r6": p2.get("r6", ""),
                "next_step": p2.get("next_step", ""), "next_step_why": p2.get("next_step_why", ""),
            })
        elif p1:
            only1.append(code)
        else:
            only2.append(code)

    Path(args.out).write_text(json.dumps(joined, indent=2, ensure_ascii=False))
    src = f"{len(merged)} kiosk + {len(joined)-len(merged)} joined" if merged else "joined"
    print(f"# decoded {len(records)} records → {len(joined)} complete ({src}) → {args.out}")
    if only1:
        print(f"# {len(only1)} did Part 1 only (chase these for Part 2): {', '.join(only1)}")
    if only2:
        print(f"# {len(only2)} have Part 2 but no matching Part 1 (code typo?): {', '.join(only2)}")
    # exposure-timing quality
    exps = [j["exposure_ms"] for j in joined if isinstance(j.get("exposure_ms"), (int, float))]
    if exps:
        exps.sort()
        bad = [e for e in exps if e < 1500 or e > 3000]
        print(f"# exposure timing: median {exps[len(exps)//2]}ms; {len(bad)} outside 1.5–3.0s "
              f"{'(review these — the glance may not have mirrored the engine)' if bad else '(all clean)'}")


# --------------------------------------------------------------------------- #
#  engine-side loaders
# --------------------------------------------------------------------------- #
def load_engine_transcripts(run_dir: Path) -> list[dict]:
    return json.loads((run_dir / "transcripts.json").read_text())


def engine_within_labels(run_dir: Path) -> set[str]:
    tc = json.loads((run_dir / "target_classification.json").read_text())
    return {d["disposition_label"] for d in tc["disposition_classifications"]
            if d["classification"] == "within"}


def engine_within_dist(run_dir: Path, key: str, cats: list[str]) -> Counter:
    within = engine_within_labels(run_dir)
    c: Counter = Counter()
    for t in load_engine_transcripts(run_dir):
        if t["disposition_label"] in within:
            v = (t.get("behavioral_signal") or {}).get(key)
            if v in cats:
                c[v] += 1
    return c


# --------------------------------------------------------------------------- #
#  behavior: action-mix + dispersion + composition
# --------------------------------------------------------------------------- #
def _human_dist(humans: list[dict], key: str, cats: list[str]) -> Counter:
    c: Counter = Counter()
    for h in humans:
        v = h.get(key)
        if v in cats:
            c[v] += 1
    return c


def _mix_table(name: str, cats: list[str], human: Counter, engine: Counter) -> None:
    hn, en = sum(human.values()), sum(engine.values())
    print(f"\n## {name}  (human n={hn}, engine within-target n={en})")
    print(f"{'choice':<20}{'human %':>9}{'  95% CI (human)':>20}{'engine %':>10}   verdict")
    print("-" * 78)
    for cat in cats:
        hp, lo, hi = wilson(human.get(cat, 0), hn)
        ep = engine.get(cat, 0) / en if en else 0.0
        inside = lo <= ep <= hi
        verdict = "· inside (weak pass)" if inside else "⚠ OUTSIDE — gross miss"
        print(f"{cat:<20}{hp*100:>8.1f}%   [{lo*100:>4.0f}%,{hi*100:>4.0f}%]{ep*100:>9.1f}%   {verdict}")
    # dispersion
    hg, eg = gini_simpson(human, cats), gini_simpson(engine, cats)
    he, ee = norm_entropy(human, cats), norm_entropy(engine, cats)
    ratio = (eg / hg) if hg > 0 else float("nan")
    print(f"\n   dispersion (Gini-Simpson): human {hg:.2f} · engine {eg:.2f} · "
          f"engine/human = {ratio:.2f}  {'✓ ≥0.70' if ratio >= 0.70 else '⚠ <0.70 (engine too uniform/too peaked)'}")
    print(f"   (normalised entropy: human {he:.2f} · engine {ee:.2f})")


def cmd_behavior(args) -> None:
    humans = json.loads(Path(args.humans).read_text())
    run_dir = Path(args.engine_run)
    print(f"# BEHAVIOR — humans={len(humans)}  vs  engine run {run_dir.name}")
    print("# Read the asymmetry: engine INSIDE the (wide) human CI is weak evidence; "
          "engine OUTSIDE it is strong evidence of a gross miss.")

    _mix_table("Action (the glance)", ACTIONS,
               _human_dist(humans, "action", ACTIONS), engine_within_dist(run_dir, "action", ACTIONS))
    _mix_table("Next step (a day+ later)", NEXT_STEPS,
               _human_dist(humans, "next_step", NEXT_STEPS), engine_within_dist(run_dir, "next_step", NEXT_STEPS))

    # Composition/bias: kiosk records carry demographics inline; else a screener CSV.
    if any(h.get("income_band") for h in humans):
        _composition(None, humans)
    elif args.screener:
        _composition(args.screener, humans)


def _composition(screener_csv: str | None, humans: list[dict]) -> None:
    """Convenience-sample bias check: human makeup vs the engine's 5 bundles.
    Reads income_band inline from kiosk records, or from a screener CSV
    (columns, case-insensitive: code, age, city_tier, income_band)."""
    if screener_csv is None:
        rows = [{"income_band": h.get("income_band", "?"), "city_tier": h.get("city_tier", "")}
                for h in humans if h.get("income_band")]
    else:
        codes = {h["code"] for h in humans}
        rows = []
        with open(screener_csv, newline="") as f:
            for row in csv.DictReader(f):
                row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
                if row.get("code", "").upper() in codes:
                    rows.append(row)
    print(f"\n## Composition (bias check) — {len(rows)}/{len(humans)} completes have demographics")
    if not rows:
        print("   (no demographics — log age/city_tier/income_band to run this)")
        return
    def norm(s: str) -> str:  # collapse "₹", "<", "under", "_", spaces; – → -
        s = s.lower().replace("₹", "").replace("–", "-").replace("under", "")
        for ch in " <_,":
            s = s.replace(ch, "")
        return s
    inc = Counter(norm(r.get("income_band", "?")) for r in rows)
    print("\n   income band            humans      engine target weight")
    print("   " + "-" * 52)
    matched = 0
    for label, _age, w in ENGINE_BUNDLES:
        band = label.split(" / ")[0]
        key = norm(band)
        hits = inc.get(key, 0)
        matched += hits
        print(f"   {band:<22}{hits:>4}        {w:>4.0f}%")
    print("   " + "-" * 52)
    if matched < len(rows):
        print(f"   ({len(rows)-matched} rows didn't map to a band — check the income labels)")
    print("   → if the humans clump in one band while the engine spreads, the match is "
          "against a skewed mirror. Recruit wider or caveat it — no n fixes this.")


# --------------------------------------------------------------------------- #
#  rating-packet / score-register  (the 'sounds human?' check)
# --------------------------------------------------------------------------- #
def _reaction_text(rec: dict, engine: bool) -> str:
    if engine:
        return (rec.get("encoding_text", "") + "\n" + rec.get("reflection_text", "")).strip()
    return (f"R1: {rec.get('r1','')}\nR2: {rec.get('r2','')}\nR3: {rec.get('r3','')}\n"
            f"[{rec.get('action','')}] {rec.get('action_why','')}\n"
            f"R4: {rec.get('r4','')}\nR5: {rec.get('r5','')}\nR6: {rec.get('r6','')}\n"
            f"[{rec.get('next_step','')}] {rec.get('next_step_why','')}").strip()


def cmd_rating_packet(args) -> None:
    humans = json.loads(Path(args.humans).read_text())
    run_dir = Path(args.engine_run)
    within = engine_within_labels(run_dir)
    engine = [t for t in load_engine_transcripts(run_dir) if t["disposition_label"] in within]
    rng = random.Random(args.seed)
    rng.shuffle(engine)
    engine = engine[:args.engine_n or len(humans)]  # balance the pile by default

    items = ([("H", h["code"], _reaction_text(h, False)) for h in humans]
             + [("E", str(t["agent_id"]), _reaction_text(t, True)) for t in engine])
    rng.shuffle(items)

    key = {}
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "reaction", "sounds_like_a_real_person_1to5"])
        for i, (src, sid, text) in enumerate(items, 1):
            rid = f"R{i:03d}"
            key[rid] = {"source": src, "src_id": sid}
            w.writerow([rid, text, ""])
    Path(args.key).write_text(json.dumps(key, indent=2))
    print(f"# rating packet → {args.out} ({len(items)} reactions, human+engine shuffled & blind)")
    print(f"# private key → {args.key}  (DON'T give this to raters)")
    print("# Give raters.csv to 2–3 people who don't know the project; they fill the 1–5 column "
          "(5 = totally real, 1 = obviously fake). Then: score-register.")


def cmd_score_register(args) -> None:
    key = json.loads(Path(args.key).read_text())
    per_rater: list[dict[str, float]] = []
    for path in args.ratings:
        scores: dict[str, float] = {}
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                rid = (row.get("id") or "").strip()
                val = (row.get("sounds_like_a_real_person_1to5") or "").strip()
                if rid and val:
                    try:
                        scores[rid] = float(val)
                    except ValueError:
                        pass
        per_rater.append(scores)
        print(f"# {path}: {len(scores)} scored")

    def mean_for(source: str) -> tuple[float, int]:
        vals = [s[rid] for s in per_rater for rid, meta in key.items()
                if meta["source"] == source and rid in s]
        return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)

    hm, hn = mean_for("H")
    em, en = mean_for("E")
    print(f"\n## Register — 'sounds like a real person' (1–5)")
    print(f"   HUMAN reactions : {hm:.2f}  (n={hn})   ← reality anchor")
    print(f"   ENGINE reactions: {em:.2f}  (n={en})   {'✓ ≥4.0' if em >= 4.0 else '⚠ below 4.0'}")
    print(f"   gap (human − engine): {hm - em:+.2f}   (small gap = engine reads as human)")
    # crude inter-rater agreement: SD of rater means
    if len(per_rater) > 1:
        rmeans = [sum(s.values()) / len(s) for s in per_rater if s]
        mu = sum(rmeans) / len(rmeans)
        sd = math.sqrt(sum((x - mu) ** 2 for x in rmeans) / len(rmeans))
        print(f"   rater agreement: per-rater means {[f'{x:.2f}' for x in rmeans]} (SD {sd:.2f}; "
              f"{'tight' if sd < 0.4 else 'loose — raters disagree, read individually'})")


# --------------------------------------------------------------------------- #
#  pains: split-half saturation + human-vs-engine PainMap   (--run-assess = PAID)
# --------------------------------------------------------------------------- #
def _human_transcripts(humans: list[dict]):
    """Adapt human records into the engine's AgentTranscript shape, so the SAME
    assess layer distils both pain sets (advisor: apples-to-apples)."""
    from agent.schema import AgentTranscript, BehavioralSignal
    out = []
    for i, h in enumerate(humans):
        enc = (f"R1 GUT: {h['r1']}\n\nR2 COMPREHENSION: {h['r2']}\n\nR3 INTEREST: {h['r3']}\n\n"
               + json.dumps({"action": h["action"], "reasoning": h["action_why"]}))
        refl = (f"R4 STICKINESS: {h['r4']}\n\nR5 SOCIAL: {h['r5']}\n\nR6 FRICTION: {h['r6']}\n\n"
                + json.dumps({"next_step": h["next_step"], "reasoning": h["next_step_why"]}))
        out.append(AgentTranscript(
            agent_id=i, disposition_label=TARGET_DISPOSITION, context_label="human",
            seed_idx=0, encoding_text=enc, reflection_text=refl,
            behavioral_signal=BehavioralSignal(h["action"], h["action_why"],
                                               h["next_step"], h["next_step_why"]),
            probe_signal=None, cycle_position="mid_cycle",
        ))
    return out


def _split_halves(humans: list[dict], seed: int) -> tuple[list[dict], list[dict]]:
    """Deterministic, code-hashed split (reproducible regardless of input order)."""
    def h(code: str) -> int:
        return int(hashlib.sha1(f"{seed}:{code}".encode()).hexdigest(), 16)
    ordered = sorted(humans, key=lambda x: h(x["code"]))
    mid = len(ordered) // 2
    return ordered[:mid], ordered[mid:]


def _run_assess(transcripts, run_dir: Path):
    """Reuse the engine's assess layer on human transcripts. PAID (one Opus call)."""
    from replay_synthesis import _config_from_run_json
    from agent.synthesis_types import TargetClassification
    from agent.synthesis_types import ConfidenceSignals
    from agent.synthesis_assess import assess_reactions
    config = _config_from_run_json(run_dir)
    tc = TargetClassification.from_dict(json.loads((run_dir / "target_classification.json").read_text()))
    cs = ConfidenceSignals(within_target_disposition_count=1, contexts_in_agreement=1,
                           total_contexts=1, homogenization_flag_count=0, total_segments=1)
    return assess_reactions(transcripts, tc, cs, config)


def _top_pains(pain_map, k: int = 3) -> list[str]:
    # No numeric rank exists (severity/prevalence are text labels); assess emits
    # pains most-important-first. The kill-criterion is about WITHIN-TARGET pains,
    # so surface those first, preserving emitted order (a stable sort).
    ordered = sorted(pain_map, key=lambda p: 0 if getattr(p, "within_target", True) else 1)
    return [f"[{getattr(p,'funnel_stage','?')}] {p.pain}" for p in ordered[:k]]


def cmd_pains(args) -> None:
    humans = json.loads(Path(args.humans).read_text())
    run_dir = Path(args.engine_run)
    ht = _human_transcripts(humans)
    A, B = _split_halves(humans, args.seed)

    # engine top-3 (already computed, free)
    engine_pm = json.loads((run_dir / "painmap.json").read_text())
    epains = engine_pm.get("pain_map") or engine_pm.get("pains") or []
    def epick(p): return f"[{p.get('funnel_stage','?')}] {p.get('pain','')}"
    # within-target pains first (stable), emitted order preserved — see _top_pains
    engine_top = [epick(p) for p in sorted(
        epains, key=lambda p: 0 if p.get("within_target", True) else 1)[:3]]

    if not args.run_assess:
        from agent.synthesis_assess import build_corpus, _classification_map
        from agent.synthesis_types import TargetClassification
        tc = TargetClassification.from_dict(json.loads((run_dir / "target_classification.json").read_text()))
        corpus = build_corpus(ht, _classification_map(tc))
        print(f"# DRY RUN ($0). Human corpus built: {len(ht)} transcripts, {len(corpus)} chars.")
        print(f"# Split-half: A={len(A)}  B={len(B)}  (deterministic on seed {args.seed})")
        print("\n# Engine top-3 pains (from painmap.json):")
        for p in engine_top:
            print(f"   • {p}")
        print("\n# To actually distil the human pains + run the split-half saturation test, "
              "re-run with --run-assess (PAID: 3 Opus calls — full-50, half-A, half-B).")
        print("# (needs dangerouslyDisableSandbox for network + .env ANTHROPIC_API_KEY)")
        if args.show_corpus:
            print("\n" + "=" * 70 + "\n" + corpus[:4000] + "\n…")
        return

    print("# PAID: running assess on full-50, half-A, half-B …")
    full = _run_assess(ht, run_dir)
    ha = _run_assess(_human_transcripts(A), run_dir)
    hb = _run_assess(_human_transcripts(B), run_dir)
    full_top, a_top, b_top = _top_pains(full.pain_map), _top_pains(ha.pain_map), _top_pains(hb.pain_map)

    out = {"engine_top3": engine_top, "human_full_top3": full_top,
           "human_halfA_top3": a_top, "human_halfB_top3": b_top,
           "n": len(humans), "halfA": len(A), "halfB": len(B)}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))

    def show(title, lst):
        print(f"\n{title}")
        for p in lst:
            print(f"   • {p}")
    print("\n" + "=" * 70)
    print("PAIN-OVERLAP — the kill-criterion (need ≥2 of 3 to overlap)")
    show("Engine top-3:", engine_top)
    show("Human top-3 (all 50):", full_top)
    print("\n--- split-half saturation (did 50 settle the top pains?) ---")
    show("Half A top-3:", a_top)
    show("Half B top-3:", b_top)
    print("\n→ You (or a blind judge) score two overlaps:")
    print("   1) engine vs human-full ≥ 2/3  → the instrument's diagnosis is real.")
    print("   2) half-A vs half-B    ≥ 2/3  → n=50 reached saturation, so (1) is trustworthy.")
    print("   If (2) fails, 50 wasn't enough to trust (1) — recruit more before believing it.")
    print(f"\n# saved → {args.out}")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decode", help="RXN answer-codes → joined human_records.json")
    d.add_argument("codes", help="file of RXN codes (one/line) OR a JSON array of records")
    d.add_argument("--out", default="human_records.json")
    d.set_defaults(func=cmd_decode)

    b = sub.add_parser("behavior", help="action-mix + Wilson CI + dispersion + composition")
    b.add_argument("humans"); b.add_argument("engine_run")
    b.add_argument("--screener", help="CSV: code,age,city_tier,income_band (composition/bias check)")
    b.set_defaults(func=cmd_behavior)

    rp = sub.add_parser("rating-packet", help="blind human+engine reactions → raters.csv")
    rp.add_argument("humans"); rp.add_argument("engine_run")
    rp.add_argument("--out", default="raters.csv"); rp.add_argument("--key", default="raters_key.json")
    rp.add_argument("--engine-n", type=int, default=0, help="engine reactions to include (default: match human n)")
    rp.add_argument("--seed", type=int, default=71)
    rp.set_defaults(func=cmd_rating_packet)

    sr = sub.add_parser("score-register", help="raters' 1-5 CSVs → register mean + agreement")
    sr.add_argument("key"); sr.add_argument("ratings", nargs="+", help="one CSV per rater")
    sr.set_defaults(func=cmd_score_register)

    p = sub.add_parser("pains", help="split-half saturation + human-vs-engine PainMap")
    p.add_argument("humans"); p.add_argument("engine_run")
    p.add_argument("--run-assess", action="store_true", help="PAID: run the real assess layer (3 Opus calls)")
    p.add_argument("--show-corpus", action="store_true", help="dry-run: print the assembled human corpus")
    p.add_argument("--out", default="pain_overlap.json"); p.add_argument("--seed", type=int, default=71)
    p.set_defaults(func=cmd_pains)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
