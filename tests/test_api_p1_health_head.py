"""
Regressão: `/health` responde a HEAD, não só a GET.

`/health` é documentado como liveness probe "for load balancers / Kubernetes". O
`APIRoute` do FastAPI, ao contrário do `Route` do Starlette, não acrescenta HEAD
junto de GET — por isso monitores que usam HEAD por omissão (`curl -I`, UptimeRobot,
vários `check` de HAProxy/NGINX) apanhavam 405 num serviço saudável.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_head_health_is_200(client: TestClient) -> None:
    assert client.head("/health").status_code == 200


def test_get_health_still_returns_body(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_head_is_not_blanket_enabled_across_the_app(client: TestClient) -> None:
    """O 200 em HEAD /health tem de vir desta alteração, não de um comportamento global.

    Sem esta asserção, `test_head_health_is_200` continuaria verde se alguém activasse
    HEAD em todas as rotas — que é uma mudança de superfície bem diferente da pretendida.
    `/` é declarado só com GET e serve de controlo.

    (Substituiu um teste que afirmava `client.head("/health").content == b""`: o cliente
    HTTP descarta sempre o corpo de uma resposta HEAD, por isso essa asserção era
    verdadeira independentemente do que o servidor fizesse.)
    """
    assert client.head("/").status_code == 405
