"""O regenerador tem de comparar com o que escreve, não com o que recebeu.

`main()` escreve `content.rstrip("\n") + "\n"` -- normalização deliberada, para que estes
ficheiros versionados não mudem por causa do SO de quem os regenerou -- mas depois compara o
conteúdo anterior com `content`, o valor **antes** da normalização. Quando os dois diferem, e para
alguns exportadores diferem sempre, o script anuncia "actualizado" em todas as execuções enquanto
`git status` fica vazio, para sempre.

Importa porque este script existe para responder a uma pergunta: as amostras publicadas
correspondem ao motor de hoje? Uma resposta que diz "actualizado" mesmo quando nada mudou não
responde a nada, e ensina quem a lê a ignorá-la -- que é o custo real de um alarme sempre aceso.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "regenerate_export_samples", _ROOT / "scripts" / "regenerate_export_samples.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_segunda_execucao_nao_reporta_alteracoes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    monkeypatch.setattr(script, "SAMPLES", tmp_path / "samples")

    assert script.main() == 0
    first = capsys.readouterr().out
    assert "criado" in first, f"a primeira execução devia criar os ficheiros:\n{first}"

    assert script.main() == 0
    second = capsys.readouterr().out

    changed = [line for line in second.splitlines() if "actualizado" in line or "criado" in line]
    assert not changed, (
        f"nada mudou entre as duas execuções e o script diz que sim — comparar com o valor pré-normalização:\n{second}"
    )


def test_uma_alteracao_real_continua_a_ser_reportada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A correcção não podia ser deixar de reportar."""
    script = _load_script()
    samples = tmp_path / "samples"
    monkeypatch.setattr(script, "SAMPLES", samples)

    script.main()
    capsys.readouterr()
    victim = next(iter(sorted(samples.iterdir())))
    victim.write_text("conteúdo obsoleto\n", encoding="utf-8", newline="\n")

    script.main()
    out = capsys.readouterr().out

    assert f"{victim.name:26} actualizado" in out, f"a alteração real não foi reportada:\n{out}"
