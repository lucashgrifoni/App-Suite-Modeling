"""
Heurísticas PLOT4ai adicionais (incrementais). Mantêm prefixo estável `plot4ai_`.
"""

from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelDocument
from otm_core_schema.enums import ComponentKind

from otm_threat_engine.ai_modeling.corpus import build_ai_calibration_corpus
from otm_threat_engine.ai_modeling.signals import AiSignalBundle, collect_ai_signals_from_document
from otm_threat_engine.methodology_lenses.common import has_any


def _llm_provider_component(c) -> bool:
    blob = f"{c.id} {c.name} {(c.description or '')} {(c.technology or '')}".lower()
    return has_any(
        blob,
        (
            "llm",
            "large language",
            "model provider",
            "hosted model",
            "openai",
            "anthropic",
            "bedrock",
            "vertex",
            "external model",
            "ai provider",
            "generative",
            "inference provider",
        ),
    )


def _agent_related_component(c) -> bool:
    blob = f"{c.id} {c.name} {(c.description or '')}".lower()
    return has_any(
        blob,
        (
            "agent",
            "orchestrator",
            "tool-gateway",
            "tool gateway",
            "action gateway",
        ),
    )


def _agent_tooling_reaches_non_llm_external(doc: ThreatModelDocument) -> bool:
    """
    Integração externa *além* do fornecedor de modelo — evita disparar com apenas LLM SaaS.
    """
    ext = [c for c in doc.components if c.kind == ComponentKind.EXTERNAL_ENTITY]
    if not ext:
        return False
    llm_ids = {c.id for c in ext if _llm_provider_component(c)}
    agent_ids = {c.id for c in doc.components if _agent_related_component(c)}
    if not agent_ids:
        return False
    for f in doc.data_flows:
        pair = {f.from_component, f.to_component}
        if not pair & agent_ids:
            continue
        other = f.to_component if f.from_component in agent_ids else f.from_component
        if other in llm_ids:
            continue
        dest = next((c for c in ext if c.id == other), None)
        if dest is not None and not _llm_provider_component(dest):
            return True
    return False


def _corpus_lower(doc: ThreatModelDocument) -> str:
    return build_ai_calibration_corpus(doc)


def _sensitive_data_mentioned(text: str) -> bool:
    return has_any(
        text,
        (
            "pii",
            "lgpd",
            "gdpr",
            "phi",
            "credential",
            "secret",
            "confidencial",
            "dados pessoais",
            "personal data",
            "payment card",
            "pan ",
            "payroll",
            "finance-system",
            "hr-system",
            "employee-records",
            "sensitive context",
        ),
    )


def _sensitive_controls_mentioned(text: str) -> bool:
    return has_any(
        text,
        (
            "redaction",
            "masking",
            "mascar",
            "tokenization",
            "pseudonym",
            "anonimiz",
            "dlp",
            "retention policy",
            "data minimization",
            "human approval",
            "approval-service",
        ),
    )


def _plot4ai_entry_flags(
    doc: ThreatModelDocument, bundle: AiSignalBundle, text: str
) -> tuple[bool, bool, bool, bool, bool, bool]:
    """Condições (em ordem) para as entradas PLOT4ai extra — isola a lógica booleana."""
    rag_vector = bundle.vector_embedding and bundle.retrieval_grounding
    third_party = bundle.provider_inference and (
        bundle.model_interaction or has_any(text, ("completion", "chat", "inference endpoint", "api.openai", "llm"))
    )
    agent_external = bundle.agent_tool and (
        has_any(
            text,
            (
                "webhook",
                "third-party tool",
                "third party tool",
                "external tool",
                "external saas",
                "public api",
                "api pública",
                "outbound integration",
                "ferramenta externa",
            ),
        )
        or _agent_tooling_reaches_non_llm_external(doc)
    )
    observability_gap = not bundle.explicit_governance_evidence and (
        (bundle.agent_tool and bundle.provider_inference) or (bundle.prompt_input and _sensitive_data_mentioned(text))
    )
    sensitive_prompt = (
        _sensitive_data_mentioned(text) and bundle.prompt_input and not _sensitive_controls_mentioned(text)
    )
    grounding_weak = (
        bundle.retrieval_grounding
        and has_any(text, ("rag", "retrieval", "grounding"))
        and not has_any(text, ("citation", "attribution", "provenance", "fonte"))
    )
    return rag_vector, third_party, agent_external, observability_gap, sensitive_prompt, grounding_weak


def extra_plot4ai_heuristic_entries(
    doc: ThreatModelDocument, bundle: AiSignalBundle
) -> list[tuple[str, str, str, StrideCategory, int, int]]:
    """Entradas condicionais; não duplicam `plot4ai.py` base mas reforçam cenários modernos."""
    text = _corpus_lower(doc)
    rag_vector, third_party, agent_external, observability_gap, sensitive_prompt, grounding_weak = _plot4ai_entry_flags(
        doc, bundle, text
    )
    candidates: list[tuple[bool, tuple[str, str, str, StrideCategory, int, int]]] = [
        (
            rag_vector,
            (
                "plot4ai_rag_vector_composition",
                "[plot4ai] RAG com vector store — superfície composta",
                "RAG inferido por sinais de retrieval e embeddings/vector store no modelo: "
                "rever isolamento de índices, filtros tenant-aware e políticas de ingestão.",
                StrideCategory.INFORMATION_DISCLOSURE,
                4,
                5,
            ),
        ),
        (
            third_party,
            (
                "plot4ai_third_party_model_dependency",
                "[plot4ai] Dependência de inferência em fornecedor terceiro",
                "Provedor ou endpoint externo referido com interação LLM — rever continuidade, "
                "termos de dados, classificação de prompts/respostas e plano de contingência.",
                StrideCategory.TAMPERING,
                3,
                4,
            ),
        ),
        (
            agent_external,
            (
                "plot4ai_agent_external_toolchain",
                "[plot4ai] Agent execution risk com dependências externas",
                "Agente com ferramentas e integrações externas — reduzir blast radius, allow-lists "
                "e confirmação humana para acções destrutivas.",
                StrideCategory.ELEVATION_OF_PRIVILEGE,
                4,
                5,
            ),
        ),
        (
            observability_gap,
            (
                "plot4ai_observability_gap",
                "[plot4ai] Lacuna de observabilidade/auditoria no fluxo de IA",
                "Governance gap detectado por ausência de sinais explícitos de observabilidade ou auditoria "
                "apesar de pipeline ou interação LLM — introduzir trilhos de decisão registáveis.",
                StrideCategory.REPUDIATION,
                3,
                4,
            ),
        ),
        (
            sensitive_prompt,
            (
                "plot4ai_sensitive_prompt_surface",
                "[plot4ai] Dados sensíveis em contexto de prompt",
                "Modelo ou texto referem dados sensíveis e camada de prompt — aplicar minimização, "
                "mascaramento e políticas de retenção do contexto.",
                StrideCategory.INFORMATION_DISCLOSURE,
                4,
                5,
            ),
        ),
        (
            grounding_weak,
            (
                "plot4ai_grounding_attribution_weak",
                "[plot4ai] Grounding com atribuição pouco explícita",
                "Retrieval sem menção clara a atribuição/citação aumenta risco de respostas difíceis "
                "de auditar ou de confiança fraca perante utilizador final.",
                StrideCategory.TAMPERING,
                3,
                4,
            ),
        ),
    ]
    return [entry for flag, entry in candidates if flag]


def extra_entries_from_document(doc: ThreatModelDocument) -> list[tuple[str, str, str, StrideCategory, int, int]]:
    """Atalho: recalcula sinais e devolve heurísticas extra."""
    return extra_plot4ai_heuristic_entries(doc, collect_ai_signals_from_document(doc))
