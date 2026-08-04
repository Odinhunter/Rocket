"""Turning the four questions a media buyer already answers into an AudienceSpec.

⚠ **Why this module exists.** Until 2026-08-04 the "new read" form asked a brand
manager to pick an **audience spec** from a dropdown of `.json` filenames, and to
type a **brand profile id** into a free-text box. Neither is a thing a marketer
knows. Worse, the two fields lied about what they did: the CATEGORY select was
labelled "which disposition library to read against" and did not choose the
library at all — the free-text brand-profile box did, and a typo there raises
`FileNotFoundError` half-way through a prepare, after the creative is uploaded.

What a media buyer *does* know is the Meta Ads Manager audience they already
built: an age range, a gender, an income band, some cities. Those are the
`AudienceSpec.demographics` this engine has always documented as
"addressability points, always customer-set". This module is the mapping.

**What the customer supplies, and what we derive:**

| they answer          | we derive from the brand profile      |
|----------------------|---------------------------------------|
| age / gender / income| the disposition library (who exists)  |
| the cities           | the attention contexts (3-5 moments)  |
|                      | the behavioural mix + panel size      |
|                      | the category                          |

The derived half is not withheld to be clever — it is the half built by hand
from primary research per brand, and no customer can author it.

⚠ **The demographics they give REALLY DO change the panel**, and that was
verified before this module was written rather than assumed. Two specs
identical but for `demographics` produce different consumer types, ages,
genders and incomes — `eligible_dispositions` gates who participates by
demographic mass, and `_clipped_bundle_points` clips the rest to the buy. A
form whose answers did not propagate would be a worse honesty failure than any
caveat, because it surfaces only after someone has trusted it.

⚠ **Matching is gender × age × income ONLY** (`panel.demographic_overlap`).
Geography is NOT part of it. Cities are still asked for and still do real work —
they compose the declared-targeting sentence, which `target_id` reads when
classifying dispositions — but nothing here may imply they narrow the panel, and
`reach()` deliberately computes what the engine actually computes.

⚠ **Bands match the libraries.** The age and income boundaries below are the
ones the hand-built bundles actually use (18-24 / 25-34 / 35-44 / 45-54 / 55-75;
0-3.5 / 3.5-7 / 7-17 / 17-40 / 40-100 LPA). Offering a boundary the library does
not share would produce partial overlaps and a reach number that moves for
reasons no one can explain.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.entities import AudienceSpec
from agent.panel import eligible_dispositions
from agent.vectors import DemographicPoint

# ---- the vocabularies the customer sees -------------------------------
#
# Value first, label second, in every case: the value is what the engine
# consumes and the label is what a person reads. Keeping them in one place
# means the form, the validator and the declared-targeting sentence cannot
# drift into three different opinions about what "₹7-17L" means.

# Age boundaries. `to` carries 75 rather than 65 because the oldest library
# bundle runs to 75, and a ceiling below it would silently exclude those
# personas from every buy that says "and older".
AGE_FROM = ((18, "18"), (25, "25"), (35, "35"), (45, "45"), (55, "55"))
AGE_TO = ((24, "24"), (34, "34"), (44, "44"), (54, "54"), (75, "65+"))

GENDERS = (
    ("any", "All genders"),
    ("female", "Women"),
    ("male", "Men"),
)

# Household income, per year, in lakhs — the unit the libraries are authored
# in. The descriptor after the dash is what makes this answerable by someone
# who thinks in audiences rather than in numbers.
INCOME_BANDS = (
    ("0:100", "Any income"),
    ("0:3.5", "Under ₹3.5L — students, first jobs"),
    ("3.5:7", "₹3.5L – ₹7L — early earners"),
    ("7:17", "₹7L – ₹17L — early-career professionals"),
    ("17:40", "₹17L – ₹40L — established professionals"),
    ("40:100", "₹40L+ — senior, affluent households"),
)

# Geography is descriptive, not a filter — see the module docstring. Offered as
# familiar buckets rather than a free-text box so the declared-targeting
# sentence stays consistent between runs of the same brand.
GEOGRAPHIES = (
    ("metro tier-1", "Metro cities (Mumbai, Delhi, Bangalore, Chennai…)"),
    ("tier-1 and tier-2", "Metros and larger towns"),
    ("tier-2 and tier-3", "Smaller towns"),
    ("all india", "All of India"),
)

_AGE_FROM_VALUES = {v for v, _ in AGE_FROM}
_AGE_TO_VALUES = {v for v, _ in AGE_TO}
_INCOME_VALUES = {v for v, _ in INCOME_BANDS}
_GENDER_VALUES = {v for v, _ in GENDERS}
_GEO_VALUES = {v for v, _ in GEOGRAPHIES}

DEFAULTS = {
    "age_from": 25, "age_to": 44, "gender": "any",
    "income": "7:17", "geography": "metro tier-1",
}


class AudienceAnswerError(ValueError):
    """A form answer that cannot be turned into a buy. The message is shown to
    the customer, so it is written for them and never names a field id."""


@dataclass(frozen=True)
class AudienceAnswers:
    """The four questions, validated.

    Constructed from raw form strings by `parse`, never directly from request
    data — every value is checked against the vocabularies above, because a
    hand-posted form is the path that skips the `<select>`.
    """

    age_from: int
    age_to: int
    gender: str
    income: str
    geography: str

    @property
    def income_range(self) -> tuple[float, float]:
        lo, hi = self.income.split(":")
        return float(lo), float(hi)

    def to_point(self) -> DemographicPoint:
        """The single declared frame this buy describes.

        ⚠ One point, deliberately. The hand-written specs carry three because a
        human composed them; a media buyer sets ONE audience per ad set, and
        asking for three is asking them to do our modelling. `demographics` is
        a list on `AudienceSpec`, so supporting several later is additive and
        not a migration.

        No `occupation_hint` or `household_hint`: those come from the library's
        own bundles and are preserved through `panel._clip_point`, which takes
        them from the persona rather than the declared frame. Verified before
        this was written — a frame with empty hints still produces agents
        described as "college student / gym trainee; stretches budget". There
        is therefore nothing to ask for and no hint table to author.
        """
        lo, hi = self.income_range
        return DemographicPoint(
            gender=self.gender,
            age_min=self.age_from, age_max=self.age_to,
            income_lpa_min=lo, income_lpa_max=hi,
            geography=self.geography,
        )

    def declared_targeting(self) -> str:
        """The buy in one sentence, as the customer described it.

        This replaces a free-text box that asked them to restate, in prose, the
        audience they had just picked from dropdowns. It is not cosmetic:
        `target_id` reads this string when classifying which consumer types sit
        inside the ad's apparent target, so composing it from the same answers
        keeps the classifier's hint and the panel's frame in agreement. They
        could previously disagree, silently, whenever someone typed one thing
        and selected another.
        """
        who = {"any": "adults", "female": "women", "male": "men"}[self.gender]
        age_to = "65+" if self.age_to >= 75 else str(self.age_to)
        bits = [f"{who} {self.age_from}-{age_to}", self.geography]
        lo, hi = self.income_range
        # Each open-ended band gets its own phrasing. Formatting both bounds
        # unconditionally produced "₹0-3.5 LPA" for the lowest band and
        # "₹40-40+ LPA" for the highest — the second is not a range at all, and
        # this sentence is read by the classifier as well as by the customer.
        if (lo, hi) == (0.0, 100.0):
            pass                                  # any income: say nothing
        elif lo <= 0:
            bits.append(f"under ₹{hi:g}L household income")
        elif hi >= 100:
            bits.append(f"₹{lo:g}L+ household income")
        else:
            bits.append(f"₹{lo:g}-{hi:g}L household income")
        return ", ".join(bits)


def parse(data: dict) -> AudienceAnswers:
    """Validate raw form values. Raises `AudienceAnswerError` with copy the
    customer can act on.

    Every value is checked against its vocabulary rather than merely coerced:
    these arrive from an HTTP POST, and the `<select>` that constrains them in
    a browser is absent from a direct post.
    """
    def _int(name: str, allowed: set[int]) -> int:
        raw = str(data.get(name, "")).strip() or str(DEFAULTS[name])
        try:
            value = int(raw)
        except ValueError:
            raise AudienceAnswerError("Pick an age range from the list.") from None
        if value not in allowed:
            raise AudienceAnswerError("Pick an age range from the list.")
        return value

    age_from = _int("age_from", _AGE_FROM_VALUES)
    age_to = _int("age_to", _AGE_TO_VALUES)
    if age_to < age_from:
        raise AudienceAnswerError(
            "The younger end of the age range has to come first.")

    def _one_of(name: str, allowed: set[str], message: str) -> str:
        value = str(data.get(name, "")).strip() or DEFAULTS[name]
        if value not in allowed:
            raise AudienceAnswerError(message)
        return value

    return AudienceAnswers(
        age_from=age_from, age_to=age_to,
        gender=_one_of("gender", _GENDER_VALUES, "Pick a gender from the list."),
        income=_one_of("income", _INCOME_VALUES,
                       "Pick an income band from the list."),
        geography=_one_of("geography", _GEO_VALUES,
                          "Pick a location from the list."),
    )


def build_spec(template: AudienceSpec, answers: AudienceAnswers) -> AudienceSpec:
    """The brand's saved audience, re-aimed at the buy the customer described.

    Everything structural is inherited: which consumer types exist, the
    attention contexts, the behavioural mix, the panel size, the purchase-cycle
    mix. Only `demographics` is replaced. That split is the whole design — the
    inherited half is hand-built per brand from primary research, and the
    replaced half is the only half a customer is in a position to know.

    Returns a NEW spec; the template is a saved entity shared across runs and
    mutating it would re-aim every future read at this one buy.
    """
    spec = AudienceSpec.from_dict(template.to_dict())
    spec.demographics = [answers.to_point()]
    spec.validate()
    return spec


@dataclass(frozen=True)
class Reach:
    """How much of the brand's panel a buy actually reaches."""

    eligible: int
    total: int
    labels: tuple[str, ...]

    @property
    def sentence(self) -> str:
        """Plain words, in the neutral register the rest of the product now
        uses — a fact they can act on, never a warning.

        The narrow case is real and worth saying at the point of CHOOSING: a
        45-60 affluent-women buy against the nutrition library reaches exactly
        one consumer type, and a ~$4 read of a single segment is a poor use of
        the money. Saying so here costs nothing; saying it after the run costs
        them the run.
        """
        if not self.total:
            return "No consumer types are set up for this brand yet."
        if self.eligible == 0:
            return ("This audience doesn't overlap any of this brand's consumer "
                    "types — widen the age or income range.")
        # The noun agrees with the TOTAL, not the count reached — "1 of 6
        # consumer type" is what agreeing with the count produces.
        noun = "consumer type" if self.total == 1 else "consumer types"
        line = f"Reaches {self.eligible} of {self.total} {noun}"
        if self.eligible == 1:
            line += " — a wider buy gives you more to compare"
        return line + "."


def reach(spec: AudienceSpec, dispositions: list) -> Reach:
    """Which of the brand's consumer types this buy actually reaches.

    ⚠ Delegates to `panel.eligible_dispositions` rather than re-implementing
    the overlap. The number a customer sees before paying and the panel the
    engine then builds must come from one calculation; two would drift, and the
    drift would show up as a promise the run did not keep.

    Free and instant — pure arithmetic over demographic ranges, no API call,
    measured at 0.2ms — which is what makes it usable as live feedback while
    someone is still choosing.

    A library whose dispositions carry no demographic bundles is
    demographically unspecified: `audience_mass` returns 1.0 for every one of
    them, so every type is reachable by every buy. That is the truthful answer
    for those brands, not a bug to special-case.
    """
    eligible = eligible_dispositions(spec, dispositions)
    return Reach(eligible=len(eligible), total=len(dispositions),
                 labels=tuple(d.label for d, _ in eligible))
