"""Validação de links internos em documentação Markdown: ficheiros **e** âncoras.

A verificação de ficheiros saltava âncoras de propósito (`target.startswith("#")` era ignorado, e
num link `ficheiro.md#secção` só a parte do ficheiro era conferida). Foi por essa lacuna que
`docs/README.md` passou a apontar `[Comece aqui](#comece-aqui)` para um heading que se chama
"Comece aqui (instalação resumida)" — cujo slug é outro — sem que nada falhasse.

Um link que não resolve é o género de defeito que ninguém reporta: quem clica volta atrás e segue
sem dizer nada. Daí valer a pena o teste em vez da revisão manual.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlparse

_ROOT = Path(__file__).resolve().parents[1]
_DOCS = _ROOT / "docs"
_MD_FILES = [_ROOT / "README.md", *_DOCS.rglob("*.md")]
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _iter_local_links(md_path: Path) -> list[Path]:
    text = md_path.read_text(encoding="utf-8")
    links: list[Path] = []
    for raw in _LINK_RE.findall(text):
        target = raw.strip()
        if not target or target.startswith("#"):
            continue
        scheme = urlparse(target).scheme
        if scheme in {"http", "https", "mailto"}:
            continue
        rel = target.split("#", 1)[0]
        if not rel:
            continue
        links.append((md_path.parent / rel).resolve())
    return links


def test_markdown_internal_links_resolve() -> None:
    broken: list[str] = []
    for md in _MD_FILES:
        for link in _iter_local_links(md):
            if not link.exists():
                broken.append(f"{md.relative_to(_ROOT)} -> {link}")
    assert not broken, "Links internos inválidos:\n" + "\n".join(broken)


_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")


def _slug(heading: str) -> str:
    """Aproximação do slug do GitHub: markup fora, minúsculas, espaços viram hífen.

    Mantém letras acentuadas, que é o que distingue `comece-aqui-instalação-resumida` de um slug
    que as tivesse perdido — e este repositório documenta em português.
    """
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("*", "").replace("_", "").strip().lower()
    kept = [c for c in text if c.isalnum() or c in "-_ " or unicodedata.category(c).startswith("L")]
    return "".join(kept).replace(" ", "-")


def _headings(md_path: Path) -> set[str]:
    return {
        _slug(m.group(1)) for line in md_path.read_text(encoding="utf-8").splitlines() if (m := _HEADING_RE.match(line))
    }


def test_markdown_anchors_resolve() -> None:
    """Cada `#âncora` tem de corresponder a um heading do ficheiro que a serve."""
    cache: dict[Path, set[str]] = {}
    broken: list[str] = []

    for md in _MD_FILES:
        for raw in _LINK_RE.findall(md.read_text(encoding="utf-8")):
            target = raw.strip()
            if urlparse(target).scheme in {"http", "https", "mailto"} or "#" not in target:
                continue
            rel, _, anchor = target.partition("#")
            if not anchor:
                continue
            page = (md if not rel else md.parent / rel).resolve()
            if not page.is_file():
                continue  # o teste acima já cobre o ficheiro em falta
            if page not in cache:
                cache[page] = _headings(page)
            if unquote(anchor).lower() not in cache[page]:
                broken.append(f"{md.relative_to(_ROOT)} -> #{anchor}")

    assert not broken, "Âncoras que não correspondem a nenhum heading:\n" + "\n".join(broken)
