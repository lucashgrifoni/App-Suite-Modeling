"""Notas de voz e foco por metodologia dominante — sem alterar o motor."""

from __future__ import annotations

from otm_core_schema import ThreatModelMethodology


def methodology_voice_lines(methodology: ThreatModelMethodology) -> list[str]:
    """Textos curtos para secções do relatório."""
    m = methodology
    if m == ThreatModelMethodology.STRIDE:
        return [
            "Foco em spoofing, tampering, repudiation, information disclosure, DoS e elevação de privilégio.",
            "Mapear explicitamente componentes, fluxos e trust boundaries para cada ameaça relevante.",
        ]
    if m == ThreatModelMethodology.LINDDUN:
        return [
            "Ênfase em linking, identifying, detecting, disclosure, unawareness e non-compliance.",
            "Dar destaque a PII, consentimento, retenção e minimização quando aplicável ao modelo.",
        ]
    if m == ThreatModelMethodology.NIST_DATA_CENTRIC:
        return [
            "Priorizar tipos de dados, estados do dado e rotas sensíveis.",
            "Controles de acesso e proteção ao longo do ciclo de vida do dado.",
        ]
    if m == ThreatModelMethodology.PASTA:
        return [
            "Orientação a objetivos do atacante, superfície de ataque e impacto.",
            "Findings devem ser interpretados como orientados a risco, não apenas taxonomia.",
        ]
    if m == ThreatModelMethodology.PLOT4AI:
        return [
            "Foco em prompt/input, retrieval/grounding, vector/embedding e execução de ferramentas.",
            "Governança, auditoria e dependência de provider são centrais na priorização.",
        ]
    return [
        f"Metodologia `{m.value}`: interpretar ameaças no contexto das regras do engine correspondente.",
    ]
