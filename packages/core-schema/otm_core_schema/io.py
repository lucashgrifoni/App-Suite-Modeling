"""Serialização YAML/JSON do documento canônico — sem lógica de negócio."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

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

#: Tecto de **profundidade** de aninhamento do documento, em YAML e em JSON.
#:
#: O tecto de nós acima conta expansão de aliases, e um documento sem um único alias não gasta
#: nada dele. `"a: " + "["*5000 + "]"*5000` são 10 KB de sequências encaixadas, zero aliases, e
#: atravessava o contador até o `compose_node` do PyYAML esgotar a pilha do interpretador. O
#: `RecursionError` que daí saía não é `ValueError`: nas rotas de import subia ao handler
#: genérico como **500 `INTERNAL_ERROR`** e escrevia o traceback completo — 627 695 bytes de log
#: para 10 003 bytes de entrada, 62,8x de amplificação por pedido. O custo real era esse, não o
#: 500.
#:
#: O tecto é **um só para as duas serializações** porque descrevem a mesma forma de documento, e
#: porque o defeito era literalmente o mesmo dos dois lados: `load_object_from_text` escolhe
#: `json.loads` quando o texto começa por `{`, e esse ramo tinha exatamente o mesmo buraco —
#: `{"a":` * 20000 devolvia 500 pela mesma razão, com o `RecursionError` a escapar a um `except
#: (yaml.YAMLError, json.JSONDecodeError)`. Um tecto por formato deixaria a segunda porta aberta.
#:
#: 100 dá ~16x de folga: o documento mais profundo deste repositório tem profundidade 6 (23
#: ficheiros YAML medidos — exemplos, fixtures, workflows, docker-compose), e os artefactos de
#: terceiros que os importadores ingerem ficam bem abaixo disto. Override:
#: `OTM_MAX_DOCUMENT_DEPTH`.
MAX_DOCUMENT_DEPTH = 100
ENV_MAX_DOCUMENT_DEPTH = "OTM_MAX_DOCUMENT_DEPTH"


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
    """`SafeLoader` que contabiliza o custo expandido dos aliases e recusa chaves duplicadas."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Any, Any]:
        """Recusa uma chave repetida em vez de deixar a última vencer.

        O YAML manda a última ganhar, em silêncio. Num `.otm.yaml` isso significa que um
        merge mal resolvido — dois blocos `components:`, duas secções `metadata:` — passa por
        `otm validate` com o painel verde enquanto metade do modelo desaparece: os componentes
        do primeiro bloco não existem, as ameaças que dependiam deles nunca são geradas, e o
        relatório que sai daí parece completo. É exatamente a classe de erro que o hook de
        pre-commit anunciado no README existe para apanhar.

        A verificação é feita ao nível dos nós, antes da construção, porque no dicionário
        resultante a duplicação já se perdeu.

        Corre **antes** de `flatten_mapping`, e por duas razões. A chave de merge (`<<`) não
        tem construtor próprio, por isso construí-la aqui rebentava; e depois do flatten as
        chaves herdadas da âncora aparecem na mesma lista que as locais, o que faria de
        `<<: *base` seguido de um override explícito um falso duplicado — que é precisamente
        o motivo pelo qual se usa uma âncora.
        """
        seen: set[Any] = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicated = key in seen
            except TypeError:  # pragma: no cover - defensive: chave não-hashable
                continue
            if duplicated:
                mark = key_node.start_mark
                raise ValueError(
                    f"duplicate key {key!r} at line {mark.line + 1}, column {mark.column + 1}: "
                    "YAML would silently keep only the last block and discard the first. "
                    "Merge the two blocks into one."
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self._max_expanded = _limit_from_env(ENV_MAX_YAML_EXPANDED_NODES, MAX_YAML_EXPANDED_NODES)
        self._expanded = 0
        self._max_depth = _limit_from_env(ENV_MAX_DOCUMENT_DEPTH, MAX_DOCUMENT_DEPTH)
        self._depth = 0
        # id(nó) -> custo expandido do sub-árvore. Usar `id` é seguro aqui porque todos os nós
        # compostos ficam vivos até ao fim (pendurados no pai ou em `self.anchors`), logo o
        # id não é reciclado durante a composição; `_pinned` garante-o mesmo assim.
        self._cost: dict[int, int] = {}
        self._pinned: list[Node] = []

    def compose_node(self, parent: Node | None, index: int) -> Node | None:
        # A profundidade conta-se aqui porque `compose_node` é a própria recursão do PyYAML: um
        # nível de aninhamento é uma chamada. O `finally` devolve o nível ao sair, para que o
        # tecto meça a profundidade da árvore e não o total de nós já visitados — dois irmãos
        # rasos não podem somar-se até ao limite.
        self._depth += 1
        try:
            if self._depth > self._max_depth:
                raise ValueError(
                    f"YAML nesting exceeds {self._max_depth} levels (override with {ENV_MAX_DOCUMENT_DEPTH})."
                )
            return self._compose_node_bounded(parent, index)
        finally:
            self._depth -= 1

    def _compose_node_bounded(self, parent: Node | None, index: int) -> Node | None:
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


def json_loads_bounded(text: str) -> Any:
    """`json.loads` com o mesmo tecto de profundidade que o loader YAML aplica.

    `json.loads` desce recursivamente e não tem limite próprio: `'{"a":' * 20000` esgota a pilha
    e levanta `RecursionError`, que não é `json.JSONDecodeError` nem `ValueError` — logo escapava
    a quem só apanhava erros de parse e voltava a sair como 500 com o traceback inteiro no log.
    Mesmo defeito do lado YAML, mesma consequência.

    A profundidade mede-se por varrimento linear **antes** de entregar o texto ao parser: o
    objectivo é recusar sem pagar a recursão, e não apanhar a explosão depois de ela custar. Um
    `RecursionError` continua a ser traduzido pelo chamador como defesa em profundidade, para o
    caso de um documento raso mas patológico de outra forma.
    """
    limit = _limit_from_env(ENV_MAX_DOCUMENT_DEPTH, MAX_DOCUMENT_DEPTH)
    if _json_depth_exceeds(text, limit):
        raise ValueError(f"JSON nesting exceeds {limit} levels (override with {ENV_MAX_DOCUMENT_DEPTH}).")
    return json.loads(text)


def _json_depth_exceeds(text: str, limit: int) -> bool:
    """Verdadeiro assim que o aninhamento passa `limit`, sem construir nada.

    Conta `{`/`[` fora de strings e sai à primeira violação, para que o custo de recusar uma
    bomba seja proporcional ao prefixo hostil e não ao ficheiro todo. As chavetas dentro de
    strings são ignoradas, incluindo as escapadas — senão `{"k": "}}}"}` contaria a menos e um
    ficheiro legítimo com chavetas no texto contaria a mais.
    """
    depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            depth += 1
            if depth > limit:
                return True
        elif ch in "}]":
            depth -= 1
    return False


def _entity_source_lines(root: Node | None) -> dict[tuple[str, str], int]:
    if not isinstance(root, MappingNode):
        return {}
    groups = {key.value: value for key, value in root.value if isinstance(key, ScalarNode)}
    lines: dict[tuple[str, str], int] = {}
    for field, kind in (("components", "component"), ("data_flows", "dataflow"), ("assets", "asset")):
        group = groups.get(field)
        if not isinstance(group, SequenceNode):
            continue
        for entry in group.value:
            if not isinstance(entry, MappingNode) or entry.start_mark.index < group.start_mark.index:
                continue
            for key, value in entry.value:
                if isinstance(key, ScalarNode) and key.value == "id" and isinstance(value, ScalarNode):
                    lines[kind, value.value] = key.start_mark.line + 1
    return lines


def load_document_from_yaml(
    text: str,
    *,
    source_lines: dict[tuple[str, str], int] | None = None,
) -> ThreatModelDocument:
    if source_lines is None:
        data = _safe_load_bounded(text)
    else:
        # Use the same bounded parse for validation and source positions.
        loader = _BoundedSafeLoader(text)
        try:
            node = loader.get_single_node()
            positions = _entity_source_lines(node)
            data = loader.construct_document(node) if node is not None else None
        finally:
            loader.dispose()
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    document = ThreatModelDocument.model_validate(data)
    if source_lines is not None:
        source_lines.update(positions)
    return document


def load_document_from_yaml_path(
    path: Path | str,
    *,
    source_lines: dict[tuple[str, str], int] | None = None,
) -> ThreatModelDocument:
    p = Path(path)
    limit = _limit_from_env(ENV_MAX_DOCUMENT_BYTES, MAX_DOCUMENT_BYTES)
    size = p.stat().st_size
    if size > limit:
        raise ValueError(
            f"document file is {size} bytes; the limit is {limit} bytes (override with {ENV_MAX_DOCUMENT_BYTES})."
        )
    return load_document_from_yaml(
        p.read_text(encoding="utf-8"),
        source_lines=source_lines if p.suffix.lower() != ".json" else None,
    )


def dump_document_to_yaml(document: ThreatModelDocument) -> str:
    # default_flow_style=False para legibilidade humana (TaC)
    data = document.model_dump(mode="json", exclude_none=True, by_alias=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


def dump_document_to_json(document: ThreatModelDocument, *, indent: int | None = 2) -> str:
    return document.model_dump_json(exclude_none=True, indent=indent, by_alias=True)


def json_schema() -> dict[str, Any]:
    """JSON Schema gerado a partir do modelo Pydantic (contrato e validação cruzada)."""
    return ThreatModelDocument.model_json_schema()
