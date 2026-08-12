"""Use cases: assisted import (OpenAPI, Terraform, K8s, repo scan)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from otm_core_schema import ThreatModelDocument, dump_document_to_yaml

from otm_cli.shared.emit import write_json_file
from otm_cli.shared.errors import CliUserError

_CONFIRM_PATH = "confirm the path."
_DRAFT_MAX_COMPONENTS = 24
_DRAFT_MAX_FLOWS = 48


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


#: OTM collections whose entries the bridge maps one-for-one when it can, plus the canonical
#: attribute that receives them. A shortfall means entries were skipped (unusable id, or a
#: dataflow endpoint that was itself skipped).
_OTM_MAPPED_COLLECTIONS = (
    ("trustZones", "trust zone", "trust_boundaries"),
    ("components", "component", "components"),
    ("dataflows", "data flow", "data_flows"),
    ("assets", "asset", "assets"),
)

#: Per-entity OTM keys with no canonical equivalent. `risk` is an integer 0-100 scale while the
#: canonical document uses enums, so it is neither translated nor approximated.
_OTM_UNMAPPED_ENTITY_KEYS = ("risk", "tags", "attributes")


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _otm_list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    return value if isinstance(value, list) else []


def _otm_not_imported(text: str, doc: ThreatModelDocument) -> list[str]:
    """Name what the OTM→canonical conversion left behind.

    The bridge covers the architecture only, and the CLI help used to call it "lossless" — an
    analyst migrating out of IriusRisk shipped a model with zero hand-authored threats and saw
    exit 0. Counting the source against the produced document keeps this honest without
    duplicating the bridge's internal id-remapping rules.
    """
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:  # pragma: no cover - the conversion above already parsed this text
        return []
    if not isinstance(raw, dict):  # pragma: no cover - import_otm_text rejects a non-mapping root
        return []

    notes: list[str] = []
    for key, noun in (("threats", "threat"), ("mitigations", "mitigation")):
        count = len(_otm_list(raw, key))
        if count:
            notes.append(f"{_plural(count, noun)} — analyst-authored; the engine derives its own")

    for key, noun, attr in _OTM_MAPPED_COLLECTIONS:
        dropped = len(_otm_list(raw, key)) - len(getattr(doc, attr))
        if dropped > 0:
            notes.append(f"{_plural(dropped, noun)} — unusable id, or an endpoint that was not imported")

    unmapped = sum(
        1
        for key, _noun, _attr in _OTM_MAPPED_COLLECTIONS
        for entry in _otm_list(raw, key)
        if isinstance(entry, dict) and any(k in entry for k in _OTM_UNMAPPED_ENTITY_KEYS)
    )
    if unmapped:
        notes.append(f"{_plural(unmapped, 'risk/tag attribute block')} — OTM's 0-100 scale has no canonical equivalent")
    return notes


def import_otm(path: Path) -> tuple[str, list[str]]:
    """Convert an Open Threat Model (OTM 0.2.0) file into a canonical `.otm.yaml`.

    Returns the YAML plus notes naming everything the conversion did not carry over, so the
    command can report the loss instead of exiting 0 on a quietly gutted model.
    """
    from otm_artifact_import.otm_native import import_otm_text
    from pydantic import ValidationError

    if not path.is_file():
        raise CliUserError(
            exit_code=1,
            failed="OTM file.",
            cause=f"not a file: {path}",
            next_step=_CONFIRM_PATH,
        )
    try:
        # `read_text` stays inside the try: a non-UTF-8 file raises UnicodeDecodeError, a
        # ValueError, and that must surface as the same friendly error as a malformed document.
        text = path.read_text(encoding="utf-8")
        doc = import_otm_text(text)
    except (ValueError, ValidationError) as e:
        raise CliUserError(
            exit_code=1,
            failed=f"OTM import of `{path}`.",
            cause=str(e),
            next_step="confirm the file is a valid Open Threat Model (otm-0.2.0) document.",
        ) from e
    return dump_document_to_yaml(doc), _otm_not_imported(text, doc)


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


_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def _slug(text: str) -> str:
    base = _SLUG_RE.sub("_", text.lower()).strip("_-")
    return base or "x"


def _short_file_id(file_path: str) -> str:
    # Normalize Windows-style separators because the Node scanner emits paths
    # such as `src\routes\admin.js` regardless of the host OS — without this,
    # the helper would yield `src_routes_admin` on Linux runners.
    name = Path(file_path.replace("\\", "/")).stem
    return _slug(name)[:24]


def scan_payload_to_draft_yaml(payload: dict[str, Any]) -> str:
    """Build a minimal ``.otm.yaml`` draft from an ``import repo`` payload.

    The output is intentionally conservative: one external user, one service
    component per file that exposes routes or sessions, one perimeter trust
    boundary, and one cross-boundary data flow per detected route (capped).
    It is editable seed material — a human still has to flesh it out.
    """
    inferences = payload.get("inferences") or []
    root = payload.get("root") or ""
    repo_name = Path(root).name or "imported_service"

    files_with_routes: dict[str, list[str]] = {}
    files_with_sessions: set[str] = set()
    admin_files: set[str] = set()
    for inf in inferences:
        kind = inf.get("kind")
        evidence = inf.get("evidence") or ""
        msg = inf.get("message") or ""
        file_match = re.search(r"`([^`]+)`", msg)
        file_path = file_match.group(1) if file_match else ""
        if kind == "route" and file_path:
            files_with_routes.setdefault(file_path, []).append(evidence)
        elif kind == "session" and file_path:
            files_with_sessions.add(file_path)
        elif kind == "admin_route" and file_path:
            admin_files.add(file_path)

    components: list[dict[str, Any]] = [
        {"id": "ext_user", "name": "Cliente externo", "kind": "external_entity"},
    ]
    member_ids: list[str] = []
    file_to_component_id: dict[str, str] = {}
    interesting_files = list(files_with_routes.keys()) + [f for f in files_with_sessions if f not in files_with_routes]
    for file_path in interesting_files[:_DRAFT_MAX_COMPONENTS]:
        comp_id = f"svc_{_short_file_id(file_path)}"
        file_to_component_id[file_path] = comp_id
        components.append(
            {
                "id": comp_id,
                "name": Path(file_path).name,
                "kind": "process",
            }
        )
        member_ids.append(comp_id)

    data_flows: list[dict[str, Any]] = []
    for file_path, routes in files_with_routes.items():
        target_comp_id = file_to_component_id.get(file_path)
        if not target_comp_id:
            continue
        for route in routes:
            if len(data_flows) >= _DRAFT_MAX_FLOWS:
                break
            data_flows.append(
                {
                    "id": f"flow_{_slug(route)[:32]}_{len(data_flows)}",
                    "name": route,
                    "from_component": "ext_user",
                    "to_component": target_comp_id,
                }
            )
        if len(data_flows) >= _DRAFT_MAX_FLOWS:
            break

    assets = [
        {
            "id": "svc_primary_data",
            "name": "Dados operacionais inferidos do repositório",
            "asset_kind": "data",
            "sensitivity": "internal",
            "business_criticality": "medium",
        }
    ]
    if files_with_sessions:
        assets.append(
            {
                "id": "svc_session_context",
                "name": "Contexto de sessão / cookies",
                "asset_kind": "session",
                "sensitivity": "confidential",
                "business_criticality": "high",
            }
        )

    summary_bits = [f"Draft gerado por `otm import repo` a partir de {len(inferences)} inferência(s)."]
    if admin_files:
        summary_bits.append("Rotas /admin detectadas — revisar fronteira e autorização.")
    if files_with_sessions:
        summary_bits.append("Sessão Express detectada — confirmar atributos de cookie (HttpOnly/Secure/SameSite).")
    if not files_with_routes:
        summary_bits.append("Nenhuma rota detectada — completar componentes manualmente.")
    summary = " ".join(summary_bits)

    perimeter = {
        "id": "default_perimeter",
        "name": "Perímetro inferido",
        "members": member_ids[:_DRAFT_MAX_COMPONENTS],
        "inference_note": (
            "Fronteira derivada do scan de repositório — revise membros, fluxos cruzados e exposição externa."
        ),
    }

    document: dict[str, Any] = {
        "model": {
            "schema_version": "1.1.0",
            "system_type": "web_application",
            "industry_sector": "generic",
        },
        "metadata": {
            "title": f"Draft — {repo_name}",
            "summary": summary,
            "tags": ["draft", "artifact-import", "repo-scan"],
        },
        "trust_boundaries": [perimeter],
        "components": components,
        "data_flows": data_flows,
        "assets": assets,
        "threats": [],
        "mitigations": [],
        "evidence_suggestions": [],
    }

    header = (
        "# Gerado por: otm import repo --draft-out\n"
        "# Draft semente — edite componentes, fronteiras, fluxos e ativos antes de `otm analyze`.\n"
    )
    body = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
    return header + body
