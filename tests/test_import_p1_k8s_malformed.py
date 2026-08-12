"""YAML malformado tem de falhar da mesma maneira em todos os importadores.

`load_object_from_text` (OpenAPI, OTM nativo) traduz o erro do parser em `ValueError`;
`iter_yaml_documents` (Kubernetes) deixava a `yaml.YAMLError` escapar. A camada HTTP só apanha
`ValueError`, por isso o mesmo ficheiro dava 400 num endpoint e 500 no outro.
"""

from __future__ import annotations

import io

import pytest
from otm_artifact_import import import_kubernetes_text, import_openapi_text
from otm_artifact_import._yamljson import iter_yaml_documents

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_BROKEN = "a: : : :\n\t- broken"


def test_iter_yaml_documents_raises_value_error_on_broken_yaml() -> None:
    with pytest.raises(ValueError, match="YAML"):
        list(iter_yaml_documents(_BROKEN))


def test_both_importers_reject_the_same_text_the_same_way() -> None:
    with pytest.raises(ValueError):
        import_openapi_text(_BROKEN)
    with pytest.raises(ValueError):
        import_kubernetes_text(_BROKEN)


def test_valid_multi_document_manifests_still_iterate() -> None:
    text = "kind: Service\nmetadata:\n  name: a\n---\nkind: Deployment\nmetadata:\n  name: b\n"
    kinds = [d.get("kind") for d in iter_yaml_documents(text)]
    assert kinds == ["Service", "Deployment"]


def test_kubernetes_endpoint_answers_400_like_the_openapi_endpoint() -> None:
    # `raise_server_exceptions=False` para o teste observar o 500 em vez de a excepção do
    # parser subir pelo próprio TestClient — é o código de estado que está em causa.
    client = TestClient(app, raise_server_exceptions=False)
    codes = {}
    for route, name in (("/v1/imports/openapi", "spec.yaml"), ("/v1/imports/kubernetes", "manifests.yaml")):
        r = client.post(route, files={"file": (name, io.BytesIO(_BROKEN.encode("utf-8")), "application/yaml")})
        codes[route] = r.status_code
    assert codes == {"/v1/imports/openapi": 400, "/v1/imports/kubernetes": 400}
