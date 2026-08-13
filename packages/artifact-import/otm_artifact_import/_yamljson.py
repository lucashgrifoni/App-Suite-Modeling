"""Parse seguro de YAML ou JSON (conteúdo de artefactos)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import yaml
from otm_core_schema.io import json_loads_bounded, safe_load_all_bounded, safe_load_bounded


def load_object_from_text(text: str) -> dict[str, Any]:
    """Carrega um único objecto raiz; falha se não for dict."""
    text = text.strip()
    if not text:
        raise ValueError("Artefacto vazio.")
    try:
        if text.startswith("{"):
            # Bounded pela mesma razão que o ramo YAML, e com o mesmo tecto: `json.loads` desce
            # recursivamente e `'{"a":' * 20000` esgotava a pilha. O `RecursionError` daí não é
            # `JSONDecodeError`, escapava a este `except` e saía como 500 com o traceback
            # completo no log — o mesmo defeito que o aninhamento YAML tinha do outro lado.
            data = json_loads_bounded(text)
        else:
            # Bounded: estes ficheiros chegam por upload HTTP, tal como o documento
            # canónico. `yaml.safe_load` impede tipos arbitrários mas não limita a
            # expansão de aliases, que é o que transforma centenas de bytes em gigabytes.
            data = safe_load_bounded(text)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Não foi possível interpretar como YAML/JSON: {e}") from e
    except RecursionError as e:
        # Defesa em profundidade. Os tectos acima recusam a bomba conhecida antes de a pagar;
        # isto garante que qualquer outra forma patológica continua a ser "input do utilizador
        # está mal" (400) e não um 500 com a pilha inteira no disco.
        raise ValueError("Artefacto demasiado aninhado para ser interpretado.") from e
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
