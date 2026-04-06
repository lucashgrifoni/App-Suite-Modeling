"""Notas de voz e foco por metodologia dominante — sem alterar o motor."""

from __future__ import annotations

from otm_core_schema import ThreatModelMethodology

from .i18n_locale import PremiumReportLocale


def methodology_voice_lines(
    methodology: ThreatModelMethodology,
    locale: PremiumReportLocale,
) -> list[str]:
    """Textos curtos para secções do relatório (estruturais, bilíngues)."""
    m = methodology
    en = locale == "en"

    if m == ThreatModelMethodology.STRIDE:
        if en:
            return [
                "Focus on spoofing, tampering, repudiation, information disclosure, DoS, and privilege escalation.",
                "Map components, flows, and trust boundaries explicitly for each relevant threat.",
            ]
        return [
            "Foco em spoofing, tampering, repudiation, information disclosure, DoS e elevação de privilégio.",
            "Mapear explicitamente componentes, fluxos e trust boundaries para cada ameaça relevante.",
        ]
    if m == ThreatModelMethodology.LINDDUN:
        if en:
            return [
                "Emphasis on linking, identifying, detecting, disclosure, unawareness, and non-compliance.",
                "Highlight PII, consent, retention, and minimization when applicable to the model.",
            ]
        return [
            "Ênfase em linking, identifying, detecting, disclosure, unawareness e non-compliance.",
            "Dar destaque a PII, consentimento, retenção e minimização quando aplicável ao modelo.",
        ]
    if m == ThreatModelMethodology.NIST_DATA_CENTRIC:
        if en:
            return [
                "Prioritize data types, data states, and sensitive routes.",
                "Access controls and protection across the data lifecycle.",
            ]
        return [
            "Priorizar tipos de dados, estados do dado e rotas sensíveis.",
            "Controles de acesso e proteção ao longo do ciclo de vida do dado.",
        ]
    if m == ThreatModelMethodology.PASTA:
        if en:
            return [
                "Oriented to attacker goals, attack surface, and impact.",
                "Findings should be read as risk-oriented, not taxonomy-only.",
            ]
        return [
            "Orientação a objetivos do atacante, superfície de ataque e impacto.",
            "Findings devem ser interpretados como orientados a risco, não apenas taxonomia.",
        ]
    if m == ThreatModelMethodology.PLOT4AI:
        if en:
            return [
                "Focus on prompt/input, retrieval/grounding, vector/embedding, and tool execution.",
                "Governance, auditing, and provider dependency are central to prioritization.",
            ]
        return [
            "Foco em prompt/input, retrieval/grounding, vector/embedding e execução de ferramentas.",
            "Governança, auditoria e dependência de provider são centrais na priorização.",
        ]
    if en:
        return [
            f"Methodology `{m.value}`: interpret threats in the context of the corresponding engine rules.",
        ]
    return [
        f"Metodologia `{m.value}`: interpretar ameaças no contexto das regras do engine correspondente.",
    ]
