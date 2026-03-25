"""Delegação para `otm_artifact_import` (sem lógica de parsing duplicada)."""

from __future__ import annotations

from otm_artifact_import import (
    ArtifactImportResult,
    import_kubernetes_text,
    import_openapi_text,
    import_terraform_text,
)


def import_openapi_bytes(data: bytes, *, filename: str = "openapi.yaml") -> ArtifactImportResult:
    return import_openapi_text(data.decode("utf-8"), filename=filename)


def import_terraform_bytes(data: bytes, *, filename: str = "bundle.tf") -> ArtifactImportResult:
    return import_terraform_text(data.decode("utf-8"), filename=filename)


def import_kubernetes_bytes(
    data: bytes,
    *,
    filename: str = "manifests.yaml",
) -> ArtifactImportResult:
    return import_kubernetes_text(data.decode("utf-8"), filename=filename)
