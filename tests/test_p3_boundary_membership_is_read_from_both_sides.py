"""Declarar a associação do lado da fronteira tem de valer o mesmo que do lado do componente.

O schema aceita as duas formas e valida ambas: `Component.in_trust_boundary` e
`TrustBoundary.member_component_ids`. `resolve_component_boundaries` existe precisamente para as
juntar, e o motor usa-o — é por isso que `structural.py` reporta o cruzamento de fronteira nos dois
casos.

Três consumidores liam o campo do componente directamente e ignoravam o outro lado:

* o relatório premium imprimia **"Principais trust boundaries: _Nenhuma listada._"** para um
  documento cujas fronteiras estão declaradas do lado da fronteira — no mesmo relatório que
  reportava `trust_perimeter_crossing`, uma contradição interna;
* `/v1/models/compare` perdia **por inteiro** o achado "novo fluxo cruza fronteiras";
* e o achado do componente utilizador novo numa fronteira desaparecia da mesma maneira.

O oráculo é a equivalência, não o texto: o mesmo modelo escrito das duas formas tem de produzir a
mesma resposta. Assim o teste continua válido quando a redacção mudar.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))
sys.path.insert(0, str(_ROOT / "apps" / "api"))


def _model(*, boundary_side: bool, with_flow: bool = True, user_component: bool = False) -> dict[str, Any]:
    components: list[dict[str, Any]] = [
        {"id": "web", "name": "Web tier", "kind": "process"},
        {"id": "db", "name": "DB tier", "kind": "datastore"},
    ]
    boundaries: list[dict[str, Any]] = [
        {"id": "tb_dmz", "name": "DMZ", "boundary_scenario": "boundary_client_to_server"},
        {"id": "tb_core", "name": "Core", "boundary_scenario": "boundary_app_to_database"},
    ]
    if user_component:
        components.append({"id": "person", "name": "Cliente", "kind": "user"})

    if boundary_side:
        boundaries[0]["member_component_ids"] = ["web"] + (["person"] if user_component else [])
        boundaries[1]["member_component_ids"] = ["db"]
    else:
        components[0]["in_trust_boundary"] = "tb_dmz"
        components[1]["in_trust_boundary"] = "tb_core"
        if user_component:
            components[2]["in_trust_boundary"] = "tb_dmz"

    return {
        "model": {"schema_version": "1.1.0"},
        "metadata": {"title": "t"},
        "components": components,
        "trust_boundaries": boundaries,
        "data_flows": [{"id": "f1", "name": "query", "from_component": "web", "to_component": "db"}]
        if with_flow
        else [],
    }


@pytest.fixture(scope="module")
def client() -> Any:
    import logging

    logging.disable(logging.CRITICAL)
    from fastapi.testclient import TestClient
    from otm_api.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_as_duas_formas_sao_ambas_validas(client: Any) -> None:
    """Sanidade: se uma delas fosse recusada, a equivalência não significaria nada."""
    for boundary_side in (True, False):
        response = client.post("/v1/models/validate", json={"document": _model(boundary_side=boundary_side)})
        assert response.status_code == 200, response.text[:200]
        assert response.json()["valid"] is True


def _boundary_section(client: Any, *, boundary_side: bool) -> list[str]:
    markdown = client.post(
        "/v1/reports/premium",
        json={
            "level": "deep",
            "output_format": "markdown",
            "run_analysis": True,
            "document": _model(boundary_side=boundary_side),
        },
    ).text
    lines = markdown.splitlines()
    start = next(n for n, line in enumerate(lines) if "Principais trust boundaries" in line)
    return [line.strip() for line in lines[start + 1 : start + 8] if line.strip() and not line.startswith("###")]


def test_o_relatorio_premium_lista_as_fronteiras_declaradas_do_lado_da_fronteira(client: Any) -> None:
    assert _boundary_section(client, boundary_side=True) == _boundary_section(client, boundary_side=False)


def _structural_insights(client: Any, *, boundary_side: bool, user_component: bool = False) -> list[str]:
    body = client.post(
        "/v1/models/compare",
        json={
            "baseline": _model(boundary_side=boundary_side, with_flow=False, user_component=False),
            "revised": _model(boundary_side=boundary_side, with_flow=True, user_component=user_component),
        },
    ).json()
    return sorted(body.get("structural_insights", []))


def test_o_compare_ve_o_cruzamento_de_fronteira_nas_duas_formas(client: Any) -> None:
    assert _structural_insights(client, boundary_side=True) == _structural_insights(client, boundary_side=False)


def test_o_compare_ve_o_componente_utilizador_novo_nas_duas_formas(client: Any) -> None:
    """Aqui a igualdade das listas **não** vale, e a razão é do documento, não do código.

    Acrescentar um componente a um modelo cuja pertença é declarada do lado da fronteira edita a
    própria fronteira, por isso o diff reporta — correctamente — uma fronteira alterada que o
    outro caso não tem. Os dois documentos não são equivalentes: um altera um componente, o outro
    altera dois objectos. O que tem de valer nos dois é o achado sobre o utilizador novo.
    """
    for boundary_side in (True, False):
        insights = _structural_insights(client, boundary_side=boundary_side, user_component=True)
        assert any("utilizador" in insight.lower() for insight in insights), (
            f"pertença declarada do lado {'da fronteira' if boundary_side else 'do componente'}: "
            f"nenhum achado sobre o componente utilizador novo: {insights}"
        )
