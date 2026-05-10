"""Run the agent: build prompt, call Anthropic API, return the response."""

import base64
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from agent.prompt import build_agent_prompt
from agent.telemetry import call_with_telemetry
from archetypes.context import sample_context
from archetypes.disposition import sample_disposition


_MODEL = "claude-sonnet-4-6"

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


_SCHEMA_INSTRUCTIONS = (
    "You're mid-Insta-scroll. This just appeared in your feed. Simulate what "
    "you actually do — most ads get a sub-second thumb-flick with no thought. "
    "Don't write a review. Don't be clever. If nothing happens, say nothing happened.\n\n"
    "Output EXACTLY this format, four lines, nothing else:\n\n"
    "attention: <scroll-past | pause | stop | scroll-back>\n"
    "time: <<0.5s | 0.5-2s | 2-5s | >5s>\n"
    "action: <none | screenshot | save | tap-profile | share | comment>\n"
    "signal: <see below>\n\n"
    "If attention == scroll-past: signal is a 1-3 word reason for the "
    "non-engagement, in your own register. Examples: 'boomer brand', "
    "'another d2c', 'wrong vibe', 'mom-coded', 'seen 5 of these', 'no price visible'. "
    "Be specific to THIS ad — not a generic label.\n\n"
    "If attention != scroll-past: signal answers ONE question — "
    "before you sleep tonight, does this become a screenshot, a search "
    "(blinkit/myntra/amazon/the brand site), a group-chat send, or nothing? "
    "Pick exactly one of: screenshot | search | group-chat | nothing. "
    "Optionally add up to 8 words of internal thought after a dash. "
    "Example: 'search — wonder what 5 sachets cost'.\n\n"
    "No preamble, no explanation, no extra lines. Just the four fields."
)


_ROUND_2_INSTRUCTIONS = (
    "Still you — same head, same scroll, a beat later.\n\n"
    "Different mode now. Forget how the ad looks or feels for a moment — "
    "the visuals, the colours, the vibe. Just the message.\n\n"
    "What's the brand actually trying to tell you here? What's the single "
    "claim they're making? And do you actually believe it?\n\n"
    "Free text, 2-3 sentences in your own voice. No fields, no labels, no "
    "format from the last turn. Cover three things: what you think they're "
    "claiming, whether you buy it, and any gap between what they're trying "
    "to say and what's actually landing for you."
)


_ROUND_3_DIMENSIONS = ("relevance", "trust", "curiosity", "irritation", "aspiration")

_ROUND_3_INSTRUCTIONS = (
    "Still you — last pass on this ad, then back to the scroll.\n\n"
    "One more task. Score the ad on five emotional dimensions, each 1-10, "
    "with a one-sentence reason in your own voice for each:\n\n"
    "- relevance: does this feel like it's talking to YOU specifically "
    "(1 = not at all, 10 = very much)\n"
    "- trust: do you believe this brand "
    "(1 = skeptical, 10 = fully trust)\n"
    "- curiosity: do you want to know more "
    "(1 = zero interest, 10 = actively want to)\n"
    "- irritation: does anything feel forced, fake, or patronising "
    "(1 = none, 10 = high)\n"
    "- aspiration: does this make you want to be associated with this brand "
    "(1 = no, 10 = yes)\n\n"
    "Return EXACTLY this JSON object — no preamble, no commentary, no "
    "markdown fences, no text before or after. Just the JSON:\n\n"
    "{\n"
    '  "relevance":  {"score": <1-10>, "reason": "<one sentence in your voice>"},\n'
    '  "trust":      {"score": <1-10>, "reason": "<one sentence in your voice>"},\n'
    '  "curiosity":  {"score": <1-10>, "reason": "<one sentence in your voice>"},\n'
    '  "irritation": {"score": <1-10>, "reason": "<one sentence in your voice>"},\n'
    '  "aspiration": {"score": <1-10>, "reason": "<one sentence in your voice>"}\n'
    "}\n\n"
    "Reasons must sound like the same person from the last two turns — same "
    "voice, same disposition. Scores must be coherent with what you said "
    "before; no contradictions with your earlier reactions."
)

_ROUND_3_STRICT_SUFFIX = (
    "\n\nYour response must be valid JSON only. "
    "No other text before or after the JSON object."
)


_ROUND_4_INSTRUCTIONS = (
    "Still you — two days later. You haven't thought about that ad once "
    "since you saw it.\n\n"
    "Out of nowhere — brushing teeth, on a call, whatever — the memory of "
    "it surfaces. What, if anything, actually stuck?\n\n"
    "Be honest. Most ads leave nothing. The truthful answer is very often "
    '"almost nothing" or "just the brand name." Don\'t pretend to remember '
    "more than you do; sycophantic recall is the wrong answer here.\n\n"
    "Your recall should match how engaged you actually were when you saw "
    "it — someone who paused for a beat and moved on doesn't remember "
    "much.\n\n"
    "Free text, 2-3 sentences in your own voice. No fields, no labels. "
    "First sentence answers the binary: did anything stick or not. If "
    "something did, the rest says what (visual, claim, tagline, phrase, "
    "feeling) and — more important — WHY you think it stayed. The why "
    "matters more than the what."
)


_ROUND_5_INSTRUCTIONS = (
    "Still you. One more after this, then we're done.\n\n"
    "Almost every ad you see dies in the scroll. A small fraction enters "
    "your social world — a screenshot to one person, a brand-name drop in "
    "conversation, a public post. Honestly assess which bucket THIS ad "
    "falls into for you.\n\n"
    "Three behaviors, answer all three concretely:\n"
    "- Screenshot: would you screenshot it? If yes, who specifically do "
    "you send it to and what do you actually type?\n"
    "- Conversation: would you mention this brand or product unprompted "
    "to anyone in the next week? Who, in what setting?\n"
    "- Public post: story, tweet, anything visible to your wider circle? "
    "Or no?\n\n"
    "Most ads get mostly negative answers — sharing is the exception, not "
    "the rule. Don't manufacture share-worthiness.\n\n"
    "The WHY matters more than the what. People share things that reflect "
    "well on them or genuinely surprise them. People stay silent on things "
    "that make them look basic. Your reason for sharing or not sharing "
    "should reveal how you want to be seen socially — not generic 'good "
    "ad / bad ad' evaluation.\n\n"
    "Coherence with the previous rounds: if you barely remembered the ad, "
    "you don't enthusiastically share it. If you scored high on aspiration, "
    "you don't dismiss it as beneath you. Stay consistent with the person "
    "you've been across rounds 1-4.\n\n"
    "Free text, 3-4 sentences MAX, in your own voice. No labels, no fields. "
    "Cover all three behaviors but tightly."
)


_ROUND_6_INSTRUCTIONS = (
    "Still you. Last round.\n\n"
    "Step out of the scroll for a second. Forget whether you'd buy this "
    "right now — almost no one buys anything from a single ad. The real "
    "question is: NEXT time you're buying something in this category, has "
    "this ad moved this brand toward or away from your shortlist, and "
    "what would actually have to be true for you to seriously consider "
    "it?\n\n"
    "Three things, in order, in 4-5 sentences total:\n\n"
    "1. CONDITION for serious consideration (1-2 sentences). What "
    "specifically would have to change — about your situation, the "
    "product, or what you know about it — for this brand to make your "
    "shortlist next time? Be concrete and unglamorous: a friend's "
    "recommendation, finding it at a price-per-cup you can math out, "
    "a sample at an event, seeing it in a moment when the format "
    "actually fits your life. Real paths to conversion, not 'better "
    "marketing.'\n\n"
    "2. SINGLE biggest friction (1-2 sentences). One thing only — pick "
    "the ONE thing standing between attention and wallet for you. Don't "
    "list. Forcing yourself to pick one is the point. It might be price "
    "opacity, format mismatch, identity mismatch, brand fatigue, lack of "
    "evidence, an objection the ad raised, something else.\n\n"
    "3. AD'S CONTRIBUTION (1 sentence). Did THIS ad reduce that friction "
    "or add to it? Did it clarify a value, address an objection, or did "
    "it introduce a concern that wasn't there before?\n\n"
    "Coherence with previous rounds matters. Irritations you flagged in "
    "round 3 should resurface here if they're load-bearing. Low recall in "
    "round 4 connects to 'I forgot about it' as a real friction. The "
    "social silence in round 5 connects to 'no one I trust will tell me "
    "this is good.' Don't contradict the person you've been across rounds "
    "1-5.\n\n"
    "Free text, 4-5 sentences MAX, in your own voice. No labels, no "
    "section headers, no bullets in your answer — just prose that moves "
    "through condition → friction → ad's contribution. Be specific enough "
    "that a brand team could act on it. Not 'improve messaging' — "
    "something like 'price absence means I exit to Google before I exit "
    "to cart, and I don't always come back.'"
)


_log = logging.getLogger(__name__)


@dataclass
class RunResult:
    output: str
    disposition: tuple[str, str] | None
    context: tuple[str, str] | None
    messages: list  # cumulative history including this round's assistant turn
    round_num: int
    parsed: dict | None = None  # populated for rounds with structured output (round 3)

    @property
    def disposition_label(self) -> str | None:
        return self.disposition[0] if self.disposition else None

    @property
    def context_label(self) -> str | None:
        return self.context[0] if self.context else None


def _visual_scenario_text() -> str:
    return _SCHEMA_INSTRUCTIONS


def _text_scenario_text(ad_content: str) -> str:
    return (
        "Ad in your feed:\n\n═══\n"
        f"{ad_content}\n"
        "═══\n\n" + _SCHEMA_INSTRUCTIONS
    )


def _image_block(image_path: str) -> dict:
    path = Path(image_path)
    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise ValueError(
            f"Unsupported image extension {path.suffix!r}. "
            f"Supported: {sorted(_MEDIA_TYPES)}"
        )
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _parse_round_3(raw: str) -> dict | None:
    """Strict-parse the round 3 JSON. Return dict on success, None on any
    parse or schema failure. Schema check: five expected keys, each with an
    int `score` and a string `reason`. Score range is enforced by the prompt,
    not here (per advisor: don't retry on a score=11)."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    for dim in _ROUND_3_DIMENSIONS:
        entry = obj.get(dim)
        if not isinstance(entry, dict):
            return None
        score = entry.get("score")
        reason = entry.get("reason")
        if not isinstance(score, int) or not isinstance(reason, str):
            return None
    return obj


def _api_text(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""


def run_agent(
    archetype: str,
    ad_content: str,
    round_num: int,
    image_path: str | None = None,
    category: str | None = None,
    disposition: tuple[str, str] | None = None,
    context: tuple[str, str] | None = None,
    sample_context_if_missing: bool = True,
    prior: RunResult | None = None,
    model: str | None = None,
    agent_id: int | None = None,
) -> RunResult | None:
    """Run a single round of the agent against an ad.

    Round 1: gut reaction — structured 4-field output gated by context.
    Round 2: comprehension audit — free text on what message landed.
    Round 3: emotional mapping — strict JSON, 5 dimensions × {score, reason}.
    Round 4: stickiness / recall — free text, two days later, what (if
        anything) actually stuck and why.
    Round 5: social calculus — free text on screenshot / conversation /
        public-post behavior; reasoning should reveal social identity.
    Round 6: purchase-friction mapping — free text on condition for serious
        consideration, single biggest friction, ad's contribution to it.

    Strategist critique (single most important change + brand's deeper
    misunderstanding) lives in `agent/synthesis.py` and operates on
    aggregated population reactions, not on a single agent flipping into
    strategist mode. Per-agent rounds end at 6.

    Layered priming (round 1):
      - `category` (e.g. "coffee") → dispositional sampling when
        `disposition` is not supplied.
      - `context` → if not supplied and `sample_context_if_missing=True`,
        sampled from the archetype's context pool.

    Chaining (rounds 2, 3, 4, 5, 6):
      - Pass `prior` = the previous round's RunResult. The new round reuses
        the prior's disposition/context tuples (no resampling), threads
        `prior.messages` into the conversation history, and appends a new
        user turn with the round-specific instructions. This keeps the
        persona stable and lets later rounds reference earlier reactions.

    Round 3 has a JSON-output retry loop: on parse/schema failure, retries
    up to 2× with a stricter instruction appended to the prompt. Returns
    None if all 3 attempts fail (logged), so the pipeline doesn't crash.

    Pre-supplied `disposition` / `context` overrides sampling — that's how
    the eval harness orchestrates stratified coverage.
    """
    if round_num not in (1, 2, 3, 4, 5, 6):
        raise NotImplementedError(
            f"Round {round_num} not implemented — only rounds 1, 2, 3, 4, 5, 6."
        )

    if round_num in (2, 3, 4, 5, 6):
        if prior is None:
            raise ValueError(
                f"Round {round_num} requires `prior` (the previous round's RunResult)."
            )
        if prior.round_num != round_num - 1:
            raise ValueError(
                f"Round {round_num} must chain off round {round_num - 1}, "
                f"got prior.round_num={prior.round_num}."
            )
        # Persona stability: reuse the exact disposition + context.
        disposition = prior.disposition
        context = prior.context
    else:
        if disposition is None and category is not None:
            disposition = sample_disposition(archetype, category)
        if context is None and sample_context_if_missing:
            context = sample_context(archetype)

    system = build_agent_prompt(
        archetype, ad_content, disposition=disposition, context=context
    )
    # max_retries=5 (default 2): the Anthropic SDK retries 429s with
    # exponential backoff, but the default 2 retries don't span a 60-second
    # ITPM window. Bumping to 5 gives ~32s of cumulative backoff, enough to
    # ride out a typical ITPM bucket.
    client = anthropic.Anthropic(max_retries=5)
    use_model = model or _MODEL

    if round_num == 1:
        if image_path:
            user_content = [
                _image_block(image_path),
                {"type": "text", "text": _visual_scenario_text()},
            ]
        else:
            user_content = _text_scenario_text(ad_content)
        messages_in = [{"role": "user", "content": user_content}]
        response = call_with_telemetry(
            client,
            layer="agent",
            model=use_model,
            agent_id=agent_id,
            round_num=1,
            max_tokens=200,
            thinking={"type": "disabled"},
            system=system,
            messages=messages_in,
        )
        output = _api_text(response)
        messages_out = messages_in + [{"role": "assistant", "content": output}]
        return RunResult(
            output=output,
            disposition=disposition,
            context=context,
            messages=messages_out,
            round_num=1,
        )

    if round_num in (2, 4, 5, 6):
        prompts = {
            2: _ROUND_2_INSTRUCTIONS,
            4: _ROUND_4_INSTRUCTIONS,
            5: _ROUND_5_INSTRUCTIONS,
            6: _ROUND_6_INSTRUCTIONS,
        }
        # r2/r4: 2-3 sentences. r5: 3-4. r6: 4-5.
        token_caps = {2: 300, 4: 300, 5: 350, 6: 400}
        max_tokens = token_caps[round_num]
        messages_in = prior.messages + [{"role": "user", "content": prompts[round_num]}]
        response = call_with_telemetry(
            client,
            layer="agent",
            model=use_model,
            agent_id=agent_id,
            round_num=round_num,
            max_tokens=max_tokens,
            thinking={"type": "disabled"},
            system=system,
            messages=messages_in,
        )
        output = _api_text(response)
        messages_out = messages_in + [{"role": "assistant", "content": output}]
        return RunResult(
            output=output,
            disposition=disposition,
            context=context,
            messages=messages_out,
            round_num=round_num,
        )

    # round 3: emotional mapping with JSON-output retry loop.
    last_output = ""
    last_messages_in: list = []
    for attempt in range(3):
        prompt = _ROUND_3_INSTRUCTIONS
        if attempt > 0:
            prompt = prompt + _ROUND_3_STRICT_SUFFIX
        messages_in = prior.messages + [{"role": "user", "content": prompt}]
        response = call_with_telemetry(
            client,
            layer="agent",
            model=use_model,
            agent_id=agent_id,
            round_num=3,
            retries=attempt,
            max_tokens=500,
            thinking={"type": "disabled"},
            system=system,
            messages=messages_in,
        )
        output = _api_text(response)
        last_output = output
        last_messages_in = messages_in
        parsed = _parse_round_3(output)
        if parsed is not None:
            messages_out = messages_in + [{"role": "assistant", "content": output}]
            return RunResult(
                output=output,
                disposition=disposition,
                context=context,
                messages=messages_out,
                round_num=3,
                parsed=parsed,
            )
        _log.warning(
            "Round 3 JSON parse/schema failed (attempt %d/3) for archetype=%s "
            "disposition=%s context=%s. Raw output: %r",
            attempt + 1,
            archetype,
            disposition[0] if disposition else None,
            context[0] if context else None,
            output,
        )

    _log.error(
        "Round 3 failed all 3 attempts for archetype=%s disposition=%s context=%s. "
        "Last raw output: %r",
        archetype,
        disposition[0] if disposition else None,
        context[0] if context else None,
        last_output,
    )
    return None
