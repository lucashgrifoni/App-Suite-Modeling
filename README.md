# App Suite Modeling

Plataforma open source de **Threat Modeling as Code** com um único núcleo partilhado por **CLI**, **API** e **UI Web**. O schema canônico versionado é a fonte da verdade.

## Stack atual (MVP)

| Camada | Tecnologia |
|--------|------------|
| Core / schema | Python, Pydantic |
| Motor de análise | Python (`otm_threat_engine`) |
| API | FastAPI |
| CLI | Typer + Rich |
| UI Web | React, TypeScript, Tailwind, React Router |
| CI / Infra | GitHub Actions, Docker Compose |

> Nota: `reactflow` está no projeto web para evolução futura de diagrama visual, mas não é central no fluxo atual do MVP.

## Estrutura do repositório

Guia completo: [**`docs/MONOREPO.md`**](docs/MONOREPO.md). Resumo:

| Área | Conteúdo |
|------|----------|
| [`packages/`](packages/) | Bibliotecas Python (`otm_*`): schema, motor, exportadores, mappings e packs |
| [`apps/`](apps/) | API FastAPI, CLI `otm`, UI React |
| [`examples/`](examples/) | Modelos `.otm.yaml` válidos |
| [`docs/`](docs/) | Arquitetura, guias operacionais e ADRs |
| [`tests/`](tests/) | Testes automatizados (pytest) |

## Começo rápido

Consulte [**`docs/README.md`**](docs/README.md) para o fluxo completo de início.

Contratos de saída, códigos de erro da API, snapshots e gate de regressão: [**`docs/CONTRACT_AND_SNAPSHOTS.md`**](docs/CONTRACT_AND_SNAPSHOTS.md).

### CLI

```bash
pip install -e ".[cli]"
otm validate examples/minimal.otm.yaml
otm analyze examples/minimal.otm.yaml
otm report examples/minimal.otm.yaml -o RELATORIO.md
```

### API

```bash
pip install -e ".[api]"
uvicorn otm_api.main:app --reload --port 8000
```

### UI Web

```bash
cd apps/web
npm install
npm run dev
```

## Limitações do MVP

- Sem persistência server-side (UI usa rascunho local em `sessionStorage`).
- Sem autenticação/autorização.
- Exportação focada em texto técnico (JSON, Markdown, Mermaid).
- Diagrama visual avançado (canvas) ainda não é parte do fluxo principal.

## Metodologias de threat modeling (estado atual)

- **STRIDE** é o default oficial e a metodologia mais madura no projeto.
- **LINDDUN** já possui primeira camada nativa com heurísticas de privacidade.
- **NIST Data-Centric**, **OCTAVE Allegro** e **CIA/CIA-DIE** já são suportadas na arquitetura.
- **PASTA** e **PLOT4ai** também já são suportadas na arquitetura:
  - `pasta`: foco avançado em risco/ataque/vulnerabilidade/impacto
  - `plot4ai`: foco especializado em sistemas de IA/LLM
- No estado atual, as metodologias atuam por **recomendação automática + lentes metodológicas** sobre a análise base.
- **PASTA** e **PLOT4ai** estão em **fase 2 incremental** (heurísticas e insights especializados).
- A profundidade nativa de cada metodologia será expandida incrementalmente, sem quebrar CLI/API/UI.

## Matriz oficial de metodologias

| Metodologia | Objetivo | Quando usar | Complexidade | Maturidade | Recomendação automática | Perfil ideal |
|-------------|----------|-------------|--------------|------------|--------------------------|--------------|
| STRIDE | Segurança técnica geral | Web/API/cloud-native | Baixa-Média | **Mature** | Sim | Times AppSec/Dev |
| LINDDUN | Privacidade e compliance | PII, LGPD/GDPR | Média | **Evolving** | Sim | Privacidade/GRC |
| NIST Data-Centric | Proteção por contexto de dado | Dados críticos/classificados | Média | **Evolving** | Sim | Segurança de dados |
| OCTAVE Allegro | Risco orientado a ativos | Contexto organizacional | Média | **Evolving** | Sim | Gestão de risco |
| CIA/CIA-DIE | Visão executiva rápida | Workshops e iniciantes | Baixa | **Evolving** | Sim | Liderança/Produto |
| PASTA | Análise avançada risk-centric | Enterprise, ataque e impacto | Média-Alta | **Specialized** | Sim | Arquitetura + Red/Blue |
| PLOT4ai | Segurança de sistemas AI/LLM | LLM, RAG, agentes, pipelines | Média | **Specialized** | Sim | AI Security / ML Eng |

## Exemplos rápidos por metodologia

### CLI

```bash
otm analyze modelo.otm.yaml --methodology stride
otm analyze modelo.otm.yaml --methodology linddun
otm analyze modelo.otm.yaml --methodology nist_data_centric
otm analyze modelo.otm.yaml --methodology octave_allegro
otm analyze modelo.otm.yaml --methodology cia_die
otm analyze modelo.otm.yaml --methodology pasta
otm analyze modelo.otm.yaml --methodology plot4ai
otm analyze modelo.otm.yaml --auto-methodology
```

### API

```json
POST /v1/models/analyze
{
  "document": { "...": "..." },
  "methodology": "plot4ai"
}
```

```json
POST /v1/models/recommend-methodology
{
  "document": { "...": "..." }
}
```

### UI

- Na tela **Análise**, escolha a metodologia no seletor.
- Use **Recomendar metodologia** para sugestão automática do backend.
- Veja metadados discretos de categoria, best-for e maturidade.
- Se necessário, faça override manual e execute **Gerar análise**.

## Branding oficial

- Nome oficial: **App Suite Modeling**
- Guia de identidade visual, paleta, tokens e logo: [docs/BRANDING.md](docs/BRANDING.md)
- Direção visual: técnica, confiável, premium e minimalista para AppSec/DevSecOps.

## Documentação relacionada

- [docs/CLI.md](docs/CLI.md)
- [docs/API.md](docs/API.md)
- [docs/UI.md](docs/UI.md)
- [docs/CHOOSE_METHODOLOGY.md](docs/CHOOSE_METHODOLOGY.md)
- [docs/RELEASE_CHECKLIST_RC.md](docs/RELEASE_CHECKLIST_RC.md)
- [docs/SMOKE_VALIDATION.md](docs/SMOKE_VALIDATION.md)
- [docs/PUBLISH_PLAYBOOK.md](docs/PUBLISH_PLAYBOOK.md)
- [docs/TEMPLATES_AND_PACKS.md](docs/TEMPLATES_AND_PACKS.md)
- [docs/EXPLAINABILITY.md](docs/EXPLAINABILITY.md)
- [docs/PLOT4AI_AI_SYSTEM.md](docs/PLOT4AI_AI_SYSTEM.md)
- [docs/THREAT_MODEL_DIFF.md](docs/THREAT_MODEL_DIFF.md)
- [docs/ARTIFACT_IMPORT.md](docs/ARTIFACT_IMPORT.md)
- [docs/REMEDIATION_BACKLOG.md](docs/REMEDIATION_BACKLOG.md)
- [docs/INNOVATION_PHASE_FINAL_INTEGRATION_RC.md](docs/INNOVATION_PHASE_FINAL_INTEGRATION_RC.md)

## Governança OSS

- Contribuição: [CONTRIBUTING.md](CONTRIBUTING.md)
- Segurança: [SECURITY.md](SECURITY.md)
- Histórico de mudanças: [CHANGELOG.md](CHANGELOG.md)
- Licença: [LICENSE](LICENSE)
