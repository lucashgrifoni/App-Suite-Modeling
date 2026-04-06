"""
Parsing JS leve opcional (Express routes) via `esprima`, quando instalado e activado.

Activar: `OTM_REPO_ESPRIMA=1` (ou `true`). Sem pacote ou sem flag → lista vazia (fallback total).
"""

from __future__ import annotations

import os
from typing import Any

_HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "use"})


def _walk(node: Any, hits: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        t = node.get("type")
        if t == "CallExpression":
            callee = node.get("callee") or {}
            if callee.get("type") == "MemberExpression":
                prop = callee.get("property") or {}
                name = prop.get("name") or (prop.get("value") if prop.get("type") == "Literal" else None)
                if isinstance(name, str) and name in _HTTP_METHODS:
                    for arg in node.get("arguments") or []:
                        if arg.get("type") == "Literal" and isinstance(arg.get("value"), str):
                            hits.append((name, arg["value"]))
                            break
        for v in node.values():
            _walk(v, hits)
    elif isinstance(node, list):
        for x in node:
            _walk(x, hits)


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
    try:
        tree = esprima.parseScript(source, tolerant=True, loc=False)
    except Exception:
        return []
    hits: list[tuple[str, str]] = []
    _walk(tree.toDict() if hasattr(tree, "toDict") else tree, hits)
    return hits
