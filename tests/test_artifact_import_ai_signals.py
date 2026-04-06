"""Sinais IA reforçados por `import_signals_corpus` (OpenAPI/K8s/Terraform/Helm)."""

from __future__ import annotations

from otm_artifact_import import (
    import_helm_text,
    import_kubernetes_text,
    import_openapi_text,
    import_terraform_text,
)
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document
from otm_threat_engine.ai_modeling.signals import collect_ai_signals_from_document


def test_openapi_import_populates_import_corpus_and_boosts_plot4ai_signals() -> None:
    spec = """
openapi: 3.0.0
info:
  title: Gateway IA interno
  version: "1.0"
paths:
  /v1/chat/completions:
    post:
      operationId: chatCompletion
  /v1/embeddings:
    post:
      operationId: embedDocuments
"""
    result = import_openapi_text(spec, filename="openapi.yaml")
    assert result.document.import_signals_corpus
    corpus = result.document.import_signals_corpus
    assert "chat completion" in corpus or "embed" in corpus
    sig = collect_ai_signals_from_document(result.document)
    assert sig.model_interaction
    assert sig.vector_embedding
    analysis = analyze_document(result.document, methodology=ThreatModelMethodology.PLOT4AI)
    plot = {h.id for h in analysis.heuristic_threats if h.id.startswith("plot4ai_")}
    assert "plot4ai_prompt_injection" in plot
    assert "plot4ai_rag_data_leakage" in plot


def test_kubernetes_import_labels_feed_import_corpus() -> None:
    manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-indexer
  labels:
    app.kubernetes.io/component: vector-retrieval
spec:
  template:
    spec:
      containers:
        - name: main
          image: corp.example/embedding-worker:1.2.0
"""
    result = import_kubernetes_text(manifest, filename="deploy.yaml")
    assert result.document.import_signals_corpus
    assert "embedding" in result.document.import_signals_corpus or "vector" in result.document.import_signals_corpus
    sig = collect_ai_signals_from_document(result.document)
    assert sig.vector_embedding or sig.retrieval_grounding


def test_terraform_bedrock_snippet_feeds_import_corpus() -> None:
    tf = """
resource "aws_bedrock_inference_profile" "example" {
  name = "demo"
}
"""
    result = import_terraform_text(tf, filename="ai.tf")
    assert result.document.import_signals_corpus
    assert "bedrock" in result.document.import_signals_corpus


def test_helm_chart_values_feeds_import_corpus_and_rag_tokens_are_token_safe() -> None:
    # Nota: este texto não é um chart real completo; é suficiente para sinais lexicais.
    helm = """
apiVersion: v2
name: ai-gateway
version: 0.1.0
appVersion: "1.0"
dependencies:
  - name: vector-db
    version: 1.2.3
---
image:
  repository: corp.example/llm-gateway
  tag: "1.0.0"
rag:
  enabled: true
provider:
  name: openai
"""
    result = import_helm_text(helm, filename="Chart.yaml")
    assert result.document.import_signals_corpus
    sig = collect_ai_signals_from_document(result.document)
    assert sig.model_interaction
    assert sig.retrieval_grounding
    assert sig.provider_inference
