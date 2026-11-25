"""Preview an OpenAPI reimport against the model the analyst has edited."""

from __future__ import annotations

from typing import Any

from otm_core_schema import FieldChange, ThreatModelDocument
from pydantic import BaseModel

from otm_artifact_import.openapi_import import compare_openapi_operations, import_openapi_text


class OpenApiReimportPreview(BaseModel):
    document: dict[str, Any]
    operations: dict[str, list[str]]
    changes: list[FieldChange]
    conflicts: list[FieldChange]


def preview_openapi_reimport(previous: str, revised: str, current: ThreatModelDocument) -> OpenApiReimportPreview:
    operations = compare_openapi_operations(previous, revised)
    baseline = import_openapi_text(previous).document.model_dump(mode="json", by_alias=True)
    incoming = import_openapi_text(revised).document.model_dump(mode="json", by_alias=True)
    proposed = current.model_dump(mode="json", by_alias=True)
    changes: list[FieldChange] = []
    conflicts: list[FieldChange] = []

    baseline_api, incoming_api = (draft["components"][1] for draft in (baseline, incoming))
    api_id = baseline_api["id"]
    active_api = next((component for component in proposed["components"] if component["id"] == api_id), None)
    # A different imported component ID could mean a rename or an unrelated contract.
    # Keep the existing IDs and links until the analyst can map the identity manually.
    if incoming_api["id"] != api_id or active_api is None or active_api["metadata"].get("import_kind") != "openapi":
        conflicts.append(
            FieldChange(field="components", before=api_id if active_api else None, after=incoming_api["id"])
        )
        return OpenApiReimportPreview(document=proposed, operations=operations, changes=changes, conflicts=conflicts)

    def review(target: dict[str, Any], key: str, original: Any, new: Any, field: str, *, eligible: bool = True) -> None:
        actual = target.get(key)
        if original == new or actual == new:
            return
        change = FieldChange(field=field, before=actual, after=new)
        if eligible and actual == original:
            target[key] = new
            changes.append(change)
        else:
            conflicts.append(change)

    api_field = f"components.{api_id}"
    review(
        proposed["metadata"],
        "summary",
        baseline["metadata"]["summary"],
        incoming["metadata"]["summary"],
        "metadata.summary",
    )
    for key in ("name", "description"):
        review(active_api, key, baseline_api[key], incoming_api[key], f"{api_field}.{key}")
    review(
        active_api["metadata"],
        "operation_sample",
        baseline_api["metadata"]["operation_sample"],
        incoming_api["metadata"]["operation_sample"],
        f"{api_field}.metadata.operation_sample",
    )
    review(
        proposed,
        "import_signals_corpus",
        baseline["import_signals_corpus"],
        incoming["import_signals_corpus"],
        "import_signals_corpus",
    )

    # The importer emits at most one aggregate flow and one payload asset. Never remove
    # model entities here: they may already have threats, mitigations or other references.
    for section in ("data_flows", "assets"):
        original: dict[str, Any] | None = next(iter(baseline[section]), None)
        new: dict[str, Any] | None = next(iter(incoming[section]), None)
        entity = original if original is not None else new
        if entity is None:
            continue
        entity_id = entity["id"]
        actual = next((entity for entity in proposed[section] if entity["id"] == entity_id), None)
        field = f"{section}.{entity_id}"
        if original is None and new is not None:
            has_endpoints = section != "data_flows" or any(
                entity["id"] == new["from_component"] for entity in proposed["components"]
            )
            if actual is None and has_endpoints:
                proposed[section].append(new)
                changes.append(FieldChange(field=field, after=entity_id))
            else:
                conflicts.append(FieldChange(field=field, before=entity_id if actual else None, after=entity_id))
        elif new is None:
            if actual is not None:
                conflicts.append(FieldChange(field=field, before=entity_id))
        elif original is not None and section == "data_flows":
            if actual is None:
                if original["metadata"] != new["metadata"] or original["authenticated"] != new["authenticated"]:
                    conflicts.append(FieldChange(field=field, after=entity_id))
                continue
            same_endpoints = all(actual[key] == original[key] for key in ("from_component", "to_component"))
            review(
                actual,
                "authenticated",
                original["authenticated"],
                new["authenticated"],
                f"{field}.authenticated",
                eligible=same_endpoints,
            )
            key = "openapi_operations_count"
            review(
                actual["metadata"],
                key,
                original["metadata"][key],
                new["metadata"][key],
                f"{field}.metadata.{key}",
                eligible=same_endpoints,
            )

    return OpenApiReimportPreview(document=proposed, operations=operations, changes=changes, conflicts=conflicts)
