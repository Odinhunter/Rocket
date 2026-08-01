"""Render a finished run's Creative Read as a self-contained HTML page.

    python render_read.py runs/demo/health_wellness_demo/<run_id> -o read.html

This is the second half of the operator-tool slice: the engine produces a
run directory, this turns it into the client-facing artifact. The tool calls
build_read_model() + render_html() directly (same two calls); this CLI exists
so the same path is exercisable, and debuggable, without the server.

Costs nothing — it reads artifacts already on disk.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent.dashboard_html import render_html
from agent.read_model import build_read_model


def _latest_run(base: Path) -> Path | None:
    candidates = [
        p for p in base.glob("*")
        if p.is_dir() and (p / "run.json").exists()
        and p.name not in ("entities", "library_renders")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render a finished Creative Read run to a single HTML file.",
    )
    ap.add_argument("run_dir", help="Path to a run directory, or a brand directory "
                                    "(the newest run inside it is used).")
    ap.add_argument("-o", "--out", default=None,
                    help="Output path. Default: <run_dir>/creative_read.html")
    ap.add_argument("--no-image", action="store_true",
                    help="Skip embedding the creative (much smaller file).")
    ap.add_argument("--fragment", action="store_true",
                    help="Emit a title+style+content fragment instead of a full "
                         "HTML document (for hosts with their own skeleton).")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not (run_dir / "run.json").exists():
        found = _latest_run(run_dir) if run_dir.is_dir() else None
        if found is None:
            print(f"ERROR: no run.json in {run_dir} (and no runs inside it).",
                  file=sys.stderr)
            sys.exit(1)
        run_dir = found
        print(f"# newest run: {run_dir.name}", file=sys.stderr)

    try:
        model = build_read_model(run_dir)
    except (ValueError, FileNotFoundError) as exc:
        # A crashed run that renders a blank page in front of a prospect is
        # far worse than a loud failure here.
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    html = render_html(
        model, embed_image=not args.no_image, base_dir=Path.cwd(),
        full_document=not args.fragment,
    )
    out = Path(args.out) if args.out else run_dir / "creative_read.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    print(f"# {model.decision_name} · trust {model.trust} · "
          f"engine read {model.report.verdict} {model.report.confidence}/100")
    if model.headline:
        print(f"#{model.headline.rstrip('.')}")
    print(f"# wrote {out}  ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
