"""Finding the finished runs on disk, and turning one into a rendered read.

Two rules this module exists to hold:

1. **Explicit run directories only.** `render_read.py:_latest_run` picks the
   newest directory by mtime and only requires `run.json` to exist — not
   `status="complete"`. That is fine for a CLI convenience form and a landmine
   mid-session, so the server never guesses which run someone meant.
2. **Renderable means a Report is actually on disk.** A committed-but-crashed
   run has a `run.json` and no report; `build_read_model` raises loudly on it
   (by design). Listing it as available would put that error in front of a
   prospect, so discovery filters it out up front.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from agent.read_model import ReadModel, build_read_model
from agent.report_html import render_html


@dataclass(frozen=True)
class RunRef:
    """A finished run, as the operator picks it off a list."""

    account_id: str
    brand_profile_id: str
    run_id: str
    path: Path
    asset_label: str
    category: str
    updated_at: str
    decision: str
    source: str  # "run.json" | "replay_report.json"

    @property
    def key(self) -> str:
        """The stable id used in URLs and stored on a session."""
        return f"{self.account_id}/{self.brand_profile_id}/{self.run_id}"


# Directories that live alongside runs inside a brand folder but are not runs.
_NOT_RUNS = {"entities", "library_renders"}


def _peek(run_json: Path) -> dict | None:
    try:
        return json.loads(run_json.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _ref(path: Path, raw: dict, source: str) -> RunRef:
    config = raw.get("config", {}) or {}
    asset = config.get("asset", {}) or {}
    report = raw.get("report") or {}
    decision = (report.get("decision") or {}).get("decision", "") if report else ""
    return RunRef(
        account_id=config.get("account_id", "") or path.parent.parent.name,
        brand_profile_id=config.get("brand_profile_id", "") or path.parent.name,
        run_id=raw.get("run_id", path.name),
        path=path,
        asset_label=asset.get("label", "") or path.name,
        category=config.get("category", ""),
        updated_at=raw.get("updated_at", ""),
        decision=decision,
        source=source,
    )


def discover_runs(runs_root: Path) -> list[RunRef]:
    """Every renderable run under runs/<account>/<brand>/<run_id>/, newest first.

    A run qualifies when a Report is reachable: either persisted in run.json at
    status='complete', or recovered into replay_report.json. Anything else is
    omitted rather than offered and then failing at render time.
    """
    out: list[RunRef] = []
    if not runs_root.is_dir():
        return out
    for run_json in sorted(runs_root.glob("*/*/*/run.json")):
        path = run_json.parent
        if path.name in _NOT_RUNS:
            continue
        raw = _peek(run_json)
        if raw is None:
            continue
        if raw.get("report"):
            out.append(_ref(path, raw, "run.json"))
        elif (path / "replay_report.json").exists():
            out.append(_ref(path, raw, "replay_report.json"))
    out.sort(key=lambda r: (r.updated_at, r.run_id), reverse=True)
    return out


def resolve_run(runs_root: Path, key: str) -> Path | None:
    """Map an `account/brand/run_id` key to its directory, refusing anything
    that escapes runs_root. The key reaches this function from a URL and from
    stored session JSON, so it is treated as untrusted in both cases."""
    parts = [p for p in key.split("/") if p]
    if len(parts) != 3:
        return None
    # resolve() collapses any `..` BEFORE the containment check, so this one
    # test is the whole guard — an explicit ".." scan alongside it would be
    # dead code that reads like protection.
    path = (runs_root / parts[0] / parts[1] / parts[2]).resolve()
    try:
        path.relative_to(runs_root.resolve())
    except ValueError:
        return None
    if not (path / "run.json").exists():
        return None
    return path


def render_run(run_path: Path, *, base_dir: Path, full_document: bool = True) -> str:
    """The finished read as HTML — `build_read_model` then `render_html`, the
    same two calls `render_read.py` makes and nothing else.

    base_dir is passed explicitly and is NOT Path.cwd(): run configs record the
    creative as a repo-relative path (`assets/mb_biozyme_ad.png`), so under a
    server started from anywhere else the embedded image would silently vanish
    from the page a prospect is looking at.
    """
    model = build_read_model(run_path)
    return render_html(model, base_dir=base_dir, full_document=full_document)


# Fields that name the ad rather than diagnose it. Each one alone hands a brand
# manager the answer to "which of these two is mine", which is the entire
# question the decoy asks.
def blind_read_model(model: ReadModel, slot: str) -> ReadModel:
    """Strip the identity of the ad, keep the whole diagnosis.

    The decoy asks whether they can tell their own ad's read from another ad's
    read BY THE DIAGNOSIS. Rendered normally, the report answers that for them
    four times over: the creative is embedded in the header, the h1 is the
    asset label, the page title repeats it, the footer prints a run_id that
    contains the asset slug, and the metaline echoes their own declared
    targeting back at them.

    So a blinded render replaces exactly those, and NOTHING else. Every pain,
    number, warning and caveat renders in full — if the diagnosis is specific
    enough for them to recognise their ad from it, they should recognise it.
    That is the signal, not a leak.

    ⚠ One known residue: `audience_mismatch` can quote the declared audience
    back inside its warning text. It stays, because a guardrail outranks the
    blinding — dropping the one surface that says "this ad is aimed at someone
    other than who you bought" to protect a test would be the wrong trade.
    """
    return replace(
        model,
        asset_label=f"Read {slot}",
        # Belt and braces with embed_image=False: no path, nothing to embed.
        asset_path=None,
        run_id=f"read-{slot}",
        declared_targeting="",
        declared_audience="",
    )


def render_blinded(
    run_path: Path, slot: str, *, base_dir: Path, full_document: bool = True,
) -> str:
    """A read rendered for the decoy comparison — unlabeled, no creative.

    base_dir is carried through even though the creative is suppressed twice
    over (asset_path=None and embed_image=False). Leaving it to default to
    Path.cwd() would mean the day anyone relaxes either suppression, the image
    resolves against whatever directory the server happened to start in —
    silently, since a missing file just renders nothing.
    """
    model = blind_read_model(build_read_model(run_path), slot)
    return render_html(model, embed_image=False, base_dir=base_dir,
                       full_document=full_document)
