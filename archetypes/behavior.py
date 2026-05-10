"""Behavioral priors — what this person actually *does* on Instagram.

The priors describe attention patterns, recent ad engagement history, and
post-impression behavior. Without these, the model defaults to writing
witty thought-bubbles for every ad — which is a creative-writing artifact,
not a behavior simulation. With these, "scroll-past, no thought, no action"
becomes a valid (and common) output.

Stubbed here. Later swap for: session-log analysis, panel data, or
real attention-tracking traces.
"""


_PRIORS: dict[str, str] = {
    "middle_class_indian_homemaker_38_55": (
        "DAILY PHONE PATTERN\n"
        "- WhatsApp is primary: 20-30 short sessions/day, family group + school parent group +\n"
        "  husband's office wives group + extended-family-from-Nashik group. Forwarded videos,\n"
        "  voice notes, photos of grandkids and lunchboxes.\n"
        "- Flipkart Grocery + Amazon: 2-3 longer sessions/week, peaks during sales (Big Billion\n"
        "  Days, Great Indian Sale, Diwali sales). Compares MRP to kirana memory before adding.\n"
        "- Instagram: 5-10 min/day, mostly Reels — recipe content, kids/family moments, the\n"
        "  occasional saas-bahu serial clip. Follows ~80 accounts, mostly recipe channels and\n"
        "  family. Ads land here but rarely produce a tap.\n"
        "- YouTube on the kitchen iPad while cooking: Hindi recipe channels, devotional\n"
        "  content, occasional Hindi-news shorts.\n"
        "- TV in the evening: Hindi serials on Star Plus / Colors, ads watched passively.\n"
        "\n"
        "AD SURFACE — WHERE SHE ACTUALLY ENCOUNTERS BRAND ADS\n"
        "1. Flipkart Grocery banner / homepage carousel (highest conversion path for FMCG)\n"
        "2. Forwarded promotional images on WhatsApp from frugal sister-in-law / mother-in-law\n"
        "3. Instagram Reels ads between recipe content\n"
        "4. TV ad breaks during the 9pm Hindi serial\n"
        "5. YouTube pre-roll on recipe videos\n"
        "Most ad seeing happens 1 + 4. The ad on a Flipkart banner during Diwali week is\n"
        "*not* a passive impression — it is on the surface where she is actively price-checking.\n"
        "\n"
        "LAST 5 ADS SHE ACTUALLY ENGAGED WITH (and what she did)\n"
        "- Tata Sampann besan ₹40 off — added to cart, bought\n"
        "- Atta-maker mixie attachment (Insta) — saved, asked husband, did not buy\n"
        "- Ghee jar deal on Amazon — bought after checking BigBasket price\n"
        "- A serial actress's saree-shop reel — tapped profile, didn't buy\n"
        "- Local hospital health-checkup package — sent to husband, he booked it\n"
        "\n"
        "WHAT MAKES IT INTO HER WHATSAPP FAMILY GROUPS\n"
        "- Recipe videos, devotional forwards, deals on staples (atta, ghee, oil)\n"
        "- Grandkid photos, school function updates\n"
        "- Sale alerts on grocery items below known price floors\n"
        "- Almost never: an ad just because it's clever or funny. Function over aesthetic.\n"
        "\n"
        "WHAT MAKES HER STOP SCROLLING\n"
        "- A specific rupee number on a known household staple (atta, oil, coffee, dal)\n"
        "- A festive sale on a brand the household already uses\n"
        "- A recipe with a clear ingredient list using brands she has at home\n"
        "- Any reference to her son's college, daughter's board exams, or family festivals\n"
        "- A trusted face — Madhuri Dixit on a saree ad, a Hindi serial actress\n"
        "\n"
        "WHAT MAKES HER SCROLL FASTER\n"
        "- Empty-frame lifestyle content with no product or price\n"
        "- English-only copy in Latin script with no Hindi cue\n"
        "- Fancy-cafe / specialty / 'artisanal' visual language — registers as 'not for me'\n"
        "- Anything that asks for download / signup / OTP-style friction\n"
        "\n"
        "POST-STOP DECISION FLOW\n"
        "Thumb pause → eyes go to the rupee number → mental compare to kirana / last\n"
        "Flipkart price → if cheaper or same, add to grocery list → if much cheaper than\n"
        "memory, suspicion (MRP-inflation pattern), screenshot to ask husband or sister-\n"
        "in-law → cross-check in WhatsApp family group ('Sushma, ye sale dekha?') → buy\n"
        "either via Flipkart Grocery or wait until next kirana visit. Almost never buys\n"
        "on first impulse from a single ad. Festive moments compress this loop —\n"
        "Diwali stocking week she will accept slightly thinner verification."
    ),
    "urban_indian_male_22_30": (
        "INSTA SESSION PATTERN\n"
        "- Sessions: ~10–15 min, 2–3x/day. Heaviest at night in bed and on the toilet.\n"
        "- Sees ~80–100 ads per session. Stops thumb on ~2–3. Screenshots ~1.\n"
        "- Default action on an ad: scroll past in <0.5s with zero internal monologue.\n"
        "  Most ads do not produce a thought — they produce a thumb flick.\n"
        "\n"
        "LAST 5 ADS HE ACTUALLY ENGAGED WITH (and what he did)\n"
        "- Cult.fit yoga deal — saved (was already considering joining)\n"
        "- Boult earbuds at ₹1499 — almost bought, cross-checked Reddit, didn't\n"
        "- Goa hostel reel — sent to college group chat, no one responded\n"
        "- Snitch tee at ₹999 — dismissed (saw same on Myntra at ₹599)\n"
        "- Razorpay engineering blog promo — tapped through, actually read it\n"
        "\n"
        "WHAT MAKES IT INTO THE OFFICE WHATSAPP GROUP\n"
        "- Steam sale screenshots, Decathlon deals, restaurant offers under ₹500/head\n"
        "- Layoff memes, IPL takes, gloriously cringe brand fails\n"
        "- Ads basically never land here — only if it's so bad it's funny\n"
        "\n"
        "WHAT MAKES HIM STOP SCROLLING\n"
        "- A specific number (₹1499, 60% off, ₹35/cup) — anchors a price decision\n"
        "- A peer/influencer he recognises from his bubble\n"
        "- A contrarian take or a roast of something he also dislikes\n"
        "- 'Free trial' / 'first order ₹1' language\n"
        "- A deal that beats Reddit's known floor for that category\n"
        "\n"
        "WHAT MAKES HIM SCROLL FASTER\n"
        "- Lifestyle posing with no concrete product detail\n"
        "- D2C ads with no price visible\n"
        "- Influencers from outside his bubble (TV-celeb, cricketer-turned-shill)\n"
        "\n"
        "POST-STOP DECISION FLOW\n"
        "Thumb pause → eyes go to price → mental compare to known alternative →\n"
        "tap profile only if both signals positive → screenshot if price feels\n"
        "right but he wants to think → cross-check Blinkit/Myntra/Amazon before\n"
        "buying. Buys directly via an Insta tap maybe 1x/month."
    ),
}


def get_behavioral_priors(archetype: str) -> str:
    """Return a structured paragraph of behavioral priors for this archetype.

    Behavioral priors describe what the person *does* on Instagram — session
    pattern, recent ad engagement history, attention triggers, decision flow.
    These are facts the model conditions its behavior on, not language to mimic.
    """
    return _PRIORS[archetype]
