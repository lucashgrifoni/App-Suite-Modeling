"""A contagem por responsável não pode ser o comprimento de uma lista truncada.

`_build_ownership_rows` guarda `backlog_item_ids=ids[:30]` — o tecto existe para limitar o payload,
e isso está certo. O renderizador imprime `len(ow.backlog_item_ids)` como se fosse o número de
itens do responsável, o que passa a estar errado assim que alguém tem mais de 30.

O efeito não é um número ligeiramente baixo: é um número **plausível**. Três responsáveis com 75,
48 e 31 itens aparecem todos como "30 itens", sem marca nenhuma de truncagem, e um leitor conclui
que a carga está distribuída por igual. O tecto é uma decisão de payload; contá-lo como se fosse a
realidade é que não.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_CAP = 30
_OWNED = 42


def _payload():
    from otm_core_schema import ThreatModelDocument
    from otm_report_premium import ReportLevel, build_premium_report_payload
    from otm_threat_engine import analyze_document

    components = [
        {"id": f"c{i}", "name": f"Servico {i}", "kind": "process", "exposure_type": "public_internet"}
        for i in range(_OWNED)
    ]
    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Muitos servicos"},
            "components": components,
        }
    )
    return build_premium_report_payload(document, analyze_document(document), level=ReportLevel.DEEP)


def test_ha_um_responsavel_com_mais_itens_do_que_o_tecto() -> None:
    """Premissa: sem isto o teste seguinte passaria por não haver truncagem nenhuma."""
    payload = _payload()

    assert payload.ownership, "o relatório não produziu linhas de responsabilidade"
    assert any(row.item_count > _CAP for row in payload.ownership), (
        f"nenhum responsável passa dos {_CAP}: {[row.item_count for row in payload.ownership]}"
    )


def test_a_contagem_publicada_nao_e_o_comprimento_da_lista_truncada() -> None:
    for row in _payload().ownership:
        if row.item_count > _CAP:
            assert len(row.backlog_item_ids) == _CAP, "premissa: a lista continua limitada"
            assert row.item_count != len(row.backlog_item_ids)


def test_o_markdown_imprime_a_contagem_real() -> None:
    from otm_report_premium.render_markdown import render_premium_markdown

    payload = _payload()
    biggest = max(row.item_count for row in payload.ownership)
    markdown = render_premium_markdown(payload)

    assert f"{biggest} " in markdown, f"o markdown não imprime {biggest}"


def test_um_responsavel_abaixo_do_tecto_continua_exacto() -> None:
    """A correcção não podia inflacionar quem não foi truncado."""
    for row in _payload().ownership:
        if row.item_count <= _CAP:
            assert row.item_count == len(row.backlog_item_ids)
