"""The signed-in application — every screen between signing in and the read.

Rebuilt from the user's Claude Design state stack (`docs/Claude design/Rocket
App.dc.html`), the same way `agent/dashboard_html.py` was rebuilt from the
report design. The design is the specification for what these pages look like;
this module is what makes them real. **Do not redesign it here.**

Three things carried over from the design and worth stating out loud, because
they are the reasons it looks like this:

**The read is not part of the application.** Opening one leaves the shell
entirely — no sidebar, no search, no chrome, just a back link above a
standalone document. The report already carries its own Export; the app adds
none. A read is a deliverable that gets shared, and wrapping it in product
furniture would make it look like a page instead of a document.

**Nothing invents motion.** The phase rows move when an agent finishes and not
otherwise; the elapsed clock is `updated_at - started_at` from `progress.json`,
so a dead run's clock stops where the run stopped rather than counting up
forever. The one exception is the *preparing* screen, where an indeterminate
bar is honest because the wait is under a minute and unmeasured.

**The five decisions are marked, never scored.** SCALE/ITERATE/RETARGET/
REBUILD/INCONCLUSIVE are instructions, not a good-to-bad scale, so they carry
shape marks rather than a red-amber-green ramp. The glosses are imported from
`agent.read_model.DECISION_TAGLINE` rather than retyped — one string, both
renderers (memory: report_surface_fidelity).

Stdlib only, matching the engine's no-template-dependency rule.
"""

from __future__ import annotations

import html

from agent.dashboard_html import PAGE_CSS
from agent.read_model import DECISION_TAGLINE
from server.runs import RunRef

# The design's two tokens that PAGE_CSS does not carry. `--leak-line` is the
# warm hairline the flag stack is drawn with; `--stripe` is the placeholder
# hatch that stands in for a creative thumbnail.
_APP_CSS = """
:root{--leak-line:#f0e0bd;--maxw:none;
  --stripe:repeating-linear-gradient(135deg,#f3f3f5 0px,#f3f3f5 6px,#ececef 6px,#ececef 7px);}
a{color:var(--accent-ink);text-decoration:none}
a:hover{color:var(--accent-ink)}
input,select,button,textarea{font-family:inherit}
:focus-visible{outline:2px solid var(--accent-ink);outline-offset:2px}
@keyframes rk-bar{0%{transform:translateX(-100%)}100%{transform:translateX(300%)}}
@keyframes rk-pulse{0%,100%{opacity:1}50%{opacity:.35}}

/* ---- shell ---- */
.app{display:flex;min-height:100vh;background:var(--surface)}
.side{width:212px;flex:none;background:var(--surface);border-right:1px solid var(--line);
  display:flex;flex-direction:column;padding:16px 12px}
.brand{display:flex;align-items:center;gap:9px;padding:6px 10px 20px}
.brand i{width:13px;height:13px;background:var(--accent);border-radius:3px;
  transform:rotate(45deg);display:block}
.brand b{font-size:15.5px;font-weight:700;letter-spacing:-.01em}
.nav{display:flex;flex-direction:column;gap:2px}
.nav a{display:block;padding:9px 12px;border-radius:8px;font-size:13px;color:var(--muted)}
.nav a:hover{background:var(--surface-2);color:var(--ink)}
.nav a.on{font-weight:600;background:var(--accent-tint);color:var(--accent-ink)}
.who{margin-top:auto;border-top:1px solid var(--line);padding:14px 12px 2px}
.who .k{font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:.09em;
  color:var(--faint)}
.who .acct{margin-top:5px;font-family:var(--font-mono);font-size:12.5px;color:var(--ink)}
.who form{margin:9px 0 0}
.who button{background:none;border:0;padding:0;font-size:12.5px;color:var(--muted);
  cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.who button:hover{color:var(--ink)}
.main{flex:1;min-width:0;background:var(--ground);padding:26px 30px 44px}
.main h1{margin:0;font-size:19px;font-weight:600;letter-spacing:-.01em}
.main .under{margin-top:5px;font-size:12.5px;color:var(--muted)}
.wrap{max-width:820px}

/* ---- shared furniture ---- */
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;
  box-shadow:var(--shadow);padding:20px 22px 22px}
.k{font-family:var(--font-mono);font-size:9.5px;font-weight:700;letter-spacing:.09em;
  color:var(--faint)}
.hint{margin-top:4px;font-size:12px;color:var(--muted);line-height:1.5}
.btn{display:inline-block;background:var(--accent);color:var(--on-accent);border:0;
  border-radius:8px;padding:10px 18px;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{background:var(--accent-ink);color:var(--on-accent)}
.btn--big{border-radius:9px;padding:13px 26px;font-size:14.5px}
.btn--quiet{background:var(--surface);border:1px solid var(--line);color:var(--ink);
  font-weight:400;padding:10px 16px}
.btn--quiet:hover{background:var(--surface);border-color:var(--faint);color:var(--ink)}
.quiet{font-size:12.5px;color:var(--muted)}
.thumb{border-radius:9px;border:1px solid var(--line);background:var(--stripe);flex:none}
.mk{width:11px;height:11px;flex:none;border-radius:2px;display:inline-block}
input[type=text],input[type=password],input[type=search],textarea,select{
  width:100%;background:var(--surface-2);border:1px solid var(--line);border-radius:8px;
  padding:10px 12px;font-size:13.5px;color:var(--ink)}
textarea{line-height:1.5;resize:vertical}

/* ---- sign in ---- */
.gate{min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:40px;background:var(--ground)}
.gate form,.gate .card{width:328px;padding:30px 30px 26px}
.gate .btn{width:100%;margin-top:16px;padding:11px 16px;font-size:13.5px}
.gate label{display:block;font-family:var(--font-mono);font-size:9.5px;font-weight:700;
  letter-spacing:.09em;color:var(--faint);margin-top:24px}
.gate input{margin-top:7px}
.bad{border-color:var(--leak)!important}
.err{margin-top:8px;display:flex;gap:8px;align-items:baseline}
.err b{font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:.07em;
  color:var(--leak);flex:none}
.err span{font-size:12px;line-height:1.5;color:var(--muted)}

/* ---- reads list ---- */
.listhead{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;
  flex-wrap:wrap}
.tools{display:flex;align-items:center;gap:10px}
.tools form{display:flex;gap:6px;margin:0}
.tools input{width:250px;font-size:12.5px;padding:8px 12px}
.tools .find{background:var(--surface);border:1px solid var(--line);border-radius:8px;
  padding:8px 13px;font-size:12.5px;color:var(--ink);cursor:pointer}
.rows{margin-top:18px;background:var(--surface);border:1px solid var(--line);
  border-radius:12px;box-shadow:var(--shadow);overflow-x:auto}
.grid{display:grid;grid-template-columns:minmax(230px,1fr) 190px 210px 150px 44px;
  padding:0 6px;min-width:830px}
.grid>*{grid-column:1/-1;display:grid;grid-template-columns:subgrid;
  border-bottom:1px solid var(--line)}
.grid .hd div{font-family:var(--font-mono);font-size:9px;font-weight:700;
  letter-spacing:.09em;color:var(--faint);padding:11px 12px}
.grid a{align-items:center;color:inherit;border-radius:8px}
.grid a:hover{background:var(--surface-2);color:inherit}
.grid .cre{padding:13px 12px;font-size:13.5px;color:var(--ink);line-height:1.4}
.grid .cell{padding:13px 12px}
.grid .stamp{font-family:var(--font-mono);font-size:12px;color:var(--ink);
  font-variant-numeric:tabular-nums}
.grid .sub{margin-top:3px;font-family:var(--font-mono);font-size:9.5px;color:var(--faint);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.grid .brand{padding:13px 12px;font-family:var(--font-mono);font-size:11px;
  color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.grid .chev{padding:13px 10px;text-align:right;font-size:13px;color:var(--faint)}
.tag{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);
  border-radius:7px;padding:4px 9px 4px 7px;background:var(--surface-2)}
.tag b{font-family:var(--font-mono);font-size:10.5px;font-weight:700;letter-spacing:.06em;
  color:var(--ink)}
.tag--none{border-style:dashed;background:none;padding:4px 9px}
.tag--none b{font-weight:400;letter-spacing:.04em;color:var(--faint)}
.legend{margin-top:16px;background:var(--surface);border:1px solid var(--line);
  border-radius:12px;box-shadow:var(--shadow);padding:18px 20px 20px}
.legend .list{margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:9px 26px}
.legend .row{display:flex;gap:10px;align-items:baseline}
.legend .mk{transform:translateY(1px)}
.legend .nm{font-family:var(--font-mono);font-size:10.5px;font-weight:700;
  letter-spacing:.06em;color:var(--ink);flex:none;width:104px}
.legend .gl{font-size:12px;line-height:1.5;color:var(--muted)}
.empty{margin-top:18px;max-width:620px;display:flex;flex-direction:column;
  align-items:flex-start;gap:16px;padding:40px 36px}
.empty p{font-size:15px;line-height:1.55;color:var(--ink)}

/* ---- new read ---- */
.form{margin:18px 0 0;max-width:760px;display:flex;flex-direction:column;gap:14px}
.form .fld{margin-top:18px}
.form .fld:first-of-type{margin-top:14px}
.two{margin-top:18px;display:grid;grid-template-columns:1fr 1fr;gap:18px}
.two>div{min-width:0}
.lbl{display:block;font-family:var(--font-mono);font-size:9.5px;font-weight:700;
  letter-spacing:.09em;color:var(--faint)}
.drop{margin-top:14px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:12px;min-height:196px;border:1.5px dashed #cfcdc7;
  border-radius:11px;background:var(--surface-2);padding:26px;cursor:pointer;
  text-align:center}
.drop:hover{border-color:var(--accent);background:var(--accent-tint)}
.drop b{font-size:15px;font-weight:600;color:var(--ink)}
.drop .exts{font-family:var(--font-mono);font-size:10.5px;letter-spacing:.05em;
  color:var(--faint)}
.drop input{width:auto;max-width:280px;font-size:12px;color:var(--muted);
  background:none;border:0;padding:0}
.check{margin-top:20px;border-top:1px solid var(--line);padding-top:16px;display:flex;
  gap:11px;align-items:flex-start}
.check input{width:16px;height:16px;margin:1px 0 0;accent-color:#0f8a6d;flex:none}
.check b{font-size:13.5px;font-weight:600;color:var(--ink);cursor:pointer}
.go{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.go .quiet{line-height:1.5;max-width:460px}

/* ---- preparing ---- */
.prep{margin-top:18px;max-width:760px;padding:22px 24px 24px}
.prep .top{display:flex;gap:16px;align-items:center}
.prep .ttl{font-size:15px;font-weight:600;color:var(--ink)}
.working{font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.07em;
  color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:5px 10px;
  flex:none;animation:rk-pulse 1.8s ease-in-out infinite}
.bar{margin-top:18px;height:3px;border-radius:2px;background:var(--line);overflow:hidden}
.bar i{display:block;width:33%;height:100%;background:var(--accent);
  animation:rk-bar 1.6s ease-in-out infinite}

/* ---- review ---- */
.review{max-width:820px;display:flex;flex-direction:column;gap:14px}
.phase2{font-family:var(--font-mono);font-size:11px;letter-spacing:.05em;color:var(--muted)}
.review h1{margin:6px 0 0;font-size:24px;font-weight:600;letter-spacing:-.015em}
.idline{margin-top:8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.idline .thumb{width:26px;height:26px;border-radius:6px}
.idline .nm{font-size:13px;color:var(--ink)}
.idline .meta{font-family:var(--font-mono);font-size:10.5px;color:var(--faint)}
.inferred{margin-top:11px;font-size:15px;line-height:1.6;color:var(--ink)}
.disp{margin-top:18px;border-top:1px solid var(--line);display:grid;
  grid-template-columns:1fr 170px}
.disp .h{font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:.08em;
  color:var(--faint);padding:10px 0 8px}
.disp .r{grid-column:1/-1;display:grid;grid-template-columns:subgrid;
  border-top:1px solid var(--line);align-items:center}
.disp .id{font-family:var(--font-mono);font-size:12.5px;color:var(--ink);padding:9px 0}
.disp .v{padding:9px 0}
.within{font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.07em;
  color:var(--accent-ink);background:var(--accent-tint);border-radius:999px;padding:3px 9px}
.outside{font-family:var(--font-mono);font-size:11.5px;color:var(--faint)}
.note{margin-top:14px;font-size:12.5px;line-height:1.55;color:var(--muted)}
.panelhd{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  flex-wrap:wrap}
.panelhd span:last-child{font-family:var(--font-mono);font-size:10.5px;color:var(--faint)}
.plines{margin-top:12px;display:flex;flex-direction:column;gap:8px}
.plines div{display:flex;gap:10px;align-items:baseline}
.plines i{width:5px;height:5px;border-radius:50%;background:var(--faint);flex:none;
  transform:translateY(-2px);display:block}
.plines span{font-family:var(--font-mono);font-size:12.5px;line-height:1.5;color:var(--ink)}
.cost{background:var(--surface);border:1.5px solid var(--ink);border-radius:12px;
  padding:22px 24px 24px}
.cost .k{color:var(--ink)}
.cost p{margin-top:10px;font-size:15px;line-height:1.6;color:var(--ink)}
.cost strong{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums}
.cost .go{margin-top:18px;gap:14px}
.cost .back{margin-top:14px}

/* ---- the flag stack ---- */
.flags{background:var(--leak-tint);border:1px solid var(--leak-line);border-radius:12px}
.flags .f{display:flex;gap:14px;padding:12px 18px;align-items:baseline;
  border-top:1px solid var(--leak-line)}
.flags .f:first-child{border-top:0}
.flags .t{flex:none;width:104px}
.flags .t span{display:inline-block;font-family:var(--font-mono);font-size:9px;
  font-weight:700;letter-spacing:.07em;color:var(--leak);padding:3px 0}
.flags .f--stop .t span{color:#fff;background:var(--leak);border-radius:4px;padding:3px 7px}
.flags .txt{font-size:12.5px;line-height:1.55;color:var(--ink)}
.flags .f--stop .txt{font-weight:600}
.flags .txt em{color:var(--muted);font-weight:400;font-style:normal}

/* ---- running / done ---- */
.runhead{display:flex;gap:16px;align-items:flex-start}
.runhead .thumb{width:72px;height:72px}
.runhead .st{font-family:var(--font-mono);font-size:10px;font-weight:700;
  letter-spacing:.09em;color:var(--faint)}
.runhead h1{margin:6px 0 0;font-size:19px;font-weight:600;letter-spacing:-.01em}
.runhead .rid{margin-top:5px;font-family:var(--font-mono);font-size:10.5px;
  color:var(--faint);word-break:break-all}
.elapsed{flex:none;text-align:right}
.elapsed .k{font-size:9px}
.elapsed div:last-child{margin-top:4px;font-family:var(--font-mono);font-size:26px;
  font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
.phases{margin-top:18px;background:var(--surface);border:1px solid var(--line);
  border-radius:12px;box-shadow:var(--shadow);padding:6px 22px 18px}
.phases .p{padding:14px 0;border-top:1px solid var(--line)}
.phases .p:first-child{border-top:0}
.phases .hd{display:flex;align-items:baseline;gap:12px}
.phases .dot{width:16px;height:16px;flex:none;border-radius:50%;border:1px solid var(--line);
  display:flex;align-items:center;justify-content:center;transform:translateY(3px)}
.phases .p--done .dot,.phases .p--on .dot{background:var(--accent);border-color:var(--accent)}
.phases .p--on .dot i{width:6px;height:6px;border-radius:50%;background:#fff;display:block;
  animation:rk-pulse 1.6s ease-in-out infinite}
.phases .p--stop .dot{background:var(--leak);border-color:var(--leak)}
.phases .nm{flex:1;min-width:0;font-size:14.5px;color:var(--faint)}
.phases .p--done .nm,.phases .p--on .nm,.phases .p--stop .nm{color:var(--ink)}
.phases .p--on .nm,.phases .p--stop .nm{font-weight:600}
.phases .nm em{font-size:12.5px;font-weight:400;color:var(--muted);font-style:normal}
.phases .ct{flex:none;font-family:var(--font-mono);font-size:13px;font-weight:600;
  color:inherit;font-variant-numeric:tabular-nums}
.phases .q{flex:none;font-family:var(--font-mono);font-size:10px;letter-spacing:.06em;
  color:var(--faint)}
.phases .pbar{margin:11px 0 0 28px;height:4px;border-radius:2px;background:var(--line);
  overflow:hidden}
.phases .pbar i{display:block;height:100%;background:var(--accent);border-radius:2px}
.foot{margin-top:14px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.foot .quiet{line-height:1.55;max-width:520px}
.foot .refresh{font-family:var(--font-mono);font-size:10px;letter-spacing:.05em;
  color:var(--faint)}
.done{max-width:820px;padding:24px 26px 26px}
.done .ok{display:flex;align-items:center;gap:8px}
.done .ok i{width:15px;height:15px;border-radius:50%;background:var(--accent);display:flex;
  align-items:center;justify-content:center}
.done .ok b{font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.09em;
  color:var(--accent-ink)}
.facts{margin-top:20px;display:grid;grid-template-columns:1fr 1fr;gap:14px}
.facts>div{border:1px solid var(--line);border-radius:10px;padding:14px 16px;
  background:var(--surface-2)}
.facts .v{margin-top:9px;display:flex;align-items:center;gap:8px;font-family:var(--font-mono);
  font-size:13px;font-weight:700;letter-spacing:.07em;color:var(--ink);
  font-variant-numeric:tabular-nums}
.facts .g{margin-top:8px;font-size:12px;line-height:1.5;color:var(--muted)}
.facts .bad{border-color:var(--leak-line)!important;background:var(--leak-tint)}
.facts .bad .k{color:var(--leak)}
.after{margin-top:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.after .btn{border-radius:9px;padding:12px 22px;font-size:14px}

/* ---- failed / interrupted ---- */
.dead{max-width:820px;padding:22px 24px 24px}
.dead .st{font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.09em}
.dead h1{margin:8px 0 0;font-size:17px;font-weight:600;letter-spacing:-.01em}
.dead .rid{margin-top:4px;font-family:var(--font-mono);font-size:10.5px;color:var(--faint);
  word-break:break-all}
.mono{margin-top:7px;background:var(--surface-2);border:1px solid var(--line);
  border-radius:9px;padding:12px 14px;font-family:var(--font-mono);font-size:11.5px;
  line-height:1.6;color:var(--ink);word-break:break-word}
.charged{margin-top:16px;border:1.5px solid var(--ink);border-radius:10px;padding:14px 16px}
.charged p{margin-top:7px;font-size:13.5px;line-height:1.55;color:var(--ink)}

/* ---- the read, outside the app ---- */
.readbar{background:var(--surface);border-bottom:1px solid var(--line);padding:13px 24px}
.readbar a{font-size:13px;color:var(--muted)}
.readbar a:hover{color:var(--ink)}
"""

NAV = (
    ("Reads", "/reads"),
    ("New read", "/reads/new"),
    ("Brand profiles", "/profiles"),
    ("Settings", "/settings"),
)

# The five decisions are instructions, not a good-to-bad ramp, so they are
# marked by SHAPE — solid, half, split, hatched, dashed — and not by colour.
# A brand manager reading a colour scale infers a ranking that the decision
# function does not express: RETARGET is not "worse than" ITERATE.
_INK = "#17181a"
_MARK = {
    "SCALE": f"background:{_INK};border:1px solid {_INK}",
    "ITERATE": f"background:linear-gradient(#fff 0 50%,{_INK} 50% 100%);"
               f"border:1px solid {_INK}",
    "RETARGET": f"background:linear-gradient(90deg,{_INK} 0 50%,#fff 50% 100%);"
                f"border:1px solid {_INK}",
    "REBUILD": f"background:repeating-linear-gradient(135deg,{_INK} 0 2px,#fff 2px 4px);"
               f"border:1px solid {_INK}",
    "INCONCLUSIVE": "background:transparent;border:1px dashed #8a8d94",
}
_NO_MARK = "background:transparent;border:1px dashed #8a8d94"


def _e(text: object) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def _doc(title: str, body: str, *, head: str = "") -> str:
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{_e(title)}</title>\n{head}"
        f"<style>{PAGE_CSS}{_APP_CSS}</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def _brand() -> str:
    return '<div class="brand"><i></i><b>Rocket</b></div>'


def shell(title: str, *, active: str, account: str, body: str,
          head: str = "") -> str:
    """The sidebar and the frame around it.

    Eleven of the design's states are this shell with a different main
    column, which is why it is one function: a nav item added here appears
    everywhere, and cannot appear on eight screens and be forgotten on three.
    """
    nav = "".join(
        f'<a href="{_e(href)}" class="{"on" if href == active else ""}"'
        f'{" aria-current=\"page\"" if href == active else ""}>{_e(label)}</a>'
        for label, href in NAV
    )
    return _doc(title, f"""<div class="app">
<nav class="side">{_brand()}
  <div class="nav">{nav}</div>
  <div class="who"><div class="k">SIGNED IN</div>
    <div class="acct">{_e(account)}</div>
    <form method="post" action="/signout"><button type="submit">Sign out</button></form>
  </div>
</nav>
<main class="main">{body}</main>
</div>""", head=head)


# ---- signing in --------------------------------------------------------


def signin_page(*, error: str = "", next_url: str = "",
                configured: bool = True) -> str:
    """One field, because there is one shared password and no user table."""
    if not configured:
        return _doc("Sign in", f"""<div class="gate"><div class="card">
{_brand()}
<div class="quiet">Sign-in is not configured on this server.</div>
<div class="err" style="margin-top:16px"><b>CLOSED</b><span>No password is
  set, so no sign-in can succeed and every page behind it stays shut. That is
  deliberate — an unconfigured server does not fall open.</span></div>
</div></div>""")
    hidden = (f'<input type="hidden" name="next" value="{_e(next_url)}">'
              if next_url else "")
    err = (f'<div class="err"><b>INCORRECT</b><span>{_e(error)}</span></div>'
           if error else "")
    return _doc("Sign in", f"""<div class="gate">
<form method="post" action="/signin" class="card">{hidden}
  {_brand()}
  <div class="quiet">Read the creative before you run it.</div>
  <label for="pw">PASSWORD</label>
  <input id="pw" name="password" type="password" required autofocus
    autocomplete="current-password" class="{'bad' if error else ''}">
  {err}
  <button type="submit" class="btn">Sign in</button>
</form></div>""")


# ---- the reads list ----------------------------------------------------


def _mark(decision: str) -> str:
    return _MARK.get(decision, _NO_MARK)


def _legend() -> str:
    rows = "".join(
        f'<div class="row"><span class="mk" style="{_mark(name)}"></span>'
        f'<span class="nm">{_e(name)}</span>'
        f'<span class="gl">{_e(gloss)}</span></div>'
        for name, gloss in DECISION_TAGLINE.items()
    )
    return f"""<div class="legend">
<div class="k">THE FIVE DECISIONS — INSTRUCTIONS, NOT SCORES</div>
<div class="list">{rows}</div></div>"""


def reads_page(runs: list[RunRef], *, account: str, query: str = "") -> str:
    """Home. Every row carries its date AND its run id, because the same
    creative is read more than once and the label alone does not identify
    which run you are opening."""
    if not runs and not query:
        return shell("Reads", active="/reads", account=account, body=f"""
<h1>Reads</h1>
<div class="card empty"><p>A read puts your ad in front of a synthetic panel of
  buyers, then tells you what it gets wrong and what to do about it — before you
  spend on it.</p>
<a class="btn" href="/reads/new">New read</a></div>""")

    rows = []
    for r in runs:
        if r.decision:
            tag = (f'<span class="tag"><span class="mk" '
                   f'style="{_mark(r.decision)}"></span>'
                   f"<b>{_e(r.decision)}</b></span>")
        else:
            # Real: runs on disk predate the decision layer. Saying so is
            # better than printing a decision they never had.
            tag = ('<span class="tag tag--none"><b>NOT GRADED</b></span>'
                   '<div class="sub">Predates the decision layer</div>')
        rows.append(f"""<a href="/reads/{_e(r.key)}">
  <div class="cre">{_e(r.asset_label)}</div>
  <div class="cell">{tag}</div>
  <div class="cell"><div class="stamp">{_e(r.updated_at[:10])}</div>
    <div class="sub">{_e(r.run_id)}</div></div>
  <div class="brand">{_e(r.brand_profile_id)}</div>
  <div class="chev">›</div></a>""")

    count = f"{len(runs)} read{'' if len(runs) == 1 else 's'} · newest first"
    if query:
        count += f" · filtered by “{_e(query)}”"
    body = "".join(rows) or (
        '<a><div class="cre">Nothing matches that filter.</div>'
        '<div class="cell"></div><div class="cell"></div>'
        '<div class="brand"></div><div class="chev"></div></a>')
    return shell("Reads", active="/reads", account=account, body=f"""
<div class="listhead">
  <div><h1>Reads</h1><div class="under">{count}</div></div>
  <div class="tools">
    <form method="get" action="/reads" role="search">
      <label for="q" style="position:absolute;width:1px;height:1px;overflow:hidden;
        clip:rect(0 0 0 0)">Filter reads</label>
      <input id="q" name="q" type="search" value="{_e(query)}"
        placeholder="Filter by creative or decision">
      <button type="submit" class="find">Filter</button>
    </form>
    <a class="btn" href="/reads/new">New read</a>
  </div>
</div>
<div class="rows"><div class="grid">
  <div class="hd"><div>CREATIVE</div><div>DECISION</div><div>RUN</div>
    <div>BRAND PROFILE</div><div></div></div>
  {body}
</div></div>
{_legend()}""")


# ---- brand profiles and settings ---------------------------------------


def profiles_page(profiles: list[tuple[str, int]], *, account: str) -> str:
    """Counts only, no charts. Rows carry equal weight so the one-read
    profiles look like the norm they are."""
    rows = "".join(
        f'<a href="/reads?q={_e(name)}"><span class="nm">{_e(name)}</span>'
        f'<span class="ct"><b>{n}</b> <i>read{"" if n == 1 else "s"}</i></span></a>'
        for name, n in profiles
    ) or '<div class="row--empty quiet" style="padding:14px 18px">No profiles yet.</div>'
    total = sum(n for _, n in profiles)
    return shell("Brand profiles", active="/profiles", account=account, body=f"""
<h1>Brand profiles</h1>
<div class="under">{total} read{'' if total == 1 else 's'} across
  {len(profiles)} profile{'' if len(profiles) == 1 else 's'}</div>
<div class="rows" style="max-width:700px">
  <div style="display:flex;align-items:baseline;justify-content:space-between;
    padding:13px 18px;border-bottom:1px solid var(--line);background:var(--surface-2)">
    <span class="k">ACCOUNT</span>
    <span style="font-family:var(--font-mono);font-size:12.5px">{_e(account)}</span>
  </div>
  <div class="plist">{rows}</div>
</div>
<div class="quiet" style="margin-top:12px;max-width:700px;line-height:1.55">A profile
  is made when the first read is filed under it. Most hold one.</div>
<style>
.plist a{{display:flex;align-items:baseline;justify-content:space-between;gap:16px;
  padding:14px 18px;border-bottom:1px solid var(--line);color:inherit}}
.plist a:hover{{background:var(--surface-2);color:inherit}}
.plist .nm{{font-family:var(--font-mono);font-size:13px;color:var(--ink);min-width:0;
  overflow:hidden;text-overflow:ellipsis}}
.plist .ct{{flex:none;display:flex;align-items:baseline;gap:6px}}
.plist .ct b{{font-family:var(--font-mono);font-size:13px;font-weight:600;
  color:var(--ink);font-variant-numeric:tabular-nums}}
.plist .ct i{{font-size:12px;color:var(--faint);font-style:normal}}
</style>""")


def settings_page(*, account: str) -> str:
    return shell("Settings", active="/settings", account=account, body=f"""
<h1>Settings</h1>
<div class="card" style="margin-top:18px;max-width:560px">
  <div class="k">ACCOUNT</div>
  <div style="margin-top:7px;font-family:var(--font-mono);font-size:15px;
    color:var(--ink)">{_e(account)}</div>
  <div class="quiet" style="margin-top:8px;line-height:1.55">Everything in the app
    is scoped to this account. There is nothing to switch to.</div>
  <div style="margin-top:18px;border-top:1px solid var(--line);padding-top:16px">
    <form method="post" action="/signout">
      <button type="submit" class="btn btn--quiet"
        style="font-weight:600">Sign out</button></form>
  </div>
</div>""")


_BACK_BAR = ('<div class="rk-appbar" style="background:#fff;border-bottom:1px solid '
             '#e7e5e0;padding:13px 24px;font:14px/1.5 \'Instrument Sans\',system-ui,'
             'sans-serif"><a href="/reads" style="font-size:13px;color:#6b6f76;'
             'text-decoration:none">← Back to reads</a></div>')


def with_back_bar(document: str) -> str:
    """One back link above the read, and nothing else.

    Opening a read LEAVES the application — no sidebar, no search, no product
    chrome. The report is a self-contained document that gets shared, and
    furniture around it would make it read as a page instead of a deliverable.

    The bar is injected into the rendered document rather than the document
    being re-rendered inside an app template, because there must stay exactly
    ONE renderer of a read (memory: report_surface_fidelity). Its styles are
    inline literals, not `var(--…)`, since the report owns that stylesheet and
    this bar must not depend on which tokens it happens to define.

    If `<body>` is not found the document is returned untouched: a missing
    back link is a wart, and a mangled read is a broken deliverable.
    """
    marker = "<body>"
    at = document.find(marker)
    if at == -1:
        return document
    cut = at + len(marker)
    return document[:cut] + "\n" + _BACK_BAR + document[cut:]


def error_page(heading: str, message: str, *, account: str = "demo") -> str:
    return shell(heading, active="", account=account, body=f"""
<h1>{_e(heading)}</h1>
<div class="card" style="margin-top:18px;max-width:700px">
  <p class="quiet" style="font-size:14px;line-height:1.6">{_e(message)}</p>
  <div style="margin-top:18px"><a href="/reads">← Back to reads</a></div>
</div>""")


# ---- new read ----------------------------------------------------------


def new_read_page(*, account: str, categories: list[tuple[str, str]],
                  audiences: list[str], jobs: list[tuple[str, str]],
                  brands: list[str], error: str = "",
                  filename: str = "") -> str:
    """One multipart post. The drop target IS the file input, so it works
    with JavaScript switched off — there is none on this page.

    The category list carries no NOT VALIDATED marker: the user's explicit
    call, 2026-08-03. The warning still arrives, on the review screen, before
    any credit is debited.
    """
    # value = the pack stem the engine needs, label = the human one. Two
    # separate things: the option text is for the operator, the value is what
    # `build_run_config` resolves a disposition library from.
    cat_opts = "".join(f'<option value="{_e(v)}">{_e(label)}</option>'
                       for v, label in categories)
    aud_opts = "".join(f"<option>{_e(a)}</option>" for a in audiences)
    job_opts = "".join(f'<option value="{_e(v)}">{_e(label)}</option>'
                       for v, label in jobs)
    brand_opts = "".join(f"<option>{_e(b)}</option>" for b in brands)

    if error:
        drop = f"""<label for="creative" class="drop"
  style="border-color:var(--leak);background:var(--leak-tint)">
  <b>Drop the ad creative here</b>
  <span class="exts">.PNG · .JPG · .WEBP</span>
  <input id="creative" name="asset" type="file" accept=".png,.jpg,.jpeg,.webp"
    required></label>
<div class="err"><b>REJECTED</b><div><span
  style="color:var(--ink)">{_e(error)}</span>
  <div style="margin-top:3px;font-family:var(--font-mono);font-size:10.5px;
    color:var(--faint)">{_e(filename)}</div></div></div>"""
    else:
        drop = """<label for="creative" class="drop">
  <span style="width:34px;height:34px;border-radius:8px;border:1.5px solid var(--faint);
    display:flex;align-items:center;justify-content:center">
    <svg width="17" height="17" viewBox="0 0 17 17" aria-hidden="true"><path
      d="M8.5 12.5V3.5M8.5 3.5 4.8 7.2M8.5 3.5l3.7 3.7" fill="none" stroke="#6b6f76"
      stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"></path><path
      d="M2.5 12v1.5h12V12" fill="none" stroke="#6b6f76" stroke-width="1.4"
      stroke-linecap="round"></path></svg></span>
  <b>Drop the ad creative here</b>
  <span class="exts">.PNG · .JPG · .WEBP</span>
  <input id="creative" name="asset" type="file" accept=".png,.jpg,.jpeg,.webp"
    required></label>"""

    return shell("New read", active="/reads/new", account=account, body=f"""
<h1>New read</h1>
<div class="under">Two phases. This one classifies the ad and resolves the panel —
  nothing is charged here.</div>
<form class="form" method="post" action="/reads/new" enctype="multipart/form-data">

  <div class="card">
    <div class="k">THE CREATIVE</div>
    {drop}
    <div class="fld">
      <label class="lbl" for="asset_label">LABEL</label>
      <div class="hint">How it should read in the report header.</div>
      <input id="asset_label" name="asset_label" type="text">
    </div>
    <div class="two">
      <div><label class="lbl" for="category">CATEGORY</label>
        <div class="hint">Which disposition library to read against.</div>
        <select id="category" name="category" required>{cat_opts}</select></div>
      <div><label class="lbl" for="audience_spec">AUDIENCE SPEC</label>
        <div class="hint">The audience this is aimed at.</div>
        <select id="audience_spec" name="audience_spec" required
          style="font-family:var(--font-mono);font-size:12px">{aud_opts}</select></div>
    </div>
  </div>

  <div class="card">
    <div class="k">THE BUY</div>
    <div class="fld">
      <label class="lbl" for="declared_targeting">DECLARED TARGETING</label>
      <div class="hint" style="max-width:600px">Their stated audience, in their
        words. A hint to the classifier — it never overrides what the creative
        itself reads as.</div>
      <textarea id="declared_targeting" name="declared_targeting" rows="2"></textarea>
    </div>
    <div class="two">
      <div><label class="lbl" for="purpose">THE AD'S JOB</label>
        <div class="hint">What it is being graded against.</div>
        <select id="purpose" name="purpose">{job_opts}</select></div>
      <div><label class="lbl" for="brand_profile">BRAND PROFILE</label>
        <div class="hint">Where the read gets filed.</div>
        <input id="brand_profile" name="brand_profile" type="text"
          list="brands" style="font-family:var(--font-mono);font-size:12px">
        <datalist id="brands">{brand_opts}</datalist></div>
    </div>
    <div class="check">
      <input id="marketer_led" name="marketer_led" type="checkbox" value="1" checked>
      <div><label for="marketer_led"><b>Marketer-led composition</b></label>
        <div class="hint" style="max-width:560px">Compose the panel from the declared
          audience. On for a real client read.</div></div>
    </div>
  </div>

  <div class="go">
    <button type="submit" class="btn" style="padding:12px 22px;font-size:13.5px">Prepare (~$0.15)</button>
    <span class="quiet">Preparing classifies the creative and resolves the panel.
      You review the cost before anything is committed.</span>
  </div>
</form>""")


def preparing_page(*, account: str, label: str, refresh: int = 2) -> str:
    """An indeterminate bar, which is honest ONLY here: the wait is under a
    minute and the engine reports nothing during it. Everywhere else in this
    app a moving thing means a real count moved."""
    return shell("Preparing the read", active="/reads/new", account=account,
                 head=f'<meta http-equiv="refresh" content="{refresh}">\n', body=f"""
<h1>New read</h1>
<div class="card prep">
  <div class="top">
    <div class="thumb" style="width:64px;height:64px;border-radius:8px"></div>
    <div style="flex:1;min-width:0">
      <div class="ttl">Preparing the read</div>
      <div class="quiet" style="margin-top:4px;line-height:1.5">Classifying the
        creative and resolving the panel. Usually under a minute — nothing is
        charged yet.</div>
    </div>
    <span class="working">WORKING</span>
  </div>
  <div class="bar"><i></i></div>
  <div style="margin-top:14px;font-family:var(--font-mono);font-size:11px;
    color:var(--faint)">{_e(label)}</div>
</div>""")


# ---- the review screen -------------------------------------------------


def flag_rows(flags: list[tuple[str, str, str, bool]]) -> str:
    """One row template for warnings and STOP flags alike.

    A gate row changes exactly two things — the tag is filled and the label is
    heavier. Same container, same hairline, same column. Eight of these read as
    a list; eight differently-shaped callouts read as a wall, and a wall is
    skipped.
    """
    if not flags:
        return ""
    rows = "".join(
        f'<div class="f{" f--stop" if stop else ""}">'
        f'<span class="t"><span>{_e(tag)}</span></span>'
        f'<span class="txt">{_e(title)}'
        f'{f"<em> — {_e(note)}</em>" if note else ""}</span></div>'
        for tag, title, note, stop in flags
    )
    return f'<div class="flags">{rows}</div>'


def review_page(*, account: str, run_id: str, label: str, meta: str,
                inferred: str, reasoning: str = "",
                dispositions: list[tuple[str, bool]] = (),
                panel_lines: list[str], panel_version: str,
                cost: str, cores: object,
                flags: list[tuple[str, str, str, bool]],
                stop_count: int = 0) -> str:
    """The money screen. Its own page, never a modal.

    The cost block borrows the report's ink-bordered treatment — the one
    weight this product reserves for "read this".

    Nothing here blocks the commit: the user's explicit call, 2026-08-03,
    taken after being shown that an unvalidated category yields a confident
    and wrong read. The flags are loud; the button is never disabled.
    """
    disp_rows = "".join(
        f'<div class="r"><div class="id">{_e(name)}</div><div class="v">'
        + ('<span class="within">WITHIN</span>' if within
           else '<span class="outside">outside</span>')
        + "</div></div>"
        for name, within in dispositions
    )
    lines = "".join(f"<div><i></i><span>{_e(t)}</span></div>" for t in panel_lines)
    within_n = sum(1 for _, w in dispositions if w)
    shape = ""
    if dispositions and within_n:
        shape = (f'<div class="note">{within_n} within and '
                 f"{len(dispositions) - within_n} outside is what a correctly "
                 "narrow ad looks like. It is not a fault in the buy.</div>")
    if stop_count == 1:
        stop_note = "One flag above is marked STOP — read it, then commit."
    elif stop_count > 1:
        stop_note = (f"{stop_count} flags above are marked STOP — read them, "
                     "then commit.")
    else:
        stop_note = ""

    return shell("Review, then commit", active="/reads/new", account=account, body=f"""
<div class="review">
  <div>
    <div class="phase2">Phase 2 of 2 · before a credit is debited</div>
    <h1>Review, then commit</h1>
    <div class="idline"><span class="thumb"></span>
      <span class="nm">{_e(label)}</span>
      <span class="meta">{_e(meta)}</span></div>
  </div>

  {flag_rows(flags)}

  <div class="card">
    <div class="k">WHAT THE CREATIVE READS AS</div>
    <div class="inferred">{_e(inferred)}</div>
    {f'<div class="note" style="margin-top:10px">{_e(reasoning)}</div>'
     if reasoning else ""}
    <div class="disp"><div class="h">DISPOSITION</div>
      <div class="h">AGAINST THAT TARGET</div>{disp_rows}</div>
    {shape}
  </div>

  <div class="card">
    <div class="panelhd"><span class="k">THE PANEL</span>
      <span>{_e(panel_version)}</span></div>
    <div class="plines">{lines}</div>
  </div>

  <form method="post" action="/reads/prepared/commit" style="margin:0">
    <input type="hidden" name="run_id" value="{_e(run_id)}">
    <div class="cost">
      <div class="k">COST</div>
      <p>Estimated <strong>{_e(cost)}</strong> — persona cores rendered:
        {_e(cores)}. Committing debits one credit and starts spending
        immediately.</p>
      <div class="go">
        <button type="submit" class="btn btn--big">Commit and run</button>
        {f'<span class="quiet">{_e(stop_note)}</span>' if stop_note else ""}
      </div>
      <div class="back"><a class="quiet" href="/reads/new">← cancel (no credit
        debited)</a></div>
    </div>
  </form>
</div>""")


# ---- a run in flight, and how it ends -----------------------------------


def elapsed_clock(progress: dict | None) -> str:
    """`updated_at - started_at`, never `now - started_at`.

    On a run whose worker is gone, a clock driven by the wall clock keeps
    counting and says the run is alive. This one stops where the run stopped,
    which is the true statement and the one the page is for.
    """
    if not progress:
        return "—"
    started, updated = progress.get("started_at"), progress.get("updated_at")
    if not isinstance(started, (int, float)) or not isinstance(updated, (int, float)):
        return "—"
    secs = int(max(0.0, updated - started))
    return f"{secs // 60:02d}:{secs % 60:02d}"


_PHASE_NOTE = {
    "reactions": "{n} people are meeting your ad.",
    "segments": "{n} segments.",
}


def _phases(view: list[dict], *, stopped_at: str | None = None) -> str:
    rows = []
    for p in view:
        state = p["state"]
        cls = {"done": "p--done", "running": "p--on"}.get(state, "")
        if stopped_at is not None and p["key"] == stopped_at:
            cls = "p--stop"
        total, done = p.get("total"), p.get("done")
        note = ""
        if total and p["key"] in _PHASE_NOTE:
            note = f"<em> — {_e(_PHASE_NOTE[p['key']].format(n=total))}</em>"
        counter, bar = "", ""
        if total:
            counter = f'<span class="ct">{done} of {total}</span>'
            pct = min(100, round((done or 0) / total * 100))
            bar = f'<div class="pbar"><i style="width:{pct}%"></i></div>'
        elif state == "pending":
            counter = '<span class="q">QUEUED</span>'
        mark = ""
        if state == "done":
            mark = ('<svg width="9" height="9" viewBox="0 0 9 9" aria-hidden="true">'
                    '<path d="M1.6 4.7 3.5 6.6 7.4 2.7" fill="none" stroke="#fff" '
                    'stroke-width="1.6" stroke-linecap="round" '
                    'stroke-linejoin="round"></path></svg>')
        elif state == "running" and cls != "p--stop":
            mark = "<i></i>"
        stop_tail = ('<span class="q" style="color:var(--leak)">STOPPED HERE</span>'
                     if cls == "p--stop" else "")
        rows.append(
            f'<div class="p {cls}"><div class="hd">'
            f'<span class="dot">{mark}</span>'
            f'<span class="nm">{_e(p["label"])}{note}</span>'
            f"{counter}{stop_tail}</div>{bar}</div>"
        )
    return f'<div class="phases">{"".join(rows)}</div>'


def _runhead(label: str, run_id: str, state_word: str, elapsed: str = "") -> str:
    clock = (f'<div class="elapsed"><div class="k">ELAPSED</div>'
             f"<div>{_e(elapsed)}</div></div>" if elapsed else "")
    return f"""<div class="runhead">
  <div class="thumb"></div>
  <div style="flex:1;min-width:0">
    <div class="st">{_e(state_word)}</div>
    <h1>{_e(label)}</h1>
    <div class="rid">{_e(run_id)}</div>
  </div>{clock}</div>"""


def running_page(*, account: str, label: str, run_id: str,
                 phases: list[dict], elapsed: str, waiting: bool = False,
                 refresh: int = 10) -> str:
    """Four to eight minutes, watched. The only moving parts are real counts."""
    # A committed run that has not written its first phase yet. Saying so beats
    # five identical QUEUED rows, which read as "nothing is happening".
    wait = ('<div class="quiet" style="margin-top:14px">Waiting for the first '
            "phase to report.</div>" if waiting else "")
    return shell("Running", active="/reads", account=account,
                 head=f'<meta http-equiv="refresh" content="{refresh}">\n', body=f"""
<div class="wrap">
  {_runhead(label, run_id, "RUNNING", elapsed)}
  {_phases(phases)}
  {wait}
  <div class="foot">
    <span class="quiet">No time remaining is shown — the phases don't run at a
      predictable rate, so any estimate would be made up. The counters above are
      the real thing.</span>
    <span class="refresh">refreshes automatically every {refresh}s</span>
  </div>
</div>""")


def complete_page(*, account: str, label: str, run_id: str, key: str,
                  decision: str, health: str, degraded: str = "") -> str:
    """Quiet. One action, and the two facts worth knowing before opening it."""
    gloss = DECISION_TAGLINE.get(decision, "")
    if degraded:
        health_card = f"""<div class="bad">
      <div class="k">PANEL HEALTH</div>
      <div class="v">{_e(health)}</div>
      <div class="g">{_e(degraded)}</div></div>"""
        after = ('<span class="quiet">The report carries the same qualification '
                 "in its header.</span>")
    else:
        health_card = f"""<div>
      <div class="k">PANEL HEALTH</div>
      <div class="v">{_e(health)}</div>
      <div class="g">Everyone in the panel responded.</div></div>"""
        after = '<a class="quiet" href="/reads">Back to reads</a>'
    return shell("Read complete", active="/reads", account=account, body=f"""
<div class="card done">
  <div class="runhead">
    <div class="thumb"></div>
    <div style="flex:1;min-width:0">
      <div class="ok"><i><svg width="9" height="9" viewBox="0 0 9 9" aria-hidden="true">
        <path d="M1.6 4.7 3.5 6.6 7.4 2.7" fill="none" stroke="#fff" stroke-width="1.6"
        stroke-linecap="round" stroke-linejoin="round"></path></svg></i>
        <b>READ COMPLETE</b></div>
      <h1 style="margin-top:8px">{_e(label)}</h1>
      <div class="rid">{_e(run_id)}</div>
    </div>
  </div>
  <div class="facts">
    <div><div class="k">DECISION</div>
      <div class="v"><span class="mk" style="{_mark(decision)}"></span>{_e(decision)}</div>
      <div class="g">{_e(gloss)}</div></div>
    {health_card}
  </div>
  <div class="after">
    <a class="btn" href="/reads/{_e(key)}">Open the Creative Read</a>
    {after}
  </div>
</div>""")


def failed_page(*, account: str, label: str, run_id: str, error: str,
                phases: list[dict], stopped_at: str | None) -> str:
    """Answers the question the user actually has: was I charged."""
    return shell("Run failed", active="/reads", account=account, body=f"""
<div class="card dead">
  <div class="st" style="color:var(--leak)">RUN FAILED</div>
  <h1>{_e(label)}</h1>
  <div class="rid">{_e(run_id)}</div>
  <div class="k" style="margin-top:16px">ERROR</div>
  <div class="mono">{_e(error or "The worker stopped without recording a reason.")}</div>
  <div class="charged">
    <div class="k" style="color:var(--ink)">WERE YOU CHARGED</div>
    <p>A credit was debited when you committed this run. It has not been
      returned.</p>
  </div>
</div>
<div class="wrap" style="margin-top:16px">{_phases(phases, stopped_at=stopped_at)}</div>
<div class="after" style="margin-top:16px">
  <a class="btn btn--quiet" href="/reads/new">Start a new read</a>
  <a class="quiet" href="/reads">Back to reads</a>
</div>""")


def interrupted_page(*, account: str, label: str, run_id: str, key: str,
                     command: str, recoverable: bool, cost_note: str,
                     phases: list[dict], stopped_at: str | None) -> str:
    """The worker is gone but the transcripts are on disk — the expensive half
    of the run already happened and does not need paying for twice."""
    action = f"""<form method="post" action="/reads/{_e(key)}/replay"
    style="margin:18px 0 0;display:flex;align-items:center;gap:14px;flex-wrap:wrap">
    <button type="submit" class="btn">Recover this run</button>
    <span class="quiet">{_e(cost_note)}</span>
  </form>""" if recoverable else (
        f'<div class="quiet" style="margin-top:18px">{_e(cost_note)}</div>')
    return shell("Run interrupted", active="/reads", account=account, body=f"""
<div class="card dead">
  <div class="st" style="color:var(--faint)">RUN INTERRUPTED · {
      "RECOVERABLE" if recoverable else "NOT RECOVERABLE"}</div>
  <h1>{_e(label)}</h1>
  <div class="rid">{_e(run_id)}</div>
  <p style="margin-top:16px;font-size:14px;line-height:1.6;color:var(--ink)">The
    worker thread is gone and the run never completed. Recover it rather than
    paying for the panel again — the agent transcripts are already on disk.</p>
  <div class="k" style="margin-top:16px">RECOVERY</div>
  <div class="mono">{_e(command)}</div>
  {action}
</div>
<div class="wrap" style="margin-top:16px">{_phases(phases, stopped_at=stopped_at)}</div>""")
