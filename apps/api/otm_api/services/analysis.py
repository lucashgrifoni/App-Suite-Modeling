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
    pack = load_pack(pack_id) if pack_id else None
    return analyze_document(
        doc,
        pack=pack,
        methodology=methodology,
        auto_recommend=auto_recommend_methodology,
    )
