## Rodada de qualidade de engenharia — relatório

Objetivo: elevar qualidade interna (Clean Code/Clean Architecture/SOLID/SoC) **sem abrir features**, **sem quebrar contratos** (schema/API/CLI/outputs) e com **validação real** após mudanças.

---

### Escopo executado (alto impacto / baixo risco)

#### 1) CLI (`otm`)
- **Deduplicação de tratamento de erros e I/O**
  - Extração de helpers para reduzir repetição e manter UX previsível:
    - carregamento de documento/pack com erro consistente
    - emissão de texto para stdout/arquivo
    - escrita JSON em arquivo com UTF-8
- **Contratos reforçados em testes**
  - `export --output` escreve arquivo JSON válido
  - `analyze --pack <inexistente>` retorna `exit_code = 1`

#### 2) API (FastAPI)
- **Deduplicação de parsing/validação do documento**
  - Helper único para `document_from_payload + 422 DOCUMENT_VALIDATION_ERROR`.
- **Padronização interna de `detail` nos erros**
  - Helper `error_detail(...)` para compor `detail` em `HTTPException` mantendo shapes existentes:
    - `PACK_NOT_FOUND`, `TEMPLATE_NOT_FOUND`, `TEMPLATE_INVALID`, `ANALYSIS_VALIDATION_ERROR`, `DOCUMENT_VALIDATION_ERROR`.
- **Services mais coesos**
  - `build_exports`: centralização do “analysis required” com `_require_analysis(...)`.
  - Remoção de import não usado em `templates_catalog`.

#### 3) Exporters (pacotes Python)
- **Markdown do motor**
  - Refatoração por extração e melhor coesão (sem alterar output).
  - **Snapshot test** para travar o Markdown gerado em modo harmonized.
- **Bundle JSON**
  - Evitado snapshot gigante (frágil) e adotado **testes determinísticos** de contrato.
  - Novo helper `export_threat_model_bundle_obj(...)` para composição/testes.
- **Mermaid**
  - Teste de contrato reforçado (sanitização de IDs + aspas + newline).
  - Refatoração mínima: `_mermaid_label(...)`.
- **Document/Analysis JSON**
  - Testes reforçados para equivalência `string JSON` vs `obj dict` em exportadores.

#### 4) Web (React/TS)
- **Cliente HTTP com erros mais úteis**
  - `ApiError.message` agora tenta formatar `detail.code` + `detail.message` quando disponível, sem mudar o contrato.
- **Tipos sem duplicação**
  - `analyzeDocument(...).options.methodology` passou a usar `MethodologyId` (tipo central).

---

### Arquivos alterados (visão por área)

#### CLI
- `apps/cli/otm_cli/cli.py`
- `tests/test_cli.py`

#### API
- `apps/api/otm_api/routers/_errors.py`
- `apps/api/otm_api/routers/models.py`
- `apps/api/otm_api/routers/exports.py`
- `apps/api/otm_api/routers/templates.py`
- `apps/api/otm_api/services/exports.py`
- `apps/api/otm_api/services/templates_catalog.py`
- `tests/test_api.py`

#### Exporters / Core libs
- `packages/exporters/otm_exporters/analysis_markdown.py`
- `packages/exporters/otm_exporters/bundle_json.py`
- `packages/exporters/otm_exporters/document_json.py`
- `packages/exporters/otm_exporters/analysis_json.py`
- `packages/exporters/otm_exporters/mermaid_flowchart.py`
- `packages/exporters/otm_exporters/__init__.py`
- `tests/test_exporters.py`
- `tests/snapshots/analysis_markdown_minimal_harmonized.md`

#### Web
- `apps/web/src/api/client.ts`
- `apps/web/src/api/otmApi.ts`

#### Docs
- `docs/archive/legacy-md-2026-03-24/packages/industry-packs/README.md` (correção de link interno)

---

### O que foi preservado (garantias)
- **Schema canônico**: sem mudanças de contrato.
- **API**: endpoints e shapes principais preservados; erros `detail` travados por testes.
- **CLI**: comandos, mensagens e códigos de saída preservados; contratos travados por testes.
- **Outputs**: Markdown do motor travado por snapshot; Mermaid/bundle/document/análise com contratos testados.
- **UI**: build portable e e2e smoke passando.

---

### Validação executada (evidência de segurança)
- `python -m pytest` (suite completa) — verde
- `python -m pytest tests/test_smoke_release_candidate.py` — verde
- `python scripts/run_test_app_validation.py` — verde
- `python scripts/run_global_regression_gate.py` — verde (inclui build web portable + Playwright e2e smoke portable)

---

### Riscos residuais
- **Baixos**: as mudanças foram incrementais, cobertas por testes de contrato e pelo gate completo.
- **Dívida histórica**: existem lints/formatos fora do escopo (não tratados para evitar refatoração cosmética em massa).

---

### Próximas melhorias sugeridas (opcionais, mantendo filosofia)
- Expandir contratos determinísticos para mais outputs (ex.: bundle + packs, e cenários com templates).
- Adicionar `ruff format`/padronização de imports gradualmente “por arquivo tocado”.
- Consolidar constantes de UI (ex.: labels de frameworks) e reduzir duplicações entre páginas, com testes/e2e cobrindo.

---

### Plano sugerido de commits (para não misturar entregas)

Ver `docs/QUALITY_COMMIT_PLAN.md`.

