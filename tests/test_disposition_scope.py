"""§2.3 — a disposition declares the sub-category it was authored for, and
reuse outside it is a deliberate, visible act.

The failure this exists for was MEASURED, not imagined: a beauty-supplement
persona written for collagen/biotin — correct there — was applied unchanged to
a protein bar, and 43 of 100 persona cores carried its vocabulary before seeing
any ad. The panel arrived pre-loaded with the wrong product's language, which
contaminates the reaction at composition time, upstream of everything the read
reports.

⚠ The hardest thing to get right here is NOT the detection. It is that six of
seven dispositions in the shipped library — and every disposition in the other
four libraries — declare no scope at all. An advisory that fired on absence
would light up every run at once and be trained away in a day. Half the tests
below are about silence.

Offline. No API calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.panel import compute_panel_version  # noqa: E402
from agent.target_id import detect_out_of_scope_dispositions  # noqa: E402
from agent.vectors import DispositionVector, NamedDisposition  # noqa: E402


def _vector() -> DispositionVector:
    return DispositionVector(
        category_relationship="regular", brand_stance="skeptical",
        price_orientation="value_calculator", decision_driver="function",
        category_involvement="high", prior_experience_valence="mixed",
        channel_behavior="marketplace", life_stage="early_career",
    )


def _disp(label: str, authored_for: list[str] | None = None) -> NamedDisposition:
    return NamedDisposition(
        label=label, vector=_vector(), authored_for=list(authored_for or [])
    )


# ---- The measured case ----


def test_the_collagen_persona_is_flagged_on_a_protein_ad() -> None:
    """The exact reuse that was measured. `switcher_results_chaser` is a
    beauty-supplement persona — OZiva, Power Gummies, Plix collagen, biotin,
    Nykaa review density — and none of that is a protein bar."""
    pool = [
        _disp("switcher_results_chaser",
              ["collagen", "biotin", "hair supplement"]),
        _disp("pragmatist_protein_snacker"),
    ]
    warning = detect_out_of_scope_dispositions(
        pool, asset_label="twt_protein_bar",
        category="health_wellness_nutrition",
    )
    assert warning is not None, "the measured reuse must be flagged"
    assert [label for label, _ in warning.out_of_scope] == ["switcher_results_chaser"]
    assert warning.scoped_count == 1 and warning.total_count == 2, (
        "the advisory must report its own denominator — 1 of 2 dispositions "
        "declared a scope, and a reader cannot weigh the flag without that"
    )
    assert "collagen" in warning.message
    print("  the collagen persona is flagged on a protein ad ✓")


def test_the_collagen_persona_is_silent_on_a_collagen_ad() -> None:
    """On its home turf the same disposition is correct, and a guard that
    flagged it there would be flagging the library's intended use."""
    pool = [_disp("switcher_results_chaser", ["collagen", "biotin"])]
    assert detect_out_of_scope_dispositions(
        pool, asset_label="wn_collagen_ad",
        category="health_wellness_nutrition",
    ) is None
    # The category alone can carry the match too — scope words are matched
    # against the label AND the category, not the label only.
    assert detect_out_of_scope_dispositions(
        [_disp("x", ["nutrition"])], asset_label="untitled_upload",
        category="health_wellness_nutrition",
    ) is None
    print("  in-scope reuse stays silent ✓")


# ---- Silence: the half that decides whether this is usable ----


def test_an_unscoped_library_never_warns() -> None:
    """⚠ THE LOAD-BEARING TEST. Every disposition in every library ships with
    `authored_for == []`. If absence read as mismatch, the first run after this
    change would flag all seven consumer types in the health-wellness library
    and every one in the other four, and the row would be worthless before
    anyone had authored a single scope."""
    pool = [_disp("a"), _disp("b"), _disp("c")]
    assert detect_out_of_scope_dispositions(
        pool, asset_label="anything_at_all", category="any_category"
    ) is None, "an unscoped disposition must never read as out of scope"

    # And a MIXED pool reports only the scoped, non-matching one — the unscoped
    # siblings are not swept in alongside it.
    mixed = [_disp("scoped", ["collagen"]), _disp("unscoped_a"), _disp("unscoped_b")]
    warning = detect_out_of_scope_dispositions(
        mixed, asset_label="protein_bar", category="nutrition"
    )
    assert warning is not None
    assert [label for label, _ in warning.out_of_scope] == ["scoped"], \
        "unscoped dispositions were swept into the warning"
    assert warning.scoped_count == 1 and warning.total_count == 3
    print("  an unscoped library never warns; a mixed pool reports only the scoped ✓")


def test_scope_matching_respects_word_boundaries() -> None:
    """Substring matching on raw text would make "bar" match "barista" and
    "protein" match "proteinuria" — a guard that silently passes on a
    coincidence is worse than one that fires, because nobody re-checks a
    silent guard."""
    # "bar" must NOT be satisfied by "barista".
    warning = detect_out_of_scope_dispositions(
        [_disp("x", ["bar"])], asset_label="barista_blend_ad", category="coffee"
    )
    assert warning is not None, '"bar" must not match inside "barista"'

    # ...but the whole word, however it is punctuated, must match.
    for label in ("protein_bar_launch", "protein-bar launch", "PROTEIN BAR"):
        assert detect_out_of_scope_dispositions(
            [_disp("x", ["bar"])], asset_label=label, category="nutrition"
        ) is None, f"whole-word 'bar' should have matched {label!r}"

    # A multi-word scope matches as a phrase, not as loose tokens.
    assert detect_out_of_scope_dispositions(
        [_disp("x", ["hair supplement"])],
        asset_label="hair_serum_and_protein_supplement", category="nutrition",
    ) is not None, "'hair supplement' must not match 'hair ... supplement' apart"
    print("  scope matching is whole-word and phrase-exact ✓")


def test_any_one_declared_scope_is_enough() -> None:
    """`authored_for` is a list of alternatives, not a conjunction — a persona
    authored for "collagen / biotin / hair supplement" is in scope on any one
    of them."""
    pool = [_disp("x", ["collagen", "biotin", "hair supplement"])]
    assert detect_out_of_scope_dispositions(
        pool, asset_label="biotin_gummies_ad", category="nutrition"
    ) is None
    print("  any one declared scope puts a disposition in scope ✓")


# ---- Serialization, and the panel-version claim it rests on ----


def test_an_empty_scope_is_omitted_so_panel_versions_do_not_move() -> None:
    """⚠ Pins a claim made in `NamedDisposition.to_dict`, and the reason is a
    paid run. `compute_panel_version` digests these dicts. Emitting
    `"authored_for": []` unconditionally would shift the panel version of every
    brand on disk — announcing a composition change that did not happen, right
    when a before/after run has to be read. Scoping a disposition DOES move it,
    which is correct: the library really changed."""
    unscoped = _disp("x")
    assert "authored_for" not in unscoped.to_dict(), (
        "an empty scope must not appear in to_dict — it would move the panel "
        "version of every existing brand"
    )
    scoped = _disp("x", ["collagen"])
    assert scoped.to_dict()["authored_for"] == ["collagen"]

    # The version claim itself, end to end.
    from agent.entities import AudienceSpec
    from agent.vectors import (
        ChaosDistribution, ChaosProfile, ChaosVector, DemographicPoint,
        NamedContext,
    )

    chaos = ChaosDistribution(weighted=[(ChaosProfile(
        label="moderate",
        vector=ChaosVector(decision_velocity="moderate", suggestibility="medium",
                           consistency="variable", risk_tolerance="balanced"),
    ), 1.0)])

    def _version(dispositions):
        spec = AudienceSpec(
            demographics=[DemographicPoint(
                gender="any", age_min=25, age_max=34,
                income_lpa_min=7.0, income_lpa_max=40.0, geography="metro")],
            disposition_labels=[d.label for d in dispositions],
            context_envelope=[NamedContext.from_dict({
                "label": "commute_scroll",
                "vector": {"attention_level": "low", "device_posture": "commute",
                           "intent_state": "killing_time", "energy_state": "drained",
                           "social_setting": "public"}})],
            chaos_distribution=chaos,
            panel_size=10,
        )
        return compute_panel_version(
            spec, dispositions, category="nutrition",
            segment_granularity="disposition", seed=71,
        )

    before = _version([_disp("x")])
    assert _version([_disp("x")]) == before, "panel version is not deterministic"
    assert _version([_disp("x", ["collagen"])]) != before, (
        "scoping a disposition must move the panel version — it is a real "
        "change to the library and the run record should say so"
    )
    print("  empty scope omitted (versions stable); scoping moves the version ✓")


def test_scope_round_trips_and_is_validated() -> None:
    """A library is JSON on disk, so a field that does not survive from_dict is
    a field that silently vanishes on the next load."""
    scoped = _disp("x", ["collagen", "biotin"])
    assert NamedDisposition.from_dict(scoped.to_dict()).authored_for == \
        ["collagen", "biotin"]
    # Legacy dicts — every library on disk today — load as unscoped.
    legacy = scoped.to_dict()
    legacy.pop("authored_for")
    assert NamedDisposition.from_dict(legacy).authored_for == []

    for bad in ([""], ["   "], [None], [3]):
        try:
            _disp("x", bad).validate()
        except (ValueError, TypeError):
            continue
        raise AssertionError(f"validate() accepted a bad scope entry: {bad!r}")
    print("  scope round-trips, legacy loads unscoped, junk is rejected ✓")


def test_the_scope_warning_never_reaches_a_customer_surface() -> None:
    """⚠ THE USER'S CALL, 2026-08-06, and the reason is not squeamishness.

    That a consumer type was authored for another product is OUR library
    problem. Telling the buyer "one of these people was written for a different
    ad" invites them to discount the whole panel over a defect they cannot fix
    and did not cause — the same instinct that stripped eight qualifications off
    the read in `#37`. The fix is to re-author or drop the disposition, so this
    is an AUTHORING signal, not a caveat that travels with the run.

    So it lives on the CLI operator surface and in `preparation.json`, and it
    must appear on NO customer-facing renderer. This is a source-level check
    because that is the only thing that fails when someone wires it in later:
    the warning is usually absent from a rendered page anyway (it is None on an
    unscoped library), so asserting on output would pass whether or not the
    wiring existed."""
    repo = Path(__file__).resolve().parent.parent
    customer_surfaces = [
        repo / "agent" / "dashboard_html.py",   # the read — the only read surface
        repo / "agent" / "read_model.py",       # everything the read can show
        repo / "server" / "app_html.py",        # the app's own screens
    ]
    for path in customer_surfaces:
        source = path.read_text()
        for token in ("disposition_scope_warning", "DispositionScopeWarning"):
            assert token not in source, (
                f"{path.name} references {token} — the scope advisory is an "
                f"internal authoring signal and must not reach the customer. "
                f"If this is deliberate, it needs the user's say-so first."
            )
    # ...and it IS reachable where it belongs, or the check above is satisfied
    # by the feature simply not existing.
    assert "disposition_scope_warning" in (repo / "batch_run.py").read_text(), (
        "the operator surface no longer shows the advisory — then nothing does, "
        "and the absence check above is vacuous"
    )
    print("  the scope warning is operator-only and reaches no customer surface ✓")


def main() -> None:
    print("=== §2.3 disposition scope ===")
    test_the_collagen_persona_is_flagged_on_a_protein_ad()
    test_the_collagen_persona_is_silent_on_a_collagen_ad()
    test_an_unscoped_library_never_warns()
    test_scope_matching_respects_word_boundaries()
    test_any_one_declared_scope_is_enough()
    test_an_empty_scope_is_omitted_so_panel_versions_do_not_move()
    test_scope_round_trips_and_is_validated()
    test_the_scope_warning_never_reaches_a_customer_surface()
    print("PASS — scope is declared, matched whole-word, and silent when absent.")


if __name__ == "__main__":
    main()
