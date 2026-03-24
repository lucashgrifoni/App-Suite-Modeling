"""Abstração simples para múltiplas metodologias de threat modeling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from otm_core_schema import (
    IndustrySector,
    RiskAssessment,
    StrideCategory,
    SystemType,
    ThreatModelDocument,
    ThreatModelMethodology,
)

from otm_threat_engine.result import (
    AnalysisResult,
    HeuristicThreat,
    MethodologyInsightBlock,
    MethodologyInsights,
    StructuralFinding,
)

_PII_LITERAL = "dados pessoais"


@dataclass(frozen=True)
class MethodologyRecommendation:
    methodology: ThreatModelMethodology
    reason: str


class ThreatModelingEngine(Protocol):
    methodology: ThreatModelMethodology

    def analyze(self, doc: ThreatModelDocument, *, pack=None) -> AnalysisResult: ...


def recommend_methodology(doc: ThreatModelDocument) -> MethodologyRecommendation:
    """
    Regras iniciais e explicáveis de recomendação.
    Mantém STRIDE como default quando não há sinal claro.
    """
    text = " ".join(
        [
            doc.metadata.title or "",
            doc.metadata.summary or "",
            " ".join(doc.metadata.tags or []),
            (doc.business_context.description if doc.business_context else "") or "",
            (doc.business_context.regulatory_context if doc.business_context else "") or "",
        ]
    ).lower()

    for predicate, methodology, reason in _recommendation_rules(doc, text):
        if predicate:
            return MethodologyRecommendation(methodology=methodology, reason=reason)

    return MethodologyRecommendation(
        methodology=ThreatModelMethodology.STRIDE,
        reason="Sem sinal forte para outra metodologia; STRIDE é o default do produto.",
    )


def _append_engine_lens_note(
    result: AnalysisResult,
    *,
    methodology: ThreatModelMethodology,
    note: str,
) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code=f"ENGINE_LENS_{methodology.value.upper()}",
            severity="info",
            message=note,
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_methodology_insights(
    result: AnalysisResult,
    *,
    profile: str,
    blocks: list[tuple[str, str, list[str]]],
) -> AnalysisResult:
    insight_blocks = [
        MethodologyInsightBlock(key=key, title=title, items=items) for key, title, items in blocks
    ]
    insights = MethodologyInsights(profile=profile, blocks=insight_blocks)
    return result.model_copy(update={"methodology_insights": insights})


def apply_methodology_lens(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    methodology: ThreatModelMethodology,
) -> AnalysisResult:
    """
    Influência inicial por metodologia sem duplicar engine inteira.
    STRIDE mantém saída base; outras metodologias ajustam foco/risco.
    """
    if methodology == ThreatModelMethodology.STRIDE:
        return result

    if methodology == ThreatModelMethodology.LINDDUN:
        return _apply_linddun_lens(doc, result)

    if methodology == ThreatModelMethodology.NIST_DATA_CENTRIC:
        return _apply_nist_data_centric_lens(result)

    if methodology == ThreatModelMethodology.OCTAVE_ALLEGRO:
        return _apply_octave_lens(result)

    if methodology == ThreatModelMethodology.CIA_DIE:
        return _apply_cia_die_lens(result)

    if methodology == ThreatModelMethodology.PASTA:
        return _apply_pasta_lens(doc, result)

    if methodology == ThreatModelMethodology.PLOT4AI:
        return _apply_plot4ai_lens(doc, result)

    return result


def _boost_impact(result: AnalysisResult, predicate) -> AnalysisResult:
    boosted = []
    for h in result.heuristic_threats:
        if predicate(h):
            new_impact = min(5, h.risk.impact + 1)
            risk = h.risk.model_copy(
                update={
                    "impact": new_impact,
                    "score": float(h.risk.likelihood * new_impact),
                }
            )
            boosted.append(h.model_copy(update={"risk": risk}))
        else:
            boosted.append(h)
    return result.model_copy(update={"heuristic_threats": boosted})


def _apply_linddun_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    out = _boost_impact(
        result,
        lambda h: h.stride
        in {
            StrideCategory.INFORMATION_DISCLOSURE,
            StrideCategory.SPOOFING,
            StrideCategory.REPUDIATION,
        },
    )
    out = _append_linddun_native_heuristics(doc, out)
    return _append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.LINDDUN,
        note=(
            "Lente LINDDUN aplicada: privacidade reforçada (PII, consentimento, "
            "identificação e linkabilidade)."
        ),
    )


def _apply_nist_data_centric_lens(result: AnalysisResult) -> AnalysisResult:
    out = _boost_impact(
        result,
        lambda h: h.target_asset_id is not None
        or h.stride == StrideCategory.INFORMATION_DISCLOSURE,
    )
    out = _append_nist_data_centric_native_heuristics(out)
    out = _append_nist_data_centric_focus_findings(out)
    out = _append_nist_data_centric_prep_notes(out)
    return _append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.NIST_DATA_CENTRIC,
        note="Lente NIST Data-Centric aplicada: foco reforçado em dados críticos.",
    )


def _apply_octave_lens(result: AnalysisResult) -> AnalysisResult:
    return _append_engine_lens_note(
        result,
        methodology=ThreatModelMethodology.OCTAVE_ALLEGRO,
        note="Lente OCTAVE Allegro aplicada: priorize ativos críticos e risco de negócio.",
    )


def _apply_cia_die_lens(result: AnalysisResult) -> AnalysisResult:
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    active_sorted = sorted(active, key=lambda h: h.risk.score or 0.0, reverse=True)[:10]
    keep_ids = {h.id for h in active_sorted}
    concise = [
        h for h in result.heuristic_threats if h.skipped_as_duplicate or h.id in keep_ids
    ]
    out = result.model_copy(update={"heuristic_threats": concise})
    return _append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.CIA_DIE,
        note="Lente CIA/CIA-DIE aplicada: resumo simplificado com ameaças de maior impacto.",
    )


def _apply_pasta_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    # PASTA fase 2: reforço risk-centric para cenários de ataque e impacto de negócio.
    out = _boost_impact(
        result,
        lambda h: h.stride
        in {
            StrideCategory.TAMPERING,
            StrideCategory.ELEVATION_OF_PRIVILEGE,
            StrideCategory.DENIAL_OF_SERVICE,
        },
    )
    out = _append_pasta_native_heuristics(doc, out)
    out = _append_pasta_risk_findings(out)
    out = _append_pasta_insights(doc, out)
    return _append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.PASTA,
        note=(
            "Lente PASTA aplicada: análise orientada a ataque, vulnerabilidade, risco e impacto "
            "com foco avançado."
        ),
    )


def _apply_plot4ai_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    out = _boost_impact(
        result,
        lambda h: h.stride
        in {
            StrideCategory.INFORMATION_DISCLOSURE,
            StrideCategory.TAMPERING,
            StrideCategory.ELEVATION_OF_PRIVILEGE,
        },
    )
    out = _append_plot4ai_native_heuristics(doc, out)
    out = _append_plot4ai_recommendations(out)
    out = _append_plot4ai_insights(doc, out)
    return _append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.PLOT4AI,
        note="Lente PLOT4ai aplicada: foco em ameaças de AI/LLM (prompt, modelo, pipeline).",
    )


def _append_linddun_native_heuristics(
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> AnalysisResult:
    """
    Heurísticas iniciais nativas de privacidade (incrementais, sem engine nova).
    """
    pii_context = _looks_like_pii_context(doc)
    if not pii_context:
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
    did = f"{base_id}_disclosure"
    lid = f"{base_id}_linkability"
    detid = f"{base_id}_detectability"
    flow_label = flow_name or flow_id
    entries = [
        (
            did,
            f"[linddun] Divulgação de PII no fluxo {flow_label}",
            "Risco de disclosure de dados pessoais em trânsito. Rever minimização, pseudonimização e proteção de canal.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            5,
        ),
        (
            lid,
            f"[linddun] Linkabilidade indevida no fluxo {flow_label}",
            "Eventos podem permitir correlacionar identidade/atividade entre contextos sem base legal clara.",
            StrideCategory.REPUDIATION,
            3,
            4,
        ),
        (
            detid,
            f"[linddun] Detectabilidade excessiva no fluxo {flow_label}",
            "Metadados de tráfego e padrões de uso podem revelar comportamento pessoal mesmo sem conteúdo explícito.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            4,
        ),
    ]
    _append_heuristics_from_entries(out, existing, entries, target_data_flow_id=flow_id)


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
    _append_heuristics_from_entries(out, existing, entries, target_component_id=component_id)


def _append_heuristics_from_entries(
    out: list[HeuristicThreat],
    existing: set[str],
    entries: list[tuple[str, str, str, StrideCategory, int, int]],
    *,
    target_component_id: str | None = None,
    target_data_flow_id: str | None = None,
) -> None:
    for hid, title, desc, stride, likelihood, impact in entries:
        if hid in existing:
            continue
        out.append(
            HeuristicThreat(
                id=hid,
                title=title,
                description=desc,
                stride=stride,
                target_component_id=target_component_id,
                target_data_flow_id=target_data_flow_id,
                risk=RiskAssessment(
                    likelihood=likelihood,
                    impact=impact,
                    score=float(likelihood * impact),
                ),
                skipped_as_duplicate=False,
            )
        )
        existing.add(hid)


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
            message="Recomendação LINDDUN: reduzir exposição em APIs, logs e integrações de terceiros.",
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
    if any(k in text for k in ("pii", _PII_LITERAL, "privacidade", "lgpd", "gdpr", "consent")):
        return True

    for a in doc.assets:
        if a.asset_kind.value == "data" and (a.sensitivity or "").lower() in {"confidential", "restricted"}:
            return True
    return False


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
            "Mapear pré-condições, vetor de ataque, exploração de vulnerabilidades e impacto de negócio para cenários críticos.",
            StrideCategory.ELEVATION_OF_PRIVILEGE,
            3,
            5,
        ),
        (
            "pasta_vulnerability_exposure",
            "[pasta] Exposição a vulnerabilidades exploráveis",
            "Correlacionar superfície de ataque com componentes críticos e controles ausentes para priorizar mitigação orientada a risco.",
            StrideCategory.TAMPERING,
            3,
            4,
        ),
        (
            "pasta_external_exposure",
            "[pasta] Exposição externa de serviços e interfaces",
            "Superfícies externas (APIs, gateways, edge) ampliam vetores de exploração e devem ser endurecidas com priorização por impacto.",
            StrideCategory.SPOOFING,
            4,
            4,
        ),
        (
            "pasta_critical_integration_path",
            "[pasta] Integrações críticas como caminho de ataque",
            "Integrações com terceiros podem propagar falhas e credenciais comprometidas para ativos centrais.",
            StrideCategory.TAMPERING,
            3,
            5,
        ),
        (
            "pasta_high_value_asset_impact",
            "[pasta] Impacto em ativos de alto valor",
            "Compromisso de ativos de alto valor pode gerar impacto operacional, financeiro e reputacional acima da média.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            5,
        ),
    ]
    _append_heuristics_from_entries(out, existing, entries)

    # Fase 2 pragmática: propaga foco risk-centric para componentes externos/processamento.
    for comp in doc.components:
        text = f"{comp.name} {(comp.technology or '')}".lower()
        if any(x in text for x in ("api", "gateway", "public", "internet", "edge")):
            _append_heuristics_from_entries(
                out,
                existing,
                [
                    (
                        f"pasta_attack_path_{comp.id}",
                        f"[pasta] Caminho plausível de ataque via {comp.name}",
                        "Componente exposto pode ser pivô para movimento lateral e escalada de privilégio.",
                        StrideCategory.ELEVATION_OF_PRIVILEGE,
                        4,
                        4,
                    )
                ],
                target_component_id=comp.id,
            )

    return result.model_copy(update={"heuristic_threats": out})


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(k in text for k in words)


def _recommendation_rules(doc: ThreatModelDocument, text: str):
    return [
        (
            _has_any(
                text,
                (
                    "llm",
                    "rag",
                    "prompt",
                    "embedding",
                    "agent",
                    "agente",
                    "inferência",
                    "inferencia",
                    "treino",
                    "training pipeline",
                    "ai pipeline",
                    "modelo de ia",
                ),
            ),
            ThreatModelMethodology.PLOT4AI,
            "Contexto com IA/LLM/RAG/agentes; PLOT4ai foca riscos de sistemas de IA.",
        ),
        (
            _has_any(
                text,
                (
                    "enterprise",
                    "avançad",
                    "advanced",
                    "attack",
                    "ataque",
                    "vulnerabilidade",
                    "vulnerability",
                    "impacto",
                    "risk-centric",
                    "threat chain",
                    "kill chain",
                ),
            ),
            ThreatModelMethodology.PASTA,
            "Contexto de análise avançada orientada a ataque/vulnerabilidade/risco (PASTA).",
        ),
        (
            _has_any(text, ("lgpd", "gdpr", "privacy", "privacidade", "pii", _PII_LITERAL)),
            ThreatModelMethodology.LINDDUN,
            "Contexto com privacidade/compliance de dados pessoais (LGPD/PII).",
        ),
        (
            doc.model_info.industry_sector in {IndustrySector.FINANCE, IndustrySector.HEALTHCARE}
            or _has_any(
                text,
                ("pagamento", "payment", "saude", "health", "classificação de dados"),
            ),
            ThreatModelMethodology.NIST_DATA_CENTRIC,
            "Setor/contexto orientado a dados críticos (financeiro/saúde/pagamentos).",
        ),
        (
            _has_any(text, ("ativo", "asset", "risco organizacional", "organizacional")),
            ThreatModelMethodology.OCTAVE_ALLEGRO,
            "Foco explícito em ativos e risco organizacional.",
        ),
        (
            _has_any(text, ("workshop", "executivo", "rápido", "iniciante")),
            ThreatModelMethodology.CIA_DIE,
            "Contexto de avaliação rápida/comunicação executiva.",
        ),
        (
            doc.model_info.system_type
            in {
                SystemType.WEB_APPLICATION,
                SystemType.API_BACKEND,
                SystemType.HYBRID,
            }
            or doc.model_info.industry_sector == IndustrySector.CLOUD_NATIVE,
            ThreatModelMethodology.STRIDE,
            "Sistema técnico (web/api/cloud-native) favorece STRIDE como base.",
        ),
    ]


def _append_nist_data_centric_prep_notes(result: AnalysisResult) -> AnalysisResult:
    """
    Preparação para NIST Data-Centric v1:
    - identificação de dados críticos/classificados
    - caminhos sensíveis
    - proteção reforçada por contexto de dado
    """
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code="NIST_DC_PREP_CLASSIFICATION",
            severity="info",
            message="Preparação NIST DC v1: classificar dados críticos por sensibilidade e impacto.",
        ),
        StructuralFinding(
            code="NIST_DC_PREP_DATA_PATHS",
            severity="info",
            message="Preparação NIST DC v1: mapear caminhos de dados sensíveis ponta a ponta.",
        ),
        StructuralFinding(
            code="NIST_DC_PREP_CONTROLS",
            severity="info",
            message="Preparação NIST DC v1: alinhar controles por contexto de dado (repouso/trânsito/uso).",
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_nist_data_centric_native_heuristics(result: AnalysisResult) -> AnalysisResult:
    """
    NIST Data-Centric v1 (incremental sobre saída base):
    - identificar dados classificados/sensíveis
    - detectar caminhos sensíveis
    - priorizar risco por criticidade de dado
    - reforçar controles por estado do dado (trânsito, repouso, uso)
    """
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
        _append_nist_dc_classification_heuristics(out, existing, comp_id)

    for flow_id in sorted(sensitive_flows):
        _append_nist_dc_sensitive_flow_heuristics(out, existing, flow_id)

    for comp_id, items in by_comp.items():
        if comp_id not in sensitive_components:
            continue
        has_datastore_signal = any(
            "datastore" in (h.title.lower() + " " + h.description.lower()) for h in items
        )
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
    sensitive_components: set[str] = set()
    for comp_id, items in by_comp.items():
        if _looks_sensitive_component_heuristics(items):
            sensitive_components.add(comp_id)
    return sensitive_components


def _collect_sensitive_flow_ids(by_flow: dict[str, list[HeuristicThreat]]) -> set[str]:
    sensitive_flows: set[str] = set()
    for flow_id, items in by_flow.items():
        if _looks_sensitive_flow_heuristics(items):
            sensitive_flows.add(flow_id)
    return sensitive_flows


def _looks_sensitive_component_heuristics(items: list[HeuristicThreat]) -> bool:
    text = " ".join((h.title + " " + h.description).lower() for h in items)
    return _has_any(
        text,
        (
            "pii",
            _PII_LITERAL,
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
    return _has_any(
        text,
        ("canal do fluxo", "atravessa fronteira", "confidencialidade", "integridade", "dados sensíveis"),
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


def _append_nist_dc_classification_heuristics(
    out: list[HeuristicThreat], existing: set[str], comp_id: str
) -> None:
    _append_heuristics_from_entries(
        out,
        existing,
        [
            (
                f"nist_dc_classified_data_{comp_id}",
                f"[nist_data_centric] Dados classificados no componente {comp_id}",
                "Componente aparenta tratar dados críticos/classificados; aplicar controles proporcionais ao nível de sensibilidade.",
                StrideCategory.INFORMATION_DISCLOSURE,
                3,
                5,
            ),
        ],
        target_component_id=comp_id,
    )


def _append_nist_dc_sensitive_flow_heuristics(
    out: list[HeuristicThreat], existing: set[str], flow_id: str
) -> None:
    _append_heuristics_from_entries(
        out,
        existing,
        [
            (
                f"nist_dc_sensitive_path_{flow_id}",
                f"[nist_data_centric] Caminho de dados sensíveis em {flow_id}",
                "Fluxo pode carregar dados sensíveis; reforçar proteção ponta a ponta, autenticação forte e rastreabilidade.",
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


def _append_nist_dc_state_heuristics(
    out: list[HeuristicThreat],
    existing: set[str],
    *,
    comp_id: str,
    has_datastore_signal: bool,
    has_process_signal: bool,
) -> None:
    if has_datastore_signal:
        _append_heuristics_from_entries(
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
        _append_heuristics_from_entries(
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


def _append_plot4ai_native_heuristics(
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> AnalysisResult:
    if not _looks_like_ai_context(doc):
        return result

    out = list(result.heuristic_threats)
    existing = {h.id for h in out}

    entries = _plot4ai_base_entries()
    _append_heuristics_from_entries(out, existing, entries)

    ai_signals = _collect_ai_signals(doc)
    if ai_signals["prompting"]:
        _append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_prompt_input_handling",
                    "[plot4ai] Validação insuficiente de prompt/input",
                    "Entrada sem normalização/guardrails pode induzir bypass de políticas e ações inseguras.",
                    StrideCategory.TAMPERING,
                    4,
                    4,
                ),
            ],
        )
    if ai_signals["retrieval"]:
        _append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_retrieval_grounding",
                    "[plot4ai] Grounding fraco em retrieval/RAG",
                    "Recuperação sem filtros por contexto e tenant pode causar data leakage e respostas não confiáveis.",
                    StrideCategory.INFORMATION_DISCLOSURE,
                    4,
                    5,
                ),
            ],
        )
    if ai_signals["agent_actions"]:
        _append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_agent_tool_execution",
                    "[plot4ai] Execução de ferramentas por agente sem isolamento",
                    "Agentes com tool-use sem sandbox podem executar ações destrutivas fora do escopo esperado.",
                    StrideCategory.ELEVATION_OF_PRIVILEGE,
                    4,
                    5,
                ),
            ],
        )
    if ai_signals["governance_pipeline"]:
        _append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_governance_pipeline",
                    "[plot4ai] Falhas de governança em pipeline de modelo",
                    "Ausência de versionamento, aprovação e rastreabilidade no pipeline aumenta risco sistêmico.",
                    StrideCategory.REPUDIATION,
                    3,
                    4,
                ),
            ],
        )

    return result.model_copy(update={"heuristic_threats": out})


def _plot4ai_base_entries() -> list[tuple[str, str, str, StrideCategory, int, int]]:
    return [
        (
            "plot4ai_prompt_injection",
            "[plot4ai] Prompt injection e instruções maliciosas",
            "Entradas maliciosas podem subverter políticas do modelo e causar ações indevidas.",
            StrideCategory.TAMPERING,
            4,
            5,
        ),
        (
            "plot4ai_rag_data_leakage",
            "[plot4ai] Exposição indevida em RAG/embeddings",
            "Contexto recuperado pode vazar dados sensíveis ou quebrar isolamento entre tenants.",
            StrideCategory.INFORMATION_DISCLOSURE,
            3,
            5,
        ),
        (
            "plot4ai_model_abuse",
            "[plot4ai] Abuso de inferência e extração de modelo",
            "Uso abusivo pode exfiltrar comportamento interno, elevar custo e reduzir disponibilidade.",
            StrideCategory.DENIAL_OF_SERVICE,
            3,
            4,
        ),
    ]


def _looks_like_ai_context(doc: ThreatModelDocument) -> bool:
    text = " ".join(
        [
            doc.metadata.title or "",
            doc.metadata.summary or "",
            " ".join(doc.metadata.tags or []),
            (doc.business_context.description if doc.business_context else "") or "",
            (doc.business_context.regulatory_context if doc.business_context else "") or "",
            " ".join(c.name for c in doc.components),
            " ".join((c.technology or "") for c in doc.components),
        ]
    ).lower()
    return any(
        k in text
        for k in (
            "llm",
            "rag",
            "prompt",
            "embedding",
            "model",
            "modelo",
            "agent",
            "agente",
            "inference",
            "inferência",
            "pipeline",
            "fine-tune",
            "fine tune",
        )
    )


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
            message="PASTA fase 2: tratar integrações críticas como caminhos preferenciais de ataque.",
        ),
        StructuralFinding(
            code="PASTA_RISK_IMPACT",
            severity="info",
            message="PASTA fase 2: relacionar cenário de ataque a impacto operacional, financeiro e reputacional.",
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_pasta_insights(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    business_goals = (doc.business_context.business_goals if doc.business_context else [])[:4]
    technical_scope = [c.name for c in doc.components[:5]]
    attack_surface = [f"{f.from_component}->{f.to_component}" for f in doc.data_flows[:5]]
    attacker_goals = [
        "Comprometer integrações externas",
        "Exfiltrar dados sensíveis",
        "Interromper serviço crítico",
    ]
    vulnerabilities = [
        "Exposição externa sem hardening completo",
        "Validação fraca em integrações críticas",
        "Controles insuficientes em ativos de alto valor",
    ]
    impact_summary = [
        "Operacional: indisponibilidade e degradação de serviço",
        "Financeiro: fraude/custos de resposta e recuperação",
        "Reputacional: perda de confiança e impacto regulatório",
    ]
    risk_findings = [
        f"{h.title} (score {h.risk.score})"
        for h in sorted(
            [x for x in result.heuristic_threats if not x.skipped_as_duplicate],
            key=lambda x: x.risk.score or 0.0,
            reverse=True,
        )[:5]
    ]
    blocks = [
        ("business_objectives", "Business objectives", business_goals or ["Objetivos não informados"]),
        ("technical_scope", "Technical scope", technical_scope or ["Escopo técnico mínimo"]),
        ("attack_surface", "Attack surface", attack_surface or ["Sem fluxos relevantes mapeados"]),
        ("likely_attacker_goals", "Likely attacker goals", attacker_goals),
        ("correlated_vulnerabilities", "Correlated vulnerabilities", vulnerabilities),
        ("impact_summary", "Impact summary", impact_summary),
        ("risk_oriented_findings", "Risk-oriented findings", risk_findings or ["Sem achados ativos"]),
    ]
    return _append_methodology_insights(
        result,
        profile="PASTA advanced / risk-centric",
        blocks=blocks,
    )


def _collect_ai_signals(doc: ThreatModelDocument) -> dict[str, bool]:
    text = " ".join(
        [
            doc.metadata.title or "",
            doc.metadata.summary or "",
            " ".join(doc.metadata.tags or []),
            (doc.business_context.description if doc.business_context else "") or "",
            " ".join(c.name for c in doc.components),
            " ".join((c.technology or "") for c in doc.components),
        ]
    ).lower()
    return {
        "prompting": _has_any(text, ("prompt", "instruction", "system prompt", "user input")),
        "retrieval": _has_any(text, ("rag", "retrieval", "embedding", "vector", "grounding")),
        "agent_actions": _has_any(text, ("agent", "tool use", "function call", "orquestração")),
        "governance_pipeline": _has_any(text, ("train", "training", "inference", "pipeline", "model provider")),
    }


def _append_plot4ai_recommendations(result: AnalysisResult) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code="PLOT4AI_REC_PROMPT_RETRIEVAL",
            severity="info",
            message="PLOT4ai fase 2: proteger dados em prompts/retrieval com minimização e filtros contextuais.",
        ),
        StructuralFinding(
            code="PLOT4AI_REC_AGENT_ISOLATION",
            severity="info",
            message="PLOT4ai fase 2: isolar ações de agentes e aplicar políticas estritas de tool execution.",
        ),
        StructuralFinding(
            code="PLOT4AI_REC_IO_VALIDATION",
            severity="info",
            message="PLOT4ai fase 2: validar entradas/saídas e monitorar comportamento anômalo de modelo.",
        ),
        StructuralFinding(
            code="PLOT4AI_REC_GOVERNANCE_OBSERVABILITY",
            severity="info",
            message="PLOT4ai fase 2: reforçar governança, observabilidade e auditoria no pipeline de IA.",
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _append_plot4ai_insights(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    signals = _collect_ai_signals(doc)
    blocks = [
        (
            "model_interaction_risks",
            "Model interaction risks",
            [
                "Abuso de inferência e extração de comportamento",
                "Dependência de provedor externo de modelo",
            ],
        ),
        (
            "prompt_input_handling_risks",
            "Prompt / input handling risks",
            [
                "Prompt injection",
                "Validação insuficiente de entrada",
            ]
            if signals["prompting"]
            else ["Sem sinal forte de prompting avançado"],
        ),
        (
            "retrieval_grounding_risks",
            "Retrieval / grounding risks",
            [
                "Leakage por contexto recuperado",
                "Grounding inconsistente por dados não confiáveis",
            ]
            if signals["retrieval"]
            else ["Sem sinal forte de retrieval/RAG"],
        ),
        (
            "agent_tool_execution_risks",
            "Agent action / tool execution risks",
            [
                "Execução de ferramentas fora de escopo",
                "Escalada de privilégio via orquestração de agentes",
            ]
            if signals["agent_actions"]
            else ["Sem sinal forte de agent tool-use"],
        ),
        (
            "data_leakage_disclosure_ai",
            "Data leakage / disclosure in AI context",
            ["Exposição de dados sensíveis em prompts, contexto ou saída de modelo"],
        ),
        (
            "governance_pipeline_risks",
            "Governance / pipeline risks",
            [
                "Ausência de trilha auditável do pipeline",
                "Governança fraca de versões/prompts/modelos",
            ]
            if signals["governance_pipeline"]
            else ["Sem sinal forte de pipeline de treino/inferência"],
        ),
    ]
    return _append_methodology_insights(
        result,
        profile="PLOT4ai AI / LLM specialized",
        blocks=blocks,
    )

