"""render-10 — a persona is never handed a brand or a shop. It is handed a
landscape and chooses.

THE FAILURE THIS EXISTS FOR WAS FOUND IN THE OUTPUT BY THE USER, 2026-08-12.
Personas kept saying they would "check if it's on Nykaa" about a PROTEIN BAR.
Nykaa is a beauty marketplace; nobody buys protein there. It was not a prompt
leak — `aspirant_clean_label`'s anchor said "on Nykaa" TWICE, and the anchor is
injected into the persona-writer prompt under "ANCHOR — HARD CONSTRAINT", so it
beat the artifact pack's own channel list. 24 of 24 of that disposition's
briefs carried it, while the two dispositions whose anchors named a different
shop scored 0/19 and 0/15. The writer was filtering correctly all along; the
anchor was overriding it.

⚠ THE DEFECT IS THE UNIFORMITY, NOT THE MENTION. A hard-coded channel arrives
at 24/24 — maximally prevalent — so a downstream prevalence floor (§1.1/§1.2)
cannot catch it: consensus and a pinned constant are indistinguishable once the
panel is composed. That is why this is pinned at the authoring layer instead.

⚠ THE FORBIDDEN VOCABULARY IS DERIVED FROM THE PACK, NOT HARD-CODED, so adding
a brand to `packs/health_wellness_nutrition.py` automatically extends the guard
instead of silently escaping it.

⚠ WHAT THIS DOES **NOT** ASSERT: that a rendered persona never names a brand.
It should — the pack hands the writer the landscape precisely so a persona can
pick a plausible one. Nykaa remains a correct answer for a beauty-supplement
buyer. What is banned is the AUTHOR pre-deciding it for all of them.

Offline. No API calls.
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.artifact_pack import load_pack  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
_CATEGORY = "health_wellness_nutrition"


def _scaffold():
    """The scaffold is the SOURCE OF TRUTH for the library — it regenerates
    `runs/demo/.../library.json`, and `runs/` is gitignored, so asserting on
    the JSON would assert on an artifact that need not exist in a clean
    checkout. Import the module that writes it instead."""
    path = _REPO / "scripts" / "scaffold_health_wellness.py"
    spec = importlib.util.spec_from_file_location("_scaffold_hw", path)
    mod = importlib.util.module_from_spec(spec)
    with redirect_stdout(io.StringIO()):  # the module prints on import
        spec.loader.exec_module(mod)
    return mod


def _forbidden_terms() -> list[str]:
    """Every brand name and every platform name the pack knows about.

    Platform entries carry a ' — what it sells' annotation as of render-10, so
    take the part before the dash. 'brand DTC website' is generic enough to
    collide with ordinary prose, so it is excluded — it names no company."""
    pack = load_pack(_CATEGORY)
    terms = {b.name for b in pack.brand_landscape}
    for channel in pack.retail_channels:
        terms.add(channel.split("—")[0].strip())
    terms.discard("brand DTC website")
    return sorted(t for t in terms if t)


def _hits(text: str, terms: list[str]) -> list[str]:
    return sorted({t for t in terms if re.search(rf"\b{re.escape(t)}\b", text)})


# --------------------------------------------------------------------------
# 1. The anchors
# --------------------------------------------------------------------------


def test_no_anchor_names_a_brand_or_a_platform():
    """The anchor is a HARD CONSTRAINT in the persona-writer prompt. A brand or
    a shop written into it is applied to 100% of that disposition's agents,
    which is what produced the Nykaa-for-a-protein-bar defect."""
    terms = _forbidden_terms()
    assert len(terms) >= 20, f"pack lexicon looks empty: {terms}"

    offenders = {}
    for d in _scaffold()._library().dispositions:
        found = _hits(d.anchor or "", terms)
        if found:
            offenders[d.label] = found

    assert not offenders, (
        "anchors must name the PRODUCT, never a brand or a marketplace — "
        f"found: {offenders}"
    )


def test_no_occupation_hint_names_a_brand_or_a_platform():
    """The second seam, and the one missed on the first pass at this fix.
    `occupation_hint` reaches the persona writer through
    `persona_writer_demographics`, so a brand parked there survives a clean
    anchor. Six of them did."""
    terms = _forbidden_terms()
    offenders = {}
    for d in _scaffold()._library().dispositions:
        for bundle in d.demographic_bundles:
            hint = bundle.point.occupation_hint or ""
            found = _hits(hint, terms)
            if found:
                offenders.setdefault(d.label, []).append((hint, found))

    assert not offenders, (
        "occupation_hint must describe the BEHAVIOUR, not the brand — "
        f"found: {offenders}"
    )


def test_no_anchor_pre_writes_the_reaction_to_an_ad():
    """render-10 also strips scripted verdicts out of the anchors. An anchor
    saying "sees a protein-powder ad and thinks 'it did nothing'" tells the
    person how to react to the stimulus BEFORE they see it — and the core is
    cached and replayed for every ad this person is ever shown, so no ad can
    ever move them. Condition on lived EXPERIENCE, not on CONCLUSIONS."""
    scripted = re.compile(
        r"(sees?|scroll(s|ing)?\s+(straight\s+)?past|glanc\w+\s+at)\b[^.]{0,80}"
        r"\b(ad|advert\w*|reel|commercial|creative)\b",
        re.IGNORECASE,
    )
    offenders = {}
    for d in _scaffold()._library().dispositions:
        found = scripted.findall(d.anchor or "")
        if found:
            offenders[d.label] = scripted.search(d.anchor).group(0)

    assert not offenders, (
        "an anchor must not pre-write how this person reacts to an ad — "
        f"found: {offenders}"
    )


# --------------------------------------------------------------------------
# 2. The pack brief — the other half of the fix
# --------------------------------------------------------------------------


def test_the_brand_list_is_framed_as_a_landscape_not_a_mandate():
    """Half 1 (clean anchors) without Half 2 (this) still pushes named brands
    into cores: the header used to read "use only these brand names", which is
    an instruction to use them. ⚠ "do not default to the most prominent" is
    load-bearing, not padding — `personal_audio` already ships brand-free
    anchors and its cores still put the top 3 brands in 12 of 12 of EVERY
    disposition. Removing the pin diversifies the tail, not the head."""
    from agent.render import _pack_brief

    brief = _pack_brief(load_pack(_CATEGORY))

    assert "use only these brand names" not in brief.lower(), (
        "the brand list is a landscape to choose from, not a list to use"
    )
    assert "TOP BRANDS IN INDIA" in brief
    lowered = brief.lower()
    assert "do not default to the most prominent" in lowered
    assert "this person would plausibly use" in lowered


def test_every_platform_declares_what_it_actually_sells():
    """The annotation is what lets a clean-label supplement buyer and a protein
    bar buyer pick DIFFERENT shops out of one list. Without it the writer has
    no way to know a beauty marketplace is the wrong place for a bar."""
    pack = load_pack(_CATEGORY)
    bare = [c for c in pack.retail_channels
            if "—" not in c and c != "brand DTC website"]
    assert not bare, f"platforms need a ' — what it sells' note: {bare}"

    nykaa = next(c for c in pack.retail_channels if c.startswith("Nykaa"))
    assert "beauty" in nykaa.lower(), nykaa
    assert "protein bar" in nykaa.lower(), (
        "the specific miss that started this must be stated outright: Nykaa "
        f"is not where protein is bought — {nykaa}"
    )


def test_the_platform_annotations_do_not_weaken_the_invented_brand_guard():
    """`agent/render.py` feeds `retail_channels` into `_vocab_tokens`, so every
    TitleCase word in an annotation joins the ALLOWED set for
    `_validate_no_invented_artifacts`. Verbose notes could quietly widen the
    net the guard casts. Only bare English connectives may be added."""
    from agent import render as render_mod

    pack = load_pack(_CATEGORY)
    after = set(render_mod._vocab_tokens(pack))

    stripped = load_pack(_CATEGORY)
    stripped.retail_channels = [c.split("—")[0].strip()
                                for c in pack.retail_channels]
    before = set(render_mod._vocab_tokens(stripped))

    added = after - before
    assert added <= {"NOT"}, (
        f"platform annotations widened the allowed-artifact vocabulary: {added}"
    )


def test_the_render_prompt_version_was_bumped_for_the_pack_brief_change():
    """⚠ THE BUMP IS THE CHANGE, and this one is easy to get wrong:
    `persona_core_hash` digests the anchor and the CATEGORY STRING, but NOT
    pack contents and NOT `_pack_brief`'s text. The anchor rewrites
    self-invalidate; the pack-brief reword would otherwise be served from cache
    for every core whose anchor did not move — every other library in the
    account — and `provenance.py` fingerprints only `_PERSONA_SYSTEM` /
    `_CONTEXT_SYSTEM`, so `run.json` would not have recorded it either."""
    from agent.render import RENDER_PROMPT_VERSION

    assert RENDER_PROMPT_VERSION == "render-10", RENDER_PROMPT_VERSION
