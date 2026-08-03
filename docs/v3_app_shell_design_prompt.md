# The Claude Design prompt — the application shell

**This is the paste-ready one.** It covers everything behind the login: the reads list, the
upload flow, the money screens, the wait, and the failure states. The public landing page is the
user's own build — guidance for it lives at `docs/v3_landing_page_playbook.md`, not here.

## Context for us, not for the design tool

**Everything below the `---` is pasteable. Everything above it is ours.**

**Attach `docs/Claude design/Rocket Report.dc.html`** — the approved dashboard. The application
frames that page; it must not compete with it.

### Why this prompt is structured as a list of states

The dashboard prompt worked because it pasted **real data** instead of adjectives. The analogue
here is **the real states, all of them, enumerated with their real copy**. A design tool left to
itself designs the happy path, and the gaps surface during wiring — which is the expensive place
to find them. Six of the eleven states below are things going wrong or costing money, and they
are the ones that decide whether this reads as a serious instrument.

### Decisions this prompt encodes

- **The nav in the approved dashboard is currently inert** (Reads / New read / Sessions /
  Library / Settings, plus a search box and an Export button). This prompt is where those get
  real behaviour, and where the two that have nothing behind them get cut.
- **"Sessions" is deliberately NOT in the customer-facing nav.** It is the predict-then-reveal
  instrument we use *on* a brand manager; showing them a nav item with their own name in it
  breaks the blind. It moves to `/operator`.
- **The two-phase money gate must survive as two screens.** This is the single thing most likely
  to be "improved" away by a designer optimising the flow.
- **The wait is real: median 6.8 minutes, fastest 3.8** measured across 33 completed runs. Not
  a spinner's worth of time.
- Progress numbers are honest — we are building `progress.json` (plan §6) so the counter below
  reflects real agent completions rather than an animation.

---

# Design the application shell for Rocket

You are designing the signed-in application for **Rocket**, a tool that reads an ad creative
before it runs and diagnoses what is wrong with it. The finished report — the **Creative Read** —
is already designed and is attached. **Do not redesign it.** You are designing everything
around it: how someone signs in, sees their past reads, starts a new one, waits for it, and
opens the result.

## 1. The relationship to the attached report

The attached file is the deliverable — the thing a marketer sends to their boss. The application
is the workshop it comes out of. **The report is the loud thing; the app is the quiet thing.**
Every screen here must look like it came from the same studio: same typeface, same palette, same
restraint, less visual weight.

## 2. Who is using it

One person, on their own laptop, usually with someone looking over their shoulder. They are
about to spend real money with a button, and they know it. Screens that cost money should feel
different from screens that do not.

## 3. The frame

A persistent left sidebar and a main column.

**Sidebar — these four items only:**

- **Reads** — the list of finished Creative Reads. The home screen.
- **New read** — start one.
- **Brand profiles** — the accounts and brands reads are filed under.
- **Settings** — thin. Account name, sign out.

**Cut from the earlier design:** "Sessions" and "Library". Neither belongs to this user. Do not
design a slot for them.

At the bottom of the sidebar: the signed-in account name and a **Sign out** control.

**No account switcher.** There is one account (`demo`) and everything in the app is scoped to
it. Reads filed under other accounts exist on disk but are internal and are not surfaced here,
so the reads list needs no account column.

**The search box stays**, but scoped: it filters the reads list by creative name and decision.
It is not a global search.

## 4. THE STATES — design every one of these

### State 1 — Signed out

A sign-in screen. **One shared password, no email field, no "forgot password", no "create
account" link** — there is no self-serve signup, so any of those would lead nowhere.

Centre it. The Rocket wordmark, a single password field, a Sign in button. Design the **wrong
password** state too: a quiet inline error, not a red modal.

### State 2 — Reads list, populated

The home screen. A table or card list of finished reads. **Use this real data:**

| creative | decision | brand profile |
|---|---|---|
| ProSki protein cereal | REBUILD | health_wellness_demo |
| The Whole Truth whey isolate (pack shot) | ITERATE | health_wellness_demo |
| AI-hype protein (buzzword control) | ITERATE | health_wellness_demo |
| MuscleBlaze Biozyme Performance Whey | ITERATE | health_wellness_demo |
| Starbucks — The world has a pause button | ITERATE | starbucks_coffee |
| MuscleBlaze Biozyme Performance Whey | *(no decision)* | health_wellness_demo |

Two things this real data forces, and both are the point of using it:

- **The same creative appears many times.** Reads get re-run. The list must stay readable when
  eight rows have the same name — a date or run identifier has to be visible, not hidden behind
  a hover.
- **The last row has no decision at all.** Older reads predate the decision layer. Design that
  cell as a real state, not a blank.

⚠ **Opening a read LEAVES the application frame.** The Creative Read is a standalone,
self-contained file — it gets exported and forwarded, so it cannot be rendered inside the
sidebar. Clicking a read navigates to a full-page document with **a single "← Back to reads"
link** at the top and no sidebar, no search box, no app chrome. Do not design the read sitting
inside the frame; design the leaving of it.

The five decisions and their meanings, verbatim — treat them as the product's vocabulary:

- **SCALE** — Put spend behind it — no in-scope lever would materially lift it.
- **ITERATE** — Target responds; a specific in-scope fix is leaking conversion. Fix it, re-run, then scale.
- **RETARGET** — The creative works — for a different audience than it's aimed at. Fix the buy, not the ad.
- **REBUILD** — The target rejects it on grounds no in-scope tweak fixes. Don't run as-is.
- **INCONCLUSIVE** — The read isn't trustworthy yet — see why below.

⚠ **Do not colour-code these on a good-to-bad scale.** REBUILD is not a failure and SCALE is not
a win — they are different instructions. A red/amber/green treatment would make the list lie.
Distinguish them by type or by a neutral marker.

### State 3 — Reads list, empty

A first-run account with nothing in it. One line explaining what a read is, and the New read
action. No illustration, no cartoon rocket.

### State 4 — New read (the upload form)

The real fields, in this order:

**The creative**
- **Image file** (.png / .jpg / .webp) — a drop target as well as a file picker. This is the
  most important control on the screen; give it real presence.
- **Label** — *hint: "How it should read in the report header."*
- **Category** — a select.
- **Audience spec** — a select. *hint: "The audience this is aimed at."* Real option values look
  like `health_wellness_cold_traffic.json` and `health_wellness_baseline.json` — machine-ish
  names, sometimes long. Design the select to survive them.

**The buy**
- **Declared targeting** — free text. *hint: "Their stated audience, in their words. A hint to
  the classifier — it never overrides what the creative itself reads as."*
- **The ad's job** — a select. The five real options, in order, with **Direct-sell** as the
  default: `Direct-sell` · `Cold-hook` · `Awareness / informer` · `Brand-building` ·
  `Retain / win-back`.
- **Brand profile** — a select.
- **Marketer-led composition** — a checkbox, on by default. *hint: "Compose the panel from the
  declared audience. On for a real client read."*

Submit button, verbatim: **`Prepare (~$0.15)`**

Design an **uploaded** state — the image thumbnailed in place, replaceable. And design the
**wrong file type** error inline: *"That's not a .png, .jpg or .webp."*

### State 5 — Preparing (a short wait, ~30 seconds)

After submitting, the ad is classified and the panel is resolved. Under a minute. A modest
inline waiting state — this one *can* be a simple indeterminate indicator, because it is short.

### State 6 — Review and confirm ⚠ THE MONEY SCREEN

**This screen must exist as its own full page. Do not merge it into State 4, and do not turn it
into a confirmation modal.** Nothing has been charged yet; committing starts spending
immediately. The whole product's safety rests on this being a deliberate second act.

Header, verbatim: **`Phase 2 of 2 · before a credit is debited`** / **`Review, then commit`**

Three blocks:

**What the creative reads as** — the inferred audience, verbatim from a real run:

> Serious gym-goers and protein-literate buyers who care about isolate purity, grams-per-scoop,
> and third-party certification. Skews male, 20s–30s, urban, already inside the whey category.

Then the buyer types and whether each is inside or outside that target. **These are the real six
from that run, with their real classifications:**

| disposition | against that target |
|---|---|
| enthusiast_macros_lifter | **within** |
| aspirant_clean_label | outside |
| switcher_results_chaser | outside |
| skeptic_lapsed_protein | outside |
| pragmatist_protein_snacker | outside |
| purist_food_first | outside |

⚠ **One "within" against five "outside" is the normal case, not an error state.** A well-aimed
ad targets one buyer type. Do not design this table as though a wall of "outside" were a
problem to flag — that is what a correctly narrow ad looks like.

**The panel** — real values from that run: `100 agents across 6 dispositions × 4 contexts` ·
`15 segments (disposition × chaos band)` · `chaos mix: impulsive 25%, moderate 45%,
deliberate 30%` · a panel version string.

**Cost** — verbatim: *"Estimated **$4.28** — persona cores rendered: 29. Committing debits one
credit and starts spending immediately."*
Button, verbatim: **`Commit and run`**
Beneath it: **`← cancel (no credit debited)`**

#### 6b — The warnings, which appear on this screen and sometimes several at once

Design a warning treatment that survives **six stacked warnings** without becoming a wall.
These are the real strings; use them. (The *digits* in the first one vary run to run — the
sentence is real, the numbers are an illustrative fill.)

- **Thin audience coverage — 11/24 personas** — fewer eligible personas than the panel expects.
- **Purpose mismatch — reads as COLD HOOK, grading as DIRECT SELL**
- **Trust ceiling — a confident "ship it" is unreachable with this panel**
- **Provisional dispositions** — *"awaiting team review; the report will carry the flag."*
- **Ambiguous target** — the classifier could not settle on one audience.
- **No match** — the creative matched none of the authored buyer types.

#### 6c — The two STOP gates, which are a different and heavier thing

These are not warnings. Each **blocks the commit button until a checkbox is ticked**, and each
must look materially more serious than the warnings above.

⚠ **Do this without introducing a new colour.** The palette has exactly one warning hue
(`--leak: #b45309`), and reaching for red would both collide with the product's restraint and
break the no-invention rule. Separate the two tiers by **weight**, not hue: a filled
`--leak-tint` background, a heavier border, more padding, a bolder label, and the blocked
button visibly disabled until the box is ticked. A stop gate should read as heavier than a
warning at a glance, in the same colour family.

**Gate 1 — Gross demographic mismatch**
> Advisory, not a block. If this is deliberate (an off-demographic creative under test), tick
> the box. Otherwise fix the declared audience, or check you uploaded the right creative.

Checkbox label, verbatim: *"Yes — run it anyway, the mismatch is intentional."*

**Gate 2 — Unvalidated category**
> There is no hand-built, validated disposition library for this category. The engine will not
> fail gracefully: every persona classifies "outside" and the read comes out confident and
> wrong.

Checkbox label, verbatim: *"Yes — I know this category is unvalidated and the read is not
trustworthy."*

Design this screen **twice**: once clean (no warnings, no gates — the common case), and once
with two warnings and one stop gate showing.

### State 7 — Running ⚠ A REAL WAIT: 4 to 8 MINUTES

The most-watched screen in the product, often with a client sitting next to the user. It must
feel alive and honest for a long time. **No fake progress bar that fills at a constant rate.**

Five real phases, in order, with the current one active and finished ones marked done:

1. **The panel is reacting** — *"100 people are meeting your ad."* Real counter: **`63 of 100`**.
   This is the longest phase.
2. **Grouping by buyer type** — *"15 segments."* Counter: **`11 of 15`**.
3. **Building the population picture**
4. **Diagnosing the problems**
5. **Ranking the fixes**

Also show: elapsed time, the creative thumbnail, and the label. **Do not show an estimated time
remaining** — we cannot compute one honestly.

The page reloads itself periodically. Design it so a reload is not visually jarring.

### State 8 — Complete

The run finished. A quiet success state and one clear action: **Open the Creative Read.** Show
the decision it landed on, and the panel health line — real example: **`100/100 agents`**.

### State 9 — Degraded

Same as complete, but some agents dropped: **`94/100 agents — DEGRADED`**. The read is usable
and the shortfall must be visible rather than hidden. Not an error; a qualification.

### State 10 — Failed

The run stopped with an error. Show the error text plainly. The user needs to know **whether
they were charged** — say so.

### State 11 — Interrupted

Verbatim, because it prevents someone paying twice:
> The worker thread is gone and the run never completed. Recover it with replay_synthesis rather
> than paying again — the agent transcripts are already on disk.

Design this as recoverable, not as a crash.

### State 12 — Brand profiles

A thin screen: the account, the brand profiles under it, and how many reads each holds. **Real
counts from disk:**

| account | brand profile | reads |
|---|---|---|
| demo | health_wellness_demo | 27 |
| demo | boat_audio | 6 |
| demo | starbucks_coffee | 1 |
| demo | bru_coffee | 1 |
| demo | cadbury_chocolate | 1 |

No charts. The long tail of one-read profiles is the real shape — design for it rather than for
a tidy list of three.

## 5. Hard rules

- **Do not redesign the attached Creative Read.** It is approved and finished. The app frames it.
- **The Export control on a read downloads the report as a single HTML file.** That is all it
  does; do not design a format menu.
- **Light mode only.** No dark variant, no OS-preference response.
- **No modals for anything that costs money.** The money screen is a page.
- **Never invent a metric, a chart or a number that is not in this prompt.** Empty is better than
  invented — the product's whole positioning is that it does not make numbers up.
- **No onboarding tour, no tooltips carousel, no empty-state illustrations.**

## 5b. Build rules that decide how much rework this costs us ⚠

The application this plugs into is **server-rendered HTML with normal form posts** — not a
single-page JavaScript app. Designs that assume otherwise are expensive to wire, so these are
requirements, not preferences:

- **Every action is a real `<form>` or a real `<a href>`.** Uploading, preparing, committing,
  signing in and signing out must each be an ordinary form submission or link. No click handlers
  standing in for navigation, no `fetch`, no client-side router.
- **Semantic form markup throughout**: real `<form method="post">`, real `<label for>`, real
  `<input name>`, real `<select>`, real `<button type="submit">`. Do not simulate a select with
  styled `<div>`s — we have to bind server field names to these, and a div is unbindable.
- **The core flow must work with JavaScript switched off.** JS may enhance (a drag-and-drop
  affordance over the file input, a filter on the reads list), never carry.
- **No framework, no build step, no bundler, no npm.** Plain HTML and CSS, vanilla JS only where
  §5b permits it.
- **No external requests** — no CDN stylesheets, no Google Fonts link, no icon packages. Inline
  everything. Draw icons as inline SVG.
- **Responsive**, and specifically: usable at 1280×800, which is the meeting-room laptop.
- **Real focus states on every interactive element**, and never `outline: none` without a
  visible replacement.

## 5c. How to hand it over — this makes the wiring mechanical

This is the rule that made the dashboard port straightforward, so repeat it here:

**Put every piece of variable content in ONE JavaScript data object at the top of the file, and
have the markup read from it** — the reads list, the warnings array, the phase list, the
counters, the account name. We then delete that object and bind our real data to the same shape.
When values are instead scattered through the markup as literals, wiring becomes a hunt, and
that hunt is where guardrails get dropped.

Name the states in the markup the way they are named here (`state-6b-warnings`,
`state-7-running`, …) so each one can be matched back to this list without guesswork.

## 6. Look and feel

Use these exact tokens — they are the running product's real values:

```
font:      "Instrument Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif
mono:      ui-monospace, Menlo, "SF Mono", "Cascadia Code", Consolas, monospace
--ground:  #edebe6   --surface: #ffffff   --surface-2: #faf9f7
--ink:     #17181a   --muted: #6b6f76     --faint: #8a8d94    --line: #e7e5e0
--accent:  #0f8a6d   --accent-ink: #0b6b55   --accent-tint: #e8f2ee
--good:    #0f8a6d   --good-tint: #e8f2ee
--leak:    #b45309   --leak-tint: #fdf6e9     (warnings, and only warnings)
--shadow:  0 1px 3px rgba(0,0,0,.05)
```

Monospace for identifiers, counts, run ids and phase labels; the sans for everything a person
reads. Small uppercase mono labels are already the product's idiom — keep that.

## 7. How to hand it over

**One self-contained HTML file per screen state, or one file with every state stacked and
labelled** — either is fine, stacked is easier to review. All CSS inline in a `<style>` block,
no external requests, no build step.

Keep the states **visually labelled** (State 6b, State 7, …) so we can match them back to this
list when wiring.

Design at finished fidelity, not wireframe.
