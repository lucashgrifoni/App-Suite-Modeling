"""Schema canônico v1 — documento raiz (fonte da verdade)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from otm_core_schema.enums import (
    AssetKind,
    ComponentKind,
    EvidenceKind,
    IndustrySector,
    MitigationStatus,
    StrideCategory,
    SystemType,
    ThreatModelMethodology,
    TreatmentStatus,
)
from otm_core_schema.version import CANONICAL_SCHEMA_VERSION

_ID_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]*$"


def _unique_ids(name: str, ids: list[str]) -> None:
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate id in {name}")


def _validate_component_refs(
    components: list[Component],
    *,
    boundary_ids: set[str],
    asset_ids: set[str],
) -> None:
    for c in components:
        if c.in_trust_boundary is not None and c.in_trust_boundary not in boundary_ids:
            raise ValueError(
                f"component '{c.id}' references unknown trust boundary '{c.in_trust_boundary}'"
            )
        for aid in c.asset_ids:
            if aid not in asset_ids:
                raise ValueError(f"component '{c.id}' references unknown asset '{aid}'")


def _validate_asset_refs(assets: list[Asset], *, comp_ids: set[str]) -> None:
    for a in assets:
        for cid in a.related_component_ids:
            if cid not in comp_ids:
                raise ValueError(f"asset '{a.id}' references unknown component '{cid}'")


def _validate_data_flow_refs(data_flows: list[DataFlow], *, comp_ids: set[str]) -> None:
    for df in data_flows:
        if df.from_component not in comp_ids:
            raise ValueError(f"data_flow '{df.id}' from_component '{df.from_component}' not found")
        if df.to_component not in comp_ids:
            raise ValueError(f"data_flow '{df.id}' to_component '{df.to_component}' not found")


def _validate_trust_boundary_refs(
    trust_boundaries: list[TrustBoundary],
    *,
    comp_ids: set[str],
) -> None:
    for tb in trust_boundaries:
        for mid in tb.member_component_ids:
            if mid not in comp_ids:
                raise ValueError(f"trust_boundary '{tb.id}' references unknown component '{mid}'")


def _validate_mitigation_refs(mitigations: list[Mitigation], *, threat_ids: set[str]) -> None:
    for m in mitigations:
        for tid in m.threat_ids:
            if tid not in threat_ids:
                raise ValueError(f"mitigation '{m.id}' references unknown threat '{tid}'")


def _validate_threat_refs(
    threats: list[Threat],
    *,
    comp_ids: set[str],
    flow_ids: set[str],
    asset_ids: set[str],
    evidence_ids: set[str],
) -> None:
    for t in threats:
        if t.target_component_id is not None and t.target_component_id not in comp_ids:
            raise ValueError(f"threat '{t.id}' target_component_id unknown")
        if t.target_data_flow_id is not None and t.target_data_flow_id not in flow_ids:
            raise ValueError(f"threat '{t.id}' target_data_flow_id unknown")
        if t.target_asset_id is not None and t.target_asset_id not in asset_ids:
            raise ValueError(f"threat '{t.id}' target_asset_id unknown")
        for eid in t.evidence_suggestion_ids:
            if eid not in evidence_ids:
                raise ValueError(f"threat '{t.id}' references unknown evidence_suggestion '{eid}'")


def _validate_evidence_refs(
    evidence_suggestions: list[EvidenceSuggestion],
    *,
    threat_ids: set[str],
) -> None:
    for ev in evidence_suggestions:
        for tid in ev.related_threat_ids:
            if tid not in threat_ids:
                raise ValueError(f"evidence_suggestion '{ev.id}' references unknown threat '{tid}'")


class Metadata(BaseModel):
    """Metadados do artefato de threat model."""

    title: str = Field(..., min_length=1, description="Título humano do modelo.")
    summary: str | None = Field(default=None, description="Resumo em uma linha.")
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)
    document_version: str | None = Field(
        default=None,
        description="Versão semântica do documento (não confundir com schema_version).",
    )


class BusinessContext(BaseModel):
    """Contexto de negócio — opcional mas recomendado para relatórios e compliance."""

    description: str | None = Field(default=None, description="Narrativa do sistema e escopo.")
    business_goals: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    regulatory_context: str | None = Field(
        default=None,
        description="Obrigações regulatórias relevantes (texto livre curto).",
    )
    assumptions: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    """Cabeçalho: versão do schema + classificação do sistema."""

    schema_version: str = Field(
        default=CANONICAL_SCHEMA_VERSION,
        description="Versão do contrato OTM (semver do schema canônico).",
    )
    system_type: SystemType = Field(
        default=SystemType.WEB_APPLICATION,
        description="Tipo técnico predominante.",
    )
    industry_sector: IndustrySector = Field(
        default=IndustrySector.GENERIC,
        description="Setor / domínio de negócio.",
    )
    methodology: ThreatModelMethodology = Field(
        default=ThreatModelMethodology.STRIDE,
        description=("Metodologia principal escolhida para análise. Default do sistema: STRIDE."),
    )


class Asset(BaseModel):
    """Ativo a proteger (dados, credenciais, serviço crítico, etc.)."""

    id: str = Field(..., pattern=_ID_PATTERN)
    name: str = Field(..., min_length=1)
    asset_kind: AssetKind = Field(default=AssetKind.DATA)
    description: str | None = None
    sensitivity: str | None = Field(
        default=None,
        description="Ex.: public, internal, confidential, restricted.",
    )
    related_component_ids: list[str] = Field(
        default_factory=list,
        description="Componentes que armazenam, processam ou expõem o ativo.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class Component(BaseModel):
    id: str = Field(..., pattern=_ID_PATTERN)
    name: str = Field(..., min_length=1)
    kind: ComponentKind
    description: str | None = None
    technology: str | None = Field(
        default=None,
        description="Ex.: PostgreSQL, Kubernetes, API REST.",
    )
    in_trust_boundary: str | None = Field(
        default=None,
        description="ID de TrustBoundary.",
    )
    asset_ids: list[str] = Field(
        default_factory=list,
        description="Ativos relevantes neste componente.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataFlow(BaseModel):
    id: str = Field(..., pattern=_ID_PATTERN)
    name: str | None = None
    from_component: str = Field(..., description="ID de Component de origem.")
    to_component: str = Field(..., description="ID de Component de destino.")
    protocol: str | None = None
    authenticated: bool | None = None
    encrypted: bool | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrustBoundary(BaseModel):
    id: str = Field(..., pattern=_ID_PATTERN)
    name: str = Field(..., min_length=1)
    description: str | None = None
    member_component_ids: list[str] = Field(
        default_factory=list,
        description="Componentes contidos na fronteira.",
    )


class RiskAssessment(BaseModel):
    """Avaliação de risco por ameaça (escala 1–5, score derivado opcional)."""

    likelihood: int = Field(..., ge=1, le=5)
    impact: int = Field(..., ge=1, le=5)
    score: float | None = Field(
        default=None,
        description="Ex.: L×I ou normalizado; pode ser preenchido pelo motor.",
    )


class ResidualRiskSummary(BaseModel):
    """Agregado opcional ao nível do documento (relatório / dashboard)."""

    aggregate_score: float | None = Field(
        default=None,
        ge=0,
        description="Ex.: maior score residual ou média ponderada — convenção do time.",
    )
    notes: str | None = None


class FrameworkRef(BaseModel):
    """Referência a um controlo em norma/framework (uso funcional, não decorativo)."""

    framework: str = Field(..., description="Ex.: owasp_asvs, nist_800_53, iso_27001.")
    control_id: str = Field(..., description="Identificador no catálogo referenciado.")
    notes: str | None = None


class EvidenceSuggestion(BaseModel):
    """Evidência sugerida para validar ou reduzir incerteza sobre ameaças."""

    id: str = Field(..., pattern=_ID_PATTERN)
    title: str = Field(..., min_length=1)
    description: str | None = None
    evidence_kind: EvidenceKind = Field(default=EvidenceKind.OTHER)
    related_threat_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Ameaças associadas (espelho opcional; ameaça também pode referenciar evidências)."
        ),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class Mitigation(BaseModel):
    id: str = Field(..., pattern=_ID_PATTERN)
    title: str = Field(..., min_length=1)
    description: str | None = None
    status: MitigationStatus = Field(default=MitigationStatus.PLANNED)
    owner: str | None = Field(default=None, description="Responsável pela implementação.")
    threat_ids: list[str] = Field(default_factory=list)
    framework_refs: list[FrameworkRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Threat(BaseModel):
    id: str = Field(..., pattern=_ID_PATTERN)
    title: str = Field(..., min_length=1)
    description: str | None = None
    stride: StrideCategory
    target_component_id: str | None = None
    target_data_flow_id: str | None = None
    target_asset_id: str | None = None
    risk: RiskAssessment | None = None
    treatment_status: TreatmentStatus = Field(default=TreatmentStatus.NEW)
    assignee: str | None = Field(default=None, description="Dono do tratamento no backlog.")
    due_date: str | None = Field(
        default=None,
        description="Prazo sugerido (ISO 8601 date, ex.: 2025-12-31).",
    )
    treatment_notes: str | None = None
    framework_refs: list[FrameworkRef] = Field(default_factory=list)
    evidence_suggestion_ids: list[str] = Field(
        default_factory=list,
        description="IDs em evidence_suggestions.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreatModelDocument(BaseModel):
    """
    Raiz do modelo canônico v1.
    Extensível via `metadata` em entidades; evitar chaves desconhecidas na raiz (extra=forbid).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    model_info: ModelInfo = Field(default_factory=ModelInfo, alias="model")
    metadata: Metadata
    business_context: BusinessContext | None = None
    assets: list[Asset] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    data_flows: list[DataFlow] = Field(default_factory=list)
    trust_boundaries: list[TrustBoundary] = Field(default_factory=list)
    threats: list[Threat] = Field(default_factory=list)
    mitigations: list[Mitigation] = Field(default_factory=list)
    evidence_suggestions: list[EvidenceSuggestion] = Field(default_factory=list)
    residual_risk_summary: ResidualRiskSummary | None = None

    @field_validator("components")
    @classmethod
    def unique_component_ids(cls, v: list[Component]) -> list[Component]:
        _unique_ids("components", [c.id for c in v])
        return v

    @field_validator("data_flows")
    @classmethod
    def unique_data_flow_ids(cls, v: list[DataFlow]) -> list[DataFlow]:
        _unique_ids("data_flows", [f.id for f in v])
        return v

    @field_validator("trust_boundaries")
    @classmethod
    def unique_trust_boundary_ids(cls, v: list[TrustBoundary]) -> list[TrustBoundary]:
        _unique_ids("trust_boundaries", [b.id for b in v])
        return v

    @field_validator("assets")
    @classmethod
    def unique_asset_ids(cls, v: list[Asset]) -> list[Asset]:
        _unique_ids("assets", [a.id for a in v])
        return v

    @field_validator("threats")
    @classmethod
    def unique_threat_ids(cls, v: list[Threat]) -> list[Threat]:
        _unique_ids("threats", [t.id for t in v])
        return v

    @field_validator("mitigations")
    @classmethod
    def unique_mitigation_ids(cls, v: list[Mitigation]) -> list[Mitigation]:
        _unique_ids("mitigations", [m.id for m in v])
        return v

    @field_validator("evidence_suggestions")
    @classmethod
    def unique_evidence_ids(cls, v: list[EvidenceSuggestion]) -> list[EvidenceSuggestion]:
        _unique_ids("evidence_suggestions", [e.id for e in v])
        return v

    @model_validator(mode="after")
    def validate_references(self) -> ThreatModelDocument:
        ids = self._collect_reference_ids()
        self._run_reference_validations(ids)
        return self

    def _collect_reference_ids(self) -> dict[str, set[str]]:
        """Coleta IDs para validação cruzada de referências internas."""
        return {
            "components": {c.id for c in self.components},
            "trust_boundaries": {b.id for b in self.trust_boundaries},
            "data_flows": {f.id for f in self.data_flows},
            "assets": {a.id for a in self.assets},
            "threats": {t.id for t in self.threats},
            "evidence_suggestions": {e.id for e in self.evidence_suggestions},
        }

    def _run_reference_validations(self, ids: dict[str, set[str]]) -> None:
        """Executa validações de referências usando o conjunto de IDs coletados."""
        _validate_component_refs(
            self.components,
            boundary_ids=ids["trust_boundaries"],
            asset_ids=ids["assets"],
        )
        _validate_asset_refs(self.assets, comp_ids=ids["components"])
        _validate_data_flow_refs(self.data_flows, comp_ids=ids["components"])
        _validate_trust_boundary_refs(self.trust_boundaries, comp_ids=ids["components"])
        _validate_mitigation_refs(self.mitigations, threat_ids=ids["threats"])
        _validate_threat_refs(
            self.threats,
            comp_ids=ids["components"],
            flow_ids=ids["data_flows"],
            asset_ids=ids["assets"],
            evidence_ids=ids["evidence_suggestions"],
        )
        _validate_evidence_refs(self.evidence_suggestions, threat_ids=ids["threats"])
