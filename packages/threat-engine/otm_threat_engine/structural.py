"""Validação estrutural complementar (avisos que não invalidam o schema)."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument

from otm_threat_engine.result import StructuralFinding


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

    if doc.trust_boundaries and doc.components:
        missing = [c.id for c in doc.components if c.in_trust_boundary is None]
        if missing:
            findings.append(
                StructuralFinding(
                    code="COMPONENT_WITHOUT_TRUST_BOUNDARY",
                    severity="info",
                    message=(
                        "Existem componentes sem fronteira de confiança atribuída: "
                        + ", ".join(missing[:10])
                        + ("…" if len(missing) > 10 else "")
                    ),
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
