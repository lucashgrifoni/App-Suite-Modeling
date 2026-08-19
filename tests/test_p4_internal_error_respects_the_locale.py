"""O 500 é a única resposta que não falava a língua do pedido.

`ObservabilityMiddleware` põe o locale num contextvar e repõe-no no `finally`. O handler de
`Exception` corre no `ServerErrorMiddleware` do Starlette, que está **por fora** da pilha de
middleware do utilizador — portanto quando ele lê o contextvar, o `finally` já correu e o valor já
voltou ao omisso.

Medido, com o mesmo `Accept-Language` que localiza correctamente todos os outros códigos:

    pt-BR  500  {"message": "An unexpected error occurred.", ...}
    en     500  {"message": "An unexpected error occurred.", ...}

Idênticos. Um 422 do mesmo cliente vem em português.

A correcção resolve o locale a partir do **pedido**, dentro do handler, em vez de depender de uma
ordem de execução que não controla.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))
sys.path.insert(0, str(_ROOT / "apps" / "api"))


@pytest.fixture()
def client():
    import logging

    logging.disable(logging.CRITICAL)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from otm_api.observability import ObservabilityMiddleware, register_unhandled_exception_handler

    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)
    register_unhandled_exception_handler(app)

    @app.get("/boom")
    def _boom() -> None:
        raise RuntimeError("explode")

    return TestClient(app, raise_server_exceptions=False)


def test_o_pedido_em_ingles_recebe_a_mensagem_em_ingles(client) -> None:
    response = client.get("/boom", headers={"Accept-Language": "en"})

    assert response.status_code == 500
    assert response.json()["message"] == "An unexpected error occurred."


def test_o_pedido_em_portugues_recebe_a_mensagem_em_portugues(client) -> None:
    response = client.get("/boom", headers={"Accept-Language": "pt-BR"})

    assert response.status_code == 500
    assert response.json()["message"] == "Ocorreu um erro inesperado."


def test_sem_cabecalho_continua_no_omisso(client) -> None:
    """A correcção não podia mudar o comportamento de quem não pede língua nenhuma."""
    assert client.get("/boom").json()["message"] == "An unexpected error occurred."


def test_o_contextvar_nao_fica_sujo_entre_pedidos(client) -> None:
    """Resolver a partir do pedido não pode deixar estado a escorrer para o pedido seguinte."""
    client.get("/boom", headers={"Accept-Language": "pt-BR"})

    assert client.get("/boom", headers={"Accept-Language": "en"}).json()["message"] == (
        "An unexpected error occurred."
    )
