"""Assemble a system prompt that primes Claude to inhabit a consumer identity.

Strategy: data-first. The prompt is mostly raw data (demographic facts,
behavioral priors, voice samples, cultural context, optional category
disposition). No "you are X" framing — the model infers identity from
the artifacts.
"""

from archetypes.behavior import get_behavioral_priors
from archetypes.culture import get_cultural_context
from archetypes.demographics import get_demographic_anchor
from archetypes.voice import get_voice_samples


def build_agent_prompt(
    archetype: str,
    ad_content: str,
    disposition: tuple[str, str] | None = None,
    context: tuple[str, str] | None = None,
) -> str:
    """Assemble a system prompt for the agent.

    The prompt is mostly raw data — no "you are X" framing. Identity
    emerges from the artifacts.

    Layer order (general → specific → most-recent):
      1. PROFILE (demographic anchor)
      2. BEHAVIOR (Insta usage priors)
      3. VOICE SAMPLES (register only — most ads don't produce speech)
      4. CULTURE (what they're living through right now)
      5. DISPOSITION (category-conditional facet — *if provided*)
      6. CONTEXT (immediate situation — gates attention — *if provided*)

    Context is intentionally last: it's the freshest priming before the ad,
    governing attention level. Disposition shapes the specific reaction
    once attention is given.
    """
    demo = get_demographic_anchor(archetype)
    samples = get_voice_samples(archetype, ad_content)
    culture = get_cultural_context(archetype)
    behavior = get_behavioral_priors(archetype)

    income_lakh = demo["income_inr_annual"] // 100_000
    spend_k = demo["discretionary_spend_inr_monthly"] // 1_000

    demo_block = (
        "PROFILE\n\n"
        f"Age: {demo['age']} · {demo['gender'].capitalize()} · "
        f"{demo['city']} ({demo['neighborhood']})\n"
        f"Job: {demo['occupation']}\n"
        f"Income: ₹{income_lakh}L/yr · Discretionary: ~₹{spend_k}k/month\n"
        f"Living: {demo['living_situation']} · {demo['household_obligations']}\n"
        f"Education: {demo['education']}\n"
        f"Status: {demo['marital_status']}\n"
        f"Tech: {demo['tech_signals']}"
    )

    behavior_block = "HOW THIS PERSON BEHAVES ON THEIR PHONE\n\n" + behavior

    samples_block = (
        "RECENT THINGS THIS PERSON WROTE ONLINE "
        "(across Reddit, Twitter, Insta, Zomato, Swiggy, WhatsApp groups). "
        "Use these to calibrate tone if they speak — most of the time, they don't.\n\n"
        + "\n\n".join(f"> {s}" for s in samples)
    )

    culture_block = (
        "WHAT THIS PERSON IS LIVING THROUGH RIGHT NOW\n\n" + culture
    )

    blocks = [demo_block, behavior_block, samples_block, culture_block]

    if disposition is not None:
        _, text = disposition
        disposition_block = (
            "WHERE THIS PERSON SITS WITHIN THIS PRODUCT CATEGORY (today's frame)\n\n"
            + text
        )
        blocks.append(disposition_block)

    if context is not None:
        _, text = context
        context_block = (
            "THE EXACT MOMENT THIS AD APPEARS IN THEIR FEED\n\n"
            + text
            + "\n\n"
            "Attention gates everything that follows. If this context implies "
            "low attention, the ad probably gets a sub-second thumb-flick "
            "regardless of whether the persona would be interested in a more "
            "alert moment. If the context implies receptivity, allow the "
            "disposition + the ad's signal to determine the reaction."
        )
        blocks.append(context_block)

    return "\n\n".join(blocks)
