from __future__ import annotations

from otm_core_schema import IndustrySector, SystemType, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.ai_modeling.corpus import build_ai_calibration_corpus
from otm_threat_engine.methodology_lenses.common import has_any, has_any_token, has_safe_ai_marker

_PII_LITERAL = "dados pessoais"


def build_recommendation_context_text(doc: ThreatModelDocument) -> str:
    """Corpus alinhado com deteção PLOT4ai (inclui componentes, fluxos, fronteiras)."""
    return build_ai_calibration_corpus(doc)


def _plot4ai_recommendation_detail(doc: ThreatModelDocument, text: str) -> tuple[str, list[str]] | None:
    """Razão curta e evidências concretas; retorna None se não houver sinal suficiente de IA."""
    tags_l = [t.lower() for t in (doc.metadata.tags or [])]
    bits: list[str] = []
    ev: list[str] = []
    if any(t in tags_l for t in ("ai", "llm", "rag", "genai", "generative-ai", "machine-learning")):
        bits.append("tags e classificação explícitas de IA")
        ev.append("As tags do documento listam IA, LLM, RAG ou variantes próximas.")
    elif has_safe_ai_marker(text):
        bits.append("sinal técnico de IA no contexto textual")
        ev.append("Token AI aparece com termos técnicos associados (ex.: model/agent/inference).")
    if has_any(
        text,
        ("large language", "language model", "chatbot", "copilot"),
    ):
        bits.append("LLM, chat ou copiloto descritos")
        ev.append("O título, resumo ou componentes mencionam LLM/chatbot/copilot.")
    elif has_any_token(text, ("llm",)):
        bits.append("LLM, chat ou copiloto descritos")
        ev.append("O título, resumo ou componentes mencionam LLM/chatbot/copilot.")
    if has_any(text, ("prompt", "orchestrator", "orquestra", "prompt-orchestrator", "normalized_prompt")):
        if has_any(
            text,
            (
                "llm",
                "rag",
                "agent",
                "embedding",
                "vector",
                "chatbot",
                "copilot",
                "completion",
                "inference",
                "model provider",
            ),
        ):
            bits.append("orquestração de prompts ou entrada normalizada para modelo")
            ev.append("Há orquestração de prompts ou cadeia explícita até ao fornecedor de modelo.")
    if has_any(text, ("rag", "retrieval", "vector", "embedding", "knowledge assistant", "vector_database")):
        bits.append("RAG, retrieval ou armazenamento vectorial")
        ev.append("Retrieval, RAG, vector DB ou embeddings aparecem no modelo.")
    elif has_any_token(text, ("rag",)):
        bits.append("RAG, retrieval ou armazenamento vectorial")
        ev.append("Retrieval, RAG, vector DB ou embeddings aparecem no modelo.")
    if has_any(
        text,
        ("agent", "tool-use", "tool use", "function calling", "tool-gateway", "ai agent", "tool_gateway"),
    ):
        bits.append("agente com tool-use ou gateway de ações")
        ev.append("Agente, ferramentas, gateway de ações ou function calling estão modelados.")
    if has_any(
        text,
        (
            "openai",
            "anthropic",
            "bedrock",
            "vertex ai",
            "vertex generative",
            "external_ai",
            "llm-provider",
            "llm provider",
            "model provider",
            "external-model-provider",
            "external model",
        ),
    ):
        bits.append("provedor ou endpoint externo de modelo")
        ev.append("Integrações nomeiam fornecedor de LLM ou serviço de inferência terceiro.")
    if has_any(text, ("inference", "inferência", "inferencia", "classification pipeline")) and (
        has_any(text, ("embedding", "orchestrator", "model provider", "generative"))
        or has_any_token(text, ("llm",))
        or has_safe_ai_marker(text)
    ):
        bits.append("pipeline de inferência com IA")
        ev.append("Pipeline de processamento referencia inferência ligada a componentes de IA.")
    if not bits:
        return None
    reason = "PLOT4ai recomendado por " + ", ".join(bits) + "."
    title_snippet = (doc.metadata.title or "")[:80]
    ev.append(f"Título (amostra): «{title_snippet}».")
    return reason, ev


def build_recommendation_rules(
    doc: ThreatModelDocument, text: str
) -> list[tuple[bool, ThreatModelMethodology, str, list[str]]]:
    """
    Cada regra: (predicate, methodology, reason, evidence).

    `evidence` são factos observáveis no documento — evita explicações vagas.
    """
    title_snippet = (doc.metadata.title or "")[:80]
    sector = doc.model_info.industry_sector.value
    sys_type = doc.model_info.system_type.value
    plot = _plot4ai_recommendation_detail(doc, text)
    return [
        (
            plot is not None,
            ThreatModelMethodology.PLOT4AI,
            plot[0] if plot else "",
            plot[1] if plot else [],
        ),
        (
            has_any(
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
            "Contexto de análise avançada orientada a ataque, vulnerabilidade ou cadeia de risco (PASTA).",
            [
                "Termos como ataque, vulnerabilidade, kill chain ou risk-centric aparecem no "
                "contexto textual do modelo.",
            ],
        ),
        (
            has_any(text, ("lgpd", "gdpr", "privacy", "privacidade", "pii", _PII_LITERAL)),
            ThreatModelMethodology.LINDDUN,
            "Metodologia LINDDUN recomendada porque o contexto aponta privacidade, PII ou obrigações LGPD/GDPR.",
            [
                "O utilizador descreveu privacidade, dados pessoais, PII ou compliance LGPD/GDPR no documento.",
                f"Setor declarado: {sector}; tipo de sistema: {sys_type}.",
            ],
        ),
        (
            doc.model_info.industry_sector in {IndustrySector.FINANCE, IndustrySector.HEALTHCARE}
            or has_any(
                text,
                ("pagamento", "payment", "saude", "health", "classificação de dados"),
            ),
            ThreatModelMethodology.NIST_DATA_CENTRIC,
            "Setor ou texto focado em dados sensíveis (finanças, saúde, pagamentos) sugere visão "
            "centrada em dados (NIST).",
            [
                f"Setor do modelo: {sector}.",
                "Ou o texto menciona pagamentos, saúde ou classificação de dados.",
            ],
        ),
        (
            has_any(text, ("ativo", "asset", "risco organizacional", "organizacional")),
            ThreatModelMethodology.OCTAVE_ALLEGRO,
            "Foco explícito em ativos ou risco organizacional encaixa em OCTAVE Allegro.",
            [
                "O texto do modelo refere ativos ou risco organizacional de forma explícita.",
            ],
        ),
        (
            has_any(text, ("workshop", "executivo", "rápido", "iniciante")),
            ThreatModelMethodology.CIA_DIE,
            "Pedido de avaliação rápida ou comunicação executiva inclina para CIA / CIA-DIE.",
            [
                "Palavras como workshop, executivo, rápido ou iniciante aparecem no contexto.",
            ],
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
            "Sistema técnico (web/api/híbrido ou cloud-native) favorece STRIDE como base.",
            [
                f"Tipo de sistema: {sys_type}; setor: {sector}.",
                "Regra de fallback do produto quando não há sinal mais forte.",
                f"Título de referência: «{title_snippet}».",
            ],
        ),
    ]
