# App Suite Modeling

**Threat modeling as code—with a canonical model, multi-methodology analysis, and exports your pipeline can use.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node 18+](https://img.shields.io/badge/node-18+-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)

> **Note:** After you publish the GitHub repository, add a CI status badge pointing at `.github/workflows/ci.yml` (replace `OWNER/REPO` in the URL).

---

## What it is

**App Suite Modeling** is an open-source **threat modeling** platform: a single **versioned canonical schema** drives a **web UI**, **CLI**, and **REST API**. You describe components, flows, and trust boundaries; the server validates the model and runs analysis (STRIDE, LINDDUN, PASTA, NIST Data-Centric, OCTAVE Allegro, CIA-DIE, **PLOT4ai** for AI/LLM systems). Outputs include **structured explainability**, **remediation backlog hints**, and **exports** (JSON, Markdown, Mermaid, PDF) plus **semantic diff** between revisions.

**Who it’s for:** AppSec engineers, DevSecOps, and architects who want threat models that stay **reviewable, portable, and close to engineering**—not one-off diagrams.

**Problem it solves:** Security and delivery teams need a **repeatable** way to capture structure and risk, attach **evidence-friendly artifacts**, and **iterate** as architecture changes—without duplicating logic across tools.

---

## Screenshots

*(Add images under `docs/screenshots/` when you capture the UI—see [`docs/SCREENSHOT_GUIDE.md`](docs/SCREENSHOT_GUIDE.md).)*

| Area | Suggested file | What to show |
|------|----------------|--------------|
| Home | `docs/screenshots/home.png` | Hero, primary CTAs (new model, import, templates) |
| Wizard | `docs/screenshots/wizard.png` | Guided modeling step |
| Analysis | `docs/screenshots/analysis.png` | Methodology selector + metrics / threats |
| Export | `docs/screenshots/export.png` | Format checkboxes + PDF action |
| Diff | `docs/screenshots/diff.png` | Side-by-side or summary of model diff |

```text
<!-- After capture, embed the Home screenshot using path docs/screenshots/home.png (no markdown link in this comment — avoids doc-link checks). -->
```

---

## Key features

- **Guided workflow** — Assistant → diagram (React Flow, drag-and-drop) → analysis → export → diff  
- **Interactive diagram editor** — Edit mode with draggable nodes, connections, and session-stored layout  
- **Multi-methodology analysis** — STRIDE, LINDDUN, PASTA, NIST Data-Centric, OCTAVE Allegro, CIA-DIE, **PLOT4ai**  
- **Exports** — JSON, Markdown, Mermaid, bundle JSON; **PDF** report generated in the browser  
- **Analysis history** — Local snapshots (browser storage), restore, export / PDF per entry  
- **Explainability** — Structured explanation records alongside heuristics  
- **Templates & packs** — Built-in catalog + industry packs for contextual threats  
- **CLI + API** — Same contracts: validate, analyze, export, import, diff, templates  
- **Artifact import** — OpenAPI/Swagger, Kubernetes YAML, Terraform (draft canonical models)

---

## How it works

```text
Import (optional) → Assistant → Diagram → Analysis → Export → Diff
```

1. **Import** (optional) — Upload OpenAPI, K8s manifests, or Terraform to seed a canonical draft.  
2. **Assistant** — Fill metadata, components, flows, boundaries.  
3. **Diagram** — Visual edit on `/review`; changes stay in session until you export or send to API.  
4. **Analysis** — Pick or auto-recommend methodology; review threats, explanations, backlog hints.  
5. **Export** — Download JSON / Markdown / Mermaid / PDF; optional bundle with analysis.  
6. **Diff** — Compare two model versions or analyses for reviews and CI-style gates.

Validation and the analysis engine run **on the server**; the UI orchestrates the flow.

---

## Quick start

### 1. Python (CLI + API)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -e ".[dev,cli,api]"
```

**Automated setup** (venv + editable install + `npm install` in `apps/web`):

```bash
python scripts/setup_dev.py
```

**One command for API + UI** (from repo root):

```bash
python scripts/run_dev.py
```

- API: `http://127.0.0.1:8000` (OpenAPI: `/docs`)  
- Web: `http://127.0.0.1:5173`

### 2. CLI (minimal)

```bash
otm validate examples/minimal.otm.yaml
otm analyze examples/minimal.otm.yaml --methodology stride
otm report examples/minimal.otm.yaml -o REPORT.md
```

### 3. API only

```bash
uvicorn otm_api.main:app --reload --port 8000
```

### 4. Web only

```bash
cd apps/web
npm install
npm run dev
```

*(Full operational guide: [`docs/README.md`](docs/README.md).)*

---

## Templates

Built-in **templates** (`otm templates`, `GET /v1/templates`) give valid starter models (APIs, cloud, identity, integrations, AI/LLM, industry scenarios). They are **starting points**—always review and extend for your system. See [`docs/TEMPLATE_CATALOG.md`](docs/TEMPLATE_CATALOG.md) and [`docs/TEMPLATES_AND_PACKS.md`](docs/TEMPLATES_AND_PACKS.md).

```bash
otm init -t saas-web model.otm.yaml
otm templates list
```

---

## CLI usage (essentials)

| Command | Purpose |
|---------|---------|
| `otm validate <file.otm.yaml>` | Validate canonical document |
| `otm analyze <file> [--methodology …] [--pack …]` | Run analysis |
| `otm report <file> -o REPORT.md` | Generate markdown report |
| `otm diff …` | Structural / analysis diff |
| `otm templates` / `otm templates list` | List embedded templates |
| `otm templates show <id>` | Template metadata |
| `otm init -t <id> <path>` | Write template to file |

Details: [`docs/CLI.md`](docs/CLI.md)

---

## API overview

| Method | Path | Role |
|--------|------|------|
| `GET` | `/health` | Liveness |
| `POST` | `/v1/models` | Create blank canonical document |
| `POST` | `/v1/models/validate` | Validate document JSON |
| `POST` | `/v1/models/analyze` | Run engine (`document`, optional `pack_id`, `methodology`) |
| `POST` | `/v1/models/diff` | Structural diff between two documents |
| `POST` | `/v1/models/compare` | Rich comparison + optional analysis |
| `POST` | `/v1/models/recommend-methodology` | Suggest methodology from context |
| `GET` | `/v1/templates` | List templates (optional filters) |
| `POST` | `/v1/templates/{id}/instantiate` | Instantiate template |
| `POST` | `/v1/exports` | Export artifacts (JSON, Markdown, Mermaid, …) |
| `POST` | `/v1/imports/*` | OpenAPI, Terraform, Kubernetes import |

Interactive docs: **`/docs`** when the API is running. Full reference: [`docs/API.md`](docs/API.md)

---

## Methodologies supported

| ID | Focus |
|----|--------|
| `stride` | Spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege |
| `linddun` | Privacy / data protection lens |
| `nist_data_centric` | Data-centric security perspective |
| `octave_allegro` | Risk and asset-oriented view |
| `cia_die` | Confidentiality, integrity, availability (and extensions) |
| `pasta` | Risk-centric, attack-path oriented analysis |
| `plot4ai` | AI/LLM systems (models, prompts, RAG, agents) |

Methodology choice: manual selector, or **recommend** from document context. See [`docs/CHOOSE_METHODOLOGY.md`](docs/CHOOSE_METHODOLOGY.md) and [`docs/PLOT4AI_AI_SYSTEM.md`](docs/PLOT4AI_AI_SYSTEM.md).

The **matriz oficial de metodologias** (goals, when to use, complexity, auto-recommendation) is in [`docs/MULTI_ENGINE_ARCHITECTURE.md`](docs/MULTI_ENGINE_ARCHITECTURE.md). **STRIDE** is the **default** general-purpose engine; you can refine threats **incrementally** as the canonical model evolves. **Branding oficial** (palette, tokens, logo): [`docs/BRANDING.md`](docs/BRANDING.md).

### CLI

Automation and CI: `otm` commands — see [CLI usage (essentials)](#cli-usage-essentials) and [`docs/CLI.md`](docs/CLI.md).

### API

Integrations and pipelines: REST — see [API overview](#api-overview) and [`docs/API.md`](docs/API.md).

### UI

Guided browser workflow — see [`docs/UI.md`](docs/UI.md).

---

## Use cases

- **AppSec teams** — Repeatable models, exports for reviews, traceable explanations  
- **DevSecOps** — CLI/API for automation; artifacts for pipelines and tickets  
- **Architecture / security reviews** — Diff and compare revisions of the same system  
- **AI / LLM systems** — PLOT4ai lens for generative AI, RAG, and agentic flows  

---

## Limitations (honest)

- Templates and imports produce **drafts**—human review is required.  
- **No** built-in server-side persistence for the web UI (session + browser storage by default).  
- **No** authentication layer in the default stack—deploy behind your identity boundary if needed.  
- Heuristic coverage is **assistive**, not a guarantee of completeness.

Full list: [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md)

---

## Contributing

- Read [`CONTRIBUTING.md`](CONTRIBUTING.md)  
- Report security issues via [`SECURITY.md`](SECURITY.md)  
- Changes: [`CHANGELOG.md`](CHANGELOG.md)

---

## Product positioning

Narrative and differentiators: [`docs/PRODUCT_POSITIONING.md`](docs/PRODUCT_POSITIONING.md)

---

## Repository layout

| Path | Contents |
|------|----------|
| [`packages/`](packages/) | Python libraries: schema, engine, exporters, industry packs, … |
| [`apps/api/`](apps/api/) | FastAPI service |
| [`apps/cli/`](apps/cli/) | `otm` CLI |
| [`apps/web/`](apps/web/) | React + Vite UI |
| [`docs/`](docs/) | Architecture, API, guides |
| [`examples/`](examples/) | Sample `.otm.yaml` files |
| [`tests/`](tests/) | Pytest suite |

Monorepo details: [`docs/MONOREPO.md`](docs/MONOREPO.md)

---

## License

[MIT](LICENSE)

---

## Trademarks

*App Suite Modeling* is the project name. Third-party frameworks (STRIDE, LINDDUN, PASTA, NIST, PLOT4ai, etc.) belong to their respective authors and are used here to describe methodology support only.
