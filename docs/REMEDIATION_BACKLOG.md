# Backlog de remediação (inteligente, não Jira)

Transforma `AnalysisResult` numa **lista acionável** com priorização heurística, agrupamentos e texto de explainability. **Não** substitui gestão de projecto nem atribuição formal de tarefas.

## Arquitetura

| Camada | Módulo | Papel |
|--------|--------|--------|
| Achados | `AnalysisResult` | Ameaças heurísticas, structural, trust boundary, hints de pack. |
| Candidatos | `remediation/build._item_*` | Cada achado activo → candidato a `BacklogItem`. |
| Classificação | `remediation/classify.py` | STRIDE + tipo de componente → causa raiz, tipo de controlo, camada. |
| Priorização | `remediation/build.py` | Score L×I (ou `risk.score`), etiquetas urgent/high/medium/low, `priority_rank`. |
| Dependências | `build.py` | Heurística: controlos de dados médio/alto podem depender do primeiro item de identidade. |
| Exportação | `otm_exporters/remediation_*` | Markdown e JSON legíveis. |

Contrato estável: `RemediationBacklog.schema_version` (actualmente `1.0`).

## Campos principais de cada item

- **id**, **title**, **description**, **rationale**
- **related_findings** (`kind` + `id`)
- **related_components** / **component_labels**
- **methodology_context**
- **suggested_control_type**, **control_category**, **grouped_root_cause**, **architecture_layer**
- **priority_rank**, **priority_label**, **priority_explanation**
- **effort_estimate**, **impact_estimate** (`low` \| `medium` \| `high`)
- **recommended_owner** (papel lógico ou `null`) + **owner_explanation**
- **quick_win**, **foundational**, **urgent** + explicações
- **next_step**, **depends_on_action_ids**, **explainability[]**

## Interpretação de prioridade / esforço / impacto

- **Prioridade**: derivada sobretudo de L×I (ou score agregado) com thresholds fixos — **heurística**, não avaliação de negócio.
- **Esforço / impacto**: regras simples por STRIDE, camada e magnitude de risco — útil para triagem, não para estimativas de sprint.
- **Quick win**: esforço baixo e (impacto alto ou score elevado).
- **Foundational**: reforço de identidade/acesso com risco não trivial (pode reduzir várias classes STRIDE).
- **Owner**: valores como `application_team`, `platform_engineering` — **nunca** pessoas; se `null`, o campo `owner_explanation` diz porquê.

## Agrupamentos

O objeto devolve dicionários:

- `by_root_cause`
- `by_control_type` (`suggested_control_type`)
- `by_control_category` (identidade, dados, exposição, observabilidade, integrações, AI, governação, transversal)

Notas em **synergy_notes** quando vários itens partilham a mesma causa raiz (ex.: vários achados IAM).

## CLI

```bash
otm backlog modelo.otm.yaml -f markdown --group-by root-cause -o backlog.md
otm backlog analyze.json --document modelo.otm.yaml -f json
```

## API

`POST /v1/remediation/backlog` com corpo `RemediationBacklogRequest`:

- `document` (obrigatório)
- `analysis` **ou** `run_analysis: true`
- Opcional: `pack_id`, `methodology`, `auto_recommend_methodology`

Query:

- `format=json` (default) — objeto completo
- `format=markdown` — relatório Markdown (`group_by` opcional: `root-cause`, `control`, `category`)

## UI

Na página **Análise**, após gerar resultado, o utilizador pode pedir o backlog (chamada à API). Vista compacta: resumo, top acções, quick wins.

## Limitações

- Não lê estado de Jira/Azure DevOps; não há workflow de estado.
- Mapa STRIDE→controlo é **genérico**; industrias específicas devem adaptar no pós-processamento.
- Dependências entre acções são **heurísticas** (não grafo de projecto completo).

## Próximos passos sugeridos

- Mapear `FrameworkRef` → catálogo interno de controlos.
- Templates de owner por `industry_pack_id`.
- Opcional: fundir itens com mesma causa raiz numa única “iniciativa” sem perder rastreio aos achados.
