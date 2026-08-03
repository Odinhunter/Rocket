"""The login — the gate, not the form.

The server is about to have a public address, and behind it sit a named third
party's unreleased creative and their real ad outcomes. So these tests are
written against the two ways a gate actually fails:

  1. **A route nobody protected.** A per-route check is one forgotten decorator
     from a hole, and the forgotten one looks like every other route. The gate
     here is default-deny, and `test_every_route_outside_the_allowlist_refuses`
     walks the app's own routing table rather than a list someone maintains —
     a route added in P5 is covered by a test written in P3.
  2. **An allowlist that quietly grows.** Enumerating routes is only half of
     it: derive the expectation from the same constant the middleware reads and
     adding a path to that constant stays green while making a page public.
     So the allowlist is ALSO asserted against a hardcoded literal here. Both
     directions, or the pair proves nothing.

Everything offline; no run directories, no engine, no network.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.auth import (
    COOKIE_NAME, PUBLIC_EXACT, PUBLIC_PREFIXES, Auth, is_public, safe_next,
    wants_json,
)
from tests.helpers_auth import PASSWORD, demo_auth, sign_in

# The JSON surfaces, written out rather than derived. A caller parsing these
# must get a 401 it can recognise, not a login page it reads as "no data".
JSON_ROUTES = (
    "/sessions.json",
    "/runs/status.json/demo/hw/r1",
    "/sessions/abc/export",
)


def _app(tmp_path: Path, auth: Auth | None = None):
    return create_app(
        runs_root=tmp_path / "runs", sessions_root=tmp_path / "sessions",
        base_dir=tmp_path, specs_dir=tmp_path / "specs",
        uploads_dir=tmp_path / "uploads", auth=auth or demo_auth(),
    )


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Signed OUT. Signing in is the thing under test here."""
    return TestClient(_app(tmp_path))


# ---- the cookie -------------------------------------------------------


def test_a_signed_cookie_roundtrips_and_names_its_account() -> None:
    auth = demo_auth()
    assert auth.verify(auth.issue("demo")) == "demo"
    print("  issue -> verify returns the account ✓")


def test_every_tampering_is_rejected() -> None:
    """The cookie is the whole credential, so each field is checked."""
    auth = demo_auth()
    account, expiry, signature = auth.issue("demo").split("|")

    cases = {
        "account swapped": f"internal|{expiry}|{signature}",
        "expiry extended": f"{account}|{int(expiry) + 99999}|{signature}",
        "signature flipped": f"{account}|{expiry}|{'0' * len(signature)}",
        "signature truncated": f"{account}|{expiry}|{signature[:-1]}",
        "field dropped": f"{account}|{signature}",
        "field added": f"{account}|{expiry}|{signature}|extra",
        "empty account": f"|{expiry}|{signature}",
        "not a cookie at all": "garbage",
        "empty": "",
    }
    for name, forged in cases.items():
        assert auth.verify(forged) is None, f"accepted a cookie with {name}"
    assert auth.verify(None) is None
    print(f"  {len(cases) + 1} malformed or forged cookies rejected ✓")


def test_a_cookie_from_another_secret_is_worthless() -> None:
    """Two deployments do not share sign-ins, and a leaked cookie from one is
    not a key to the other."""
    theirs = Auth(password=PASSWORD, secret=b"a-different-secret-entirely")
    assert demo_auth().verify(theirs.issue("demo")) is None
    print("  cross-secret forgery rejected ✓")


def test_expiry_is_inside_the_signature() -> None:
    auth = Auth(password=PASSWORD, secret=b"s", ttl_seconds=100)
    cookie = auth.issue("demo", now=1_000)
    assert auth.verify(cookie, now=1_099) == "demo"
    assert auth.verify(cookie, now=1_100) is None, "expired cookie accepted"
    assert auth.verify(cookie, now=9_999) is None
    print("  cookie expires, and the expiry cannot be edited ✓")


def test_a_separator_in_the_account_is_refused_at_issue() -> None:
    """`a|b|<sig>` and an account literally called `a|b` would parse the same.
    Refused where it is created, so the ambiguity cannot exist on the wire."""
    with pytest.raises(ValueError):
        demo_auth().issue("demo|internal")
    print("  ambiguous account refused ✓")


def test_an_unconfigured_server_accepts_nothing() -> None:
    """No password set is not 'open' — it is closed."""
    auth = Auth(password=None, secret=b"s")
    assert not auth.configured
    for attempt in ("", "None", "password", PASSWORD):
        assert auth.check_password(attempt) is False, f"{attempt!r} let in"
    print("  unset password lets nobody in, including the empty string ✓")


def test_the_cookie_carries_its_flags() -> None:
    flags = demo_auth().cookie_kwargs()
    assert flags["httponly"] is True      # XSS cannot read it
    assert flags["samesite"] == "lax"     # a cross-site POST cannot ride it
    assert flags["secure"] is False       # off by default: dropped over http
    assert Auth(password="p", secret=b"s", secure_cookie=True).cookie_kwargs()[
        "secure"] is True
    print("  HttpOnly + SameSite=Lax always, Secure when configured ✓")


# ---- where signing in lands you ---------------------------------------


def test_next_only_accepts_a_local_path() -> None:
    """An honoured `?next=` is an open redirect: our domain, our login, their
    landing page."""
    assert safe_next("/operator/x?y=1") == "/operator/x?y=1"
    for hostile in ("//evil.example", "https://evil.example", "\\\\evil.example",
                    "/\\evil.example", "/ok\nSet-Cookie: x=1", "", None,
                    "javascript:alert(1)", "evil.example"):
        assert safe_next(hostile) == "/operator", f"followed {hostile!r}"
    print("  9 hostile next targets fall back to /operator ✓")


def test_signing_in_returns_you_to_where_you_were_stopped(client) -> None:
    stopped = client.get("/operator", follow_redirects=False)
    assert stopped.status_code == 303
    assert stopped.headers["location"] == "/login?next=%2Foperator"

    landed = client.post("/login", data={"password": PASSWORD, "next": "/operator"},
                         follow_redirects=False)
    assert landed.headers["location"] == "/operator"
    assert client.get("/operator").status_code == 200
    print("  stopped at /operator -> login -> back to /operator ✓")


def test_the_query_string_survives_the_round_trip(client) -> None:
    """A read URL carries no query today, but a filtered /app list in P5 will
    — and losing it silently drops the filter the user asked for."""
    stopped = client.get("/operator?brand=hw&sort=new", follow_redirects=False)
    assert stopped.headers["location"] == (
        "/login?next=%2Foperator%3Fbrand%3Dhw%26sort%3Dnew")
    print("  query string preserved through the login ✓")


def test_a_blocked_post_does_not_come_back_as_a_replay(client) -> None:
    """/runs/commit spends ~$4. A `next` that replays a POST after signing in
    is a way to spend it by accident."""
    stopped = client.post("/runs/commit", data={"run_id": "x"},
                          follow_redirects=False)
    assert stopped.status_code == 303
    assert stopped.headers["location"] == "/login", "a POST was queued for replay"
    print("  a blocked POST is never replayed after login ✓")


# ---- the gate ---------------------------------------------------------


def test_the_public_allowlist_is_exactly_this(tmp_path: Path) -> None:
    """Asserted against a literal, not against the constant the middleware
    reads. Deriving both sides from one constant means adding a path to it
    silently stays green — which is the entire failure mode."""
    assert PUBLIC_EXACT == frozenset({"/", "/login", "/logout", "/healthz"})
    assert PUBLIC_PREFIXES == ("/static/",)
    # The trailing slash is load-bearing: on "/static" this would be public.
    assert not is_public("/static-secret")
    assert not is_public("/operator")
    assert is_public("/static/hero.mp4")
    print("  4 public paths, 1 public prefix, and /static-secret is not one ✓")


def test_every_route_outside_the_allowlist_refuses(tmp_path: Path) -> None:
    """Walks the app's own routing table, so a route added later is covered by
    this test without anyone editing it."""
    app = _app(tmp_path)
    client = TestClient(app)
    checked = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path is None or path in PUBLIC_EXACT:
            continue
        method = "GET" if "GET" in methods else sorted(methods)[0]
        # Concrete values for the path params; the middleware answers before
        # routing, so nothing here needs to resolve to a real run.
        url = path.replace("{", "").replace("}", "")
        resp = client.request(method, url, follow_redirects=False)
        assert resp.status_code in (303, 401), (
            f"{method} {path} answered {resp.status_code} while signed out")
        if resp.status_code == 303:
            assert resp.headers["location"].startswith("/login")
        checked.append(f"{method} {path}")
    assert len(checked) >= 15, f"only {len(checked)} routes walked — did the app build?"
    print(f"  {len(checked)} routes refuse while signed out ✓")


def test_the_json_surfaces_refuse_in_json(client) -> None:
    """A 303 to an HTML login page, parsed by a caller expecting a record,
    reads as 'no data' rather than 'not signed in'."""
    for path in JSON_ROUTES:
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 401, f"{path} redirected instead of 401"
        assert json.loads(resp.text)["detail"] == "Not signed in."
        assert wants_json(path)
    print(f"  {len(JSON_ROUTES)} JSON routes answer 401 JSON, not a redirect ✓")


def test_the_landing_page_and_healthz_are_public_and_say_nothing(client) -> None:
    landing = client.get("/")
    assert landing.status_code == 200
    assert "Sign in" in landing.text

    health = client.get("/healthz")
    assert health.status_code == 200
    # Not a subset check: the point is that nothing ELSE is in the body. It
    # used to return absolute filesystem paths and a count of client runs.
    assert health.json() == {"ok": True}
    print("  / and /healthz are public and disclose nothing ✓")


def test_a_wrong_password_issues_no_cookie_and_says_nothing(client) -> None:
    resp = client.post("/login", data={"password": "wrong"},
                       follow_redirects=False)
    assert resp.status_code == 401
    assert COOKIE_NAME not in resp.cookies
    assert not client.cookies.get(COOKIE_NAME)
    # The failure must not reveal whether a password is even set.
    assert PASSWORD not in resp.text
    assert client.get("/operator", follow_redirects=False).status_code == 303
    print("  wrong password: no cookie, no hint, still locked ✓")


def test_a_failed_attempt_actually_costs_a_delay(tmp_path: Path) -> None:
    """The only defence against guessing one shared password.

    Deliberately not a lockout: behind a hosting proxy `request.client.host` is
    the proxy's address, so N failures would lock out every visitor at once —
    an outage anyone on the internet could trigger, mid-demo.
    """
    auth = Auth(password=PASSWORD, secret=b"s", failed_delay_seconds=0.25)
    client = TestClient(_app(tmp_path, auth=auth))

    started = time.monotonic()
    assert client.post("/login", data={"password": "no"}).status_code == 401
    assert time.monotonic() - started >= 0.25, "a wrong password cost nothing"

    started = time.monotonic()
    assert client.post("/login", data={"password": PASSWORD},
                       follow_redirects=False).status_code == 303
    assert time.monotonic() - started < 0.25, "the delay is charged on success too"
    print("  a wrong password costs the delay; the right one does not ✓")


def test_signing_out_closes_the_door_behind_you(tmp_path: Path) -> None:
    client = sign_in(TestClient(_app(tmp_path)))
    assert client.get("/operator").status_code == 200

    client.get("/logout", follow_redirects=False)
    assert not client.cookies.get(COOKIE_NAME), "cookie survived /logout"
    assert client.get("/operator", follow_redirects=False).status_code == 303
    print("  /logout clears the cookie and the console closes ✓")


def test_an_unconfigured_server_refuses_to_open(tmp_path: Path) -> None:
    """The deploy where ROCKET_APP_PASSWORD was forgotten. It must fail shut,
    and the login page must say why rather than looking broken."""
    client = TestClient(_app(tmp_path, auth=Auth(
        password=None, secret=b"s", failed_delay_seconds=0.0)))
    page = client.get("/login")
    assert page.status_code == 200
    assert "not configured" in page.text.lower()

    for attempt in ("", "password", PASSWORD):
        resp = client.post("/login", data={"password": attempt},
                           follow_redirects=False)
        assert resp.status_code == 401
        assert not client.cookies.get(COOKIE_NAME)
    assert client.get("/operator", follow_redirects=False).status_code == 303
    print("  no password configured: nothing opens, and the page says so ✓")


def test_an_expired_cookie_stops_working_mid_visit(tmp_path: Path) -> None:
    """Not the same as never having one — this is the fortnight-later demo.

    The cookie is minted by the real `issue()` with a past clock, rather than
    by logging into a zero-TTL server: `max_age=0` makes the client drop the
    cookie on receipt, so that version of the test would pass on an empty jar
    and prove nothing about expiry.
    """
    auth = Auth(password=PASSWORD, secret=b"s", failed_delay_seconds=0.0)
    client = TestClient(_app(tmp_path, auth=auth))
    client.cookies.set(COOKIE_NAME, auth.issue("demo", now=time.time()
                                               - auth.ttl_seconds - 1))
    assert auth.verify(client.cookies.get(COOKIE_NAME)) is None

    assert client.get("/operator", follow_redirects=False).status_code == 303
    # ...and the same cookie, minted now, does work — otherwise this test
    # would pass on any broken cookie at all.
    client.cookies.set(COOKIE_NAME, auth.issue("demo"))
    assert client.get("/operator").status_code == 200
    print("  a correctly signed but expired cookie is refused ✓")


def test_the_gate_does_not_make_the_routes_async(tmp_path: Path) -> None:
    """server/app.py's docstring: every route is a plain `def`, because
    RunService.commit calls asyncio.run() and report rendering blocks. ASGI
    middleware sits above routing and does not change that — pinned here
    because the cost of finding out otherwise is a rewrite."""
    import inspect

    app = _app(tmp_path)
    for route in app.routes:
        fn = getattr(route, "endpoint", None)
        if fn is None or not getattr(route, "path", "").startswith(
                ("/runs", "/sessions", "/reads", "/operator", "/login")):
            continue
        assert not inspect.iscoroutinefunction(fn), (
            f"{route.path} became async — see server/app.py's docstring")
    print("  every app route is still a plain def ✓")
