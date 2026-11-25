"""O estado geral da capa não pode ignorar as ameaças que o documento declara.

`_overall_status` recebia `result.summary.max_risk_score`, que `build_analysis_summary` calcula
**só** a partir das heurísticas. As ameaças declaradas em `doc.threats` nunca lá chegam — apesar
de o mesmo relatório as contar no total, que a sua própria frase descreve como *"ameaças
(canónicas + heurísticas activas)"*, e de as somar ao quadro de severidade.

Medido num documento cuja única ameaça crítica é declarada pelo modelador (L5×I5 = 25) sobre um
componente cujas heurísticas não passam de 9.0:

    com a ameaça declarada    estado: Aceitável com acompanhamento
    sem a ameaça declarada    estado: Aceitável com acompanhamento

Idênticos. Declarar uma ameaça crítica não move o veredito que um decisor lê na capa.

A correcção é cirúrgica de propósito. O rótulo de risco está rotulado `Risk (heuristic)` no HTML e
continua a significar isso — não é ele que está errado. O que estava errado era o **estado geral**,
que não traz qualificação nenhuma e é a linha pela qual alguém decide se age.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _cover(*, declared: bool, likelihood: int = 5, impact: int = 5) -> Any:
    from otm_core_schema import ThreatModelDocument
    from otm_report_premium import ReportLevel, build_premium_report_payload
    from otm_threat_engine import analyze_document

    threats = (
        [
            {
                "id": "t_crit",
                "title": "Perda total da fila",
                "stride": "denial_of_service",
                "target_component_id": "q1",
                "risk": {"likelihood": likelihood, "impact": impact},
            }
        ]
        if declared
        else []
    )
    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "system_type": "web_application", "industry_sector": "saas"},
            "metadata": {"title": "Fila"},
            "components": [{"id": "q1", "name": "Fila de eventos", "kind": "queue"}],
            "threats": threats,
        }
    )
    payload = build_premium_report_payload(document, analyze_document(document), level=ReportLevel.DEEP)
    return payload.cover


def test_a_heuristica_sozinha_fica_abaixo_do_limiar() -> None:
    """Premissa: sem a ameaça declarada, o modelo é mesmo de risco médio."""
    assert _cover(declared=False).overall_status == "acceptable_with_follow_up"


def test_uma_ameaca_critica_declarada_muda_o_estado_geral() -> None:
    cover = _cover(declared=True)

    assert cover.overall_status == "requires_immediate_attention", (
        f"estado `{cover.overall_status}` para um documento que declara uma ameaça de score 25"
    )


def test_uma_ameaca_declarada_media_nao_dispara_o_estado_maximo() -> None:
    """A correcção não podia ser tratar qualquer ameaça declarada como crítica."""
    cover = _cover(declared=True, likelihood=2, impact=2)

    assert cover.overall_status == "acceptable_with_follow_up", cover.overall_status


def test_o_rotulo_de_risco_continua_a_ser_o_heuristico() -> None:
    """`Risk (heuristic)` diz o que mede; mexer nele seria tornar o rótulo falso."""
    assert _cover(declared=True).overall_risk_label == _cover(declared=False).overall_risk_label
