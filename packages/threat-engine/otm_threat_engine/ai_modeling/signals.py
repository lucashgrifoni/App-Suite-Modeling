"""
Deteção pragmática de sinais AI/LLM a partir do `ThreatModelDocument`.

Usa texto agregado e pistas estruturais (fluxos, tecnologias). Não afirma presença física
de serviços — apenas confiança heurística para o motor PLOT4ai.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from otm_core_schema import ThreatModelDocument

from otm_threat_engine.methodology_lenses.common import has_any


@dataclass
class AiSignalBundle:
    """Sinais por camada de análise AI; `evidence` documenta o porquê (curto)."""

    model_interaction: bool = False
    prompt_input: bool = False
    retrieval_grounding: bool = False
    vector_embedding: bool = False
    agent_tool: bool = False
    provider_inference: bool = False
    ml_pipeline_referenced: bool = False
    explicit_governance_evidence: bool = False
    evidence: dict[str, list[str]] = field(default_factory=dict)

    # Compat entrada antiga plot4ai.py
    @property
    def prompting(self) -> bool:
        return self.prompt_input

    @property
    def retrieval(self) -> bool:
        return self.retrieval_grounding

    @property
    def agent_actions(self) -> bool:
        return self.agent_tool

    @property
    def governance_pipeline(self) -> bool:
        """Activa a heurística legada de governança de pipeline (inferência/treino)."""
        return self.ml_pipeline_referenced


def _add_evidence(bundle: AiSignalBundle, key: str, line: str) -> None:
    bundle.evidence.setdefault(key, []).append(line)


def _flatten_document_corpus(doc: ThreatModelDocument) -> str:
    parts: list[str] = [
        doc.metadata.title or "",
        doc.metadata.summary or "",
        " ".join(doc.metadata.tags or []),
        (doc.business_context.description if doc.business_context else "") or "",
        (doc.business_context.regulatory_context if doc.business_context else "") or "",
    ]
    for c in doc.components:
        parts.append(c.name or "")
        parts.append(c.technology or "")
    for f in doc.data_flows:
        parts.append(f.name or "")
        parts.append(f.protocol or "")
    for a in doc.assets:
        parts.append(a.name or "")
        sens = getattr(a, "sensitivity", None) or ""
        parts.append(str(sens))
    return " ".join(parts).lower()


def collect_ai_signals_from_document(doc: ThreatModelDocument) -> AiSignalBundle:
    """Infere camadas AI prováveis a partir do modelo canónico."""
    text = _flatten_document_corpus(doc)
    b = AiSignalBundle()

    if has_any(
        text,
        (
            "llm",
            "large language",
            "chat completion",
            "completion api",
            "tokenizer",
            "guardrail",
            "model serving",
            "inference server",
        ),
    ):
        b.model_interaction = True
        _add_evidence(b, "model_interaction", "Texto ou tecnologia sugere interação com modelo LLM.")
    if has_any(
        text,
        (
            "prompt",
            "instruction",
            "system prompt",
            "user message",
            "jailbreak",
            "input sanitization",
            "input validation",
        ),
    ):
        b.prompt_input = True
        _add_evidence(b, "prompt_input", "Referências a prompts ou tratamento de entrada.")
    if has_any(
        text,
        (
            "rag",
            "retrieval",
            "grounding",
            "chunk",
            "chunking",
            "knowledge base",
            "document store",
            "citation",
            "attribution",
        ),
    ):
        b.retrieval_grounding = True
        _add_evidence(b, "retrieval_grounding", "Sinais de RAG / retrieval / grounding.")
    if has_any(
        text,
        (
            "embedding",
            "embeddings",
            "vector",
            "vector db",
            "vector store",
            "pinecone",
            "weaviate",
            "chroma",
            "milvus",
            "qdrant",
            "faiss",
            "ann",
            "similarity search",
        ),
    ):
        b.vector_embedding = True
        _add_evidence(b, "vector_embedding", "Referências a embeddings ou armazenamento vectorial.")
    if has_any(
        text,
        (
            "agent",
            "agentic",
            "tool use",
            "tool-use",
            "function call",
            "function calling",
            "mcp",
            "plugin",
            "orchestrat",
            "executor",
        ),
    ):
        b.agent_tool = True
        _add_evidence(b, "agent_tool", "Sinais de agente ou execução de ferramentas.")
    if has_any(
        text,
        (
            "openai",
            "anthropic",
            "azure openai",
            "bedrock",
            "vertex ai",
            "vertex generative",
            "cohere",
            "mistral api",
            "api.openai",
            "third-party model",
            "model provider",
            "hosted model",
        ),
    ):
        b.provider_inference = True
        _add_evidence(b, "provider_inference", "Integração explícita com fornecedor/modelo alojado terceiro.")
    if has_any(
        text,
        (
            "observability",
            "audit trail",
            "audit log",
            "tracing",
            "opentelemetry",
            "langfuse",
            "model card",
            "governance",
            "prompt versioning",
            "eval harness",
            "red team",
        ),
    ):
        b.explicit_governance_evidence = True
        _add_evidence(
            b,
            "governance_observability",
            "Menção a auditoria, observabilidade ou governança de IA.",
        )
    if has_any(
        text,
        (
            "inference",
            "inferência",
            "pipeline",
            "training",
            "train ",
            "fine-tune",
            "finetune",
            "model provider",
        ),
    ):
        b.ml_pipeline_referenced = True
        _add_evidence(
            b,
            "governance_observability",
            "Pipeline ou inferência referidos — validar trilha de auditoria e controlos.",
        )

    return b
