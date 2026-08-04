"""A brand set up on disk, for tests that drive the "new read" form.

Since 2026-08-04 the form derives the category, the disposition library and the
audience template from the BRAND the customer picks, so a temp world with no
brand entities renders "no brands are set up on this account yet" and every
form test fails identically and unhelpfully. This builds the three entities a
brand needs.

⚠ Built through the real constructors and written with `to_dict`, never as
hand-rolled JSON. `AudienceSpec`, `DispositionLibrary` and `SavedAudience` are
strict about nested shapes, and a hand-written fixture drifts from them
silently — at which point the tests are exercising the fixture rather than the
server. `validate()` is called on the way out for the same reason.

⚠ The demographic bundles are the load-bearing part. `discover_brands` and the
reach calculation both turn on them, and a library without them makes every
consumer type reachable by every buy (`audience_mass` returns 1.0 when a
disposition is demographically unspecified) — which would leave the reach tests
green against any answer at all. The three below are deliberately disjoint on
age and income so a narrow buy provably excludes some of them.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent.entities import (
    AudienceSpec, BrandProfile, DispositionLibrary, SavedAudience,
)
from agent.vectors import (
    DemographicBundle, DemographicPoint, DispositionVector, NamedDisposition,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

ACCOUNT = "demo"
BRAND = "hw"
LIBRARY_ID = "hw_lib_v1"
AUDIENCE_ID = "cold_traffic_v1"
CATEGORY = "health_wellness_nutrition"

# (label, age range, income LPA range, gender). Disjoint on purpose — see the
# module docstring. A 18-24 / under-3.5L buy reaches ONLY `young_lifter`; a
# 45-75 / 40L+ buy reaches ONLY `settled_parent`.
_TYPES = (
    ("young_lifter", (18, 24), (0.0, 3.5), "male"),
    ("early_career_aspirant", (25, 34), (7.0, 17.0), "any"),
    ("settled_parent", (45, 75), (40.0, 100.0), "female"),
)


def _vector() -> DispositionVector:
    """One coherent vector, shared. These tests turn on demographics, not on
    attitudes, and three hand-varied vectors would suggest otherwise."""
    return DispositionVector(
        category_relationship="regular", brand_stance="loyalist",
        price_orientation="value_calculator", decision_driver="function",
        category_involvement="obsessive", prior_experience_valence="positive",
        channel_behavior="marketplace", life_stage="early_career",
    )


def build_brand(runs_root: Path, *, account: str = ACCOUNT, brand: str = BRAND,
                category: str = CATEGORY, audience_id: str = AUDIENCE_ID) -> None:
    """Write brand_profile.json, library.json and one saved audience.

    Writes THROUGH `runs_root` rather than calling the entities' own `.save()`:
    those resolve the path from `agent.telemetry.runs_root()`, which is the
    repo's real `runs/` and not the temp world under test. Saving that way is
    how the offline suite once wrote into the directory holding real client
    runs.
    """
    entities = runs_root / account / brand / "entities"
    (entities / "audiences").mkdir(parents=True, exist_ok=True)

    dispositions = [
        NamedDisposition(
            label=label, vector=_vector(),
            demographic_bundles=[DemographicBundle(
                point=DemographicPoint(
                    gender=gender, age_min=age[0], age_max=age[1],
                    income_lpa_min=inc[0], income_lpa_max=inc[1],
                    geography="metro tier-1",
                    occupation_hint=f"{label} occupation",
                    household_hint=f"{label} household"),
                weight=1.0)])
        for label, age, inc, gender in _TYPES
    ]
    library = DispositionLibrary(
        library_id=LIBRARY_ID, account_id=account, brand_profile_id=brand,
        dispositions=dispositions)
    library.validate()
    (entities / "library.json").write_text(json.dumps(library.to_dict()))

    # A real spec, for its context envelope, chaos mix and panel size — the
    # parts the form inherits rather than asks for. Its demographics are
    # replaced by whatever the form posts, which is the behaviour under test.
    spec = AudienceSpec.from_dict(json.loads(
        (REPO_ROOT / "specs" / "health_wellness_cold_traffic.json").read_text()))
    spec.disposition_labels = [label for label, *_ in _TYPES]
    spec.panel_size = 30
    spec.validate()
    saved = SavedAudience(
        audience_id=audience_id, name="Cold traffic",
        brand_profile_id=brand, account_id=account, spec=spec)
    saved.validate()
    (entities / "audiences" / f"{audience_id}.json").write_text(
        json.dumps(saved.to_dict()))

    profile = BrandProfile(
        brand_profile_id=brand, account_id=account, categories=[category],
        library_id=LIBRARY_ID, audience_ids=[audience_id])
    profile.validate()
    (entities / "brand_profile.json").write_text(json.dumps(profile.to_dict()))


# The four audience answers, as the form posts them. Every form test needs
# these, and a test that omits one is relying on a server-side default it did
# not mean to exercise.
ANSWERS = {"brand": BRAND, "age_from": "25", "age_to": "44",
           "gender": "any", "income": "7:17", "geography": "metro tier-1"}
