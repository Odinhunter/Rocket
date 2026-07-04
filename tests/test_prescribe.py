"""Phase 3 offline tests (rocket-2.2.0, diagnosis rung): the deterministic
machinery of the prescribe pass — the METHODOLOGY_GAP short-circuit (no model
call), the prescription validators (3-changes / non-empty bet_ranking / every
rec derives from a pain / referential integrity / lever space), the
raw-reaction blindness of the handoff payload, and the audience-match routing
input. The model call itself is not exercised (offline).

Run: python tests/test_prescribe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import RunConfig
from agent.schema import (
    AudienceMatch,
    BehavioralSignalDistribution,
    FunnelProjection,
    FunnelRates,
    TopChange,
)
from agent.synthesis_prescribe import (
    PrescribeResult,
    prescribe_from_painmap,
    _build_prescribe_payload,
    _overall_rates,
    _validate_prescription,
)
from agent.synthesis_types import (
    DispositionTarget,
    InferredAudience,
    TargetClassification,
)


def _frozen(verdict: str = "MIXED") -> dict:
    return {
        "verdict": verdict,
        "confidence": 58,
        "pain_map": [
            {"id": "P1", "pain": "generic hero", "funnel_stage": "attention",
             "severity": "execution", "within_target": True, "prevalence": "most",
             "cited_by": ["a"], "evidence_quotes": []},
            {"id": "P2", "pain": "DIY-equivalence leak", "funnel_stage": "consideration",
             "severity": "structural", "within_target": True, "prevalence": "some",
             "cited_by": ["a"], "evidence_quotes": []},
        ],
        "strengths_to_preserve": [],
        "context_fit": {},
    }


def _changes(derives=("P1", "P2"), lever="creative", n=3) -> list[TopChange]:
    out = []
    for i in range(n):
        out.append(TopChange(
            change=f"specific move {i}",
            why=f"reasoning {i}",
            derives_from_pains=list(derives),
            lever_class=lever,
            within_target_corroboration="within-target flagged this",
        ))
    return out


def _tc() -> TargetClassification:
    return TargetClassification(
        inferred_target_description="protein-curious adults 25-34",
        target_reasoning="clean-label cues",
        disposition_classifications=[
            DispositionTarget(disposition_label="aspirant_clean_label", classification="within", reasoning=""),
            DispositionTarget(disposition_label="purist_food_first", classification="outside", reasoning=""),
        ],
        inferred_audience=InferredAudience(gender="mixed", age_band="25_34"),
    )


def _funnel() -> FunnelProjection:
    fr = FunnelRates(
        stop_rate=0.42, stop_band=(0.30, 0.54),
        click_rate=0.031, click_band=(0.022, 0.040),
        visit_rate=0.028, visit_band=(0.019, 0.037),
        convert_rate=0.011, convert_band=(0.006, 0.016),
        basis="heuristic_v1", baseline_source="acct avg 90d",
    )
    return FunnelProjection(
        overall=fr,
        by_segment=[],
        population_behavioral_distribution=BehavioralSignalDistribution(
            counts={"linger": 4, "tap_cta": 3}, would_act_within_week_count=3, n=15
        ),
        calibration_note="directional",
    )


def _cfg() -> RunConfig:
    from agent.config import AssetSpec
    return RunConfig(
        asset=AssetSpec(image_path="assets/boat_ad.png", label="Boat"),
        archetype="unspecified",
        category="personal_audio",
    )


def test_methodology_gap_short_circuits_without_model_call() -> None:
    # verdict METHODOLOGY_GAP returns empties before any client is constructed —
    # so this runs fully offline (no network).
    res = prescribe_from_painmap(_frozen("METHODOLOGY_GAP"), _funnel(), None, _tc(), _cfg())
    assert isinstance(res, PrescribeResult)
    assert res.top_3_changes == [] and res.bet_ranking == []
    print("  OK  METHODOLOGY_GAP short-circuits to empty recommendations (no model call)")


def test_validate_prescription_accepts_clean() -> None:
    assert _validate_prescription(_changes(), ["bet 1", "bet 2"], _frozen()["pain_map"]) == ""
    print("  OK  clean prescription accepted")


def test_validate_rejects_wrong_change_count() -> None:
    p = _validate_prescription(_changes(n=2), ["bet 1"], _frozen()["pain_map"])
    assert "exactly 3" in p, p
    print("  OK  non-3 change count rejected:", p)


def test_validate_rejects_empty_bet_ranking() -> None:
    p = _validate_prescription(_changes(), [], _frozen()["pain_map"])
    assert "bet_ranking is empty" in p, p
    print("  OK  empty bet_ranking rejected")


def test_validate_rejects_change_with_no_pains() -> None:
    p = _validate_prescription(_changes(derives=()), ["bet"], _frozen()["pain_map"])
    assert "cites no pains" in p, p
    print("  OK  recommendation citing no pains rejected")


def test_validate_rejects_dangling_pain_reference() -> None:
    p = _validate_prescription(_changes(derives=("P1", "P99")), ["bet"], _frozen()["pain_map"])
    assert "P99" in p and "unknown pain id" in p, p
    print("  OK  dangling pain reference rejected:", p)


def test_validate_rejects_out_of_scope_lever() -> None:
    bad = [
        TopChange(change="Launch a smaller pack to lower the price", why="cheaper entry",
                  derives_from_pains=["P1"], lever_class="offer"),
        _changes(n=1)[0], _changes(n=1)[0],
    ]
    p = _validate_prescription(bad, ["bet"], _frozen()["pain_map"])
    assert "out-of-scope lever" in p, p
    print("  OK  out-of-scope (product/pack/price) lever rejected:", p)


def test_payload_is_blind_to_raw_reactions_and_carries_audience_match() -> None:
    am = AudienceMatch(
        verdict="mismatched", declared_summary="women 20-24",
        inferred_summary="men 45-54", axes=["gender", "age"],
        message="creative reads 45-54 but the buy is 20-24",
    )
    payload = _build_prescribe_payload(_frozen(), _funnel(), am, _tc())
    # The frozen painmap has no raw reactions to leak, and the payload must not
    # reintroduce any reaction transcript markers.
    assert "encoding_text" not in payload and "R1 GUT" not in payload
    # Audience-match routing input is present (so "mismatched -> lead targeting"
    # is actionable) and the target lever slice is included.
    assert "mismatched" in payload and "disposition_classifications" in payload
    # Funnel is directional scalars only — no bands leak in.
    assert "stop_rate" in payload and "stop_band" not in payload
    print("  OK  prescribe payload is raw-blind + carries audience-match routing")


def test_overall_rates_scalars_only() -> None:
    rates = _overall_rates(_funnel())
    assert set(rates.keys()) == {"stop_rate", "click_rate", "visit_rate", "convert_rate"}
    assert _overall_rates(None) == {}
    print("  OK  _overall_rates returns scalar rates only (no bands)")


def main() -> None:
    print("=== prescribe pass deterministic machinery (rocket-2.2.0) ===")
    test_methodology_gap_short_circuits_without_model_call()
    test_validate_prescription_accepts_clean()
    test_validate_rejects_wrong_change_count()
    test_validate_rejects_empty_bet_ranking()
    test_validate_rejects_change_with_no_pains()
    test_validate_rejects_dangling_pain_reference()
    test_validate_rejects_out_of_scope_lever()
    test_payload_is_blind_to_raw_reactions_and_carries_audience_match()
    test_overall_rates_scalars_only()
    print("PASS — prescribe deterministic machinery locked.")


if __name__ == "__main__":
    main()
