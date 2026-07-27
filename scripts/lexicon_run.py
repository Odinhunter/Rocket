"""PAID — build a lexicon (the tabled word-cloud pass) for one finished run.

    .venv/bin/python scripts/lexicon_run.py <run_dir>

Three small Sonnet calls (~$0.07): one proposes candidate terms, then ONE PER
AUDIENCE so the target and everyone else are each judged from their own
sentences. Writes lexicon.json into the run directory.

The feature is TABLED (see agent/lexicon.py) — this script exists so it stays
runnable without reconstructing the driver.

Wraps the client to capture exact token usage, so the cost printed at the end
is measured rather than estimated: telemetry no-ops without a run context and
this deliberately runs outside RunService.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Explicit path + override: the ambient environment may define an EMPTY
# ANTHROPIC_API_KEY, and load_dotenv() will not replace an already-set var.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
# Explicit path + override: the ambient environment may define an EMPTY
# ANTHROPIC_API_KEY, and load_dotenv() will not replace an already-set var.
load_dotenv(_ROOT / ".env", override=True)

import os  # noqa: E402

if not (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
    raise SystemExit("no ANTHROPIC_API_KEY resolved - refusing to call")

import anthropic  # noqa: E402

from agent.config import DEFAULT_MODEL_VERSIONS, DEFAULT_TEMPERATURES  # noqa: E402
from agent.lexicon import (  # noqa: E402
    assemble_lexicon, build_corpus, classify_terms, count_term,
    load_transcripts, propose_terms,
)

# sonnet-4-6 $/MTok: input, output, cache_read, cache_write (agent/telemetry.py)
RATES = (3.0, 15.0, 0.3, 3.75)


class Recorder:
    """Minimal pass-through that remembers usage for every call."""

    def __init__(self, inner):
        self._inner = inner
        self.usages = []

    @property
    def messages(self):
        return self

    def create(self, **kw):
        r = self._inner.messages.create(**kw)
        self.usages.append(r.usage)
        return r

    def cost(self) -> float:
        total = 0.0
        for u in self.usages:
            total += (getattr(u, "input_tokens", 0) or 0) * RATES[0] / 1e6
            total += (getattr(u, "output_tokens", 0) or 0) * RATES[1] / 1e6
            total += (getattr(u, "cache_read_input_tokens", 0) or 0) * RATES[2] / 1e6
            total += (getattr(u, "cache_creation_input_tokens", 0) or 0) * RATES[3] / 1e6
        return total


class Cfg:
    model_versions = dict(DEFAULT_MODEL_VERSIONS)
    temperatures = dict(DEFAULT_TEMPERATURES)


run_dir = Path(sys.argv[1])
raw = json.loads((run_dir / "run.json").read_text())
within = ((raw.get("report") or {}).get("decision") or {}).get("within_dispositions") or []

corpus = build_corpus(load_transcripts(run_dir), within)
print(f"corpus: {corpus.n} agents ({corpus.excluded} excluded), "
      f"within-target = {within}")

client = Recorder(anthropic.Anthropic(max_retries=5))
cfg = Cfg()

candidates = propose_terms(corpus, cfg, client)
print(f"\nmodel proposed {len(candidates)} candidate terms")

grounded = [t for t in (count_term(corpus, " ".join(c.lower().split()))
                        for c in dict.fromkeys(candidates) if c)
            if t.people >= 2]
dropped = [c for c in candidates
           if not any(t.term == " ".join(c.lower().split()) for t in grounded)]
print(f"grounded (>=2 people): {len(grounded)}   DROPPED as ungrounded/n=1: "
      f"{len(dropped)}")

# Judge each audience from ITS OWN sentences.
in_terms = [t for t in grounded if t.within >= 2]
out_terms = [t for t in grounded if t.outside >= 2]
print(f"\njudging separately: {len(in_terms)} terms your target used, "
      f"{len(out_terms)} terms everyone else used")
s_within = classify_terms(in_terms, cfg, client, audience="within")
s_outside = classify_terms(out_terms, cfg, client, audience="outside")

lex = assemble_lexicon(corpus, [t.term for t in grounded], {},
                       sentiments_within=s_within, sentiments_outside=s_outside)

for audience, label in (("within", "YOUR TARGET"), ("outside", "EVERYONE ELSE")):
    rows = lex.for_audience(audience)
    n = lex.audience_n(audience)
    print(f"\n=== {label} ({n} people) — {len(rows)} terms ===")
    for sent, mark in (("bad", "RED  "), ("good", "GREEN"), ("neutral", "grey ")):
        group = [t for t in rows if t.sentiment_for(audience) == sent]
        if not group:
            continue
        print(f"  {mark} ({len(group)})")
        for t in sorted(group, key=lambda x: -x.share(audience))[:9]:
            c = t.within if audience == "within" else t.outside
            print(f"     {t.term:28} {c:>3}/{n} = {t.share(audience):.0%}")

(run_dir / "lexicon.json").write_text(json.dumps(lex.to_dict(), indent=2))
print(f"\nwrote {run_dir / 'lexicon.json'}")
print(f"API calls: {len(client.usages)}   MEASURED COST: ${client.cost():.4f}")
