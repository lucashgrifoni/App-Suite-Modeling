"""Regressão semântica — ranking de metodologia (rodada melhorias_3)."""

from __future__ import annotations

from otm_core_schema.io import load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_industry_packs.loader import load_template_yaml
from otm_core_schema import load_document_from_yaml
from otm_threat_engine import analyze_document, recommend_methodology
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _doc_from_template(tid: str):
    return load_document_from_yaml(load_template_yaml(tid))


def test_data_pipeline_etl_recommends_nist_or_keeps_declared() -> None:
    doc = _doc_from_template("data-pipeline-etl")
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.NIST_DATA_CENTRIC


def test_healthcare_clinical_recommends_linddun_or_nist_close() -> None:
    doc = _doc_from_template("industry-healthcare-clinical")
    rec = recommend_methodology(doc)
    assert rec.methodology in (
        ThreatModelMethodology.LINDDUN,
        ThreatModelMethodology.NIST_DATA_CENTRIC,
    )
    scores = rec.methodology_scores or {}
    assert float(scores.get("linddun", 0)) >= float(scores.get("stride", 0)) * 0.85


def test_core_saas_lab_saas_web_stride_not_nist_mass() -> None:
    doc = _doc_from_template("saas-web")
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.STRIDE
    assert float(( rec.methodology_scores or {}).get("nist_data_centric", 99)) < float(
        (rec.methodology_scores or {}).get("stride", 0)
    )


def test_payment_integration_template_recommends_pasta() -> None:
    doc = _doc_from_template("payment-integration")
    assert recommend_methodology(doc).methodology == ThreatModelMethodology.PASTA


def test_batch_scheduled_jobs_template_recommends_stride() -> None:
    doc = _doc_from_template("batch-scheduled-jobs")
    assert recommend_methodology(doc).methodology == ThreatModelMethodology.STRIDE


def test_industry_finance_core_template_recommends_pasta() -> None:
    doc = _doc_from_template("industry-finance-core")
    assert recommend_methodology(doc).methodology == ThreatModelMethodology.PASTA


def test_aggregate_risk_and_cockpit_populated_on_analyze() -> None:
    doc = load_document_from_yaml_path(_ROOT / "examples" / "minimal.otm.yaml")
    r = analyze_document(doc)
    assert r.aggregate_risk is not None
    assert r.decision_cockpit is not None
    assert r.aggregate_risk.get("active_threat_count", 0) >= 0
    assert r.decision_cockpit.get("risk_posture")
