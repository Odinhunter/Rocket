# Disposition Authoring Protocol — v1 (SUPERSEDED)

> **⚠️ SUPERSEDED 2026-05-26 by `docs/disposition_protocol_v2.md`.**
> v1 (this doc) assumed per-disposition corpus scrape (~3-4 hr each, 18-24 hr per category library). v2 ships disciplined hand-mapping (~30-40 min each, 3-4 hr per category) for the v1 launch path. Modal-behaviors library is now ROADMAP P0.1 — to be picked up after first design-partner reaction.
> **Use v2 protocol for all current disposition work.** This v1 doc is preserved as historical reference and as the protocol we'll return to when/if the scraped-corpus investment ships.

**Status:** v1 · 2026-05-18 · RETIRED 2026-05-26
**Owner:** team-internal, applied every time a new disposition is added to any brand library.
**Why this exists:** the first pass of dispositions produced agents who talk like product reviewers, not buyers — the `enthusiast_specs` agent in the cmf_ad run wrote "48 dB measured how, at what frequency, under what test conditions, against what standard" because the disposition anchor said the person "keeps a Notion comparison doc tracking ANC depth in dB." That's a real consumer behavior — but it's the 99.9th-percentile behavior. The render engine, given an extreme anchor, faithfully produced an extreme voice. The protocol below stops that at the source: dispositions describe the **80th-percentile** of a stance, not the 99th.

---

## §1 — The failure mode this protocol prevents

Dispositions can fail in two opposite directions:

1. **Too generic** — every "loyalist" sounds the same; no specific behavior; agents produce vague reactions. (We solved this in v1 with anchors.)
2. **Too extreme** — the anchor specifies an outlier behavior (Notion doc, frequency-response measurements, /r/headphones moderator); agents talk like industry insiders, not consumers. **This is the current failure.**

The protocol's whole job is to push every disposition into the realistic-but-distinctive middle: the **top 20% of buyers for that stance, not the top 0.1%.** An audio enthusiast knows the brand hierarchy, can tell good ANC from bad, watches a YouTube review before buying — and *cannot* read a frequency-response curve, *does not* keep spreadsheets, *has never* heard of Topping or Moondrop.

---

## §2 — When to invoke this protocol

- Every time a new disposition is added to a brand library
- Every time an existing disposition is rewritten (e.g., after a `target_id` flipping investigation)
- Before any spec change that adds a disposition to an audience
- During quarterly library audits

If you find yourself opening `scaffold_<brand>.py` to add a `NamedDisposition` entry, you are invoking this protocol. There is no shortcut path.

---

## §3 — The 5-line format

A disposition has exactly **5 lines** of free-text content (plus the 8-dim vector + the stance/anchor-key label). Each line ≤30 words. Each behavioral claim traces to ≥3 corpus sources (see §4).

| Line | Name | What it carries | Bound |
|---|---|---|---|
| **L1** | CONTEXT | demographics + life situation in one sentence | age, city, occupation, income tier, one household detail |
| **L2** | CATEGORY | how this person interacts with the category | purchase frequency, channels, typical price band, one habit |
| **L3** | KNOWLEDGE | what they know — and explicitly what they don't | the upper bound on expertise; this is the 80th-percentile ceiling |
| **L4** | STANCE | what they care about; what they reject; why | the disposition vector translated into a value statement |
| **L5** | ANCHOR-BEHAVIOR | one concrete behavior, sourced from modal corpus | one thing that distinguishes them; NOT a sweep |

**Critical: L3 is the realism guardrail.** Most failures happen because L3 is missing or weak. Without an explicit ceiling, the render engine assumes maximum expertise. State what the person does NOT know.

### Worked example — `enthusiast_specs` rewritten under this protocol

(Compare against the current version's anchor: *"the published spec sheet itself — driver size in mm, ANC depth in dB, codec list... keeps a Notion comparison doc; watches Geekyranjit before any purchase above ₹1,000."*)

**L1 (CONTEXT):** 28-year-old male product designer in Bangalore, ₹12-18L household income, lives in a shared 3BHK and replaces earbuds every 18-24 months.

**L2 (CATEGORY):** Has owned 3-4 TWS earbuds over five years in the ₹2-6K range; shops Amazon and Flipkart during sale events; reads one or two written comparisons before any purchase above ₹3K.

**L3 (KNOWLEDGE):** Knows the major brand hierarchy (Sony, Bose, Sennheiser, Nothing, Boat, OnePlus) and can tell ANC works or doesn't on a 10-second test; does NOT know what "48 dB ANC" means in measurement terms, does NOT read teardowns, does NOT participate in audio forums.

**L4 (STANCE):** Cares about build quality, ANC that actually works on a noisy commute, and clear specs over marketing fluff; rejects vague hype phrases like "AI-enhanced sound"; will pay extra for a brand he trusts but won't pay 3× for marginal improvement.

**L5 (ANCHOR-BEHAVIOR):** Before buying anything above ₹3K, watches one Geekyranjit or Beebom video and skims the top three Amazon reviews — and *that's it*, no spreadsheets, no Reddit threads.

Each line is concrete, demographically grounded, and **bounded** — L3 explicitly closes the door on the Notion-doc voice. This person can still react meaningfully to spec claims ("48 dB? sounds high, but what's normal for this price?") without talking like an audio engineer.

---

## §4 — Sourcing standard (the "actual data, not random Reddit" rule)

Each disposition must be backed by a corpus of **≥30 data points** distributed across **≥4 source types**, with no single source contributing >30% of the corpus.

### Source types

| Type | Minimum N | Examples |
|---|---|---|
| **Industry / market research** | 5 | Nielsen, Statista, Mintel, Kantar, IMRB-Kantar India BAV, IDC, Counterpoint, Forrester, eMarketer, Mordor Intelligence — paid summaries acceptable, free abstracts often sufficient |
| **Trade press / category journalism** | 5 | Mint, ET Brand Equity, Campaign India, Storyboard18, AdAge, Marketing Week, Best Media Info, exchange4media |
| **Social / forum** | 10 | Reddit (≥3 different subreddits), Quora, YouTube comments under ≥3 different category reviews, Twitter/X threads. NEVER one subreddit only. |
| **Brand / marketer commentary** | 5 | LinkedIn posts from category brand managers, podcast transcripts (Ana Mascarenhas's *Brand Building*, Ranjan Roy's *Margins*), published interviews, agency case studies |

### Triangulation rule

A behavior counts as **modal** (eligible for inclusion in the 5-line disposition) only if it appears in **≥3 sources across ≥2 source types.** A behavior that shows up in 5 Reddit threads but nowhere else is suspect — Reddit over-represents the 99th-percentile. A behavior that shows up in one Nielsen report + one trade article + one forum thread is solid.

### Outlier suppression

Behaviors that appear in **<20% of corpus** are excluded — even if they're vivid. The Notion-doc behavior would fail this test: it appears in maybe one out of 30 sources. Vivid ≠ representative.

### How to gather the corpus (practical)

Dispatch a Claude Code `general-purpose` sub-agent with this exact brief:

> Find ≥30 data points about [`stance`] [`anchor`] consumers in [category] in India (or relevant geography), distributed across:
> - ≥5 industry/market-research reports
> - ≥5 trade-press articles
> - ≥10 social/forum threads from ≥3 different subreddits or forums
> - ≥5 brand-side commentary pieces (LinkedIn, podcasts, marketer interviews)
>
> For each: source URL, source type, 1-line attestation of the consumer behavior observed.
> Then rank the behaviors by attestation count across source types.
> Return: (a) the full corpus with sources, (b) ranked list of 5-7 modal behaviors with attestation counts, (c) explicit flag for any behavior that appears in only one source type (these are NOT modal, do not use).

The corpus output gets saved alongside the disposition (see §7).

---

## §5 — Sequence of steps (time-budgeted)

| # | Step | Time | Output |
|---|---|---|---|
| 1 | Define stance + anchor key + one-sentence hypothesis | 5 min | `<stance>_<anchor_key>` label + "this person Xs Y because Z" |
| 2 | Dispatch corpus-gathering sub-agent (§4) | 2-3 hr (mostly async wait) | corpus.md with ≥30 attested data points |
| 3 | Read corpus, identify 5-7 modal behaviors | 30 min | ranked modal-behaviors list |
| 4 | Draft 5-line disposition (§3) | 15 min | draft disposition |
| 5 | Apply realism gate (§6) | 5 min | revised disposition |
| 6 | Commit disposition + corpus + modal-behaviors (§7) | 5 min | library JSON updated, corpus file saved |

Total: **~3-4 hours per disposition, mostly async.** A new brand library with 6 dispositions: 18-24 hours of effort spread across 2-3 days.

This is real work — not a 15-minute scaffold write. The 30-day MVP plan budgets for hand-mapped dispositions because shortcuts here produce the failure mode this protocol prevents.

---

## §6 — Realism gate (the test before commit)

Three checks, in order:

### Check 1 — The 80th-percentile audit
For each behavioral claim in L2, L3, L4, L5: **what fraction of this stance's actual buyers do this?** If <20%, the claim is outlier — strip it or soften it.

Examples for an "audio enthusiast" stance:
- "Watches a YouTube review before buying above ₹3K" → 50-70% do this → ✓ keep
- "Keeps a Notion doc tracking specs" → <2% do this → ✗ strip
- "Knows the difference between LDAC and aptX" → 15-25% do this → soften: "vaguely aware that codec matters; can't explain why"
- "Has opinions about Sony WH-1000XM5 vs Bose QC Ultra" → 30-50% do this → ✓ keep

### Check 2 — The high-consumer-not-professional rule
The persona can be at the TOP of the consumer-engagement distribution for that stance, but **must not cross into professional/expert territory.** The audio enthusiast is the guy at the office who has opinions about earbuds; he is NOT the guy who designs them, writes about them for a living, or moderates a forum. The food enthusiast cooks well at home; he is not a chef. The fashion enthusiast follows trends; she is not a buyer at Zara HQ.

If you find yourself writing a behavior that requires occupational expertise to perform (measurement, analysis, technical specification authoring), you have crossed the line.

### Check 3 — The wedding-table test
Read the 5 lines aloud. **Could you meet this person at a wedding and have them describe themselves this way after a polite glass of wine?** If the description sounds like an industry analyst's segmentation slide, rewrite it as how the person would describe their own habits. People don't think in segments — they think in routines.

A `loyalist_airdopes` does NOT think "I'm a Boat brand loyalist with a price-orientation toward value-calculation." She thinks "I always buy Boat, they're cheap and they last six months, why would I change."

---

## §7 — Output artifact

Each disposition saves THREE things in `runs/<account>/<brand_profile>/entities/`:

1. **`library.json`** — the standard structure (vector + anchor field). The `anchor` field contains the 5-line disposition as plain text, lines separated by `\n\n`. This is what the render engine reads.

2. **`dispositions/<disposition_label>_corpus.md`** — the full corpus from §4. Source URLs, attestations, source types. Auditable provenance.

3. **`dispositions/<disposition_label>_modal_behaviors.md`** — the ranked list of 5-7 modal behaviors with attestation counts and a one-line note on which made it into the 5-line disposition (and which didn't, with reason).

Why all three? Because in six months, when someone says "why does the `enthusiast_specs` persona say X?", the answer is "because behavior X is attested by 7 of 30 corpus sources across 3 source types — and you can read the corpus to verify." Hand-waved dispositions don't survive a methodology audit. Sourced ones do.

---

## §8 — Migration from v1 dispositions

The 18 dispositions in current libraries (boat_audio, cadbury_chocolate, bru_coffee) were written under the old approach. They are NOT all wrong, but several are too extreme (the `enthusiast_specs` Notion-doc anchor is the worst offender; some others have similar issues).

**Migration order**: rewrite when an audience is being built that includes the disposition, OR when a re-run produces evidently off-character voices. Do not retroactively rewrite all 18 — let need drive priority.

When migrating, **preserve the stance label and the 8-dim vector**. Only the anchor (now 5-line) changes. The render cache will invalidate for that disposition (one extra ~$0.02 render per affected agent on first run after).

---

## §9 — Common failure modes to watch

| Symptom in transcripts | Likely root cause | Fix |
|---|---|---|
| Agents talk like reviewers/analysts | L3 KNOWLEDGE line missing or weak | Add explicit "does NOT know X" bounds |
| Agents reference brands not in the artifact pack | L1-L5 mention specific competitor brand not in pack | Strip brand mentions from disposition; let pack provide vocabulary |
| Verbatim quotes are all from one disposition | Other dispositions are too generic (vector defaults) | Strengthen the L4 STANCE — what they care about / reject |
| Agents disagree with the persona core | L4 STANCE contradicts disposition vector | Re-check stance verb against vector's `brand_stance` field |
| Identical reactions across personas | All 5 lines are interchangeable | Re-apply Check 3 (wedding test) |

---

## Changelog

- **v1 — 2026-05-18:** initial protocol authored after `cmf_ad` run surfaced the 99th-percentile voice failure in `enthusiast_specs`. Worked example uses the rewrite of that disposition.
