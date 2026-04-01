from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.common import (
    append_engine_lens_note,
    append_heuristics_from_entries,
    append_methodology_insights,
    boost_impact,
)
from otm_threat_engine.result import AnalysisResult, StructuralFinding


def apply_pasta_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    out = boost_impact(
        result,
        lambda h: (
            h.stride
            in {
                StrideCategory.TAMPERING,
                StrideCategory.ELEVATION_OF_PRIVILEGE,
                StrideCategory.DENIAL_OF_SERVICE,
            }
        ),
    )
    out = _append_pasta_native_heuristics(doc, out)
    out = _append_pasta_risk_findings(out)
    out = _append_pasta_insights(doc, out)
    return append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.PASTA,
        note=(
            "Lente PASTA aplicada: análise orientada a ataque, vulnerabilidade, risco e impacto "
            "com foco avançado."
        ),
    )


def _append_pasta_native_heuristics(
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> AnalysisResult:
    out = list(result.heuristic_threats)
    existing = {h.id for h in out}
    entries = [
        (
            "pasta_attack_chain_abuse",
            "[pasta] Cadeia de ataque multi-etapas",
            "Mapear pré-condições, vetor de ataque, exploração de vulnerabilidades e impacto "
            "de negócio para cenários críticos.",
            StrideCategory.ELEVATION_OF_PRIVILEGE,
            3,
            5,
        ),
        (
            "pasta_vulnerability_exposure",
            "[pasta] Exposição a vulnerabilidades exploráveis",
            "Correlacionar superfície de ataque com componentes críticos e controles ausentes "
            "para priorizar mitigação orientada a risco.",
            StrideCategory.TAMPERING,
            3,
            4,
        ),
        (
            "pasta_external_exposure",
            "[pasta] Exposição externa de serviços e interfaces",
            "Superfícies externas (APIs, gateways, edge) ampliam vetores de exploração e devem "
            "ser endurecidas com priorização por impacto.",
            StrideCategory.SPOOFING,
            4,
            4,
        ),
        (
            "pasta_critical_integration_path",
            "[pasta] Integrações críticas como caminho de ataque",
            "Integrações com terceiros podem propagar falhas e credenciais comprometidas "
            "para ativos centrais.",
            StrideCategory.TAMPERING,
            3,
            5,
        ),
        (
            "pasta_high_value_asset_impact",
            "[pasta] Impacto em ativos de alto valor",
            "Compromisso de ativos de alto valor pode gerar impacto operacional, financeiro "
            "e reputacional acima da média.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            5,
        ),
    ]
    append_heuristics_from_entries(out, existing, entries)
    for comp in doc.components:
        text = f"{comp.name} {(comp.technology or '')}".lower()
        if any(x in text for x in ("api", "gateway", "public", "internet", "edge")):
            append_heuristics_from_entries(
                out,
                existing,
                [
                    (
                        f"pasta_attack_path_{comp.id}",
                        f"[pasta] Caminho plausível de ataque via {comp.name}",
                        "Componente exposto pode ser pivô para movimento lateral e escalada "
                        "de privilégio.",
                        StrideCategory.ELEVATION_OF_PRIVILEGE,
                        4,
                        4,
                    )
                ],
                target_component_id=comp.id,
            )
    return result.model_copy(update={"heuristic_threats": out})


def _append_pasta_risk_findings(result: AnalysisResult) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code="PASTA_RISK_SURFACE",
            severity="info",
            message="PASTA fase 2: priorizar redução de superfície de ataque exposta externamente.",
        ),
        StructuralFinding(
            code="PASTA_RISK_INTEGRATIONS",
            severity="info",
            message=(
                "PASTA fase 2: tratar integrações críticas como caminhos preferenciais de ataque."
            ),
        ),
        StructuralFinding(
            code="PASTA_RISK_IMPACT",
            severity="info",
            message=(
                "PASTA fase 2: relacionar cenário de ataque a impacto operacional, financeiro "
                "e reputacional."
            ),
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_pasta_insights(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    business_goals = (doc.business_context.business_goals if doc.business_context else [])[:4]
    technical_scope = [c.name for c in doc.components[:5]]
    attack_surface = [f"{f.from_component}->{f.to_component}" for f in doc.data_flows[:5]]
    risk_findings = [
        f"{h.title} (score {h.risk.score})"
        for h in sorted(
            [x for x in result.heuristic_threats if not x.skipped_as_duplicate],
            key=lambda x: x.risk.score or 0.0,
            reverse=True,
        )[:5]
    ]
    return append_methodology_insights(
        result,
        profile="PASTA advanced / risk-centric",
        blocks=[
            (
                "business_objectives",
                "Business objectives",
                business_goals or ["Objetivos não informados"],
            ),
            ("technical_scope", "Technical scope", technical_scope or ["Escopo técnico mínimo"]),
            (
                "attack_surface",
                "Attack surface",
                attack_surface or ["Sem fluxos relevantes mapeados"],
            ),
            (
                "likely_attacker_goals",
                "Likely attacker goals",
                [
                    "Comprometer integrações externas",
                    "Exfiltrar dados sensíveis",
                    "Interromper serviço crítico",
                ],
            ),
            (
                "correlated_vulnerabilities",
                "Correlated vulnerabilities",
                [
                    "Exposição externa sem hardening completo",
                    "Validação fraca em integrações críticas",
                    "Controles insuficientes em ativos de alto valor",
                ],
            ),
            (
                "impact_summary",
                "Impact summary",
                [
                    "Operacional: indisponibilidade e degradação de serviço",
                    "Financeiro: fraude/custos de resposta e recuperação",
                    "Reputacional: perda de confiança e impacto regulatório",
                ],
            ),
            (
                "risk_oriented_findings",
                "Risk-oriented findings",
                risk_findings or ["Sem achados ativos"],
            ),
        ],
    )
