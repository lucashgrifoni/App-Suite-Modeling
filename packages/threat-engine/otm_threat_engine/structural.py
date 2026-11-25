"""Validação estrutural complementar (avisos que não invalidam o schema)."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_core_schema.trust_membership import boundary_membership_conflicts, resolve_component_boundaries

from otm_threat_engine.result import StructuralFinding


def _message_component_without_trust_boundary(missing_ids: list[str]) -> str:
    shown = ", ".join(missing_ids[:10])
    suffix = "…" if len(missing_ids) > 10 else ""
    return f"Existem componentes sem fronteira de confiança atribuída: {shown}{suffix}"


def _message_membership_conflict(conflicts: dict[str, list[str]]) -> str:
    shown = "; ".join(f"{cid} → {', '.join(bounds)}" for cid, bounds in list(conflicts.items())[:10])
    suffix = "…" if len(conflicts) > 10 else ""
    return f"Pertença a fronteira declarada em contradição (o lado do componente prevalece): {shown}{suffix}"


def collect_structural_findings(doc: ThreatModelDocument) -> list[StructuralFinding]:
    findings: list[StructuralFinding] = []

    if not doc.components:
        findings.append(
            StructuralFinding(
                code="EMPTY_COMPONENTS",
                severity="warning",
                message="O modelo não contém componentes; o diagrama está vazio.",
            )
        )

    # `info` e não `warning`: a análise não muda (o lado do componente prevalece, como sempre
    # prevaleceu) e vários templates enviados com o produto declaram esta contradição, por isso
    # subir a severidade só encheria de avisos modelos cuja análise está correcta. Fica ao nível
    # do seu irmão `COMPONENT_WITHOUT_TRUST_BOUNDARY` — dito, não escondido.
    conflicts = boundary_membership_conflicts(doc)
    if conflicts:
        findings.append(
            StructuralFinding(
                code="TRUST_BOUNDARY_MEMBERSHIP_CONFLICT",
                severity="info",
                message=_message_membership_conflict(conflicts),
            )
        )

    if doc.trust_boundaries and doc.components:
        # A pertença pode estar declarada na fronteira (`member_component_ids`) em vez de no
        # componente; dizer "sem fronteira atribuída" nesse caso era simplesmente falso.
        resolved = resolve_component_boundaries(doc)
        missing = [c.id for c in doc.components if c.id not in resolved]
        if missing:
            findings.append(
                StructuralFinding(
                    code="COMPONENT_WITHOUT_TRUST_BOUNDARY",
                    severity="info",
                    message=_message_component_without_trust_boundary(missing),
                )
            )

    if not doc.data_flows and len(doc.components) > 1:
        findings.append(
            StructuralFinding(
                code="NO_DATA_FLOWS",
                severity="info",
                message="Há vários componentes mas nenhum data flow; revisar o modelo.",
            )
        )

    return findings
