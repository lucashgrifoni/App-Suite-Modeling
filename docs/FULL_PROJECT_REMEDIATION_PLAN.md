# Plano de execução por fases — remediação e elevação de qualidade

Este plano traduz o backlog (`FULL_PROJECT_REMEDIATION_BACKLOG.md`) em entregas sequenciadas, com **ganhos**, **riscos** e **dependências**.

---

## Fase 1 — Correções críticas e de alto impacto

**Objetivo:** reduzir risco de regressão e elevar gates mínimos de qualidade sem redesenhar produto.

**Itens típicos:** BL-02 (mypy no CI), BL-03 (SCA básico), BL-01 início (extrair 2–3 comandos mais críticos do CLI para validar padrão).

**Ganhos esperados:** menos bugs de contrato; visibilidade de vulnerabilidades conhecidas em dependências; primeiro corte na complexidade do CLI.

**Riscos da fase:** mypy pode expor dezenas de erros legados — mitigar com `strict` gradual e allowlist por pacote.

**Dependências:** nenhuma externa crítica; requer acordo sobre nível inicial de strictness.

**Quick wins:** adicionar `mypy` apenas a `apps/api` e `packages/core-schema` primeiro; `pip-audit` com allowlist documentada.

---

## Fase 2 — Refactors estruturais

**Objetivo:** tornar o CLI e páginas UI sustentáveis.

**Itens:** BL-01 completo (módulos de comando + testes unitários por comando), BL-09 (WizardPage), BL-07 (remover sqlalchemy ou usar).

**Ganhos esperados:** velocidade de PR; testes mais rápidos e focados; menos conflitos em `cli.py`.

**Riscos:** regressões em caminhos Typer pouco testados — mitigar com matriz de testes dourada + smoke existente.

**Dependências:** Fase 1 (mypy) facilita refactor seguro.

**Quick wins:** mover um comando isolado (`validate`, `analyze`) para ficheiro próprio como template.

---

## Fase 3 — Melhorias de arquitetura e design

**Objetivo:** clarificar boundaries de deployment e consistência de produto.

**Itens:** BL-05/BL-06 (política de auth/CORS por ambiente ou documentação formal + gateway), BL-10 (tokens partilhados), BL-13 (`EngineConfig`), BL-14 (contratos versionados).

**Ganhos esperados:** projeto preparado para ambientes partilhados; menos deriva entre sites; motor mais testável.

**Riscos:** auth mal desenhada pode quebrar UX local — mitigar com *feature flag* ou perfis `dev`/`prod`.

**Dependências:** decisão de produto sobre hosting público vs apenas local.

**Quick wins:** variáveis de ambiente para CORS sem implementar OAuth completo.

---

## Fase 4 — Hardening final e padronização

**Objetivo:** fechar lacunas de qualidade contínua e OSS.

**Itens:** BL-08 (Sonar integrado), BL-11 (Ruff expandido), BL-12 (CSP/revisão XSS), BL-04 (E2E crítico no CI), BL-15 (badges/docs).

**Ganhos esperados:** quality gate contínuo; menor risco de regressão visual; imagem OSS mais profissional.

**Riscos:** Sonar/E2E aumentam tempo de CI — usar cache, sharding de testes, ou execução em `main` apenas para suite pesada.

**Dependências:** Fase 2 estável (CLI modular) para não duplicar fixes.

**Quick wins:** Sonar só em `main` inicialmente; E2E crítico em PR com `paths-filter` para `apps/web/**`.

---

## Mapa de dependências entre tarefas

```text
BL-02 (mypy) ───────────────► BL-01 (refactor CLI)
     │                              │
     └──────────────────────► BL-09 (Wizard)

BL-05/06 (seg deployment) independente de código se usar gateway externo;
se auth in-process, depende de design API v1.

BL-10 (tokens) pode paralelizar com BL-01 após convenção de naming.

BL-08 (Sonar) ideal após BL-02 (menos ruído inicial).
```

---

## Métricas de sucesso por fase (sugestão)

| Fase | Métrica |
|------|---------|
| 1 | CI verde com mypy em pacotes-alvo; 0 vulnerabilidades críticas SCA sem supressão abusiva |
| 2 | `cli.py` < 200 linhas (bootstrap); cada comando com teste dedicado |
| 3 | Documento `docs/DEPLOYMENT_THREAT_MODEL.md` + CORS via env |
| 4 | E2E crítico no CI; Sonar quality gate definido; CSP revisada |

---

## Notas finais

- **Não** é obrigatório executar todas as fases se o produto permanecer estritamente local — nesse caso, BL-05 pode ser substituído por documentação forte e exemplos Docker com rede interna.
- Reavaliar prioridades após cada release semestral.
