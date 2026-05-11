"""Cache validation v2: strict per-round prompt constraints, max_tokens=1100,
Sonnet 4.6, single cache marker (drop secondary). Verify R3 (emotion) actually
renders in bundled mode — quality blocker for the bundled architecture.
"""

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

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1100


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
                "ENCODING PHASE — emit three sections, each labelled.\n\n"
                "R1 GUT: exactly 1-2 sentences. Your first-glance reaction "
                "before parsing the ad. Pre-thought, visceral. Stop after the "
                "second period.\n\n"
                "R2 COMPREHENSION: exactly 3 sentences. What message did the "
                "ad land for you? What did you actually take from it? Stop "
                "after the third period.\n\n"
                "R3 EMOTION: free-form prose, 4-5 sentences max. The "
                "emotional texture the ad left on you — what did it stir, "
                "what did it leave flat? Be honest about the feeling."
            ),
        },
    ]

    client = anthropic.Anthropic(max_retries=3)

    print(f"=== Call A: Encoding (model={MODEL}, max_tokens={MAX_TOKENS}) ===")
    t0 = time.time()
    call_a = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": encoding_user}],
    )
    t_a = time.time() - t0
    usage_a = call_a.usage
    call_a_text = next(b.text for b in call_a.content if b.type == "text")
    print(f"Latency: {t_a*1000:.0f}ms · stop_reason={call_a.stop_reason}")
    print(f"Usage: cache_create={getattr(usage_a, 'cache_creation_input_tokens', 0)}, "
          f"cache_read={getattr(usage_a, 'cache_read_input_tokens', 0)}, "
          f"in={usage_a.input_tokens}, out={usage_a.output_tokens}")

    has_r1 = "R1" in call_a_text
    has_r2 = "R2" in call_a_text
    has_r3 = "R3" in call_a_text
    print(f"Round labels present: R1={has_r1}, R2={has_r2}, R3={has_r3}")
    print(f"Output ({len(call_a_text)} chars):\n{call_a_text}\n")

    print(f"=== Call B: Reflection (cache read, no secondary cache marker) ===")
    reflection_user = (
        "REFLECTION PHASE — 48 hours later. Emit three sections, each "
        "labelled.\n\n"
        "R4 STICKINESS: 3-4 sentences. What stuck from that ad, and what "
        "didn't? Be specific. Stop after the fourth period at most.\n\n"
        "R5 SOCIAL: 3-4 sentences. Would you share/screenshot/mention this "
        "ad to anyone? Why or why not? What social cost or upside?\n\n"
        "R6 FRICTION: 4-5 sentences. If you were considering buying, what's "
        "the single biggest friction the ad introduced — and would you act "
        "on it?"
    )

    t0 = time.time()
    call_b = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[
            {"role": "user", "content": encoding_user},
            {"role": "assistant", "content": call_a_text},
            {"role": "user", "content": reflection_user},
        ],
    )
    t_b = time.time() - t0
    usage_b = call_b.usage
    call_b_text = next(b.text for b in call_b.content if b.type == "text")
    print(f"Latency: {t_b*1000:.0f}ms · stop_reason={call_b.stop_reason}")
    print(f"Usage: cache_create={getattr(usage_b, 'cache_creation_input_tokens', 0)}, "
          f"cache_read={getattr(usage_b, 'cache_read_input_tokens', 0)}, "
          f"in={usage_b.input_tokens}, out={usage_b.output_tokens}")
    has_r4 = "R4" in call_b_text
    has_r5 = "R5" in call_b_text
    has_r6 = "R6" in call_b_text
    print(f"Round labels present: R4={has_r4}, R5={has_r5}, R6={has_r6}")
    print(f"Output ({len(call_b_text)} chars):\n{call_b_text}\n")

    PRICE = {"in": 3.0, "out": 15.0, "cache_read": 0.3, "cache_write_5m": 3.75}

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

    cost_a, b_a = cost(usage_a)
    cost_b, b_b = cost(usage_b)
    print("=== Cost analysis ===")
    print(f"Call A: {json.dumps(b_a)} -> ${cost_a:.5f}")
    print(f"Call B: {json.dumps(b_b)} -> ${cost_b:.5f}")
    per_agent = cost_a + cost_b
    print(f"Per-agent total: ${per_agent:.5f}")
    print(f"200 agents projection: ${per_agent*200:.2f}")
    print(f"Plus synthesis ~$1.50 -> run total: ${per_agent*200 + 1.50:.2f}")
    print(f"Reduction vs current $0.0937/agent: {(1 - per_agent/0.0937)*100:.1f}%")

    all_rendered = all([has_r1, has_r2, has_r3, has_r4, has_r5, has_r6])
    print(f"\n{'PASS' if all_rendered else 'FAIL'}: All 6 rounds rendered.")


if __name__ == "__main__":
    main()
