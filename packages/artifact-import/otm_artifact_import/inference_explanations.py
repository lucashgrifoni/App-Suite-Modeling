"""Mapeia `InferenceRecord` para o contrato canónico `ExplanationRecord`."""

from __future__ import annotations

from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_artifact_import.types import InferenceRecord


def explanations_from_inferences(records: list[InferenceRecord]) -> list[ExplanationRecord]:
    """Uma explicação por inferência; `subject` curto, `message` com o texto completo da inferência."""
    out: list[ExplanationRecord] = []
    for i, r in enumerate(records, start=1):
        subj = f"Inferência ({r.source})"
        rel = [RelatedEntityRef(entity_kind="component", entity_id=c) for c in r.related_component_ids[:8]]
        out.append(
            ExplanationRecord(
                id=explanation_id(i, prefix="exp_imp"),
                type=ExplanationType.IMPORT_INFERENCE,
                category=ExplanationCategory.IMPORT,
                subject=subj[:200],
                message=r.message,
                evidence=[f"Fonte declarada: {r.source}", f"Id da inferência: {r.id}"],
                confidence=r.confidence,
                related_entities=rel,
                reasoning_path=["Artefacto", "Parser", "Regra de inferência"],
            )
        )
    return out
