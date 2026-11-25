"""P6 — os cabeçalhos de segurança vivem em três sítios mantidos à mão e não podem divergir.

A mesma política é escrita três vezes, em três formatos diferentes:

- `apps/web/vite.config.ts` — `PREVIEW_SECURITY_HEADERS`, o que o `vite preview` serve;
- `apps/web/public/_headers` — o que Netlify, Cloudflare Pages e análogos aplicam ao site estático;
- `docs/features/SECURITY_HEADERS.md` — o exemplo de nginx que um operador copia.

Hoje as três coincidem. O que este teste impede é o modo de falha silencioso: alguém aperta a CSP
num dos ficheiros — tipicamente naquele onde está a trabalhar — e os outros dois continuam a servir
a política antiga. Ninguém repara, porque uma CSP mais frouxa não parte nada: apenas deixa de
proteger. E o sítio que fica para trás costuma ser o de produção, porque é o que menos se toca.

O teste compara as **directivas**, não o texto: reordenar `img-src` e `connect-src` continua a ser
a mesma política, e falhar por isso ensinaria a ignorar o teste.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VITE = _ROOT / "apps" / "web" / "vite.config.ts"
_HEADERS = _ROOT / "apps" / "web" / "public" / "_headers"
_DOC = _ROOT / "docs" / "features" / "SECURITY_HEADERS.md"


def _directives(csp: str) -> set[str]:
    """`img-src 'self' data:` → um item normalizado, insensível à ordem entre directivas."""
    return {" ".join(part.split()) for part in csp.split(";") if part.strip()}


def _csp_from_vite() -> str:
    text = _VITE.read_text(encoding="utf-8")
    match = re.search(r'"Content-Security-Policy":\s*\n?\s*"([^"]+)"', text)
    assert match, "não encontrei a CSP em vite.config.ts"
    return match.group(1)


def _csp_from_headers() -> str:
    for line in _HEADERS.read_text(encoding="utf-8").splitlines():
        if "Content-Security-Policy:" in line:
            return line.split("Content-Security-Policy:", 1)[1]
    raise AssertionError("não encontrei a CSP em public/_headers")


def _csp_from_doc() -> str:
    for line in _DOC.read_text(encoding="utf-8").splitlines():
        if "add_header Content-Security-Policy" in line:
            match = re.search(r'"([^"]+)"', line)
            assert match, "a linha do nginx não tem a política entre aspas"
            return match.group(1)
    raise AssertionError("não encontrei a CSP em SECURITY_HEADERS.md")


def test_as_tres_copias_da_csp_declaram_a_mesma_politica() -> None:
    preview, deploy, documented = _csp_from_vite(), _csp_from_headers(), _csp_from_doc()

    assert _directives(preview) == _directives(deploy), (
        "o preview do Vite e o deploy estático divergem — o site publicado não serve o que se testou"
    )
    assert _directives(deploy) == _directives(documented), (
        "o deploy e o exemplo de nginx divergem — quem seguir a documentação fica com outra política"
    )


def test_a_csp_mantem_as_directivas_que_fecham_o_perímetro() -> None:
    """Um travão contra o afrouxamento acidental, não só contra a divergência.

    Se as três forem relaxadas ao mesmo tempo, o teste acima continua verde. Estas quatro
    directivas são as que impedem embedding, injecção de base href e plugins.
    """
    directives = _directives(_csp_from_headers())

    for required in ("frame-ancestors 'none'", "object-src 'none'", "base-uri 'self'", "default-src 'self'"):
        assert required in directives, f"a CSP publicada deixou de declarar `{required}`"
