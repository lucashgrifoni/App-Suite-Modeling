# App Suite Modeling — Relatório da rodada integrada (fecho elite)

Entrega após execução das frentes: **superfície OpenAPI fechada para o SPA**, **gate CI anti-stale**, **E2E híbrido (API real)**, **goldens HTTP semânticos**, mantendo **semantic diff v1.4**, **benchmark 38**, e restante maturidade já existente.

---

## 1. Resumo executivo

| Frente | Resultado |
|--------|-----------|
| Contratos | **Precheck** (`ModelPrecheckResponse`), **diff** (`ThreatModelDiff`), **analyses/diff** (`AnalysisDiff`), **remediation/backlog** JSON (`RemediationBacklog`), **exports** / **imports** com `response_model`; **premium** documentado por media type; `contracts/openapi.json` + TS gerado. |
| Gate OpenAPI | `scripts/verify_openapi_up_to_date.py` + CI Python; `npm run contracts:verify`. |
| E2E | `e2e:critical` **6** testes (mocks); `e2e:hybrid` **3** testes (uvicorn + Vite); job CI `hybrid-e2e`. |
| Goldens HTTP | `tests/test_http_response_goldens.py` + `http_api_semantic_expectations.json` para `/analyze` e `/compare`. |
| Anti-patterns 3.0 | `structural_primary` + mensagens dedicadas; admin/API/upload/e-commerce com disparo ancorado no grafo. |
| Repo import | `.py` + FastAPI/Flask/uvicorn; `detected_stacks`; `stack_hint`; hint de boundary para FastAPI. |
| Semantic diff 1.4 | `link_kind`, `inference_strength` `low`, `shared_tokens`; `entity_topic_correlation` como segunda camada; `change_category` nas refs; `comparison_contract_version` **1.4**. |
| Benchmark | `min_model_completeness_score` **38** nos quatro casos wave. |
| UX | Diff: microcopy v1.4; exibição de tipo de ligação e categoria de mudança nas refs. |

---

## 2. Disciplina de skills (aplicação real)

- **Arquitetura / dívida:** `meta` como modelo Pydantic com `extra="allow"` — fecho contratual sem bloquear evolução; sem parser pesado no import.
- **Contratos / AppSec:** OpenAPI espelha campos semânticos; disclaimers explícitos em motor, Markdown e UI.
- **Testes / quality gate:** OpenAPI verificado no CI; contract tests por `$ref`; goldens semânticos sem snapshot gigante; E2E híbrido honesto (links interpretativos opcionais).
- **UI / design system:** blocos existentes (`InterpretationLinksBlock`, `StructuralRefsBlock`) com costura textual e dados estruturados.
- **Readiness:** CHANGELOG, `docs/CONTRACTS_CI_HYBRID.md`, `docs/API.md` (ponte), `contracts:sync` / `contracts:verify`.

---

## 3. Contratos e tipagem

- **Backend:** routers `models`, `analyses`, `remediation`, `exports`, `imports`, `reports_premium` (último: respostas por tipo MIME).
- **Artefactos:** `contracts/openapi.json`, `export_openapi.py`, `verify_openapi_up_to_date.py`.
- **Frontend:** `npm run contracts:sync` | `contracts:verify`.
- **Testes:** `tests/test_openapi_contract_file.py` — schemas + `$ref` de precheck, diff, analyses/diff, remediation JSON.

---

## 4. E2E

- **Mocks:** `e2e:critical` — **6 passed**.
- **Híbrido:** `playwright.hybrid.config.ts`, `e2e/hybrid.spec.ts`, fixture `e2e/fixtures/minimal-document.json` — **3 passed**; `npm run e2e:hybrid`.

---

## 5. Anti-patterns 3.0

- **Código:** `structural_primary`, `structural_primary_message`, `_bump_confidence`, ramo dedicado com `detection_sources` contendo `structural:primary`.
- **Dados:** `catalog.yaml` — admin (trust boundary + id admin), upload (≥3 fluxos + `supports_file_upload`), API gateway + cross-boundary, e-commerce + cross-boundary.
- **Teste:** `test_structural_primary_gateway_cross_boundary_without_rate_keywords`.

---

## 6. Repo import

- **Ficheiro:** `repo_scan.py` — sufixo `.py`, regex FastAPI/Flask/ASGI, `detected_stacks`, `stack_hint`, hint `repo_inference:python_fastapi`.
- **Teste:** `test_scan_detects_python_fastapi_signals`, extensão de `test_scan_node_express_repo_finds_route_and_signals` para `javascript_family`.

---

## 7. Semantic diff 1.4

- **Motor:** `semantic_comparison.py` — `_interpretation_links` (lexical + tópico por `entity_kind`), `semantic_insights_version` **1.4**.
- **Orquestração:** `threat_model_comparison.py` — `ComparisonResultMeta.model_validate`, `comparison_contract_version` **1.4**.
- **Canais:** `comparison_markdown.py`, `cli.py`, `DiffPage.tsx` (`diff-interpretation-links`, `diff-structural-refs`).
- **Testes:** `test_semantic_comparison.py`, `test_comparison_ts_contract_alignment.py`.

---

## 8. Benchmark / golden

- `tests/fixtures/golden/benchmark_expectations_v1.json` — completude mínima **38** (quatro templates principais).

---

## 9. UX executiva

- `DecisionCockpit.tsx` — texto que liga pré-check a **Comparar** / **Exportar**.
- `DiffPage.tsx` — v1.4, tipo de ligação e força inferencial visíveis; categoria nas refs.

---

## 10. Ficheiros principais (criados ou alterados)

**Alterados (esta continuação):** `comparison_models.py`, `semantic_comparison.py`, `threat_model_comparison.py`, `comparison_markdown.py`, `cli.py`, `test_semantic_comparison.py`, `test_comparison_ts_contract_alignment.py`, `test_openapi_contract_file.py`, `DiffPage.tsx`, `api.ts`, `journeys.spec.ts`, `contracts/openapi.json`, `openapi.d.ts`, `CHANGELOG.md`, `audit-gpt.md`, `docs/THREAT_MODEL_DIFF.md`.

---

## 11. Validação executada

| Comando | Resultado |
|---------|-----------|
| `python -m pytest tests -q` | **367 passed** |
| `python scripts/verify_openapi_up_to_date.py` | OK |
| `npm run typecheck` / `build` (apps/web) | OK |
| `npm run e2e:critical` | **6 passed** |
| `npm run e2e:hybrid` | **3 passed** |

---

## 12. Limitações remanescentes

- **`ComparisonResultMeta`** permite `additionalProperties` — extensões não documentadas no schema podem existir; campos semânticos estáveis estão cobertos por testes + TS.
- **Import Python** é heurística por regex (com sinais opcionais leves onde existirem), não AST completo.
- **Ligações v1.4** permanecem proxies (`low`) — omitidas quando não há overlap lexical nem correlação por tópico.
- **Premium** e **remediation Markdown** não têm um único schema JSON — por desenho (conteúdo textual/binário).
- **E2E híbrido** exige Python com `otm_api` instalado no ambiente que corre Playwright.

---

## 13. Avaliação honesta: 9.5+?

**Aproximação:** integração **motor ↔ OpenAPI ↔ TS ↔ UI ↔ E2E** para o diff semântico subiu um degrau (meta tipado, v1.4 ancorado, testes e E2E mais exigentes). **9.5+ “real”** no sentido de produto fechado de ponta a ponta ainda depende de: (1) `response_model` / OpenAPI para **todos** os payloads que o SPA consome em produção; (2) CI que falhe se `openapi.json` estiver stale; (3) E2E contra API real ou contract tests HTTP para rotas críticas; (4) import multi-stack com fixtures de repos mínimos verificáveis.

---

## 14. O que ainda falta para nota elite máxima

1. Cobertura OpenAPI + tipos gerados para **precheck, remediation, premium** e outros endpoints ainda genéricos.
2. Gate CI em `python scripts/export_openapi.py` + diff do `contracts/openapi.json`.
3. E2E híbrido (servidor de teste + UI) para fluxos que hoje usam só mocks.
4. Goldens pequenos para respostas HTTP reais de `/compare` e `/analyze`.

---

*Última validação: pytest 367; verify_openapi OK; e2e:critical 6; e2e:hybrid 3; build/typecheck web OK.*
