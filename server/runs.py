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

from agent.dashboard_html import render_html
from agent.entities import (
    AudienceSpec, BrandProfile, DispositionLibrary, SavedAudience,
)
from agent.read_model import ReadModel, build_read_model


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


def discover_runs(runs_root: Path, *, account: str | None = None) -> list[RunRef]:
    """Every renderable run under runs/<account>/<brand>/<run_id>/, newest first.

    A run qualifies when a Report is reachable: either persisted in run.json at
    status='complete', or recovered into replay_report.json. Anything else is
    omitted rather than offered and then failing at render time.

    `account` narrows the list to one account. It is a FILING decision, not an
    access control: the product surface shows `demo` because `internal/*` is
    our own smoke-test exhaust and putting it in front of a brand manager makes
    the product look like a scratch pad. A signed-in browser that types an
    `internal/...` read URL still gets the read, and that is intended — one
    shared password means one trust level, and a filter that pretends
    otherwise would be a permission system that nothing enforces.

    The filter is on `RunRef.account_id`, the same field the URL key is built
    from, so what the list shows and what its links resolve to cannot drift.
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
            ref = _ref(path, raw, "run.json")
        elif (path / "replay_report.json").exists():
            ref = _ref(path, raw, "replay_report.json")
        else:
            continue
        if account is not None and ref.account_id != account:
            continue
        out.append(ref)
    out.sort(key=lambda r: (r.updated_at, r.run_id), reverse=True)
    return out


@dataclass(frozen=True)
class BrandChoice:
    """One brand a read can actually be run against, with everything a run
    needs already resolved off it.

    ⚠ This exists because the "new read" form used to ask the customer for the
    things on the right-hand side of this dataclass — a category from a
    dropdown, an audience from a list of `.json` filenames, and a brand profile
    typed into a FREE-TEXT box that silently selected the disposition library.
    Every one is derivable from the brand, and the free-text one failed hard:
    `DispositionLibrary.load` raises `FileNotFoundError` on a typo, so a
    misspelling ended the prepare after the creative had been uploaded.

    ⚠ It carries the resolved `template` and `dispositions` rather than the ids
    needed to re-load them, and that is deliberate. Re-loading would mean the
    caller resolving `runs/` a SECOND time — and the entity loaders resolve it
    from `agent.telemetry.runs_root()` while this server resolves it from the
    `runs_root` handed to `create_app`. Two spellings of that path is the exact
    bug that put a finished ~$4 run somewhere the app could not see it. One
    lookup, here, and the result travels.
    """

    brand_profile_id: str
    category: str
    library_id: str
    audience_id: str
    template: AudienceSpec
    dispositions: tuple

    @property
    def n_consumer_types(self) -> int:
        return len(self.dispositions)


def discover_brands(runs_root: Path, *, account: str) -> list[BrandChoice]:
    """The brands this account can actually run a read against.

    ⚠ Filtered by the ENGINE'S OWN predicates rather than by what exists on
    disk. This is the `#29` rule, and it replaced a `discover_specs` that
    applied the same discipline to the audience-file picker this supersedes:
    listing something guaranteed to fail is worse than not listing it, because
    the failure lands AFTER the operator has filled in the whole form and
    uploaded the creative.

    A brand is offered only when all four hold, and each rules out a real
    failure that has a shape:

      * the profile parses and names a category (nothing to run against);
      * its disposition library loads (the free-text-typo failure, now
        unreachable from the form);
      * it has a saved audience whose spec VALIDATES (the `*_baseline.json`
        failure, in its entity form);
      * the audience's disposition labels all RESOLVE against the library — a
        saved audience naming a type its own library dropped would pass its own
        validate() and then die inside `RunService.prepare`.

    ⚠ `audience_ids` is a list. The first entry whose spec both validates and
    resolves wins, so a profile carrying a broken audience alongside a working
    one is offered rather than hidden. Every profile on disk carries exactly
    one today; the rule is written down so the second does not surprise anyone.

    ⚠ `runs_root` is a PARAMETER, matching `discover_runs`, and the entities are
    read through it rather than through `BrandProfile.load` and friends — those
    resolve the path themselves from `agent.telemetry`, which is a different
    spelling of it. See `BrandChoice`.
    """
    out: list[BrandChoice] = []
    root = runs_root / account
    if not root.is_dir():
        return out
    for profile_path in sorted(root.glob("*/entities/brand_profile.json")):
        entities = profile_path.parent
        brand_id = profile_path.parts[-3]
        try:
            profile = BrandProfile.from_dict(json.loads(profile_path.read_text()))
            library = DispositionLibrary.from_dict(
                json.loads((entities / "library.json").read_text()))
        except Exception:  # noqa: BLE001 — any failure means "do not offer it"
            continue
        if not profile.categories:
            continue
        for audience_id in profile.audience_ids:
            try:
                saved = SavedAudience.from_dict(json.loads(
                    (entities / "audiences" / f"{audience_id}.json").read_text()))
                saved.spec.validate()
                dispositions = library.resolve(saved.spec.disposition_labels)
            except Exception:  # noqa: BLE001
                continue
            out.append(BrandChoice(
                brand_profile_id=brand_id,
                category=profile.categories[0],
                library_id=profile.library_id,
                audience_id=audience_id,
                template=saved.spec,
                dispositions=tuple(dispositions),
            ))
            break
    out.sort(key=lambda b: b.brand_profile_id)
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


def peek_run(runs_root: Path, key: str) -> tuple[str, str]:
    """`(asset_label, decision)` for a run that may not have finished.

    `discover_runs` deliberately skips runs with no Report, so the status page
    — whose whole subject is a run that has not finished — cannot use it. This
    reads the same file with no such requirement, and returns empty strings
    rather than raising: every field it wants is one the engine writes later.
    """
    path = resolve_run(runs_root, key)
    if path is None:
        return "", ""
    raw = _peek(path / "run.json") or {}
    config = raw.get("config", {}) or {}
    asset = config.get("asset", {}) or {}
    report = raw.get("report") or {}
    if not report:
        report = _peek(path / "replay_report.json") or {}
    decision = (report.get("decision") or {}).get("decision", "") if report else ""
    return asset.get("label", "") or "", decision or ""


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

    `audience_aligned` gets no such pass. It quotes the declared audience the
    same way, and it is NOT a guardrail — it is the same check passing. So it
    is stripped with the rest of the identity.

    ⚠ `homogeneity_note` is stripped too, and it is the one addition to "exactly
    those and nothing else". It is not diagnosis — it reports how many EARLIER
    runs this brand has on record, and that count is identity. A contact's own
    ad is typically the first run under a newly-created brand profile, so it
    reads "no baseline for this brand yet"; the decoy comes from a library brand
    with a long history and reads "typical for this brand across 15 earlier
    runs". That difference lets someone pick correctly WITHOUT reading either
    diagnosis, which is precisely the measurement the decoy exists to make.
    Everything the note says about the panel is meaningless without its
    baseline anyway — the copy says so itself.
    """
    return replace(
        model,
        asset_label=f"Read {slot}",
        # Belt and braces with embed_image=False: no path, nothing to embed.
        asset_path=None,
        run_id=f"read-{slot}",
        declared_targeting="",
        declared_audience="",
        audience_aligned=None,
        homogeneity_note=None,
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
