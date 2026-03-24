# Release Candidate Checklist

Checklist técnico para publicação incremental de **App Suite Modeling**.

## 1) Checklist técnico obrigatório

- [ ] Schema canônico valida exemplos e documentos reais
- [ ] CLI funciona (`validate`, `analyze`, `export`, `report`)
- [ ] API responde (`/health`, `/v1/models/*`, `/v1/exports`)
- [ ] UI carrega e executa fluxo mínimo de análise
- [ ] Testes Python passam
- [ ] Smoke suite passa
- [ ] Build da UI validado (padrão ou portátil)
- [ ] Documentação atualizada (README + docs centrais)
- [ ] Branding consistente (nome, identidade, tokens)
- [ ] CHANGELOG atualizado
- [ ] Limitações conhecidas documentadas

## 2) Comandos de validação rápida

### Python (core/API/CLI/export)

```bash
python -m pytest
python -m pytest tests/test_smoke_release_candidate.py
```

### UI (Linux/macOS)

```bash
cd apps/web
npm ci
npm run ci:build
```

### UI (Windows com path problemático)

```bash
cd apps/web
npm ci
npm run ci:build:portable
```

## 3) Critério de aprovação

Release candidate aprovado quando:

1. Todos os testes passam.
2. Smoke suite passa.
3. Build UI validado por caminho oficial (ou portátil em Windows).
4. Docs e changelog refletem o estado real.
5. Limitações e riscos operacionais estão explícitos.
