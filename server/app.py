"""The FastAPI app — routes only. The protocol lives in server/sessions.py and
the rendering in server/runs.py.

⚠ EVERY route here is a plain `def`, never `async def`, and that is load-bearing
rather than stylistic. `RunService.commit` calls `asyncio.run()` internally
(`agent/run_service.py:494`), which raises inside a running event loop; report
rendering embeds a creative as base64 and blocks the loop while it does. Sync
routes run in Starlette's threadpool, where both are fine. An `async def` here
is a rewrite, not a patch.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import (
    HTMLResponse, JSONResponse, RedirectResponse, Response,
)

from agent.config import build_run_config, default_asset_label
from agent.purpose import DEFAULT_PURPOSE, PURPOSE_ORDER, resolve_purpose
from agent.read_model import build_read_model, purpose_scope_note
from server import pages
from server.launcher import VALIDATED_CATEGORIES, Launcher
from server.runs import discover_runs, render_blinded, render_run, resolve_run
from server.sessions import SLOTS, PredictionMissing, SessionError, SessionStore

REPO_ROOT = Path(__file__).resolve().parent.parent


def create_app(
    *,
    runs_root: Path | None = None,
    sessions_root: Path | None = None,
    base_dir: Path | None = None,
    specs_dir: Path | None = None,
    uploads_dir: Path | None = None,
    launcher: Launcher | None = None,
) -> FastAPI:
    """Build the app against explicit roots.

    Everything is injected rather than read from module globals so the tests
    can point the whole server at a temp directory — and so `runs/` (real
    money, real client data) is never touched by a test run.
    """
    runs_root = Path(runs_root or REPO_ROOT / "runs")
    sessions_root = Path(
        sessions_root or os.environ.get("ROCKET_SESSIONS_DIR")
        or REPO_ROOT / "sessions"
    )
    # base_dir resolves the repo-relative asset paths recorded in run configs.
    # NOT Path.cwd(): uvicorn can be started from anywhere, and the failure is
    # silent — the creative simply disappears from the page.
    base_dir = Path(base_dir or REPO_ROOT)
    specs_dir = Path(specs_dir or REPO_ROOT / "specs")
    uploads_dir = Path(uploads_dir or REPO_ROOT / "uploads")

    app = FastAPI(title="Rocket — operator", docs_url=None, redoc_url=None)
    store = SessionStore(sessions_root)
    # Injected so tests can drive the run flow without ever calling the paid
    # engine. Nothing in the offline suite may reach RunService.
    runner = launcher or Launcher()

    # ---- helpers ----

    def _session(session_id: str):
        try:
            session = store.load(session_id)
        except SessionError:
            session = None
        if session is None:
            raise HTTPException(status_code=404, detail="No such session.")
        return session

    def _html(body: str, status: int = 200) -> HTMLResponse:
        return HTMLResponse(body, status_code=status)

    # ---- console ----

    @app.get("/", response_class=HTMLResponse)
    def console() -> HTMLResponse:
        return _html(pages.console(store.list(), discover_runs(runs_root)))

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        return JSONResponse({
            "ok": True,
            "runs_root": str(runs_root),
            "sessions_root": str(sessions_root),
            "finished_runs": len(discover_runs(runs_root)),
        })

    # ---- reports, outside a session (operator's own view) ----

    @app.get("/runs/{account_id}/{brand_profile_id}/{run_id}",
             response_class=HTMLResponse)
    def run_report(account_id: str, brand_profile_id: str,
                   run_id: str) -> HTMLResponse:
        path = resolve_run(runs_root, f"{account_id}/{brand_profile_id}/{run_id}")
        if path is None:
            raise HTTPException(status_code=404, detail="No such run.")
        try:
            return _html(render_run(path, base_dir=base_dir))
        except (ValueError, FileNotFoundError) as exc:
            # build_read_model refuses a run with no Report. Surface that,
            # never a blank page — this one can be in front of a prospect.
            return _html(pages.error_page("This run has no read", str(exc)), 409)

    # ---- starting a run (PAID) ----

    @app.get("/runs/new", response_class=HTMLResponse)
    def new_run() -> HTMLResponse:
        specs = sorted(p.name for p in specs_dir.glob("*.json"))
        cats = sorted(
            (p.stem, p.stem in VALIDATED_CATEGORIES)
            for p in (REPO_ROOT / "packs").glob("*.py")
            if not p.stem.startswith("_")
        )
        # Validated categories first — the picker should make the safe choice
        # the obvious one, not bury it alphabetically among the unvalidated.
        cats.sort(key=lambda c: (not c[1], c[0]))
        return _html(pages.new_run_page(specs, cats, list(PURPOSE_ORDER)))

    @app.post("/runs/prepare")
    def prepare_run(
        asset: UploadFile = File(...),
        category: str = Form(...), audience_spec: str = Form(...),
        asset_label: str = Form(""), declared_targeting: str = Form(""),
        purpose: str = Form(DEFAULT_PURPOSE), account: str = Form("demo"),
        brand_profile: str = Form("default"), library_id: str = Form(""),
        audience_id: str = Form(""), marketer_led: str = Form(""),
    ) -> Response:
        """PAID (~$0.15). Classifies the ad, resolves the panel, debits nothing."""
        spec_path = (specs_dir / Path(audience_spec).name)
        if not spec_path.exists():
            return _html(pages.error_page(
                "No such audience spec",
                f"{audience_spec!r} is not in {specs_dir}.",
            ), 400)

        uploads_dir.mkdir(parents=True, exist_ok=True)
        # Never reuse the client-supplied name as a path: it is attacker- (or
        # Finder-) controlled. A timestamp plus a token keeps two uploads of
        # "ad.png" apart, and keeps the run config pointing at a stable file
        # for as long as the report can be re-rendered from it.
        suffix = Path(asset.filename or "").suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            return _html(pages.error_page(
                "Unsupported image type",
                f"{asset.filename!r} is not a .png / .jpg / .webp.",
            ), 400)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = uploads_dir / f"{stamp}_{secrets.token_hex(3)}{suffix}"
        dest.write_bytes(asset.file.read())
        # Record the creative the way every existing run records it — relative
        # to the repo root — so an uploaded run's directory stays as portable
        # and re-renderable as a CLI one.
        try:
            recorded = dest.relative_to(base_dir)
        except ValueError:
            recorded = dest

        config = build_run_config(
            asset_path=recorded,
            asset_label=asset_label or default_asset_label(
                asset.filename or dest.name),
            audience_spec=spec_path, category=category,
            account_id=account, brand_profile_id=brand_profile,
            library_id=library_id, audience_id=audience_id,
            declared_targeting=declared_targeting, purpose=purpose,
            marketer_led=bool(marketer_led),
            max_concurrent_agents=100,
        )
        try:
            prep = runner.prepare(config)
        except (ValueError, FileNotFoundError) as exc:
            return _html(pages.error_page("Could not prepare the run", str(exc)), 400)

        preset = resolve_purpose(config.creative_inputs.purpose)
        return _html(pages.preparation_page(
            prep,
            scope_note=purpose_scope_note(config.creative_inputs.purpose),
            purpose_label=preset.label, metric_label=preset.metric_label,
            estimated=f"${prep.estimated_cost_usd:.2f}",
            unvalidated_category=(
                config.category if config.category not in VALIDATED_CATEGORIES
                else None
            ),
        ))

    @app.post("/runs/commit")
    def commit_run(run_id: str = Form(...),
                   acknowledge_mismatch: str = Form(""),
                   acknowledge_unvalidated_category: str = Form("")) -> Response:
        """PAID (~$4). Debits a credit and runs L1→L4 on a worker thread."""
        prep = runner.take(run_id)
        if prep is None:
            return _html(pages.error_page(
                "That prepared run is gone",
                "Prepared runs are held in memory, so a server restart between "
                "preparing and committing loses them. The preparation itself is "
                "on disk under the run directory; prepare again to commit.",
            ), 409)
        # The CLI refuses to auto-commit through a gross demographic mismatch
        # even with --yes. A click is cheaper than a flag, so the same refusal
        # is enforced here rather than left to the form's `required` attribute,
        # which any direct POST skips.
        if prep.demographic_mismatch is not None and not acknowledge_mismatch:
            return _html(pages.error_page(
                "Gross demographic mismatch — not committed",
                f"{prep.demographic_mismatch.message} No credit debited. Confirm "
                "deliberately on the preparation screen if the mismatch is "
                "intentional, or fix the declared audience or the creative.",
            ), 409)
        # The category gate is the MORE dangerous of the two: a mismatch
        # produces a read of the wrong people, an unvalidated category produces
        # a confident read of nobody — every persona lands "outside", and the
        # output is fluent and wrong. Leaving it advisory while the weaker
        # guardrail is a hard gate had it backwards.
        if (prep.config.category not in VALIDATED_CATEGORIES
                and not acknowledge_unvalidated_category):
            return _html(pages.error_page(
                "Unvalidated category — not committed",
                f"{prep.config.category!r} has no hand-built, validated "
                "disposition library. The engine will not fail gracefully: it "
                "emits a confident, wrong read. No credit debited. Author the "
                "library first, or tick the acknowledgement on the preparation "
                "screen if this run is a deliberate experiment.",
            ), 409)

        job = runner.commit(prep)
        return RedirectResponse(f"/runs/status/{job.key}", status_code=303)

    @app.get("/runs/status/{account_id}/{brand_profile_id}/{run_id}",
             response_class=HTMLResponse)
    def run_status(account_id: str, brand_profile_id: str,
                   run_id: str) -> HTMLResponse:
        key = f"{account_id}/{brand_profile_id}/{run_id}"
        return _html(pages.run_status_page(runner.status(runs_root, key)))

    @app.get("/runs/status.json/{account_id}/{brand_profile_id}/{run_id}")
    def run_status_json(account_id: str, brand_profile_id: str,
                        run_id: str) -> JSONResponse:
        key = f"{account_id}/{brand_profile_id}/{run_id}"
        return JSONResponse(runner.status(runs_root, key))

    # ---- sessions ----

    @app.post("/sessions")
    def create_session(
        contact: str = Form(...), company: str = Form(...),
        real_key: str = Form(...), decoy_key: str = Form(...),
        ad_label: str = Form(""),
    ) -> Response:
        for key in (real_key, decoy_key):
            if resolve_run(runs_root, key) is None:
                return _html(pages.error_page(
                    "That read is not on disk",
                    f"No finished run at {key!r}. A session needs a rendered "
                    "Creative Read for their ad and one for a different ad.",
                ), 400)
        # The decoy has to be a HARD comparison or it certifies nothing.
        # docs/v3_discriminant_check.md: reads whose inferred audiences differ
        # are uninterpretable to compare — the valid pair there was control vs
        # TWT, not control vs MB. A coffee decoy beside a whey read is caught
        # for free (the footer even prints the category), and the session then
        # records decoy_caught=true as evidence of discriminating power it does
        # not have. Enforced here rather than in the form: the picker filters
        # for convenience, a direct POST would walk past that.
        by_key = {r.key: r for r in discover_runs(runs_root)}
        real, decoy = by_key.get(real_key), by_key.get(decoy_key)
        if real is not None and decoy is not None and real.category != decoy.category:
            return _html(pages.error_page(
                "The decoy is from a different category",
                f"Their ad is {real.category!r} and the decoy is "
                f"{decoy.category!r}. A cross-category decoy is distinguishable "
                "without reading either diagnosis, so 'they caught it' would "
                "prove nothing about whether the read discriminates. Pick a "
                "decoy from the same category.",
            ), 400)
        try:
            session = store.create(
                contact=contact, company=company, ad_label=ad_label,
                real_key=real_key, decoy_key=decoy_key,
            )
        except SessionError as exc:
            return _html(pages.error_page("Cannot start that session", str(exc)), 400)
        return RedirectResponse(f"/sessions/{session.session_id}", status_code=303)

    @app.get("/sessions/{session_id}", response_class=HTMLResponse)
    def session_home(session_id: str) -> HTMLResponse:
        return _html(pages.session_page(_session(session_id)))

    @app.get("/sessions/{session_id}/predict", response_class=HTMLResponse)
    def predict_form(session_id: str) -> HTMLResponse:
        return _html(pages.predict_page(_session(session_id)))

    @app.post("/sessions/{session_id}/predict")
    def capture_prediction(
        session_id: str,
        outcome: str = Form(...), predicted_problems: str = Form(...),
        outcome_metrics: str = Form(""), predicted_verdict: str = Form(""),
        predicted_working: str = Form(""),
    ) -> Response:
        session = _session(session_id)
        try:
            session.set_prediction({
                "outcome": outcome,
                "outcome_metrics": outcome_metrics,
                "predicted_verdict": predicted_verdict,
                "predicted_problems": predicted_problems,
                "predicted_working": predicted_working,
            })
        except SessionError as exc:
            # Editing after the reveal — refused, and the refusal is the point.
            return _html(pages.error_page("Already revealed", str(exc)), 409)
        store.save(session)
        return RedirectResponse(f"/sessions/{session_id}/reveal", status_code=303)

    @app.get("/sessions/{session_id}/reveal", response_class=HTMLResponse)
    def reveal(session_id: str) -> HTMLResponse:
        session = _session(session_id)
        try:
            if session.mark_revealed():
                store.save(session)
        except PredictionMissing as exc:
            return _html(pages.blocked_page(session, str(exc)), 403)
        return _html(pages.reveal_page(session))

    @app.get("/sessions/{session_id}/report/{slot}", response_class=HTMLResponse)
    def session_report(session_id: str, slot: str) -> HTMLResponse:
        session = _session(session_id)
        # The gate is repeated here deliberately: this URL is guessable, and a
        # gate that only covers the page with the links on it is not a gate.
        try:
            session.require_prediction()
        except PredictionMissing as exc:
            return _html(pages.blocked_page(session, str(exc)), 403)
        slot = slot.upper()
        if slot not in SLOTS:
            raise HTTPException(status_code=404, detail="No such read.")
        key = session.key_for_slot(slot)
        path = resolve_run(runs_root, key or "")
        if path is None:
            return _html(pages.error_page(
                "That read is missing",
                f"The run behind Read {slot} is no longer on disk.",
            ), 409)
        try:
            return _html(render_blinded(path, slot, base_dir=base_dir))
        except (ValueError, FileNotFoundError) as exc:
            return _html(pages.error_page("This run has no read", str(exc)), 409)

    @app.get("/sessions/{session_id}/react", response_class=HTMLResponse)
    def react_form(session_id: str) -> HTMLResponse:
        session = _session(session_id)
        try:
            session.require_prediction()
        except PredictionMissing as exc:
            return _html(pages.blocked_page(session, str(exc)), 403)
        return _html(pages.react_page(session))

    @app.post("/sessions/{session_id}/react")
    def capture_reaction(
        session_id: str,
        verdict_match: str = Form(...), diagnosis_overlap: str = Form(...),
        anything_new: str = Form(...), run_differently: str = Form(...),
        pilot_live_ad: str = Form(...),
        decoy_pick: str = Form(""), decoy_note: str = Form(""),
        diagnosis_note: str = Form(""), anything_new_what: str = Form(""),
        run_differently_what: str = Form(""), pilot_note: str = Form(""),
    ) -> Response:
        session = _session(session_id)
        try:
            session.set_reaction({
                "decoy_pick": decoy_pick, "decoy_note": decoy_note,
                "verdict_match": verdict_match,
                "diagnosis_overlap": diagnosis_overlap,
                "diagnosis_note": diagnosis_note,
                "anything_new": anything_new,
                "anything_new_what": anything_new_what,
                "run_differently": run_differently,
                "run_differently_what": run_differently_what,
                "pilot_live_ad": pilot_live_ad, "pilot_note": pilot_note,
            })
        except PredictionMissing as exc:
            return _html(pages.blocked_page(session, str(exc)), 403)
        store.save(session)
        return RedirectResponse(f"/sessions/{session_id}", status_code=303)

    def _with_engine_half(session) -> dict:
        """The capture row, both halves of it.

        brand_manager_sessions.md's table pairs `their predicted verdict +
        pains` with `engine verdict + top pains` — comparing the two IS the
        analysis. Exporting only the human half leaves every row needing a
        hand-join against run.json before it can be read.
        """
        row = session.to_dict()
        path = resolve_run(runs_root, session.real_key)
        engine: dict = {"available": False}
        if path is not None:
            try:
                m = build_read_model(path)
                engine = {
                    "available": True,
                    "run_key": session.real_key,
                    "decision": m.decision_name,
                    "trust": m.trust,
                    "headline": m.headline,
                    "verdict": m.report.verdict,
                    "confidence": m.report.confidence,
                    "asset_label": m.asset_label,
                    "top_pains": [
                        {"pain": p.pain, "funnel_stage": p.funnel_stage,
                         "severity": p.severity, "within_target": p.within_target}
                        for p in m.report.pain_map[:5]
                    ],
                    "top_changes": [c.change for c in m.report.top_3_changes],
                }
            except (ValueError, FileNotFoundError) as exc:
                engine = {"available": False, "error": str(exc)}
        row["engine"] = engine
        return row

    @app.get("/sessions/{session_id}/export")
    def export(session_id: str) -> JSONResponse:
        return JSONResponse(_with_engine_half(_session(session_id)))

    @app.get("/sessions.json")
    def export_all() -> JSONResponse:
        return JSONResponse([_with_engine_half(s) for s in store.list()])

    return app


app = create_app()
