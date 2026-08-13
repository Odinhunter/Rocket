"""The brand manager describes the ad and tells us what they know — and the
two land in different places on purpose.

WHAT THE FORM GAINED (2026-08-14): the ad's own words (headline / caption /
offer) and a free-text box of the marketer's own context. The engine plumbing
for the first three already existed and was reachable only from the CLI; the
fourth is new.

⚠ THE SPLIT THIS FILE DEFENDS. Ad copy is printed on the creative, so the
persona reads it. Notes are the marketer talking to US, so they reach the
target classifier and nothing else. The prompt-level seam is pinned by
`tests/test_marketer_notes_never_reach_the_agent.py`; THIS file pins that the
web form actually delivers each one to the right field, because a seam guarding
a value the form never sends guards nothing.

⚠ There is still no free-text "describe your audience" box and there must not
be one. That field is what let a competitor build 105 personas out of a
sentence describing the ad. Structured demographic controls are the audience;
prose is context.

Offline. `_NoSpendLauncher` intercepts prepare, so this never reaches the paid
classifier.

Run: .venv/bin/python -m pytest tests/test_ad_copy_and_notes_form.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.app import create_app
from server.launcher import Launcher
from tests.helpers_auth import demo_auth, sign_in
from tests.helpers_brand import ANSWERS, build_brand

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

HEADLINE = "India's first protein wafer"
CAPTION = "20g protein, made with atta and jowar, no palm oil."
OFFER = "₹625 for a pack of 5"
NOTES = "They are not supplement buyers — they would grab a chocolate bar at 4pm."


class _NoSpendLauncher(Launcher):
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
    return client, launcher


def _post(client, **extra):
    data = {**ANSWERS, "asset_label": "Winter whey v2", "purpose": "direct_sell"}
    data.update(extra)
    return client.post(
        "/reads/new",
        files={"asset": ("ad.png", PNG, "application/octet-stream")},
        data=data, follow_redirects=False)


def test_the_fields_are_on_the_form(world) -> None:
    client, _ = world
    body = client.get("/reads/new").text
    for name in ("headline", "primary_text", "offer", "marketer_notes"):
        assert f'name="{name}"' in body, f"the form is missing {name}"
    print("  all four new fields render on /reads/new ✓")


def test_ad_copy_lands_on_creative_inputs_and_notes_do_not(world) -> None:
    """The whole point, in one assertion set."""
    client, launcher = world
    resp = _post(client, headline=HEADLINE, primary_text=CAPTION,
                 offer=OFFER, marketer_notes=NOTES)
    assert resp.status_code == 303, resp.status_code
    assert launcher.reached, "the post never reached prepare"
    cfg = launcher.reached[-1]

    assert cfg.creative_inputs.headline == HEADLINE
    assert cfg.creative_inputs.primary_text == CAPTION
    assert cfg.creative_inputs.offer == OFFER
    assert cfg.marketer_notes == NOTES

    # ⚠ The seam, restated at the field level: notes are NOT creative inputs.
    # `_creative_copy_block` feeds a CreativeInputs straight to the agent, so a
    # note that ended up on this object would be read aloud to the panel.
    assert NOTES not in cfg.creative_inputs.to_dict().values()
    print("  copy → creative_inputs, notes → RunConfig, and they do not mix ✓")


def test_ad_copy_unlocks_the_funnel_stages(world) -> None:
    """Not decoration: `provided_inputs()` is what gates L3.5's click/convert
    stages, so supplying copy changes what the run can project."""
    client, launcher = world
    _post(client)
    assert launcher.reached[-1].provided_inputs() == []
    _post(client, headline=HEADLINE, offer=OFFER)
    assert launcher.reached[-1].provided_inputs() == ["ad_copy", "offer"]
    print("  supplying copy/offer unlocks the L3.5 stages ✓")


def test_an_image_only_run_is_unchanged(world) -> None:
    """The positive control for "no engine change": leave every new box empty
    and the config must be byte-identical to what the form produced before."""
    client, launcher = world
    _post(client)
    cfg = launcher.reached[-1]
    assert cfg.creative_inputs.headline == ""
    assert cfg.creative_inputs.primary_text == ""
    assert cfg.creative_inputs.offer == ""
    assert cfg.marketer_notes == ""
    assert cfg.brand_notes == ""
    print("  empty boxes leave an image-only run exactly as it was ✓")


def test_typed_prose_survives_a_rejected_upload(world) -> None:
    """Design state 4C. Losing a paragraph someone wrote is a worse failure
    than losing a dropdown, and prose is the most expensive thing to retype."""
    client, _ = world
    resp = client.post(
        "/reads/new",
        files={"asset": ("brief.pdf", b"%PDF-1.4", "application/octet-stream")},
        data={**ANSWERS, "asset_label": "x", "purpose": "direct_sell",
              "headline": HEADLINE, "primary_text": CAPTION,
              "offer": OFFER, "marketer_notes": NOTES},
        follow_redirects=False)
    assert resp.status_code == 400
    body = resp.text.replace("&#x27;", "'").replace("&amp;", "&")
    assert HEADLINE in body, "the headline was cleared by the rejection"
    assert CAPTION in body, "the caption was cleared by the rejection"
    assert OFFER in body, "the offer was cleared by the rejection"
    assert NOTES in body, "the notes were cleared by the rejection"
    print("  a rejection keeps every typed field ✓")


def test_notes_cannot_smuggle_markup_into_the_form(world) -> None:
    """They are echoed back into a textarea, and a textarea is closed by the
    literal string `</textarea>` regardless of context."""
    client, _ = world
    resp = client.post(
        "/reads/new",
        files={"asset": ("brief.pdf", b"%PDF-1.4", "application/octet-stream")},
        data={**ANSWERS, "asset_label": "x", "purpose": "direct_sell",
              "marketer_notes": "</textarea><script>alert(1)</script>"},
        follow_redirects=False)
    assert resp.status_code == 400
    assert "<script>alert(1)</script>" not in resp.text, "the notes broke out"
    print("  notes are escaped on the way back into the form ✓")


def test_there_is_still_no_free_text_audience_box(world) -> None:
    """The competitor's central defect, kept out deliberately. Structured
    controls compose the panel; prose is context for classification only."""
    client, _ = world
    body = client.get("/reads/new").text.lower()
    assert "describe your audience" not in body
    assert 'name="audience"' not in body and 'name="target_audience"' not in body
    # and the structured controls are still all there
    for name in ("age_from", "age_to", "gender", "income", "geography"):
        assert f'name="{name}"' in body, f"the {name} control disappeared"
    print("  no prose audience box; every structured control intact ✓")
