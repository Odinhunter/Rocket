"""Which of a brand's population goes in the room for one buy.

⚠ WHY THIS MODULE EXISTS. A disposition library is UNCAPPED — `DispositionLibrary`
says so, and once buyer types are generated per demographic region the population
accumulates without limit. A RUN is capped at `AUDIENCE_DISPOSITION_CAP` types.
So something has to choose, and before this module nothing did: a saved audience
listed every type in the library, which only worked while the library was small
enough to fit in a run.

Two jobs, and they must not drift apart:

1. **WHO IS ELIGIBLE** — the people the declared buy can actually reach.
   ⚠ `server.audience_form.reach()` shows this count BEFORE the customer pays,
   and its docstring commits to the number shown and the panel built coming from
   ONE calculation. This module is that calculation, and it now has three
   consumers rather than two.

2. **WHO GETS A SEAT** — when more people are eligible than a run can carry,
   spread the seats across the demand spaces instead of taking the first N.
   Sorting by label would hand a whole run to whichever occasion sorts first.

⚠ WE NEVER TELL A CUSTOMER TO WIDEN THE BUY — the user's call, 2026-08-15. If a
buy reaches very few people, it runs as-is with very few. Nothing here refuses,
trims a thin set, or substitutes anyone. The answer to a thin audience is to
generate more people for that region, never to quietly widen it.
"""

from __future__ import annotations

import re
from dataclasses import replace

from agent.panel import audience_mass
from agent.vectors import DemographicPoint, NamedDisposition

# --------------------------------------------------------------------------
# The curator note that carries a generated type's grid position.
# --------------------------------------------------------------------------
# ⚠ THIS FORMAT IS LOAD-BEARING AND IT LIVES HERE, not in the generator script.
# Selection stratifies across occasion x stance and has to read it back at run
# time. `NamedDisposition` has no structural field for either, and adding one
# would change `to_dict()` — which `compute_panel_version` digests — moving
# `panel_version` for every library already on disk and breaking comparability
# with every run ever made. So the note is the channel, the engine owns the
# format, and `scripts/generate_audience.py` imports these two functions rather
# than writing the string itself.

def notes_for(occasion: str, stance: str, region_key: str) -> str:
    return f"generated: occasion={occasion} stance={stance} region={region_key}"


def parse_notes(notes: str) -> dict:
    """`notes_for`'s inverse. Returns {} for a note this did not write — a
    hand-authored disposition has a human's note and must not be mis-parsed."""
    if not notes or not notes.startswith("generated:"):
        return {}
    out = {}
    for token in notes[len("generated:"):].split():
        if "=" in token:
            key, value = token.split("=", 1)
            out[key] = value
    return out


# --------------------------------------------------------------------------
# Tier.
# --------------------------------------------------------------------------
# ⚠ GEOGRAPHY IS NOT PART OF `panel.demographic_overlap` — matching there is
# gender x age x income ONLY, and it stays that way: that function is pinned by
# a dozen tests and is the definition of "in the declared frame" for every run
# on disk. Tier is applied HERE instead, as an extra eligibility filter, so the
# engine's contract does not move.
#
# ⚠ FAIL OPEN ON AN UNKNOWN TIER. A person whose geography is a bare city name
# carries no tier token, and dropping them would silently shrink a panel because
# of how a generator happened to phrase a string. A person is excluded only on a
# DEFINITE mismatch.

_TIER_RE = re.compile(r"tier[\s-]?([123])", re.I)
_METRO_RE = re.compile(r"\bmetro\b", re.I)


def tiers_in(text: str) -> set[str]:
    """The city tiers a free-text geography mentions. Empty means unknown."""
    found = {m.group(1) for m in _TIER_RE.finditer(text or "")}
    if _METRO_RE.search(text or ""):
        found.add("1")          # a metro IS tier-1; the form says so too
    return found


def region_tier(notes: str) -> set[str]:
    """The tier a generated buyer type was WRITTEN for, from its region key.

    ⚠ PREFERRED OVER PARSING THE CITY STRING, because the city string is prose
    and the region is data. "Mumbai suburb" carries neither the word "metro" nor
    a tier token, so text parsing fails open and lets an obviously-metro person
    into a smaller-towns buy — measured 2026-08-16. A type generated for a
    tier-3 region simply IS tier-3, whatever its author called the town.
    """
    key = parse_notes(notes).get("region", "")
    tail = key.rsplit("_", 1)[-1] if key else ""
    return {tail[1]} if len(tail) == 2 and tail[0] == "t" and tail[1] in "123" else set()


def tier_compatible(person_geography: str, frame_geography: str,
                    notes: str = "") -> bool:
    wanted = tiers_in(frame_geography)
    if not wanted:              # "all india", or a frame with no tier stated
        return True
    theirs = region_tier(notes) or tiers_in(person_geography)
    if not theirs:              # genuinely unknown tier -> fail open, see above
        return True
    return bool(theirs & wanted)


# --------------------------------------------------------------------------
# Eligibility and selection.
# --------------------------------------------------------------------------

def eligible(dispositions: list[NamedDisposition],
             frames: list[DemographicPoint]) -> list[NamedDisposition]:
    """The buyer types this buy can actually reach, in library order — each one
    carrying only the PEOPLE the buy reaches.

    Gender x age x income comes from `panel.audience_mass` — unchanged, and the
    reason a POINT person is reachable from any customer-chosen range. Tier is
    layered on top, per the note above.

    ⚠ TIER FILTERS PEOPLE, NOT JUST TYPES, AND GATING THE TYPE IS NOT ENOUGH.
    Measured 2026-08-16: a buy for "smaller towns" returned 17 buyer types and
    then simulated a panel living in Mumbai, metro NCR and Mumbai suburb. A type
    holds several people across several cities, so keeping the whole type
    because ONE of its people is tier-2 lets every metro sibling into the room
    behind them — and the report still describes the buy as tier-2/3. So the
    disposition is rebuilt here with only the matching bundles.

    ⚠ This DOES move `panel_version` for a tier-scoped buy, and that is correct:
    a different set of people in the room is a different panel, and freeze
    records either side of it are genuinely not comparable.
    """
    out = []
    for d in dispositions:
        if audience_mass(d, frames) <= 0:
            continue
        if not d.demographic_bundles:
            # Demographically unspecified — lives everywhere, tier included.
            out.append(d)
            continue
        keep = [b for b in d.demographic_bundles
                if any(tier_compatible(b.point.geography, f.geography, d.notes)
                       for f in frames)]
        if not keep:
            continue
        if len(keep) == len(d.demographic_bundles):
            out.append(d)
            continue
        narrowed = replace(d, demographic_bundles=keep)
        # ⚠ Re-checked AFTER narrowing. The people who satisfied the age/income
        # frame and the people who satisfy the tier can be different subsets, so
        # a type can pass `audience_mass` on its metro members and have nobody
        # left once tier is applied — which is the state `_clipped_bundle_points`
        # now refuses to invent agents for.
        if audience_mass(narrowed, frames) > 0:
            out.append(narrowed)
    return out


def _grid_position(d: NamedDisposition) -> tuple[str, str]:
    note = parse_notes(d.notes)
    return note.get("occasion", ""), note.get("stance", "")


def select(dispositions: list[NamedDisposition],
           frames: list[DemographicPoint], budget: int) -> list[NamedDisposition]:
    """Up to `budget` buyer types for one buy, spread across the demand spaces.

    ⚠ A THIN BUY IS NEVER PADDED AND NEVER REFUSED. If fewer than `budget` are
    eligible, all of them run and that is the whole panel — the honest answer,
    and the user's explicit call.

    When there are more, seats go round-robin over OCCASIONS: the first type of
    each occasion, then the second of each, and so on. Taking the first `budget`
    in library order would hand an entire run to whichever occasions the
    generator happened to write first — which is exactly how `--count 40`
    against a 64-cell grid produced a library with no purist, pragmatist or
    gifter at all.
    """
    pool = eligible(dispositions, frames)
    if len(pool) <= budget:
        return pool

    buckets: dict[str, list[NamedDisposition]] = {}
    for d in pool:
        occasion, stance = _grid_position(d)
        buckets.setdefault(occasion, []).append(d)
    for occasion in buckets:
        # Stable within a bucket: stance, then label. Never library order, which
        # is generation order and carries the generator's own biases.
        buckets[occasion].sort(key=lambda d: (_grid_position(d)[1], d.label))

    chosen: list[NamedDisposition] = []
    depth = 0
    order = sorted(buckets)
    while len(chosen) < budget:
        took = False
        for occasion in order:
            if depth < len(buckets[occasion]):
                chosen.append(buckets[occasion][depth])
                took = True
                if len(chosen) == budget:
                    break
        if not took:
            break
        depth += 1
    return chosen
