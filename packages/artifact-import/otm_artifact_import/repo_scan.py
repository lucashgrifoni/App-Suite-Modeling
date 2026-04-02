"""
Varredura pragmática de repositório (Node/Express comum) — sinais úteis, não AST completo.

Produz inferências explicáveis para enriquecer `import_signals_corpus` ou revisão humana.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Extensões consideradas para texto de aplicação
_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx"}


def _read_text_files(root: Path, *, max_files: int = 200) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in _SUFFIXES:
            continue
        if "node_modules" in p.parts or ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out.append((p, text))
        if len(out) >= max_files:
            break
    return out


def scan_node_express_repo(root: Path) -> dict[str, Any]:
    """
    Percorre ficheiros e devolve inferências com evidência curta.

    Não altera o schema canónico sozinho — consumidores agregam ao modelo.
    """
    root = root.resolve()
    files = _read_text_files(root)
    inferences: list[dict[str, Any]] = []
    corpus_chunks: list[str] = []

    route_re = re.compile(r"(?:app|router)\.(?:get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]")
    router_mount_re = re.compile(r"(?:app|router)\.use\s*\(\s*['\"]([^'\"]+)['\"]")
    multer_re = re.compile(r"multer\(|upload\.single|upload\.array")
    session_re = re.compile(r"express-session|expressSession")
    fetch_re = re.compile(r"(?:axios|fetch)\(")
    eval_re = re.compile(r"\beval\s*\(|exec\s*\(")
    auth_re = re.compile(
        r"(?:passport|jsonwebtoken|express-jwt|jwt\.verify|requireAuth|authMiddleware|isAuthenticated)",
        re.IGNORECASE,
    )
    admin_route_re = re.compile(r"['\"]\/admin(?:\/|['\"])")
    child_re = re.compile(r"child_process|spawn\s*\(|execFile\s*\(")

    for path, text in files:
        rel = path.relative_to(root)
        for m in route_re.finditer(text):
            inferences.append(
                {
                    "kind": "route",
                    "message": f"Rota HTTP encontrada em `{rel}`",
                    "evidence": m.group(1)[:120],
                    "confidence": "medium",
                }
            )
        if multer_re.search(text):
            inferences.append(
                {
                    "kind": "upload",
                    "message": f"Possível upload de ficheiros (`multer`/upload) em `{rel}`",
                    "evidence": "multer|upload.single|upload.array",
                    "confidence": "medium",
                }
            )
        if session_re.search(text):
            inferences.append(
                {
                    "kind": "session",
                    "message": f"Sessão/cookies prováveis em `{rel}`",
                    "evidence": "express-session",
                    "confidence": "medium",
                }
            )
        if fetch_re.search(text):
            inferences.append(
                {
                    "kind": "external_fetch",
                    "message": f"Chamadas HTTP externas (axios/fetch) em `{rel}`",
                    "evidence": "axios|fetch",
                    "confidence": "low",
                }
            )
        if eval_re.search(text):
            inferences.append(
                {
                    "kind": "dangerous_eval",
                    "message": f"Possível eval/exec em `{rel}` — rever risco de injeção",
                    "evidence": "eval|exec",
                    "confidence": "high",
                }
            )
        if auth_re.search(text):
            inferences.append(
                {
                    "kind": "auth_middleware",
                    "message": f"Padrões de autenticação/autorização em `{rel}`",
                    "evidence": "passport|jwt|authMiddleware",
                    "confidence": "low",
                }
            )
        if admin_route_re.search(text):
            inferences.append(
                {
                    "kind": "admin_route",
                    "message": f"Possível rota ou prefixo `/admin` em `{rel}`",
                    "evidence": "/admin",
                    "confidence": "medium",
                }
            )
        if child_re.search(text):
            inferences.append(
                {
                    "kind": "child_process",
                    "message": f"Uso de child_process/spawn/execFile em `{rel}` — rever superfície de comando",
                    "evidence": "child_process|spawn|execFile",
                    "confidence": "medium",
                }
            )
        for m in router_mount_re.finditer(text):
            inferences.append(
                {
                    "kind": "middleware_mount",
                    "message": f"Montagem `use('{m.group(1)}')` em `{rel}`",
                    "evidence": m.group(1)[:120],
                    "confidence": "low",
                }
            )
        if len(corpus_chunks) < 40:
            corpus_chunks.append(f"{rel}: {text[:400]}")

    # dedupe por (kind, message)
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for inf in inferences:
        key = (inf.get("kind", ""), inf.get("message", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(inf)

    dir_hints: list[dict[str, Any]] = []
    for sub in ("public", "uploads", "static", "dist"):
        p = root / sub
        if p.is_dir():
            dir_hints.append(
                {
                    "kind": "directory_convention",
                    "message": f"Diretório `{sub}/` presente na raiz — possível conteúdo estático ou uploads",
                    "evidence": str(p.relative_to(root)),
                    "confidence": "low",
                }
            )

    return {
        "root": str(root),
        "files_scanned": len(files),
        "inferences": unique[:80],
        "directory_hints": dir_hints,
        "corpus_excerpt": "\n\n".join(corpus_chunks)[:8000],
    }
