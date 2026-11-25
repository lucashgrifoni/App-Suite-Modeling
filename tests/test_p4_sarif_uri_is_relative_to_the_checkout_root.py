"""O URI no SARIF tem de ser relativo à raiz que o `%SRCROOT%` declara.

O exportador declara `uriBaseId: "%SRCROOT%"` com a descrição *"The root of the repository
checkout the analysis ran in."*, e o GitHub resolve o URI contra o repositório. O CLI escrevia o
caminho **tal como o utilizador o escreveu**, que é relativo ao directório de trabalho.

A Action expõe um input `working-directory` e corre o `analyze` lá dentro. Com
`working-directory: services/api` e `model: models/orders.otm.yaml`, o SARIF afirmava
`<root>/models/orders.otm.yaml` para um ficheiro que está em
`<root>/services/api/models/orders.otm.yaml`. Reproduzido: o caminho afirmado existia e era
**outro ficheiro**, por isso os alertas do code scanning ligavam-se ao ficheiro errado.

`checkout_path` no `upload-sarif` não resolve isto — esse input diz onde está o checkout, e um
subdirectório não é um checkout: não tem `.git` e a action precisa dele para o SHA. O prefixo tem
de vir de quem o conhece, que é a própria Action.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))
sys.path.insert(0, str(_ROOT / "apps" / "cli"))

_ACTION = _ROOT / "action.yml"


@pytest.fixture()
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Uma árvore com o modelo num subdirectório e uma isca no sítio que o SARIF afirmava."""
    (tmp_path / "models").mkdir()
    (tmp_path / "services" / "api" / "models").mkdir(parents=True)
    source = _ROOT / "examples" / "minimal.otm.yaml"
    shutil.copy(source, tmp_path / "services" / "api" / "models" / "orders.otm.yaml")

    decoy = yaml.safe_load(source.read_text(encoding="utf-8"))
    decoy["metadata"]["title"] = "ISCA na raiz"
    (tmp_path / "models" / "orders.otm.yaml").write_text(
        yaml.safe_dump(decoy, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path / "services" / "api")
    return tmp_path


def _sarif_uri(args: list[str]) -> str:
    from otm_cli.main import cli_app
    from typer.testing import CliRunner

    result = CliRunner().invoke(cli_app, ["analyze", "models/orders.otm.yaml", "--sarif-out", "out.sarif", "-q", *args])
    assert result.exit_code == 0, result.output
    run = json.loads(Path("out.sarif").read_text(encoding="utf-8"))["runs"][0]
    return run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]


def test_sem_prefixo_o_uri_continua_relativo_ao_diretorio(checkout: Path) -> None:
    """Não-regressão: quem corre na raiz do checkout não pode ver o caminho mudar."""
    assert _sarif_uri([]) == "models/orders.otm.yaml"


def test_com_prefixo_o_uri_aponta_ao_ficheiro_analisado(checkout: Path) -> None:
    uri = _sarif_uri(["--sarif-uri-prefix", "services/api"])

    assert uri == "services/api/models/orders.otm.yaml", uri
    assert (checkout / uri).exists(), "o URI afirmado não existe na árvore"
    assert "ISCA" not in (checkout / uri).read_text(encoding="utf-8"), "o URI aponta para a isca"


@pytest.mark.parametrize("prefix", [".", "./", ""])
def test_um_prefixo_vazio_ou_ponto_nao_altera_nada(checkout: Path, prefix: str) -> None:
    """`working-directory` tem `.` por omissão; esse caso não pode ganhar um `./` no URI."""
    assert _sarif_uri(["--sarif-uri-prefix", prefix]) == "models/orders.otm.yaml"


def test_a_action_passa_o_seu_working_directory_ao_cli() -> None:
    """Sem esta ligação a opção existe e ninguém a usa, que é o mesmo que não a ter."""
    steps = yaml.safe_load(_ACTION.read_text(encoding="utf-8"))["runs"]["steps"]
    analyze = next(s for s in steps if s.get("id") == "analyze")

    assert "--sarif-uri-prefix" in analyze["run"], analyze["run"]
    assert "WORKING_DIRECTORY" in analyze["run"] and "WORKING_DIRECTORY" in analyze["env"], analyze
