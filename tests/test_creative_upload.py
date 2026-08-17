"""The creative field: what it offers, what it refuses, and what it keeps.

Three things are pinned here, and each one was a defect on 2026-08-05.

⚠ **The picker and the engine must agree about file types.** The upload guard
carried its own list that also allowed `.gif`, which `AssetSpec.validate()`
refuses. A `.gif` therefore passed the door, was written into `uploads/`, and
died *inside* prepare on the generic "could not prepare" page with the whole
form lost — a failure landing after the operator had done the work, which is
what `#29` exists to forbid. The list is now the engine's own, imported.

⚠ **A rejection must not clear what was typed.** Design state 4C says so in as
many words ("Kept as typed — the form does not clear"), and every field obeyed
it except the label, whose markup rendered no `value`.

⚠ **State 4B is drawn by script, so the testable surface is the boundary.**
Asserting on a card that JavaScript builds would be asserting on nothing from
here. What IS assertable, and what actually protects it, is that the constants
reaching the script are the same ones the POST handler enforces, and that the
no-script path still submits. The card's own behaviour is driven in a DOM
harness (jsdom), mutation-proved separately.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.config import SUPPORTED_IMAGE_SUFFIXES, AssetSpec
from server import app_html
from server.app import create_app
from server.launcher import Launcher
from tests.helpers_auth import demo_auth, sign_in
from tests.helpers_brand import ANSWERS, build_brand

# A real one-pixel GIF. The bytes matter: the guard reads the extension, but a
# test that shipped a fake blob would not prove the file was ever plausible.
GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
       b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
       b"\x00\x02\x02D\x01\x00;")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class _NoSpendLauncher(Launcher):
    """Records what prepare was handed and never reaches the API.

    ⚠ Not merely a speed-up. If this test regresses — someone re-adds `.gif` to
    the guard — the real `prepare_async` would spawn the paid classifier on a
    worker thread. A test that costs money when it fails is a trap, so the
    money is removed rather than relied upon not to happen.
    """

    def __init__(self) -> None:
        super().__init__()
        self.reached: list = []

    def prepare_async(self, config) -> str:
        self.reached.append(config)
        return "stub-token"


@pytest.fixture
def world(tmp_path: Path):
    build_brand(tmp_path / "runs")
    launcher = _NoSpendLauncher()
    client = sign_in(TestClient(create_app(
        runs_root=tmp_path / "runs", sessions_root=tmp_path / "s",
        base_dir=tmp_path, uploads_dir=tmp_path / "uploads",
        launcher=launcher, auth=demo_auth())))
    return client, launcher, tmp_path


def _post(client, filename: str, blob: bytes, *, label: str = "Winter whey v2"):
    return client.post(
        "/reads/new", files={"asset": (filename, blob, "application/octet-stream")},
        data={**ANSWERS, "asset_label": label, "purpose": "direct_sell"},
        follow_redirects=False)


# ---- the picker offers what the engine reads ---------------------------


def test_the_picker_offers_exactly_what_the_engine_can_read() -> None:
    """Two-sided. The names a person reads collapse `.jpeg` into `.jpg` — one
    format under two spellings — so the copy is pinned through the alias map
    rather than to a literal list, and adding a format to the engine while
    forgetting the picker fails here instead of shipping."""
    normalised = {app_html.CREATIVE_ALIASES.get(s, s)
                  for s in SUPPORTED_IMAGE_SUFFIXES}
    assert set(app_html.CREATIVE_SHOWN) == normalised, (
        "what the page offers and what the engine reads have drifted: "
        f"shown {sorted(app_html.CREATIVE_SHOWN)}, engine {sorted(normalised)}")
    # The accept attribute carries every real suffix, aliases included — it
    # filters a file dialog, so it must not hide `.jpeg` from someone who has
    # one on disk.
    assert set(app_html.CREATIVE_ACCEPT.split(",")) == set(SUPPORTED_IMAGE_SUFFIXES)
    for shown in app_html.CREATIVE_SHOWN:
        assert shown in app_html.CREATIVE_REJECTED, \
            f"{shown} is offered but the rejection sentence never names it"
    print(f"  picker offers {app_html.CREATIVE_SHOWN}, engine reads "
          f"{sorted(SUPPORTED_IMAGE_SUFFIXES)} ✓")


def test_the_script_checks_the_same_list_the_server_enforces(world) -> None:
    """The 4B card is drawn client-side, so a second, drifting copy of the
    accept list would let it draw a card for a file the server then refuses —
    `#29` reintroduced on the other side of the wire. Both constants are
    injected into the page, so they are assertable from here."""
    client, _, _ = world
    page = client.get("/reads/new").text
    assert f"var OK = {json.dumps(sorted(SUPPORTED_IMAGE_SUFFIXES))};" in page, \
        "the script's accept list is not the engine's"
    assert f"var REJECTED = {json.dumps(app_html.CREATIVE_REJECTED)};" in page, \
        "the script says something the server does not"
    print("  the script and the POST handler share both constants ✓")


def test_the_creative_field_survives_with_no_javascript(world) -> None:
    """The card is an enhancement. With scripting blocked the plain, visible,
    required input is the whole control — and it must not start life inside the
    hidden card, which would make choosing a file impossible."""
    client, _, _ = world
    page = client.get("/reads/new").text
    field_at = page.index('name="asset"')
    card_at = page.index('id="creative-card"')
    assert field_at < card_at, \
        "the file input is rendered inside the hidden 4B card"
    assert 'required' in page[field_at:field_at + 120]
    assert '<div class="upl" id="creative-card" hidden>' in page, \
        "the card must start hidden — with no script it never opens"
    print("  no-JS: a visible required input, card hidden and empty ✓")


def test_the_hidden_card_is_actually_hidden(world) -> None:
    """⚠ The `hidden` attribute alone does NOT hide `.upl`.

    `hidden` is honoured by a rule in the User-Agent stylesheet, and any author
    rule that sets `display` on the same element overrides it — `.upl` sets
    `display:flex`. Without the override the empty card renders above the form
    on a first visit, broken thumbnail and all, for every visitor with CSS.

    Asserted on the stylesheet because there is no browser here to ask. A DOM
    harness answers this question wrongly: jsdom reports `display:none` for the
    attribute alone, which is exactly the reassurance that would let the bug
    ship.
    """
    client, _, _ = world
    page = client.get("/reads/new").text
    assert ".upl[hidden]{display:none}" in page.replace(" ", "").replace("\n", ""), \
        "nothing re-hides the card against .upl's own display:flex"
    print("  the hidden card is hidden against its own display rule ✓")


# ---- what gets refused, and where -------------------------------------


def test_a_file_the_engine_refuses_is_refused_at_the_door(world) -> None:
    """⚠ THE `.gif` REGRESSION. The point is not that `.gif` specifically is
    banned — it is that the door and the engine agree, so the test derives its
    own subject from the engine rather than naming one.

    A file refused *inside* prepare costs the operator the upload and the whole
    form and lands on a dead-end error page. Refused at the door it costs a
    sentence.
    """
    client, launcher, tmp = world
    # Something the engine will not read, chosen BY the engine's own set so
    # this cannot rot into testing a hardcoded extension.
    assert ".gif" not in SUPPORTED_IMAGE_SUFFIXES, \
        "pick another refused suffix — .gif is now supported"
    probe = tmp / "probe.gif"
    probe.write_bytes(GIF)
    with pytest.raises(ValueError):
        AssetSpec(image_path=str(probe), label="x").validate()

    resp = _post(client, "ad.gif", GIF)

    assert resp.status_code == 400, \
        f"the door let through a file the engine refuses (HTTP {resp.status_code})"
    assert not launcher.reached, \
        "it reached prepare — the refusal lands after the operator has paid attention"
    assert "REJECTED" in resp.text and app_html.CREATIVE_REJECTED in resp.text
    assert "ad.gif" in resp.text, "the rejection does not say which file"
    written = list((tmp / "uploads").glob("*"))
    assert not written, f"a refused creative was still written to disk: {written}"
    print("  a file the engine cannot read is stopped at the door, unwritten ✓")


def test_a_file_the_engine_reads_gets_through(world) -> None:
    """The positive control. Without it, a guard that refused EVERYTHING would
    pass every assertion above."""
    client, launcher, tmp = world
    resp = _post(client, "ad.png", PNG)
    assert resp.status_code == 303, resp.status_code
    assert launcher.reached, "a valid creative never reached prepare"
    assert list((tmp / "uploads").glob("*.png")), "the creative was not stored"
    print("  a readable creative still gets through to prepare ✓")


def test_the_form_does_not_clear_what_was_typed(world) -> None:
    """Design state 4C, verbatim: "Kept as typed — the form does not clear."

    Every select re-rendered its choice; the label alone was dropped, because
    its markup carried no `value`. On a rejection that is the one field the
    operator has to type again from memory.
    """
    client, _, _ = world
    typed = "MuscleBlaze Biozyme — winter carousel v2"
    resp = _post(client, "brief_final_v3.pdf", b"%PDF-1.4", label=typed)
    assert resp.status_code == 400
    body = resp.text
    assert f'value="{typed}"' in body.replace("&#x27;", "'").replace("&amp;", "&"), \
        "the typed label was cleared by the rejection"
    assert f'value="{ANSWERS["brand"]}" selected' in body, \
        "the chosen brand was cleared by the rejection"
    # ⚠ Age is a NUMBER INPUT since 2026-08-16, not a <select>, so there is no
    # `selected` to look for — the value rides on the input itself. The
    # behaviour under test is unchanged: a rejection must not clear it.
    for field, expected in (("age_from", ANSWERS["age_from"]),
                            ("age_to", ANSWERS["age_to"])):
        match = re.search(rf'<input[^>]*name="{field}"[^>]*>', body)
        assert match, f"the {field} control vanished from the form"
        assert f'value="{expected}"' in match.group(0), \
            f"the age range was cleared by the rejection ({match.group(0)})"
    print("  a rejection keeps the label, the brand and the audience ✓")


def test_the_typed_label_cannot_smuggle_markup_back_into_the_form(world) -> None:
    """It is echoed into an attribute on the way back, so the quoting matters
    more here than anywhere else on the page."""
    client, _, _ = world
    resp = _post(client, "brief.pdf", b"%PDF-1.4",
                 label='" autofocus onfocus="alert(1)')
    assert resp.status_code == 400
    assert 'onfocus="alert(1)"' not in resp.text, "the label broke out of its attribute"
    assert "&quot;" in resp.text or "&#34;" in resp.text
    print("  a label full of quotes comes back as text, not as markup ✓")
