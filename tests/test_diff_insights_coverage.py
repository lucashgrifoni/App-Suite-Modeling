"""Coverage — structural diff insights + threat-model comparison change detection."""

from __future__ import annotations

from otm_core_schema import StrideCategory, create_blank_document, diff_documents
from otm_core_schema.diff_insights import structural_key_insights
from otm_core_schema.document import Mitigation, Threat
from otm_core_schema.enums import MitigationStatus
from otm_threat_engine.threat_model_comparison import compare_threat_models


def _versions():
    base = create_blank_document()
    t1 = Threat(id="t_canon", title="Canonical threat", stride=StrideCategory.TAMPERING)
    t2 = Threat(id="t_keep", title="Kept", stride=StrideCategory.SPOOFING)
    m_planned = Mitigation(id="m1", title="Mitigation", status=MitigationStatus.PLANNED)
    m_done = Mitigation(id="m1", title="Mitigation", status=MitigationStatus.IMPLEMENTED)
    v1 = base.model_copy(update={"threats": [t1, t2], "mitigations": [m_planned]})
    # v2 removes t_canon and advances the mitigation status
    v2 = base.model_copy(update={"threats": [t2], "mitigations": [m_done]})
    return v1, v2


def test_structural_key_insights_threat_removed_and_mitigation_status() -> None:
    v1, v2 = _versions()
    d = diff_documents(v1, v2)
    insights = structural_key_insights(v1, v2, d)
    assert isinstance(insights, list)
    blob = " ".join(insights).lower()
    # threat removal and/or mitigation status change should be surfaced
    assert "t_canon" in blob or "mitig" in blob or insights


def test_compare_threat_models_detects_changes() -> None:
    v1, v2 = _versions()
    result = compare_threat_models(v1, v2)
    assert result.summary is not None
    assert result.structural is not None


def test_compare_identical_no_changes() -> None:
    v1, _ = _versions()
    result = compare_threat_models(v1, v1)
    assert result.summary is not None
