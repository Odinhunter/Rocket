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
import time
from urllib.parse import quote
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    HTMLResponse, JSONResponse, RedirectResponse, Response,
)

from agent.config import build_run_config, default_asset_label
from agent.progress import phase_view
from agent.purpose import DEFAULT_PURPOSE, PURPOSE_ORDER, resolve_purpose
from agent.read_model import build_read_model, purpose_scope_note
from server import app_html, pages
from server.auth import COOKIE_NAME, DEMO_ACCOUNT, Auth, RequireSignIn, safe_next
from server.launcher import VALIDATED_CATEGORIES, Launcher
from server.runs import (
    discover_runs, peek_run, render_blinded, render_run, resolve_run,
)
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
    auth: Auth | None = None,
    contact_email: str | None = None,
) -> FastAPI:
    """Build the app against explicit roots.

    Everything is injected rather than read from module globals so the tests
    can point the whole server at a temp directory — and so `runs/` (real
    money, real client data) is never touched by a test run.

    `auth` is injected the same way, and for the same reason with one
    addition: a test builds an Auth with a known password and signs in through
    the real `/login`. There is no test-only bypass, because a bypass is a
    thing that can be switched on in production.
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
    auth = auth or Auth.from_env()
    contact = (contact_email if contact_email is not None
               else os.environ.get("ROCKET_CONTACT_EMAIL", "").strip())

    # Default-deny, and outermost: it sees the request before routing, so a
    # route added later is protected without anyone remembering to protect it.
    app.add_middleware(RequireSignIn, auth=auth)

    # The label typed on the form, held only until the preparation carries its
    # own. Small, bounded by how many reads one operator starts in a session,
    # and losing it to a restart costs a line of grey text on one screen.
    _prepare_labels: dict[str, str] = {}

    def _run_label(root, key: str) -> str:
        return peek_run(root, key)[0]

    def _run_decision(root, key: str) -> str:
        return peek_run(root, key)[1]

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

    # ---- public ----

    @app.get("/", response_class=HTMLResponse)
    def landing() -> HTMLResponse:
        """The only page served to whoever finds the address.

        It reads nothing off disk. P4 replaces it with the user's own design.
        """
        return _html(pages.landing_page(contact))

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        """Public, so it says only whether the process is up.

        It used to return runs_root, sessions_root and a count of finished
        runs. On localhost that was a convenience; on a public address it is
        absolute filesystem paths and a client count, handed to anyone.
        """
        return JSONResponse({"ok": True})

    @app.get("/signin", response_class=HTMLResponse)
    def signin_form(request: Request, next: str = "") -> Response:
        # Already signed in: send them where they were going rather than
        # showing a password box to someone who has already used it.
        if auth.verify(request.cookies.get(COOKIE_NAME)) is not None:
            return RedirectResponse(safe_next(next), status_code=303)
        return _html(app_html.signin_page(
            next_url=safe_next(next, ""), configured=auth.configured))

    @app.get("/login", include_in_schema=False)
    def login_alias(next: str = "") -> Response:
        """The sign-in page was `/login` until 2026-08-03."""
        keep = safe_next(next, "")
        return RedirectResponse(
            f"/signin?next={quote(keep, safe='')}" if keep else "/signin",
            status_code=303)

    @app.get("/logout", include_in_schema=False)
    def logout_alias() -> Response:
        """Signing out is a POST now, so this cannot do it — it lands on the
        page that has the button. A GET that cleared the cookie would be
        triggerable by any <img> tag on any page."""
        return RedirectResponse("/settings", status_code=303)

    @app.post("/signin")
    def sign_in(password: str = Form(""), next: str = Form("")) -> Response:
        """`Form("")` rather than `Form(...)`: a required field turns a missing
        or empty password into a 422 validation page, which is a different and
        chattier answer than a wrong one. Every failed sign-in should look
        identical and cost the same second."""
        target = safe_next(next)
        if not auth.check_password(password):
            # A flat delay on failure. Online guessing against a single shared
            # password is the whole threat model here, and a second per attempt
            # ends it. Not a lockout — see Auth.failed_delay_seconds.
            time.sleep(auth.failed_delay_seconds)
            return _html(app_html.signin_page(
                error=("That password doesn't match. Try again."
                       if auth.configured else "Sign-in is not configured."),
                next_url=safe_next(next, ""), configured=auth.configured,
            ), 401)
        response = RedirectResponse(target, status_code=303)
        response.set_cookie(COOKIE_NAME, auth.issue(DEMO_ACCOUNT),
                            **auth.cookie_kwargs())
        return response

    @app.post("/signout")
    def sign_out() -> Response:
        """POST, not a link — the design's call and the right one. A GET
        /logout is triggerable by any image tag on any page, which signs a
        user out mid-run for no reason."""
        response = RedirectResponse("/", status_code=303)
        # Deleted with the same path the cookie was set on. A delete_cookie
        # whose path does not match leaves the cookie in place and the browser
        # signed in, silently.
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    # ---- console ----

    @app.get("/operator", response_class=HTMLResponse)
    def console() -> HTMLResponse:
        """The brand-manager session instrument, off `/` as of P3.

        It shows every account, `internal/*` included — this is our own
        surface. The product surface (P5's `/app`) is scoped; this is not.
        """
        return _html(pages.console(store.list(), discover_runs(runs_root)))

    # ---- the application ----

    @app.get("/reads", response_class=HTMLResponse)
    def reads(q: str = "") -> HTMLResponse:
        """Home. Scoped to one account — `internal/*` is our own smoke-test
        exhaust and never appears in the product surface."""
        runs = discover_runs(runs_root, account=DEMO_ACCOUNT)
        if q.strip():
            needle = q.strip().lower()
            runs = [r for r in runs
                    if needle in r.asset_label.lower()
                    or needle in r.decision.lower()
                    or needle in r.brand_profile_id.lower()]
        return _html(app_html.reads_page(runs, account=DEMO_ACCOUNT, query=q))

    @app.get("/profiles", response_class=HTMLResponse)
    def profiles() -> HTMLResponse:
        counts: dict[str, int] = {}
        for r in discover_runs(runs_root, account=DEMO_ACCOUNT):
            counts[r.brand_profile_id] = counts.get(r.brand_profile_id, 0) + 1
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return _html(app_html.profiles_page(ordered, account=DEMO_ACCOUNT))

    @app.get("/settings", response_class=HTMLResponse)
    def settings() -> HTMLResponse:
        return _html(app_html.settings_page(account=DEMO_ACCOUNT))

    # ---- the read itself ----

    # Registered twice on purpose. `/reads/...` is the name a client-facing
    # read should have had all along; `/runs/...` stays because it is in
    # session records, in bookmarks and across the tests. Two registrations of
    # one handler rather than a redirect: a redirect would change the status
    # code and the response body of every existing caller.
    @app.get("/reads/{account_id}/{brand_profile_id}/{run_id}",
             response_class=HTMLResponse)
    @app.get("/runs/{account_id}/{brand_profile_id}/{run_id}",
             response_class=HTMLResponse)
    def run_report(account_id: str, brand_profile_id: str,
                   run_id: str) -> HTMLResponse:
        path = resolve_run(runs_root, f"{account_id}/{brand_profile_id}/{run_id}")
        if path is None:
            raise HTTPException(status_code=404, detail="No such run.")
        try:
            return _html(app_html.with_back_bar(render_run(path, base_dir=base_dir)))
        except (ValueError, FileNotFoundError) as exc:
            # build_read_model refuses a run with no Report. Surface that,
            # never a blank page — this one can be in front of a prospect.
            return _html(pages.error_page("This run has no read", str(exc)), 409)

    # ---- starting a run (PAID) ----

    def _humanise(stem: str) -> str:
        """`health_wellness_nutrition` -> `Health wellness nutrition`.

        Derived, not a lookup table: a hand-written display map drifts the
        moment someone adds a pack, and the failure is a category that silently
        stops appearing in the picker.
        """
        words = stem.replace("_", " ").strip()
        return words[:1].upper() + words[1:]

    @app.get("/reads/new", response_class=HTMLResponse)
    def new_read() -> HTMLResponse:
        specs = sorted(p.name for p in specs_dir.glob("*.json"))
        cats = sorted(p.stem for p in (REPO_ROOT / "packs").glob("*.py")
                      if not p.stem.startswith("_"))
        # Validated first — the picker still leads with the safe choice even
        # though it no longer labels the others (the user's call, 2026-08-03:
        # the warning arrives on the review screen instead, before any spend).
        cats.sort(key=lambda c: (c not in VALIDATED_CATEGORIES, c))
        brands = sorted({r.brand_profile_id
                         for r in discover_runs(runs_root, account=DEMO_ACCOUNT)})
        return _html(app_html.new_read_page(
            account=DEMO_ACCOUNT,
            categories=[(c, _humanise(c)) for c in cats],
            audiences=specs,
            jobs=[(k, resolve_purpose(k).label) for k in PURPOSE_ORDER],
            brands=brands,
        ))

    @app.post("/reads/new")
    def start_prepare(
        asset: UploadFile = File(...),
        category: str = Form(...), audience_spec: str = Form(...),
        asset_label: str = Form(""), declared_targeting: str = Form(""),
        purpose: str = Form(DEFAULT_PURPOSE),
        brand_profile: str = Form(""), library_id: str = Form(""),
        audience_id: str = Form(""), marketer_led: str = Form(""),
    ) -> Response:
        """PAID (~$0.15) — but off the request thread, so the browser gets a
        page that can say what is happening instead of a spinner it owns."""
        spec_path = (specs_dir / Path(audience_spec).name)
        if not spec_path.exists():
            return _html(app_html.error_page(
                "No such audience spec",
                f"{audience_spec!r} is not in {specs_dir}.",
                account=DEMO_ACCOUNT), 400)

        uploads_dir.mkdir(parents=True, exist_ok=True)
        # Never reuse the client-supplied name as a path: it is attacker- (or
        # Finder-) controlled. A timestamp plus a token keeps two uploads of
        # "ad.png" apart, and keeps the run config pointing at a stable file
        # for as long as the report can be re-rendered from it.
        suffix = Path(asset.filename or "").suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            # Back to the form with the rejection stated and the reason next to
            # the drop target, rather than a dead-end error page — the design's
            # state 4C, and the whole point of it is that the form does not
            # clear what was already typed.
            return _html(app_html.new_read_page(
                account=DEMO_ACCOUNT,
                categories=[(c, _humanise(c)) for c in sorted(
                    p.stem for p in (REPO_ROOT / "packs").glob("*.py")
                    if not p.stem.startswith("_"))],
                audiences=sorted(p.name for p in specs_dir.glob("*.json")),
                jobs=[(k, resolve_purpose(k).label) for k in PURPOSE_ORDER],
                brands=sorted({r.brand_profile_id for r in discover_runs(
                    runs_root, account=DEMO_ACCOUNT)}),
                error="That's not a .png, .jpg or .webp.",
                filename=asset.filename or "",
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

        label = asset_label or default_asset_label(asset.filename or dest.name)
        config = build_run_config(
            asset_path=recorded, asset_label=label,
            audience_spec=spec_path, category=category,
            account_id=DEMO_ACCOUNT,
            brand_profile_id=brand_profile or "default",
            library_id=library_id, audience_id=audience_id,
            declared_targeting=declared_targeting, purpose=purpose,
            marketer_led=bool(marketer_led),
            max_concurrent_agents=100,
        )
        token = runner.prepare_async(config)
        _prepare_labels[token] = label
        return RedirectResponse(f"/reads/preparing/{token}", status_code=303)

    @app.get("/reads/preparing/{token}", response_class=HTMLResponse)
    def preparing(token: str) -> Response:
        state = runner.preparation(token)
        if state is None:
            return _html(app_html.error_page(
                "That preparation is gone",
                "Preparations are held in memory, so a server restart loses "
                "them. Nothing was charged beyond the classification itself. "
                "Start the read again.", account=DEMO_ACCOUNT), 409)
        if state.error is not None:
            return _html(app_html.error_page(
                "Could not prepare the read", state.error,
                account=DEMO_ACCOUNT), 400)
        if state.prep is not None:
            return RedirectResponse(f"/reads/review/{state.prep.run_id}",
                                    status_code=303)
        return _html(app_html.preparing_page(
            account=DEMO_ACCOUNT, label=_prepare_labels.get(token, "")))

    @app.get("/reads/review/{run_id}", response_class=HTMLResponse)
    def review(run_id: str) -> Response:
        prep = runner.take(run_id)
        if prep is None:
            return _html(app_html.error_page(
                "That prepared run is gone",
                "Prepared runs are held in memory, so a server restart between "
                "preparing and committing loses them. The preparation itself is "
                "on disk under the run directory; prepare again to commit.",
                account=DEMO_ACCOUNT), 409)
        flags, stops = _prep_flags(prep)
        tc = prep.target_classification
        a = prep.audience_summary
        chaos = ", ".join(f"{c['profile']} {c['weight'] * 100:.0f}%"
                          for c in a["chaos_distribution"])
        preset = resolve_purpose(prep.config.creative_inputs.purpose)
        return _html(app_html.review_page(
            account=DEMO_ACCOUNT, run_id=prep.run_id,
            label=prep.config.asset.label,
            meta=f"{preset.label} · {prep.config.brand_profile_id}",
            inferred=tc.inferred_target_description,
            # WHY it reads that way, not only what it reads as. The
            # design has one paragraph here; the CLI prints both, and
            # the reasoning is what lets an operator catch a
            # misclassification while it is still free to catch.
            reasoning=tc.target_reasoning,
            dispositions=[(d.disposition_label, d.classification == "within")
                          for d in tc.disposition_classifications],
            panel_lines=[
                f"{a['panel_size']} agents across "
                f"{len(a['disposition_labels'])} dispositions × "
                f"{len(a['context_envelope'])} contexts",
                f"{a['n_segments']} segments ({a['segment_granularity']})",
                f"chaos mix: {chaos}",
            ],
            panel_version=prep.panel_version,
            cost=f"${prep.estimated_cost_usd:.2f}",
            cores=prep.persona_cores_rendered,
            flags=flags, stop_count=stops,
        ))

    def _prep_flags(prep) -> tuple[list[tuple[str, str, str, bool]], int]:
        """Every warning `batch_run._print_preparation` prints, as flag rows.

        Fidelity spec is that function, NOT the design's placeholder list: a
        warning that exists in the engine and not here is a run committed
        blind (memory: report_surface_fidelity). The design supplies the ROW,
        this supplies WHICH rows.

        The two `stop=True` rows used to be hard gates that refused the commit
        without a ticked acknowledgement. They are advisory as of 2026-08-03 —
        the user's explicit decision, taken after being shown that an
        unvalidated category makes the engine answer confidently about nobody.
        The flag is loud; the button is not blocked.
        """
        tc = prep.target_classification
        rows: list[tuple[str, str, str, bool]] = []
        scope = purpose_scope_note(prep.config.creative_inputs.purpose)
        if scope:
            rows.append(("SCOPE", "Launch scope", scope, False))
        if tc.no_match_note:
            rows.append(("NO MATCH", "No match", tc.no_match_note, False))
        if tc.ambiguity_note:
            rows.append(("TARGET", "Ambiguous target", tc.ambiguity_note, False))
        if prep.coverage_warning is not None:
            c = prep.coverage_warning
            rows.append(("COVERAGE",
                         f"Thin audience coverage — {c.eligible_count}/"
                         f"{c.total_count} personas", c.message, False))
        if prep.purpose_mismatch is not None:
            pm = prep.purpose_mismatch
            rows.append(("PURPOSE",
                         f"Purpose mismatch — reads as {pm.apparent_label.upper()}, "
                         f"grading as {pm.declared_label.upper()}",
                         pm.message, False))
        if prep.trust_ceiling_warning is not None:
            rows.append(("TRUST",
                         "Trust ceiling — a confident “ship it” is unreachable "
                         "with this panel", prep.trust_ceiling_warning, False))
        if prep.provisional_dispositions:
            rows.append(("DISPOSITIONS", "Provisional dispositions",
                         ", ".join(prep.provisional_dispositions)
                         + " — awaiting team review; the report will carry the "
                         "flag.", False))
        stops = 0
        if prep.demographic_mismatch is not None:
            rows.append(("STOP", "Gross demographic mismatch",
                         prep.demographic_mismatch.message
                         + " Advisory, not a block. If this is deliberate (an "
                         "off-demographic creative under test), carry on. "
                         "Otherwise fix the declared audience, or check you "
                         "uploaded the right creative.", True))
            stops += 1
        if prep.config.category not in VALIDATED_CATEGORIES:
            rows.append(("STOP", "Unvalidated category",
                         f"There is no hand-built, validated disposition library "
                         f"for {prep.config.category!r}. The engine will not fail "
                         "gracefully: every persona classifies “outside” and the "
                         "read comes out confident and wrong.", True))
            stops += 1
        return rows, stops

    @app.post("/reads/prepared/commit")
    def commit_read(run_id: str = Form(...)) -> Response:
        """PAID (~$4). Debits a credit and runs L1→L4 on a worker thread.

        Nothing refuses here any more — see `_prep_flags`. The one refusal left
        is a prepared run that is no longer in memory, which is not a judgement
        about the run but the absence of one.
        """
        prep = runner.take(run_id)
        if prep is None:
            return _html(app_html.error_page(
                "That prepared run is gone",
                "Prepared runs are held in memory, so a server restart between "
                "preparing and committing loses them. The preparation itself is "
                "on disk under the run directory; prepare again to commit.",
                account=DEMO_ACCOUNT), 409)
        job = runner.commit(prep)
        return RedirectResponse(f"/reads/status/{job.key}", status_code=303)

    @app.get("/reads/status/{account_id}/{brand_profile_id}/{run_id}",
             response_class=HTMLResponse)
    def read_status(account_id: str, brand_profile_id: str,
                    run_id: str) -> HTMLResponse:
        key = f"{account_id}/{brand_profile_id}/{run_id}"
        status = runner.status(runs_root, key)
        progress = status.get("progress")
        phases = phase_view(progress)
        label = _run_label(runs_root, key) or run_id
        stopped = next((p["key"] for p in phases if p["state"] == "running"), None)

        if status["status"] == "complete" or status["has_report"]:
            health = status.get("panel_health") or {}
            got, want = health.get("succeeded"), health.get("expected")
            line = f"{got}/{want} agents" if want else "—"
            degraded = ""
            if health.get("degraded"):
                line += " — DEGRADED"
                missing = (want or 0) - (got or 0)
                degraded = (f"{missing} agent{'' if missing == 1 else 's'} dropped "
                            f"out mid-run. The read stands, on {got} responses "
                            f"instead of {want}.")
            return _html(app_html.complete_page(
                account=DEMO_ACCOUNT, label=label, run_id=run_id, key=key,
                decision=_run_decision(runs_root, key), health=line,
                degraded=degraded))
        if status["status"] == "failed":
            return _html(app_html.failed_page(
                account=DEMO_ACCOUNT, label=label, run_id=run_id,
                error=status.get("error") or "", phases=phases,
                stopped_at=stopped))
        if status["status"] == "interrupted":
            path = resolve_run(runs_root, key)
            # Recoverable only if the expensive half actually landed: replay
            # reads transcripts off disk, and without them there is nothing to
            # replay and the button would spend money to fail.
            recoverable = bool(path is not None and (
                (path / "transcripts.json").exists()
                or (path / "agent_calls").is_dir()))
            return _html(app_html.interrupted_page(
                account=DEMO_ACCOUNT, label=label, run_id=run_id, key=key,
                command=f"replay_synthesis.py runs/{key}",
                recoverable=recoverable,
                cost_note=(
                    "No credit is debited. It does re-run the analysis stage "
                    "through the model, which costs real money — a fraction of "
                    "a full run, because the panel is not re-asked."
                    if recoverable else
                    "The agent transcripts are not on disk, so there is nothing "
                    "to replay. This run would have to be paid for again."),
                phases=phases, stopped_at=stopped))
        return _html(app_html.running_page(
            account=DEMO_ACCOUNT, label=label, run_id=run_id, phases=phases,
            elapsed=app_html.elapsed_clock(progress), waiting=progress is None))

    @app.post("/reads/{account_id}/{brand_profile_id}/{run_id}/replay")
    def replay_read(account_id: str, brand_profile_id: str,
                    run_id: str) -> Response:
        """SPENDS MONEY, debits no credit — the distinction the button states.

        The 100 agent calls that dominate a run's bill are read back off disk;
        only L2→L4 go through the model again. Refused when the transcripts are
        not there, because then there is nothing to replay and the spend would
        buy a failure.
        """
        key = f"{account_id}/{brand_profile_id}/{run_id}"
        path = resolve_run(runs_root, key)
        if path is None:
            raise HTTPException(status_code=404, detail="No such run.")
        if not ((path / "transcripts.json").exists()
                or (path / "agent_calls").is_dir()):
            return _html(app_html.error_page(
                "Nothing to recover",
                "This run has no agent transcripts on disk, so there is nothing "
                "for the analysis stage to re-read. Recovering it would spend "
                "money to reach the same place. The panel would have to be run "
                "again from the start.", account=DEMO_ACCOUNT), 409)
        runner.replay(path, key)
        return RedirectResponse(f"/reads/status/{key}", status_code=303)

    @app.get("/reads/status.json/{account_id}/{brand_profile_id}/{run_id}")
    def read_status_json(account_id: str, brand_profile_id: str,
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
