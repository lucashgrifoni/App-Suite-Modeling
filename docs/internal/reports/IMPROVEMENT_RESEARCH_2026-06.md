# Improvement research & evolution plan — App Suite Modeling

> **Date:** 2026-06-18 · **Baseline:** v7.6.4 · **Author:** maintainer research pass
> **Scope guardrail:** every item below stays inside the project's idea — *threat modeling as code*: one canonical `.otm.yaml` document driving a CLI, a REST API, and a web UI, with a heuristic multi‑methodology engine, artifact import, exports, and diff. Anything that would turn the project into a different product (multi‑tenant SaaS, GUI diagram editor, generic scanner, commercial platform) is listed under **Out of scope** and is **not** planned.

This document is the source‑grounded output of a deliberate internet‑research pass on *what to improve without straying from the idea*. It is meant to be executed top‑down.

---

## 1. Executive summary

App Suite Modeling already occupies a credible, differentiated niche: a **canonical‑document, code‑first** threat‑modeling toolkit that is simultaneously usable from a **CLI**, a **REST API**, and a **web UI**, with a heuristic engine spanning **seven methodology lenses** (STRIDE, LINDDUN, PASTA, NIST Data‑Centric, OCTAVE Allegro, CIA‑DIE, PLOT4ai) plus **import from real engineering artifacts** (OpenAPI, Kubernetes, Terraform, Helm) and a **semantic diff**. That multi‑surface + import‑from‑IaC combination is genuinely uncommon among open tools.

The research surfaced **five high‑value, on‑mission evolution themes**, none of which require leaving the project's idea:

1. **Open Threat Model (OTM) interoperability.** The project is *named* `open-threat-model` and uses `.otm.yaml`, but its schema is **OTM‑inspired, not OTM‑conformant** to IriusRisk's published **OTM standard** (`otmVersion`/`project`/`trustZones`/`dataflows`, camelCase). Adding an OTM **import/export bridge** unlocks interop with the entire OTM ecosystem (IriusRisk, StartLeft) and is the single most strategic, identity‑aligned improvement.
2. **Threat traceability via standard libraries.** Industry tools link **STRIDE → CAPEC → CWE** (and MITRE ATT&CK), giving each suggested threat an authoritative reference and traceability. Our engine maps to ASVS/NIST CSF but does not yet attach CAPEC/CWE to threats.
3. **SARIF output for CI.** Emitting threats as **SARIF 2.1.0** would let `otm analyze` results surface natively in GitHub code scanning and any SARIF‑aware pipeline — a strong, low‑risk DevSecOps integration that fits the "repeatable in CI" promise.
4. **Deeper, better‑mapped AI/LLM lens.** Our PLOT4ai lens (~13 heuristics) can be mapped to **OWASP Top 10 for LLM Applications (2025)** and **MITRE ATLAS**, and informed by the upstream **PLOT4ai library (138 threats / 8 categories)**.
5. **Packaging & distribution for adoption.** We install from a clone today. **PyPI publishing via OIDC trusted publishing**, a **composite GitHub Action**, and a **pre‑commit hook** would make the tool installable and CI‑droppable, which is the main blocker to real adoption.

These are sequenced as workstreams in §4. §5 lists what we deliberately will **not** do.

---

## 2. Positioning vs comparable tools (honest)

| Tool | Model input | Threat generation | Surfaces | Where it's stronger | Where we differ / can win |
|------|-------------|-------------------|----------|---------------------|---------------------------|
| **OWASP pytm** ([repo](https://github.com/OWASP/pytm), [OWASP](https://owasp.org/www-project-pytm/)) | Model defined in **Python source** | Threats as Python expressions over element properties; built‑in threat list | CLI/library; DFD + report outputs | Pure code, very developer‑centric | We use a **declarative document** (reviewable by non‑Python users), plus **API + UI** and **IaC import** |
| **Threagile** ([repo](https://github.com/Threagile/threagile), [site](https://threagile.io/)) | **YAML** architecture model | **~40 built‑in risk rules** + custom rules; risk tracking in the YAML | CLI/Docker; DFD, Excel, JSON | Mature rule engine, IDE schema autocomplete | We span **CLI+API+UI**, **multi‑methodology** (not just risk rules), and **import from OpenAPI/IaC** |
| **OWASP Threat Dragon** ([repo](https://github.com/owasp/threat-dragon), [site](https://threatdragon.github.io/)) | **Diagram (GUI)** | Rule engine; supports **STRIDE/LINDDUN/CIA/DIE/PLOT4ai** | Web + desktop app | Polished diagram‑first UX, OWASP flagship | We are **code/document‑first** (Git‑reviewable, diffable, CI‑native), with API automation |
| **IriusRisk** ([site](https://www.iriusrisk.com/)) + **OTM/StartLeft** ([OTM](https://github.com/iriusrisk/OpenThreatModel), [StartLeft](https://github.com/iriusrisk/startleft)) | Diagram / **OTM** / IaC via StartLeft | Commercial rules + CAPEC mappings | Commercial platform | Enterprise depth, the **OTM standard** itself | We're **open‑source and self‑contained**; interop *with* OTM is an opportunity, not competition |
| **Microsoft TMT** | Diagram (GUI, Windows) | Template‑driven STRIDE | Desktop app | Familiar in MS shops | Cross‑platform, code‑first, automatable |

**Our defensible position:** *the* open, code‑first, **multi‑surface** (CLI+API+UI) threat‑modeling‑as‑code tool with **multi‑methodology** heuristics and **import from real engineering artifacts**, designed to live in the repo and run in CI. The improvements below reinforce that position rather than chase a different one.

---

## 3. Research findings by dimension (cited)

### 3.1 Open Threat Model (OTM) standard — the identity question
- The **Open Threat Model (OTM)** is a real, formal, **tool‑agnostic standard** maintained by IriusRisk: a JSON/YAML document, semver‑versioned (`otm-0.2.0.schema.json`), Apache‑2.0. Top‑level keys: `otmVersion` (req), `project` (req), `representations`, `assets`, `components`, `dataflows`, `trustZones`, `threats`, `mitigations`. Component refs use `parent` (a trustZone/component); dataflows use `source`/`destination`/`bidirectional`. Sources: [OTM repo](https://github.com/iriusrisk/OpenThreatModel), [otm_schema.json](https://github.com/iriusrisk/OpenThreatModel/blob/main/otm_schema.json), [EXAMPLE.yaml](https://github.com/iriusrisk/OpenThreatModel/blob/main/EXAMPLE.yaml), [intro blog](https://www.iriusrisk.com/resources-blog/introduction-to-the-open-threat-model-standard).
- **StartLeft** generates OTM from IaC, diagrams, and other tools' exports ([repo](https://github.com/iriusrisk/startleft)) — i.e. OTM is an interchange hub.
- **Our schema is *not* OTM‑conformant.** Ours: `model` / `metadata` / `components` / `trust_boundaries` / `data_flows` / `assets`, snake_case, `in_trust_boundary` refs, `schema_version: "1.1.0"`. OTM: `otmVersion` / `project` / `trustZones` / `dataflows`, camelCase, `parent` refs. → **An OTM import/export adapter is the highest‑identity‑alignment improvement available.**

### 3.2 Threat libraries & methodology depth
- The industry pattern is **STRIDE category → CAPEC attack pattern → CWE weakness**, optionally linked to MITRE ATT&CK and compliance frameworks, for coverage and traceability ([Security Compass](https://www.securitycompass.com/blog/capec-powers-threat-models-security-requirements/), [CAPEC‑STRIDE mapping](https://medium.com/@brettcrawley/capec-stride-mapping-1aa83a058c5d), [IriusRisk STRIDE+CAPEC](https://www.iriusrisk.com/resources-blog/stride-and-capec-with-iriusrisk)). Caveat: only ~34% of CWEs link to CAPECs, so mappings are partial.
- The **Threat Modeling Manifesto** (values + principles) is the cultural reference our docs/positioning should echo ([manifesto](https://www.threatmodelingmanifesto.org/)).
- Threagile demonstrates the value of a **named, documented rule set** (40 rules) and **custom rules** ([repo](https://github.com/Threagile/threagile)).

### 3.3 DevSecOps / CI integration
- **SARIF 2.1.0** is the JSON standard GitHub code scanning ingests; any tool can emit SARIF and have findings appear in the Security tab ([GitHub: SARIF for code scanning](https://docs.github.com/en/code-security/concepts/code-scanning/sarif-files), [uploading SARIF](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github)). → `otm analyze --sarif` is a natural, in‑scope output format.
- A **composite GitHub Action** (action.yml at repo root, published from a public repo) is the standard way to distribute a Python CLI step ([marketplace how‑to](https://medium.com/kpmg-uk-engineering/create-your-own-action-in-github-action-marketplace-145acd2276b0)).

### 3.4 AI / LLM threat modeling (PLOT4ai lens)
- **OWASP Top 10 for LLM Applications 2025**: LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM03 Supply Chain, LLM04 Data & Model Poisoning, LLM05 Improper Output Handling, LLM06 Excessive Agency, LLM07 System Prompt Leakage, LLM08 Vector & Embedding Weaknesses, LLM09 Misinformation, LLM10 Unbounded Consumption ([OWASP GenAI](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/), [PDF](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)).
- **MITRE ATLAS**: 16 tactics / 84 techniques for AI systems ([ATLAS](https://atlas.mitre.org/), [matrix repo](https://github.com/mitre/advmlthreatmatrix)).
- **PLOT4ai library**: 138 threats in 8 categories, published as JSON ([site](https://plot4.ai/), [library repo](https://github.com/PLOT4ai/plot4ai-library)). Our lens already borrows the name; mapping our heuristic IDs to these external references adds authority.

### 3.5 Adoption / DX / packaging
- **PyPI trusted publishing (OIDC)** via `pypa/gh-action-pypi-publish` removes long‑lived tokens and is the recommended modern release path ([PyPI docs](https://docs.pypi.org/trusted-publishers/), [GitHub OIDC](https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-pypi), [action](https://github.com/pypa/gh-action-pypi-publish)). We currently document install‑from‑clone only.
- Distribution as a **GitHub Action** and a **pre‑commit hook** are the two highest‑leverage adoption surfaces for a CLI security tool.

---

## 4. Prioritized workstreams (execute top‑down)

> Discipline: each item ships behind the existing contracts (no breaking change to CLI flags / OpenAPI / OTM schema unless explicitly versioned), with tests, and verified CI‑green. Prefer additive features.

### P0 — Threat traceability: attach CAPEC / CWE / OWASP references to generated threats  · effort **M** · impact **high**
- Extend the threat/heuristic data model with optional `references` (CAPEC id, CWE id, ATT&CK technique, OWASP‑LLM id where relevant), populated from a curated, data‑driven mapping table (mirrors the existing `framework-mappings` package).
- Surface them in exports (Markdown/JSON) and the UI threat cards.
- *Why P0:* highest authority‑per‑effort, purely additive, reinforces the "evidence‑friendly" promise, and is the foundation the AI‑lens mapping (P1) reuses. Sources: §3.2.

### P1 — SARIF export (`otm analyze --sarif` / API format)  · effort **M** · impact **high**
- Add a SARIF 2.1.0 exporter that maps suggested threats → SARIF `results` (rule = methodology+category, level from L×I band, locations = component/flow id, helpUri = the CAPEC/CWE ref from P0).
- Document the CI recipe (upload to GitHub code scanning). Sources: §3.3.

### P1 — OTM standard import/export bridge  · effort **L** · impact **high**
- Add `otm import otm <file>` and `otm export … --format otm` that convert between our canonical schema and IriusRisk OTM v0.2.0 (field renames + ref remapping: `trust_boundaries`↔`trustZones`, `data_flows`↔`dataflows`, `in_trust_boundary`↔`parent`, etc.). Round‑trip tested against the official `EXAMPLE.yaml`.
- *Why not P0 despite being strategic:* larger surface and needs careful round‑trip fidelity; do it right after the cheaper authority wins. Sources: §3.1.

### P1 — Deepen the PLOT4ai / AI lens with standard mappings  · effort **M** · impact **medium‑high**
- Map each PLOT4ai heuristic id to OWASP‑LLM‑2025 + MITRE ATLAS (reusing the P0 references mechanism); add any clearly‑missing high‑value signals justified by the upstream PLOT4ai library and OWASP‑LLM list (e.g. system‑prompt leakage, unbounded consumption, vector/embedding weaknesses). Keep it heuristic/assistive. Sources: §3.4.

### P2 — Packaging & distribution  · effort **S–M** · impact **high (adoption)**
- PyPI release workflow via OIDC trusted publishing (tag‑triggered, `pypa/gh-action-pypi-publish`); update README install to `pip install open-threat-model`.
- A **composite GitHub Action** wrapping `otm validate/analyze` (+ SARIF upload) for downstream CI.
- A **pre-commit hook** definition. Sources: §3.5.

### P2 — Threat‑model diff/drift gate in CI  · effort **M** · impact **medium**
- Build on the existing semantic diff: `otm diff … --fail-on <new-critical|…>` plus a baseline file, so a PR that adds unmitigated high‑risk flows can fail the build (the threat‑modeling analogue of a security gate). Sources: §3.3.

### P3 — Custom rule / heuristic authoring  · effort **M–L** · impact **medium**
- A documented, sandboxed way for adopters to add org‑specific heuristics (declarative, à la Threagile custom rules) without forking the engine. Sources: §3.2.

### P3 — Positioning & docs polish  · effort **S** · impact **medium**
- A comparison page (this table), explicit Threat Modeling Manifesto alignment, and crisp "assistive, not a completeness proof" framing. Sources: §2, §3.2.

---

## 5. Explicitly out of scope (do **not** build — scope creep / overengineering)

- **No GUI diagram editor** to compete with Threat Dragon / MS TMT. We stay code/document‑first (the web UI visualizes and guides; it is not a freeform drawing tool).
- **No multi‑tenant SaaS, accounts, org management, or hosted service.** Persistence stays local/browser by default (documented maturity boundary).
- **No commercial‑platform features** (paid tiers, enterprise RBAC, cloud rule marketplace).
- **No pivot into a generic SAST/DAST/dependency scanner.** We model threats from architecture; we do not scan source for vulns.
- **No "LLM writes your threat model" generative core.** The engine stays deterministic/heuristic and explainable; AI references are mappings, not a black‑box generator.
- **No real‑time multi‑user collaboration / live editing.** Git is the collaboration layer (by design).
- **No abandoning snake_case canonical schema.** OTM support is an *adapter*, not a replacement of the internal contract.

---

## 6. Key sources

- OTM standard: <https://github.com/iriusrisk/OpenThreatModel> · <https://github.com/iriusrisk/OpenThreatModel/blob/main/otm_schema.json> · <https://github.com/iriusrisk/startleft>
- pytm: <https://github.com/OWASP/pytm> · Threagile: <https://github.com/Threagile/threagile> · Threat Dragon: <https://github.com/owasp/threat-dragon>
- CAPEC/CWE/STRIDE: <https://www.securitycompass.com/blog/capec-powers-threat-models-security-requirements/> · <https://medium.com/@brettcrawley/capec-stride-mapping-1aa83a058c5d>
- Threat Modeling Manifesto: <https://www.threatmodelingmanifesto.org/>
- SARIF / code scanning: <https://docs.github.com/en/code-security/concepts/code-scanning/sarif-files>
- OWASP LLM Top 10 (2025): <https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/>
- MITRE ATLAS: <https://atlas.mitre.org/> · PLOT4ai: <https://plot4.ai/> · <https://github.com/PLOT4ai/plot4ai-library>
- PyPI trusted publishing: <https://docs.pypi.org/trusted-publishers/> · <https://github.com/pypa/gh-action-pypi-publish>

---

*Heuristic/assistive tool: this plan deepens evidence and interoperability; it does not turn analysis into a completeness proof. Execute in priority order, each behind existing contracts, with tests and CI‑green verification.*
