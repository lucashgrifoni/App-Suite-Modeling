"""P4 regressão — o limitador não pode guardar para sempre quem já não está a bater.

`RateLimitMiddleware` guarda os contadores num `MemoryStorage` da `limits`. Esse armazenamento
tem um varredor de expiração, mas corre num `threading.Timer` que não é reagendado enquanto não
houver actividade — por isso um cliente que **pare** de bater deixa a sua entrada lá.

Medido antes desta correcção: 20 000 endereços distintos ⇒ 20 000 entradas em `events` e 20 000
em `locks`; com uma janela de `5/second`, seis segundos de inactividade (doze vezes a janela)
não libertavam nada. A 474 bytes por endereço, cerca de 2,1 M de endereços chegam a 1 GB. Em
`development` não há limite, mas em `staging`/`production` o limite está activo **por omissão**
(`120/minute`), portanto a superfície existe exactamente onde o controlo devia proteger: ligar a
protecção é que a cria.

Descartar por LRU resolveria a memória e abriria um desvio — bastaria inundar com endereços
distintos para expulsar a própria chave quente e reiniciar o balde. Varrer tudo a cada pedido é
O(chaves) por pedido. O que aqui se faz é descartar **apenas** chaves cuja janela já passou, e
isso não tem custo de segurança nenhum: um cliente cujo balde expirou tem direito a um balde novo
de qualquer maneira. É por isso que o teste que mais interessa neste ficheiro não é o da memória —
é `test_um_cliente_activo_continua_a_ser_limitado`.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from limits import parse  # noqa: E402
from otm_api.middleware_rate_limit import RateLimitMiddleware  # noqa: E402
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware  # noqa: E402


def _harness(limit: str) -> tuple[TestClient, RateLimitMiddleware]:
    """A app servida como o uvicorn a serve: o proxy reescreve o endereço a partir do cabeçalho."""
    inner = FastAPI()

    @inner.get("/ping")
    def ping() -> dict[str, bool]:  # pragma: no cover - trivial
        return {"ok": True}

    middleware = RateLimitMiddleware(inner, limit=parse(limit), trust_forwarded=True)
    served: Any = ProxyHeadersMiddleware(middleware, trusted_hosts="*")
    return TestClient(served), middleware


def _retained(middleware: RateLimitMiddleware) -> int:
    storage = middleware._limiter.storage
    return max(len(storage.events), len(storage.locks))


def _knock(client: TestClient, addresses: range | list[int]) -> None:
    for i in addresses:
        client.get("/ping", headers={"X-Forwarded-For": f"10.{i // 65536}.{(i // 256) % 256}.{i % 256}"})


def test_clientes_dentro_da_janela_sao_todos_guardados() -> None:
    """Metade um: esquecer não pode apanhar quem ainda está dentro da janela.

    A janela é de um minuto de propósito. A primeira versão deste teste usava `200/second` e
    afirmava que 300 chaves existiam depois de 300 pedidos; passou isolada e falhou na suíte
    completa com 222, porque sob carga os 300 pedidos demoraram mais do que a janela de um segundo
    e o esquecimento — correctamente — já tinha corrido a meio. A asserção é que dependia da
    velocidade da máquina, não o produto. Com um minuto de janela nenhuma carga plausível a
    aproxima, e a afirmação passa a ser sobre o que se quer dizer.
    """
    client, middleware = _harness("5000/minute")

    _knock(client, range(300))

    assert _retained(middleware) == 300, "nenhuma chave dentro da janela pode ser esquecida"


def test_clientes_que_pararam_de_bater_sao_esquecidos_apos_a_janela() -> None:
    """Metade dois: o caso medido — chamadores que desapareceram não ocupam memória."""
    client, middleware = _harness("200/second")

    _knock(client, range(300))
    time.sleep(1.1)  # a janela é de 1 s; passado isto nenhuma delas guarda informação útil
    _knock(client, [999])  # um pedido qualquer dá a oportunidade de varrer

    assert _retained(middleware) <= 2, f"{_retained(middleware)} chaves sobreviveram à própria janela"


def test_a_memoria_retida_nao_cresce_com_o_numero_de_clientes_ja_vistos() -> None:
    """A afirmação mais forte da mesma invariante: é constante, não apenas pequena."""
    client, middleware = _harness("200/second")

    _knock(client, range(100))
    time.sleep(1.1)
    _knock(client, [1])
    poucos = _retained(middleware)

    _knock(client, range(100, 600))
    time.sleep(1.1)
    _knock(client, [2])
    muitos = _retained(middleware)

    assert muitos <= poucos + 1, f"depois de 100 clientes: {poucos}; depois de 600: {muitos}"


def test_um_cliente_activo_continua_a_ser_limitado() -> None:
    """O teste que impede a correcção de comprar memória com permissividade.

    Se o esquecimento apanhasse uma janela ainda aberta, um chamador activo ganhava balde novo —
    trocar-se-ia uma fuga de memória por um limite que não limita.
    """
    client, middleware = _harness("3/minute")
    headers = {"X-Forwarded-For": "203.0.113.7"}

    codes = [client.get("/ping", headers=headers).status_code for _ in range(5)]

    assert codes == [200, 200, 200, 429, 429]


def test_o_esquecimento_de_outros_nao_reabre_o_balde_de_quem_esta_a_bater() -> None:
    """Inundar com endereços distintos não pode servir de desvio ao limite próprio."""
    client, middleware = _harness("3/minute")
    headers = {"X-Forwarded-For": "203.0.113.9"}

    assert [client.get("/ping", headers=headers).status_code for _ in range(3)] == [200, 200, 200]
    _knock(client, range(2000, 2400))  # muitos vizinhos a aparecer e a desaparecer

    assert client.get("/ping", headers=headers).status_code == 429


def test_um_cliente_recomeca_com_balde_novo_depois_de_a_janela_passar() -> None:
    """Contrapartida do anterior: esquecer é exactamente o que já acontecia, não é mais permissivo."""
    client, middleware = _harness("2/second")
    headers = {"X-Forwarded-For": "198.51.100.4"}

    assert [client.get("/ping", headers=headers).status_code for _ in range(3)] == [200, 200, 429]
    time.sleep(1.1)

    assert client.get("/ping", headers=headers).status_code == 200
