"""Notas de voz e foco por metodologia dominante — sem alterar o motor."""

from __future__ import annotations

from otm_core_schema import ThreatModelMethodology

from .i18n_locale import PremiumReportLocale

# Table-driven (en_lines, pt_lines) per methodology — keeps cognitive complexity low.
_VOICE_LINES: dict[ThreatModelMethodology, tuple[list[str], list[str]]] = {
    ThreatModelMethodology.STRIDE: (
        [
            "Focus on spoofing, tampering, repudiation, information disclosure, DoS, and privilege escalation.",
            "Map components, flows, and trust boundaries explicitly for each relevant threat.",
        ],
        [
            "Foco em spoofing, tampering, repudiation, information disclosure, DoS e elevação de privilégio.",
            "Mapear explicitamente componentes, fluxos e trust boundaries para cada ameaça relevante.",
        ],
    ),
    ThreatModelMethodology.LINDDUN: (
        [
            "Emphasis on linking, identifying, detecting, disclosure, unawareness, and non-compliance.",
            "Highlight PII, consent, retention, and minimization when applicable to the model.",
        ],
        [
            "Ênfase em linking, identifying, detecting, disclosure, unawareness e non-compliance.",
            "Dar destaque a PII, consentimento, retenção e minimização quando aplicável ao modelo.",
        ],
    ),
    ThreatModelMethodology.NIST_DATA_CENTRIC: (
        [
            "Prioritize data types, data states, and sensitive routes.",
            "Access controls and protection across the data lifecycle.",
        ],
        [
            "Priorizar tipos de dados, estados do dado e rotas sensíveis.",
            "Controles de acesso e proteção ao longo do ciclo de vida do dado.",
        ],
    ),
    ThreatModelMethodology.PASTA: (
        [
            "Oriented to attacker goals, attack surface, and impact.",
            "Findings should be read as risk-oriented, not taxonomy-only.",
        ],
        [
            "Orientação a objetivos do atacante, superfície de ataque e impacto.",
            "Findings devem ser interpretados como orientados a risco, não apenas taxonomia.",
        ],
    ),
    ThreatModelMethodology.PLOT4AI: (
        [
            "Focus on prompt/input, retrieval/grounding, vector/embedding, and tool execution.",
            "Governance, auditing, and provider dependency are central to prioritization.",
        ],
        [
            "Foco em prompt/input, retrieval/grounding, vector/embedding e execução de ferramentas.",
            "Governança, auditoria e dependência de provider são centrais na priorização.",
        ],
    ),
}


def methodology_voice_lines(
    methodology: ThreatModelMethodology,
    locale: PremiumReportLocale,
) -> list[str]:
    """Textos curtos para secções do relatório (estruturais, bilíngues)."""
    pair = _VOICE_LINES.get(methodology)
    if pair is not None:
        return pair[0] if locale == "en" else pair[1]
    if locale == "en":
        return [
            f"Methodology `{methodology.value}`: interpret threats in the context of the corresponding engine rules.",
        ]
    return [
        f"Metodologia `{methodology.value}`: interpretar ameaças no contexto das regras do engine correspondente.",
    ]
