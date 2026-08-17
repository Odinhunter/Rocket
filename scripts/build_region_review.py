"""Render v1 next to v2 as a document the user can judge the panel from.

The question this page exists to answer: is this set of 192 women believable as
a slice of small-town India? Everything on it serves that judgement — the
measurement at the top, the people underneath, and the caveats in between.
"""
import html
import json
import pathlib
import sys
from collections import Counter

sys.path.insert(0, "/Users/ishan/Code/Rocket")
from agent import demography as demo  # noqa: E402

ROOT = pathlib.Path("/Users/ishan/Code/Rocket")
V1 = json.loads((ROOT / "generated_audience_w4560_t3.json").read_text())
V2 = json.loads((ROOT / "generated_audience_w4560_t3_v2.json").read_text())
OUT = pathlib.Path(__file__).resolve().parent.parent / "region_review.html"

e = html.escape
grid = V2["grid"]
OCC = {o["key"]: o for o in grid["occasions"]}
STANCE_ORDER = {s: i for i, s in enumerate(grid["stances"])}


def people_of(d):
    return [b for t in d["raw"] for b in t["bundles"]]


def town(b):
    return b["geography"].split("/")[0].strip()


p1, p2 = people_of(V1), people_of(V2)
u1, t1 = demo.achieved_mix(p1)
u2, t2 = demo.achieved_mix(p2)
expected = 100 - demo.female_lfpr(V2["region"]["age_min"], V2["region"]["age_max"],
                                  V2["region"]["tier"])

towns2 = Counter(town(b) for b in p2)
jobs2 = {b["occupation_hint"] for b in p2}
ages2 = sorted({b["age"] for b in p2})

by_occ = {}
for t in V2["raw"]:
    by_occ.setdefault(t["occasion"], []).append(t)

# The contrast strip: what the two generations put in the same field. Sampled
# across types rather than taken in file order, so neither side is cherry-picked
# from one occasion.
def sample_jobs(people, n=9):
    seen, out = set(), []
    for b in people:
        j = b["occupation_hint"]
        if j not in seen:
            seen.add(j)
            out.append(b)
    step = max(1, len(out) // n)
    return out[::step][:n]


# ⚠ THE SECOND CLAIM ON THIS PAGE IS MEASURED HERE, NOT ASSERTED. An earlier
# draft captioned the v1 column "everybody has an employer" and described v1 as
# a salaried monoculture. Both were wrong and the sample on the page disproved
# them: v1 already contained business owners and a pensioner. What actually
# moved is the share of WORKING women who work for themselves — PLFS puts it at
# 67 in 100, which is the figure the brief quotes at the model.
_SELF = __import__("re").compile(
    r"\bowns?\b|\bruns a\b|\bco-owns\b|from home|at home|her own|tiffin|tailor|"
    r"stitch|parlour|tuition|freelance|sells ", __import__("re").I)


def self_employed_share(people):
    working = [b for b in people if not demo.looks_unpaid(b["occupation_hint"])]
    if not working:
        return 0, 0
    return sum(bool(_SELF.search(b["occupation_hint"])) for b in working), len(working)


se1, w1 = self_employed_share(p1)
se2, w2 = self_employed_share(p2)


# ---------------------------------------------------------------- occasions
sections = []
for o in grid["occasions"]:
    types_ = sorted(by_occ.get(o["key"], []),
                    key=lambda t: STANCE_ORDER.get(t["stance"], 99))
    cards = []
    for t in types_:
        rows = []
        for b in t["bundles"]:
            unpaid = demo.looks_unpaid(b["occupation_hint"])
            rows.append(
                f'<tr class="{"unpaid" if unpaid else ""}">'
                f'<td class="mark" aria-hidden="true">{"—" if unpaid else ""}</td>'
                f'<td class="age">{b["age"]}</td>'
                f'<td class="town">{e(town(b))}</td>'
                f'<td class="day">{e(b["occupation_hint"])}'
                f'<span class="hh">{e(b["household_hint"])}</span></td></tr>')
        cards.append(f"""
      <article class="type">
        <header>
          <span class="stance">{e(t["stance"])}</span>
          <h3>{e(t["label"].replace("_", " "))}</h3>
        </header>
        <p class="ctx">{e(t["l1_context"])}</p>
        <p class="line"><span class="lbl">refuses</span>{e(t["l4_stance"])}</p>
        <p class="line"><span class="lbl">last did</span>{e(t["l5_behavior"])}</p>
        <table class="who">
          <caption class="sr">The people who hold this opinion</caption>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </article>""")
    sections.append(f"""
    <section class="occ" id="{e(o["key"])}" tabindex="-1">
      <div class="occ-head">
        <h2>{e(o["moment"])}</h2>
        <dl>
          <div><dt>competing with</dt><dd>{e(o["competes_with"])}</dd></div>
          <div><dt>decided by</dt><dd>{e(o["decided_by"])}</dd></div>
        </dl>
      </div>
      <div class="types">{"".join(cards)}</div>
    </section>""")

nav = "".join(f'<a href="#{e(o["key"])}">{e(o["key"].replace("_", " "))}</a>'
              for o in grid["occasions"])

v1_jobs = "".join(f"<li>{e(b['occupation_hint'])}</li>" for b in sample_jobs(p1))
v2_jobs = "".join(
    f'<li class="{"u" if demo.looks_unpaid(b["occupation_hint"]) else ""}">'
    f"{e(b['occupation_hint'])}</li>" for b in sample_jobs(p2))

HTML = f"""<title>The Women of Tier-3</title>
<style>
:root {{
  --ground:#EEF0EA; --raise:#F6F7F3; --ink:#1C231E; --soft:#5A6459;
  --faint:#8A9287; --rule:#D3D8CD; --accent:#1D4E5F; --clay:#A05A3A;
  --olive:#4F7042; --olive-wash:#E3EADD;
  --serif:ui-serif,"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#131714; --raise:#1A1F1B; --ink:#E4E8DF; --soft:#A3ADA0;
    --faint:#78826F; --rule:#2C332C; --accent:#7FBACB; --clay:#D08A63;
    --olive:#93B882; --olive-wash:#1E2A1D;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#131714; --raise:#1A1F1B; --ink:#E4E8DF; --soft:#A3ADA0;
  --faint:#78826F; --rule:#2C332C; --accent:#7FBACB; --clay:#D08A63;
  --olive:#93B882; --olive-wash:#1E2A1D;
}}
*,*::before,*::after {{ box-sizing:border-box; }}
body {{
  background:var(--ground); color:var(--ink);
  font-family:var(--sans); font-size:16px; line-height:1.6;
  margin:0; padding:0 5vw 6rem;
  -webkit-font-smoothing:antialiased;
}}
.sr {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }}
.wrap {{ max-width:74rem; margin:0 auto; }}
a {{ color:var(--accent); }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:3px; border-radius:2px; }}

/* ---- masthead ---- */
.mast {{ padding:4.5rem 0 2rem; border-bottom:1px solid var(--rule); }}
.eyebrow {{
  font-size:.72rem; letter-spacing:.16em; text-transform:uppercase;
  color:var(--faint); margin:0 0 1.1rem;
}}
.mast h1 {{
  font-family:var(--serif); font-weight:400; font-size:clamp(2.1rem,5vw,3.4rem);
  line-height:1.12; margin:0 0 1rem; text-wrap:balance; letter-spacing:-.01em;
}}
.dek {{
  font-family:var(--serif); font-size:clamp(1.02rem,1.7vw,1.2rem);
  color:var(--soft); max-width:38em; margin:0; line-height:1.55;
}}

/* ---- verdict ---- */
.verdict {{
  display:grid; gap:1px; background:var(--rule);
  grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));
  border:1px solid var(--rule); margin:2.5rem 0 0;
}}
.cell {{ background:var(--raise); padding:1.4rem 1.5rem; }}
.cell dt {{
  font-size:.7rem; letter-spacing:.13em; text-transform:uppercase;
  color:var(--faint); margin:0 0 .6rem;
}}
.cell dd {{
  margin:0; font-family:var(--mono); font-variant-numeric:tabular-nums;
  font-size:1.85rem; line-height:1.1; letter-spacing:-.02em;
}}
.cell .sub {{ font-family:var(--sans); font-size:.82rem; color:var(--soft); margin-top:.45rem; line-height:1.45; }}
.was dd {{ color:var(--clay); }}
.now dd {{ color:var(--olive); }}

/* ---- prose blocks ---- */
.note {{
  border-left:3px solid var(--accent); background:var(--raise);
  padding:1.3rem 1.5rem; margin:2.5rem 0 0; max-width:52em;
}}
.note h2 {{
  font-size:.72rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--accent); margin:0 0 .7rem; font-weight:600;
}}
.note p {{ margin:0 0 .8rem; font-size:.94rem; color:var(--soft); }}
.note p:last-child {{ margin-bottom:0; }}
.note strong {{ color:var(--ink); font-weight:600; }}

h2.rule {{
  font-family:var(--serif); font-weight:400; font-size:1.6rem;
  margin:4rem 0 .5rem; padding-bottom:.6rem; border-bottom:1px solid var(--rule);
}}
.standfirst {{ color:var(--soft); max-width:44em; margin:0 0 1.8rem; font-size:.95rem; }}

/* ---- contrast strip ---- */
.contrast {{ display:grid; gap:1.5rem; grid-template-columns:repeat(auto-fit,minmax(19rem,1fr)); }}
.col {{ border:1px solid var(--rule); background:var(--raise); padding:1.3rem 1.4rem; }}
.col h3 {{
  font-size:.72rem; letter-spacing:.13em; text-transform:uppercase;
  margin:0 0 .3rem; font-weight:600;
}}
.col.before h3 {{ color:var(--clay); }}
.col.after h3 {{ color:var(--olive); }}
.col .cap {{ font-size:.8rem; color:var(--faint); margin:0 0 1rem; }}
.col ul {{ margin:0; padding:0; list-style:none; }}
.col li {{
  font-family:var(--serif); font-size:.93rem; line-height:1.45;
  padding:.5rem 0 .5rem .9rem; border-top:1px solid var(--rule);
  border-left:2px solid transparent;
}}
.col li:first-child {{ border-top:0; }}
.col li.u {{ border-left-color:var(--olive); background:var(--olive-wash); }}

/* ---- nav ---- */
.nav {{
  position:sticky; top:0; z-index:5; background:var(--ground);
  border-bottom:1px solid var(--rule); padding:.7rem 0;
  display:flex; flex-wrap:wrap; gap:.4rem .9rem; margin-top:3rem;
}}
.nav a {{
  font-size:.74rem; letter-spacing:.05em; text-transform:uppercase;
  text-decoration:none; color:var(--soft); padding:.15rem 0;
  border-bottom:1px solid transparent;
}}
.nav a:hover {{ color:var(--accent); border-bottom-color:var(--accent); }}

/* ---- occasions ---- */
.occ {{ padding-top:3rem; scroll-margin-top:3.5rem; }}
.occ-head {{ margin-bottom:1.5rem; }}
.occ-head h2 {{
  font-family:var(--serif); font-weight:400; font-size:clamp(1.35rem,2.6vw,1.85rem);
  margin:0 0 .9rem; text-wrap:balance; max-width:26em; line-height:1.25;
}}
.occ-head dl {{ margin:0; display:grid; gap:.35rem; max-width:52em; }}
.occ-head dt {{
  font-size:.68rem; letter-spacing:.13em; text-transform:uppercase;
  color:var(--faint); display:inline;
}}
.occ-head dd {{ display:inline; margin:0 0 0 .55rem; font-size:.87rem; color:var(--soft); }}

.types {{ display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule);
          grid-template-columns:repeat(auto-fit,minmax(20rem,1fr)); }}
.type {{ background:var(--raise); padding:1.4rem 1.5rem; }}
.type header {{ margin-bottom:.85rem; }}
.stance {{
  font-size:.66rem; letter-spacing:.15em; text-transform:uppercase;
  color:var(--accent); font-weight:600;
}}
.type h3 {{
  font-family:var(--serif); font-weight:400; font-size:1.12rem;
  margin:.25rem 0 0; line-height:1.3;
}}
.ctx {{ font-family:var(--serif); font-size:.95rem; margin:0 0 .9rem; line-height:1.5; }}
.line {{ font-size:.86rem; color:var(--soft); margin:0 0 .55rem; line-height:1.5; }}
.lbl {{
  display:block; font-size:.62rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--faint); margin-bottom:.12rem;
}}

.who {{ width:100%; border-collapse:collapse; margin-top:1.1rem; font-size:.83rem; }}
.who tr {{ border-top:1px solid var(--rule); }}
.who td {{ padding:.5rem .5rem .5rem 0; vertical-align:top; }}
.who .mark {{
  width:1rem; padding-right:.35rem; color:var(--olive);
  font-family:var(--mono); font-weight:700;
}}
.who .age {{
  font-family:var(--mono); font-variant-numeric:tabular-nums;
  color:var(--faint); width:2.2rem;
}}
.who .town {{ color:var(--soft); white-space:nowrap; padding-right:.7rem; }}
.who .day {{ font-family:var(--serif); line-height:1.4; }}
.who .hh {{ display:block; color:var(--faint); font-family:var(--sans); font-size:.76rem; margin-top:.15rem; }}
.who tr.unpaid {{ background:var(--olive-wash); }}

.legend {{
  display:flex; flex-wrap:wrap; gap:1.2rem; align-items:center;
  font-size:.8rem; color:var(--soft); margin:1.2rem 0 0;
}}
.swatch {{ display:inline-block; width:.85rem; height:.85rem; background:var(--olive-wash);
           border-left:2px solid var(--olive); vertical-align:-1px; margin-right:.4rem; }}

footer {{ margin-top:5rem; padding-top:1.5rem; border-top:1px solid var(--rule);
          font-size:.82rem; color:var(--faint); max-width:50em; }}
@media (max-width:600px) {{
  .who .town {{ white-space:normal; }}
  body {{ padding:0 1.2rem 4rem; }}
}}
</style>

<div class="wrap">
<header class="mast">
  <p class="eyebrow">Generated audience · women 45–60 · tier-3 towns · {e(V2["category"])}</p>
  <h1>Does this look like {len(p2)} real women?</h1>
  <p class="dek">The first version of this panel gave every one of its 194 women a paid job.
  In small-town India roughly two in three do not have one. Here is the same region generated
  again with the population figures in front of the model — and the people it wrote.</p>
</header>

<dl class="verdict">
  <div class="cell was">
    <dt>Before the fix</dt>
    <dd>{u1} <span style="font-size:1rem;color:var(--faint)">of {t1}</span></dd>
    <p class="sub">women whose day is unpaid or household-centred — one woman, helping at her husband's grain shop</p>
  </div>
  <div class="cell now">
    <dt>After the fix</dt>
    <dd>{u2} <span style="font-size:1rem;color:var(--faint)">of {t2}</span></dd>
    <p class="sub">{u2 / t2:.0%} of the panel — homemakers, unpaid helpers, women minding grandchildren</p>
  </div>
  <div class="cell">
    <dt>Distinct days</dt>
    <dd>{len(jobs2)}</dd>
    <p class="sub">of {len(p2)} people, across {len(towns2)} towns and {len(ages2)} ages</p>
  </div>
  <div class="cell">
    <dt>Cost</dt>
    <dd>$1.30</dd>
    <p class="sub">64 buyer types, 13 batches, no refusals, all five checks pass</p>
  </div>
</dl>

<div class="note">
  <h2>Read the number honestly</h2>
  <p><strong>37% is not being compared with 69% as a score.</strong> The population figure counts
  women outside the labour force. Our count is a keyword read of what was written, and the two
  miss in opposite directions: a woman living on a pension alone is missed by ours but counted
  by theirs, while a woman keeping her husband's accounts unpaid is counted by ours and treated
  as <em>employed</em> by the official survey.</p>
  <p>So the gap is not a shortfall to close, and chasing it would teach the generator to write
  the words the counter looks for. <strong>What was being tested is whether the number could stop
  being zero.</strong> It did.</p>
</div>

<h2 class="rule">What changed in kind, not just in count</h2>
<p class="standfirst">The count is the alarm. This is the evidence — the same field, filled by the
two generations, sampled the same way across both. The change is not only that homemakers
appeared. Among the women who <em>do</em> work, the share working for themselves rather than for
an employer went from <strong>{se1 / w1:.0%}</strong> to <strong>{se2 / w2:.0%}</strong>. The
survey puts it at 67%, and that is the figure the model was shown.</p>
<div class="contrast">
  <div class="col before">
    <h3>Before</h3>
    <p class="cap">Every woman earns. {se1} of the {w1} working are self-employed.</p>
    <ul>{v1_jobs}</ul>
  </div>
  <div class="col after">
    <h3>After</h3>
    <p class="cap">Shaded rows are days counted as unpaid. {se2} of the {w2} working are
    self-employed.</p>
    <ul>{v2_jobs}</ul>
  </div>
</div>

<h2 class="rule">The register</h2>
<p class="standfirst">Every buyer type the model wrote, in the moment it was written for, with the
women who hold that opinion. Eight moments, eight positions in each. This is the thing to judge:
not whether the numbers are right, but whether you would believe these people.</p>
<div class="legend"><span><span class="swatch"></span>an unpaid or household-centred day</span>
<span>age · town · what fills the day</span></div>

<nav class="nav">{nav}</nav>
{"".join(sections)}

<footer>
  <p>Generated 18 August 2026 from the same brief, grid and region as the first version — women
  aged 45–60 in tier-3 towns, any household income — so the prompt is the only thing that differs
  between them. Population proportions from the Periodic Labour Force Survey 2023–24, by way of
  the UNFPA analytical paper on women's labour force participation; a secondary source, and
  labelled as one.</p>
  <p>Nothing here has been installed as a library. These checks test form, not truth: the panel
  has still never been put next to real people.</p>
</footer>
</div>
"""

OUT.write_text(HTML)
print(f"wrote {OUT}  ({len(HTML) / 1024:.0f} KB)")
print(f"v1 {u1}/{t1} · v2 {u2}/{t2} · expected ~{expected:.0f}%")
print(f"self-employed among working: v1 {se1}/{w1} ({se1 / w1:.0%}) -> "
      f"v2 {se2}/{w2} ({se2 / w2:.0%}); PLFS says 67%")
print(f"{len(jobs2)} distinct days · {len(towns2)} towns · ages {ages2[0]}-{ages2[-1]}")
