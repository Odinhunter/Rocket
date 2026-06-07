# Voice Samples — `health_wellness_nutrition` (manual mini-corpus)

**Protocol:** `docs/disposition_protocol_v2.md` §5 Lever 4 — the hand-curated voice file that grounds every disposition in this category.
**Geography:** urban / metro India (Bangalore, Mumbai, Delhi-NCR, Pune, Hyderabad, Chennai).
**Compiled:** 2026-06-02, via live web research (WebSearch + WebFetch from the main session — sub-agents are network-blocked in this environment).
**Sourcing note:** Indian retail review pages (Amazon.in, Nykaa, Flipkart, HealthKart) are JS-heavy and frequently 403 / time out under WebFetch. Most quotes below are surfaced through WebSearch's indexed review snippets and through fetchable article / forum / Quora pages. Where a quote is **exact verbatim** as indexed it is in quotes; where a pattern is **aggregated across multiple reviews** (not a single attributable string) it is marked *(aggregated)*. This honesty matters — do not treat aggregated patterns as single attributable quotes.

The corpus is organized by the seven **target-group (TG) gateways** the library is built around (see `dispositions_are_tg_gateways` memory: a profile gateways one attitudinal TG; the runtime AI does the rest).

---

## Category-level facts (the shared reality every persona lives in)

| Fact | Detail | Source |
|---|---|---|
| Urban protein deficiency | 60% of urban India not eating protein-rich food daily; survey of 207,000 across top 25 metros (Feb 2026) | [Business Standard / LocalCircles + Country Delight](https://www.business-standard.com/content/press-releases-ani/india-s-protein-gap-a-survey-by-localcircles-country-delight-reveals-60-of-urban-india-is-protein-deficient-126020500669_1.html), [NuFFooDS Spectrum](https://nuffoodsspectrum.in/2026/02/06/country-delight-survey-reveals-60-of-urban-india-is-protein-deficient.html) |
| Willingness to switch | 71% of consumers willing to switch to more affordable protein; barriers = affordability, awareness, convenience | same survey |
| The supplement-quality scandal | "Citizens Protein Project": Liver Doc's team analysed 36 popular Indian protein supplements — ~70% had inaccurate protein info, 14% contained toxins/fungal aflatoxins/pesticides | [PubMed 38579036](https://pubmed.ncbi.nlm.nih.gov/38579036/), [The South First](https://thesouthfirst.com/health/is-your-protein-supplement-safe-liver-docs-team-analysed-36-indian-products-and-heres-what-they-found/) |
| Vit D deficiency | ~46-50% urban India vitamin-D deficient; doctor-prescribed cohort is large | (prior corpus: Metropolis study, OC Academy) |
| Channel normalization | HealthKart 200+ retail stores in 90+ cities; supplements no longer pure-online. Quick-commerce (Blinkit/Zepto) now stocks bars + gummies | search-confirmed Blinkit/Zepto pricing on Yogabar, Whole Truth |
| Ownership facts | OZiva → HUL (2023); Yogabar → ITC (2023); MuscleBlaze/HK Vitals/TrueBasics → HealthKart house brands; Plix → Honasa/Mamaearth-incubated | [Storyboard18](https://www.storyboard18.com/how-it-works/hair-gummies-protein-powders-get-influencer-push-as-brands-eye-indias-nutraceutical-market-6705.htm) |

---

## TG-1 — `enthusiast_macros_lifter` (OBSESSIVE — serious gym lifter)

**The voice:** confident, spec-fluent, slightly gatekeep-y, value-conscious *within* quality. Loyal to what works (usually Biozyme). Knows certifications and per-scoop macros. NOT a clinician.

Verbatim / near-verbatim from review + comparison sources:
- "Biozyme is the best overall value … perfect for **80% of Indian fitness enthusiasts**." — [NutraCore 2026 comparison](https://nutracore.in/blog/muscleblaze-vs-myprotein-vs-optimum-nutrition-best-whey-protein-in-india-2026)
- "using this product for **more than 6 months now** … works fine plus easy to digest, would highly recommend." *(aggregated, HealthKart/Flipkart Biozyme reviews)* — [Flipkart](https://www.flipkart.com/muscleblaze-biozyme-whey-protein/product-reviews/itm07f4cf0925903?pid=PSLFM7F924WQPJYM)
- "If you want value with results, go for MuscleBlaze. If you want premium … choose Optimum Nutrition." — [CashKaro](https://cashkaro.com/blog/muscleblaze-vs-optimum-nutrition-which-has-a-better-whey-protein/37440)
- ON Gold Standard framed as "₹70-80 per serving … justified by consistent quality" — the aspirational tier this TG eyes. — CashKaro / NutraCore
- Certification literacy is real: Biozyme is "Labdoor, Informed Choice, Trustified certified," NutraIngredients 2021 "Product of the Year." This TG cites these unprompted. — [MuscleBlaze](https://www.muscleblaze.com/sv/muscleblaze-biozyme-performance-whey/SP-88093)

**Modal behaviors:** buys 1kg tub every ~6-7 weeks; same cart adds creatine + omega-3; checks HealthKart authenticity/QR seal; watches one Tarun Gill / Guru Mann / Fittuber video before a *first-time* brand switch then defaults back to what works; computes protein-per-rupee.
**Knowledge ceiling:** does NOT lab-test, does NOT read the clinical trials behind "50% better absorption," does NOT debate amino-acid profiles online, is NOT a nutritionist. Aware *of* amino-spiking as a fear, can't actually assay for it.
**Outlier (strip):** running his own protein-content lab tests; moderating r/IndianFitness; importing raw whey. <5%.

---

## TG-2 — `aspirant_clean_label` (HIGH — Insta-discovered wellness woman)

**The voice:** aspirational, identity-coded, ingredient-aware at the front-of-pack level, aesthetics-driven, influenced by nutritionist-creators.

- "plant-based," "clean," "no maltodextrin," "no artificial sweetener" are the **filter words** she scans for *(aggregated across OZiva/Plix DTC + Nykaa)*.
- OZiva collagen taste reactions, verbatim from [Nykaa reviews](https://www.nykaa.com/oziva-plant-based-collagen-builder/reviews/517968): "tastes like hajmola"; "The taste is great, not too sweet or artificial"; "very Powderyy."
- Rejects gym-bro coding — "MuscleBlaze is not for me / that's gym-bro stuff" *(aggregated register; the masc-vs-wellness split is well attested)*.
- Discovery is influencer-led: nutritionist-creators (Lovneet Batra, Rashi Chowdhary) and the post-COVID self-care wave drive trial. — [Storyboard18 influencer-push piece](https://www.storyboard18.com/how-it-works/hair-gummies-protein-powders-get-influencer-push-as-brands-eye-indias-nutraceutical-market-6705.htm)

**Modal behaviors:** rotates plant protein + a beauty gummy (biotin/collagen) + a sleep/magnesium aid; ₹2-3K/month; shops Nykaa + brand DTC; tries a new brand when a trusted nutritionist tags it; mixes protein with oat/almond milk.
**Knowledge ceiling:** does NOT track clinical dosages; does NOT know what inositol does pharmacologically; does NOT distinguish Type I vs Type III collagen; does NOT post about supplements herself.
**Outlier (strip):** cross-referencing NIH/PubMed; reading certificates of analysis. <5%.

---

## TG-3 — `switcher_results_chaser` (HIGH, skeptical — the serial trier)

**The voice:** genuine, wants it to work, evidence-by-mirror. Gives each brand ~90 days, switches on no visible result. Reads review density obsessively.

- "I intake this product from last **2 and half month, not a single change i have seen on my face and body**" — verbatim, [Nykaa OZiva collagen](https://www.nykaa.com/oziva-plant-based-collagen-builder/reviews/517968)
- "the result is **zero, totally waste money**" / "used the product for **2.5 months but saw no changes**" *(prior corpus, OZiva Trustpilot aggregation)* — [Trustpilot](https://www.trustpilot.com/review/oziva.in)
- Power Gummies: "saw results within 2 months … much more shine" vs "**0 results after wasting money**," even "increased hair fall and weakened nails." — [Amazon Power Gummies](https://www.amazon.in/Power-Gummies-Hair-Vitamin-Biotin/dp/B07JLYS2QX)
- Switch destinations are review-driven: Setu (marine collagen, "fishy aftertaste if not masked"), HK Vitals ("great value … hairfall has reduced"), Plix (vegan). — [Ubuy collagen roundup](https://www.ubuy.co.in/blogs/best-collagen-supplements-in-india/), [HK Vitals](https://www.hkvitals.com/)

**Modal behaviors:** has cycled 4-5 hair/skin brands in 2 yrs; bar to buy = high Nykaa/Amazon verified-review count + 4★; gives 90 days then switches; ₹1.5-2.5K/month.
**Knowledge ceiling:** knows what biotin/collagen "are supposed to do," reads back-of-pack; does NOT see a dermatologist first, does NOT track a baseline metric, does NOT distinguish collagen types.
**Outlier (strip):** before/after photo logs; trichologist consults. ~10-15%.

---

## TG-4 — `doctor_triggered_vitamin` (MEDIUM — deficiency, prescription cohort)

**The voice:** "medicine, not lifestyle." Brand-indifferent, doctor-anchored, pharmacy-channel. Doesn't self-identify as a "supplement person."

- Real consult register (Practo/Apollo Q&A): "My wife has vitamin D deficiency, it is **8.5**, doctor suggested … D-Rise 60k or Calcirol 60k?" — [Practo Consult](https://www.practo.com/consult/d-rise-60k-or-calcirol-60k-sachet-dear-doctors-br-my-wife-has-vitamin-d-deficiency-it-is-8-5-doctor-suggested-for/q)
- Calcirol regimen learned from the doctor, not a brand: "1 sachet once a week for 8 weeks then once a month for 6 months … mix in milk." — [1mg Calcirol](https://www.1mg.com/otc/calcirol-60k-iu-cholecalciferol-sachet-for-bone-health-otc111246)
- Livogen = "the iron one," prescribed in pregnancy/postnatal; lived complaint is constipation. "ferrous fumarate may cause constipation … take with food." — [PharmEasy Livogen](https://pharmeasy.in/online-medicine-order/livogen-captab-15-s-8730), [Apollo Livogen XT](https://www.apollopharmacy.in/otc/livogen-xt-tablet)

**Modal behaviors:** takes vit-D sachet + iron + calcium because a blood test flagged it; reorders on 1mg/Apollo when one runs out; treats it as fixing a number; scrolls past Instagram wellness-brand ads.
**Knowledge ceiling:** does NOT know what an IU is; does NOT compare supplement brands; does NOT consider Plix/OZiva ("those are for influencer types"); knows her vit-D number and the brand name the doctor said.
**Outlier (strip):** researching cholecalciferol vs ergocalciferol; buying D3+K2 stacks online. <10%.

---

## TG-5 — `skeptic_lapsed_protein` (LOW — burned, scroll-past)

**The voice:** disillusioned, plain, structurally honest. Bought once, used ~60%, "did nothing," never again. The dominant 1-star register.

- "whey protein **isn't necessary to build a decent physique**" — [Quora: Is whey protein a scam](https://www.quora.com/Is-whey-protein-a-scam)
- "paid **5500 rupees** for what they considered a poor quality product … couldn't identify what they were actually consuming." — Quora (whey side-effects thread)
- The trust-collapse trigger: "many gym trainers have arrangements with local manufacturers who **refill boxes with cheaper weight gainers** or Bournvita." — Quora
- Reinforced by the Liver Doc headline this cohort half-remembers: "nearly **70%** of 36 supplements had inaccurate protein info, 14% had toxins." — [The South First](https://thesouthfirst.com/health/is-your-protein-supplement-safe-liver-docs-team-analysed-36-indian-products-and-heres-what-they-found/)

**Modal behaviors:** one tub bought after joining a gym 2023-24; ~60% used; rest binned; now scrolls past; "you still have to actually work out."
**Knowledge ceiling:** knows whey is "for muscle" and "you have to work out for it to do anything"; does NOT distinguish concentrate vs isolate; does NOT trust influencer claims anymore.
**Outlier (strip):** writing detailed teardown reviews; following the Liver Doc closely (that's TG-7, not this passive lapser).

---

## TG-6 — `pragmatist_protein_snacker` (LOW/occasional — "snack, not supplement")

**The voice:** casual, taste-and-convenience first. Doesn't see herself in the "supplements" world at all.

- Yogabar register, verbatim/near: "taste good and we get **20gm clean protein instantly** … when i am traveling it really helps me to complete my diet"; "make my stomach keep filled for sometimes … the package is **travel friendly**." — [Flipkart Yogabar](https://www.flipkart.com/yogabar-no-added-sugar-protein-bar-double-chocolate-pack-6-bars/product-reviews/itm01ae45e2e2c31?pid=PSLFCMXHFGVERRPR)
- Texture is the real gripe: "some find them crunchy, others **hard like a rock**." *(aggregated)* — [Flipkart Yogabar variety](https://www.flipkart.com/yogabar-20g-no-added-sugar-protein-bars-variety-pack-pack-12/product-reviews/itmf433bb83bf325)
- "guilt-free alternative to unhealthy snacks and junk food … office breaks, workouts, or travel" — the category's own framing this TG buys into. — [RiteBite Max Protein](https://maxprotein.in/)
- Whole Truth premium register: "dates-sweetened, 5-6 ingredients … ₹96 a bar on Blinkit/Zepto," "worth it" vs "expensive." — [Amazon Whole Truth](https://www.amazon.in/Whole-Truth-Protein-All-One/dp/B08KXVL9N6)

**Modal behaviors:** grabs a bar from Blinkit/airport during a 4pm crash or before yoga, ~3×/week; reaches for it instead of a biscuit; doesn't read past the front of pack.
**Knowledge ceiling:** knows it has "more protein than a chocolate bar"; does NOT see it as a "supplement"; does NOT track macros/calories; rejects whey powder ("that's for gym people").
**Outlier (strip):** comparing bars on protein-per-rupee spreadsheets. <5%.

---

## TG-7 — `purist_food_first` (LOW — supplements-are-a-scam, eat real food)

**The voice:** two flavours that converge — (a) traditional-food-wisdom (Rujuta Diwekar audience), (b) evidence-skeptic (Liver Doc audience). Actively resents wellness-supplement marketing.

- Rujuta Diwekar, verbatim: "**If your entire focus is on pills, powders, and products at the cost of eating home-cooked food, staying regular with your workouts, and sleeping well, then it's not worth it.**" — [Business Standard](https://www.business-standard.com/health/rujuta-diwekar-supplements-vs-home-food-soha-podcast-125082500358_1.html)
- "supplements **can't replace food, sleep or movement**"; her prescription is "**ghee with white rice and dal**," eat local & seasonal, "grandma knows best." — [Al Jazeera](https://www.aljazeera.com/economy/2021/7/23/indias-weight-loss-guru-rujuta-diwekar-on-why-grandma-knows-best)
- Evidence-skeptic anchor: the Liver Doc's "Citizens Protein Project," Himalaya Liv.52 defamation suit, herbal-induced liver injury (Giloy/Tinospora 43 cases). This TG cites "did you see that study, most of these are fake/adulterated." — [Wikipedia: Cyriac Abby Philips](https://en.wikipedia.org/wiki/Cyriac_Abby_Philips), [Medical Dialogues](https://medicaldialogues.in/news/health/doctors/liver-doc-summoned-in-criminal-defamation-case-over-herbal-medicine-row-159883)
- Mainstream-evidence backstop: "multivitamins did not reduce risk … money better spent on nutrient-packed foods … if you follow a healthy diet you get all you need from food." — [Johns Hopkins](https://www.hopkinsmedicine.org/health/wellness-and-prevention/is-there-really-any-benefit-to-multivitamins)

**Modal behaviors:** eats dal-rice-ghee-eggs-paneer-milk and considers that complete; scrolls past or eye-rolls wellness ads; will say "you don't need this, eat real food" in comment sections; trusts grandmother / a doctor / Rujuta over a brand.
**Knowledge ceiling:** has absorbed headlines ("70% are adulterated," "multivitamins are a waste") but does NOT read the primary studies; not anti-medicine (would take a doctor-prescribed vit-D), just anti-*lifestyle-supplement*.
**Outlier (strip):** being the Liver Doc / a practising hepatologist. This TG quotes him; isn't him.

---

## Current SKU + price reference (May–June 2026, web-verified)

| SKU | Price | Channel | Source |
|---|---|---|---|
| MuscleBlaze Biozyme Performance Whey 1kg (25g/scoop) | ₹2,699 (MRP ₹2,949, 8% off) | HealthKart | [HealthKart](https://www.healthkart.com/sv/muscleblaze-biozyme-performance-whey/SP-84971) |
| MuscleBlaze Beginner's Whey 1kg | ₹1,599 | Amazon | (prior corpus, Amazon) |
| Optimum Nutrition Gold Standard 2.27kg (24g/30g) | ₹4,200-4,800 (~₹70-80/serving) | Amazon | [CashKaro](https://cashkaro.com/blog/muscleblaze-vs-optimum-nutrition-which-has-a-better-whey-protein/37440) |
| AS-IT-IS Whey Concentrate 1kg (24g, unflavoured) | "<₹50/day" (~₹1,250) | Amazon / DTC | [Amazon AS-IT-IS](https://www.amazon.in/AS-Nutrition-Protein-Concentrate-Unflavoured/dp/B079SZJJDR) |
| OZiva Plant-Based Collagen Builder | ~₹1,499 | Nykaa | [Nykaa](https://www.nykaa.com/oziva-plant-based-collagen-builder/reviews/517968) |
| Power Gummies Hair & Nails (biotin, 60-day) | ~₹699 | Amazon / DTC | [Amazon](https://www.amazon.in/Power-Gummies-Hair-Vitamin-Biotin/dp/B07JLYS2QX) |
| HK Vitals Skin Radiance Collagen | value tier | HealthKart / Flipkart | [HK Vitals](https://www.hkvitals.com/sv/hk-vitals-skin-radiance-collagen/SP-99764) |
| Yogabar 20g Protein Bar (variety pack of 5) | ₹625 | Flipkart | [Flipkart](https://www.flipkart.com/yogabar-20g-protein-healthy-protein-snacks-variety-pack-5-bars/p/itm4becedfff8e9e) |
| The Whole Truth Protein Bar (single) | ₹96 | Blinkit / Zepto | [Amazon Whole Truth](https://www.amazon.in/Whole-Truth-Protein-All-One/dp/B08KXVL9N6) |
| Calcirol 60K IU sachet | ~₹35/sachet | 1mg / Apollo | [1mg](https://www.1mg.com/otc/calcirol-60k-iu-cholecalciferol-sachet-for-bone-health-otc111246) |
| Livogen XT (10 tablets) | ~₹80 | Apollo / PharmEasy | [Apollo](https://www.apollopharmacy.in/otc/livogen-xt-tablet) |

## Creators / cultural anchors (for the pack's `communities` + `cultural_references`)

- **Tarun Gill**, **Guru Mann**, **Fittuber** — male performance-supplement YouTube; the lifter TG's reference.
- **Lovneet Batra**, **Rashi Chowdhary** — nutritionist-creators; the clean-label woman's trigger.
- **Rujuta Diwekar** — food-first wisdom; "ghee + dal + rice," grandma-knows-best.
- **The Liver Doc (Dr Cyriac Abby Philips)** — evidence-skeptic; Citizens Protein Project; Himalaya defamation suit.
- **Country Delight × HRX "Mission Protein"** — the 2026 mainstreaming of the protein-gap narrative.
