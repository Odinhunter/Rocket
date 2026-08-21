"""Deterministic content checks that run BEFORE the first model call.

⚠⚠ WHY THIS EXISTS, AND WHY IT IS NOT ANOTHER RunPreparation ADVISORY.

On 2026-08-22 a $3.85 run described the market to every persona in it as
**"international food and drink"** — for an Indian food and beverage pack. The
cause was `category`, the string `"fnb_world"`, interpolated into prose a model
reads. It is a machine identifier: it names the module, keys the render cache
and gates the install guard. It was never a description of anything.

Nothing caught it, because the value was structurally perfect — a valid string,
in a valid field, of the correct type. Schema validation cannot see this class
of defect. Only reading the assembled prompt can.

⭐⭐ THE ORDERING IS THE WHOLE POINT. `RunPreparation` already carries six
advisories (demographic mismatch, coverage, purpose, trust ceiling, scope...)
and they are all computed AFTER `target_id` — one model call in. By then the
render prompts are already being built with the bad string in them. These checks
are free and deterministic, so they run at the TOP of `prepare()`, before
anything is spent.

⭐ AND WHY IT BLOCKS RATHER THAN WARNS. Every existing advisory is a marketer
JUDGEMENT CALL — an off-demographic creative can be deliberate, so those warn and
`--acknowledge-...` proceeds. A machine identifier in a prompt is not a judgement
call. No user has ever wanted it. There is no override flag here on purpose.

⭐ WHAT THIS ADDS OVER THE OFFLINE SUITE, which is the fair question to ask of
any runtime check. `tests/test_identifiers_never_reach_a_reader.py` covers the
eight packs that ship, at the moment the suite runs. This covers the data the
suite never sees: the run's own resolved library, a pack installed after the
tests were written, a freshly generated audience. Same functions, two consumers.
"""

from __future__ import annotations

from agent.artifact_pack import CategoryArtifactPack
from agent.vectors import (
    ContextVector, KNOWN_CONVENTION_VIOLATIONS, unknown_stance_labels,
)


class PreflightError(RuntimeError):
    """A mechanical content defect found before any credit was debited.

    Carries every defect found, not just the first — a run blocked twice for two
    reasons it learns about one at a time is the shape that wastes an afternoon.
    """

    def __init__(self, defects: list[str]) -> None:
        self.defects = defects
        body = "\n".join(f"  - {d}" for d in defects)
        super().__init__(
            f"content preflight failed — {len(defects)} defect(s), no credit "
            f"debited and no model called:\n{body}"
        )


def _slug_forms(category: str, market_name: str = "") -> list[str]:
    """The forms of a slug that can never be legitimate prose — and only those.

    ⚠⚠ I GOT THIS WRONG TWICE BEFORE IT WAS RIGHT, both times by being too
    broad, which is the same error as the "desk" ban in the F&B map.

      1st: flagged the `coffee` pack eleven times — `CATEGORY: Indian coffee`,
           `Cafe Coffee Day`, `/r/coffee`. For a SINGLE-TOKEN category the
           identifier and the English word are the same string, so a model
           reading it understands the right thing. No defect is possible.
      2nd: flagged `personal_audio`, whose market_name IS "Indian personal
           audio". The humanised form of a slug is sometimes the real English
           name of the category, and the pack's own authored market_name is the
           evidence of which case you are in.

    ⭐ SO THE RULE USES THE PACK'S OWN PROSE AS THE ORACLE. The underscore form
    is never English and is always flagged. The humanised form is flagged only
    when it is NOT part of the market name — `fnb world` is absent from "Indian
    urban food and beverage" and is a defect; `personal audio` is present in
    "Indian personal audio" and is the category's actual name.

    ⚠ A guard that cries wolf on a legitimate pack is worse than no guard. It
    gets bypassed, and then it is not there for the real one."""
    if "_" not in category:
        return []
    spaced = category.replace("_", " ")
    # the underscore form: never prose, in any pack, ever
    forms = [category]
    if spaced.lower() not in market_name.lower():
        forms += [spaced, spaced.title(), spaced.capitalize()]
    return forms


def check_pack(pack: CategoryArtifactPack) -> list[str]:
    """The two seams that actually leaked, checked on the ASSEMBLED text.

    ⚠ Checked at pack level, once per run — not per agent. The prompts differ
    per persona, but the pack blocks inside them do not, so per-agent checking
    would cost time and find nothing new.
    """
    defects: list[str] = []
    category = pack.category

    if not pack.market_name:
        defects.append(
            f"pack {category!r} has no market_name, so the humanised slug "
            f"({category.replace('_', ' ')!r}) is what a model would be told "
            f"the market is"
        )
    elif pack.market_name.strip().lower() == category.replace("_", " ").lower():
        defects.append(
            f"pack {category!r} market_name is just the humanised slug — the "
            f"defect with extra steps"
        )

    # ⚠ Imported HERE rather than at module scope: agent.render pulls in the
    # model client, and preflight is imported by run_service at startup.
    from agent.render import _context_user_payload, _pack_brief

    seams = {
        "the persona-writer brief (_pack_brief)": _pack_brief(pack),
        "the context writer (_context_user_payload)": _context_user_payload(
            ContextVector(
                attention_level="high", device_posture="desk",
                intent_state="actively_shopping", energy_state="alert",
                social_setting="alone",
            ),
            pack,
        ),
    }
    for where, text in seams.items():
        for form in _slug_forms(category, pack.market_name):
            if form in text:
                defects.append(
                    f"the category slug {form!r} reaches {where} — this is the "
                    f"exact hop that produced 'international food and drink'"
                )
                break
    return defects


def check_labels(labels: list[str], *, source: str = "the resolved library") -> list[str]:
    """A label whose stance does not parse drops out of the retain frame AND out
    of champion candidacy — silently, failing closed, with no error and no flag.

    ⭐ Runtime is where this matters most: the offline guard reads libraries on
    disk NOW, and a library installed tomorrow is exactly the one nobody checked.
    """
    unknown = [
        lab for lab in unknown_stance_labels(labels)
        if lab not in KNOWN_CONVENTION_VIOLATIONS
    ]
    if not unknown:
        return []
    return [
        f"{source}: {sorted(unknown)} lead with no known stance, so every "
        f"persona carrying them would drop out of retain scoring and out of "
        f"champion candidacy without an error"
    ]


def preflight_or_raise(
    pack: CategoryArtifactPack, labels: list[str], *, source: str = "the resolved library"
) -> None:
    """The one call site's entry point. Raises `PreflightError` or returns None.

    ⚠ NOT display_name. All seven installed libraries predate that field and
    `disposition_display` falls back to the stance-separated form by design —
    hard-failing on it would brick every library that exists today. It is
    REQUIRED of the generator going forward, which is where it belongs.
    """
    defects = check_pack(pack) + check_labels(labels, source=source)
    if defects:
        raise PreflightError(defects)
