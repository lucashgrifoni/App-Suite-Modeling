# Documentação

Projeto oficial: **App Suite Modeling**.

## Release atual

- **Versão:** `7.0.0` (tag Git sugerida: `v7.0.0`; histórico `v0.1.0` em notas antigas)
- **Congelamento de escopo:** [RELEASE_SCOPE_FREEZE.md](RELEASE_SCOPE_FREEZE.md) · [ENGINEERING_CLOSEOUT_SCOPE.md](ENGINEERING_CLOSEOUT_SCOPE.md)
- **Definition of Done:** [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md)
- **Checklist técnico (gates):** [RELEASE_ENGINEERING_CHECKLIST.md](RELEASE_ENGINEERING_CHECKLIST.md)
- **Notas:** [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md) (marco inicial) + [CHANGELOG.md](../CHANGELOG.md) `[7.0.0]`
- **Limitações:** [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)
- **Gate GO/NO-GO (1 página):** [GO_NO_GO_v0.1.0.md](GO_NO_GO_v0.1.0.md) (ler versão em `pyproject.toml` / `package.json`)
- **Checklist de lançamento (dia D):** [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)
- **Validação (evidência):** [VALIDATION_REPORT_v0.1.0.md](VALIDATION_REPORT_v0.1.0.md)

## Guia mínimo (primeiro uso)

1. Instalação → secção abaixo  
2. `otm init` ou copiar `examples/minimal.otm.yaml`  
3. `otm validate` → `otm analyze` → `otm report` ou `otm export`  
4. Metodologia: [CHOOSE_METHODOLOGY.md](CHOOSE_METHODOLOGY.md) ou `otm recommend-methodology`  
5. Import: [ARTIFACT_IMPORT.md](ARTIFACT_IMPORT.md) e `otm import --help`  
6. Diff: [THREAT_MODEL_DIFF.md](THREAT_MODEL_DIFF.md) e `otm diff --help`  
7. Backlog: [REMEDIATION_BACKLOG.md](REMEDIATION_BACKLOG.md) e `otm backlog --help`

---

## Comece aqui

### 1) Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev,cli,api]"
```

**Setup automatizado (recomendado):** um único fluxo para **Windows e Linux/Ubuntu** — cria `.venv`, instala o pacote em modo editável (`dev`, `cli`, `api`) e corre `npm install` em `apps/web`.

Na **raiz do repositório**:

```bash
python scripts/setup_dev.py
```

Opções: `python scripts/setup_dev.py --skip-npm` (só Python) ou `--recreate-venv` (recriar o venv).

Atalhos:

| SO | Setup | API + UI juntos |
|----|--------|------------------|
| Qualquer | `python scripts/setup_dev.py` | `python scripts/run_dev.py` |
| Linux/macOS | `./scripts/setup_dev.sh` | `./scripts/run_dev.sh` |
| Windows (PowerShell) | `.\scripts\setup_dev.ps1` | `.\scripts\run_dev.ps1` |

`run_dev.py` inicia **uvicorn** na porta 8000 e **Vite** na 5173; use Ctrl+C para parar os dois. Exige `setup_dev` já executado e `npm` no PATH.

### 2) Primeiro arquivo `.otm.yaml`

Opção pronta:

```bash
otm init modelo.otm.yaml
```

Ou use o exemplo:

```bash
copy examples\minimal.otm.yaml modelo.otm.yaml
```

### 3) Validar

```bash
otm validate modelo.otm.yaml
```

### 4) Analisar

```bash
otm analyze modelo.otm.yaml
```

### 5) Gerar relatório

```bash
otm report modelo.otm.yaml -o RELATORIO.md
```

### 6) Usar a UI Web

Terminal 1 (API):

```bash
uvicorn otm_api.main:app --reload --port 8000
```

Terminal 2 (UI):

```bash
cd apps/web
npm install
npm run dev
```

Abra `http://localhost:5173`.

---

## Índice da documentação

| Documento | Conteúdo |
|-----------|----------|
| [MONOREPO.md](MONOREPO.md) | Árvore do repositório, convenções, packaging, checklist OSS |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Camadas, fonte da verdade, pacotes Python |
| [MVP_ROADMAP.md](MVP_ROADMAP.md) | Fases de implementação e critérios de MVP |
| [SCHEMA_V1.md](SCHEMA_V1.md) | Schema canônico v1 (conceito, versionamento, validações) |
| [CORE_ENGINE.md](CORE_ENGINE.md) | Motor de análise (`otm_threat_engine`) e consumo CLI/API |
| [CLI.md](CLI.md) | Comandos `otm`, exemplos e arquitetura da CLI |
| [API.md](API.md) | Endpoints da API FastAPI |
| [UI.md](UI.md) | Fluxos da UI web e integração com API |
| [I18N.md](I18N.md) | Internacionalização (pt-BR / en): UI, exports, premium, limitações |
| [MULTI_ENGINE_ARCHITECTURE.md](MULTI_ENGINE_ARCHITECTURE.md) | Base multi-metodologia (STRIDE, LINDDUN, NIST DC, OCTAVE, CIA-DIE) |
| [BRANDING.md](BRANDING.md) | Identidade visual, paleta, tokens e sistema de marca |
| [CHOOSE_METHODOLOGY.md](CHOOSE_METHODOLOGY.md) | Guia rápido para escolher metodologia |
| [CONTRACT_AND_SNAPSHOTS.md](CONTRACT_AND_SNAPSHOTS.md) | Contratos de saída, códigos de erro API, snapshots e gate |
| [RELEASE_CHECKLIST_RC.md](RELEASE_CHECKLIST_RC.md) | Checklist técnico de release candidate |
| [RELEASE_ENGINEERING_CHECKLIST.md](RELEASE_ENGINEERING_CHECKLIST.md) | Gates de engenharia (typecheck, build, pytest, OpenAPI, E2E) |
| [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | Definition of Done para merge e manutenção |
| [ENGINEERING_CLOSEOUT_SCOPE.md](ENGINEERING_CLOSEOUT_SCOPE.md) | Scope freeze do fecho atual (fronteiras explícitas) |
| [SMOKE_VALIDATION.md](SMOKE_VALIDATION.md) | Fluxos de smoke validation e critérios |
| [EXPLAINABILITY.md](EXPLAINABILITY.md) | Contrato de explicabilidade (`ExplanationRecord`) e interpretação |
| [PLOT4AI_AI_SYSTEM.md](PLOT4AI_AI_SYSTEM.md) | Trilha especializada de AI/LLM com PLOT4ai |
| [ARTIFACT_IMPORT.md](ARTIFACT_IMPORT.md) | Importação assistida por artefatos reais |
| [REMEDIATION_BACKLOG.md](REMEDIATION_BACKLOG.md) | Backlog inteligente de remediação |
| [THREAT_MODEL_DIFF.md](THREAT_MODEL_DIFF.md) | Diff semântico de modelos e análise (inclui histórico resumido das frentes de inovação) |
| [CI_AND_SECURITY_EVIDENCE.md](CI_AND_SECURITY_EVIDENCE.md) | Mypy, SCA, CLI modular, observabilidade e perímetro da API (evidência consolidada) |
| [GITHUB_README_AND_METADATA.md](GITHUB_README_AND_METADATA.md) | README raiz, metadados OSS e publicação GitHub |
| [FRONTEND_UI_ROLLOUT_HISTORY.md](FRONTEND_UI_ROLLOUT_HISTORY.md) | Histórico resumido da evolução da UI web (substitui trilhos plano/validação/handoff) |
| [RELEASE_NOTES_RC1.md](RELEASE_NOTES_RC1.md) | Nota de release incremental (RC1) |
| [RELEASE_NOTES_RC2.md](RELEASE_NOTES_RC2.md) | Nota histórica (RC2) |
| [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md) | Notas de release **v0.1.0** |
| [RELEASE_SCOPE_FREEZE.md](RELEASE_SCOPE_FREEZE.md) | Escopo congelado e maturidade por área |
| [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) | Limitações conhecidas (honestas) |
| [GO_NO_GO_v0.1.0.md](GO_NO_GO_v0.1.0.md) | **Gate decisivo** GO/NO-GO (1 página, dia D) |
| [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) | Checklist final operacional de lançamento |
| [VALIDATION_REPORT_v0.1.0.md](VALIDATION_REPORT_v0.1.0.md) | Evidência de validação da rodada final |
| [PUBLISH_PLAYBOOK.md](PUBLISH_PLAYBOOK.md) | Playbook de publicação (tag, artefactos, pós-release) |
| [PREPUBLISH_CHECKLIST.md](PREPUBLISH_CHECKLIST.md) | Checklist rápido do dia D |
| [VERSIONING_AND_TAGS.md](VERSIONING_AND_TAGS.md) | Convenção de versionamento e tags |
| [EXPORTERS.md](EXPORTERS.md) | JSON, Markdown, Mermaid e bundle |
| [TEMPLATES_AND_PACKS.md](TEMPLATES_AND_PACKS.md) | Templates iniciais e industry packs |
| [TEMPLATE_CATALOG.md](TEMPLATE_CATALOG.md) | Catálogo embutido: categorias, API/UI/CLI, manutenção |
| [PRODUCT_POSITIONING.md](PRODUCT_POSITIONING.md) | Posicionamento do produto (AppSec / DevSecOps, OSS) |
| [SCREENSHOT_GUIDE.md](SCREENSHOT_GUIDE.md) | Guia para capturas da UI (README e materiais) |
| [adr/](adr/) | Architecture Decision Records |
