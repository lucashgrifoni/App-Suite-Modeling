"""
Benchmark onda 2 — templates-chave: ativos, fronteiras, pré-check, anti-leakage, PASTA degradado.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import ThreatModelMethodology
from otm_core_schema.enums import MethodologyCompletenessState
from otm_core_schema.io import load_document_from_yaml
from otm_industry_packs.loader import load_pack, load_template_yaml
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATES = [
    "industry-ecommerce",
    "admin-portal",
    "file-upload-processing",
    "api-public",
]


def _doc(tid: str):
    return load_document_from_yaml(load_template_yaml(tid))


@pytest.mark.parametrize("template_id", _TEMPLATES)
def test_wave2_template_has_assets_and_boundaries(template_id: str) -> None:
    doc = _doc(template_id)
    assert len(doc.assets) >= 2, template_id
    assert len(doc.trust_boundaries) >= 2, template_id


def test_file_upload_has_internet_dmz_app_tiers() -> None:
    doc = _doc("file-upload-processing")
    ids = {b.id for b in doc.trust_boundaries}
    assert {"internet", "dmz", "app_tier"}.issubset(ids)


@pytest.mark.parametrize("template_id", _TEMPLATES)
def test_wave2_precheck_score_reasonable(template_id: str) -> None:
    doc = _doc(template_id)
    from otm_core_schema import assess_model_precheck

    p = assess_model_precheck(doc)
    assert p.score_0_100 >= 35, (template_id, p.score_0_100)
    assert p.methodology_fit_matrix.get("stride") in ("strong", "partial", "weak")


@pytest.mark.parametrize("template_id", _TEMPLATES)
def test_wave2_analysis_has_precheck_and_completeness(template_id: str) -> None:
    doc = _doc(template_id)
    r = analyze_document(doc, methodology="stride")
    assert r.model_quality_precheck is not None
    assert r.model_quality_precheck.score_0_100 >= 0
    assert r.methodology_completeness is not None
    assert r.methodology_completeness.state.value in ("complete", "partial", "degraded")


def test_api_public_pasta_without_objectives_is_partial_or_degraded() -> None:
    doc = _doc("api-public")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PASTA)
    assert r.methodology_completeness is not None
    assert r.methodology_completeness.state in (
        MethodologyCompletenessState.PARTIAL,
        MethodologyCompletenessState.DEGRADED,
    )


def test_finance_pack_no_payment_leakage_on_admin_portal() -> None:
    doc = _doc("admin-portal")
    r = analyze_document(doc, pack=load_pack("finance"), methodology="stride")
    joined = " ".join(r.pack_control_hints).lower()
    assert "pagamento" not in joined and "payment" not in joined
