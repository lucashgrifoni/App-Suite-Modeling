"""Testes de comparação estruturada entre documentos canónicos (`diff_documents`)."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import Metadata, Threat, diff_documents, load_document_from_yaml_path
from otm_core_schema.enums import StrideCategory, TreatmentStatus

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_diff_identical_documents() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = diff_documents(doc, doc.model_copy(deep=True))
    assert not d.has_any_change()
    assert "sem diferenças" in d.summary_line.lower()


def test_diff_detects_added_component() -> None:
    base = load_document_from_yaml_path(_MINIMAL)
    rev = base.model_copy(
        update={
            "components": [
                *base.components,
                type(base.components[0]).model_validate(
                    {
                        "id": "svc_new",
                        "name": "Novo serviço",
                        "kind": base.components[0].kind,
                    }
                ),
            ]
        }
    )
    out = diff_documents(base, rev)
    assert "svc_new" in out.components.added
    assert out.has_any_change()


def test_diff_detects_removed_threat_and_metadata_change() -> None:
    base = load_document_from_yaml_path(_MINIMAL)
    if not base.threats:
        base = base.model_copy(
            update={
                "threats": [
                    Threat(
                        id="t_manual",
                        title="Risco teste",
                        stride=StrideCategory.SPOOFING,
                        target_component_id=base.components[0].id,
                        treatment_status=TreatmentStatus.NEW,
                    )
                ]
            }
        )
    rev = base.model_copy(
        update={
            "threats": [],
            "metadata": Metadata(
                title=base.metadata.title,
                summary=base.metadata.summary,
                owner=base.metadata.owner,
                tags=base.metadata.tags,
                document_version="2.0.0",
            ),
        }
    )
    out = diff_documents(base, rev)
    assert out.threats.removed
    assert any(c.field == "document_version" for c in out.metadata)
    assert out.has_any_change()


def test_diff_detects_modified_model_info() -> None:
    from otm_core_schema.enums import IndustrySector

    base = load_document_from_yaml_path(_MINIMAL)
    other = (
        IndustrySector.HEALTHCARE
        if base.model_info.industry_sector != IndustrySector.HEALTHCARE
        else IndustrySector.FINANCE
    )
    rev = base.model_copy(
        update={"model_info": base.model_info.model_copy(update={"industry_sector": other})}
    )
    out = diff_documents(base, rev)
    assert any(c.field == "industry_sector" for c in out.model_info)
