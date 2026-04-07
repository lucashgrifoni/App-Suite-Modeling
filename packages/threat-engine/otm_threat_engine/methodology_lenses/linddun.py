from __future__ import annotations

from otm_core_schema import IndustrySector, StrideCategory, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.common import (
    append_engine_lens_note,
    append_heuristics_from_entries,
    boost_impact,
)
from otm_threat_engine.result import AnalysisResult, HeuristicThreat, StructuralFinding

_PII_LITERAL = "dados pessoais"


def apply_linddun_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    out = boost_impact(
        result,
        lambda h: (
            h.stride
            in {
                StrideCategory.INFORMATION_DISCLOSURE,
                StrideCategory.SPOOFING,
                StrideCategory.REPUDIATION,
            }
        ),
    )
    out = _append_linddun_native_heuristics(doc, out)
    return append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.LINDDUN,
        note=("Lente LINDDUN aplicada: privacidade reforçada (PII, consentimento, identificação e linkabilidade)."),
    )


def _append_linddun_native_heuristics(
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> AnalysisResult:
    if not _looks_like_pii_context(doc):
        return result
    out = list(result.heuristic_threats)
    existing = {h.id for h in out}
    for flow in doc.data_flows:
        _append_linddun_flow_heuristics(out, existing, flow.id, flow.name)
    for comp in doc.components:
        if comp.kind not in {"process", "gateway"}:
            continue
        _append_linddun_component_heuristics(out, existing, comp.id, comp.name)
    findings = _append_linddun_recommendation_findings(result.structural_findings)
    return result.model_copy(update={"heuristic_threats": out, "structural_findings": findings})


def _append_linddun_flow_heuristics(
    out: list[HeuristicThreat],
    existing: set[str],
    flow_id: str,
    flow_name: str | None,
) -> None:
    base_id = f"linddun_flow_{flow_id}"
    flow_label = flow_name or flow_id
    entries = [
        (
            f"{base_id}_disclosure",
            f"[linddun] Divulgação de PII no fluxo {flow_label}",
            "Risco de disclosure de dados pessoais em trânsito. Rever minimização, pseudonimização "
            "e proteção de canal.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            5,
        ),
        (
            f"{base_id}_linkability",
            f"[linddun] Linkabilidade indevida no fluxo {flow_label}",
            "Eventos podem permitir correlacionar identidade/atividade entre contextos sem base legal clara.",
            StrideCategory.REPUDIATION,
            3,
            4,
        ),
        (
            f"{base_id}_detectability",
            f"[linddun] Detectabilidade excessiva no fluxo {flow_label}",
            "Metadados de tráfego e padrões de uso podem revelar comportamento pessoal mesmo sem conteúdo explícito.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            4,
        ),
    ]
    append_heuristics_from_entries(out, existing, entries, target_data_flow_id=flow_id)


def _append_linddun_component_heuristics(
    out: list[HeuristicThreat],
    existing: set[str],
    component_id: str,
    component_name: str,
) -> None:
    entries = [
        (
            f"linddun_comp_{component_id}_identification",
            f"[linddun] Identificação indevida em {component_name}",
            "Possível reidentificação de titulares por combinação de dados ou telemetria excessiva.",
            StrideCategory.SPOOFING,
            2,
            5,
        ),
        (
            f"linddun_comp_{component_id}_consent",
            f"[linddun] Consentimento e finalidade em {component_name}",
            "Verificar base legal, finalidade e trilha de consentimento para tratamento de dados pessoais.",
            StrideCategory.REPUDIATION,
            3,
            4,
        ),
        (
            f"linddun_comp_{component_id}_unawareness",
            f"[linddun] Falta de transparência para titulares em {component_name}",
            "Risco de unawareness: titular sem clareza de coleta, finalidade, retenção e compartilhamento.",
            StrideCategory.REPUDIATION,
            3,
            3,
        ),
        (
            f"linddun_comp_{component_id}_non_compliance",
            f"[linddun] Não conformidade regulatória em {component_name}",
            "Risco de non-compliance por ausência de controles de consentimento, minimização, retenção e governança.",
            StrideCategory.REPUDIATION,
            2,
            5,
        ),
    ]
    append_heuristics_from_entries(out, existing, entries, target_component_id=component_id)


def _append_linddun_recommendation_findings(
    structural_findings: list[StructuralFinding],
) -> list[StructuralFinding]:
    return [
        *structural_findings,
        StructuralFinding(
            code="LINDDUN_REC_CONSENT",
            severity="info",
            message="Recomendação LINDDUN: explicitar consentimento e base legal por finalidade.",
        ),
        StructuralFinding(
            code="LINDDUN_REC_MINIMIZATION",
            severity="info",
            message="Recomendação LINDDUN: aplicar minimização/pseudonimização em dados pessoais.",
        ),
        StructuralFinding(
            code="LINDDUN_REC_RETENTION",
            severity="info",
            message="Recomendação LINDDUN: definir retenção curta e descarte seguro auditável.",
        ),
        StructuralFinding(
            code="LINDDUN_REC_EXPOSURE",
            severity="info",
            message=("Recomendação LINDDUN: reduzir exposição em APIs, logs e integrações de terceiros."),
        ),
    ]


def _looks_like_pii_context(doc: ThreatModelDocument) -> bool:
    text = " ".join(
        [
            doc.metadata.title or "",
            doc.metadata.summary or "",
            " ".join(doc.metadata.tags or []),
            (doc.business_context.description if doc.business_context else "") or "",
            (doc.business_context.regulatory_context if doc.business_context else "") or "",
        ]
    ).lower()
    comp_blob = " ".join(f"{c.name or ''} {c.id or ''}" for c in doc.components).lower()
    blob = f"{text} {comp_blob}"
    privacy_tokens = (
        "pii",
        _PII_LITERAL,
        "privacidade",
        "lgpd",
        "gdpr",
        "consent",
        "phi",
        "ehr",
        "clinical",
        "paciente",
        "hipaa",
        "dados clínicos",
        "clinical record",
    )
    if any(k in blob for k in privacy_tokens):
        return True
    if doc.model_info.industry_sector == IndustrySector.HEALTHCARE:
        return True
    return any(
        a.asset_kind.value == "data" and (a.sensitivity or "").lower() in {"confidential", "restricted"}
        for a in doc.assets
    )
