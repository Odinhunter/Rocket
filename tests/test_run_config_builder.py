"""Offline tests for the shared RunConfig seam (`agent.config.build_run_config`).

batch_run assembles a RunConfig from argparse; the operator tool assembles one
from an upload + form fields. Both call build_run_config so the two surfaces
cannot drift — and the load-bearing test here is the CLI pin below, not the
happy-path builder test.

Why the CLI pin matters: every knob the builder takes has a DEFAULT. Dropping
`marketer_led=args.marketer_led` from batch_run's call raises no error — it
silently becomes False, changing panel composition on every future run. A test
that only calls build_run_config directly with hand-written kwargs cannot see
that; only driving the real argparse path can.

Run: python tests/test_run_config_builder.py
"""

from __future__ import annotations

import atexit
import dataclasses
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import (
    DEFAULT_PURPOSE,
    build_run_config,
    default_asset_label,
    load_audience_spec,
)
from agent.entities import AudienceSpec
from agent.vectors import (
    ChaosDistribution,
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    NamedContext,
)

# A real temp dir outside the repo, torn down at interpreter exit. atexit rather
# than the main() runner below, so cleanup also happens under pytest (which calls
# the test functions directly and never reaches main()) — otherwise these
# scratch files accumulate in the working tree.
_TMP = Path(tempfile.mkdtemp(prefix="rocket_run_config_builder_"))
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)


def _spec_dict() -> dict:
    return AudienceSpec(
        demographics=[DemographicPoint(
            gender="male", age_min=25, age_max=44,
            income_lpa_min=7.0, income_lpa_max=40.0, geography="metro",
        )],
        disposition_labels=["enthusiast_macros_lifter", "aspirant_clean_label"],
        context_envelope=[NamedContext(
            label="commute",
            vector=ContextVector(
                attention_level="low", device_posture="commute",
                intent_state="killing_time", energy_state="drained",
                social_setting="public",
            ),
        )],
        chaos_distribution=ChaosDistribution(weighted=[(
            ChaosProfile(label="moderate", vector=ChaosVector(
                decision_velocity="moderate", suggestibility="medium",
                consistency="variable", risk_tolerance="balanced",
            )), 1.0,
        )]),
        panel_size=30,
    ).to_dict()


def _asset(name: str = "mb_biozyme_ad.png") -> Path:
    """A stand-in asset file. build_run_config deliberately does NOT validate
    the asset (RunService.prepare does), so the bytes are irrelevant — but
    batch_run.main() checks existence before building, so the file must exist."""
    p = _TMP / name
    p.write_bytes(b"")
    return p


# ---- load_audience_spec: instance / dict / path ----

def test_load_audience_spec_three_forms() -> None:
    data = _spec_dict()
    from_dict = load_audience_spec(data)

    path = _TMP / "spec.json"
    import json
    path.write_text(json.dumps(data))
    from_path = load_audience_spec(path)
    from_str = load_audience_spec(str(path))
    from_instance = load_audience_spec(from_dict)

    assert from_instance is from_dict, "an AudienceSpec must pass through unchanged"
    for other in (from_path, from_str):
        assert other.to_dict() == from_dict.to_dict()
    print("  OK  load_audience_spec accepts an instance, a dict, and a path")


def test_default_asset_label() -> None:
    assert default_asset_label("assets/mb_biozyme_ad.png") == "Mb Biozyme Ad"
    assert default_asset_label(Path("/x/plix_noceleb_ad.jpg")) == "Plix Noceleb Ad"
    print("  OK  default_asset_label makes a filename readable")


def test_asset_label_falls_back_to_filename() -> None:
    cfg = build_run_config(
        asset_path=_asset(), audience_spec=_spec_dict(),
        category="health_wellness_nutrition",
    )
    assert cfg.asset.label == "Mb Biozyme Ad", cfg.asset.label

    explicit = build_run_config(
        asset_path=_asset(), audience_spec=_spec_dict(),
        category="health_wellness_nutrition", asset_label="MuscleBlaze Whey",
    )
    assert explicit.asset.label == "MuscleBlaze Whey"
    print("  OK  asset_label defaults to the filename, an explicit label wins")


def test_builder_defaults_are_the_conservative_ones() -> None:
    """The defaults a caller gets by omission must stay the safe ones: funnel
    OFF (v3 D4 — heuristic_v1 is unfitted), marketer_led OFF (legacy runs stay
    byte-unchanged), purpose = direct_sell."""
    cfg = build_run_config(
        asset_path=_asset(), audience_spec=_spec_dict(),
        category="health_wellness_nutrition",
    )
    assert cfg.funnel_enabled is False, "the unfitted funnel must stay off by default"
    assert cfg.marketer_led is False
    assert cfg.tail_fraction == 0.0
    assert cfg.creative_inputs.purpose == DEFAULT_PURPOSE
    assert cfg.baseline_funnel is None
    assert cfg.segment_granularity == "disposition_chaos_band"
    print("  OK  omitted knobs resolve to the conservative defaults")


def test_creative_inputs_are_packed() -> None:
    cfg = build_run_config(
        asset_path=_asset(), audience_spec=_spec_dict(),
        category="health_wellness_nutrition",
        primary_text="20g protein per scoop", headline="Fuel the work",
        offer="₹2,699, 20% off", purpose="cold_hook",
    )
    ci = cfg.creative_inputs
    assert (ci.primary_text, ci.headline, ci.offer) == (
        "20g protein per scoop", "Fuel the work", "₹2,699, 20% off",
    )
    assert ci.purpose == "cold_hook"
    assert cfg.provided_inputs() == ["ad_copy", "offer"]
    print("  OK  ad copy + offer + purpose reach CreativeInputs")


def test_baseline_funnel_accepts_dict_or_path() -> None:
    import json
    fp = _TMP / "funnel.json"
    rates = {"stop_rate": 0.1, "click_rate": 0.02}
    fp.write_text(json.dumps(rates))

    from_path = build_run_config(
        asset_path=_asset(), audience_spec=_spec_dict(),
        category="health_wellness_nutrition", baseline_funnel=fp,
    )
    from_dict = build_run_config(
        asset_path=_asset(), audience_spec=_spec_dict(),
        category="health_wellness_nutrition", baseline_funnel=rates,
    )
    assert from_path.baseline_funnel == rates == from_dict.baseline_funnel
    print("  OK  baseline_funnel loads from a path or passes a dict through")


def test_builder_does_not_validate_the_asset() -> None:
    """Validation belongs to RunService.prepare (which calls config.validate()
    first thing), so an upload fails the same way whoever submitted it. The
    builder accepting a missing path is deliberate, not an oversight."""
    cfg = build_run_config(
        asset_path="does/not/exist.png", audience_spec=_spec_dict(),
        category="health_wellness_nutrition",
    )
    assert cfg.asset.image_path == "does/not/exist.png"
    try:
        cfg.validate()
    except ValueError as e:
        assert "not found" in str(e), e
    else:
        raise AssertionError("validate() should reject a missing asset")
    print("  OK  the builder defers asset validation to validate()")


# ---- THE ANTI-DRIFT PIN: the real argparse path ----

def test_cli_path_builds_every_field() -> None:
    """Drive batch_run.main() with a full argument set and assert the RunConfig
    it hands to RunService. This is the guard that catches a kwarg dropped from
    batch_run's builder call — an omission that has a default and so raises
    nothing. prepare() is intercepted, so this test never spends.
    """
    import json

    import agent.run_service as run_service
    import batch_run

    spec_path = _TMP / "cli_spec.json"
    spec_path.write_text(json.dumps(_spec_dict()))
    asset = _asset("cli_asset.png")

    class _Stop(Exception):
        pass

    captured: dict = {}

    def _fake_prepare(config):
        captured["config"] = config
        raise _Stop()

    real_prepare = run_service.RunService.prepare
    real_argv = sys.argv
    run_service.RunService.prepare = staticmethod(_fake_prepare)
    batch_run.RunService.prepare = staticmethod(_fake_prepare)
    sys.argv = [
        "batch_run.py",
        "--asset", str(asset),
        "--asset-label", "MuscleBlaze Biozyme Performance Whey",
        "--audience-spec", str(spec_path),
        "--category", "health_wellness_nutrition",
        "--archetype", "unspecified",
        "--account", "demo",
        "--brand-profile", "health_wellness_demo",
        "--library-id", "health_wellness_nutrition_lib_v1",
        "--audience-id", "cold_traffic_v1",
        "--declared-targeting", "adults 25-44, metro tier-1",
        "--primary-text", "20g protein per scoop",
        "--headline", "Fuel the work",
        "--offer", "₹2,699",
        "--purpose", "cold_hook",
        "--seed", "71",
        "--max-concurrent", "100",
        "--segment-granularity", "disposition",
        "--tail-fraction", "0.1",
        "--marketer-led",
        "--funnel",
        "--yes",
    ]
    try:
        batch_run.main()
    except _Stop:
        pass
    else:
        raise AssertionError("RunService.prepare was never reached")
    finally:
        run_service.RunService.prepare = real_prepare
        batch_run.RunService.prepare = real_prepare
        sys.argv = real_argv

    cfg = captured["config"]
    expected = {
        "archetype": "unspecified",
        "category": "health_wellness_nutrition",
        "account_id": "demo",
        "brand_profile_id": "health_wellness_demo",
        "library_id": "health_wellness_nutrition_lib_v1",
        "audience_id": "cold_traffic_v1",
        "declared_targeting": "adults 25-44, metro tier-1",
        "seed": 71,
        "max_concurrent_agents": 100,
        "segment_granularity": "disposition",
        "tail_fraction": 0.1,
        "marketer_led": True,
        "funnel_enabled": True,
    }
    for field, want in expected.items():
        got = getattr(cfg, field)
        assert got == want, f"{field}: CLI produced {got!r}, expected {want!r}"

    assert cfg.asset.label == "MuscleBlaze Biozyme Performance Whey"
    assert cfg.creative_inputs.primary_text == "20g protein per scoop"
    assert cfg.creative_inputs.headline == "Fuel the work"
    assert cfg.creative_inputs.offer == "₹2,699"
    assert cfg.creative_inputs.purpose == "cold_hook"
    assert cfg.audience_spec is not None
    assert cfg.audience_spec.panel_size == 30

    # Every RunConfig field the CLI can set must appear above. If a new field is
    # added to RunConfig and wired into batch_run, this fails until it is pinned
    # here too — that is the point.
    covered = set(expected) | {
        "asset", "creative_inputs", "audience_spec", "baseline_funnel",
        # not settable from the CLI:
        "dispositions_per_run", "contexts_per_run", "seeds_per_cell", "mode",
        "protocol_version", "disposition_version", "model_versions",
        "temperatures", "efforts",
        # stamped by RunService.prepare once the panel is resolved, never by a
        # caller — see the §5.1 config freeze
        "panel_version",
    }
    unpinned = {f.name for f in dataclasses.fields(cfg)} - covered
    assert not unpinned, f"RunConfig fields not pinned by this test: {sorted(unpinned)}"
    print("  OK  the batch_run CLI path sets every field it is supposed to")


def main() -> None:
    print("=== RunConfig builder — the shared CLI/server seam ===")
    test_load_audience_spec_three_forms()
    test_default_asset_label()
    test_asset_label_falls_back_to_filename()
    test_builder_defaults_are_the_conservative_ones()
    test_creative_inputs_are_packed()
    test_baseline_funnel_accepts_dict_or_path()
    test_builder_does_not_validate_the_asset()
    test_cli_path_builds_every_field()
    print("PASS — the builder holds and the CLI path cannot drift silently.")


if __name__ == "__main__":
    main()
