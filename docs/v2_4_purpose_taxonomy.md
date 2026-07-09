# v2.4 — The Purpose Layer: an ad-purpose taxonomy + per-purpose criteria

*Letting a brand manager declare an ad's **job**, and grading the ad against the
criteria for **that** job — instead of judging every ad by "would the target buy
this week."*

Status: **DESIGN / proposed** (2026-07-08, research-updated + 5th purpose locked
2026-07-09). Extends `docs/v2_3_decision_layer.md`. Grounded in **two** web-research
sweeps + a manual browse (see §8 for sources + an honesty note on what was and wasn't
machine-verified). Builds *after* v2.3 ships.

**Locked taxonomy — five jobs:** direct-sell · cold-hook · awareness/informer ·
brand-building · retain/win-back. Direct-sell is the default.

---

## 1. The one principle (the spine of the whole feature)

Every serious effectiveness framework converges on the same truth:

> **An ad's job sits on a spectrum from demand GENERATION (build future memory and
> awareness — broad, slow, emotional) to demand CAPTURE (convert intent — targeted,
> fast, rational), with a distinct RETAIN job aimed at existing customers. You must
> measure each against its own job. Judging one job by another's metric is a category
> error.**

This is not our opinion; it is the loudest, most-replicated finding in the field:

- **Avinash Kaushik (See-Think-Do-Care):** segments audiences by *intent*, not
  channel/demographic — "See" = largest audience, no commercial intent; "Think" =
  some intent; "Do" = ready to buy; **"Care" = existing customers.** Applying
  conversion metrics to upper-funnel ("See") audiences is "like judging a fish by its
  ability to climb a tree"; the fix is to match each stage's metric to that stage's
  job. *(kaushik.net, primary)*
- **Binet & Field (IPA, "the long and short of it"):** brand-building (build memory
  structures, months–years, broad future buyers, works through emotion) and sales
  activation (activate memory now, days–weeks, in-market buyers, works through
  offers) "are weak at doing each other's job" and must be measured differently.
  Optimal split **60:40** (2013) → **62:38** (2018) — barely moved in 5 years.
  *(ipa.co.uk + system1group.com, primary)*
- **The 95:5 rule (John Dawes, Ehrenberg-Bass) — the single strongest data point for
  this feature:** at any moment only **~5%** of category buyers are in-market;
  **~95%** cannot buy now. So for most ads seen by most people, "would you buy this
  week" is *structurally the wrong question.* *(marketingscience.info, primary)*
- **System1** operationalizes measure-by-job in a *single pre-test*: a long-term
  **Star Rating** (1.0–5.0; *type/breadth* of emotion → brand growth) and a short-term
  **Spike Rating** (short-term sales, 8–10 weeks post-airing; *intensity* of emotion +
  *speed of brand identification*). Two jobs, two scores, one test. *(system1group.com,
  primary)* — the direct existence-proof that Rocket's approach is legitimate.
- **Ehrenberg-Bass (Byron Sharp / Jenni Romaniuk):** brands grow mainly by
  *penetration* (more buyers, mostly *light* buyers), built through **mental
  availability** — being thought of at **category entry points (CEPs)** — via
  **distinctive brand assets**; **broad reach beats tight targeting.**
  *(marketingscience.info, primary)*

**Rocket today commits precisely the category error the field warns against:** one
ruler — within-target "would_act_within_week." v2.3 sharpens that ruler; v2.4 adds
the *other* rulers, and lets the user pick which one applies.

*(Both independent research sweeps — 35 sources between them — extracted these same
facts from the same authoritative primaries. See §8.)*

---

## 2. Cross-framework map (they are all the same ladder)

| Rocket purpose | Funnel | AIDA | See-Think-Do-Care | Binet & Field | Ehrenberg-Bass | Demand | Meta objective |
|---|---|---|---|---|---|---|---|
| **Awareness / informer** | Awareness | Attention | See | Brand building (cognitive) | Mental availability via CEPs | Generation | Awareness |
| **Brand-building** | Awareness→Consideration | Interest/Desire | See | Brand building (affective) | Mental availability via emotion + distinctive assets | Generation | Awareness / Video views |
| **Cold hook** | Consideration | Attention→Interest | Think | (bridge to activation) | Reach into non-buyers | Gen→Capture edge | Traffic / Engagement |
| **Direct-sell** | Conversion | Action | Do | Sales activation (new buyers) | Physical availability | Capture | Sales / Leads |
| **Retain / win-back** | Loyalty / advocacy | (Satisfaction) | **Care** | Activation of *existing* memory | Retention (light-buyer re-nudge) | Capture (existing) | Engagement / Sales (existing-customer) |

Reading: the five purposes the user locked are the five practitioner-legible rungs of
the one ladder every framework describes — the four acquisition/build rungs **plus**
the "Care"/loyalty rung that targets people who already bought. The split that matters
most among the first four: **awareness/informer and brand-building both live in
demand-generation** and both need a **broad-reach** frame; they differ on **cognitive**
(informer: "know they make X" — comprehension/breadth) vs **affective** (brand-building:
"feel + remember the brand" — emotion/memory/attribution). And the split that defines
the 5th: **retain/win-back is a purchase job like direct-sell, but aimed at
*existing/lapsed* customers, not new prospects** — same "would they act" question, a
different audience.

---

## 3. How the platform layer operationalizes purpose (what the D2C user sees daily)

Every major platform bins its objectives by funnel stage — so Rocket's purpose picker
should *speak this language* (familiar, not academic):

- **Meta** (simplified 11→6 in Jan 2024, "ODAX"): **Awareness** (optimizes reach +
  *estimated ad recall*) · **Traffic** (link clicks / landing-page views) ·
  **Engagement** (feed interactions, messages, video views) · **Leads** (form fills) ·
  **App Promotion** (installs) · **Sales** (purchases). *(facebook.com/business +
  WordStream + Madgicx; ODAX shift via adweek.com.)*
- **Google Ads:** Sales · Leads · Website Traffic · Awareness & Consideration ·
  App. *(support.google.com, primary)*
- **TikTok:** Awareness (Reach) · Consideration (Traffic, Video Views, Community) ·
  Conversion. *(ads.tiktok.com, primary)*
- **LinkedIn:** Brand Awareness · Consideration (Website Visits, Engagement, Video
  Views) · Conversions. *(linkedin.com/help, primary)*

Rocket's five purposes map onto these: Sales→direct-sell, Traffic/Engagement→cold-hook,
Awareness→awareness/informer, brand-building as the strategic layer above, and
retain/win-back via Engagement / Sales run against *existing-customer* (warm/retargeting)
audiences.

---

## 4. The five purposes, fully parametrized (the criteria)

For each purpose we fix six parameters. **These six parameters ARE the design.**

Parameters: **(1) headline metric** · **(2) diagnostic signals** — which reaction
rounds (R1 gut · R2 comprehension · R3 emotion · R4 stickiness · R5 share/mention ·
R6 friction · R7 action) count, and which are ignored · **(3) audience frame** —
narrow/broad/existing · **(4) R7 success direction** · **(5) new probe required** ·
**(6) decision meaning** (how SCALE / ITERATE / RETARGET / REBUILD reads).

### 4.1 DIRECT-SELL  *(default — = v2.3, no change)*
- **Job:** make a *new-prospect* target buy one product now.
- **Real KPI:** ROAS · CPA · conversion rate.
- **Headline:** **within-target action rate** (would_act_within_week among within-target).
- **Signals:** R7 tap_cta/would_act (primary) · R6 friction · R2 offer-comprehension.
- **Audience frame:** **narrow** — the within-target disposition(s).
- **R7 win:** tap_cta / would_act.  **New probe:** none.
- **Decision:** exactly v2.3.  **Build:** ✅ done.

### 4.2 COLD-HOOK  *(top-of-funnel prospecting)*
- **Job:** stop a cold, low-intent scroller and earn a lean-in (curiosity/click/save)
  — **not** an immediate purchase.
- **Real KPI:** hook rate / thumbstop rate (3-sec views ÷ impressions) · hold rate ·
  CTR · CPC. *("Hook rate beats CTR" up-funnel — nine.am; "more than ROAS" — martech.org.)*
- **Headline:** **stop-and-lean-in rate on a COLD audience** = fraction doing anything
  other than scroll_past (linger + seek_info + save + tap) among low-prior-intent
  dispositions. *(95:5 rule is the theory: most reachable people aren't buying today —
  count the stop, not the sale.)*
- **Signals:** R1 gut (arresting?) · R7 linger vs scroll_past · R7 seek_info · R4
  stickiness. **Ignore** would_act.
- **Audience frame:** **broad-cold** — people not currently shopping the category.
- **R7 win:** linger / seek_info / save.  **New probe:** minor thumbstop flag from R1.
- **Decision:** SCALE = hooks broadly + curious · ITERATE = stops but no reason-to-care ·
  RETARGET = hooks wrong crowd · REBUILD = scrolled past.
- **Build:** cheap. **`*_cold_traffic` specs already exist.**

### 4.3 AWARENESS / INFORMER  *(the portfolio ad — the case that started this)*
- **Job:** make people NOTICE and UNDERSTAND — "know the brand / know they make X /
  know the range." Comprehension + breadth, not purchase.
- **Real KPI:** reach · estimated ad-recall lift · aided/unaided awareness · message
  association · share of search.
- **Headline:** **breadth of registration** = how many *distinct disposition types*
  both correctly understood the offer (R2) and would remember it (R4). A breadth read,
  NOT a within-target action rate (undefined for a multi-target ad).
- **Signals:** R2 comprehension · **NEW novelty** ("'I didn't know they made this'?") ·
  R4 stickiness · breadth across dispositions. **Ignore** R7 action.
- **Audience frame:** **broad** — whole category-buyer population. *Breaks the single
  within/outside/ambiguous frame* → deepest build.
- **R7 win:** n/a.  **New probe:** **novelty** + **multi-target breadth aggregation.**
- **Decision:** SCALE = broad clear comprehension + memorable + teaches · ITERATE =
  noticed but message unclear · REBUILD = confusing/forgettable.
- **Build:** dearest — the finale.

### 4.4 BRAND-BUILDING  *(emotional / long-term)*
- **Job:** make people FEEL something and REMEMBER the brand — build memory + affinity,
  not act now.
- **Real KPI:** brand lift · favorability · aided+unaided recall · emotional response
  (**System1 Star Rating 1.0–5.0**) · fame / share of search · (6+ months).
- **Headline:** **resonance × brand-memorability rate** = fraction who both had a
  genuine positive emotional response (R3) and would remember/mention it (R4 + R5),
  aggregated broadly. *(System1: long-term value = TYPE + BREADTH of positive emotion,
  not peak intensity.)*
- **Signals:** R3 emotion (type/breadth) · R4 stickiness · R5 share/mention · **NEW
  brand-attribution / fluency** · distinctive-asset usage. **Ignore** R7 action.
- **Audience frame:** **broad** — reach/penetration, all category buyers.
- **R7 win:** n/a.  **New probe:** **brand-attribution / fluency** ("which brand was
  this for — sure?"). Catches **"loved the ad, forgot the brand"** — a strong-emotion,
  mis-attributed ad *fails*. Most tools miss this; a differentiator for us.
- **Decision:** SCALE = broad positive emotion + correctly branded + memorable ·
  ITERATE = resonant but weak brand linkage · REBUILD = flat / wrong emotion ·
  RETARGET = resonates with a different group than intended.
- **Build:** medium — one probe + broad frame (shares breadth machinery with informer).

### 4.5 RETAIN / WIN-BACK  *(the 5th — existing & lapsed customers)*
- **Job:** re-engage people who **already bought** — reorder, renew, stay, or come back
  — **not** acquire new buyers. Covers reorder/subscription reminders, loyalty offers,
  "we miss you" win-backs, member-only news.
- **Real KPI:** repeat-purchase / reorder rate · subscription retention (churn) ·
  win-back rate · customer lifetime value (CLV) · retargeting conversion among
  existing customers. *(Framework home: funnel Loyalty · See-Think-Do "Care" · Binet
  activation of existing memory.)*
- **Headline:** **re-engagement rate among *existing-customer* dispositions** =
  fraction of the already-bought / lapsed dispositions who would reorder / renew /
  return. Structurally like direct-sell's action rate, but the frame is **existing
  customers, not new prospects.**
- **Signals:** R7 action (reframed as reorder/return intent, primary) · R1 gut
  (does it feel *for-me* as an existing user?) · R6 friction (reorder blockers —
  inertia, a better offer elsewhere, forgot) · R2 comprehension of the reason-to-return.
  R3 emotion matters for loyalty/affinity ads.
- **Audience frame:** **existing / lapsed customers** — a distinct disposition type
  (loyalist · active subscriber · lapsed user). Expressible in the 8-dim vector today
  (`category_relationship` + `brand_stance=loyalist` + `prior_experience_valence`),
  but the library must actually *contain* such dispositions to test against.
- **R7 win:** reorder / renew / return (a "would_act", existing-customer framing).
- **New probe:** none new — reuses R7 (repeat framing) + R6 (reorder friction). The
  real requirement is the **audience frame = existing-customer dispositions**, a
  library/onboarding task, not a new reaction question.
- **Decision:** SCALE = existing customers strongly re-engage · ITERATE = they'd return
  but a fixable barrier (no incentive / unclear it's for them) leaks it · RETARGET =
  it lands better on new prospects than on the lapsed target (wrong audience) · REBUILD
  = existing customers reject the reason to return.
- **Failure it prevents:** judging a reorder/win-back ad by *new-customer acquisition*
  metrics, or running it against a *cold-prospect* panel when its real audience is
  people who already know and bought the brand.
- **Build:** low-medium — metric machinery ≈ direct-sell's (cheap); the real cost is
  ensuring the disposition library carries existing/lapsed-customer dispositions.

---

## 5. The unifying view — six knobs, five presets

Everything in §4 reduces to **six knobs**; each purpose is a **preset** over them:

| Knob | direct-sell | cold-hook | awareness/informer | brand-building | retain/win-back |
|---|---|---|---|---|---|
| Headline metric | within-target action rate | cold stop-and-lean-in rate | breadth of comprehension | resonance × brand-memory | existing-customer re-engagement rate |
| Primary signals | R7 buy, R6 | R1, R7 linger/seek, R4 | R2, novelty, R4 | R3, R4, R5, attribution | R7 reorder, R6, R1 |
| Audience frame | narrow (new) | broad cold | broad category | broad category | existing / lapsed |
| R7 win = | buy | curiosity | (ignored) | (ignored) | reorder / return |
| New probe | — | (thumbstop) | **novelty** | **brand attribution** | — (needs existing-cust. dispositions) |
| Decision basis | action + pain | stop + curiosity | comprehension breadth | emotion + attribution | re-engagement + reorder-friction |

So "design parameters around them" has a clean answer: **a purpose is a
`(headline-metric, signal-weight-profile, audience-frame, required-probes)` preset.**
`resolve_decision` grows one parameter — a "primary metric" — and the rest is data.
Do **not** pre-abstract all five now; build the preset when each purpose actually
arrives (per §7).

Note the tidy symmetry: **direct-sell and retain/win-back are the same knobs except
the audience frame** (new prospects vs existing customers) — which is exactly why
retain is cheap to add on top of the v2.3 machinery.

---

## 6. What genuinely new signal we must capture (the honest gap list)

Most of what each purpose needs, **we already collect** (R1–R7 span the space). The
true *new* captures are only two, both small additive self-report probes:

1. **Novelty / news probe** (awareness/informer) — "does this update a belief — 'I
   didn't know they made this'?" The single most-important missing signal — the core
   outcome of the ad type that motivated this feature.
2. **Brand-attribution / fluency probe** (brand-building) — "which brand was this for
   — sure?" Catches "loved the ad, forgot the brand."

Plus two **structural** pieces (not probes): (a) the **multi-target breadth read** —
awareness + brand-building are evaluated across a *broad* audience, so within-target
action rate is undefined and must become a breadth aggregation; (b) **existing-customer
dispositions** in the library — retain/win-back needs a panel of people who already
bought, which is a library/onboarding task, not an engine change.

---

## 7. Build boundary (mirrors v2.3's no-shortcut gate)

Purpose splits on the **same calibration boundary** as v2.3:

**Ship now (no new calibration):**
- the **purpose input field** (in `CreativeInputs`, defaults to direct-sell);
- the **declared-vs-apparent-purpose mismatch flag** (extend the target_id vision call
  to infer the ad's *apparent* job; mirror the demographic-mismatch guard; fires even
  when the field is left default — the common case);
- **descriptive** per-purpose metrics that reuse existing signals, shown as reads.

**Gated — one reference/anchor run *per purpose* before its graded decision** (exactly
v2.3's SCALE gate, one level out): zero observations of what a "strong"
cold-hook / informer / brand / retain ad looks like in our engine. Capturing the field
now accumulates the **purpose-labeled runs** later calibration needs.

**Build order (cheapest → dearest):**
1. **direct-sell** — ✅ done (v2.3).
2. **cold-hook** — cheapest: new headline over existing signals + the cold frame
   (`*_cold_traffic` specs exist).
3. **retain/win-back** — metric ≈ direct-sell (cheap); needs existing-customer
   dispositions in the library (data/onboarding work).
4. **brand-building** — + one probe (brand attribution) + broad frame.
5. **awareness/informer** — + novelty probe + the multi-target breadth read. Finale.

---

## 8. Sources & honesty note

**Honesty note.** Two automated deep-research sweeps (2026-07-08 and 2026-07-09) each
completed their search + claim-extraction phases (sweep 2: **22 sources → 102
claims**) but **both hit an account session limit during verification** — every
verified claim returned `0-0 (3 abstain)` (verifier agents never ran), which the
harness *defaulted* to "killed." That is an infrastructure false-negative, **not** a
refutation. Confidence rests on three legs: (1) claims come from **authoritative
primaries** (Kaushik, IPA, System1, the Ehrenberg-Bass Institute, and Google/TikTok/
LinkedIn's *own* help docs); (2) **two independent sweeps extracted the same facts** —
cross-run triangulation; (3) a **manual browse** (2026-07-09) confirmed Meta's six
objectives and the Sharp-vs-Binet disagreement. A clean machine re-verify can run
after the limit resets — worth doing before we hard-code any *numeric* threshold, but
the *frameworks* here are canonical and not in doubt.

**Primary sources:** kaushik.net (See-Think-Do-Care) · ipa.co.uk (60:40→62:38) ·
system1group.com (Star/Spike, methodology, metrics) · marketingscience.info /
Ehrenberg-Bass (95:5 rule, mental/physical availability, CEPs, penetration) ·
support.google.com · ads.tiktok.com · linkedin.com/help · facebook.com/business (Meta
6 objectives) · Kantar & Zappi (copy-testing). **Secondary/blog:** adweek.com (Meta
ODAX) · nine.am (hook rate > CTR) · motionapp.com (creative metrics) · martech.org
("more than ROAS") · WordStream / Madgicx (Meta objectives) · Wikipedia (AIDA) ·
ruleranalytics.com (demand gen vs capture) · adamigo.ai (Meta funnel benchmarks).

**Copy-testing precedent:** Kantar, Zappi, and System1 all vary evaluation criteria
*by ad objective* — Rocket letting the user declare a job and grading against it is
standard pre-testing practice, not a novelty.

---

## 9. Where practitioners genuinely disagree (flagged, per the brief)

- **Byron Sharp vs Binet & Field — the 60:40 rule.** Sharp (Ehrenberg-Bass) publicly
  dismisses the 60:40 split as built on "unsound awards data" and says to drop
  budget-ratio quotas for *always-on broad reach*; Binet/Field defenders (e.g. James
  Hurman) counter that Sharp applies inconsistent standards.
  - **What it means for us:** treat the *specific 60:40 number* as contested, but note
    **both camps agree** on what Rocket relies on: build demand (don't only capture
    it), measure each job by its own metric, and demand-gen wants broad reach. **We use
    no 60:40 number anywhere.**
- **Retention as a *growth* lever is itself contested.** Ehrenberg-Bass argues growth
  comes from *penetration* (new/light buyers), not loyalty — so some would down-weight
  a retention *strategy*. But retention/win-back *ads* unquestionably exist as a job
  D2C brands run; Rocket judges the *ad against its stated job*, staying out of the
  strategy debate. The retain purpose grades "does this re-engage existing customers,"
  not "is retention the right strategy."

---

## 10. Open questions for the build session
- Confirm the two new probes (novelty, brand-attribution) survive a live reaction test
  without contaminating the blind/authentic reaction (they are *self*-report → lower
  risk than purpose-conditioning the persona).
- Decide whether the multi-target breadth read is its own synthesis module or a mode of
  the existing L2/L3 aggregation.
- For retain/win-back: confirm the disposition library can express existing/lapsed
  customers cleanly, and whether onboarding should author a standard "loyalist +
  lapsed" pair per brand.
- Re-run the machine verification post-reset before any numeric threshold is set (§7 gate).
```
