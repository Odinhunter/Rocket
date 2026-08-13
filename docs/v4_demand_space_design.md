# The Demand Space Architecture

**A design book for the v4 pivot — how the audience stops being authored and starts being composed.**

Status: proposed, nothing built. Written 2026-08-14.
Supersedes the per-customer disposition-authoring model (`dispositions_hand_mapped`).

---

## 0. The one-paragraph version

Today we hand-author an audience for each product type, so anything a brand launches
outside that narrow slice falls outside the instrument — and the instrument answers
anyway, confidently, with the wrong people in the room. The fix is to invert the
direction of the work: instead of building a narrow audience per customer on demand,
build a **broad map of a market's demand once, ahead of time**, and let each product
select a slice of it. Brands stop commissioning audiences and start querying one that
already exists. The onboarding becomes a two-minute confirmation instead of a two-week
authoring project, and a new product launch becomes a lookup instead of a phone call.

---

## 1. What is actually broken

### 1.1 The evidence

The SuperYou PB Bar run, 2026-08-13, is the whole case in one artifact.

The classifier read the creative and described the buyer correctly, before the panel ran:

> *"Young urban Indians who want a tasty, snackable protein hit without the gym-bro
> supplement baggage — protein-curious snackers who like chocolate/wafer formats but
> respond to 'clean' cues like no added sugar, atta & jowar, no palm oil."*

That is the right person. The library then had nobody like them. Every disposition in it
is a **supplement-buyer identity** — the macros lifter, the clean-label wellness buyer,
the results-chasing switcher, the lapsed skeptic, the food-first purist. The closest
match, `pragmatist_protein_snacker`, is authored as someone *already buying protein bars*
at ₹625 for a five-pack.

The category pack contains twenty brands and **zero confectionery**. No Dairy Milk, no
Snickers, no Britannia. Every price point is a tub between ₹1,250 and ₹4,800. There is no
₹30 chocolate bar anywhere in these personas' world, so the trade-up decision the product
actually competes for — *this instead of that* — is literally unrepresentable.

All four situations tested were feed-browsing: commute scroll, weekend browse, late-night
wind-down, pre-purchase research. Ninety-nine of a hundred agents scrolled past. The
`pragmatist_protein_snacker` biography names a 4pm desk crash as her moment; the panel
never once put her there.

And then the failure that matters most: `no_match_note` came back **empty**. The system
had a field for "I don't have this buyer" and left it blank, forced two supplement
dispositions into "within," and returned **trust: HIGH, confidence 84**.

### 1.2 The root cause, stated plainly

**Audiences are authored narrow and per product type, so the default state of anything
new is "outside."**

That is not a gap you can close by authoring more. It is the direction of the whole
system. Every new product a brand launches triggers days of hand-authoring, which means
telling a paying customer to wait while we invent their buyer. That is a consulting
practice with a software interface, and it does not scale past a handful of accounts.

### 1.3 The failure mode is worse than the gap

A missing audience is a scheduling problem. A **confident answer built on the wrong
audience** is a trust problem, and it is the one we currently have. The customer ships on
our read, and finds out later that nobody in the panel was their buyer.

---

## 2. The principle

We cannot guarantee that every buyer for every product is covered. Nobody can, and
promising it would be the same overclaim the funded competitors make.

There is a stronger guarantee available underneath it:

> **The instrument never answers outside its coverage without saying so.**

Coverage will always have holes. **Detection of a hole can be made mechanical.** That
single property is what turns an unbounded liability into a bounded, manageable
conversation — and it is the same honesty-as-behaviour position that is already the only
thing separating us from a crowded field.

---

## 3. The inversion

### 3.1 Build the market, not the brand

The key observation: **demand spaces are not brand-specific.**

"The 4pm desk slump" is the same occasion whether the brand is The Whole Truth, Yogabar,
SuperYou or Britannia. The same population is deciding, in the same moment, against the
same competitive set. The occasion belongs to the *market*, not to whoever is selling
into it.

So the durable asset is not "The Whole Truth's audience." It is **"Indian urban snacking
demand"** — and every brand playing in that market queries the same underlying map.

### 3.2 What this changes economically

| | authored per customer | pre-built per market |
|---|---|---|
| cost shape | linear — every customer costs days | fixed per market, then free |
| new product | days of authoring, a phone call | a lookup, same day |
| improvement | none; each library is a dead end | every brand sharpens the shared map |
| business type | consulting with a UI | product |

This is the difference between a services business and a software business, and it is
decided entirely by *when* the work happens — ahead of time at market level, or on
demand at customer level.

### 3.3 "Demand space" is not an invented term

BCG and Kantar sell demand-space studies as consulting engagements costing lakhs. We are
not introducing an exotic concept to the market; we are **operationalising a framework
brands already pay for and already understand.** That is credibility with a CMO, and it
is cover for charging properly at onboarding.

---

## 4. The architecture

Four layers. Only one of them is ever rebuilt for a new market, and none of them is
rebuilt for a new product.

### Layer 1 — WHO (universal, built once)

Real consumer biographies: age, gender, income, city, occupation, household, life stage.
Category-independent. A person does not become a different person when the product
changes.

Session 38 already built 62 of these as `demographic_bundles`, with 25 distinct
biographies under the shipped brief. That work is the seed of this layer and carries over
intact.

**Rebuilt when:** a new geography (India-urban → India tier-3, or a new country).
**Never rebuilt for:** a new category, a new brand, or a new product.

### Layer 2 — WHEN AND WHY (per market, built once at market launch)

The demand spaces themselves. Each is an *occasion*, not a person:

- the 4pm desk slump
- post-workout recovery
- the late-night craving
- breakfast on the run
- the kids' lunchbox
- the guilt-free weekend treat
- the health-goal daily routine
- the deficiency/medical trigger
- gifting

Each carries four things:

1. **the trigger** — what starts the moment
2. **the competitive set** — what actually gets bought, *including "nothing"*
3. **the deciding criteria** — speed, taste, price, health, convenience, guilt
4. **the channel** — quick commerce, kirana, Amazon, gym shop, pharmacy

Indian snacking probably has twelve to fifteen of these, not five hundred. That is a
tractable, finite, one-time job.

**This is the layer that does not exist today, and its absence is the entire SuperYou
failure.**

### Layer 3 — HOW THEY RELATE (universal grammar)

The nine stances already in use — loyalist, switcher, upgrader, aspirant, skeptic,
purist, enthusiast, pragmatist, gifter — are category-independent. A skeptic is a skeptic
in protein, in coffee, in skincare. What changes is *what they are skeptical of*, and
that comes from the demand space, not from the stance.

### Layer 4 — THE WORLD THEY LIVE IN (per market)

Brands, prices, channels, communities, cultural narratives. This is what the artifact
pack already is. One change, and it is the single most important line in this document:

> **Scope the pack to the DEMAND SPACE, not to the product category.**

A pack scoped to "protein supplements" can never contain a chocolate bar. A pack scoped
to "4pm snacking in urban India" contains chocolate automatically, at its real ₹30 price
point, alongside biscuits, samosas, coffee and skipping-it-entirely. The trade-up
comparison becomes thinkable because the thing being traded up *from* is finally in the
room.

### 4.1 A persona becomes a composition

```
persona  =  biography (L1)  ×  demand space (L2)  ×  stance (L3)  ×  world (L4)
```

Not a hand-written document. A composition drawn from four pre-built layers. That is what
makes a new product free.

---

## 5. The experience — and why ours can be *simpler* than Lumina's

### 5.1 Their flexibility is their defect

Lumina asks the user to type an audience description into a free-text field. That field is
exactly why the test run we examined produced nonsense: the field was filled with
*"Informing the audience of the range of TWT products"* — a description of the ad, not an
audience — and the system built 105 personas out of it and reported findings "among
Informing the audience of the range of T…".

**Their apparent flexibility is a burden they push onto the user, and then a failure they
bill for.**

### 5.2 So we delete the field

We already read the creative and infer the buyer correctly. So the brand should not be
asked to describe an audience at all. The flow:

1. **Upload the creative.**
2. **We infer** — category, demand space, competitive set, occasion, audience.
3. **One confirmation, written as consequences.**
4. **Run.**

The confirmation is the entire interface, and its wording is load-bearing:

> *"We'll test this as a **4pm snacking decision**, against **chocolate bars and
> biscuits**, with people who currently buy those. Change anything?"*

A marketer can check that in five seconds and knows immediately if it is wrong. Compare
the version that fails:

> ~~*"Demand space: guilt-free indulgence. Stance mix: pragmatist/aspirant."*~~

Nobody can validate that, so nobody will, and the confirmation becomes a rubber stamp.
**Confirmation screens must show consequences, never classifications.**

### 5.3 Inference proposes; declaration disposes

This is a constitutional rule, not a UX preference.

Today the marketer *declares* the audience, and that declaration is the sampling frame —
it is what `marketer_led` means and it is load-bearing throughout the engine. If
inference silently replaces declaration, then **an inference error becomes the sampling
frame**, and we have rebuilt Lumina's failure with better manners.

So: the system **proposes**, the marketer **disposes**. The declared frame remains the
authority. The inference is a very good default, offered for one-tap acceptance.

Our evidence that inference works is currently **one run**. It got that one right. That
is encouraging, not settled — especially since the same classifier left `no_match_note`
empty on the same run.

### 5.4 A rejected inference is data, not just UX

Every time a marketer overrides the proposal, that is a labelled example of the
classifier being wrong, generated for free by normal product use. Log it. Over a few
hundred runs it becomes the first real error rate we have ever had for any part of this
instrument — measured against human judgement, at zero cost, without a study.

---

## 6. Onboarding: confirmation, not creation

Because the market map is pre-built, onboarding stops being a project.

1. The brand tells us who they are — or we read it from a URL.
2. **We show them the demand spaces we already have for their market**, and which ones we
   think they play in.
3. They confirm and adjust. Two minutes.
4. Optionally, they connect data — reviews, listings, CRM, support transcripts — which
   sharpens their slice.

Step 2 inverts the emotional shape of the sale. Instead of *"wait while we build your
audience,"* it is *"here is a map of your category's demand — tell us where you sit."*
Being shown a demand map of your own market is itself a consulting deliverable. It is a
reason to say yes, not a cost to bear before value appears.

The high-ticket commitment the brand makes buys **depth and their own data folded in**,
not their basic right to be covered.

---

## 7. How market maps get built

The human stays in the loop. Their job changes from **writing** to **approving**, and it
happens at market level once, not per customer.

**Pipeline:** mine → cluster into occasions → extract competitive sets and stances →
human edits and signs off → automated admission gates.

**Sources:**

| source | what it yields |
|---|---|
| marketplace reviews (Amazon, Blinkit, Zepto, Flipkart, Nykaa) | occasions, substitutions, real vocabulary |
| product Q&A | objections in raw form |
| Reddit, YouTube and Instagram comments | non-buyers, skeptics, cultural narratives |
| search and category browse data | how demand is actually expressed |
| the brand's own reviews, CRM, support logs, return reasons | their real buyers, at onboarding |

### 7.1 The trap that would quietly ruin this

**Reviews are written by people who bought.** Build a panel from reviews alone and you get
a room full of enthusiasts — and you lose precisely the people who keep the instrument
honest: the skeptic, the purist, the one who returned it, the one who was never going to
buy. Their refusals are what stop the panel liking everything.

So the mining has to deliberately target **non-buyers and ceilings**: one-star reviews,
unanswered questions, "why I stopped" threads, comment-section dismissals. Miss this and
every floor goes soft — the honest 0% readings become meaningless 40%s, and the instrument
becomes a flattery machine.

### 7.2 It also satisfies a rule we already hold

Our own standing bound is **condition on experience, not on conclusions** — a stated
position cannot be moved by an ad, but a lived experience can. Mined material is naturally
experiential ("I binned the tub after two months"). Invented material drifts toward stated
positions. Grounding in real text makes the rule easier to keep, not harder.

---

## 8. Quality: three mechanisms, none of them "trust us"

### 8.1 Coverage refusal — the safety net

Before any money is spent, one check: **does the composed panel actually contain the buyer
the classifier just described?** If not, say so at the review screen, pre-spend.

We already own the right mechanism. `_trust_ceiling_warning` exists for exactly this shape
of problem — the panel cannot support a confident verdict, so disclose it up front while
it is still free to fix. A coverage gap is a second failure mode feeding the same choke
point.

**On the SuperYou run, "trust: HIGH" should have been structurally impossible.**

### 8.2 Admission gates — already built

No composed library ships without passing the checks that already exist and cost nothing:

- **`gate_test.py`** — does it still tell one ad from another?
- **`check_panel_diversity.py`** — are these actually different people?
- the realism bar from the authoring protocol

⚠ These gates must be **re-baselined**. Every existing baseline was produced by
hand-authored libraries; a composed library needs its own baseline before "still
discriminates" means anything.

### 8.3 Provenance — grounding you can point at

Every stance traces to its source material: *this buyer type is built from 340 reviews,
82 unanswered questions and 14 discussion threads.*

That is four things at once — an internal quality signal, an input to confidence (thin
evidence should lower it), a sales asset, and an honest claim that does not require
confessing anything.

**And here is the discipline that keeps it honest:** provenance is a **grounding** claim,
not an **accuracy** claim. "Built from 4,300 real reviews" is true and checkable. "So it
predicts the market" does not follow, and that step is exactly what Lumina takes with
different units. Volume of source material does not touch the validation debt. The design
book says both halves or it is doing the thing it criticises.

---

## 9. Why this beats the competition structurally

Lumina generates personas per run from a free-text string. That is not a missing feature
list; it is a set of things their architecture **cannot** do:

- **They cannot run the same panel twice.** No two reports are comparable, so there is no
  before-and-after, no tracking a creative's improvement, no longitudinal anything.
- **Nothing accumulates.** Run a thousand simulations and the thousand-and-first is no
  better than the first.
- **There is no boundary to refuse at**, because every string is a valid audience.

A demand-space panel is **stable**. Same brand, same audience, every time — so "this ad
scored against the identical hundred people your last one faced" is a sentence we can say
and they cannot. A thermometer has to be the same thermometer twice.

The trade, stated honestly: **they are instant always and grounded never; we are instant
after day one and grounded always.** Day one is the onboarding, and it now takes minutes.

---

## 10. Decisions this design deliberately preserves

A pivot is not a licence to relitigate settled calls. These stand, unchanged:

- **The four-question audience form remains the demographic axis.** Demographics are
  verified to change the panel; geography composes the targeting sentence but does not
  filter it. Demand-space selection sits *beside* this, not instead of it.
- **`marketer_led` is not a form field**, and inference does not become one by the back
  door. Declaration remains the frame.
- **No caveats render inline on the customer read.** Coverage refusal happens at the
  *review screen, pre-spend* — it is an authoring/operator gate, not a hedge stapled to a
  finished deliverable.
- **The buy-intent headline leads, uncaveated.** Settled; untouched here.
- **Any panel-wide aggregate splits in-target from out-of-target.** Every new surface this
  design introduces inherits that rule.
- **The read stays light-only, self-contained, zero-JavaScript.**
- **Library defects never reach the customer.** A coverage gap is disclosed as a fact
  about *scope* ("this product sits outside the demand spaces we built for you"), never as
  a confession about our internals.

---

## 11. The migration ledger

This is a real refactor and the costs should be visible, not discovered.

| what moves | cost / risk |
|---|---|
| `persona_core_hash` — cache keys on demographics + disposition + chaos + anchor | composition changes what a persona *is*; every core re-renders once. At current rates, tens of dollars per market, not hundreds. |
| `panel_version` | moves on every composition change, by design. Freeze records stay valid but are not comparable across the boundary. |
| `disposition_version` | hashes label + anchor; composed stances need a versioning scheme that survives recomposition. **Unsolved — design needed.** |
| gate-test baselines | all six baseline runs used hand-authored libraries. A composed library needs a fresh baseline *before* the gate test can certify it. **Blocking for Stage 2.** |
| the four thin scaffolds (`personal_audio`, `cadbury_chocolate`, `bru_coffee`, `starbucks_coffee`) | unvalidated and one-bundle-per-row. They should be **retired**, not migrated. Say it out loud so they do not zombie. |
| `health_wellness_nutrition` | the one validated library. It becomes the seed corpus for the first market map, not a casualty. |
| the audience form | gains occasion and substitution; keeps its four demographic questions. |

---

## 12. Staging — a working product at every step

"We can refactor" must not be read as "big-bang rewrite." Each stage ships on its own and
is falsifiable before the next one gets money.

**Stage 0 — no refactor at all. Ships on today's engine.**
- Add the two questions to the form: *what would they buy instead?* and *when do they buy
  it?* Asked explicitly at first, inferred later.
- Wire coverage refusal into the existing trust-ceiling choke point.
- Broaden the context envelope beyond feed-scrolling to include a point-of-purchase and a
  craving moment.

*This alone would have caught the SuperYou failure completely.*

**Stage 1 — data work, current architecture.**
- Rescope the nutrition pack to demand-space breadth: confectionery brands, real snack
  price points, quick-commerce channels.
- Author two or three missing stances by hand, the old way, to prove the demand-space
  framing produces a different and better read.

**Stage 2 — composition replaces authoring.**
- Build the mining and clustering pipeline.
- Re-baseline the gate test.
- Composition must beat hand-authoring on the gates before it is allowed to replace it.

**Stage 3 — market maps as pre-built assets.**
- One market, fully built, ahead of any customer for it.
- Onboarding becomes the two-minute confirmation.

---

## 13. Which market first, and why

**Indian nutrition and snacking**, and it is not close:

- it is the **only validated library** we have, so it starts half-built;
- it is where the **quick-commerce thesis** lives — Blinkit and Zepto are enormous for
  this category, and the panel surfaced Blinkit as the decisive channel unprompted;
- protein, snacking and confectionery **share one demand space**, so the corpus overlaps
  and one mining effort serves all three;
- and it is where the failure that started this was found, which means we can measure
  whether the fix worked on a case we already understand.

The bet being made, stated plainly: **pre-building a market map is fixed cost incurred
before revenue from that market.** That is a startup bet and it is the founder's to make.
It is only a good bet if the map serves many brands, which is exactly why the map must be
built at market level rather than per customer.

---

## 14. What this does not fix

**The instrument has still never touched reality.**

Nothing in this document changes that. Mining ten thousand reviews makes the panel
*grounded*, not *correct*. Composition makes coverage *scalable*, not *accurate*. The
gates test whether a library discriminates and whether its people differ from each other —
they do not test whether any of it corresponds to how humans actually behave.

The human panel study, and a backtest against real outcomes, remain **the only things that
convert any of this into evidence.** The demand-space architecture makes that study more
valuable, because a stable panel is something you can actually validate — you cannot
validate an audience that is regenerated from a text box on every run.

E-commerce listing images are the most promising route to that evidence: the outcome is a
clean per-product conversion number the platform hands the brand directly, and brands have
historical image sets with historical conversion. That is a retrospective backtest that
needs no live engagement.

---

## 15. Risks

| risk | why it matters | mitigation |
|---|---|---|
| composed stances go soft | if everyone likes every ad, the instrument dies quietly and looks fine | mine non-buyers deliberately; gate on discrimination; watch the refusal ceilings |
| inference error becomes the sampling frame | we would rebuild the competitor's central defect politely | inference proposes, declaration disposes; confirmation shows consequences; log overrides |
| demand-space granularity | too coarse reproduces the SuperYou failure; too fine shatters 100 agents into meaningless cells | one or two spaces per run, never twelve; treat granularity as an empirical question settled by the gate test |
| fixed cost before revenue | a market map is real spend ahead of a real customer | one market first, chosen because it is half-built already |
| provenance mistaken for validity | it is the exact overclaim we are attacking others for | never let a source count imply an accuracy number |
| n=1 evidence for inference | one correct classification is not a working classifier | log every override from day one; it is free error-rate data |

---

## 16. The promise, in the customer's words

> We build your market's demand map once. Everything inside it works instantly, forever,
> and the same audience judges every ad you bring us — so a change between two reports
> means something. At the edge of what we cover, the instrument tells you it is at the
> edge, before you spend, not after you have shipped.

The refusal is the product. It is not the flaw in it.
