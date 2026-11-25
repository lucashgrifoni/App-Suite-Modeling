"""Comparação de modelos e análises — sem HTTP."""

from __future__ import annotations

from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_threat_engine import AnalysisResult
from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.comparison_models import AnalysisDiff, ThreatModelComparisonResult
from otm_threat_engine.threat_model_comparison import compare_threat_models

from otm_api.services.analysis import run_analysis


def comparison_from_validated_documents(
    baseline_doc: ThreatModelDocument,
    revised_doc: ThreatModelDocument,
    *,
    baseline_analysis: dict[str, Any] | AnalysisResult | None = None,
    revised_analysis: dict[str, Any] | AnalysisResult | None = None,
    run_analysis_flag: bool = False,
    pack_id: str | None = None,
) -> ThreatModelComparisonResult:
    """
    Documentos já validados (ex.: via `document_from_payload_or_422`).

    Análises explícitas têm prioridade sobre `run_analysis_flag`. Aceitam-se `AnalysisResult`
    já validados, para que a rota possa validá-los antes de os emparelhar com o documento
    respetivo (ver `routers/models.py::compare_models`) sem os validar duas vezes —
    `model_validate` devolve a instância tal como está.
    """
    ba: AnalysisResult | None = None
    ra: AnalysisResult | None = None
    if baseline_analysis is not None and revised_analysis is not None:
        ba = AnalysisResult.model_validate(baseline_analysis)
        ra = AnalysisResult.model_validate(revised_analysis)
    elif run_analysis_flag:
        ba = run_analysis(baseline_doc, pack_id=pack_id, methodology=None, auto_recommend_methodology=False)
        ra = run_analysis(revised_doc, pack_id=pack_id, methodology=None, auto_recommend_methodology=False)
    return compare_threat_models(baseline_doc, revised_doc, baseline_analysis=ba, revised_analysis=ra)


def analysis_diff_from_payloads(
    *,
    baseline_analysis: dict[str, Any],
    revised_analysis: dict[str, Any],
) -> AnalysisDiff:
    b = AnalysisResult.model_validate(baseline_analysis)
    a = AnalysisResult.model_validate(revised_analysis)
    return diff_analysis_results(b, a)
