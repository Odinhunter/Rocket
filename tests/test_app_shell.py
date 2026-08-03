"""The signed-in application — the screens between the login and the read.

Built from the user's Claude Design state stack, so most of what matters here
is not "does it render" but the handful of properties that would be quietly
lost the next time someone touches it:

  * the read LEAVES the app — no sidebar wrapped around a deliverable
  * the elapsed clock stops when the run stops, rather than counting forever
  * the reads list says NOT GRADED instead of inventing a decision for the 26
    runs on disk that predate the decision layer
  * `internal/*` never appears in the product surface

Offline: synthetic run directories in a temp dir, never runs/, never the API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server import app_html
from server.app import create_app
from tests.helpers_auth import demo_auth, sign_in
from tests.test_server import _report


def _flat(html: str) -> str:
    """Collapse whitespace before matching a sentence.

    The renderers wrap long strings across source lines for readability, so a
    sentence that reads as one line in a browser is not contiguous in the
    bytes. Asserting on the raw text would fail on a re-indent, which is not a
    change to anything a reader sees.
    """
    return " ".join(html.split())

APP_PAGES = ("/reads", "/reads/new", "/profiles", "/settings")


def _run(runs_root: Path, *, account: str = "demo", brand: str = "hw",
         run_id: str = "r1", label: str = "Q3 whey", decision: str | None = "ITERATE",
         updated: str = "2026-07-28T00:00:00+00:00") -> None:
    rd = runs_root / account / brand / run_id
    rd.mkdir(parents=True, exist_ok=True)
    # A REAL Report: build_read_model refuses anything less, so a hand-rolled
    # stub would make every route that renders a read fail for the wrong reason.
    report = _report(decision=_report().decision.__class__(
        decision=decision or "INCONCLUSIVE", target_action_rate=0.11,
        trust="DIRECTIONAL", target_action_num=2, target_action_denom=18,
        within_dispositions=["enthusiast_macros_lifter"],
        load_bearing_pain_id="P1", rationale="P1 is fixable",
    )).to_dict()
    if decision is None:
        report["decision"] = None
    (rd / "run.json").write_text(json.dumps({
        "run_id": run_id, "status": "complete", "updated_at": updated,
        "config": {"asset": {"image_path": "a.png", "label": label},
                   "category": "health_wellness_nutrition",
                   "account_id": account, "brand_profile_id": brand},
        "report": report,
    }))


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    runs_root = tmp_path / "runs"
    _run(runs_root, run_id="r1", label="MuscleBlaze Biozyme", decision="ITERATE")
    _run(runs_root, run_id="r2", label="ProSki cereal", decision="REBUILD",
         updated="2026-07-26T00:00:00+00:00")
    _run(runs_root, run_id="r3", label="Old whey read", decision=None,
         updated="2026-06-30T00:00:00+00:00", brand="legacy")
    _run(runs_root, account="internal", brand="cmf_smoke", run_id="s1",
         label="Smoke test 3")
    c = sign_in(TestClient(create_app(
        runs_root=runs_root, sessions_root=tmp_path / "sessions",
        base_dir=tmp_path, specs_dir=tmp_path / "specs",
        uploads_dir=tmp_path / "uploads", auth=demo_auth())))
    c.__dict__["runs_root"] = runs_root
    return c


# ---- the shell --------------------------------------------------------


def test_every_app_page_carries_the_same_shell(client) -> None:
    """One `shell()`, so a nav item cannot appear on three screens and be
    forgotten on the fourth."""
    for path in APP_PAGES:
        page = client.get(path).text
        for label, href in app_html.NAV:
            assert f'href="{href}"' in page, f"{path} is missing the {label} link"
        assert "SIGNED IN" in page and ">demo<" in page
        # Sign-out is a POST. As a GET link, any <img src="/signout"> on any
        # page signs the operator out mid-run.
        assert '<form method="post" action="/signout">' in page
        assert 'href="/signout"' not in page
    print(f"  {len(APP_PAGES)} app pages, one shell, sign-out is a POST ✓")


def test_the_current_page_is_marked_in_the_nav(client) -> None:
    for path in APP_PAGES:
        page = client.get(path).text
        marked = page.split('aria-current="page"')[0].rsplit('href="', 1)[-1]
        assert marked.startswith(path.rstrip("/")) or path.startswith(marked), (
            f"{path} marks {marked!r} as the current page")
    print("  each page marks itself in the nav ✓")


# ---- the reads list ---------------------------------------------------


def test_the_list_shows_decisions_as_marks_and_says_when_there_is_none(client) -> None:
    """26 of the runs on disk predate the decision layer. Printing a decision
    they never had would be inventing one; the design says NOT GRADED."""
    page = client.get("/reads").text

    assert "MuscleBlaze Biozyme" in page and "ProSki cereal" in page
    assert ">ITERATE<" in page and ">REBUILD<" in page
    assert "NOT GRADED" in page
    assert "Predates the decision layer" in _flat(page)
    # The run id rides along with the date: the same creative is read more than
    # once, so the label alone does not say which run you are opening.
    assert "r1" in page and "2026-07-28" in page
    print("  decisions marked, ungraded runs named as such ✓")


def test_the_list_is_scoped_and_the_filter_narrows_it(client) -> None:
    page = client.get("/reads").text
    assert "Smoke test 3" not in page, "internal/* leaked into the product list"
    assert "3 reads" in page

    filtered = client.get("/reads?q=proski").text
    assert "ProSki cereal" in filtered
    assert "MuscleBlaze" not in filtered
    assert "filtered by" in filtered
    print("  list scoped to demo, filter narrows it ✓")


def test_the_filter_finding_nothing_says_so(client) -> None:
    page = client.get("/reads?q=zzz-no-such-ad").text
    assert "Nothing matches that filter" in page
    # NOT the first-run empty state — that one invites you to make a read, and
    # showing it here would say "you have no reads" to someone who has three.
    assert "A read puts your ad in front of" not in _flat(page)
    print("  an empty filter result is not the empty state ✓")


def test_the_empty_state_appears_only_with_no_reads(tmp_path: Path) -> None:
    c = sign_in(TestClient(create_app(
        runs_root=tmp_path / "runs", sessions_root=tmp_path / "s",
        base_dir=tmp_path, auth=demo_auth())))
    page = c.get("/reads").text
    assert "A read puts your ad in front of" in _flat(page)
    assert "New read" in page
    print("  first-run empty state ✓")


def test_the_five_decisions_are_glossed_from_the_engine(client) -> None:
    """The glosses are imported, never retyped: one string, both renderers."""
    from agent.read_model import DECISION_TAGLINE

    page = client.get("/reads").text
    for name, gloss in DECISION_TAGLINE.items():
        assert name in page, f"{name} missing from the legend"
        assert gloss.split(" — ")[0][:40] in page.replace("&#x27;", "'"), (
            f"the {name} gloss drifted from agent.read_model")
    print(f"  {len(DECISION_TAGLINE)} decisions glossed from the engine ✓")


# ---- brand profiles and settings --------------------------------------


def test_profiles_counts_reads_per_brand_within_the_account(client) -> None:
    page = client.get("/profiles").text
    assert "hw" in page and "legacy" in page
    assert "cmf_smoke" not in page, "internal/* leaked into profiles"
    assert "3 reads across 2 profiles" in _flat(page)
    print("  profiles count per brand, scoped ✓")


def test_settings_says_why_there_is_no_account_switcher(client) -> None:
    page = client.get("/settings").text
    assert "There is nothing to switch to" in _flat(page)
    print("  settings is honest about the single account ✓")


# ---- the read is not part of the app ----------------------------------


def test_opening_a_read_leaves_the_application(client) -> None:
    """No sidebar, no search, no product chrome — one back link above a
    document that gets shared."""
    page = client.get("/reads/demo/hw/r1").text

    assert "← Back to reads" in page
    assert 'class="side"' not in page, "the app shell wrapped the deliverable"
    assert "Brand profiles" not in page and "SIGNED IN" not in page
    print("  a read renders as a document, not a page ✓")


def test_the_back_bar_never_mangles_the_document() -> None:
    """It is injected into a rendered read rather than the read being
    re-rendered inside a template, because there must stay exactly one
    renderer. So it has to be inert when it cannot find its anchor."""
    assert app_html.with_back_bar("no body tag here") == "no body tag here"

    doc = "<html><head></head><body><h1>read</h1></body></html>"
    out = app_html.with_back_bar(doc)
    assert "Back to reads" in out
    assert "<h1>read</h1>" in out
    assert out.index("Back to reads") < out.index("<h1>read</h1>")
    print("  back bar injects cleanly, or not at all ✓")


# ---- the run states ---------------------------------------------------


def test_the_elapsed_clock_stops_when_the_run_stops() -> None:
    """`updated_at - started_at`, never `now - started_at`.

    A wall-clock timer on a dead run keeps counting and says it is alive,
    which is the one thing the status page exists to answer.
    """
    assert app_html.elapsed_clock({"started_at": 1000.0,
                                   "updated_at": 1161.0}) == "02:41"
    assert app_html.elapsed_clock({"started_at": 1000.0,
                                   "updated_at": 1000.0}) == "00:00"
    # A run that died an hour ago still reads as the 2m41s it lived.
    import time
    old = {"started_at": time.time() - 3600, "updated_at": time.time() - 3439}
    assert app_html.elapsed_clock(old) == "02:41"
    assert app_html.elapsed_clock(None) == "—"
    assert app_html.elapsed_clock({"started_at": "nonsense"}) == "—"
    print("  elapsed is measured, not ticking ✓")


def test_a_degraded_panel_is_a_qualification_not_an_error(client) -> None:
    runs_root = client.__dict__["runs_root"]
    rd = runs_root / "demo" / "hw" / "deg"
    rd.mkdir(parents=True)
    (rd / "run.json").write_text(json.dumps({
        "run_id": "deg", "status": "complete", "updated_at": "t",
        "config": {"asset": {"label": "Q3 whey"}},
        "report": {"decision": {"decision": "ITERATE"}},
        "panel_health": {"succeeded": 94, "expected": 100, "degraded": True},
    }))
    page = client.get("/reads/status/demo/hw/deg").text

    assert "READ COMPLETE" in page, "a degraded run is still a complete read"
    assert "94/100 agents — DEGRADED" in page
    assert "6 agents dropped out" in _flat(page)
    assert "on 94 responses instead of 100" in _flat(page)
    assert "Open the Creative Read" in page
    print("  degraded panel qualifies the read without hiding it ✓")


def test_a_failed_run_answers_whether_it_was_charged(client) -> None:
    """The question the operator actually has."""
    page = app_html.failed_page(
        account="demo", label="Q3 whey", run_id="r9",
        error="provider request failed after 3 retries", phases=[],
        stopped_at=None)
    assert "WERE YOU CHARGED" in page
    assert "has not been returned" in _flat(page)
    assert "provider request failed after 3 retries" in page
    print("  a failed run says a credit was spent ✓")


def test_recovery_is_offered_only_when_there_is_something_to_replay(client) -> None:
    """The button spends money. With no transcripts on disk it would spend it
    to reach the same place."""
    runs_root = client.__dict__["runs_root"]
    for name, with_transcripts in (("recoverable", True), ("bare", False)):
        rd = runs_root / "demo" / "hw" / name
        rd.mkdir(parents=True)
        (rd / "run.json").write_text(json.dumps({
            "run_id": name, "status": "interrupted", "updated_at": "t",
            "config": {"asset": {"label": "Q3 whey"}}}))
        if with_transcripts:
            (rd / "transcripts.json").write_text("[]")

    ok = client.get("/reads/status/demo/hw/recoverable").text
    assert "RECOVERABLE" in ok
    assert "/reads/demo/hw/recoverable/replay" in ok
    # ...and it states the real cost rather than implying free.
    assert "costs real money" in _flat(ok)
    assert "No credit is debited" in ok

    bare = client.get("/reads/status/demo/hw/bare").text
    assert "NOT RECOVERABLE" in bare
    assert "/replay" not in bare, "offered to spend money on an empty run"

    refused = client.post("/reads/demo/hw/bare/replay", follow_redirects=False)
    assert refused.status_code == 409, "the route itself must refuse too"
    assert "Nothing to recover" in refused.text
    print("  recovery offered only when transcripts exist, and priced honestly ✓")
