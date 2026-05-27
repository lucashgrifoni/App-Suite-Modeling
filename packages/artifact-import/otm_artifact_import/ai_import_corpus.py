"""
Texto agregado a partir de artefactos importados para reforçar `import_signals_corpus` no OTM.

Objetivo: expor paths OpenAPI, tags K8s, imagens e pistas Terraform a `AiSignalBundle` sem duplicar
parsing pesado no motor de análise.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "trace"},
)


def _append_normalized_api_surface(path_keys: list[str], parts: list[str]) -> None:
    """Normaliza paths frequentes de APIs de modelo para frases já reconhecidas por PLOT4ai."""
    blob = " ".join(path_keys).lower()
    if "embed" in blob:
        parts.append("embeddings")
    if "chat" in blob and "complet" in blob:
        parts.append("chat completion")
    if "complet" in blob and "chat" not in blob:
        parts.append("completion api")
    if "vector" in blob or "similarity" in blob:
        parts.append("vector search")
    if "inference" in blob or "predict" in blob:
        parts.append("inference")


def _openapi_op_parts(op: Any) -> list[str]:
    """Tokens de uma operação OpenAPI (`operationId` + resumo/descrição)."""
    if not isinstance(op, dict):
        return []  # pragma: no cover - defensive guard
    out: list[str] = []
    oid = op.get("operationId")
    if oid:
        out.append(str(oid))
    summ = op.get("summary") or op.get("description")
    if isinstance(summ, str) and summ.strip():
        out.append(summ.strip()[:160])
    return out


def _openapi_path_parts(paths: Any) -> tuple[list[str], list[str]]:
    """Devolve (path_keys, op_parts) percorrendo os paths/métodos OpenAPI."""
    path_keys: list[str] = []
    op_parts: list[str] = []
    if not isinstance(paths, dict):
        return path_keys, op_parts
    for pth, item in paths.items():
        path_keys.append(str(pth))
        if not isinstance(item, dict):
            continue  # pragma: no cover - defensive guard
        for method, op in item.items():
            if method.lower() in _HTTP_METHODS:
                op_parts.extend(_openapi_op_parts(op))
    return path_keys, op_parts


def build_openapi_import_signals_corpus(data: dict[str, Any]) -> str:
    """Paths, tags globias e amostra de `operationId`/resumo por operação."""
    parts: list[str] = []
    path_keys, op_parts = _openapi_path_parts(data.get("paths"))
    parts.extend(op_parts)
    parts.extend(path_keys)
    _append_normalized_api_surface(path_keys, parts)

    gtags = data.get("tags")
    if isinstance(gtags, list):
        for t in gtags:
            if isinstance(t, dict) and t.get("name"):
                parts.append(str(t["name"]))

    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    if isinstance(info, dict):
        for key in ("title", "description"):
            v = info.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip()[:200])

    return " ".join(parts).strip().lower()


def _k8s_metadata_parts(meta: Any) -> list[str]:
    """Tokens de `metadata`: name, labels e annotations relevantes a IA."""
    if not isinstance(meta, dict):
        return []
    out: list[str] = []
    if meta.get("name"):
        out.append(str(meta["name"]))
    labels = meta.get("labels")
    if isinstance(labels, dict):
        for ky, val in list(labels.items())[:48]:
            out.append(f"{ky}={val}")
    ann = meta.get("annotations")
    if isinstance(ann, dict):
        for ky, val in list(ann.items())[:24]:
            if any(
                x in ky.lower() for x in ("description", "sidecar", "model", "inference", "gpu", "vertex", "openai")
            ):
                out.append(f"{ky}={val}")
    return out


def _k8s_deployment_image_parts(doc: dict[str, Any]) -> list[str]:
    """Imagens e nomes de container de um Deployment (spec→template→spec→containers)."""
    raw_spec = doc.get("spec")
    spec: dict[str, Any] = raw_spec if isinstance(raw_spec, dict) else {}
    raw_tmpl = spec.get("template")
    tmpl: dict[str, Any] = raw_tmpl if isinstance(raw_tmpl, dict) else {}
    raw_pod = tmpl.get("spec")
    pod: dict[str, Any] = raw_pod if isinstance(raw_pod, dict) else {}
    raw_cnts = pod.get("containers")
    cnts: list[Any] = raw_cnts if isinstance(raw_cnts, list) else []
    out: list[str] = []
    for c in cnts:
        if isinstance(c, dict) and c.get("image"):
            out.append(str(c["image"]))
        if isinstance(c, dict) and c.get("name"):
            out.append(str(c["name"]))
    return out


def build_kubernetes_import_signals_corpus(docs: list[dict[str, Any]]) -> str:
    """Nomes, labels, annotations e imagens declaradas nos manifests."""
    parts: list[str] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        parts.extend(_k8s_metadata_parts(doc.get("metadata")))
        if str(doc.get("kind") or "") == "Deployment":
            parts.extend(_k8s_deployment_image_parts(doc))
    return " ".join(parts).strip().lower()


_TERRAFORM_AI_MARKERS = (
    "bedrock",
    "sagemaker",
    "openai",
    "vertex_ai",
    "googlevertex",
    "anthropic",
    "azure_openai",
    "cognitive",
    "open_ai",
    "machine_learning",
    "aiplatform",
    "generative",
    "embedding",
    "vector_search",
)


def build_terraform_import_signals_corpus(text: str) -> str:
    """Extrai tokens de blocos `resource` quando o tipo/nome/body sugere serviços de IA geridos."""
    low = text.lower()
    hits: list[str] = []
    for marker in _TERRAFORM_AI_MARKERS:
        if marker in low:
            hits.append(marker)
    for mat in re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"', text):
        blob = f"{mat.group(1)} {mat.group(2)}".lower()
        if any(x in blob for x in _TERRAFORM_AI_MARKERS):
            hits.append(mat.group(1))
            hits.append(mat.group(2))
    return " ".join(dict.fromkeys(hits)).strip().lower()


def _helm_chart_parts(d: dict[str, Any]) -> list[str]:
    """Tokens prováveis de um Chart.yaml (campos chave + nomes de dependências)."""
    out: list[str] = []
    for k in ("name", "version", "appVersion", "description", "type"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            out.append(v.strip()[:200])
    deps = d.get("dependencies")
    if isinstance(deps, list):
        for dep in deps[:32]:
            if isinstance(dep, dict) and dep.get("name"):
                out.append(str(dep["name"]))
    return out


def _helm_values_parts(d: dict[str, Any]) -> list[str]:
    """Chaves e valores curtos de um values.yaml (ou outro dict)."""
    out: list[str] = []
    for k, v in list(d.items())[:80]:
        out.append(str(k))
        if isinstance(v, str) and v.strip():
            out.append(v.strip()[:160])
    return out


_HELM_MARKERS = (
    "openai",
    "anthropic",
    "bedrock",
    "vertex",
    "embedding",
    "embeddings",
    "vector",
    "rag",
    "llm",
    "chat completion",
    "function calling",
    "tool-use",
    "model provider",
)


def _helm_marker_parts(low: str) -> list[str]:
    """Marcadores de IA encontrados como tokens isolados no texto."""
    out: list[str] = []
    for marker in _HELM_MARKERS:
        if re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", low):
            out.append(marker)
    return out


def build_helm_import_signals_corpus(text: str) -> str:
    """
    Extrai sinais de Helm sem parser pesado:
    - Chart.yaml: name, version, appVersion, dependencies[*].name
    - values.yaml (ou similares): chaves relevantes e strings marcadoras

    A saída é texto simples para `import_signals_corpus`.
    """
    parts: list[str] = []
    # tenta carregar múltiplos docs YAML (Chart.yaml + values.yaml concatenados)
    try:
        docs = [d for d in yaml.safe_load_all(text) if isinstance(d, dict)]
    except yaml.YAMLError:  # pragma: no cover - defensive: malformed manifest tolerated
        docs = []

    for d in docs:
        if not isinstance(d, dict):
            continue  # pragma: no cover - defensive guard
        if {"apiVersion", "name", "version"} <= set(d.keys()):
            parts.extend(_helm_chart_parts(d))
        else:
            parts.extend(_helm_values_parts(d))

    # fallback super simples: recolhe linhas com marcadores (sem interpretar YAML)
    parts.extend(_helm_marker_parts(text.lower()))

    # heurística para releases: nome em comentários comuns
    m = re.search(r"release(?:_name)?\\s*[:=]\\s*([a-z0-9_.-]{1,64})", text, flags=re.IGNORECASE)
    if m:
        parts.append(m.group(1))

    return " ".join(dict.fromkeys(p.strip().lower() for p in parts if str(p).strip())).strip()
