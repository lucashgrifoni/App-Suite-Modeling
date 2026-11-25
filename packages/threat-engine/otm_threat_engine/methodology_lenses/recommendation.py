from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from otm_core_schema import IndustrySector, SystemType, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.ai_modeling.corpus import build_ai_calibration_corpus
from otm_threat_engine.methodology_lenses.common import has_any, has_any_token, has_safe_ai_marker

_PII_LITERAL = "dados pessoais"
_MODEL_PROVIDER = "model provider"
_DATA_LAKE = "data lake"
_INGESTAO = "ingestão"

_TIE_PRIORITY: dict[ThreatModelMethodology, int] = {
    ThreatModelMethodology.PLOT4AI: 7,
    ThreatModelMethodology.PASTA: 6,
    ThreatModelMethodology.LINDDUN: 5,
    ThreatModelMethodology.NIST_DATA_CENTRIC: 4,
    ThreatModelMethodology.OCTAVE_ALLEGRO: 3,
    ThreatModelMethodology.CIA_DIE: 2,
    ThreatModelMethodology.STRIDE: 1,
}


@dataclass(frozen=True)
class MethodologyRanking:
    """Resultado da competição por pontuação entre metodologias."""

    scores: dict[ThreatModelMethodology, float]
    winner: ThreatModelMethodology
    runner_up: ThreatModelMethodology | None
    score_gap: float
    confidence: Literal["low", "medium", "high"]
    supporting_signals: tuple[str, ...]
    counter_signals: tuple[str, ...]
    reason_summary: str


def build_recommendation_context_text(doc: ThreatModelDocument) -> str:
    """Corpus alinhado com deteção PLOT4ai (inclui componentes, fluxos, fronteiras)."""
    return build_ai_calibration_corpus(doc)


def _plot4ai_text_signals(text: str) -> list[tuple[str, str]]:
    """Sinais textuais concretos de PLOT4ai como pares (bit, evidência), em ordem de prioridade."""
    llm = has_any(text, ("large language", "language model", "chatbot", "copilot")) or has_any_token(text, ("llm",))
    prompt_to_model = has_any(
        text, ("prompt", "orchestrator", "orquestra", "prompt-orchestrator", "normalized_prompt")
    ) and has_any(
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
            _MODEL_PROVIDER,
        ),
    )
    rag = has_any(
        text, ("rag", "retrieval", "vector", "embedding", "knowledge assistant", "vector_database")
    ) or has_any_token(text, ("rag",))
    agent = has_any(
        text,
        ("agent", "tool-use", "tool use", "function calling", "tool-gateway", "ai agent", "tool_gateway"),
    )
    provider = has_any(
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
            _MODEL_PROVIDER,
            "external-model-provider",
            "external model",
        ),
    )
    inference = has_any(text, ("inference", "inferência", "inferencia", "classification pipeline")) and (
        has_any(text, ("embedding", "orchestrator", _MODEL_PROVIDER, "generative"))
        or has_any_token(text, ("llm",))
        or has_safe_ai_marker(text)
    )
    rules: list[tuple[bool, str, str]] = [
        (llm, "LLM, chat ou copiloto descritos", "O título, resumo ou componentes mencionam LLM/chatbot/copilot."),
        (
            prompt_to_model,
            "orquestração de prompts ou entrada normalizada para modelo",
            "Há orquestração de prompts ou cadeia explícita até ao fornecedor de modelo.",
        ),
        (
            rag,
            "RAG, retrieval ou armazenamento vectorial",
            "Retrieval, RAG, vector DB ou embeddings aparecem no modelo.",
        ),
        (
            agent,
            "agente com tool-use ou gateway de ações",
            "Agente, ferramentas, gateway de ações ou function calling estão modelados.",
        ),
        (
            provider,
            "provedor ou endpoint externo de modelo",
            "Integrações nomeiam fornecedor de LLM ou serviço de inferência terceiro.",
        ),
        (
            inference,
            "pipeline de inferência com IA",
            "Pipeline de processamento referencia inferência ligada a componentes de IA.",
        ),
    ]
    return [(bit, evidence) for matched, bit, evidence in rules if matched]


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
    for bit, evidence in _plot4ai_text_signals(text):
        bits.append(bit)
        ev.append(evidence)
    if not bits:
        return None
    reason = "PLOT4ai recomendado por " + ", ".join(bits) + "."
    title_snippet = (doc.metadata.title or "")[:80]
    ev.append(f"Título (amostra): «{title_snippet}».")
    return reason, ev


def _apply_declared_methodology_template_alignment(
    doc: ThreatModelDocument,
    scores: dict[ThreatModelMethodology, float],
    sector: IndustrySector,
    sys_t: SystemType,
    mega: str,
    pos: list[str],
) -> None:
    """
    Ajuste semântico por metodologia **declarada** no OTM (tipicamente herdada do template).

    - Evita que o viés «finanças → NIST» ou «batch_data_pipeline → NIST» sobreponha um
      template que já fixou PASTA ou STRIDE.
    - Documentos com STRIDE por omissão (ex.: testes unitários sem `methodology` no YAML)
      não recebem estes reforços: só PASTA explícito ou STRIDE+NIST em pipelines de dados.
    """
    decl = doc.model_info.methodology
    if decl == ThreatModelMethodology.PASTA:
        scores[ThreatModelMethodology.PASTA] += 44.0
        if sector == IndustrySector.FINANCE:
            scores[ThreatModelMethodology.NIST_DATA_CENTRIC] -= 26.0
            pos.append("template declara PASTA em finanças → atenua viés genérico finance→NIST")
    elif decl == ThreatModelMethodology.STRIDE and sys_t == SystemType.BATCH_DATA_PIPELINE:
        scores[ThreatModelMethodology.STRIDE] += 38.0
        scores[ThreatModelMethodology.NIST_DATA_CENTRIC] -= 28.0
        # Vocabulário ETL/pipeline no texto não deve sobrepor um template que já fixou STRIDE.
        if has_any(
            mega,
            ("etl", "ingest", _INGESTAO, "transform", "warehouse", _DATA_LAKE, "pipeline", "armazém"),
        ):
            scores[ThreatModelMethodology.NIST_DATA_CENTRIC] -= 22.0
            pos.append("STRIDE+batch: atenua bónus semântico ETL/pipeline face ao template")
        pos.append("template declara STRIDE em batch pipeline → equilibra batch→NIST")
    elif decl == ThreatModelMethodology.NIST_DATA_CENTRIC and sys_t == SystemType.BATCH_DATA_PIPELINE:
        scores[ThreatModelMethodology.NIST_DATA_CENTRIC] += 14.0
        pos.append("template declara NIST em pipeline de dados → reforço data-centric")


def _score_stride(sys_t: SystemType, sector: IndustrySector, mega: str) -> tuple[float, list[str]]:
    pos: list[str] = []
    stride = 8.0
    if sys_t in (SystemType.WEB_APPLICATION, SystemType.API_BACKEND, SystemType.HYBRID):
        stride += 22
        pos.append("tipo web/api/híbrido → STRIDE")
    if sys_t == SystemType.MOBILE_APPLICATION:
        stride += 14
    if sector == IndustrySector.SAAS:
        stride += 12
        pos.append("setor SaaS")
    if sector == IndustrySector.CLOUD_NATIVE:
        stride += 10
    if has_any(mega, ("tenant", "multi-tenant", "multitenant", "bff", "waf", "api gateway")):
        stride += 10
    if sys_t == SystemType.BATCH_DATA_PIPELINE:
        stride -= 10
    if has_any(mega, ("etl", "ingest", _INGESTAO, "transform", "data warehouse", _DATA_LAKE, "pipeline")):
        stride -= 14
    return stride, pos


def _score_nist(sys_t: SystemType, sector: IndustrySector, mega: str) -> tuple[float, list[str]]:
    pos: list[str] = []
    nist = 5.0
    if sys_t == SystemType.BATCH_DATA_PIPELINE:
        nist += 38
        pos.append("batch_data_pipeline → NIST data-centric")
    if has_any(mega, ("etl", "ingest", _INGESTAO, "transform", "warehouse", _DATA_LAKE, "pipeline", "armazém")):
        nist += 26
        pos.append("vocabulário ETL/pipeline")
    if sector == IndustrySector.FINANCE:
        nist += 32
        pos.append("setor finanças → NIST data-centric")
    if sector == IndustrySector.HEALTHCARE and has_any(
        mega, ("clinical", "ehr", "phi", "paciente", "clínico", "clinical record")
    ):
        nist += 10
    elif sector == IndustrySector.HEALTHCARE:
        nist += 5
    if has_any(mega, ("pagamento", "payment", "pci")):
        nist += 8
    if sector == IndustrySector.SAAS and sys_t != SystemType.BATCH_DATA_PIPELINE:
        nist -= 16
    if has_any(mega, ("privileg", "admin", "pam", "jump", "consola privilegiada", "administrador")):
        nist -= 8
    return nist, pos


def _score_linddun(
    doc: ThreatModelDocument, sector: IndustrySector, mega: str, tags_l: list[str]
) -> tuple[float, list[str]]:
    pos: list[str] = []
    ld = 3.0
    if sector == IndustrySector.HEALTHCARE:
        ld += 34
        pos.append("setor healthcare → LINDDUN")
    if has_any(mega, ("phi", "clinical", "ehr", "paciente", "dados clínicos", "hipaa", "registo eletrónico")):
        ld += 22
    privacy_kw = ("lgpd", "gdpr", "privacy", "privacidade", "pii", _PII_LITERAL, "consent")
    if has_any(mega, privacy_kw):
        hits = sum(1 for k in privacy_kw if k in mega)
        ld += min(52, 18 + hits * 14)
    if any(t in tags_l for t in ("healthcare", "phi", "clinical")):
        ld += 8
    if doc.model_info.methodology == ThreatModelMethodology.LINDDUN:
        ld += 5
    return ld, pos


def _score_plot4ai(doc: ThreatModelDocument, text: str) -> tuple[float, list[str]]:
    plot = _plot4ai_recommendation_detail(doc, text)
    if plot is None:
        return 0.0, []
    ev_count = max(3, len(plot[1]))
    return 40.0 + min(42.0, 6.0 * float(ev_count)), ["sinais AI/LLM/RAG/PLOT4ai"]


def _score_pasta(mega: str) -> tuple[float, list[str]]:
    pos: list[str] = []
    pasta = 4.0
    if has_any(mega, ("kill chain", "threat chain", "attack chain", "risk-centric", "cadeia de risco")):
        pasta += 34
        pos.append("linguagem de cadeia de risco/ataque (PASTA)")
    if has_any(mega, ("ataque", "attack", "threat actor", "simulation", "simulação")):
        pasta += 14
    if has_any(mega, ("vulnerability", "vulnerabilidade", "exploit")):
        pasta += 12
    if has_any(mega, ("enterprise", "avançad", "advanced")) and pasta > 14:
        pasta += 4
    return pasta, pos


def _score_octave(mega: str) -> tuple[float, list[str]]:
    pos: list[str] = []
    octave = 2.0
    if has_any(
        mega,
        (
            "risco organizacional",
            "organizational risk",
            "inventário de ativos",
            "inventario de ativos",
            "asset inventory",
            "octave",
            "business impact",
        ),
    ) or has_any_token(mega, ("bia",)):
        # `bia` sai da lista de subcadeias e passa a exigir fronteira dos dois lados. É acrónimo de
        # Business Impact Analysis, e mora dentro de **bias** — palavra banal em qualquer modelo de
        # ameaças de IA, que é o vocabulário da própria lente PLOT4ai deste produto. Um resumo com
        # "avaliamos bias do modelo" levava OCTAVE de 2.0 a 32.0 pontos e mudava a metodologia
        # recomendada de STRIDE para OCTAVE Allegro — e a metodologia decide que lente corre.
        #
        # `has_any_token`, e não a regra de radical usada para `admin`/*administrator*: "bias"
        # começa por "bia", por isso a fronteira à esquerda não bastaria.
        # Ver `tests/test_p3_bia_is_an_acronym_not_a_prefix.py`.
        octave += 30
        pos.append("contexto OCTAVE/BIA/inventário explícito")
    if has_any(mega, ("crown jewel", "ativos críticos", "critical asset")):
        octave += 14
    return octave, pos


def _score_cia(mega: str) -> tuple[float, list[str]]:
    cia = 2.0
    if has_any(mega, ("workshop", "executivo", "rápido", "iniciante")):
        cia += 24
    return cia, []


def _ranking_confidence(gap: float, top: float) -> Literal["low", "medium", "high"]:
    if gap >= 12 or top >= 48:
        return "high"
    if gap >= 5 or top >= 28:
        return "medium"
    return "low"


def _counter_signals(
    scores: dict[ThreatModelMethodology, float], winner: ThreatModelMethodology, top: float
) -> list[str]:
    counters: list[str] = []
    for m, v in scores.items():
        if m != winner and top - v <= 8:
            counters.append(f"{m.value} competiu com {v:.1f} pts (Δ {top - v:.1f})")
    return counters


def compute_methodology_ranking(doc: ThreatModelDocument) -> MethodologyRanking:
    """
    Pontua todas as metodologias e escolhe a vencedora por ranking (empates quebrados por `_TIE_PRIORITY`).

    Evita o viés da «primeira regra que casa» que empurrava NIST/PLOT4AI/PASTA de forma desproporcional.
    """
    text = build_recommendation_context_text(doc)
    sector = doc.model_info.industry_sector
    sys_t = doc.model_info.system_type
    tags_l = [t.lower() for t in (doc.metadata.tags or [])]
    comp_blob = " ".join(f"{c.name or ''} {c.id or ''}" for c in doc.components).lower()
    flow_blob = " ".join(f"{f.name or ''} {f.id or ''}" for f in doc.data_flows).lower()
    mega = f"{text} {comp_blob} {flow_blob}"

    scores: dict[ThreatModelMethodology, float] = dict.fromkeys(ThreatModelMethodology, 0.0)
    pos: list[str] = []

    scored: list[tuple[ThreatModelMethodology, tuple[float, list[str]]]] = [
        (ThreatModelMethodology.STRIDE, _score_stride(sys_t, sector, mega)),
        (ThreatModelMethodology.NIST_DATA_CENTRIC, _score_nist(sys_t, sector, mega)),
        (ThreatModelMethodology.LINDDUN, _score_linddun(doc, sector, mega, tags_l)),
        (ThreatModelMethodology.PLOT4AI, _score_plot4ai(doc, text)),
        (ThreatModelMethodology.PASTA, _score_pasta(mega)),
        (ThreatModelMethodology.OCTAVE_ALLEGRO, _score_octave(mega)),
        (ThreatModelMethodology.CIA_DIE, _score_cia(mega)),
    ]
    for methodology, (score, signals) in scored:
        scores[methodology] = score
        pos.extend(signals)

    _apply_declared_methodology_template_alignment(doc, scores, sector, sys_t, mega, pos)

    winner = max(scores, key=lambda m: (scores[m], _TIE_PRIORITY[m]))
    ordered = sorted(scores, key=lambda m: (scores[m], _TIE_PRIORITY[m]), reverse=True)
    second = ordered[1] if len(ordered) > 1 else None
    top = scores[winner]
    second_v = scores[second] if second is not None else 0.0
    gap = top - second_v

    conf = _ranking_confidence(gap, top)
    counters = _counter_signals(scores, winner, top)

    support_unique = list(dict.fromkeys(pos))[:12]
    reason = (
        f"Metodologia `{winner.value}` por ranking ({top:.1f} pts; 2ª `{second.value if second else '—'}` "
        f"com {second_v:.1f}; gap {gap:.1f})."
    )

    return MethodologyRanking(
        scores=scores,
        winner=winner,
        runner_up=second,
        score_gap=round(gap, 2),
        confidence=conf,
        supporting_signals=tuple(support_unique),
        counter_signals=tuple(counters[:10]),
        reason_summary=reason,
    )


def build_recommendation_rules(
    doc: ThreatModelDocument, text: str
) -> list[tuple[bool, ThreatModelMethodology, str, list[str]]]:
    """
    Compatível com testes: uma entrada por valor de `ThreatModelMethodology`, com `predicate` só na vencedora.

    `text` é ignorado porque o ranking recalcula o corpus via `build_recommendation_context_text`.
    """
    _ = text
    ranking = compute_methodology_ranking(doc)
    rows: list[tuple[bool, ThreatModelMethodology, str, list[str]]] = []
    for m in ThreatModelMethodology:
        if m == ranking.winner:
            ev = list(ranking.supporting_signals) or [ranking.reason_summary]
            rows.append((True, m, ranking.reason_summary, ev))
        else:
            rows.append((False, m, "", []))
    return rows
