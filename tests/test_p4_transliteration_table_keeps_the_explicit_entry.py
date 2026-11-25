"""A entrada derivada por `.upper()` não pode sobrescrever a que foi escrita à mão.

`_TRANSLITERATIONS` deriva as maiúsculas das minúsculas: `{k.upper(): v.capitalize()}`. Para
quase todos os caracteres `k.upper()` é outro carácter e as duas entradas coexistem. Para os que
não têm forma maiúscula, `k.upper()` devolve o próprio `k`, e a entrada derivada -- que vem depois
no dicionário -- apaga a explícita.

Hoje isso atinge um carácter, `ĸ` (U+0138, LATIN SMALL LETTER KRA), que transliterava para `K`
maiúsculo no meio de uma palavra minúscula. É pequeno, mas a regra é geral e a próxima linha
acrescentada à tabela pode cair na mesma armadilha em silêncio: o teste verifica a **propriedade**,
não o carácter.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "packages" / "report-premium"))


def test_nenhuma_entrada_explicita_e_apagada_pela_derivada() -> None:
    from otm_report_premium.pdf_text import _CYRILLIC_LOWER, _LATIN_FALLBACKS, _TRANSLITERATIONS

    corrupted = {
        char: (wanted, _TRANSLITERATIONS[char])
        for source in (_LATIN_FALLBACKS, _CYRILLIC_LOWER)
        for char, wanted in source.items()
        if _TRANSLITERATIONS.get(char) != wanted
    }

    assert not corrupted, (
        f"caracteres cuja transliteração explícita foi substituída pela versão derivada em maiúscula: {corrupted}"
    )


def test_o_kra_translitera_em_minuscula() -> None:
    """O caso concreto que expôs a regra, para que a correcção não se perca numa refactorização."""
    from otm_report_premium.pdf_text import to_pdf_font_text

    assert "\u0138".upper() == "\u0138", "premissa: o KRA não tem forma maiúscula"
    assert to_pdf_font_text("\u0138ayak") == "kayak"


def test_as_maiusculas_derivadas_continuam_a_existir() -> None:
    """A correcção não podia ser deixar de derivar: as maiúsculas reais têm de sobreviver.

    Os pares vêm da tabela, não da minha cabeça: a primeira versão deste teste afirmava
    `Ä` -> `Ae` e falhou porque `ä` nem sequer está na tabela -- a fonte desenha-o, e só entra
    aqui o que ela não desenha.
    """
    from otm_report_premium.pdf_text import to_pdf_font_text

    assert to_pdf_font_text("ł") == "l"
    assert to_pdf_font_text("Ł") == "L"
    assert to_pdf_font_text("а") == "a"
    assert to_pdf_font_text("А") == "A"
