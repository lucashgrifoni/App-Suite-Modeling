"""Discover literal local module calls within an imported Terraform directory."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

_TOKEN = re.compile(
    r"(?P<comment>/\*[\s\S]*?(?:\*/|\Z)|//[^\r\n]*|\#[^\r\n]*)"
    r"|<<-?(?P<heredoc>[\w-]+)[ \t]*\r?\n"
    r"|[^\W\d][\w-]*|\S"
)
_LABEL = re.compile(r'"([\w-]+)"')
_LITERAL = re.compile(r'"([^"\\\r\n$%]+)"')


def _after_heredoc(text: str, label: str, position: int) -> int:
    end = re.compile(rf"(?m)^[ \t]*{re.escape(label)}[ \t]*\r?$").search(text, position)
    return end.end() if end else len(text)


def _after_quoted(text: str, position: int) -> int:
    # None represents quoted text. An integer counts braces inside a template expression.
    scopes: list[int | None] = [None]
    while scopes and position < len(text):
        char = text[position]
        depth = scopes[-1]
        if depth is None:
            if char == '"':
                scopes.pop()
            elif char == "\\":
                position += 1
            elif text.startswith(("$${", "%%{"), position):
                position += 2
            elif text.startswith(("${", "%{"), position):
                scopes.append(1)
                position += 1
        elif char == '"':
            scopes.append(None)
        elif char == "{":
            scopes[-1] = depth + 1
        elif char == "}":
            if depth == 1:
                scopes.pop()
            else:
                scopes[-1] = depth - 1
        elif char in "/#<":
            match = _TOKEN.match(text, position)
            if match and match["comment"] is not None:
                position = match.end() - 1
            elif match and (label := match["heredoc"]):
                position = _after_heredoc(text, label, match.end()) - 1
        position += 1
    return position


def _tokens(text: str) -> Iterator[str]:
    position = 0
    while match := _TOKEN.search(text, position):
        position = match.end()
        label = match["heredoc"]
        if label:
            position = _after_heredoc(text, label, position)
        elif match[0] == '"':
            position = _after_quoted(text, position)
            yield text[match.start() : position]
        elif match["comment"] is None:
            yield match[0]


def _module_calls(text: str) -> Iterator[tuple[str, str | None]]:
    tokens = list(_tokens(text))
    depth = 0
    name: str | None = None
    source: str | None = None
    for i, token in enumerate(tokens):
        if depth == 0 and token == "module" and i + 2 < len(tokens) and tokens[i + 2] == "{":
            label = _LABEL.fullmatch(tokens[i + 1])
            name = label[1] if label else None
            source = None
        elif depth == 1 and name and token == "source" and i + 2 < len(tokens) and tokens[i + 1] == "=":
            literal = _LITERAL.fullmatch(tokens[i + 2])
            source = literal[1] if literal else None
        if token == "{":
            depth += 1
        elif token == "}":
            depth = max(depth - 1, 0)
            if depth == 0 and name:
                yield name, source
                name = None


def read_local_modules(root: Path) -> tuple[list[tuple[str, str]], tuple[Path, ...], list[str]]:
    root = root.resolve()
    pending: list[tuple[str, Path, frozenset[Path]]] = [("", root, frozenset())]
    cache: dict[Path, tuple[str, list[tuple[str, str | None]]]] = {}
    modules: list[tuple[str, str]] = []
    inputs: set[Path] = set()
    unknowns: list[str] = []
    while pending:
        prefix, folder, ancestors = pending.pop()
        if folder in ancestors:
            unknowns.append(f"Módulo Terraform {prefix.removesuffix('.')} tem uma referência cíclica.")
            continue
        if folder not in cache:
            parts = []
            calls: list[tuple[str, str | None]] = []
            for path in sorted(folder.glob("*.tf")):
                if path.is_file() and path.resolve().is_relative_to(root):
                    content = path.read_text(encoding="utf-8")
                    inputs.add(path)
                    parts.append(content)
                    calls.extend(_module_calls(content))
            cache[folder] = "\n\n".join(parts), calls
        text, calls = cache[folder]
        modules.append((prefix, text))
        seen = set()
        for name, source in calls:
            if name in seen:
                continue
            seen.add(name)
            address = f"{prefix}module.{name}"
            if not source or not source.startswith(("./", "../")):
                unknowns.append(f"Módulo Terraform {address} sem fonte local literal.")
                continue
            try:
                target = (folder / source).resolve()
            except (OSError, RuntimeError, ValueError):
                unknowns.append(f"Módulo Terraform {address} com caminho local inválido.")
                continue
            if not target.is_relative_to(root) or not target.is_dir():
                unknowns.append(f"Módulo Terraform {address} ausente na pasta selecionada.")
                continue
            pending.append((f"{address}.", target, ancestors | {folder}))
    return modules, tuple(sorted(inputs)), unknowns
