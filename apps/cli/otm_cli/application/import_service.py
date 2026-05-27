"""Use cases: assisted import (OpenAPI, Terraform, K8s, repo scan)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otm_core_schema import dump_document_to_yaml

from otm_cli.shared.emit import write_json_file
from otm_cli.shared.errors import CliUserError

_CONFIRM_PATH = "confirm the path."


def import_openapi(spec: Path) -> tuple[str, dict[str, Any] | None, list[Any]]:
    """Return (yaml_text, explain_payload_or_none, inferences_for_ui_summary)."""
    from otm_artifact_import import import_openapi_path

    if not spec.is_file():
        raise CliUserError(
            exit_code=1,
            failed="OpenAPI file.",
            cause=f"not a file: {spec}",
            next_step=_CONFIRM_PATH,
        )
    result = import_openapi_path(spec)
    yaml_text = dump_document_to_yaml(result.document)
    explain_payload = {
        "document": result.document.model_dump(mode="json", by_alias=True),
        "inferences": [i.model_dump(mode="json") for i in result.inferences],
        "unknowns": result.unknowns,
        "assumptions": result.assumptions,
    }
    return yaml_text, explain_payload, list(result.inferences)


def import_terraform(target: Path) -> tuple[str, dict[str, Any] | None, list[Any]]:
    from otm_artifact_import import import_terraform_path

    if not target.exists():
        raise CliUserError(
            exit_code=1,
            failed="Terraform.",
            cause=f"path does not exist: {target}",
            next_step=_CONFIRM_PATH,
        )
    result = import_terraform_path(target)
    yaml_text = dump_document_to_yaml(result.document)
    explain_payload = {
        "document": result.document.model_dump(mode="json", by_alias=True),
        "inferences": [i.model_dump(mode="json") for i in result.inferences],
        "unknowns": result.unknowns,
        "assumptions": result.assumptions,
    }
    return yaml_text, explain_payload, list(result.inferences)


def import_kubernetes(target: Path) -> tuple[str, dict[str, Any] | None, list[Any]]:
    from otm_artifact_import import import_kubernetes_path

    if not target.exists():
        raise CliUserError(
            exit_code=1,
            failed="Kubernetes.",
            cause=f"path does not exist: {target}",
            next_step=_CONFIRM_PATH,
        )
    result = import_kubernetes_path(target)
    yaml_text = dump_document_to_yaml(result.document)
    explain_payload = {
        "document": result.document.model_dump(mode="json", by_alias=True),
        "inferences": [i.model_dump(mode="json") for i in result.inferences],
        "unknowns": result.unknowns,
        "assumptions": result.assumptions,
    }
    return yaml_text, explain_payload, list(result.inferences)


def scan_repo(root: Path) -> dict[str, Any]:
    from otm_artifact_import import scan_node_express_repo

    if not root.is_dir():
        raise CliUserError(
            exit_code=1,
            failed="repo scan.",
            cause=f"not a directory: {root}",
            next_step="pass the repository root path.",
        )
    return scan_node_express_repo(root)


def write_explain_json(payload: dict[str, Any], explain_out: Path) -> None:
    write_json_file(payload=payload, output=explain_out)
