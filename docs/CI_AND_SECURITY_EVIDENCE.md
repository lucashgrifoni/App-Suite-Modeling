# Evidência consolidada — CI, tipagem, SCA, CLI, observabilidade e perímetro da API

Documento único que substitui relatórios de execução dispersos (rodada de higiene docs, 2026-04).  
**Índice:** [Ruff + Bandit](#0-ruff-lint--formato) · [Mypy](#1-mypy-no-ci-monorepo) · [SCA](#2-sca-supply-chain) · [CLI modular](#3-refatoração-da-cli) · [Observabilidade](#4-observabilidade-da-api) · [Perímetro / CORS](#5-endurecimento-de-perímetro-da-api) · [Semgrep](#6-semgrep) · [Trivy](#7-trivy-imagem-api)

---

## 0. Ruff (lint + formato)

### Comandos no CI (job `python`)

```bash
ruff check packages apps tests
ruff format --check packages apps tests
```

### Critérios de aceite

- **Lint:** regras em `[tool.ruff.lint]` no `pyproject.toml` (`E`, `F`, `I`, `UP`), com `per-file-ignores` onde documentado.
- **Formato:** o repositório mantém estilo canónico Ruff; PRs que desviarem falham no job `Ruff (format)`.

### Local

```bash
ruff check packages apps tests
ruff format packages apps tests
```

### Bandit (SAST, Python)

- Job `python`: `python -m bandit -r packages apps -ll -q` (severidade **medium** e acima; `-q` reduz ruído).
- Dependência: `bandit>=1.7` no extra `[dev]` do `pyproject.toml` (instalado com `pip install -e ".[dev,cli,api]"` no CI).

---

## 1. Mypy no CI (monorepo)

### Pacotes cobertos (job `python`)

O comando no `.github/workflows/github-ci-cd.yml` (job `python`) inclui **todos** os pacotes Python de primeira linha e a CLI:

- `packages/core-schema/otm_core_schema`
- `apps/api/otm_api`
- `packages/explainability/otm_explainability`
- `packages/framework-mappings/otm_framework_mappings`
- `packages/diagram-engine/otm_diagram_engine`
- `apps/cli/otm_cli`
- `packages/exporters/otm_exporters`
- `packages/artifact-import/otm_artifact_import`
- `packages/report-premium/otm_report_premium`
- `packages/threat-engine/otm_threat_engine`
- `packages/industry-packs/otm_industry_packs`

### Strictness

- Configuração global em `[tool.mypy]` no `pyproject.toml` (`python_version`, `warn_unused_ignores`, `show_error_codes`).
- `ignore_missing_imports = true` no global; próximo passo de maturidade: `[[tool.mypy.overrides]]` por pacote e stubs onde fizer sentido.

### Critérios de aceite

- Job `Mypy (monorepo)` falha em erros de tipo nos diretórios listados.

---

## 2. SCA (supply chain)

### Ferramentas

| Stack | Ferramenta | Onde |
|-------|------------|------|
| Python | **pip-audit** (OSV/PyPI) | Job `python` no CI, após `pip install -e ".[dev,cli,api]"` |
| Node | **npm audit** | Job `web`, `apps/web`, após `npm ci` |

### Thresholds

- **Python:** `python -m pip_audit --desc on -S .` — gate estrito (qualquer vulnerabilidade conhecida falha o CI na árvore resolvida).
- **Node:** `npm audit --audit-level=critical` e **`npm audit --audit-level=moderate`** (job `web`; após upgrade Vite 6 / Vitest 3 a árvore `apps/web` ficou sem CVEs reportados na resolução actual).

### Política de exceção

Não silenciar findings sem registo (issue/ADR com CVE, plano e prazo). Preferir upgrade de dependência.

### Dependabot

- `.github/dependabot.yml`: atualizações semanais para **pip** (raiz) e **npm** (`apps/web`).

---

## 3. Refatoração da CLI

### Problema resolvido

`apps/cli/otm_cli/cli.py` era um god module monolítico; hoje é **bootstrap** (~70 linhas) com comandos em `commands/` e orquestração em `application/`.

### Estrutura

```
apps/cli/otm_cli/
  cli.py          # Typer + registo de comandos
  main.py
  commands/
  application/
  shared/
```

### Testabilidade

- `tests/test_cli_application.py` cobre serviços sem Typer.
- `tests/test_cli.py` e smoke mantêm contrato externo.

---

## 4. Observabilidade da API

### Implementação

1. **`otm_api.observability`**
   - `setup_api_logging()`: JSON por linha em stdout.
   - `ObservabilityMiddleware`: `request_id` (`X-Request-ID`), duração, sucesso/falha.
   - `register_unhandled_exception_handler`: resposta JSON genérica com `request_id`, sem stack ao cliente.

2. **`main.py`**: logging antes da app; middleware de observabilidade na stack (coordenado com CORS).

### Campos típicos de log HTTP

`request_id`, `method`, `path`, `status_code`, `duration_ms`, `event_name` (`http_request_completed` \| `http_request_failed` \| `unhandled_route_exception`).

Variável: `OTM_LOG_LEVEL` (default `INFO`).

### O que não é logado

- Corpo de pedidos, payloads OTM/análise completos, secrets.

---

## 5. Endurecimento de perímetro da API

### Decisão

**Cenário A (local / internal-only):** API **sem** authn/authz de aplicação no código; deployment em rede confiável ou gateway. **CORS e perfis** parametrizados para produção não herdar defaults de desenvolvimento.

### Implementação

- `otm_api.cors_settings.resolve_cors_profile()`: `OTM_ENV`, `OTM_CORS_ORIGINS`; produção sem origens explícitas → lista vazia; métodos/headers enumerados fora de `development`.

### Riscos aceites

API sem autenticação se exposta publicamente sem gateway — ver [`DEPLOYMENT_INVARIANTS.md`](architecture/DEPLOYMENT_INVARIANTS.md).

### Próximos passos (cenário público)

API keys/OAuth2/mTLS + testes de autorização + OpenAPI/UI alinhados ao fluxo completo.

---

## 6. Semgrep

- Job `semgrep` no CI: imagem `semgrep/semgrep`, configs **`p/python`**, **`p/typescript`**, **`p/javascript`**, **`p/react`** sobre `packages` e `apps/web/src`.
- Exclusões: **`.semgrepignore`** na raiz (artefactos, `node_modules`, `.venv`, etc.).
- Política de triagem, `nosemgrep` e evolução: **[`SEMGREP_POLICY.md`](architecture/SEMGREP_POLICY.md)**.

---

## 7. Trivy (imagem API)

- Job `trivy-image`: `docker build -f apps/api/Dockerfile -t otm-api:ci .` seguido de `aquasecurity/trivy-action@0.35.0` com `severity: CRITICAL,HIGH` e `exit-code: 1`.
- Complementa pip-audit (Python na host) com visão de **imagem** (OS + dependências instaladas na layer).

---

## 8. Gate de deriva do modelo de ameaças (`otm diff --fail-on`)

O análogo, em threat modeling, de um security gate: um PR que **acrescenta risco novo** reprova o build.
O baseline é o modelo commitado — não é preciso ficheiro de supressão, porque o risco pré-existente
aparece dos dois lados do diff e nunca conta como novo.

### Flags

| Flag | Efeito |
| --- | --- |
| `--fail-on <none\|low\|medium\|high\|critical>` | Reprova se uma ameaça **nova** ou **agravada** atinge a banda (inclusive). Implica `--with-analysis`. |
| `--fail-on-risk-increase` | Reprova se **qualquer** ameaça sobe de score, mesmo sem mudar de banda — e também se o score máximo do resumo sobe. |

Disponíveis em `otm diff` (corre o motor nos dois `.otm.yaml`) e em `otm diff-analysis`
(compara dois `analyze.json` já produzidos).

### Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Sem reprovação (e sempre, quando nenhuma flag de gate é usada, ou quando o gate não é avaliável). |
| `1` | Erro de utilização: ficheiro inexistente, YAML inválido, `--fail-on` inválido. |
| `3` | **Gate reprovou.** |

`3` distingue "a política falhou" de "o comando falhou" — um operador de CI não pode confundir um
caminho mal escrito com uma violação de política.

### O que dispara — e o que nunca dispara

Dispara: ameaça **nova** na banda ou acima; ameaça **agravada** que *cruza* para a banda (ex.: `medium → high`).
Uma ameaça cujo id mudou (o motor emite `signature_remap_hints`) é comparada com o gémeo removido, por
score: um rename inerte não reprova, mas um rename que também sobe de banda **reprova**.

Nunca dispara: remoções, melhorias, descidas de score, renames inertes, nem subidas *dentro* da mesma
banda (ex.: `21 → 22`) — para essas existe `--fail-on-risk-increase`, que avalia **cada ameaça**, não
apenas o máximo do resumo. Sem isso, uma ameaça que subisse `12 → 15` sem ser a de score máximo não
era apanhada por política nenhuma.

**Troca de metodologia: `NOT EVALUATED`, não `PASSED`.** Trocar de lente troca a própria régua — as
heurísticas de uma metodologia não existem na outra, por isso *todas* as ameaças aparecem como novas
sem que ninguém as tenha causado. Nesse caso o gate não emite veredito: imprime `THREAT MODEL GATE:
NOT EVALUATED`, explica porquê e sai com `0`. Não diz `PASSED`, porque não avaliou nada — o mesmo
princípio que faz `otm diff-analysis` recusar comparar entre versões do motor.

Ameaças novas sem score são reportadas como `unranked` no relatório do gate, nunca ignoradas em silêncio.

### Receita (GitHub Actions)

```yaml
- name: Threat-model drift gate
  run: |
    otm diff \
      "$(git show origin/main:threat-model.otm.yaml > /tmp/baseline.otm.yaml && echo /tmp/baseline.otm.yaml)" \
      threat-model.otm.yaml \
      --fail-on high \
      --json-out threat-model-diff.json

- name: Upload diff artifact
  if: always()          # o artefacto é escrito ANTES do gate reprovar
  uses: actions/upload-artifact@v4
  with:
    name: threat-model-diff
    path: threat-model-diff.json
```

O relatório do gate vai para **stderr** e o payload para **stdout**, por isso
`otm diff … --format json --fail-on high > diff.json` mantém `diff.json` como JSON válido.
Num pipe, use `set -o pipefail` para não perder o código de saída.

### Restrições

- Em `otm diff-analysis`, gatear dois `analyze.json` produzidos por **versões diferentes do motor** é
  recusado (exit `1`): a churn de heurísticas seria indistinguível de deriva real do modelo.
- Renomear um componente ou fluxo muda o alvo da heurística e, por isso, a sua assinatura: as ameaças
  associadas surgem como novas. O relatório mostra as remoções emparelhadas, tornando o rename evidente.
