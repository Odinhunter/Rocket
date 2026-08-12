# Disposition Authoring Protocol — v2

**Status:** v2 · 2026-05-26 · ACTIVE
**Supersedes:** `docs/disposition_protocol.md` (v1, retired)
**Owner:** Ishan (writes + reviews every disposition personally; protocol is the working spec)
**Scope:** Used for every disposition added to any brand library during v1 build (`health_wellness_nutrition`, then rewrites of `personal_audio`, `chocolate`, `coffee`).

---

## §0 — What changed from v1 → v2

| Aspect | v1 | v2 |
|---|---|---|
| Methodology | Per-disposition corpus scrape (≥30 sources × 4 source types, ~3-4 hr per disposition) | Disciplined hand-mapping + lightweight manual mini-corpus (~30-40 min per disposition) |
| Sourcing standard | Scraped + LLM-extracted | Hand-curated from a 20-30-sample-per-category voice file + Ishan's domain knowledge + research thinking |
| Time cost per disposition | 3-4 hours | 30-40 minutes |
| Time cost per category (6 dispositions) | 18-24 hours | 3-4 hours |
| Realism floor | "behaviors attested across ≥2 source families" | "would I meet this person at a wedding" + "L3 KNOWLEDGE explicitly bounds expertise" + manual-corpus voice samples in render prompt |
| When v1 still applies | After v2 ships and first design partner reaction validates the simpler approach | — |

**Why simpler:** v1 protocol assumed the modal-behaviors library was the unit of work. For v1 launch we're skipping the scraped corpus and hand-mapping under discipline. v2 protocol gets us to 70-80% of v1's voice realism at 5% of the time cost. The full scraped library is now ROADMAP P0.1 (post-launch).

**v1 protocol stays in repo** as `docs/disposition_protocol.md` with a SUPERSEDED banner — it's the right protocol when/if we get back to per-disposition rigor. v2 is what we use now.

---

## §1 — The failure mode this protocol prevents (unchanged from v1)

Dispositions can fail in two opposite directions:

1. **Too generic** — every "loyalist" sounds the same; no specific behavior; agents produce vague reactions. (Solved in v1 with anchors; carries forward.)
2. **Too extreme** — the anchor specifies an outlier behavior (Notion doc, frequency-response measurements, /r/headphones moderator); agents talk like industry insiders, not consumers. **This is the current cmf_ad failure.**

The protocol's job: push every disposition into the realistic-but-distinctive middle — **the top 20% of buyers for that stance, not the top 0.1%.**

An audio enthusiast knows the brand hierarchy, can tell good ANC from bad, watches a YouTube review before buying — and *cannot* read a frequency-response curve, *does not* keep spreadsheets, *has never* heard of Topping or Moondrop.

---

## §2 — When to invoke this protocol

- Every new disposition added to any brand library
- Every rewrite of an existing disposition (we're rewriting all 25 right now)
- Before any spec change that adds a disposition to an audience
- Whenever a transcript surfaces consultant-voice — that's the signal to re-audit the disposition

If you find yourself opening a scaffold script to write or edit a `NamedDisposition`, you are invoking this protocol.

---

## §3 — The 5-line format

A disposition has exactly **5 lines** of free-text content in its `anchor` field (plus the 8-dim `DispositionVector` + the `<stance>_<anchor_key>` label). Each line ≤30 words. Lines separated by `\n\n` so the render engine reads them as discrete clauses.

> ⚠⚠ **L1 IS THE ONE LINE THIS TABLE NO LONGER DESCRIBES — corrected 2026-08-13.**
> The literal rule below ("age, city, occupation, income tier" *in the anchor*) predates the
> gateway reframe and the per-disposition demographic bundles, and following it now is a
> **defect**, for three reasons. (1) The render engine cross-products demographic × disposition ×
> context, so a biography in the anchor **contradicts** the demographic point the agent was
> actually assigned. (2) The anchor is injected as a HARD CONSTRAINT and beats the pack, so one
> biography would be pinned onto every agent of that disposition — the render-10 uniformity
> defect. (3) "income tier" in the anchor walks **straight past** the income redaction at
> `_persona_user_payload` (§2.6), which exists because handing the persona writer income costs
> −4.51 on SimBench.
>
> **The intent survives; only the location moves.** Every persona still gets a concrete age, city,
> occupation and household detail — they live in the disposition's `demographic_bundles`
> (`DemographicPoint.occupation_hint` / `household_hint` / `geography`), which is where the engine
> composes identity. **Income is deliberately withheld from the writer and is the one element of
> the old L1 that must NOT appear anywhere the writer can see it.**
>
> So in this architecture: **L1 = how this person came to the category** (the origin of the
> stance), demographic-free and gender-neutral. Who they are is the bundle's job. See
> `scripts/scaffold_health_wellness.py` (module docstring + the bundle block) and
> `tests/test_persona_biographies.py`, which fails the build if the two layers get mixed.

| Line | Name | Carries | The rule |
|---|---|---|---|
| **L1** | CONTEXT | ⚠ see the correction above — how they came to the category, NOT demographics | demographic-free; the bundle layer owns age / city / occupation / household |
| **L2** | CATEGORY | how this person interacts with the category | purchase frequency, channels, typical price band, one habit |
| **L3** | KNOWLEDGE | what they know — and explicitly what they don't | the upper bound on expertise; **this line closes the door on consultant voice** |
| **L4** | STANCE | what they care about; what they reject; why | the disposition vector translated into a value statement |
| **L5** | ANCHOR-BEHAVIOR | one concrete behavior at SKU+price level | one thing that distinguishes them; sourced from the manual mini-corpus where possible |

### Critical line: L3 is the realism guardrail

Most disposition failures happen because L3 is missing or weak. Without an explicit ceiling, the render engine assumes maximum expertise — and Claude's training-data prior pulls toward the loudest 5% of any cohort (Reddit posters, YouTube reviewers, blog commenters). State what the person does NOT know.

### Critical line: L5 anchors at SKU+price level

NOT generic: *"Cares about quality."*
NOT a sweep: *"Researches everything before buying."*
YES concrete: *"Bought the MuscleBlaze Biozyme Performance Whey 1kg chocolate tub at ₹1,650 on HealthKart in March; uses 32g-protein-per-scoop as the only brand-comparison datum he checks."*

The render engine treats `anchor` as a **HARD CONSTRAINT** (per render-4 update in `agent/render.py`). Concrete SKU + price + behavioral fingerprint → concrete buyer voice. Vague anchor → Claude's generic training prior → consultant voice.

---

## §4 — Worked examples (the patterns you'll keep returning to)

### Example 1 — `enthusiast_specs` rewritten under v2

(Compare against the v1 anchor that produced the consultant voice: *"the published spec sheet itself — driver size in mm, ANC depth in dB, codec list (AAC / aptX / LDAC), multipoint support, mic pickup pattern. Treats any TWS ad that leads with marketing shorthand like 'AI-ENx' or '4 mics' without published measurements as a non-signal regardless of price — will not click. Brand-agnostic; keeps a Notion comparison doc; watches Geekyranjit before any purchase above ₹1,000."*)

> **L1 (CONTEXT)** — 28-year-old male product designer in Bangalore, ₹12-18L household income, lives in a shared 3BHK and replaces earbuds every 18-24 months.
>
> **L2 (CATEGORY)** — Has owned 3-4 TWS earbuds over five years in the ₹2-6K range; shops Amazon and Flipkart during sale events; reads one or two written comparisons before any purchase above ₹3K.
>
> **L3 (KNOWLEDGE)** — Knows the major brand hierarchy (Sony, Bose, Sennheiser, Nothing, Boat, OnePlus) and can tell ANC works or doesn't on a 10-second test; does NOT know what "48 dB ANC" means in measurement terms, does NOT read teardowns, does NOT participate in audio forums.
>
> **L4 (STANCE)** — Cares about build quality, ANC that actually works on a noisy commute, and clear specs over marketing fluff; rejects vague hype phrases like "AI-enhanced sound"; will pay extra for a brand he trusts but won't pay 3× for marginal improvement.
>
> **L5 (ANCHOR-BEHAVIOR)** — Before buying anything above ₹3K, watches one Geekyranjit or Beebom video and skims the top three Amazon reviews — and that's it, no spreadsheets, no Reddit threads.

L3 explicitly closes the door on the Notion-doc voice. This person can still react meaningfully to spec claims ("48 dB? sounds high, but what's normal for this price?") without writing an audio-engineering essay.

### Example 2 — A health & wellness disposition (`switcher_clean_label`)

> **L1 (CONTEXT)** — 31-year-old female mid-level corporate professional in Mumbai, ₹15-22L household income, married no kids, lives in a 2BHK in Powai.
>
> **L2 (CATEGORY)** — Has tried 4-5 supplement brands over the last two years (Plix collagen, OZiva multivitamin, Power Gummies biotin, a Setu sleep blend); buys on HealthKart and Nykaa; spends ₹2-3K/month on supplements.
>
> **L3 (KNOWLEDGE)** — Knows which brands market themselves as "clean" vs "loaded with fillers"; reads the ingredient list before buying; does NOT know what a typical clinical dosage is, does NOT compare lab-test reports, does NOT post about supplements on Insta.
>
> **L4 (STANCE)** — Wants supplements that fit a clean-eating identity (no artificial sweeteners, no maltodextrin filler, plant-based protein); rejects MuscleBlaze-style gym-bro branding as "not for me"; will switch the moment she sees a cleaner-positioned alternative under ₹1,500.
>
> **L5 (ANCHOR-BEHAVIOR)** — Bought OZiva Plant Protein Builder in vanilla last month at ₹1,899 on Nykaa after seeing an Insta ad; mixes with almond milk pre-workout; will probably switch again in 4-6 months if a new brand shows up with better ingredients.

L3 keeps her at the realistic "informed lifestyle buyer" tier — not the "I cross-reference NIH databases" tier that would produce the consultant voice.

---

## §5 — The five accuracy levers (apply to every disposition)

These are the substitutes for the v1 scraped corpus. Apply all five.

### Lever 1 — 5-line format with bounded L3

Already covered above. L3's explicit "does NOT know X" bounds are non-negotiable.

### Lever 2 — Concrete SKU+price anchors in L5

Not "loyal to brand X" → "Bought [specific SKU] at [specific ₹] on [specific channel] in [recent timeframe]; [one concrete habit involving that SKU]."

### Lever 3 — Audience composition discipline (cohort-spanning, not engaged-only)

Every brand library MUST include at least 2 low-involvement personas (the "wife asked me to grab whey", the "lapsed skeptic", the "scrolled past on instinct"). Do NOT compose a library where every disposition is engaged or obsessive — that's the cmf_ad failure mode at the audience layer.

A 6-disposition health_wellness library should distribute roughly:
- 1 obsessive (the spec-reader; e.g., `enthusiast_macros_lifter`)
- 2 high (the engaged-but-not-obsessed; e.g., `aspirant_clean_label`, `loyalist_brand_x`)
- 1-2 medium (the casual category user; e.g., `switcher_brand_y`, `pragmatist_pantry`)
- 1-2 low (the lapsed / skeptic / "this isn't for me"; e.g., `skeptic_marketing`, `purist_natural_food`)

### Lever 4 — Manual mini-corpus per category

For each category, maintain `data/voice_samples/<category>.md` — 20-30 hand-picked verbatim Indian buyer voices from Amazon India, HealthKart, Reddit India, YouTube comments. This is NOT a scrape; it's curation. Pick:
- 5-7 samples from the obsessive cohort (spec-readers, brand-defenders)
- 5-7 from the engaged cohort (regular buyers with opinions)
- 5-7 from the casual cohort (one-line reviews, "it's fine")
- 5-7 from the lapsed/skeptic cohort (negative reviews, "tried for 2 weeks, no result")

These are referenced from the persona render prompt as voice exemplars. Cost: ~1-2 hours per category.

This is ~70% of the grounding effect of the v1 scraped corpus, at 5% of the cost. Do this BEFORE writing dispositions for a new category.

### Lever 5 — Personal review on every disposition

Ishan reviews and edits every disposition before it ships. ~10 min per disposition. Catches:
- 99th-percentile drift (apply check 1)
- Identity slips (e.g., disposition reads as marketer-coded)
- Vector / anchor contradictions (per the cmf_ad `enthusiast_specs` lesson — vector and anchor must pull in the same direction)
- Voice register drift (the wedding-table test)

---

## §6 — Realism gate (the three checks before commit)

### Check 1 — The 80th-percentile audit

For each behavioral claim in L2, L3, L4, L5: **what fraction of this stance's actual buyers do this?** If <20%, it's outlier — strip it or soften it.

Examples for a `health_wellness_nutrition` "aspirant clean-label" stance:
- "Reads ingredient list before buying" → 60-70% do this → ✓ keep
- "Watches a YouTube review before buying" → 40-50% do this → ✓ keep
- "Cross-references lab-test certificates of analysis" → <5% do this → ✗ strip
- "Posts before/after photos to Insta after 30 days" → ~15% do this → soften: "vaguely tracks results but doesn't post about it"

### Check 2 — High-consumer-not-professional rule

The persona can be at the TOP of the consumer-engagement distribution for that stance, but **must not cross into professional/expert territory.** The audio enthusiast is the guy at the office who has opinions about earbuds; he is NOT the guy who designs them. The supplement buyer reads ingredient lists; she is NOT a sports nutritionist.

Crossing the line: any behavior requiring occupational expertise to perform (measurement, certification analysis, technical specification authoring).

### Check 3 — The wedding-table test

Read the 5 lines aloud. **Could you meet this person at a wedding and have them describe themselves this way after a polite glass of wine?**

If the description sounds like an industry analyst's segmentation slide, rewrite it as how the person would describe their own habits. People don't think in segments — they think in routines.

A `loyalist_household_jar` does NOT think *"I am a habitual brand-loyal value-calculator buyer of mass-market instant coffee."* She thinks *"I always buy Bru, it's been on the kitchen shelf since I got married, why would I change."*

---

## §7 — The 30-40 minute disposition-writing flow

For each new or rewritten disposition:

| # | Step | Time | Output |
|---|---|---|---|
| 1 | Define stance + anchor key + one-sentence hypothesis | 3 min | `<stance>_<anchor_key>` label + "this person Xs Y because Z" |
| 2 | Reference manual mini-corpus (`data/voice_samples/<category>.md`); skim 5-10 relevant voice samples | 5 min | Felt sense of the voice |
| 3 | Map to 8-enum DispositionVector (use existing enums in `agent/vectors.py`) | 5 min | Vector populated |
| 4 | Draft 5 lines under the format (§3) | 12 min | Draft anchor |
| 5 | Apply 3 realism-gate checks (§6) | 5 min | Revised anchor |
| 6 | Ishan reviews + edits | 10 min | Final disposition |

Total: ~40 min per disposition. For a 6-disposition library: ~4 hours of focused work.

---

## §8 — Vector + anchor coherence (the cmf_ad lesson)

The `target_id` flipping problem on the original `enthusiast_specs` (sessions 5 + 6 of handoff history) was caused by vector and anchor pulling opposite directions:

- Vector had `price_orientation: value_calculator` + `decision_driver: function`
- Anchor said "obsessive spec-reader, brand-agnostic, watches Geekyranjit"

A value-calculator + functional buyer + obsessive spec-reader is internally contradictory — value-calculators look for utility, but obsessive spec-readers chase the best regardless of price. The model can't render a coherent persona; the agent flips behavior across runs.

**Rule:** Before saving a disposition, mentally simulate the persona reacting to a typical test ad in the category. If you can imagine two opposite reactions from the same persona depending on which dimension dominates, the vector and anchor are in conflict — rewrite one.

---

## §9 — Output artifact (where dispositions live)

For each brand library:

- `scripts/scaffold_<brand>.py` — the source of truth. Holds the `NamedDisposition` Python objects.
- `runs/<account>/<brand>/entities/library.json` — generated by running the scaffold. This is what the render engine reads.
- `data/voice_samples/<category>.md` — the manual mini-corpus that informs every disposition in that category.

When a disposition is rewritten:
- Edit `scripts/scaffold_<brand>.py`
- Re-run the scaffold to regenerate `library.json`
- The render cache invalidates for that disposition (one extra ~$0.02 render per affected agent on first run after — `persona_core_hash` includes the anchor)

---

## §10 — Migration from v1 dispositions

All 19 existing dispositions across `boat_audio`, `cadbury_chocolate`, `bru_coffee` were written under v1 protocol and exhibit consultant-voice risk at varying severity. **All are being wiped and rewritten under v2.**

Order of rewrite:
1. Build `health_wellness_nutrition` dispositions first (for first design partner — Week 1)
2. Rewrite `personal_audio` dispositions (most-validated category; useful as cmf-comparison baseline — Week 1)
3. Rewrite `cadbury_chocolate` + `bru_coffee` (only when needed for incoming design partner — Week 2+)

When rewriting:
- **Preserve the `<stance>_<anchor_key>` label** if it still fits — this keeps audience spec disposition_labels list stable
- **Preserve the 8-enum DispositionVector** unless the new anchor genuinely warrants a vector change
- **Rewrite the anchor entirely** as 5-line format

---

## §11 — Common failure modes (carried from v1 + v2 additions)

| Symptom in transcripts | Likely root cause | Fix |
|---|---|---|
| Agents talk like reviewers/analysts | L3 KNOWLEDGE line missing or weak | Add explicit "does NOT know X" bounds |
| Agents reference brands not in the artifact pack | L1-L5 mention specific competitor brand not in pack | Strip brand mentions from disposition; let pack provide vocabulary |
| Verbatim quotes all from one disposition | Other dispositions are too generic | Strengthen L4 STANCE — what they care about / reject |
| Agents disagree with the persona core | L4 STANCE contradicts `brand_stance` field | Re-check stance verb against vector |
| Identical reactions across personas | All 5 lines are interchangeable | Re-apply Check 3 (wedding test) |
| Disposition flips within/outside target across runs | Vector / anchor pull opposite ways | Apply §8 coherence check; rewrite one |
| Persona reads as marketer-coded, not buyer-coded | Anchor describes behaviors a marketer would note about a buyer | Rewrite anchor as how the buyer would describe themselves |
| Hinglish samples in manual mini-corpus get standardized in render output | Render prompt not preserving code-switched voice | Add explicit "preserve Hinglish verbatim" directive when adding manual-corpus voice samples to render context |

---

## §12 — Disposition naming convention

Format: `<stance>_<anchor_key>`, lowercase snake_case. Stance vocabulary (9 words):

| Stance | When | Examples |
|---|---|---|
| `loyalist` | repeat buyer, brand devotion | `loyalist_airdopes`, `loyalist_dairymilk` |
| `switcher` | actively left one brand for another | `switcher_nescafe`, `switcher_clean_label` |
| `upgrader` | moved up a price/quality tier | `upgrader_premium`, `upgrader_bru_gold` |
| `aspirant` | wants to upgrade but hasn't | `aspirant_airpods` |
| `skeptic` | distrusts brand/category claims | `skeptic_warranty`, `skeptic_health_dark` |
| `purist` | committed to a non-brand alternative | `purist_wired`, `purist_filter` |
| `enthusiast` | high-involvement hobbyist | `enthusiast_specs`, `enthusiast_third_wave` |
| `pragmatist` | low-involvement, function-only | `pragmatist_urgent_replacement`, `pragmatist_pantry` |
| `gifter` | buys for others, occasion-driven | `gifter_festive`, `gifter_silk_dating` |

Anchor key: 1-3 lowercase snake_case tokens describing the *object* of the stance (SKU, sub-category, lifestyle, occasion). Brand name implicit (library is brand-scoped at `runs/<account>/<brand_profile>/`).

No code validation enforces this — convention is documentation-only through v1 launch.

---

## Changelog

- **v2 — 2026-05-26:** rewrite for v1 launch path. Replaces v1's per-disposition corpus scrape with: 5-line format + bounded L3 + concrete SKU anchors + audience composition discipline + manual mini-corpus per category + personal review. 30-40 min per disposition instead of 3-4 hours. Modal-behaviors library moves to ROADMAP P0.1.
- **v1 — 2026-05-18:** initial protocol authored after cmf_ad run surfaced the 99th-percentile voice failure. Per-disposition corpus scrape (~3-4 hr each). Retired with v2.
