"""P5 — o sdist tem de descrever a fonte, tal como o wheel já descreve.

`[tool.setuptools.package-data]` e `exclude-package-data` governam o **wheel**. O sdist é
seleccionado à parte e, por omissão, arrasta o que estiver dentro dos directórios dos pacotes.
Como `otm_threat_engine/data/` é ele próprio um pacote, basta importar o catálogo — uma corrida de
testes chega — para o sdist seguinte levar bytecode.

Medido nesta árvore, imediatamente depois de uma corrida completa da suíte:

    wheel   321 entradas, 0 `.pyc`      (a correcção da fase 3 aguenta-se)
    sdist   620 entradas, 4 `__pycache__`, das quais 2 `.pyc`

e dois sdists da mesma fonte diferiam em tamanho (1 062 485 vs 1 062 398 bytes) com lista de
ficheiros idêntica, porque o conteúdo do bytecode difere entre construções. Com o `MANIFEST.in`:
617 entradas, zero.

`pyproject.toml` já escreve o argumento por extenso para o wheel — o caminho de publicação está
limpo "por ordenação, não por construção", e a correcção da fase 3 tornou-o construção. Isto
termina a mesma frase para o sdist.

**O que este ficheiro NÃO prova.** É um guarda de *configuração*, não de artefacto. Verificar o
artefacto exigiria construir o sdist dentro da suíte, e não é praticável aqui: `setuptools` não é
importável neste ambiente (venvs de 3.12 já não o incluem), pelo que `python -m build` precisa de
isolamento e de rede. A verificação ao nível do artefacto foi feita por medição, fora da suíte, e
está registada acima. O que se garante aqui é que a configuração que a produziu não desaparece nem
diverge da do wheel.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _ROOT / "MANIFEST.in"


def _manifest_lines() -> list[str]:
    raw = _MANIFEST.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in raw if ln.strip() and not ln.startswith("#")]


def _wheel_exclusions() -> list[str]:
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["setuptools"]["exclude-package-data"]["*"]


def test_the_manifest_exists() -> None:
    """Sem ele, o sdist volta a ser o que estiver no disco de quem construiu."""
    assert _MANIFEST.is_file(), "MANIFEST.in é o que impede o sdist de levar bytecode"


def test_bytecode_is_excluded_from_the_sdist() -> None:
    lines = _manifest_lines()

    assert "global-exclude *.pyc" in lines
    assert any(ln.startswith("prune") and "__pycache__" in ln for ln in lines), (
        "os directórios `__pycache__` têm de ser podados, não só os ficheiros dentro deles"
    )


def test_the_sdist_and_the_wheel_agree_on_what_is_junk() -> None:
    """Se as duas listas divergirem, um artefacto passa a levar o que o outro rejeita.

    A lista do wheel vive em `exclude-package-data`; a do sdist no `MANIFEST.in`. São mecanismos
    diferentes com sintaxes diferentes, e é exactamente por isso que podem afastar-se em silêncio.
    """
    manifest = " ".join(_manifest_lines())
    missing = []
    for pattern in _wheel_exclusions():
        # `**/__pycache__/*` (wheel) corresponde a `prune **/__pycache__` (sdist).
        token = pattern.replace("**/", "").replace("/*", "").lstrip("*")
        if token not in manifest:
            missing.append(pattern)

    assert not missing, f"o wheel exclui {missing}, o sdist não"


def test_the_repository_is_not_shipping_a_stale_build_directory() -> None:
    """`build/` guarda uma cópia antiga da árvore; se entrasse no sdist, envelhecia com ele."""
    lines = _manifest_lines()

    assert not any(ln.startswith("include") and "build" in ln for ln in lines)
