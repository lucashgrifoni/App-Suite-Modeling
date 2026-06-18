"""
Montagem de `ThreatModelDocument` a partir de elementos já normalizados.

Não contém parsing de artefactos — apenas consistência de fronteiras e texto de contexto.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from otm_core_schema import (
    Asset,
    BusinessContext,
    Component,
    DataFlow,
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    TrustBoundary,
)
from otm_core_schema.enums import IndustrySector, SystemType, ThreatModelMethodology

from otm_artifact_import.inference_explanations import explanations_from_inferences
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord

SourceKind = Literal["openapi", "terraform", "kubernetes", "helm"]


def slug_id(text: str, *, prefix: str = "c") -> str:
    """
    Converte texto em id válido para o schema canónico (``ENTITY_ID_PATTERN``).
    """
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text.strip().lower())
    s = s.strip("._-") or "x"
    if not re.match(r"^\w", s, re.ASCII):
        s = f"{prefix}_{s}"  # pragma: no cover - defensive: sanitized slug always starts with a word char
    return s[:56]


def _dedup_by_id(items: list[Any], *, kind: str, notes: list[str]) -> list[Any]:
    """Drop entries whose ``id`` already appeared, recording a reconciliation note.

    Importers derive ids from artifact text (resource names, titles, file
    names). Distinct inputs can slug to the same id — e.g. two Kubernetes
    resources of the same kind sharing a name across namespaces, a Terraform
    address duplicated across concatenated files, or two names colliding after
    the slug length cap. Without this guard the canonical schema rejects the
    whole draft with a hard "duplicate id" error (surfacing as a 400/500 or a
    CLI stack trace). Keeping the first occurrence yields a valid, reviewable
    draft; the note tells the human to reconcile the merged entities.
    """
    seen: set[str] = set()
    out: list[Any] = []
    for item in items:
        if item.id in seen:
            notes.append(
                f"{kind} com id `{item.id}` duplicado (nomes/identificadores colidiram na importação) "
                "— mantido o primeiro; reveja e separe manualmente se forem entidades distintas."
            )
            continue
        seen.add(item.id)
        out.append(item)
    return out


def _sync_trust_boundary_members(
    components: list[Component],
    trust_boundaries: list[TrustBoundary],
) -> None:
    """Preenche `member_component_ids` a partir de `Component.in_trust_boundary`."""
    by_id = {b.id: b for b in trust_boundaries}
    for b in trust_boundaries:
        b.member_component_ids = []
    for c in components:
        bid = c.in_trust_boundary
        if bid and bid in by_id:
            by_id[bid].member_component_ids.append(c.id)
    for b in trust_boundaries:
        b.member_component_ids = list(dict.fromkeys(b.member_component_ids))


def assemble_draft(
    *,
    title: str,
    summary: str | None,
    source_kind: SourceKind,
    system_type: SystemType,
    industry: IndustrySector,
    components: list[Component],
    data_flows: list[DataFlow],
    trust_boundaries: list[TrustBoundary],
    assets: list[Asset],
    inferences: list[InferenceRecord],
    unknowns: list[str],
    extra_assumptions: list[str],
    import_signals_corpus: str | None = None,
) -> ArtifactImportResult:
    """
    Constrói um documento canónico **draft** e devolve transparência estruturada à parte.

    As inferências também são copiadas para `business_context.assumptions` no YAML,
    para o rascunho ser audível sem depender da API.
    """
    # Guard against id collisions from artifact-derived ids before the canonical
    # schema (unique-id + referential integrity) rejects the whole draft. Flows
    # keep referencing the surviving id, so referential integrity holds.
    collision_notes: list[str] = []
    components = _dedup_by_id(components, kind="Componente", notes=collision_notes)
    data_flows = _dedup_by_id(data_flows, kind="Fluxo", notes=collision_notes)
    trust_boundaries = _dedup_by_id(trust_boundaries, kind="Fronteira de confiança", notes=collision_notes)
    assets = _dedup_by_id(assets, kind="Ativo", notes=collision_notes)
    if collision_notes:
        unknowns = [*unknowns, *collision_notes]

    _sync_trust_boundary_members(components, trust_boundaries)

    bc_lines: list[str] = [
        "Rascunho gerado por importação assistida de artefactos (não é análise de ameaças).",
        f"Fonte do artefacto: {source_kind}.",
        "Revise componentes, fluxos, fronteiras e lista abaixo antes de correr o motor.",
    ]
    assumption_lines = list(extra_assumptions)
    for inf in inferences:
        assumption_lines.append(f"[inferência {inf.confidence} | {inf.source}] {inf.message}")
    for u in unknowns:
        assumption_lines.append(f"[não inferido] {u}")

    # model_info: mypy+pydantic v2 alinham o campo Python automaticamente (plugin pydantic ativo).
    doc = ThreatModelDocument(
        metadata=Metadata(
            title=title,
            summary=summary or f"Rascunho importado ({source_kind})",
            tags=["draft", "artifact-import", source_kind],
            document_version="0.0.1-draft",
        ),
        model_info=ModelInfo(
            system_type=system_type,
            industry_sector=industry,
            methodology=ThreatModelMethodology.STRIDE,
        ),
        business_context=BusinessContext(
            description="\n\n".join(bc_lines),
            assumptions=assumption_lines,
        ),
        assets=assets,
        components=components,
        data_flows=data_flows,
        trust_boundaries=trust_boundaries,
        import_signals_corpus=import_signals_corpus,
    )
    return ArtifactImportResult(
        document=doc,
        inferences=inferences,
        unknowns=unknowns,
        assumptions=list(extra_assumptions),
        explanations=explanations_from_inferences(inferences),
    )
