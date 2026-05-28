"""Coverage — render_premium_html across tiers/bands using a richly-banded payload."""

from __future__ import annotations

import pytest
from otm_core_schema import StrideCategory, create_blank_document
from otm_core_schema.document import Threat
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment

pytest.importorskip("fastapi")
from otm_report_premium.builder import build_premium_report_payload  # noqa: E402
from otm_report_premium.enums import ReportLevel  # noqa: E402
from otm_report_premium.render_html import render_premium_html  # noqa: E402


def _banded_doc():
    base = create_blank_document()
    threats = [
        Threat(id=f"t{i}", title=f"T{i}", stride=StrideCategory.TAMPERING, risk=build_risk_assessment(lk, i_))
        for i, (lk, i_) in enumerate([(5, 5), (3, 5), (3, 3), (1, 2), (2, 2), (4, 4)])
    ]
    return base.model_copy(update={"threats": threats})


def _heuristics():
    return [
        HeuristicThreat(
            id=f"h{i}", title=f"H{i}", description="d",
            stride=StrideCategory.SPOOFING, risk=build_risk_assessment(lk, im),
            target_component_id="c1",
        )
        for i, (lk, im) in enumerate([(5, 5), (3, 4), (2, 2), (1, 2)])
    ]


def test_render_html_all_tiers_and_bands() -> None:
    doc = _banded_doc()
    res = AnalysisResult(engine_version="t", document_title="T", heuristic_threats=_heuristics())
    res.summary.max_risk_score = 25.0
    payload = build_premium_report_payload(doc, res, level=ReportLevel.DEEP)
    html = render_premium_html(payload)
    assert "<html" in html.lower() or "<section" in html.lower()


def test_render_html_low_risk() -> None:
    doc = create_blank_document()
    res = AnalysisResult(engine_version="t", document_title="T", heuristic_threats=[])
    res.summary.max_risk_score = 3.0
    payload = build_premium_report_payload(doc, res, level=ReportLevel.STANDARD)
    assert render_premium_html(payload)
