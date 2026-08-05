# Scorecard executivo — qualidade e prontidão

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Projeto:** App Suite Modeling  
**Data de referência da auditoria:** 2026-04-06  
**Nota geral:** **7,0 / 10**

---

## Nota por categoria

| Categoria | Nota | Status |
|-----------|------|--------|
| Clean Code | 6,5 | ACEITÁVEL |
| Clean Architecture | 7,5 | BOM |
| Frontend / UI | 7,2 | BOM |
| Backend / Engine | 7,8 | BOM |
| Security | 5,8 | ACEITÁVEL |
| Testability | 8,0 | EXCELENTE |
| DevSecOps / Release Readiness | 6,3 | ACEITÁVEL |
| Maintainability | 7,0 | BOM |

**Legenda de status:**  
EXCELENTE (≥8,5) · BOM (7,0–8,4) · ACEITÁVEL (5,5–6,9) · FRACO (4,0–5,4) · CRÍTICO (<4,0)

---

## Top 10 gaps

1. CLI monolítica (`apps/cli/otm_cli/cli.py`, ~1272 linhas) — risco de regressão e onboarding lento.
2. API sem autenticação/autorização — adequado só com trust boundary explícita (rede confiável / gateway).
3. CORS e métodos/headers abertos no middleware de desenvolvimento — reavaliar para ambientes não locais.
4. `mypy` presente nas dependências de dev mas **não** executado no CI (`.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml`).
5. `sonar-project.properties` sem integração visível no pipeline CI — qualidade “opt-in manual”.
6. E2E no CI limitado a smoke; suites `e2e:critical` / `e2e:phase4` não bloqueiam merge.
7. Duas bases de UI (`apps/web`, `gitpage`) — risco de inconsistência visual e de segurança de conteúdo.
8. Extra `sqlalchemy` em `[api]` sem uso em `apps/api` — ruído e superfície de manutenção.
9. Ruff com regras mínimas — menos deteção automática de complexidade e bugs.
10. Estado do modelo em `sessionStorage` — superfície XSS herdada da origem; depende de CSP/sanitização rigorosas.

---

## Top 10 pontos fortes

1. Separação clara **domínio / motor / adaptadores** (packages vs `apps/api`, `apps/cli`).
2. Script `scripts/check_core_adapter_boundary.py` — **enforcement** de dependências no núcleo.
3. API com validação Pydantic e erros estruturados (`apps/api/otm_api/routers/_errors.py`).
4. Motor extensível (packs, heurísticas, anti-padrões, múltiplas metodologias).
5. **Suite de testes Python extensa** + smoke de release (`tests/test_smoke_release_candidate.py`).
6. Testes de alinhamento contrato TS ↔ backend (`tests/test_analysis_ts_contract_alignment.py`, `tests/test_comparison_ts_contract_alignment.py`).
7. UI com **design tokens** (CSS vars + Tailwind `otm.*`) e code-splitting por rota.
8. Import de artefactos com **limite de tamanho** explícito (2 MiB).
9. Documentação de segurança para reporte responsável (`SECURITY.md`).
10. Consciência explícita de não renderizar HTML não confiável em diagramas (`apps/web/src/utils/diagramSanitize.ts`).

---

## Top 5 ações de maior impacto

1. **Modularizar o CLI** e adicionar testes por comando — reduz risco e acelera evolução.
2. **Adicionar `mypy --strict` gradual** ao CI — reduz bugs de contrato em runtime.
3. **Expandir E2E obrigatório** (pelo menos `e2e:critical`) — captura regressões de jornada.
4. **Política de deployment:** documentar e, se aplicável, implementar auth + CORS por ambiente.
5. **SCA automatizado** (pip audit / dependabot + npm audit no CI) — reduz risco de cadeia de dependências.

---

## Parecer final: GO / PARTIAL GO / NO GO

| Cenário | Parecer |
|---------|---------|
| Uso como **ferramenta local / OSS** com operadores técnicos | **GO** |
| **Release** com expectativa de API exposta a redes não confiáveis sem camada extra | **NO GO** |
| **Merge contínuo** com confiança máxima em UI e tipos estáticos | **PARTIAL GO** |

**Parecer agregado:** **PARTIAL GO** — excelente núcleo e testes; faltam gates e endurecimento para cenários “prod aberto” e para reduzir dívida estrutural no CLI.

---

## Trade-offs assumidos (explícitos)

- **Simplicidade de desenvolvimento** (CORS localhost, sem auth) vs **segurança de deployment genérico** — trade-off razoável para MVP local, **desde que documentado**.
- **Velocidade de CI** (smoke E2E apenas) vs **cobertura de regressão UI** — trade-off que aumenta risco de falhas visíveis ao utilizador.

---

## Nota histórica — perspectiva “bar Staff/Principal”

Uma auditoria paralela destacou **observabilidade / operação** como dimensão mais fraca (~4,5/10) quando a API não tinha logging estruturado nem correlação de pedidos. **Estado atual:** `request_id`, logs JSON, mypy e SCA no CI, CORS por ambiente — ver [`CI_AND_SECURITY_EVIDENCE.md`](../../CI_AND_SECURITY_EVIDENCE.md). O veredicto qualitativo permanece: **excelente núcleo e contratos**; **deployment público** exige camada extra (gateway/auth) e disciplina documentada em [`DEPLOYMENT_INVARIANTS.md`](../../architecture/DEPLOYMENT_INVARIANTS.md).
