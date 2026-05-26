# Política Semgrep — App Suite Modeling

## O que corre no CI

No `.github/workflows/security-ci-cd.yml`, job **SAST - Semgrep**:

- `p/security-audit` — regras de segurança multi-linguagem (Python, JS/TS, etc.).  
- `p/github-actions` — padrões de risco em workflows do GitHub Actions.  
- `rules/semgrep/appsec-runtime-footguns.yml` — rule pack custom deste repositório.

O scan corre com `--severity WARNING --error` (bloqueia WARNING e ERROR) e publica SARIF.

Comando equivalente local (com Docker):

```bash
docker run --rm -v "$PWD:/src" -w /src semgrep/semgrep semgrep scan \
  --config p/security-audit --config p/github-actions \
  --config rules/semgrep/appsec-runtime-footguns.yml \
  --severity WARNING --error .
```

## Quando o job falha

1. **Confirmar** que o finding é verdadeiro positivo (reproduzir ou ler a regra).  
2. **Corrigir** no código (preferido).  
3. Se for **falso positivo** aceite pela equipa:  
   - comentário `# nosemgrep` / `// nosemgrep` na linha **com** `ruleid` explícito na mesma linha ou linha acima;  
   - ou exclusão mínima em **`.semgrepignore`** (pastas geradas, nunca `packages/` core sem justificativa).  
4. Registar em PR: motivo da exclusão ou `nosemgrep` (1–2 frases).

## Ficheiros ignorados

Ver **`.semgrepignore`** na raiz (`.git`, `node_modules`, `.venv`, artefactos de build, lockfiles como fonte primária, etc.).

## Evolução

- Regras **corporativas** ou **custom** (`semgrep.yml` na raiz) podem ser acrescentadas; manter o CI estável (evitar `r/all` sem filtro).  
- Subir gravidade: avaliar `p/owasp-top-ten` em job separado ou agendado para não bloquear PRs até a dívida estar tratada.
