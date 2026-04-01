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


def build_openapi_import_signals_corpus(data: dict[str, Any]) -> str:
    """Paths, tags globias e amostra de `operationId`/resumo por operação."""
    parts: list[str] = []
    paths = data.get("paths")
    path_keys: list[str] = []
    if isinstance(paths, dict):
        for pth, item in paths.items():
            path_keys.append(str(pth))
            if not isinstance(item, dict):
                continue
            for method, op in item.items():
                if method.lower() not in _HTTP_METHODS or not isinstance(op, dict):
                    continue
                oid = op.get("operationId")
                if oid:
                    parts.append(str(oid))
                summ = op.get("summary") or op.get("description")
                if isinstance(summ, str) and summ.strip():
                    parts.append(summ.strip()[:160])
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


def build_kubernetes_import_signals_corpus(docs: list[dict[str, Any]]) -> str:
    """Nomes, labels, annotations e imagens declaradas nos manifests."""
    parts: list[str] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = str(doc.get("kind") or "")
        meta = doc.get("metadata")
        if isinstance(meta, dict):
            if meta.get("name"):
                parts.append(str(meta["name"]))
            labels = meta.get("labels")
            if isinstance(labels, dict):
                for ky, val in list(labels.items())[:48]:
                    parts.append(f"{ky}={val}")
            ann = meta.get("annotations")
            if isinstance(ann, dict):
                for ky, val in list(ann.items())[:24]:
                    if any(
                        x in ky.lower()
                        for x in ("description", "sidecar", "model", "inference", "gpu", "vertex", "openai")
                    ):
                        parts.append(f"{ky}={val}")
        if kind == "Deployment":
            spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
            tmpl = spec.get("template") if isinstance(spec.get("template"), dict) else {}
            pod = tmpl.get("spec") if isinstance(tmpl.get("spec"), dict) else {}
            cnts = pod.get("containers") if isinstance(pod.get("containers"), list) else []
            for c in cnts:
                if isinstance(c, dict) and c.get("image"):
                    parts.append(str(c["image"]))
                if isinstance(c, dict) and c.get("name"):
                    parts.append(str(c["name"]))
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
    for m in _TERRAFORM_AI_MARKERS:
        if m in low:
            hits.append(m)
    for m in re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"', text):
        blob = f"{m.group(1)} {m.group(2)}".lower()
        if any(x in blob for x in _TERRAFORM_AI_MARKERS):
            hits.append(m.group(1))
            hits.append(m.group(2))
    return " ".join(dict.fromkeys(hits)).strip().lower()


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
    except yaml.YAMLError:
        docs = []

    for d in docs:
        if not isinstance(d, dict):
            continue
        if {"apiVersion", "name", "version"} <= set(d.keys()):
            # Chart.yaml provável
            for k in ("name", "version", "appVersion", "description", "type"):
                v = d.get(k)
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip()[:200])
            deps = d.get("dependencies")
            if isinstance(deps, list):
                for dep in deps[:32]:
                    if isinstance(dep, dict) and dep.get("name"):
                        parts.append(str(dep["name"]))
        else:
            # values.yaml ou outro dict: colhe chaves e alguns valores curtos
            for k, v in list(d.items())[:80]:
                parts.append(str(k))
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip()[:160])

    # fallback super simples: recolhe linhas com marcadores (sem interpretar YAML)
    low = text.lower()
    for marker in (
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
    ):
        if re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", low):
            parts.append(marker)

    # heurística para releases: nome em comentários comuns
    m = re.search(r"release(?:_name)?\\s*[:=]\\s*([a-zA-Z0-9_.-]{1,64})", text, flags=re.IGNORECASE)
    if m:
        parts.append(m.group(1))

    return " ".join(dict.fromkeys(p.strip().lower() for p in parts if str(p).strip())).strip()
