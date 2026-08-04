"""The demo login — one shared password, a signed cookie, no user table.

This is deliberately the smallest thing that can stand in front of a public
address. There is no signup, no password reset, no per-user account: the
product is shown to brand managers by us, and the login exists so that a real
web address does not mean a public one.

Three properties are load-bearing.

**"auth", never "session".** `server/sessions.py` already means the
predict-then-reveal record for a brand-manager session — a piece of research
evidence with its own lifecycle. A signed-in browser borrowing that word would
make every future reader guess which one a variable holds.

**The cookie is stateless and signed, not a handle into a server-side set.** A
set in memory empties on every restart and does not survive a second worker
process; a signed cookie carries its own expiry and needs neither. The trade is
that a cookie cannot be revoked before it expires — with one shared password
that is not a distinction, because revoking anything means changing the
password anyway.

**There is no way to turn auth off.** No `auth_disabled` flag, no open default
when the password is unset: an unconfigured server refuses to issue a cookie
and therefore refuses every protected page. A disable switch is the kind of
thing that gets set in a deploy config to get past a bad first deploy and then
stays set, and the runs behind this login are a named third party's unreleased
creative and their real ad outcomes.
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from hashlib import sha256
from http.cookies import CookieError, SimpleCookie
from urllib.parse import quote

from starlette.responses import JSONResponse, RedirectResponse

log = logging.getLogger(__name__)

COOKIE_NAME = "rocket_auth"
# Long enough that a demo booked a fortnight out does not start with a login
# nobody remembers the password for.
DEFAULT_TTL_SECONDS = 14 * 24 * 60 * 60
# The single account the product surface shows. `internal/*` — our own smoke
# tests — is reachable only from /operator and by direct URL.
DEMO_ACCOUNT = "demo"

_SEP = "|"


def _random_secret() -> bytes:
    log.warning(
        "ROCKET_AUTH_SECRET is not set — signing cookies with a random "
        "per-process secret. Every restart signs everyone out. Set it in the "
        "environment before this server has users who mind."
    )
    return secrets.token_bytes(32)


@dataclass(frozen=True)
class Auth:
    """The password, the signing key, and the cookie's shape.

    Constructed in `create_app` and injected, mirroring how the run roots are:
    a test builds its own with a known password and signs in through the real
    `/login`, so the offline suite exercises the production path rather than a
    hole cut beside it.
    """

    password: str | None
    secret: bytes = field(default_factory=_random_secret, repr=False)
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    # Set once the server is behind HTTPS. Left off by default because a
    # Secure cookie is silently dropped over plain http, which on localhost
    # looks exactly like a wrong password.
    secure_cookie: bool = False
    # A flat delay on every failed attempt. Not a lockout: behind a hosting
    # proxy `request.client.host` is the proxy's address, so a per-IP lockout
    # locks out every visitor at once — a self-inflicted outage mid-demo.
    failed_delay_seconds: float = 1.0

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Auth":
        env = os.environ if env is None else env
        raw_secret = env.get("ROCKET_AUTH_SECRET", "").strip()
        password = env.get("ROCKET_APP_PASSWORD", "").strip() or None
        if password is None:
            log.warning(
                "ROCKET_APP_PASSWORD is not set — every signed-in page will "
                "refuse. Set it to open the server."
            )
        return cls(
            password=password,
            secret=raw_secret.encode() if raw_secret else _random_secret(),
            secure_cookie=env.get("ROCKET_HTTPS", "").strip().lower()
            in ("1", "true", "yes"),
        )

    # ---- password ----

    @property
    def configured(self) -> bool:
        return bool(self.password)

    def check_password(self, supplied: str) -> bool:
        """Constant-time, and False when nothing is configured.

        `compare_digest` rather than `==` so the comparison does not leak the
        length of the matching prefix through its own duration.
        """
        if not self.password:
            return False
        return hmac.compare_digest(supplied.encode(), self.password.encode())

    # ---- cookie ----

    def _sign(self, payload: str) -> str:
        return hmac.new(self.secret, payload.encode(), sha256).hexdigest()

    def issue(self, account: str = DEMO_ACCOUNT, *, now: float | None = None) -> str:
        """`account|expiry|signature`, signed over the first two fields.

        The expiry is inside the signed payload, not beside it: a cookie whose
        lifetime the holder can edit has no lifetime.
        """
        if _SEP in account:
            raise ValueError(f"account may not contain {_SEP!r}: {account!r}")
        expires_at = int(now if now is not None else time.time()) + self.ttl_seconds
        payload = f"{account}{_SEP}{expires_at}"
        return f"{payload}{_SEP}{self._sign(payload)}"

    def verify(self, value: str | None, *, now: float | None = None) -> str | None:
        """The account the cookie proves, or None. Never raises.

        Every rejection is silent and identical. This runs on every request
        against an attacker-supplied string, so it is written to have no
        interesting failure modes rather than to explain itself.
        """
        if not value:
            return None
        parts = value.split(_SEP)
        if len(parts) != 3:
            return None
        account, raw_expiry, signature = parts
        if not account:
            return None
        payload = f"{account}{_SEP}{raw_expiry}"
        if not hmac.compare_digest(signature, self._sign(payload)):
            return None
        # Only after the signature holds — an unsigned integer parse on
        # attacker input decides nothing, but doing it first invites someone to
        # move a check above the signature later.
        try:
            expires_at = int(raw_expiry)
        except ValueError:
            return None
        if (now if now is not None else time.time()) >= expires_at:
            return None
        return account

    def cookie_kwargs(self) -> dict:
        """The flags, in one place so /login and /logout cannot disagree."""
        return {
            "httponly": True,      # a stolen XSS payload cannot read it
            "samesite": "lax",     # a cross-site POST cannot ride it
            "secure": self.secure_cookie,
            "path": "/",
            "max_age": self.ttl_seconds,
        }


def safe_next(target: str | None, fallback: str = "/reads") -> str:
    r"""Where to land after signing in — same-site only.

    `?next=` is attacker-suppliable, so a login page that honours it becomes an
    open redirect: a link to *our* domain that lands on theirs, with our login
    as the thing that looked trustworthy.

    Exactly one shape is allowed — a path beginning with a single `/`.
    `//evil.example` is protocol-relative and leaves the site; `/\evil.example`
    is treated as protocol-relative by browsers even though it does not look
    like it; a newline can inject a second header.
    """
    if not target or not target.startswith("/"):
        return fallback
    if target.startswith("//"):
        return fallback
    if "\\" in target or "\n" in target or "\r" in target:
        return fallback
    return target


# ---- enforcement ------------------------------------------------------
#
# The gate is default-deny: everything is protected unless it is named here.
# The alternative — a dependency added to each route — is one forgotten
# decorator away from a hole, and the forgotten one is invisible. Here a new
# route is private the moment it exists, and making something public is a
# deliberate edit to a list of five strings.

# Exact matches only. `/login` and `/logout` are the pre-2026-08-03 names,
# kept as redirects because they are in browser histories and in things we
# already told people — a dead URL that someone typed from memory looks like a
# broken server, not a renamed route. They carry no data and set no cookie.
# `/methodology` is public by deliberate decision (2026-08-04): it states what
# the instrument can and cannot do, and it exists so the read itself does not
# have to carry that inline. A prospect reading it before they have an account
# is the point. It renders from constants — no disk, no client name.
PUBLIC_EXACT = frozenset({"/", "/signin", "/healthz", "/login", "/logout",
                          "/methodology"})
# Prefixes. The trailing slash is not cosmetic: on "/static" a path like
# "/static-secret" would also match.
PUBLIC_PREFIXES = ("/static/",)


def is_public(path: str) -> bool:
    return path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIXES)


def wants_json(path: str) -> bool:
    """Whether a refusal on this path should be JSON rather than a redirect.

    A 303 to the login page is the right answer for a browser and the wrong
    one for `/sessions.json` — a caller parsing the response gets a login page
    where it expected a record, and reads that as "no data" rather than "not
    signed in". `.json/` catches `/runs/status.json/{account}/...`, where the
    marker is in the middle of the path rather than at the end.
    """
    return path.endswith(".json") or ".json/" in path or path.endswith("/export")


def cookie_value(scope: dict, name: str = COOKIE_NAME) -> str | None:
    """Read one cookie straight off the ASGI scope.

    HTTP/2 may split cookies across several headers, so every one is merged
    rather than only the first being read.
    """
    jar = SimpleCookie()
    for key, value in scope.get("headers", []):
        if key == b"cookie":
            try:
                jar.load(value.decode("latin-1"))
            except CookieError:
                continue
    morsel = jar.get(name)
    return morsel.value if morsel else None


class RequireSignIn:
    """Pure-ASGI default-deny gate.

    Deliberately NOT `BaseHTTPMiddleware`: that wraps every response in a task
    group and streams it back through an anyio memory stream, and the response
    passing through here is a whole dashboard with the creative inlined as
    base64 — megabytes, on every read. This does the one thing needed, which is
    to look at the path and either call through or answer.

    It also does not force the routes async. Middleware sits at the ASGI layer,
    above routing; FastAPI still dispatches a plain `def` handler to the
    threadpool, which is what `server/app.py`'s docstring depends on.
    """

    def __init__(self, app, auth: Auth):
        self.app = app
        self.auth = auth

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if not is_public(path):
            account = self.auth.verify(cookie_value(scope))
            if account is None:
                await self._refuse(scope, receive, send, path)
                return
            # Left for the product surface to read: P5's /app lists one
            # account's reads, and this is where it learns which.
            scope.setdefault("state", {})["auth_account"] = account
        await self.app(scope, receive, send)

    async def _refuse(self, scope, receive, send, path: str) -> None:
        if wants_json(path):
            response = JSONResponse({"detail": "Not signed in."}, status_code=401)
        else:
            target = "/signin"
            # Only a GET is worth returning to. Replaying a POST after login
            # would mean re-submitting a form the browser no longer holds —
            # and on /runs/commit that POST spends ~$4.
            if scope.get("method", "GET") in ("GET", "HEAD"):
                query = scope.get("query_string", b"").decode("latin-1")
                back = path + (f"?{query}" if query else "")
                target = f"/signin?next={quote(back, safe='')}"
            response = RedirectResponse(target, status_code=303)
        await response(scope, receive, send)
