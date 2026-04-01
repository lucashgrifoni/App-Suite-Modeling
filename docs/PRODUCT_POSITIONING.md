# Product positioning — App Suite Modeling

Audience: **application security engineers**, **DevSecOps**, **security architects**, and teams that need **reviewable, exportable threat models** tied to real engineering workflows—not slide-deck diagrams that age in a week.

---

## Tagline

**Threat modeling as code—with a canonical model, multi-methodology analysis, and exports your pipeline can use.**

---

## Short description (2–3 lines)

**App Suite Modeling** is an open-source platform for **structured threat modeling**: one versioned canonical schema powers a **web UI**, **CLI**, and **REST API**. You model systems, run analysis under methodologies from STRIDE to PLOT4ai, and ship **JSON, Markdown, Mermaid, or PDF**—plus **semantic diff** and **structured explainability**—so security stays aligned with how software is actually built and shipped.

---

## Expanded description (one paragraph)

Modern AppSec and DevSecOps need threat models that survive handoffs: the same artifact should validate in CI, attach to reviews, and evolve with the architecture. App Suite Modeling treats a **single canonical threat model document** as the source of truth, validates it server-side, and runs a **multi-engine analysis layer** (including **PLOT4ai** for AI/LLM-heavy systems) with **explainability records** and **remediation-oriented backlog signals**—without replacing human judgment. **Industry packs**, **artifact import**, **templates**, and **diff across revisions** bridge the gap between security intent and day-to-day engineering, so teams can document trust boundaries and data flows once and iterate as the system changes.

---

## Differentiators (factual)

| Area | What it means here |
|------|-------------------|
| **Multi-methodology** | STRIDE, LINDDUN, NIST Data-Centric, OCTAVE Allegro, CIA/CIA-DIE, PASTA, PLOT4ai—selected per analysis, with methodology recommendation from the model context. |
| **Exportable** | JSON (canonical document), Markdown, Mermaid flowcharts, **PDF** report, bundles; suitable for repos, tickets, and evidence packs. |
| **Engineering integration** | CLI + API for automation; **import** paths from OpenAPI, Kubernetes, Terraform toward a canonical draft. |
| **Explainability** | Structured `ExplanationRecord` output—traceable rationale, not a black-box score. |
| **AI/LLM (PLOT4ai)** | Dedicated lens and signals for systems where models, prompts, RAG, or agents matter—alongside traditional STRIDE-style coverage. |

---

## What this product is *not*

- Not a replacement for skilled threat modeling workshops or organizational risk acceptance.
- Not a guarantee of completeness: heuristics and imports produce **drafts** to review.
- Not “AI that replaces your security team”—analysis and templates are **assistive**.

---

## Language strategy (repository)

- **GitHub-facing** `README.md`, positioning, and social/meta copy: **English** (broad reach, standard for OSS).
- **In-app UI** may remain **Portuguese (pt-BR)** in the current branch; i18n is a future increment unless unified later.
