# Disposition Income Brackets — health_wellness_nutrition

**Purpose:** per-disposition income distributions to sample each agent's `income_tier` at panel-build time, replacing the current uniform 3-frame model where every disposition inherits the same `upper_mid`/`affluent` tiers. Income skews *per disposition* because income is partly constitutive of the buyer type.

**Status:** research framework (2026-06-10). Not yet wired into `agent/panel.py` / the audience spec. Grounded in named MBB / Kantar / PRICE / category reports (sources at bottom). **The relative orderings across dispositions are the defensible part; absolute cell values are evidence-grounded inferences, not measured splits — no published per-archetype income crosstab exists. Confidence ceiling is Medium.**

---

## Income tier definitions (annual HOUSEHOLD income, INR)

| Tier | Annual HH income | NCCS (approx) | PRICE ICE 360° anchor |
|---|---|---|---|
| `mass` | < ₹3.5L | C2 / D / E | Destitute + lower Aspirer |
| `lower_mid` | ₹3.5–7L | C1 / B2 | Upper Aspirer → entry "Seeker" |
| `upper_mid` | ₹7–17L | B1 / A3 | Core "Seeker" middle class |
| `affluent` | ₹17–40L | A2 | "Striver" middle → entry near-rich |
| `premium` | ₹40L+ | A1 | Near-rich → rich tail |

Caveats on the scale: NCCS has no income cutoffs (it's education-of-CWE + durables) — the NCCS column is an illustrative bridge. PRICE ICE 360° (200K households, income-based) is the anchor; boundaries are interpolated between PRICE breakpoints (1.25 / 5 / 15 / 30 / 50L). Goldman Sachs "Affluent India" (₹8.3L+, ~60M people 2023) independently corroborates the upper_mid floor. Tiers are a household-income proxy applied to reachable individuals.

---

## Per-disposition income distributions  (each row sums to 100)

| Disposition | `mass` | `lower_mid` | `upper_mid` | `affluent` | `premium` | Conf | Modal tier |
|---|---:|---:|---:|---:|---:|---|---|
| `enthusiast_macros_lifter` | 12 | 26 | **38** | 18 | 6 | Med | upper_mid (broad/bimodal) |
| `aspirant_clean_label` | 5 | 17 | **45** | 26 | 7 | Med | upper_mid (most affluent-skewed) |
| `switcher_results_chaser` | 12 | 30 | **39** | 16 | 3 | Med | upper_mid (broad, pragmatic) |
| `skeptic_lapsed_protein` | 20 | **32** | 32 | 12 | 4 | Med-Low | lower_mid/upper_mid (most value) |
| `pragmatist_protein_snacker` | 6 | 18 | **40** | 26 | 10 | Med | upper_mid (metro, no mass tail) |
| `purist_food_first` | 12 | 22 | **34** | 24 | 8 | Med-Low | upper_mid (traditionalist) |
| — *reference: Meta-reachable baseline* | 21 | 30 | 31 | 12 | 6 | Med | — |
| — *derived: cold-traffic 6-disp mean* | ≈11 | ≈24 | ≈38 | ≈20 | ≈7 | — | — |

### Rationale (one line each)
- **`enthusiast_macros_lifter` `[12,26,38,18,6]`** — whey is pricey (₹2–4k/tub) but MuscleBlaze democratized it into tier-2/3 + railway stalls; the mass/lower_mid tail is young aspirational gym-goers stretching budgets (individual spend ≠ household income). Broadest/most bimodal.
- **`aspirant_clean_label` `[5,17,45,26,7]`** — premium D2C clean-label (OZiva/Plix/Wellbeing), Instagram-discovered metro woman; RedSeer's premium-wellness buyer = HHI >₹12L metro. Most affluent-skewed; mass suppressed (premium-priced, metro).
- **`switcher_results_chaser` `[12,30,39,16,3]`** — beauty/nutricosmetic results-chaser also buys mid-market Amazon brands + gummy/sachet entry formats → broader & more pragmatic than the aspirant; NCCS-B middle-income (₹6–7.5L) is the center of gravity; thin premium head.
- **`skeptic_lapsed_protein` `[20,32,32,12,4]`** — the enthusiast pool shifted DOWN: lapse is price- and trust-driven (Citizens Protein Project: 70% of 36 supplements mislabelled). Premium buyers rarely lapse on price, so the top thins and mass+lower_mid (52%) is the largest of any disposition.
- **`pragmatist_protein_snacker` `[6,18,40,26,10]`** — protein bars are metro premium impulse (₹90–100/bar); nobody budget-stretches for a bar, so it loses the enthusiast's aspirational mass tail and tilts affluent. *(Independent cross-check landed `[4,14,36,32,14]` — even more affluent; this primary is the conservative read.)*
- **`purist_food_first` `[12,22,34,24,8]`** — underlying population is bimodal (affordability-rejecters at the bottom + affluent traditionalists who choose dal-rice on principle), but cold-traffic ad addressability filters out most of the affordability tail → the affluent/upper_mid traditionalist dominates, with a residual value tail. Swings most with where the campaign draws its audience boundary.

---

## Validation check
The 6-disposition mean `≈[11, 24, 38, 20, 7]` sits **above** the generic Meta-reachable baseline `[21, 30, 31, 12, 6]` — i.e. richer. This is **correct, not a contradiction**: a supplement/wellness *cold-traffic* audience is a self-selected, more affluent subset of all Instagram users. The per-disposition curves being collectively richer than the platform baseline is the expected shape.

## Soft spots (flagged honestly)
1. **`skeptic_lapsed_protein` (Med-Low)** — no lapsed-user income survey exists; derived as a downward shift of the enthusiast using churn-driver evidence (price sensitivity + trust collapse). Weakest single cell set.
2. **`purist_food_first` (Med-Low)** — built from a proxy chain (PwC tradition-attitude + protein-gap affordability + clean-eating-is-affluent-adopter + LocalCircles ad-pool tier skew). The biggest swing factor is the campaign's audience boundary: a broad/cheap reach campaign pulls it toward `mass`; a narrow fitness-interest campaign pushes it toward `affluent`.
3. **Spend-share vs headcount.** All distributions are HEADCOUNT (people), not rupee spend-share. If ever weighted by purchase value, the top two tiers inflate substantially. Correct for a synthetic *audience*.

---

## Sources (condensed)
**Framework / income scale:** PRICE ICE 360° "Rise of India's Middle Class" 2022 (Shukla); Goldman Sachs "Rise of Affluent India" 2024; Kantar/MRUC NCCS; Bain–Flipkart "How India Shops Online" 2023/2025; IAMAI–Kantar ICUBE 2023/25; DataReportal "Digital 2025: India" (Meta ~557M reach); McKinsey "Bird of Gold" 2007 (historical).
**Protein / sports nutrition:** IMARC India Protein Supplements & Whey 2024; Avendus "India Unjunking"; Spherical Insights India Whey 2025; IBEF "Fuelling Fitness"; Mordor India Energy Bar; nutraingredients Apr 2026; Citizens Protein Project (Medicine journal 2024 / Business Standard 2025); LoEstro "Powered by Protein"; Inc42 (The Whole Truth FY25).
**Clean-label / nutricosmetics:** RedSeer Quick Commerce & Consumer Health 2024–25; Nykaa–RedSeer Premiumization 2024; IMARC India Collagen / Beauty Supplements 2024; Inventiva (Wellbeing Nutrition); Tracxn (OZiva 70% women).
**Food-first / attitude:** PwC "Voice of the Consumer 2025" India (74% food rooted in tradition); LocalCircles×Country Delight Protein Gap 2025 (60% urban protein-deficient, affordability #1); LocalCircles Nutraceuticals 2024 (tier mix 45/31/24); McKinsey "Future of Wellness" 2024; Frontiers in Nutrition 2022 (urban middle-class food choices); Mondelēz "State of Snacking" 2024.
