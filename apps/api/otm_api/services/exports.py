"""Geração de artefactos de exportação a partir do documento e/ou análise."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_exporters import (
    export_analysis_json,
    export_analysis_markdown,
    export_document_json,
    export_document_markdown,
    export_flowchart_mermaid,
    export_threat_model_bundle_json,
)
from otm_threat_engine import AnalysisResult

from otm_api.domain.export_formats import ExportFormat
from otm_api.services.analysis import run_analysis

_ANALYSIS_REQUIRED_ERROR = "analysis required but not resolved"


def _require_analysis(resolved: AnalysisResult | None) -> AnalysisResult:
    if resolved is None:
        raise RuntimeError(_ANALYSIS_REQUIRED_ERROR)
    return resolved


def build_exports(
    doc: ThreatModelDocument,
    *,
    formats: list[ExportFormat],
    analysis: AnalysisResult | None = None,
    pack_id: str | None = None,
    locale: str | None = None,
) -> dict[str, str]:
    """
    Devolve mapa formato → texto.
    Formatos que exigem análise obtêm-na via `analysis` ou executam `run_analysis`.
    """
    need_analysis = any(
        f in (ExportFormat.analysis_json, ExportFormat.analysis_markdown, ExportFormat.bundle_json) for f in formats
    )
    resolved = analysis
    if need_analysis and resolved is None:
        resolved = run_analysis(doc, pack_id=pack_id)

    out: dict[str, str] = {}
    # `out` é indexado pelo formato, por isso uma entrada repetida em `formats` sobrescrevia a
    # chave que acabara de escrever — mas a exportação corria na mesma. Nada no caminho do pedido
    # deduplicava a lista e nada lhe limita o comprimento: medido contra servidor real na postura
    # por omissão, um pedido de 47 KB com `analysis_markdown` 2000 vezes custou 558 ms e devolveu
    # exactamente os mesmos 14 459 bytes que um pedido com uma só, deixando um `GET /health` à
    # espera 158 ms. `dict` mantém a chave na posição da **primeira** inserção, portanto colapsar
    # antes do ciclo devolve as mesmas chaves, pela mesma ordem, com os mesmos valores.
    for fmt in dict.fromkeys(formats):
        match fmt:
            case ExportFormat.document_json:
                out[fmt.value] = export_document_json(doc)
            case ExportFormat.document_markdown:
                out[fmt.value] = export_document_markdown(doc, locale=locale)
            case ExportFormat.flowchart_mermaid:
                out[fmt.value] = export_flowchart_mermaid(doc)
            case ExportFormat.analysis_json:
                out[fmt.value] = export_analysis_json(_require_analysis(resolved))
            case ExportFormat.analysis_markdown:
                out[fmt.value] = export_analysis_markdown(_require_analysis(resolved), locale=locale)
            case ExportFormat.bundle_json:
                out[fmt.value] = export_threat_model_bundle_json(doc, _require_analysis(resolved))
    return out
