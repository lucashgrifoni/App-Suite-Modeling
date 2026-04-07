# Scorecard executivo — release readiness (2026-04-01)

**Projeto:** App Suite Modeling / **`open-threat-model`**  
**Decisão resumida:** **GO WITH CAVEATS** (ver [`FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md`](FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md))

Escala de notas: **0–10**. Estados: **FAIL** · **WEAK** · **OK** · **STRONG**

---

## Por eixo

| Eixo | Nota | Status | Comentário |
|------|------|--------|------------|
| **Product positioning** | 8.5 | **STRONG** | Problema, audiência e diferencial claros; escopo honesto na documentação. |
| **README quality** | 8.0 | **STRONG** | Topo vende bem; maturidade explícita; falta só *proof* visual (PNG). |
| **Onboarding / quick start** | 8.5 | **STRONG** | Caminho CLI + dev stack documentado; extras `api` clarificados. |
| **Documentation architecture** | 8.0 | **OK→STRONG** | Índice bom; volume alto — risco de sobrecarga para novatos mitigado pelo `docs/README.md`. |
| **OSS readiness** | 8.0 | **STRONG** | MIT, CONTRIBUTING, SECURITY, CoC, issue/PR templates (pós-rodada). |
| **Visual presentation** | 5.5 | **WEAK** | Guia e tabela existem; assets reais ainda não no README. |
| **Engineering trust** | 9.0 | **STRONG** | CI largo, mypy/bandit/semgrep/trivy, 411 testes Python verdes (ambiente completo). |
| **Launch readiness** | 7.5 | **OK** | Pronto para abrir o repo; *polish* visual e tag de release melhoram a narrativa pública. |

---

## Nota global (média simples)

**Aproximadamente 7.9 / 10** — nível **forte** para OSS técnico, com **ponto fraco único** visível na *storytelling* visual.

---

## Top blockers

*Nenhum blocker duro para publicação técnica.*

“Blockers *moles*” para impacto máximo:

1. Ausência de screenshots no README.  
2. Badge de CI com URL de repositório real (pós-publicação).

---

## Top strengths

1. **Profundidade de engenharia** e testes alinhados a um domínio difícil (threat modeling).  
2. **Tripla superfície** (CLI/API/UI) sem divergência arbitrária de contrato.  
3. **Documentação de maturidade e limitações** — reduz *overselling* e litígio de expectativas.  
4. **Pipelines de segurança** integrados (SCA, SAST estático, imagem).

---

## Decisão em uma linha

**GO WITH CAVEATS:** lançamento público recomendado com reforço visual opcional e release notes alinhadas a `7.2.0`.
