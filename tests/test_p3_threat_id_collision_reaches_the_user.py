"""A recusa por colisão de ids tem de chegar ao utilizador na convenção do produto.

`assert_threat_ids_are_injective` recusa um documento em que dois sujeitos distintos produzem o
mesmo id de ameaça. A recusa está certa e é deliberada -- antes dela o par era colapsado em
silêncio, e o gate de drift julgava uma ameaça substituída em vez de acrescentada.

O que estava errado era a entrega. A recusa saía como `ValueError` cru, e ninguém a traduzia:

* `POST /v1/models/validate` devolve **200 `{"valid": true}`** para o documento, e
  `POST /v1/models/analyze` devolve **500 INTERNAL_ERROR** para o mesmo documento -- um 5xx culpa
  o servidor por uma entrada que o cliente pode corrigir, e a única frase que dizia como a
  corrigir ficava no log do servidor;
* `otm analyze` despejava um traceback do Python, em vez do `Failure: / Likely cause: / Next step:`
  que o mesmo comando já produz para um pack inexistente -- e o traceback imprime o **caminho
  absoluto** de quem corre o comando.

O documento deste teste é `examples/minimal.otm.yaml` com duas linhas acrescentadas, para que a
premissa "isto é um documento que o produto aceita" não dependa de nada escrito à mão.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from otm_api.main import app
from otm_cli.main import cli_app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]


def _colliding_document() -> dict[str, Any]:
    """O exemplo mínimo mais um componente `flow_svc` e um fluxo `svc`: `eng_flow_svc_*` para ambos."""
    doc = copy.deepcopy(yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8")))
    doc["components"].append({"id": "flow_svc", "name": "Flow Svc", "kind": "process", "in_trust_boundary": "vpc"})
    for boundary in doc["trust_boundaries"]:
        if boundary["id"] == "vpc":
            boundary.setdefault("member_component_ids", []).append("flow_svc")
    doc["data_flows"].append(
        {"id": "svc", "name": "svc", "from_component": "flow_svc", "to_component": doc["components"][0]["id"]}
    )
    return doc


@pytest.fixture(scope="module")
def colliding() -> dict[str, Any]:
    return _colliding_document()


def test_o_documento_do_caso_e_aceite_pelo_validador(colliding: dict[str, Any]) -> None:
    """Sanidade: sem isto o teste provaria apenas que um documento inválido falha."""
    response = TestClient(app, raise_server_exceptions=False).post("/v1/models/validate", json={"document": colliding})

    assert response.status_code == 200, response.text
    assert response.json()["valid"] is True


def test_a_analise_recusa_com_4xx_e_diz_porque(colliding: dict[str, Any]) -> None:
    response = TestClient(app, raise_server_exceptions=False).post("/v1/models/analyze", json={"document": colliding})

    assert 400 <= response.status_code < 500, (
        f"entrada corrigível pelo cliente devolvida como {response.status_code}: {response.text[:200]}"
    )
    body = response.text
    assert "flow_svc" in body and "svc" in body, f"a resposta não nomeia os sujeitos em colisão: {body[:300]}"


def test_o_cli_falha_na_convencao_do_produto_sem_traceback(colliding: dict[str, Any], tmp_path: Path) -> None:
    model = tmp_path / "collide.otm.yaml"
    model.write_text(yaml.safe_dump(colliding, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = CliRunner().invoke(cli_app, ["analyze", str(model)])
    # `result.output`, não `result.stdout`: o erro sai em stderr, e ler o fluxo errado dá a string
    # vazia — contra a qual `"Traceback" not in output` passa sem provar nada.
    output = result.output

    assert output, "o CLI não escreveu nada; o teste seguinte não provaria nada"
    assert result.exit_code == 1, output
    assert "Traceback" not in output, f"o CLI despejou um traceback do Python:\n{output[:600]}"
    assert "Failure:" in output and "Next step:" in output, (
        f"o erro não segue a convenção `Failure:/Likely cause:/Next step:`:\n{output[:600]}"
    )
    assert "flow_svc" in output, f"o erro não nomeia o sujeito a renomear:\n{output[:600]}"
