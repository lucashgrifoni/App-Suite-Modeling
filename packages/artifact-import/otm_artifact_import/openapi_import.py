"""
Importação assistida a partir de OpenAPI 3.x ou Swagger 2.x.

Heurísticas modestas: superfície agregada, exposição via `servers`/`host`, pistas de auth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otm_core_schema import Asset, Component, DataFlow, TrustBoundary
from otm_core_schema.enums import AssetKind, ComponentKind, IndustrySector, SystemType

from otm_artifact_import._yamljson import load_object_from_text
from otm_artifact_import.ai_import_corpus import build_openapi_import_signals_corpus
from otm_artifact_import.builders import assemble_draft, slug_id
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord

_HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "trace"},
)


def _collect_servers_v3(data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for s in data.get("servers") or []:
        if isinstance(s, dict) and s.get("url"):
            out.append(str(s["url"]).strip())
    return out


def _collect_servers_v2(data: dict[str, Any]) -> list[str]:
    host = (data.get("host") or "").strip()
    base = (data.get("basePath") or "").strip() or "/"
    schemes = data.get("schemes") or ["https"]
    if not host:
        return []
    out: list[str] = []
    for sch in schemes:
        if isinstance(sch, str):
            url = f"{sch}://{host}{base}" if base.startswith("/") else f"{sch}://{host}/{base}"
            out.append(url)
    return out


def _security_hints_v3(data: dict[str, Any]) -> tuple[bool, list[str]]:
    comp = (data.get("components") or {}) if isinstance(data.get("components"), dict) else {}
    schemes = comp.get("securitySchemes") or {}
    if not isinstance(schemes, dict):
        return False, []
    names: list[str] = []
    for key, sch in schemes.items():
        if not isinstance(sch, dict):
            continue
        t = str(sch.get("type") or "")
        names.append(f"{key}:{t}" if t else str(key))
    return bool(names), names


def _security_hints_v2(data: dict[str, Any]) -> tuple[bool, list[str]]:
    sdef = data.get("securityDefinitions") or {}
    if not isinstance(sdef, dict):
        return False, []
    return bool(sdef), [str(k) for k in sdef.keys()]


def _root_security_required(data: dict[str, Any]) -> bool:
    return bool(data.get("security"))


def _operation_security_required(path_item: dict[str, Any]) -> bool | None:
    if not isinstance(path_item, dict):
        return None
    if "security" in path_item:
        return bool(path_item.get("security"))
    return None


def _count_operations(paths: dict[str, Any] | None) -> tuple[int, list[str]]:
    if not paths or not isinstance(paths, dict):
        return 0, []
    detail: list[str] = []
    n = 0
    for pth, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            # YAML 1.1 maps bare keys like on/off/yes/no to bool and numeric
            # keys to int; guard before calling str methods on the path-item key.
            if not isinstance(method, str):
                continue
            lm = method.lower()
            if lm not in _HTTP_METHODS or not isinstance(op, dict):
                continue
            op_id = op.get("operationId") or f"{lm} {pth}"
            detail.append(str(op_id))
            n += 1
    return n, detail[:40]


def _detect_openapi_header(data: dict[str, Any]) -> tuple[str, list[str], bool, list[str], str, str | None]:
    """Devolve (version, servers, has_auth, scheme_names, title, unknown_msg-ou-None) por dialecto."""
    if "openapi" in data:
        has_auth, scheme_names = _security_hints_v3(data)
        title = str((data.get("info") or {}).get("title") or "API OpenAPI")
        return str(data.get("openapi") or ""), _collect_servers_v3(data), has_auth, scheme_names, title, None
    if data.get("swagger"):
        has_auth, scheme_names = _security_hints_v2(data)
        title = str((data.get("info") or {}).get("title") or "API Swagger")
        return str(data.get("swagger") or "2.0"), _collect_servers_v2(data), has_auth, scheme_names, title, None
    return (
        "?",
        [],
        False,
        [],
        "API (formato desconhecido)",
        "Chave raiz 'openapi' ou 'swagger' não encontrada — não é um OpenAPI/Swagger reconhecido.",
    )


def _infer_authenticated(data: dict[str, Any], paths: dict[str, Any]) -> bool | None:
    """Autenticação efetiva por operação: a declaração mais específica ganha.

    A precedência é a que a especificação OpenAPI define, e não a inversa: `security` numa
    operação **substitui** o do documento, e uma lista vazia remove a exigência para essa
    operação. Consultar a raiz primeiro — o que esta função fazia, e a sua docstring declarava
    como regra — devolvia `True` para uma spec cuja raiz exige `bearerAuth` e cujas operações
    **todas** declaram `security: []`, isto é, uma API inteiramente aberta. Indistinguível da
    spec em que as operações herdam o requisito, e errada na direção que esconde exposição.

    `all`, e não `any`: um único caminho aberto basta para a API não ser toda autenticada.
    Ausência de qualquer declaração continua a ser `None` — não saber não é o mesmo que saber
    que não há, e só a renúncia explícita vale como resposta negativa.
    """
    root = _root_security_required(data)
    effective: list[bool] = []
    declared = False

    for item in paths.values():
        if not isinstance(item, dict):
            continue  # pragma: no cover - defensive guard
        path_level = _operation_security_required(item)
        for method, op in item.items():
            if not (isinstance(method, str) and method.lower() in _HTTP_METHODS and isinstance(op, dict)):
                continue
            if "security" in op:
                declared = True
                effective.append(bool(op.get("security")))
            elif path_level is not None:
                declared = True
                effective.append(path_level)
            else:
                effective.append(root)

    if not effective:
        return True if root else None
    if not declared and not root:
        return None
    return all(effective)


def import_openapi_text(text: str, *, filename: str = "openapi.yaml") -> ArtifactImportResult:
    data = load_object_from_text(text)
    inferences: list[InferenceRecord] = []
    unknowns: list[str] = []

    version, servers, has_auth, scheme_names, title, header_unknown = _detect_openapi_header(data)
    if header_unknown:
        unknowns.append(header_unknown)

    paths = data.get("paths")
    if not isinstance(paths, dict):
        paths = {}
        unknowns.append("Secção 'paths' ausente ou inválida — nenhuma operação listada.")
    op_count, op_sample = _count_operations(paths)

    inf_idx = 0

    def inf(
        message: str,
        confidence: str,
        *,
        related: list[str] | None = None,
    ) -> None:
        nonlocal inf_idx
        inf_idx += 1
        inferences.append(
            InferenceRecord(
                id=f"inf_{inf_idx:03d}",
                message=message,
                confidence=confidence,
                source="openapi",
                related_component_ids=list(related or []),
            )
        )

    cid_internet = "ext_http_clients"
    cid_api = slug_id(title.replace(" ", "_"), prefix="api")
    tb_ext = "tb_public_exposure"
    tb_app = "tb_application"

    components = [
        Component(
            id=cid_internet,
            name="Clientes HTTP (exterior)",
            kind=ComponentKind.EXTERNAL_ENTITY,
            description="Chamadores externos inferidos como entidade agregada; refinamento manual recomendado.",
            in_trust_boundary=tb_ext,
            metadata={"artifact": filename, "import_kind": "openapi"},
        ),
        Component(
            id=cid_api,
            name=title,
            kind=ComponentKind.PROCESS,
            description=(
                f"Superfície de API agregada a partir do OpenAPI (versão: {version}). "
                f"Operações identificadas: {op_count}."
            ),
            technology="REST/OpenAPI",
            in_trust_boundary=tb_app,
            metadata={
                "artifact": filename,
                "import_kind": "openapi",
                "operation_sample": op_sample,
            },
        ),
    ]

    flows: list[DataFlow] = []
    if op_count > 0:
        authenticated = _infer_authenticated(data, paths)

        flows.append(
            DataFlow(
                id="flow_clients_to_api",
                name="Pedidos HTTP à API",
                from_component=cid_internet,
                to_component=cid_api,
                protocol="HTTP",
                authenticated=authenticated,
                description="Fluxo agregado; cada operação em `paths` não foi modelada como componente separado.",
                metadata={"openapi_operations_count": op_count},
            )
        )
        inf(
            f"Superfície de API e {op_count} operação(ões) HTTP inferida(s) a partir de `paths` no OpenAPI.",
            "high",
            related=[cid_api],
        )
    else:
        unknowns.append("Nenhuma operação HTTP encontrada em `paths`.")

    if servers:
        vis = ", ".join(servers[:5])
        extra = f" (+{len(servers) - 5} mais)" if len(servers) > 5 else ""
        inf(
            f"Pontos de exposição provável(s) (servers/base URL): {vis}{extra}. "
            "Isto sugere fronteira pública; confirme VPN, API gateway ou rede interna.",
            "medium",
            related=[cid_internet, cid_api],
        )
    else:
        inf(
            "Sem `servers` (ou host/basePath em Swagger 2) — exposição de rede não inferida.",
            "low",
            related=[cid_api],
        )

    if has_auth:
        joined = ", ".join(scheme_names[:8])
        inf(
            f"Pistas de autenticação presentes (securitySchemes/securityDefinitions): {joined}. "
            "O desenho exacto de OAuth2/scopes não foi expandido.",
            "high",
            related=[cid_api],
        )
    else:
        inf(
            "Nenhum esquema de segurança declarado no documento — não inferir autenticação forte.",
            "medium",
            related=[cid_api],
        )

    if _root_security_required(data):
        inf(
            "Requisito global `security` no OpenAPI — operações assumidas como protegidas salvo override local.",
            "medium",
            related=[cid_api],
        )

    assets: list[Asset] = []
    if op_count:
        assets.append(
            Asset(
                id="asset_api_payloads",
                name="Payloads de API (request/response)",
                asset_kind=AssetKind.DATA,
                sensitivity="unknown",
                description="Corpos e parâmetros não foram inspeccionados campo-a-campo.",
                related_component_ids=[cid_api],
                metadata={"artifact": filename},
            )
        )
        inf(
            "Ativo genérico 'payloads de API' adicionado; classificação de dados requer revisão manual.",
            "low",
            related=[cid_api],
        )

    boundaries: list[TrustBoundary] = [
        TrustBoundary(
            id=tb_ext,
            name="Exterior / alcance rede público provável",
            description="Fronteira sugerida para chamadores além da aplicação (com base em servers e entidade externa).",
            member_component_ids=[],
        ),
        TrustBoundary(
            id=tb_app,
            name="Aplicação / zona servida",
            description="Contém o processo que implementa a API descrita.",
            member_component_ids=[],
        ),
    ]

    import_corpus = build_openapi_import_signals_corpus(data)
    return assemble_draft(
        title=f"{title} (rascunho OpenAPI)",
        summary=f"Importação assistida de OpenAPI — {op_count} operação(ões).",
        source_kind="openapi",
        system_type=SystemType.API_BACKEND,
        industry=IndustrySector.GENERIC,
        components=components,
        data_flows=flows,
        trust_boundaries=boundaries,
        assets=assets,
        inferences=inferences,
        unknowns=unknowns,
        extra_assumptions=[
            "Um único componente agrega toda a superfície REST; pode ser refinado por domínio ou tag.",
        ],
        import_signals_corpus=import_corpus or None,
    )


def import_openapi_path(path: Path) -> ArtifactImportResult:
    text = path.read_text(encoding="utf-8")
    return import_openapi_text(text, filename=path.name)
