"""report_html — render a ReadModel as the client-facing Creative Read.

A single self-contained HTML file: no external CSS, fonts, scripts or image
requests (the creative is embedded as a data URI), so it renders identically
whether it is served by the operator tool, opened from disk, or published.
Theme-aware (light/dark). Stdlib only — the engine has no template
dependency and this must not add one.

Everything it renders comes from ReadModel. It must never reach past the
model into raw run JSON: the model is where the guardrails live, and going
around it is how a client-facing page quietly loses one.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from agent.read_model import (
    FUNNEL_STAGE_ORDER, VERDICT_CAVEAT, ReadModel, humanize,
)

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
}

# Pains are ordered by the funnel stage they leak at, so the page reads in the
# order the buyer actually moves. Shared with the diagnosis overview, which
# counts the same stages — see read_model.FUNNEL_STAGE_ORDER.
_STAGE_ORDER = FUNNEL_STAGE_ORDER

# Glance segment colours, keyed by action. Escalating engagement: ignored →
# noticed → acted. Anything unrecognised falls back to accent-ink, so a new
# action still renders rather than disappearing.
_GLANCE_CSS = {
    "scroll_past": "var(--neutral)",
    "seek_info": "var(--accent)",
    "linger": "var(--accent)",
    "save": "var(--accent-ink)",
    "share": "var(--accent-ink)",
    "tap_cta": "var(--good)",
}


def _e(text: object) -> str:
    """Escape for HTML text. Everything model-generated goes through here —
    an LLM-authored pain or quote can contain < > &."""
    return html.escape(str(text if text is not None else ""), quote=True)


def _data_uri(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    mime = _MIME.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _quotes_html(quotes) -> str:
    out = []
    for q in quotes or []:
        cite = " · ".join(
            p for p in (getattr(q, "disposition", ""), getattr(q, "context", "")) if p
        )
        out.append(
            f'<div class="quote">“{_e(q.quote)}”'
            + (f'<span class="cite">{_e(cite)}</span>' if cite else "")
            + "</div>"
        )
    return "".join(out)


_CSS = """
:root{
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --font-mono:ui-monospace,"SF Mono","Cascadia Code","Roboto Mono",Menlo,Consolas,monospace;
  --ground:#EFF1F4;--surface:#FFFFFF;--surface-2:#F7F8FA;
  --ink:#171A20;--muted:#576070;--faint:#8A92A0;--line:#E1E4EA;
  --accent:#C9741B;--accent-ink:#8A4E0E;--accent-tint:rgba(201,116,27,.10);
  --good:#2C7A57;--good-tint:rgba(44,122,87,.10);
  --leak:#B4453A;--leak-tint:rgba(180,69,58,.09);
  --neutral:#AEB6C2;
  --shadow:0 1px 2px rgba(20,24,33,.04),0 10px 34px rgba(20,24,33,.06);
  --maxw:820px;
}
@media (prefers-color-scheme:dark){
  :root{--ground:#0F1116;--surface:#181C22;--surface-2:#1E232B;--ink:#E9ECF1;--muted:#9AA2AE;--faint:#69717D;--line:#272D36;
    --accent:#EC9A45;--accent-ink:#F4B877;--accent-tint:rgba(236,154,69,.14);
    --good:#5FBE8F;--good-tint:rgba(95,190,143,.13);--leak:#E0796C;--leak-tint:rgba(224,121,108,.13);--neutral:#4B5462;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 12px 38px rgba(0,0,0,.5);}
}
:root[data-theme="light"]{--ground:#EFF1F4;--surface:#FFFFFF;--surface-2:#F7F8FA;--ink:#171A20;--muted:#576070;--faint:#8A92A0;--line:#E1E4EA;--accent:#C9741B;--accent-ink:#8A4E0E;--accent-tint:rgba(201,116,27,.10);--good:#2C7A57;--good-tint:rgba(44,122,87,.10);--leak:#B4453A;--leak-tint:rgba(180,69,58,.09);--neutral:#AEB6C2;--shadow:0 1px 2px rgba(20,24,33,.04),0 10px 34px rgba(20,24,33,.06);}
:root[data-theme="dark"]{--ground:#0F1116;--surface:#181C22;--surface-2:#1E232B;--ink:#E9ECF1;--muted:#9AA2AE;--faint:#69717D;--line:#272D36;--accent:#EC9A45;--accent-ink:#F4B877;--accent-tint:rgba(236,154,69,.14);--good:#5FBE8F;--good-tint:rgba(95,190,143,.13);--leak:#E0796C;--leak-tint:rgba(224,121,108,.13);--neutral:#4B5462;--shadow:0 1px 2px rgba(0,0,0,.3),0 12px 38px rgba(0,0,0,.5);}

*{box-sizing:border-box;}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--font-sans);font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased;}
.page{max-width:var(--maxw);margin:0 auto;padding:34px 22px 80px;}
.eyebrow{font-family:var(--font-mono);font-size:11.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--accent-ink);font-weight:600;}
h1{font-size:27px;line-height:1.16;margin:8px 0 0;font-weight:750;letter-spacing:-.015em;text-wrap:balance;}
h2{font-size:14px;font-family:var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600;margin:0;}
section{margin-top:34px;}
section>h2{margin-bottom:14px;}
p{margin:0;color:var(--muted);}
.lead{color:var(--ink);}

.head{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap;}
.thumb{width:96px;height:96px;flex:0 0 auto;border-radius:12px;overflow:hidden;border:1px solid var(--line);box-shadow:var(--shadow);background:var(--surface-2);}
.thumb img{width:100%;height:100%;object-fit:cover;display:block;}
.head__meta{flex:1;min-width:240px;}
.metaline{margin-top:10px;font-size:13.5px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 16px;font-family:var(--font-mono);}
.metaline b{color:var(--ink);font-weight:600;}

.decision{margin-top:24px;border:1px solid var(--line);border-left:4px solid var(--accent);background:var(--surface);border-radius:14px;padding:20px 22px;box-shadow:var(--shadow);}
.decision__row{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;}
.verdict{font-size:30px;font-weight:800;letter-spacing:-.01em;color:var(--accent-ink);}
@media (prefers-color-scheme:dark){.verdict{color:var(--accent);}}
:root[data-theme="dark"] .verdict{color:var(--accent);}
:root[data-theme="light"] .verdict{color:var(--accent-ink);}
.pill{font-family:var(--font-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--line);border-radius:999px;padding:4px 10px;color:var(--muted);}
.decision p{margin-top:10px;color:var(--ink);font-size:16.5px;}
.decision .sub{margin-top:8px;color:var(--muted);font-size:13.5px;}

.warn{margin-top:14px;border:1px solid var(--line);border-left:3px solid var(--leak);background:var(--leak-tint);border-radius:11px;padding:13px 15px;font-size:14px;color:var(--ink);}
.warn b{font-family:var(--font-mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--leak);display:block;margin-bottom:4px;}
.warn--stop{border-left-width:5px;}
.warn--stop .sub{margin:3px 0 0;}

.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
@media (max-width:620px){.tiles{grid-template-columns:1fr;}}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:13px;padding:16px 17px;box-shadow:var(--shadow);}
.tile .k{font-family:var(--font-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);}
.tile .v{font-size:34px;font-weight:750;letter-spacing:-.02em;margin-top:6px;font-variant-numeric:tabular-nums;line-height:1;}
.tile .d{font-size:13px;color:var(--muted);margin-top:7px;}

.panelbox{margin-top:12px;background:var(--surface);border:1px solid var(--line);border-radius:13px;padding:17px;box-shadow:var(--shadow);}
.panelbox .k{font-family:var(--font-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);}
.bar{display:flex;height:26px;border-radius:7px;overflow:hidden;margin-top:12px;gap:2px;background:var(--surface);}
.bar span{display:block;height:100%;border-radius:3px;}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;font-size:13px;color:var(--muted);}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px;}

.cycle{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;}
.cycle th{text-align:left;font-family:var(--font-mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);font-weight:600;padding:0 0 7px;}
.cycle td{padding:7px 0;border-top:1px solid var(--line);color:var(--ink);font-variant-numeric:tabular-nums;}
.cycle td.n{color:var(--muted);}
.cycle .track{display:block;height:7px;border-radius:4px;background:var(--surface-2);overflow:hidden;min-width:80px;}
.cycle .track i{display:block;height:100%;background:var(--accent);border-radius:4px;}

.cards{display:flex;flex-direction:column;gap:12px;}
.card{background:var(--surface);border:1px solid var(--line);border-radius:13px;padding:17px 18px;box-shadow:var(--shadow);}
.card--good{border-left:3px solid var(--good);}
.card--leak{border-left:3px solid var(--leak);}
.card--fix{border-left:3px solid var(--accent);}
.card .stage{font-family:var(--font-mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);}
.card .t{font-weight:680;font-size:16.5px;margin-top:4px;letter-spacing:-.01em;}
.card .body{color:var(--muted);font-size:14.5px;margin-top:7px;}
.quote{margin-top:11px;padding-left:12px;border-left:2px solid var(--line);color:var(--ink);font-size:14px;font-style:italic;}
.quote+.quote{margin-top:7px;}
.quote .cite{display:block;font-style:normal;font-family:var(--font-mono);font-size:11px;color:var(--faint);margin-top:3px;}
.fixnum{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--accent-tint);color:var(--accent-ink);font-family:var(--font-mono);font-size:12px;font-weight:700;margin-right:9px;}
@media (prefers-color-scheme:dark){.fixnum{color:var(--accent);}}
.traces{margin-top:9px;font-family:var(--font-mono);font-size:11px;color:var(--faint);letter-spacing:.04em;}
.chip{display:inline-block;margin-left:9px;padding:2px 8px;border-radius:999px;background:var(--leak-tint);color:var(--leak);font-family:var(--font-mono);font-size:10px;letter-spacing:.07em;text-transform:uppercase;font-weight:700;}
.ptab{width:100%;border-collapse:collapse;font-size:14px;min-width:560px;}
.ptab th{text-align:left;font-family:var(--font-mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);font-weight:600;padding:0 12px 8px 0;white-space:nowrap;}
.ptab td{padding:11px 12px 11px 0;border-top:1px solid var(--line);color:var(--ink);vertical-align:top;}
.ptab td.n{font-variant-numeric:tabular-nums;white-space:nowrap;}
.ptab .ct{font-weight:650;}
.ptab .sm{font-size:12.5px;color:var(--muted);}
.tgt{display:inline-block;margin-top:4px;font-family:var(--font-mono);font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--faint);border:1px solid var(--line);border-radius:999px;padding:2px 8px;}
.tgt--in{background:var(--good-tint);border-color:var(--good);color:var(--good);font-weight:700;}
.minibar{display:flex;height:9px;width:110px;border-radius:5px;overflow:hidden;gap:1px;background:var(--surface-2);}
.minibar span{display:block;height:100%;border-radius:2px;}
.stagerow{display:flex;flex-wrap:wrap;gap:7px;margin-top:13px;}
.st{display:inline-block;padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:var(--surface-2);color:var(--faint);font-size:13px;}
.st--leak{background:var(--leak-tint);border-color:var(--leak);color:var(--leak);font-weight:650;}
.reachrow{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px;}
.reach{display:inline-block;padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:var(--surface-2);color:var(--faint);font-size:13px;text-decoration:line-through;}
.reach--in{background:var(--good-tint);border-color:var(--good);color:var(--good);font-weight:650;text-decoration:none;}

.ctxgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
@media (max-width:620px){.ctxgrid{grid-template-columns:1fr;}}
.ctx{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:13px 14px;box-shadow:var(--shadow);}
.ctx .name{font-weight:650;font-size:14px;}
.ctx .vtag{font-family:var(--font-mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-ink);}
.ctx .s{color:var(--muted);font-size:13px;margin-top:6px;}

ol.bets{margin:0;padding-left:20px;color:var(--ink);font-size:15px;}
ol.bets li{margin-bottom:9px;}
ol.bets li::marker{font-family:var(--font-mono);color:var(--accent-ink);font-weight:700;}

.note{margin-top:32px;background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:16px 18px;font-size:13.5px;color:var(--muted);}
.note b{color:var(--ink);}
.note+.note{margin-top:12px;}
.foot{margin-top:26px;font-family:var(--font-mono);font-size:11.5px;color:var(--faint);border-top:1px solid var(--line);padding-top:14px;display:flex;flex-wrap:wrap;gap:5px 18px;}
"""


def _header(m: ReadModel, embed_image: bool, base_dir: Path) -> str:
    thumb = ""
    if embed_image and m.asset_path is not None:
        p = m.asset_path if m.asset_path.is_absolute() else base_dir / m.asset_path
        uri = _data_uri(p)
        if uri:
            thumb = (f'<div class="thumb"><img src="{uri}" '
                     f'alt="the creative under test"></div>')
    meta = [f"read against: <b>{_e(m.within_label)}</b>"]
    if m.glance.n:
        meta.append(f"panel: <b>{m.glance.n} in-target</b>")
    elif m.panel_size:
        meta.append(f"panel: <b>{m.panel_size} simulated</b>")
    meta.append(f"job: <b>{_e(m.purpose_label)}</b>")
    if m.declared_audience:
        meta.append(f"audience bought: <b>{_e(m.declared_audience)}</b>")
    return f"""<div class="head">{thumb}
  <div class="head__meta">
    <div class="eyebrow">Creative read · pre-flight diagnostic</div>
    <h1>{_e(m.asset_label or 'Creative read')}</h1>
    <div class="metaline">{''.join(f'<span>{s}</span>' for s in meta)}</div>
  </div>
</div>"""


def _warnings(m: ReadModel) -> str:
    """Every surface that qualifies how much of this page to believe.

    Pinned to the TOP, above the result band — not because the page should
    open on caveats (it shouldn't, and on most runs this block is empty so it
    doesn't), but because three of these four qualify THE NUMBERS, not the
    diagnosis: the coherence check qualifies the buy tile, the launch-scope
    note qualifies the headline metric, and panel degradation qualifies every
    denominator on the page. Placed below the result band they would each
    arrive after the number they exist to qualify, which is not a caveat.

    On an INCONCLUSIVE read this block is doing the most work on the page: it
    is the only thing standing between a prospect and a confident-looking
    report the engine itself does not trust.
    """
    out: list[str] = []
    # INCONCLUSIVE — say so before a single pain is read.
    if m.is_inconclusive or m.headline is None:
        lines = "".join(f'<p class="sub">{_e(l.strip())}</p>' for l in m.inconclusive)
        out.append(f'<div class="warn warn--stop"><b>{_e(m.tagline)}</b>{lines}</div>')
    # v2.1 audience match — the creative reads as aimed at someone other than
    # the audience being bought. It qualifies every number and pain below it.
    if m.audience_mismatch:
        out.append(f'<div class="warn"><b>Audience mismatch</b>'
                   f'{_e(m.audience_mismatch)}</div>')
    # F3 launch scope — the headline metric for this job is not fully anchored.
    if m.scope_note:
        out.append(f'<div class="warn"><b>How much to trust the headline</b>'
                   f'{_e(m.scope_note)}</div>')
    # A7 coherence.
    if m.coherence_warning:
        out.append(f'<div class="warn"><b>Coherence check</b>'
                   f'{_e(m.coherence_warning.split(":", 1)[-1].strip())}</div>')
    if m.panel_degraded:
        out.append(f'<div class="warn"><b>Sample note</b>{_e(m.panel_degraded)}</div>')
    return "".join(out)


def _verdict_block(m: ReadModel) -> str:
    """The decision bucket — the claim the report makes, and the first thing
    on the page after any warning.

    It LEADS the result beat, by the user's explicit call (asked twice). That
    puts the least reliable element on the page — docs/v3_discriminant_check.md:
    it scored a deliberately-bad control the same as real ads — where a reader
    who goes no further will have read only it. VERDICT_CAVEAT rendering
    INSIDE this block is therefore load-bearing, not decoration: it is the
    whole of what keeps a lead-with-the-bucket page honest. Don't move it to a
    footnote, and don't drop it in a restyle.
    """
    pills = [f'<span class="pill">trust: {_e(m.trust.lower())}</span>']
    pills.append(
        f'<span class="pill">engine read: {_e(m.report.verdict.lower())} · '
        f'{m.report.confidence}</span>'
    )
    # On INCONCLUSIVE, _warnings has already run this tagline AND the reasons
    # under it at the top of the page. Repeating the tagline here would print
    # "…see why below" with nothing below it — the why moved upward — and say
    # it twice. So the bucket shows only its trust note in that state.
    lead = "" if m.is_inconclusive else f'\n  <p class="lead">{_e(m.tagline)}</p>'
    out = [f"""<div class="decision">
  <div class="decision__row">
    <span class="verdict">{_e(m.decision_name)}</span>{''.join(pills)}
  </div>{lead}
  <p class="sub">{_e(m.trust_note)}</p>
  <p class="sub">{_e(VERDICT_CAVEAT)}</p>"""]
    out.append("</div>")
    return "".join(out)


def _numbers(m: ReadModel) -> str:
    """The tiles + the glance bar + the A4 cycle table. Suppressed entirely on
    an INCONCLUSIVE read — an untrustworthy read must never show a confident
    action-rate headline."""
    if m.is_inconclusive or m.headline is None:
        return ""

    d = m.report.decision
    buy_rate = d.target_action_rate or 0.0
    tiles = [f"""<div class="tile">
      <div class="k">{_e(m.purpose_metric_label)}</div>
      <div class="v" style="color:var(--leak)">{_pct(buy_rate)}</div>
      <div class="d">{_e(m.headline.strip())}</div>
    </div>"""]
    if m.research_line:
        tiles.append(f"""<div class="tile">
      <div class="k">Would research first</div>
      <div class="v" style="color:var(--accent-ink)">{_pct(d.research_rate or 0)}</div>
      <div class="d">Interested, but they leave the ad to go compare — reported
      separately, never counted as a sale.</div>
    </div>""")
    if m.glance.n:
        engaged = (m.glance.engaged / m.glance.n) if m.glance.n else 0.0
        acted = m.glance.count("tap_cta") + m.glance.count("save") + m.glance.count("share")
        followed = (f"{acted} of {m.glance.n} went further — tapped, saved or shared."
                    if acted else "none tapped, saved or shared.")
        tiles.append(f"""<div class="tile">
      <div class="k">Stopped to look</div>
      <div class="v">{_pct(engaged)}</div>
      <div class="d">Caught the eye in the feed; {followed}</div>
    </div>""")

    out = [f'<section><h2>The numbers that matter — your actual buyers</h2>'
           f'<div class="tiles">{"".join(tiles)}</div>']

    if m.glance.n:
        # Driven by what the run actually recorded. A hardcoded three-segment
        # list is what previously rendered a permanent "tapped through 0%" and
        # silently dropped savers from the denominator.
        segs, legend = [], []
        for key, label, count, r in m.glance.segments():
            css = _GLANCE_CSS.get(key, "var(--accent-ink)")
            if r:
                segs.append(f'<span style="width:{r*100:.4f}%;background:{css}"></span>')
            legend.append(f'<span><i style="background:{css}"></i>{_e(label)} — '
                          f'{_pct(r)} <b>({count})</b></span>')
        aria = ", ".join(f"{_pct(r)} {label.lower()}"
                         for _, label, _, r in m.glance.segments())
        out.append(f"""<div class="panelbox">
      <div class="k">The 2-second glance — what the thumb did ({m.glance.n} in-target)</div>
      <div class="bar" role="img" aria-label="{_e(aria)}">{''.join(segs)}</div>
      <div class="legend">{''.join(legend)}</div>
    </div>""")

    # A4 — the mix-independent read. The blended headline above assumes the
    # panel's sampled cycle mix; these rows are what it assumes.
    if m.cycle_rows:
        rows = "".join(
            f'<tr><td>{_e(r["label"])}</td>'
            f'<td><span class="track"><i style="width:{r["rate"]*100:.4f}%"></i></span></td>'
            f'<td>{_pct(r["rate"])}</td>'
            f'<td class="n">{r["num"]} of {r["denom"]}</td></tr>'
            for r in m.cycle_rows
        )
        out.append(f"""<div class="panelbox">
      <div class="k">Where they are in the buying cycle — the mix-independent read</div>
      <table class="cycle"><thead><tr><th>Position</th><th></th><th>Would buy</th><th>Count</th></tr></thead>
      <tbody>{rows}</tbody></table>
      <p style="margin-top:10px;font-size:13px;">The headline above blends these
      at the panel's sampled cycle mix — read the rows, not just the blend.</p>
    </div>""")

    out.append(_reach(m))

    if m.champion_line:
        out.append(f'<div class="warn"><b>Right ad, wrong person</b>'
                   f'{_e(m.champion_line)}</div>')
    elif m.narrow_frame_line:
        out.append(f'<p class="sub" style="margin-top:12px;font-size:13px;">'
                   f'{_e(m.narrow_frame_line)}</p>')
    out.append("</section>")
    return "".join(out)


def _panel_table(m: ReadModel) -> str:
    """Every consumer type in the panel, in and out of target.

    The rest of the page is measured on the in-target slice, which can answer
    "did the people we bought respond" but cannot answer "who else did" — and
    in real runs those come apart: a type read as in-target can do nothing
    while an out-of-target type acts. Suppressed on INCONCLUSIVE with the rest
    of the numbers; an untrustworthy read must not show response rates here
    either, by any route.
    """
    p = m.panel
    if p.is_empty or m.is_inconclusive or m.headline is None:
        return ""

    rows = []
    for t in p.types:
        bar = "".join(
            f'<span style="width:{r*100:.4f}%;background:'
            f'{_GLANCE_CSS.get(k, "var(--accent-ink)")}"></span>'
            for k, _, _, r in t.glance.segments() if r
        )
        steps = " · ".join(f"{lab} <b>{n}</b>" for _, lab, n in t.step_rows()
                           if _ != "nothing") or "—"
        tag = ('<span class="tgt tgt--in">your target</span>' if t.within_target
               else '<span class="tgt">not targeted</span>')
        rows.append(f"""<tr>
      <td><div class="ct">{_e(t.label)}</div>{tag}</td>
      <td class="n">{t.n}</td>
      <td><span class="minibar">{bar}</span></td>
      <td class="n"><b>{_pct(t.engaged_rate)}</b><br><span class="sm">{t.engaged} of {t.n}</span></td>
      <td class="sm">{steps}</td>
    </tr>""")

    note = ""
    if p.decoupling_note:
        note = (f'<div class="warn"><b>Right ad, wrong person?</b>'
                f'{_e(p.decoupling_note)}</div>')

    return f"""<section><h2>Who else responded — every consumer type</h2>
  <p class="lead" style="margin-bottom:12px;">{_e(p.summary)}</p>
  <div class="panelbox" style="margin-top:0;overflow-x:auto;">
    <table class="ptab">
      <thead><tr><th>Consumer type</th><th>Saw it</th><th>What the thumb did</th>
      <th>Responded</th><th>What they'd do next</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>{note}</section>"""


def _strengths(m: ReadModel) -> str:
    items = m.report.strengths_to_preserve
    if not items:
        return ""
    cards = "".join(
        f'<div class="card card--good"><div class="t">{_e(s.strength)}</div>'
        f'{_quotes_html(s.evidence_quotes)}</div>'
        for s in items
    )
    return (f'<section><h2>What\'s working — keep these</h2>'
            f'<div class="cards">{cards}</div></section>')


# The lead is set at display weight, so it has to stay scannable. Assessed
# pains routinely open with a 40-word sentence; bolding all of it produces a
# wall the eye slides off. Past this many words we clip the lead to a headline
# and keep the FULL text in the body, so nothing is lost.
_LEAD_MAX_WORDS = 22


def _split_lead(text: str) -> tuple[str, str]:
    """Split an LLM-authored paragraph into a scannable headline and the rest,
    so a card can lead with the claim without repeating it in the body."""
    text = (text or "").strip()
    lead, rest = text, ""
    for i in range(len(text) - 1):
        # A sentence end: '.' followed by a space and a capital/quote. Avoids
        # splitting on decimals, 'e.g.', or an abbreviation mid-sentence.
        if text[i] == "." and text[i + 1] == " " and i + 2 < len(text):
            nxt = text[i + 2]
            if nxt.isupper() or nxt in "“\"'":
                lead, rest = text[: i + 1].strip(), text[i + 2:].strip()
                break

    words = lead.split()
    if len(words) > _LEAD_MAX_WORDS:
        # Clip to a headline, and carry the whole pain in the body so the
        # clipped words are still on the page.
        return " ".join(words[:_LEAD_MAX_WORDS]).rstrip(",;:—-") + "…", text
    return lead, rest


def _diagnosis_overview(m: ReadModel) -> str:
    """The shape of the diagnosis, ahead of the problems themselves.

    Its own beat because the pattern across the problems — how many land on
    the audience being bought, how many are structural, where in the funnel
    they cluster — is invisible while reading them one card at a time, and it
    is the part that decides what to do. Deliberately a derived text strip and
    not a chart: this states what the cards below already say, and a chart
    would claim precision the counts don't have.
    """
    ov = m.diagnosis
    if ov.is_empty:
        return ""

    out = [f'<section><h2>Why they\'re not buying — the diagnosis</h2>'
           f'<div class="panelbox" style="margin-top:0;">'
           f'<p class="lead">{_e(ov.summary)}</p>']

    # All four stages, with the leaking ones marked — the stages that DIDN'T
    # leak are as informative as the ones that did, and are invisible if only
    # the leaks are listed.
    leaking = set(ov.stages)
    chips = "".join(
        f'<span class="st{" st--leak" if s in leaking else ""}">{_e(s)}</span>'
        for s in list(_STAGE_ORDER) + [s for s in ov.stages if s not in _STAGE_ORDER]
    )
    out.append(f'<div class="stagerow">{chips}</div>')

    if ov.widest_breadth:
        types = ("one buyer type" if ov.widest_breadth == 1
                 else f"{ov.widest_breadth} different buyer types")
        out.append(f'<p class="sub" style="margin-top:12px;font-size:13px;">'
                   f'The most widely-felt problem was raised by {types}.</p>')

    if ov.load_bearing_id:
        stage = f" ({_e(ov.load_bearing_stage)})" if ov.load_bearing_stage else ""
        out.append(f'<p class="sub" style="margin-top:8px;font-size:13px;">'
                   f'Start with <b>{_e(ov.load_bearing_id)}</b>{stage} — it is the '
                   f'one driving the verdict, and it is marked in the detail below.'
                   f'</p>')

    out.append("</div></section>")
    return "".join(out)


def _pains(m: ReadModel) -> str:
    pains = list(m.report.pain_map)
    if not pains:
        return ""
    load_bearing = (m.report.decision.load_bearing_pain_id
                    if m.report.decision else "") or ""

    # Within-target pains first (they gate the decision), the load-bearing one
    # ahead of its peers, then by funnel stage in the order the buyer moves.
    def key(p):
        stage = (p.funnel_stage or "").lower()
        return (0 if p.within_target else 1,
                0 if p.id == load_bearing else 1,
                _STAGE_ORDER.index(stage) if stage in _STAGE_ORDER else len(_STAGE_ORDER))

    cards = []
    for p in sorted(pains, key=key):
        tags = [t for t in (p.id, p.funnel_stage) if t]
        if not p.within_target:
            tags.append("outside target")
        chip = ('<span class="chip">the one to fix first</span>'
                if p.id == load_bearing else "")
        lead, rest = _split_lead(p.pain)
        cards.append(
            f'<div class="card card--leak">'
            f'<div class="stage">{_e(" · ".join(tags))}{chip}</div>'
            f'<div class="t">{_e(lead)}</div>'
            + (f'<div class="body">{_e(rest)}</div>' if rest else "")
            + (f'<div class="traces">prevalence: {_e(p.prevalence)}</div>'
               if p.prevalence else "")
            + _quotes_html(p.evidence_quotes)
            + "</div>"
        )
    # "The diagnosis" now heads the overview section above; these cards are
    # its detail, so the heading says so rather than repeating the claim.
    return (f'<section><h2>The problems in detail</h2>'
            f'<div class="cards">{"".join(cards)}</div></section>')


def _reach(m: ReadModel) -> str:
    """Which audience types the creative actually reached. This is what makes
    the in-target denominator legible — an 18-of-100 panel is not a small
    sample by accident, it is one audience type out of six."""
    tm = m.report.target_match
    if not (tm.reached or tm.missed):
        return ""
    chips = "".join(
        f'<span class="reach reach--in">{_e(humanize(d.disposition))}</span>'
        for d in tm.reached
    ) + "".join(
        f'<span class="reach">{_e(humanize(d.disposition))}</span>'
        for d in tm.missed
    )
    total = len(tm.reached) + len(tm.missed)
    return f"""<div class="panelbox">
      <div class="k">Who it reached — {len(tm.reached)} of {total} audience types in your library</div>
      <div class="reachrow">{chips}</div>
      <p style="margin-top:10px;font-size:13px;">Highlighted types are the ones
      this creative speaks to; the rest scrolled past as out-of-target. The
      numbers above are measured on the highlighted group only.</p>
    </div>"""


def _fixes(m: ReadModel) -> str:
    changes = m.report.top_3_changes
    if not changes:
        return ""
    cards = []
    for i, c in enumerate(changes, 1):
        traces = ""
        if getattr(c, "derives_from_pains", None):
            traces = (f'<div class="traces">traces to: '
                      f'{_e(", ".join(c.derives_from_pains))}'
                      + (f' · lever: {_e(c.lever_class)}' if getattr(c, "lever_class", "") else "")
                      + "</div>")
        corr = ""
        if getattr(c, "within_target_corroboration", ""):
            corr = (f'<div class="body" style="margin-top:8px;"><b>What your target '
                    f'said:</b> {_e(c.within_target_corroboration)}</div>')
        cards.append(
            f'<div class="card card--fix">'
            f'<div class="t"><span class="fixnum">{i}</span>{_e(c.change)}</div>'
            f'<div class="body">{_e(c.why)}</div>{corr}{traces}'
            f'{_quotes_html(c.evidence_quotes)}</div>'
        )
    return (f'<section><h2>The fixes in detail — each traced to the diagnosis</h2>'
            f'<div class="cards">{"".join(cards)}</div></section>')


def _bets(m: ReadModel) -> str:
    if not m.report.bet_ranking:
        return ""
    items = "".join(f"<li>{_e(b)}</li>" for b in m.report.bet_ranking)
    return (f'<section><h2>{_e(m.lever_heading.rstrip(":"))}</h2>'
            f'<div class="panelbox" style="margin-top:0;">'
            f'<ol class="bets">{items}</ol></div></section>')


def _context(m: ReadModel) -> str:
    cfm = m.report.context_fit_map
    if not cfm:
        return ""
    cards = "".join(
        f'<div class="ctx"><span class="vtag">{_e(e.verdict)}</span>'
        f'<div class="name">{_e(ctx.replace("_", " "))}</div>'
        f'<div class="s">{_e(e.friction_summary)}</div></div>'
        for ctx, e in cfm.items()
    )
    return (f'<section><h2>Where it lands — across {len(cfm)} feed moments</h2>'
            f'<div class="ctxgrid">{cards}</div></section>')


def _voice(m: ReadModel, limit: int = 6) -> str:
    quotes = m.report.verbatim_consumer_voice[:limit]
    if not quotes:
        return ""
    return (f'<section><h2>Simulated consumer voice</h2>'
            f'<div class="panelbox" style="margin-top:0;">{_quotes_html(quotes)}</div>'
            f'</section>')


def _notes(m: ReadModel) -> str:
    notes = [f'<div class="note"><b>How to read the quotes.</b> {_e(m.disclaimer)}</div>']
    if m.trust == "DIRECTIONAL":
        n = len(m.within_dispositions)
        notes.append(
            '<div class="note"><b>Why the confidence is “directional,” not a hard '
            f'score.</b> This ad speaks to {"one buyer type" if n == 1 else f"{n} buyer types"}'
            f'{" (" + _e(m.within_label) + ")" if n else ""}, so the read rests on a '
            'single attitudinal group. That is enough to point a clear direction and '
            'name the leak — not enough to stake a precise number on. A confident '
            '“ship it” needs a creative that speaks to two or more buyer types.</div>'
        )
    if m.funnel_note:
        notes.append(f'<div class="note"><b>Funnel projection.</b> {_e(m.funnel_note)}</div>')
    return "".join(notes)


def _footer(m: ReadModel) -> str:
    bits = [f"run: {_e(m.run_id)}", f"engine read: {_e(m.report.verdict)} · "
            f"{m.report.confidence}/100"]
    if m.report.methodology_flags:
        bits.append(f"flags: {_e(', '.join(m.report.methodology_flags))}")
    if m.report.provisional_dispositions:
        bits.append("provisional dispositions: "
                    f"{_e(', '.join(m.report.provisional_dispositions))}")
    if m.category:
        bits.append(f"category: {_e(m.category)}")
    if m.report_source != "run.json":
        bits.append(f"recovered via {_e(m.report_source)}")
    return f'<div class="foot">{"".join(f"<span>{b}</span>" for b in bits)}</div>'


def render_html(
    model: ReadModel, *, embed_image: bool = True, base_dir: Path | None = None,
    full_document: bool = True,
) -> str:
    """Render the Creative Read as a self-contained HTML page.

    base_dir resolves a relative asset path (defaults to the repo root, which
    is where run configs record asset paths from). full_document=False emits
    just the <title>/<style>/<body-content> fragment, for hosts that supply
    their own document skeleton.
    """
    base_dir = base_dir or Path.cwd()
    title = f"Creative Read — {model.asset_label}" if model.asset_label else "Creative Read"
    # Order is deliberate, is the USER'S specified narrative, and differs from
    # batch_run._print_report (the operator terminal view), which is left
    # as-is — presentation order is legitimately per-surface; the shared
    # vocabulary in read_model.py is what must never drift.
    #
    # The story a brand manager reads, in five beats:
    #     result → diagnosis → problems → solutions → extras
    #
    # Two placements inside that are load-bearing and were reasoned about;
    # don't re-flip either without reading the note attached to it:
    #
    #   * _warnings stays pinned ABOVE the result. Three of the four surfaces
    #     it renders qualify the NUMBERS (coherence → the buy tile, launch
    #     scope → the headline metric, panel degradation → every denominator),
    #     so below the result band each would arrive after the number it
    #     qualifies. It is empty on most runs, so the page still opens on the
    #     result — which was the actual complaint about the old order.
    #   * _verdict_block OPENS the result beat, and its caveat is therefore
    #     load-bearing. The bucket is the least reliable element on the page
    #     (docs/v3_discriminant_check.md: it scored a deliberately-bad control
    #     the same as real ads), and leading with it means a reader who goes
    #     no further has read only that. VERDICT_CAVEAT rendering INSIDE the
    #     block is what keeps that honest — it is not decoration, and it must
    #     not be moved out to a footnote or dropped in a restyle.
    body = "".join([
        '<div class="page">',
        _header(model, embed_image, base_dir),
        _warnings(model),
        # --- the result -------------------------------------------------
        # Verdict FIRST, then the numbers that substantiate it. This is the
        # user's explicit call, asked twice: the bucket is the claim the
        # report makes, and a brand manager opening it should not have to
        # scroll to find out what it says.
        _verdict_block(model),
        _numbers(model),
        # Still the result beat: the numbers above are the in-target slice,
        # this is everyone. It follows them because it reframes them — you
        # need to have read "2 of 18" before "and here is the other 81".
        _panel_table(model),
        # --- the diagnosis ----------------------------------------------
        _diagnosis_overview(model),
        # --- the problems -----------------------------------------------
        _pains(model),
        # --- the solutions ----------------------------------------------
        # _bets before _fixes: the ranked lever list is the summary, _fixes is
        # the detail behind it. They are both prescription and must stay
        # adjacent — _bets' heading is decision-keyed copy written as a
        # call-to-action ("TO GET A TRUSTWORTHY READ:" on INCONCLUSIVE), so
        # separating them reads as two competing fixes sections.
        _bets(model),
        _fixes(model),
        # --- the extras -------------------------------------------------
        _strengths(model),
        _context(model),
        _voice(model),
        _notes(model),
        _footer(model),
        "</div>",
    ])
    head = f"<title>{_e(title)}</title>\n<style>{_CSS}</style>\n"
    if not full_document:
        return head + body
    return (f"<!doctype html>\n<html lang=\"en\">\n<head>\n"
            f'<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f"{head}</head>\n<body>\n{body}\n</body>\n</html>\n")
