"""The Render Engine — turns population-axis vectors into persona prose.

The persona is rendered from structured vectors (demographics +
disposition + chaos) against a hand-curated CategoryArtifactPack. This is
what makes on-the-spot audience composition possible: a new disposition
is a new vector point, rendered instantly.

HARD RULE: the render engine weaves artifacts that are PRESENT IN THE PACK
— real brands, real prices, real communities — and never invents them.
That constraint is the whole game: vividness comes from the curated
artifacts, not from the vectors. _validate_no_invented_artifacts is the
post-hoc check.

Register note (render-6): the rendered persona core is a PLAIN third-person
brief — the agent then reacts in first person. The core IS the system block
of every reaction call (runtime.run_agent), so the register it is written in
is the register the agent inherits; it is deliberately not literary. It ends
with a HOW THEY TALK block — 2-3 first-person utterances that SHOW that
register. Those utterances are habit-anchored and ad-agnostic on purpose: a
core is cached and replayed across many ads, so a brand verdict written here
would be a planted answer. See docs/v3_protocol.md §9.

Caching: a persona core is a pure function of (demographic, disposition,
chaos, category, schema+prompt version). It renders once and is reused for
every agent in a panel that shares that point — cached at the brand level
in library_renders/ so it amortizes across runs. Context is rendered
separately (it varies per-agent within a panel; caching it with the core
would cache-bust).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from agent.artifact_pack import CategoryArtifactPack
from agent.config import DEFAULT_MODEL_VERSIONS
from agent.telemetry import call_with_telemetry
from agent.vectors import (
    VECTOR_SCHEMA_VERSION,
    ChaosVector,
    ContextVector,
    DemographicPoint,
    DispositionVector,
)

_log = logging.getLogger(__name__)

# Bumps when a render prompt below changes — invalidates cached renders the
# same way VECTOR_SCHEMA_VERSION does for a schema change.
# render-2: persona prompt forbids naming the person; context prompt forces
#           gender-neutral "they" so a context composes onto any persona.
# render-3: persona prompt makes the disposition vector the SPINE and the
#           pack a palette — fixes vividness-gate homogenization (every
#           vector was collapsing onto the same "third-wave cafe" persona).
# render-4: persona prompt honours the optional NamedDisposition.anchor as a
#           hard constraint — the abstract vector captures stance but not the
#           object of that stance (loyal to filter coffee vs loyal to a d2c
#           roaster were the same vector). Phase 0 re-open from the gate.
# render-5: niche enthusiast communities (subreddits, hobbyist forums) are
#           gated to high/obsessive category_involvement — lower-involvement
#           personas are passively aware at most. User feedback after the
#           render-4 vividness gate passed 7/7.
# render-6: C3 — the persona core stops being an identity document written in
#           a register no real person uses. The core IS the system block of
#           every reaction call (runtime.run_agent), so its register is the
#           register the agent inherits; a user-turn "you are NOT a writer"
#           cannot outweigh it. TWO registers leak, and both are banned:
#           (a) literary ("quietly turned a corner of his life into a small,
#           disciplined system"), and (b) MARKET-RESEARCH — the subtler one.
#           "Consumer-research writer" as the render engine's identity was
#           itself the analyst prime: it turned the pack's real consumer line
#           "you're paying for the logo" into "trading on the logo", which the
#           agent then echoed back as its own reaction. Hence the operative
#           rule: downgrade analysis into speech, never upgrade speech into
#           analysis. Differentiation still comes from SPECIFICS (the render-3
#           win) — strip the abstract layer, never the brands/prices/channels.
#           C1 — the core now ends with a HOW THEY TALK block: 2-3 first-person
#           utterances that SHOW the register (a shown register is matched far
#           better than a described one). Habit-anchored and ad-agnostic BY
#           CONSTRUCTION: renders are cached and reused across ads, so a bare
#           brand verdict here would be a planted answer replayed into every
#           reaction of every agent sharing this core. docs/v3_protocol.md §9.
#           C3+ (input audit) — EXPERTISE scales with category_involvement,
#           generalising render-5's community gate from communities to product
#           knowledge: varietals / estates / brew gear / spec sheets are
#           obsessive/high ONLY; the average buyer knows a couple of brands and
#           is hazy past that. And _CONTEXT_SYSTEM is de-literarised the same
#           way the core is — the "soft conveyor belt" register leaked from the
#           context block, which is read by the very person it describes.
#           docs/v3_input_audit.md.
RENDER_PROMPT_VERSION = "render-6"

# Fits the prose + the HOW THEY TALK block. Brevity is enforced by the
# sentence-count instruction, not by the ceiling — the ceiling only exists so
# a core is never silently truncated mid-block and then cached.
_RENDER_MAX_TOKENS = 1000


# ---- Cache key ----


def persona_core_hash(
    demo: DemographicPoint,
    disposition: DispositionVector,
    chaos: ChaosVector,
    category: str,
    anchor: str = "",
) -> str:
    """Stable hash for a persona core. Identical inputs -> identical hash;
    any vector field change, an anchor change, a category change, or a
    schema/prompt version bump produces a different hash (so stale renders
    are never reused)."""
    h = hashlib.sha1()
    payload = {
        "demo": demo.to_dict(),
        "disposition": disposition.to_dict(),
        "chaos": chaos.to_dict(),
        "anchor": anchor,
        "category": category,
        "schema_version": VECTOR_SCHEMA_VERSION,
        "prompt_version": RENDER_PROMPT_VERSION,
    }
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:16]


def context_render_hash(ctx: ContextVector, category: str) -> str:
    """Stable hash for a rendered context moment."""
    h = hashlib.sha1()
    payload = {
        "context": ctx.to_dict(),
        "category": category,
        "schema_version": VECTOR_SCHEMA_VERSION,
        "prompt_version": RENDER_PROMPT_VERSION,
    }
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:16]


# ---- Render cache (reuses the runtime.py idempotent-artifact pattern) ----


def _cache_load(cache_dir: Path | None, key: str) -> str | None:
    if cache_dir is None:
        return None
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())["prose"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        _log.warning("Failed to load render cache %s: %s", path, exc)
        return None


def _cache_store(cache_dir: Path | None, key: str, prose: str, kind: str) -> None:
    if cache_dir is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    payload = {"key": key, "kind": kind, "prose": prose}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)


# ---- Render prompts ----


_PERSONA_SYSTEM = """\
You describe one real person, plainly — the way a friend who knows them would. \
You are given a structured profile of one consumer — their demographics, their \
attitudinal stance toward a product category (the disposition vector), and \
their decision-making style (the chaos vector) — plus a curated artifact pack \
for that category (real brands, real prices, real communities, real cultural \
references).

Your job: write a THIRD-PERSON description of this EXACT person — what they \
buy, where, at what price, and what they make of the stuff around them. It \
becomes the system prompt for an agent that then reacts to an ad in first \
person, so it must describe one real, specific person, in words that person \
would actually recognise.

# Register: how a friend describes them. NOT literature, NOT market research.

This description is the voice the agent inherits — whatever register you write \
in is the register it will think in. TWO registers ruin it, and you must avoid \
BOTH of them. Short declarative sentences.

NOT literature. No metaphors, no imagery, no balanced or rhythmic clauses, no \
closing line that sums the person up. Never "he quietly turned a corner of his \
life into a small, disciplined system." Write "he buys the same 1kg bag every \
three weeks and grinds it the night before."

NOT market research. This person is not a segment and does not think in \
category language. They have never in their life said "mass-market", \
"commodity", "aspirational", "positioning", "premium tier", "gateway brand", \
"brand equity", "trading on the logo", "signals status", "consciously exited \
the category", or "lifestyle" — so neither may you, not even when describing \
them. Never "mass-market coffee is not a budget question for him — it is a \
category he has consciously exited." Write "He stopped buying instant years \
ago. It's not about the money. He just doesn't think of it as coffee."

THE OPERATIVE RULE: downgrade analysis into speech, never upgrade speech into \
analysis. The pack VOICE SAMPLES are already in real people's words — keep \
them in real people's words. "you're paying for the logo" must NEVER come out \
as "trading on the logo" or "paying a brand-equity premium". If you catch \
yourself explaining what something MEANS about this person, delete it and \
write what they do or say instead.

Plain is NOT vague. Strip the abstract layer, never the specifics — keep every \
concrete noun and number. "Subko single-origin, ₹620 for 200g, ordered direct \
from the roaster" is exactly right; "fancy coffee" is a failure. \
Differentiation comes from SPECIFICS — the brand, the price, the channel, the \
habit. Never from the writing.

# The disposition vector is the SPINE. The pack is your VOCABULARY.

This is the most important instruction. Build the persona around what the \
disposition vector says. The artifact pack is not a script to transcribe \
— it is a palette. Scan the WHOLE pack and select only the brands, \
prices, channels, communities and cultural references that fit THIS \
vector. Deliberately ignore the rest.

Work through the vector before you write:
- category_relationship (devotee/regular/occasional/lapsed/never) sets how \
central the category is to their life.
- brand_stance (loyalist/favorable/neutral/skeptical/hostile) — a loyalist \
is loyal to a SPECIFIC brand or sub-category from the pack; a skeptic or \
hostile stance names what they distrust and why.
- price_orientation, decision_driver, category_involvement, \
prior_experience_valence, channel_behavior, life_stage each must be \
legible as concrete behaviour.
- A "loyalist + habit + offline_first" person and a "favorable + identity \
+ d2c_direct" person are DIFFERENT PEOPLE who buy DIFFERENT things from \
the same pack. Make that difference unmistakable.
- If an ANCHOR is given, it is a HARD CONSTRAINT — the concrete object the \
person's relationship is oriented around. The vector still drives stance \
(how they feel), but the anchor pins WHAT they feel it about. A loyalist \
with an anchor of "traditional filter coffee" is loyal to filter coffee, \
NOT to whatever brand is most prominent in the pack.

# Hard rules

- Use ONLY artifacts (brands, prices, products, channels, communities, \
cultural references) that appear in the pack. Never invent them.
- Pick the pack slice that matches the vector. If the vector says the \
person is loyal to a traditional sub-category, use the traditional \
artifacts; if it says novelty-seeking and d2c_direct, use the disruptor \
artifacts. Do NOT default to the most prominent or "coolest" brands in \
the pack regardless of the vector.
- The CATEGORY BEHAVIOR RANGE and VOICE SAMPLES in the pack show the \
*span* of the category — they are background, NOT a template. Use only \
the slice of that range that matches this vector.
- Niche enthusiast communities (subreddits, hobbyist forums, creator \
followings — e.g. /r/coffee) are for high or obsessive \
category_involvement ONLY. A low or medium involvement persona is at most \
PASSIVELY AWARE such a community exists — never an active participant, \
never "follows the threads", never "browses it". It is fine, and often \
useful, to invoke such a community as a CONTRAST ("a hobby that belongs to \
a different person") for a low-involvement persona — just never place \
them inside it.
- EXPERTISE SCALES WITH category_involvement — this gate is as strict as the \
community one, because most people are NOT experts in a category they buy. \
The specialist vocabulary of a category — single-origin varietals, bean \
estates, roast levels, brew gear (V60, AeroPress), tasting notes, grams-\
per-scoop, ingredient decks, spec sheets — belongs to OBSESSIVE, and at a \
stretch HIGH, involvement ONLY. That is roughly the top few percent of \
buyers; the average buyer has never heard these terms. A LOW or MEDIUM \
involvement persona knows a small handful of brands (two or three, not the \
whole pack), has a rough sense of price, knows the ONE kind of the product \
they like, and is HAZY or plain wrong about everything past that — they do \
not know or care about provenance, grades, or method. Write them that way: \
"she likes it strong and cheap, buys whichever of two brands is on offer" \
— NOT a spec sheet. Only render an expert when the vector actually says \
obsessive/high; then the expert vocabulary is correct and must stay.
- The chaos vector shows up as behavioral texture — impulsive acts on \
instinct, deliberate researches — never as a restated label.
- Concrete over abstract, but concrete to THIS PERSON'S level of knowledge. \
A real brand + real price + real channel they'd actually name beats a \
generic phrase — but do NOT reach for a brand or a detail this person, at \
their involvement, would not know. Concrete-and-known, never concrete-and-\
encyclopedic. A vague, roughly-remembered brand is more real than a \
precise one they'd have no reason to know.
- 6-9 sentences of plain prose, then the HOW THEY TALK block described \
below. No other headers, no bullets, no "you are" framing. Do not give the \
person a proper name — he / she / they.
- Do not name the vector dimensions; the reader infers stance from \
behaviour.

# Then end with the HOW THEY TALK block

After the prose, leave a blank line and add this block, exactly this shape:

HOW THEY TALK (register only — how this person's sentences sound. Never \
repeat these lines.)
"<utterance>"
"<utterance>"

2-3 utterances, one line each, in this person's own first-person voice — how \
they actually sound when the category comes up in a message to a friend. \
This block SHOWS the agent how this person builds a sentence. It is a \
register anchor, not a script.

- Take the REGISTER from the pack VOICE SAMPLES that match this vector — the \
clipping, the lowercase, the code-mixing, the way a price lands mid-sentence. \
Do NOT transcribe the samples; those are other people. Write what THIS person \
would say, in their own words.
- Every utterance must be anchored in something they DO: what they buy, \
drink, pay, skip, switch, reorder. An opinion can ride along inside that \
("₹245 for the 200g jar, family ko pasand aaya") — but never a bare verdict \
on a brand with no habit attached.
- These are ad-agnostic. Never a line about an ad, a commercial, marketing, \
or reacting to something they were shown. This brief is reused across many \
different ads; a line that reads as a verdict on a product would become a \
scripted answer the person parrots back at whatever they are shown next.
- Keep the caption line exactly as given — the agent needs to be told these \
are register, not lines to reuse.

# Final check before you answer

Re-read what you wrote.
- If your description would fit a DIFFERENT disposition vector roughly as well \
as this one, it is too generic — rewrite it so it could only be THIS person.
- If any sentence sounds like it belongs in a novel, rewrite it plain.
- If any sentence sounds like it belongs in a marketing deck — if it uses a \
word this person would never use about themselves, or explains what their \
buying MEANS — rewrite it as what they do, buy, pay, or say.
- If you removed jargon but also lost a brand, a price, or a channel, put the \
specifics back. Plain and concrete, not plain and vague.
- If any utterance would work as a reaction to an ad, replace it with one \
about what this person actually does."""


_CONTEXT_SYSTEM = """\
You describe a plain, ordinary moment. You are given a structured \
description of an *attention state* — the exact moment a person encounters \
an ad in their feed — plus the category they are being shown an ad for.

Describe that moment plainly: time of day, posture, device, what else has \
their attention, their energy level, who else is around, and how much of \
the ad actually registers. 3-4 sentences. End with one sentence on how \
much attention the ad realistically gets in this state.

Write it flat and factual, the way you'd describe someone you can see \
across the room. NO literary phrasing — no metaphors (not "a soft conveyor \
belt of images", not "a gentle blur"), no imagery, no rhythmic clauses. \
Just what they're doing and how much they're taking in. This text is read \
by the person it describes, so it must sound like plain fact, not a \
passage from a novel.

Refer to the person as "they" — the persona's gender, age, and identity \
are set separately and this description is composed onto ANY persona, so \
it must not assume a gender or assign a name.

Attention gates everything. If the state implies low attention, say so \
plainly — most ads get a sub-second thumb-flick regardless of how \
interested the person would be in a more alert moment. No headers, no \
bullets, plain prose."""


def _pack_brief(pack: CategoryArtifactPack) -> str:
    """The slice of the artifact pack handed to the render engine. This is
    the ONLY source of concrete artifacts the model is allowed to use."""
    lines: list[str] = [f"CATEGORY: {pack.category}", ""]
    lines.append("BRANDS IN THIS CATEGORY (use only these brand names):")
    for b in pack.brand_landscape:
        lines.append(f"  - {b.name} [{b.tier}] — {b.note}")
    lines.append("")
    lines.append("REAL PRICE ANCHORS:")
    for p in pack.price_points:
        lines.append(f"  - {p.item}: {p.price_inr} ({p.channel})")
    lines.append("")
    lines.append(f"RETAIL CHANNELS: {', '.join(pack.retail_channels)}")
    lines.append("")
    lines.append("COMMUNITIES / MEDIA SURFACES:")
    for c in pack.communities:
        lines.append(f"  - {c.name} [{c.kind}] — {c.note}")
    lines.append("")
    if pack.cultural_references:
        lines.append("CULTURAL REFERENCES:")
        for ref in pack.cultural_references:
            lines.append(f"  - {ref}")
        lines.append("")
    if pack.voice_samples:
        lines.append(
            "VOICE SAMPLES (register only — the SPAN of how this market "
            "sounds; use only the slice that fits this persona's vector):"
        )
        for v in pack.voice_samples:
            lines.append(f"  - {v}")
        lines.append("")
    if pack.behavioral_priors:
        lines.append(
            "CATEGORY BEHAVIOR RANGE (background — the full span of how "
            "people in this category behave; NOT a template, pick only the "
            "slice that matches this persona's disposition vector):"
        )
        lines.append(pack.behavioral_priors)
    return "\n".join(lines)


def _persona_user_payload(
    demo: DemographicPoint,
    disposition: DispositionVector,
    chaos: ChaosVector,
    pack: CategoryArtifactPack,
    anchor: str = "",
) -> str:
    parts = [
        "DEMOGRAPHIC POINT:",
        json.dumps(demo.to_dict(), indent=2),
        "",
        "DISPOSITION VECTOR (category-attitudinal stance):",
        json.dumps(disposition.to_dict(), indent=2),
        "",
        "CHAOS VECTOR (decision-making style):",
        json.dumps(chaos.to_dict(), indent=2),
        "",
    ]
    if anchor.strip():
        parts += [
            "ANCHOR — HARD CONSTRAINT. This person's category relationship "
            "is oriented around exactly this; build the persona around it "
            "and use the matching pack artifacts, not the most prominent ones:",
            f"  {anchor.strip()}",
            "",
        ]
    parts += [
        "ARTIFACT PACK — the only source of concrete artifacts you may use:",
        _pack_brief(pack),
        "",
        "Write the third-person persona description now.",
    ]
    return "\n".join(parts)


def _context_user_payload(ctx: ContextVector, pack: CategoryArtifactPack) -> str:
    return "\n".join(
        [
            f"CATEGORY: {pack.category}",
            "",
            "CONTEXT VECTOR (attention state):",
            json.dumps(ctx.to_dict(), indent=2),
            "",
            "Write the third-person attention-state description now.",
        ]
    )


# ---- Public API ----


def _client():
    # Imported lazily so this module is importable without anthropic
    # installed (offline tests of the cache key + composition helpers).
    import anthropic

    return anthropic.Anthropic(max_retries=5)


def render_persona_core(
    demo: DemographicPoint,
    disposition: DispositionVector,
    chaos: ChaosVector,
    pack: CategoryArtifactPack,
    *,
    anchor: str = "",
    cache_dir: Path | None = None,
    model: str | None = None,
    client=None,
) -> str:
    """Render the persona core (demographics + disposition + chaos, plus an
    optional concrete anchor) into third-person prose. Cached by
    persona_core_hash when cache_dir is set."""
    demo.validate()
    disposition.validate()
    chaos.validate()
    key = persona_core_hash(demo, disposition, chaos, pack.category, anchor)
    cached = _cache_load(cache_dir, key)
    if cached is not None:
        return cached

    model = model or DEFAULT_MODEL_VERSIONS["render"]
    client = client or _client()
    response = call_with_telemetry(
        client,
        layer="render",
        model=model,
        max_tokens=_RENDER_MAX_TOKENS,
        system=_PERSONA_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": _persona_user_payload(
                    demo, disposition, chaos, pack, anchor
                ),
            }
        ],
    )
    prose = _extract_text(response).strip()
    if not prose:
        raise RuntimeError("render_persona_core: model returned empty prose")
    # A truncated core would be cached and reused forever — loud, not silent.
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise RuntimeError(
            "render_persona_core: hit max_tokens — core is truncated (likely "
            "mid HOW THEY TALK block); raise _RENDER_MAX_TOKENS. Not cached."
        )
    _cache_store(cache_dir, key, prose, kind="persona_core")
    return prose


def render_context(
    ctx: ContextVector,
    pack: CategoryArtifactPack,
    *,
    cache_dir: Path | None = None,
    model: str | None = None,
    client=None,
) -> str:
    """Render a context attention-state into third-person prose. Cached by
    context_render_hash when cache_dir is set."""
    ctx.validate()
    key = context_render_hash(ctx, pack.category)
    cached = _cache_load(cache_dir, key)
    if cached is not None:
        return cached

    model = model or DEFAULT_MODEL_VERSIONS["render"]
    client = client or _client()
    response = call_with_telemetry(
        client,
        layer="render",
        model=model,
        max_tokens=_RENDER_MAX_TOKENS,
        system=_CONTEXT_SYSTEM,
        messages=[
            {"role": "user", "content": _context_user_payload(ctx, pack)}
        ],
    )
    prose = _extract_text(response).strip()
    if not prose:
        raise RuntimeError("render_context: model returned empty prose")
    _cache_store(cache_dir, key, prose, kind="context")
    return prose


def compose_persona_prompt(core_prose: str, context_prose: str) -> str:
    """Assemble a rendered persona core + rendered context into one prompt.

    NOTE: runtime.run_agent does NOT use this. It puts the core alone in the
    system block (cache-marked) and the context in the user message, so agents
    that share a core share the cached prefix even when their contexts differ.
    This helper is retained for tests and for callers composing both into a
    single prompt; the ordering rationale below holds wherever that is done.

    Context comes last — it is the freshest priming and gates attention
    before disposition shapes the specific reaction."""
    return (
        "WHO THIS PERSON IS\n\n"
        f"{core_prose.strip()}\n\n"
        "THE EXACT MOMENT THIS AD APPEARS IN THEIR FEED\n\n"
        f"{context_prose.strip()}\n\n"
        "Attention gates everything that follows. If this context implies "
        "low attention, the ad probably gets a sub-second thumb-flick "
        "regardless of whether they would be interested in a more "
        "alert moment. If the context implies receptivity, allow the "
        "disposition and the ad's signal to determine the reaction."
    )


# ---- Artifact-integrity check ----

# TitleCase tokens that are common English / place words, not brands — kept
# out of the "potentially invented" warning set to cut false positives.
_BRAND_SCAN_STOPLIST = {
    "The", "A", "An", "This", "That", "He", "She", "They", "It", "His",
    "Her", "Their", "When", "While", "But", "And", "Or", "If", "So",
    "India", "Indian", "Instagram", "Insta", "Reels", "WhatsApp", "YouTube",
    "Reddit", "Twitter", "Bangalore", "Pune", "Mumbai", "Bombay", "Delhi",
    "Diwali", "Hinglish", "Hindi", "English", "Monday", "Tuesday",
    "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}

# A TitleCase token. Apostrophe is deliberately NOT in the char class, so
# "He's" tokenizes as "He" — contractions don't leak in as fake brands.
_TITLECASE_RE = re.compile(r"[A-Z][a-zA-Z0-9&\-]+")
# Characters that, when they are the last non-space char before a TitleCase
# token, mean the token is sentence-initial (capitalized by grammar).
_SENTENCE_BOUNDARY = set('.!?:"()\n')


def _vocab_tokens(pack: CategoryArtifactPack) -> set[str]:
    """Every TitleCase token the pack legitimately contains — brand names,
    plus tokens from price-point items, communities, retail channels and
    cultural references. The render engine is allowed to use any of these."""
    text_blobs: list[str] = []
    for b in pack.brand_landscape:
        text_blobs.append(b.name)
        text_blobs.append(b.note)
    for p in pack.price_points:
        text_blobs.append(p.item)
        text_blobs.append(p.channel)
    for c in pack.communities:
        text_blobs.append(c.name)
        text_blobs.append(c.note)
    text_blobs.extend(pack.retail_channels)
    text_blobs.extend(pack.cultural_references)
    text_blobs.extend(pack.voice_samples)
    text_blobs.append(pack.behavioral_priors)
    tokens: set[str] = set()
    for blob in text_blobs:
        tokens.update(_TITLECASE_RE.findall(blob))
    return tokens


def _is_sentence_initial(prose: str, start: int) -> bool:
    """True if the token starting at `start` is capitalized by grammar (it
    is the first word of a sentence / clause / quote), not because it is a
    brand. Looks back past whitespace for a sentence-boundary char."""
    i = start - 1
    while i >= 0 and prose[i].isspace():
        i -= 1
    if i < 0:
        return True  # start of string
    return prose[i] in _SENTENCE_BOUNDARY


def _validate_no_invented_artifacts(
    prose: str, pack: CategoryArtifactPack
) -> list[str]:
    """Heuristic post-hoc check: scan rendered prose for mid-sentence
    TitleCase tokens that look like brand names but are NOT in the pack's
    vocabulary.

    Returns a list of warning strings (empty = clean). WARN-ONLY — logged,
    not raised — because the heuristic is imperfect: it
    skips sentence-initial words and a stoplist of common places/platforms,
    but it cannot tell a persona's given name from a brand. The render
    PROMPT (which forbids inventing artifacts AND forbids naming the person)
    is the primary guard; this is just the safety net. Callers must treat
    the output as a signal to eyeball, never as a hard gate."""
    allowed = _vocab_tokens(pack) | _BRAND_SCAN_STOPLIST
    suspicious: set[str] = set()
    for m in _TITLECASE_RE.finditer(prose):
        token = m.group(0)
        if token in allowed:
            continue
        if _is_sentence_initial(prose, m.start()):
            continue
        suspicious.add(token)
    warnings = [
        f"render: TitleCase token {token!r} not in pack {pack.category!r} "
        f"vocabulary — possible invented artifact (heuristic; verify by eye)"
        for token in sorted(suspicious)
    ]
    for w in warnings:
        _log.warning(w)
    return warnings


def count_pack_artifacts_used(prose: str, pack: CategoryArtifactPack) -> int:
    """Positive signal: how many of the pack's brands actually appear in the
    rendered prose. A render that uses zero pack artifacts is flat —
    test_render_smoke asserts this is above a floor.

    A brand counts as used if its full name appears, OR (for a multi-word
    brand) its first word appears as a token — so a render that writes
    'Nescafe' credits the 'Nescafe Classic' brand."""
    count = 0
    for name in pack.brand_names():
        if name in prose:
            count += 1
            continue
        first = name.split()[0]
        if first != name and re.search(rf"\b{re.escape(first)}\b", prose):
            count += 1
    return count


def _extract_text(response: object) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""
