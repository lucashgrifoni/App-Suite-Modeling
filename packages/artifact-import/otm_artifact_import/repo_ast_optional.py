"""
Parsing JS leve opcional (Express routes) via `esprima`, quando instalado e activado.

Activar: `OTM_REPO_ESPRIMA=1` (ou `true`). Sem pacote ou sem flag → lista vazia (fallback total).
"""

from __future__ import annotations

import os
from typing import Any

_HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "use"})


def _route_method_name(callee: Any) -> str | None:
    """Nome do método HTTP (`get`/`post`/…) numa `MemberExpression`, ou None."""
    if callee.get("type") != "MemberExpression":
        return None
    prop = callee.get("property") or {}
    name = prop.get("name") or (prop.get("value") if prop.get("type") == "Literal" else None)
    if isinstance(name, str) and name in _HTTP_METHODS:
        return name
    return None


def _first_string_arg(node: Any) -> str | None:
    """Primeiro argumento `Literal` string da chamada, ou None."""
    for arg in node.get("arguments") or []:
        if arg.get("type") == "Literal" and isinstance(arg.get("value"), str):
            return str(arg["value"])
    return None


def _collect_call_route(node: Any, hits: list[tuple[str, str]]) -> None:
    name = _route_method_name(node.get("callee") or {})
    if name is None:
        return
    path = _first_string_arg(node)
    if path is not None:
        hits.append((name, path))


def _walk(node: Any, hits: list[tuple[str, str]]) -> None:
    """Percorre a árvore com uma pilha explícita — a profundidade custa heap, não stack.

    A versão recursiva gastava uma frame por nó, por isso a profundidade da árvore era a
    profundidade da pilha do interpretador: `a+a+a…` com mil termos (2 KB de JavaScript, e o
    ficheiro é de quem estamos a analisar precisamente por não confiarmos nele) rebentava com
    `RecursionError` para fora do comando. Limitar a profundidade teria trocado o crash por rotas
    silenciosamente em falta; uma pilha explícita não perde nenhuma.

    Os filhos entram invertidos porque `pop()` tira do fim: a ordem de visita — e portanto a ordem
    das rotas devolvidas — fica idêntica à da travessia recursiva.
    """
    stack: list[Any] = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if current.get("type") == "CallExpression":
                _collect_call_route(current, hits)
            stack.extend(reversed(current.values()))
        elif isinstance(current, list):
            stack.extend(reversed(current))


def collect_express_routes_ast_lite(source: str) -> list[tuple[str, str]]:
    """
    Devolve [(method, path), ...] quando `esprima` está disponível e parsing tolerante tem êxito.
    """
    flag = (os.environ.get("OTM_REPO_ESPRIMA") or "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return []
    try:
        import esprima
    except ImportError:
        return []
    hits: list[tuple[str, str]] = []
    try:
        tree = esprima.parseScript(source, tolerant=True, loc=False)
        _walk(tree.toDict() if hasattr(tree, "toDict") else tree, hits)
    except Exception:
        # O contrato do módulo é degradação total para a heurística regex. A conversão e a
        # travessia estavam fora deste `try` enquanto o parse estava dentro, por isso um ficheiro
        # que o parser aceitava mas cuja árvore rebentava a travessia saía como traceback.
        return []
    return hits
