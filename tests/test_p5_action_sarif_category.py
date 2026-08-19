"""P5 — dois modelos no mesmo repositório não podem apagar os alertas um do outro.

O passo `Upload SARIF` do `action.yml` publicava com `category: otm-threat-model`, um literal sem
forma de o mudar. O GitHub indexa um conjunto de resultados de code scanning por
`(ref, category)`: duas invocações da action no mesmo repositório e ref escrevem no mesmo balde, e
a segunda substitui a primeira. Os alertas dos modelos anteriores passam a "no longer detected" e
fecham-se sozinhos.

E várias invocações são o uso previsto, não um desvio: o input `model` (`action.yml:12-14`) é
obrigatório e aponta **um** ficheiro `.otm.yaml`. Uma equipa que modele três serviços escreve uma
matriz e corre a action uma vez por modelo. Nenhum passo falha, nada avisa, e o separador de
segurança fica a mostrar só o último — o modo de falha silencioso.

**A correcção não pode mudar o comportamento de quem já a usa.** Mudar a categoria por omissão
deixaria os alertas antigos órfãos sob a categoria anterior: nunca mais seriam actualizados, logo
ficariam abertos para sempre. Por isso o default continua a ser exactamente `otm-threat-model`, e
o que se acrescenta é a possibilidade de distinguir. `test_o_default_continua_a_ser_a_categoria_de_hoje`
é o travão que impede isso de se perder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ACTION = Path(__file__).resolve().parents[1] / "action.yml"


def _action() -> dict[str, Any]:
    return yaml.safe_load(_ACTION.read_text(encoding="utf-8"))


def _step(name: str) -> dict[str, Any]:
    for step in _action()["runs"]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"action.yml não tem um passo chamado {name!r}")


def test_a_categoria_do_sarif_e_configuravel() -> None:
    """Sem um input, uma matriz de modelos não tem como separar os seus resultados."""
    assert "sarif-category" in _action()["inputs"]


def test_o_upload_usa_o_input_e_nao_um_literal() -> None:
    category = _step("Upload SARIF")["with"]["category"]

    assert "inputs.sarif-category" in str(category), f"a categoria continua fixa: {category!r}"


def test_o_default_continua_a_ser_a_categoria_de_hoje() -> None:
    """Mudar o default órfã os alertas de quem já corre esta action.

    Um conjunto de resultados que deixa de ser actualizado não se fecha: fica aberto sob a
    categoria antiga, para sempre. Quem tem um só modelo não pode pagar nada por esta correcção.
    """
    assert _action()["inputs"]["sarif-category"]["default"] == "otm-threat-model"


def test_a_categoria_nao_e_obrigatoria() -> None:
    """Exigi-la partiria todos os workflows que hoje chamam a action."""
    assert _action()["inputs"]["sarif-category"].get("required") is False


def test_a_descricao_diz_porque_e_que_isto_existe() -> None:
    """Um input cuja razão de ser não é óbvia é um input que ninguém define a tempo."""
    description = _action()["inputs"]["sarif-category"]["description"].lower()

    assert "categor" in description
    assert any(word in description for word in ("modelo", "model")), (
        "a descrição tem de dizer que é preciso um valor distinto por modelo"
    )
