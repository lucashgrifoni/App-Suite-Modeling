# Smoke Validation (Release Candidate)

Validação funcional mínima para garantir prontidão de release incremental.

## Escopo

- CLI básico
- API básico
- análise STRIDE
- análise LINDDUN
- análise PASTA
- análise PLOT4ai
- export principal
- build mínimo de UI

## Como rodar

```bash
python -m pytest tests/test_smoke_release_candidate.py
```

### E2E smoke mínimo da UI (headless)

```bash
cd apps/web
npm ci
npx playwright install chromium
npm run e2e:smoke
```

### Build da UI

Linux/macOS:

```bash
cd apps/web
npm ci
npm run ci:build
```

Windows (fallback oficial):

```bash
cd apps/web
npm ci
npm run ci:build:portable
```

## Resultado esperado

- Status code 200 em endpoints principais da API
- CLI com `exit_code == 0` nos fluxos básicos
- Análises retornando metodologia correta e resumo
- Export retornando artefato `analysis_markdown`
- Build UI concluído sem erro (padrão ou portátil)

## Critérios de aprovação

- Todos os smoke tests passam.
- Build UI validado em pelo menos um caminho oficial por ambiente.
- Sem regressão em contratos de análise.
- E2E smoke mínimo da UI passa no caminho feliz.

## Checklist curto de validação (inovação)

- [ ] `diff` / `compare` devolvem insights e `explanations` sem erro.
- [ ] `imports` devolvem `inferences` + `explanations` no mesmo lote.
- [ ] `backlog` gera itens com `explanations` e ranking estável.
- [ ] `analyze --methodology plot4ai` devolve `methodology_insights` e `ai_system_context`.
- [ ] `otm analyze --explain` e `otm explain` mantêm saída curta e útil.

## Checklist curto de validação (PLOT4ai precisão residual)

- [ ] Fixtures positivas `otm-ai-001..005` continuam a activar contexto IA e heurísticas `plot4ai_*` esperadas.
- [ ] Fixtures negativas `otm-nai-001` e `otm-nai-002` **não** activam `plot4ai_*` com metodologia PLOT4ai forçada.
- [ ] `looks_like_ai_context` mantém gate token-safe (`rag`/`llm`) e marcador `ai` com termos acompanhantes.
- [ ] Casos anti-substring (`outrage`, `airflow`) mantêm resultado negativo nos testes.
- [ ] `import_signals_corpus` é preenchido por OpenAPI/Kubernetes/Terraform/Helm quando houver sinais úteis.
- [ ] Contratos (`ai_system_context`, `explanations`, `import_signals_corpus`) permanecem compatíveis (campos opcionais).
