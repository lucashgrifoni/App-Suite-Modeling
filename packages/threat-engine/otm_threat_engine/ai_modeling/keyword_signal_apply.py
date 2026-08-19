"""
Aplicação de regras lexicais a `AiSignalBundle` — extraído para baixar complexidade cognitiva.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from otm_threat_engine.methodology_lenses.common import has_any, has_any_token, has_safe_ai_marker

if TYPE_CHECKING:
    from otm_threat_engine.ai_modeling.signals import AiSignalBundle

AddEvidence = Callable[["AiSignalBundle", str, str], None]

_KW_MODEL = (
    "large language",
    "chat completion",
    "completion api",
    "tokenizer",
    "guardrail",
    "model serving",
    "inference server",
    "chatbot",
    "copilot",
)
_KW_PROMPT = (
    "prompt",
    "instruction",
    "system prompt",
    "user message",
    "jailbreak",
    "input sanitization",
    "input validation",
    "normalized_prompt",
    "grounded_prompt",
)
_KW_RETRIEVAL = (
    "retrieval",
    "grounding",
    "chunk",
    "chunking",
    "knowledge base",
    "document store",
    "citation",
    "attribution",
    "vector search",
    "retrieved_chunks",
)
_KW_VECTOR = (
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
    "similarity search",
    "embeddings-index",
)
_KW_AGENT = (
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
    "tool_gateway",
    "tool gateway",
)
_KW_PROVIDER = (
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
    "external_ai",
    "external model",
    "llm provider",
    "llm-provider",
)
_KW_GOV = (
    "observability",
    "audit trail",
    "audit log",
    "audit-log",
    "tracing",
    "opentelemetry",
    "langfuse",
    "model card",
    "governance",
    "prompt versioning",
    "eval harness",
    "red team",
    "secure log",
    "secure-log",
    "access log",
    "decision log",
    "approval-service",
    "human approval",
)
_KW_ML_PIPELINE = (
    "inference",
    "inferência",
    "pipeline",
    "training",
    "train ",
    "fine-tune",
    "finetune",
)


def apply_keyword_signals(text: str, b: AiSignalBundle, add_evidence: AddEvidence) -> None:
    """Preenche flags do bundle a partir do corpus lexical unificado (OTM + import)."""
    # tokens curtos: matching por token para reduzir colaterais
    if has_any_token(text, ("llm",)) or has_any(text, _KW_MODEL) or has_safe_ai_marker(text):
        b.model_interaction = True
        add_evidence(b, "model_interaction", "Texto ou tecnologia sugere interação com modelo LLM.")
    if has_any(text, _KW_PROMPT):
        b.prompt_input = True
        add_evidence(b, "prompt_input", "Referências a prompts ou tratamento de entrada.")
    if has_any_token(text, ("rag",)) or has_any(text, _KW_RETRIEVAL):
        b.retrieval_grounding = True
        add_evidence(b, "retrieval_grounding", "Sinais de RAG / retrieval / grounding.")
    # `ann` (approximate nearest neighbour) sai de `_KW_VECTOR` e passa a comparar-se por token:
    # em subcadeia acendia com `scanner`, `planner`, `banner`, `channel`, `annual`, `manner` e
    # `canning` — nomes banais de componentes — e o PLOT4ai emitia ameaças de RAG e de
    # armazenamento vectorial para sistemas que não têm nenhum dos dois. `has_any_token` já existe
    # neste ficheiro e já é usado para os outros dois termos curtos com o mesmo problema, `llm` e
    # `rag`. Ver `tests/test_p3_plot4ai_ann_is_a_word_not_a_substring.py`.
    if has_any(text, _KW_VECTOR) or has_any_token(text, ("ann",)):
        b.vector_embedding = True
        add_evidence(b, "vector_embedding", "Referências a embeddings ou armazenamento vectorial.")
    if has_any(text, _KW_AGENT):
        b.agent_tool = True
        add_evidence(b, "agent_tool", "Sinais de agente ou execução de ferramentas.")
    if has_any(text, _KW_PROVIDER):
        b.provider_inference = True
        add_evidence(
            b,
            "provider_inference",
            "Integração explícita com fornecedor/modelo alojado terceiro.",
        )
    if has_any(text, _KW_GOV):
        b.explicit_governance_evidence = True
        add_evidence(
            b,
            "governance_observability",
            "Menção a auditoria, observabilidade ou governança de IA.",
        )
    if has_any(text, _KW_ML_PIPELINE):
        b.ml_pipeline_referenced = True
        add_evidence(
            b,
            "governance_observability",
            "Pipeline ou inferência referidos — validar trilha de auditoria e controlos.",
        )
