"""`otm import k8s` must read Ingress hosts from `.spec.rules`, where Kubernetes puts them.

`_handle_ingress` read `doc["rules"]` — the document root — so for every valid
`networking.k8s.io/v1` Ingress the drafted component recorded `hosts: []` and the importer
emitted the *opposite* of the manifest: "Ingress `shop-ingress` sem hosts explícitos no
manifest". That sentence is then copied into `business_context.assumptions`, so a false claim
travelled with the saved model into every downstream report and export, and the public
hostnames — the exposure surface a threat modeller most needs — were lost.

The positive branch was unreachable for any valid manifest: it only fired for root-level
`rules`, which Kubernetes does not accept. The sibling `_handle_service` already used
`doc["spec"]`, and `_find_ingress_spec` even carries the comment "Ingress rules live under
`.spec.rules`, not at the document root." — one call site was fixed and this one was missed.
"""

from __future__ import annotations

from typing import Any

import pytest
from otm_artifact_import import import_kubernetes_text
from otm_artifact_import.types import ArtifactImportResult

_INGRESS = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop-ingress
spec:
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: orders-api
                port:
                  number: 80
    - host: admin.example.com
"""

_INGRESS_WITHOUT_HOSTS = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hostless-ingress
spec:
  defaultBackend:
    service:
      name: orders-api
      port:
        number: 80
"""


@pytest.fixture
def imported() -> ArtifactImportResult:
    return import_kubernetes_text(_INGRESS, filename="ingress.yaml")


def _ingress_component(result: ArtifactImportResult) -> Any:
    return next(c for c in result.document.components if c.id.startswith("ing"))


def _assumptions(result: ArtifactImportResult) -> list[str]:
    context = result.document.business_context
    return list(context.assumptions) if context else []


def test_the_hosts_reach_the_drafted_component(imported: ArtifactImportResult) -> None:
    assert _ingress_component(imported).metadata["hosts"] == ["shop.example.com", "admin.example.com"]


def test_the_positive_inference_is_emitted(imported: ArtifactImportResult) -> None:
    messages = [record.message for record in imported.inferences if "shop-ingress" in record.message]

    assert any("com host(s) shop.example.com, admin.example.com" in message for message in messages)


def test_the_false_hostless_claim_is_gone(imported: ArtifactImportResult) -> None:
    """This sentence was the exact opposite of the manifest."""
    assert [m for m in _assumptions(imported) if "sem hosts explícitos" in m] == []


def test_the_hostnames_survive_into_the_saved_model(imported: ArtifactImportResult) -> None:
    """The assumptions block is what travels with the draft into reports and exports."""
    assert any("shop.example.com" in assumption for assumption in _assumptions(imported))


def test_an_ingress_that_really_has_no_hosts_still_says_so() -> None:
    """The honest version of the message must survive: `defaultBackend` alone declares no host."""
    result = import_kubernetes_text(_INGRESS_WITHOUT_HOSTS, filename="ingress.yaml")
    messages = [record.message for record in result.inferences if "hostless-ingress" in record.message]

    assert any("sem hosts explícitos" in message for message in messages)


def test_an_ingress_without_hosts_records_an_empty_list() -> None:
    result = import_kubernetes_text(_INGRESS_WITHOUT_HOSTS, filename="ingress.yaml")

    assert _ingress_component(result).metadata["hosts"] == []


def test_the_backend_service_reference_still_resolves(imported: ArtifactImportResult) -> None:
    """`.spec.rules` was already read correctly for backends; that must not regress."""
    assert any("orders-api" in unknown for unknown in imported.unknowns)
