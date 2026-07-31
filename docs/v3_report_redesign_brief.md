# Creative Read — report redesign: constraints, data inventory, and what failed

**Status (2026-07-26): the DESIGN is the user's, taken in-house after three
prompt-driven attempts overshot.** This file is not a design. It is the durable
material any redesign needs — the real data available, the guardrails that must survive,
and a record of what was already tried so it isn't repeated.

**Update 2026-07-27 — the ORDER is now settled; the visual design is still the user's.**
The user supplied a reference dashboard and specified the narrative:
**result → diagnosis → problems → solutions → extras**. That order is built, pinned by 7
mutation-proved tests, and verified on all 56 runs — see `v3_discriminant_check.md` §7,
which supersedes the earlier diagnosis-first order. Two structural decisions from that
reference are already in the HTML and any redesign should keep them: the **verdict sits
inside the opening result beat but after the measured numbers, wearing its own caveat**
(`read_model.VERDICT_CAVEAT`), and the **diagnosis is a counted overview before the problem
cards**. What remains open here is the visual layer — the grid, the charts, the density.

---

## 1. What failed, and why — three rounds

Each round fixed the previous complaint and overshot into the opposite failure. Worth
knowing before writing another design prompt.

| round | prompt asked for | what came back | user's verdict |
|---|---|---|---|
| 1 | fidelity to the terminal report | a single 820px column of prose | *"page not utilised, first half entirely text"* |
| 2 | "charts and numbers over sentences" + full data inventory | ~10 panels at equal weight in 3 columns, every pixel filled | *"haywire, no story — we've just filled every blank pixel"* |
| 3 | one four-beat argument + max 5 elements above the fold | huge serif editorial headlines, one beat per screen | *"absolute crap"* |

**The pattern: each prompt over-corrected the last complaint.** Round 2's "show the
numbers" produced an inventory; round 3's "tell one story" produced a magazine spread that
wastes vertical space. The failure was never the visual craft — it was that a written
prompt converts a *balance* problem into a *direction* instruction, and direction
instructions overshoot.

Two diagnoses from round 2 that stay true regardless of visual direction:
- **Redundancy at the top reads as inventory.** A KPI tile saying "4 of 100 stopped" above
  a chart showing the same thing is the same fact twice. Three of five tiles were repeats.
- **Uniform density is the problem, not density.** Ten panels at equal visual weight means
  nothing is primary, so the eye has no entry point.

---

## 2. The constraint that outranks visual taste

**A dashboard built on "what percent of the panel did X" renders near-identically for a
great ad and a deliberately terrible one.** Measured across four real ads:

| | scroll past | stopped | saved | would buy |
|---|---|---|---|---|
| MuscleBlaze | 95 | 4 | 0 | 2 |
| AI-buzzword control (built to be bad) | 87 | 10 | 3 | 0 |
| The Whole Truth | 85 | 14 | 1 | 0 |
| ProSki | 93 | 7 | 0 | 0 |

Out of ~100 every time. This is the same discriminant failure `docs/v3_discriminant_check.md`
found at the *score* layer, reappearing visually. **There is no time series and no
benchmark** — nothing trends, nothing compares to last period. Designing for data we don't
have is the main way this goes wrong.

**What actually varies between a good ad and a bad one** — build on these:
1. **Audience breadth** — how many consumer types engaged at all (1 / 1 / 3 / 3 across the
   four ads above). The single most discriminating number, currently a chip row.
2. **The diagnosis structure** — 6–9 problems × funnel stage × severity × in/out of target
   × breadth. The layer that correctly separated the bad ad.
3. **Fix → problem traceability** — a real many-to-many mapping.
4. **Buying-cycle position** — 0 of 5 running low would buy; all intent was mid-cycle.

---

## 3. Data inventory — everything that exists

Values from the validated σ-study MB run.

**Identity** — creative image · asset label · read against `enthusiast macros lifter` ·
panel 18 in-target of 99 · job `direct_sell` · audience bought "all genders 25-44"

**Diagnosis — 6 problems (range 6–9).** Each: id (`P1`…) · funnel stage (`attention` →
`comprehension` → `consideration` → `conversion`) · severity `execution` (fixable in the
creative) or `structural` (product/market) · within/outside target (here 4 within, 2
outside) · exactly one flagged load-bearing · breadth = how many consumer types raised it
(1–3, from `cited_by`) · a ≤22-word lead + a 40–70 word explanation · a prevalence sentence
· 3–4 verbatim quotes each attributed to a consumer type and browsing context.

**Fixes** — 0–5 ranked one-line levers; 0–3 detailed fixes, each with the change, rationale,
a "what your target said" line, `traces_to` problem ids, and a lever class
(`creative` / `media_buy` / `offer`).

**Response** — per consumer type (5 sampled of a 6–7 library), action mix + next step.
Actions: `scroll_past` · `linger` · `tap_cta` · `save` · `share`. Next step: `nothing` ·
`research_first` · `buy_at_restock` · `buy_now` · `mention_to_someone`. In-target headline:
would buy 11% (2 of 18) · research first 22% · stopped to look 22%. Cycle: running low
0 of 5 · mid-cycle 2 of 9 · just bought 0 of 4. Reach: 1 of 6 library types.

**Verdict** — `ITERATE` · trust `directional` · engine read `mixed · 76`. **The least
reliable element on the page** (see §2) — do not hero it.

**Supporting** — 3 strengths with quotes · 4 browsing contexts each with a verdict and a
line · 6 consumer verbatims · footer with run id, flags, category.

**Denominators are load-bearing.** 11% is 2 of 18 people. n is small and honest.

---

## 4. Guardrails — must survive any redesign

Conditional surfaces. A page showing a confident number with its qualifier missing is worse
than no page. Each is pinned by a test at its trigger condition in
`tests/test_read_model.py` / `tests/test_report_html.py`.

1. Sample degradation · "how much to trust the headline" (F3 launch scope) · A7 coherence check
2. **v2.1 audience mismatch** — has never fired in any of the 56 runs on disk, so it cannot
   be seen in real output, but it fires on a client's own ad
3. **Model-inferred disclaimer** — every quote is a simulated persona. Unmissable, never
   footer-buried
4. Why confidence is "directional" rather than a hard score
5. Funnel projection off — why a number is deliberately withheld
6. Methodology flags + provisional dispositions

**INCONCLUSIVE is a distinct layout**: the entire numbers block disappears — no
percentages, no bars, no cycle table — and the untrustworthy-read notice takes the top,
above the diagnosis. The state most likely to be in front of a skeptical prospect.

**Shapes that vary:** problems 6–9 · detailed fixes 0–3 · levers 0–5 · contexts 3–4 ·
consumer types 5 sampled / 6–7 library / 1–3 engaged · quotes 0–4 per card. Any section can
be empty and must vanish cleanly, not leave a shell.

---

## 5. Rules for the build, whatever the design looks like

- **`ReadModel` is the source of truth.** No renderer reaches past it into raw run JSON —
  that is how a guardrail gets lost. See [[report_surface_fidelity]] and the
  `sample_report.html` lesson (a hand-built page that silently dropped two guardrails).
- **The copy is load-bearing.** Headings, taglines, trust lines and caveat wording are
  shared with `batch_run._print_report` and several are precisely worded for honesty
  reasons. Section *order* is legitimately per-surface; *vocabulary* is not.
- **Self-contained output** — no external fonts, scripts or images; creative inlined as a
  data URI. Light and dark.
- **New panels need data-layer work, not just CSS. This is now CLOSED for both §2 items.**
  `ReadModel.diagnosis` (`build_diagnosis_overview`) exposes **problem counts,
  in/out-of-target split, structural-vs-execution split, funnel-stage distribution, the
  load-bearing problem id, and widest breadth** (`max(len(cited_by))`) — §2 item 2, and the
  raw material for a stage chart. **`ReadModel.panel` (`build_panel_response`, shipped
  2026-07-28) closes §2 item 1** — every consumer type, in AND out of target, with action
  mix, response rate and next steps, plus a `decoupling_note` that fires when outsiders
  out-respond the target. Audience breadth is no longer a chip row; it is a full table's
  worth of structured data. Still not exposed: per-problem breadth as a *series* rather
  than a max.
- One client-facing wording bug to fix whenever the redesign lands: the glance legend can
  render **"unclassified"**, which is engine vocabulary. Use the action name or "other".

---

## 6. The build path — stack, tools, and the process that stops the overshoot

**Added 2026-08-01, at the user's explicit request for direction.** This supersedes the
"don't write another design prompt" rule in §1: the user has asked to be told what to use
and how it should look, because they build rather than design. §1's *lesson* still holds —
what failed was the method, not the effort.

### 6.1 The architecture fork — decide this FIRST

The current page is HTML assembled from Python strings (`agent/report_html.py`). That is
why it looks the way it does: there is no component library, no chart library, and CSS
inside a Python string literal is a hostile medium for iterating on a visual design.

| | A — keep server-rendered Python | B — JSON API + Next.js front end |
|---|---|---|
| Look | bounded by hand-written CSS | shadcn/ui baseline is production-grade on day one |
| Charts | hand-built SVG | Recharts |
| AI design tools | cannot target it | v0 and Claude both emit exactly this stack |
| Output | one self-contained file (emailable) | a served app; a file export becomes work |
| Guardrail risk | low — one renderer | **high — this is how `sample_report.html` silently dropped two guardrails** |

**Recommended: B, with one discipline that removes its only real risk.**

> **Guardrails travel as DATA, not as front-end copy.** `ReadModel` already holds every
> caveat, trust line, scope note and disclaimer as a *string* (that is the whole point of
> the module). The API serialises those strings; the front end renders what it is handed
> and composes none of its own. A React component that writes its own caveat text is the
> `sample_report.html` failure rebuilt in TypeScript.

The FastAPI server already builds `ReadModel` on every request, so the API is a
serialiser away. Keep `agent/report_html.py` alive as the self-contained export path.

### 6.2 Tools — what to use, and what not to

- **v0.dev** — generate the React/Tailwind/shadcn components from a prompt plus reference
  screenshots. This is the one that turns Pinterest references into code.
- **shadcn/ui + Tailwind + Recharts** — the foundation. shadcn is why it will look
  professional without a designer. The repo already has `vercel:shadcn` and `vercel:nextjs`
  skills available.
- **Claude Code (this CLI)** — wiring the generated components to real data, and iterating
  in-repo once the skeleton exists.
- **Figma — skip for now.** It produces a picture, not a product, and the gap between the
  two is the work. Reach for it only to hand a real designer a starting point.
- **Higgsfield — wrong tool.** It generates images and video (ad creative, visuals). It has
  no part in building a dashboard UI. Worth using *later* for marketing the product; not
  for this.

### 6.3 The process — one objective test, and components before pages

§1 records three rounds where each prompt over-corrected the last complaint. A fourth
prompt will do it again. What breaks the loop is a pass/fail test that is not taste:

> **Render the SAME design for two ads at once — a real one and the deliberately-bad
> AI-buzzword control — and put them side by side. If the two pages look substantially
> alike, the design has failed, however beautiful it is.**

That is §2 made operational: percentages render near-identically for a great ad and a
terrible one, so any design leaning on them is a design that cannot tell them apart. The
four things that genuinely change shape are **audience breadth** (`ReadModel.panel`), the
**problem map** (stage × severity × in/out target), **fix → problem traceability**, and
**cycle position**. Build the hero elements out of those.

Then: **review one component at a time, not whole pages.** Verdict block, then diagnosis
map, then problem card, then panel table. Round 2 failed because ten panels arrived at
equal weight and nothing was primary — a per-component review makes "what is the hero
here" answerable, which a whole-page review never does.

### 6.4 What it should feel like

Not an analytics dashboard. There is no time series, nothing trends, nothing compares to
last period, and a KPI tile row was three-fifths repetition last time. The right reference
class is a **diagnostic instrument** — a lab result, a structural survey, a credit report:
one primary object per screen, everything else visibly subordinate to it, and the reader
never in doubt about what the page is claiming or how much to believe it.

Structure that is already settled and should not be relitigated: the five-beat order
(**result → diagnosis → problems → solutions → extras**), the verdict inside the opening
result beat wearing `VERDICT_CAVEAT`, warnings above the result, and levers adjacent to
the fixes they summarise. The open layer is grid, charts, type and density.
