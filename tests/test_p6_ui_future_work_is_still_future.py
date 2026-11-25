"""P6 — uma lista de "extensões futuras" não pode conter o que já foi entregue.

`docs/features/UI.md` é o que `docs/README.md` oferece como referência dos fluxos da aplicação web.
A sua secção "Extensões futuras" prometia duas coisas que já existem há várias releases:

- *"Diagrama visual (React Flow) alinhado a `data_flows`"* — `apps/web/src/components/diagram/`
  tem `ThreatModelDiagram.tsx` e `ComponentNode.tsx`, `reactflow` é dependência declarada, e há
  `apps/web/e2e/diagram.spec.ts`;
- *"Internacionalização (i18n)"* — `apps/web/src/i18n/` existe, `i18next` e `react-i18next` são
  dependências, e há `apps/web/e2e/i18n.spec.ts`.

Coerente com isso, a mesma página descrevia o passo 3 do fluxo como "lista de componentes e fluxos",
sem mencionar o diagrama interactivo.

O efeito é subtil e desfavorável: um leitor a avaliar a UI é informado de que lhe faltam duas
capacidades que ela tem. Documentação desactualizada normalmente promete a mais; esta prometia a
menos, e ninguém reclama de uma funcionalidade que lhe disseram não existir.

O terceiro item continua legitimamente por fazer — autenticação e persistência multi-utilizador —
e `KNOWN_LIMITATIONS.md` confirma-o. O teste distingue as duas situações ligando cada palavra-chave
a **evidência no repositório**, em vez de fixar a redacção da lista.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_UI_DOC = _ROOT / "docs" / "features" / "UI.md"

#: palavra que apareceria na lista de futuro -> caminho que prova que já foi entregue.
_SHIPPED = {
    "react flow": _ROOT / "apps" / "web" / "src" / "components" / "diagram",
    "reactflow": _ROOT / "apps" / "web" / "src" / "components" / "diagram",
    "internacionaliza": _ROOT / "apps" / "web" / "src" / "i18n",
    "i18n)": _ROOT / "apps" / "web" / "src" / "i18n",
}


def _future_section() -> str:
    text = _UI_DOC.read_text(encoding="utf-8")
    start = text.index("## Extensões futuras")
    rest = text[start + len("## Extensões futuras") :]
    end = rest.index("\n## ") if "\n## " in rest else len(rest)
    return rest[:end].lower()


@pytest.mark.parametrize("keyword", sorted(_SHIPPED))
def test_a_lista_de_futuro_nao_promete_o_que_ja_existe(keyword: str) -> None:
    evidence = _SHIPPED[keyword]
    if not evidence.exists():
        pytest.skip(f"{evidence.name} ainda não existe, logo continuar na lista está certo")

    section = _future_section()
    # A prosa pode nomear as duas para dizer que **foram** entregues; o que não pode é listá-las.
    listed = [ln for ln in section.splitlines() if ln.strip().startswith("-") and keyword in ln]

    assert not listed, f"`{keyword}` está listado como futuro mas {evidence.relative_to(_ROOT)} existe: {listed}"


def test_o_que_continua_por_fazer_continua_listado() -> None:
    """A correcção não pode ser esvaziar a secção: o que falta tem de continuar declarado."""
    section = _future_section()

    assert "multi-utilizador" in section or "persistência" in section, (
        "a ausência de contas e de persistência server-side é uma limitação real e tem de continuar escrita"
    )


def test_o_passo_do_diagrama_menciona_o_diagrama_interactivo() -> None:
    """O fluxo descrevia o passo 3 como uma lista, o que subestima o que a UI faz."""
    text = _UI_DOC.read_text(encoding="utf-8").lower()
    step = next(ln for ln in text.splitlines() if ln.startswith("3. **diagrama**"))

    assert "react flow" in step or "interactivo" in step
