# The application build — plan and decisions

**Written 2026-08-02, session 27.** The dashboard is finished (`agent/dashboard_html.py`).
This plan covers what wraps around it: a landing page, a login, and a product skin over the
upload → processing → read flow.

Method is the one that worked for the dashboard: **the user designs, we productionalize.**

**The two halves are owned by different people (decided 2026-08-02):**

| | owner | artifact |
|---|---|---|
| **the landing page** | **the user** — Higgsfield for motion, their own Pinterest references, their own design rounds | `docs/v3_landing_page_playbook.md` — structure, claim rules, video specs. Not a paste-ready prompt. |
| **the application shell** | **us** | `docs/v3_app_shell_design_prompt.md` — paste-ready, pasted as-is |

They were always going to be separate prompts (a marketing page and an application are different
design problems, and a mega-prompt is what produced the three overshoot rounds). The ownership
split makes that structural.

---

## 1. What already exists (do not rebuild it)

The user's framing was "the upload, the processing, the result — that part is entirely left."
It is not. `server/app.py` already carries the whole spine:

| flow step | route today | state |
|---|---|---|
| upload a creative | `GET /runs/new` → `POST /runs/prepare` | built — file allowlist, safe rename, config build |
| what it will cost + the gates | `preparation_page` | built — every warning `batch_run._print_preparation` prints |
| commit | `POST /runs/commit` | built — idempotent, worker thread, returns immediately |
| processing | `GET /runs/status/{key}` (+ `.json`) | built — `<meta http-equiv="refresh" content="10">`, no JS |
| the read | `GET /runs/{account}/{brand}/{run_id}` | built — the finished dashboard |

`runs/{account_id}/{brand_profile_id}/{run_id}` on disk **is** the `Account → Brand Profile →
Run` model from memory `icp_and_account_model`. Nothing about it needs inventing.

**Genuinely missing:** a landing page, a login, per-account scoping, the product skin, and a
route map that does not have the operator console sitting on `/`.

---

## 2. Decisions taken with the user, 2026-08-02

| question | answer |
|---|---|
| **Who logs in?** | **Us only, for demos.** One shared login. No self-serve signup, no billing, no password reset, no per-customer isolation. A brand manager sees a real login and a real account; nobody outside can create one. |
| **Where does it run?** | **A real web address**, openable on any laptop and linkable. Not localhost-only. |
| **What can a convinced prospect do?** | **Write an email.** With no self-serve signup, a page whose only action is a login they cannot use is a dead end. So the landing page carries **Sign in** plus a plain `mailto:` contact — no capture form, no waitlist. It also happens to describe how onboarding actually works today. |
| **What does the site say about categories?** | **Nothing at all.** The user's words: *"we will do only nutrition and health but no talk of any categories."* In practice: only nutrition/health work gets shown to anyone, and the marketing copy never raises the subject of coverage. **Inside the app the category picker and the unvalidated-category gate stay exactly as they are** — we still run deliberate out-of-category experiments ourselves (Starbucks, boAt), and the gate is what keeps those from being mistaken for a real read. Silent in the marketing, enforced in the product. |

### The consequence of "a real web address"

The money gate and the category gate stop being UX and become security surfaces, and
`sessions/` holds a contact's confidential CTR/ROAS on disk. Therefore, non-negotiable:

- Every paid route sits **behind the login**. A logged-out `POST /app/commit` must 401, not run.
- HTTPS only; the login cookie is `Secure`, `HttpOnly`, `SameSite=Lax`.
- `ANTHROPIC_API_KEY` comes from the host's secret store, never the repo.
- Login attempts are rate-limited — one shared password on the open internet is the whole
  perimeter.

### Hosting: NOT serverless, and this is a hard constraint

A committed run holds a **non-daemon worker thread for minutes** and writes to local disk
(`runs/`, `uploads/`, `sessions/`). Serverless functions time out and have no persistent disk,
so **Vercel is the wrong host for this app** despite being wired up in the environment. What is
needed is an always-on container with a persistent volume — Render, Railway, Fly.io, or a small
VPS. Decide the specific host at phase P6; nothing earlier depends on which one.

---

## 3. Route map

**BUILT in P3, 2026-08-03**, except the `/app/*` rows, which land with the shell design in P5.
`/` was the operator console; it is now the landing placeholder and the console is on
`/operator`.

| route | who | what |
|---|---|---|
| `/` | public | **the landing page** |
| `/login`, `/logout` | public | the demo login |
| `/app` | signed in | reads list for the account — the product home |
| `/app/new` | signed in | new read: upload + setup |
| `/app/prepare` (POST) | signed in | PAID ~$0.15 — the review-and-confirm screen |
| `/app/commit` (POST) | signed in | PAID ~$4 |
| `/app/status/{account}/{brand}/{run_id}` | signed in | processing |
| `/reads/{account}/{brand}/{run_id}` | signed in | **the dashboard**, unchanged |
| `/runs/...` | signed in | kept as an alias of `/reads/...` so existing links and tests hold |
| `/operator`, `/sessions/...` | signed in | the brand-manager session instrument, moved off `/` |
| `/static/...` | public | landing-page assets — the hero video, poster, images |

**The landing page needs static file serving, which the server does not have today.** Everything
it currently returns is a generated HTML string with the creative inlined as base64. A hero
video cannot be inlined (it would defeat the point of `+faststart` streaming), so P4 adds a
mounted static directory. It must be a real mount with correct `Content-Type` and range-request
support — Starlette's `StaticFiles` handles both; a hand-rolled file route does not, and video
scrubbing silently breaks without ranges.

### Which account does `/app` show?

`discover_runs` finds **two** accounts on disk: `demo` (36 reads across 5 brand profiles) and
`internal` (20 reads — smoke tests, `cmf_smoke`, `default`). Under a single shared login the app
must not simply show everything.

**Decision: `/app` is scoped to the `demo` account.** `internal/*` stays reachable through
`/operator` and by direct URL, but never appears in the product surface — it is our own test
exhaust and putting it in front of a brand manager makes the product look like a scratch pad.
The consequence for the design: **no account switcher, and no account column in the reads
list.** Brand profile is the only filing dimension the user sees.

### A naming collision to settle before any code is written

**`server/sessions.py` already means brand-manager session records.** A login session must not
borrow the word. Use **auth** throughout: `server/auth.py`, cookie `rocket_auth`, functions
`sign_in` / `require_signed_in`. "Session" stays reserved for the predict-then-reveal record.

### What P3 built, and the four decisions inside it

- **Default-deny, as a pure-ASGI middleware.** Everything is private unless it is in
  `auth.PUBLIC_EXACT` / `PUBLIC_PREFIXES`. The alternative — a dependency per route — is one
  forgotten decorator from a hole, and the forgotten one looks like every other route. **P5's
  `/app/*` routes are therefore protected the moment they exist.** Not `BaseHTTPMiddleware`: it
  re-wraps every response through a task group, and the response going through here is a
  whole dashboard with the creative inlined — 941KB on a real read.
- **JSON surfaces refuse in JSON.** `/sessions.json`, `/runs/status.json/...`,
  `/sessions/{id}/export` answer **401 JSON**; everything else 303s to `/login?next=…`. A caller
  parsing a login page where it expected a record reads it as "no data", not "not signed in".
- **No password set = closed, not open.** There is no `auth_disabled` flag and no test bypass —
  the offline suite POSTs the real password to the real `/login`. A disable switch is the kind
  of thing that gets set to rescue a bad first deploy and then stays set.
- **`/healthz` was leaking.** It returned `runs_root`, `sessions_root` and a count of finished
  runs — a convenience on localhost, absolute filesystem paths and a client count once `/` is
  public. Now `{"ok": true}`.

⚠ **Account scoping is FILING, not permission.** `discover_runs(account="demo")` keeps
`internal/*` smoke-test exhaust out of the product list; a signed-in browser that types
`/reads/internal/...` still gets the read, and `test_scoping_is_filing_and_not_a_permission`
pins that on purpose. One shared password is one trust level. If that must change, the answer is
real per-account accounts, not a filter on a list.

**Environment:** `ROCKET_APP_PASSWORD` (required to let anyone in), `ROCKET_AUTH_SECRET` (without
it, cookies are signed with a per-process random key and every restart signs everyone out),
`ROCKET_HTTPS=1` (adds `Secure` to the cookie — set it in P6, not before: a Secure cookie is
silently dropped over plain http, which looks exactly like a wrong password),
`ROCKET_CONTACT_EMAIL` (the landing `mailto:`; the link is omitted when unset). `serve.py` loads
`.env` before importing the app.

---

## 4. Stack: extend FastAPI, do not start a separate Next.js site

`docs/v3_report_redesign_brief.md` §6 recommends Next.js/Tailwind/shadcn. That advice was
written for the report, and the path actually taken — Claude Design → Python string HTML —
shipped. §6 is **not binding here.**

The constraint that decides it: **the read must stay a single self-contained, zero-JavaScript
file** (`test_page_is_self_contained`), because it is a deliverable that gets shared and
exported. On a Next.js front end the dashboard would either be reimplemented in React — two
renderers of the same numbers, which is precisely the drift trap in memory
`report_surface_fidelity` — or iframed as an opaque blob. Staying in FastAPI keeps one
renderer, and `dashboard_html.PAGE_CSS` already makes the console and the deliverable one
design system.

**Note on JavaScript:** the *report* is zero-JS and stays that way. The *server's own pages* are
not — `server/pages.py:139` already ships a small convenience script on the console. So the app
chrome may use small amounts of vanilla JS. No framework, no build step, no bundler.

---

## 5. The design system the new surfaces inherit

Both prompts must pin these, because "looks like one product" is the entire point of doing it
this way. Real values from `agent/dashboard_html.PAGE_CSS`:

```
--font-sans:"Instrument Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
--font-mono:ui-monospace, Menlo, "SF Mono", "Cascadia Code", Consolas, monospace;
--ground:#edebe6;  --surface:#fff;    --surface-2:#faf9f7;  --ink:#17181a;
--muted:#6b6f76;   --faint:#8a8d94;   --line:#e7e5e0;
--accent:#0f8a6d;  --accent-ink:#0b6b55;  --accent-tint:#e8f2ee;
--good:#0f8a6d;    --good-tint:#e8f2ee;   --leak:#b45309;   --leak-tint:#fdf6e9;
--on-accent:#fff;  --shadow:0 1px 3px rgba(0,0,0,.05);  --maxw:860px;
```

**Light only, for every reader, regardless of their OS setting** — the user's explicit call on
2026-08-02, pinned by `test_the_read_renders_light_for_everyone`. A dark palette exists but is
opt-in via `data-theme="dark"`, never automatic.

---

## 6. Progress reporting — an engine addition, and the reason for it

`run.json` is written exactly three times: `prepared`, `committed`, `complete`
(`run_service.py:472,492,496`). `panel_health` lands only at `complete`. **So today the engine
can report nothing at all between "started" and "done", across a wait of minutes.**

A fake progress bar is not an option. But the phases are cleanly bounded in `_commit_async` —
L1 fan-out → L2 per-segment → L3 population → L3.5 projection → L4 assess/prescribe — and
`_bounded()` wraps every single agent call, so a completion counter costs one increment.

**Decision: build real progress (phase P2).** Write a small `progress.json` beside `run.json` at
each phase boundary and on each agent completion. It is honest, it is contained, and a
multi-minute wait in front of a brand manager is exactly where the product either feels alive or
feels broken. The design prompts may therefore assume a true "N of 100 people have reacted"
counter and a real phase list.

**BUILT.** `agent/progress.py` writes `progress.json` beside `run.json`; the five phases are
`reactions → segments → population → diagnosis → prescription`, then `complete`. L1 and L2 carry
a real denominator; the last three do not and show none. `synthesize_report` gained an optional
`on_phase` hook — its two passes are separately reportable only from inside it, and together
they are the last minutes of a run.

⚠ **Two hazards, both built in rather than discovered later:**

1. **The write must be atomic.** The writer is the run's worker thread; the reader is a sync
   route in Starlette's threadpool. A plain overwrite lets a reader catch a half-written file —
   and `launcher.status` already swallows `json.JSONDecodeError` into `{}`, which would surface
   mid-run as status `unknown`. So: write to a temp file in the same directory and `os.replace`
   it, which is atomic on POSIX. The existing `json.JSONDecodeError` fallback stays as a belt.
2. **Throttle the writes.** ~100 agent completions against a page that reloads every 10 seconds
   does not need 100 writes. Update on each phase boundary, and within the L1 fan-out at most
   every ~2 seconds or every Nth agent. The counter increment itself needs a lock — `_bounded()`
   runs under an `asyncio.Semaphore` on one event loop, so an `asyncio.Lock` is sufficient and a
   thread lock is not required.

---

## 7. Phases

| | phase | depends on |
|---|---|---|
| **P0** | decisions + route map + naming — **this document** | — |
| **P1** | ✅ **DONE** — the app-shell prompt + the landing playbook | P0 |
| **P2** | ✅ **DONE** — engine progress reporting (`agent/progress.py`, wired through `run_service._commit_async` + `synthesize_report`, surfaced by `Launcher.status` and the status page). 26 tests, **12/12 mutations caught.** | — |
| **P3** | ✅ **DONE** — `server/auth.py` (HMAC-signed cookie + default-deny ASGI gate), the route map (`/` landing · `/operator` console · `/reads/...` with `/runs/...` kept as an alias), `/healthz` reduced to `{"ok": true}`, and `discover_runs(account=...)`. 24 tests. | P0 |
| **P4** | wire the user's landing design + mount `/static` + **produce the anonymised hero screenshot for them** (§5 of the playbook — our task, not theirs) | the user's design |
| **P5** | productionalize the app shell design | P1, P2, P3 |
| **P6** | hosting: pick the host, persistent volume, secrets, HTTPS, deploy | P3–P5 |

P1 and P2 are the two things that can start immediately, and they do not block each other.

---

## 8. Traps to carry into both prompts

- **The two-phase money gate must survive as two screens.** Any designer optimising flow will
  collapse prepare → commit into one button. The prompt states both screens with the real cost
  string and the real acknowledgement checkboxes, or we spend the wiring phase fighting the
  design.
- **Processing is minutes, not seconds.** Design for a real wait with named phases.
- **Every route is a plain `def`, never `async def`** (`server/app.py:1-10`). Auth middleware
  must respect it. Getting this wrong is a rewrite, not a patch.
- **Do not redesign or re-prompt the dashboard** (memory `report_redesign_is_users_job`). The new
  surfaces inherit its stylesheet; that inheritance is what makes them one product.
- **The landing page may not claim more than the engine has earned.** See the claim rules in
  `docs/v3_landing_page_playbook.md` §3 — no accuracy figures, no testimonials, no client logos,
  no performance prediction, no pricing. The instrument has never been checked against a human
  panel or an in-market backtest (memory `v3_one_month_plan`), and the landing page is exactly
  where that fact gets quietly forgotten.
