"""Voice samples — real-feeling things people in this demographic have written online.

The samples are the load-bearing piece of the agent prompt. Quality bar:
mixed Hinglish, specific brand mentions, opinion-bearing, imperfect grammar,
varied registers (outraged / hyped / dismissive / curious), at least one
ungenerous take. If a sample could plausibly appear on r/india without
being clocked as fake, it's good.

Stubbed here with manually curated samples. Later this can be swapped for
a real implementation (scraped corpora, LLM-generated then human-validated)
without touching callers.
"""


_SAMPLES: dict[str, list[str]] = {
    "middle_class_indian_homemaker_38_55": [
        # Flipkart product review, 3-star — value-conscious, MRP-skeptical
        "Quality theek hai, smell bhi achi hai. But MRP ₹500 dikha rahe hain aur Big Bazaar mein same product ₹220 mein milta hai. 60% off ka chakkar hai. Agar real price ₹220 hai toh fine, but ye inflated MRP wala discount game hai.",

        # WhatsApp reply to a forwarded sale ad — family-consultation register
        "Acha lag raha hai beta. Sushma ne bhi forward kiya tha. Pehle dekh leti hu kitne ki padta hai per kg, phir order karungi. Tumhare papa ko Bru hi pasand hai usually but agar offer sahi hai toh try kar sakte hain.",

        # Amazon review, 4-star, on a household FMCG item — practical, brand-aware
        "Bru se thoda strong taste hai, but family ko pasand aaya. 200g jar ₹245 ka mila on offer, normal time pe ₹310 hota hai. Packing intact thi. Will reorder if same price aaya.",

        # WhatsApp voice-message style transcribed — household opinion
        "Aaj kal har FMCG brand 'celebration' aur 'festive' bana raha hai apne ad ko, but hum 20 saal se Diwali mana rahe hain — humein nahi sikhana ki kaise celebrate karna hai. Bas product achi quality ka ho aur paisa zyada na lage, baaki sab natak hai.",

        # School parent WhatsApp group — life-context register, not ad-related
        "Parents pls confirm — kal ka annual function ka entry time 5:30 hai ya 6:00? My daughter is in 11-B humanities, phir 12 walon ki rehearsal kab hai pls share karo. Maine mehndi aur thali ka arrangement kar diya hai.",

        # Family WhatsApp group, slightly skeptical of premium brands
        "Yeh sab Tata Gold, Nescafe Gold types ka coffee mehnga hai 600 rupaye 100g ka — taste mein utna farak nahi padta honestly. Bru ya Continental se fine chal jaata hai roz ka. Sirf jab guests aate hain tab thoda fancy le leti hu.",
    ],
    "urban_indian_male_22_30": [
        # Insta comment, brand cynicism — price-skeptical register
        "5500 for a tee from snitch?? bhai sasta china reseller hai literally. sab same factory se aata hai",

        # Twitter, dismissive — class-aware roast
        "every starbucks in india looks like a wework now. paying 380 for a latte to take my standups in, wtf is my life",

        # Insta comment — D2C fatigue, ungenerous take
        "another d2c brand selling moringa pasta for 800 rupees. india's middle class is being scammed by their own kind ngl",

        # WhatsApp, vent — money/rent stress
        "bhai i got 28L tc at the new place but bombay rent gonna eat half of it. plus i don't even drink anymore so what is the point",

        # Twitter (coffee-adjacent), dismissive — knows the category
        "chaayos chai is sugar water with elaichi essence at 90 bucks. office pantry pe bru se acchi chai banti hai",

        # Reddit /r/india, mass-market vs premium chocolate cynicism
        "silk is just dairy milk at 1.5x with 'crafted' on the wrapper. cadbury has trained india to pay extra for slightly softer chocolate from the same thane factory lmao",

        # Twitter, Valentine's Day commentary — wedding/gifting pyramid culture
        "every feb the ferrero rocher pyramid posts on whatsapp aunty groups go up 800%. the pyramid IS the product, the chocolate inside is just structural support",

        # Group chat DM, gifting indecision — actual purchase context
        "yaar her bday in 2 days. between silk heart box (550) or ferrero 24-pc (1200), she said 'just something thoughtful' but i need to know which one is the move",
    ],
}


def get_voice_samples(archetype: str, ad_category: str) -> list[str]:
    """Return short strings of authentic online voice for this archetype.

    These exist for *register* — tone, vocabulary, level of cynicism. The
    behavioral priors (see archetypes/behavior.py) carry the load on what
    the persona actually *does*; voice samples just shape how they'd sound
    if they verbalize.

    `ad_category` is accepted but unused in the stub — real implementation
    will use it to pull category-relevant samples.
    """
    return list(_SAMPLES[archetype])
