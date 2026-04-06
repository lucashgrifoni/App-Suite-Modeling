"""Rótulos user-facing para `export_document_markdown` (pt-BR / en)."""

from __future__ import annotations

from dataclasses import dataclass

from otm_exporters.export_locale import ExportArtifactLocale, normalize_export_locale


@dataclass(frozen=True, slots=True)
class DocumentMarkdownMessages:
    owner_label: str
    document_version_label: str
    schema_bullet: str
    system_type_bullet: str
    sector_bullet: str
    section_business: str
    section_assets: str
    section_components: str
    section_data_flows: str
    section_trust_boundaries: str
    section_threats: str
    section_mitigations: str
    threat_risk_li: str
    threat_risk_score: str
    component_trust_boundary: str


_MESSAGES: dict[ExportArtifactLocale, DocumentMarkdownMessages] = {
    "pt-BR": DocumentMarkdownMessages(
        owner_label="**Responsável:**",
        document_version_label="**Versão do documento:**",
        schema_bullet="- **Schema:**",
        system_type_bullet="- **Tipo de sistema:**",
        sector_bullet="- **Setor:**",
        section_business="Contexto de negócio",
        section_assets="Ativos",
        section_components="Componentes",
        section_data_flows="Fluxos de dados",
        section_trust_boundaries="Fronteiras de confiança",
        section_threats="Ameaças",
        section_mitigations="Mitigações",
        threat_risk_li=" — risco L×I=",
        threat_risk_score=" (score ",
        component_trust_boundary=", fronteira `{boundary}`",
    ),
    "en": DocumentMarkdownMessages(
        owner_label="**Owner:**",
        document_version_label="**Document version:**",
        schema_bullet="- **Schema:**",
        system_type_bullet="- **System type:**",
        sector_bullet="- **Sector:**",
        section_business="Business context",
        section_assets="Assets",
        section_components="Components",
        section_data_flows="Data flows",
        section_trust_boundaries="Trust boundaries",
        section_threats="Threats",
        section_mitigations="Mitigations",
        threat_risk_li=" — risk L×I=",
        threat_risk_score=" (score ",
        component_trust_boundary=", trust boundary `{boundary}`",
    ),
}


def document_markdown_messages(locale: str | None) -> DocumentMarkdownMessages:
    return _MESSAGES[normalize_export_locale(locale)]
