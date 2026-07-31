"""Session state for a brand-manager session — and the gate that makes it mean
something.

`panel/v3_human_panel/brand_manager_sessions.md` step 2: capture their read
BEFORE the reveal, because it "stops them reacting to the report with pure
hindsight agreement". A prediction typed after seeing the engine's answer is
not a prediction, and nothing downstream can tell the difference. So the gate
lives here, server-side, and every route that could leak the read goes through
it — operator discipline is not a mechanism.

The decoy is not optional. A brand manager cannot tell a real diagnosis from a
fluent wrong one (that is the whole reason this track does not certify the
diagnosis), and `docs/v3_discriminant_check.md` showed the headline metric
itself failing to separate a deliberately-bad ad from a real one. So a session
carries two reads — theirs and one for a different ad — presented unlabeled as
Read A / Read B in a randomised order, and "did they catch it" is DERIVED from
which one they picked, never self-reported.

Session records hold a named third party's unpublished ad outcomes and their
CTR/ROAS. They are written outside runs/ and are gitignored.
"""

from __future__ import annotations

import json
import random
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SLOTS = ("A", "B")


class SessionError(RuntimeError):
    """Base for the protocol violations the server refuses."""


class PredictionMissing(SessionError):
    """The reveal was requested before the prediction was captured."""


class AlreadyRevealed(SessionError):
    """A prediction edit arrived after the read was shown."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:24] or "session"


@dataclass
class Session:
    """One ad, one contact, one predict-then-reveal pass."""

    session_id: str
    contact: str
    company: str
    ad_label: str
    real_key: str
    decoy_key: str
    # Which run each unlabeled slot shows. Randomised at creation and then
    # frozen — the real read must not always be Read A, or the operator's own
    # tell (or a contact who sits two sessions) defeats the blinding.
    slot_map: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    prediction: dict | None = None
    revealed_at: str | None = None
    reaction: dict | None = None

    # ---- protocol state ----

    @property
    def has_prediction(self) -> bool:
        return self.prediction is not None

    @property
    def revealed(self) -> bool:
        return self.revealed_at is not None

    @property
    def stage(self) -> str:
        if not self.has_prediction:
            return "predict"
        if not self.revealed:
            return "reveal"
        if self.reaction is None:
            return "react"
        return "done"

    def key_for_slot(self, slot: str) -> str | None:
        return self.slot_map.get(slot.upper())

    def slot_of_real(self) -> str:
        for slot, key in self.slot_map.items():
            if key == self.real_key:
                return slot
        return ""

    # ---- the gate ----

    def require_prediction(self) -> None:
        """Raise unless the prediction is already on record. Every path that
        could show the engine's read calls this — the reveal page, both report
        slots, and the reaction form."""
        if not self.has_prediction:
            raise PredictionMissing(
                "The reveal is blocked until their prediction is captured. "
                "That ordering is the only thing separating this from a demo: "
                "a read given after seeing the report is hindsight, not a "
                "prediction, and nothing downstream can tell them apart."
            )

    def set_prediction(self, data: dict) -> None:
        if self.revealed:
            raise AlreadyRevealed(
                "This session's read has already been shown, so the prediction "
                "can no longer be edited — the captured version is the only one "
                "taken blind. Start a new session for another ad."
            )
        self.prediction = {**data, "captured_at": _now()}

    def mark_revealed(self) -> bool:
        """Stamp the first reveal. Returns True when this call was the one that
        stamped it, so the timestamp measures predict→reveal and not a reload."""
        self.require_prediction()
        if self.revealed:
            return False
        self.revealed_at = _now()
        return True

    def set_reaction(self, data: dict) -> None:
        self.require_prediction()
        self.reaction = {**data, "captured_at": _now()}

    # ---- the derived signal ----

    def decoy_caught(self) -> bool | None:
        """Did they pick their OWN ad's read out of the two?

        Derived from the recorded pick against the frozen slot map — never
        asked, because "could you tell?" answered out loud is the same
        agreeableness the decoy exists to defeat. None until they answer.
        """
        if not self.reaction:
            return None
        pick = str(self.reaction.get("decoy_pick", "")).upper()
        if pick not in SLOTS:
            return None
        return self.key_for_slot(pick) == self.real_key

    def to_dict(self) -> dict:
        d = asdict(self)
        d["decoy_caught"] = self.decoy_caught()
        d["stage"] = self.stage
        return d

    @classmethod
    def from_dict(cls, raw: dict) -> "Session":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})


class SessionStore:
    """One JSON file per session, under a root outside runs/."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, session_id: str) -> Path:
        # session_id reaches this from the URL; keep it to what create() mints.
        if not re.fullmatch(r"[a-z0-9\-]{1,64}", session_id):
            raise SessionError(f"bad session id: {session_id!r}")
        return self.root / f"{session_id}.json"

    def create(
        self, *, contact: str, company: str, ad_label: str,
        real_key: str, decoy_key: str, rng: random.Random | None = None,
    ) -> Session:
        if real_key == decoy_key:
            raise SessionError(
                "The decoy must be a read of a DIFFERENT ad — two copies of the "
                "same report tests nothing."
            )
        rng = rng or random.SystemRandom()
        keys = [real_key, decoy_key]
        rng.shuffle(keys)
        session = Session(
            session_id=f"{datetime.now().strftime('%Y%m%d')}-{_slug(company or contact)}"
                       f"-{secrets.token_hex(2)}",
            contact=contact, company=company, ad_label=ad_label,
            real_key=real_key, decoy_key=decoy_key,
            slot_map=dict(zip(SLOTS, keys)),
            created_at=_now(),
        )
        self.save(session)
        return session

    def load(self, session_id: str) -> Session | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        return Session.from_dict(json.loads(path.read_text()))

    def save(self, session: Session) -> None:
        path = self._path(session.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Written whole via a temp file: a session record is a research
        # artifact, and a half-written one mid-session is unrecoverable.
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(session.to_dict(), indent=2))
        tmp.replace(path)

    def list(self) -> list[Session]:
        if not self.root.is_dir():
            return []
        out = [
            Session.from_dict(json.loads(p.read_text()))
            for p in sorted(self.root.glob("*.json"))
        ]
        out.sort(key=lambda s: s.created_at, reverse=True)
        return out
