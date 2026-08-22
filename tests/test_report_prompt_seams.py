"""The three prompts that WRITE the customer's report, read as assembled artifacts.

⚠⚠ WHY THIS FILE EXISTS. `docs/why_we_keep_making_the_same_mistake.md` §6 counted
17 surfaces in this engine. Eight had no assembled-output test at all, and three
of those eight are `_L2_SYSTEM`, `_L4_SYSTEM` and `_ASSESS_SYSTEM` — the prompts
that produce every word a customer pays to read. They appeared in ZERO test files.
Every defect found in session 48 was invisible to piece-level tests and obvious in
assembled output, and these three had neither.

⭐ THE SHAPE THIS FILE INSISTS ON. Each test reads what `build_l2_call` /
`build_l4_call` / `build_assess_call` return — the same functions the production
call sites consume, and nothing else. The review found `render.compose_persona_prompt`:
a prompt assembler with zero production callers, whose ordering a passing test
asserts, and whose header no persona has ever seen. A test that assembles the
prompt its own way tests a phantom.

⭐ AND THE TOOL SCHEMA IS PART OF THE ARTIFACT. The one seam test this repo already
had (`test_generation_prompt`) joins the system blocks and the user turn but not the
tool schema, which is a separate argument at the call site — so an exemplar re-added
in a field description is invisible to the test written to catch exactly that
(review §5). Everything here reads system + user + schema together.

⚠ These are PROPERTY assertions, not snapshots. A snapshot of a 6,000-word prompt
turns every wording change into a test failure and gets deleted within a month.

Offline. No API calls.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agent.artifact_pack import market_name_for
from agent.config import AssetSpec, RunConfig
from agent.projection_l35 import project_funnel
from agent.schema import AgentTranscript, BehavioralSignal
from agent.synthesis_assess import build_assess_call, build_corpus
from agent.synthesis_l2 import build_l2_call
from agent.synthesis_l3 import synthesize_population
from agent.synthesis_l4 import _PRIOR_RAW_MAX_CHARS, build_l4_call
from agent.synthesis_types import (
    DispositionTarget,
    L2Summary,
    L3Summary,
    Quote,
    TargetClassification,
)


# ---- Fixtures: the smallest run that exercises every module ----


def _config(**kw) -> RunConfig:
    base = dict(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat teaser"),
        archetype="unspecified", category="personal_audio",
    )
    base.update(kw)
    return RunConfig(**base)


def _transcript(agent_id: int, label: str, context: str = "commute") -> AgentTranscript:
    return AgentTranscript(
        agent_id=agent_id,
        disposition_label=label,
        context_label=context,
        seed_idx=0,
        encoding_text=f"R1 GUT: agent {agent_id} glanced at it.",
        reflection_text=f"R6 FRICTION: agent {agent_id} would not chase it.",
        behavioral_signal=BehavioralSignal(
            action="linger", action_reasoning="held a beat",
            next_step="buy_now", next_step_reasoning="cheap enough",
        ),
    )


def _tc(**classifications: str) -> TargetClassification:
    return TargetClassification(
        inferred_target_description="commuters who want cheap ANC",
        target_reasoning="the creative leads on price and noise.",
        disposition_classifications=[
            DispositionTarget(disposition_label=k, classification=v,
                              reasoning="fixture")
            for k, v in classifications.items()
        ],
        ambiguity_note="one disposition could go either way",
    )


_CLASSIFIED = {"upgrader_commute_anc": "within", "skeptic_price_anchor": "outside"}


def _transcripts() -> list[AgentTranscript]:
    return [
        _transcript(1, "upgrader_commute_anc"),
        _transcript(2, "upgrader_commute_anc", context="gym"),
        _transcript(3, "skeptic_price_anchor"),
    ]


def _l3() -> L3Summary:
    l2s = [
        L2Summary(disposition_label="upgrader_commute_anc",
                  summary_paragraph="They liked the price.",
                  within_cell_variance="spread", outlier_note=None,
                  segment_label="upgrader_commute_anc",
                  representative_quotes={1: Quote(quote="cheap enough",
                                                  disposition="upgrader_commute_anc",
                                                  round=1, context="commute")}),
        L2Summary(disposition_label="skeptic_price_anchor",
                  summary_paragraph="They did not believe the claim.",
                  within_cell_variance="spread", outlier_note=None,
                  segment_label="skeptic_price_anchor"),
    ]
    return synthesize_population(l2s, _tc(**_CLASSIFIED))


def _l4_call(**kw):
    l3 = _l3()
    return build_l4_call(l3, _tc(**_CLASSIFIED),
                         project_funnel(l3, None), _config(), **kw)


def _assess_call(**kw):
    return build_assess_call(
        _tc(**_CLASSIFIED), build_corpus(_transcripts(), _CLASSIFIED), **kw
    )


def _l2_call(**kw):
    return build_l2_call("upgrader_commute_anc", _transcripts()[:2], _config(), **kw)


def _assembled(call: dict) -> str:
    """System + user turn + tool schema, as ONE artifact. The schema is a
    separate argument at the call site and is exactly where a defect hides
    from a test that reads only the prose."""
    parts = [call["system"], call["user"]]
    if call.get("tools"):
        parts.append(json.dumps(call["tools"], ensure_ascii=False))
    return "\n\n".join(parts)


# ---- The assembler IS what production sends ----


def _calls_made_by(module: str, func: str) -> set[str]:
    """Names of the functions called INSIDE `func`, via the AST.

    ⚠ Deliberately not a substring scan. The first draft of this test sliced
    the source from the caller's `def` to end-of-file and asked whether the
    assembler's name appeared — which it always did, on the assembler's OWN
    `def` line further down. It passed on a codebase where the wiring did not
    exist. That is vacuous shape #10 for this project's list.
    """
    tree = ast.parse((Path(__file__).resolve().parent.parent / module).read_text())
    node = next(n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == func)
    return {c.func.id for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


def test_every_report_writing_call_site_goes_through_its_assembler() -> None:
    """⚠ THE compose_persona_prompt TRAP. The review found a prompt assembler
    with ZERO production callers whose ordering a passing test asserts and whose
    output no persona has ever seen. A test over an assembler proves nothing
    unless production uses that assembler — so this pins the wiring itself."""
    for module, caller, assembler in (
        ("agent/synthesis_l2.py", "synthesize_segment", "build_l2_call"),
        ("agent/synthesis_l4.py", "synthesize_memo", "build_l4_call"),
        ("agent/synthesis_assess.py", "assess_reactions", "build_assess_call"),
    ):
        called = _calls_made_by(module, caller)
        assert assembler in called, (
            f"{module}: {caller}() does not call {assembler}() — the assembler "
            f"this file tests is not what production sends. Calls found: "
            f"{sorted(called)}"
        )
    print("  OK  all three call sites consume their own assembler ✓")


# ---- L2 ----


def test_l2_carries_every_transcript_it_was_given() -> None:
    """A segment summary is only as good as the transcripts that reach the
    prompt. A silent drop here is invisible downstream — the summary reads
    perfectly well, it is just about fewer people than the run paid for."""
    call = _l2_call()
    art = _assembled(call)
    for t in _transcripts()[:2]:
        assert t.encoding_text in art, f"agent {t.agent_id} encoding text missing"
        assert t.reflection_text in art, f"agent {t.agent_id} reflection text missing"
    assert "COUNT: 2 transcript(s)" in art, "the count line must state the real N"
    assert "'commute'" in art or "commute" in art
    assert "gym" in art, "both contexts must be named"
    print("  OK  L2 carries every transcript, its count and its contexts ✓")


def test_l2_tool_schema_is_forced_and_matches_the_field_the_code_reads() -> None:
    """The tool is forced (`tool_choice`), so its schema — not the prose — is
    what shapes the output. Every field `_build_l2_summary` reads must be
    REQUIRED in that schema, or the model may legally omit it."""
    call = _l2_call()
    assert call["tool_choice"] == {"type": "tool",
                                   "name": "emit_disposition_summary"}
    tool = call["tools"][0]
    assert tool["name"] == call["tool_choice"]["name"], (
        "tool_choice names a tool that is not in the tools list"
    )
    required = set(tool["input_schema"]["required"])
    for field in ("summary_paragraph", "within_cell_variance", "outlier_note",
                  "representative_quotes", "emotional_read", "friction_summary"):
        assert field in required, f"{field} is read by the code but not required"
    print(f"  OK  L2 tool forced, {len(required)} fields required ✓")


def test_l2_never_asks_the_model_for_the_behavioural_counts() -> None:
    """R7 is counted in Python and never emitted by a model — the invariant
    `scripts/gate_test.py` QC1/QC2 rest on. The prompt has to say so, and the
    schema must not offer a field to put counts in."""
    call = _l2_call()
    assert "Do NOT summarize or count R7" in call["user"]
    props = set(call["tools"][0]["input_schema"]["properties"])
    for forbidden in ("behavioral_distribution", "counts", "n",
                      "next_step_counts", "buy_intent_count"):
        assert forbidden not in props, (
            f"the L2 tool schema offers {forbidden!r} — a model-emitted "
            "distribution breaks the convexity invariant"
        )
    print("  OK  L2 asks for no counts and offers nowhere to put them ✓")


# ---- L4 ----


def test_l4_payload_carries_all_seven_modules() -> None:
    """⚠ The review's §6 finding: the L4 payload concatenates seven modules with
    NO test reading the result. Each is a separate contributor, and a missing
    one degrades the memo silently rather than raising."""
    call = _l4_call()
    payload = json.loads(call["user"][call["user"].index("{"):
                                      call["user"].rindex("}") + 1])
    for module in ("asset_label", "category", "context_labels_in_run",
                   "target_classification", "l3_summary", "funnel_projection"):
        assert module in payload, f"L4 payload lost its {module!r} module"
        assert payload[module] is not None
    # The seventh is conditional — present only with a declared audience.
    assert "audience_match" not in payload, (
        "audience_match must be absent, not null, when there is no declared "
        "audience — a null teaches the model there was one and it was empty"
    )
    print(f"  OK  L4 payload carries its modules ({len(payload)} present) ✓")


def test_l4_is_told_the_market_in_english_never_by_its_module_key() -> None:
    """⭐ THE `#78` CLASS, pinned at the seam. `category` is a machine key — it
    names the module, keys the render cache and gates the install guard. A model
    read one and told every persona in a $3.85 run the market was "international
    food and drink" for an Indian pack. Prose slots get `market_name_for()`."""
    for category in ("personal_audio", "fnb_world", "health_nutrition_snacking"):
        l3 = _l3()
        call = build_l4_call(l3, _tc(**_CLASSIFIED),
                             project_funnel(l3, None),
                             _config(category=category))
        payload = json.loads(call["user"][call["user"].index("{"):
                                          call["user"].rindex("}") + 1])
        assert payload["category"] == market_name_for(category), (
            f"L4 was handed the raw key {category!r} instead of "
            f"{market_name_for(category)!r}"
        )
        assert category not in call["user"], (
            f"the raw module key {category!r} still reaches the L4 prompt"
        )
    print("  OK  L4 is told the market in English at every category ✓")


def test_l4_is_told_the_funnel_is_an_input_it_must_not_emit() -> None:
    """Funnel rates are computed in Python and attached after the model
    returns. If the model emits one it is invented, and it lands on the report
    beside real ones with nothing distinguishing them."""
    call = _l4_call()
    assert "The funnel_projection is an INPUT" in call["user"]
    assert "Do not emit it or any funnel rate" in call["user"]
    print("  OK  L4 is told the funnel is an input, not an output ✓")


def test_l4_retry_turn_appends_the_prior_output_delimited_and_capped() -> None:
    """⚠⚠ THE BRANCH A HAPPY-PATH FIXTURE NEVER REACHES. On attempt 2+ the
    model's own rejected output goes back into the prompt. Unbounded that is a
    context blow-up; undelimited the model cannot tell its bad output from the
    real inputs."""
    clean = _l4_call()
    assert "BEGIN PRIOR OUTPUT" not in clean["user"], (
        "the first attempt must carry no retry suffix"
    )

    # ⚠ PIN THE LITERAL, NOT JUST THE CONSTANT. The first draft asserted the
    # truncation against _PRIOR_RAW_MAX_CHARS itself — so a mutation that raised
    # the constant raised the test's own bar with it and went uncaught. A test
    # that measures the code against the code is vacuous. Raising this cap is a
    # real decision (it is context budget on a retry that already failed once);
    # changing it should require changing this number on purpose.
    assert _PRIOR_RAW_MAX_CHARS == 8000, (
        f"the prior-output cap moved to {_PRIOR_RAW_MAX_CHARS}. That is a "
        "context-budget decision on a turn that already failed once — make it "
        "deliberately and update this number."
    )
    huge = "x" * (_PRIOR_RAW_MAX_CHARS * 3)
    retry = _l4_call(is_retry=True, feedback="SchemaError: bet_ranking is empty",
                     prior_raw=huge)
    added = retry["user"][len(clean["user"]):]

    assert retry["user"].startswith(clean["user"]), (
        "the retry turn must APPEND to the original payload, not replace it — "
        "the model is asked to fix its output, not regenerate from scratch"
    )
    assert "--- BEGIN PRIOR OUTPUT ---" in added
    assert "--- END PRIOR OUTPUT ---" in added
    assert "SchemaError: bet_ranking is empty" in added
    assert "[TRUNCATED" in added, "an oversized prior output must be truncated"
    block = added[added.index("--- BEGIN PRIOR OUTPUT ---"):
                  added.index("--- END PRIOR OUTPUT ---")]
    assert block.count("x") <= _PRIOR_RAW_MAX_CHARS, (
        f"prior output not capped at {_PRIOR_RAW_MAX_CHARS}: "
        f"{block.count('x')} characters of it got through"
    )
    assert block.count("x") > _PRIOR_RAW_MAX_CHARS // 2, (
        "the cap must keep most of the budget — a truncation that keeps almost "
        "nothing gives the model nothing to repair"
    )
    print(f"  OK  L4 retry appends, delimits and caps at "
          f"{_PRIOR_RAW_MAX_CHARS} chars ✓")


# ---- assess ----


def test_assess_carries_every_reaction_with_its_target_tag() -> None:
    """⚠ The assess pass is the ONLY prompt that reads the raw corpus, and
    grounding is verified against that same corpus. A transcript dropped here
    does not merely lose a voice — it makes that voice's quotes unverifiable,
    and `_drop_unverifiable` then deletes them from the report as fabrications."""
    call = _assess_call()
    art = _assembled(call)
    for t in _transcripts():
        assert t.encoding_text in art, f"agent {t.agent_id} missing from corpus"
        assert t.reflection_text in art
        tag = _CLASSIFIED[t.disposition_label].upper()
        assert f"{t.disposition_label} [{tag}-TARGET]" in art, (
            f"agent {t.agent_id} reached the corpus without its target tag — "
            "the assess pass cannot split in/out of target without it"
        )
    print("  OK  every reaction reaches assess carrying its target tag ✓")


def test_assess_corpus_is_uncapped_so_no_reaction_is_dropped_silently() -> None:
    """A length cap on the corpus would be a SILENT sampling decision made in a
    prompt builder. If one is ever added it must announce itself in the text —
    this test is what forces that conversation rather than a quiet truncation."""
    many = [_transcript(i, "upgrader_commute_anc") for i in range(60)]
    corpus = build_corpus(many, _CLASSIFIED)
    assert corpus.count("--- agent ") == 60, (
        f"build_corpus emitted {corpus.count('--- agent ')} of 60 blocks — if a "
        "cap was added deliberately, make it say so in the corpus text"
    )
    call = build_assess_call(_tc(**_CLASSIFIED), corpus)
    assert call["user"].count("--- agent ") == 60
    print("  OK  60 of 60 reactions reach the prompt, none dropped ✓")


def test_assess_gets_the_classification_it_needs_and_no_reactions_in_it() -> None:
    """Target is a property of the AD, read by a separate call that never saw a
    reaction — that is what stops the classifier rationalising target to fit
    whoever responded. The compact classification handed to assess must carry
    the decision without smuggling reaction text into it."""
    call = _assess_call()
    head = call["user"][:call["user"].index("--- agent ")]
    assert "TARGET CLASSIFICATION" in head
    assert "commuters who want cheap ANC" in head
    assert "ambiguity_note" in head
    for reasoning in ("target_reasoning", "the creative leads on price"):
        assert reasoning not in head, (
            f"{reasoning!r} is in the classification block — assess is given "
            "the classification, not the argument for it"
        )
    print("  OK  assess gets the classification, compact and reaction-free ✓")


def test_assess_retry_turn_names_the_rejection_and_repeats_the_quote_rule() -> None:
    """⚠ The retry branch, which used to be an f-string inline in the call loop
    and could not be reached from a test at all. Its whole job is the grounding
    rule, so the retry has to restate it — that is the turn that fires when
    quotes came back paraphrased."""
    clean = _assess_call()
    assert "was rejected" not in clean["user"]

    retry = _assess_call(is_retry=True,
                         feedback="3 evidence quote(s) are not verbatim")
    added = retry["user"][len(clean["user"]):]
    assert retry["user"].startswith(clean["user"]), (
        "the retry must append — the corpus above it is what quotes are "
        "checked against"
    )
    assert "3 evidence quote(s) are not verbatim" in added
    assert "EXACT substring" in added, (
        "the retry must restate the grounding rule it is retrying for"
    )
    assert "No prose, no fences." in added
    print("  OK  assess retry names the rejection and restates the rule ✓")


# ---- Absence properties that hold across all three ----


@pytest.mark.parametrize("name", ["l2", "l4", "assess"])
def test_no_report_writing_prompt_carries_the_marketers_own_thesis(name) -> None:
    """`tests/test_marketer_notes_never_reach_the_agent.py` draws this boundary
    for the persona prompts. It is the same boundary here for a different
    reason: a marketer's thesis in the prompt that WRITES the diagnosis buys
    them their own opinion back with a confidence score on it."""
    notes = "This ad is our best performer and the hook is the price point."
    brand = "We always lose to Boat on price and it is killing the margin."
    cfg = _config(marketer_notes=notes, brand_notes=brand)
    l3 = _l3()
    call = {
        "l2": lambda: build_l2_call("upgrader_commute_anc", _transcripts()[:2], cfg),
        "l4": lambda: build_l4_call(l3, _tc(**_CLASSIFIED),
                                    project_funnel(l3, None), cfg),
        "assess": lambda: build_assess_call(
            _tc(**_CLASSIFIED), build_corpus(_transcripts(), _CLASSIFIED)),
    }[name]()
    art = _assembled(call)
    assert notes not in art, f"{name}: marketer notes reached the prompt"
    assert brand not in art, f"{name}: brand notes reached the prompt"
    assert "best performer" not in art and "killing the margin" not in art
    print(f"  OK  {name}: the marketer's thesis stays out ✓")


@pytest.mark.parametrize("name", ["l2", "l4", "assess"])
def test_every_report_writing_prompt_states_its_output_contract(name) -> None:
    """Each of the three ends by naming exactly what it must return. Losing that
    line is how a JSON-only prompt starts getting prose wrapped around it, which
    the parser then strips with a regex and mostly gets right."""
    call = {"l2": _l2_call, "l4": _l4_call, "assess": _assess_call}[name]()
    tail = call["user"][-400:]
    expected = {
        "l2": "Call emit_disposition_summary with your structured output",
        "l4": "Return the Report JSON now",
        "assess": "JSON",
    }[name]
    assert expected in tail, (
        f"{name}: the closing instruction {expected!r} is not in the last 400 "
        f"characters of the user turn"
    )
    assert call["system"].strip(), f"{name}: empty system prompt"
    print(f"  OK  {name}: output contract stated at the end of the turn ✓")


def main() -> None:
    print("=== seam tests: the three prompts that write the report ===")
    test_every_report_writing_call_site_goes_through_its_assembler()
    test_l2_carries_every_transcript_it_was_given()
    test_l2_tool_schema_is_forced_and_matches_the_field_the_code_reads()
    test_l2_never_asks_the_model_for_the_behavioural_counts()
    test_l4_payload_carries_all_seven_modules()
    test_l4_is_told_the_market_in_english_never_by_its_module_key()
    test_l4_is_told_the_funnel_is_an_input_it_must_not_emit()
    test_l4_retry_turn_appends_the_prior_output_delimited_and_capped()
    test_assess_carries_every_reaction_with_its_target_tag()
    test_assess_corpus_is_uncapped_so_no_reaction_is_dropped_silently()
    test_assess_gets_the_classification_it_needs_and_no_reactions_in_it()
    test_assess_retry_turn_names_the_rejection_and_repeats_the_quote_rule()
    for n in ("l2", "l4", "assess"):
        test_no_report_writing_prompt_carries_the_marketers_own_thesis(n)
        test_every_report_writing_prompt_states_its_output_contract(n)
    print("PASS — the three report-writing prompts have assembled-output cover.")


if __name__ == "__main__":
    main()
