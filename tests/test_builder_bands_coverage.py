"""Coverage — premium builder severity bands + urgency across low/medium/high/critical."""

from __future__ import annotations

import pytest
from otm_core_schema import StrideCategory, create_blank_document
from otm_core_schema.document import Threat
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment

pytest.importorskip("fastapi")
from otm_report_premium.builder import build_premium_report_payload  # noqa: E402
from otm_report_premium.enums import ReportLevel  # noqa: E402


def _doc_with_banded_threats():
    base = create_blank_document()
    threats = [
        Threat(id="t_crit", title="Critical", stride=StrideCategory.TAMPERING, risk=build_risk_assessment(5, 5)),
        Threat(id="t_high", title="High", stride=StrideCategory.SPOOFING, risk=build_risk_assessment(3, 5)),
        Threat(id="t_med", title="Medium", stride=StrideCategory.REPUDIATION, risk=build_risk_assessment(3, 3)),
        Threat(id="t_low", title="Low", stride=StrideCategory.DENIAL_OF_SERVICE, risk=build_risk_assessment(1, 2)),
    ]
    return base.model_copy(update={"threats": threats})


def _heuristic(score_l: int, score_i: int) -> HeuristicThreat:
    return HeuristicThreat(
        id="h",
        title="h",
        description="d",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(score_l, score_i),
    )


def _result(max_score: float | None, heuristics: list[HeuristicThreat]) -> AnalysisResult:
    res = AnalysisResult(engine_version="t", document_title="T", heuristic_threats=heuristics)
    res.summary.max_risk_score = max_score
    return res


@pytest.mark.parametrize("max_score", [None, 4.0, 10.0, 16.0, 25.0])
def test_builder_payload_urgency_and_bands(max_score: float | None) -> None:
    doc = _doc_with_banded_threats()
    # low-score heuristic exercises the heuristic-loop "low" severity band
    res = _result(max_score, [_heuristic(1, 2)])
    payload = build_premium_report_payload(doc, res, level=ReportLevel.DEEP)
    assert payload is not None
    assert payload.executive_summary is not None
