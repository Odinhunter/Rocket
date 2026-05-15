"""Phase 0 offline test: the entity model (Account -> BrandProfile ->
DispositionLibrary / SavedAudience, and AudienceSpec) round-trips through
to_dict / from_dict AND through filesystem save / load. AudienceSpec.validate
enforces the per-run disposition cap, context-envelope bounds, and panel ceiling.

Run: python tests/test_entities_roundtrip.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.entities import (
    AUDIENCE_DISPOSITION_CAP,
    Account,
    AudienceSpec,
    BrandProfile,
    DispositionLibrary,
    SavedAudience,
)
from agent.telemetry import RUNS_DIR
from agent.vectors import (
    ChaosDistribution,
    ChaosProfile,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
    NamedContext,
    NamedDisposition,
)

_TEST_ACCOUNT = "_test_entities_acct"
_TEST_BRAND = "_test_entities_brand"


def _chaos_distribution() -> ChaosDistribution:
    def profile(label: str, dv: str) -> ChaosProfile:
        return ChaosProfile(
            label=label,
            vector=ChaosVector(
                decision_velocity=dv,
                suggestibility="medium",
                consistency="variable",
                risk_tolerance="balanced",
            ),
        )

    return ChaosDistribution(
        weighted=[
            (profile("impulsive", "impulsive"), 0.20),
            (profile("moderate", "moderate"), 0.55),
            (profile("deliberate", "deliberate"), 0.25),
        ]
    )


def _disposition(label: str) -> NamedDisposition:
    return NamedDisposition(
        label=label,
        vector=DispositionVector(
            category_relationship="regular",
            brand_stance="skeptical",
            price_orientation="value_calculator",
            decision_driver="function",
            category_involvement="high",
            prior_experience_valence="mixed",
            channel_behavior="quick_commerce",
            life_stage="early_career",
        ),
    )


def _context(label: str) -> NamedContext:
    return NamedContext(
        label=label,
        vector=ContextVector(
            attention_level="low",
            device_posture="commute",
            intent_state="killing_time",
            energy_state="drained",
            social_setting="public",
        ),
    )


def _audience_spec() -> AudienceSpec:
    return AudienceSpec(
        demographics=[
            DemographicPoint(
                gender="male",
                age_band="25_34",
                income_tier="upper_mid",
                geography="Bangalore / metro tier-1",
            )
        ],
        disposition_labels=["disp_a", "disp_b"],
        context_envelope=[_context("c1"), _context("c2"), _context("c3")],
        chaos_distribution=_chaos_distribution(),
        panel_size=200,
    )


def _cleanup() -> None:
    path = RUNS_DIR / _TEST_ACCOUNT
    if path.exists():
        shutil.rmtree(path)


def test_audience_spec_roundtrip() -> None:
    spec = _audience_spec()
    spec.validate()
    spec2 = AudienceSpec.from_dict(spec.to_dict())
    assert spec.to_dict() == spec2.to_dict(), "AudienceSpec round-trip mismatch"
    print("  OK  AudienceSpec round-trip")


def test_audience_spec_rejects_too_many_dispositions() -> None:
    spec = _audience_spec()
    spec.disposition_labels = [f"d{i}" for i in range(AUDIENCE_DISPOSITION_CAP + 1)]
    try:
        spec.validate()
    except ValueError as e:
        assert "per-run cap" in str(e)
        print("  OK  AudienceSpec rejects > cap dispositions:", e)
        return
    raise AssertionError("AudienceSpec.validate should reject > cap dispositions")


def test_audience_spec_rejects_bad_context_envelope() -> None:
    spec = _audience_spec()
    spec.context_envelope = [_context("only_one")]  # < 3
    try:
        spec.validate()
    except ValueError as e:
        assert "context_envelope" in str(e)
        print("  OK  AudienceSpec rejects a too-small context envelope:", e)
        return
    raise AssertionError("AudienceSpec.validate should reject < 3 contexts")


def test_audience_spec_rejects_oversized_panel() -> None:
    spec = _audience_spec()
    spec.panel_size = 500
    try:
        spec.validate()
    except ValueError as e:
        assert "panel_size" in str(e)
        print("  OK  AudienceSpec rejects panel_size over the ceiling:", e)
        return
    raise AssertionError("AudienceSpec.validate should reject panel_size > 200")


def test_entities_filesystem_roundtrip() -> None:
    _cleanup()
    try:
        account = Account(account_id=_TEST_ACCOUNT, name="Test Co")
        account.validate()
        account.save()
        assert Account.load(_TEST_ACCOUNT).to_dict() == account.to_dict()

        brand = BrandProfile(
            brand_profile_id=_TEST_BRAND,
            account_id=_TEST_ACCOUNT,
            categories=["coffee"],
            library_id="lib_1",
            audience_ids=["aud_1"],
        )
        brand.validate()
        brand.save()
        assert (
            BrandProfile.load(_TEST_ACCOUNT, _TEST_BRAND).to_dict() == brand.to_dict()
        )

        library = DispositionLibrary(
            library_id="lib_1",
            brand_profile_id=_TEST_BRAND,
            account_id=_TEST_ACCOUNT,
            dispositions=[_disposition("disp_a"), _disposition("disp_b")],
        )
        library.validate()
        library.save()
        loaded_lib = DispositionLibrary.load(_TEST_ACCOUNT, _TEST_BRAND)
        assert loaded_lib.to_dict() == library.to_dict()
        # resolve() pulls the right dispositions back out, in order.
        resolved = loaded_lib.resolve(["disp_b", "disp_a"])
        assert [d.label for d in resolved] == ["disp_b", "disp_a"]

        audience = SavedAudience(
            audience_id="aud_1",
            name="Cold traffic — coffee",
            brand_profile_id=_TEST_BRAND,
            account_id=_TEST_ACCOUNT,
            spec=_audience_spec(),
        )
        audience.validate()
        audience.save()
        assert (
            SavedAudience.load(_TEST_ACCOUNT, _TEST_BRAND, "aud_1").to_dict()
            == audience.to_dict()
        )
        print("  OK  Account/BrandProfile/Library/SavedAudience filesystem round-trip")
    finally:
        _cleanup()


def test_library_rejects_duplicate_labels() -> None:
    library = DispositionLibrary(
        library_id="lib_dup",
        brand_profile_id=_TEST_BRAND,
        account_id=_TEST_ACCOUNT,
        dispositions=[_disposition("dup"), _disposition("dup")],
    )
    try:
        library.validate()
    except ValueError as e:
        assert "duplicate" in str(e)
        print("  OK  DispositionLibrary rejects duplicate labels:", e)
        return
    raise AssertionError("DispositionLibrary.validate should reject duplicate labels")


def main() -> None:
    print("=== entities round-trip smoke ===")
    test_audience_spec_roundtrip()
    test_audience_spec_rejects_too_many_dispositions()
    test_audience_spec_rejects_bad_context_envelope()
    test_audience_spec_rejects_oversized_panel()
    test_entities_filesystem_roundtrip()
    test_library_rejects_duplicate_labels()
    print("PASS — entity model is locked.")


if __name__ == "__main__":
    main()
