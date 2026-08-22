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
import uuid
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
# render-7: §2.6 — INCOME IS NO LONGER SHOWN TO THE PERSONA WRITER. SimBench
#           measures a per-axis penalty for conditioning a simulated persona on
#           a demographic axis, and income is among the worst of them
#           (ΔS −4.51) while age (−1.50) and gender (−1.24) are the safest.
#           Every persona we rendered carried an LPA band. See
#           docs/research/04_simbench_read.md §3 and the plan's §2.6.
#           ⚠ THE BUMP IS THE CHANGE. Renders are cached by persona_core_hash,
#           which digests this constant — editing the payload without bumping
#           here would serve every core from the old prompt and the change
#           would be completely invisible (agent/provenance.py's whole point).
# render-8: THE CORE IS ADDRESSED TO THE PERSON, NOT WRITTEN ABOUT THEM.
#           Every core through render-7 was THIRD PERSON ("She's been taking
#           hair and skin supplements for about two years...") and sat in the
#           system slot with NO framing around it — `runtime.run_agent` passes
#           `core_prose` as the entire system block, so nothing anywhere told
#           the model that the person described WAS it. The only nudge toward
#           first person was `_ENCODING_USER`'s "You are a real person glancing
#           at an ad", one turn later and in the user message. A third-person
#           brief in the system slot asks a model to PORTRAY someone; "you are"
#           asks it to BE them. The user's call, 2026-08-11, made with the raw
#           1886-char system block in front of them.
#           ⚠ THE ADDRESS IS SECOND PERSON, and that is deliberate — a
#           first-person core ("I have been taking...") followed by a
#           second-person task turn reads as two different speakers. The
#           HOW THEY TALK block stays first person, because it always was:
#           it is this person's own utterances, and only the frame moved.
#           ⚠ THIS IS A SWEEP, NOT ONE STRING. Third person reached the agent
#           from FIVE places and fixing only the core leaves the seams talking
#           about the person in the same breath the core talks to them:
#           `_PERSONA_SYSTEM` (this file), `_CONTEXT_SYSTEM` (this file), and
#           in `agent/runtime.py` the context-block header, `_CYCLE_PROSE` /
#           `_cycle_line`, and the attention-gate sentence.
#           `tests/test_second_person_address.py` pins the four deterministic
#           ones; the two model-written ones can only be pinned as INSTRUCTION
#           offline (the same limit the render-6 contract already concedes).
# render-9: THE UTTERANCES GET SHORT, AND THE ADVERTISING BAN GETS TEETH.
#           render-8's samples showed both problems. (a) 2 of 6 personas emitted
#           an utterance mentioning advertising ("saw the ad, looked
#           interesting... skipped it") where render-7 emitted 0 of 6 — n=1 per
#           cell at temperature 1.0, so NOT a measured regression, but the ban
#           was a single soft line and the cost of it landing is high: the core
#           is CACHED and replayed for every ad this person is ever shown, so a
#           line about advertising is a pre-written stance toward the stimulus.
#           It is now an explicit word list plus a per-line check. (b) Utterances
#           ran 80-140 chars with up to 4 commas, stacking brand + price +
#           channel + verdict into one breath — nobody messages like that, and
#           the register block is the register the agent inherits. Now capped at
#           ~8-14 words, one thought, at most one comma.
#           ⚠ The user's call, 2026-08-11, with all 17 rendered quotes in front
#           of them: "remove the ads from the persona sample quotes, simplify".
# render-10: THE PACK IS A LANDSCAPE, NOT A SHOPPING LIST — and the anchors stop
#           naming brands and shops at all (the anchor half lives in
#           `scripts/scaffold_health_wellness.py`, not here).
#           ⚠ THE USER FOUND THIS IN THE OUTPUT, 2026-08-12: personas kept
#           saying they would "check if it's on Nykaa" about a PROTEIN BAR.
#           Nykaa is a beauty marketplace; nobody buys protein there. Traced:
#           `aspirant_clean_label`'s anchor said "on Nykaa" TWICE, and the
#           anchor is injected as a HARD CONSTRAINT, so it beat this pack's own
#           channel list — 24 of 24 of that disposition's briefs carried it,
#           and the price list two lines away already said the bar sells on
#           quick commerce. The dispositions whose anchors named a different
#           shop scored 0/19 and 0/15 on Nykaa, which is the proof the writer
#           already filters correctly and the anchor was overriding it.
#           ⚠ THE DEFECT IS THE UNIFORMITY, NOT THE MENTION. A hard-coded
#           channel arrives at 24/24 — maximally prevalent — so the §1.1/§1.2
#           prevalence floor cannot catch it; consensus and a pinned constant
#           look identical downstream. It has to be fixed here, upstream.
#           So `_pack_brief` now says TOP BRANDS IN INDIA / MOST-SELLING
#           PLATFORMS IN INDIA, each platform annotated with what it actually
#           sells, and tells the writer to pick what THIS person would use.
#           ⚠ "Do NOT default to the most prominent" is LOAD-BEARING, not
#           padding: personal_audio already ships brand-free anchors, and its
#           cores still put the top 3 brands in 12/12 of every disposition.
#           Removing the pin diversifies the tail, not the head.
#           ⚠ AND THE BUMP IS THE CHANGE, for a reason specific to this one:
#           `persona_core_hash` digests the ANCHOR and the CATEGORY STRING but
#           NOT pack contents or this function's text. The anchor rewrites
#           self-invalidate; the `_pack_brief` reword would otherwise be
#           invisible to every cached core whose anchor did not move — i.e.
#           every other library in the account. `provenance.py` fingerprints
#           only `_PERSONA_SYSTEM`/`_CONTEXT_SYSTEM`, so `run.json` would not
#           have recorded it either.
RENDER_PROMPT_VERSION = "render-10"

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
    cut_moments: list[str] | None = None,
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
    # ⚠⚠ THE CUT WORLD IS PART OF THE INPUT, SO IT MUST BE PART OF THE KEY.
    # `category` names the pack but says nothing about how much of it the
    # persona was shown. Without this, a core rendered against the whole
    # 105-brand world and one rendered against a 3-moment cut share a hash —
    # the cache serves the wrong world and nothing ever notices.
    #
    # ⚠ OMITTED WHEN THERE IS NO CUT, deliberately: every render cached before
    # 2026-08-22 stays valid, so no library re-renders and no before/after
    # comparison silently breaks. Only cut reads get their own entries.
    if cut_moments:
        payload["cut_moments"] = sorted(cut_moments)
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:16]


def context_render_hash(ctx: ContextVector, category: str,
                        cut_moments: list[str] | None = None) -> str:
    """Stable hash for a rendered context moment.

    ⚠ `cut_moments` for the same reason as `persona_core_hash`: the context
    writer is handed the pack too, so a cut changes its input. Omitted when
    absent, so every context cached before 2026-08-22 stays valid."""
    h = hashlib.sha1()
    payload = {
        "context": ctx.to_dict(),
        "category": category,
        "schema_version": VECTOR_SCHEMA_VERSION,
        "prompt_version": RENDER_PROMPT_VERSION,
    }
    if cut_moments:
        payload["cut_moments"] = sorted(cut_moments)
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
    # ⚠ The temp name must be UNIQUE PER WRITER, not per key. Renders run
    # concurrently now, and two runs preparing the same library at the same
    # time (the server permits that) hit the same key from two threads: with a
    # shared `<key>.json.tmp` one writer's partial bytes get renamed into place
    # by the other. Model output is not deterministic, so "same key, same
    # content" does not save us. os.replace stays atomic; only the staging
    # path needed to stop being shared.
    tmp = path.with_suffix(f".json.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


# ---- Render prompts ----


_PERSONA_SYSTEM = """\
You write one real person's life back to them, plainly — the way a friend who \
knows them would say it to their face. You are given a structured profile of \
one consumer — their demographics, their attitudinal stance toward a product \
category (the disposition vector), and their decision-making style (the chaos \
vector) — plus a curated artifact pack for that category (real brands, real \
prices, real communities, real cultural references).

Your job: write a SECOND-PERSON description of this EXACT person, ADDRESSED TO \
THEM — what you buy, where, at what price, and what you make of the stuff \
around you. Begin with "You are" or "You've been" or "You " + a verb.

⚠ THIS TEXT IS THE ENTIRE SYSTEM PROMPT OF THE AGENT THAT THEN REACTS TO AN AD \
AS THIS PERSON, and nothing else frames it. Written in the third person it is a \
character brief, and a model handed a character brief PORTRAYS someone else. \
Written as "you", it is an identity. Never "She's been taking supplements for \
two years" — write "You've been taking supplements for two years."

# Register: how a friend describes them. NOT literature, NOT market research.

This description is the voice the agent inherits — whatever register you write \
in is the register it will think in. TWO registers ruin it, and you must avoid \
BOTH of them. Short declarative sentences.

NOT literature. No metaphors, no imagery, no balanced or rhythmic clauses, no \
closing line that sums the person up. Never "you quietly turned a corner of \
your life into a small, disciplined system." Write "you buy the same 1kg bag \
every three weeks and grind it the night before."

NOT market research. This person is not a segment and does not think in \
category language. They have never in their life said "mass-market", \
"commodity", "aspirational", "positioning", "premium tier", "gateway brand", \
"brand equity", "trading on the logo", "signals status", "consciously exited \
the category", or "lifestyle" — so neither may you, not even when describing \
them. Never "mass-market coffee is not a budget question for you — it is a \
category you have consciously exited." Write "You stopped buying instant years \
ago. It's not about the money. You just don't think of it as coffee."

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
"you like it strong and cheap, buy whichever of two brands is on offer" \
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
- 6-9 sentences of plain prose, then the HOW YOU TALK block described \
below. No other headers, no bullets. Do not give the person a proper name.
- ⚠ ADDRESS THEM AS "you" IN EVERY SENTENCE. Not one "he", "she", "they", \
"this person", "the buyer", or "the consumer" anywhere in the prose. If a \
sentence needs a subject, it is "you". This is the hardest rule to keep for \
6-9 sentences and the easiest to drift out of halfway through — reread and \
fix any sentence that slipped back into describing rather than addressing.
- Do not name the vector dimensions; stance is shown by behaviour, never \
declared.

# Then end with the HOW YOU TALK block

After the prose, leave a blank line and add this block, exactly this shape:

HOW YOU TALK (register only — how your own sentences sound. Never repeat \
these lines.)
"<utterance>"
"<utterance>"

2-3 utterances, one line each, in this person's own first-person voice — how \
they actually sound when the category comes up in a message to a friend. \
⚠ The CAPTION is second person ("how your own sentences sound") because the \
person reads it about themselves; the UTTERANCES stay first person ("i've \
been on the same tub since March") because they are that person speaking. \
Both are correct at once and neither is a slip. This block SHOWS the agent \
how it builds a sentence. It is a register anchor, not a script.

- Take the REGISTER from the pack VOICE SAMPLES that match this vector — the \
clipping, the lowercase, the code-mixing, the way a price lands mid-sentence. \
Do NOT transcribe the samples; those are other people. Write what THIS person \
would say, in their own words.
- Every utterance must be anchored in something they DO: what you buy, \
drink, pay, skip, switch, reorder. An opinion can ride along inside that \
("₹245 for the 200g jar, family ko pasand aaya") — but never a bare verdict \
on a brand with no habit attached.
- ⚠ KEEP THEM SHORT. ONE thought per line. Aim for roughly 8-14 words; a \
line past 90 characters is too long. Do NOT stack brand + price + channel + \
opinion into one breath. Never "biozyme 1kg chocolate, ₹2,699 on healthkart, \
same cart as always with the creatine — i'm not fixing what isn't broken" \
— that is four thoughts comma-spliced together and nobody messages like \
that. Write "same biozyme tub as always, ₹2,699" and let the next line carry \
the next thought. AT MOST ONE COMMA per line. A price or a brand alone is \
plenty of specificity for one line.
- ⚠ NOTHING ABOUT ADVERTISING. THIS IS AN ABSOLUTE BAN, NOT A PREFERENCE. \
The words "ad", "advert", "advertisement", "commercial", "marketing", \
"campaign", "sponsored", "reel", and "promo" must not appear in ANY \
utterance — not as a reaction ("saw the ad, skipped it"), not as a passing \
comparison ("that's a test result, not an ad"), not as scenery. Also no \
"saw", "scrolled past", "came up on my feed", or "they're advertising". \
⚠ WHY THIS IS ABSOLUTE: this core is CACHED and replayed as the system \
prompt for every different ad this person is ever shown. An utterance that \
mentions advertising at all is a pre-written stance toward the thing we are \
about to show them, and they will parrot it back as their reaction. It \
contaminates the measurement before the ad exists. Write only what this \
person does when nobody is showing them anything.
- Keep the caption line exactly as given — the agent needs to be told these \
are register, not lines to reuse.

# Final check before you answer

Re-read what you wrote.
- ⚠ FIRST: scan every sentence of the prose for "he", "she", "they", "him", \
"her", "their", "this person", "the buyer". If ANY of them refers to the \
person you are describing, the whole thing is a character brief instead of an \
identity — rewrite that sentence to address them as "you". This is the one \
check that must pass; everything below is a matter of degree.
- If your description would fit a DIFFERENT disposition vector roughly as well \
as this one, it is too generic — rewrite it so it could only be THIS person.
- If any sentence sounds like it belongs in a novel, rewrite it plain.
- If any sentence sounds like it belongs in a marketing deck — if it uses a \
word this person would never use about themselves, or explains what their \
buying MEANS — rewrite it as what they do, buy, pay, or say.
- If you removed jargon but also lost a brand, a price, or a channel, put the \
specifics back. Plain and concrete, not plain and vague.
- ⚠ LAST, ON THE UTTERANCES, and check each one separately: does it contain \
"ad", "advert", "commercial", "marketing", "campaign", "sponsored", "reel", \
"promo", "saw", or "scrolled"? Delete that line and write one about a \
purchase, a habit, or a price instead. Is it longer than 90 characters or \
does it hold more than one comma? Cut it down to a single thought."""


_CONTEXT_SYSTEM = """\
You describe a plain, ordinary moment. You are given a structured \
description of an *attention state* — the exact moment a person encounters \
an ad in their feed — plus the category they are being shown an ad for.

Describe that moment plainly: time of day, posture, device, what else has \
their attention, their energy level, who else is around, and how much of \
the ad actually registers. 3-4 sentences. End with one sentence on how \
much attention the ad realistically gets in this state.

Write it flat and factual. NO literary phrasing — no metaphors (not "a soft \
conveyor belt of images", not "a gentle blur"), no imagery, no rhythmic \
clauses. Just what you're doing and how much you're taking in. This text is \
read by the person it describes, so it must sound like plain fact, not a \
passage from a novel.

⚠ ADDRESS THE PERSON AS "you" — "You are lying down, phone above your face." \
NEVER "they", "he", "she", or "the person". This composes onto ANY persona, \
so it must not assume a gender or assign a name, and "you" is the only \
address that is gender-neutral WITHOUT talking about them in the third \
person. (Through render-7 this block said "they" for exactly that \
gender-neutrality, which is why the fix is an address change and not a \
pronoun swap.)

Attention gates everything. If the state implies low attention, say so \
plainly — most ads get a sub-second thumb-flick regardless of how \
interested you would be in a more alert moment. No headers, no \
bullets, plain prose."""


def _pack_brief(pack: CategoryArtifactPack) -> str:
    """The slice of the artifact pack handed to the render engine. This is
    the ONLY source of concrete artifacts the model is allowed to use."""
    lines: list[str] = [f"CATEGORY: {pack.market_name or pack.category}", ""]
    # render-10: the brand and platform lists are a LANDSCAPE, not a
    # shopping list. They used to read "use only these brand names", which
    # is a mandate — and a mandate plus a brand-naming anchor is how one
    # persona ended up checking a beauty marketplace for a protein bar in
    # 24 of 24 briefs. Inform the writer what exists and let THIS person
    # select; the "do not default to the most prominent" clause is
    # load-bearing, because a brand-free anchor alone lets the two or three
    # most famous names saturate every persona (measured on personal_audio).
    lines.append(
        "TOP BRANDS IN INDIA — this is the landscape, not a shopping list. "
        "Pick only what THIS person would plausibly use or mention, or none "
        "at all. Do NOT default to the most prominent names, and do NOT use "
        "a brand this person's stance would not have led them to."
    )
    for b in pack.brand_landscape:
        lines.append(f"  - {b.name} [{b.tier}] — {b.note}")
    lines.append("")
    lines.append("REAL PRICE ANCHORS:")
    for p in pack.price_points:
        lines.append(f"  - {p.item}: {p.price_inr} ({p.channel})")
    lines.append("")
    lines.append(
        "MOST-SELLING PLATFORMS IN INDIA — where this category actually "
        "sells, and what each one is known for. Pick the one THIS person "
        "would already have open for THIS kind of product; a platform that "
        "does not sell the product is the wrong answer."
    )
    for ch in pack.retail_channels:
        lines.append(f"  - {ch}")
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


# §2.6 — the axes withheld from the persona WRITER. SimBench's conditioning
# penalties: income −4.51 (with political −4.97 and religiosity −9.91 worse, and
# neither is an axis we carry), against age −1.50 and gender −1.24, the two
# safest. Income was in every persona we rendered.
#
# ⚠ INCOME IS NOT REMOVED FROM THE ENGINE — only from this one prompt. It still
# selects the panel (`panel.demographic_overlap` matches on gender × age ×
# income), still keeps each demographic bundle internally coherent, still rides
# in `panel.json`, still keys `persona_core_hash`, and still reaches the
# target-ID classifier through `declared_targeting`. Those are SELECTION and
# CLASSIFICATION. The measured penalty is a SIMULATION penalty, and it is only
# paid where a model is asked to BE the person — which is here.
_WRITER_SUPPRESSED_DEMOGRAPHIC_KEYS = frozenset({
    "income_lpa_min", "income_lpa_max", "income_tier",
})


def persona_writer_demographics(demo: DemographicPoint) -> dict:
    """The demographic point AS THE PERSONA WRITER SEES IT.

    ⚠ Built here rather than by narrowing `DemographicPoint.to_dict()`: that
    dict is the serialization contract for `panel.json`, for
    `persona_core_hash`, and for the `from_dict` round-trip, so narrowing it
    would break panel selection and replay of every run already on disk. The
    redaction belongs at the prompt seam and nowhere else."""
    return {
        k: v for k, v in demo.to_dict().items()
        if k not in _WRITER_SUPPRESSED_DEMOGRAPHIC_KEYS
    }


def _persona_user_payload(
    demo: DemographicPoint,
    disposition: DispositionVector,
    chaos: ChaosVector,
    pack: CategoryArtifactPack,
    anchor: str = "",
) -> str:
    parts = [
        "DEMOGRAPHIC POINT:",
        json.dumps(persona_writer_demographics(demo), indent=2),
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
            f"CATEGORY: {pack.market_name or pack.category}",
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
    optional concrete anchor) into SECOND-PERSON prose addressed to the person
    ("You've been taking..."), because this string becomes the entire system
    prompt of the agent that then reacts as them — render-8. Cached by
    persona_core_hash when cache_dir is set."""
    demo.validate()
    disposition.validate()
    chaos.validate()
    key = persona_core_hash(demo, disposition, chaos, pack.category, anchor,
                            cut_moments=list(pack.cut_moments))
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
    key = context_render_hash(ctx, pack.category,
                              cut_moments=list(pack.cut_moments))
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


# ⚠⚠ `compose_persona_prompt` WAS DELETED 2026-08-22 AND MUST NOT COME BACK.
# It assembled a core + context into one prompt, had ZERO production callers
# (its own docstring said so: "runtime.run_agent does NOT use this"), and was
# kept alive only by `tests/test_render_cache.py::test_compose_persona_prompt`,
# which asserted its block ordering and passed for months.
# ⭐ The header it built — "WHO THIS PERSON IS" — occurred nowhere else in
# `agent/`, so no persona ever saw it. And it was written in the THIRD person
# ("their feed", "they would be interested") while the shipped path is second
# person, a rule `tests/test_second_person_address.py` enforces — dead code
# that would have violated an enforced law the moment anyone wired it up.
# ⭐⭐ The real assembly is `runtime.build_encoding_prompt`: core alone in the
# cache-marked system block, context in the user message, so agents sharing a
# core share the cached prefix. A test that guards code nothing runs is a lie
# the next session will believe.
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
