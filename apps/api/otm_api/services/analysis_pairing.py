"""
Correspondência entre um `document` e o `analysis` enviado ao lado dele (sem HTTP).

A API é sem estado: quem chama envia os dois artefactos. Enviar o documento A com a
análise do modelo B devolvia 200 e produzia um artefacto com duas identidades — o
backlog rotulado com o título e a metodologia de B, o relatório premium com o cabeçalho
de A e as ameaças de B. Nada no produto avisava.

A identidade é lida em `otm_threat_engine.analysis_identity`, o mesmo módulo que a CLI
(`otm report`, `otm backlog`, `otm diff-analysis`) usa — as duas superfícies respondiam à
mesma pergunta com critérios diferentes e discordavam uma da outra. Três divergências, cada
uma com o seu `errors[].type`:

- **título** (`…mismatch.title`) — sinal fraco: `otm init -t <template>` copia o título do
  template, por isso dois modelos diferentes colidem nele. Fica porque, quando difere, o par
  está mesmo trocado; nunca é o *único* critério.
- **entidades estranhas** (`…mismatch.components`) — a análise pendura ameaças em componentes,
  fluxos ou ativos que o documento não define, logo não foi produzida a partir dele.
- **componentes por analisar** (`…mismatch.stale_components`) — o documento define componentes
  que a análise nunca viu. É o sinal de *desactualização*: uma análise da revisão 1 referencia
  um subconjunto estrito da revisão 2, passava em todos os outros critérios, e o relatório
  inventariava o componente novo sem lhe apontar uma única ameaça.

Só é aplicado onde a análise **descreve o documento submetido**. Em `/v1/reports/premium`,
`baseline_analysis` é a análise de uma versão anterior *do documento que não foi enviado*:
não há com que a comparar, e a divergência é o objetivo do endpoint.

Isso isenta o baseline da guarda de *mesma revisão*, e não de guarda nenhuma — a distinção que
faltava. A pergunta certa para um baseline é a outra do vocabulário partilhado, "mesmo
sistema?", e é a que a CLI já fazia (`require_baseline_describes_same_system`). Sem ela, a API
aceitava o baseline de um modelo sem relação nenhuma e devolvia 200 com uma secção
`## Baseline / diff` a atribuir 13 ameaças adicionadas e 6 removidas a uma revisão que nunca
existiu, enquanto a CLI recusava o mesmo par de artefactos. Ver `baseline_system_mismatches`.

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
from otm_threat_engine.analysis_identity import (
    foreign_entity_ids,
    system_overlap,
    unanalysed_component_ids,
)


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

    foreign = foreign_entity_ids(document, analysis)
    if foreign:
        mismatches.append(
            {
                "loc": ["body", analysis_field, "heuristic_threats"],
                "msg": (f"{analysis_field} targets entities absent from the {document_field}: {', '.join(foreign)}"),
                "type": "analysis_document_mismatch.components",
            }
        )

    unanalysed = unanalysed_component_ids(document, analysis)
    if unanalysed:
        mismatches.append(
            {
                "loc": ["body", analysis_field, "heuristic_threats"],
                "msg": (
                    f"{analysis_field} never analysed components the {document_field} defines "
                    f"({', '.join(unanalysed)}); it was produced for an earlier revision"
                ),
                "type": "analysis_document_mismatch.stale_components",
            }
        )

    return mismatches


def baseline_system_mismatches(
    current: AnalysisResult,
    baseline: AnalysisResult,
    *,
    baseline_field: str = "baseline_analysis",
) -> list[dict[str, Any]]:
    """
    Divergências entre um baseline e a análise actual, no formato `errors[]` da API.

    Relação deliberadamente mais fraca do que `analysis_document_mismatches`: um baseline é
    outra revisão por definição, por isso nada aqui pode exigir que os dois concordem — nem o
    título (renomear entre releases é banal, e recusar custava o relatório inteiro), nem o
    conjunto de componentes (crescer é a mudança que um baseline existe para mostrar). Só se
    recusa a troca de sistema, na mesma medida que `otm report --baseline` e `diff-analysis`
    usam (`analysis_identity.system_overlap`).

    Lista e não booleano para acompanhar `analysis_document_mismatches`: a resposta 422 carrega
    `errors[]`, e a proporção medida é o que torna a recusa verificável por quem a lê.
    """
    overlap = system_overlap(baseline, current)
    if overlap.is_same_system:
        return []
    return [
        {
            "loc": ["body", baseline_field, "heuristic_threats"],
            "msg": (
                f"{baseline_field} shares {overlap.shared} of the {overlap.smaller} structural entities "
                "the smaller side models; a baseline is an earlier revision of the same system, so the "
                "diff would be invented"
            ),
            "type": "baseline_system_mismatch.structure",
        }
    ]
