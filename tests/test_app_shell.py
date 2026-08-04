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
from server.runs import discover_brands
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
        base_dir=tmp_path,
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
    """Equality, not prefix matching.

    A `startswith` check here passes when /reads/new marks *Reads* as current,
    which is exactly the confusion available: the review and status screens
    deliberately claim a nav item that is not their own URL, and which one they
    claim is a decision worth pinning rather than a coincidence to tolerate.
    """
    runs_root = client.__dict__["runs_root"]
    rd = runs_root / "demo" / "hw" / "live"
    rd.mkdir(parents=True)
    (rd / "run.json").write_text(json.dumps(
        {"run_id": "live", "status": "committed", "updated_at": "t",
         "config": {"asset": {"label": "Q3 whey"}}}))

    expected = {
        "/reads": "/reads",
        "/reads/new": "/reads/new",
        "/profiles": "/profiles",
        "/settings": "/settings",
        # A run in flight belongs to the list it will appear in, not to the
        # form that started it.
        "/reads/status/demo/hw/live": "/reads",
    }
    for path, want in expected.items():
        page = client.get(path).text
        marked = (page.split('aria-current="page"')[0]
                  .rsplit('href="', 1)[-1].split('"')[0])
        assert marked == want, f"{path} marks {marked!r}, expected {want!r}"
    print(f"  {len(expected)} screens mark the right nav item ✓")


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


# ---- the pickers only offer things that work --------------------------


def test_the_brand_picker_hides_brands_that_cannot_actually_run(tmp_path: Path) -> None:
    """⚠ Replaces the audience-spec picker test, 2026-08-04. The form no longer
    offers audience files at all, so the `#29` rule — NEVER OFFER WHAT CANNOT BE
    CHOSEN — has to hold on the surface that replaced it.

    The rule exists because the failure lands AFTER the operator has done the
    work: they upload a creative, fill in an audience, submit, and only then
    does the engine refuse. Every broken shape below is one that passes a
    superficial "does the directory exist" check and dies inside
    `RunService.prepare`.
    """
    from tests.helpers_brand import build_brand

    runs = tmp_path / "runs"
    build_brand(runs, brand="good")

    # 1. A profile naming no category — nothing to read the ad against.
    ent = runs / "demo" / "no_category" / "entities"
    (ent / "audiences").mkdir(parents=True)
    build_brand(runs, brand="no_category")
    profile = json.loads((ent / "brand_profile.json").read_text())
    profile["categories"] = []
    (ent / "brand_profile.json").write_text(json.dumps(profile))

    # 2. A profile whose disposition library is missing — the failure the old
    #    free-text brand box produced on a typo, as a FileNotFoundError inside
    #    prepare.
    build_brand(runs, brand="no_library")
    (runs / "demo" / "no_library" / "entities" / "library.json").unlink()

    # 3. A saved audience that does not validate — the `*_baseline.json`
    #    failure in its entity form.
    build_brand(runs, brand="bad_audience")
    aud_path = (runs / "demo" / "bad_audience" / "entities" / "audiences"
                / "cold_traffic_v1.json")
    bad = json.loads(aud_path.read_text())
    bad["spec"]["demographics"] = []
    aud_path.write_text(json.dumps(bad))

    # 4. A saved audience naming a consumer type its own library does not have.
    #    This one PASSES its own validate() and dies at library.resolve(), so a
    #    check that only called validate() would offer it.
    build_brand(runs, brand="dangling_type")
    aud_path = (runs / "demo" / "dangling_type" / "entities" / "audiences"
                / "cold_traffic_v1.json")
    dangling = json.loads(aud_path.read_text())
    dangling["spec"]["disposition_labels"] = ["a_type_that_was_deleted"]
    aud_path.write_text(json.dumps(dangling))

    offered = [b.brand_profile_id for b in discover_brands(runs, account="demo")]
    assert offered == ["good"], (
        f"a brand that cannot run was offered: {offered}")

    # Positive control: the four broken ones are genuinely on disk, so the
    # assertion above is the filter working rather than the fixture being empty.
    assert len(list((runs / "demo").glob("*/entities/brand_profile.json"))) == 5
    print("  4 unrunnable brands on disk, 0 of them offered ✓")


def test_the_repo_s_own_brands_are_all_runnable_as_offered() -> None:
    """The picker against the real `runs/` directory rather than fixtures —
    the `#29` bug was about the actual files on disk, not a hypothetical.

    Skipped rather than failed when the repo has no brands set up: `runs/` is
    gitignored, so a fresh clone legitimately has none until the scaffolds are
    run, and failing there would report a missing fixture as a broken filter.
    """
    from agent.telemetry import runs_root

    offered = discover_brands(runs_root(), account="demo")
    if not offered:
        pytest.skip("no brands scaffolded in this checkout")
    for brand in offered:
        brand.template.validate()        # the exact call prepare makes
        assert brand.dispositions, f"{brand.brand_profile_id} resolved no types"
        assert brand.category, f"{brand.brand_profile_id} has no category"
    print(f"  {len(offered)} brands offered, every one of them runnable ✓")


def test_an_account_with_no_brands_says_so_instead_of_an_empty_picker(
        tmp_path: Path) -> None:
    """⚠ Rewritten 2026-08-04: the unusable state is "no BRANDS", not "no
    audience specs", because the form now derives everything from the brand.

    This is a NEW ACCOUNT's very first visit, so what it says matters as much
    as that it says something: it explains what a brand is and that we build it
    during onboarding, rather than describing a `specs/` directory the customer
    will never look at. And it offers no submit path — a picker with no options
    looks fine and then fails on a field they were never able to fill in.
    """
    c = sign_in(TestClient(create_app(
        runs_root=tmp_path / "runs", sessions_root=tmp_path / "s",
        base_dir=tmp_path, auth=demo_auth())))
    page = c.get("/reads/new").text
    flat = _flat(page)
    assert "No brands are set up on this account yet" in flat
    assert "during onboarding" in flat, \
        "it says what is missing without saying how it gets fixed"
    assert "<select" not in page, "an unusable form still offered a submit path"
    # The old vocabulary must not resurface here — a customer has no idea what
    # an audience spec is, which is the whole reason for the rewrite.
    for jargon in ("audience spec", "specs/", ".json"):
        assert jargon not in flat, f"internal vocabulary on a customer page: {jargon!r}"
    print("  no brands: says so, says why, offers no dead submit path ✓")


def test_a_refused_preparation_answers_whether_it_was_charged() -> None:
    page = app_html.error_page(
        "Could not prepare the read", "The run was refused before it started.",
        detail="ValueError: AudienceSpec.demographics must have >= 1 point",
        note="No credit was debited.")
    assert "WERE YOU CHARGED" in page
    assert "No credit was debited" in _flat(page)
    # The engine's own words survive, framed rather than raw.
    assert "must have &gt;= 1 point" in page
    assert "WHAT THE ENGINE SAID" in page
    print("  a refusal says what happened, what the engine said, and the cost ✓")
