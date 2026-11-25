"""Motor de análise — delegado a `otm_threat_engine`."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_industry_packs.loader import load_pack
from otm_threat_engine import AnalysisResult, analyze_document


def run_analysis(
    doc: ThreatModelDocument,
    *,
    pack_id: str | None = None,
    methodology: ThreatModelMethodology | None = None,
    auto_recommend_methodology: bool = False,
) -> AnalysisResult:
    # `is not None` e não um teste de verdade: com `if pack_id`, um `pack_id: ""`
    # (típico de `form.pack ?? ""` ou de uma variável de shell por definir) era
    # descartado em silêncio e a análise corria sem pack, devolvendo 200 como se
    # nada faltasse. Qualquer outro valor inválido — incluindo `" "` — dá 404
    # PACK_NOT_FOUND; a string vazia tem de falhar da mesma forma, alto e bom som.
    # Ausência de pack continua a exprimir-se por omissão do campo ou `null`.
    pack = load_pack(pack_id) if pack_id is not None else None
    return analyze_document(
        doc,
        pack=pack,
        methodology=methodology,
        auto_recommend=auto_recommend_methodology,
    )
