"""Every model this engine can call must have a price in the cost meter.

⚠⚠ WHY THIS FILE EXISTS. On 2026-08-22, hours before a proposed $5-8 region
generation, `telemetry_summary`'s rate table held sonnet-4-6, opus-4-7 and
opus-4-8 — and `scripts/generate_audience.py` runs on **claude-opus-5**. An
unpriced model contributes nothing to the total, so the most expensive path in
the product reported its cost as **$0.00**, silently and with no warning.

⭐ It went unnoticed because Opus 5 is priced identically to 4.7 and 4.8
($5/$25 per MTok) — there was no number to look wrong, only a missing row.

⭐⭐ THIS IS THE CLASS FIX, NOT THE INSTANCE. Adding `claude-opus-5` to the
table fixes today; this test fixes the next model swap. It reads the models the
engine actually uses — the per-layer defaults AND the generator's own constant —
and fails if any of them is absent from the rate table. A future session that
bumps a model string gets a red test instead of a meter that quietly reads zero.

⚠ It deliberately does NOT check that the RATES are correct — a wrong number is
a different defect and needs a source, not a test. It checks only that a number
exists. `telemetry.py` already carries the scar of the other kind: opus-4-7 was
priced at a stale Opus-3-era (15, 75), 3x too high, and overcounted every run.

Offline. No API calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from agent.config import DEFAULT_MODEL_VERSIONS
from agent.telemetry import _rate_table


def _models_in_use() -> dict[str, str]:
    """Every model string the engine can send to the API, with where it lives.

    ⚠ Read from the CONSTANTS, never by grepping for `claude-*`: a grep over
    the source would also match the rate table itself, so the test would be
    asserting the table against itself and could never fail. That is vacuous
    shape 3, and this repo has already written it twice.
    """
    models = {
        model: f"DEFAULT_MODEL_VERSIONS[{layer!r}]"
        for layer, model in DEFAULT_MODEL_VERSIONS.items()
    }
    from generate_audience import MODEL as GENERATOR_MODEL
    models.setdefault(GENERATOR_MODEL, "")
    models[GENERATOR_MODEL] = (
        (models[GENERATOR_MODEL] + " / " if models[GENERATOR_MODEL] else "")
        + "scripts/generate_audience.MODEL"
    )
    return models


def test_every_model_the_engine_uses_has_a_price() -> None:
    """The one that would have caught it. ⚠ The generator's model is the whole
    point — it is NOT in `DEFAULT_MODEL_VERSIONS`, it is a module constant in a
    script, which is exactly why it was missed."""
    rates = _rate_table()
    unpriced = {m: where for m, where in _models_in_use().items() if m not in rates}
    assert not unpriced, (
        "these models are called by the engine but carry no price, so every "
        "call to them reports as $0.00:\n  "
        + "\n  ".join(f"{m}  ({where})" for m, where in sorted(unpriced.items()))
        + f"\n\npriced today: {sorted(rates)}"
    )
    print(f"  OK  all {len(_models_in_use())} models in use are priced ✓")


def test_the_generator_model_is_covered_specifically() -> None:
    """A positive control naming the actual defect. If a refactor moves the
    generator's model constant, the test above starts passing over a shrunken
    set and goes quietly vacuous — vacuous shape 7, a guard that removes its own
    coverage. This fails loudly instead."""
    from generate_audience import MODEL as GENERATOR_MODEL

    assert GENERATOR_MODEL, "generate_audience.MODEL is empty"
    assert GENERATOR_MODEL in _rate_table(), (
        f"the audience generator runs on {GENERATOR_MODEL!r} and it is not "
        "priced — this is the exact 2026-08-22 defect, restored"
    )
    assert GENERATOR_MODEL in _models_in_use(), (
        "the generator's model is no longer discovered by _models_in_use(); "
        "the test above is now checking a smaller set than it claims to"
    )
    print(f"  OK  generator model {GENERATOR_MODEL} is priced and discovered ✓")


def test_a_price_is_four_positive_numbers() -> None:
    """Shape, not value. A rate entry that is short a field would raise an
    IndexError deep inside a summary — at the moment someone is trying to find
    out what a run cost."""
    for model, rate in sorted(_rate_table().items()):
        assert len(rate) == 4, f"{model}: expected (in, out, cache_read, cache_write), got {rate}"
        assert all(isinstance(x, (int, float)) and x > 0 for x in rate), (
            f"{model}: every rate must be a positive number, got {rate}"
        )
        in_rate, out_rate, cache_read, cache_write = rate
        assert out_rate > in_rate, f"{model}: output should cost more than input, got {rate}"
        assert cache_read < in_rate, f"{model}: a cache READ must be cheaper than fresh input"
        assert cache_write > in_rate, f"{model}: a cache WRITE carries a premium over fresh input"
    print(f"  OK  all {len(_rate_table())} rate entries are well-formed ✓")


def main() -> None:
    print("=== every model the engine calls carries a price ===")
    test_every_model_the_engine_uses_has_a_price()
    test_the_generator_model_is_covered_specifically()
    test_a_price_is_four_positive_numbers()
    print("PASS — the cost meter cannot silently read zero.")


if __name__ == "__main__":
    main()
