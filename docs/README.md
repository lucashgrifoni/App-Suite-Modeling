# Documentação

Projeto oficial: **App Suite Modeling**.

## Comece aqui

### 1) Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev,cli,api]"
```

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
| [MULTI_ENGINE_ARCHITECTURE.md](MULTI_ENGINE_ARCHITECTURE.md) | Base multi-metodologia (STRIDE, LINDDUN, NIST DC, OCTAVE, CIA-DIE) |
| [BRANDING.md](BRANDING.md) | Identidade visual, paleta, tokens e sistema de marca |
| [CHOOSE_METHODOLOGY.md](CHOOSE_METHODOLOGY.md) | Guia rápido para escolher metodologia |
| [RELEASE_CHECKLIST_RC.md](RELEASE_CHECKLIST_RC.md) | Checklist técnico de release candidate |
| [SMOKE_VALIDATION.md](SMOKE_VALIDATION.md) | Fluxos de smoke validation e critérios |
| [RELEASE_NOTES_RC1.md](RELEASE_NOTES_RC1.md) | Nota de release incremental (RC1) |
| [EXPORTERS.md](EXPORTERS.md) | JSON, Markdown, Mermaid e bundle |
| [TEMPLATES_AND_PACKS.md](TEMPLATES_AND_PACKS.md) | Templates iniciais e industry packs |
| [adr/](adr/) | Architecture Decision Records |
