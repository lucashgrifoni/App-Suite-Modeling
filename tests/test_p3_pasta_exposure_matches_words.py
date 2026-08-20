""" "Componente exposto" não pode ser decidido por subcadeia.

A lente PASTA marcava um componente como caminho de ataque quando o seu nome ou tecnologia
contivesse `api`, `gateway`, `public`, `internet` ou `edge` — em subcadeia. `Ledger` contém `edge`;
`terapia` e `rapidez` contêm `api`. Um livro-razão interno passava a ser anunciado como
"componente exposto pode ser pivô para movimento lateral", com ameaça de elevação de privilégio.

`has_any_token` já existe e é o comparador que o projecto usa para os termos curtos com este
problema. Trocar às cegas trocaria falsos positivos por falsos negativos — `apis internas` e
`gateways` deixariam de casar — por isso os plurais entram explicitamente.

Medido nos 38 templates distribuídos antes de escolher: a troca retira exactamente **2**
correspondências, ambas `Ledger`, e não perde nem ganha mais nenhuma.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _attack_path_ids(name: str, technology: str | None = None) -> set[str]:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    component = {"id": "c1", "name": name, "kind": "process"}
    if technology:
        component["technology"] = technology
    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Sistema"},
            "components": [component, {"id": "outro", "name": "Outro", "kind": "datastore"}],
        }
    )
    result = analyze_document(document, methodology="pasta")
    return {h.id for h in result.heuristic_threats if h.id.startswith("pasta_attack_path_")}


@pytest.mark.parametrize("name", ["Ledger", "Ledger / transações", "Terapia", "Rapidez", "Cannon"])
def test_uma_palavra_que_contem_o_termo_nao_e_um_componente_exposto(name: str) -> None:
    assert not _attack_path_ids(name), f"`{name}` anunciado como componente exposto"


@pytest.mark.parametrize(
    ("name", "technology"),
    [
        ("API de encomendas", None),
        ("Gateway de borda", None),
        ("Portal", "public internet"),
        ("Servico", "edge router"),
        ("Camada de APIs", None),
        ("Cluster de gateways", None),
    ],
)
def test_um_componente_genuinamente_exposto_continua_a_contar(name: str, technology: str | None) -> None:
    """Incluindo os plurais: trocar para token sem eles seria trocar um erro por outro."""
    assert _attack_path_ids(name, technology), f"`{name}` deixou de ser reconhecido como exposto"


def test_os_templates_distribuidos_so_perdem_o_falso_positivo() -> None:
    """A medição que justificou o desenho, presa para não se perder."""
    import yaml
    from otm_core_schema import ThreatModelDocument
    from otm_core_schema.ai_context import has_any_token
    from otm_industry_packs.loader import list_template_ids, load_template_yaml

    substring_terms = ("api", "gateway", "public", "internet", "edge")
    token_terms = ("api", "apis", "gateway", "gateways", "public", "internet", "edge")
    lost = []
    for template_id in list_template_ids():
        document = ThreatModelDocument.model_validate(yaml.safe_load(load_template_yaml(template_id)))
        for component in document.components:
            text = f"{component.name} {(component.technology or '')}".lower()
            if any(term in text for term in substring_terms) and not has_any_token(text, token_terms):
                lost.append(component.name)

    assert all("ledger" in name.lower() for name in lost), f"perdeu correspondências legítimas: {lost}"
