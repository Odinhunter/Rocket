"""The operator server's own pages — console, capture forms, blinded reveal.

Reports are NOT rendered here. They come from agent/dashboard_html.py through
server/runs.py; this module only builds the scaffolding around them, and it
borrows that module's stylesheet (dashboard_html.PAGE_CSS) so the session and
the deliverable read as one product rather than two.

Stdlib only, matching the engine's no-template-dependency rule.
"""

from __future__ import annotations

import html

from agent.dashboard_html import PAGE_CSS
from server.runs import RunRef
from server.sessions import SLOTS, Session

# Form + console styling. Everything visual it needs beyond PAGE_CSS, which
# carries the palette, the type scale and the light/dark handling.
_EXTRA_CSS = """
a{color:var(--accent-ink);}
:root[data-theme="dark"] a,@media (prefers-color-scheme:dark){a{color:var(--accent);}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:13px;
  padding:18px 20px;box-shadow:var(--shadow);margin-top:14px;}
.card h3{margin:0 0 4px;font-size:16px;font-weight:700;}
label{display:block;margin-top:16px;font-size:14px;color:var(--ink);font-weight:600;}
label .hint{display:block;font-weight:400;color:var(--muted);font-size:13px;margin-top:2px;}
input[type=text],input[type=password],textarea,select{width:100%;margin-top:7px;padding:10px 12px;font:inherit;
  font-size:15px;color:var(--ink);background:var(--surface-2);border:1px solid var(--line);
  border-radius:9px;}
textarea{min-height:76px;resize:vertical;}
button{margin-top:22px;padding:11px 20px;font:inherit;font-weight:650;font-size:15px;
  color:var(--on-accent);background:var(--accent);border:0;border-radius:9px;
  cursor:pointer;}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px;font-family:var(--font-mono);
  font-size:11px;letter-spacing:.06em;text-transform:uppercase;}
.steps span{border:1px solid var(--line);border-radius:999px;padding:4px 11px;color:var(--faint);}
.steps span.on{border-color:var(--accent);color:var(--accent-ink);background:var(--accent-tint);}
:root[data-theme="dark"] .steps span.on{color:var(--accent);}
.steps span.did{color:var(--good);border-color:var(--good);}
.slots{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px;}
@media (max-width:620px){.slots{grid-template-columns:1fr;}}
.slot{display:block;text-align:center;padding:26px 16px;border:1px solid var(--line);
  border-radius:13px;background:var(--surface);text-decoration:none;box-shadow:var(--shadow);}
.slot b{display:block;font-size:24px;color:var(--ink);}
.slot span{font-size:13px;color:var(--muted);}
table.rows{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;}
table.rows th{text-align:left;font-family:var(--font-mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--faint);font-weight:600;
  padding:6px 10px 6px 0;border-bottom:1px solid var(--line);}
table.rows td{padding:8px 10px 8px 0;border-bottom:1px solid var(--line);color:var(--muted);
  vertical-align:top;}
table.rows td b{color:var(--ink);font-weight:600;}
.phases div{padding:7px 0;color:var(--faint);font-size:15px;}
.phases div+div{border-top:1px solid var(--line);}
.phases .mark{display:inline-block;width:18px;font-family:var(--font-mono);}
.phases .done{color:var(--muted);}
.phases .done .mark{color:var(--good);}
.phases .running{color:var(--ink);font-weight:650;}
.phases .running .mark{color:var(--accent);}
.phases .stopped{color:var(--ink);font-weight:650;}
.phases .stopped .mark{color:var(--leak);}
.phases b{font-family:var(--font-mono);font-weight:650;}
.kv{margin-top:10px;font-size:14px;}
.kv div{padding:5px 0;border-bottom:1px solid var(--line);}
.kv b{color:var(--ink);}
"""


def _e(text: object) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def shell(title: str, body: str) -> str:
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{_e(title)}</title>\n<style>{PAGE_CSS}{_EXTRA_CSS}</style>\n"
        f'</head>\n<body>\n<div class="page">{body}</div>\n</body>\n</html>\n'
    )


def _head(eyebrow: str, heading: str, sub: str = "") -> str:
    return (
        f'<div class="eyebrow">{_e(eyebrow)}</div><h1>{_e(heading)}</h1>'
        + (f'<p style="margin-top:10px">{_e(sub)}</p>' if sub else "")
    )


def _steps(session: Session) -> str:
    order = ["predict", "reveal", "react", "done"]
    label = {"predict": "1 · predict", "reveal": "2 · reveal",
             "react": "3 · react", "done": "captured"}
    here = order.index(session.stage)
    out = []
    for i, key in enumerate(order):
        cls = "did" if i < here else ("on" if i == here else "")
        out.append(f'<span class="{cls}">{label[key]}</span>')
    return f'<div class="steps">{"".join(out)}</div>'


# ---- console ----------------------------------------------------------


def console(sessions: list[Session], runs: list[RunRef]) -> str:
    rows = "".join(
        f"<tr><td><b>{_e(s.company or s.contact)}</b><br>{_e(s.ad_label)}</td>"
        f"<td>{_e(s.contact)}</td><td>{_e(s.stage)}</td>"
        f'<td><a href="/sessions/{_e(s.session_id)}">open</a></td></tr>'
        for s in sessions
    ) or '<tr><td colspan="4">No sessions yet.</td></tr>'

    options = "".join(
        f'<option value="{_e(r.key)}" data-category="{_e(r.category)}">'
        f"{_e(r.asset_label)} — {_e(r.decision or 'no decision')} · "
        f"{_e(r.run_id)}</option>"
        for r in runs
    )
    if not runs:
        new = (
            '<div class="card"><h3>No finished reads on disk</h3><p>A session '
            "needs a Creative Read for their ad and one for a different ad (the "
            "decoy). Run each through the engine first — that is a paid run, so "
            "price it with scripts/preflight_cost.py and get an explicit go.</p>"
            "</div>"
        )
    else:
        new = f"""<form class="card" method="post" action="/sessions">
  <h3>New session</h3>
  <p>Their prediction is captured before the read is shown; the server will not
     open the reveal until it is on record.</p>
  <label>Contact<input type="text" name="contact" required></label>
  <label>Company<input type="text" name="company" required></label>
  <label>Their ad
    <span class="hint">The one they brought, with the outcome they have not told you yet.</span>
    <select name="real_key" required>{options}</select></label>
  <label>Decoy read
    <span class="hint">A read of a DIFFERENT ad in the SAME category, shown
      unlabeled beside theirs. Not optional: a plausible report reads the same
      whether it is right or wrong, so this is the only check on whether the
      diagnosis discriminates — and a cross-category decoy gives itself away
      without either diagnosis being read, which proves nothing.</span>
    <select name="decoy_key" required>{options}</select></label>
  <label>Ad label (your notes only, never shown to them)
    <input type="text" name="ad_label"></label>
  <button type="submit">Start session</button>
</form>
<script>
// Convenience only — the server refuses a cross-category pair regardless, so a
// direct POST cannot get past it either.
(function () {{
  var form = document.currentScript.previousElementSibling;
  var real = form.querySelector('[name=real_key]');
  var decoy = form.querySelector('[name=decoy_key]');
  var all = Array.prototype.slice.call(decoy.options);
  function sync() {{
    var want = real.selectedOptions[0].dataset.category;
    decoy.innerHTML = '';
    all.forEach(function (o) {{
      if (o.dataset.category === want && o.value !== real.value) {{
        decoy.appendChild(o.cloneNode(true));
      }}
    }});
    if (!decoy.options.length) {{
      var none = document.createElement('option');
      none.textContent = 'No other read in this category — run one first';
      none.value = '';
      decoy.appendChild(none);
    }}
  }}
  real.addEventListener('change', sync);
  sync();
}})();
</script>"""

    run_rows = "".join(
        f"<tr><td><b>{_e(r.asset_label)}</b></td><td>{_e(r.decision)}</td>"
        f"<td>{_e(r.brand_profile_id)}</td>"
        f'<td><a href="/reads/{_e(r.key)}">view read</a></td></tr>'
        for r in runs[:40]
    ) or '<tr><td colspan="4">None.</td></tr>'

    return shell("Rocket — operator console", f"""
{_head("Rocket · operator", "Brand-manager sessions",
       "Predict, then reveal. Run the ads through the engine beforehand.")}
<section><h2>Sessions</h2>
  <table class="rows"><tr><th>Company / ad</th><th>Contact</th><th>Stage</th><th></th></tr>
  {rows}</table></section>
<section><h2>Start one</h2>{new}</section>
<section><h2>Finished reads on disk</h2>
  <table class="rows"><tr><th>Creative</th><th>Decision</th><th>Brand</th><th></th></tr>
  {run_rows}</table>
  <div class="slots" style="grid-template-columns:1fr">
    <a class="slot" href="/reads/new"><b>Run a new ad</b>
      <span>Paid — prepare (~$0.15), then confirm the full run</span></a>
  </div></section>
<form method="post" action="/signout" style="margin-top:20px"><button type="submit" style="background:none;border:0;padding:0;font:inherit;font-size:14px;color:var(--accent-ink);cursor:pointer;text-decoration:underline">Sign out</button></form>
""")


# ---- session ----------------------------------------------------------


def session_page(session: Session) -> str:
    nxt = {
        "predict": ('<a class="slot" href="/sessions/%s/predict"><b>Capture their '
                    'prediction</b><span>Before anything is shown</span></a>'),
        "reveal": ('<a class="slot" href="/sessions/%s/reveal"><b>Reveal the '
                   'reads</b><span>Two, unlabeled</span></a>'),
        "react": ('<a class="slot" href="/sessions/%s/react"><b>Capture their '
                  'reaction</b><span>The four questions</span></a>'),
        "done": ('<a class="slot" href="/sessions/%s/export"><b>Export the '
                 'row</b><span>JSON</span></a>'),
    }[session.stage] % _e(session.session_id)

    caught = session.decoy_caught()
    summary = ""
    if session.stage == "done":
        summary = f"""<section><h2>Captured</h2>
  <div class="card"><div class="kv">
    <div><b>Decoy caught:</b> {'yes' if caught else 'no' if caught is False else '—'}
      — they picked Read {_e((session.reaction or {}).get('decoy_pick', '?'))};
      theirs was Read {_e(session.slot_of_real())}.</div>
    <div><b>Predicted verdict:</b> {_e((session.prediction or {}).get('predicted_verdict', ''))}</div>
    <div><b>Verdict match:</b> {_e((session.reaction or {}).get('verdict_match', ''))}</div>
    <div><b>Would pilot a live ad:</b> {_e((session.reaction or {}).get('pilot_live_ad', ''))}</div>
  </div></div></section>"""

    return shell(f"Session — {session.company}", f"""
{_head("Session", session.company or session.contact,
       f"{session.contact} · {session.ad_label}" if session.ad_label else session.contact)}
{_steps(session)}
<section><h2>Next</h2><div class="slots">{nxt}</div></section>
{summary}
<section><h2></h2><p><a href="/operator">← all sessions</a></p></section>
""")


def predict_page(session: Session) -> str:
    return shell("Predict — before the reveal", f"""
{_head("Step 1 of 3 · before the reveal", "What do they say, before they see it?",
       "Captured now so their reaction later is not hindsight agreement. This is "
       "also the borrowed ground truth for the backtest.")}
{_steps(session)}
<form class="card" method="post" action="/sessions/{_e(session.session_id)}/predict">
  <label>What did this ad actually do in-market?
    <span class="hint">Their words. Flopped / mid / won — now they say it.</span>
    <textarea name="outcome" required></textarea></label>
  <label>Numbers, if they have them
    <span class="hint">CTR, ROAS, spend, whatever they will share.</span>
    <input type="text" name="outcome_metrics"></label>
  <label>Their call, if they were grading it
    <select name="predicted_verdict">
      <option value="">— they would rather not guess —</option>
      <option>SCALE</option><option>ITERATE</option>
      <option>RETARGET</option><option>REBUILD</option>
    </select></label>
  <label>What did they think the top 2–3 problems were?
    <textarea name="predicted_problems" required></textarea></label>
  <label>What did they think was working?
    <textarea name="predicted_working"></textarea></label>
  <button type="submit">Save and unlock the reveal</button>
</form>
""")


def reveal_page(session: Session) -> str:
    slots = "".join(
        f'<a class="slot" href="/sessions/{_e(session.session_id)}/report/{s}" '
        f'target="_blank" rel="noopener"><b>Read {s}</b>'
        f"<span>opens in a new tab</span></a>"
        for s in SLOTS
    )
    return shell("Reveal — two reads, unlabeled", f"""
{_head("Step 2 of 3 · the reveal", "Two reads. One is theirs.",
       "Neither carries the creative, the ad name or the targeting — only the "
       "diagnosis. Let them read both before you ask which is which.")}
{_steps(session)}
<section><h2>The reads</h2><div class="slots">{slots}</div></section>
<section><h2>Say this out loud</h2>
  <div class="card"><p>Don't act on this specific report yet — it is unvalidated,
    and a wrong call acted on is exactly what would burn you as a customer.</p></div>
</section>
<section><h2>Then</h2><div class="slots">
  <a class="slot" href="/sessions/{_e(session.session_id)}/react">
    <b>Capture their reaction</b><span>The four questions</span></a>
</div></section>
""")


def react_page(session: Session) -> str:
    slot_opts = "".join(f"<option>{s}</option>" for s in SLOTS)
    return shell("Reaction", f"""
{_head("Step 3 of 3 · after the reveal", "What did it land as?",
       "Ask the behavioural questions, not 'would you pay for this'.")}
{_steps(session)}
<form class="card" method="post" action="/sessions/{_e(session.session_id)}/react">
  <label>Which read was theirs?
    <span class="hint">Ask before you tell them. If they cannot separate the two
      diagnoses, that is a finding about the product, not about them.</span>
    <select name="decoy_pick" required>
      <option value="">— they could not tell —</option>{slot_opts}</select></label>
  <label>How did they tell (or fail to)?<textarea name="decoy_note"></textarea></label>

  <label>Did the engine's call match what the ad actually did?
    <span class="hint">The backtest signal.</span>
    <select name="verdict_match" required>
      <option>yes</option><option>partial</option><option>no</option></select></label>

  <label>Diagnosis vs their own theory
    <select name="diagnosis_overlap" required>
      <option>high</option><option>partial</option><option>none</option></select></label>
  <label>Where do they differ, and does either side have data?
    <span class="hint">Their theory is a second expert opinion, not consumer truth.</span>
    <textarea name="diagnosis_note"></textarea></label>

  <label>Anything here they did not already know, or would act on?
    <select name="anything_new" required>
      <option>yes</option><option>no</option></select></label>
  <label>What?<textarea name="anything_new_what"></textarea></label>

  <label>Would they have run this ad differently if they had seen this first?
    <select name="run_differently" required>
      <option>yes</option><option>no</option></select></label>
  <label>What would they have changed?<textarea name="run_differently_what"></textarea></label>

  <label>Would they run a live, upcoming ad through this before launching?
    <span class="hint">The willingness signal that counts. A stated price from a
      warm contact is near-worthless.</span>
    <select name="pilot_live_ad" required>
      <option>yes</option><option>maybe</option><option>no</option></select></label>
  <label>Their words<textarea name="pilot_note"></textarea></label>
  <button type="submit">Save the row</button>
</form>
""")


def blocked_page(session: Session, message: str) -> str:
    return shell("Not yet — capture the prediction first", f"""
{_head("Blocked on purpose", "The prediction comes first")}
<div class="card"><p>{_e(message)}</p></div>
<section><h2>Next</h2><div class="slots">
  <a class="slot" href="/sessions/{_e(session.session_id)}/predict">
    <b>Capture their prediction</b><span>Then the reveal opens</span></a>
</div></section>
""")


def error_page(heading: str, message: str) -> str:
    return shell(heading, f"""
{_head("Rocket · operator", heading)}
<div class="card"><p>{_e(message)}</p></div>
<p style="margin-top:18px"><a href="/operator">← operator console</a></p>
""")


# ---- public: the landing placeholder and the login ---------------------


def landing_page(contact_email: str = "") -> str:
    """A holding page until the user's own landing design lands (P4).

    It lists nothing. `/` is the one route served to anyone who finds the
    address, and a helpful "recent reads" strip here would publish a named
    client's unreleased creative to the open internet. Sign in, and a way to
    reach a human. That is the whole page.

    No category is named, on the user's explicit call: the engine is validated
    on one category today and marketing that fact narrows the product to it.
    """
    mail = (
        f'<a class="slot" href="mailto:{_e(contact_email)}"><b>Talk to us</b>'
        "<span>There is no signup — this is how you reach us</span></a>"
        if contact_email else ""
    )
    return shell("Rocket", f"""
{_head("Rocket", "See how an ad lands before you spend on it.",
       "A panel of simulated buyers reacts to your creative, and you get back "
       "what stopped them, what lost them, and what to change.")}
<section><div class="slots">
  <a class="slot" href="/login"><b>Sign in</b><span>For accounts we have set up</span></a>
  {mail}
</div></section>
""")


def login_page(*, error: str = "", next_url: str = "",
               configured: bool = True) -> str:
    """The sign-in form.

    One field, because there is one shared password and no user table. The
    failure text never distinguishes "wrong password" from anything else.
    """
    if not configured:
        return shell("Sign in", f"""
{_head("Rocket", "Sign-in is not configured")}
<div class="warn"><b>No password is set on this server</b>ROCKET_APP_PASSWORD
  is empty, so no sign-in can succeed and every page behind it stays closed.
  That is deliberate — an unconfigured server does not fall open.</div>
""")
    hidden = (f'<input type="hidden" name="next" value="{_e(next_url)}">'
              if next_url else "")
    warn = f'<div class="warn"><b>Try again</b>{_e(error)}</div>' if error else ""
    return shell("Sign in", f"""
{_head("Rocket", "Sign in")}
{warn}
<form class="card" method="post" action="/login">
  {hidden}
  <label>Password<input type="password" name="password" required autofocus
    autocomplete="current-password"></label>
  <button type="submit">Sign in</button>
</form>
""")


# The run flow's pages — new_run_page, preparation_page, run_status_page and
# _phase_list — lived here until 2026-08-03. They are gone rather than kept as
# a second way to start a run: two renderers of the same paid flow is the drift
# trap this codebase already paid for once (memory: report_surface_fidelity).
# The product surface is server/app_html.py, built from the user's design.
