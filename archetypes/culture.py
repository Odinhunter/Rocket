"""Cultural context — what this demographic is currently talking about and reacting to.

Short paragraph capturing the live cultural surface area. Stubbed here;
later this can be a feed of recent topics (news, memes, brand events).
"""


_CONTEXT: dict[str, str] = {
    "middle_class_indian_homemaker_38_55": (
        "What's in the air right now: Diwali is coming, the household stocking-up window is "
        "active. Flipkart Big Billion Days and Amazon Great Indian Sale notifications fire "
        "every hour; sister-in-law and neighbor Sushma forward sale screenshots constantly. "
        "Onion prices are up again, LPG cylinder went to ₹1100 last refill, Atta and oil are "
        "the household-budget pain points. Kids' education stress is loud — son's mid-sem "
        "engineering exams in two weeks, daughter starting JEE coaching that costs ₹85k for "
        "the year. Recipe Reels (Kabita's Kitchen, Nisha Madhulika, Hebbar's Kitchen) are her "
        "default cooking reference now, replacing the recipe books her mother used. WhatsApp "
        "family groups are the social fabric — extended family, school parents, husband's "
        "office wives, building society. Forwards-as-care is the dominant communication mode. "
        "Hindi serial schedule is a daily ritual: 9pm Anupamaa or Yeh Rishta on Star Plus, ad "
        "breaks are her phone-scroll window. Vibe is: practical, brand-aware in a household-"
        "purchase way (Bru, Tata, Patanjali, Amul, Maggi register strongly; D2C names mostly "
        "don't), price-vigilant after years of MRP-inflation games and post-Covid grocery "
        "inflation, festively warm but not naive about 'Diwali offer' marketing tactics."
    ),
    "urban_indian_male_22_30": (
        "What's in the air right now: startup layoffs and TC-flexing memes on r/India and "
        "r/developersIndia. D2C fatigue — every other brand on Insta is a moringa-pasta or "
        "ashwagandha-coffee 'wellness' pitch and the cynicism is loud. Third-wave coffee "
        "(Blue Tokai, Subko, Third Wave Coffee Roasters) is normalised in metros but still "
        "feels like a class signal. Bombay/Bangalore rents are an open wound. Goa is 'over' "
        "for this set; everyone is doing Vietnam, Bali, or a Himachal road trip. Hinge has "
        "replaced Tinder; people complain about the same five photo-archetypes endlessly. "
        "Cricket twitter is unhinged during IPL. Blinkit/Zepto 10-minute delivery is both a "
        "joke and a daily habit. Vibe is: tired, plugged-in, suspicious of marketing, "
        "performatively cynical online but quietly buying the things they roast."
    ),
}


def get_cultural_context(archetype: str) -> str:
    """Return a short paragraph of current cultural context for this archetype."""
    return _CONTEXT[archetype]
