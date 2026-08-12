"""Serialização YAML/JSON do documento canônico — sem lógica de negócio."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import Node

from otm_core_schema.document import ThreatModelDocument

#: Tecto de bytes para um `.otm.yaml` lido do disco. Deliberadamente generoso — o maior
#: documento real deste repositório tem ~300 KB — porque isto é uma rede de segurança contra um
#: ficheiro absurdo, não uma opinião sobre o tamanho de um modelo. Override:
#: variável de ambiente `OTM_MAX_DOCUMENT_BYTES`.
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
ENV_MAX_DOCUMENT_BYTES = "OTM_MAX_DOCUMENT_BYTES"

#: Tecto de nós **expandidos** ao compor o YAML.
#:
#: O limite de bytes acima não protege contra o ataque real. `yaml.safe_load` resolve um alias
#: partilhando o nó de destino, por isso um ficheiro de ~600 bytes com sete níveis de aliases
#: encadeados carrega-se em milissegundos; a factura só chega quando alguém serializa o
#: documento (`otm export`), e aí são centenas de MB de saída e gigabytes de RSS. É o clássico
#: *billion laughs*, e cada linha extra multiplica o custo pelo fan-out.
#:
#: Contamos o custo *expandido* de cada alias durante a composição e paramos antes de a
#: expansão ser paga. 500k nós dão ~38x de folga sobre o maior documento real conhecido.
#: Override: variável de ambiente `OTM_MAX_YAML_NODES`.
MAX_YAML_EXPANDED_NODES = 500_000
ENV_MAX_YAML_EXPANDED_NODES = "OTM_MAX_YAML_NODES"


def _limit_from_env(name: str, default: int) -> int:
    """Lê o override em cada chamada — assim um teste ou um runner pode ajustá-lo sem reimportar."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}.")
    return value


class _BoundedSafeLoader(yaml.SafeLoader):
    """`SafeLoader` que contabiliza o custo expandido dos aliases e desiste a tempo."""

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self._max_expanded = _limit_from_env(ENV_MAX_YAML_EXPANDED_NODES, MAX_YAML_EXPANDED_NODES)
        self._expanded = 0
        # id(nó) -> custo expandido do sub-árvore. Usar `id` é seguro aqui porque todos os nós
        # compostos ficam vivos até ao fim (pendurados no pai ou em `self.anchors`), logo o
        # id não é reciclado durante a composição; `_pinned` garante-o mesmo assim.
        self._cost: dict[int, int] = {}
        self._pinned: list[Node] = []

    def compose_node(self, parent: Node | None, index: int) -> Node | None:
        is_alias = self.check_event(yaml.AliasEvent)
        before = self._expanded
        node = super().compose_node(parent, index)
        if node is None:  # pragma: no cover - defensive: o composer devolve sempre um nó aqui
            return None
        if is_alias:
            cost = self._cost.get(id(node))
            if cost is None:
                # A âncora ainda estava a ser composta quando o alias apareceu (`&r [*r]`):
                # o grafo é recursivo. Nenhum documento canónico tem esta forma e expandi-lo
                # não termina, por isso recusa-se aqui em vez de rebentar na serialização.
                raise ValueError("YAML alias recursivo não é suportado no documento canónico.")
            self._expanded += cost
        else:
            # Os filhos já se contaram a si próprios na recursão acima; falta este nó.
            self._expanded += 1
            self._cost[id(node)] = self._expanded - before
            self._pinned.append(node)
        if self._expanded > self._max_expanded:
            raise ValueError(
                f"YAML alias expansion exceeds {self._max_expanded} nodes "
                f"(override with {ENV_MAX_YAML_EXPANDED_NODES})."
            )
        return node


def load_document_from_dict(data: dict[str, Any]) -> ThreatModelDocument:
    return ThreatModelDocument.model_validate(data)


def _safe_load_bounded(text: str) -> Any:
    """Equivalente a `yaml.safe_load`, com o tecto de expansão de aliases aplicado.

    Instancia-se o loader à mão em vez de usar `yaml.load(..., Loader=...)`: a construção é
    exactamente a do `SafeLoader` (nenhum tipo Python arbitrário é construído), e evita-se a
    forma `yaml.load` que os scanners tratam sempre como insegura.
    """
    loader = _BoundedSafeLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def safe_load_bounded(text: str) -> Any:
    """`yaml.safe_load` com o tecto de expansão de aliases aplicado.

    Público porque o documento canónico não é a única entrada não confiável: os importadores
    de artefactos (`otm_artifact_import`) recebem ficheiros carregados por HTTP e precisam do
    mesmo tecto. `yaml.safe_load` impede a construção de tipos Python arbitrários mas não
    limita a expansão de aliases, que é o que transforma centenas de bytes em gigabytes.
    """
    return _safe_load_bounded(text)


def safe_load_all_bounded(text: str) -> list[Any]:
    """Idem para streams multi-documento (ex.: manifests Kubernetes com `---`).

    O tecto é partilhado por todo o stream, não por documento: senão bastaria repetir a mesma
    bomba N vezes para multiplicar o custo por N mantendo cada documento dentro do limite.
    Devolve uma lista em vez de um gerador para que o limite seja aplicado — e o `ValueError`
    levantado — no momento da chamada, e não a meio da iteração de quem chama.
    """
    loader = _BoundedSafeLoader(text)
    try:
        out: list[Any] = []
        while loader.check_data():
            out.append(loader.get_data())
        return out
    finally:
        loader.dispose()


def load_document_from_yaml(text: str) -> ThreatModelDocument:
    data = _safe_load_bounded(text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return ThreatModelDocument.model_validate(data)


def load_document_from_yaml_path(path: Path | str) -> ThreatModelDocument:
    p = Path(path)
    limit = _limit_from_env(ENV_MAX_DOCUMENT_BYTES, MAX_DOCUMENT_BYTES)
    size = p.stat().st_size
    if size > limit:
        raise ValueError(
            f"document file is {size} bytes; the limit is {limit} bytes (override with {ENV_MAX_DOCUMENT_BYTES})."
        )
    return load_document_from_yaml(p.read_text(encoding="utf-8"))


def dump_document_to_yaml(document: ThreatModelDocument) -> str:
    # default_flow_style=False para legibilidade humana (TaC)
    data = document.model_dump(mode="json", exclude_none=True, by_alias=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


def dump_document_to_json(document: ThreatModelDocument, *, indent: int | None = 2) -> str:
    return document.model_dump_json(exclude_none=True, indent=indent, by_alias=True)


def json_schema() -> dict[str, Any]:
    """JSON Schema gerado a partir do modelo Pydantic (contrato e validação cruzada)."""
    return ThreatModelDocument.model_json_schema()
