from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.common import (
    append_engine_lens_note,
    append_heuristics_from_entries,
    boost_impact,
    has_any,
)
from otm_threat_engine.result import AnalysisResult, HeuristicThreat, StructuralFinding


def apply_nist_data_centric_lens(result: AnalysisResult) -> AnalysisResult:
    out = boost_impact(
        result,
        lambda h: h.target_asset_id is not None or h.stride == StrideCategory.INFORMATION_DISCLOSURE,
    )
    out = _append_nist_data_centric_native_heuristics(out)
    out = _append_nist_data_centric_focus_findings(out)
    out = _append_nist_data_centric_prep_notes(out)
    return append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.NIST_DATA_CENTRIC,
        note="Lente NIST Data-Centric aplicada: foco reforçado em dados críticos.",
    )


def _append_nist_data_centric_prep_notes(result: AnalysisResult) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code="NIST_DC_PREP_CLASSIFICATION",
            severity="info",
            message=("Preparação NIST DC v1: classificar dados críticos por sensibilidade e impacto."),
        ),
        StructuralFinding(
            code="NIST_DC_PREP_DATA_PATHS",
            severity="info",
            message="Preparação NIST DC v1: mapear caminhos de dados sensíveis ponta a ponta.",
        ),
        StructuralFinding(
            code="NIST_DC_PREP_CONTROLS",
            severity="info",
            message=("Preparação NIST DC v1: alinhar controles por contexto de dado (repouso/trânsito/uso)."),
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_nist_data_centric_native_heuristics(result: AnalysisResult) -> AnalysisResult:
    out = list(result.heuristic_threats)
    existing = {h.id for h in out}
    by_comp: dict[str, list[HeuristicThreat]] = {}
    by_flow: dict[str, list[HeuristicThreat]] = {}
    for h in out:
        if h.target_component_id:
            by_comp.setdefault(h.target_component_id, []).append(h)
        if h.target_data_flow_id:
            by_flow.setdefault(h.target_data_flow_id, []).append(h)
    sensitive_components = _collect_sensitive_component_ids(by_comp)
    sensitive_flows = _collect_sensitive_flow_ids(by_flow)
    for comp_id in sorted(sensitive_components):
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    f"nist_dc_classified_data_{comp_id}",
                    f"[nist_data_centric] Dados classificados no componente {comp_id}",
                    "Componente aparenta tratar dados críticos/classificados; aplicar controles "
                    "proporcionais ao nível de sensibilidade.",
                    StrideCategory.INFORMATION_DISCLOSURE,
                    3,
                    5,
                ),
            ],
            target_component_id=comp_id,
        )
    for flow_id in sorted(sensitive_flows):
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    f"nist_dc_sensitive_path_{flow_id}",
                    f"[nist_data_centric] Caminho de dados sensíveis em {flow_id}",
                    "Fluxo pode carregar dados sensíveis; reforçar proteção ponta a ponta, "
                    "autenticação forte e rastreabilidade.",
                    StrideCategory.INFORMATION_DISCLOSURE,
                    4,
                    5,
                ),
                (
                    f"nist_dc_in_transit_{flow_id}",
                    f"[nist_data_centric] Proteção em trânsito no fluxo {flow_id}",
                    "Reforçar criptografia, integridade e autenticação de canal para dados críticos em trânsito.",
                    StrideCategory.TAMPERING,
                    4,
                    5,
                ),
            ],
            target_data_flow_id=flow_id,
        )
    for comp_id, items in by_comp.items():
        if comp_id not in sensitive_components:
            continue
        has_datastore_signal = any("datastore" in (h.title.lower() + " " + h.description.lower()) for h in items)
        has_process_signal = any(
            x in (h.title.lower() + " " + h.description.lower())
            for h in items
            for x in ("api", "process", "gateway", "serviço", "service")
        )
        _append_nist_dc_state_heuristics(
            out,
            existing,
            comp_id=comp_id,
            has_datastore_signal=has_datastore_signal,
            has_process_signal=has_process_signal,
        )
    return result.model_copy(update={"heuristic_threats": out})


def _collect_sensitive_component_ids(by_comp: dict[str, list[HeuristicThreat]]) -> set[str]:
    return {comp_id for comp_id, items in by_comp.items() if _looks_sensitive_component_heuristics(items)}


def _collect_sensitive_flow_ids(by_flow: dict[str, list[HeuristicThreat]]) -> set[str]:
    return {flow_id for flow_id, items in by_flow.items() if _looks_sensitive_flow_heuristics(items)}


def _looks_sensitive_component_heuristics(items: list[HeuristicThreat]) -> bool:
    text = " ".join((h.title + " " + h.description).lower() for h in items)
    return has_any(
        text,
        (
            "pii",
            "dados pessoais",
            "sensível",
            "sensitive",
            "confidential",
            "restricted",
            "finance",
            "health",
            "payment",
            "lgpd",
            "gdpr",
        ),
    ) or any((h.risk.score or 0.0) >= 12.0 for h in items)


def _looks_sensitive_flow_heuristics(items: list[HeuristicThreat]) -> bool:
    text = " ".join((h.title + " " + h.description).lower() for h in items)
    return has_any(
        text,
        (
            "canal do fluxo",
            "atravessa fronteira",
            "confidencialidade",
            "integridade",
            "dados sensíveis",
        ),
    ) or any((h.risk.score or 0.0) >= 12.0 for h in items)


def _append_nist_data_centric_focus_findings(result: AnalysisResult) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code="NIST_DC_FOCUS_DATA_PROTECTION",
            severity="info",
            message="NIST DC v1: priorizar proteção de dados (trânsito, repouso, uso).",
        ),
        StructuralFinding(
            code="NIST_DC_FOCUS_ACCESS",
            severity="info",
            message="NIST DC v1: reforçar controles de acesso por classificação de dado.",
        ),
        StructuralFinding(
            code="NIST_DC_FOCUS_AUDIT",
            severity="info",
            message="NIST DC v1: garantir auditoria de acesso e trilha para dados sensíveis.",
        ),
        StructuralFinding(
            code="NIST_DC_FOCUS_SEGREGATION",
            severity="info",
            message="NIST DC v1: aplicar segregação lógica/física conforme criticidade do dado.",
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_nist_dc_state_heuristics(
    out: list[HeuristicThreat],
    existing: set[str],
    *,
    comp_id: str,
    has_datastore_signal: bool,
    has_process_signal: bool,
) -> None:
    if has_datastore_signal:
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    f"nist_dc_at_rest_{comp_id}",
                    f"[nist_data_centric] Proteção em repouso no componente {comp_id}",
                    "Aplicar hardening de storage, criptografia em repouso, gestão de chaves e segregação de dados.",
                    StrideCategory.INFORMATION_DISCLOSURE,
                    3,
                    5,
                )
            ],
            target_component_id=comp_id,
        )
    if has_process_signal:
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    f"nist_dc_in_use_{comp_id}",
                    f"[nist_data_centric] Proteção em uso no componente {comp_id}",
                    "Reforçar controle de acesso contextual, minimização de dados e isolamento durante processamento.",
                    StrideCategory.ELEVATION_OF_PRIVILEGE,
                    3,
                    4,
                )
            ],
            target_component_id=comp_id,
        )
