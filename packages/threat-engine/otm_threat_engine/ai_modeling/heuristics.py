"""
Heurísticas PLOT4ai adicionais (incrementais). Mantêm prefixo estável `plot4ai_`.
"""

from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelDocument

from otm_threat_engine.ai_modeling.signals import AiSignalBundle, collect_ai_signals_from_document
from otm_threat_engine.methodology_lenses.common import has_any


def _corpus_lower(doc: ThreatModelDocument) -> str:
    parts = [
        doc.metadata.title or "",
        doc.metadata.summary or "",
        " ".join(doc.metadata.tags or []),
        (doc.business_context.description if doc.business_context else "") or "",
        " ".join(c.name for c in doc.components),
        " ".join((c.technology or "") for c in doc.components),
    ]
    return " ".join(parts).lower()


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
        ),
    )


def extra_plot4ai_heuristic_entries(doc: ThreatModelDocument, bundle: AiSignalBundle) -> list[tuple[str, str, str, object, int, int]]:
    """Entradas condicionais; não duplicam `plot4ai.py` base mas reforçam cenários modernos."""
    text = _corpus_lower(doc)
    out: list[tuple[str, str, str, object, int, int]] = []

    if bundle.vector_embedding and bundle.retrieval_grounding:
        out.append(
            (
                "plot4ai_rag_vector_composition",
                "[plot4ai] RAG com vector store — superfície composta",
                "RAG inferido por sinais de retrieval e embeddings/vector store no modelo: "
                "rever isolamento de índices, filtros tenant-aware e políticas de ingestão.",
                StrideCategory.INFORMATION_DISCLOSURE,
                4,
                5,
            )
        )
    if bundle.provider_inference and (
        bundle.model_interaction or has_any(text, ("completion", "chat", "inference endpoint", "api.openai"))
    ):
        out.append(
            (
                "plot4ai_third_party_model_dependency",
                "[plot4ai] Dependência de inferência em fornecedor terceiro",
                "Provedor ou endpoint externo referido com interação LLM — rever continuidade, "
                "termos de dados, classificação de prompts/respostas e plano de contingência.",
                StrideCategory.TAMPERING,
                3,
                4,
            )
        )
    if bundle.agent_tool and has_any(text, ("http", "external", "webhook", "api pública", "third-party")):
        out.append(
            (
                "plot4ai_agent_external_toolchain",
                "[plot4ai] Agent execution risk com dependências externas",
                "Agente com ferramentas e integrações externas — reduzir blast radius, allow-lists "
                "e confirmação humana para acções destrutivas.",
                StrideCategory.ELEVATION_OF_PRIVILEGE,
                4,
                5,
            )
        )
    if (
        not bundle.explicit_governance_evidence
        and (
            (bundle.agent_tool and bundle.provider_inference)
            or (bundle.prompt_input and _sensitive_data_mentioned(text))
        )
    ):
        out.append(
            (
                "plot4ai_observability_gap",
                "[plot4ai] Lacuna de observabilidade/auditoria no fluxo de IA",
                "Governance gap detectado por ausência de sinais explícitos de observabilidade ou auditoria "
                "apesar de pipeline ou interação LLM — introduzir trilhos de decisão registáveis.",
                StrideCategory.REPUDIATION,
                3,
                4,
            )
        )
    if _sensitive_data_mentioned(text) and bundle.prompt_input and not _sensitive_controls_mentioned(text):
        out.append(
            (
                "plot4ai_sensitive_prompt_surface",
                "[plot4ai] Dados sensíveis em contexto de prompt",
                "Modelo ou texto referem dados sensíveis e camada de prompt — aplicar minimização, "
                "mascaramento e políticas de retenção do contexto.",
                StrideCategory.INFORMATION_DISCLOSURE,
                4,
                5,
            )
        )
    if bundle.retrieval_grounding and has_any(text, ("rag", "retrieval", "grounding")) and not has_any(
        text,
        ("citation", "attribution", "provenance", "fonte"),
    ):
        out.append(
            (
                "plot4ai_grounding_attribution_weak",
                "[plot4ai] Grounding com atribuição pouco explícita",
                "Retrieval sem menção clara a atribuição/citação aumenta risco de respostas difíceis "
                "de auditar ou de confiança fraca perante utilizador final.",
                StrideCategory.TAMPERING,
                3,
                4,
            )
        )

    return out


def extra_entries_from_document(doc: ThreatModelDocument) -> list[tuple[str, str, str, object, int, int]]:
    """Atalho: recalcula sinais e devolve heurísticas extra."""
    return extra_plot4ai_heuristic_entries(doc, collect_ai_signals_from_document(doc))
