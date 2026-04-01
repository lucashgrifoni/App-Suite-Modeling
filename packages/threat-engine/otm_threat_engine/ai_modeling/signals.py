"""
Deteção pragmática de sinais AI/LLM a partir do `ThreatModelDocument`.

Usa corpus lexical (metadata, componentes, fluxos, fronteiras) e reforços estruturais
(p. ex. vector DB + retrieval no diagrama). Não afirma presença física de serviços.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from otm_core_schema import ThreatModelDocument
from otm_core_schema.enums import ComponentKind

from otm_threat_engine.ai_modeling.corpus import build_ai_calibration_corpus
from otm_threat_engine.ai_modeling.keyword_signal_apply import apply_keyword_signals
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
    external_model_provider_linked: bool = False
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
    if line not in bundle.evidence.setdefault(key, []):
        bundle.evidence[key].append(line)


def _external_model_blob_match(blob: str) -> bool:
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
            "vertex ai",
            "vertex generative",
            "external model",
            "generative model",
            "ai provider",
            "copilot-api",
            "inference",
        ),
    )


def _apply_structural_enrichment(doc: ThreatModelDocument, b: AiSignalBundle) -> None:
    """Reforça sinais quando o diagrama OTM descreve camadas AI sem o vocabulário genérico 'model'."""
    comp_blob = " ".join(
        f"{c.id} {c.name} {(c.description or '')} {(c.technology or '')}" for c in doc.components
    ).lower()

    if has_any(
        comp_blob,
        (
            "llm",
            "chatbot",
            "copilot",
            "embedding",
            "complet",
            "inference orchestrator",
            "ai orchestrator",
        ),
    ):
        b.model_interaction = True
        _add_evidence(
            b,
            "model_interaction",
            "Componentes nomeados sugerem interação com modelo LLM ou serviço de IA.",
        )
    if has_any(
        comp_blob,
        (
            "prompt",
            "orchestrator",
            "chat api",
            "copilot-api",
            "rag-api",
        ),
    ):
        b.prompt_input = True
        _add_evidence(
            b,
            "prompt_input",
            "Orquestração ou API que monta prompts/contexto para o modelo.",
        )
    if has_any(comp_blob, ("retrieval", "rag", "vector search", "chunk")) and has_any(
        comp_blob,
        (
            "vector",
            "embedding",
            "ann",
            "similarity",
        ),
    ):
        b.retrieval_grounding = True
        b.vector_embedding = True
        _add_evidence(
            b,
            "retrieval_grounding",
            "Padrão RAG estrutural: retrieval associado a vector store/embeddings no diagrama.",
        )
    if has_any(comp_blob, ("vector", "embedding", "pinecone", "weaviate", "chroma", "milvus", "qdrant")):
        b.vector_embedding = True
        _add_evidence(
            b,
            "vector_embedding",
            "Armazenamento vectorial ou serviço de embeddings explícito no diagrama.",
        )
    if has_any(
        comp_blob,
        (
            "agent",
            "tool gateway",
            "tool-gateway",
            "action gateway",
            "ai agent",
        ),
    ):
        b.agent_tool = True
        _add_evidence(
            b,
            "agent_tool",
            "Agente, gateway de ferramentas ou orquestração com tool-use descrita estruturalmente.",
        )

    ext = [c for c in doc.components if c.kind == ComponentKind.EXTERNAL_ENTITY]
    llm_ext_ids = {
        c.id
        for c in ext
        if _external_model_blob_match(
            f"{c.id} {c.name} {(c.description or '')} {(c.technology or '')}".lower()
        )
    }
    if llm_ext_ids:
        b.provider_inference = True
        _add_evidence(
            b,
            "provider_inference",
            "Componente externo (fornecedor de modelo / inferência) declarado no diagrama.",
        )
        for f in doc.data_flows:
            if f.from_component in llm_ext_ids or f.to_component in llm_ext_ids:
                b.external_model_provider_linked = True
                _add_evidence(
                    b,
                    "provider_inference",
                    "Fluxo cruza fronteira até fornecedor externo de modelo — dependência de terceiros relevante.",
                )
                break


def collect_ai_signals_from_document(doc: ThreatModelDocument) -> AiSignalBundle:
    """Infere camadas AI prováveis a partir do modelo canónico."""
    text = build_ai_calibration_corpus(doc)
    b = AiSignalBundle()
    apply_keyword_signals(text, b, _add_evidence)
    _apply_structural_enrichment(doc, b)
    return b
