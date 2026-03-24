"""Identificadores canónicos de catálogos de framework (extensível)."""

from __future__ import annotations

from enum import StrEnum


class FrameworkCatalog(StrEnum):
    """
    IDs estáveis usados em `FrameworkRef.framework` e nos ficheiros de dados.

    Novos catálogos (ex.: mitre_attack, capec, pci_dss) acrescentam-se aqui
    e entram nos YAML sem alterar o schema canónico.
    """

    OWASP_TM = "owasp_tm"
    OWASP_ASVS = "owasp_asvs"
    NIST_CSF = "nist_csf"
    ISO_27001 = "iso_27001"


def framework_display_name(catalog_id: str) -> str:
    """Rótulo curto para CLI / relatórios."""
    labels = {
        FrameworkCatalog.OWASP_TM.value: "OWASP Threat Modeling",
        FrameworkCatalog.OWASP_ASVS.value: "OWASP ASVS",
        FrameworkCatalog.NIST_CSF.value: "NIST CSF",
        FrameworkCatalog.ISO_27001.value: "ISO/IEC 27001 (Annex A)",
    }
    return labels.get(catalog_id, catalog_id)
