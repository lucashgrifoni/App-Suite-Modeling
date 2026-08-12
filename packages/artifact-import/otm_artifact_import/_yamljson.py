"""Parse seguro de YAML ou JSON (conteúdo de artefactos)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import yaml
from otm_core_schema.io import safe_load_all_bounded, safe_load_bounded


def load_object_from_text(text: str) -> dict[str, Any]:
    """Carrega um único objecto raiz; falha se não for dict."""
    text = text.strip()
    if not text:
        raise ValueError("Artefacto vazio.")
    try:
        if text.startswith("{"):
            data = json.loads(text)
        else:
            # Bounded: estes ficheiros chegam por upload HTTP, tal como o documento
            # canónico. `yaml.safe_load` impede tipos arbitrários mas não limita a
            # expansão de aliases, que é o que transforma centenas de bytes em gigabytes.
            data = safe_load_bounded(text)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Não foi possível interpretar como YAML/JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Raiz do artefacto deve ser um objecto (mapping).")
    return data


def iter_yaml_documents(text: str) -> Iterator[dict[str, Any]]:
    """Itera documentos multi-parte (ex.: manifests Kubernetes).

    O erro do parser é traduzido para `ValueError`, tal como em `load_object_from_text`. Quem
    chama — a rota HTTP e o CLI — só sabe mapear `ValueError` para "input do utilizador está
    mal"; uma `yaml.YAMLError` a escapar daqui dava 500 INTERNAL_ERROR para o mesmo ficheiro
    malformado a que o import de OpenAPI já respondia 400.
    """
    try:
        # Bounded, e com o tecto partilhado por todo o stream: por documento, bastaria
        # repetir a mesma bomba depois de cada `---` para multiplicar o custo mantendo
        # cada parte dentro do limite.
        docs = safe_load_all_bounded(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Não foi possível interpretar como YAML/JSON: {e}") from e
    for doc in docs:
        if doc is None:
            continue  # pragma: no cover - defensive: empty YAML document skipped
        if isinstance(doc, dict):
            yield doc
