"""
Explainability — contrato reutilizável para methodology, threat engine, backlog, import, diff.
"""

from otm_explainability.ids import explanation_id
from otm_explainability.records import (
    ConfidenceLevel,
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
)

__all__ = [
    "ConfidenceLevel",
    "ExplanationCategory",
    "ExplanationRecord",
    "ExplanationType",
    "RelatedEntityRef",
    "explanation_id",
]
