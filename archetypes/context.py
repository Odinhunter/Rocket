"""Context — the immediate situation when the persona encounters the ad.

Disposition encodes the persona's stance toward a category. Context encodes
their *attention state right now*: time of day, posture, mood, what they're
doing, how engaged they are with their phone. Context governs whether
someone engages with an ad they would otherwise care about, or scrolls past
one they would otherwise stop for.

Each context grounds time / place / mood / posture concretely. The model
uses them to gate attention before disposition gets a chance to shape the
specific reaction.

Stubbed here for urban_indian_male_22_30. Later: derive from real device
usage / panel data / time-of-day mix studies.
"""

from __future__ import annotations

import random


_CONTEXTS: dict[str, list[tuple[str, str]]] = {
    "middle_class_indian_homemaker_38_55": [
        (
            "evening_tv_scroll",
            "Tuesday 9:14 PM. Anupamaa is on Star Plus, husband is half-watching, half on his "
            "phone. Ad break just hit. She's on the sofa with a cup of elaichi chai, idly "
            "scrolling Flipkart Grocery's Diwali sale page. Attention is medium-low and "
            "fragmented across the TV and the phone. Receptive to a good rupee number on a "
            "household staple but will not sit through a fancy creative.",
        ),
        (
            "morning_kitchen_break",
            "7:38 AM Wednesday. Husband has left for the office, daughter just out the door for "
            "school, son is in the bathroom getting ready for college. She has 6 minutes of "
            "actual quiet before she has to pack his tiffin. Standing at the kitchen counter "
            "with her own chai, phone in hand. WhatsApp first — three new forwards from sister-"
            "in-law overnight — then Flipkart for the day's grocery list. Attention is focused "
            "but utilitarian. Will not get distracted by lifestyle content.",
        ),
        (
            "afternoon_rest",
            "Wednesday 2:35 PM. Lunch dishes are done, kids and husband won't be home for "
            "another two hours. Lying on the sofa with the AC on, phone propped on her chest, "
            "the JBL speaker playing a Lata Mangeshkar bhajan. Mood is relaxed, slightly "
            "drowsy. This is the most receptive window of her day — willing to read captions, "
            "tap profiles, even add things to a Flipkart cart she'll review later.",
        ),
        (
            "diwali_shopping_research",
            "Saturday 11:20 AM, eight days before Diwali. Sitting at the dining table with a "
            "notebook, comparing Flipkart and Amazon prices on five things — atta, ghee, "
            "coffee, dry fruits for the gift boxes she's making for the building society "
            "neighbors, and a steel kadhai her mother-in-law mentioned. Husband is at the "
            "barber, kids are out. Maximum focus, screenshotting prices, cross-checking with "
            "WhatsApp messages from her sister in Indore.",
        ),
        (
            "last_minute_grocery_panic",
            "Thursday 7:48 AM. Just realized the Bru jar is empty when husband asked for his "
            "second cup. Has 10 minutes to add it to the Flipkart Grocery slot that closes at "
            "8 AM for same-day delivery. Phone in one hand, dosa batter on the other. Attention "
            "is task-focused and fast — she will tap the first known brand at a recognizable "
            "price and not browse. Any ad needs to surface a usable answer in under 3 seconds "
            "or it's invisible.",
        ),
        (
            "weekend_family_planning",
            "Sunday 10:45 AM. Husband is reading the paper, son is home for the weekend from "
            "his hostel-style PG, daughter is sleeping in. The mood is relaxed and unpressured. "
            "She's planning the week's groceries on Flipkart while the moka pot's brewing some "
            "Tata Coffee Gold for her son. WhatsApp family group is busy with a cousin's "
            "engagement update from Lucknow. Attention is high, mood is festive-warm. Open to "
            "considering a slight upgrade if the price is right and the family will accept it.",
        ),
        (
            "late_evening_planning",
            "Wednesday 10:38 PM. House is quiet — husband and daughter asleep, son on a video "
            "call with his project group. Sitting up in bed with the bedside lamp on, doing the "
            "actual order placement for tomorrow's grocery on Flipkart. This is when she "
            "finalizes — she's already done the comparison earlier in the day. Attention is "
            "high but execution-mode, not exploration. An ad here either fits a list-item she "
            "already has, or gets ignored.",
        ),
        (
            "whatsapp_family_group_scroll",
            "Tuesday 4:22 PM. Folding the dry laundry on the sofa, phone propped on the coffee "
            "table, idly scrolling the seven-person extended-family WhatsApp group where a "
            "cousin in Bhopal just forwarded a Flipkart sale screenshot. The forward includes "
            "a comment from sister-in-law Sushma: 'Anjali ye coffee dekho, mere ghar mein le "
            "li.' Attention is medium and socially-anchored — Sushma's endorsement matters "
            "more than the ad's claim. Recall is high if Sushma confirms by phone later.",
        ),
    ],
    "urban_indian_male_22_30": [
        (
            "late_night_wind_down",
            "11:42 PM Tuesday. Lights off, lying in bed, phone brightness on "
            "minimum. Half-asleep, doom-scrolling toward sleep. Standup is at "
            "9:30am. Eyes refocus slowly between posts. Long exposure but very "
            "low cognitive engagement — won't tap profile, won't search, won't "
            "screenshot unless something is genuinely funny.",
        ),
        (
            "between_meetings",
            "11:15 AM Tuesday. Standup ended at 11:08, 1:1 with skip-level at "
            "11:30. He has 7 minutes. Half-cold black coffee in hand. Phone-"
            "checking out of habit; mind is on the upcoming 1:1. Fast-scrolling, "
            "attention mostly elsewhere. Will dismiss anything that asks for "
            "more than 1 second of evaluation.",
        ),
        (
            "weekend_afternoon_home",
            "Saturday 3:20 PM. Just had bisi bele bath from Punjabi Rasoi for "
            "lunch, lying on the couch in shorts and a Manchester United tee. "
            "No plans till evening. Phone is the entertainment. Mildly bored, "
            "*receptive* — actually reads captions, considers things, sometimes "
            "follows a brand profile when a reel is good.",
        ),
        (
            "bangalore_traffic_uber",
            "Tuesday 7:12 PM. In an Uber Sedan from Indiranagar to Whitefield. "
            "ETA was 35 min, has been 50. Frustrated low-grade. Airpods in, lo-"
            "fi playing. Phone is the only real entertainment for the next 25 "
            "min. Attention is medium and bored — willing to watch a 15-second "
            "reel if the first frame holds.",
        ),
        (
            "late_evening_unwinding",
            "Tuesday 10:36 PM. Lights low, lying on the couch, the day's done, "
            "phone on his chest. Half-watching a YouTube video on the TV, "
            "half-scrolling Insta. Mood is unpressured and slightly indulgent — "
            "the post-dinner slot where treats register and he might actually "
            "tap profile on something. Attention is medium-receptive; not "
            "fast-scrolling, not committed-reading. The right window for a "
            "chocolate ad to land if it lands at all.",
        ),
        (
            "weekend_planning",
            "Saturday 10:50 AM. Coffee on the table, phone in hand, half a "
            "thought about what to do this evening. WhatsApp with the partner "
            "or college friends is open — vague plans being discussed about "
            "dinner, a movie, picking something up on the way. Mood is "
            "anticipatory and mildly transactional — already in 'what should "
            "I get / where should we go' mode. Receptive to specific buying "
            "prompts that fit the Saturday-evening slot.",
        ),
        (
            "sunday_hungover",
            "Sunday 11:30 AM. Drank too much at a Koramangala bar last night. "
            "Light hangover, on the couch with electrolytes and parle-g, "
            "watching nothing in particular on the TV. Mood is mildly "
            "irritable, low energy. Phone is the painkiller. Attention is low "
            "and selective — rejects anything that demands cognition.",
        ),
        (
            "bathroom_break",
            "9:50 AM Tuesday. In the apartment bathroom mid-morning routine. "
            "Phone in hand, 4-7 minutes available. Attention is medium-"
            "focused: literally nothing else to do, but pacing himself. Not a "
            "committed long session. Ad evaluation is fast and decisive — "
            "either stop hard or scroll hard.",
        ),
        (
            "commute_scroll",
            "Wednesday 8:47 AM. On the Bangalore Namma Metro from Indiranagar to "
            "MG Road station — coach is packed, standing, holding the strap with "
            "his left hand, phone in his right. Instagram open, thumb flicking "
            "fast through reels and brand stories. Earbuds in (his current pair) "
            "playing a Ranveer Allahbadia podcast at half-volume. Metro hits MG "
            "Road in 4 stops; from there it's a 12-minute walk to office. "
            "Attention is split between not missing his stop, the podcast in his "
            "ear, and the scroll — closer to ambient than focused. An ad that "
            "requires reading small print or doing price math is invisible here; "
            "an ad that lands a single hook in the first frame might survive.",
        ),
        (
            "pre_purchase_research",
            "Saturday 4:18 PM. Sitting at his desk in his Koramangala 1BHK, "
            "ThinkPad open with five tabs side by side: Flipkart's earbuds "
            "category sorted by Popularity, Amazon's TWS section, a Geekyranjit "
            "comparison video from last month running in the background, the "
            "r/IndianGaming 'best TWS under 3k 2026' megathread, and a Notion "
            "doc where he's been listing specs side-by-side. Filter coffee in "
            "the cup on the desk, phone in hand for cross-checking Instagram "
            "and YouTube reactions. He's been at this for 90 minutes and is "
            "ready to buy tonight if the right product surfaces — meaning the "
            "right one shows up with the right price, the right feature signal, "
            "and a credible reason to stop comparing. Attention is maximum and "
            "decision-mode. Every ad gets read against the open tabs.",
        ),
    ],
}


def list_contexts(archetype: str) -> list[tuple[str, str]]:
    """Return the full context pool for this archetype."""
    return list(_CONTEXTS.get(archetype, []))


def sample_context(
    archetype: str, rng: random.Random | None = None
) -> tuple[str, str] | None:
    """Sample one (label, context_text) tuple for this archetype.

    Returns None if no context pool is defined for this archetype.
    """
    pool = _CONTEXTS.get(archetype)
    if not pool:
        return None
    rng = rng or random
    return rng.choice(pool)
