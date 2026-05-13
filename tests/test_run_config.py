"""Step-2 smoke test: RunConfig validates correctly and the multi-tenant
run_dir builds the expected paths.

Run: python tests/test_run_config.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import RunConfig, AssetSpec, PROTOCOL_VERSION
from agent.telemetry import (
    run_dir,
    current_account_id,
    current_brand_profile_id,
)


def test_default_config_is_valid() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat Airdopes Prime 512"),
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
        asset=AssetSpec(image_path="assets/boat_ad.png", label="y"),
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
        asset=AssetSpec(image_path="assets/boat_ad.png", label="y"),
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
    assert p == Path("runs/internal/boat/20260512_abc"), f"unexpected {p}"
    print(f"  OK  multi-tenant run_dir: {p}")


def test_explicit_args_override_context_vars() -> None:
    current_account_id.set("internal")
    current_brand_profile_id.set("boat")
    p = run_dir("rid", account_id="acme", brand_profile_id="prod1")
    assert p == Path("runs/acme/prod1/rid"), f"unexpected {p}"
    print(f"  OK  explicit override: {p}")


def test_flat_fallback_when_unset() -> None:
    current_account_id.set(None)
    current_brand_profile_id.set(None)
    p = run_dir("rid")
    assert p == Path("runs/rid"), f"unexpected {p}"
    print(f"  OK  flat fallback: {p}")


def test_disposition_version_hash() -> None:
    cfg = RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="y"),
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
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
        archetype="urban_indian_male_22_30",
        category="personal_audio",
    )
    s = json.dumps(cfg.to_dict())
    assert "boat_ad.png" in s
    assert "rocket-1.0.0" in s
    print("  OK  to_dict JSON-serializable")


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
    print("PASS — RunConfig + multi-tenant paths.")


if __name__ == "__main__":
    main()
