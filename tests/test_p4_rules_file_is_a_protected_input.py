"""O ficheiro de regras da organização é uma entrada, e tem de ser protegido como tal.

`_require_output_is_not_a_source` recusa escrever o artefacto por cima de um ficheiro que o comando
acabou de ler, e o projecto tem `input_paths()` precisamente para dobrar as entradas **opcionais**
nesse `sources=`. `backlog -d` e `report --analysis-json` já o usam. O `--rules` não.

Medido: `otm analyze m.otm.yaml --rules org-rules.yaml --json-out org-rules.yaml` sai **0**, imprime
"Analysis written to …" e substitui 3 917 bytes de política escrita à mão por 77 938 bytes de dump
da análise. A mesma linha de comandos com o **modelo** como destino é correctamente recusada com
saída 1 — as duas entradas do mesmo comando eram tratadas de maneira diferente.

`docs/features/CUSTOM_RULES.md` diz ao utilizador para manter este ficheiro versionado ao lado do
modelo, e em CI as duas flags aparecem na mesma linha. Um caminho errado apaga a política que devia
travar o pipeline, e o pipeline fica verde.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def workspace(tmp_path: Path) -> dict[str, Path]:
    shutil.copy(_ROOT / "examples" / "minimal.otm.yaml", tmp_path / "m.otm.yaml")
    shutil.copy(_ROOT / "examples" / "minimal.otm.yaml", tmp_path / "m2.otm.yaml")
    shutil.copy(_ROOT / "examples" / "custom-rules.example.yaml", tmp_path / "org-rules.yaml")
    return {
        "model": tmp_path / "m.otm.yaml",
        "revised": tmp_path / "m2.otm.yaml",
        "rules": tmp_path / "org-rules.yaml",
    }


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv fixo, sem shell
        [sys.executable, "-m", "otm_cli.main", *args],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )


def test_o_modelo_ja_estava_protegido(workspace: dict[str, Path]) -> None:
    """Premissa: o guarda existe e funciona — o que falta é aplicá-lo à outra entrada."""
    before = workspace["model"].read_bytes()
    result = _run(["analyze", str(workspace["model"]), "--json-out", str(workspace["model"]), "-q"])

    assert result.returncode == 1
    assert workspace["model"].read_bytes() == before


@pytest.mark.parametrize("flag", ["--json-out", "--sarif-out"])
def test_analyze_recusa_escrever_por_cima_das_regras(workspace: dict[str, Path], flag: str) -> None:
    before = workspace["rules"].read_bytes()
    result = _run(
        [
            "analyze",
            str(workspace["model"]),
            "--rules",
            str(workspace["rules"]),
            flag,
            str(workspace["rules"]),
            "-q",
        ]
    )

    assert result.returncode == 1, f"saiu {result.returncode}: {result.stdout[:200]}"
    assert workspace["rules"].read_bytes() == before, "o ficheiro de regras foi destruído"


def test_diff_recusa_escrever_por_cima_das_regras(workspace: dict[str, Path]) -> None:
    before = workspace["rules"].read_bytes()
    result = _run(
        [
            "diff",
            str(workspace["model"]),
            str(workspace["revised"]),
            "--with-analysis",
            "--rules",
            str(workspace["rules"]),
            "--json-out",
            str(workspace["rules"]),
        ]
    )

    assert result.returncode == 1, f"saiu {result.returncode}: {result.stdout[:200]}"
    assert workspace["rules"].read_bytes() == before


def test_um_destino_legitimo_continua_a_ser_escrito(workspace: dict[str, Path], tmp_path: Path) -> None:
    """A correcção não podia ser recusar toda a escrita quando `--rules` é passado."""
    out = tmp_path / "analysis.json"
    result = _run(
        ["analyze", str(workspace["model"]), "--rules", str(workspace["rules"]), "--json-out", str(out), "-q"]
    )

    assert result.returncode == 0, result.stdout[:300]
    assert out.exists() and out.stat().st_size > 0
