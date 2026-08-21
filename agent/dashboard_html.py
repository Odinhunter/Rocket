"""dashboard_html — the Creative Read as the product dashboard.

The visual design is the user's, produced in Claude Design and kept at
`docs/Claude design/Rocket Report.dc.html`. This module is that design rebuilt
against `ReadModel`: same palette, same section order, same components. It is
NOT a restyle of the renderer it replaced (`agent/report_html.py`, deleted —
`git show 298b60e:agent/report_html.py` if you ever need to see it) and it is
not an interpretation: where the two disagree, the design wins on look and
`ReadModel` wins on data.

Three properties the design does not carry on its own, and this module must:

  * **Self-contained.** No external CSS, font, script or image request — the
    page renders identically served by the operator tool, opened from disk, or
    emailed. The design linked Google Fonts; that link is dropped (see
    `_FONT_STACK`). `tests/test_dashboard_html.py` pins this.
  * **Zero JavaScript.** Expanding a problem card is `<details>/<summary>`,
    not a click handler. The design's lightbox modal becomes an inline
    `<details>` for the same reason, and so does every card in the problem map
    (`_map_card`) — opening one lifts the two-line clamp on its lead and adds
    the rest of the pain underneath. A script tag would break the
    self-contained guarantee and the print/export path with it.
  * **Every guardrail, in one findable place.** The client artifact may curate
    which FINDINGS it shows; it may never DROP a guardrail. It may, and now
    does, COLLECT them — see the next paragraph.

⚠ **2026-08-04 — the guardrails moved. They were not removed, and this is the
user's explicit decision, taken with the finished page in front of them.**
Previously every qualifier rendered beside the thing it qualified: a warnings
strip above the result, a caveat under the decision chip, another under the
headline number, a third under the champion line, a fourth under the
outside-response bars, a fifth above the panel table, a NOT RANKED block inside
the fixes, and a methodology card. Eight interruptions, so a reader met a
qualification before they met a finding, and the page read as a product that
did not believe itself. They ALL now render inside `_how_it_was_made` —
collapsed, at the foot, complete, and inlined rather than linked so the
artifact stays self-contained.

**Do not reinstate any of them inline on a reviewer's instinct that a number
looks bare.** That is a decision the user makes, and reversing it is a flag
flip here, not a rebuild, precisely because `read_model` still computes every
one of them.

Guardrail → where it lives in this design:

  | guardrail                        | slot                                  |
  |----------------------------------|---------------------------------------|
  | VERDICT_CAVEAT                   | `_how_it_was_made` — keep-in-mind     |
  | HEADLINE_CAVEAT                  | `_how_it_was_made` — keep-in-mind     |
  | SEGMENT_CAVEAT                   | `_how_it_was_made` — keep-in-mind     |
  | OUT_OF_TARGET_ONLY_NOTE          | `_how_it_was_made`, only when the     |
  |                                  |   floor actually reordered something  |
  | F3 launch scope                  | `_how_it_was_made` — this-run row     |
  | panel degradation                | `_how_it_was_made` — this-run row     |
  | audience mismatch / coherence    | `_how_it_was_made` — this-run rows    |
  | methodology flags                | `_how_it_was_made` — this-run rows    |
  | provisional dispositions         | `_how_it_was_made` — how-it-was-run   |
  | why trust is DIRECTIONAL         | `_how_it_was_made` — how-it-was-run   |
  | brand-relative panel agreement   | `_how_it_was_made` — how-it-was-run   |
  | INCONCLUSIVE hides the rate      | the INCONCLUSIVE result card          |
  | INCONCLUSIVE hides the panel     | ADDED — the design showed it always   |
  | A3 research reported separately  | its own line under the headline       |
  | A4 per-cycle breakdown           | the purchase-cycle dots               |
  | A6 trust + note                  | the trust chip + line                 |
  | E3 model-inferred disclaimer     | the bordered block                    |
  | decoupling note                  | under the panel table (a FINDING —    |
  |                                  |   neutral tint, not the warning one)  |
  | panel denominator summary        | under the panel heading               |
  | breadth + traced evidence count  | the chip on both problem surfaces     |

⚠ **This page and the INTERNAL surfaces diverge on purpose.** The operator
console and `server/app.py`'s session export — the Track-2 artifact that lands
beside a contact's real CTR/ROAS — keep every qualifier inline, because they
are how we find out whether the instrument works. Stripping one there would
corrupt our evidence rather than our presentation. Tests pin the divergence in
BOTH directions so neither side gets "fixed" into matching the other.

Everything rendered comes from `ReadModel`. Never reach past it into raw run
JSON: the model is where the guardrails live, and going around it is how a
client-facing page quietly loses one.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from agent.artifact_pack import market_name_for
from agent.vectors import disposition_display, readable_identifiers
from agent.read_model import (
    FUNNEL_STAGE_ORDER, HEADLINE_CAVEAT, OUT_OF_TARGET_ONLY_NOTE,
    SEGMENT_CAVEAT, VERDICT_CAVEAT, Glance, ReadModel, client_pain_text,
    humanize,
)

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
}

# The design specifies Instrument Sans, loaded from Google Fonts. That link is
# dropped — a page that must render identically from disk cannot depend on a
# network request — and the real face is EMBEDDED instead, as a base64 data URI
# built from the woff2 files in agent/fonts/. ~53KB per page, licence-clean
# (SIL OFL 1.1; the licence ships beside the files at agent/fonts/OFL.txt).
# The system faces stay behind it: they still carry the glyphs Instrument Sans
# has no coverage for, e.g. the Devanagari that shows up in persona verbatims.
_FONT_STACK = ('"Instrument Sans",system-ui,-apple-system,"Segoe UI",Roboto,'
               '"Helvetica Neue",Arial,sans-serif')
_MONO = 'ui-monospace,Menlo,"SF Mono","Cascadia Code",Consolas,monospace'

_FONT_DIR = Path(__file__).parent / "fonts"

# Google's own subsets of the Instrument Sans variable face, with their
# unicode-ranges copied verbatim from the css2 response they came from.
#
# The ranges are NOT decoration. Two faces share one family/weight/style here,
# so with the ranges removed the last one declared wins outright and every
# ASCII character falls through to the system stack — a page that looks subtly
# wrong and errors nowhere.
#
# What each subset actually contains, read out of the cmap rather than assumed
# from the range it declares — a range is the subset's DEFINITION, not a
# promise that the glyph exists:
#
#   latin (208 glyphs)  — everything real reports use today, verified against
#                         the character inventory of all 56 runs on disk:
#                         ASCII plus · × é – — “ ” … ™ −
#   latin-ext (123)     — accented Latin only (ā ł ş …). NONE of it appears in
#                         any report so far; it ships as insurance, because the
#                         day one accented name lands in a persona verbatim the
#                         alternative is a typeface change mid-word. 14KB.
#
# NOT in either, so they render in the reader's fallback face: ₹ (U+20B9 — the
# font has no rupee glyph at all, in any subset), → ↔ ▴ ▾, and the Devanagari
# that turns up in verbatims. Checked on screen at body and display size: the
# macOS fallback sits with Instrument Sans without reading as an island.
_FONT_SUBSETS = (
    ("InstrumentSans-latin-ext.woff2",
     "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,"
     "U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,"
     "U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"),
    ("InstrumentSans-latin.woff2",
     "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,"
     "U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,"
     "U+FEFF,U+FFFD"),
)


def _font_faces() -> str:
    """The @font-face block, with the face bytes inlined as data URIs.

    A missing file raises at import rather than degrading quietly: the whole
    failure mode of an embedded font is that the page still renders, just not
    in the typeface it was designed in, and nothing downstream can notice.
    No font-display — there is nothing to fetch, so there is no swap period.
    """
    faces = []
    for name, ranges in _FONT_SUBSETS:
        b64 = base64.b64encode((_FONT_DIR / name).read_bytes()).decode("ascii")
        faces.append(
            '@font-face{font-family:"Instrument Sans";font-style:normal;'
            'font-weight:400 700;font-stretch:100%;'
            f'src:url(data:font/woff2;base64,{b64}) format("woff2");'
            f'unicode-range:{ranges}}}'
        )
    return "\n".join(faces)


_FONT_FACES = _font_faces()

# The five funnel stages, in the order a buyer moves through them, with the
# tapering pill widths the design gives them. Sourced from read_model so a
# stage added to the schema cannot go missing from the map — that exact bug
# (a renderer with four stages against a schema with five) silently dropped
# every `recall` pain from the funnel row once already.
_PILL_W = ("158px", "142px", "126px", "110px", "94px")

# Glance colours by ACTION, not by position. The design keyed them off the
# index of the filtered segment list, which re-colours every bar as soon as a
# run has a different action mix — the same segment would be grey on one report
# and green on the next.
_SEG_COLOR = {
    "scroll_past": "var(--baridle)",
    "linger": "var(--barmid)",
    "seek_info": "var(--barmid)",
    "save": "var(--accent)",
    "share": "var(--accent)",
    "tap_cta": "var(--accent)",
}

# The panel table's fixed action columns, per the design. Any action outside
# this set would be invisible in the table, so it is reported underneath rather
# than dropped, and tests/test_dashboard_html.py fails loudly on one.
_PANEL_ACTION_COLUMNS = ("scroll_past", "linger", "save")

# Above this many people in a purchase-cycle row the dot matrix stops being
# readable and starts being a wall. The count beside it is the actual datum;
# the dots are an illustration of it, so they are what gives way.
_MAX_CYCLE_DOTS = 40


def _e(text: object) -> str:
    """Escape for HTML text. Everything model-generated goes through here —
    an LLM-authored pain or quote can contain < > &.

    ⭐⭐ AND SINCE EVERYTHING MODEL-GENERATED GOES THROUGH HERE, THIS IS ALSO
    WHERE ENGINE IDENTIFIERS STOP. The L2/L4 models are handed raw disposition
    labels and write them into their own prose — measured across 47 runs on
    2026-08-22, in `prevalence`, `bet_ranking`, `why`, `pain`, `change` and
    `quote`. The customer's methodology block read "Widespread across
    aspirant_cafe_culture and loyalist_starbucks_regular in every context".

    ⚠ THE PREVIOUS FIXES IN THIS CLASS ALL WENT TO ONE CALL SITE EACH, which is
    why the defect kept reappearing on a surface nobody had a failing test for.
    All 64 `_e()` call sites are visible text — spans and divs, never an id,
    class or data- attribute — so one substitution here covers every rendered
    surface at once, including ones added later.

    ⚠ Only a KNOWN STANCE followed by an underscore is rewritten, so the
    ordinary word "loyalist" in a sentence is untouched."""
    return html.escape(
        readable_identifiers(str(text if text is not None else "")), quote=True
    )


def _data_uri(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    mime = _MIME.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _sentence_case(text: str) -> str:
    """`health_wellness_nutrition` → `Health wellness nutrition`. Underscores
    out, first letter up, nothing else invented."""
    t = humanize(text or "").strip()
    return (t[:1].upper() + t[1:]) if t else ""


def _split_lead(text: str) -> tuple[str, str]:
    """Split an authored pain into its first sentence and the remainder.

    Always a clean sentence boundary — never a word-count clip. The previous
    renderer clipped the lead at 22 words, which cut 4 of 6 real pains
    mid-clause ("…and largely already uses — so…") and then repeated the whole
    text from the beginning in the body underneath. Here the lead is a
    complete sentence, the body is strictly what follows it, and the map view
    shortens it with CSS instead of with scissors.
    """
    text = (text or "").strip()
    for i in range(len(text) - 1):
        # A sentence end: '.' followed by a space and a capital or quote.
        # Avoids splitting on decimals, 'e.g.', or an abbreviation mid-line.
        if text[i] == "." and text[i + 1] == " " and i + 2 < len(text):
            nxt = text[i + 2]
            if nxt.isupper() or nxt in "“\"'":
                return text[: i + 1].strip(), text[i + 2:].strip()
    return text, ""


# ---- the design's palette ------------------------------------------------

_TOKENS_LIGHT = """
--bg:#edebe6;--card:#fff;--card2:#faf9f7;--ink:#17181a;--body:#26282c;
--txt:#3c3e43;--soft:#55585e;--muted:#6b6f76;--faint:#8a8d94;--ghost:#b0b3b9;
--line:#eceae5;--line2:#e7e5e0;--chipbg:#f1f0ec;--shadow:0 1px 3px rgba(0,0,0,.05);
--accent:#0f8a6d;--accent-deep:#0b6b55;--accent-tint:#e8f2ee;--accent-line:#dcebe4;
--warnbg:#fdf6e9;--warnline:#f0e0bd;--warntag:#92400e;
--execbg:#fffdf7;--execline:#f0e3c8;--exectag:#92400e;--exectagbg:#fdeeca;
--structstripe:repeating-linear-gradient(135deg,#f3f3f5 0px,#f3f3f5 6px,#ececef 6px,#ececef 7px);
--structline:#dedfe4;--structtag:#3f4653;--structtagbg:#dfe2e8;
--quotebg:#faf9f6;--quoteline:#eceae3;--baridle:#e9e7e1;--barmid:#82c3b1;
--outsidebar:#efede8;--spine:#e3e1dc;--pillbd:#e0ded8;--loadring:#17181a;
--onload:#fff;--danger:#b91c1c;--dangerbg:#fdecec;
"""

_TOKENS_DARK = """
--bg:#131416;--card:#1d1f23;--card2:#191b1e;--ink:#ececea;--body:#dededb;
--txt:#c9cac6;--soft:#aaabaa;--muted:#96979a;--faint:#7f8287;--ghost:#63666c;
--line:#2c2e33;--line2:#33363c;--chipbg:#2a2c31;--shadow:0 1px 3px rgba(0,0,0,.4);
--accent:#37b393;--accent-deep:#52c8a8;--accent-tint:#143229;--accent-line:#1d4237;
--warnbg:#282214;--warnline:#4a3c20;--warntag:#e0a45c;
--execbg:#242019;--execline:#453a21;--exectag:#e8b46a;--exectagbg:#3d331d;
--structstripe:repeating-linear-gradient(135deg,#232529 0px,#232529 6px,#2b2d32 6px,#2b2d32 7px);
--structline:#3a3d44;--structtag:#b9bfc9;--structtagbg:#333841;
--quotebg:#212327;--quoteline:#2e3035;--baridle:#32343a;--barmid:#3d7c6a;
--outsidebar:#26282c;--spine:#2e3036;--pillbd:#33363c;--loadring:#ececea;
--onload:#131416;--danger:#f87171;--dangerbg:#2a1717;
"""

# The decision's own colour. Set on the wrapper, not on <body>, so a fragment
# embedded in someone else's document still colours its own chip.
_DECISION_BG = {
    "SCALE": "#15803d", "ITERATE": "#b45309", "RETARGET": "#1e56c2",
    "REBUILD": "#b91c1c", "INCONCLUSIVE": "#475569",
}

# LIGHT IS THE DELIVERABLE. The read renders light for everyone, whatever the
# reader's OS is set to — this page is handed to a brand manager, and a client
# artifact that looks like a different document on their laptop than it did on
# ours is not a deliverable, it is a variable. Light is also the design's own
# primary. The dark palette above is Claude Design's and is KEPT, but it is
# opt-in via data-theme="dark" on <html>, never automatic.
_CSS = f"""
{_FONT_FACES}
*{{box-sizing:border-box}}
body{{margin:0;background:#edebe6}}
:root[data-theme="dark"] body{{background:#131416}}

.rk{{{_TOKENS_LIGHT}
  font-family:{_FONT_STACK};color:var(--ink);background:var(--bg);
  min-height:100vh;font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}}
:root[data-theme="dark"] .rk{{{_TOKENS_DARK}}}
{"".join(f'.rk[data-decision="{k}"]{{--decbg:{v}}}' for k, v in _DECISION_BG.items())}
.rk{{--decbg:#475569}}

.rk-top{{height:56px;background:var(--card);border-bottom:1px solid var(--line2);
  display:flex;align-items:center;gap:20px;padding:0 20px;position:sticky;top:0;z-index:30}}
.rk-brand{{display:flex;align-items:center;gap:9px;width:200px}}
.rk-mark{{width:13px;height:13px;background:var(--accent);border-radius:3px;transform:rotate(45deg)}}
.rk-name{{font-size:15.5px;font-weight:700;letter-spacing:-.01em}}
.rk-search{{flex:1;max-width:340px;background:var(--chipbg);border-radius:8px;
  padding:8px 13px;font-size:12.5px;color:var(--faint)}}
.rk-acct{{margin-left:auto;display:flex;align-items:center;gap:8px}}
.rk-avatar{{width:30px;height:30px;border-radius:50%;background:var(--accent-tint);
  color:var(--accent-deep);font-size:11.5px;font-weight:700;display:flex;
  align-items:center;justify-content:center}}

.rk-body{{display:flex;align-items:flex-start}}
.rk-side{{width:212px;flex:none;position:sticky;top:56px;height:calc(100vh - 56px);
  background:var(--card);border-right:1px solid var(--line2);padding:16px 12px;
  display:flex;flex-direction:column;gap:2px}}
.rk-nav{{color:var(--soft);font-size:13px;padding:9px 12px;border-radius:8px}}
.rk-nav.on{{background:var(--accent-tint);color:var(--accent-deep);font-weight:600}}
.rk-main{{flex:1;min-width:0;padding:26px 32px 60px}}
.rk-col{{max-width:1080px;margin:0 auto;display:flex;flex-direction:column;gap:14px}}
@media (max-width:900px){{
  .rk-side{{display:none}}
  .rk-main{{padding:18px 14px 48px}}
}}

.rk-card{{background:var(--card);border:1px solid var(--line2);border-radius:12px;
  box-shadow:var(--shadow);padding:22px 26px 26px}}
.rk-k{{font-size:10px;font-weight:700;letter-spacing:.09em;color:var(--faint)}}
.rk-hr{{height:1px;background:var(--line);margin:18px 0;border:0}}
.rk-chip{{font-size:9.5px;font-weight:700;letter-spacing:.05em;border-radius:999px;
  padding:2px 8px;white-space:nowrap}}
.rk-id{{font-family:{_MONO};font-size:10.5px;font-weight:700;color:var(--soft);
  background:var(--chipbg);border-radius:5px;padding:2px 7px}}
.rk-num{{font-variant-numeric:tabular-nums}}

/* run header */
.rk-head{{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}}
.rk-thumb{{width:120px;height:120px;flex:none;border-radius:10px;overflow:hidden;
  border:1px solid var(--line2);background:var(--card2);display:block}}
.rk-thumb img{{width:100%;height:100%;object-fit:cover;display:block}}
.rk-zoom{{flex:none}}
.rk-zoom>summary{{list-style:none;cursor:zoom-in}}
.rk-zoom>summary::-webkit-details-marker{{display:none}}
.rk-big{{margin-top:12px;max-width:420px;border-radius:10px;border:1px solid var(--line2);display:block}}
.rk-asset{{font-size:17px;font-weight:600;letter-spacing:-.01em}}
.rk-meta{{margin-top:5px;font-size:12.5px;color:var(--muted)}}
.rk-lbl{{font-weight:700;color:var(--faint);font-size:10px;letter-spacing:.07em}}
.rk-export{{background:var(--accent);color:#fff;font-size:12.5px;font-weight:600;
  padding:8px 16px;border-radius:8px;display:inline-block}}
.rk-runid{{font-family:{_MONO};font-size:9.5px;color:var(--ghost);max-width:170px;
  word-break:break-all;text-align:right;line-height:1.5}}

/* warnings */
.rk-warn{{background:var(--warnbg);border:1px solid var(--warnline);border-radius:12px}}
.rk-warn>div{{display:flex;gap:12px;padding:11px 18px;align-items:baseline}}
.rk-warn>div+div{{border-top:1px solid var(--warnline)}}
.rk-warn .t{{flex:none;font-size:9px;font-weight:700;letter-spacing:.06em;
  color:var(--warntag);width:128px}}
.rk-warn .x{{font-size:12.5px;line-height:1.55;color:var(--txt)}}
@media (max-width:640px){{.rk-warn>div{{flex-direction:column;gap:3px}}.rk-warn .t{{width:auto}}}}

/* result */
.rk-dec{{background:var(--decbg);color:#fff;font-size:12px;font-weight:700;
  letter-spacing:.08em;padding:6px 13px;border-radius:8px}}
.rk-tag{{font-size:13.5px;font-weight:500;color:var(--txt);line-height:1.4}}
.rk-sub{{margin-top:10px;font-size:12px;line-height:1.5;color:var(--muted)}}
.rk-headline{{font-size:23px;font-weight:600;line-height:1.3;letter-spacing:-.01em;
  font-variant-numeric:tabular-nums;text-wrap:pretty}}
.rk-under{{margin-top:8px;font-size:13px;line-height:1.55;color:var(--soft)}}
.rk-bar{{display:flex;height:26px;border-radius:7px;overflow:hidden;margin-top:10px}}
.rk-legend{{display:flex;gap:18px;margin-top:8px;font-size:12px;color:var(--soft);
  flex-wrap:wrap;font-variant-numeric:tabular-nums}}
.rk-legend span{{display:inline-flex;align-items:center;gap:6px}}
.rk-swatch{{width:9px;height:9px;border-radius:3px}}
.rk-two{{display:grid;grid-template-columns:1fr 1fr;gap:28px}}
@media (max-width:720px){{.rk-two{{grid-template-columns:1fr;gap:20px}}}}
.rk-row{{display:flex;justify-content:space-between;align-items:baseline;
  margin-top:9px;font-size:13px}}
.rk-dot{{width:9px;height:9px;border-radius:50%;border:1.5px solid var(--ghost)}}
.rk-dot.on{{border-color:var(--ink);background:var(--ink)}}

/* problem map */
.rk-map{{display:grid;grid-template-columns:1fr 180px 1fr;margin-top:14px}}
.rk-zone{{font-size:10px;font-weight:700;letter-spacing:.08em;padding-bottom:10px}}
.rk-stage{{background:linear-gradient(var(--spine),var(--spine)) center/2px 100% no-repeat;
  display:flex;align-items:center;justify-content:center;padding:9px 0}}
.rk-pill{{background:var(--card);border:1px solid var(--pillbd);border-radius:999px;
  padding:6px 0;text-align:center;box-shadow:var(--shadow)}}
.rk-pill.clear{{background:var(--card2);border-style:dashed;padding:5px 0;box-shadow:none}}
.rk-spur{{width:16px;height:2px;background:var(--spine);flex:none}}
.rk-pcard{{border-radius:9px;padding:8px 10px;overflow:hidden}}
.rk-pcard>summary{{list-style:none;cursor:pointer}}
.rk-pcard>summary::-webkit-details-marker{{display:none}}
.rk-clamp{{margin-top:4px;font-size:11px;line-height:1.4;max-height:2.8em;overflow:hidden;
  -webkit-mask-image:linear-gradient(180deg,#000 55%,rgba(0,0,0,0) 96%);
  mask-image:linear-gradient(180deg,#000 55%,rgba(0,0,0,0) 96%)}}
/* Opening a map card has to LIFT the clamp, not just reveal a second block.
   Every authored lead on disk runs past two lines (shortest is 121 chars), so
   without this the card expands and its first sentence is still cut off — a
   half-fix that a test asserting only "the card is a <details>" would pass. */
details[open]>summary .rk-clamp{{max-height:none;
  -webkit-mask-image:none;mask-image:none}}
.rk-pcard .detail{{margin-top:7px;padding-top:7px;border-top:1px solid var(--pillbd);
  font-size:10.5px;line-height:1.5;color:var(--soft);text-wrap:pretty}}
.rk-maplegend{{display:flex;gap:18px;margin-top:14px;font-size:11px;color:var(--muted);
  align-items:center;flex-wrap:wrap}}
.rk-maplegend span{{display:inline-flex;align-items:center;gap:6px}}
@media (max-width:820px){{
  .rk-map{{grid-template-columns:1fr}}
  .rk-map .rk-stage{{background:none;justify-content:flex-start;padding:14px 0 6px}}
  .rk-map .rk-spur{{display:none}}
  .rk-zone{{padding-top:10px}}
}}

/* problem cards */
.rk-prob{{border-radius:11px;box-shadow:var(--shadow);overflow:hidden}}
.rk-prob>summary{{list-style:none;cursor:pointer;padding:14px 18px}}
.rk-prob>summary::-webkit-details-marker{{display:none}}
.rk-prob .hd{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.rk-prob .lead{{margin-top:8px;font-size:13.5px;line-height:1.5;max-width:880px;
  text-wrap:pretty}}
.rk-more{{font-size:11px;color:var(--accent);font-weight:600;white-space:nowrap}}
/* Scoped to `details`, not to one component: the extras band uses the same
   affordance, and a rule keyed to .rk-prob left it showing "Show" and "Hide"
   side by side. The child combinator keeps an open card from flipping the
   label of a closed disclosure nested inside it. */
details[open]>summary .shut{{display:none}}
details:not([open])>summary .opened{{display:none}}
.rk-prob .detail{{padding:0 18px 16px}}
.rk-quote{{background:var(--quotebg);border:1px solid var(--quoteline);border-radius:9px;
  padding:10px 14px;margin-top:10px}}
.rk-quote .q{{font-size:12.5px;line-height:1.55;color:var(--txt)}}
.rk-quote .a{{margin-top:5px;font-size:11px;color:var(--faint)}}

/* fixes */
.rk-lever{{display:flex;gap:12px;align-items:baseline;margin-top:9px}}
.rk-levern{{flex:none;width:20px;height:20px;border-radius:50%;background:var(--accent-tint);
  color:var(--accent-deep);font-size:11px;font-weight:700;display:flex;
  align-items:center;justify-content:center;transform:translateY(3px)}}
.rk-fix{{border:1px solid var(--line2);border-radius:10px;padding:13px 16px;margin-top:10px}}
.rk-fix .ch{{font-size:13px;line-height:1.55;color:var(--body);text-wrap:pretty}}
.rk-why{{margin-top:10px}}
.rk-why>summary{{list-style:none;cursor:pointer;font-size:11px;font-weight:600;
  color:var(--accent)}}
.rk-why>summary::-webkit-details-marker{{display:none}}
.rk-why .x{{margin-top:8px;font-size:12.5px;line-height:1.6;color:var(--soft)}}

/* how this read was made — collapsed, quiet, and the last thing on the page.
   Deliberately styled DOWN: it is complete and findable, not advertised. The
   summary is a plain sentence rather than a flag colour, because everything
   inside it used to be scattered up the page in warning tints and that is the
   look the user asked to be rid of. */
.rk-made>summary{{list-style:none;cursor:pointer;font-size:11px;font-weight:700;
  letter-spacing:.07em;text-transform:uppercase;color:var(--faint);
  display:flex;align-items:center;gap:7px}}
.rk-made>summary::-webkit-details-marker{{display:none}}
.rk-made>summary::after{{content:"▾";font-size:9px;transform:translateY(-1px)}}
.rk-made[open]>summary::after{{content:"▴"}}
.rk-made>summary:hover{{color:var(--muted)}}

/* what worked */
.rk-grid{{margin-top:12px;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.rk-won{{background:var(--accent-tint);border:1px solid var(--accent-line);
  border-radius:10px;padding:13px 15px}}

/* panel table */
.rk-tblwrap{{margin-top:12px;overflow-x:auto}}
.rk-tbl{{width:100%;border-collapse:separate;border-spacing:0;
  font-variant-numeric:tabular-nums;min-width:640px}}
.rk-tbl th{{font-size:9.5px;font-weight:700;letter-spacing:.07em;color:var(--faint);
  padding:6px 10px;text-align:right;white-space:nowrap}}
.rk-tbl th:first-child,.rk-tbl th:last-child{{text-align:left}}
.rk-tbl td{{padding:10px;border-top:1px solid var(--line);text-align:right;font-size:13px}}
.rk-tbl td:first-child,.rk-tbl td:last-child{{text-align:left}}
.rk-tbl tr.in td{{background:var(--accent-tint)}}
.rk-tbl tr.in td:first-child{{border-radius:8px 0 0 8px}}
.rk-tbl tr.in td:last-child{{border-radius:0 8px 8px 0}}
.rk-badge{{font-size:8.5px;font-weight:700;letter-spacing:.06em;color:#fff;
  background:var(--accent);border-radius:999px;padding:2px 7px;margin-left:8px}}

.rk-disc{{border:1.5px solid var(--ink);background:var(--card);border-radius:12px;
  padding:13px 18px;font-size:12.5px;line-height:1.6;color:var(--body);font-weight:500}}
.rk-method{{margin-top:10px;display:grid;grid-template-columns:150px 1fr;gap:7px 14px;
  font-size:12px;line-height:1.55;color:var(--soft)}}
.rk-method .k{{font-size:9.5px;font-weight:700;letter-spacing:.06em;color:var(--ghost);
  padding-top:2px}}
@media (max-width:640px){{.rk-method{{grid-template-columns:1fr;gap:2px 0}}
  .rk-method .k{{padding-top:10px}}}}
.rk-foot{{padding:6px 2px 0;display:flex;justify-content:space-between;
  align-items:baseline;gap:12px}}
.rk-foot span{{font-size:11px;color:var(--ghost)}}
"""


# The stylesheet the operator server's own pages borrow (console, intake,
# prediction capture, the blinded reveal). It is the design's palette exposed
# under the token names those pages already use, plus the handful of layout
# classes they render — so the tool a prospect watches being driven and the
# deliverable they are handed are visibly one product, rather than two
# stylesheets that drift apart. Style only: no report content, no guardrail.
PAGE_CSS = f"""
{_FONT_FACES}
:root{{
  --font-sans:{_FONT_STACK};--font-mono:{_MONO};
  --ground:#edebe6;--surface:#fff;--surface-2:#faf9f7;--ink:#17181a;
  --muted:#6b6f76;--faint:#8a8d94;--line:#e7e5e0;
  --accent:#0f8a6d;--accent-ink:#0b6b55;--accent-tint:#e8f2ee;
  --good:#0f8a6d;--good-tint:#e8f2ee;--leak:#b45309;--leak-tint:#fdf6e9;
  --on-accent:#fff;
  --shadow:0 1px 3px rgba(0,0,0,.05);--maxw:860px;
}}
/* Light by default here too, for the same reason as the report: the operator
   drives this in front of the contact, and the tool matching the deliverable
   is the point of sharing a stylesheet. Dark stays opt-in. */
:root[data-theme="dark"]{{--ground:#131416;--surface:#1d1f23;--surface-2:#191b1e;
  --ink:#ececea;--muted:#96979a;--faint:#7f8287;--line:#33363c;--accent:#37b393;
  --accent-ink:#52c8a8;--accent-tint:#143229;--good:#37b393;--good-tint:#143229;
  --leak:#e0a45c;--leak-tint:#282214;--on-accent:#08130f;
  --shadow:0 1px 3px rgba(0,0,0,.4);}}

*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--font-sans);
  font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}}
.page{{max-width:var(--maxw);margin:0 auto;padding:34px 22px 80px}}
.eyebrow{{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:var(--faint)}}
h1{{font-size:26px;line-height:1.18;margin:8px 0 0;font-weight:700;
  letter-spacing:-.015em;text-wrap:balance}}
h2{{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:var(--faint);margin:0}}
section{{margin-top:32px}}
section>h2{{margin-bottom:12px}}
p{{margin:0;color:var(--muted)}}
.lead{{color:var(--ink)}}
.sub{{margin-top:8px;color:var(--muted);font-size:13px;line-height:1.55}}
.warn{{margin-top:14px;background:var(--leak-tint);border:1px solid var(--line);
  border-radius:12px;padding:12px 16px;font-size:13px;color:var(--ink)}}
.warn b{{display:block;margin-bottom:4px;font-size:9px;font-weight:700;
  letter-spacing:.07em;text-transform:uppercase;color:var(--leak)}}
.warn--stop{{border-width:1.5px;border-color:var(--leak)}}
"""


# ---- components ---------------------------------------------------------


def _run_header(m: ReadModel, embed_image: bool, base_dir: Path) -> str:
    thumb = ""
    if embed_image and m.asset_path is not None:
        p = m.asset_path if m.asset_path.is_absolute() else base_dir / m.asset_path
        uri = _data_uri(p)
        if uri:
            # The design's click-to-enlarge lightbox, as a <details> — a modal
            # would need a script, and a script would cost the page its
            # self-contained guarantee.
            thumb = (
                f'<details class="rk-zoom"><summary>'
                f'<span class="rk-thumb"><img src="{uri}" alt="the creative under test">'
                f'</span></summary>'
                f'<img class="rk-big" src="{uri}" alt="the creative under test, enlarged">'
                f"</details>"
            )

    # ⚠ This is the run header — the first line under the ad, on every read.
    # `_sentence_case(m.category)` put "Fnb world" there. Found only by grepping
    # the RENDERED page after fixing the methodology block; the tests were green.
    bits = [b for b in (market_name_for(m.category),
                        (m.generated_at or "")[:10],
                        f"Panel — {m.panel_size} simulated consumers" if m.panel_size
                        else "") if b]

    job = (f'<span class="rk-chip" style="color:var(--soft);background:var(--chipbg)">'
           f'{_e(m.purpose_label.upper())}</span>' if m.purpose_label else "")

    targeting = ""
    if m.declared_targeting:
        targeting = (f'<div style="margin-top:12px;font-size:12px;color:var(--soft)">'
                     f'<span class="rk-lbl">DECLARED TARGETING&nbsp;&nbsp;</span>'
                     f"{_e(m.declared_targeting)}</div>")

    # The two-axis audience verdict, in both directions, and THE ONLY place it
    # renders. This is a finding about the creative, so it stays on the visible
    # page beside the targeting it contradicts — see `_run_qualifiers` for why
    # it is the one qualifier-shaped thing that did not move into the collapsed
    # block on 2026-08-04.
    aud = ""
    if m.audience_mismatch:
        aud = (f'<span class="rk-chip" style="color:var(--danger);'
               f'background:var(--dangerbg)">AUDIENCE MISMATCH</span>'
               f'<span style="font-size:12px;color:var(--muted);line-height:1.5">'
               f"{_e(m.audience_mismatch)}</span>")
    elif m.audience_aligned:
        aud = (f'<span class="rk-chip" style="color:var(--accent-deep);'
               f'background:var(--accent-tint)">AUDIENCE ALIGNED</span>'
               f'<span style="font-size:12px;color:var(--muted);line-height:1.5">'
               f"{_e(m.audience_aligned)}</span>")
    if aud:
        aud = ('<div style="margin-top:7px;display:flex;align-items:baseline;'
               f'gap:8px;flex-wrap:wrap">{aud}</div>')

    return f"""<div class="rk-card rk-head" style="padding:20px 24px">{thumb}
  <div style="flex:1;min-width:240px">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <span class="rk-asset">{_e(m.asset_label or 'Creative read')}</span>{job}
    </div>
    <div class="rk-meta">{_e(' · '.join(bits))}</div>{targeting}{aud}
  </div>
  <div style="flex:none;display:flex;flex-direction:column;align-items:flex-end;gap:10px">
    <span class="rk-export">Export</span>
    <span class="rk-runid">{_e(m.run_id)}</span>
  </div>
</div>"""


def _run_qualifiers(m: ReadModel) -> list[tuple[str, str]]:
    """This run's own qualifiers — the rows that used to be the warnings strip
    pinned above the result.

    ⚠ They are NO LONGER rendered above the result, or anywhere the page opens
    on them. The user's explicit decision, 2026-08-04, after reviewing the read
    end to end: a page that leads with five qualifications reads as a product
    that does not believe itself. They now render inside `_how_it_was_made`,
    collapsed, at the bottom.

    ⚠ Nothing is dropped and nothing stops being computed — this function is
    still the single place that enumerates them, and `read_model` still derives
    every field. The operator console and the session export (the Track-2
    artifact that lands beside real CTR/ROAS) are deliberately NOT changed:
    those are our own measuring instruments, and stripping a qualifier there
    would corrupt the evidence rather than the presentation.
    `tests/test_dashboard_html.py` pins that divergence in both directions.
    """
    rows: list[tuple[str, str]] = []
    # ⚠ `audience_mismatch` is deliberately NOT here, and its absence is the
    # one judgement call inside this change rather than a copy of it. A
    # mismatch is a FINDING ABOUT THE AD — "your creative reads as women 35-54
    # and you are buying men 18-24" — not a qualification of our own instrument,
    # which is what everything else in this list is. It keeps its chip in
    # `_run_header`, in full, beside the declared targeting it contradicts.
    # Repeating it down here would be the second copy of one statement, which
    # is the habit this whole change exists to break.
    if m.scope_note:                                   # F3
        rows.append(("HOW FAR TO TRUST IT", m.scope_note))
    if m.coherence_warning:                            # A7
        rows.append(("COHERENCE", m.coherence_warning))
    if m.panel_degraded:
        rows.append(("PANEL", m.panel_degraded))
    for line in m.flag_lines:
        rows.append(("METHOD", line))
    return rows


def _decision_head(m: ReadModel, trust_chip: bool) -> str:
    chip = ""
    if trust_chip and m.trust:
        border = ("1.5px solid var(--ink)" if m.trust == "HIGH"
                  else "1.5px dashed var(--ghost)")
        chip = (f'<span style="border:{border};color:var(--soft);font-size:10.5px;'
                f'font-weight:700;letter-spacing:.07em;padding:5px 10px;'
                f'border-radius:999px;white-space:nowrap">TRUST: {_e(m.trust)}</span>')
    return (f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
            f'<span class="rk-dec">{_e(m.decision_name)}</span>'
            f'<span class="rk-tag" style="flex:1">{_e(m.tagline)}</span>{chip}</div>')


def _result(m: ReadModel) -> str:
    """The decision, then the numbers that substantiate it.

    ⚠ The caveats that used to render in this card — VERDICT_CAVEAT under the
    chip, HEADLINE_CAVEAT under the number, SEGMENT_CAVEAT under the champion
    line — are GONE from the visible page by the user's explicit decision,
    2026-08-04, and this is not an oversight to fix. They were reviewed
    together and judged to read as an apology for the product rather than as
    honesty. Every one of them still exists: `read_model` computes them all
    unchanged, and they render inside `_how_it_was_made`, collapsed at the
    bottom of the page, plus on the standalone methodology page.

    ⚠ The buy-intent number KEEPS ITS POSITION here, caveat-free — also the
    user's explicit call, taken after being shown the measurement
    (`read_model.HEADLINE_CAVEAT`: same-ad re-runs move it as much as
    different ads do, signal-to-noise 1.0). It was put to them as a choice
    against leading with the problem map, which is the surface that measurably
    DOES discriminate, and they chose to keep the number leading. Do not
    re-litigate it in a restyle; do not quietly reinstate the caveat line.
    """
    # INCONCLUSIVE: the reasons, and never an action rate by any route.
    if m.is_inconclusive or m.headline is None:
        rest = "".join(
            f'<div class="rk-under">{_e(l.strip())}</div>'
            for l in m.inconclusive[1:]
        )
        first = _e(m.inconclusive[0].strip()) if m.inconclusive else ""
        return f"""<div class="rk-card">{_decision_head(m, trust_chip=False)}
  <hr class="rk-hr">
  <div style="font-size:21px;font-weight:600;line-height:1.35;letter-spacing:-.01em;
    text-wrap:pretty">{first}</div>{rest}
</div>"""

    # ⚠ `trust_note` no longer renders here. It read "treat as a lead, not a
    # verdict" directly beneath the decision — the single most self-undermining
    # sentence on the page — and it was ALREADY a duplicate: the collapsed
    # block's WHY DIRECTIONAL row states the same thing with the reason
    # attached. The trust CHIP stays, because a one-word quality signal is a
    # finding; the sentence apologising for it is not.
    out = [f'<div class="rk-card">{_decision_head(m, trust_chip=True)}']
    out.append('<hr class="rk-hr">')
    out.append(f'<div class="rk-headline">{_e(m.headline.strip())}</div>')
    if m.research_line:      # A3 — research reported separately, never as a sale
        out.append(f'<div class="rk-under">{_e(m.research_line)}</div>')
    if m.champion_line:
        # The single strongest between-segment claim the read makes — "right ad,
        # wrong person" — and the one that drives a RETARGET decision. It can
        # render on its own, far above the panel table that carries the same
        # caveat, so it gets its own copy rather than relying on the reader
        # scrolling to find the qualifier.
        out.append(f'<div class="rk-under">{_e(m.champion_line)}</div>')
    elif m.narrow_frame_line:
        out.append(f'<div class="rk-under">{_e(m.narrow_frame_line)}</div>')

    # the 2-second glance, in-target
    if m.glance.n:
        segs, legend = [], []
        for key, label, count, rate in m.glance.segments():
            color = _SEG_COLOR.get(key, "var(--accent)")
            segs.append(f'<div style="flex:{count};background:{color}"></div>')
            legend.append(f'<span><span class="rk-swatch" style="background:{color}">'
                          f"</span>{_e(label)} — {count}</span>")
        aria = ", ".join(f"{label.lower()} {count}"
                         for _, label, count, _ in m.glance.segments())
        out.append('<hr class="rk-hr">')
        out.append(
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<span class="rk-k">GLANCE RESPONSE — TARGET: '
            f'{_e(m.within_label.upper())}</span>'
            f'<span class="rk-k rk-num" style="font-size:11px">n={m.glance.n}</span></div>'
            f'<div class="rk-bar" role="img" aria-label="{_e(aria)}">{"".join(segs)}</div>'
            f'<div class="rk-legend">{"".join(legend)}</div>'
        )
        if m.outside_n:
            # Proportional, not a flat bar. The design drew one solid block
            # here because everyone outside the target scrolled past on the
            # run it was built from — but that is a property of that ad, not
            # of the format: outsiders out-responded the target on two of the
            # eight v3 runs. A bar that cannot show the difference would say
            # "nobody" on a run where 9% acted.
            segs = "".join(
                f'<div style="flex:{count};background:'
                f'{"var(--outsidebar)" if key == "scroll_past" else "var(--barmid)"}">'
                f"</div>"
                for key, _, count, _ in _outside_glance(m).segments()
            ) or '<div style="flex:1;background:var(--outsidebar)"></div>'
            out.append(
                f'<div style="margin-top:16px;display:flex;justify-content:space-between;'
                f'align-items:baseline"><span class="rk-k">EVERYONE ELSE</span>'
                f'<span class="rk-k rk-num" style="font-size:11px">n={m.outside_n}</span>'
                f"</div>"
                f'<div style="display:flex;height:12px;border-radius:6px;overflow:hidden;'
                f'margin-top:8px">{segs}</div>'
                f'<div class="rk-k rk-num" style="margin-top:6px;font-size:12px">'
                f'{_e(_outside_legend(m))}</div>'
            )

    next_rows = m.panel.next_steps_in_target()
    if next_rows or m.cycle_rows:
        out.append('<hr class="rk-hr">')
        out.append('<div class="rk-two">')
        out.append(_next_steps_col(next_rows))
        out.append(_cycle_col(m))
        out.append("</div>")
    out.append("</div>")
    return "".join(out)


def _outside_glance(m: ReadModel) -> Glance:
    """The action mix of everyone NOT in the target, pooled.

    Kept strictly separate from `m.glance`, which is the target's. Pooling the
    two is the mistake that has cost this project a rebuild twice: 81 outside
    against 19 inside means the pooled bar is the outside bar with rounding.
    """
    g = Glance()
    for t in m.panel.out_types:
        for action, count in t.glance.counts.items():
            g.add(action, count)
    return g


def _outside_legend(m: ReadModel) -> str:
    """What the people outside the target did, in one line. Counted, not
    assumed: 'everyone scrolled' is true on most runs and false on TWT and
    ProSki, where the outsiders out-responded the target."""
    n = m.outside_n
    engaged = sum(t.engaged for t in m.panel.out_types)
    if not engaged:
        return f"Scrolled past — {n} of {n}"
    return f"{engaged} of {n} did something other than scroll past"


def _next_steps_col(rows) -> str:
    if not rows:
        return "<div></div>"
    body = "".join(
        f'<div class="rk-row"><span style="color:var(--txt)">{_e(label)}</span>'
        f'<span class="rk-num" style="font-weight:600;color:'
        f'{"var(--faint)" if key == "nothing" else "var(--ink)"}">{n} of {denom}</span>'
        f"</div>"
        for key, label, n, denom in rows
    )
    return f'<div><div class="rk-k">NEXT STEP — IN TARGET</div>{body}</div>'


def _cycle_col(m: ReadModel) -> str:
    """A4 — the per-cycle breakdown that accompanies the blended headline, so
    the headline never hides its cycle-mix assumption."""
    if not m.cycle_rows:
        return "<div></div>"
    rows = []
    for r in m.cycle_rows:
        denom, num = int(r["denom"]), int(r["num"])
        dots = ""
        if denom <= _MAX_CYCLE_DOTS:
            dots = "".join(
                f'<span class="rk-dot{" on" if i < num else ""}"></span>'
                for i in range(denom)
            )
        rows.append(
            f'<div style="display:flex;align-items:center;gap:10px;margin-top:9px">'
            f'<span style="font-size:13px;color:var(--txt);width:92px">'
            f'{_e(r["label"].capitalize())}</span>'
            f'<span style="display:flex;gap:3px;flex-wrap:wrap">{dots}</span>'
            f'<span class="rk-num" style="margin-left:auto;font-size:12.5px;'
            f'font-weight:600">{num} of {denom}</span></div>'
        )
    label = m.purpose_metric_label.upper() if m.purpose_metric_label else "WOULD ACT"
    # A4 is not the rows alone — it is the rows plus the reason they are there.
    # The headline blends them at whatever cycle mix the panel happened to
    # sample, and a reader who doesn't know that reads the blend as a property
    # of the ad rather than of the sample.
    return (f'<div><div class="rk-k">PURCHASE CYCLE — {_e(label)}</div>'
            f'{"".join(rows)}'
            f'<div style="margin-top:10px;font-size:11px;line-height:1.5;'
            f'color:var(--faint)">The headline above blends these at the panel\'s '
            f'sampled cycle mix — read the rows, not just the blend.</div></div>')


# ---- the problem map — the hero of the page ------------------------------


def _marker(p, m: ReadModel) -> dict:
    """The visual state of one problem: execution vs structural, load-bearing
    or not, in or out of target. Shared by the map and the cards so the two
    can never disagree about what a problem is.

    `types` is composed by `ReadModel.breadth_line`, not here: it carries a
    denominator and an evidence count that are model decisions, and a renderer
    that writes its own version of that string is how a surface drifts from the
    read model that owns it."""
    exec_ = (p.severity or "").lower() != "structural"
    return {
        "sev_label": (p.severity or "").upper(),
        "sev_col": "var(--exectag)" if exec_ else "var(--structtag)",
        "sev_bg": "var(--exectagbg)" if exec_ else "var(--structtagbg)",
        "card_bg": "var(--execbg)" if exec_ else "var(--structstripe)",
        "card_line": "var(--execline)" if exec_ else "var(--structline)",
        "types": m.breadth_line(p),
    }


def _map_card(p, m: ReadModel, load_bearing: str, small: bool) -> str:
    mk = _marker(p, m)
    border = ("1.5px solid var(--loadring)" if p.id == load_bearing
              else f"1px solid {mk['card_line']}")
    lb = ('<span class="rk-chip" style="color:var(--onload);background:var(--loadring);'
          'font-size:9px;padding:1px 7px">LOAD-BEARING</span>'
          if p.id == load_bearing else "")
    lead, rest = _split_lead(client_pain_text(p.pain))
    # 17 of the 99 authored pains on disk are a single sentence. Those cards
    # still open — the lead itself is clamped to two lines and every lead is
    # longer than that — but they must not emit an empty detail block, which
    # renders as a visible empty box under a rule and a bare separator.
    detail = f'<div class="detail">{_e(rest)}</div>' if rest.strip() else ""
    return (
        f'<details class="rk-pcard" style="border:{border};'
        f'background:{mk["card_bg"]}"><summary>'
        f'<div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap">'
        f'<span class="rk-id" style="font-size:10px;padding:1px 5px">{_e(p.id)}</span>'
        f'<span class="rk-chip" style="color:{mk["sev_col"]};background:{mk["sev_bg"]};'
        f'font-size:9px;padding:1px 7px">{_e(mk["sev_label"])}</span>{lb}'
        f'<span style="font-size:9.5px;color:var(--faint)">{_e(mk["types"])}</span>'
        f'<span class="rk-more" style="margin-left:auto;font-size:9.5px">'
        f'<span class="shut">More ▾</span>'
        f'<span class="opened">Less ▴</span></span></div>'
        f'<div class="rk-clamp" style="font-size:{"10.5px" if small else "11px"};'
        f'color:{"var(--muted)" if small else "var(--txt)"}">{_e(lead)}</div>'
        f'</summary>{detail}</details>'
    )


def _problem_map(m: ReadModel) -> str:
    """Where the problems sit in the funnel, split by whether they hit the
    audience being bought.

    This is the hero of the page, and deliberately so. The headline number
    cannot be: under v3 buy-intent reads 0% on six of the last eight runs, and
    a tile that says 0% every time cannot lead. What actually differs between
    a good read and a bad one is the shape of the diagnosis — which stage
    leaks, whether it is fixable in the creative, and whether it lands on the
    people being bought. That is this grid.

    The left/right split is the rule that has cost this project the most: on a
    narrow ad the out-of-target majority swamps the signal, so a pooled map
    would show a wall of problems for a creative that worked exactly as aimed.
    """
    ov = m.diagnosis
    if ov.is_empty:
        return ""
    pains = list(m.report.pain_map)
    load_bearing = (m.report.decision.load_bearing_pain_id
                    if m.report.decision else "") or ""

    counts = (f"{ov.total} problem{'' if ov.total == 1 else 's'} — "
              f"{ov.within} within target · {ov.outside} outside · "
              f"{ov.execution} execution · {ov.structural} structural")

    # Every stage the schema knows, plus any this build doesn't recognise —
    # sorted last rather than dropped, because an unknown stage is a reporting
    # gap, not a licence to under-report where a creative leaks.
    stages = list(FUNNEL_STAGE_ORDER) + [
        s for s in ov.stages if s not in FUNNEL_STAGE_ORDER]

    cells = []
    for i, stage in enumerate(stages):
        at = [p for p in pains if (p.funnel_stage or "").lower() == stage]
        within = [p for p in at if p.within_target]
        outside = [p for p in at if not p.within_target]
        width = _PILL_W[i] if i < len(_PILL_W) else _PILL_W[-1]

        left = "".join(_map_card(p, m, load_bearing, small=False) for p in within)
        right = "".join(_map_card(p, m, load_bearing, small=True) for p in outside)

        if at:
            n = len(at)
            pill = (f'<div class="rk-pill" style="width:{width}">'
                    f'<div style="font-size:11.5px;font-weight:600">'
                    f'{_e(stage.capitalize())}</div>'
                    f'<div class="rk-num" style="font-size:9.5px;color:var(--faint)">'
                    f'{n} problem{"" if n == 1 else "s"}</div></div>')
        else:
            # A stage with nothing wrong reads "Clear" — it must not vanish, or
            # the funnel silently loses a stage a creative can leak at.
            pill = (f'<div class="rk-pill clear" style="width:{width}">'
                    f'<div style="font-size:11px;font-weight:600;color:var(--faint)">'
                    f'{_e(stage.capitalize())}</div>'
                    f'<div style="font-size:9.5px;color:var(--accent);font-weight:600">'
                    f"Clear</div></div>")

        cells.append(
            f'<div style="display:flex;justify-content:flex-end;align-items:center;'
            f'padding:9px 0">'
            f'<div style="display:flex;flex-direction:column;gap:6px;max-width:330px;'
            f'min-width:0">{left}</div>'
            + (f'<div class="rk-spur"></div>' if within else "") + "</div>"
            f'<div class="rk-stage">{pill}</div>'
            f'<div style="display:flex;justify-content:flex-start;align-items:center;'
            f'padding:9px 0">'
            + (f'<div class="rk-spur"></div>' if outside else "")
            + f'<div style="display:flex;flex-direction:column;gap:6px;max-width:300px;'
              f'min-width:0">{right}</div></div>'
        )

    return f"""<div class="rk-card" style="padding:22px 26px 24px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;
    flex-wrap:wrap;gap:6px">
    <span class="rk-k">PROBLEM MAP</span>
    <span class="rk-num" style="font-size:12px;color:var(--soft)">{_e(counts)}</span>
  </div>
  <div class="rk-map">
    <div class="rk-zone" style="color:var(--soft);text-align:right;padding-right:16px"
      >WITHIN TARGET — {m.target_n} OF {m.panel.panel_n or m.panel_size}</div>
    <div></div>
    <div class="rk-zone" style="color:var(--faint);padding-left:16px"
      >OUTSIDE — {m.outside_n} OF {m.panel.panel_n or m.panel_size}</div>
    {''.join(cells)}
  </div>
  <div class="rk-maplegend">
    <span><span class="rk-swatch" style="background:var(--exectagbg);border:1px solid
      var(--execline)"></span>Execution — fixable in the creative</span>
    <span><span class="rk-swatch" style="background:var(--structstripe);border:1px solid
      var(--structline)"></span>Structural — no creative tweak fixes it</span>
    <span><span class="rk-swatch" style="border:1.5px solid var(--loadring)"
      ></span>Load-bearing</span>
  </div>
</div>"""


def _quotes(quotes) -> str:
    out = []
    for q in quotes or []:
        cite = " · ".join(p for p in (disposition_display(getattr(q, "disposition", "")),
                                      humanize(getattr(q, "context", ""))) if p)
        attr = f"— {cite} · simulated" if cite else "— simulated"
        out.append(f'<div class="rk-quote"><div class="q">“{_e(q.quote)}”</div>'
                   f'<div class="a">{_e(attr)}</div></div>')
    return "".join(out)


def _problem_cards(m: ReadModel) -> str:
    pains = list(m.report.pain_map)
    if not pains:
        return ""
    load_bearing = (m.report.decision.load_bearing_pain_id
                    if m.report.decision else "") or ""

    # Within-target pains first (they gate the decision), the load-bearing one
    # ahead of its peers, then by funnel stage in the order a buyer moves.
    def key(p):
        stage = (p.funnel_stage or "").lower()
        return (0 if p.within_target else 1,
                0 if p.id == load_bearing else 1,
                FUNNEL_STAGE_ORDER.index(stage) if stage in FUNNEL_STAGE_ORDER
                else len(FUNNEL_STAGE_ORDER))

    cards = []
    for p in sorted(pains, key=key):
        mk = _marker(p, m)
        border = ("1.5px solid var(--loadring)" if p.id == load_bearing
                  else f"1px solid {mk['card_line']}")
        lb = ('<span class="rk-chip" style="color:var(--onload);'
              'background:var(--loadring)">LOAD-BEARING</span>'
              if p.id == load_bearing else "")
        tgt_col = "var(--accent-deep)" if p.within_target else "var(--muted)"
        tgt_bg = "var(--accent-tint)" if p.within_target else "var(--chipbg)"
        tgt = "WITHIN TARGET" if p.within_target else "OUTSIDE TARGET"

        lead, rest = _split_lead(client_pain_text(p.pain))
        detail = (f'<div class="rk-why" style="margin:0">'
                  f'<div class="x">{_e(rest)}</div></div>' if rest else "")
        prev = ""
        if p.prevalence:
            prev = (f'<div style="margin-top:12px;display:flex;gap:10px;'
                    f'align-items:baseline"><span style="flex:none;font-size:9px;'
                    f'font-weight:700;letter-spacing:.07em;color:var(--faint)">'
                    f'PREVALENCE</span><span style="font-size:12px;line-height:1.55;'
                    f'color:var(--soft)">{_e(p.prevalence)}</span></div>')
        quotes = _quotes(p.evidence_quotes)
        body = detail + prev + quotes

        cards.append(
            f'<details class="rk-prob" style="border:{border};'
            f'background:{mk["card_bg"]}"><summary><div class="hd">'
            f'<span class="rk-id">{_e(p.id)}</span>'
            f'<span class="rk-chip" style="color:var(--soft);'
            f'border:1px solid var(--pillbd)">'
            f'{_e((p.funnel_stage or "").upper())}</span>'
            f'<span class="rk-chip" style="color:{mk["sev_col"]};'
            f'background:{mk["sev_bg"]}">{_e(mk["sev_label"])}</span>'
            f'<span class="rk-chip" style="color:{tgt_col};background:{tgt_bg}">'
            f'{tgt}</span>{lb}'
            f'<span style="margin-left:auto;font-size:10.5px;color:var(--faint)">'
            f'{_e(mk["types"])}</span>'
            f'<span class="rk-more"><span class="shut">Details ▾</span>'
            f'<span class="opened">Hide ▴</span></span></div>'
            f'<div class="lead" style="color:'
            f'{"var(--body)" if p.within_target else "var(--soft)"}">{_e(lead)}</div>'
            f'</summary><div class="detail">'
            f'<hr class="rk-hr" style="margin:0 0 14px">{body}</div></details>'
        )

    head = (f'<div style="display:flex;align-items:baseline;gap:10px;margin-top:6px;'
            f'padding:0 2px"><span class="rk-k">PROBLEMS — {len(pains)}</span>'
            f'<span style="font-size:11px;color:var(--ghost)">leads only — expand a '
            f'card for the evidence</span></div>')
    return (head + '<div style="display:flex;flex-direction:column;gap:10px">'
            + "".join(cards) + "</div>")


def _fixes(m: ReadModel) -> str:
    """The ranked levers and the detailed changes, kept adjacent.

    The lever list is the summary and the changes are the detail behind it;
    the heading is decision-keyed call-to-action copy ("TO GET A TRUSTWORTHY
    READ:" on INCONCLUSIVE), so separating them reads as two competing
    prescriptions.
    """
    # `bet_ranking` is passed through untouched and unreordered — see
    # read_model.OUT_OF_TARGET_ONLY_NOTE for why the floor cannot reach it.
    levers = m.report.bet_ranking
    if not levers and not (m.ranked_changes or m.unranked_changes):
        return ""
    out = [f'<div class="rk-card" style="padding:20px 24px 24px">'
           f'<div style="font-size:11px;font-weight:700;letter-spacing:.08em;'
           f'color:var(--body)">{_e(m.lever_heading)}</div>']
    if levers:
        out.append('<div style="margin-top:14px">')
        for i, text in enumerate(levers, 1):
            out.append(f'<div class="rk-lever"><span class="rk-levern">{i}</span>'
                       f'<span style="font-size:13px;line-height:1.55;color:var(--body);'
                       f'text-wrap:pretty">{_e(text)}</span></div>')
        out.append("</div>")
    # The prevalence floor still runs — it just stops announcing itself. A fix
    # resting only on out-of-target problems sorts LAST instead of sitting
    # under a "NOT RANKED" heading with OUT_OF_TARGET_ONLY_NOTE attached (the
    # user's explicit call, 2026-08-04: the machinery is ours to act on, not
    # the customer's to read). The ordering is the whole of what the floor now
    # does to the page, so `ranked_changes` must stay computed in read_model.
    #
    # ⚠ All three changes render. `_validate_prescription` requires exactly
    # three, so dropping the demoted ones would silently show two on the 2-of-51
    # runs that have one — a gap with no explanation, which is worse than the
    # heading this replaces.
    changes = list(m.ranked_changes) + list(m.unranked_changes)
    if changes:
        if levers:
            out.append('<hr class="rk-hr">')
        out.append('<div class="rk-k">DETAILED CHANGES</div>')
        out.extend(_fix_card(c) for c in changes)
    out.append("</div>")
    return "".join(out)


def _fix_card(c) -> str:
    """One detailed change. Shared by the ranked and unranked lists so the two
    can never drift into looking like different kinds of object."""
    lever = (c.lever_class or "creative").lower()
    creative = lever == "creative"
    solves = "".join(
        f'<span class="rk-id" style="font-size:10px;padding:2px 6px">{_e(pid)}</span>'
        for pid in getattr(c, "derives_from_pains", []) or []
    )
    traced = (f'<span style="margin-left:8px;font-size:9px;font-weight:700;'
              f'letter-spacing:.07em;color:var(--ghost)">SOLVES</span>{solves}'
              if solves else "")
    # The design's card carries the change and its traceability only. `why` and
    # the target's own corroboration are real engine output, so they fold into
    # the same disclosure the problem cards use rather than being dropped.
    extra = ""
    detail = _e(c.why or "")
    if getattr(c, "within_target_corroboration", ""):
        detail += (f'<br><span style="color:var(--body)">What your target '
                   f'said:</span> {_e(c.within_target_corroboration)}')
    if detail:
        extra = (f'<details class="rk-why"><summary>Why this change ▾</summary>'
                 f'<div class="x">{detail}</div>{_quotes(c.evidence_quotes)}'
                 f"</details>")
    return (
        f'<div class="rk-fix"><div class="ch">{_e(c.change)}</div>'
        f'<div style="margin-top:10px;display:flex;align-items:center;gap:6px;'
        f'flex-wrap:wrap">'
        f'<span class="rk-chip" style="color:'
        f'{"var(--accent-deep)" if creative else "var(--structtag)"};background:'
        f'{"var(--accent-tint)" if creative else "var(--structtagbg)"}">'
        f'{_e(humanize(lever).upper())}</span>{traced}</div>{extra}</div>'
    )


def _what_worked(m: ReadModel) -> str:
    items = m.report.strengths_to_preserve
    if not items:
        return ""
    cards = []
    for s in items:
        q = s.evidence_quotes[0].quote if s.evidence_quotes else ""
        quote = (f'<div style="margin-top:9px;font-size:11.5px;line-height:1.5;'
                 f'color:var(--muted)">“{_e(q)}”</div>' if q else "")
        cards.append(f'<div class="rk-won"><div style="font-size:12.5px;'
                     f'line-height:1.55;color:var(--body);text-wrap:pretty">'
                     f'{_e(s.strength)}</div>{quote}</div>')
    return (f'<div class="rk-card" style="padding:20px 24px 22px">'
            f'<div class="rk-k">WHAT WORKED</div>'
            f'<div class="rk-grid">{"".join(cards)}</div></div>')


def _panel_table(m: ReadModel) -> str:
    """Every consumer type in the panel, in and out of target.

    The rest of the page is measured on the in-target slice, which answers
    "did the people we bought respond" and cannot answer "who else did" — and
    in real runs those come apart: a type read as in-target can do nothing
    while an out-of-target type acts.

    Suppressed on INCONCLUSIVE, with the rest of the numbers. The design
    rendered this table unconditionally; an untrustworthy read must not show
    response rates here either, by any route.
    """
    p = m.panel
    if p.is_empty or m.is_inconclusive or m.headline is None:
        return ""

    rows: list[str] = []
    uncovered: dict[str, int] = {}
    for t in p.types:
        for action, count in t.glance.counts.items():
            if action not in _PANEL_ACTION_COLUMNS and count:
                uncovered[action] = uncovered.get(action, 0) + count
        steps = [f"{n} {label}" for k, label, n in t.step_rows() if k != "nothing"]
        nxt = " · ".join(steps) if steps else "none"
        badge = '<span class="rk-badge">TARGET</span>' if t.within_target else ""
        col = "var(--ink)" if t.within_target else "var(--soft)"
        weight = 600 if t.within_target else 400

        def cell(v: int) -> str:
            shade = col if v else "var(--ghost)"
            return f'<td style="color:{shade}">{v}</td>'

        rows.append(
            f'<tr class="{"in" if t.within_target else ""}">'
            f'<td style="color:{col};font-weight:{weight}">{_e(t.label)}{badge}</td>'
            f'<td style="color:{col};font-weight:{weight}">{t.n}</td>'
            f'{cell(t.glance.scroll_past)}{cell(t.glance.linger)}{cell(t.glance.save)}'
            f'<td style="font-size:12.5px;color:'
            f'{"var(--ghost)" if nxt == "none" else col}">{_e(nxt)}</td></tr>'
        )

    # An action with no column of its own is reported rather than dropped. A
    # hand-maintained column list inside a renderer is exactly how this page
    # previously lost every saver from its denominator.
    extra = ""
    if uncovered:
        said = ", ".join(f"{n} {humanize(a)}" for a, n in sorted(uncovered.items()))
        extra = (f'<div style="margin-top:10px;font-size:12px;color:var(--muted)">'
                 f"Also in the panel, without a column above: {_e(said)}.</div>")

    # "Who it landed on" is a FINDING — often the most useful thing in the
    # table — and it used to render in the warning tint, which made a result
    # look like a problem with the result. Neutral styling; same content.
    note = ""
    if p.decoupling_note:
        note = (f'<div style="margin-top:12px;padding:12px 14px;border-radius:10px;'
                f'background:var(--accent-tint);border:1px solid var(--accent-line)">'
                f'<div class="rk-k" style="color:var(--accent-deep)">WHO IT LANDED ON</div>'
                f'<div style="margin-top:5px;font-size:12.5px;line-height:1.55;'
                f'color:var(--body)">{_e(p.decoupling_note)}</div></div>')

    return f"""<div class="rk-card" style="padding:20px 24px 22px">
  <div class="rk-k">PANEL — {m.panel.panel_n} SIMULATED CONSUMERS</div>
  <div style="margin-top:6px;font-size:12px;line-height:1.55;color:var(--muted)">
    {_e(p.summary)}</div>
  <div class="rk-tblwrap"><table class="rk-tbl">
    <thead><tr><th>CONSUMER TYPE</th><th>N</th><th>SCROLLED PAST</th>
    <th>STOPPED</th><th>SAVED</th><th>NEXT STEP</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>{extra}{note}
</div>"""


def _extras(m: ReadModel) -> str:
    """Findings the design has no slot for, in the design's own language.

    Not guardrails — the artifact may curate findings — but real engine output
    a brand manager asked about would want: where the creative lands across
    feed moments, and the panel's own words beyond the ones attached to a
    problem. Collapsed, so they cost the page nothing until opened.
    """
    blocks = []
    cfm = m.report.context_fit_map
    if cfm:
        rows = "".join(
            f'<div class="rk-fix"><div style="font-size:9.5px;font-weight:700;'
            f'letter-spacing:.06em;color:var(--accent-deep)">{_e(e.verdict)}</div>'
            f'<div style="margin-top:4px;font-size:13px;font-weight:600">'
            f'{_e(_sentence_case(ctx))}</div>'
            f'<div style="margin-top:5px;font-size:12.5px;line-height:1.55;'
            f'color:var(--soft)">{_e(e.friction_summary)}</div></div>'
            for ctx, e in cfm.items()
        )
        blocks.append((f"WHERE IT LANDS — {len(cfm)} FEED MOMENTS", rows))
    voice = m.report.verbatim_consumer_voice[:8]
    if voice:
        blocks.append(("SIMULATED CONSUMER VOICE", _quotes(voice)))
    if not blocks:
        return ""
    return "".join(
        f'<details class="rk-card" style="padding:16px 24px">'
        f'<summary style="list-style:none;cursor:pointer;display:flex;'
        f'justify-content:space-between;align-items:baseline">'
        f'<span class="rk-k">{_e(title)}</span>'
        f'<span class="rk-more"><span class="shut">Show ▾</span>'
        f'<span class="opened">Hide ▴</span></span></summary>'
        f"<div>{body}</div></details>"
        for title, body in blocks
    )


def _how_it_was_made(m: ReadModel) -> str:
    """Everything about HOW this read was produced, collapsed, at the foot.

    ⚠ This is where the honesty budget of the page now lives, entire, and it is
    a deliberate consolidation rather than a deletion — the user's explicit
    decision, 2026-08-04. Previously the same content was scattered across the
    page as eight separate interruptions: a warnings strip above the result, a
    caveat under the decision chip, another under the headline number, a third
    under the champion line, a fourth under the outside-response bars, a fifth
    above the panel table, a NOT RANKED block in the fixes, and a methodology
    card. A reader met a qualification before they met a finding.

    Nothing is gone. `read_model` computes every one of them unchanged, they
    all render here, and `<details>` costs the page nothing until opened —
    the same zero-JS mechanism the problem cards already use.

    Three sections, in the order someone who opens this actually wants them:
    what to keep in mind (the standing caveats, true of every read), what
    qualifies THIS run (`_run_qualifiers`), and the run's configuration.

    ⚠ The standing caveats are INLINED, not linked to the methodology page.
    This artifact is self-contained by hard requirement — it is emailed and
    opened from disk — so a `/methodology` href would be a dead link exactly
    where the reader went looking for the qualification.
    """
    rows: list[tuple[str, str]] = [
        ("PANEL", f"{m.panel.panel_n or m.panel_size} simulated consumers"),
    ]
    contexts = list(m.report.context_fit_map)
    if contexts:
        rows.append(("CONTEXTS", " · ".join(humanize(c) for c in contexts)))
    if m.declared_targeting:
        rows.append(("DECLARED TARGETING", m.declared_targeting))
    if m.category:
        # ⚠ `_sentence_case(m.category)` rendered the SLUG — "Fnb world" — in the
        # customer's own methodology block. `market_name_for` is the prose half.
        rows.append(("CATEGORY", market_name_for(m.category)))
    rows.append(("AD JOB", m.purpose_label))
    rows.append(("ENGINE READ",
                 f"{m.report.verdict} · confidence {m.report.confidence}/100"))
    # Why the trust chip says what it says. The chip is the claim; on a
    # DIRECTIONAL read this is the reason, and it is the difference between
    # "directional" reading as a hedge and reading as a measurement.
    if m.trust == "DIRECTIONAL":
        n = len(m.within_dispositions)
        who = "one buyer type" if n == 1 else f"{n} buyer types"
        rows.append(("WHY DIRECTIONAL",
                     f"This ad speaks to {who}"
                     + (f" ({m.within_label})" if n else "")
                     + ", so the read rests on a narrow attitudinal base. Enough "
                       "to point a direction and name the leak; not enough to "
                       "stake a precise number on."))
    if m.homogeneity_note:
        rows.append(("PANEL AGREEMENT", m.homogeneity_note))
    # ⚠ No FLAGS row. `_run_qualifiers` already emits one METHOD row per flag
    # line into the "specific to this run" grid directly above this one, and
    # rendering them here too printed the same sentence twice inside a single
    # collapsed block — which is the duplication this change exists to remove,
    # reproduced in miniature.
    if m.report.provisional_dispositions:
        # ⚠⚠ WAS humanize(d) — i.e. label.replace("_", " "), the exact defect,
        # on the customer's own methodology block. It survived #81 and survived
        # my "render the page and read it" pass, because the run I rendered has
        # no provisional dispositions so the branch never executed. One real run
        # does: the Starbucks read shows three of them.
        # ⭐ A surface you cannot see firing is not a surface you have checked.
        rows.append(("PROVISIONAL DISPOSITIONS",
                     ", ".join(disposition_display(d)
                               for d in m.report.provisional_dispositions)))
    if m.funnel_note:
        rows.append(("PROJECTED FUNNEL", m.funnel_note))
    if m.report_source != "run.json":
        rows.append(("RECOVERED VIA", m.report_source))
    rows.append(("RUN ID", m.run_id))

    def _grid(pairs: list[tuple[str, str]]) -> str:
        return ('<div class="rk-method">' + "".join(
            f'<div class="k">{_e(k)}</div><div>{_e(v)}</div>' for k, v in pairs)
            + "</div>")

    # The standing caveats — true of every read this engine produces, which is
    # why they are stated once here rather than re-attached to each number.
    # VERDICT_CAVEAT keeps the user's own wording.
    mind = [
        ("THE VERDICT", VERDICT_CAVEAT),
        ("THE BUY-INTENT FIGURE", HEADLINE_CAVEAT),
        ("BETWEEN CONSUMER TYPES", SEGMENT_CAVEAT),
    ]
    if m.unranked_changes:
        # Only when the floor actually moved something, because otherwise this
        # describes machinery that did nothing on this run.
        mind.append(("CHANGE ORDER", OUT_OF_TARGET_ONLY_NOTE))

    qualifiers = _run_qualifiers(m)
    parts = [f'<div class="rk-k">WHAT TO KEEP IN MIND</div>{_grid(mind)}']
    if qualifiers:
        parts.append(f'<hr class="rk-hr"><div class="rk-k">SPECIFIC TO THIS RUN</div>'
                     f"{_grid(qualifiers)}")
    parts.append(f'<hr class="rk-hr"><div class="rk-k">HOW IT WAS RUN</div>{_grid(rows)}')

    return (f'<details class="rk-card rk-made" style="padding:20px 24px 22px">'
            f'<summary>How this read was made</summary>'
            f'<div style="margin-top:16px">{"".join(parts)}</div></details>')


def _shell(inner: str, m: ReadModel) -> str:
    nav = "".join(
        f'<div class="rk-nav{" on" if item == "Reads" else ""}">{item}</div>'
        for item in ("Reads", "New read", "Sessions", "Library", "Settings")
    )
    decision = m.decision_name if m.decision_name in _DECISION_BG else "INCONCLUSIVE"
    return f"""<div class="rk" data-decision="{_e(decision)}">
<div class="rk-top">
  <div class="rk-brand"><span class="rk-mark"></span><span class="rk-name">Rocket</span></div>
  <div class="rk-search">Search</div>
  <div class="rk-acct"><span class="rk-avatar">BM</span>
    <span style="font-size:11px;color:var(--faint)">▾</span></div>
</div>
<div class="rk-body">
  <nav class="rk-side">{nav}</nav>
  <div class="rk-main"><div class="rk-col">{inner}</div></div>
</div>
</div>"""


def render_html(
    model: ReadModel, *, embed_image: bool = True, base_dir: Path | None = None,
    full_document: bool = True,
) -> str:
    """Render the Creative Read as a self-contained dashboard page.

    The signature is the one the renderer it replaced had, which is why the
    operator server and `render_read.py` were cut over without a call site
    changing. Keep it: `full_document=False` is the fragment path.

    The section order below is the user's design and is fixed.

    ⚠ The page no longer opens on a warnings strip, and no caveat renders
    beside the finding it qualifies. That is the user's explicit decision of
    2026-08-04, taken with the whole page in front of them, and it is not a
    regression to repair: every qualifier still exists, still gets computed by
    `read_model`, and renders in `_how_it_was_made` at the foot — collapsed,
    findable, complete. Reinstating any of them inline needs THEIR say-so, not
    a reviewer's instinct that a number looks bare.

    ⚠ The customer read and the internal surfaces now DIVERGE ON PURPOSE. The
    operator console and `server/app.py`'s session export — the Track-2
    artifact that lands next to real CTR/ROAS — keep every qualifier inline,
    because they are how we find out whether this instrument works. The
    divergence is pinned by tests in both directions so that neither side gets
    "fixed" into agreement with the other.
    """
    base_dir = base_dir or Path.cwd()
    title = (f"Creative Read — {model.asset_label}" if model.asset_label
             else "Creative Read")
    inner = "".join([
        _run_header(model, embed_image, base_dir),
        _result(model),
        _problem_map(model),
        _problem_cards(model),
        _fixes(model),
        _what_worked(model),
        _panel_table(model),
        f'<div class="rk-disc">{_e(model.disclaimer)}</div>',   # E3
        _extras(model),
        _how_it_was_made(model),
        f'<div class="rk-foot"><span>Rocket</span>'
        f'<span style="font-family:{_MONO};font-size:9.5px">{_e(model.run_id)}</span></div>',
    ])
    body = _shell(inner, model)
    head = f"<title>{_e(title)}</title>\n<style>{_CSS}</style>\n"
    if not full_document:
        return head + body
    return (f'<!doctype html>\n<html lang="en">\n<head>\n'
            f'<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f"{head}</head>\n<body>\n{body}\n</body>\n</html>\n")
