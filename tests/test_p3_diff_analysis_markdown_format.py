"""`otm diff-analysis --format markdown` tem de emitir Markdown, como o seu irmão já faz.

`DiffFormat` tem três valores e o `--help` do comando mostra `<text|json|markdown>`. O serviço e o
comando só ramificavam em `json`, por isso `markdown` caía no `else` que desenha um `Panel` do
Rich: o utilizador pedia Markdown, recebia caracteres de desenho de caixa, e o comando saía **0**.
Uma pipeline que redireccione isto para um ficheiro `.md` fica com lixo sem um aviso.

`otm diff` — o irmão, que arma a mesma política de gate e partilha este enum — honra `markdown` e
imprime-o cru para se manter *pipeable*; o comentário em `diff_cmd.py` diz exactamente isso. Eram
os dois comandos a discordar sobre a mesma flag.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))
sys.path.insert(0, str(_ROOT / "apps" / "cli"))

_BOX_DRAWING = "─│┌┐└┘╭╮╰╯━┏┓┗┛"


@pytest.fixture(scope="module")
def analyses(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Duas análises guardadas que diferem, para o diff ter o que reportar."""
    from otm_cli.main import cli_app

    tmp = tmp_path_factory.mktemp("diffanalysis")
    base = yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8"))
    revised = yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8"))
    revised["components"].append(
        {"id": "extra", "name": "Extra service", "kind": "process", "in_trust_boundary": "vpc"}
    )

    out: list[Path] = []
    for name, doc in (("a", base), ("b", revised)):
        model = tmp / f"{name}.otm.yaml"
        model.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        analysis = tmp / f"{name}.json"
        result = CliRunner().invoke(cli_app, ["analyze", str(model), "--json-out", str(analysis), "-q"])
        assert result.exit_code == 0, result.output
        out.append(analysis)
    return out[0], out[1]


def _run(analyses: tuple[Path, Path], fmt: str) -> str:
    from otm_cli.main import cli_app

    result = CliRunner().invoke(cli_app, ["diff-analysis", str(analyses[0]), str(analyses[1]), "--format", fmt])
    assert result.exit_code == 0, result.output
    return result.output


def test_o_formato_json_continua_a_ser_json(analyses: tuple[Path, Path]) -> None:
    """Sanidade e não-regressão: o único formato que já funcionava tem de continuar."""
    assert json.loads(_run(analyses, "json"))


def test_o_formato_markdown_nao_traz_desenho_de_caixa(analyses: tuple[Path, Path]) -> None:
    output = _run(analyses, "markdown")

    offending = sorted({ch for ch in output if ch in _BOX_DRAWING})
    assert not offending, f"saída pedida em markdown traz caracteres de painel: {offending}"


def test_o_formato_markdown_e_markdown(analyses: tuple[Path, Path]) -> None:
    output = _run(analyses, "markdown")

    assert any(line.startswith("#") for line in output.splitlines()), f"nenhum título:\n{output[:400]}"
    assert any(line.startswith("- ") for line in output.splitlines()), f"nenhuma lista:\n{output[:400]}"


def test_o_formato_texto_continua_a_ter_o_painel(analyses: tuple[Path, Path]) -> None:
    """A correcção não podia ser tirar o painel a quem não pediu markdown."""
    assert any(ch in _BOX_DRAWING for ch in _run(analyses, "text"))


def test_a_ajuda_nao_esconde_o_formato_que_o_comando_aceita() -> None:
    """O `--help` dizia "text or json." para um enum de três valores."""
    from otm_cli.main import cli_app

    help_text = CliRunner().invoke(cli_app, ["diff-analysis", "--help"]).output

    assert "markdown" in help_text, help_text
