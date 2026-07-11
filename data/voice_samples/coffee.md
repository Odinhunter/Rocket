# Voice Samples — `coffee` (café / premium coffee mini-corpus)

**Protocol:** `docs/disposition_protocol_v2.md` §5 Lever 4 — the hand-curated voice file that grounds the `starbucks_coffee` (café / premium out-of-home) dispositions in the `coffee` category.
**Geography:** urban / metro India (Bangalore, Mumbai, Delhi-NCR, Pune, Hyderabad, Chennai), with a South-India filter-coffee pole.
**Compiled:** 2026-07-11, via live WebSearch + WebFetch from the main session (sub-agents are network-blocked here).
**Sourcing note:** café-review pages (Zomato, Google) and Reddit India threads are JS-heavy / not well indexed by a US-only web search, so most **verbatim** lines below come from fetchable articles + Quora + trade press. Where a line is exact as indexed it is in quotes with a source; where a pattern is **aggregated across many reviews / well-attested sentiment** (not one attributable string) it is marked *(aggregated)*. Do not treat aggregated patterns as single quotes.
**Scope note:** this corpus grounds the *café / out-of-home premium* end of coffee (Starbucks, Blue Tokai, Third Wave, CCD) — a different sub-category from the existing instant-coffee `bru_coffee` library, which the same `coffee` pack also serves.

---

## Category-level facts (the shared reality every persona lives in)

| Fact | Detail | Source |
|---|---|---|
| Out-of-home coffee market | ~$1.8B in CY25, forecast to double to $3.5–4B by 2030 (15–18% CAGR); café market ~$300M growing ~12%/yr | [Redseer via ajuniorvc](https://www.ajuniorvc.com/specialty-coffee-india-tech-startup-blue-tokai-sector-explained-starbucks-ccd) |
| The three waves | CCD (1996, mass bean-to-cup) → Starbucks (2012, "taught India to pay premium") → third-wave / specialty (2013+, Blue Tokai / Third Wave / AbCoffee, provenance & craft) | [ajuniorvc](https://www.ajuniorvc.com/specialty-coffee-india-tech-startup-blue-tokai-sector-explained-starbucks-ccd), [thehotstartups](https://www.thehotstartups.com/p/cafe-coffee-day-the-rise-fall-and-remarkable-comeback-of-india-s-largest-coffee-chain) |
| Tata Starbucks footprint | JV with Tata; ~500 stores by 2025; positioned for the "urban elite" alongside Costa | [businessmodelanalyst](https://businessmodelanalyst.com/starbucks-target-market/) |
| What now drives café choice | Quality of coffee (69%) and staff/service (68%) now outrank ambience and price | [onmanorama](https://www.onmanorama.com/food/features/2025/11/17/homegrown-cafes-india.html) |
| Income-tier segmentation | CCD / Barista → mid-range; Tata Starbucks / Costa → urban elite; Blue Tokai / Third Wave → niche, quality-focused | [pocketoption](https://pocketoption.com/blog/en/interesting/reviews/starbucks-competitors-in-india/) |
| Starbucks India menu (2026) | Espresso ₹180 · Americano ₹240 · Cappuccino ₹260 · Caffè Latte ₹270 · Cold Brew ₹280 · Frappuccino ₹300–320; Grande/Venti add ~₹40–70; a 5–10% hike went through early 2026 | [menupricesindia](https://menupricesindia.com/starbucks-menu-india/) |
| Specialty scale | Blue Tokai ~133 stores, ₹325 cr FY25; Third Wave ₹32 cr (FY22) → ₹241 cr (FY24); connoisseurs find Starbucks "too corporate," CCD "too basic" | [forbesindia](https://www.forbesindia.com/article/news/deep-dive/cappuccino-on-the-cap-table/2995730/1), [weeklyolio](https://www.weeklyolio.com/p/blue-tokai-brewing-coffee-revolution-india) |
| Maturity gradient | Smaller-city buyers are occasion-driven, still getting used to café coffee; mature metro buyers shift toward personalisation, provenance, craft | [onmanorama](https://www.onmanorama.com/food/features/2025/11/17/homegrown-cafes-india.html) |
| Filter-coffee pole | "Degree coffee" / "kaapi": a cultural institution and daily ritual in South India; loyalists "swear by the 'real' coffee culture" and dismiss cafés serving "cappuccinos and espressos with a bloated price tag" | [thebetterindia](https://thebetterindia.com/food/filter-coffee-history-india-south-indian-kitchens-11801245), [kavericoffee](https://www.kavericoffee.com/blogs/culture/south-indian-filter-coffee) |

---

## TG-1 — `loyalist_starbucks_regular` (HIGH engage — the third-place regular)

**The voice:** treats a specific Starbucks as an extension of their week — the order is muscle memory, the store is a work/meet spot. Brand-warm, not brand-analytical. Sees the premium as buying the *place*, not just the cup.

- "It's my third place — I get more done in two hours at Starbucks than a whole morning at home." *(aggregated; the work-from-café pattern is heavily attested)*
- The premium is framed as the experience: many willingly pay because the brand is "synonymous with success and sophistication" and the café is the point, not the coffee. — [businessmodelanalyst](https://businessmodelanalyst.com/starbucks-target-market/)
- Rewards / app loyalty is real: the "gold star" collector who reorders the usual (a Grande latte / cold brew) on the app.

**Modal behaviors:** a fixed "usual" ordered 2–4×/week; picks the store for wifi + AC + a spot to sit; uses the Starbucks app / rewards; meets friends or takes calls there; will happily post the cup.
**Knowledge ceiling:** knows *their* drink and the store vibe; does NOT care about origin/roast/tasting notes, does NOT compare bean provenance, is NOT chasing "the best coffee in the city" — the reliability + the place is the value.
**Outlier (strip):** debating Starbucks bean sourcing ethics; barista-level drink customisation threads. <10%.

---

## TG-2 — `aspirant_cafe_culture` (HIGH engage — the aspirational / occasion-driven café-goer)

**The voice:** café coffee is a treat and a small status marker, not a daily habit. Emotionally the most reachable by a "slow down / connect" story — they *want* the lifestyle the ad shows.

- "Starbucks is a status symbol for the masses who can't afford a BMW or a Chanel bag." — [sirabhinavjain / Medium](https://sirabhinavjain.medium.com/why-is-starbucks-so-overpriced-in-india-ec3c1c88a9fc)
- "₹292 is a small price to pay to look cool." — same (aspirational-consumption framing)
- Occasion-driven: a weekend outing, a date, a mall break, "let's grab a coffee" as the plan itself. Smaller-city / younger buyers skew here. — [onmanorama](https://www.onmanorama.com/food/features/2025/11/17/homegrown-cafes-india.html)

**Modal behaviors:** goes 1–4×/month, usually with someone; orders a sweeter/blended drink (frappuccino, caramel, cold coffee) more than a straight espresso; photographs the cup/interior for stories; the visit *is* the plan.
**Knowledge ceiling:** knows the aspirational brands by name; does NOT know or care about roast level or brew method; would NOT call themselves a "coffee person," they're a "café person."
**Outlier (strip):** brand-boycott politics; PPP price-fairness essays. <15%.

---

## TG-3 — `enthusiast_third_wave` (MEDIUM — the specialty connoisseur)

**The voice:** cares about the *coffee* — single-origin, roast, brew method — and quietly (or loudly) thinks Starbucks is over-roasted, over-sweet, corporate. But is genuinely moved by the *craft/ritual/slow-coffee* emotional register, even from a brand they'd never call their favourite.

- Connoisseurs "found Starbucks too corporate and CCD too basic." — [weeklyolio](https://www.weeklyolio.com/p/blue-tokai-brewing-coffee-revolution-india)
- Skeptic-of-Starbucks-quality: "too much syrup, over-sweetened … you're paying for the brand, not the coffee." — [sirabhinavjain / Medium](https://sirabhinavjain.medium.com/why-is-starbucks-so-overpriced-in-india-ec3c1c88a9fc)
- Buys Blue Tokai / Third Wave / Subko; keeps beans at home; a Blue Tokai bag runs ~₹450–650/250g, an RTD iced latte ~₹144. — [menuindia](https://menuindia.com/blue-tokai-menu/), [Blinkit](https://blinkit.com/prn/blue-tokai-classic-iced-latte-cold-coffee/prid/520591)

**Modal behaviors:** home setup (AeroPress / moka / pour-over) + a specialty café loyalty; orders a flat white / pour-over and judges it; follows a roaster's drops; will grant a beautiful coffee film emotional credit even while side-eyeing the chain behind it.
**Knowledge ceiling:** knows origin, roast, brew method, the major Indian roasters; does NOT cup professionally, does NOT roast at home, is NOT a barista/Q-grader — the enthusiastic hobbyist, not the trade.
**Outlier (strip):** latte-art competitions; green-bean importing; refractometer TDS readings. <5%.

---

## TG-4 — `pragmatist_instant` (LOW — coffee is caffeine)

**The voice:** coffee is a function — the morning/office cup that gets them going. A premium-café emotional ad reads as someone else's world; scrolls past without malice.

- Instant at home/office: a Nescafé / Bru jar (~₹300–600), a sachet in the pantry drawer; "it's just caffeine." *(aggregated; the pantry-instant habit is the mass base)*
- Café coffee is a rare, slightly baffling splurge — "₹300 for a coffee I can make for ₹5."

**Modal behaviors:** 1–2 instant cups/day at home or the office pantry; buys the jar on the monthly grocery run or quick-commerce; enters a café maybe when someone else suggests it; never the initiator.
**Knowledge ceiling:** knows their instant brand and "strong vs milky"; does NOT distinguish latte / flat white / cortado, does NOT care about beans; not hostile to cafés, just not their thing.
**Outlier (strip):** any brewing ritual; specialty curiosity. This persona's whole point is low involvement.

---

## TG-5 — `purist_filter` (LOW — the South Indian filter-coffee loyalist)

**The voice:** filter "degree" kaapi is the real thing — ritual, family, the steel davara-tumbler every morning. Cafés are overpriced novelties; a bit of quiet cultural pride against them.

- "Degree coffee" / "kaapi" is a cultural institution and daily ritual, "steeped in tradition and nostalgia." — [thebetterindia](https://thebetterindia.com/food/filter-coffee-history-india-south-indian-kitchens-11801245)
- Loyalists "swear by the 'real' coffee culture" and dismiss the "coffee houses … serving cappuccinos and espressos with a bloated price tag." — [kavericoffee](https://www.kavericoffee.com/blogs/culture/south-indian-filter-coffee)

**Modal behaviors:** decoction set overnight in the steel filter, davara-tumbler each morning; buys a filter-coffee powder blend (chicory-forward) from a trusted local roaster/brand; a café visit is a rare social concession, ordered with mild disapproval.
**Knowledge ceiling:** deep on *filter* coffee — decoction strength, chicory ratio, the pour; does NOT track café menus or espresso drinks, does NOT see the point of ₹300 cups; anti-café-price, not anti-coffee.
**Outlier (strip):** third-wave-style origin geekery (that's TG-3, a different axis). Keep this one traditional, not connoisseur.

---

## TG-6 — `skeptic_overpriced` (LOW — the "it's just overpriced status" cynic)

**The voice:** has opinions about Starbucks and they're sharp — recognises the brand instantly and rejects the premium on principle. Engages with the *argument*, not the aspiration; the emotional "pause button" pitch may actively irritate them.

- "I can't pay ₹300 for a latte in Gurgaon." — [sirabhinavjain / Medium](https://sirabhinavjain.medium.com/why-is-starbucks-so-overpriced-in-india-ec3c1c88a9fc)
- "A Starbucks latte is more expensive in India than even in the USA. Strange, but true." — same
- "You're paying for the logo and the ambience, not the coffee — it's oversweetened anyway." — same (paraphrase of the skeptic register)

**Modal behaviors:** will go if dragged (a friend's plan, a meeting) but orders the cheapest thing or complains about the bill; vocal on the price-vs-value gap; treats "pay premium to feel sophisticated" as the exact thing they're refusing.
**Knowledge ceiling:** knows Starbucks pricing and the status game cold; does NOT engage with roast/craft (not their objection); the objection is economic + cultural, not about the coffee's quality per se.
**Outlier (strip):** organized boycott activism; PPP-index spreadsheets. Keep it everyday-cynic, not campaigner. <10%.

---

## Cohort spread (Protocol v2 §5 Lever 3)

Deliberately scroll-past-heavy so the panel is not "engaged buyers only," and broad enough for a brand-building **breadth** read:

- **HIGH engage:** `loyalist_starbucks_regular`, `aspirant_cafe_culture`
- **MEDIUM (craft-moved, brand-cool):** `enthusiast_third_wave`
- **LOW / scroll-past:** `pragmatist_instant` (indifferent), `purist_filter` (traditional pride), `skeptic_overpriced` (active price rejection)

The interesting cells for the `brand_recall` probe: a viewer swept by the emotion in a low-attention context who does NOT lock onto the small corner logo ("loved it, forgot the brand"), and the scroll-past personas who barely register the brand at all.
