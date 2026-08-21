"""A disposition label's stance prefix is runtime logic, so it must parse.

⚠⚠ WHY. `agent/decision.py:stance_of` recovers a stance by splitting the label
on its first underscore. Two decisions depend on the result: which personas form
the **retain frame**, and which personas may be crowned **RETARGET champion**
(the counterfactual guard added 2026-08-22). A label that leads with anything
other than a known stance parses to `""` and drops out of BOTH — silently,
failing closed, with no error and no flag.

⭐ The convention is therefore a DATA CONTRACT, not a naming style, and it was
nowhere enforced. `NamedDisposition` carries no stance field even though the
generator emits one per type, so the prefix is currently the only way to
recover it. These tests are what stop a malformed label reaching a paid run.
"""

from __future__ import annotations

import glob
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from agent.decision import (                                     # noqa: E402
    KNOWN_STANCES, _is_existing_customer, stance_of, unknown_stance_labels,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _shipped_labels() -> dict[str, list[str]]:
    """Every disposition label in every generated audience on disk."""
    out: dict[str, list[str]] = {}
    for path in sorted(glob.glob(str(ROOT / "generated_audience*.json"))):
        try:
            data = json.loads(pathlib.Path(path).read_text())
        except (json.JSONDecodeError, OSError):
            continue
        labels = [t["label"] for t in data.get("raw", []) if "label" in t]
        if labels:
            out[pathlib.Path(path).name] = labels
    return out


def test_the_generator_and_the_decision_layer_agree_on_the_vocabulary() -> None:
    """⭐ The stance list lives in TWO places — the demand grids and
    `decision.py`. If they drift, every type carrying the orphaned stance
    silently stops counting. This is the seam."""
    from generate_audience import FNB_MAP, SNACKING_GRID   # noqa: E402

    for grid in (FNB_MAP, SNACKING_GRID):
        missing = set(grid["stances"]) - KNOWN_STANCES
        assert not missing, (
            f"the generator can emit {sorted(missing)}, which decision.py cannot "
            f"parse — every such type would drop out of the retain frame and out "
            f"of champion candidacy, silently"
        )


def test_every_shipped_label_parses_to_a_known_stance() -> None:
    """The offline guard. Runs against every generated audience on disk."""
    shipped = _shipped_labels()
    assert shipped, "no generated audiences found — this guard would be vacuous"
    bad: dict[str, list[str]] = {}
    for name, labels in shipped.items():
        unknown = unknown_stance_labels(labels)
        if unknown:
            bad[name] = unknown
    assert not bad, f"labels that would silently drop out of scoring: {bad}"


def test_stance_of_rejects_rather_than_guesses() -> None:
    """⚠ MUTATION-PROVED. The failure mode this file exists for is a label that
    LOOKS conventional and is not — `brand_loyalist_x` leads with `brand`, so it
    is not an existing customer however much it reads like one."""
    assert stance_of("loyalist_tapri_chai_break") == "loyalist"
    assert stance_of("lapsed_protein_user") == "lapsed"
    assert stance_of("brand_loyalist_x") == ""
    assert stance_of("tapri_loyalist_break") == ""
    assert stance_of("nostance") == ""
    # and the consequence, stated as behaviour rather than as a string
    assert _is_existing_customer("loyalist_tapri_chai_break")
    assert not _is_existing_customer("brand_loyalist_x")


@pytest.mark.parametrize("stance", sorted(KNOWN_STANCES))
def test_each_known_stance_round_trips(stance: str) -> None:
    assert stance_of(f"{stance}_some_anchor_here") == stance
