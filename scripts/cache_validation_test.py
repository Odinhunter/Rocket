"""Cache validation: confirm persona+context+image prefix tokenizes in the
estimated 2,500-3,500 range and that cache_read works as expected for a
two-call bundled architecture (Encoding + Reflection)."""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic
from dotenv import load_dotenv

from agent.prompt import build_agent_prompt
from archetypes.disposition import _PROFILES
from archetypes.context import _CONTEXTS

load_dotenv()

MODEL = "claude-sonnet-4-5"  # Sonnet 4.6 alias as of this snapshot


def image_block(path: str, cache: bool = False) -> dict:
    data = base64.standard_b64encode(Path(path).read_bytes()).decode("ascii")
    block = {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": data},
    }
    if cache:
        block["cache_control"] = {"type": "ephemeral"}
    return block


def main() -> None:
    disp = [
        d for d in _PROFILES[("urban_indian_male_22_30", "personal_audio")]
        if d[0] == "brand_loyal_boat_user"
    ][0]
    ctx = [
        c for c in _CONTEXTS["urban_indian_male_22_30"]
        if c[0] == "pre_purchase_research"
    ][0]
    system_text = build_agent_prompt(
        archetype="urban_indian_male_22_30",
        ad_content="Boat Airdopes Prime 512 Special Deal Price ₹1,199",
        disposition=disp,
        context=ctx,
    )

    system = [
        {
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    encoding_user = [
        image_block("assets/boat_ad.png", cache=True),
        {
            "type": "text",
            "text": (
                "ENCODING PHASE — emit three sections.\n\n"
                "R1 GUT (≤60 tokens, 1-2 sentences): your first-glance reaction "
                "before parsing the ad. Pre-thought, visceral.\n\n"
                "R2 COMPREHENSION (≤150 tokens, 3-4 sentences): what message "
                "did the ad land for you? What did you actually take from it?\n\n"
                "R3 EMOTION (≤200 tokens, free prose): the emotional texture "
                "this ad left on you — what did it stir, what did it leave flat?"
            ),
        },
    ]

    client = anthropic.Anthropic(max_retries=3)

    print("=== Call A: Encoding (write cache) ===")
    t0 = time.time()
    call_a = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=system,
        messages=[{"role": "user", "content": encoding_user}],
    )
    t_a = time.time() - t0
    usage_a = call_a.usage
    print(f"Latency: {t_a*1000:.0f}ms")
    print(f"Usage: {usage_a}")
    call_a_text = next(b.text for b in call_a.content if b.type == "text")
    print(f"Output ({len(call_a_text)} chars):")
    print(call_a_text[:600] + ("..." if len(call_a_text) > 600 else ""))

    print("\n=== Call B: Reflection (read cache) ===")
    reflection_user = (
        "REFLECTION PHASE — 48 hours later. Emit three sections.\n\n"
        "R4 STICKINESS (≤180 tokens): what stuck from that ad, and what "
        "didn't? Be specific.\n\n"
        "R5 SOCIAL (≤200 tokens): would you share/screenshot/mention this "
        "ad to anyone? Why or why not? What social cost or upside?\n\n"
        "R6 FRICTION (≤250 tokens): if you were considering buying, what's "
        "the single biggest friction the ad introduced — and would you act?"
    )

    t0 = time.time()
    call_b = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=system,
        messages=[
            {"role": "user", "content": encoding_user},
            {"role": "assistant", "content": call_a_text},
            {"role": "user", "content": reflection_user},
        ],
    )
    t_b = time.time() - t0
    usage_b = call_b.usage
    print(f"Latency: {t_b*1000:.0f}ms")
    print(f"Usage: {usage_b}")
    call_b_text = next(b.text for b in call_b.content if b.type == "text")
    print(f"Output ({len(call_b_text)} chars):")
    print(call_b_text[:600] + ("..." if len(call_b_text) > 600 else ""))

    print("\n=== Cost analysis ===")
    # Sonnet 4.x pricing per MTok
    PRICE = {
        "in": 3.0,
        "out": 15.0,
        "cache_read": 0.3,
        "cache_write_5m": 3.75,
    }

    def cost(usage) -> tuple[float, dict]:
        in_t = getattr(usage, "input_tokens", 0) or 0
        out_t = getattr(usage, "output_tokens", 0) or 0
        cr = getattr(usage, "cache_read_input_tokens", 0) or 0
        cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
        c = (
            in_t * PRICE["in"]
            + out_t * PRICE["out"]
            + cr * PRICE["cache_read"]
            + cw * PRICE["cache_write_5m"]
        ) / 1_000_000
        return c, {"in": in_t, "out": out_t, "cache_read": cr, "cache_write": cw}

    cost_a, breakdown_a = cost(usage_a)
    cost_b, breakdown_b = cost(usage_b)
    print(f"Call A: {json.dumps(breakdown_a)} -> ${cost_a:.5f}")
    print(f"Call B: {json.dumps(breakdown_b)} -> ${cost_b:.5f}")
    per_agent = cost_a + cost_b
    print(f"Per-agent total: ${per_agent:.5f}")
    print(f"200 agents projection: ${per_agent*200:.2f}")
    print(f"120 agents projection: ${per_agent*120:.2f}")

    # Compare to current per-agent: $0.0937
    print(f"\nReduction vs current $0.0937/agent: "
          f"{(1 - per_agent/0.0937)*100:.1f}%")


if __name__ == "__main__":
    main()
