# Disposition Demographic Bundles — health_wellness_nutrition

**Purpose:** coherent per-disposition persona bundles that realize the income distributions in `docs/disposition_income_brackets.md`. Each disposition's agents are allocated across its bundles by weight (deterministic largest-remainder), so income varies realistically AND every persona's occupation/geo stays consistent with its income tier.

**Status:** re-authored 2026-08-13 (session 38). Generated from `scripts/scaffold_health_wellness.py`, which is the source of truth — `runs/.../entities/library.json` is regenerated from it. Pinned by `tests/test_persona_biographies.py`.

Income tiers: `mass` <₹3.5L · `lower_mid` ₹3.5–7L · `upper_mid` ₹7–17L · `affluent` ₹17–40L · `premium` ₹40L+.

---

## ⭐ What changed, and the measurement that forced it

The old table had **one bundle per income row** — 5 biographies per disposition. That looks like enough until you notice what the declared audience does to it. `demographic_overlap` is **gender × age × income only**, so under the shipped 25-44 / ₹7-40L brief the `mass`, `lower_mid` and `premium` rows score zero and **drop out entirely**. Every disposition was left with its `upper_mid` and `affluent` rows — two biographies each.

Measured on the 2026-08-11 protein-bar run and reproduced exactly offline:

| | before | after |
|---|---:|---:|
| distinct biographies backing 100 agents | **10** | **25** |
| agents sharing the single most common biography | **15** | **5** |
| distinct persona cores (= paid renders, cold cache) | 29 | 60 |
| bundles in the library | 30 | 62 |

Fifteen agents were the same person — same job, same household, same everything the persona writer is handed except the chaos vector.

### The splitting rule

Sub-bundles of one documented row share its **gender, age band and summed weight**, and differ only in **geography / occupation_hint / household_hint**. Because overlap ignores all three of those, every sub-bundle of a row scores the identical overlap, so `audience_mass` — the marketer-led selection weight — is **arithmetically unchanged**. The research income distribution is untouched; only the number of distinct people realizing it moved.

Rows under ~10% are left **whole**: at ~17 agents per disposition a 5% row is already under one agent, so splitting it would delete it from the panel rather than diversify it.

### The authoring rule: the bundle owns WHO, the anchor owns WHAT THEY THINK

`occupation_hint` and `household_hint` reach the persona writer through `render.persona_writer_demographics`, and unlike `income_lpa_*` they are **not** redacted. That makes them a second seam for the render-10 uniformity defect, and the old hints were sitting in it:

- **Category content in a hint pre-agrees the panel.** "outcome-driven", "mid-market gummies", "distrusts the category" arrived verbatim on every agent drawn from that bundle — maximally prevalent, so a prevalence floor cannot distinguish it from consensus.
- **Product content in a hint leaks the wrong product across runs.** "protein bar as a convenient snack" met a collagen ad unchanged; "buys imported whey" met a bar ad unchanged.
- **Two hints contradicted their own anchor's L3 knowledge ceiling.** The `switcher` premium hint said "dermatologist-guided" where L3 says *does NOT see a dermatologist first*; the `purist` affluent hint made the person a **doctor** where L3 says *does NOT read the studies*. Both are now non-medical professions — protocol v2 §8 vector/anchor coherence.

Hints now carry **the job, the city and one household detail. Nothing else.** No ₹ figure and no income word (that would bypass the §2.6 redaction), no brand or platform (`test_anchors_are_brand_free.py`), and no gendered pronoun in a `gender="any"` bundle (the frame resolves the side at `_clip_point`, and a baked-in pronoun contradicts it for half the panel).

Geography is now **named cities**. It composes the targeting sentence and adds render vividness; it does **not** narrow the panel.

---

## 1. `enthusiast_macros_lifter` — rows [12, 26, 38, 18, 6] · young, male-skewed
*11 bundles across 5 income rows.*

| wt | tier | gender | age | city | occupation | household |
|---:|---|---|---|---|---|---|
| 6 | mass | male | 18-24 | Nagpur / tier-2 town | second-year college student; trains before morning classes | lives with parents and a younger brother; no rent, small allowance |
| 6 | mass | male | 18-24 | Rajkot / tier-3 town | works the counter at his family's mobile-repair shop | joint family home; eats whatever the kitchen cooks |
| | | | | | | |
| 13 | lower_mid | male | 25-34 | Indore / tier-2 city | junior field-sales executive covering a two-district territory | shares a rented 1BHK with two flatmates; sends money home monthly |
| 13 | lower_mid | male | 25-34 | Coimbatore / tier-2 city | assistant trainer at a neighbourhood gym; takes the evening batches | rented room near the gym; cooks on a single burner |
| | | | | | | |
| 13 | upper_mid | male | 25-34 | Bangalore / metro tier-1 | backend engineer at a mid-stage startup; lifts before work five days a week | 1BHK in a gated block, lives alone; orders in most nights |
| 13 | upper_mid | male | 25-34 | Pune / metro tier-1 | operations manager at a logistics firm; 6am gym before the shift | 2BHK with a flatmate; meal-preps chicken and rice on Sundays |
| 12 | upper_mid | male | 25-34 | Hyderabad / metro tier-1 | product designer; lifts four evenings a week after office | 1BHK near the office; parents visit twice a year |
| | | | | | | |
| 9 | affluent | male | 35-44 | Delhi NCR / metro tier-1 | chartered accountant running his own practice; members' gym before the office | owns a 3BHK, married, one toddler |
| 9 | affluent | male | 35-44 | Mumbai / metro tier-1 | regional sales head; works out in hotel gyms three weeks a month | owns a flat, married; travels Monday to Thursday |
| | | | | | | |
| 3 | premium | male | 35-44 | Mumbai / metro tier-1 | founder of a mid-size firm; trains with a personal coach at a boutique studio | high-rise apartment with family; a cook handles meals |
| 3 | premium | male | 35-44 | Gurugram / metro tier-1 | senior banking executive; 5am strength sessions with a coach | owns a duplex; two kids in school, staff at home |

## 2. `aspirant_clean_label` — rows [5, 17, 45, 26, 7] · woman, 25-40, metro
*9 bundles across 5 income rows.*

| wt | tier | gender | age | city | occupation | household |
|---:|---|---|---|---|---|---|
| 5 | mass | female | 25-34 | Jaipur / tier-2 city | front-desk executive at a clinic | lives with parents; saving for a wedding |
| | | | | | | |
| 9 | lower_mid | female | 25-34 | Kochi / tier-2 city | early-career content writer at a small agency | shares a flat with a colleague; cooks most dinners |
| 8 | lower_mid | female | 25-34 | Chandigarh / tier-1 | junior HR executive at a mid-size company | paying-guest room; family in the same city |
| | | | | | | |
| 15 | upper_mid | female | 25-34 | Mumbai / metro tier-1 | brand marketing manager at a consumer company | 1BHK in the metro core, lives alone; long commute |
| 15 | upper_mid | female | 25-34 | Bangalore / metro tier-1 | UX designer at a product company; morning yoga three times a week | 2BHK with her partner; recently married |
| 15 | upper_mid | female | 25-34 | Delhi NCR / metro tier-1 | account manager at an agency; Pilates class on weekends | rented 2BHK with a flatmate; family an hour away |
| | | | | | | |
| 13 | affluent | female | 35-44 | Mumbai / metro tier-1 | senior product manager; a tight morning routine before the kids wake | owns a 3BHK; two young kids and full-time help |
| 13 | affluent | female | 35-44 | Bangalore / metro tier-1 | runs a small design studio she founded | owns a flat, married, one child in playschool |
| | | | | | | |
| 7 | premium | female | 35-44 | Delhi NCR / metro tier-1 | co-founder of a growing company; a trainer on retainer | large flat, household staff; two kids |

## 3. `switcher_results_chaser` — rows [12, 30, 39, 16, 3] · working women, 25-44, broad
*11 bundles across 5 income rows.*

| wt | tier | gender | age | city | occupation | household |
|---:|---|---|---|---|---|---|
| 6 | mass | female | 25-34 | Patna / tier-3 town | school teacher in her second year of work | lives with parents; contributes to the household |
| 6 | mass | female | 25-34 | Nashik / tier-2 city | receptionist at a small clinic | shares a flat with her sister; both send money home |
| | | | | | | |
| 10 | lower_mid | female | 25-34 | Hyderabad / tier-1 | process associate on a night shift at a BPO | shares a flat with two colleagues; sleeps days |
| 10 | lower_mid | female | 25-34 | Lucknow / tier-2 city | retail floor supervisor at a mall store; on her feet nine hours | lives with family; long bus commute |
| 10 | lower_mid | female | 25-34 | Bhopal / tier-2 city | primary school teacher; grades papers after dinner | married, one small child; joint family home |
| | | | | | | |
| 13 | upper_mid | female | 25-34 | Bangalore / metro tier-1 | business analyst at a consulting firm; long desk hours | 1BHK alone; parents in another city |
| 13 | upper_mid | female | 25-34 | Mumbai / metro tier-1 | assistant manager at a bank; two-hour daily commute | shares a 2BHK; recently engaged |
| 13 | upper_mid | female | 25-34 | Chennai / metro tier-1 | software tester; back-to-back calls most afternoons | 2BHK with her husband; no kids yet |
| | | | | | | |
| 8 | affluent | female | 35-44 | Delhi NCR / metro tier-1 | senior HR business partner; travels for hiring drives | owns a 3BHK; one child in primary school |
| 8 | affluent | female | 35-44 | Pune / metro tier-1 | runs a boutique event-management outfit | owns a flat, married; help comes twice a day |
| | | | | | | |
| 3 | premium | female | 35-44 | Mumbai / metro tier-1 | practice head at a consulting firm; long-haul travel most months | sea-facing flat; full household staff |

## 4. `skeptic_lapsed_protein` — rows [20, 32, 32, 12, 4] · mirrors enthusiast, lapsed/value
*11 bundles across 5 income rows.*

| wt | tier | gender | age | city | occupation | household |
|---:|---|---|---|---|---|---|
| 10 | mass | male | 18-24 | Kanpur / tier-3 town | final-year college student; plays cricket on Sundays | lives with family in a rented ground-floor flat |
| 10 | mass | male | 18-24 | Jodhpur / tier-2 town | works at his uncle's electrical-goods shop | joint family; eats all three meals at home |
| | | | | | | |
| 11 | lower_mid | male | 25-34 | Surat / tier-2 city | salaried accountant at a textile trading firm | shares a flat; carries a home-packed lunch |
| 11 | lower_mid | male | 25-34 | Vadodara / tier-2 city | junior civil engineer on site most days | rented room near the site; family in the village |
| 10 | lower_mid | male | 25-34 | Mysuru / tier-2 city | customer-support executive on rotating shifts | shares a 1BHK with a cousin |
| | | | | | | |
| 11 | upper_mid | any | 25-34 | Bangalore / metro tier-1 | QA engineer at a services company; desk job, walks in the evening | 1BHK alone; cooks twice a week |
| 11 | upper_mid | any | 25-34 | Delhi NCR / metro tier-1 | media planner at an agency; irregular hours | shares a 2BHK with two flatmates |
| 10 | upper_mid | any | 25-34 | Chennai / metro tier-1 | school administrator; steady nine-to-five | lives with parents; the family kitchen runs the meals |
| | | | | | | |
| 6 | affluent | any | 35-44 | Mumbai / metro tier-1 | project manager at an IT firm; badminton twice a week | owns a 2BHK, married, one child |
| 6 | affluent | any | 35-44 | Hyderabad / metro tier-1 | runs a small trading business | owns a flat; two kids, the kitchen runs on a fixed routine |
| | | | | | | |
| 4 | premium | any | 35-44 | Bangalore / metro tier-1 | engineering director at a large tech company | villa in a gated community; a cook and daily help |

## 5. `pragmatist_protein_snacker` — rows [6, 18, 40, 26, 10] · 25-44, mixed, metro
*10 bundles across 5 income rows.*

| wt | tier | gender | age | city | occupation | household |
|---:|---|---|---|---|---|---|
| 6 | mass | any | 25-34 | Guwahati / tier-2 city | junior lab technician at a diagnostics centre | shares a rented room; canteen lunches |
| | | | | | | |
| 9 | lower_mid | any | 25-34 | Bhubaneswar / tier-2 city | graphic designer at a small studio; works late often | shares a flat; skips dinner more often than not |
| 9 | lower_mid | any | 25-34 | Kochi / tier-1 | trainee at an audit firm; long client-site days | paying-guest accommodation; no kitchen |
| | | | | | | |
| 14 | upper_mid | any | 25-34 | Bangalore / metro tier-1 | consultant at a professional-services firm; back-to-back meetings | 1BHK alone; a 4pm slump most days |
| 13 | upper_mid | any | 25-34 | Mumbai / metro tier-1 | investment banking analyst; desk lunch, late finishes | shares a 2BHK; barely home except to sleep |
| 13 | upper_mid | any | 25-34 | Gurugram / metro tier-1 | product marketer at a tech company; hybrid, three days in office | 2BHK with a partner; neither of them cooks much |
| | | | | | | |
| 13 | affluent | any | 35-44 | Delhi NCR / metro tier-1 | senior manager at a consumer company; school run before office | owns a 3BHK; two kids, packed mornings |
| 13 | affluent | any | 35-44 | Pune / metro tier-1 | engineering lead; keeps a desk drawer stocked for late evenings | owns a flat, married; one child |
| | | | | | | |
| 5 | premium | any | 35-44 | Mumbai / metro tier-1 | vice-president at a financial services firm; gym at 6am, office by 8 | high-rise flat; a cook, a driver, two kids |
| 5 | premium | any | 35-44 | Bangalore / metro tier-1 | startup founder; eats at the desk between meetings | large apartment; help manages the house |

## 6. `purist_food_first` — rows [12, 22, 34, 24, 8] · older 35-55, traditional
*10 bundles across 5 income rows.*

| wt | tier | gender | age | city | occupation | household |
|---:|---|---|---|---|---|---|
| 6 | mass | any | 45-54 | Varanasi / tier-3 town | shopkeeper on a busy market lane; opens at eight every morning | joint family above the shop; one kitchen for nine people |
| 6 | mass | any | 45-54 | Salem / tier-2 town | government clerk nearing thirty years of service | own small house; a vegetable patch at the back |
| | | | | | | |
| 11 | lower_mid | any | 35-44 | Jalandhar / tier-2 city | runs a small hardware business with a brother | family home; mother still runs the kitchen |
| 11 | lower_mid | any | 35-44 | Trichy / tier-2 city | bank clerk; cycles to work | rented house; two school-going kids |
| | | | | | | |
| 12 | upper_mid | any | 35-44 | Chennai / metro tier-1 | civil engineer at a construction firm; carries lunch from home daily | 2BHK with parents and one child |
| 11 | upper_mid | any | 35-44 | Pune / metro tier-1 | college lecturer; walks in the mornings | family flat; someone cooks fresh every evening |
| 11 | upper_mid | any | 35-44 | Kolkata / metro tier-1 | bank branch manager; fixed hours, home by seven | family home; three generations at one table |
| | | | | | | |
| 12 | affluent | any | 45-54 | Delhi NCR / metro tier-1 | practising lawyer with an independent chamber | owns a house; grown kids, home-cooked meals |
| 12 | affluent | any | 45-54 | Mumbai / metro tier-1 | senior government officer close to retirement | owns a flat; a cook who has been with the family for years |
| | | | | | | |
| 8 | premium | any | 55-75 | Bangalore / metro tier-1 | retired professor; a morning walk and the newspaper | large house; children abroad, help lives in |

---

## `doctor_triggered_vitamin` — deliberately has NO bundles

It is excluded from the cold-traffic audience (it ignores every wellness-brand ad; it belongs in a deficiency/medical audience), and a disposition with no bundles returns `audience_mass` 1.0 — "lives everywhere". Authoring bundles for it is a real job, but it should be done **when an audience actually uses it**, not speculatively.

## Coherence checks

- **Income↔occupation:** every `mass`/`lower_mid` bundle is a student/junior/tier-2 role; every `affluent`/`premium` bundle is a settled/senior/metro role. No "family head tagged mass" contradictions.
- **Gender/age skew honored:** enthusiast & skeptic male-skewed and young; aspirant & switcher female 25–44; snacker mixed 25–44; purist `any` but oldest (35–55+).
- **Income weights = research table:** each disposition's bundle weights still sum, per row, to its row in `disposition_income_brackets.md`. Pinned by `test_income_rows_survive_being_split`.
- **No occupational expertise in the category:** protocol v2 §6 check 2. Nobody in this library is a doctor, dietitian or sports nutritionist — that would hand a persona knowledge its own anchor L3 denies.
- **Tails at small panels:** at ~16–17 agents/disposition the `premium`/`mass` tails resolve to ~1 agent — largest-remainder allocation makes them appear deterministically rather than rounding to zero.

## What this does NOT do

It does not move the problem-map signal. Sociodemographics are the **weakest** channel in the realism literature (≈1.5% of response variance, vs 1.4–10.6% for persona variables), and the gate test already shows the **ad**, not the disposition layer, drives the problem map (0.148 between-ad vs 0.231 same-ad Jaccard). This makes the panel read as real people and removes two measurement contaminants. Treat any claim beyond that as unmeasured.
