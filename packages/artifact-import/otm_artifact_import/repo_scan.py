"""
Varredura pragmática de repositório (Node/Express comum) — sinais úteis, não AST completo.

Produz inferências explicáveis para enriquecer `import_signals_corpus` ou revisão humana.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from otm_artifact_import.repo_ast_optional import collect_express_routes_ast_lite

# Extensões consideradas para texto de aplicação (Node + Python leve)
_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".py"}

_PY_FASTAPI = re.compile(
    r"(?:FastAPI\s*\(|APIRouter\s*\(|@app\.(?:get|post|put|delete|patch)\s*\()",
    re.IGNORECASE,
)
_PY_FLASK = re.compile(r"(?:Flask\s*\(|Blueprint\s*\(|@app\.route\s*\()", re.IGNORECASE)
_PY_UVICORN = re.compile(r"uvicorn\b|hypercorn\b", re.IGNORECASE)


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
    multer_re = re.compile(
        r"multer\s*\(|upload\.(?:single|array|fields)|express\.file\s*\(|busboy\s*\(",
        re.IGNORECASE,
    )
    session_re = re.compile(
        r"express-session|expressSession|cookie-session|connect\.mongo|req\.session\b",
        re.IGNORECASE,
    )
    fetch_re = re.compile(r"(?:axios|fetch|got|needle|request)\s*\(")
    eval_re = re.compile(r"\beval\s*\(|new\s+Function\s*\(")
    auth_re = re.compile(
        r"(?:passport|jsonwebtoken|express-jwt|jwt\.verify|requireAuth|authMiddleware|isAuthenticated)",
        re.IGNORECASE,
    )
    admin_route_re = re.compile(r"['\"]\/admin(?:\/|['\"])")
    debug_route_re = re.compile(r"['\"]\/(?:debug|__debug)['\"\/]")
    child_re = re.compile(
        r"child_process|\.spawn\s*\(|execFile\s*\(|\.fork\s*\(|promisify\s*\(\s*exec\s*\)",
        re.IGNORECASE,
    )

    detected_stacks: list[str] = []

    for path, text in files:
        rel = path.relative_to(root)
        if path.suffix.lower() == ".py":
            if _PY_FASTAPI.search(text):
                inferences.append(
                    {
                        "kind": "python_web_framework",
                        "message": f"Padrões FastAPI/APIRouter/`@app.*` em `{rel}`",
                        "evidence": "fastapi|APIRouter|@app.",
                        "confidence": "medium",
                        "inference_source": "regex_heuristic",
                        "stack_hint": "python_fastapi",
                    }
                )
            elif _PY_FLASK.search(text):
                inferences.append(
                    {
                        "kind": "python_web_framework",
                        "message": f"Padrões Flask/Blueprint/`@app.route` em `{rel}`",
                        "evidence": "Flask|Blueprint|@app.route",
                        "confidence": "medium",
                        "inference_source": "regex_heuristic",
                        "stack_hint": "python_flask",
                    }
                )
            if _PY_UVICORN.search(text):
                inferences.append(
                    {
                        "kind": "python_asgi_server",
                        "message": f"Referência a servidor ASGI (uvicorn/hypercorn) em `{rel}`",
                        "evidence": "uvicorn|hypercorn",
                        "confidence": "low",
                        "inference_source": "regex_heuristic",
                        "stack_hint": "python_asgi",
                    }
                )
            if len(corpus_chunks) < 40:
                corpus_chunks.append(f"{rel}: {text[:400]}")
            continue

        ast_routes = collect_express_routes_ast_lite(text)
        ast_paths = {p for _, p in ast_routes}
        route_matches = list(route_re.finditer(text))
        regex_paths = {m.group(1) for m in route_matches}

        for m in route_matches:
            ev = m.group(1)[:120]
            src = "combined" if ev in ast_paths else "regex_heuristic"
            inferences.append(
                {
                    "kind": "route",
                    "message": f"Rota HTTP encontrada em `{rel}`",
                    "evidence": ev,
                    "confidence": "medium",
                    "inference_source": src,
                }
            )
        for method, apath in ast_routes:
            if apath in regex_paths:
                continue
            inferences.append(
                {
                    "kind": "route",
                    "message": f"Rota HTTP {method.upper()} (deteção AST leve) em `{rel}`",
                    "evidence": f"{method.upper()} {apath}"[:120],
                    "confidence": "medium",
                    "inference_source": "ast_lite",
                }
            )
        if multer_re.search(text):
            inferences.append(
                {
                    "kind": "upload",
                    "message": f"Possível upload de ficheiros (`multer`/upload) em `{rel}`",
                    "evidence": "multer|upload.single|upload.array",
                    "confidence": "medium",
                    "inference_source": "regex_heuristic",
                }
            )
        if session_re.search(text):
            inferences.append(
                {
                    "kind": "session",
                    "message": f"Sessão/cookies prováveis em `{rel}`",
                    "evidence": "express-session",
                    "confidence": "medium",
                    "inference_source": "regex_heuristic",
                }
            )
        if fetch_re.search(text):
            inferences.append(
                {
                    "kind": "external_fetch",
                    "message": f"Chamadas HTTP externas (axios/fetch) em `{rel}`",
                    "evidence": "axios|fetch",
                    "confidence": "low",
                    "inference_source": "regex_heuristic",
                }
            )
        if eval_re.search(text):
            inferences.append(
                {
                    "kind": "dangerous_eval",
                    "message": f"Possível eval/exec em `{rel}` — rever risco de injeção",
                    "evidence": "eval|exec",
                    "confidence": "high",
                    "inference_source": "regex_heuristic",
                }
            )
        if auth_re.search(text):
            inferences.append(
                {
                    "kind": "auth_middleware",
                    "message": f"Padrões de autenticação/autorização em `{rel}`",
                    "evidence": "passport|jwt|authMiddleware",
                    "confidence": "low",
                    "inference_source": "regex_heuristic",
                }
            )
        if admin_route_re.search(text):
            inferences.append(
                {
                    "kind": "admin_route",
                    "message": f"Possível rota ou prefixo `/admin` em `{rel}`",
                    "evidence": "/admin",
                    "confidence": "medium",
                    "inference_source": "regex_heuristic",
                }
            )
        if debug_route_re.search(text):
            inferences.append(
                {
                    "kind": "debug_route",
                    "message": f"Possível rota de debug em `{rel}` — rever exposição",
                    "evidence": "/debug|__debug",
                    "confidence": "low",
                    "inference_source": "regex_heuristic",
                }
            )
        if child_re.search(text):
            inferences.append(
                {
                    "kind": "child_process",
                    "message": f"Uso de child_process/spawn/execFile em `{rel}` — rever superfície de comando",
                    "evidence": "child_process|spawn|execFile",
                    "confidence": "medium",
                    "inference_source": "regex_heuristic",
                }
            )
        for m in router_mount_re.finditer(text):
            inferences.append(
                {
                    "kind": "middleware_mount",
                    "message": f"Montagem `use('{m.group(1)}')` em `{rel}`",
                    "evidence": m.group(1)[:120],
                    "confidence": "low",
                    "inference_source": "regex_heuristic",
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
                    "inference_source": "convention",
                }
            )

    modeling_hints: list[dict[str, Any]] = []
    kinds_present = {inf.get("kind") for inf in unique}
    if "upload" in kinds_present:
        modeling_hints.append(
            {
                "target": "data_flow",
                "hint": "Marcar fluxos com `supports_file_upload: true` onde o código trata multipart.",
                "confidence": "low",
                "basis": "repo_inference:upload",
            }
        )
    if "session" in kinds_present:
        modeling_hints.append(
            {
                "target": "trust_boundary",
                "hint": "Garantir boundary explícito entre cliente e camada de sessão/cookies.",
                "confidence": "low",
                "basis": "repo_inference:session",
            }
        )
    if "external_fetch" in kinds_present:
        modeling_hints.append(
            {
                "target": "data_flow",
                "hint": "Marcar `supports_external_fetch: true` e rever SSRF no modelo.",
                "confidence": "low",
                "basis": "repo_inference:external_fetch",
            }
        )
    if "admin_route" in kinds_present or "debug_route" in kinds_present:
        modeling_hints.append(
            {
                "target": "component",
                "hint": "Componentes admin/debug devem refletir `privilege_level` / segregação no threat model.",
                "confidence": "medium",
                "basis": "repo_inference:admin_or_debug",
            }
        )

    import_signals_corpus_snippets: list[str] = []
    for inf in unique[:24]:
        msg = inf.get("message")
        if isinstance(msg, str) and msg:
            import_signals_corpus_snippets.append(msg[:200])

    stack_set: set[str] = set()
    if any(p.suffix.lower() in {".js", ".mjs", ".cjs", ".ts", ".tsx"} for p, _ in files):
        stack_set.add("javascript_family")
    if any(p.suffix.lower() == ".py" for p, _ in files):
        stack_set.add("python_family")
    for inf in unique:
        sh = inf.get("stack_hint")
        if isinstance(sh, str) and sh:
            stack_set.add(sh)
    detected_stacks = sorted(stack_set)

    if any(inf.get("stack_hint") == "python_fastapi" for inf in unique):
        modeling_hints.append(
            {
                "target": "trust_boundary",
                "hint": "Modelar boundary explícito entre cliente/API e workers Python quando usar FastAPI.",
                "confidence": "low",
                "basis": "repo_inference:python_fastapi",
            }
        )

    return {
        "root": str(root),
        "files_scanned": len(files),
        "inferences": unique[:80],
        "directory_hints": dir_hints,
        "corpus_excerpt": "\n\n".join(corpus_chunks)[:8000],
        "modeling_hints": modeling_hints[:20],
        "import_signals_corpus_snippets": import_signals_corpus_snippets,
        "detected_stacks": detected_stacks,
    }
