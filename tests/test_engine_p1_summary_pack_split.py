"""O sumário apresenta heurísticas base e ameaças de pack como números disjuntos.

`build_analysis_summary` subtraía as ameaças de pack da contagem base de propósito, e a seguir
`recompute_summary_with_methodology` reescrevia o campo com o total de tudo. O CLI, o Markdown
e a grelha de métricas da UI mostram os dois lado a lado — "Base heuristics: N new" e "pack
threats: M" — para uma análise que contém N ameaças no total. Quem soma os dois obtém um número
que não existe em lado nenhum do JSON.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_industry_packs import list_pack_ids, load_pack
from otm_threat_engine import analyze_document
from otm_threat_engine.engine_support import recompute_summary_with_methodology
from otm_threat_engine.result import AnalysisResult, AnalysisSummary, HeuristicThreat, RiskAssessment

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.mark.parametrize("pack_id", [None, *sorted(list_pack_ids())])
def test_base_and_pack_counts_add_up_to_the_threat_list(pack_id: str | None) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, pack=load_pack(pack_id) if pack_id else None)

    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    skipped = [h for h in result.heuristic_threats if h.skipped_as_duplicate]
    summary = result.summary

    assert summary.heuristic_threats_generated + summary.pack_threats_generated == len(active)
    assert summary.heuristic_threats_skipped_duplicate + summary.pack_threats_skipped_duplicate == len(skipped)
    assert summary.heuristic_threats_generated == sum(1 for h in active if not h.id.startswith("pack_"))


def test_a_pack_actually_contributes_threats_on_this_fixture() -> None:
    """Sem isto o teste acima passaria por vacuidade se o pack deixasse de disparar."""
    doc = load_document_from_yaml_path(_MINIMAL)
    assert analyze_document(doc, pack=load_pack("saas")).summary.pack_threats_generated > 0


def _threat(hid: str, *, skipped: bool) -> HeuristicThreat:
    from otm_core_schema import StrideCategory

    return HeuristicThreat(
        id=hid,
        title=hid,
        description="x",
        stride=StrideCategory.TAMPERING,
        risk=RiskAssessment(likelihood=3, impact=3, score=9.0),
        skipped_as_duplicate=skipped,
    )


def test_recompute_keeps_the_split_including_skipped_duplicates() -> None:
    result = AnalysisResult(
        engine_version="test",
        document_title="t",
        heuristic_threats=[
            _threat("eng_a", skipped=False),
            _threat("eng_b", skipped=False),
            _threat("eng_c", skipped=True),
            _threat("pack_saas_x_api", skipped=False),
            _threat("pack_saas_y_db", skipped=True),
        ],
        summary=AnalysisSummary(),
    )
    summary = recompute_summary_with_methodology(result).summary
    assert summary.heuristic_threats_generated == 2
    assert summary.heuristic_threats_skipped_duplicate == 1
    assert summary.pack_threats_generated == 1
    assert summary.pack_threats_skipped_duplicate == 1
    assert summary.max_risk_score == 9.0
