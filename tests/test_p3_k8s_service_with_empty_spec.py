"""Um `spec:` sem corpo não pode rebentar o importador de Kubernetes.

`kind: Service` com `spec:` presente e vazia é YAML válido e um estado banal: é o que fica quando
alguém comenta o corpo da spec para desligar temporariamente um `type: LoadBalancer`. O YAML dá
`spec = None`, e `doc.get("spec", {})` devolve `None` -- o valor por omissão só se aplica quando a
**chave** falta, não quando o valor é nulo.

O ficheiro tem `_as_dict` precisamente para isto e usa-o em todo o lado; esta linha ficou de fora.
Os outros `kind` (Deployment, Ingress, StatefulSet, ConfigMap) sobrevivem ao mesmo manifesto, o
que confirma que é um sítio esquecido e não uma decisão.

O resultado é `AttributeError` a subir por `otm import k8s` como traceback, para um ficheiro que
`kubectl apply` aceitaria.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_EMPTY_SPEC = "apiVersion: v1\nkind: Service\nmetadata:\n  name: web\nspec:\n"
_EXPLICIT_EMPTY = "apiVersion: v1\nkind: Service\nmetadata:\n  name: web\nspec: {}\n"


def test_o_yaml_do_caso_da_mesmo_spec_nula() -> None:
    """Sanidade: a premissa é `spec = None`, não `spec` ausente."""
    import yaml

    parsed = yaml.safe_load(_EMPTY_SPEC)
    assert "spec" in parsed
    assert parsed["spec"] is None


def test_o_service_com_spec_vazia_importa() -> None:
    from otm_artifact_import.k8s_import import import_kubernetes_text

    result = import_kubernetes_text(_EMPTY_SPEC)

    assert [c.name for c in result.document.components]


def test_da_o_mesmo_que_a_spec_vazia_explicita() -> None:
    """`spec:` e `spec: {}` dizem a mesma coisa; o importador tem de concordar."""
    from otm_artifact_import.k8s_import import import_kubernetes_text

    implicit = import_kubernetes_text(_EMPTY_SPEC).document
    explicit = import_kubernetes_text(_EXPLICIT_EMPTY).document

    assert [(c.id, c.name, c.kind) for c in implicit.components] == [
        (c.id, c.name, c.kind) for c in explicit.components
    ]


@pytest.mark.parametrize("kind", ["Service", "Deployment", "Ingress", "StatefulSet", "ConfigMap"])
def test_nenhum_kind_rebenta_com_spec_vazia(kind: str) -> None:
    from otm_artifact_import.k8s_import import import_kubernetes_text

    import_kubernetes_text(f"apiVersion: v1\nkind: {kind}\nmetadata:\n  name: x\nspec:\n")
