"""Coverage — importer helper functions (defensive/type-guard branches)."""

from __future__ import annotations

from otm_artifact_import import ai_import_corpus as aic
from otm_artifact_import import openapi_import as oi


def test_collect_servers_v2_no_host() -> None:
    assert oi._collect_servers_v2({"basePath": "/v1", "schemes": ["https"]}) == []


def test_collect_servers_v2_with_host_relative_base() -> None:
    out = oi._collect_servers_v2({"host": "api.example.com", "basePath": "v1", "schemes": ["https", 5]})
    assert any("api.example.com" in u for u in out)


def test_security_hints_v3_schemes_not_dict() -> None:
    assert oi._security_hints_v3({"components": {"securitySchemes": ["bad"]}}) == (False, [])


def test_security_hints_v3_scheme_entry_not_dict_skipped() -> None:
    present, names = oi._security_hints_v3(
        {"components": {"securitySchemes": {"good": {"type": "http"}, "bad": "x", "noType": {}}}}
    )
    assert present and "good:http" in names and "noType" in names


def test_security_hints_v2_not_dict() -> None:
    assert oi._security_hints_v2({"securityDefinitions": ["bad"]}) == (False, [])


def test_security_hints_v2_ok() -> None:
    present, names = oi._security_hints_v2({"securityDefinitions": {"k": {"type": "apiKey"}}})
    assert present and names == ["k"]


def test_operation_security_required_variants() -> None:
    assert oi._operation_security_required("not-a-dict") is None  # type: ignore[arg-type]
    assert oi._operation_security_required({"security": [{"x": []}]}) is True
    assert oi._operation_security_required({}) is None


def test_count_operations_edges() -> None:
    assert oi._count_operations(None) == (0, [])
    n, detail = oi._count_operations(
        {"/p": {"get": {"operationId": "g"}, "bogus": 1, "post": {}}, "/q": "not-a-dict"}
    )
    # get -> "g"; post (empty dict is still a dict) -> "post /p"; bogus(int) and /q(str) skipped
    assert n == 2 and "g" in detail


def test_root_security_required() -> None:
    assert oi._root_security_required({"security": [{"k": []}]}) is True
    assert oi._root_security_required({}) is False


# --- ai_import_corpus signal builders ---


def test_corpus_openapi_rich() -> None:
    data = {
        "openapi": "3.0.0",
        "info": {"title": "LLM Chat API", "description": "RAG vector embedding completion"},
        "paths": {
            "/chat/completions": {"post": {"operationId": "createCompletion"}},
            "/embeddings": {"post": {"operationId": "embed"}},
            "/admin/models": {"get": {"operationId": "listModels"}},
        },
        "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
    }
    out = aic.build_openapi_import_signals_corpus(data)
    assert isinstance(out, str)


def test_corpus_kubernetes_rich() -> None:
    docs = [
        {"kind": "Deployment", "metadata": {"name": "llm-gateway"},
         "spec": {"template": {"spec": {"containers": [{"image": "vllm/serve:1", "name": "llm"}]}}}},
        {"kind": "Service", "metadata": {"name": "vector-db"}, "spec": {"type": "LoadBalancer"}},
        {"kind": "Ingress", "metadata": {"name": "i"}, "spec": {"rules": [{"host": "ai.example.com"}]}},
    ]
    assert isinstance(aic.build_kubernetes_import_signals_corpus(docs), str)


def test_corpus_terraform_and_helm() -> None:
    tf = 'resource "aws_sagemaker_endpoint" "ml" {}\nresource "aws_s3_bucket" "vectors" { bucket = "embeddings" }\n'
    assert isinstance(aic.build_terraform_import_signals_corpus(tf), str)
    helm = "image:\n  repository: qdrant/qdrant\nenv:\n  - name: OPENAI_API_KEY\n    value: sk\n"
    assert isinstance(aic.build_helm_import_signals_corpus(helm), str)


def test_import_openapi_unknown_format() -> None:
    # No `openapi`/`swagger` root key -> "formato desconhecido" path.
    r = oi.import_openapi_text("foo: bar\nbaz: 1\n", filename="not_api.yaml")
    assert r.document is not None
    assert r.unknowns


def test_import_openapi_root_security_authenticated() -> None:
    spec = (
        "openapi: 3.0.0\ninfo: {title: A, version: '1'}\n"
        "security: [{bearer: []}]\n"
        "paths: {/p: {get: {operationId: p}}}\n"
        "components: {securitySchemes: {bearer: {type: http, scheme: bearer}}}\n"
    )
    r = oi.import_openapi_text(spec, filename="rootsec.yaml")
    assert r.document is not None


def test_import_openapi_all_paths_secured() -> None:
    spec = (
        "openapi: 3.0.0\ninfo: {title: A, version: '1'}\n"
        "paths:\n"
        "  /a: {get: {operationId: a, security: [{k: []}]}}\n"
        "  /b: {post: {operationId: b, security: [{k: []}]}}\n"
        "components: {securitySchemes: {k: {type: apiKey, in: header, name: X}}}\n"
    )
    r = oi.import_openapi_text(spec, filename="allsec.yaml")
    assert r.document is not None


def test_corpus_openapi_normalized_ai_surface() -> None:
    data = {
        "openapi": "3.0.0",
        "info": {"title": "AI", "description": "x"},
        "paths": {
            "/completions": {"post": {"operationId": "complete"}},  # completion api (no 'chat')
            "/vector-search": {"post": {"operationId": "vsearch"}},  # vector search
            "/predict": {"post": {"operationId": "predict"}},        # inference
        },
        "tags": [{"name": "ml"}, {"name": "ai"}, {"notname": 1}],
    }
    out = aic.build_openapi_import_signals_corpus(data)
    assert "completion api" in out and "vector search" in out and "inference" in out
    assert "ml" in out and "ai" in out


def test_corpus_kubernetes_model_annotations() -> None:
    docs = [
        {
            "kind": "Deployment",
            "metadata": {
                "name": "llm",
                "labels": {"app": "llm"},
                "annotations": {"model.serving/engine": "vllm", "sidecar.istio.io/inject": "true"},
            },
            "spec": {"template": {"spec": {"containers": [{"name": "c", "image": "vllm:1"}]}}},
        }
    ]
    out = aic.build_kubernetes_import_signals_corpus(docs)
    assert "model.serving/engine" in out or "vllm" in out


def test_corpus_kubernetes_malformed_text_handled() -> None:
    # build_kubernetes corpus path tolerates non-parseable docs (defensive yaml handling).
    assert isinstance(aic.build_kubernetes_import_signals_corpus([{"kind": "X"}, "not-a-dict"]), str)


def test_corpus_empty_inputs() -> None:
    assert isinstance(aic.build_openapi_import_signals_corpus({}), str)
    assert isinstance(aic.build_kubernetes_import_signals_corpus([]), str)
    assert isinstance(aic.build_terraform_import_signals_corpus(""), str)
    assert isinstance(aic.build_helm_import_signals_corpus(""), str)
