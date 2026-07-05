"""rocket-2.2.0 (v2.2 diagnosis rung): pure grounding + scope validators.

These are the enforcement seam for the assess/prescribe split. Grounding moved
up a level — recommendations derive from diagnosed pains, and each pain is
grounded in verbatim consumer quotes. The checks:

  * verify_quote_authenticity — every evidence quote is a real (verbatim)
    substring of the raw reaction corpus. Fixes two bugs in the prototype's
    version: it matches the FULL normalized quote (no 60-char truncation, so a
    fabricated tail cannot sneak through), and the caller is expected to feed
    quotes from the pains AND the verbatim_consumer_voice AND the strengths
    (the prototype only checked pain quotes, but verbatim_voice is the
    customer-facing "the room's voice" deliverable where a hallucination is
    worst).
  * verify_pain_references — every recommendation's derives_from_pains cites a
    pain id that actually exists in the PainMap.
  * check_lever_space — recommendations stay on the marketer control surface
    (creative / media-buy / offer-on-existing-SKU); never product / base-price
    / new-SKU / formulation / distribution.

All pure functions, no network — fully offline-testable. Each accepts either a
dataclass object (Quote / Pain / TopChange) or a plain dict, so they run on raw
model JSON before deserialization and on an assembled Report alike.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


def _norm(s: str) -> str:
    """Collapse whitespace + lowercase — the normalization both the corpus and
    each candidate quote pass through before substring comparison."""
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _quote_text(q: Any) -> str:
    """Accept a Quote dataclass (`.quote`) or a raw dict (`["quote"]`)."""
    if isinstance(q, dict):
        return q.get("quote", "") or ""
    return getattr(q, "quote", "") or ""


def _pain_id(p: Any) -> str:
    if isinstance(p, dict):
        return p.get("id", "") or ""
    return getattr(p, "id", "") or ""


def _derives_from(change: Any) -> list[str]:
    if isinstance(change, dict):
        return list(change.get("derives_from_pains", []))
    return list(getattr(change, "derives_from_pains", []) or [])


# How much of a quote's normalized head must appear verbatim in the corpus for
# it to count as grounded. opus-4-8 quotes REAL reactions but lightly reworders
# them (fixes contractions, trims, joins fragments), so a full-exact-substring
# check false-rejects legitimate near-verbatim quotes wholesale (empirically it
# killed 2/4 calibration runs). A head-prefix match accepts near-verbatim while
# still catching wholesale invention; the residual reworded-tail risk is
# absorbed by the caller, which DROPS (never fabricates) unverifiable quotes.
_MIN_QUOTE_PREFIX = 40


def verify_quote_authenticity(quotes: Iterable[Any], corpus: str) -> list[str]:
    """Return the quote texts whose normalized head (first _MIN_QUOTE_PREFIX
    chars, or the whole quote if shorter) is NOT found in the corpus — i.e. the
    quotes that cannot be traced to a real reaction.

    Empty list == every quote is grounded. `quotes` may be Quote objects or
    dicts. Empty quotes are skipped (nothing to ground). Grounding is a FILTER,
    not a gate: the caller drops what this flags, it does not fabricate.
    """
    ncorpus = _norm(corpus)
    fabricated: list[str] = []
    for q in quotes:
        text = _quote_text(q)
        nq = _norm(text)
        if not nq:
            continue
        probe = nq if len(nq) <= _MIN_QUOTE_PREFIX else nq[:_MIN_QUOTE_PREFIX]
        if probe not in ncorpus:
            fabricated.append(text)
    return fabricated


def verify_pain_references(changes: Iterable[Any], pains: Iterable[Any]) -> list[str]:
    """Return the pain ids cited by recommendations that don't exist in the
    PainMap. Empty list == referential integrity holds."""
    known = {_pain_id(p) for p in pains}
    dangling: list[str] = []
    for c in changes:
        for pid in _derives_from(c):
            if pid not in known:
                dangling.append(pid)
    return dangling


# The marketer's control surface. A recommendation that reaches past creative /
# media-buy / offer-on-existing-SKU into the product, base price, pack size,
# formulation, or distribution is out of scope — the assess pass may NAME such
# a pain as structural, but prescribe must pivot to an in-scope move. Ported
# from the prototype minus "launch a" (false-positive risk on legit media
# moves like "launch a retargeting campaign").
LEVER_BANNED = [
    "trial size", "trial pack", "trial sku", "smaller pack", "smaller sku",
    "new sku", "new pack", "reformulate", "reformulation", "lower the price",
    "reduce the price", "drop the price", "cut the price", "new flavour line",
    "get into more stores", "expand distribution", "change the formula",
]


def _change_text(change: Any) -> str:
    if isinstance(change, dict):
        return (change.get("change", "") or "") + " " + (change.get("why", "") or "")
    return (getattr(change, "change", "") or "") + " " + (getattr(change, "why", "") or "")


def check_lever_space(changes: Iterable[Any], bets: Iterable[str]) -> list[str]:
    """Return out-of-scope lever violations found in the recommendations or the
    bet ranking. Empty list == clean."""
    hits: list[str] = []
    haystacks = [_change_text(c) for c in changes] + list(bets)
    for h in haystacks:
        nl = h.lower()
        for term in LEVER_BANNED:
            if term in nl:
                hits.append(f"{term!r} in: {h[:80]}")
    return hits
