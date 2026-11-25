"""O mapa de calor tem de contar as mesmas ameaças que a tabela ao lado dele.

`_build_distribution_counters` percorre `doc.threats` para actualizar os contadores de STRIDE, de
severidade e de componente — e nunca toca no `heatmap`. As ameaças que o modelador declara entram
portanto na tabela "por STRIDE" e na de severidade, e desaparecem do quadro STRIDE × severidade
impresso imediatamente a seguir, na mesma página.

Duas leituras da mesma página não podem discordar sobre quantas ameaças existem. É a mesma classe
da capa executiva, que ignorava estas ameaças no veredito enquanto o resto do relatório as contava.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _payload(*, declared: bool):
    from otm_core_schema import ThreatModelDocument
    from otm_report_premium import ReportLevel, build_premium_report_payload
    from otm_threat_engine import analyze_document

    threats = (
        [
            {
                "id": "t1",
                "title": "Perda total da fila",
                "stride": "denial_of_service",
                "target_component_id": "q1",
                "risk": {"likelihood": 5, "impact": 5},
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
    return build_premium_report_payload(document, analyze_document(document), level=ReportLevel.DEEP)


def _distribution(payload):
    for block in (payload.model_dump(mode="json"),):
        stack = [block]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if "heatmap_stride_severity" in node:
                    return node
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    raise AssertionError("o payload não expõe `heatmap_stride_severity`")


def test_a_tabela_por_stride_conta_a_ameaca_declarada() -> None:
    """Premissa: é a tabela que já a conta, e com a qual o mapa tem de concordar."""
    block = _distribution(_payload(declared=True))

    assert block["by_stride"].get("denial_of_service", 0) >= 1, block["by_stride"]


def test_o_mapa_de_calor_conta_o_mesmo_total_que_a_tabela_por_stride() -> None:
    block = _distribution(_payload(declared=True))

    by_stride = sum(block["by_stride"].values())
    heatmap = sum(sum(bands.values()) for bands in block["heatmap_stride_severity"].values())

    assert heatmap == by_stride, (
        f"o mapa conta {heatmap} e a tabela ao lado conta {by_stride}: "
        f"{block['heatmap_stride_severity']} vs {block['by_stride']}"
    )


def test_a_ameaca_declarada_entra_na_banda_da_sua_severidade() -> None:
    """L5xI5 = 25 é crítico; o mapa tem de a pôr lá, não noutra banda."""
    block = _distribution(_payload(declared=True))
    row = block["heatmap_stride_severity"].get("denial_of_service", {})

    assert row.get("critical", 0) >= 1, row


def test_declarar_uma_ameaca_nao_apaga_a_linha_do_mapa() -> None:
    """O efeito mais estranho, e o que expôs a causa.

    A heurística de `denial_of_service` que a fila gera é suprimida como duplicada quando o
    modelador declara a sua própria — o que está certo, e é por isso que `by_stride` continua em 1.
    Mas o ciclo que percorre `doc.threats` nunca tocava no mapa, por isso a linha desaparecia
    inteira: declarar a ameaça **removia-a** do quadro em vez de a mover de banda.
    """
    without = _distribution(_payload(declared=False))["heatmap_stride_severity"]
    with_declared = _distribution(_payload(declared=True))["heatmap_stride_severity"]

    assert "denial_of_service" in without, without
    assert "denial_of_service" in with_declared, (
        f"declarar a ameaça apagou a linha do mapa: {without} -> {with_declared}"
    )
