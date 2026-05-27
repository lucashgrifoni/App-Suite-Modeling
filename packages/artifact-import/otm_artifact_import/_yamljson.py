"""Parse seguro de YAML ou JSON (conteúdo de artefactos)."""

from __future__ import annotations

import json
from typing import Any

import yaml


def load_object_from_text(text: str) -> dict[str, Any]:
    """Carrega um único objecto raiz; falha se não for dict."""
    text = text.strip()
    if not text:
        raise ValueError("Artefacto vazio.")
    try:
        if text.startswith("{"):
            data = json.loads(text)
        else:
            data = yaml.safe_load(text)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Não foi possível interpretar como YAML/JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Raiz do artefacto deve ser um objecto (mapping).")
    return data


def iter_yaml_documents(text: str):
    """Itera documentos multi-parte (ex.: manifests Kubernetes)."""
    for doc in yaml.safe_load_all(text):
        if doc is None:
            continue  # pragma: no cover - defensive: empty YAML document skipped
        if isinstance(doc, dict):
            yield doc
