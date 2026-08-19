"""A urgência e a prontidão não podem discordar do estado que a capa publica.

Uma correcção anterior deste ramo pôs `_overall_status` a olhar para as ameaças declaradas, além
das heurísticas. `urgency` e `readiness`, dez linhas abaixo, continuaram na pontuação só-heurística.
Resultado, no mesmo bloco do relatório executivo:

    - **Estado geral:** Requer atenção imediata
    - **Urgência:** medium
    | critical | 1 |

Três leituras do mesmo modelo, na mesma página, e duas delas erradas. Foi a minha própria correcção
que ficou a meio: tratei uma chamada e deixei duas.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _payload(*, declared: bool, likelihood: int = 5, impact: int = 5) -> Any:
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
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Fila"},
            "components": [{"id": "q1", "name": "Fila de eventos", "kind": "queue"}],
            "threats": threats,
        }
    )
    return build_premium_report_payload(document, analyze_document(document), level=ReportLevel.EXECUTIVE)


def _field(payload: Any, name: str) -> Any:
    stack: list[Any] = [payload.model_dump(mode="json")]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if name in node:
                return node[name]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    raise AssertionError(f"o payload não expõe `{name}`")


def test_sem_ameaca_declarada_a_urgencia_e_moderada() -> None:
    """Premissa: o modelo só-heurístico é mesmo de urgência média."""
    assert _field(_payload(declared=False), "urgency_level") == "medium"


def test_uma_ameaca_critica_declarada_eleva_a_urgencia() -> None:
    payload = _payload(declared=True)

    assert _field(payload, "overall_status") == "requires_immediate_attention"
    assert _field(payload, "urgency_level") == "high", (
        "a capa diz atenção imediata e a urgência diz o contrário, na mesma página"
    )


def test_uma_ameaca_declarada_media_nao_eleva_a_urgencia() -> None:
    """A correcção não podia ser tratar qualquer ameaça declarada como urgente."""
    assert _field(_payload(declared=True, likelihood=2, impact=2), "urgency_level") == "medium"
