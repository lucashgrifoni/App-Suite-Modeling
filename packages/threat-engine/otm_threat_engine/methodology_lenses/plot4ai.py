from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.ai_modeling.heuristics import extra_plot4ai_heuristic_entries
from otm_threat_engine.ai_modeling.signals import AiSignalBundle, collect_ai_signals_from_document
from otm_threat_engine.ai_modeling.summary import build_ai_system_context_summary
from otm_threat_engine.methodology_lenses.common import (
    append_engine_lens_note,
    append_heuristics_from_entries,
    append_methodology_insights,
    boost_impact,
    has_any,
    looks_like_ai_context,
)
from otm_threat_engine.result import AnalysisResult, StructuralFinding


def apply_plot4ai_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    bundle = collect_ai_signals_from_document(doc)
    out = boost_impact(
        result,
        lambda h: (
            h.stride
            in {
                StrideCategory.INFORMATION_DISCLOSURE,
                StrideCategory.TAMPERING,
                StrideCategory.ELEVATION_OF_PRIVILEGE,
            }
        ),
    )
    out = _append_plot4ai_native_heuristics(doc, out, bundle)
    out = _append_plot4ai_recommendations(out)
    out = _append_plot4ai_insights(doc, out, bundle)
    out = out.model_copy(
        update={"ai_system_context": build_ai_system_context_summary(doc, out, bundle)},
    )
    return append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.PLOT4AI,
        note=(
            "Lente PLOT4ai aplicada: threat modeling incremental para LLM, RAG, agentes, vector DB e integrações."
        ),
    )


def _append_plot4ai_native_heuristics(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    ai_signals: AiSignalBundle,
) -> AnalysisResult:
    if not looks_like_ai_context(doc):
        return result
    out = list(result.heuristic_threats)
    existing = {h.id for h in out}
    append_heuristics_from_entries(out, existing, _plot4ai_base_entries())
    if ai_signals.prompt_input:
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_prompt_input_handling",
                    "[plot4ai] Validação insuficiente de prompt/input",
                    "Entrada sem normalização/guardrails pode induzir bypass de políticas "
                    "e ações inseguras.",
                    StrideCategory.TAMPERING,
                    4,
                    4,
                ),
            ],
        )
    if ai_signals.retrieval_grounding:
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_retrieval_grounding",
                    "[plot4ai] Grounding fraco em retrieval/RAG",
                    "Recuperação sem filtros por contexto e tenant pode causar data leakage "
                    "e respostas não confiáveis.",
                    StrideCategory.INFORMATION_DISCLOSURE,
                    4,
                    5,
                ),
            ],
        )
    if ai_signals.agent_tool:
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_agent_tool_execution",
                    "[plot4ai] Execução de ferramentas por agente sem isolamento",
                    "Agentes com tool-use sem sandbox podem executar ações destrutivas "
                    "fora do escopo esperado.",
                    StrideCategory.ELEVATION_OF_PRIVILEGE,
                    4,
                    5,
                ),
            ],
        )
    if ai_signals.governance_pipeline:
        append_heuristics_from_entries(
            out,
            existing,
            [
                (
                    "plot4ai_governance_pipeline",
                    "[plot4ai] Falhas de governança em pipeline de modelo",
                    "Ausência de versionamento, aprovação e rastreabilidade no pipeline "
                    "aumenta risco sistémico.",
                    StrideCategory.REPUDIATION,
                    3,
                    4,
                ),
            ],
        )
    append_heuristics_from_entries(out, existing, extra_plot4ai_heuristic_entries(doc, ai_signals))
    return result.model_copy(update={"heuristic_threats": out})


def _plot4ai_base_entries() -> list[tuple[str, str, str, object, int, int]]:
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
            "Uso abusivo pode exfiltrar comportamento interno, elevar custo e reduzir "
            "disponibilidade.",
            StrideCategory.DENIAL_OF_SERVICE,
            3,
            4,
        ),
    ]


def _append_plot4ai_recommendations(result: AnalysisResult) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code="PLOT4AI_REC_PROMPT_RETRIEVAL",
            severity="info",
            message=(
                "PLOT4ai: proteger dados em prompts/retrieval com minimização e filtros contextuais."
            ),
        ),
        StructuralFinding(
            code="PLOT4AI_REC_AGENT_ISOLATION",
            severity="info",
            message=("PLOT4ai: isolar acções de agentes e políticas estritas de tool execution."),
        ),
        StructuralFinding(
            code="PLOT4AI_REC_IO_VALIDATION",
            severity="info",
            message=("PLOT4ai: validar entradas/saídas e monitorar comportamento anómalo do modelo."),
        ),
        StructuralFinding(
            code="PLOT4AI_REC_VECTOR_GOVERNANCE",
            severity="info",
            message=(
                "PLOT4ai: governança de índices/embeddings — ingestão, segregação e ciclo de vida dos vectores."
            ),
        ),
        StructuralFinding(
            code="PLOT4AI_REC_GOVERNANCE_OBSERVABILITY",
            severity="info",
            message=("PLOT4ai: trilhos de auditoria e observabilidade mínimos no pipeline de IA."),
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def _insight_items_yes_no(active: bool, yes_bullets: list[str], no_bullet: str) -> list[str]:
    return yes_bullets if active else [no_bullet]


def _append_plot4ai_insights(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    signals: AiSignalBundle,
) -> AnalysisResult:
    text_l = " ".join(
        [
            doc.metadata.title or "",
            doc.metadata.summary or "",
            " ".join(c.name for c in doc.components),
        ]
    ).lower()
    pii_hint = has_any(text_l, ("pii", "lgpd", "gdpr", "dados pessoais", "sensitive"))

    blocks: list[tuple[str, str, list[str]]] = [
        (
            "model_interaction_layer",
            "Camada: interação com o modelo",
            _insight_items_yes_no(
                signals.model_interaction,
                [
                    "Superfície de inferência LLM e políticas de abuso/custo",
                    "Exposição a extração de comportamento ou jailbreak transversal",
                ],
                "Sem sinal textual forte nesta camada — confirmar com desenho real.",
            ),
        ),
        (
            "prompt_input_layer",
            "Camada: prompt e tratamento de entrada",
            _insight_items_yes_no(
                signals.prompt_input,
                ["Prompt injection e validação de instruções do utilizador", "Gestão de tamanho e sensibilidade do contexto"],
                "Sem sinal explícito de camada de prompt — rever se input passa pelo modelo.",
            ),
        ),
        (
            "retrieval_grounding_layer",
            "Camada: retrieval e grounding",
            _insight_items_yes_no(
                signals.retrieval_grounding,
                [
                    "Qualidade e confiança do contexto recuperado (RAG)",
                    "Risco de misturar fontes ou violar isolamento entre inquilinos",
                ],
                "Sem sinal forte de RAG — se existir, documentar no modelo.",
            ),
        ),
        (
            "vector_embedding_layer",
            "Camada: vectores e embeddings",
            _insight_items_yes_no(
                signals.vector_embedding,
                [
                    "Segregação de índices/coleções e política de ingestão",
                    "Exposição de metadados sensíveis em vectores",
                ],
                "Sem menção explícita a vector store — validar se embeddings existem fora do diagrama.",
            ),
        ),
        (
            "agent_tool_layer",
            "Camada: agente e execução de ferramentas",
            _insight_items_yes_no(
                signals.agent_tool,
                [
                    "Tool-use com credenciais ou efeitos destrutivos",
                    "Orquestração com dependências externas não confiáveis",
                ],
                "Sem sinal de agentes/tools — se usar, acrescentar componentes e fluxos.",
            ),
        ),
        (
            "provider_integration_layer",
            "Camada: integração com fornecedor / inferência",
            _insight_items_yes_no(
                signals.provider_inference,
                [
                    "Termos de tratamento de dados com terceiros e residência",
                    "Continuidade e limites de SLA do endpoint de modelo",
                ],
                "Sem referência explícita a API de modelo terceira — pode ser interno.",
            ),
        ),
        (
            "governance_observability_layer",
            "Camada: governação, auditoria e observabilidade",
            (
                [
                    "Trilha auditável de prompts, respostas resumidas e chamadas a ferramentas",
                    "Versionamento de prompts/modelos e avaliações periódicas",
                ]
                if signals.explicit_governance_evidence
                else (
                    [
                        "Pipeline ou inferência referidos — reforçar observabilidade e deriva",
                        "Sem evidência textual de controlos formais (possível gap operacional)",
                    ]
                    if signals.ml_pipeline_referenced or signals.model_interaction
                    else [
                        "Sem sinal de pipeline de IA no texto — planear mínimo de logging seguro para evolução."
                    ]
                )
            ),
        ),
    ]

    if pii_hint and (signals.prompt_input or signals.model_interaction):
        extra = list(blocks[-1][2])
        extra.append("Dados pessoais/sensíveis mencionados: rever minimização no contexto LLM.")
        blocks = list(blocks[:-1]) + [(blocks[-1][0], blocks[-1][1], extra)]

    return append_methodology_insights(
        result,
        profile="PLOT4ai — sistemas com IA (heurístico, incremental)",
        blocks=blocks,
    )
