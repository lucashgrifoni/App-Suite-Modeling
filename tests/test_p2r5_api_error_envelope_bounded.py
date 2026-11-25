"""
Regressão: o envelope 422 limitava cada valor ecoado, mas não o **número** de entradas.

`errors._MAX_INPUT_CHARS = 256` e os cortes de 50 itens / 50 chaves em `_truncate` existem para
"keep 422 responses bounded even when a client sends MB-sized fields". A intenção estava
declarada e meia implementada: `_truncated_errors` percorria `exc.errors()` e truncava o `input`
e o `ctx` de cada entrada, mas nunca limitava `len(errors)`. Como cada item rejeitado de um enum
custa ~330 bytes constantes de texto (a lista de valores aceites sai duas vezes, em `msg` e em
`ctx.expected`), a resposta crescia linearmente com o número de itens inválidos.

Medido antes: 1 MB de pedido -> 66 MB de resposta em 1,4 s de CPU (amplificação 66x), sem
autenticação e sem limite na configuração por defeito. Um documento com 3000 componentes
inválidos produzia um 422 de 1 126 682 bytes em validate/analyze/exports/premium/backlog.

Os dois caminhos partilham o mesmo helper (`RequestValidationError` via `errors.py` e
`DOCUMENT_VALIDATION_ERROR` via `routers/_errors._pydantic_error_items`), por isso ambos são
verificados aqui.
"""

from __future__ import annotations

import json

import httpx
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.errors import _MAX_ERROR_ITEMS  # noqa: E402
from otm_api.main import app  # noqa: E402

#: Teto de resposta com folga. O medido depois da correção é ~16,5 kB para qualquer n.
_BOUND_BYTES = 128 * 1024


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _export_with_bad_formats(client: TestClient, count: int) -> httpx.Response:
    doc = client.post("/v1/models").json()["document"]
    payload = json.dumps({"document": doc, "formats": ["x"] * count}).encode()
    return client.post("/v1/exports", content=payload, headers={"content-type": "application/json"})


def _document_with_bad_components(count: int) -> dict:
    return {
        "model": {"system_type": "web_application", "methodology": "stride"},
        "metadata": {"title": "T"},
        "components": [{"id": "", "name": "", "kind": "not-a-kind"} for _ in range(count)],
        "data_flows": [],
    }


# --- o defeito: a amplificação ---------------------------------------------------------


def test_the_request_validation_envelope_caps_the_number_of_errors(client: TestClient) -> None:
    r = _export_with_bad_formats(client, 20_000)

    assert len(r.json()["errors"]) <= _MAX_ERROR_ITEMS + 1


def test_the_response_no_longer_grows_with_the_number_of_invalid_items(client: TestClient) -> None:
    """O sintoma: 49,5x com 1000 itens, 64,8x com 20 000, 66,0x com 200 000.

    Vinte vezes mais itens inválidos podem custar mais alguns bytes — o total real vai escrito
    no marcador — mas não podem custar mais uma linha por item, que é o que amplificava.
    """
    small = len(_export_with_bad_formats(client, 1_000).content)
    large = len(_export_with_bad_formats(client, 20_000).content)

    assert large - small < 100, f"a resposta ainda cresce com o pedido: {small} -> {large}"


def test_a_megabyte_of_invalid_items_does_not_produce_a_megabyte_of_response(client: TestClient) -> None:
    r = _export_with_bad_formats(client, 200_000)

    assert len(r.content) < _BOUND_BYTES


def test_the_amplification_factor_is_below_one_for_a_large_request(client: TestClient) -> None:
    """A propriedade que interessa: a resposta deixa de ser um multiplicador do pedido."""
    doc = client.post("/v1/models").json()["document"]
    payload = json.dumps({"document": doc, "formats": ["x"] * 200_000}).encode()

    r = client.post("/v1/exports", content=payload, headers={"content-type": "application/json"})

    assert len(r.content) < len(payload)


def test_the_document_validation_path_is_capped_too(client: TestClient) -> None:
    """`_pydantic_error_items` reusa o mesmo helper: a rota de domínio tinha o mesmo buraco."""
    r = client.post("/v1/models/validate", json={"document": _document_with_bad_components(3_000)})

    assert len(r.json()["detail"]["errors"]) <= _MAX_ERROR_ITEMS + 1


def test_the_document_validation_response_is_bounded(client: TestClient) -> None:
    r = client.post("/v1/models/validate", json={"document": _document_with_bad_components(3_000)})

    assert len(r.content) < _BOUND_BYTES


@pytest.mark.parametrize("route", ["/v1/models/validate", "/v1/models/analyze", "/v1/models/precheck"])
def test_every_document_route_bounds_the_same_payload(client: TestClient, route: str) -> None:
    r = client.post(route, json={"document": _document_with_bad_components(3_000)})

    assert len(r.content) < _BOUND_BYTES


# --- o que não pode partir: o diagnóstico continua utilizável -------------------------


def test_the_status_code_is_unchanged(client: TestClient) -> None:
    assert _export_with_bad_formats(client, 20_000).status_code == 422


def test_a_normal_number_of_errors_is_reported_in_full(client: TestClient) -> None:
    """O risco oposto: um utilizador com dez erros reais não pode perder nenhum deles."""
    r = _export_with_bad_formats(client, 10)

    assert len(r.json()["errors"]) == 10


def test_a_list_exactly_at_the_cap_is_not_truncated(client: TestClient) -> None:
    r = _export_with_bad_formats(client, _MAX_ERROR_ITEMS)

    assert [e["type"] for e in r.json()["errors"]].count("too_many_errors") == 0


def test_the_first_errors_are_the_real_ones(client: TestClient) -> None:
    """Cortar não pode substituir o diagnóstico: as primeiras entradas continuam intactas."""
    errors = _export_with_bad_formats(client, 20_000).json()["errors"]

    assert errors[0]["loc"][:2] == ["body", "formats"]


def test_the_first_errors_keep_their_message(client: TestClient) -> None:
    errors = _export_with_bad_formats(client, 20_000).json()["errors"]

    assert errors[0]["msg"]


def test_the_truncation_is_declared_and_not_silent(client: TestClient) -> None:
    """Sem marcador, "50 erros" leria-se como "o meu documento tem 50 problemas"."""
    errors = _export_with_bad_formats(client, 20_000).json()["errors"]

    assert errors[-1]["type"] == "too_many_errors"


def test_the_marker_names_the_real_total(client: TestClient) -> None:
    errors = _export_with_bad_formats(client, 20_000).json()["errors"]

    assert "20000 in total" in errors[-1]["msg"]


def test_the_marker_has_the_shape_of_every_other_entry(client: TestClient) -> None:
    """Um cliente que percorra `errors[]` não pode precisar de um caso especial."""
    marker = _export_with_bad_formats(client, 20_000).json()["errors"][-1]

    assert set(marker) >= {"type", "loc", "msg"}


def test_a_single_valid_export_request_still_works(client: TestClient) -> None:
    """Controlo: o corte no envelope de erro não toca no caminho feliz."""
    doc = client.post("/v1/models").json()["document"]

    r = client.post("/v1/exports", json={"document": doc, "formats": ["document_json"]})

    assert r.status_code == 200
