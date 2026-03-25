from __future__ import annotations

from otm_core_schema import IndustrySector, SystemType, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.common import has_any

_PII_LITERAL = "dados pessoais"


def build_recommendation_context_text(doc: ThreatModelDocument) -> str:
    return " ".join(
        [
            doc.metadata.title or "",
            doc.metadata.summary or "",
            " ".join(doc.metadata.tags or []),
            (doc.business_context.description if doc.business_context else "") or "",
            (doc.business_context.regulatory_context if doc.business_context else "") or "",
        ]
    ).lower()


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
    return [
        (
            has_any(
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
            "Contexto com IA/LLM/RAG/agentes; PLOT4ai foca riscos específicos de sistemas de IA.",
            [
                f"No modelo «{title_snippet}» o texto agregado (título, resumo, tags, contexto) "
                "menciona IA, agentes, RAG, prompts ou pipeline de ML.",
            ],
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
                "Termos como ataque, vulnerabilidade, kill chain ou risk-centric aparecem no contexto textual do modelo.",
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
            "Setor ou texto focado em dados sensíveis (finanças, saúde, pagamentos) sugere visão centrada em dados (NIST).",
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
            ],
        ),
    ]
