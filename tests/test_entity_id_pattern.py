"""IDs de entidades canónicas: padrão alargado (underscores, ponto, dígito inicial)."""

from __future__ import annotations

import pytest
from otm_core_schema import ThreatModelDocument, create_blank_document
from pydantic import ValidationError


def _minimal_with_components_flows(payload: dict) -> ThreatModelDocument:
    return ThreatModelDocument.model_validate(payload)


def test_data_flow_optional_name_accepts_unicode_and_symbols() -> None:
    """Nome de fluxo é etiqueta humana; não usa ENTITY_ID_PATTERN."""
    base = create_blank_document().model_dump(mode="json", by_alias=True)
    base["assets"] = []
    base["trust_boundaries"] = []
    base["components"] = [
        {"id": "a", "name": "A", "kind": "process"},
        {"id": "b", "name": "B", "kind": "process"},
    ]
    base["data_flows"] = [
        {
            "id": "f1",
            "from_component": "a",
            "to_component": "b",
            "name": "Requisições — café & € (100%)",
        },
    ]
    doc = _minimal_with_components_flows(base)
    assert doc.data_flows[0].name == "Requisições — café & € (100%)"


def test_data_flow_optional_name_blank_becomes_none() -> None:
    base = create_blank_document().model_dump(mode="json", by_alias=True)
    base["assets"] = []
    base["trust_boundaries"] = []
    base["components"] = [
        {"id": "a", "name": "A", "kind": "process"},
        {"id": "b", "name": "B", "kind": "process"},
    ]
    base["data_flows"] = [
        {"id": "f1", "from_component": "a", "to_component": "b", "name": "   "},
    ]
    doc = _minimal_with_components_flows(base)
    assert doc.data_flows[0].name is None


def test_entity_id_accepts_x_x_x_dots_and_leading_digit() -> None:
    base = create_blank_document().model_dump(mode="json", by_alias=True)
    base["assets"] = []
    base["trust_boundaries"] = []
    base["components"] = [
        {"id": "x_x_x", "name": "Três x", "kind": "process"},
        {"id": "api.v2", "name": "API versão 2", "kind": "process"},
        {"id": "9east", "name": "Serviço legacy", "kind": "other"},
    ]
    base["data_flows"] = [
        {"id": "flow_1.0-beta", "from_component": "x_x_x", "to_component": "api.v2"},
        {"id": "f2", "from_component": "api.v2", "to_component": "9east"},
    ]
    doc = _minimal_with_components_flows(base)
    assert [c.id for c in doc.components] == ["x_x_x", "api.v2", "9east"]
    assert {f.id for f in doc.data_flows} == {"flow_1.0-beta", "f2"}


@pytest.mark.parametrize(
    "bad_id",
    [
        "",
        "no spaces",
        "a/b",
        "a\\b",
        ".startdot",
        "-startdash",
        "oops<tag>",
    ],
)
def test_entity_id_rejects_unsafe_or_invalid(bad_id: str) -> None:
    base = create_blank_document().model_dump(mode="json", by_alias=True)
    base["assets"] = []
    base["trust_boundaries"] = []
    base["components"] = [{"id": bad_id, "name": "X", "kind": "process"}]
    base["data_flows"] = []
    with pytest.raises(ValidationError):
        _minimal_with_components_flows(base)
