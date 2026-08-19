#!/usr/bin/env python3
"""PART B — does one person hold together across moments?  (decision 5)

⚠⚠ THIS IS AN EXPERIMENT RIG, NOT A GENERATION PATH. Its output is NOT an
audience: no grid coverage, no stance grid, and the five gates in
`check_generated_audience.py` do not apply to it. ⭐ Do not "fix" it into a
library and do not install it. Criterion: `docs/fnb_test_b_preregistration.md`.

WHAT IT DOES, AND WHY IT IS SHAPED THIS WAY
-------------------------------------------
It takes PEOPLE that already exist — the demographic bundles of a paid region —
and asks for each person's anchor at a moment they were NOT written for. The
person is fixed; the opinion is written per moment.

⚠⚠ THE OBVIOUS RIG IS VACUOUS. Hand the model one person and ask for three
moments in one conversation and it will keep them consistent, because the
person is sitting in its context — that measures context retention, not the
concept. ⭐ So the calls are MOMENT-MAJOR AND BLIND: one call per moment, each
given all the people, none able to see any other moment's output. That is also
the production shape, since a 22-moment map cannot be one context.

⭐ WHAT IS SHARED IS THE PERSON, NOT THE OPINION. Only the demographic bundle
travels — age, income, city, occupation, household. That is the split the
codebase already has (WHO a persona is lives in `demographic_bundles`, not the
anchor), so the rig is faithful to the architecture it is testing.

⚠ THE STANCE IS NOT GIVEN. It is asked for per anchor, so stance stability
across moments can be read. The native stance is known to the READER and must
never reach the model.

⚠ THE WORLD IS PRODUCTION'S, VERBATIM — `_pack_brief` + `_grid_brief` +
`_region_brief` are imported, not re-written, so the only thing under test is
the person-reuse concept. The SYSTEM prompt is trimmed on purpose: most of
`generate_audience._SYSTEM` is about INVENTING people, which is precisely what
does not happen here. What is carried over is the register: disagreement, the
L3/L4 ceilings, the price-comparison ban, and write-the-experience.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from agent.artifact_pack import load_pack  # noqa: E402
from scripts.generate_audience import (  # noqa: E402
    GRIDS, Region, _grid_brief, _pack_brief, _region_brief,
)

load_dotenv(override=True)

MODEL = "claude-opus-5"

# ⚠ Trimmed from `generate_audience._SYSTEM` and the trimming is deliberate —
# rules 1, 5 and 6 there are about inventing people and filling a grid, neither
# of which happens here. Rules 2, 3 and 4 are about the REGISTER of an anchor
# and they are what must not drift, or a coherence failure could be an artifact
# of a different voice rather than a different person.
_SYSTEM = """\
You write the opinion half of a consumer buyer type for a simulated-audience \
instrument that reads advertising.

⭐ THE PEOPLE ARE GIVEN AND THEY ARE FIXED. You are not inventing anyone. Each \
person below already exists — their age, income, city, work and household are \
settled facts and you may not change, soften or add to them. Your job is to \
write what THIS person's relationship to ONE moment actually is.

⚠⚠ AND SOME OF THEM DO NOT HAVE THIS MOMENT. That is the important part. A \
moment is not a questionnaire everybody answers: a man on a daily wage does not \
have a subscription habit, and a man who is asleep by ten does not have an 11pm \
one. If this person does not genuinely have this moment, DECLINE them and say \
why in one line. ⭐ A decline is information and it is the RIGHT answer more \
often than it feels. Writing a moment onto someone who does not have it puts a \
person in the room who does not exist, which is the one thing this instrument \
cannot survive.

⚠ Do not decline merely because the person is poor, or because the moment is \
modest. A ₹10 habit is a habit. Decline when the moment's CHANNEL, PRICE or \
TIME does not exist in this person's life.

THREE RULES ON HOW THE LINES ARE WRITTEN.

1. CONDITION ON EXPERIENCE, NOT ON CONCLUSIONS. "Believes clean labels matter" \
is a position an ad cannot move. "Binned a half-used ₹1,599 tub after the gym \
habit died" is a thing that happened, and it produces reactions. Write what \
happened to them.

2. L3 AND L4 ARE CEILINGS AND THEY ARE NON-NEGOTIABLE. L3 states what this \
person does NOT know; L4 states what they REJECT. Without them the persona \
writer assumes maximum expertise and maximum agreeableness, and every type \
becomes one that likes every ad it is shown. A panel that likes everything \
measures nothing. Two explicit "does NOT" clauses in L3, minimum.

3. WRITE THE EXPERIENCE, NOT THE ARITHMETIC. The pack and the alternatives list \
give you a world that is concrete down to the SKU and the rupee, and that world \
is what this person reasons INSIDE — it is not what they say. Name real things, \
never invent a brand or a price, and take what you name from the category pack \
or the everyday alternatives list. ⚠ A single price is fine as texture. PRICE \
COMPARISON IS BANNED in every line: no per-gram maths, no multiples, no two \
prices weighed against each other. Most of these people, most of the time, buy \
the everyday alternative — write that honestly.

⚠ THE STANCE IS YOURS TO DECIDE, NOT YOURS TO ASSUME. Read the person and say \
which of the stances they hold AT THIS MOMENT. Do not default to a flattering \
one, and do not make everyone a pragmatist.
"""


def _tool(grid: dict, people: list[dict]) -> dict:
    """⚠ `strict: True` is load-bearing. Without it a batch of the first real
    run emitted five types with no vector axes at all despite every one being
    `required` — a non-strict schema is a request, not a contract."""
    ids = [p["id"] for p in people]
    return {
        "name": "emit_moment_anchors",
        "description": "Emit one anchor per person who genuinely has this moment, "
                       "and a decline for every person who does not.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "anchors": {
                    "type": "array",
                    "description": "One entry per person who HAS this moment. "
                                   "Order does not matter; every person must "
                                   "appear either here or in `declines`, never "
                                   "in both and never in neither.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "person_id": {"type": "string", "enum": ids},
                            "stance": {
                                "type": "string",
                                "enum": grid["stances"],
                                "description": "Which stance THIS person holds at "
                                               "THIS moment. Decide it from the "
                                               "person; do not default.",
                            },
                            "l1_context": {
                                "type": "string",
                                "description": "HOW THEY CAME TO THE CATEGORY. <=30 words. "
                                               "⚠ NO age, NO city, NO job, NO income, NO "
                                               "gender — those are given above and "
                                               "repeating them wastes the line.",
                            },
                            "l2_category": {
                                "type": "string",
                                "description": "How they interact with the category at THIS "
                                               "moment: frequency, channel, typical price "
                                               "band, one habit. <=30 words.",
                            },
                            "l3_knowledge": {
                                "type": "string",
                                "description": "What they know AND explicitly what they do "
                                               "not. MUST contain at least two 'does NOT' "
                                               "clauses. This is the ceiling that stops "
                                               "consultant voice.",
                            },
                            "l4_stance": {
                                "type": "string",
                                "description": "What they want and what they REJECT, and "
                                               "why. Must contain an explicit rejection. "
                                               "<=30 words.",
                            },
                            "l5_behavior": {
                                "type": "string",
                                "description": "ONE recent thing they actually DID at this "
                                               "moment, named at product and channel level. "
                                               "A specific act, not a summary. ⚠ A single "
                                               "price is allowed as texture; COMPARING two "
                                               "prices, or any per-gram / multiple "
                                               "arithmetic, is banned. <=30 words.",
                            },
                        },
                        "required": ["person_id", "stance", "l1_context", "l2_category",
                                     "l3_knowledge", "l4_stance", "l5_behavior"],
                    },
                },
                "declines": {
                    "type": "array",
                    "description": "One entry per person who does NOT genuinely have this "
                                   "moment. ⭐ Expected to be non-empty for most moments.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "person_id": {"type": "string", "enum": ids},
                            "reason": {
                                "type": "string",
                                "description": "One line: what about this person's life "
                                               "means the moment does not occur. Name the "
                                               "channel, the price or the time that is "
                                               "missing — not a generality.",
                            },
                        },
                        "required": ["person_id", "reason"],
                    },
                },
            },
            "required": ["anchors", "declines"],
        },
    }


def _people_brief(people: list[dict]) -> str:
    lines = [
        "THE PEOPLE. These already exist and they are FIXED — every fact here is "
        "settled and none of it may be changed, softened or added to.\n"
    ]
    for p in people:
        lines.append(
            f"[{p['id']}]  {p['age']}, ₹{p['income_lpa']}L household, {p['geography']}\n"
            f"     what fills the day : {p['occupation_hint']}\n"
            f"     at home            : {p['household_hint']}\n"
        )
    return "\n".join(lines)


def _moment_brief(grid: dict, key: str) -> str:
    o = next(o for o in grid["occasions"] if o["key"] == key)
    return (
        f"THE MOMENT YOU ARE WRITING, AND ONLY THIS ONE — [{key}]\n"
        f"  {o['moment']}\n"
        f"    instead they might buy : {o['competes_with']}\n"
        f"    what decides it        : {o['decided_by']}\n"
        f"    where                  : {o['channel']}\n\n"
        "⚠ Every person you write must be written AT THIS MOMENT. Do not write "
        "their general relationship to snacking, and do not write a different "
        "moment that suits them better — if this one does not occur in their "
        "life, that is a decline, not a substitution."
    )


def _load_people(path: Path) -> tuple[list[dict], Region, list[str]]:
    """⚠ FIRST BUNDLE OF EACH TYPE, DETERMINISTIC — no cherry-picking, and the
    pre-registration says so. Also returns each person's NATIVE stance, which is
    for the READER only and must never reach the model."""
    payload = json.loads(path.read_text())
    region = Region(**payload["region"]) if payload.get("region") else Region()
    people, native = [], []
    for i, t in enumerate(payload["dispositions"], 1):
        pt = t["demographic_bundles"][0]["point"]
        people.append({
            "id": f"P{i}",
            "age": pt["age_min"],
            "income_lpa": pt["income_lpa_min"],
            "geography": pt["geography"],
            "occupation_hint": pt["occupation_hint"],
            "household_hint": pt["household_hint"],
        })
        native.append(t["label"].split("_")[0])
    return people, region, native


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", required=True,
                    help="a generated-audience JSON to take the PEOPLE from")
    ap.add_argument("--native", required=True,
                    help="the moment those people were written for ($0, not regenerated)")
    ap.add_argument("--moments", required=True,
                    help="comma-separated transplant moments, one PAID blind call each")
    ap.add_argument("--market", default="snacking", choices=sorted(GRIDS))
    ap.add_argument("--category", default="health_wellness_nutrition")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    grid = GRIDS[args.market]
    pack = load_pack(args.category)
    people, region, native_stances = _load_people(Path(args.people))
    moments = [m.strip() for m in args.moments.split(",") if m.strip()]
    known = {o["key"] for o in grid["occasions"]}
    for m in [args.native, *moments]:
        if m not in known:
            raise SystemExit(f"unknown moment {m!r} — grid has {sorted(known)}")

    print(f"people      : {len(people)} from {args.people}")
    print(f"region      : {region.brief()}")
    print(f"native      : {args.native} (already paid, not regenerated)")
    print(f"transplants : {', '.join(moments)}  ({len(moments)} blind calls, "
          f"{len(people) * len(moments)} anchors)")
    print(f"pack        : {args.category} ({len(pack.brand_landscape)} brands)")

    world = _pack_brief(pack) + "\n\n" + _grid_brief(grid) + "\n\n" + _region_brief(region)

    if args.dry_run:
        print("\n" + "=" * 70)
        print(_SYSTEM)
        print(world)
        print("\n" + _people_brief(people))
        print("\n" + _moment_brief(grid, moments[0]))
        return

    client = anthropic.Anthropic()
    out = Path(args.out)
    payload = {
        "experiment": "part_b_shared_people",
        "people_source": args.people,
        "region": region.__dict__,
        "category": args.category,
        "native_moment": args.native,
        # ⚠ READER-ONLY. Never sent to the model — see the docstring.
        "native_stances": dict(zip([p["id"] for p in people], native_stances)),
        "people": people,
        "moments": {},
    }

    def _checkpoint() -> None:
        """⚠ CALLED THE INSTANT A CALL LANDS. This repo has twice paid for the
        'it was all in memory when it died' shape."""
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    _checkpoint()
    for m in moments:
        # ⚠ BLIND: a fresh `messages` per moment. Nothing from another moment's
        # reply is in this context — that is the whole design, see the docstring.
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=[
                {"type": "text", "text": _SYSTEM},
                {"type": "text", "text": world, "cache_control": {"type": "ephemeral"}},
            ],
            tools=[_tool(grid, people)],
            tool_choice={"type": "tool", "name": "emit_moment_anchors"},
            messages=[{"role": "user", "content":
                       _people_brief(people) + "\n\n" + _moment_brief(grid, m)}],
        )
        block = next(b for b in resp.content if b.type == "tool_use")
        payload["moments"][m] = block.input
        u = resp.usage
        print(f"  {m}: {len(block.input['anchors'])} anchors, "
              f"{len(block.input['declines'])} declined  "
              f"(in {u.input_tokens}, cached {getattr(u, 'cache_read_input_tokens', 0)}, "
              f"out {u.output_tokens})")
        _checkpoint()

    print(f"\nsaved -> {out}")
    print("⚠ THIS FILE IS AN EXPERIMENT, NOT AN AUDIENCE. It never installs and "
          "the five gates do not apply to it.")


if __name__ == "__main__":
    main()
