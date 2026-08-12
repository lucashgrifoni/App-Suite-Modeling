"""
Correspondência entre um `document` e o `analysis` enviado ao lado dele (sem HTTP).

A API é sem estado: quem chama envia os dois artefactos. Enviar o documento A com a
análise do modelo B devolvia 200 e produzia um artefacto com duas identidades — o
backlog rotulado com o título e a metodologia de B, o relatório premium com o cabeçalho
de A e as ameaças de B. Nada no produto avisava.

O `AnalysisResult` descreve-se a si próprio, por isso a incompatibilidade é detetável:

- `document_title` — a identidade que a análise carrega;
- `heuristic_threats[].target_component_id` — os componentes que a análise assume existirem.

Só é aplicado onde a análise **descreve o documento submetido**. Em `/v1/reports/premium`,
`baseline_analysis` é a análise de uma versão anterior *do documento que não foi enviado*:
não há com que a comparar, e a divergência é o objetivo do endpoint.

`/v1/models/compare` **não** é essa exceção, e tratá-lo como tal era um defeito: ali chegam
dois pares completos (`baseline` + `baseline_analysis`, `revised` + `revised_analysis`), e
cada análise descreve o documento que vem ao lado dela. Divergir *entre* os pares é o objetivo
do endpoint; divergir *dentro* de um par significa que o delta foi calculado a partir de
análises de outros modelos — e trocar as duas devolvia 200 com a transição ao contrário.
"""

from __future__ import annotations

from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_threat_engine import AnalysisResult


def _unknown_target_component_ids(document: ThreatModelDocument, analysis: AnalysisResult) -> list[str]:
    known = {c.id for c in document.components}
    referenced = {t.target_component_id for t in analysis.heuristic_threats if t.target_component_id}
    return sorted(referenced - known)


def analysis_document_mismatches(
    document: ThreatModelDocument,
    analysis: AnalysisResult,
    *,
    analysis_field: str = "analysis",
    document_field: str = "document",
) -> list[dict[str, Any]]:
    """
    Divergências entre a análise e o documento, no formato `errors[]` da API.

    Os nomes dos campos entram no `loc` e na mensagem: quem chama `/v1/models/compare` precisa
    de saber *qual* dos dois pares está trocado, não só que "analysis" não bate certo.
    """
    mismatches: list[dict[str, Any]] = []

    if analysis.document_title != document.metadata.title:
        mismatches.append(
            {
                "loc": ["body", analysis_field, "document_title"],
                "msg": (
                    f"{analysis_field}.document_title={analysis.document_title!r} does not match "
                    f"{document_field}.metadata.title={document.metadata.title!r}"
                ),
                "type": "analysis_document_mismatch.title",
            }
        )

    unknown = _unknown_target_component_ids(document, analysis)
    if unknown:
        mismatches.append(
            {
                "loc": ["body", analysis_field, "heuristic_threats"],
                "msg": (f"{analysis_field} targets components absent from the {document_field}: {', '.join(unknown)}"),
                "type": "analysis_document_mismatch.components",
            }
        )

    return mismatches
