"""Step-2 smoke test: RunConfig validates correctly and the multi-tenant
run_dir builds the expected paths.

Run: python tests/test_run_config.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import (
    RunConfig,
    AssetSpec,
    PROTOCOL_VERSION,
    DEFAULT_TEMPERATURES,
    DEFAULT_EFFORTS,
)
from agent.telemetry import (
    run_dir,
    runs_root,
    current_account_id,
    current_brand_profile_id,
)


def test_default_config_is_valid() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat Airdopes Prime 512"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    cfg.validate()
    assert cfg.total_agents() == 15
    assert cfg.protocol_version == PROTOCOL_VERSION
    assert cfg.model_versions["agent"] == "claude-sonnet-4-6"
    assert cfg.model_versions["l4"] == "claude-opus-4-7"
    print(f"  OK  default 5x3x1 = {cfg.total_agents()} agents")


def test_validate_rejects_over_ceiling() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="y"),
        archetype="a", category="c",
        dispositions_per_run=7, contexts_per_run=5, seeds_per_cell=10,
    )
    try:
        cfg.validate()
    except ValueError as e:
        assert "200" in str(e)
        print("  OK  >200 agents rejected:", e)
        return
    raise AssertionError("Should reject >200 agents")


def test_validate_rejects_too_many_dispositions() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="y"),
        archetype="a", category="c",
        dispositions_per_run=9,
    )
    try:
        cfg.validate()
    except ValueError as e:
        assert "7" in str(e)
        print("  OK  >7 dispositions rejected:", e)
        return
    raise AssertionError("Should reject >7 dispositions")


def test_validate_rejects_missing_asset() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/__nonexistent__.png", label="y"),
        archetype="a", category="c",
    )
    try:
        cfg.validate()
    except ValueError as e:
        assert "not found" in str(e)
        print("  OK  missing asset rejected:", e)
        return
    raise AssertionError("Should reject missing asset")


def test_validate_rejects_unsupported_extension() -> None:
    # dabur ad.webp exists; create a sibling stub-name with bad extension via tmp
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tf:
        tf.write(b"\x47\x49\x46\x38\x39\x61")  # GIF89a
        bogus_path = tf.name
    cfg = RunConfig(
        asset=AssetSpec(image_path=bogus_path, label="y"),
        archetype="a", category="c",
    )
    try:
        cfg.validate()
    except ValueError as e:
        assert "unsupported extension" in str(e)
        print("  OK  unsupported extension rejected:", e)
        return
    finally:
        Path(bogus_path).unlink(missing_ok=True)
    raise AssertionError("Should reject unsupported extension")


def test_validate_rejects_oversize_image() -> None:
    """A PNG larger than 3.93 MB will base64-encode past Anthropic's 5 MB."""
    import tempfile
    # 4.2 MB of zeros, named .png — extension check passes; size check fails.
    payload = b"\x00" * int(4.2 * 1024 * 1024)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(payload)
        big_path = tf.name
    cfg = RunConfig(
        asset=AssetSpec(image_path=big_path, label="y"),
        archetype="a", category="c",
    )
    try:
        cfg.validate()
    except ValueError as e:
        assert "5 MB" in str(e) and "post-base64" in str(e)
        print("  OK  oversize image rejected:", e)
        return
    finally:
        Path(big_path).unlink(missing_ok=True)
    raise AssertionError("Should reject oversize image")


def test_multi_tenant_run_dir() -> None:
    """With context vars set, run_dir returns the multi-tenant path."""
    current_account_id.set("internal")
    current_brand_profile_id.set("boat")
    p = run_dir("20260512_abc")
    assert p == runs_root() / "internal" / "boat" / "20260512_abc", f"unexpected {p}"
    assert p.is_absolute(), "a cwd-relative run dir is how the suite wrote into real runs/"
    print(f"  OK  multi-tenant run_dir: {p}")


def test_explicit_args_override_context_vars() -> None:
    current_account_id.set("internal")
    current_brand_profile_id.set("boat")
    p = run_dir("rid", account_id="acme", brand_profile_id="prod1")
    assert p == runs_root() / "acme" / "prod1" / "rid", f"unexpected {p}"
    print(f"  OK  explicit override: {p}")


def test_flat_fallback_when_unset() -> None:
    current_account_id.set(None)
    current_brand_profile_id.set(None)
    p = run_dir("rid")
    assert p == runs_root() / "rid", f"unexpected {p}"
    print(f"  OK  flat fallback: {p}")


def test_disposition_version_hash() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="y"),
        archetype="a", category="c",
    )
    pool = [("d1", "desc1"), ("d2", "desc2")]
    h1 = cfg.compute_disposition_version(pool)
    h2 = cfg.compute_disposition_version(pool)
    h3 = cfg.compute_disposition_version([("d1", "desc1"), ("d2", "DIFFERENT")])
    assert h1 == h2, "stable hash failed"
    assert h1 != h3, "hash should change with pool change"
    assert len(h1) == 12, "hash should be 12 chars"
    print(f"  OK  disposition_version hash: {h1}")


def test_to_dict_serializable() -> None:
    import json
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    s = json.dumps(cfg.to_dict())
    assert "sample_creative.png" in s
    assert PROTOCOL_VERSION in s
    assert "temperatures" in s
    assert "efforts" in s
    print("  OK  to_dict JSON-serializable")


def test_marketer_led_fields() -> None:
    base = dict(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    d = RunConfig(**base).to_dict()
    assert d["marketer_led"] is False and d["tail_fraction"] == 0.0, d
    d2 = RunConfig(**base, marketer_led=True, tail_fraction=0.15).to_dict()
    assert d2["marketer_led"] is True and d2["tail_fraction"] == 0.15, d2
    assert PROTOCOL_VERSION == "rocket-3.0.0-dev", PROTOCOL_VERSION
    print("  OK  marketer_led / tail_fraction serialize (protocol rocket-3.0.0-dev)")


def test_model_versions_backfills_missing_keys() -> None:
    """rocket-2.2.0: a pre-2.2 run.json config carries model_versions WITHOUT
    the assess/prescribe keys. RunConfig must backfill them from defaults (so
    replay/old-run loading doesn't KeyError), preserve stored overrides, and
    keep DEFAULT_MODEL_VERSIONS isolated."""
    from agent.config import DEFAULT_MODEL_VERSIONS
    legacy = {
        "agent": "claude-sonnet-4-6", "l2": "claude-sonnet-4-6",
        "l3": "claude-sonnet-4-6", "l4": "claude-opus-4-7",
        "target_id": "claude-opus-4-7", "render": "claude-sonnet-4-6",
    }
    c = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat"),
        archetype="unspecified", category="personal_audio",
        model_versions=dict(legacy),
    )
    assert c.model_versions["assess"] == DEFAULT_MODEL_VERSIONS["assess"]
    assert c.model_versions["prescribe"] == DEFAULT_MODEL_VERSIONS["prescribe"]
    assert c.model_versions["l4"] == "claude-opus-4-7"  # stored override wins
    assert "assess" not in legacy, "backfill must not mutate the caller's dict"
    print("  OK  model_versions backfills assess/prescribe from defaults (back-compat)")


def test_default_temperatures_match_advisor_schedule() -> None:
    """The 1.1.0 temperature schedule is load-bearing for verdict stability
    and L4 voice fidelity. Changing any of these is a methodology shift
    that requires re-validating the benchmark library — gate it with a
    test so a casual edit can't move the values silently.
    """
    expected = {
        "agent":     1.0,   # consumer voice diversity is the product
        "l2":        0.5,
        "l3":        0.5,
        "l4":        None,  # claude-opus-4-7 deprecated temperature
        "target_id": None,  # claude-opus-4-7 deprecated temperature
        # v3 word-cloud post-pass. 0.0 deliberately: it extracts vocabulary
        # that is already in the corpus and judges it, rather than generating
        # anything, so the same run must yield the same cloud. This layer reads
        # finished transcripts only — it cannot affect reaction calibration.
        "lexicon":   0.0,
    }
    assert DEFAULT_TEMPERATURES == expected, (
        f"DEFAULT_TEMPERATURES drift: expected {expected}, "
        f"got {DEFAULT_TEMPERATURES}"
    )
    print(f"  OK  DEFAULT_TEMPERATURES = {DEFAULT_TEMPERATURES}")


def test_temperatures_round_trip_through_to_dict() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    d = cfg.to_dict()
    assert d["temperatures"] == DEFAULT_TEMPERATURES
    # mutating the dict on the config doesn't leak back into the default
    cfg.temperatures["l4"] = 0.9
    assert DEFAULT_TEMPERATURES["l4"] is None, "DEFAULT_TEMPERATURES leaked"
    print("  OK  temperatures round-trip + default isolation")


def test_default_efforts_match_advisor_schedule() -> None:
    """The 1.3.0 effort schedule is load-bearing for target_id determinism;
    changing it requires re-validating the bru boundary case. Gate it with
    a test so a casual edit can't move the values silently.
    """
    expected = {
        "agent":     None,   # Sonnet, SDK default
        "l2":        None,
        "l3":        None,
        "l4":        None,   # Opus, deliberately SDK default for memo quality
        "target_id": "low",  # empirically 5/5 stable on bru
    }
    assert DEFAULT_EFFORTS == expected, (
        f"DEFAULT_EFFORTS drift: expected {expected}, got {DEFAULT_EFFORTS}"
    )
    print(f"  OK  DEFAULT_EFFORTS = {DEFAULT_EFFORTS}")


def test_efforts_round_trip_through_to_dict() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/sample_creative.png", label="Boat"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    d = cfg.to_dict()
    assert d["efforts"] == DEFAULT_EFFORTS
    # mutating the dict on the config doesn't leak back into the default
    cfg.efforts["target_id"] = "medium"
    assert DEFAULT_EFFORTS["target_id"] == "low", "DEFAULT_EFFORTS leaked"
    print("  OK  efforts round-trip + default isolation")


def main() -> None:
    print("=== run config smoke ===")
    test_default_config_is_valid()
    test_validate_rejects_over_ceiling()
    test_validate_rejects_too_many_dispositions()
    test_validate_rejects_missing_asset()
    test_validate_rejects_unsupported_extension()
    test_validate_rejects_oversize_image()
    test_multi_tenant_run_dir()
    test_explicit_args_override_context_vars()
    test_flat_fallback_when_unset()
    test_disposition_version_hash()
    test_to_dict_serializable()
    test_marketer_led_fields()
    test_model_versions_backfills_missing_keys()
    test_default_temperatures_match_advisor_schedule()
    test_temperatures_round_trip_through_to_dict()
    test_default_efforts_match_advisor_schedule()
    test_efforts_round_trip_through_to_dict()
    print("PASS — RunConfig + multi-tenant paths.")


if __name__ == "__main__":
    main()
