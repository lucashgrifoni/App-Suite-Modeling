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

---

## Audit trail do assistente (`wizard_signal_trace`) e propagação

- **Modelo:** `WizardSignalTraceEntry` (`packages/threat-engine/otm_threat_engine/wizard_audit_models.py`).
- **Produção:** `wizard_signals.apply_wizard_context_to_heuristics`, `build_corpus_mitigation_trace` → agregado em `AnalysisResult.wizard_signal_trace`.
- **Consumo:** JSON de análise; export Markdown; report premium (`GuidedModelingAuditBlock`); resumo na CLI (`otm analyze`) quando há traço; diff Markdown com bloco semântico quando aplicável.

### Calibração anti-overfitting (admin / API / e-commerce)

- Boost em perfil **admin** exige **≥2** respostas negativas nos eixos `approval`/`segregation` e não coexistir com `approval=yes` como mitigador isolado.
- Negativa isolada → `observation` (`wz:internal_admin_portal:isolated_no`, `wz:api_backend_rest:isolated_no`) sem alterar scores.
- Testes: `tests/test_wizard_engine_integration.py`.

### Import de repositório — AST opcional (Express)

- `OTM_REPO_ESPRIMA=1` e extra `artifact_import_ast` (`esprima`). Função: `collect_express_routes_ast_lite` em `repo_ast_optional.py`.
- Sem flag ou sem `esprima`: só heurística regex (comportamento anterior).

### E2E cockpit

- `apps/web/e2e/cockpit.spec.ts` — jornada Home → modelo → Análise com mock enriquecido.

### Limitações

- AST cobre padrões simples Express; TS ou rotas dinâmicas podem falhar silenciosamente (fallback).
