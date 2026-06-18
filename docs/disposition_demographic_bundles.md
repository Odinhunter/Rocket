# Disposition Demographic Bundles — health_wellness_nutrition

**Purpose:** coherent per-disposition persona bundles that realize the income distributions in `docs/disposition_income_brackets.md`. Each disposition's agents are allocated across its bundles by weight (deterministic largest-remainder), so income varies realistically AND every persona's occupation/geo stays consistent with its income tier. Replaces the old 3-frame global `spec.demographics` cross-product (which pinned every disposition to the same upper_mid/affluent frames).

**Status:** DRAFT for review (2026-06-10). Needs human eye on occupation↔income coherence and gender/age skews before wiring into `agent/panel.py`. Bundle `weight` = % of that disposition's agents (sums to ~100 per disposition, matching the research income table). Gender/age skews per disposition are from the category research (enthusiast young male; aspirant/switcher women 25–40; purist older 35–55; snacker 25–44 mixed).

Income tiers: `mass` <₹3.5L · `lower_mid` ₹3.5–7L · `upper_mid` ₹7–17L · `affluent` ₹17–40L · `premium` ₹40L+.

---

## 1. `enthusiast_macros_lifter`  — target [12, 26, 38, 18, 6] · young, male-skewed
| wt | gender | age | income | geography | occupation | household |
|---:|---|---|---|---|---|---|
| 12 | male | 18_24 | mass | tier-2/3 town | college student / gym trainee; stretches budget for a value whey tub | joint family home |
| 26 | male | 25_34 | lower_mid | tier-2 city | junior sales/field exec or assistant gym trainer; buys MuscleBlaze on discount | shared flat with flatmates |
| 38 | male | 25_34 | upper_mid | metro / tier-1 | software/ops professional, serious 5-day gym routine | 1–2BHK metro, single |
| 18 | male | 35_44 | affluent | metro | established professional/business owner; imported whey (ON) | owns flat, married |
| 6 | male | 35_44 | premium | metro | senior manager / founder; boutique gym + personal coach | premium high-rise, family |

## 2. `aspirant_clean_label`  — target [5, 17, 45, 26, 7] · woman, 25–40, metro
| wt | gender | age | income | geography | occupation | household |
|---:|---|---|---|---|---|---|
| 5 | female | 25_34 | mass | tier-2 city | aspirational follower of wellness influencers; rarely converts at premium price | family home |
| 17 | female | 25_34 | lower_mid | tier-1 / tier-2 | early-career content/marketing exec; buys occasional OZiva on sale | shared flat |
| 45 | female | 25_34 | upper_mid | Mumbai / Bangalore metro | marketing/design/product professional; Instagram-discovered wellness buyer | 1–2BHK metro, single or recently married |
| 26 | female | 35_44 | affluent | metro | settled professional / small entrepreneur; regular premium D2C wellness | owns home, young kids |
| 7 | female | 35_44 | premium | metro | affluent founder / homemaker; full premium wellness stack | premium metro, household help |

## 3. `switcher_results_chaser`  — target [12, 30, 39, 16, 3] · working women, 25–44, broad
| wt | gender | age | income | geography | occupation | household |
|---:|---|---|---|---|---|---|
| 12 | female | 25_34 | mass | tier-2/3 | value-seeker chasing hair/skin fixes via cheap Amazon biotin | family home |
| 30 | female | 25_34 | lower_mid | tier-1 / tier-2 | salaried (BPO / retail / teaching); mid-market gummies, switches on no result | shared or family flat |
| 39 | female | 25_34 | upper_mid | metro / tier-1 | working professional; Nykaa/Amazon collagen & biotin, outcome-driven | metro flat |
| 16 | female | 35_44 | affluent | metro | settled professional; mixes premium + mid brands, results-led | owns home |
| 3 | female | 35_44 | premium | metro | affluent; dermatologist-guided premium nutricosmetics | premium metro |

## 4. `skeptic_lapsed_protein`  — target [20, 32, 32, 12, 4] · mirrors enthusiast, lapsed/value
| wt | gender | age | income | geography | occupation | household |
|---:|---|---|---|---|---|---|
| 20 | male | 18_24 | mass | tier-2/3 | tried a trainer-pushed tub, quit on cost; back to home food | family / shared, tier-2 |
| 32 | male | 25_34 | lower_mid | tier-2 city | salaried; bought discount whey once, churned on price + doubt | shared flat |
| 32 | any | 25_34 | upper_mid | metro / tier-1 | professional; lapsed after mislabeling news, now skeptical | metro flat |
| 12 | any | 35_44 | affluent | metro | settled; tried premium, didn't see the value, dropped it | owns home |
| 4 | any | 35_44 | premium | metro | affluent; tried & abandoned, indifferent to the category | premium metro |

## 5. `pragmatist_protein_snacker`  — target [6, 18, 40, 26, 10] · 25–44, mixed, metro, no mass tail
| wt | gender | age | income | geography | occupation | household |
|---:|---|---|---|---|---|---|
| 6 | any | 25_34 | mass | tier-2 | occasional bar buyer at quick-commerce, price-aware | family / shared |
| 18 | any | 25_34 | lower_mid | tier-1 / tier-2 | young salaried; grabs a Yogabar on Blinkit sometimes | shared flat |
| 40 | any | 25_34 | upper_mid | metro | busy professional; protein bar as a convenient snack | metro flat, single or married |
| 26 | any | 35_44 | affluent | metro | settled professional; mindful-indulgence snacker, premium bars | owns home, kids |
| 10 | any | 35_44 | premium | metro | affluent; habitual premium D2C snacking | premium metro |

## 6. `purist_food_first`  — target [12, 22, 34, 24, 8] · older 35–55, traditional
| wt | gender | age | income | geography | occupation | household |
|---:|---|---|---|---|---|---|
| 12 | any | 45_54 | mass | tier-2/3 | value household; home-cooked dal-rice, no spare for supplements | joint family, tier-2 |
| 22 | any | 35_44 | lower_mid | tier-2 city | salaried / small-business; traditional diet, rejects supplements on cost + principle | family home |
| 34 | any | 35_44 | upper_mid | metro / tier-1 | established professional; traditional eater, "real food is enough" | family home, metro |
| 24 | any | 45_54 | affluent | metro | settled professional / doctor; affluent traditionalist, distrusts the category | owns home |
| 8 | any | 55_plus | premium | metro | affluent elder / senior professional; full home-cooked, philosophically anti-supplement | premium metro, household help |

---

## Coherence checks
- **Income↔occupation:** every `mass`/`lower_mid` bundle is a student/junior/tier-2 role; every `affluent`/`premium` bundle is a settled/senior/metro role. No "finance family head tagged mass" contradictions.
- **Gender/age skew honored:** enthusiast & skeptic male-skewed and young; aspirant & switcher female 25–44; snacker mixed 25–44; purist `any` but oldest (35–55+).
- **Income weights = research table:** each disposition's bundle weights reproduce its row in `disposition_income_brackets.md`.
- **Tails at small panels:** at ~16–17 agents/disposition, the `premium`/`mass` tails resolve to ~1 agent — largest-remainder allocation makes them appear deterministically rather than rounding to zero.

## Open authoring notes
- Within-tier variation is currently 1 bundle per income tier (gender/age fixed per tier). If you want e.g. both a male and female upper_mid snacker, split that bundle into two with half weight each — cheap to add later.
- `geography` is kept coarse (metro / tier-1 / tier-2/3) and coherent with income; can be sharpened to named cities if useful for render vividness.
