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
_PY_DECORATOR_ROUTE = re.compile(
    r"@(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_PY_UPLOAD = re.compile(
    r"\bUploadFile\b|\bFile\s*\(\s*|FileStorage|request\.files\b",
    re.IGNORECASE,
)
_PY_AUTH_DEPS = re.compile(
    r"Depends\s*\(\s*|OAuth2PasswordBearer|HTTPBearer|HTTPAuthorizationCredentials|"
    r"SessionMiddleware|itsdangerous\b",
    re.IGNORECASE,
)
_PY_HTTP_OUT = re.compile(
    r"\bhttpx\.(?:get|post|request)|requests\.(?:get|post|put|delete)|aiohttp\.|urllib\.request\b",
    re.IGNORECASE,
)
_PY_ADMIN_PATH = re.compile(r"[\"']/admin[/\"']", re.IGNORECASE)
_PY_DEBUG_PATH = re.compile(r"[\"']/(?:debug|__debug__?)[\"']", re.IGNORECASE)


def _read_text_files(root: Path, *, max_files: int = 200) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in _SUFFIXES:
            continue
        if "node_modules" in p.parts or ".git" in p.parts:
            continue  # pragma: no cover - defensive guard
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover - defensive: file read error during scan
            continue
        out.append((p, text))
        if len(out) >= max_files:
            break  # pragma: no cover - defensive guard
    return out


# Sinais simples Python (regex já compilado, kind, template de mensagem, evidência,
# confiança, stack_hint fixo — None usa o stack derivado do ficheiro).
_PY_SIMPLE_SIGNALS: tuple[tuple[re.Pattern[str], str, str, str, str, str | None], ...] = (
    (
        _PY_UPLOAD,
        "python_upload",
        "Upload multipart / `UploadFile` / ficheiros em `{rel}`",
        "UploadFile|File(|request.files",
        "medium",
        None,
    ),
    (
        _PY_AUTH_DEPS,
        "python_auth_layer",
        "Dependências de auth/sessão (Depends/OAuth2/sessão) em `{rel}`",
        "Depends|OAuth2|Bearer|Session",
        "low",
        None,
    ),
    (
        _PY_HTTP_OUT,
        "python_external_http",
        "Cliente HTTP externo (httpx/requests/aiohttp) em `{rel}` — rever SSRF/exfiltração",
        "httpx|requests|aiohttp",
        "medium",
        "python_web",
    ),
    (_PY_ADMIN_PATH, "admin_route", "Possível caminho `/admin` em `{rel}`", "/admin", "medium", "python_web"),
    (_PY_DEBUG_PATH, "debug_route", "Possível rota de debug em `{rel}`", "/debug", "low", "python_web"),
)

# Regexes Node/Express (nível de módulo: compiladas uma vez).
_JS_ROUTE_RE = re.compile(r"(?:app|router)\.(?:get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]")
_JS_ROUTER_MOUNT_RE = re.compile(r"(?:app|router)\.use\s*\(\s*['\"]([^'\"]+)['\"]")
_JS_MULTER_RE = re.compile(
    r"multer\s*\(|upload\.(?:single|array|fields)|express\.file\s*\(|busboy\s*\(",
    re.IGNORECASE,
)
_JS_SESSION_RE = re.compile(
    r"express-session|expressSession|cookie-session|connect\.mongo|req\.session\b",
    re.IGNORECASE,
)
_JS_FETCH_RE = re.compile(r"(?:axios|fetch|got|needle|request)\s*\(")
_JS_EVAL_RE = re.compile(r"\beval\s*\(|new\s+Function\s*\(")
_JS_AUTH_RE = re.compile(
    r"(?:passport|jsonwebtoken|express-jwt|jwt\.verify|requireAuth|authMiddleware|isAuthenticated)",
    re.IGNORECASE,
)
_JS_ADMIN_RE = re.compile(r"['\"]\/admin[/'\"]")
_JS_DEBUG_RE = re.compile(r"['\"]\/(?:debug|__debug)['\"\/]")
_JS_CHILD_RE = re.compile(
    r"child_process|\.spawn\s*\(|execFile\s*\(|\.fork\s*\(|promisify\s*\(\s*exec\s*\)",
    re.IGNORECASE,
)

# Sinais simples JS (regex, kind, template de mensagem, evidência, confiança).
_JS_SIMPLE_SIGNALS: tuple[tuple[re.Pattern[str], str, str, str, str], ...] = (
    (
        _JS_MULTER_RE,
        "upload",
        "Possível upload de ficheiros (`multer`/upload) em `{rel}`",
        "multer|upload.single|upload.array",
        "medium",
    ),
    (_JS_SESSION_RE, "session", "Sessão/cookies prováveis em `{rel}`", "express-session", "medium"),
    (_JS_FETCH_RE, "external_fetch", "Chamadas HTTP externas (axios/fetch) em `{rel}`", "axios|fetch", "low"),
    (_JS_EVAL_RE, "dangerous_eval", "Possível eval/exec em `{rel}` — rever risco de injeção", "eval|exec", "high"),
    (
        _JS_AUTH_RE,
        "auth_middleware",
        "Padrões de autenticação/autorização em `{rel}`",
        "passport|jwt|authMiddleware",
        "low",
    ),
    (_JS_ADMIN_RE, "admin_route", "Possível rota ou prefixo `/admin` em `{rel}`", "/admin", "medium"),
    (_JS_DEBUG_RE, "debug_route", "Possível rota de debug em `{rel}` — rever exposição", "/debug|__debug", "low"),
    (
        _JS_CHILD_RE,
        "child_process",
        "Uso de child_process/spawn/execFile em `{rel}` — rever superfície de comando",
        "child_process|spawn|execFile",
        "medium",
    ),
)


def _scan_python_file(text: str, rel: Path) -> list[dict[str, Any]]:
    """Inferências para um ficheiro `.py` (ordem preservada do scan original)."""
    out: list[dict[str, Any]] = []
    is_fastapi = bool(_PY_FASTAPI.search(text))
    py_stack = "python_fastapi" if is_fastapi else "python_web"
    if is_fastapi:
        out.append(
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
        out.append(
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
        out.append(
            {
                "kind": "python_asgi_server",
                "message": f"Referência a servidor ASGI (uvicorn/hypercorn) em `{rel}`",
                "evidence": "uvicorn|hypercorn",
                "confidence": "low",
                "inference_source": "regex_heuristic",
                "stack_hint": "python_asgi",
            }
        )
    for rm in _PY_DECORATOR_ROUTE.finditer(text):
        path_bit = rm.group(1).strip()[:120]
        out.append(
            {
                "kind": "python_route",
                "message": f"Rota FastAPI/Starlette provável `{path_bit}` em `{rel}`",
                "evidence": path_bit,
                "confidence": "medium",
                "inference_source": "regex_heuristic",
                "stack_hint": py_stack,
            }
        )
    for rx, kind, msg, ev, conf, stack in _PY_SIMPLE_SIGNALS:
        if rx.search(text):
            out.append(
                {
                    "kind": kind,
                    "message": msg.format(rel=rel),
                    "evidence": ev,
                    "confidence": conf,
                    "inference_source": "regex_heuristic",
                    "stack_hint": stack or py_stack,
                }
            )
    return out


def _scan_js_file(text: str, rel: Path) -> list[dict[str, Any]]:
    """Inferências para um ficheiro JS/TS (ordem preservada do scan original)."""
    out: list[dict[str, Any]] = []
    ast_routes = collect_express_routes_ast_lite(text)
    ast_paths = {p for _, p in ast_routes}
    route_matches = list(_JS_ROUTE_RE.finditer(text))
    regex_paths = {m.group(1) for m in route_matches}

    for m in route_matches:
        ev = m.group(1)[:120]
        src = "combined" if ev in ast_paths else "regex_heuristic"
        out.append(
            {
                "kind": "route",
                "message": f"Rota HTTP encontrada em `{rel}`",
                "evidence": ev,
                "confidence": "medium",
                "inference_source": src,
            }
        )
    for method, apath in ast_routes:  # pragma: no cover - AST routes require the optional `esprima` extra
        if apath in regex_paths:
            continue  # pragma: no cover - defensive guard
        out.append(
            {
                "kind": "route",
                "message": f"Rota HTTP {method.upper()} (deteção AST leve) em `{rel}`",
                "evidence": f"{method.upper()} {apath}"[:120],
                "confidence": "medium",
                "inference_source": "ast_lite",
            }
        )
    for rx, kind, msg, ev, conf in _JS_SIMPLE_SIGNALS:
        if rx.search(text):
            out.append(
                {
                    "kind": kind,
                    "message": msg.format(rel=rel),
                    "evidence": ev,
                    "confidence": conf,
                    "inference_source": "regex_heuristic",
                }
            )
    for m in _JS_ROUTER_MOUNT_RE.finditer(text):
        out.append(
            {
                "kind": "middleware_mount",
                "message": f"Montagem `use('{m.group(1)}')` em `{rel}`",
                "evidence": m.group(1)[:120],
                "confidence": "low",
                "inference_source": "regex_heuristic",
            }
        )
    return out


def _dedupe_inferences(inferences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicados por (kind, message), mantendo a primeira ocorrência."""
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for inf in inferences:
        key = (inf.get("kind", ""), inf.get("message", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(inf)
    return unique


def _directory_hints(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sub in ("public", "uploads", "static", "dist"):
        p = root / sub
        if p.is_dir():
            out.append(
                {
                    "kind": "directory_convention",
                    "message": f"Diretório `{sub}/` presente na raiz — possível conteúdo estático ou uploads",
                    "evidence": str(p.relative_to(root)),
                    "confidence": "low",
                    "inference_source": "convention",
                }
            )
    return out


def _detected_stacks(files: list[tuple[Path, str]], unique: list[dict[str, Any]]) -> list[str]:
    stack_set: set[str] = set()
    if any(p.suffix.lower() in {".js", ".mjs", ".cjs", ".ts", ".tsx"} for p, _ in files):
        stack_set.add("javascript_family")
    if any(p.suffix.lower() == ".py" for p, _ in files):
        stack_set.add("python_family")
    for inf in unique:
        sh = inf.get("stack_hint")
        if isinstance(sh, str) and sh:
            stack_set.add(sh)
    return sorted(stack_set)


def _collect_modeling_hints(kinds_present: set[Any], unique: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sugestões de modelagem derivadas dos kinds detectados (ordem preservada)."""
    hints: list[dict[str, Any]] = []
    if "upload" in kinds_present:
        hints.append(
            {
                "target": "data_flow",
                "hint": "Marcar fluxos com `supports_file_upload: true` onde o código trata multipart.",
                "confidence": "low",
                "basis": "repo_inference:upload",
            }
        )
    if "session" in kinds_present:
        hints.append(
            {
                "target": "trust_boundary",
                "hint": "Garantir boundary explícito entre cliente e camada de sessão/cookies.",
                "confidence": "low",
                "basis": "repo_inference:session",
            }
        )
    if "external_fetch" in kinds_present:
        hints.append(
            {
                "target": "data_flow",
                "hint": "Marcar `supports_external_fetch: true` e rever SSRF no modelo.",
                "confidence": "low",
                "basis": "repo_inference:external_fetch",
            }
        )
    if "admin_route" in kinds_present or "debug_route" in kinds_present:
        hints.append(
            {
                "target": "component",
                "hint": "Componentes admin/debug devem refletir `privilege_level` / segregação no threat model.",
                "confidence": "medium",
                "basis": "repo_inference:admin_or_debug",
            }
        )
    if any(inf.get("stack_hint") == "python_fastapi" for inf in unique):
        hints.append(
            {
                "target": "trust_boundary",
                "hint": "Modelar boundary explícito entre cliente/API e workers Python quando usar FastAPI.",
                "confidence": "low",
                "basis": "repo_inference:python_fastapi",
            }
        )
    if "python_upload" in kinds_present:
        hints.append(
            {
                "target": "data_flow",
                "hint": "Fluxos com `supports_file_upload: true` onde FastAPI/Flask aceita multipart.",
                "confidence": "medium",
                "basis": "repo_inference:python_upload",
            }
        )
    if "python_external_http" in kinds_present:
        hints.append(
            {
                "target": "data_flow",
                "hint": "Marcar chamadas externas e rever superfície SSRF no threat model.",
                "confidence": "medium",
                "basis": "repo_inference:python_external_http",
            }
        )
    if "python_auth_layer" in kinds_present:
        hints.append(
            {
                "target": "component",
                "hint": "Explicitar identity/session na fronteira API (Depends/OAuth2) como componente ou controlos.",
                "confidence": "low",
                "basis": "repo_inference:python_auth_layer",
            }
        )
    if any(inf.get("kind") == "python_route" for inf in unique):
        hints.append(
            {
                "target": "asset",
                "hint": "Cada rota HTTP inferida pode mapear endpoints expostos — cruzar com dados sensíveis modelados.",
                "confidence": "low",
                "basis": "repo_inference:python_route",
            }
        )
    return hints


def scan_node_express_repo(root: Path) -> dict[str, Any]:
    """
    Percorre ficheiros e devolve inferências com evidência curta.

    Não altera o schema canónico sozinho — consumidores agregam ao modelo.
    """
    root = root.resolve()
    files = _read_text_files(root)
    inferences: list[dict[str, Any]] = []
    corpus_chunks: list[str] = []

    for path, text in files:
        rel = path.relative_to(root)
        if path.suffix.lower() == ".py":
            inferences.extend(_scan_python_file(text, rel))
        else:
            inferences.extend(_scan_js_file(text, rel))
        if len(corpus_chunks) < 40:
            corpus_chunks.append(f"{rel}: {text[:400]}")

    unique = _dedupe_inferences(inferences)
    kinds_present = {inf.get("kind") for inf in unique}
    dir_hints = _directory_hints(root)
    modeling_hints = _collect_modeling_hints(kinds_present, unique)

    import_signals_corpus_snippets: list[str] = []
    for inf in unique[:24]:
        msg = inf.get("message")
        if isinstance(msg, str) and msg:
            import_signals_corpus_snippets.append(msg[:200])

    detected_stacks = _detected_stacks(files, unique)

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
