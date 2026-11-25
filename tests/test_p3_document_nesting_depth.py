"""
Aninhamento profundo em documento não confiável (YAML e JSON): `ValueError` acionável, nunca `RecursionError`.

O `_BoundedSafeLoader` já travava a *expansão de aliases* — o billion laughs, em que ~600 bytes
com sete níveis de âncoras encadeadas viram gigabytes ao serializar. Esse tecto conta **nós
expandidos**, e um documento sem um único alias não gasta nada dele: `"a: " + "["*5000 +
"]"*5000` tem 10 KB, zero aliases, e passa direto pelo contador até o `compose_node` do PyYAML
esgotar a pilha do interpretador.

O que isso produzia, medido antes da correção:

- `POST /v1/imports/kubernetes` e `/v1/imports/openapi` com 10 003 bytes devolviam **500
  `INTERNAL_ERROR`** em 0,42 s. `_draft_from_upload` traduz `UnicodeDecodeError`, `ValueError`,
  `AttributeError` e `TypeError` para 400; `RecursionError` é subclasse de `RuntimeError` e não
  estava em nenhum ramo, por isso subia ao handler genérico. É exatamente a classe de defeito
  que `_shape_error` foi criado para fechar — a mesma causa raiz, um tipo de exceção adiante.
- Cada pedido escrevia **627 695 bytes de log** (traceback completo, com a pilha repetida
  milhares de vezes) para 10 003 bytes de entrada: **62,8x de amplificação**. Esse é o impacto
  que interessa — não o 500 em si, mas o custo de disco e de ingestão de logs que um cliente
  não autenticado provoca com um upload trivial.
- No CLI a falha já degradava sem traceback, mas com a causa errada ("confirm the path, YAML,
  and file permissions" para um documento cuja profundidade é o problema).

O tecto fica em `MAX_DOCUMENT_DEPTH`. O documento mais profundo deste repositório tem profundidade
**6** (medido em 23 ficheiros YAML: exemplos, fixtures, workflows, docker-compose), e os
artefactos de terceiros que os importadores ingerem — OpenAPI com `allOf` encadeado, manifests
Helm — ficam bem abaixo de 100. A folga é ~16x sobre o pior caso real, na mesma linha dos 38x
que `MAX_YAML_EXPANDED_NODES` deixa.
"""

from __future__ import annotations

import io
import logging

import pytest
import yaml
from otm_core_schema.io import (
    ENV_MAX_DOCUMENT_DEPTH,
    MAX_DOCUMENT_DEPTH,
    json_loads_bounded,
    safe_load_all_bounded,
    safe_load_bounded,
)

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

#: Só estas duas rotas atravessam o loader YAML. `terraform` fica de fora de propósito: o
#: importador é regex sobre texto HCL (`_RESOURCE_HEAD`), nunca chama `safe_load_bounded`, e por
#: isso um payload YAML aninhado é, para ele, conteúdo não reconhecido — que o contrato manda
#: aceitar como rascunho com `unknowns[]`. Ver `test_terraform_is_exempt_because_it_never_parses_yaml`.
_YAML_IMPORT_ROUTES = ["openapi", "kubernetes"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _nested(depth: int) -> str:
    """Aninhamento puro de sequências: nenhum alias, logo o contador de expansão não o vê."""
    return "a: " + "[" * depth + "]" * depth


# --- o loader ---------------------------------------------------------------------------


def test_deep_nesting_raises_value_error_not_recursion_error() -> None:
    """A garantia central: a falha é do domínio do documento, não do interpretador."""
    with pytest.raises(ValueError) as exc:
        safe_load_bounded(_nested(MAX_DOCUMENT_DEPTH + 50))

    assert not isinstance(exc.value, RecursionError)


def test_the_refusal_names_the_limit_and_the_override() -> None:
    """Uma mensagem que não diz o tecto nem como mudá-lo obriga a ler o código."""
    with pytest.raises(ValueError) as exc:
        safe_load_bounded(_nested(MAX_DOCUMENT_DEPTH + 50))

    message = str(exc.value)
    assert str(MAX_DOCUMENT_DEPTH) in message
    assert ENV_MAX_DOCUMENT_DEPTH in message


def test_a_document_at_the_limit_still_loads() -> None:
    """O tecto recusa o que passa dele — não o que lá chega."""
    assert safe_load_bounded(_nested(MAX_DOCUMENT_DEPTH - 1)) is not None


def test_real_documents_are_far_below_the_limit() -> None:
    """Profundidade 6 é o pior caso real deste repositório; 100 não pode apertar ninguém."""
    realistic = (
        "model:\n"
        "  schema_version: '1.1.0'\n"
        "components:\n"
        "  - id: api\n"
        "    tags: [a, b]\n"
        "    meta:\n"
        "      owner:\n"
        "        team: platform\n"
    )
    assert safe_load_bounded(realistic)["components"][0]["meta"]["owner"]["team"] == "platform"


def test_the_multi_document_path_is_bounded_too() -> None:
    """`safe_load_all_bounded` é a porta dos manifests Kubernetes com `---`."""
    with pytest.raises(ValueError) as exc:
        safe_load_all_bounded(_nested(MAX_DOCUMENT_DEPTH + 50))

    assert not isinstance(exc.value, RecursionError)


def test_a_shallow_first_document_does_not_shield_a_deep_second_one() -> None:
    """O tecto é estrutural e por documento, ao contrário do orçamento de aliases, que é do
    stream inteiro. O que importa aqui é que o guarda continua a correr depois do primeiro
    `---`: um manifest raso à cabeça não é um bilhete de entrada para o resto do ficheiro."""
    stream = "shallow: 1\n---\n" + _nested(MAX_DOCUMENT_DEPTH + 50)

    with pytest.raises(ValueError):
        safe_load_all_bounded(stream)


def test_mappings_nest_as_deeply_as_sequences() -> None:
    """O tecto é sobre a estrutura, não sobre o tipo de nó com que se constrói."""
    deep_map = "".join(f"{'  ' * i}k{i}:\n" for i in range(MAX_DOCUMENT_DEPTH + 50)) + (
        f"{'  ' * (MAX_DOCUMENT_DEPTH + 50)}leaf: 1"
    )

    with pytest.raises(ValueError) as exc:
        safe_load_bounded(deep_map)

    assert not isinstance(exc.value, RecursionError)


def test_the_env_override_can_lower_the_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lido por chamada, como os outros dois tectos — um runner pode apertá-lo sem reimportar."""
    monkeypatch.setenv(ENV_MAX_DOCUMENT_DEPTH, "10")

    with pytest.raises(ValueError):
        safe_load_bounded(_nested(30))

    assert safe_load_bounded(_nested(5)) is not None


def test_a_non_positive_override_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesmo contrato de validação que `OTM_MAX_YAML_NODES` e `OTM_MAX_DOCUMENT_BYTES`."""
    monkeypatch.setenv(ENV_MAX_DOCUMENT_DEPTH, "0")

    with pytest.raises(ValueError, match=ENV_MAX_DOCUMENT_DEPTH):
        safe_load_bounded("a: 1")


def test_the_alias_ceiling_still_refuses_the_billion_laughs() -> None:
    """A defesa anterior não pode ter sido substituída por esta."""
    bomb = "a: &a [x,x,x,x,x,x,x,x,x]\n" + "".join(
        f"{chr(97 + i)}: &{chr(97 + i)} [{','.join('*' + chr(96 + i) for _ in range(9))}]\n" for i in range(1, 9)
    )

    with pytest.raises(ValueError, match="alias expansion"):
        safe_load_bounded(bomb)


def test_plain_pyyaml_still_blows_the_stack_on_the_same_payload() -> None:
    """Prova de que o payload é genuinamente hostil e que o tecto é nosso, não do PyYAML."""
    with pytest.raises(RecursionError):
        yaml.safe_load(_nested(5000))


# --- o mesmo defeito do lado JSON -------------------------------------------------------
#
# `load_object_from_text` escolhe `json.loads` quando o texto começa por `{`. Esse ramo tinha o
# buraco idêntico: `'{"a":' * 20000` num upload para `/v1/imports/openapi` devolvia 500, porque
# o `RecursionError` do parser não é `json.JSONDecodeError` e escapava ao `except` da função.
# Encontrado a procurar variantes da mesma causa raiz, depois de fechar o lado YAML.


def _nested_json(depth: int) -> str:
    return '{"a":' * depth + "1" + "}" * depth


def test_deep_json_raises_value_error_not_recursion_error() -> None:
    with pytest.raises(ValueError) as exc:
        json_loads_bounded(_nested_json(MAX_DOCUMENT_DEPTH + 50))

    assert not isinstance(exc.value, RecursionError)
    assert str(MAX_DOCUMENT_DEPTH) in str(exc.value)
    assert ENV_MAX_DOCUMENT_DEPTH in str(exc.value)


def test_json_at_the_limit_still_loads() -> None:
    assert json_loads_bounded(_nested_json(MAX_DOCUMENT_DEPTH - 1)) is not None


def test_braces_inside_strings_do_not_count_as_nesting() -> None:
    """Um `{` dentro de uma string é texto. Contá-lo recusaria specs legítimas — uma descrição
    OpenAPI com um exemplo de JSON lá dentro é o caso normal, não o exótico."""
    payload = '{"description": "' + "{[" * 500 + '", "ok": true}'

    assert json_loads_bounded(payload)["ok"] is True


def test_escaped_quotes_do_not_break_the_scanner() -> None:
    """`\\"` não fecha a string; se fechasse, o resto do texto passaria a contar como estrutura."""
    payload = '{"k": "he said \\"' + "{" * 500 + '\\" and left", "ok": true}'

    assert json_loads_bounded(payload)["ok"] is True


def test_plain_json_loads_still_blows_the_stack_on_the_same_payload() -> None:
    """O payload é genuinamente hostil: o tecto é nosso, não do módulo `json`."""
    import json as stdlib_json

    with pytest.raises(RecursionError):
        stdlib_json.loads(_nested_json(20000))


def test_import_refuses_deep_json_with_400_not_500(client: TestClient) -> None:
    payload = _nested_json(MAX_DOCUMENT_DEPTH + 50).encode()

    response = client.post(
        "/v1/imports/openapi",
        files={"file": ("deep.json", payload, "application/json")},
    )

    assert response.status_code == 400, response.text


def test_a_normal_openapi_spec_still_imports(client: TestClient) -> None:
    spec = b'{"openapi":"3.0.0","info":{"title":"Orders","version":"1"},"paths":{}}'

    response = client.post(
        "/v1/imports/openapi",
        files={"file": ("api.json", spec, "application/json")},
    )

    assert response.status_code == 200, response.text


# --- a API ------------------------------------------------------------------------------


@pytest.mark.parametrize("route", _YAML_IMPORT_ROUTES)
def test_import_refuses_deep_nesting_with_400_not_500(client: TestClient, route: str) -> None:
    """O contrato de `docs/features/API.md`: erro do artefacto é 400 no envelope, nunca 500."""
    payload = _nested(MAX_DOCUMENT_DEPTH + 50).encode()

    response = client.post(
        f"/v1/imports/{route}",
        files={"file": ("deep.yaml", payload, "application/yaml")},
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize("route", _YAML_IMPORT_ROUTES)
def test_the_refusal_keeps_the_documented_envelope(client: TestClient, route: str) -> None:
    """`{code, message}` — o parser do frontend lê `detail.code`."""
    payload = _nested(MAX_DOCUMENT_DEPTH + 50).encode()

    response = client.post(
        f"/v1/imports/{route}",
        files={"file": ("deep.yaml", payload, "application/yaml")},
    )

    detail = response.json()["detail"]
    assert detail["code"] == "IMPORT_ARTIFACT_INVALID"
    assert isinstance(detail["message"], str) and detail["message"]


def test_a_hostile_upload_does_not_amplify_into_the_log(client: TestClient) -> None:
    """O impacto medido era **62,8x** de amplificação por pedido; tem de cair para perto de zero.

    Este é o teste que fixa a descoberta, por isso mede o que ela afirma — bytes escritos — e não
    a presença de `exc_info`. O handler desta API não usa `exc_info`: anexa a pilha como campo
    `extra` (`traceback=...`), de modo que uma asserção sobre `record.exc_info` fica verde com o
    defeito presente. Foi o que aconteceu na primeira versão deste teste.

    Antes da correção: 10 003 bytes de entrada -> 627 695 bytes de log. Depois: 13 bytes.
    O tecto de 1x é ordens de grandeza abaixo do defeito e bem acima do ruído normal.
    """
    payload = _nested(MAX_DOCUMENT_DEPTH + 50).encode()

    sink = io.StringIO()
    handler = logging.StreamHandler(sink)
    api_log = logging.getLogger("otm.api")
    api_log.addHandler(handler)
    try:
        response = client.post(
            "/v1/imports/kubernetes",
            files={"file": ("deep.yaml", payload, "application/yaml")},
        )
    finally:
        api_log.removeHandler(handler)

    written = len(sink.getvalue())
    assert response.status_code == 400
    assert written < len(payload), (
        f"{written} bytes de log para {len(payload)} bytes de entrada "
        f"({written / len(payload):.1f}x): a pilha voltou ao log"
    )


def test_terraform_is_exempt_because_it_never_parses_yaml(client: TestClient) -> None:
    """Fixa a razão da exceção, para que o dia em que `terraform` ganhar um parser YAML esta
    rota volte à lista acima em vez de ficar silenciosamente descoberta.

    O importador lê HCL por regex (`resource "tipo" "nome" {`). Um documento YAML aninhado não
    tem blocos `resource`, logo é conteúdo presente mas não reconhecido — 200 com rascunho e
    `unknowns[]` é o contrato deliberado do import assistido, não uma falha do tecto.
    """
    import inspect

    from otm_artifact_import import terraform_import

    source = inspect.getsource(terraform_import)
    assert "safe_load" not in source, (
        "o importador Terraform passou a ler YAML: acrescente 'terraform' a _YAML_IMPORT_ROUTES"
    )

    response = client.post(
        "/v1/imports/terraform",
        files={"file": ("deep.yaml", _nested(MAX_DOCUMENT_DEPTH + 50).encode(), "application/yaml")},
    )

    assert response.status_code == 200


def test_a_normal_manifest_still_imports(client: TestClient) -> None:
    """A correção não pode ter fechado a porta ao uso legítimo."""
    manifest = b"apiVersion: v1\nkind: Service\nmetadata:\n  name: orders\n"

    response = client.post(
        "/v1/imports/kubernetes",
        files={"file": ("svc.yaml", manifest, "application/yaml")},
    )

    assert response.status_code == 200, response.text
