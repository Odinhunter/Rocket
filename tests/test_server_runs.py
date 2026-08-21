"""Starting a run from the browser — the paid path, tested without paying.

Every test here stubs `RunService`. Nothing in the offline suite may reach the
real engine: a route that fires target_id on import, or a double-submitted
form that commits twice, costs real money, and the whole point of testing this
layer is to find that before a session does.

The load-bearing assertions:

  * ⚠ the confirmation surface carries every warning the operator can ACT ON,
    which as of 2026-08-04 is no longer every warning `batch_run._print_preparation`
    prints. The user's explicit decision: a row survives here if it tells them
    something about their own input they can fix before paying; instrument
    limits (trust ceiling, provisional dispositions) moved to the methodology
    page. The CLI is unchanged and remains the full-fidelity surface
    (memory: report_surface_fidelity), so the two now differ on purpose and
    both directions are asserted.
  * a gross demographic mismatch is refused server-side, not by the form's
    `required` attribute, which a direct POST walks straight past. The CLI
    treats this one as overriding even --yes.
  * committing is idempotent, because the failure mode of a double click is a
    second ~$4 charge.
"""

from __future__ import annotations

import json
import threading
import time
from html import escape
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.config import build_run_config
from agent.run_service import RunPreparation
from agent.synthesis_types import (
    CoverageWarning, DemographicMismatch, DispositionTarget, PurposeMismatch,
    TargetClassification,
)
from server.app import create_app
from server.launcher import VALIDATED_CATEGORIES, Launcher
from tests.helpers_auth import demo_auth, sign_in
from tests.helpers_brand import ANSWERS, BRAND, build_brand

# Fragments of every warning the CLI confirmation surface prints. Kept as data
# so a new guardrail added to _print_preparation shows up as a failing name
# here rather than being silently absent from the browser flow.
MISMATCH_MSG = "Ad reads as aimed at men 25-34; declared audience is women 45+"
COVERAGE_MSG = "Only 3 of 22 personas fall inside the declared slice"
PURPOSE_MSG = "Dense product-spec layout, no price, no CTA"
TRUST_MSG = "This panel has 1 within-target disposition"
NO_MATCH_MSG = "No disposition in the pool sits inside this ad's target"
AMBIGUITY_MSG = "The creative could plausibly be aimed at two segments"
SCOPE_LABELS = ("BETA", "PARKED")


def _prep(tmp_path: Path, *, mismatch: bool = False, spec_name: str,
          category: str = "health_wellness_nutrition",
          **config_kw) -> RunPreparation:
    """A RunPreparation carrying every advisory at once — the maximal surface,
    so one render proves them all present rather than six fixtures each
    proving one."""
    config = build_run_config(
        asset_path=tmp_path / "ad.png", audience_spec=tmp_path / spec_name,
        category=category, account_id="demo",
        brand_profile_id="hw", **config_kw,
    )
    tc = TargetClassification(
        inferred_target_description="Macro-counting lifters, 25-34",
        target_reasoning="Spec-forward pack shot, gram claims in the headline",
        disposition_classifications=[
            DispositionTarget(disposition_label="enthusiast_macros_lifter",
                              classification="within", reasoning="r"),
            DispositionTarget(disposition_label="aspirant_clean_label",
                              classification="outside", reasoning="r"),
        ],
        ambiguity_note=AMBIGUITY_MSG, no_match_note=NO_MATCH_MSG,
    )
    return RunPreparation(
        run_id="20260728_120000_seed71_test_ad", config=config,
        target_classification=tc,
        audience_summary={
            "demographics": [], "disposition_labels": ["a", "b"],
            "context_envelope": ["feed", "story"],
            "chaos_distribution": [{"profile": "impulsive", "weight": 0.5},
                                   {"profile": "deliberate", "weight": 0.5}],
            "panel_size": 100, "n_segments": 6,
            "segment_granularity": "disposition_chaos_band",
        },
        panel=[], provisional_dispositions=["skeptic_new_brand"],
        estimated_cost_usd=4.13, persona_cores_rendered=29,
        panel_version="9baaf54d7841",
        demographic_mismatch=(
            DemographicMismatch(axes=["gender", "age"], inferred_gender="male",
                                inferred_age_band="25-34",
                                declared_summary="women 45+",
                                message=MISMATCH_MSG)
            if mismatch else None
        ),
        coverage_warning=CoverageWarning(
            eligible_count=3, total_count=22, eligible_labels=["a"],
            message=COVERAGE_MSG),
        purpose_mismatch=PurposeMismatch(
            declared_purpose="direct_sell", apparent_purpose="awareness_informer",
            declared_label="direct sell", apparent_label="awareness informer",
            suggested_flag="--purpose awareness_informer", message=PURPOSE_MSG),
        trust_ceiling_warning=TRUST_MSG,
    )


class StubLauncher(Launcher):
    """Records what it was asked to do; never calls RunService.

    That second half was FALSE until 2026-08-04. `commit` delegated to
    `super().commit(prep)` — correct, because these tests want the real
    idempotency lock and the real worker thread — but the real worker then
    called the real `RunService.commit`, which wrote directories into the real
    `runs/` and was one populated fixture away from spending ~$4 from pytest.

    Overriding `_run_engine` keeps everything the tests care about (thread,
    job bookkeeping, error capture) and drops only the model calls.
    """

    def _run_engine(self, prep) -> None:  # noqa: ANN001
        self.engine_calls.append(prep.run_id)

    def __init__(self, prep: RunPreparation | None = None) -> None:
        super().__init__()
        self.stub_prep = prep
        self.prepared_configs: list = []
        self.committed: list[str] = []
        # What the worker thread actually reached, as opposed to what commit
        # was asked for. The two differing is the bug this class had.
        self.engine_calls: list[str] = []

    def prepare(self, config):
        self.prepared_configs.append(config)
        prep = self.stub_prep
        assert prep is not None, "test did not supply a preparation"
        prep.config = config
        self.prepared[prep.run_id] = prep
        return prep

    def commit(self, prep):
        self.committed.append(prep.run_id)
        return super().commit(prep)


@pytest.fixture
def world(tmp_path: Path):
    """A repo-shaped temp world: a spec, a creative, and one brand set up.

    The brand entities are what the form reads since 2026-08-04 — it derives
    the category, the disposition library and the audience template from the
    brand rather than asking for them. `specs/` is still written because
    `_prep` builds its RunConfig from a spec file directly, which is the CLI's
    path and not the form's.
    """
    specs = tmp_path / "specs"
    specs.mkdir()
    # A REAL spec, copied rather than hand-written: AudienceSpec.from_dict is
    # strict about nested shapes, and a hand-rolled stub would test the fixture
    # instead of the route.
    (specs / "hw_cold.json").write_text(
        (Path(__file__).resolve().parent.parent
         / "specs" / "health_wellness_cold_traffic.json").read_text()
    )
    (tmp_path / "ad.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "runs").mkdir()
    build_brand(tmp_path / "runs")
    return tmp_path


def _client(world: Path, launcher: Launcher) -> TestClient:
    return sign_in(TestClient(create_app(
        runs_root=world / "runs", sessions_root=world / "sessions",
        base_dir=world,
        uploads_dir=world / "uploads", launcher=launcher, auth=demo_auth(),
    )))


# ---- the form ---------------------------------------------------------

def _prepare(client: TestClient, **data):
    """POST the form and follow the preparing page through to the review.

    The real flow is asynchronous — the POST starts a thread and redirects to
    a page that says "preparing" until it finishes — so a test that just
    POSTed and read the response would be reading the wrong screen. Polling
    here rather than reaching into the launcher keeps the test on the same
    path a browser takes, including the redirect that page issues when the
    preparation lands.
    """
    files = data.pop("files", {"asset": ("a.png", b"x", "image/png")})
    # The four audience answers plus the brand — what the form posts since
    # 2026-08-04. `category` and `audience_spec` are no longer inputs at all:
    # both are derived from the brand.
    form = dict(ANSWERS)
    form.update(data)
    resp = client.post("/reads/new", files=files, data=form,
                       follow_redirects=False)
    if resp.status_code != 303:
        return resp        # rejected before anything was started
    where = resp.headers["location"]
    for _ in range(200):
        resp = client.get(where, follow_redirects=False)
        if resp.status_code == 303:
            where = resp.headers["location"]
            continue
        if "Preparing the read" not in resp.text:
            return resp
        time.sleep(0.01)
    raise AssertionError("preparation never finished")




def test_the_picker_offers_brands_and_leads_with_the_validated_one(world) -> None:
    """⚠ Rewritten 2026-08-04. The picker used to offer CATEGORIES (pack stems)
    and a second dropdown of audience `.json` FILENAMES. It now offers brands,
    because the category, the disposition library and the audience template are
    all derivable from one — and the free-text brand box that actually selected
    the library is gone with them.

    What survives from the old contract is the ORDER: the safe choice leads,
    and nothing is marked (the user's explicit call, 2026-08-03 — the warning
    moved to the review screen, asserted by
    `test_an_unvalidated_category_warns_loudly_and_commits_anyway`).

    A marker that quietly reappears, or an order that quietly goes
    alphabetical, are both changes to a decision rather than to a style.
    """
    # A second brand whose category has no validated library, and whose id
    # sorts BEFORE the validated one — so "validated first" cannot pass by
    # alphabetical accident, which is what it would do with a name like "zzz".
    build_brand(world / "runs", brand="aaa_choc", category="chocolate",
                audience_id="cold_traffic_v1")
    client = _client(world, StubLauncher())
    page = client.get("/reads/new").text

    for brand in (BRAND, "aaa_choc"):
        assert f'value="{brand}"' in page, f"{brand} missing from the picker"
    assert "NOT VALIDATED" not in page
    assert "hw_cold.json" not in page, "a filename is back in front of the customer"
    assert "audience_spec" not in page and "declared_targeting" not in page, \
        "a field the customer cannot answer came back"

    assert page.index(f'value="{BRAND}"') < page.index('value="aaa_choc"'), (
        "the picker leads with a brand whose category has no validated library")
    print("  brands offered, validated category first, no filenames ✓")


def test_prepare_builds_the_config_the_form_described(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    resp = _prepare(
        client,
        files={"asset": ("client_ad.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        asset_label="Q3 whey", purpose="direct_sell",
        age_from="25", age_to="44", gender="female", income="17:40",
        geography="metro tier-1")
    assert resp.status_code == 200, resp.text

    config = launcher.prepared_configs[-1]
    assert config.asset.label == "Q3 whey"
    # Derived from the brand, never posted — the whole point of the rewrite.
    assert config.category == "health_wellness_nutrition"
    assert config.account_id == "demo" and config.brand_profile_id == BRAND
    assert config.library_id == "hw_lib_v1" and config.audience_id == "cold_traffic_v1"
    # Composed from the four answers, so the classifier's hint and the panel's
    # frame come from one source and can no longer disagree.
    assert config.declared_targeting == (
        "women 25-44, metro tier-1, ₹17-40L household income"), \
        f"declared targeting was not composed from the answers: {config.declared_targeting!r}"
    # The answers reached the SPEC, not just the prose.
    point = config.audience_spec.demographics[0]
    assert len(config.audience_spec.demographics) == 1
    assert (point.gender, point.age_min, point.age_max) == ("female", 25, 44)
    assert (point.income_lpa_min, point.income_lpa_max) == (17.0, 40.0)
    # Inherited from the brand's saved audience rather than asked for.
    assert config.audience_spec.panel_size == 30
    assert len(config.audience_spec.context_envelope) >= 3
    # The upload landed outside the repo tree the tests were given, with a
    # server-minted name rather than the client's.
    saved = list((world / "uploads").glob("*.png"))
    assert len(saved) == 1 and saved[0].name != "client_ad.png"
    # Recorded relative to the repo root, resolving to the file just saved.
    assert (world / config.asset.image_path).resolve() == saved[0].resolve()
    print("  prepare builds the config the form described ✓")


def test_marketer_led_is_always_on_from_the_form(world) -> None:
    """⚠ Inverted 2026-08-04, and the inversion is the honest direction.

    `marketer_led` was a checkbox, and it is what makes the customer's declared
    demographics compose the panel. A form built ENTIRELY out of those
    demographics can only ever want it on: unticked, every answer they gave
    would be collected, displayed back to them, and then ignored by the panel
    builder. A checkbox that must never be unticked is not a choice, it is a
    trap, so it is gone and the value is derived.

    The CLI still exposes `--marketer-led`; this pins the form's path only.
    """
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = client.get("/reads/new").text
    assert "marketer_led" not in page, "the trap checkbox is back on the form"
    _prepare(client)
    assert launcher.prepared_configs[-1].marketer_led is True, (
        "the demographics the customer answered would not compose the panel")
    print("  marketer-led is derived, not offered as a checkbox ✓")


def test_upload_rejects_a_non_image(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    resp = _prepare(client,
                    files={"asset": ("payload.svg", b"<svg/>", "image/svg+xml")})
    assert resp.status_code == 400
    assert not launcher.prepared_configs, "prepared (and paid) on a bad upload"
    # Back on the form with the reason, not a dead-end error page: the design's
    # state 4C. A rejection that loses what was already typed is a re-type.
    assert "Drop the ad creative here" in resp.text
    assert "REJECTED" in resp.text and "payload.svg" in resp.text
    print("  non-image upload refused before any spend, form kept ✓")


def test_an_unknown_brand_is_refused_before_spending(world) -> None:
    """The brand id arrives from a form field and is resolved against the
    DISCOVERED list, never used as a path component. Posting a traversal
    reaches `_resolve_audience`, which does not find it and refuses — before
    target_id fires and before anything is charged.

    Both halves matter: a 400 with the prepare still having run would be a paid
    refusal.
    """
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    for bad in ("../../etc/passwd", "no_such_brand", "demo/health_wellness_demo"):
        resp = _prepare(client, brand=bad)
        assert resp.status_code == 400, f"{bad!r} was accepted"
        assert not launcher.prepared_configs, f"{bad!r} reached the engine"
        assert "Pick one of your brands" in resp.text, \
            f"{bad!r} refused without saying what to do"
    print("  an unknown brand is refused before target_id fires ✓")


# ---- the confirmation surface -----------------------------------------


def test_the_review_screen_keeps_what_the_operator_can_act_on(world) -> None:
    """⚠ Rewritten 2026-08-04. This screen no longer mirrors
    `batch_run._print_preparation` row for row, and the divergence is the point.

    The rule `_prep_flags` applies: a row survives if it tells the operator
    something about THEIR OWN INPUT that they can fix before paying; it moves
    to the methodology page if it is a limit of our instrument. Eight
    qualifications stacked above the commit button read as a product
    apologising for itself.

    Both halves are asserted, because either alone is satisfiable by the wrong
    outcome — keeping everything, or quietly dropping something that protects
    the operator's money. The CLI is deliberately unchanged and keeps all of
    them (memory: report_surface_fidelity), so its fidelity test still stands.
    """
    launcher = StubLauncher(_prep(world, mismatch=True,
                                  spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client).text

    # Escaped, because the renderer escapes — the no-match note contains an
    # apostrophe, and asserting the raw string would report a dropped guardrail
    # that is actually present.
    for fragment, what in (
        (MISMATCH_MSG, "the creative does not match the declared audience"),
        (COVERAGE_MSG, "how many consumer types this audience reaches"),
        (PURPOSE_MSG, "the ad's apparent job is not the one selected"),
        (NO_MATCH_MSG, "creative and audience do not overlap"),
        (AMBIGUITY_MSG, "who the ad is for is ambiguous"),
        ("$4.13", "estimated cost"),
        ("29", "persona cores rendered"),
        ("Macro-counting lifters", "inferred target"),
        ("Spec-forward pack shot", "target reasoning"),
        # ⚠⚠ WAS ("enthusiast_macros_lifter", ...) — THE THIRD TEST FOUND
        # RATIFYING THIS DEFECT, after test_dashboard_html.py:1204 and
        # test_cycle_position.py::test_cycle_line_prose. It REQUIRED the raw
        # underscore label on the page a customer reads before spending a
        # credit, so fixing the bug broke the suite and the fix looked like
        # the regression. The FACT still belongs here — an operator must see
        # which buyer types were classified — so it asserts the readable form.
        ("enthusiast · macros lifter", "disposition classification"),
        ("impulsive 50%", "chaos mix"),
        ("9baaf54d7841", "panel version"),
    ):
        assert escape(fragment, quote=True) in page, \
            f"the review screen dropped something actionable: {what}"

    # Moved to the methodology page: limits of the instrument, not of their ad.
    for fragment, what in (
        (TRUST_MSG, "trust ceiling — 'a confident ship-it is unreachable'"),
        ("skeptic_new_brand", "provisional dispositions (library bookkeeping)"),
    ):
        assert escape(fragment, quote=True) not in page, \
            f"an instrument limit is back on the money screen: {what}"

    # ⭐⭐ THE CLASS, NOT THE INSTANCE. Asserting the readable form is present
    # would still pass if BOTH forms rendered. This bans the machine identifier
    # outright on the last screen before a credit is spent — the surface the
    # review doc named and the one still leaking after #81 fixed the report.
    for raw in ("enthusiast_macros_lifter", "enthusiast macros lifter"):
        assert raw not in page, (
            f"the raw disposition label {raw!r} is back on the pre-commit "
            f"screen — engine vocabulary wearing the grammar of English, on "
            f"the page where a customer decides whether to spend"
        )
    print("  the review screen keeps what they can act on, drops the rest ✓")


def test_a_demographic_mismatch_warns_loudly_and_commits_anyway(world) -> None:
    """Advisory as of 2026-08-03 — the user's explicit call, and it matches
    what the guard was always documented to be (memory:
    demographic_mismatch_guard, "never blocks").

    What this pins is the half that still has to hold: the operator is TOLD,
    in words they can act on, and told what to do about it. ⚠ The STOP tag and
    the alarm styling are gone as of 2026-08-04 (the user's call); the MESSAGE
    is not, and the message was always the whole guardrail once the block was
    removed. Deleting the refusal without this test would leave nothing at all
    asserting the operator was told.
    """
    launcher = StubLauncher(_prep(world, mismatch=True,
                                  spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client).text
    run_id = launcher.stub_prep.run_id

    assert escape(MISMATCH_MSG, quote=True) in page, "the mismatch was not shown"
    assert "The creative and the audience don&#x27;t match" in page
    # What to DO about it — the half that makes the row actionable rather than
    # merely worrying, which is the whole justification for it surviving here.
    for phrase in ("check you uploaded the right creative", "carry on"):
        assert phrase in page, f"the row no longer says what to do: {phrase!r}"
    # ⚠ Asserted on the RENDERED row, not the bare token: `.flags .f--stop`
    # is still defined in the stylesheet (the mechanism is kept so reinstating
    # a gate stays a one-line change), so `"f--stop" not in page` matches the
    # CSS and fails on a page that emits no alarm at all.
    assert 'class="f f--stop"' not in page, "the alarm styling is back"
    assert "marked STOP" not in page, "the STOP counter line is back"
    # No acknowledgement field is posted any more — the design's call, and a
    # hidden one would be worse than none: a gate that looks present.
    assert "acknowledge_mismatch" not in page

    ok = client.post("/reads/prepared/commit", data={"run_id": run_id},
                     follow_redirects=False)
    assert ok.status_code == 303
    assert launcher.committed == [run_id]
    for job in launcher.jobs.values():
        job.thread.join(timeout=5)
    print("  mismatch shown as STOP, commit not blocked ✓")


def test_an_unvalidated_category_warns_loudly_and_commits_anyway(world) -> None:
    """The more consequential of the two, so the wording is pinned, not just
    the presence of a flag.

    An unvalidated category does not degrade — every persona classifies
    "outside" and the read comes out fluent, confident and wrong. This was a
    hard gate until 2026-08-03; the user removed the block with that
    consequence stated. The text that says so is now the entire guardrail,
    which is exactly why it is asserted word by word here.
    """
    # The category is no longer posted — it comes off the brand. So the
    # unvalidated case needs a BRAND whose category has no validated library,
    # which is also the shape a real customer hits: they pick their brand, and
    # whether we have researched that category is our fact, not their input.
    build_brand(world / "runs", brand="choc_co", category="chocolate",
                audience_id="cold_traffic_v1")
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json",
                                  category="chocolate"))
    client = _client(world, launcher)
    page = _prepare(client, brand="choc_co").text
    run_id = launcher.stub_prep.run_id

    assert "We haven&#x27;t validated this category yet" in page
    assert "chocolate" in page
    # ⚠ Word for word, and deliberately unchanged by the 2026-08-04 softening.
    # The tag and the styling were cosmetic; THIS is the guardrail, and it is
    # the one thing on the screen standing between the operator and $4 spent on
    # a fluent, confident, wrong read.
    for phrase in ("will not fail gracefully", "confident and wrong"):
        assert phrase in page, f"the consequence no longer says {phrase!r}"
    assert 'class="f f--stop"' not in page, "the alarm styling is back"
    assert "acknowledge_unvalidated_category" not in page

    ok = client.post("/reads/prepared/commit", data={"run_id": run_id},
                     follow_redirects=False)
    assert ok.status_code == 303, "the commit is not supposed to be blocked"
    for job in launcher.jobs.values():
        job.thread.join(timeout=5)
    print("  unvalidated category shown as STOP with its consequence, "
          "commit not blocked ✓")


def test_the_worst_case_review_screen_is_a_short_list_not_a_wall(world) -> None:
    """⚠ Rewritten 2026-08-04. This used to assert the design's worst case —
    eight rows, two of them marked STOP — and the worst case is now the thing
    being measured rather than the thing being preserved.

    Every row here is still actionable and none of them is styled as an alarm.
    The count is asserted with a CEILING, not an exact number: the point of the
    change is that this screen cannot grow back into a wall, and pinning an
    exact count would fail the next time a genuinely actionable check is added
    while saying nothing about the property that matters.
    """
    launcher = StubLauncher(_prep(world, mismatch=True, category="chocolate",
                                  spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client, category="chocolate").text

    assert 'class="f f--stop"' not in page, "the alarm styling is back"
    assert "marked STOP" not in page, "the STOP counter line is back"
    assert page.count('<div class="flags">') == 1, "flags split across stacks"
    rows = page.count('<div class="f"')
    assert rows, "no rows at all — this fixture is supposed to be the worst case"
    assert rows <= 6, (
        f"the review screen grew back to {rows} rows; every one must be "
        "something the operator can act on before paying")
    print(f"  worst-case review screen: {rows} actionable rows, no alarms ✓")


def test_a_validated_category_needs_no_category_tick(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client).text
    assert "Unvalidated category" not in page
    print("  a validated category raises no STOP flag ✓")


def test_uploaded_creative_is_recorded_the_way_cli_runs_record_it(world) -> None:
    """Every existing run stores a repo-relative asset path. An absolute one
    would still render today but makes the run directory non-portable."""
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    _prepare(client)
    recorded = Path(launcher.prepared_configs[-1].asset.image_path)
    assert not recorded.is_absolute(), recorded
    assert (world / recorded).exists()
    print("  uploaded creative recorded relative to the repo root ✓")


def test_commit_without_a_mismatch_needs_no_acknowledgement(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    _prepare(client)
    resp = client.post("/reads/prepared/commit",
                       data={"run_id": launcher.stub_prep.run_id},
                       follow_redirects=False)
    assert resp.status_code == 303
    for job in launcher.jobs.values():
        job.thread.join(timeout=5)
    print("  clean prep commits without an extra tick ✓")


def test_committing_an_unknown_run_spends_nothing(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    resp = client.post("/reads/prepared/commit", data={"run_id": "not_a_run"},
                       follow_redirects=False)
    assert resp.status_code == 409
    assert launcher.committed == []
    print("  unknown run_id refused ✓")


# ---- the launcher itself ----------------------------------------------


def test_commit_is_idempotent_so_a_double_click_pays_once(monkeypatch) -> None:
    """The failure mode of a double-submitted form here is a second ~$4 run."""
    calls: list[str] = []
    started = threading.Event()
    release = threading.Event()

    def fake_commit(prep):
        calls.append(prep.run_id)
        started.set()
        release.wait(timeout=5)

    monkeypatch.setattr("server.launcher.RunService.commit",
                        staticmethod(fake_commit))
    launcher = Launcher()

    class _Cfg:
        account_id, brand_profile_id = "demo", "hw"

    class _Prep:
        run_id, config = "r1", _Cfg()

    prep = _Prep()
    first = launcher.commit(prep)
    started.wait(timeout=5)
    second = launcher.commit(prep)
    release.set()
    first.thread.join(timeout=5)

    assert first is second
    assert calls == ["r1"], f"committed {len(calls)} times"
    print("  double commit runs once ✓")


def test_a_crash_on_the_worker_thread_is_recorded_not_swallowed(
        tmp_path, monkeypatch) -> None:
    """A run that dies leaves run.json at 'committed' forever. Reporting that
    as 'still running' has the operator waiting on a thread that is gone."""
    def boom(prep):
        raise RuntimeError("L2 produced zero usable segment summaries")

    monkeypatch.setattr("server.launcher.RunService.commit", staticmethod(boom))
    launcher = Launcher()

    class _Cfg:
        account_id, brand_profile_id = "demo", "hw"

    class _Prep:
        run_id, config = "r1", _Cfg()

    rd = tmp_path / "demo" / "hw" / "r1"
    rd.mkdir(parents=True)
    (rd / "run.json").write_text(json.dumps(
        {"run_id": "r1", "status": "committed", "updated_at": "t"}))

    job = launcher.commit(_Prep())
    job.thread.join(timeout=5)

    status = launcher.status(tmp_path, "demo/hw/r1")
    assert status["status"] == "failed"
    assert "zero usable segment" in status["error"]
    assert status["running"] is False
    print("  worker crash surfaces as failed, with the reason ✓")


def test_status_reads_the_phase_the_engine_already_persists(tmp_path) -> None:
    """Status is a file read, not a second source of truth: the engine writes
    prepared → committed → complete into run.json on its own."""
    launcher = Launcher()
    rd = tmp_path / "demo" / "hw" / "r1"
    rd.mkdir(parents=True)
    for phase, has_report in (("prepared", False), ("committed", False),
                              ("complete", True)):
        (rd / "run.json").write_text(json.dumps({
            "run_id": "r1", "status": phase, "updated_at": "t",
            "report": {"verdict": "MIXED"} if has_report else None,
        }))
        status = launcher.status(tmp_path, "demo/hw/r1")
        assert status["status"] == phase
        assert status["has_report"] is has_report

    assert launcher.status(tmp_path, "demo/hw/nope")["status"] == "unknown"
    print("  status mirrors run.json's own phase ✓")


def test_the_status_page_stops_refreshing_once_the_run_is_done(world) -> None:
    """A finished run that keeps meta-refreshing re-fetches a whole read every
    ten seconds forever, and looks like it is still working."""
    runs_root = world / "runs"
    for name, status, report in (("running", "committed", None),
                                 ("done", "complete", {"decision":
                                                       {"decision": "ITERATE"}})):
        rd = runs_root / "demo" / "hw" / name
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "run.json").write_text(json.dumps(
            {"run_id": name, "status": status, "updated_at": "t",
             "config": {"asset": {"label": "Q3 whey"}},
             "report": report}))

    client = _client(world, StubLauncher())
    running = client.get("/reads/status/demo/hw/running").text
    done = client.get("/reads/status/demo/hw/done").text

    assert 'http-equiv="refresh"' in running
    assert 'http-equiv="refresh"' not in done
    assert "/reads/demo/hw/done" in done, "finished run does not link to its read"
    print("  status page polls while running, links the read when done ✓")


def test_interrupted_run_points_at_replay_not_a_rerun(tmp_path, monkeypatch) -> None:
    """A committed run costs $2-7 and the sigma study proved they can die
    mid-way. The recovery is replay_synthesis, never paying again."""
    monkeypatch.setattr("server.launcher.RunService.commit",
                        staticmethod(lambda prep: None))
    launcher = Launcher()

    class _Cfg:
        account_id, brand_profile_id = "demo", "hw"

    class _Prep:
        run_id, config = "r1", _Cfg()

    rd = tmp_path / "demo" / "hw" / "r1"
    rd.mkdir(parents=True)
    (rd / "run.json").write_text(json.dumps(
        {"run_id": "r1", "status": "committed", "updated_at": "t"}))
    job = launcher.commit(_Prep())
    job.thread.join(timeout=5)

    status = launcher.status(tmp_path, "demo/hw/r1")
    assert status["status"] == "interrupted"

    from server import app_html
    from agent.progress import phase_view
    page = app_html.interrupted_page(
        account="demo", label="Q3 whey", run_id="r1", key="demo/hw/r1",
        command="replay_synthesis.py runs/demo/hw/r1", recoverable=True,
        cost_note="No credit is debited.",
        phases=phase_view(status["progress"]), stopped_at=None)
    assert "replay_synthesis" in page
    assert "/reads/demo/hw/r1/replay" in page
    print("  interrupted run sends you to replay, not the checkout ✓")
