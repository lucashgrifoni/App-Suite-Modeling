"""Testes dos exportadores (JSON, Markdown, Mermaid, bundle)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from otm_core_schema import (
    Component,
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    load_document_from_yaml_path,
)
from otm_core_schema.enums import ComponentKind
from otm_exporters import (
    export_analysis_json,
    export_analysis_json_obj,
    export_analysis_markdown,
    export_bundle_json,
    export_document_and_analysis_markdown,
    export_document_json,
    export_document_json_obj,
    export_document_markdown,
    export_flowchart_mermaid,
    export_threat_model_bundle_json,
    export_threat_model_bundle_obj,
)
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_SAAS_ORDERING = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"
_SNAPSHOTS = _ROOT / "tests" / "snapshots"


def test_export_document_json_roundtrip_shape() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    text = export_document_json(doc)
    data = json.loads(text)
    assert "metadata" in data or "model" in data  # alias
    obj = export_document_json_obj(doc)
    assert isinstance(obj, dict)
    assert obj.get("metadata") or data.get("metadata")
    # Contrato: string JSON e objeto python devem ser equivalentes
    assert data == obj
    # Contrato: aliases estáveis
    assert "model" in data
    assert "schema_version" in data["model"]
    assert "system_type" in data["model"]
    assert "industry_sector" in data["model"]
    assert "methodology" in data["model"]


def test_export_document_json_minimal_top_level_key_order_stable() -> None:
    """Ordem das chaves de topo alinhada a `ThreatModelDocument` (`exclude_none=True`)."""
    doc = load_document_from_yaml_path(_MINIMAL)
    assert list(export_document_json_obj(doc).keys()) == [
        "model",
        "metadata",
        "assets",
        "components",
        "data_flows",
        "trust_boundaries",
        "threats",
        "mitigations",
        "evidence_suggestions",
    ]


def test_export_document_json_saas_top_level_key_order_stable() -> None:
    doc = load_document_from_yaml_path(_SAAS_ORDERING)
    assert list(export_document_json_obj(doc).keys()) == [
        "model",
        "metadata",
        "business_context",
        "assets",
        "components",
        "data_flows",
        "trust_boundaries",
        "threats",
        "mitigations",
        "evidence_suggestions",
        "residual_risk_summary",
    ]


def test_export_document_json_minimal_model_and_metadata_key_order_stable() -> None:
    """Ordem dentro de `model` (`ModelInfo`) e `metadata` com `exclude_none=True`."""
    doc = load_document_from_yaml_path(_MINIMAL)
    obj = export_document_json_obj(doc)
    assert list(obj["model"].keys()) == [
        "schema_version",
        "system_type",
        "industry_sector",
        "methodology",
    ]
    assert list(obj["metadata"].keys()) == ["title", "summary", "owner", "tags"]


def test_export_document_json_saas_metadata_key_order_includes_document_version() -> None:
    doc = load_document_from_yaml_path(_SAAS_ORDERING)
    meta = export_document_json_obj(doc)["metadata"]
    assert list(meta.keys()) == [
        "title",
        "summary",
        "owner",
        "tags",
        "document_version",
    ]


def test_export_document_json_saas_business_context_key_order_stable() -> None:
    doc = load_document_from_yaml_path(_SAAS_ORDERING)
    bc = export_document_json_obj(doc)["business_context"]
    assert list(bc.keys()) == [
        "description",
        "business_goals",
        "stakeholders",
        "regulatory_context",
        "assumptions",
    ]


def test_export_document_json_saas_asset_and_evidence_key_order_stable() -> None:
    doc = load_document_from_yaml_path(_SAAS_ORDERING)
    obj = export_document_json_obj(doc)
    assert list(obj["assets"][0].keys()) == [
        "id",
        "name",
        "asset_kind",
        "description",
        "sensitivity",
        "related_component_ids",
        "metadata",
    ]
    assert list(obj["evidence_suggestions"][0].keys()) == [
        "id",
        "title",
        "description",
        "evidence_kind",
        "related_threat_ids",
        "metadata",
    ]


def test_export_analysis_json_plot4ai_methodology_insights_key_order_stable() -> None:
    """Contrato de `MethodologyInsights` / `MethodologyInsightBlock` na serialização JSON."""
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="LLM RAG pipeline",
                summary="prompts, retrieval e agentes",
            )
        }
    )
    obj = export_analysis_json_obj(analyze_document(doc, methodology="plot4ai"))
    mi = obj["methodology_insights"]
    assert mi is not None
    assert list(mi.keys()) == ["profile", "blocks"]
    assert mi["blocks"]
    assert list(mi["blocks"][0].keys()) == ["key", "title", "items"]


def test_export_document_json_minimal_nested_entity_key_order_stable() -> None:
    """Ordem de chaves em `Component`, `DataFlow` e `TrustBoundary` (Pydantic + exclude_none)."""
    doc = load_document_from_yaml_path(_MINIMAL)
    obj = export_document_json_obj(doc)
    assert list(obj["components"][0].keys()) == [
        "id",
        "name",
        "kind",
        "in_trust_boundary",
        "asset_ids",
        "metadata",
    ]
    assert list(obj["components"][1].keys()) == [
        "id",
        "name",
        "kind",
        "technology",
        "in_trust_boundary",
        "asset_ids",
        "metadata",
    ]
    assert list(obj["data_flows"][0].keys()) == [
        "id",
        "name",
        "from_component",
        "to_component",
        "protocol",
        "authenticated",
        "encrypted",
        "metadata",
    ]
    assert list(obj["trust_boundaries"][0].keys()) == [
        "id",
        "name",
        "member_component_ids",
    ]


def test_export_document_json_snapshot_minimal() -> None:
    """Trava o JSON do exportador; alterações devem ser intencionais."""
    doc = load_document_from_yaml_path(_MINIMAL)
    text = export_document_json(doc)
    expected = (_SNAPSHOTS / "document_json_minimal.json").read_text(encoding="utf-8")
    assert text == expected


def test_export_document_markdown_has_title_and_sections() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    md = export_document_markdown(doc)
    assert md.startswith("# ")
    assert "Componentes" in md or "Fluxos" in md


def test_export_document_markdown_minimal_heading_order_stable() -> None:
    """Contrato de ordem das secções para o exemplo mínimo (regressão silenciosa no exportador)."""
    doc = load_document_from_yaml_path(_MINIMAL)
    md = export_document_markdown(doc)
    headings = [line.strip() for line in md.splitlines() if line.startswith("## ")]
    assert headings == ["## Componentes", "## Fluxos de dados", "## Fronteiras de confiança"]


def test_export_document_markdown_full_example_heading_order_stable() -> None:
    """Ordem canónica de secções quando contexto, ativos, ameaças e mitigações existem."""
    doc = load_document_from_yaml_path(_SAAS_ORDERING)
    md = export_document_markdown(doc)
    headings = [line.strip() for line in md.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Contexto de negócio",
        "## Ativos",
        "## Componentes",
        "## Fluxos de dados",
        "## Fronteiras de confiança",
        "## Ameaças",
        "## Mitigações",
    ]


def test_export_document_markdown_snapshot_minimal() -> None:
    """
    Trava o output do exportador de documento em Markdown.
    Mudanças devem ser intencionais (não por refactor acidental).
    """
    doc = load_document_from_yaml_path(_MINIMAL)
    md = export_document_markdown(doc)
    snap = (_SNAPSHOTS / "document_markdown_minimal.md").read_text(encoding="utf-8")
    assert md == snap


def test_export_flowchart_mermaid() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    mmd = export_flowchart_mermaid(doc)
    assert mmd.startswith("flowchart LR")
    assert "-->" in mmd


def test_export_flowchart_mermaid_minimal_node_and_edge_line_counts() -> None:
    """Um bloco de declaração por componente e uma aresta por `data_flow`; termina com newline."""
    doc = load_document_from_yaml_path(_MINIMAL)
    mmd = export_flowchart_mermaid(doc)
    assert mmd.endswith("\n")
    lines = [ln for ln in mmd.splitlines() if ln.strip()]
    assert lines[0] == "flowchart LR"
    rest = lines[1:]
    node_lines = [ln for ln in rest if "-->" not in ln]
    edge_lines = [ln for ln in rest if "-->" in ln]
    assert len(node_lines) == len(doc.components)
    assert len(edge_lines) == len(doc.data_flows)


def test_export_flowchart_mermaid_sanitizes_ids_and_quotes() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)

    # adiciona um nó e um fluxo com IDs "não mermaid-friendly" e aspas no label
    doc.components.append(
        doc.components[0].model_copy(update={"id": "api-gw", "name": 'API "Gateway"'})
    )
    doc.data_flows.append(
        doc.data_flows[0].model_copy(
            update={
                "id": "http-in-2",
                "name": 'HTTP "alt"',
                "from_component": "user",
                "to_component": "api-gw",
            }
        )
    )

    mmd = export_flowchart_mermaid(doc)
    assert "api_gw[\"API 'Gateway'\"]" in mmd
    assert "user -->|HTTP 'alt'| api_gw" in mmd
    assert mmd.endswith("\n")


def test_export_analysis_json_and_markdown() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    aj = export_analysis_json(result)
    parsed = json.loads(aj)
    assert parsed["engine_version"]
    assert "heuristic_threats" in parsed
    # Contrato: objeto python e string JSON devem ser equivalentes
    assert parsed == export_analysis_json_obj(result)
    # Contrato: chaves raiz mínimas estáveis
    expected_top = {
        "engine_version",
        "methodology",
        "document_title",
        "structural_findings",
        "trust_boundary_findings",
        "heuristic_threats",
        "summary",
    }
    assert expected_top.issubset(set(parsed.keys()))
    md = export_analysis_markdown(result)
    assert "## Análise automática" in md
    assert "Motor" in md or "motor" in md
    assert "Resumo executivo" in md
    assert "Próximos passos sugeridos" in md


def test_export_analysis_json_minimal_top_level_key_order_stable() -> None:
    """Ordem das chaves de topo alinhada a `AnalysisResult`."""
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    assert list(export_analysis_json_obj(result).keys()) == [
        "engine_version",
        "methodology",
        "methodology_recommendation_reason",
        "document_title",
        "structural_findings",
        "trust_boundary_findings",
        "heuristic_threats",
        "summary",
        "methodology_insights",
        "industry_pack_id",
        "pack_control_hints",
        "explanations",
        "ai_system_context",
    ]


def test_export_analysis_json_summary_minimal_key_order_stable() -> None:
    """Ordem das chaves em `summary` alinhada a `AnalysisSummary`."""
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    summary = export_analysis_json_obj(result)["summary"]
    assert list(summary.keys()) == [
        "structural_findings",
        "trust_boundary_findings",
        "heuristic_threats_generated",
        "heuristic_threats_skipped_duplicate",
        "pack_threats_generated",
        "pack_threats_skipped_duplicate",
        "max_risk_score",
        "framework_ref_counts_by_catalog",
    ]


def test_export_analysis_json_structural_finding_key_order_stable() -> None:
    """Ordem em `StructuralFinding` quando existem avisos estruturais."""
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="struct-export-order"),
        components=[
            Component(id="a", name="A", kind=ComponentKind.PROCESS),
            Component(id="b", name="B", kind=ComponentKind.PROCESS),
        ],
        data_flows=[],
    )
    obj = export_analysis_json_obj(analyze_document(doc))
    assert obj["structural_findings"]
    assert list(obj["structural_findings"][0].keys()) == ["code", "severity", "message"]


def test_export_analysis_json_minimal_framework_ref_key_order_stable() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    obj = export_analysis_json_obj(analyze_document(doc))
    h = next(h for h in obj["heuristic_threats"] if h["framework_refs"])
    assert list(h["framework_refs"][0].keys()) == ["framework", "control_id", "notes"]


def test_export_analysis_json_minimal_heuristic_and_boundary_finding_key_order_stable() -> None:
    """Ordem em `HeuristicThreat`, `RiskAssessment` aninhado e `TrustBoundaryFinding`."""
    doc = load_document_from_yaml_path(_MINIMAL)
    obj = export_analysis_json_obj(analyze_document(doc))
    h0 = obj["heuristic_threats"][0]
    assert list(h0.keys()) == [
        "id",
        "title",
        "description",
        "stride",
        "target_component_id",
        "target_data_flow_id",
        "target_asset_id",
        "risk",
        "skipped_as_duplicate",
        "framework_refs",
    ]
    assert list(h0["risk"].keys()) == ["likelihood", "impact", "score"]
    assert list(obj["trust_boundary_findings"][0].keys()) == [
        "code",
        "message",
        "data_flow_id",
        "from_boundary_id",
        "to_boundary_id",
    ]


def test_export_document_json_saas_threat_mitigation_residual_key_order_stable() -> None:
    """Ordem em `Threat`, `Mitigation` e `ResidualRiskSummary` com `exclude_none=True`."""
    doc = load_document_from_yaml_path(_SAAS_ORDERING)
    obj = export_document_json_obj(doc)
    assert list(obj["threats"][0].keys()) == [
        "id",
        "title",
        "description",
        "stride",
        "target_component_id",
        "target_asset_id",
        "risk",
        "treatment_status",
        "assignee",
        "due_date",
        "framework_refs",
        "evidence_suggestion_ids",
        "metadata",
    ]
    assert list(obj["threats"][0]["risk"].keys()) == ["likelihood", "impact", "score"]
    assert list(obj["mitigations"][0].keys()) == [
        "id",
        "title",
        "status",
        "owner",
        "threat_ids",
        "framework_refs",
        "metadata",
    ]
    assert list(obj["residual_risk_summary"].keys()) == ["aggregate_score", "notes"]


def test_export_analysis_markdown_harmonized_minimal_h3_heading_order_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contrato de ordem das secções `###` no modo harmonizado (exemplo mínimo + STRIDE)."""
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "harmonized")
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    md = export_analysis_markdown(result)
    headings = [line.strip() for line in md.splitlines() if line.startswith("### ")]
    assert headings == [
        "### Referências a frameworks (agregado)",
        "### Fluxos entre fronteiras",
        "### Resumo executivo",
        "### Categorias de risco (top)",
        "### Ameaças sugeridas (harmonizadas)",
        "### Explicabilidade (resumo)",
        "### Próximos passos sugeridos",
    ]


def test_export_analysis_markdown_snapshot_minimal_harmonized() -> None:
    """
    Este teste trava o output do exportador Markdown.
    Se mudar, deve ser intencional e revisado (não por refatoração acidental).
    """
    os.environ["OTM_MARKDOWN_VIEW_MODE"] = "harmonized"
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    md = export_analysis_markdown(result)

    expected = (_SNAPSHOTS / "analysis_markdown_minimal_harmonized.md").read_text(encoding="utf-8")
    assert md == expected


def test_export_full_markdown_concat() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    full = export_document_and_analysis_markdown(doc, result)
    assert full.startswith("# ")
    assert "## Análise automática" in full


def test_export_bundle_json() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    raw = export_threat_model_bundle_json(doc, result)
    bundle = json.loads(raw)
    assert bundle["document"] is not None
    assert bundle["analysis"] is not None
    assert bundle["analysis"]["summary"]["heuristic_threats_generated"] >= 0

    empty = export_bundle_json(document=None, analysis=None)
    assert json.loads(empty) == {"document": None, "analysis": None}


def test_export_bundle_json_string_top_level_key_order_stable() -> None:
    raw = export_bundle_json(document={"ok": True}, analysis={})
    assert list(json.loads(raw).keys()) == ["document", "analysis"]


def test_export_threat_model_bundle_obj_matches_parsed_bundle_json() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    obj = export_threat_model_bundle_obj(doc, result)
    parsed = json.loads(export_threat_model_bundle_json(doc, result))
    assert obj == parsed


def test_export_threat_model_bundle_obj_top_level_key_order_stable() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    assert list(export_threat_model_bundle_obj(doc, result).keys()) == ["document", "analysis"]
    assert list(export_threat_model_bundle_obj(doc, None).keys()) == ["document", "analysis"]


def test_export_threat_model_bundle_obj_analysis_none() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    obj = export_threat_model_bundle_obj(doc, None)
    assert set(obj.keys()) == {"document", "analysis"}
    assert obj["analysis"] is None
    assert isinstance(obj["document"], dict)


def test_export_threat_model_bundle_json_contract_minimal_stride() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    raw = export_threat_model_bundle_json(doc, result, indent=2)
    payload = json.loads(raw)

    assert set(payload.keys()) == {"document", "analysis"}
    assert isinstance(payload["document"], dict)
    assert isinstance(payload["analysis"], dict)

    # Documento: chaves raiz estáveis
    doc_out = payload["document"]
    assert "metadata" in doc_out
    assert "model" in doc_out
    assert isinstance(doc_out.get("components"), list)
    assert isinstance(doc_out.get("data_flows"), list)

    # Análise: chaves raiz estáveis
    analysis_out = payload["analysis"]
    expected_top = {
        "engine_version",
        "methodology",
        "document_title",
        "structural_findings",
        "trust_boundary_findings",
        "heuristic_threats",
        "summary",
        "industry_pack_id",
        "pack_control_hints",
        "methodology_recommendation_reason",
        "methodology_insights",
        "explanations",
        "ai_system_context",
    }
    assert expected_top.issubset(set(analysis_out.keys()))
    assert analysis_out["methodology"] == "stride"
    assert isinstance(analysis_out["heuristic_threats"], list)

    # Um pouco de determinismo sem snapshot gigante
    ids = [t["id"] for t in analysis_out["heuristic_threats"]]
    assert "eng_flow_to_worker_tampering" in ids


def test_export_threat_model_bundle_json_contract_plot4ai() -> None:
    # O objetivo é travar que o bundle preserva insights especializados quando a análise os produz.
    base = load_document_from_yaml_path(_MINIMAL)
    doc = base.model_copy(
        update={
            "metadata": base.metadata.model_copy(
                update={"title": "Plataforma LLM com RAG e agentes"}
            )
        }
    )
    result = analyze_document(doc, methodology="plot4ai")
    payload = json.loads(export_threat_model_bundle_json(doc, result, indent=2))

    analysis_out = payload["analysis"]
    assert analysis_out["methodology"] == "plot4ai"
    assert analysis_out["methodology_insights"] is not None
    assert analysis_out["methodology_insights"]["profile"]


def test_diagram_engine_reexports_mermaid() -> None:
    from otm_diagram_engine import export_flowchart_mermaid as from_de

    doc = load_document_from_yaml_path(_MINIMAL)
    assert from_de(doc) == export_flowchart_mermaid(doc)
