# Plano de execução brutal — fases e critérios de saída

Este plano é **cruelmente honesto**: sem estas fases, **não há argumento credível** de “excelência Staff” para o repositório **como um todo**.

---

## Fase 1 — Riscos críticos (credibilidade e perímetro)

**Objetivo:** eliminar o que **desqualifica** o projeto como plataforma séria ou **documentar** invariantes com enforcement.

**Inclui:** B-03 (auth **ou** contrato “rede privada apenas” com exemplos e checks), B-04 (CORS/HTTP por ambiente), B-02 (logging mínimo na API), B-05 (mypy no CI).

**Critérios de saída (definição de pronto):**

- Cada request HTTP gera **pelo menos** um log com método, path, status, duração, `request_id`.  
- Build CI falha em **novos** erros mypy nos pacotes alvo.  
- Documento único `docs/DEPLOYMENT_INVARIANTS.md` descreve **quem pode chamar a API** e **em que redes**; se não há auth, isso está **explícito** e ligado a exemplos Docker/K8s network policies (mesmo que mínimos).

**Riscos da fase:** mypy explode — mitigar com strict por pacote. Logging pode vazar payloads — **nunca** logar corpo do documento; só metadados.

**Quick win:** variáveis `OTM_CORS_ORIGINS`, `OTM_ENV` lidas em `main.py` com defaults seguros quando `OTM_ENV=production`.

---

## Fase 2 — Arquitetura (teto de escala da equipa)

**Objetivo:** remover **god module** e reduzir **shotgun surgery**.

**Inclui:** B-01 (refactor CLI), B-10 (dois fronts), B-14 (dados gerados).

**Critérios de saída:**

- `cli.py` < 200 linhas (bootstrap).  
- Cada comando Typer com ficheiro próprio + **≥1** teste que não invoque o CLI inteiro (unitário da camada de aplicação).  
- Decisão escrita: **tokens partilhados** ou **fronts explicitamente independentes** (sem ambiguidade).

**Riscos:** regressões em comandos pouco usados — mitigar com matriz de smoke CLI alargada.

---

## Fase 3 — Qualidade e testes (gates que não mentem)

**Objetivo:** o CI reflete o que o README promete.

**Inclui:** B-06 (SCA), B-08 (E2E crítico), B-07 (Sonar ou remoção), B-11 (Ruff), B-13 (caracterização exporters).

**Critérios de saída:**

- Pipeline falha em **vulnerabilidades críticas** não justificadas (com processo de exceção).  
- `e2e:critical` (ou equivalente) **corre** em PR ou em gate de release.  
- Sonar integrado **ou** ficheiro removido com justificativa no README.

**Riscos:** tempo de CI — usar cache, `paths-filter`, ou job pesado só em `main`.

---

## Fase 4 — Hardening final (browser, dados, polish OSS)

**Objetivo:** reduzir superfície XSS e dívida cosmética.

**Inclui:** B-09 (CSP/sessionStorage), B-12 (exceções), B-15 (deps órfãs).

**Critérios de saída:**

- CSP documentada para o hosting estático; revisão de qualquer `innerHTML`/renderização de strings externas.  
- Extras `pyproject` coerentes com o código.

---

## Ganhos esperados por fase

| Fase | Ganho |
|------|--------|
| 1 | **Operável** e **defensável** perante AppSec/rede |
| 2 | **Velocidade de equipa** e menos medo de mudar |
| 3 | **Confiança** em merge e supply chain |
| 4 | **Menos vergonha** em demo pública e relatórios XSS |

---

## Dependências entre fases

```text
Fase 1 (perimetro + logs + mypy)
    └──► Fase 2 (CLI + fronts)  [mypy ajuda refactor]
    └──► Fase 3 (SCA/E2E/Sonar) [CLI estável evita flaky]
Fase 4 pode paralelizar com Fase 3 após Fase 1.
```

---

## Caminho mínimo até “excelência real” (definição usada nesta auditoria)

1. **Fase 1 completa** (não negociável para plataforma).  
2. **B-01 completo** (não negociável para escala de equipa).  
3. **B-06 + B-08** (não negociável para credibilidade DevSecOps).  

Só depois disto faz sentido discutir **10/10** sem rir.
