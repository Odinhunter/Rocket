"""lexicon — the words people actually used about the creative, and whether
each one is working for the brand or against it.

A read-only post-pass over `transcripts.json`. It adds NOTHING to any agent
prompt and does not touch the assess/prescribe layer: v2.4 proved that adding
a question to a validated prompt moves the metrics it was meant to observe
(the probe-contamination finding), and the reaction surface is frozen and
pinned by tests/test_reaction_surface.py. Reading artifacts that already exist
cannot contaminate anything, and it means this can be developed and re-run
against finished runs for the price of one small call.

Two rules this module exists to enforce:

  1. THE MODEL NEVER REPORTS A NUMBER. It proposes candidate terms and it
     judges sentiment. Every count is computed here, in code, by exact match
     against the corpus. A term the model proposes that nobody actually said
     is dropped, not reported. This is the grounding-as-a-filter principle
     from v2.2 applied to word frequency.

  2. THE READBACK SLOT IS EXCLUDED. R2 asks the persona "what is this
     selling", so they recite the ad's own copy back. A word cloud built over
     R2 measures the ad's headline, not consumer reaction — the exact
     mechanism that made brand_recall unmeasurable in v2.4 and that
     docs/v3_discriminant_check.md §5 turned into a standing rule. R2 is
     removed before a single word is counted.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Reaction sections, by number. R2 is the readback slot — see the module
# docstring. Anything not listed here is still included; only R2 is special.
READBACK_SECTION = 2

# Section headers are model-authored and their formatting varies by protocol
# generation. Verified against all 3,722 transcripts on disk: with the
# delimiter OPTIONAL this matches 100% of them; requiring a colon drops 5.2%
# (runs that write "**R2 COMPREHENSION**" on its own line), and every dropped
# transcript is one whose readback slot could not be found to be excluded.
_SECTION_RE = re.compile(
    r"^[ \t]*[*_#>\-]*[ \t]*R(?P<num>\d+)[ \t]*"
    r"(?P<label>[A-Za-z][A-Za-z _/-]*?)[ \t]*"
    r"(?:\**[ \t]*[:\-–—]|\**[ \t]*$)",
    re.MULTILINE,
)

# A trailing JSON object carries the structured action/next_step. It is data,
# not speech — counting words out of it would inflate protocol vocabulary
# ("scroll_past", "reasoning") into the cloud.
_TRAILING_JSON_RE = re.compile(r"\{[^{}]*\"(?:action|next_step)\"[^{}]*\}", re.S)

# If more than this fraction of the panel cannot be split, something about the
# transcript format has changed and the exclusion guard can no longer be
# trusted — abort rather than emit a cloud that may be full of readback. Mirrors
# the L1 panel-resilience rule: survive a few strays, abort on a gutted panel.
_MAX_UNSPLITTABLE = 0.10

SENTIMENT_VALUES = ("good", "bad", "neutral")


def split_sections(text: str) -> dict[int, str]:
    """Split one reaction into {section_number: text}.

    Returns {} when no section header is found at all — the caller must treat
    that as "cannot exclude the readback slot", never as "no readback here".
    """
    marks = [(m.start(), m.end(), int(m.group("num")))
             for m in _SECTION_RE.finditer(text or "")]
    if not marks:
        return {}
    out: dict[int, str] = {}
    for i, (_, end, num) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = text[end:stop].strip()
        # A repeated section number (protocol drift, or the model restating)
        # appends rather than overwrites, so nothing is silently lost.
        out[num] = f"{out[num]}\n{body}".strip() if num in out else body
    return out


def reaction_text(transcript: dict, *, exclude: tuple[int, ...] = (READBACK_SECTION,)
                  ) -> str | None:
    """The speech of one persona with the readback slot removed.

    None means the sections could not be found, so the readback slot could not
    be excluded. The caller drops that agent — including it would be exactly
    the contamination this module exists to prevent.
    """
    joined = "\n".join(
        t for t in ((transcript.get("encoding_text") or ""),
                    (transcript.get("reflection_text") or "")) if t
    )
    joined = _TRAILING_JSON_RE.sub(" ", joined)
    sections = split_sections(joined)
    if not sections or READBACK_SECTION not in sections:
        return None
    return "\n".join(body for num, body in sorted(sections.items())
                     if num not in exclude).strip()


@dataclass
class CorpusEntry:
    agent_id: str
    disposition: str
    within_target: bool
    text: str


@dataclass
class Corpus:
    entries: list[CorpusEntry] = field(default_factory=list)
    excluded: int = 0

    @property
    def n(self) -> int:
        return len(self.entries)

    def sample_text(self, limit: int = 60, chars: int = 900) -> str:
        """A bounded slice for the proposal call. Terms are counted against the
        FULL corpus afterwards, so sampling here costs coverage of rare words,
        never accuracy of a reported number."""
        step = max(1, self.n // limit) if self.n > limit else 1
        picked = self.entries[::step][:limit]
        return "\n\n---\n\n".join(
            f"[{e.disposition}{' · target' if e.within_target else ''}]\n"
            f"{e.text[:chars]}" for e in picked
        )


def build_corpus(transcripts: list[dict], within_dispositions: list[str]) -> Corpus:
    """Every agent's speech, readback removed, tagged in/out of target.

    The whole panel, not the target slice: 'who else responded, and in what
    words' is the question this exists to answer.
    """
    wanted = set(within_dispositions or [])
    corpus = Corpus()
    for t in transcripts or []:
        text = reaction_text(t)
        if not text:
            corpus.excluded += 1
            continue
        disp = str(t.get("disposition_label") or "")
        corpus.entries.append(CorpusEntry(
            agent_id=str(t.get("agent_id") or ""), disposition=disp,
            within_target=disp in wanted, text=text,
        ))
    total = corpus.n + corpus.excluded
    if total and corpus.excluded / total > _MAX_UNSPLITTABLE:
        raise ValueError(
            f"{corpus.excluded} of {total} transcripts could not be split into "
            "reaction sections, so the readback slot (R2) cannot be excluded "
            f"for them. Refusing to build a lexicon that may be measuring the "
            "ad's own copy back. Check the transcript format against "
            "agent/lexicon.py:_SECTION_RE."
        )
    return corpus


@dataclass
class Term:
    """One word or phrase, with counts computed in code — never model-reported."""

    term: str
    sentiment: str = "neutral"
    within: int = 0
    outside: int = 0
    contexts: list[str] = field(default_factory=list)

    @property
    def people(self) -> int:
        """PEOPLE who used it, not times it was said. One person saying
        'chalky' three times is one person — the honest denominator, and the
        same one the panel table uses."""
        return self.within + self.outside

    def to_dict(self) -> dict:
        return {"term": self.term, "sentiment": self.sentiment,
                "within": self.within, "outside": self.outside,
                "people": self.people, "contexts": list(self.contexts)}

    @classmethod
    def from_dict(cls, d: dict) -> "Term":
        return cls(term=d["term"], sentiment=d.get("sentiment", "neutral"),
                   within=int(d.get("within", 0)), outside=int(d.get("outside", 0)),
                   contexts=list(d.get("contexts", [])))


def _term_pattern(term: str) -> re.Pattern:
    """Word-boundary, case-insensitive, whitespace-tolerant for phrases."""
    parts = [re.escape(p) for p in term.split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\w*\b", re.IGNORECASE)


def count_term(corpus: Corpus, term: str, *, max_contexts: int = 3) -> Term:
    """Exact count of how many PEOPLE used a term, split in/out of target,
    with real sentences kept as evidence. This is the grounding step: a term
    the model invented scores 0 people and the caller drops it."""
    pat = _term_pattern(term)
    out = Term(term=term)
    for e in corpus.entries:
        if not pat.search(e.text):
            continue
        if e.within_target:
            out.within += 1
        else:
            out.outside += 1
        if len(out.contexts) < max_contexts:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", e.text):
                if pat.search(sentence):
                    out.contexts.append(sentence.strip()[:220])
                    break
    return out


@dataclass
class Lexicon:
    """The word cloud, grounded."""

    terms: list[Term] = field(default_factory=list)
    corpus_n: int = 0
    excluded: int = 0
    panel_n: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.terms

    def by_sentiment(self, sentiment: str) -> list[Term]:
        return [t for t in self.terms if t.sentiment == sentiment]

    def to_dict(self) -> dict:
        return {"terms": [t.to_dict() for t in self.terms],
                "corpus_n": self.corpus_n, "excluded": self.excluded,
                "panel_n": self.panel_n}

    @classmethod
    def from_dict(cls, d: dict) -> "Lexicon":
        return cls(terms=[Term.from_dict(t) for t in d.get("terms", [])],
                   corpus_n=int(d.get("corpus_n", 0)),
                   excluded=int(d.get("excluded", 0)),
                   panel_n=int(d.get("panel_n", 0)))


def assemble_lexicon(
    corpus: Corpus, candidates: list[str], sentiments: dict[str, str],
    *, min_people: int = 2, limit: int = 40,
) -> Lexicon:
    """Ground candidates against the corpus and assemble the final lexicon.

    Pure and deterministic — no API. `candidates` and `sentiments` are whatever
    the model returned; everything numeric is recomputed here. Terms nobody
    said, or that only one person said, are dropped: a word cloud built on
    n=1 is a quote, not a pattern.
    """
    seen: set[str] = set()
    terms: list[Term] = []
    for cand in candidates:
        key = " ".join((cand or "").lower().split())
        if not key or key in seen:
            continue
        seen.add(key)
        t = count_term(corpus, key)
        if t.people < min_people:
            continue
        s = (sentiments.get(cand) or sentiments.get(key) or "neutral").lower()
        t.sentiment = s if s in SENTIMENT_VALUES else "neutral"
        terms.append(t)

    terms.sort(key=lambda t: (-t.people, t.term))
    return Lexicon(terms=terms[:limit], corpus_n=corpus.n,
                   excluded=corpus.excluded, panel_n=corpus.n + corpus.excluded)


def load_transcripts(run_dir: str | Path) -> list[dict]:
    p = Path(run_dir) / "transcripts.json"
    if not p.exists():
        raise FileNotFoundError(f"no transcripts.json in {run_dir}")
    data = json.loads(p.read_text())
    if not isinstance(data, list):
        raise ValueError(f"transcripts.json in {run_dir} is not a list")
    return data


# ---- The two model calls ------------------------------------------------
#
# Deliberately the ONLY paid surface here, and deliberately small. The model
# does what models are good at (which words are associations, is this word
# working for the brand) and does not touch anything countable.

_PROPOSE_TOOL = {
    "name": "emit_association_terms",
    "description": (
        "Emit the words and short phrases these people actually used about "
        "the creative — the vocabulary that would form a word cloud."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "30-60 words or 2-word phrases, lowercase, EXACTLY as they "
                    "appear in the reactions. No invented synonyms, no words "
                    "that only appear in the ad's own copy, no protocol "
                    "vocabulary. Prefer what people said about the product, "
                    "how it made them feel, and why they did or didn't act."
                ),
            }
        },
        "required": ["terms"],
    },
}

_PROPOSE_SYSTEM = (
    "You are reading raw reactions from a panel of people who saw one ad in "
    "their social feed. Extract the vocabulary they actually used — the words "
    "that characterise how they talked about it.\n\n"
    "Rules:\n"
    "- Return words that APPEAR IN THE TEXT. Do not paraphrase or invent "
    "synonyms; every term is checked against the corpus afterwards and "
    "anything nobody said is discarded.\n"
    "- Skip words that are just the ad's own copy being repeated back.\n"
    "- Skip generic filler (thing, really, stuff) and category nouns that "
    "carry no attitude on their own.\n"
    "- Include negative and positive vocabulary alike; do not soften."
)

_CLASSIFY_TOOL = {
    "name": "emit_term_sentiment",
    "description": "Judge whether each term is working for or against the brand.",
    "input_schema": {
        "type": "object",
        "properties": {
            "judgements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "term": {"type": "string"},
                        "sentiment": {
                            "type": "string",
                            "enum": list(SENTIMENT_VALUES),
                            "description": (
                                "good = helps the brand as used here; "
                                "bad = hurts it; neutral = descriptive, "
                                "context-dependent, or genuinely mixed. Use "
                                "neutral rather than guessing."
                            ),
                        },
                    },
                    "required": ["term", "sentiment"],
                },
            }
        },
        "required": ["judgements"],
    },
}

_CLASSIFY_SYSTEM = (
    "For each term you are given the real sentences it appeared in. Judge the "
    "term AS USED IN THOSE SENTENCES, not the word in the abstract — 'cheap' "
    "can be value or it can be shoddy, 'clinical' can be credible or cold, and "
    "only the context decides.\n\n"
    "Answer from the brand's point of view: does a person saying this, in this "
    "way, help or hurt the product?\n\n"
    "Use 'neutral' whenever the term is purely descriptive, genuinely mixed "
    "across its uses, or you would be guessing. A confident wrong colour is "
    "worse than an honest grey."
)


def propose_terms(corpus: Corpus, config, client) -> list[str]:
    """PAID. Ask the model which words characterise how people talked."""
    from agent.telemetry import call_with_telemetry

    response = call_with_telemetry(
        client, layer="lexicon",
        model=config.model_versions.get("lexicon", "claude-sonnet-4-6"),
        max_tokens=2000, temperature=config.temperatures.get("lexicon", 0.0),
        system=_PROPOSE_SYSTEM,
        messages=[{"role": "user", "content":
                   f"REACTIONS FROM THE PANEL\n\n{corpus.sample_text()}"}],
        tools=[_PROPOSE_TOOL],
        tool_choice={"type": "tool", "name": "emit_association_terms"},
    )
    return [str(t) for t in _tool_input(response, "emit_association_terms")
            .get("terms", [])]


def classify_terms(grounded: list[Term], config, client) -> dict[str, str]:
    """PAID. Judge each grounded term good/bad/neutral, WITH its real context.

    Takes terms that have already survived grounding, so nothing is spent
    judging words nobody said.
    """
    from agent.telemetry import call_with_telemetry

    block = "\n\n".join(
        f"TERM: {t.term}  ({t.people} people)\n"
        + "\n".join(f"  - \"{c}\"" for c in t.contexts)
        for t in grounded
    )
    response = call_with_telemetry(
        client, layer="lexicon",
        model=config.model_versions.get("lexicon", "claude-sonnet-4-6"),
        max_tokens=2000, temperature=config.temperatures.get("lexicon", 0.0),
        system=_CLASSIFY_SYSTEM,
        messages=[{"role": "user", "content": block}],
        tools=[_CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "emit_term_sentiment"},
    )
    out: dict[str, str] = {}
    for j in _tool_input(response, "emit_term_sentiment").get("judgements", []):
        term, sentiment = j.get("term"), str(j.get("sentiment", "neutral")).lower()
        if term:
            out[str(term)] = sentiment if sentiment in SENTIMENT_VALUES else "neutral"
    return out


def _tool_input(response, name: str) -> dict:
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use" and block.name == name:
            return dict(block.input or {})
    raise ValueError(f"model returned no {name} tool call")


def build_lexicon(
    run_dir: str | Path, within_dispositions: list[str], config, client,
    *, propose=propose_terms, classify=classify_terms,
) -> Lexicon:
    """End to end. PAID (two small calls) unless propose/classify are stubbed —
    they are injectable exactly so the whole path can be tested for $0."""
    corpus = build_corpus(load_transcripts(run_dir), within_dispositions)
    if not corpus.n:
        return Lexicon()

    candidates = propose(corpus, config, client)
    # Ground BEFORE classifying: never spend judging a word nobody said.
    grounded = [t for t in (count_term(corpus, " ".join(c.lower().split()))
                            for c in dict.fromkeys(candidates) if c)
                if t.people >= 2]
    sentiments = classify(grounded, config, client) if grounded else {}
    return assemble_lexicon(corpus, [t.term for t in grounded], sentiments)
