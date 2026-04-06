"""
Comparação estruturada entre duas versões de `ThreatModelDocument`.

Regras de desenho:
- Sem I/O: recebe documentos já validados.
- Comparável e serializável em JSON (para API/CLI).
- Entidades com `id` são comparadas por ID; campos alterados são listados no nível superior
  do `model_dump` (objetos aninhados aparecem como um campo único se diferentes).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from otm_core_schema.document import ThreatModelDocument

_MISSING = object()


def _json_stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


class FieldChange(BaseModel):
    """Uma diferença em um campo de entidade ou na raiz do documento."""

    field: str
    before: Any | None = None
    after: Any | None = None


class ModifiedEntity(BaseModel):
    id: str
    changes: list[FieldChange] = Field(default_factory=list)


class IdListSectionDiff(BaseModel):
    """Diff de uma lista indexada por `id` (ativos, componentes, fluxos, etc.)."""

    added: list[str] = Field(default_factory=list, description="IDs presentes só na revisão.")
    removed: list[str] = Field(default_factory=list, description="IDs presentes só na baseline.")
    modified: list[ModifiedEntity] = Field(
        default_factory=list,
        description="Mesmo ID com campos alterados.",
    )


class ThreatModelDiff(BaseModel):
    """Resultado canónico de `diff_documents` — estável para `/models/diff` e CLI."""

    baseline_title: str = Field(..., description="metadata.title da baseline.")
    revised_title: str = Field(..., description="metadata.title da revisão.")
    summary_line: str = Field(
        ...,
        description="Resumo em uma linha para logs e UI compacta.",
    )
    model_info: list[FieldChange] = Field(default_factory=list)
    metadata: list[FieldChange] = Field(default_factory=list)
    business_context: list[FieldChange] = Field(default_factory=list)
    residual_risk_summary: list[FieldChange] = Field(default_factory=list)
    assets: IdListSectionDiff = Field(default_factory=IdListSectionDiff)
    components: IdListSectionDiff = Field(default_factory=IdListSectionDiff)
    data_flows: IdListSectionDiff = Field(default_factory=IdListSectionDiff)
    trust_boundaries: IdListSectionDiff = Field(default_factory=IdListSectionDiff)
    threats: IdListSectionDiff = Field(default_factory=IdListSectionDiff)
    mitigations: IdListSectionDiff = Field(default_factory=IdListSectionDiff)
    evidence_suggestions: IdListSectionDiff = Field(default_factory=IdListSectionDiff)

    def has_any_change(self) -> bool:
        """True se existir qualquer diferença estrutural."""
        sections: list[IdListSectionDiff] = [
            self.assets,
            self.components,
            self.data_flows,
            self.trust_boundaries,
            self.threats,
            self.mitigations,
            self.evidence_suggestions,
        ]
        if any(s.added or s.removed or s.modified for s in sections):
            return True
        root_lists = [
            self.model_info,
            self.metadata,
            self.business_context,
            self.residual_risk_summary,
        ]
        return any(bool(x) for x in root_lists)


def _field_changes_for_dicts(before: dict[str, Any], after: dict[str, Any]) -> list[FieldChange]:
    keys = set(before) | set(after)
    out: list[FieldChange] = []
    for key in sorted(keys):
        if key == "id":
            continue
        vb = before.get(key, _MISSING)
        va = after.get(key, _MISSING)
        if vb is _MISSING:
            out.append(FieldChange(field=key, before=None, after=va))
        elif va is _MISSING:
            out.append(FieldChange(field=key, before=vb, after=None))
        elif _json_stable(vb) != _json_stable(va):
            out.append(FieldChange(field=key, before=vb, after=va))
    return out


def _diff_optional_block(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[FieldChange]:
    if before is None and after is None:
        return []
    if before is None:
        return [FieldChange(field="*", before=None, after=after)]
    if after is None:
        return [FieldChange(field="*", before=before, after=None)]
    return _field_changes_for_dicts(before, after)


def _diff_id_list(items_before: list[Any], items_after: list[Any]) -> IdListSectionDiff:
    def as_map(rows: list[Any]) -> dict[str, dict[str, Any]]:
        m: dict[str, dict[str, Any]] = {}
        for row in rows:
            d = row.model_dump(mode="json")
            eid = d["id"]
            m[eid] = d
        return m

    b_map = as_map(items_before)
    a_map = as_map(items_after)
    b_ids = set(b_map)
    a_ids = set(a_map)
    added = sorted(a_ids - b_ids)
    removed = sorted(b_ids - a_ids)
    modified: list[ModifiedEntity] = []
    for eid in sorted(b_ids & a_ids):
        ch = _field_changes_for_dicts(b_map[eid], a_map[eid])
        if ch:
            modified.append(ModifiedEntity(id=eid, changes=ch))
    return IdListSectionDiff(added=added, removed=removed, modified=modified)


def diff_documents(baseline: ThreatModelDocument, revised: ThreatModelDocument) -> ThreatModelDiff:
    """
    Compara dois documentos canónicos válidos e devolve diff estruturado.

    Não altera os documentos de entrada.
    """
    b_model = baseline.model_info.model_dump(mode="json")
    a_model = revised.model_info.model_dump(mode="json")
    b_meta = baseline.metadata.model_dump(mode="json")
    a_meta = revised.metadata.model_dump(mode="json")
    b_biz = baseline.business_context.model_dump(mode="json") if baseline.business_context else None
    a_biz = revised.business_context.model_dump(mode="json") if revised.business_context else None
    b_res = baseline.residual_risk_summary.model_dump(mode="json") if baseline.residual_risk_summary else None
    a_res = revised.residual_risk_summary.model_dump(mode="json") if revised.residual_risk_summary else None

    assets = _diff_id_list(baseline.assets, revised.assets)
    components = _diff_id_list(baseline.components, revised.components)
    data_flows = _diff_id_list(baseline.data_flows, revised.data_flows)
    trust_boundaries = _diff_id_list(baseline.trust_boundaries, revised.trust_boundaries)
    threats = _diff_id_list(baseline.threats, revised.threats)
    mitigations = _diff_id_list(baseline.mitigations, revised.mitigations)
    evidence = _diff_id_list(baseline.evidence_suggestions, revised.evidence_suggestions)

    def _count(sec: IdListSectionDiff) -> int:
        return len(sec.added) + len(sec.removed) + len(sec.modified)

    total = (
        _count(assets)
        + _count(components)
        + _count(data_flows)
        + _count(trust_boundaries)
        + _count(threats)
        + _count(mitigations)
        + _count(evidence)
    )
    root_changes = (
        len(_field_changes_for_dicts(b_model, a_model))
        + len(_field_changes_for_dicts(b_meta, a_meta))
        + len(_diff_optional_block(b_biz, a_biz))
        + len(_diff_optional_block(b_res, a_res))
    )

    diff = ThreatModelDiff(
        baseline_title=baseline.metadata.title,
        revised_title=revised.metadata.title,
        summary_line=(
            f"baseline «{baseline.metadata.title}» → revisão «{revised.metadata.title}»: "
            f"{total} mudança(s) em listas indexadas; {root_changes} em campos de topo."
        ),
        model_info=_field_changes_for_dicts(b_model, a_model),
        metadata=_field_changes_for_dicts(b_meta, a_meta),
        business_context=_diff_optional_block(b_biz, a_biz),
        residual_risk_summary=_diff_optional_block(b_res, a_res),
        assets=assets,
        components=components,
        data_flows=data_flows,
        trust_boundaries=trust_boundaries,
        threats=threats,
        mitigations=mitigations,
        evidence_suggestions=evidence,
    )
    if not diff.has_any_change():
        diff = diff.model_copy(
            update={
                "summary_line": (
                    f"baseline «{baseline.metadata.title}» → revisão «{revised.metadata.title}»: "
                    "sem diferenças estruturais detectadas."
                )
            }
        )
    return diff
