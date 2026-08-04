"""Fingerprints of the PROMPT TEXT a run was produced with (§5.1, the config
freeze).

Why this exists
---------------
`run.json` already stamps eight hand-maintained version strings
(`assess_prompt_version = "assess-3"`, and so on). They are bumped by a human,
which means an edited prompt with an unbumped constant is completely invisible:
two runs claim the same `assess-3` and were produced by different instructions.

That is the single most expensive kind of undeclared freedom this project can
have. Across 66 defensible configurations of ONE task on ONE dataset, published
human-vs-silicon correlations ranged r = .23 to .84 — the configuration swamps
the effect being measured. Any human-panel comparison we run is worthless
unless we can say exactly what produced the numbers, and "assess-3" is only a
claim about that.

⚠ What is fingerprinted, and why not more
-----------------------------------------
STATIC, NAMED, module-level template constants — enumerated explicitly below.
Nothing else.

Hashing an *assembled* prompt would look far more thorough and detect nothing:
the assembled text contains the reaction corpus, the asset label and the
disposition prose, so it differs on every run by construction. A hash that
always changes cannot tell you that a prompt changed. Enumerating by hand also
means a NEW template is invisible until someone adds it here — that is the
deliberate trade against a magic scan of every module-level string, which would
churn the fingerprint on any unrelated constant.

The Call-B reflection prompt is assembled per purpose from several blocks
(`_REFLECTION_BASE` + the conditional `_NOVELTY_BLOCK` / `_BRAND_CHECK_BLOCK`).
Each block is fingerprinted separately rather than the assembly, so a change is
attributable to the block it happened in, whichever purposes include it.

⚠ This runs in the PAID path. Every caller must treat it as best-effort — see
`run_service._run_json_payload`. A provenance record is worth a lot; it is not
worth a ~$4 run, and anything that can raise near the end of one can replace the
return value of a successful synthesis.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

# (label, module path, attribute). The label is what lands in run.json, so keep
# it stable — renaming one silently orphans the history of that template.
_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("agent.encoding", "agent.runtime", "_ENCODING_USER"),
    ("agent.reflection_base", "agent.runtime", "_REFLECTION_BASE"),
    ("agent.reflection_novelty", "agent.runtime", "_NOVELTY_BLOCK"),
    ("agent.reflection_brand_check", "agent.runtime", "_BRAND_CHECK_BLOCK"),
    ("agent.next_step_head", "agent.runtime", "_NEXT_STEP_HEAD"),
    ("agent.next_step_core", "agent.runtime", "_NEXT_STEP_CORE"),
    ("agent.next_step_note", "agent.runtime", "_NEXT_STEP_NOTE"),
    ("agent.cycle_prose", "agent.runtime", "_CYCLE_PROSE"),
    ("l2.system", "agent.synthesis_l2", "_L2_SYSTEM"),
    ("assess.system", "agent.synthesis_assess", "_ASSESS_SYSTEM"),
    ("assess.verdict_framework", "agent.synthesis_assess", "_VERDICT_FRAMEWORK"),
    ("prescribe.system", "agent.synthesis_prescribe", "_PRESCRIBE_SYSTEM"),
    ("target_id.system", "agent.target_id", "_SYSTEM"),
    ("render.persona_system", "agent.render", "_PERSONA_SYSTEM"),
    ("render.context_system", "agent.render", "_CONTEXT_SYSTEM"),
)


def _stable_text(value: object) -> str:
    """Render a template to text for hashing. Dicts are sorted, so a fingerprint
    tracks CONTENT and not Python's iteration order."""
    if isinstance(value, dict):
        return "\n".join(f"{k}\x00{_stable_text(v)}"
                         for k, v in sorted(value.items(), key=lambda kv: str(kv[0])))
    if isinstance(value, (list, tuple)):
        return "\n".join(_stable_text(v) for v in value)
    return str(value)


@lru_cache(maxsize=1)
def _compute() -> tuple[tuple[str, str], ...]:
    """Hash every template once per process.

    ⚠ Cached deliberately, and the reason is a measured one. `_write_run_json`
    is called several times per run — at `committed`, at `complete` — and each
    call was importing six modules and re-hashing constants that cannot change
    within a process. On the paid path that work sits between run.json landing
    and the first progress write, and it widened that window enough to make an
    existing race in the progress test fail about one run in four. Static
    templates are static; compute them once.
    """
    from importlib import import_module

    out: list[tuple[str, str]] = []
    for label, module_path, attr in _TEMPLATES:
        try:
            value = getattr(import_module(module_path), attr)
        except (ImportError, AttributeError):
            out.append((label, "unavailable"))
            continue
        h = hashlib.sha1(_stable_text(value).encode("utf-8"))
        out.append((label, h.hexdigest()[:12]))
    return tuple(out)


def prompt_fingerprints() -> dict[str, str]:
    """`{label: sha1[:12]}` for every static prompt template.

    Imports are deferred into the call: `agent.runtime` and the synthesis
    modules import `agent.config`, so importing them at module scope here would
    close a cycle. A template that cannot be resolved is recorded as
    `"unavailable"` rather than dropped — a MISSING key would read as "this run
    had no such prompt", which is a stronger and wrong claim.

    Returns a fresh dict each call so a caller cannot mutate the cache.
    """
    return dict(_compute())
