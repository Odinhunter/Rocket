"""The gate test's own arithmetic.

`scripts/gate_test.py` is the only check that answers "did that engine change
help?" — so a gate test that is quietly wrong is worse than no gate test: it
greenlights a regression. It normally runs over `runs/` (gitignored, and full of
real client work), so everything here is built on a synthetic runs tree.

Offline. No API calls, and it never reads the real runs directory.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from gate_test import (  # noqa: E402
    _jaccard,
    _spread,
    _vocab,
    load_decisions,
    load_projections,
    load_runs,
    qc1_pooling_identity,
    qc2_convexity,
    qc3_cycle_identity,
)


def _write_run(root: Path, name: str, *, label: str, pains: list[str],
               protocol: str | None = "reaction-v3", report: bool = True) -> None:
    rd = root / "acct" / "brand" / name
    rd.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": name,
        "reaction_protocol_version": protocol,
        "config": {"asset": {"label": label}},
        "report": ({"pain_map": [{"id": f"P{i}", "pain": t}
                                 for i, t in enumerate(pains)]} if report else None),
    }
    (rd / "run.json").write_text(json.dumps(payload))


def test_gate_test_reads_only_finished_v3_runs() -> None:
    """v2 runs are a DIFFERENT protocol. An earlier pass pooled them and got a
    scarier, wrong answer — which is the whole reason this filter exists."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_run(root, "20260721_000001_a", label="Ad A", pains=["price is invisible"])
        _write_run(root, "20260601_000002_b", label="Ad B", pains=["x"], protocol=None)
        _write_run(root, "20260601_000003_c", label="Ad C", pains=["y"], protocol="reaction-v2")
        _write_run(root, "20260721_000004_d", label="Ad D", pains=[], report=False)
        runs = load_runs(root)
    labels = sorted(label for label, _ in runs.values())
    assert labels == ["Ad A"], f"non-v3 or unfinished runs leaked in: {labels}"
    print("  gate test reads only finished reaction-v3 runs ✓")


def test_gate_test_defaults_to_an_absolute_runs_root() -> None:
    """A relative "runs" default is the landmine this project already paid for
    once: the engine wrote to <cwd>/runs while the server read REPO_ROOT/runs,
    and a ~$4 run completed into a directory nothing looked at. It must also
    honour ROCKET_RUNS_DIR, which is how the hosted build will point at its
    mounted volume — otherwise the gate test reads the wrong disk in production
    and reports on runs that are not the ones being made."""
    import os
    import subprocess
    import sys as _sys

    repo = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "elsewhere"
        # Two runs of one ad and one of another: enough for the script to have
        # something to report, and nothing like the repo's real runs/.
        _write_run(root, "20260721_000001_a1", label="Only Ad", pains=["price invisible"])
        _write_run(root, "20260721_000002_a2", label="Only Ad", pains=["price hidden"])
        _write_run(root, "20260721_000003_b1", label="Other Ad", pains=["celebrity reads paid"])

        # Run it from a directory that has no runs/ at all. With a relative
        # default this finds nothing and dies; the assertion is that it reads
        # the volume ROCKET_RUNS_DIR names, from the wrong cwd.
        out = subprocess.run(
            [_sys.executable, str(repo / "scripts" / "gate_test.py")],
            capture_output=True, text=True, cwd=td,
            env=dict(os.environ, ROCKET_RUNS_DIR=str(root),
                     PYTHONPATH=str(repo)),
        )
    assert out.returncode == 0, f"gate test failed from another cwd:\n{out.stderr}"
    assert "distinct ads                   : 2" in out.stdout, out.stdout
    assert "Only Ad x2" in out.stdout, out.stdout
    print("  gate test reads ROCKET_RUNS_DIR from any working directory ✓")


def test_spread_and_jaccard_are_what_the_published_numbers_mean() -> None:
    """The two primitives behind §0a and §0b. `_spread` is max-min, so the
    published 0.111 is 11.1% against 0%."""
    assert abs(_spread([0.111, 0.0, 0.053, 0.0]) - 0.111) < 1e-9
    assert _spread([]) == 0.0 and _spread([0.4]) == 0.0

    assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0
    assert abs(_jaccard({"a", "b"}, {"b", "c"}) - 1 / 3) < 1e-9
    # Two runs with no pains at all are not "identical" — that would report a
    # perfect 1.0 overlap for an empty diagnosis and read as high stability.
    assert _jaccard(set(), set()) == 0.0
    print("  spread = max-min; jaccard handles identical, disjoint and empty ✓")


def test_vocabulary_is_built_from_the_pain_text_of_every_pain() -> None:
    """Reading only the first pain, or only its lead sentence, would compare
    fragments of two diagnoses and call the result stability."""
    pains = [{"id": "P1", "pain": "The price is invisible."},
             {"id": "P2", "pain": "Sceptical about the CLAIMS."}]
    words = _vocab(pains, lambda t: True)
    assert {"price", "invisible", "sceptical", "claims"} <= words, words
    assert "CLAIMS" not in words, "vocabulary must be case-folded"
    # A pain with no text must not crash or contribute.
    assert _vocab([{"id": "P1", "pain": None}], lambda t: True) == set()
    print("  vocabulary covers every pain, case-folded, None-safe ✓")


def test_a_repeated_ad_overlaps_itself_more_than_a_different_ad() -> None:
    """The shape of the 0b claim, on data whose answer is known by construction:
    two runs of one ad share most of their vocabulary; a different ad shares
    almost none. If this ever inverts, the metric is reading the wrong field."""
    shared_a = "the price is invisible and the buyer defers the decision"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_run(root, "20260721_000001_a1", label="Ad A",
                   pains=[shared_a + " entirely"])
        _write_run(root, "20260721_000002_a2", label="Ad A",
                   pains=[shared_a + " completely"])
        _write_run(root, "20260721_000003_b1", label="Ad B",
                   pains=["celebrity endorsement reads as paid and nobody believes it"])
        runs = load_runs(root)

    v = {p: _vocab(pains, lambda t: True) for p, (_, pains) in runs.items()}
    a1, a2, b1 = (next(p for p, (lbl, _) in runs.items() if p.endswith(s))
                  for s in ("a1", "a2", "b1"))
    assert _jaccard(v[a1], v[a2]) > _jaccard(v[a1], v[b1]), \
        "a re-run of one ad must overlap itself more than it overlaps a different ad"
    print("  a repeated ad overlaps itself more than a different ad ✓")


# ---- 0c: the convex-combination check ----
#
# ⚠ Every test below MUTATES a clean fixture and asserts the detector fires. On
# the runs currently on disk 0c reports no violation, so a detector that could
# not fire at all would produce exactly the same output — a clean bill of health
# from a checker pointed at nothing. These are what tell the two apart.


def _clean_projection() -> tuple[dict, dict]:
    """An l35_projection / l3_summary pair whose arithmetic is correct by
    construction: three segments, and a population that really is their sum."""
    segments = [
        {"segment_label": "sceptic_price::deliberate",
         "behavioral_distribution": {"counts": {"scroll_past": 4, "linger": 1},
                                     "next_step_counts": {"nothing": 4, "buy_now": 1},
                                     "n": 5},
         "funnel_rates": {"stop_rate": 0.060, "click_rate": 0.0072,
                          "visit_rate": 0.0068, "convert_rate": 0.0028}},
        {"segment_label": "aspirant_clean_label::impulsive",
         "behavioral_distribution": {"counts": {"scroll_past": 2, "tap_cta": 2},
                                     "next_step_counts": {"nothing": 2, "research_first": 2},
                                     "n": 4},
         "funnel_rates": {"stop_rate": 0.080, "click_rate": 0.0110,
                          "visit_rate": 0.0090, "convert_rate": 0.0035}},
        {"segment_label": "loyalist_brand::deliberate",
         "behavioral_distribution": {"counts": {"linger": 3},
                                     "next_step_counts": {"buy_at_restock": 3},
                                     "n": 3},
         "funnel_rates": {"stop_rate": 0.070, "click_rate": 0.0090,
                          "visit_rate": 0.0080, "convert_rate": 0.0031}},
    ]
    l35 = {
        "overall": {"stop_rate": 0.068, "click_rate": 0.0088,
                    "visit_rate": 0.0078, "convert_rate": 0.0031},
        "by_segment": segments,
    }
    l3 = {
        "population_behavioral_distribution": {
            "counts": {"scroll_past": 6, "linger": 4, "tap_cta": 2},
            "next_step_counts": {"nothing": 6, "buy_now": 1,
                                 "research_first": 2, "buy_at_restock": 3},
            "n": 12,
        }
    }
    return l35, l3


def test_qc1_catches_a_population_that_is_not_the_sum_of_its_segments() -> None:
    """QC1 is an INTEGER identity, so there is no rounding excuse: if the panel
    distribution is not exactly its segments added up, it was not pooled — and
    every average derived from it summarises a population that does not exist."""
    l35, l3 = _clean_projection()
    assert qc1_pooling_identity(l35, l3) == [], "the clean fixture must pass"

    # Each field on its own — a checker comparing only `n` would miss a
    # population whose totals are right but whose mix is invented.
    mutations = {
        "n": lambda p: p.__setitem__("n", p["n"] - 1),
        "counts": lambda p: p["counts"].__setitem__("linger", 99),
        "next_step_counts": lambda p: p["next_step_counts"].__setitem__("buy_now", 7),
    }
    for field, break_it in mutations.items():
        _, fresh = _clean_projection()
        break_it(fresh["population_behavioral_distribution"])
        found = qc1_pooling_identity(l35, fresh)
        assert found, f"QC1 did not fire on a corrupted population {field}"
        assert any(field in msg for msg in found), found
    print("  QC1 fires on n, counts and next_step_counts independently ✓")


def test_qc2_catches_an_overall_rate_outside_the_segment_range() -> None:
    """Both directions. A panel number ABOVE its best subgroup and one BELOW its
    worst are the same defect, and a one-sided check passes half of them."""
    l35, _ = _clean_projection()
    assert qc2_convexity(l35) == [], "the clean fixture must pass"

    high, _ = _clean_projection()
    high["overall"]["convert_rate"] = 0.99
    assert any("convert_rate" in m for m in qc2_convexity(high)), \
        "QC2 did not fire on an overall above every segment"

    low, _ = _clean_projection()
    low["overall"]["stop_rate"] = 0.0
    assert any("stop_rate" in m for m in qc2_convexity(low)), \
        "QC2 did not fire on an overall below every segment"

    # The boundary is inclusive: an overall sitting exactly on its own maximum
    # is what a single-segment-dominated panel legitimately produces.
    edge, _ = _clean_projection()
    edge["overall"]["stop_rate"] = 0.080
    assert qc2_convexity(edge) == [], "QC2 false-fired on the inclusive boundary"
    print("  QC2 fires above and below the segment range, not on its edge ✓")


def test_qc2_deliberately_ignores_the_confidence_bands() -> None:
    """⚠ Pins an omission, not a behaviour. `_band_halfwidth_fraction` widens
    with a small n, so the pooled panel's band is legitimately TIGHTER than
    every segment's — that is more evidence, not a violation. Extending QC2 over
    the bands would look like rigour and would false-fire on every healthy run."""
    l35, _ = _clean_projection()
    for seg in l35["by_segment"]:
        seg["funnel_rates"]["stop_band"] = [0.02, 0.14]
    l35["overall"]["stop_band"] = [0.066, 0.070]  # far inside every segment's
    assert qc2_convexity(l35) == [], \
        "QC2 must not treat a tighter panel band as a convexity violation"
    print("  QC2 leaves the bands alone on purpose ✓")


def test_qc3_catches_a_headline_that_is_not_its_own_cycle_breakdown() -> None:
    """The decision layer's half. The headline and the cycle breakdown are two
    independent implementations of one count over one frame, so they must agree
    exactly; if they ever drift, the number the read LEADS with stops being the
    thing the breakdown under it decomposes."""
    clean = {"target_action_num": 2, "target_action_denom": 18,
             "by_cycle_position": {"in_market": {"num": 2, "denom": 7},
                                   "passive": {"num": 0, "denom": 11}}}
    assert qc3_cycle_identity(clean) == [], "the clean fixture must pass"

    bad_num = dict(clean, target_action_num=3)
    assert any("numerator" in m for m in qc3_cycle_identity(bad_num)), \
        "QC3 did not fire on a headline numerator that is not the cycle sum"

    bad_denom = dict(clean, target_action_denom=19)
    assert any("denominator" in m for m in qc3_cycle_identity(bad_denom)), \
        "QC3 did not fire on a headline denominator that is not the cycle sum"

    # ⚠ No breakdown is a SKIP, never a pass. An empty dict sums to 0/0 and
    # would silently "agree" with any headline on a run that checked nothing.
    assert qc3_cycle_identity({"target_action_num": 2, "target_action_denom": 18}) is None
    assert qc3_cycle_identity({"by_cycle_position": {}}) is None
    print("  QC3 fires on both counts, and reports 'no breakdown' as a skip ✓")


def test_the_0c_loaders_only_see_v3_runs_that_kept_their_sidecars() -> None:
    """0c reads `l35_projection.json` and `l3_summary.json`, NOT run.json —
    `report.funnel_projection` is None unless the run used --funnel, so a
    loader that read run.json would check nothing and report a clean pass."""
    l35, l3 = _clean_projection()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_run(root, "20260721_000001_full", label="Ad A", pains=["p"])
        full = root / "acct" / "brand" / "20260721_000001_full"
        (full / "l35_projection.json").write_text(json.dumps(l35))
        (full / "l3_summary.json").write_text(json.dumps(l3))

        # v3 but never persisted the sidecars.
        _write_run(root, "20260721_000002_bare", label="Ad B", pains=["p"])
        # Sidecars present, but a DIFFERENT protocol — the same pooling error
        # 0a/0b already paid for once.
        _write_run(root, "20260601_000003_v2", label="Ad C", pains=["p"],
                   protocol="reaction-v2")
        v2 = root / "acct" / "brand" / "20260601_000003_v2"
        (v2 / "l35_projection.json").write_text(json.dumps(l35))
        (v2 / "l3_summary.json").write_text(json.dumps(l3))

        found = load_projections(root)
        decisions = load_decisions(root)

    assert [Path(p).name for p in found] == ["20260721_000001_full"], sorted(found)
    # No decision block on any of these fixtures -> nothing to check, and the
    # loader must say so by omission rather than inventing an empty one.
    assert decisions == {}, decisions
    print("  0c loaders take v3 runs with sidecars, and nothing else ✓")


def main() -> None:
    print("=== the gate test's own arithmetic ===")
    test_gate_test_reads_only_finished_v3_runs()
    test_gate_test_defaults_to_an_absolute_runs_root()
    test_spread_and_jaccard_are_what_the_published_numbers_mean()
    test_vocabulary_is_built_from_the_pain_text_of_every_pain()
    test_a_repeated_ad_overlaps_itself_more_than_a_different_ad()
    test_qc1_catches_a_population_that_is_not_the_sum_of_its_segments()
    test_qc2_catches_an_overall_rate_outside_the_segment_range()
    test_qc2_deliberately_ignores_the_confidence_bands()
    test_qc3_catches_a_headline_that_is_not_its_own_cycle_breakdown()
    test_the_0c_loaders_only_see_v3_runs_that_kept_their_sidecars()
    print("PASS — the gate test measures what it claims to.")


if __name__ == "__main__":
    main()
