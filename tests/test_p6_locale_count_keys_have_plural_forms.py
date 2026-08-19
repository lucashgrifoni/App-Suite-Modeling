"""Uma chave invocada com `count` tem de ter forma singular, ou a UI escreve "1 itens".

O i18next escolhe entre `chave_one` e `chave_other` quando lhe passam `count`. Sem essas formas
fica a chave base, e o número entra num substantivo já plural: medido no pt-BR, "1 itens",
"1 ligações", "1 componentes", "1 fluxos", "+1 adicionados", "−1 removidos", "~1 alterados". O
inglês sofre do mesmo em quatro delas ("1 components", "1 items"), por isso não é um defeito de
tradução — é da estrutura das chaves.

O contrato está no ponto de chamada, e é de lá que este teste o lê: se um componente escreve
`t("k", { count: n })`, então `k_one` e `k_other` têm de existir em **todos** os locales. Assim a
próxima chave de contagem que alguém acrescentar sem formas plurais é apanhada, em vez de se ficar
por corrigir a lista de hoje.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "apps" / "web" / "src"
_LOCALES = _SRC / "i18n" / "locales"

#: `t("alguma.chave", { count: ... })` — o que faz o i18next procurar as formas plurais.
_COUNT_CALL = re.compile(r"""t\(\s*["'`]([\w.]+)["'`]\s*,\s*\{[^}]*\bcount\s*:""")


def _keys_called_with_count() -> set[str]:
    found: set[str] = set()
    for path in _SRC.rglob("*.ts*"):
        if path.name.endswith((".test.ts", ".test.tsx")):
            continue
        found |= set(_COUNT_CALL.findall(path.read_text(encoding="utf-8")))
    return found


def _flat(data: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out |= _flat(value, name)
        else:
            out[name] = value
    return out


def _locale(name: str) -> dict[str, str]:
    return _flat(json.loads((_LOCALES / f"{name}.json").read_text(encoding="utf-8")))


def test_ha_chaves_invocadas_com_count() -> None:
    """Sanidade: se a varredura não encontrasse nada, o teste seguinte passaria por vazio."""
    assert len(_keys_called_with_count()) >= 7


def test_toda_a_chave_de_contagem_tem_singular_e_plural() -> None:
    missing: dict[str, list[str]] = {}
    for locale in ("en", "pt-BR"):
        strings = _locale(locale)
        absent = sorted(
            key for key in _keys_called_with_count() if f"{key}_one" not in strings or f"{key}_other" not in strings
        )
        if absent:
            missing[locale] = absent

    assert not missing, (
        f"chaves invocadas com `count` e sem formas plurais — a UI escreve o plural ao singular: {missing}"
    )


def test_o_singular_nao_e_igual_ao_plural_em_pt_br() -> None:
    """Se as duas formas forem iguais, a chave plural não corrigiu nada."""
    strings = _locale("pt-BR")
    identical = sorted(
        key
        for key in _keys_called_with_count()
        if strings.get(f"{key}_one") is not None and strings[f"{key}_one"] == strings.get(f"{key}_other")
    )

    assert not identical, f"formas singular e plural idênticas em pt-BR: {identical}"
