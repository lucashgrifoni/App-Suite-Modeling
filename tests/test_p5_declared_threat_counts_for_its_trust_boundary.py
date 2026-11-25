"""Declarar uma ameaça tem de **mover** uma linha da distribuição por fronteira, nunca apagá-la.

`_build_distribution_counters` percorre `doc.threats` e alimenta `stride_counter`, `sev_counter`,
`comp_counter` e — desde a correcção do mapa — `heatmap`. Salta `tb_counter`, o único que ficou de
fora. E o efeito não é uma contagem a menos: a heurística equivalente é suprimida como duplicada
quando o modelador declara a sua própria ameaça, portanto declarar ameaças sobre os componentes de
uma fronteira faz a fronteira **desaparecer** de `by_trust_boundary`, de `top_boundaries_ranked` e
da lista "Principais trust boundaries" do relatório — na mesma página que continua a listar os
componentes dessa fronteira em "Principais superfícies".

Medido: 12 ameaças declaradas sobre dois componentes de `app_tier` levam
`by_trust_boundary` de `{'Camada aplicacional': 8, 'Internet': 2}` a `{'Internet': 2}`, enquanto
todos os outros contadores sobem de 13 para 17.

A invariante que o teste fixa é a do ciclo das heurísticas, quatro linhas acima: uma ameaça que
conta para um componente conta para a fronteira desse componente.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_DECLARED = [
    ("t_dec_spoof", "spoofing", "c_api"),
    ("t_dec_repud", "repudiation", "c_db"),
]


def _distributions(*, declared: bool) -> Any:
    from otm_core_schema import ThreatModelDocument
    from otm_report_premium import ReportLevel, build_premium_report_payload
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "system_type": "web_application", "industry_sector": "saas"},
            "metadata": {"title": "Camada aplicacional"},
            "trust_boundaries": [{"id": "tb_app", "name": "Camada aplicacional"}],
            "components": [
                {"id": "c_api", "name": "API de contas", "kind": "process", "in_trust_boundary": "tb_app"},
                {"id": "c_db", "name": "Base de dados", "kind": "datastore", "in_trust_boundary": "tb_app"},
            ],
            "threats": (
                [
                    {
                        "id": tid,
                        "title": f"Ameaça declarada {tid}",
                        "stride": stride,
                        "target_component_id": target,
                        "risk": {"likelihood": 5, "impact": 5},
                    }
                    for tid, stride, target in _DECLARED
                ]
                if declared
                else []
            ),
        }
    )
    return build_premium_report_payload(document, analyze_document(document), level=ReportLevel.DEEP).distributions


def test_todos_os_componentes_do_modelo_estao_dentro_da_fronteira() -> None:
    """Premissa: sem isto, uma diferença entre os dois contadores seria legítima."""
    base = _distributions(declared=False)

    assert sum(base.by_component.values()) == sum(base.by_trust_boundary.values()), (
        f"o modelo base já divergia: componentes={base.by_component} fronteiras={base.by_trust_boundary}"
    )


def test_a_fronteira_nao_desaparece_quando_o_modelador_declara_as_ameacas() -> None:
    declared = _distributions(declared=True)

    assert "Camada aplicacional" in declared.by_trust_boundary, (
        f"a fronteira saiu da distribuição: {declared.by_trust_boundary}"
    )
    assert "Camada aplicacional" in dict(declared.top_boundaries_ranked), (
        f"a fronteira saiu do ranking: {declared.top_boundaries_ranked}"
    )


def test_uma_ameaca_que_conta_para_o_componente_conta_para_a_fronteira() -> None:
    """A invariante do ciclo das heurísticas, aplicada ao ciclo das declaradas."""
    declared = _distributions(declared=True)

    assert sum(declared.by_trust_boundary.values()) == sum(declared.by_component.values()), (
        f"componentes={declared.by_component} fronteiras={declared.by_trust_boundary}"
    )


def test_declarar_move_a_linha_em_vez_de_a_apagar() -> None:
    """Duas ameaças declaradas não podem baixar a contagem da fronteira que as contém."""
    base, declared = _distributions(declared=False), _distributions(declared=True)

    assert declared.by_trust_boundary.get("Camada aplicacional", 0) >= base.by_trust_boundary.get(
        "Camada aplicacional", 0
    ), f"base={base.by_trust_boundary} declarado={declared.by_trust_boundary}"
