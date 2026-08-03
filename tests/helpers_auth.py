"""Signing a test client in — through the real login, never around it.

There is no test-only bypass in `create_app`, deliberately: a flag that opens
the server is a flag someone can set in a deploy config to get past a bad
first deploy, and then it stays set. So the offline suite does what a browser
does — POSTs the password to `/signin` and keeps the cookie.

The cost is one line per fixture. The benefit is that every server test also
exercises the gate, so a change that breaks sign-in cannot pass by being
invisible to the tests that do not think they are about auth.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.auth import Auth

PASSWORD = "test-password-not-a-real-one"


def demo_auth() -> Auth:
    """The Auth every server test injects.

    NOT named `test_auth`: imported into a test module, pytest would collect
    the name as a test case and report a vacuous pass.

    A fixed secret so a signed cookie is reproducible across a test's asserts,
    and no failure delay — the production 1s pause would otherwise be paid on
    every wrong-password test in the suite.
    """
    return Auth(password=PASSWORD, secret=b"test-secret-32-bytes-of-nonsense",
                failed_delay_seconds=0.0)


def sign_in(client: TestClient) -> TestClient:
    """POST the real form and keep the cookie on the client's jar."""
    resp = client.post("/signin", data={"password": PASSWORD},
                       follow_redirects=False)
    assert resp.status_code == 303, resp.text
    assert client.cookies.get("rocket_auth"), "sign-in issued no cookie"
    return client
