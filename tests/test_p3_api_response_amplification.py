"""
Regressão: a entrada desta API é limitada em bytes, nós YAML, profundidade e tamanho de
upload; a **saída** não tinha limite nenhum, e o operador não tinha como a dimensionar.

Medido antes da correção, em `/v1/models/analyze` (documento do template `admin-portal` com
componentes sintéticos acrescentados):

    componentes   pedido      resposta    razão
          1 005    490 KB      10,5 MB    22,0x
          2 005    974 KB      21,0 MB    22,1x
          4 005  1 943 KB      42,1 MB    22,2x

Sem 413, sem truncagem, sem streaming: 200 com um corpo de dezenas de MB, construído inteiro
em memória antes do primeiro byte sair. A razão é praticamente **constante** — a amplificação
é linear na entrada, não super-linear — e é isso que decide a forma da correção:

* um tecto **por omissão** não é possível sem recusar entrada legítima. Medido: um upload
  Terraform de 1,64 MiB, aceite pelo limite de 2 MiB que a própria rota `/v1/imports`
  documenta, produz um rascunho com **30 001 componentes**; e `analyze` responde hoje a 4 005
  componentes em 3,6 s. Qualquer tecto na ordem dos milhares — o único intervalo em que
  limitaria alguma coisa — recusaria o caminho `import -> analyze` que o produto anuncia.
* o que faltava, e existe agora, é o **controlo** e o **número**: `OTM_MAX_DOCUMENT_ENTITIES`
  dá ao operador um tecto explícito no ponto em que todas as rotas de documento convergem, e
  `docs/features/API.md` passa a publicar a razão de amplificação, sem a qual dimensionar o
  limite de corpo do gateway (obrigatório em `DEPLOYMENT_INVARIANTS.md`) é adivinhar.

Por omissão a variável está por definir e nada muda — o que estes testes também fixam.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.document_limits import (  # noqa: E402
    DocumentLimitConfigError,
    count_document_entities,
    resolve_max_document_entities,
)
from otm_api.main import app  # noqa: E402
from otm_api.services.documents import document_from_payload  # noqa: E402

_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_MAX_DOCUMENT_ENTITIES"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def restore_main_module() -> Iterator[None]:
    """Quem recarrega `otm_api.main` tem de devolver a app default aos outros módulos."""
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    import otm_api.main as main

    importlib.reload(main)


@pytest.fixture
def template(client: TestClient) -> dict[str, Any]:
    return client.post("/v1/templates/admin-portal/instantiate").json()["document"]


def _grown(template: dict[str, Any], extra_components: int) -> dict[str, Any]:
    """O documento do template com `extra_components` componentes válidos acrescentados."""
    document = json.loads(json.dumps(template))
    shape = dict(document["components"][1])
    document["components"] += [
        dict(shape, id=f"svc{i}", name=f"Service {i}", asset_ids=[]) for i in range(extra_components)
    ]
    return document


def _entities(document: dict[str, Any]) -> int:
    return sum(len(document.get(key) or []) for key in ("components", "data_flows", "assets"))


# --- contagem e leitura do tecto --------------------------------------------------------


def test_the_count_is_the_three_entity_collections(template: dict[str, Any]) -> None:
    assert count_document_entities(document_from_payload(template)) == _entities(template)


def test_the_count_follows_a_grown_document(template: dict[str, Any]) -> None:
    grown = _grown(template, 40)

    assert count_document_entities(document_from_payload(grown)) == _entities(template) + 40


def test_the_ceiling_is_unset_by_default() -> None:
    assert resolve_max_document_entities() is None


@pytest.mark.parametrize("value", ["", "   "])
def test_a_blank_value_is_no_ceiling(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Um secret de CI que resolveu para nada não pode virar "recusa tudo"."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", value)

    assert resolve_max_document_entities() is None


def test_a_configured_ceiling_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "  250  ")

    assert resolve_max_document_entities() == 250


@pytest.mark.parametrize("value", ["nope", "1oo", "12.5", "0", "-3"])
def test_an_unusable_ceiling_is_refused(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """`0` recusaria todos os documentos, incluindo os vazios; uma gralha não pode fazer isso."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", value)

    with pytest.raises(DocumentLimitConfigError, match="OTM_MAX_DOCUMENT_ENTITIES"):
        resolve_max_document_entities()


def test_the_app_refuses_to_start_with_an_unusable_ceiling(
    monkeypatch: pytest.MonkeyPatch,
    restore_main_module: None,
) -> None:
    """Uma gralha aborta o deploy, em vez de aparecer como 500 no primeiro pedido com documento."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "1oo")
    import otm_api.main as main

    with pytest.raises(DocumentLimitConfigError, match="OTM_MAX_DOCUMENT_ENTITIES"):
        importlib.reload(main)


def test_startup_announces_a_configured_ceiling(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    """Um 413 num documento legítimo tem de ter uma linha no arranque a explicá-lo."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "250")
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "document_entity_ceiling max_entities=250" in caplog.text


def test_startup_says_nothing_when_there_is_no_ceiling(
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "document_entity_ceiling" not in caplog.text


# --- o tecto aplicado, no funil onde todas as rotas de documento convergem ---------------


#: Cada rota que recebe um documento, com o resto do corpo que ela exige. `analyze`,
#: `validate` e `exports` recusam campos desconhecidos, por isso `run_analysis` só vai onde
#: existe — ver `tests/test_api_p1_unknown_request_fields.py`.
_DOCUMENT_ROUTES = [
    ("/v1/models/analyze", {}),
    ("/v1/models/validate", {}),
    ("/v1/exports", {}),
    ("/v1/reports/premium", {"run_analysis": True}),
    ("/v1/remediation/backlog", {"run_analysis": True}),
]


@pytest.mark.parametrize(("path", "extra"), _DOCUMENT_ROUTES)
def test_a_document_above_the_ceiling_is_refused(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    extra: dict[str, Any],
) -> None:
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")

    r = client.post(path, json={"document": _grown(template, 30), **extra})

    assert r.status_code == 413, f"{path} -> {r.status_code}"


def test_the_refusal_uses_the_documented_envelope(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O mesmo `{code, message}` de `IMPORT_TOO_LARGE`, e não um `detail` em string solta."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")

    detail = client.post("/v1/models/analyze", json={"document": _grown(template, 30)}).json()["detail"]

    assert detail["code"] == "DOCUMENT_TOO_LARGE"


def _refusal_message(client: TestClient, template: dict[str, Any]) -> str:
    body = {"document": _grown(template, 30)}
    return str(client.post("/v1/models/analyze", json=body).json()["detail"]["message"])


def test_the_refusal_names_the_variable_that_decided_it(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O tecto é uma escolha deste deployment, não um limite do produto: tem de se ver onde."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")

    assert "OTM_MAX_DOCUMENT_ENTITIES" in _refusal_message(client, template)


def test_the_refusal_names_the_ceiling(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")

    assert "20" in _refusal_message(client, template)


def test_the_refusal_names_the_size_that_was_sent(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem o número enviado, o utilizador não sabe por quanto tem de dividir o modelo."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")

    assert str(_entities(_grown(template, 30))) in _refusal_message(client, template)


def test_nothing_is_analysed_before_the_refusal(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recusar depois de construir a resposta não pouparia a memória que o tecto existe para poupar."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")

    r = client.post("/v1/models/analyze", json={"document": _grown(template, 30)})

    assert len(r.content) < 2000, len(r.content)


def test_the_second_document_of_a_pair_is_also_checked(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/v1/models/compare` recebe dois documentos; um tecto que só olhasse para o primeiro
    seria contornável trocando a ordem."""
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", "20")
    body = {"baseline": template, "revised": _grown(template, 30), "run_analysis": True}

    assert client.post("/v1/models/compare", json=body).status_code == 413


# --- e o que o tecto não pode passar a recusar ------------------------------------------


@pytest.mark.parametrize(("path", "extra"), _DOCUMENT_ROUTES)
def test_a_document_at_the_ceiling_is_accepted(
    client: TestClient,
    template: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    extra: dict[str, Any],
) -> None:
    """Exatamente no tecto passa: a fronteira é `>`, não `>=`."""
    document = _grown(template, 8)
    monkeypatch.setenv("OTM_MAX_DOCUMENT_ENTITIES", str(_entities(document)))

    r = client.post(path, json={"document": document, **extra})

    assert r.status_code == 200, r.text


@pytest.mark.parametrize(("path", "extra"), _DOCUMENT_ROUTES)
def test_without_the_variable_nothing_changes(
    client: TestClient,
    template: dict[str, Any],
    path: str,
    extra: dict[str, Any],
) -> None:
    """O default é "sem tecto": nenhuma instalação existente muda de comportamento."""
    r = client.post(path, json={"document": _grown(template, 200), **extra})

    assert r.status_code == 200, r.text[:400]


def test_the_import_path_the_product_advertises_is_untouched(client: TestClient) -> None:
    """
    O tecto vive no funil dos documentos submetidos, não no importador.

    Medido: um Terraform de 1,64 MiB — aceite pelo limite de 2 MiB da própria rota — produz
    30 001 componentes. Se o tecto valesse aqui, o caminho `import` anunciado no README
    passaria a 413 com a variável definida em qualquer valor útil.
    """
    terraform = "".join(f'resource "aws_s3_bucket" "b{i}" {{\n  bucket = "b{i}"\n}}\n' for i in range(300)).encode()

    r = client.post("/v1/imports/terraform", files={"file": ("main.tf", terraform, "text/plain")})

    assert r.status_code == 200, r.text[:400]


# --- o número que o operador precisa para dimensionar o gateway -------------------------


def test_the_documented_amplification_ratio_still_holds(client: TestClient, template: dict[str, Any]) -> None:
    """
    Guarda de razão: se uma mudança no motor aumentar o fan-out por componente, é este teste
    que dá o sinal — e não o operador cujo gateway foi dimensionado com o número antigo.

    `docs/features/API.md` publica ~25x para `/v1/models/analyze`; o tecto aqui é 150x, largo
    o suficiente para não ser frágil e apertado o suficiente para apanhar uma ordem de
    grandeza.
    """
    body = {"document": _grown(template, 100)}
    request_bytes = len(json.dumps(body).encode())

    response = client.post("/v1/models/analyze", json=body)

    assert len(response.content) < 150 * request_bytes, len(response.content) / request_bytes


def test_the_backlog_route_amplifies_within_the_same_bound(client: TestClient, template: dict[str, Any]) -> None:
    body = {"document": _grown(template, 100), "run_analysis": True}
    request_bytes = len(json.dumps(body).encode())

    response = client.post("/v1/remediation/backlog", json=body)

    assert len(response.content) < 150 * request_bytes, len(response.content) / request_bytes
