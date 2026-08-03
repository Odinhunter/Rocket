"""Produce the landing page's product screenshot from a real read (playbook §5).

Every finished read on disk diagnoses a REAL company's ad. Publishing one under
its own name is a named public critique of a company that never agreed to it —
so the hero shot is rendered from an ANONYMISED COPY of the run, never from the
run itself.

What this does NOT do is invent anything. Every number, every problem, every
quote is the real read's. Only names are removed:

  * the asset label and the run_id, both of which carry the brand
  * five sentences that name real third parties (two certification bodies and
    two competitor brands), replaced by the generic term they are an instance
    of, so the diagnosis still reads the same

The copy is written to the scratchpad and NEVER under runs/ — account scoping
is filing, not permission, so a stray run directory would surface in /reads.

The render goes through render_read.py --no-image unmodified: no anonymise flag
in the product, and no hand-built sample HTML that could drift from the real
read surface (memory: report_surface_fidelity).
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "assets"                     # untracked, like every other asset
WORK = Path(tempfile.mkdtemp(prefix="rocket-anon-"))  # never under runs/
SRC = REPO / "runs/demo/health_wellness_demo/20260721_023743_seed71_the_whole_truth_whey_isolate_p"

# The copy's identity. Same shape as a real run_id — it is printed on the page
# next to Export — with the brand taken out of it.
NEW_RUN_ID = "20260721_023743_seed71_unflavoured_whey_isolate_pack"
NEW_LABEL = "Unflavoured whey isolate (pack shot)"

# Text substitutions, applied to every string in the report. Each replaces a
# real company with the category it belongs to; none changes what the read says.
SUBS = [
    ("a visible third-party seal (Labdoor/Informed-Choice)",
     "a visible third-party testing seal"),
    ("a visible Labdoor/Informed-Choice seal",
     "a visible third-party testing seal"),
    ("an Informed-Choice or Labdoor seal",
     "a third-party testing seal"),
    ("No Labdoor or Informed-Choice seal visible",
     "No third-party testing seal visible"),
    ("mid-tub on plant-based (Plix/OZiva)",
     "mid-tub on plant-based rivals"),
]

# Applied to the rendered HTML, not the report — this string is in the app
# chrome, so run.json has no field to edit.
#
# The account chip shows the hardcoded placeholder initials "BM". On a
# marketing page, initials read as a person with an account, and §5's rule is
# that the shot must never imply a paying customer. "R" reads as Rocket's own
# demo account instead. This changes the SHOT, not the design — the renderer
# is the user's and is finished (memory: report_redesign_is_users_job).
POST_RENDER_SUBS = [
    ('<span class="rk-avatar">BM</span>', '<span class="rk-avatar">R</span>'),
]

# Nothing matching these may survive into the render. Checked case-insensitively
# after rendering, because a substitution that silently missed is the whole risk.
FORBIDDEN = [
    "whole truth", "wholetruth", "twt", "labdoor", "informed choice",
    "informed-choice", "plix", "oziva", "the_whole_truth",
    "twt_whey_isolate", "20260721_023743_seed71_the_whole",
]


def content_of(path: Path) -> str:
    """The page's text, with the embedded font's base64 removed.

    The read inlines two woff2 fonts as ~95KB of base64, and a short token
    like "twt" occurs in that alphabet by chance — five times here. Sweeping
    the raw file therefore reports leaks that are not leaks, and the fix is to
    sweep the content rather than to shorten the token list.
    """
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,BLOB",
                  path.read_text()).lower()


def substitute(node, counts: dict[str, int]):
    """Walk the report, replacing named companies in every string."""
    if isinstance(node, dict):
        return {k: substitute(v, counts) for k, v in node.items()}
    if isinstance(node, list):
        return [substitute(v, counts) for v in node]
    if isinstance(node, str):
        for old, new in SUBS:
            if old in node:
                node = node.replace(old, new)
                counts[old] = counts.get(old, 0) + 1
        return node
    return node


def main() -> int:
    dst = WORK / NEW_RUN_ID
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SRC, dst)
    assert (REPO / "runs") not in dst.parents, \
        "the anonymised copy must never live under runs/ — it would surface in /reads"

    run = json.loads((dst / "run.json").read_text())
    run["run_id"] = NEW_RUN_ID
    run["config"]["asset"]["label"] = NEW_LABEL
    # --no-image means it is never read, but the path names the brand too.
    run["config"]["asset"]["image_path"] = "assets/whey_isolate_pack.png"

    counts: dict[str, int] = {}
    run["report"] = substitute(run["report"], counts)
    (dst / "run.json").write_text(json.dumps(run, indent=2))

    print("# substitutions applied:")
    for old, _ in SUBS:
        n = counts.get(old, 0)
        flag = "" if n else "   <-- NOT FOUND: the source text changed"
        print(f"    {n} x  {old[:62]}{flag}")

    out = OUT / "landing_product_shot.html"
    proc = subprocess.run(
        [str(REPO / ".venv/bin/python"), "render_read.py", str(dst),
         "-o", str(out), "--no-image"],
        cwd=REPO, capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        return proc.returncode

    rendered = out.read_text()
    for old, new in POST_RENDER_SUBS:
        if old not in rendered:
            print(f"\n!! post-render anchor missing, the chrome changed: {old}")
            return 1
        rendered = rendered.replace(old, new)
    out.write_text(rendered)

    html = content_of(out)
    leaks = [tok for tok in FORBIDDEN if tok in html]
    if leaks:
        print(f"\n!! STILL IN THE RENDER: {leaks}")
        return 1

    # Positive control: the same sweep against the UNMODIFIED read must find
    # them, or the check above passed because the tokens were never there.
    real = subprocess.run(
        [str(REPO / ".venv/bin/python"), "render_read.py", str(SRC),
         "-o", str(WORK / "real.html"), "--no-image"],
        cwd=REPO, capture_output=True, text=True,
    )
    if real.returncode == 0:
        control = content_of(WORK / "real.html")
        found = [t for t in FORBIDDEN if t in control]
        print(f"\n# control: the real render contains {len(found)} of "
              f"{len(FORBIDDEN)} forbidden tokens {found}")
        if not found:
            print("!! the control found nothing — the sweep proves nothing")
            return 1

    print(f"\n# clean: 0 of {len(FORBIDDEN)} forbidden tokens in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
