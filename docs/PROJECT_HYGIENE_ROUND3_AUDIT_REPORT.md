# Auditoria — higiene rodada 3 (fecho canónico)

**Data:** 2026-04-07  
**Objetivo:** polir resíduos pós-round 2; **sem** nova reestruturação.

---

## 1. Executive summary

Triagem do `git status` identificou **pacote `docs/I18N_*.md` untracked** (16 ficheiros efectivos no working tree) com sobreposição forte: decisões, planos, checklists, auditorias e matrizes que duplicavam o mesmo conhecimento. **Decisão:** um único **`docs/I18N.md`** canónico; remoção de todos os `I18N_*.md`.

No **`CHANGELOG.md` [Unreleased]**, referências a relatórios CI já removidos (`*_EXECUTION_REPORT.md`) foram **atualizadas** para `docs/CI_AND_SECURITY_EVIDENCE.md` com nota explicativa. Entradas **históricas** `[7.0.0]`, `[6.0.0]`, `[5.0.0]` receberam **notas editoriais** curtas onde citavam ficheiros apagados, preservando o texto original.

**Índice:** `docs/README.md` ganhou linha **`I18N.md`**. **`PREMIUM_REPORTS.md`** aponta para `I18N.md` em vez de `I18N_FINAL_STATE.md`.

**`.gitignore`:** sem alteração obrigatória (artefactos já cobertos).

---

## 2. Triagem final (classificação)

| Item | Decisão |
|------|---------|
| `docs/I18N_*.md` (vários) | **Consolidar** → `docs/I18N.md`; **remover** shards |
| `docs/I18N.md` (novo) | **Preservar** como única fonte i18n |
| Relatórios `PROJECT_HYGIENE_ROUND2_*` | **Preservar** (histórico de round 2); não duplicar conteúdo na R3 |
| Outros `?? docs/*` (CI_AND_SECURITY, etc.) | **Preservar / promover** para commit (canónicos da R2) — não ignorar |
| Código `?? apps/`, `packages/`, `tests/` | **Fora do escopo R3** (entrega funcional); não `.gitignore`; commit em PR separado |
| `audit-gpt.md` (staged D) | Já removido; sem acção R3 |
| `.github/dependabot.yml` (??) | **Preservar** — útil; promover em commit de chore |

---

## 3. Pacote I18N — análise objetiva

| Pergunta | Resposta |
|----------|----------|
| Vivos e necessários? | Sim o **conhecimento**; não a **proliferação** de ficheiros. |
| Duplicados? | Sim — `DECISIONS` vs `EXPORTS_DECISIONS`, `FINAL_STATE` vs `ROLLOUT`, várias auditorias. |
| Rascunhos transitórios? | Planos/checklists de rollout **já executados** — valor como lista de verificação **condensada** em `I18N.md` §8. |
| Consolidar? | **Sim** → `docs/I18N.md`. |
| Remover do working tree? | **Sim** — `I18N_*.md`. |
| `.gitignore`? | **Não** — não são artefactos gerados; eram docs de trabalho. |
| Promover canónico? | **`docs/I18N.md`** + índice + CHANGELOG. |

---

## 4. Referências editoriais residuais

- **[Unreleased]:** alinhado a ficheiros existentes + notas onde fundido.  
- **Versões antigas:** notas `*(Nota editorial 2026-04: …)*` sem apagar listas originais.  
- **grep** pós-mudança: sem `I18N_FINAL_STATE` em ficheiros de produto (exceto relatórios históricos de higiene R2).

---

## 5. Riscos

- Conteúdo ultra-detalhado de uma matriz ou audit **perdido** — mitigado por resumo na secção 9 de `I18N.md` e histórico Git dos ficheiros apagados se alguma vez tinham sido commitados.

---

## 6. Decisão

**Executar** consolidação I18N, correcções CHANGELOG/PREMIUM_REPORTS/README índice, artefactos R3, validação.
