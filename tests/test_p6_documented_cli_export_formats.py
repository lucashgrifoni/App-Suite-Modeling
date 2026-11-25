"""P6 — a tabela do CLI tem de listar os formatos que `otm export` aceita.

`docs/features/CLI.md` documentava `otm export <arquivo> -f yaml|json|md` e omitia `otm`, que o
`ExportFormat` do CLI aceita e que `docs/POSITIONING.md` anuncia como o formato de intercâmbio do
produto — *"`otm import otm` and `otm export --format otm`"*.

É a mesma forma de erro que o `UI.md` tinha: documentação a prometer **a menos**. Ninguém reclama de
uma capacidade que lhe disseram não existir, por isso este tipo de omissão sobrevive mais tempo que
o exagero. Aqui custa mais do que noutro sítio: o formato omitido é o que torna o modelo portável
para fora da ferramenta, que é precisamente o argumento de posicionamento do projecto.

O teste lê o enum **do código** e exige que cada valor apareça na linha do `export`. Não fixa
redacção nem ordem, e continua a valer quando a tabela for reescrita.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CLI_DOC = _ROOT / "docs" / "features" / "CLI.md"

sys.path.insert(0, str(_ROOT / "apps" / "cli"))


def _export_formats() -> set[str]:
    from otm_cli.shared.enums import ExportFormat

    return {f.value for f in ExportFormat}


def _documented_formats() -> set[str]:
    """Só a lista de valores do `-f`, não a linha inteira.

    A primeira versão deste teste procurava cada formato na linha completa e **não discriminava**:
    a prosa que descreve o formato de intercâmbio contém a própria palavra `otm`, por isso retirá-lo
    da lista de flags deixava o teste verde. Verificado por mutação, que é como o defeito apareceu.
    """
    for line in _CLI_DOC.read_text(encoding="utf-8").splitlines():
        if "otm export" in line and line.lstrip().startswith("|"):
            match = re.search(r"-f\s+([a-z|\\]+)", line)
            assert match, f"a linha do export não declara os valores do `-f`: {line}"
            return {v for v in match.group(1).replace("\\", "").split("|") if v}
    raise AssertionError("não encontrei a linha do `otm export` na tabela do CLI.md")


def test_o_cli_aceita_os_formatos_que_esperamos() -> None:
    """Sanidade: sem isto, o teste seguinte passaria por não haver nada para comparar."""
    formats = _export_formats()

    assert {"yaml", "json", "md"} <= formats
    assert "otm" in formats, "o formato de intercâmbio deixou de existir no enum"


def test_a_tabela_do_cli_lista_todos_os_formatos_de_export() -> None:
    documented = _documented_formats()
    missing = sorted(_export_formats() - documented)

    assert not missing, (
        f"formatos aceites pelo CLI e ausentes da tabela: {missing} (documentados: {sorted(documented)})"
    )


def test_a_tabela_nao_promete_um_formato_que_o_cli_recusa() -> None:
    """O outro sentido da mesma deriva: documentar um valor que o enum recusa manda o leitor para um erro."""
    invented = sorted(_documented_formats() - _export_formats())

    assert not invented, f"formatos documentados que o CLI não aceita: {invented}"


def test_o_formato_de_intercambio_e_nomeado_e_nao_apenas_listado() -> None:
    """Aparecer numa lista alfabética não responde à pergunta que o leitor traz.

    `otm` é o formato que torna o modelo portável para fora da ferramenta — o argumento que
    `POSITIONING.md` usa contra as alternativas. A tabela tem de dizer o que ele é.
    """
    text = _CLI_DOC.read_text(encoding="utf-8").lower()

    assert "intercambio" in text or "intercâmbio" in text or "interchange" in text
