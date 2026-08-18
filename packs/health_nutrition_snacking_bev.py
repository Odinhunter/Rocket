"""TEST ARTIFACT — `health_nutrition_snacking` plus the beverages it competes
with. Built 2026-08-19 for the F&B refactor's part-A test. ⚠ NOT FOR INSTALL.

WHAT THIS IS FOR
----------------
The F&B design doc's central claim is that beverages and snacks are competitors
in the same moments, not siblings in a tree — that chai wins the 4pm dip in
India more often than any biscuit, and a pack with no chai in it therefore
cannot represent the choice a real person makes. Part A of the paid test is the
kill-switch for that claim: generate ONE moment for ONE region twice, once
against the base pack and once against this one, and read whether the people
change.

⚠⚠ THE ATTRIBUTION CONTRACT IS THE WHOLE POINT, WHICH IS WHY THIS FILE IS
DERIVED AND NOT COPIED. It is `dataclasses.replace` over the base PACK, so
"only the beverages differ" is true BY CONSTRUCTION rather than by a claim
about a 1,000-line copy that could drift.

⭐ **EXACTLY TWO FIELDS REACH THE MODEL: `brand_landscape` and `price_points`.**
Verified against `_pack_brief` in `scripts/generate_audience.py`, which reads
six pack fields and no others — brands, prices, retail channels, cultural
references, voice samples, behavioral priors. Everything else — chaos
distribution, communities, occasions, journeys, market stats, price
architecture — is the same OBJECT as the base pack's, not a copy of it.

⚠ `sources` and `open_questions` are ALSO extended here, and that is safe
precisely because **`_pack_brief` never reads them** — they are provenance for
whoever audits this file later, and no part of them can reach a persona. ⚠ If
`_pack_brief` ever grows to include them, this pack stops being attributable
and part A must be re-run.

⚠ `retail_channels` deliberately NOT touched: the base pack already carries
"street cart and chai stall — samosa, vada pav, cutting chai; hot, immediate,
cheaper than almost anything packaged". ⭐ THE GAP WAS NEVER THE CHANNEL. The
pack already knew chai was where the money goes; it had no chai anyone could
BUY. Adding a channel that exists would have moved a second field for nothing
and weakened the attribution.

WHAT WAS ADDED, AND WHY EXACTLY THIS SET
----------------------------------------
Only beverages the grid's own `competes_with` fields already name, plus the
malted-milk tier the test spec names:
  - CHAI  — `desk_slump_4pm` competes with "...samosa/vada from the canteen,
    chai, a banana, or skipping it entirely"
  - COFFEE — `breakfast_on_the_run` competes with "toast, poha, cereal, a
    bought sandwich, coffee alone, skipping"
  - MALTED MILK — not named in a `competes_with` string, but named in the test
    spec, and it is the incumbent "health drink" this population actually holds
    an opinion about. It competes at `daily_health_routine` ("a powder,
    gummies, a multivitamin, real food, nothing") and at the bedtime cup.

⭐ THE DISCIPLINE: the pack gains what the grid ALREADY SAYS IT LOSES TO, not a
wish-list. Nothing here was chosen because it would be interesting to see.

⚠ PRICES ARE SOURCED, AUGUST 2026, quick-commerce and marketplace listings —
the same bar as the base pack's 28. A brand whose price could not be pinned
confidently is carried WITHOUT a price point rather than with a guessed one
(Bru), because a wrong price is worse than a missing one: the personas reason
about trade-offs in rupees.

⚠⚠ THE ONE KNOWN GAP, RECORDED RATHER THAN INVENTED: the ₹10-12 cutting chai at
the stall is arguably the single most important price in this whole set for a
tier-3 buyer, and it is NOT here — no reliable 2026 source was found. It is
partly covered by the channel text above, which describes it without a number.
⚠ Do not add it from memory.
"""

from __future__ import annotations

import dataclasses

from agent.artifact_pack import BrandLandscapeEntry, PricePoint

from . import health_nutrition_snacking as _base

# --------------------------------------------------------------------------
# THE DELTA. Everything in this module is these two lists.
# --------------------------------------------------------------------------

_BEVERAGE_BRANDS = [
    # --- CHAI. The 4pm dip's real winner, and the household's default hot
    # drink. Bought as a 250g packet and made at home, which is why the packet
    # price — not a cup price — is what a household actually weighs.
    BrandLandscapeEntry(
        name="Tata Tea Premium", tier="mass",
        note="the default household CTC packet across much of north and west India; bought monthly, made at home, and the thing a 4pm snack is genuinely eaten ALONGSIDE rather than instead of",
    ),
    BrandLandscapeEntry(
        name="Brooke Bond Red Label", tier="mass",
        note="the other default CTC packet; near-interchangeable with Tata Tea at the shelf and fiercely non-interchangeable in a household that has picked one",
    ),
    # --- COFFEE. Named at breakfast-on-the-run. Instant, not brewed —
    # filter coffee is a southern household ritual and a different object.
    BrandLandscapeEntry(
        name="Nescafé Classic", tier="mass-premium",
        note="instant coffee; the jar that signals a household where someone drinks coffee rather than tea, and a markedly higher per-cup cost than the chai it displaces",
    ),
    BrandLandscapeEntry(
        name="Bru", tier="mass",
        note="instant coffee-chicory; the cheaper coffee, and the one a tea household buys when a coffee-drinking relative visits",
    ),
    # --- MALTED MILK. The bedtime cup and the "health drink" tier — the
    # incumbent this population has held an opinion about for forty years,
    # and the nearest thing to a protein powder that is already in the house.
    BrandLandscapeEntry(
        name="Horlicks", tier="mass-premium",
        note="the original malted health drink; read as nourishment for children, the elderly and the recovering — and the tin a woman is most likely to already own when a protein powder is pitched to her",
    ),
    BrandLandscapeEntry(
        name="Bournvita", tier="mass",
        note="the chocolate malt; a children's drink first, bought to get milk into a child, and increasingly argued about for its sugar",
    ),
    BrandLandscapeEntry(
        name="Boost", tier="mass",
        note="the stamina-and-sport malt; the same tier as Bournvita with an energy claim rather than a growth one",
    ),
]

# ⚠ SOURCED AUGUST 2026 — Blinkit / BigBasket listings. See `sources` below.
_BEVERAGE_PRICES = [
    PricePoint(item="Brooke Bond Red Label 250g", price_inr="₹120",
               channel="supermarket / kirana"),
    PricePoint(item="Tata Tea Premium 250g", price_inr="₹125",
               channel="supermarket / quick commerce"),
    PricePoint(item="Nescafé Classic 50g pouch", price_inr="₹230",
               channel="supermarket / quick commerce"),
    PricePoint(item="Horlicks Classic Malt 500g jar", price_inr="₹264",
               channel="supermarket / quick commerce"),
    PricePoint(item="Bournvita 500g refill pouch", price_inr="₹241",
               channel="supermarket / quick commerce"),
    PricePoint(item="Boost 750g pack", price_inr="₹337",
               channel="quick commerce"),
]

_BEVERAGE_SOURCES = [
    "Blinkit product listings, retrieved 2026-08-19 — Tata Tea Premium 250g ₹125; Bournvita chocolate drink mix 500g pouch ₹241; Horlicks Classic Malt 500g jar ₹264; Boost 750g ₹337",
    "BigBasket product listings, retrieved 2026-08-19 — Brooke Bond Red Label 250g carton ₹120; Nescafé Classic 50g pouch ₹230",
]

_BEVERAGE_OPEN_QUESTIONS = [
    "⚠ NO SOURCED PRICE FOR STALL CHAI (the ₹10-12 cutting chai), which is plausibly the most important single price in this set for a tier-3 buyer at the 4pm dip. The retail channel describes it without a number. Do not fill it from memory.",
    "Wagh Bakri, Society and the strong regional CTC brands are absent — tea loyalty in India is intensely regional and a national list understates it.",
    "Filter coffee (the southern household ritual) is deliberately absent: it is a different object from instant, and this region is tier-3 with no southern scoping.",
    "No price is carried for Bru — the listings found did not pin a pack size to a price, and a guessed rupee figure is worse than none when personas reason in rupees.",
]

# --------------------------------------------------------------------------
# ⚠ TWO FIELDS MOVE. If a third ever moves, part A stops being attributable
# and the run it justifies is wasted.
# --------------------------------------------------------------------------

PACK = dataclasses.replace(
    _base.PACK,
    category="health_nutrition_snacking_bev",
    brand_landscape=[*_base.PACK.brand_landscape, *_BEVERAGE_BRANDS],
    price_points=[*_base.PACK.price_points, *_BEVERAGE_PRICES],
    sources=[*_base.PACK.sources, *_BEVERAGE_SOURCES],
    open_questions=[*_base.PACK.open_questions, *_BEVERAGE_OPEN_QUESTIONS],
)
