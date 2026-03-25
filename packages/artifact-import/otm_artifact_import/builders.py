"""
Montagem de `ThreatModelDocument` a partir de elementos já normalizados.

Não contém parsing de artefactos — apenas consistência de fronteiras e texto de contexto.
"""

from __future__ import annotations

import re
from typing import Literal

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
    Converte texto em id válido para o schema canónico (`^[a-zA-Z][a-zA-Z0-9_-]*$`).
    """
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower())
    s = s.strip("_") or "x"
    if not re.match(r"^[a-zA-Z]", s):
        s = f"{prefix}_{s}"
    return s[:56]


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
) -> ArtifactImportResult:
    """
    Constrói um documento canónico **draft** e devolve transparência estruturada à parte.

    As inferências também são copiadas para `business_context.assumptions` no YAML,
    para o rascunho ser audível sem depender da API.
    """
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
    )
    return ArtifactImportResult(
        document=doc,
        inferences=inferences,
        unknowns=unknowns,
        assumptions=list(extra_assumptions),
        explanations=explanations_from_inferences(inferences),
    )
