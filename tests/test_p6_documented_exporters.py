"""P6 — a página de exportadores tem de listar os exportadores que existem.

`docs/features/EXPORTERS.md` é o que `docs/README.md` e o `README.md` oferecem como resposta a
"o que é que isto exporta?". Listava **10** dos 17 nomes de `otm_exporters.__all__`, e entre os sete
em falta estavam `export_analysis_sarif` e `export_analysis_sarif_obj` — SARIF não aparecia uma
única vez no documento.

Isso é a omissão que mais custa: o SARIF é o formato de que depende toda a integração com code
scanning, é o que a action composta publica, e é a razão pela qual o produto aparece no separador
de segurança de quem o usa. Quem avaliasse a ferramenta para essa integração abria a página das
exportações e não o encontrava, enquanto o README duas páginas antes o vendia.

Faltavam também o backlog de remediação (três funções), a comparação e uma variante de bundle.

O teste lê `__all__` **do pacote** e exige que cada nome apareça no documento. Não fixa a redacção
nem a ordem: fixa a cobertura, que é o que se quer manter quando alguém reorganizar a página.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "features" / "EXPORTERS.md"

sys.path.insert(0, str(_ROOT / "packages" / "exporters"))


def _exported_names() -> set[str]:
    import otm_exporters

    return {name for name in otm_exporters.__all__ if name.startswith("export_")}


def test_o_pacote_expoe_os_exportadores_que_esperamos() -> None:
    """Sanidade: sem isto, o teste seguinte passaria por não haver nada para comparar."""
    names = _exported_names()

    assert len(names) >= 15, f"apenas {len(names)} exportadores encontrados"
    assert "export_analysis_sarif" in names


def test_todos_os_exportadores_estao_documentados() -> None:
    """A regra: cada função pública do pacote aparece na página que a documenta."""
    text = _DOC.read_text(encoding="utf-8")
    missing = sorted(name for name in _exported_names() if name not in text)

    assert not missing, f"exportadores ausentes de EXPORTERS.md: {missing}"


def test_o_sarif_e_nomeado_e_nao_apenas_listado() -> None:
    """A omissão que motivou este ficheiro: o formato tem de ser reconhecível como tal.

    Listar `export_analysis_sarif` numa lista alfabética satisfaz o teste acima sem responder à
    pergunta que o leitor traz — "isto exporta SARIF?". A palavra tem de estar lá.
    """
    text = _DOC.read_text(encoding="utf-8").lower()

    assert "sarif" in text


def test_a_pagina_nao_se_anuncia_como_mvp() -> None:
    """O rótulo `API pública (MVP)` descrevia um estado que sete releases deixaram para trás."""
    text = _DOC.read_text(encoding="utf-8")

    assert "API pública (MVP)" not in text
