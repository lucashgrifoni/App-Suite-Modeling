# Explicabilidade (Explainability Engine)

## O que cobre

- **Metodologia**: recomendação automática com evidências do documento (regras + contexto).
- **Análise**: ameaças heurísticas, notas de risco quando o score/fronteira/ativo justificam,
  achados estruturais e de **trust boundary**.
- **Backlog**: por item — origem do achado, prioridade, *quick win* e sugestões de controlo (pack).
- **Importação de artefactos**: cada `InferenceRecord` mapeada para `ExplanationRecord` (`import_inference`).
- **Diff / comparação**: mudança estrutural principal, Δ de risco na análise, mudança de metodologia entre
  execuções, síntese do primeiro *insight* quando não redundante.

## Contrato (`ExplanationRecord`)

| Campo | Uso |
|-------|-----|
| `type` | Natureza (`methodology_recommendation`, `threat_heuristic`, `risk_score`, …). |
| `category` | Área (metodologia, threat, risk, backlog, import, diff, …). |
| `subject` | Título curto (≤ 200 caracteres). |
| `message` | Porquê, em linguagem directa. |
| `evidence` | Factos discretos que suportam a mensagem. |
| `confidence` | `low` \| `medium` \| `high` (dependência de dados explícitos vs heurística). |
| `related_entities` | Ligações a componentes, fluxos, ameaças, etc. |
| `reasoning_path` | Opcional — passos quando há cadeia de decisão. |

Pacote: `otm_explainability`.

## Como interpretar

- Priorize **`message` + `evidence`**: são o raciocínio auditável.
- `confidence=low` indica inferência fraca — não trate como garantia.
- Em análises longas, o Markdown limita a lista; o JSON (`explanations`) é completo.

## API e CLI

- `POST /v1/models/analyze` — campo `explanations` no `AnalysisResult`.
- `POST /v1/models/recommend-methodology` — `explanations` junto de `reason`.
- `POST /v1/imports/*` — `explanations` alinhadas às inferências.
- `POST /v1/models/compare` — `explanations` no `ThreatModelComparisonResult`.
- CLI: `otm analyze … --explain` (resumo no terminal); `otm explain <ficheiro.json> --from analysis|compare`.

## Limitações actuais

- Textos são **heurísticos**: não substituem parecer humano nem avaliação de risco formal.
- O número de explicações na análise cresce com ameaças ativas; filtros por tipo ficam a cargo do cliente.
- Alguns motores (ex.: todos os caminhos de *methodology insights* avançados) ainda não geram `ExplanationRecord` próprio — apenas o texto em `methodology_insights`.

## Expansão futura

- Explicações por *lens* metodológica com evidência do bloco activado.
- Agregação de explicações de diff com remapeamento semântico de IDs.
- Filtro padrão `max_explanations` por ambiente (dev vs relatório executivo).
