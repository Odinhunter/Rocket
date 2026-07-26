"""lexicon — the two rules must hold, and both are testable without an API.

  1. the model never reports a number (a word nobody said must not appear)
  2. the readback slot (R2) never reaches the corpus

Offline: synthetic transcripts + stubbed model calls. The paid path is
injectable precisely so the whole flow can be proven for $0.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent.lexicon import (
    Corpus, CorpusEntry, Lexicon, Term, assemble_lexicon, build_corpus,
    build_lexicon, count_term, reaction_text, split_sections,
)


def _t(enc: str, ref: str = "", disp: str = "enthusiast_macros_lifter") -> dict:
    return {"agent_id": f"a{abs(hash(enc)) % 999}", "disposition_label": disp,
            "encoding_text": enc, "reflection_text": ref}


# ---- section splitting -------------------------------------------------


def test_split_handles_both_header_formats_on_disk() -> None:
    """Two formats exist across the runs: 'R1 GUT:' and '**R1 GUT**' with no
    colon at all. The second is 5.2% of transcripts — requiring a colon loses
    exactly the readback slot we need to find in order to drop it."""
    colon = "R1 GUT: thumb moving\n\nR2 COMPREHENSION: whey isolate\n\nR3 EMOTION: flat"
    bold = "**R1 GUT**\nthumb moving\n\n**R2 COMPREHENSION**\nwhey isolate\n\n**R3 EMOTION**\nflat"
    for label, text in (("colon", colon), ("bold-no-colon", bold)):
        s = split_sections(text)
        assert set(s) == {1, 2, 3}, f"{label}: got {sorted(s)}"
        assert s[2] == "whey isolate", f"{label}: wrong body"
    print("  both header formats split cleanly ✓")


def test_readback_section_never_reaches_the_corpus() -> None:
    """R2 asks 'what is this selling', so the persona recites the ad's copy.
    Counting it measures the ad, not the reaction — the brand_recall failure."""
    txt = ("R1 GUT: looks like gym stuff\n\n"
           "R2 COMPREHENSION: AI-designed functional protein for longevity\n\n"
           "R3 EMOTION: nothing, scrolled")
    out = reaction_text(_t(txt))
    assert "looks like gym stuff" in out and "scrolled" in out
    assert "AI-designed" not in out and "longevity" not in out, \
        "readback text leaked into the corpus"
    print("  readback slot excluded from the corpus ✓")


def test_unsplittable_transcript_is_dropped_not_guessed() -> None:
    """No sections means the readback slot cannot be located. Including such a
    transcript would silently admit the thing this module exists to exclude."""
    assert reaction_text(_t("just some prose with no section headers at all")) is None
    # R2 specifically missing is also a drop, even though other sections parsed.
    assert reaction_text(_t("R1 GUT: hi\n\nR3 EMOTION: flat")) is None
    print("  unsplittable transcripts dropped, never guessed ✓")


def test_corpus_aborts_when_too_much_of_the_panel_is_unsplittable() -> None:
    """Survive a few strays; abort loudly on a gutted panel — the same rule L1
    panel resilience uses."""
    good = _t("R1 GUT: fine\n\nR2 COMPREHENSION: a tub\n\nR3 EMOTION: flat")
    bad = _t("no headers here")
    assert build_corpus([good] * 19 + [bad], []).excluded == 1  # 5% -> fine
    try:
        build_corpus([good] * 5 + [bad] * 5, [])
    except ValueError as e:
        assert "readback slot" in str(e)
    else:
        raise AssertionError("50% unsplittable must abort, not silently proceed")
    print("  corpus survives strays, aborts on a gutted panel ✓")


# ---- grounding: the model never reports a number -----------------------


def _corpus() -> Corpus:
    return Corpus(entries=[
        CorpusEntry("a1", "enthusiast_macros_lifter", True,
                    "it tastes chalky. really chalky honestly, chalky texture"),
        CorpusEntry("a2", "enthusiast_macros_lifter", True,
                    "the price feels steep for what you get"),
        CorpusEntry("a3", "skeptic_lapsed_protein", False,
                    "chalky is my worry with these tubs"),
        CorpusEntry("a4", "skeptic_lapsed_protein", False,
                    "looks trustworthy, the certification helps"),
    ])


def test_count_is_people_not_mentions_and_splits_in_out_of_target() -> None:
    """a1 says "chalky" THREE times and must count once; a3 says it once. So
    the honest answer is 2 people, not 4 mentions — inflating a word cloud by
    repetition would make one loud person look like a pattern."""
    c = _corpus()
    assert c.entries[0].text.count("chalky") == 3, "fixture must exercise repeats"
    t = count_term(c, "chalky")
    assert t.people == 2, "3 mentions by one person is still one person"
    assert (t.within, t.outside) == (1, 1), "in/out split must be preserved"
    assert len(t.contexts) == 2, "one piece of evidence per person, not per mention"
    assert t.contexts and "chalky" in t.contexts[0].lower(), "real evidence kept"
    print("  counts are people not mentions, split in/out of target ✓")


def test_a_term_nobody_said_is_dropped_not_reported() -> None:
    """The whole grounding contract: the model can propose anything; only what
    the corpus actually contains survives."""
    lex = assemble_lexicon(
        _corpus(),
        candidates=["chalky", "gritty", "revolutionary", "price"],
        sentiments={"chalky": "bad", "gritty": "bad",
                    "revolutionary": "good", "price": "neutral"},
    )
    terms = {t.term for t in lex.terms}
    assert "chalky" in terms
    assert "gritty" not in terms and "revolutionary" not in terms, \
        "invented terms must be dropped, never rendered"
    assert "price" not in terms, "a term only one person used is a quote, not a pattern"
    print("  ungrounded and n=1 terms dropped ✓")


def test_sentiment_falls_back_to_neutral_never_to_a_guess() -> None:
    lex = assemble_lexicon(_corpus(), ["chalky"], {"chalky": "catastrophic"})
    assert lex.terms[0].sentiment == "neutral", \
        "an unrecognised sentiment must go grey, not be passed through"
    lex2 = assemble_lexicon(_corpus(), ["chalky"], {})
    assert lex2.terms[0].sentiment == "neutral", "missing judgement -> neutral"
    print("  unknown sentiment degrades to neutral ✓")


def test_lexicon_round_trips_and_reports_its_own_coverage() -> None:
    lex = assemble_lexicon(_corpus(), ["chalky"], {"chalky": "bad"})
    lex.excluded = 2
    back = Lexicon.from_dict(json.loads(json.dumps(lex.to_dict())))
    assert back.terms[0].term == "chalky" and back.terms[0].sentiment == "bad"
    assert back.terms[0].people == 2 and back.corpus_n == lex.corpus_n
    assert back.excluded == 2, "how many agents were dropped must survive"
    print("  lexicon round-trips including its coverage ✓")


# ---- end to end, with the paid calls stubbed ---------------------------


def test_build_lexicon_end_to_end_with_stubbed_model_calls() -> None:
    """Proves the whole path — corpus, grounding, classification, assembly —
    without an API call. The model is stubbed to return one real term and one
    invented one; only the real one may survive."""
    # Two people per audience: a term must clear the >=2 display threshold
    # WITHIN an audience to be judged for it, so one-per-side would leave both
    # clouds empty and prove nothing. The FIRST sentence carries the
    # distinguishing word, because context capture takes one sentence per
    # person and stops at the first match.
    rows = [
        _t("R1 GUT: chalky and bland\n\nR2 COMPREHENSION: AI-designed longevity"
           "\n\nR3 EMOTION: flat", disp="enthusiast_macros_lifter"),
        _t("R1 GUT: chalky, quite bland\n\nR2 COMPREHENSION: AI-designed longevity"
           "\n\nR3 EMOTION: flat", disp="enthusiast_macros_lifter"),
        _t("R1 GUT: chalky and not for me\n\nR2 COMPREHENSION: AI-designed longevity"
           "\n\nR3 EMOTION: skip", disp="skeptic_lapsed_protein"),
        _t("R1 GUT: chalky, not for me either\n\nR2 COMPREHENSION: AI-designed"
           " longevity\n\nR3 EMOTION: skip", disp="skeptic_lapsed_protein"),
    ]
    with tempfile.TemporaryDirectory() as td:
        rd = Path(td)
        (rd / "transcripts.json").write_text(json.dumps(rows))

        seen = {}

        def fake_propose(corpus, config, client):
            seen["corpus_n"] = corpus.n
            seen["sample"] = corpus.sample_text()
            return ["chalky", "longevity", "unicorn"]

        def fake_classify(grounded, config, client, *, audience=""):
            # Record per audience: the whole point is that each audience is
            # judged from its own sentences, so the stub must see them apart.
            seen.setdefault("classified", []).extend(t.term for t in grounded)
            seen.setdefault("audiences", []).append(audience)
            key = "ctx_" + (audience or "pooled")
            seen[key] = [
                (t.term, list(t.contexts_within if audience == "within"
                              else t.contexts_outside if audience == "outside"
                              else t.contexts))
                for t in grounded
            ]
            return {t.term: "bad" for t in grounded}

        lex = build_lexicon(rd, ["enthusiast_macros_lifter"], config=None,
                            client=None, propose=fake_propose,
                            classify=fake_classify)

    terms = {t.term for t in lex.terms}
    assert terms == {"chalky"}, f"expected only the grounded term, got {terms}"
    assert lex.terms[0].within == 2 and lex.terms[0].outside == 2
    assert "unicorn" not in seen["classified"], "never spend judging an unsaid word"
    assert "longevity" not in seen["classified"], \
        "readback-only vocabulary must not survive grounding"
    assert "AI-designed" not in seen["sample"], "readback leaked into the prompt"
    assert lex.corpus_n == 4 and lex.panel_n == 4
    assert lex.within_n == 2 and lex.outside_n == 2, "audience denominators set"
    assert seen["audiences"] == ["within", "outside"], \
        "each audience must be judged separately, in order"
    # The in-target call must see ONLY in-target sentences, and vice versa.
    within_ctx = dict(seen["ctx_within"])["chalky"]
    outside_ctx = dict(seen["ctx_outside"])["chalky"]
    assert any("bland" in c for c in within_ctx), "in-target sentence missing"
    assert not any("bland" in c for c in outside_ctx), \
        "an in-target sentence leaked into the out-of-target judgement"
    assert any("not for me" in c for c in outside_ctx)
    print("  end-to-end: grounded, non-readback, judged per audience ✓")
