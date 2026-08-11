"""Render every disposition's persona core twice from identical inputs, so that
exactly one thing differs between the two sides.

TWO MODES:

  PROMPT MODE (default) — the variable is the render system prompt. The "before"
  is read out of git so it cannot drift from what shipped.

  ANCHOR MODE (`--old-library`) — the variable is the ANCHOR TEXT, with the
  prompt held constant. Built for render-10, where the anchors stopped naming
  brands and marketplaces. ⚠ The old anchors CANNOT be read out of git the way
  the old prompt can: the library lives under `runs/`, which is gitignored, so
  pass a snapshot taken before the edit.

    .venv/bin/python scripts/render_persona_samples.py [--library <path>]
                     [--old-library <snapshot>] [--samples N]
                     [--limit N] [--first-person] [-o out.md]

⚠ `--samples` EXISTS BECAUSE ONE RENDER PER SIDE CANNOT MEASURE A RATE. The
question render-10 has to answer is not "does this core mention Nykaa" but
"what FRACTION of this persona's cores do, and do all of them collapse onto the
same famous brand" — the old anchors scored 24/24 on Nykaa for one disposition
and 0/19 for another. n=1 answers neither, so it buys nothing.

⚠ WHY BOTH SIDES ARE RENDERED HERE rather than one being read off disk: every
run on disk is **render-6**. render-7 (§2.6, income withheld from the writer)
shipped 2026-08-06 and has never been rendered — no paid run has used it. So an
on-disk core is TWO changes away from render-8, and a before/after built that way
would show the income withholding and the address change mixed together. The
"before" here is render-7 rendered fresh, which isolates the address.

The old prompt is read out of git rather than kept as a copy in this file, so it
cannot drift from what actually shipped.

⚠ THIS SPENDS. One render is one model call (~$0.02), and the count is
dispositions × sides × samples. It never runs a panel and never touches the
reaction layer. ⚠ Dispositions with no `demographic_bundles` are SKIPPED, so
the live health_wellness library renders 6, not 7.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

# ⚠ override=True — the ambient environment may define an EMPTY
# ANTHROPIC_API_KEY, which silently wins over .env without it.
load_dotenv(REPO_ROOT / ".env", override=True)

from agent import render as render_mod  # noqa: E402
from agent.artifact_pack import load_pack  # noqa: E402
from agent.vectors import (  # noqa: E402
    ChaosVector,
    DemographicPoint,
    DispositionVector,
)

_DEFAULT_LIBRARY = (
    REPO_ROOT / "runs/demo/health_wellness_demo/entities/library.json"
)

# The neutral chaos band, held constant across every persona so the comparison
# is not confounded by decision style.
_CHAOS = ChaosVector(
    decision_velocity="moderate",
    suggestibility="medium",
    consistency="variable",
    risk_tolerance="balanced",
)


def _old_persona_system(ref: str = "HEAD") -> str:
    """`_PERSONA_SYSTEM` as it stands in git — the render-7 prompt. Read from the
    committed file so this cannot drift from what shipped."""
    src = subprocess.run(
        ["git", "show", f"{ref}:agent/render.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    m = re.search(r'_PERSONA_SYSTEM = """\\\n(.*?)"""', src, re.DOTALL)
    if not m:
        raise SystemExit(f"could not find _PERSONA_SYSTEM in {ref}:agent/render.py")
    # The source uses trailing backslashes for line continuation; undo them the
    # way Python's parser would.
    return m.group(1).replace("\\\n", "")


# A first-person variant, offered so the user can rule between "You are" and
# "I am" with both in front of them rather than in the abstract. Built by
# transforming the SHIPPED prompt, so it stays in sync with every other rule.
def _first_person_variant(second_person_prompt: str) -> str:
    """⚠ `_PERSONA_SYSTEM` is a line-continued string, so the newlines visible in
    the SOURCE are not in the VALUE. An early version of this matched on a
    pattern containing "\\n", silently failed to fire, and would have rendered a
    second-person core under a "first person" heading. Every substitution is
    asserted below for exactly that reason."""
    out = (
        second_person_prompt
        .replace(
            "write a SECOND-PERSON description of this EXACT person, ADDRESSED TO THEM",
            "write a FIRST-PERSON description of this EXACT person, IN THEIR OWN VOICE",
        )
        .replace(
            'Begin with "You are" or "You\'ve been" or "You " + a verb.',
            'Begin with "I am" or "I\'ve been" or "I " + a verb.',
        )
        .replace('ADDRESS THEM AS "you" IN EVERY SENTENCE', 'WRITE AS "I" IN EVERY SENTENCE')
        .replace('If a sentence needs a subject, it is "you".',
                 'If a sentence needs a subject, it is "I".')
        .replace("HOW YOU TALK", "HOW I TALK")
        .replace("how your own sentences sound", "how my own sentences sound")
        .replace('Never "She\'s been taking supplements for two years" — write '
                 '"You\'ve been taking supplements for two years."',
                 'Never "She\'s been taking supplements for two years" — write '
                 '"I\'ve been taking supplements for two years."')
    )
    for must_go, must_come in (
        ("SECOND-PERSON description", "FIRST-PERSON description"),
        ('ADDRESS THEM AS "you"', 'WRITE AS "I"'),
        ("HOW YOU TALK", "HOW I TALK"),
    ):
        if must_go in out or must_come not in out:
            raise SystemExit(
                f"first-person variant did not apply: {must_go!r} still present "
                f"or {must_come!r} missing. The prompt wording changed — update "
                f"_first_person_variant before rendering, or the sample will be "
                f"mislabelled."
            )
    return out


def _bundle_point(disposition: dict) -> DemographicPoint | None:
    """The heaviest demographic bundle — the modal person for this stance.

    None when the disposition carries no bundles. ⚠ Returned rather than
    substituted with a default: inventing a demographic would make one sample
    in the comparison not correspond to anyone the engine would ever build.
    The caller SKIPS it and records the skip in the output."""
    bundles = disposition.get("demographic_bundles") or []
    if not bundles:
        return None
    best = max(bundles, key=lambda b: b.get("weight", 0))
    return DemographicPoint(**best["point"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", type=Path, default=_DEFAULT_LIBRARY)
    ap.add_argument("--old-library", type=Path, default=None,
                    help="ANCHOR MODE: a snapshot of the library taken BEFORE "
                         "the anchor edit. The prompt is then held constant "
                         "and the anchor is the only variable. Cannot come "
                         "from git — runs/ is gitignored.")
    ap.add_argument("--samples", type=int, default=1,
                    help="renders per disposition per side. n=1 cannot measure "
                         "a rate; use 3+ when the question is 'how often'")
    ap.add_argument("--limit", type=int, default=0, help="first N dispositions")
    ap.add_argument("--first-person", action="store_true",
                    help="also render ONE persona in first person, for comparison")
    ap.add_argument("--after-only", action="store_true",
                    help="render only the CURRENT prompt — halves the spend when "
                         "you are checking whether a new rule lands, not "
                         "producing a before/after")
    ap.add_argument("-o", "--out", type=Path,
                    default=REPO_ROOT / "docs/v3_persona_address_samples.md")
    args = ap.parse_args()

    lib = json.loads(args.library.read_text())
    dispositions = lib.get("dispositions", lib)
    if isinstance(dispositions, dict):
        dispositions = list(dispositions.values())
    if args.limit:
        dispositions = dispositions[: args.limit]

    category = lib.get("category") or "health_wellness_nutrition"
    pack = load_pack(category)

    anchor_mode = args.old_library is not None
    new_prompt = render_mod._PERSONA_SYSTEM

    if anchor_mode:
        # The prompt is held constant; the anchor is the variable.
        old_prompt = new_prompt
        _old_lib = json.loads(args.old_library.read_text()).get("dispositions", [])
        old_anchors = {d.get("label"): d.get("anchor", "") for d in _old_lib}
        # ⚠ The BEFORE side must also use the OLD demographic bundle. render-10
        # swept brands out of `occupation_hint` as well as out of the anchors,
        # and that hint reaches the persona writer too. Rendering "before" with
        # the new hints would measure a half-reverted state and understate what
        # changed.
        old_demos = {d.get("label"): d for d in _old_lib}
        out: list[str] = [
            f"# Persona anchors — before vs after ({render_mod.RENDER_PROMPT_VERSION})",
            "",
            "Generated by `scripts/render_persona_samples.py --old-library`. "
            "Both sides use the **same** render prompt, demographic bundle, "
            "disposition vector, chaos band and artifact pack — the only "
            "variable is the anchor text.",
            "",
            f"`--samples {args.samples}` per side. ⚠ The old anchors are read "
            "from a snapshot, not from git: the library lives under `runs/`, "
            "which is gitignored.",
            "",
        ]
    else:
        old_anchors = {}
        old_prompt = _old_persona_system()
        if old_prompt.strip() == new_prompt.strip():
            raise SystemExit(
                "the committed prompt and the working-tree prompt are "
                "identical — there is no before/after to render. (Did you mean "
                "--old-library, to compare ANCHORS instead?)"
            )
        out = [
            "# Persona address — before vs after",
            "",
            "Generated by `scripts/render_persona_samples.py`. Both sides are "
            "rendered fresh from **identical** inputs (same demographic bundle, "
            "same disposition vector, same anchor, same chaos band, same "
            "artifact pack), so the only variable is the address.",
            "",
        ]

    # The vocabulary the summary counts. Derived from the pack so it cannot go
    # stale as brands are added, and split on the render-10 skew annotation.
    brand_terms = sorted({b.name for b in pack.brand_landscape})
    platform_terms = sorted(
        {c.split("—")[0].strip() for c in pack.retail_channels}
        - {"brand DTC website"}
    )

    def _found(text: str, terms: list[str]) -> set[str]:
        return {t for t in terms
                if re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE)}

    tally: dict[str, dict] = {}

    def render_with(prompt: str, demo, vec, anchor) -> str:
        original = render_mod._PERSONA_SYSTEM
        try:
            render_mod._PERSONA_SYSTEM = prompt
            # cache_dir=None — never serve either side from a cached core.
            return render_mod.render_persona_core(
                demo, vec, _CHAOS, pack, anchor=anchor, cache_dir=None,
            )
        finally:
            render_mod._PERSONA_SYSTEM = original

    skipped: list[str] = []
    for i, d in enumerate(dispositions):
        label = d.get("label", f"disposition_{i}")
        vec = DispositionVector(**d["vector"])
        demo = _bundle_point(d)
        anchor = d.get("anchor", "")
        if demo is None:
            skipped.append(label)
            print(f"[{i + 1}/{len(dispositions)}] {label} — SKIPPED "
                  f"(no demographic_bundles)", flush=True)
            continue
        old_anchor = old_anchors.get(label, anchor) if anchor_mode else anchor
        if anchor_mode and old_anchor == anchor:
            skipped.append(f"{label} (anchor unchanged)")
            print(f"[{i + 1}/{len(dispositions)}] {label} — SKIPPED "
                  f"(anchor unchanged, nothing to compare)", flush=True)
            continue
        print(f"[{i + 1}/{len(dispositions)}] {label} ...", flush=True)

        afters = [render_with(new_prompt, demo, vec, anchor)
                  for _ in range(args.samples)]

        out += [
            f"## {label}",
            "",
            f"`{demo.gender} · {demo.age_min}-{demo.age_max} · "
            f"{demo.geography}` · chaos `moderate`",
            "",
        ]
        befores: list[str] = []
        if not args.after_only:
            old_demo = demo
            if anchor_mode and label in old_demos:
                old_demo = _bundle_point(old_demos[label]) or demo
            befores = [render_with(old_prompt, old_demo, vec, old_anchor)
                       for _ in range(args.samples)]
            for n, before in enumerate(befores, 1):
                out += [f"### BEFORE {n}/{len(befores)}"
                        + (" — old anchor" if anchor_mode else " — committed prompt"),
                        "", "```", before.strip(), "```", ""]
        for n, after in enumerate(afters, 1):
            out += [f"### AFTER {n}/{len(afters)} — "
                    f"{render_mod.RENDER_PROMPT_VERSION}",
                    "", "```", after.strip(), "```", ""]

        tally[label] = {
            "before_brands": [_found(b, brand_terms) for b in befores],
            "before_platforms": [_found(b, platform_terms) for b in befores],
            "after_brands": [_found(a, brand_terms) for a in afters],
            "after_platforms": [_found(a, platform_terms) for a in afters],
            "before_len": [len(b) for b in befores],
            "after_len": [len(a) for a in afters],
        }

        if args.first_person and i == 0:
            fp = render_with(_first_person_variant(new_prompt), demo, vec, anchor)
            out += [
                "### VARIANT — first person, for comparison only (not shipped)",
                "", "```", fp.strip(), "```", "",
                "*Rendered so the second-person/first-person choice can be made "
                "with both in front of you. Only the second-person form is "
                "wired into the engine.*", "",
            ]

    if skipped:
        # Never a silent cap — a comparison that quietly covers 6 of 7 reads as
        # if it covered all 7.
        out += [
            "## Not rendered",
            "",
            "These dispositions carry no `demographic_bundles`, so there is no "
            "modal person to render them as. Skipped rather than rendered "
            "against an invented demographic:",
            "",
            *[f"- `{s}`" for s in skipped],
            "",
        ]
        print(f"\n⚠ skipped (no demographic_bundles): {', '.join(skipped)}")

    if tally:
        n = args.samples
        rows = [
            "## Summary — what each persona reached for",
            "",
            "Counts are **mentions across samples**, per side. The question is "
            "not whether a brand appears — the pack hands the writer a "
            "landscape so that it can — but whether the AUTHOR pre-decided it "
            "for everyone.",
            "",
            "| disposition | brands before | brands after | platforms before | platforms after |",
            "|---|---|---|---|---|",
        ]

        def _fmt(sets: list[set]) -> str:
            if not sets:
                return "—"
            counts: dict[str, int] = {}
            for s in sets:
                for t in s:
                    counts[t] = counts.get(t, 0) + 1
            if not counts:
                return "*none*"
            return ", ".join(f"{k} {v}/{len(sets)}"
                             for k, v in sorted(counts.items(),
                                                key=lambda kv: (-kv[1], kv[0])))

        for label, t in tally.items():
            rows.append(
                f"| `{label}` | {_fmt(t['before_brands'])} | "
                f"{_fmt(t['after_brands'])} | {_fmt(t['before_platforms'])} | "
                f"{_fmt(t['after_platforms'])} |"
            )

        def _sat(key: str) -> str:
            """How often the SAME term shows up in every sample of a side —
            the prominence-collapse read. personal_audio ships brand-free
            anchors and still puts its top 3 brands in 12/12 of every
            disposition, so this is the number that says whether the landscape
            reframe actually worked."""
            saturated = []
            for label, t in tally.items():
                sets = t[key]
                if not sets:
                    continue
                common = set.intersection(*sets) if sets else set()
                if common:
                    saturated.append(f"`{label}`: {', '.join(sorted(common))}")
            return "; ".join(saturated) or "*nothing appears in every sample*"

        rows += [
            "",
            f"**Saturated after (in all {n} samples):** {_sat('after_brands')}",
            "",
            f"**Saturated before (in all {n} samples):** {_sat('before_brands')}",
            "",
            "**Mean core length** — generic must not mean thin:",
            "",
        ]
        for label, t in tally.items():
            mb = sum(t["before_len"]) / len(t["before_len"]) if t["before_len"] else 0
            ma = sum(t["after_len"]) / len(t["after_len"]) if t["after_len"] else 0
            rows.append(f"- `{label}`: {mb:.0f} → {ma:.0f} chars")
        out += ["", *rows, ""]
        print("\n".join(rows))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
