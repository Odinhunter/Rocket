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

from gate_test import _jaccard, _spread, _vocab, load_runs  # noqa: E402


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


def main() -> None:
    print("=== the gate test's own arithmetic ===")
    test_gate_test_reads_only_finished_v3_runs()
    test_gate_test_defaults_to_an_absolute_runs_root()
    test_spread_and_jaccard_are_what_the_published_numbers_mean()
    test_vocabulary_is_built_from_the_pain_text_of_every_pain()
    test_a_repeated_ad_overlaps_itself_more_than_a_different_ad()
    print("PASS — the gate test measures what it claims to.")


if __name__ == "__main__":
    main()
