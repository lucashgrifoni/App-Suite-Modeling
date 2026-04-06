"""
Contrato JSON de `AnalysisResult`: chaves estáveis alinhadas ao consumidor TS (`apps/web/src/types/api.ts`).

Falha se o motor expuser campos de primeira ordem novos sem actualização do front (reduz drift).
"""

from __future__ import annotations

from otm_threat_engine.result import AnalysisResult

# Subconjunto mínimo que o SPA deve reconhecer para cockpit / export — espelhar em api.ts.
_TS_FIRST_CLASS_ANALYSIS_FIELDS = frozenset(
    {
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
        "model_quality_precheck",
        "methodology_completeness",
        "wizard_context_notes",
        "wizard_signal_trace",
        "anti_pattern_hits",
    }
)


def test_analysis_result_model_includes_ts_contract_fields() -> None:
    names = set(AnalysisResult.model_fields.keys())
    missing = sorted(_TS_FIRST_CLASS_ANALYSIS_FIELDS - names)
    assert not missing, f"AnalysisResult lacks fields expected by TS contract: {missing}"
