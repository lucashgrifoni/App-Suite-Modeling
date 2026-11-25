"""O contrato publicado promete uma forma de erro que a API nunca devolve.

`contracts/openapi.json` documenta o 422 de **16 das 19** operações como `HTTPValidationError` —
o esquema por omissão do FastAPI, `{detail: ValidationError[]}`. A API não devolve isso em lado
nenhum. Devolve duas formas, ambas deliberadas e ambas com testes próprios:

* envelope do pedido (`problem_detail`): `{code, message, status, errors}` — sem chave `detail`;
* domínio (`error_detail` dentro de `HTTPException`): `{detail: {code, message, errors}}`, em que
  `detail` é um **objecto**, não um array.

Isto não é documentação a envelhecer: `apps/web` gera os seus tipos TypeScript deste ficheiro
(`npm run contracts:generate`), portanto um cliente escrito contra o contrato lê `detail[0].msg`
num objecto que não tem `detail`, ou que o tem como dicionário.

O contrato é gerado da app (`scripts/export_openapi.py`), por isso a correcção é declarar as
respostas reais nas rotas e regenerar — não editar o JSON à mão.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))
sys.path.insert(0, str(_ROOT / "apps" / "api"))

_CONTRACT = _ROOT / "contracts" / "openapi.json"


def _spec() -> dict:
    return json.loads(_CONTRACT.read_text(encoding="utf-8"))


def _client():
    import logging

    logging.disable(logging.CRITICAL)
    from fastapi.testclient import TestClient
    from otm_api.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_o_contrato_documenta_algum_422() -> None:
    """Sanidade: sem isto o teste seguinte passaria por não haver nada declarado."""
    documented = [
        (path, method)
        for path, ops in _spec()["paths"].items()
        for method, op in ops.items()
        if "422" in op.get("responses", {})
    ]

    assert len(documented) >= 10, documented


def test_nenhuma_operacao_promete_o_422_por_omissao_do_fastapi() -> None:
    """`HTTPValidationError` é `{detail: ValidationError[]}`, forma que esta API nunca produz."""
    offenders = [
        f"{method.upper()} {path}"
        for path, ops in _spec()["paths"].items()
        for method, op in ops.items()
        if "HTTPValidationError" in json.dumps(op.get("responses", {}).get("422", {}))
    ]

    assert not offenders, f"operações que prometem o esquema por omissão: {offenders[:6]} (total {len(offenders)})"


@pytest.mark.parametrize(
    ("body", "expected_top_level"),
    [({}, {"code", "message", "status"}), ({"document": {"nope": 1}}, {"detail"})],
    ids=["envelope", "dominio"],
)
def test_as_duas_formas_reais_de_422(body: dict, expected_top_level: set[str]) -> None:
    """A premissa da correcção: são estas as formas que a API produz."""
    response = _client().post("/v1/models/validate", json=body)

    assert response.status_code == 422
    assert expected_top_level <= set(response.json())


def test_o_detail_do_dominio_e_um_objecto_e_nao_uma_lista() -> None:
    """O ponto exacto em que um cliente gerado do contrato parte."""
    payload = _client().post("/v1/models/validate", json={"document": {"nope": 1}}).json()

    assert isinstance(payload["detail"], dict), type(payload["detail"])


def test_o_contrato_no_disco_esta_sincronizado_com_a_app() -> None:
    """Sem isto, corrigir a app deixaria o ficheiro publicado desactualizado."""
    from otm_api.main import app

    assert json.loads(json.dumps(app.openapi())) == _spec(), (
        "contracts/openapi.json difere do que a app gera; correr `python scripts/export_openapi.py`"
    )
