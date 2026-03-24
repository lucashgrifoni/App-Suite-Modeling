"""Testes dos exportadores (JSON, Markdown, Mermaid, bundle)."""

from __future__ import annotations

import json
from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_exporters import (
    export_analysis_json,
    export_analysis_markdown,
    export_bundle_json,
    export_document_and_analysis_markdown,
    export_document_json,
    export_document_json_obj,
    export_document_markdown,
    export_flowchart_mermaid,
    export_threat_model_bundle_json,
)
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_export_document_json_roundtrip_shape() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    text = export_document_json(doc)
    data = json.loads(text)
    assert "metadata" in data or "model" in data  # alias
    obj = export_document_json_obj(doc)
    assert isinstance(obj, dict)
    assert obj.get("metadata") or data.get("metadata")


def test_export_document_markdown_has_title_and_sections() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    md = export_document_markdown(doc)
    assert md.startswith("# ")
    assert "Componentes" in md or "Fluxos" in md


def test_export_flowchart_mermaid() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    mmd = export_flowchart_mermaid(doc)
    assert mmd.startswith("flowchart LR")
    assert "-->" in mmd


def test_export_analysis_json_and_markdown() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    aj = export_analysis_json(result)
    parsed = json.loads(aj)
    assert parsed["engine_version"]
    assert "heuristic_threats" in parsed
    md = export_analysis_markdown(result)
    assert "## Análise automática" in md
    assert "Motor" in md or "motor" in md
    assert "Resumo executivo" in md
    assert "Próximos passos sugeridos" in md


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


def test_diagram_engine_reexports_mermaid() -> None:
    from otm_diagram_engine import export_flowchart_mermaid as from_de

    doc = load_document_from_yaml_path(_MINIMAL)
    assert from_de(doc) == export_flowchart_mermaid(doc)
