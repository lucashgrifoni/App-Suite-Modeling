"""
Backlog de remediação inteligente (não é gestor de tarefas).

Fluxo: `AnalysisResult` (+ opcional `ThreatModelDocument`) → `RemediationBacklog`.
"""

from otm_threat_engine.remediation.build import build_remediation_backlog
from otm_threat_engine.remediation.models import (
    BACKLOG_CONTRACT_VERSION,
    BacklogItem,
    FindingRef,
    RemediationBacklog,
)

__all__ = [
    "BACKLOG_CONTRACT_VERSION",
    "BacklogItem",
    "FindingRef",
    "RemediationBacklog",
    "build_remediation_backlog",
]
