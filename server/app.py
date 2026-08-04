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
from fastapi.staticfiles import StaticFiles

from agent.config import build_run_config, default_asset_label
from agent.progress import phase_view
from agent.purpose import DEFAULT_PURPOSE, PURPOSE_ORDER, resolve_purpose
from agent.read_model import (
    HEADLINE_CAVEAT,
    OUT_OF_TARGET_ONLY_NOTE,
    build_read_model,
    purpose_scope_note,
)
from agent.telemetry import runs_root as engine_runs_root
from server import app_html, audience_form, pages
from server.auth import COOKIE_NAME, DEMO_ACCOUNT, Auth, RequireSignIn, safe_next
from server.launcher import VALIDATED_CATEGORIES, Launcher
from server.runs import (
    discover_brands, discover_runs, peek_run, render_blinded, render_run,
    resolve_run,
)
from server.sessions import SLOTS, PredictionMissing, SessionError, SessionStore

REPO_ROOT = Path(__file__).resolve().parent.parent


def create_app(
    *,
    runs_root: Path | None = None,
    sessions_root: Path | None = None,
    base_dir: Path | None = None,
    uploads_dir: Path | None = None,
    static_dir: Path | None = None,
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
    # ⚠ The SAME expression the engine writes through (agent.telemetry.
    # runs_root), never a second spelling of it. These were two: the server
    # read REPO_ROOT/"runs" while the engine wrote cwd-relative "runs". Start
    # uvicorn from anywhere but the repo root and a ~$4 run completes into a
    # directory this server never looks at — spent, finished, and invisible.
    runs_root = Path(runs_root or engine_runs_root())
    sessions_root = Path(
        sessions_root or os.environ.get("ROCKET_SESSIONS_DIR")
        or REPO_ROOT / "sessions"
    )
    # base_dir resolves the repo-relative asset paths recorded in run configs.
    # NOT Path.cwd(): uvicorn can be started from anywhere, and the failure is
    # silent — the creative simply disappears from the page.
    base_dir = Path(base_dir or REPO_ROOT)
    uploads_dir = Path(uploads_dir or REPO_ROOT / "uploads")
    # REPO_ROOT, not cwd, for the same reason as base_dir above.
    static_dir = Path(static_dir or REPO_ROOT / "static")
    # Created, not required. An empty static/ is a legitimate state — the
    # landing page is required to look finished with its video absent — and
    # StaticFiles re-checks the directory on the FIRST REQUEST as well as at
    # construction, so `check_dir=False` does not buy tolerance here, it only
    # moves the failure from a loud startup error to a 500 on an asset.
    static_dir.mkdir(parents=True, exist_ok=True)

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

    # The landing page's own assets — its video, its poster, its images.
    #
    # StaticFiles rather than a route that reads the file and returns bytes:
    # only this serves Range requests, and without them a browser cannot seek
    # inside a video. The failure is not an error, it is a scrub bar that does
    # nothing, which reads as a broken page rather than a missing feature.
    #
    # This is an ASGI mount, not a route: the "every route is a plain def"
    # rule at the top of this file does not apply to it, and wrapping it in
    # one would be the mistake. "/static/" is already in auth.PUBLIC_PREFIXES,
    # trailing slash and all, and the middleware sees the path before routing.
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def landing() -> HTMLResponse:
        """The only page served to whoever finds the address.

        It reads nothing off disk. P4 replaces it with the user's own design.
        """
        return _html(pages.landing_page(contact))

    @app.get("/methodology", response_class=HTMLResponse)
    def methodology() -> HTMLResponse:
        """How the instrument works, and what it can and cannot tell you.

        PUBLIC on purpose (`auth.PUBLIC_EXACT`). This is where the read's
        standing qualifications went when they came off the page on 2026-08-04,
        and a prospect being able to read them before they have an account is
        the point of the change rather than a side effect of it. It reads
        nothing off disk and names no client.
        """
        return _html(pages.methodology_page(contact))

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

    def _brand_choices() -> list:
        """Brands offered by the picker, validated brands first.

        Validated leads for the same reason the category list used to: the safe
        choice is the default one, and the warning about anything else arrives
        on the review screen before a credit is debited (the user's call,
        2026-08-03). Nothing is labelled here.
        """
        brands = discover_brands(runs_root, account=DEMO_ACCOUNT)
        brands.sort(key=lambda b: (b.category not in VALIDATED_CATEGORIES,
                                   b.brand_profile_id))
        return brands

    def _brand_options(brands: list) -> list[tuple[str, str]]:
        """`(value, label)` for the brand select. The category rides in the
        label because a brand profile carries no display name of its own, and
        "which research library is behind this" is the one thing about the
        choice a customer might actually want to check."""
        return [(b.brand_profile_id,
                 f"{_humanise(b.brand_profile_id)} — {_humanise(b.category)}")
                for b in brands]

    def _new_read_form(answers: dict | None = None, *, error: str = "",
                       filename: str = "") -> str:
        """The form, rendered from one place.

        It is reached three ways — first visit, a rejected upload, and a
        rejected audience answer — and the two rejection paths must come back
        with everything already chosen still chosen. Building it in three
        places is how state 4C ("the form does not clear what was typed")
        silently stops being true on one of them.
        """
        brands = _brand_choices()
        line = ""
        if brands:
            try:
                chosen, ans = _resolve_audience(answers or {}, brands)
                line = audience_form.reach(
                    audience_form.build_spec(chosen.template, ans),
                    list(chosen.dispositions)).sentence
            except Exception:  # noqa: BLE001 — a reach line is never load-bearing
                line = ""
        return app_html.new_read_page(
            account=DEMO_ACCOUNT, brands=_brand_options(brands),
            jobs=[(k, resolve_purpose(k).label) for k in PURPOSE_ORDER],
            answers=answers, reach_line=line, error=error, filename=filename,
        )

    def _resolve_audience(data: dict, brands: list):
        """(brand choice, validated answers) or raise `AudienceAnswerError`.

        The brand is checked against the DISCOVERED list rather than loaded
        straight from the posted id: that id reaches here from a form field, so
        treating it as a path component would let a hand-posted request read an
        entity directory outside this account.
        """
        wanted = str(data.get("brand", "") or "").strip()
        chosen = next((b for b in brands if b.brand_profile_id == wanted),
                      brands[0] if wanted == "" else None)
        if chosen is None:
            raise audience_form.AudienceAnswerError(
                "Pick one of your brands from the list.")
        return chosen, audience_form.parse(data)

    @app.get("/reads/new", response_class=HTMLResponse)
    def new_read() -> HTMLResponse:
        return _html(_new_read_form())

    @app.get("/reads/audience-reach")
    def audience_reach(brand: str = "", age_from: str = "", age_to: str = "",
                       gender: str = "", income: str = "",
                       geography: str = "") -> JSONResponse:
        """How many of the brand's consumer types this buy reaches. $0.

        Pure range arithmetic against the brand's own library — no model call,
        measured at 0.2ms — which is what lets the form update it live while
        someone is still choosing. It exists so the narrow-audience case is
        visible at the point of CHOOSING rather than after a ~$4 run has
        already produced a single-segment read.

        Answers 200 with a readable sentence in every case, including a bad
        one: this feeds a line of text beside a form, and a 4xx here would
        replace guidance with nothing at the moment it is most useful.
        """
        brands = _brand_choices()
        if not brands:
            return JSONResponse({"sentence": ""})
        data = {"brand": brand, "age_from": age_from, "age_to": age_to,
                "gender": gender, "income": income, "geography": geography}
        try:
            chosen, answers = _resolve_audience(data, brands)
            spec = audience_form.build_spec(chosen.template, answers)
            return JSONResponse({
                "sentence": audience_form.reach(
                    spec, list(chosen.dispositions)).sentence,
                "targeting": answers.declared_targeting(),
            })
        except audience_form.AudienceAnswerError as exc:
            return JSONResponse({"sentence": str(exc)})
        except (OSError, ValueError, KeyError):
            return JSONResponse({"sentence": ""})

    @app.post("/reads/new")
    def start_prepare(
        asset: UploadFile = File(...),
        brand: str = Form(""), asset_label: str = Form(""),
        age_from: str = Form(""), age_to: str = Form(""),
        gender: str = Form(""), income: str = Form(""),
        geography: str = Form(""),
        purpose: str = Form(DEFAULT_PURPOSE),
    ) -> Response:
        """PAID (~$0.15) — but off the request thread, so the browser gets a
        page that can say what is happening instead of a spinner it owns.

        ⚠ The signature is the 2026-08-04 rewrite: `category`, `audience_spec`,
        `declared_targeting`, `brand_profile`, `library_id` and `marketer_led`
        are gone as INPUTS. Every one is now derived — the first five from the
        brand, the last because `marketer_led` is what makes the customer's
        declared demographics compose the panel, so a form built entirely out
        of those demographics can only ever want it on. A checkbox that must
        never be unticked is not a choice, it is a trap.
        """
        answers_raw = {"brand": brand, "age_from": age_from, "age_to": age_to,
                       "gender": gender, "income": income, "geography": geography,
                       "purpose": purpose}
        brands = _brand_choices()
        if not brands:
            return _html(_new_read_form(), 400)
        try:
            chosen, answers = _resolve_audience(answers_raw, brands)
        except audience_form.AudienceAnswerError as exc:
            return _html(_new_read_form(answers_raw, error=str(exc)), 400)

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
            # clear what was already chosen.
            return _html(_new_read_form(
                answers_raw, error="That's not a .png, .jpg or .webp.",
                filename=asset.filename or ""), 400)
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
        # The brand's saved audience, re-aimed at the buy they described. The
        # customer supplies `demographics`; the consumer types, attention
        # moments, behavioural mix and panel size come from the brand's own
        # hand-built research and are not theirs to author.
        spec = audience_form.build_spec(chosen.template, answers)
        config = build_run_config(
            asset_path=recorded, asset_label=label,
            audience_spec=spec, category=chosen.category,
            account_id=DEMO_ACCOUNT,
            brand_profile_id=chosen.brand_profile_id,
            library_id=chosen.library_id, audience_id=chosen.audience_id,
            # Composed from the same answers that built the frame above, so the
            # classifier's hint and the panel's frame can no longer disagree —
            # which they could whenever someone typed one audience into the old
            # free-text box and selected another from the spec dropdown.
            declared_targeting=answers.declared_targeting(), purpose=purpose,
            marketer_led=True,
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
                "Could not prepare the read",
                "The run was refused before it started, so there is nothing to "
                "review and nothing to commit.",
                detail=state.error,
                note="No credit was debited — a credit is only debited when you "
                     "commit a run. If the classifier had already run before "
                     "this failed, that step (about $0.15) is spent.",
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
        """What the operator should see before spending ~$4.

        ⚠ REWRITTEN 2026-08-04 on the user's explicit decision, and the rule
        that decides what appears here is worth stating because it is the one
        judgement in this change that is not "remove it":

            Does this tell them something about THEIR OWN INPUT that they can
            act on before paying — or is it a limit of OUR INSTRUMENT?

        The first kind stays. It protects their money: a mismatched creative, a
        category we cannot read, an ad whose job is not the job they picked are
        all things they can fix in thirty seconds, and letting someone spend $4
        to discover it is a worse failure than any wording. The second kind
        moves to the methodology page, where it can be read by anyone who goes
        looking. Eight qualifications on the screen before the button read as a
        product apologising for itself, which is what this removes.

        Moved OFF this screen (instrument limits, not their input):
          * launch scope — that a purpose is BETA is our maturity, not their ad;
          * trust ceiling — "a confident ship-it is unreachable with this panel"
            is the purest example of the register the user objected to;
          * provisional dispositions — internal library bookkeeping.

        ⚠ The STOP tag and the "N flags are marked STOP" counter are gone, but
        NOTHING BELOW IS: both former STOP rows still render, with their
        consequence text intact, because that text is the entire guardrail now
        that the commit gates are advisory (the user's call, 2026-08-03). The
        tests pin the consequence wording word for word — change the copy and
        change them together, deliberately.

        Fidelity note: `batch_run._print_preparation` is the CLI equivalent and
        is deliberately NOT changed. It is an operator instrument, and it keeps
        every row (memory: report_surface_fidelity).
        """
        tc = prep.target_classification
        rows: list[tuple[str, str, str, bool]] = []
        # --- about the creative they uploaded --------------------------------
        if prep.demographic_mismatch is not None:
            rows.append(("CHECK", "The creative and the audience don't match",
                         prep.demographic_mismatch.message
                         + " If that is deliberate — an off-demographic creative "
                         "under test — carry on. Otherwise fix the audience, or "
                         "check you uploaded the right creative.", False))
        if prep.purpose_mismatch is not None:
            pm = prep.purpose_mismatch
            rows.append(("CHECK",
                         f"This reads as a {pm.apparent_label.lower()} ad, and "
                         f"you picked {pm.declared_label.lower()}",
                         pm.message, False))
        if tc.no_match_note:
            rows.append(("CHECK", "The creative and the audience don't overlap",
                         tc.no_match_note, False))
        if tc.ambiguity_note:
            rows.append(("CHECK", "Who this ad is for is ambiguous",
                         tc.ambiguity_note, False))
        # --- about the audience they chose -----------------------------------
        if prep.coverage_warning is not None:
            c = prep.coverage_warning
            rows.append(("REACH",
                         f"This audience reaches {c.eligible_count} of "
                         f"{c.total_count} consumer types", c.message, False))
        # --- about the category, which is what actually protects the $4 ------
        if prep.config.category not in VALIDATED_CATEGORIES:
            rows.append(("CHECK", "We haven't validated this category yet",
                         f"There is no hand-built, validated disposition library "
                         f"for {prep.config.category!r}. The engine will not fail "
                         "gracefully: every persona classifies “outside” and the "
                         "read comes out confident and wrong.", False))
        # `stops` is retained at 0 so `review_page`'s counter line never
        # renders. The parameter stays in the signature rather than being
        # ripped out, because reinstating a gate is the user's decision to make
        # later and this keeps that a one-line change.
        return rows, 0

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
                    # ⚠ The caveat travels WITH the number, and it matters more
                    # here than on the page. This export is the Track-2
                    # artifact — engine read against a known outcome — so this
                    # figure lands in an analysis next to real CTR/ROAS, where a
                    # bare number reads as a measurement. Its signal-to-noise is
                    # 1.0 (scripts/gate_test.py). On the page the caveat is one
                    # line below it; in a spreadsheet there is no "below".
                    "headline_caveat": HEADLINE_CAVEAT if m.headline else None,
                    "verdict": m.report.verdict,
                    "confidence": m.report.confidence,
                    "asset_label": m.asset_label,
                    "top_pains": [
                        {"pain": p.pain, "funnel_stage": p.funnel_stage,
                         "severity": p.severity, "within_target": p.within_target}
                        for p in m.report.pain_map[:5]
                    ],
                    # The prevalence floor applies HERE TOO. This is a
                    # hand-assembled projection of ReadModel — the shape that
                    # dropped two guardrails in sample_report.html — so reading
                    # report.top_3_changes directly would export, as ranked, a
                    # fix that both the read and the CLI demote.
                    "top_changes": [c.change for c in m.ranked_changes],
                    "unranked_changes": [c.change for c in m.unranked_changes],
                    "unranked_reason": (OUT_OF_TARGET_ONLY_NOTE
                                        if m.unranked_changes else None),
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
