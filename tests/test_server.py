"""The operator server — the two properties that make a session evidence.

A brand-manager session is only worth running if two things hold, and both are
mechanisms rather than intentions:

  1. **The prediction is captured before the read is shown.** A prediction
     typed after seeing the engine's answer is hindsight, and nothing
     downstream can tell the two apart. Operator discipline is not a mechanism;
     these tests pin the server-side refusal, including on the guessable
     report URL rather than only on the page that links to it.
  2. **The decoy is actually blind.** The report normally names the ad five
     ways over (creative, h1, page title, run_id, declared targeting). If any
     of those survive into the reveal, "could they tell their read from
     another ad's?" answers itself and the check is theatre.

Offline: synthetic run directories in a temp dir, never runs/, never the API.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.schema import (
    AudienceMatch, Decision, Pain, Report, TargetMatch, TopChange,
)
from server.app import create_app
from server.runs import blind_read_model, discover_runs, resolve_run
from server.sessions import PredictionMissing, SessionStore
from tests.helpers_auth import demo_auth, sign_in

# The identifying strings planted in the fixture run. Each one is a real field
# the renderer prints; the blinding test asserts every one is gone.
REAL_LABEL = "MuscleBlaze Biozyme Performance Whey"
REAL_RUN_ID = "20260607_223525_seed71_muscleblaze_biozyme"
REAL_TARGETING = "adults 25-44, metro tier-1, protein-curious"
DECOY_LABEL = "ProSki Breakfast Cereal"


def _report(**kw) -> Report:
    base = dict(
        verdict="MIXED", confidence=76, target_match=TargetMatch(),
        top_3_changes=[TopChange(change="Put the price on the creative",
                                 why="nobody could tell what it costs")],
        strengths_to_preserve=[], context_fit_map={}, verbatim_consumer_voice=[],
        methodology_flags=["single_within_target"],
        # Populated so the header's "audience bought:" line actually renders —
        # without it the declared-audience blinding has nothing to blind and
        # its test passes for the wrong reason.
        audience_match=AudienceMatch(
            verdict="aligned", declared_summary=REAL_TARGETING,
            inferred_summary="men 25-40, gym-going",
        ),
        pain_map=[Pain(id="P1", pain="No price anywhere on the frame",
                       funnel_stage="consider", severity="high",
                       within_target=True, cited_by=["a1", "a2"])],
        decision=Decision(
            decision="ITERATE", target_action_rate=0.1111, trust="DIRECTIONAL",
            target_action_num=2, target_action_denom=18,
            within_dispositions=["enthusiast_macros_lifter"],
            load_bearing_pain_id="P1", rationale="P1 is fixable",
        ),
    )
    base.update(kw)
    return Report(**base)


# A real 1x1 PNG. The creative has to EXIST on disk for the blinding test to
# mean anything: _data_uri returns None for a missing file, so a fixture
# pointing at a nonexistent path renders no image whether or not embedding is
# suppressed, and "no data: URI in the page" passes for the wrong reason.
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def _write_run(
    runs_root: Path, *, account: str, brand: str, run_id: str,
    label: str, targeting: str = "", status: str = "complete",
    report: Report | None = None, with_replay: bool = False,
    asset_rel: str = "assets/nonexistent.png",
    category: str = "health_wellness_nutrition",
) -> Path:
    rd = runs_root / account / brand / run_id
    rd.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id, "status": status,
        "updated_at": f"2026-07-2{len(run_id) % 8}T00:00:00+00:00",
        "config": {
            "asset": {"image_path": asset_rel, "label": label},
            "category": category,
            "account_id": account, "brand_profile_id": brand,
            "declared_targeting": targeting,
            "creative_inputs": {"purpose": "direct_sell"},
            "audience_spec": {"panel_size": 100},
        },
        "report": (report or _report()).to_dict() if status == "complete" else None,
    }
    (rd / "run.json").write_text(json.dumps(payload))
    if with_replay:
        (rd / "replay_report.json").write_text(
            json.dumps((report or _report()).to_dict())
        )
    return rd


@pytest.fixture
def env(tmp_path: Path):
    """A whole server pointed at a temp world: two finished runs, no sessions."""
    runs_root = tmp_path / "runs"
    sessions_root = tmp_path / "sessions"
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "creative.png").write_bytes(_PNG)
    _write_run(runs_root, account="demo", brand="hw", run_id=REAL_RUN_ID,
               label=REAL_LABEL, targeting=REAL_TARGETING,
               asset_rel="assets/creative.png")
    _write_run(runs_root, account="demo", brand="hw",
               run_id="20260609_232052_seed71_proski_cereal", label=DECOY_LABEL,
               asset_rel="assets/creative.png")
    app = create_app(runs_root=runs_root, sessions_root=sessions_root,
                     base_dir=tmp_path, auth=demo_auth())
    client = sign_in(TestClient(app))
    client.__dict__["runs_root"] = runs_root
    client.__dict__["sessions_root"] = sessions_root
    return client


def _start(client: TestClient) -> str:
    runs = discover_runs(client.__dict__["runs_root"])
    real = next(r for r in runs if r.run_id == REAL_RUN_ID)
    decoy = next(r for r in runs if r.run_id != REAL_RUN_ID)
    resp = client.post("/sessions", data={
        "contact": "Priya", "company": "Acme Nutrition",
        "real_key": real.key, "decoy_key": decoy.key, "ad_label": "whey q3",
    }, follow_redirects=False)
    assert resp.status_code == 303, resp.text
    return resp.headers["location"].rsplit("/", 1)[-1]


_PREDICTION = {
    "outcome": "It flopped — CPA was double target",
    "outcome_metrics": "CTR 0.4%, ROAS 0.8",
    "predicted_verdict": "REBUILD",
    "predicted_problems": "Too much text; no price",
    "predicted_working": "The pack shot",
}


# ---- the gate ---------------------------------------------------------


def test_reveal_is_refused_until_the_prediction_is_captured(env) -> None:
    sid = _start(env)

    blocked = env.get(f"/sessions/{sid}/reveal")
    assert blocked.status_code == 403
    assert "prediction" in blocked.text.lower()
    # And nothing leaked through the page that refused.
    assert REAL_LABEL not in blocked.text
    assert "ITERATE" not in blocked.text

    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    assert env.get(f"/sessions/{sid}/reveal").status_code == 200
    print("  reveal blocked before prediction, open after ✓")


def test_the_report_url_is_gated_too_not_just_the_page_linking_to_it(env) -> None:
    """The gate has to sit on the resource. /sessions/<id>/report/A is a
    guessable URL, and a gate that only covers the reveal page is not a gate —
    an operator who bookmarked the report from a previous session walks
    straight past it."""
    sid = _start(env)
    for slot in ("A", "B"):
        resp = env.get(f"/sessions/{sid}/report/{slot}")
        assert resp.status_code == 403, f"slot {slot} served before prediction"
        assert "ITERATE" not in resp.text
        assert "No price anywhere on the frame" not in resp.text

    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    assert env.get(f"/sessions/{sid}/report/A").status_code == 200
    print("  report slots gated at the resource, not the link ✓")


def test_react_form_is_gated_and_reaction_cannot_be_stored_blind(env) -> None:
    sid = _start(env)
    assert env.get(f"/sessions/{sid}/react").status_code == 403
    resp = env.post(f"/sessions/{sid}/react", data={
        "verdict_match": "yes", "diagnosis_overlap": "high",
        "anything_new": "yes", "run_differently": "yes",
        "pilot_live_ad": "yes", "decoy_pick": "A",
    })
    assert resp.status_code == 403
    assert env.get(f"/sessions/{sid}/export").json()["reaction"] is None
    print("  reaction refused while the prediction is missing ✓")


def test_prediction_cannot_be_rewritten_after_the_reveal(env) -> None:
    """The captured prediction is the only one taken blind. Once the read has
    been shown, an edit would silently replace evidence with hindsight."""
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    env.get(f"/sessions/{sid}/reveal")

    rewrite = dict(_PREDICTION, predicted_problems="Actually it was the price")
    resp = env.post(f"/sessions/{sid}/predict", data=rewrite,
                    follow_redirects=False)
    assert resp.status_code == 409
    stored = env.get(f"/sessions/{sid}/export").json()
    assert stored["prediction"]["predicted_problems"] == "Too much text; no price"
    print("  post-reveal prediction edit refused ✓")


def test_reveal_timestamp_measures_the_first_view_not_a_reload(env) -> None:
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    env.get(f"/sessions/{sid}/reveal")
    first = env.get(f"/sessions/{sid}/export").json()["revealed_at"]
    assert first is not None
    env.get(f"/sessions/{sid}/reveal")
    assert env.get(f"/sessions/{sid}/export").json()["revealed_at"] == first
    print("  revealed_at stamped once ✓")


# ---- the decoy --------------------------------------------------------


def test_blinded_report_carries_no_way_to_identify_the_ad(env) -> None:
    """Every field that names the ad, checked against the SAME page a contact
    sees. The diagnosis must survive in full — that is what they are judging."""
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    page = env.get(f"/sessions/{sid}/report/A").text

    for leak in (REAL_LABEL, DECOY_LABEL, REAL_RUN_ID, REAL_TARGETING,
                 "proski", "muscleblaze"):
        assert leak.lower() not in page.lower(), f"blinded read leaks {leak!r}"
    assert "data:image" not in page, "blinded read embeds the creative"
    assert "Read A" in page
    # Sanity: an UNBLINDED render of the same run does leak all of it, so the
    # assertions above are testing the blinding and not a fixture that never
    # had anything to leak.
    plain = env.get(f"/runs/demo/hw/{REAL_RUN_ID}").text
    assert REAL_LABEL in plain and REAL_RUN_ID in plain
    assert REAL_TARGETING in plain and "data:image" in plain

    # The diagnosis itself is intact — blinding the identity must not blind
    # the content, or there is nothing left to tell the two reads apart by.
    assert "No price anywhere on the frame" in page
    assert "ITERATE" in page
    print("  blinded read: identity stripped, diagnosis intact ✓")


def test_the_honesty_surfaces_survive_blinding(env) -> None:
    """Blinding strips identity, never a guardrail. The verdict caveat and the
    model-inferred disclaimer are the two a prospect must not read without."""
    from html import escape

    from agent.read_model import DISCLAIMER, VERDICT_CAVEAT

    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    page = env.get(f"/sessions/{sid}/report/A").text
    # Escaped, because the renderer escapes: VERDICT_CAVEAT contains an
    # apostrophe, and asserting the raw string would pass only by accident.
    assert escape(VERDICT_CAVEAT, quote=True) in page
    assert escape(DISCLAIMER, quote=True) in page
    print("  verdict caveat + disclaimer survive the blinding ✓")


def test_which_slot_is_real_is_randomised_not_always_a(env) -> None:
    """If the real read is always Read A the blinding is decorative — the
    operator's own tell, or a contact sitting a second session, defeats it."""
    store = SessionStore(env.__dict__["sessions_root"])
    seen = set()
    for i in range(2):
        s = store.create(contact="c", company=f"co{i}", ad_label="",
                         real_key="a/b/real", decoy_key="a/b/decoy",
                         rng=random.Random(i))
        seen.add(s.slot_of_real())
    assert seen == {"A", "B"}, f"real read never moved slots: {seen}"
    print("  slot assignment randomised ✓")


def test_decoy_caught_is_derived_from_the_pick_never_self_reported(env) -> None:
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    env.get(f"/sessions/{sid}/reveal")
    real_slot = env.get(f"/sessions/{sid}/export").json()["slot_map"]
    real_key = env.get(f"/sessions/{sid}/export").json()["real_key"]
    correct = next(s for s, k in real_slot.items() if k == real_key)
    wrong = next(s for s in ("A", "B") if s != correct)

    base = {"verdict_match": "yes", "diagnosis_overlap": "high",
            "anything_new": "yes", "run_differently": "yes",
            "pilot_live_ad": "yes"}
    env.post(f"/sessions/{sid}/react", data={**base, "decoy_pick": correct},
             follow_redirects=False)
    assert env.get(f"/sessions/{sid}/export").json()["decoy_caught"] is True

    env.post(f"/sessions/{sid}/react", data={**base, "decoy_pick": wrong},
             follow_redirects=False)
    assert env.get(f"/sessions/{sid}/export").json()["decoy_caught"] is False

    env.post(f"/sessions/{sid}/react", data={**base, "decoy_pick": ""},
             follow_redirects=False)
    assert env.get(f"/sessions/{sid}/export").json()["decoy_caught"] is None
    print("  decoy_caught derived from the pick ✓")


def test_a_cross_category_decoy_is_refused(env) -> None:
    """A decoy from another category is distinguishable without reading either
    diagnosis — the report footer even prints the category — so 'they caught
    it' would record discriminating power the read has not demonstrated.
    docs/v3_discriminant_check.md made the same point about comparing reads
    with different inferred audiences: the valid pair was control vs TWT.

    Enforced in the route, not the picker: the form filters for convenience
    and a direct POST ignores it.
    """
    runs_root = env.__dict__["runs_root"]
    _write_run(runs_root, account="demo", brand="cafe",
               run_id="20260712_101010_seed71_starbucks_pause",
               label="Starbucks Pause Button", category="coffee")
    runs = discover_runs(runs_root)
    whey = next(r for r in runs if r.run_id == REAL_RUN_ID)
    coffee = next(r for r in runs if r.category == "coffee")

    resp = env.post("/sessions", data={
        "contact": "P", "company": "C",
        "real_key": whey.key, "decoy_key": coffee.key,
    })
    assert resp.status_code == 400
    assert "different category" in resp.text.lower()

    # Same category still works.
    same = next(r for r in runs if r.category == whey.category
                and r.key != whey.key)
    ok = env.post("/sessions", data={
        "contact": "P", "company": "C",
        "real_key": whey.key, "decoy_key": same.key,
    }, follow_redirects=False)
    assert ok.status_code == 303
    print("  cross-category decoy refused, same-category accepted ✓")


def test_the_picker_offers_a_category_for_each_read(env) -> None:
    """The server-side refusal is the mechanism; the form still has to let the
    operator pick a valid pair without guessing."""
    page = env.get("/operator").text
    assert 'data-category="health_wellness_nutrition"' in page
    print("  picker carries the category per read ✓")


def test_a_session_cannot_use_the_same_read_twice(env) -> None:
    runs = discover_runs(env.__dict__["runs_root"])
    key = runs[0].key
    resp = env.post("/sessions", data={
        "contact": "P", "company": "C", "real_key": key, "decoy_key": key,
    })
    assert resp.status_code == 400
    assert "different ad" in resp.text.lower()
    print("  same-run decoy refused ✓")


# ---- run discovery + rendering ----------------------------------------


def test_discovery_omits_runs_that_carry_no_report(tmp_path: Path) -> None:
    """A committed-but-crashed run has a run.json and no Report;
    build_read_model raises on it by design. Offering it in the picker moves
    that failure to the middle of a session."""
    runs_root = tmp_path / "runs"
    _write_run(runs_root, account="a", brand="b", run_id="done", label="Done")
    _write_run(runs_root, account="a", brand="b", run_id="crashed",
               label="Crashed", status="committed")
    _write_run(runs_root, account="a", brand="b", run_id="recovered",
               label="Recovered", status="committed", with_replay=True)

    ids = {r.run_id for r in discover_runs(runs_root)}
    assert ids == {"done", "recovered"}, ids
    assert next(r for r in discover_runs(runs_root)
                if r.run_id == "recovered").source == "replay_report.json"
    print("  discovery: report-bearing runs only, replay included ✓")


def test_run_keys_cannot_escape_the_runs_root(tmp_path: Path) -> None:
    """The escape has to be a REACHABLE one, or the test proves nothing.

    A traversal key that lands on a directory with no run.json is rejected by
    the existence check further down, whatever the containment guard does. So
    this plants a real run.json outside runs_root and aims a three-segment key
    straight at it — the one shape that is served if containment is dropped.
    """
    runs_root = tmp_path / "runs"
    _write_run(runs_root, account="a", brand="b", run_id="r", label="R")
    outside = tmp_path / "secret" / "x"
    outside.mkdir(parents=True)
    (outside / "run.json").write_text("{}")

    assert resolve_run(runs_root, "a/b/r") is not None
    assert resolve_run(runs_root, "../secret/x") is None, "escaped runs_root"
    for bad in ("a/../../secret", "a/b", "a/b/r/extra", "", "/etc/passwd"):
        assert resolve_run(runs_root, bad) is None, bad
    print("  path traversal refused, on a key that would otherwise resolve ✓")


def test_report_route_refuses_a_run_with_no_read(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    _write_run(runs_root, account="a", brand="b", run_id="crashed",
               label="Crashed", status="committed")
    client = sign_in(TestClient(create_app(runs_root=runs_root,
                                           sessions_root=tmp_path / "s",
                                           base_dir=tmp_path,
                                           auth=demo_auth())))
    resp = client.get("/runs/a/b/crashed")
    assert resp.status_code == 409
    assert "replay_synthesis" in resp.text
    print("  crashed run fails loudly, never blank ✓")


def test_blind_read_model_leaves_the_diagnosis_untouched() -> None:
    """Unit-level companion to the page test: the blinding must be surgical."""
    from agent.read_model import ReadModel

    model = ReadModel(run_id="run_x", run_dir=Path("."), report=_report(),
                      report_source="run.json", asset_label=REAL_LABEL,
                      asset_path=Path("assets/x.png"),
                      declared_targeting=REAL_TARGETING,
                      declared_audience=REAL_TARGETING,
                      decision_name="ITERATE", headline="11% would buy")
    blinded = blind_read_model(model, "B")

    assert blinded.asset_label == "Read B"
    assert blinded.asset_path is None
    assert blinded.run_id == "read-B"
    assert blinded.declared_targeting == "" and blinded.declared_audience == ""
    # Untouched:
    assert blinded.report is model.report
    assert blinded.decision_name == "ITERATE"
    assert blinded.headline == "11% would buy"
    print("  blind_read_model replaces identity fields only ✓")


# ---- storage ----------------------------------------------------------


def test_session_records_never_land_inside_a_run_directory(env) -> None:
    """Session records hold a contact's confidential outcomes. runs/ is shared,
    synced and rendered from; these belong outside it (and are gitignored)."""
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    runs_root = env.__dict__["runs_root"]
    sessions_root = env.__dict__["sessions_root"]

    assert (sessions_root / f"{sid}.json").exists()
    assert sessions_root.resolve() not in runs_root.resolve().parents
    leaked = [p for p in runs_root.rglob("*")
              if p.is_file() and "flopped" in p.read_text(errors="ignore")]
    assert not leaked, f"prediction text found under runs/: {leaked}"
    print("  session data stored outside runs/ ✓")


def test_export_carries_the_engine_half_of_the_capture_row(env) -> None:
    """brand_manager_sessions.md's table pairs their predicted verdict + pains
    against the ENGINE's verdict + top pains. An export with only the human
    half needs a hand-join against run.json before any row can be read."""
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    row = env.get(f"/sessions/{sid}/export").json()

    engine = row["engine"]
    assert engine["available"] is True
    assert engine["decision"] == "ITERATE"
    assert engine["trust"] == "DIRECTIONAL"
    assert engine["verdict"] == "MIXED" and engine["confidence"] == 76
    assert engine["asset_label"] == REAL_LABEL
    assert engine["top_pains"][0]["pain"] == "No price anywhere on the frame"
    assert "Put the price on the creative" in engine["top_changes"]
    # Both halves in one row.
    assert row["prediction"]["predicted_verdict"] == "REBUILD"
    print("  export carries both halves of the capture row ✓")


def test_export_survives_a_read_that_has_gone_missing(env) -> None:
    sid = _start(env)
    env.post(f"/sessions/{sid}/predict", data=_PREDICTION, follow_redirects=False)
    (env.__dict__["runs_root"] / "demo" / "hw" / REAL_RUN_ID
     / "run.json").unlink()
    row = env.get(f"/sessions/{sid}/export").json()
    assert row["engine"]["available"] is False
    assert row["prediction"] is not None, "human half lost with the engine half"
    print("  export degrades to the human half rather than 500ing ✓")


def test_bad_session_id_is_rejected_not_used_as_a_path(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s")
    from server.sessions import SessionError
    for bad in ("../etc/passwd", "a/b", "A" * 100, ""):
        with pytest.raises(SessionError):
            store.load(bad)
    print("  session id validated before it touches the filesystem ✓")


def test_store_round_trips_a_full_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s")
    s = store.create(contact="Priya", company="Acme", ad_label="whey",
                     real_key="a/b/real", decoy_key="a/b/decoy")
    s.set_prediction(_PREDICTION)
    s.mark_revealed()
    s.set_reaction({"decoy_pick": s.slot_of_real(), "verdict_match": "yes"})
    store.save(s)

    back = store.load(s.session_id)
    assert back.prediction["outcome"] == _PREDICTION["outcome"]
    assert back.revealed_at == s.revealed_at
    assert back.decoy_caught() is True
    assert back.stage == "done"
    assert [x.session_id for x in store.list()] == [s.session_id]
    print("  session round-trips through disk ✓")


def test_require_prediction_raises_the_typed_error() -> None:
    store = SessionStore(Path("/nonexistent"))  # never written to
    from server.sessions import Session
    s = Session(session_id="x", contact="c", company="co", ad_label="",
                real_key="a/b/r", decoy_key="a/b/d",
                slot_map={"A": "a/b/r", "B": "a/b/d"})
    with pytest.raises(PredictionMissing):
        s.require_prediction()
    with pytest.raises(PredictionMissing):
        s.mark_revealed()
    print("  typed refusal, not a bare bool ✓")


# ---- the route map (P3) -----------------------------------------------


def test_a_read_answers_on_both_its_names(env) -> None:
    """`/reads/...` is the name a client-facing read should have; `/runs/...`
    stays because it is stored inside session records, sits in bookmarks, and
    is what every existing caller sends.

    Two registrations of one handler, not a redirect: a redirect would change
    the status code and the body every one of those callers gets back.
    """
    key = f"demo/hw/{REAL_RUN_ID}"
    new = env.get(f"/reads/{key}")
    old = env.get(f"/runs/{key}")

    assert new.status_code == old.status_code == 200
    assert new.text == old.text, "the two names render differently"
    assert REAL_LABEL in new.text
    print("  /reads/... and /runs/... are byte-identical ✓")


def test_the_product_surface_is_scoped_to_one_account(env) -> None:
    """`internal/*` is our own smoke-test exhaust — 20 runs of `cmf_smoke` and
    `default` on the real disk. In front of a brand manager that makes the
    product look like a scratch pad, so the product list shows `demo` only.
    """
    runs_root = env.__dict__["runs_root"]
    _write_run(runs_root, account="internal", brand="cmf_smoke",
               run_id="20260101_000000_smoke", label="Smoke test 3")

    everything = {r.key for r in discover_runs(runs_root)}
    scoped = {r.key for r in discover_runs(runs_root, account="demo")}

    assert "internal/cmf_smoke/20260101_000000_smoke" in everything
    assert scoped and scoped < everything
    assert not any(k.startswith("internal/") for k in scoped)
    print(f"  {len(everything)} runs on disk, {len(scoped)} in the product list ✓")


def test_scoping_is_filing_and_not_a_permission(env) -> None:
    """The intended NON-guarantee, pinned so nobody later 'fixes' it into a
    404 and calls that security.

    One shared password means one trust level. A signed-in browser that types
    an `internal/...` URL gets the read. If that ever needs to stop being
    true, the answer is real per-account accounts, not a filter on a list.
    """
    runs_root = env.__dict__["runs_root"]
    _write_run(runs_root, account="internal", brand="cmf_smoke",
               run_id="20260101_000000_smoke", label="Smoke test 3")

    listed = env.get("/operator").text
    assert "Smoke test 3" in listed, "the operator console is not scoped"

    direct = env.get("/reads/internal/cmf_smoke/20260101_000000_smoke")
    assert direct.status_code == 200, "a signed-in reader was refused a read"
    print("  scoping hides a run from a list, and gates nothing ✓")
