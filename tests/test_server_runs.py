"""Starting a run from the browser — the paid path, tested without paying.

Every test here stubs `RunService`. Nothing in the offline suite may reach the
real engine: a route that fires target_id on import, or a double-submitted
form that commits twice, costs real money, and the whole point of testing this
layer is to find that before a session does.

The load-bearing assertions:

  * the confirmation surface carries EVERY warning `batch_run._print_preparation`
    prints — the fidelity spec is that function, not a mock-up
    (memory: report_surface_fidelity). A missing warning is a run committed blind.
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
    """Records what it was asked to do; never calls RunService."""

    def __init__(self, prep: RunPreparation | None = None) -> None:
        super().__init__()
        self.stub_prep = prep
        self.prepared_configs: list = []
        self.committed: list[str] = []

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
    """A repo-shaped temp world: a spec, a creative, empty runs/."""
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
    return tmp_path


def _client(world: Path, launcher: Launcher) -> TestClient:
    return sign_in(TestClient(create_app(
        runs_root=world / "runs", sessions_root=world / "sessions",
        base_dir=world, specs_dir=world / "specs",
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
    form = {"category": "health_wellness_nutrition",
            "audience_spec": "hw_cold.json"}
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




def test_the_picker_offers_every_category_and_leads_with_the_validated_one(world) -> None:
    """The picker stopped marking unvalidated categories on 2026-08-03 — the
    user's explicit call, taken with the consequence in front of them. What
    survives is the ORDER (the safe choice is first) and the warning itself,
    which moved to the review screen and is asserted there by
    `test_an_unvalidated_category_warns_loudly_and_commits_anyway`.

    Pinned because a marker that quietly reappears, or an order that quietly
    goes alphabetical, are both changes to a decision rather than to a style.
    """
    client = _client(world, StubLauncher())
    page = client.get("/reads/new").text

    packs = [p.stem for p in Path("packs").glob("*.py")
             if not p.stem.startswith("_")]
    for cat in packs:
        assert f'value="{cat}"' in page, f"{cat} missing from the picker"
    assert "NOT VALIDATED" not in page

    order = [c for c in
             [page.split('value="')[i].split('"')[0]
              for i in range(1, page.count('value="') + 1)] if c in packs]
    assert order[0] in VALIDATED_CATEGORIES, (
        f"picker leads with {order[0]!r}, which has no validated library")
    print(f"  {len(packs)} categories offered, validated first, unmarked ✓")


def test_prepare_builds_the_config_the_form_described(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    resp = _prepare(
        client,
        files={"asset": ("client_ad.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        asset_label="Q3 whey", declared_targeting="adults 25-44, metro",
        purpose="direct_sell", brand_profile="hw", marketer_led="1")
    assert resp.status_code == 200, resp.text

    config = launcher.prepared_configs[-1]
    assert config.asset.label == "Q3 whey"
    assert config.category == "health_wellness_nutrition"
    assert config.declared_targeting == "adults 25-44, metro"
    assert config.marketer_led is True
    assert config.account_id == "demo" and config.brand_profile_id == "hw"
    # The upload landed outside the repo tree the tests were given, with a
    # server-minted name rather than the client's.
    saved = list((world / "uploads").glob("*.png"))
    assert len(saved) == 1 and saved[0].name != "client_ad.png"
    # Recorded relative to the repo root, resolving to the file just saved.
    assert (world / config.asset.image_path).resolve() == saved[0].resolve()
    print("  prepare builds the config the form described ✓")


def test_marketer_led_is_off_when_the_box_is_unticked(world) -> None:
    """An omitted checkbox posts nothing at all. Defaulting it to True would
    silently change panel composition on every run."""
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    _prepare(client)
    assert launcher.prepared_configs[-1].marketer_led is False
    print("  unticked marketer-led stays off ✓")


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


def test_unknown_audience_spec_is_refused_before_spending(world) -> None:
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    resp = _prepare(client, audience_spec="../../etc/passwd")
    assert resp.status_code == 400
    assert not launcher.prepared_configs
    print("  bad spec path refused before target_id fires ✓")


# ---- the confirmation surface -----------------------------------------


def test_confirmation_surface_carries_every_cli_warning(world) -> None:
    """Fidelity against batch_run._print_preparation. Each fragment below is a
    guardrail the CLI prints before a credit is debited."""
    launcher = StubLauncher(_prep(world, mismatch=True,
                                  spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client).text

    for fragment, what in (
        (MISMATCH_MSG, "gross demographic mismatch"),
        (COVERAGE_MSG, "thin audience coverage"),
        (PURPOSE_MSG, "purpose mismatch"),
        (TRUST_MSG, "trust ceiling"),
        (NO_MATCH_MSG, "no-match note"),
        (AMBIGUITY_MSG, "ambiguity note"),
        ("skeptic_new_brand", "provisional dispositions"),
        ("$4.13", "estimated cost"),
        ("29", "persona cores rendered"),
        ("Macro-counting lifters", "inferred target"),
        ("Spec-forward pack shot", "target reasoning"),
        ("enthusiast_macros_lifter", "disposition classification"),
        ("impulsive 50%", "chaos mix"),
        ("9baaf54d7841", "panel version"),
    ):
        # Escaped, because the renderer escapes — the no-match note contains an
        # apostrophe, and asserting the raw string would report a dropped
        # guardrail that is actually present.
        assert escape(fragment, quote=True) in page, \
            f"confirmation surface dropped: {what}"
    print("  all 14 CLI warnings present on the confirm screen ✓")


def test_a_demographic_mismatch_warns_loudly_and_commits_anyway(world) -> None:
    """Advisory as of 2026-08-03 — the user's explicit call, and it matches
    what the guard was always documented to be (memory:
    demographic_mismatch_guard, "never blocks").

    What this pins is the half that still has to hold: the flag is RENDERED,
    and it is rendered as a STOP row rather than folded in with the ordinary
    warnings. Deleting the refusal without this test would leave nothing at all
    asserting the operator was told.
    """
    launcher = StubLauncher(_prep(world, mismatch=True,
                                  spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client).text
    run_id = launcher.stub_prep.run_id

    assert escape(MISMATCH_MSG, quote=True) in page, "the mismatch was not shown"
    assert "Gross demographic mismatch" in page
    assert "f--stop" in page, "shown, but not as a STOP row"
    assert "marked STOP" in page, "the commit button does not point at the flag"
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
    launcher = StubLauncher(_prep(world, spec_name="specs/hw_cold.json",
                                  category="chocolate"))
    client = _client(world, launcher)
    page = _prepare(client, category="chocolate").text
    run_id = launcher.stub_prep.run_id

    assert "Unvalidated category" in page
    assert "chocolate" in page
    for phrase in ("will not fail gracefully", "confident and wrong"):
        assert phrase in page, f"the consequence no longer says {phrase!r}"
    assert "f--stop" in page, "shown, but not as a STOP row"
    assert "acknowledge_unvalidated_category" not in page

    ok = client.post("/reads/prepared/commit", data={"run_id": run_id},
                     follow_redirects=False)
    assert ok.status_code == 303, "the commit is not supposed to be blocked"
    for job in launcher.jobs.values():
        job.thread.join(timeout=5)
    print("  unvalidated category shown as STOP with its consequence, "
          "commit not blocked ✓")


def test_both_stop_flags_render_in_one_stack(world) -> None:
    """Six warnings and two STOPs — the design's worst case. One container,
    hairline rows, one tag column: eight read as a list, not a wall."""
    launcher = StubLauncher(_prep(world, mismatch=True, category="chocolate",
                                  spec_name="specs/hw_cold.json"))
    client = _client(world, launcher)
    page = _prepare(client, category="chocolate").text

    assert page.count('class="f f--stop"') == 2, "both STOPs should be marked"
    assert page.count('<div class="flags">') == 1, "flags split across stacks"
    assert "2 flags above are marked STOP" in page
    print("  8 flags, 2 of them STOP, in one stack ✓")


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
