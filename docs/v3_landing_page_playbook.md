# The landing page — playbook

**The user is building this one.** They are using Higgsfield for motion/graphics, gathering
their own Pinterest references, and driving the design themselves. This file is not a
paste-ready prompt: it is the structure, the rules that must survive whatever design comes back,
and the technical specs that make video on a landing page fast instead of miserable.

*(Replaces the earlier `v3_landing_design_prompt.md`. The app shell — which we do drive — has a
paste-ready prompt at `docs/v3_app_shell_design_prompt.md`.)*

---

## 0. Read this first: the landing page plays by different rules than the report

Two constraints you have heard a hundred times **do not apply here**, and knowing that unlocks
the whole thing:

| | the Creative Read (the report) | the landing page |
|---|---|---|
| self-contained single file | **required** — it is a deliverable people forward | **no** — it is a normal web page |
| zero JavaScript | **required** | **no** — motion, lazy loading, whatever it needs |
| external assets (video, images, fonts) | forbidden | **fine** — they live in `static/` |
| light mode only | required | your call, but match the app |

So: **go as rich as you like.** Video, motion, big type. The only things that carry over are the
palette, the typeface, and the claim rules in §3 — and the claim rules are non-negotiable.

**On Higgsfield:** an earlier note in `v3_report_redesign_brief.md` §6 says Higgsfield is the
wrong tool. That was about designing **the report** — a dense data surface, where a generative
video tool has nothing to offer. For a **landing page hero**, it is a sensible choice. Different
job, different tool; the old note does not apply.

---

## 1. What you are gathering before you prompt anything

1. **Pinterest references — 4 to 6, no more.** Pick ones that agree with each other. Six
   references pulling in six directions is how the dashboard went three rounds. For each one,
   write a single line about *what specifically* you want from it ("the way the type sits over
   the video", "that amount of empty space") — otherwise the tool copies the wrong thing.
2. **The hero motion clip** from Higgsfield — see §4 for what to generate and what to avoid.
3. **The product shot.** A real screenshot of a Creative Read, anonymised. **This one is mine to
   produce** — recipe in §5, and I will hand you the PNG.

---

## 2. The page structure

In this order. Everything here has real content behind it in §6.

1. **Top bar** — the Rocket wordmark, a **Sign in** button. Nothing else. No nav links to pages
   that do not exist.
2. **Hero** — headline, one supporting sentence, **Sign in**, and a quiet **Talk to us** email
   link beside it. The Higgsfield motion lives here, behind or beside the type.
3. **The problem** — three or four lines. Real copy in §6a.
4. **How it works** — three steps. §6b.
5. **What you actually get** — the anatomy of a Creative Read. The longest section, and the one
   that does the selling. Real problems and fixes in §6d–e. **The product screenshot goes here**
   if not in the hero.
6. **Why you can trust it** — the honesty section. §7. Design it as a feature, not small print.
   This is the section that wins a sceptical performance marketer.
7. **Footer** — wordmark, the contact email, nothing invented.

**Two actions on the whole page, and only two:** *Sign in* (top bar + hero) and a plain
`mailto:` *Talk to us* (hero, secondary + footer). There is no signup, so the email is how a
convinced reader reaches you. No capture form, no waitlist, no "Book a demo" modal.

---

## 3. ⚠ CLAIM RULES — these survive every design round

Paste this section verbatim into whatever prompt you end up writing. The product is early and
its claims are governed: it has **never been checked against a human panel or an in-market
backtest**, and a landing page is exactly where that gets quietly forgotten.

**Never write, imply, or leave a slot for:**

- ❌ Accuracy or performance figures. No "94% accurate", no "2.3× ROAS", no "saves you $40k".
- ❌ Any prediction of media metrics. Rocket does **not** predict CTR, ROAS, CPA or conversion
  rate. It is a **pre-flight diagnostic**, not a forecast.
- ❌ Testimonials, customer quotes, names, job titles, headshots.
- ❌ Client or brand logos. There is no "trusted by" strip to design.
- ❌ User counts, "10,000 ads analysed", counters that tick up.
- ❌ Pricing, plan tables, "free trial".
- ❌ "Replaces focus groups", and never the phrase "synthetic focus group".
- ❌ **Any mention of a product category or vertical** — not nutrition, not supplements, not D2C,
  not any industry. The page never raises the subject of which ads it can read. *(Your explicit
  call.)*

**What you may say, because it is true:** the panel is about 100 personas; they are built from
hand-researched real buyer profiles; the reactions are blind; every problem traces back to what
the panel actually said; and the report tells you when its own read is not trustworthy.

---

## 4. Higgsfield: what to generate, and how to keep it fast

### What works as a hero

Abstract, slow, and **loopable**. Things that read as "instrument" rather than "ad agency":
slow drifting fields, particles resolving into order, an eye/attention motif, light moving
across a surface, something crowd-like resolving into a pattern (which is quietly on-message —
100 people, one signal).

### What to avoid

- ❌ AI-generated **people**, especially faces — they land in the uncanny valley on a page whose
  entire pitch is "we are honest about what is real".
- ❌ Any generated **UI or dashboard**. Use the real screenshot; a fabricated one undercuts the
  page.
- ❌ Generated **text of any kind** — AI video renders letterforms badly and it is the first
  thing a designer's eye catches.
- ❌ Fast cuts and heavy motion behind headline type. It fights the words and it compresses
  badly.

### The specs that keep it fast ⚠

A hero video is the single easiest way to make a landing page feel slow. Hit these:

| | target |
|---|---|
| length | **4–8 seconds**, seamless loop |
| dimensions | **max 1600px wide** — it is decorative, it does not need 4K |
| file size | **under 2 MB**, ideally under 1 MB |
| audio | **none** — stripped, not just muted |
| format | **H.264 MP4** as the universal one; WebM/VP9 optional as a smaller alternate |

**Compress whatever Higgsfield gives you.** Raw output is typically 10–50× larger than it needs
to be. Two commands do it — send me the raw file if you would rather I run them:

```bash
# 1. the video: scale, drop audio, compress, and move the index to the front
#    (+faststart is what lets it start playing before it has finished downloading)
ffmpeg -i raw.mp4 -vf "scale=1600:-2,fps=24" -c:v libx264 -crf 28 -preset slow \
       -an -movflags +faststart hero.mp4

# 2. a poster frame, so something is on screen instantly
ffmpeg -i hero.mp4 -frames:v 1 -q:v 3 hero-poster.jpg
```

Check the result with `ls -lh hero.mp4`. Over 2 MB, raise `-crf` (30, then 32) and re-run — it
is a quality/size dial, higher means smaller.

### How it must be embedded

Tell the design tool this explicitly, because the default it produces will be wrong:

```html
<video autoplay muted loop playsinline preload="none" poster="hero-poster.jpg">
  <source src="hero.mp4" type="video/mp4">
</video>
```

- `muted` and `playsinline` are **required** — without both, iOS refuses to autoplay.
- `poster` means the page never shows a black rectangle while loading.
- **The page must look finished with the video absent.** If it fails to load, the poster carries
  it. Never put text *inside* the video.
- Text over video needs a **scrim** — a dark or light gradient between the two — or it will be
  unreadable on some frames. This is the most common failure of a video hero.
- Honour reduced motion — but **keep the element**, or you leave a hole where the hero was. Drop
  the autoplay and let the poster carry it:

```css
@media (prefers-reduced-motion: reduce) {
  video { /* still visible — the poster frame shows */ }
}
```

In practice: leave the `poster` in place and remove the `autoplay` attribute for those users
(one line of JS, or ship a paused video). The poster is a real image; it is not a fallback.

- Any video **below the fold** gets `preload="none"` and loads only when scrolled near.

---

## 5. The product screenshot — mine to produce, and why it needs care

⚠ **Every finished read on disk diagnoses a REAL company's ad.** Publishing "here is what is
wrong with MuscleBlaze's creative", under their name, on our own marketing site is a named
public critique of a company that has not agreed to it.

**The obvious escape hatch does not work.** The read labelled `AI-hype protein (buzzword
control)` sounds like an ad we invented. It is not — the PNG is a real **Herbyvore / Agrocorp**
creative. Publishing that one under the label "buzzword control" would be worse, not better.
*(The label describes; only the artifact is.)*

So the hero shot is produced from an anonymised copy: neutral `asset.label`, brand mentions
stripped from the pain text, rendered with `--no-image` so no third-party creative appears. Real
numbers, real diagnosis, no company named — and **the page must never imply a paying customer.**

---

## 6. The real content — use this copy, do not rewrite it into marketing language

The specificity is the product demonstration. Trim from the end if it is long; do not
paraphrase.

**The one-sentence claim:**

> Find out what is wrong with your ad before you pay to run it.

### 6a. The problem

> You find out an ad did not work by spending money finding out. By the time the numbers come
> back, the budget is gone and the only thing you have learned is that something was wrong —
> not what.

### 6b. How it works

1. **Upload the creative.** The image you are about to run, before it goes live.
2. **A panel of ~100 people meets it.** Each built from researched buyer profiles, each seeing
   the ad the way it appears in a feed — no briefing, no questions about your brand, no idea
   they are being studied.
3. **You get a Creative Read.** One decision, the problems ranked by what they are costing, and
   the specific changes worth making.

### 6c. The five decisions — verbatim, and do not add a sixth

- **SCALE** — Put spend behind it — no in-scope lever would materially lift it.
- **ITERATE** — Target responds; a specific in-scope fix is leaking conversion. Fix it, re-run, then scale.
- **RETARGET** — The creative works — for a different audience than it's aimed at. Fix the buy, not the ad.
- **REBUILD** — The target rejects it on grounds no in-scope tweak fixes. Don't run as-is.
- **INCONCLUSIVE** — The read isn't trustworthy yet — see why below.

⚠ Do not colour these on a good-to-bad scale. REBUILD is not a failure and SCALE is not a win —
they are different instructions.

### 6d. Real problems from a real read — use two of these three

Verbatim from a Creative Read of a whey isolate ad, brand removed. **This is the most persuasive
content on the page.**

> **The ad never dramatizes a switching trigger.** The creative presents the isolate as a
> familiar line-extension of a brand the target already trusts and largely already uses — so
> recognition is instant, but every lifter parses it as "the iso version of what I run" and
> correctly slots it as adjacent, not new.

> **An unanswered price-per-serving question.** The single most repeated friction: the target
> reads "isolate" and immediately prices in a premium the ad never shows or justifies. Because
> the cost delta is left blank, the engaged buyer defers the decision.

> **The one proof asset that earns a stop is never used.** The certification seal fires a
> half-second flicker but is never built into a claim the target can act on. Lifters recognize
> and trust it, yet it lands as a passive checkmark rather than an argument.

### 6e. A real ranked fix

> **Rebuild the headline around an explicit upgrade-and-cost argument** — lead with the switch
> trigger, so the spec delta and the price-per-serving both live on the creative surface.

---

## 7. The honesty section — the one that actually sells

Rocket is unusual in that it tells you when to distrust it. Three true things:

- **It grades its own confidence.** A read comes back HIGH, DIRECTIONAL or INCONCLUSIVE — and an
  INCONCLUSIVE read **withholds its own numbers** rather than letting you read them anyway.
- **Every problem traces back to what the panel said.** Nothing is asserted without the
  reactions underneath it.
- **It ships with its own caveat**, on every single report. Use this line verbatim:

> Didn't separate a known-bad control — tiebreaker, not gate.

Putting that on the marketing page *is* the marketing.

---

## 8. Look and feel — the part that must match the app

```
font:      "Instrument Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif
mono:      ui-monospace, Menlo, "SF Mono", "Cascadia Code", Consolas, monospace
--ground:  #edebe6   (warm off-white — not grey, not white)
--surface: #ffffff   --surface-2: #faf9f7
--ink:     #17181a   --muted: #6b6f76   --faint: #8a8d94   --line: #e7e5e0
--accent:  #0f8a6d   --accent-ink: #0b6b55   --accent-tint: #e8f2ee
--leak:    #b45309   --leak-tint: #fdf6e9
```

**The accent green is for one thing at a time.** A page where five things are green has no
accent.

Avoid, regardless of what the references show: gradient meshes, glassmorphism, floating 3D
shapes, abstract AI blobs, stock photography of people in offices, animated counters, parallax,
fake terminal windows, and any drawn/fake dashboard.

---

## 9. What to hand me when you are done

- The design as **HTML + CSS** (one file is fine), no build step, no framework.
- The **video files** — `hero.mp4` and `hero-poster.jpg`, compressed per §4.
- Any other images, at final size.

I will wire it onto `/`, serve the assets from `static/`, substitute the real email address, and
check it loads fast on a cold cache. Fonts are already embedded in the product and I will make
the landing page use the same ones — do not link Google Fonts.
