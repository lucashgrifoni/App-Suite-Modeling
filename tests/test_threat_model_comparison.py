"""Testes do diff unificado (estrutura + análise) e de diff de AnalysisResult."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import DataFlow, Metadata, Threat, diff_documents, load_document_from_yaml_path
from otm_core_schema.diff_insights import structural_key_insights
from otm_core_schema.enums import StrideCategory, ThreatModelMethodology, TreatmentStatus
from otm_threat_engine import AnalysisResult, analyze_document, diff_analysis_results, compare_threat_models

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_compare_models_structural_only_matches_diff_documents() -> None:
    b = load_document_from_yaml_path(_MINIMAL)
    r = b.model_copy(deep=True)
    r = r.model_copy(
        update={
            "metadata": Metadata(
                title=b.metadata.title,
                summary=b.metadata.summary,
                owner=b.metadata.owner,
                tags=b.metadata.tags,
                document_version="9.9.9",
            )
        }
    )
    full = compare_threat_models(b, r)
    plain = diff_documents(b, r)
    assert full.structural.model_dump() == plain.model_dump()
    assert full.analysis is None
    assert full.summary.has_structural_changes
    assert not full.summary.has_analysis_changes
    assert len(full.key_insights) >= 0
    assert full.explanations
    assert any(e.type.value == "diff_change" for e in full.explanations)


def test_compare_with_analysis_shows_heuristic_delta() -> None:
    b = load_document_from_yaml_path(_MINIMAL)
    r = b.model_copy(deep=True)
    r = r.model_copy(
        update={
            "components": [
                *b.components,
                type(b.components[0]).model_validate(
                    {
                        "id": "extra_proc",
                        "name": "Extra",
                        "kind": b.components[0].kind,
                    }
                ),
            ]
        },
    )
    br = analyze_document(b, methodology=ThreatModelMethodology.STRIDE)
    rr = analyze_document(r, methodology=ThreatModelMethodology.STRIDE)
    full = compare_threat_models(b, r, baseline_analysis=br, revised_analysis=rr)
    assert full.analysis is not None
    assert full.summary.has_analysis_changes or full.structural.has_any_change()
    assert isinstance(full.risk_delta.analysis_max_score_delta, float | type(None))
    assert full.explanations


def test_diff_analysis_methodology_change() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    b = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    a = analyze_document(doc, methodology=ThreatModelMethodology.PASTA)
    d = diff_analysis_results(b, a)
    assert d.methodology_changed
    assert d.methodology_before == "stride"
    assert d.methodology_after == "pasta"


def test_diff_analysis_stable_contract_keys() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    b = analyze_document(doc)
    a = analyze_document(doc)
    d = diff_analysis_results(b, a)
    data = d.model_dump(mode="json")
    for key in (
        "methodology_before",
        "methodology_after",
        "methodology_changed",
        "heuristic_threats",
        "framework_ref_counts",
        "pack_control_hints",
    ):
        assert key in data


def test_structural_insights_detects_cross_boundary_flow() -> None:
    fin = _ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml"
    b = load_document_from_yaml_path(fin)
    r = b.model_copy(
        update={
            "data_flows": [
                *b.data_flows,
                DataFlow(
                    id="user_to_provider_probe",
                    name="probe",
                    from_component="end_user",
                    to_component="payment_webhook_provider",
                    protocol="HTTPS",
                ),
            ]
        }
    )
    d = diff_documents(b, r)
    ins = structural_key_insights(b, r, d)
    assert any("cruza fronteiras" in s.lower() for s in ins)


def test_threat_risk_change_in_document() -> None:
    base = load_document_from_yaml_path(_MINIMAL)
    if not base.threats:
        base = base.model_copy(
            update={
                "threats": [
                    Threat(
                        id="t1",
                        title="T",
                        stride=StrideCategory.SPOOFING,
                        target_component_id=base.components[0].id,
                        treatment_status=TreatmentStatus.NEW,
                    )
                ]
            }
        )
    t0 = base.threats[0]
    from otm_core_schema import RiskAssessment

    rev = base.model_copy(
        update={
            "threats": [
                t0.model_copy(
                    update={"risk": RiskAssessment(likelihood=5, impact=5, score=25.0)},
                )
            ]
        }
    )
    d = diff_documents(base, rev)
    assert d.threats.modified
