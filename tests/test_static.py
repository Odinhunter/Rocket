"""The landing page's own assets — `/static/`.

P4's landing design ships a hero video, and a video is the reason this is a
StaticFiles mount rather than a route that reads bytes off disk and returns
them. A plain route answers 200 to everything and ignores `Range:`, which does
not look like an error — it looks like a scrub bar that does nothing. That is
the property `test_the_hero_video_can_be_scrubbed` exists to hold.

The other half is that these assets are the ONE public thing served off disk.
`/static/` is the only entry in `auth.PUBLIC_PREFIXES`, so anything reachable
through this mount is reachable by anyone who finds the address — hence the
traversal test. Which paths are public is pinned in test_auth.py; what the
mount then *does* with them is pinned here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from tests.helpers_auth import demo_auth

# Every byte value, repeated — so a slice asserted below cannot accidentally
# equal a different slice, which is how an off-by-one range passes.
PAYLOAD = bytes(range(256)) * 40


@pytest.fixture
def anon(tmp_path: Path) -> TestClient:
    """A client that has NOT signed in, and a static dir with a fake video."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "hero.mp4").write_bytes(PAYLOAD)
    (tmp_path / "secret.txt").write_text("SECRET-NOT-FOR-THE-INTERNET")

    app = create_app(runs_root=tmp_path / "runs",
                     sessions_root=tmp_path / "sessions",
                     base_dir=tmp_path, static_dir=static_dir,
                     auth=demo_auth())
    client = TestClient(app)
    client.__dict__["tmp_path"] = tmp_path
    return client


def test_assets_are_served_without_signing_in(anon: TestClient) -> None:
    """The landing page is public, so its assets have to be too — a hero video
    behind the password would 303 to the sign-in page and render as nothing.

    The positive control is below: this same client is refused elsewhere, so a
    200 here is the allowlist working rather than the gate being off.
    """
    resp = anon.get("/static/hero.mp4")
    assert resp.status_code == 200, "the landing page cannot load its own video"
    assert resp.content == PAYLOAD
    assert resp.headers["content-type"] == "video/mp4"

    gated = anon.get("/operator", follow_redirects=False)
    assert gated.status_code == 303, (
        "positive control failed — this client is signed IN, so the 200 above "
        "proved nothing about the asset being public")
    print("  assets public, /operator still refused to the same client ✓")


def test_the_hero_video_can_be_scrubbed(anon: TestClient) -> None:
    """206 + Content-Range + the exact bytes asked for.

    This is the whole reason for StaticFiles. Swap the mount for a route that
    returns `FileResponse` bytes without range handling and every assertion
    here fails — while the page still *looks* fine, which is why it needs a
    test rather than a look.
    """
    resp = anon.get("/static/hero.mp4", headers={"Range": "bytes=1000-1009"})
    assert resp.status_code == 206, (
        "Range was ignored — the video will download whole and refuse to seek")
    assert resp.headers["content-range"] == f"bytes 1000-1009/{len(PAYLOAD)}"
    assert resp.content == PAYLOAD[1000:1010]
    assert len(resp.content) == 10

    # A second, different window: one hardcoded slice could match by accident,
    # two cannot, and this is where an off-by-one in the range maths shows up.
    tail = anon.get("/static/hero.mp4", headers={"Range": "bytes=10238-"})
    assert tail.status_code == 206
    assert tail.content == PAYLOAD[10238:]

    assert anon.get("/static/hero.mp4").headers["accept-ranges"] == "bytes"
    print("  206 on two windows, exact bytes, accept-ranges advertised ✓")


def test_a_missing_asset_is_a_404_and_not_a_crash(anon: TestClient) -> None:
    """The design must survive its video failing to load — the poster frame
    carries it. So a missing file is an ordinary 404, never a 500."""
    resp = anon.get("/static/no-such-file.mp4")
    assert resp.status_code == 404
    print("  a missing asset 404s ✓")


def test_the_mount_cannot_reach_outside_its_directory(anon: TestClient) -> None:
    """`/static/` is the only public prefix that serves files off disk, and
    the repo root above it holds `.env` and every client's runs.

    Encoded traversal is what a normalising HTTP client cannot flatten for
    you, so those are the forms worth asserting.
    """
    secret = (anon.__dict__["tmp_path"] / "secret.txt").read_text()
    for probe in ("/static/%2e%2e/secret.txt",
                  "/static/..%2fsecret.txt",
                  "/static/%2e%2e%2fsecret.txt",
                  "/static/....//secret.txt"):
        resp = anon.get(probe, follow_redirects=False)
        assert resp.status_code == 404, f"{probe} answered {resp.status_code}"
        assert secret not in resp.text, f"{probe} served a file above static/"
    print("  4 traversal forms refused ✓")


def test_the_default_static_directory_is_made_not_required() -> None:
    """A deployment that has never had a static/ directory must still boot.

    StaticFiles raises `RuntimeError` both at construction AND on its first
    request when the directory is absent, so `check_dir=False` would only move
    the failure to a 500 on an asset. create_app makes the directory instead.
    Delete the mkdir in server/app.py and this fails at create_app.
    """
    import tempfile

    root = Path(tempfile.mkdtemp()) / "never-existed"
    assert not root.exists()
    app = create_app(runs_root=root.parent / "runs",
                     sessions_root=root.parent / "sessions",
                     base_dir=root.parent, static_dir=root, auth=demo_auth())
    assert root.is_dir(), "create_app did not make the static directory"

    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/static/hero.mp4").status_code == 404, (
        "an empty static dir should 404, not 500")
    print("  a missing static/ is created, and the server serves ✓")
