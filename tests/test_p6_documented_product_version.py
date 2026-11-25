"""P6 — a versão de produto escrita na documentação tem de ser a do `pyproject.toml`.

`docs/README.md` abria com *"**Versão de produto:** `7.5.0` — fonte canónica:
[`pyproject.toml`](../pyproject.toml)"*. A linha nomeia a fonte canónica e contradi-la ao mesmo
tempo: o `pyproject.toml` diz `7.9.0` há quatro releases.

Copiar um número à mão para a documentação garante que ele envelhece; a única questão é quando.
Este teste fecha a distância entre a afirmação e a fonte que ela própria invoca.

Só olha para linhas que afirmam a versão **corrente** — `Versão de produto:` e
`Derived from: … App Suite Modeling`. O `CHANGELOG.md` e o `VERSIONING_AND_TAGS.md` nomeiam versões
antigas de propósito, e devem continuar a poder fazê-lo.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

#: Marcadores de uma afirmação sobre a versão **actual**, com o padrão que a captura.
_CLAIMS = (
    re.compile(r"\*\*Versão de produto:\*\*\s*`([0-9]+\.[0-9]+\.[0-9]+)`"),
    re.compile(r"Derived from:\*\*\s*App Suite Modeling\s*`v([0-9]+\.[0-9]+\.[0-9]+)`"),
)


def _pyproject_version() -> str:
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _claimed_versions() -> dict[str, str]:
    found: dict[str, str] = {}
    for md in sorted((_ROOT / "docs").rglob("*.md")) + [_ROOT / "README.md"]:
        text = md.read_text(encoding="utf-8")
        for pattern in _CLAIMS:
            for match in pattern.finditer(text):
                found[f"{md.relative_to(_ROOT).as_posix()}: {match.group(0)[:40]}"] = match.group(1)
    return found


def test_alguma_documentacao_afirma_a_versao() -> None:
    """Sanidade: sem afirmações, o teste seguinte passaria por vazio."""
    assert _claimed_versions(), "nenhuma afirmação de versão encontrada — os padrões deixaram de casar?"


def test_a_versao_afirmada_e_a_do_pyproject() -> None:
    expected = _pyproject_version()
    wrong = {where: got for where, got in _claimed_versions().items() if got != expected}

    assert not wrong, f"pyproject diz {expected}; a documentação diz outra coisa: {wrong}"
