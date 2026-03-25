"""Validação mínima de links internos em documentação Markdown."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

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
