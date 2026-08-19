"""Uma etiqueta que **começa** por crase torna o diagrama inteiro inparseável.

`["\u0060texto"]` é a sintaxe de *markdown string* do Mermaid, e ela dispara pela adjacência: a
crase tem de vir logo a seguir à aspa. Um nome de componente como `` `api `` abria uma markdown
string que nunca fechava e o `.mmd` inteiro deixava de parsear — não a linha, o ficheiro.

Verificado contra o **parser real** (mermaid 11.17.0 + jsdom, `mermaid.parse`,
`securityLevel: "strict"`), sobre o diagrama que este exportador produz:

    sem crase             PARSE OK
    crase inicial         PARSE FALHOU
    crase no meio         PARSE OK
    crases a envolver     PARSE OK

Só a inicial, o que confirma que é a adjacência e não a crase. Candidatos testados contra o mesmo
parser: espaço à frente OK, `&#96;` OK, `\\u0060` FALHA. Escolhido o espaço, porque preserva todos os
caracteres e não depende de como cada renderizador trata entidades HTML.

Esse harness precisa de npm e de um DOM, por isso não corre nesta suíte — como já documenta
`test_p2r2_export_mermaid_parseability.py`. As asserções abaixo fixam a forma emitida que ele
provou correcta.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _diagram(component_name: str) -> str:
    from otm_core_schema import ThreatModelDocument
    from otm_exporters import export_flowchart_mermaid

    doc = yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8"))
    doc["components"][0]["name"] = component_name
    return export_flowchart_mermaid(ThreatModelDocument.model_validate(doc))


def test_nenhuma_etiqueta_abre_uma_markdown_string() -> None:
    diagram = _diagram("`api")

    assert '["`' not in diagram, f"a aspa seguida de crase abre uma markdown string:\n{diagram[:300]}"


def test_o_texto_da_etiqueta_sobrevive() -> None:
    """Neutralizar não é apagar: a crase e o nome continuam lá."""
    diagram = _diagram("`api")

    assert "`api" in diagram, diagram[:300]


@pytest.mark.parametrize("name", ["a`b", "`api`", "API", "`"])
def test_as_outras_posicoes_da_crase_nao_mudam(name: str) -> None:
    """Só a adjacência à aspa é o problema; o parser aceita as outras, e não se mexe nelas."""
    diagram = _diagram(name)

    assert name.lstrip("`") in diagram or name in diagram
    assert '["`' not in diagram


def test_uma_etiqueta_normal_nao_ganha_espaco() -> None:
    """O custo do espaço só é pago por quem tem uma crase inicial."""
    assert '["API"]' in _diagram("API")
