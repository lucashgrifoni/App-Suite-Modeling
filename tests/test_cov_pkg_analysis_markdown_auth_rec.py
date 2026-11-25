"""The contextual-authorization root-cause recommendation in the analysis report.

`_append_root_cause_recommendations` turns clusters of findings into one consolidated
recommendation each. Four of the five (webhook, payment, cancel, coupon) are exercised by the
e-commerce example models; the authorization one never fired in any test, so the report could
have stopped emitting it without a single failure — and it is the recommendation that follows
`biz_authorization_without_business_context`, the finding that says authentication passed but
ownership was never checked.
"""

from __future__ import annotations

import pytest
from otm_core_schema import Metadata, ModelInfo, ThreatModelDocument
from otm_core_schema.document import Component, DataFlow
from otm_core_schema.enums import ComponentKind
from otm_exporters import export_analysis_markdown
from otm_threat_engine import analyze_document
from otm_threat_engine.result import AnalysisResult

_AUTH_REC_EN = "Implement contextual authorization"
_AUTH_REC_PT = "Implementar autorização contextual"
_SECTION_EN = "Consolidated root-cause recommendations"


@pytest.fixture(scope="module")
def authorization_analysis() -> AnalysisResult:
    """A checkout flow into a service that owns the ownership check."""
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="Ownership check"),
        components=[
            Component(id="user", name="User", kind=ComponentKind.USER),
            Component(id="ownership_service", name="Ownership service", kind=ComponentKind.PROCESS),
        ],
        data_flows=[
            DataFlow(id="checkout_call", name="checkout", from_component="user", to_component="ownership_service"),
        ],
    )
    return analyze_document(doc)


@pytest.fixture(scope="module")
def plain_analysis() -> AnalysisResult:
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="No business signal"),
        components=[
            Component(id="user", name="User", kind=ComponentKind.USER),
            Component(id="api", name="API", kind=ComponentKind.PROCESS),
        ],
        data_flows=[DataFlow(id="call", name="request", from_component="user", to_component="api")],
    )
    return analyze_document(doc)


def test_the_model_actually_raises_the_authorization_finding(authorization_analysis: AnalysisResult) -> None:
    """Premise of the assertions below."""
    active = [
        h
        for h in authorization_analysis.heuristic_threats
        if h.id.startswith("biz_authorization_") and not h.skipped_as_duplicate
    ]

    assert len(active) == 1


def test_the_report_recommends_contextual_authorization(authorization_analysis: AnalysisResult) -> None:
    report = export_analysis_markdown(authorization_analysis, locale="en")

    assert _SECTION_EN in report
    assert _AUTH_REC_EN in report


def test_the_recommendation_is_localised(authorization_analysis: AnalysisResult) -> None:
    report = export_analysis_markdown(authorization_analysis, locale="pt")

    assert _AUTH_REC_PT in report
    assert _AUTH_REC_EN not in report


def test_a_model_without_the_finding_gets_no_authorization_recommendation(plain_analysis: AnalysisResult) -> None:
    """Recommending a control for a problem nobody reported invents a problem."""
    report = export_analysis_markdown(plain_analysis, locale="en")

    assert _AUTH_REC_EN not in report
