"""Um Ingress que encaminha por `defaultBackend` não pode perder a sua aresta.

`_ingress_backend_service_names` lia apenas `spec.rules[].http.paths[].backend`.
`spec.defaultBackend` é uma forma válida e comum — o *catch-all* de um Ingress de serviço único —
e ficava de fora.

Medido em dois manifestos **semanticamente equivalentes**:

    defaultBackend      1 fluxo   (só cliente → ingress)
    rules[] equivalente 2 fluxos  (cliente → ingress, ingress → service)

O fluxo perdido é o que liga o Ingress ao Service, e com ele desaparecem as ameaças desse
percurso. Pior do que o número: `unknowns` ficava **vazio**, por isso o rascunho parecia completo.
Quem o revê vê tráfego a chegar a um Ingress que não vai a lado nenhum, e nada lhe diz que faltou
alguma coisa — que é exactamente o modo de falha que `unknowns` existe para evitar.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_SERVICE = """---
apiVersion: v1
kind: Service
metadata: {name: web}
spec: {type: ClusterIP}
"""

_DEFAULT_BACKEND = (
    """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: {name: web}
spec:
  defaultBackend:
    service:
      name: web
      port: {number: 80}
"""
    + _SERVICE
)

_RULES = (
    """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: {name: web}
spec:
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend: {service: {name: web, port: {number: 80}}}
"""
    + _SERVICE
)


def _edges(manifest: str) -> set[tuple[str, str]]:
    from otm_artifact_import.k8s_import import import_kubernetes_text

    document = import_kubernetes_text(manifest).document
    return {(f.from_component, f.to_component) for f in document.data_flows}


def test_a_forma_com_rules_liga_o_ingress_ao_servico() -> None:
    """Sanidade: é contra este resultado que a outra forma é comparada."""
    assert ("ing_web", "svc_web") in _edges(_RULES)


def test_o_default_backend_produz_o_mesmo_grafo_que_as_rules() -> None:
    assert _edges(_DEFAULT_BACKEND) == _edges(_RULES)


def test_o_default_backend_com_rules_junta_os_dois_destinos() -> None:
    """Um Ingress pode ter os dois; nenhum deles pode apagar o outro."""
    from otm_artifact_import.k8s_import import import_kubernetes_text

    manifest = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: {name: web}
spec:
  defaultBackend:
    service: {name: fallback, port: {number: 80}}
  rules:
    - http:
        paths:
          - path: /api
            pathType: Prefix
            backend: {service: {name: api, port: {number: 80}}}
---
apiVersion: v1
kind: Service
metadata: {name: fallback}
spec: {type: ClusterIP}
---
apiVersion: v1
kind: Service
metadata: {name: api}
spec: {type: ClusterIP}
"""
    targets = {to for _, to in _edges(manifest)}

    assert {"svc_fallback", "svc_api"} <= targets, targets
    assert import_kubernetes_text(manifest).document is not None
