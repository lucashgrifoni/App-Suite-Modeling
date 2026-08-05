# Where this tool fits

Threat modelling has good tools. This page says what App Suite Modeling does that they do not,
and — more usefully — when you should use one of them instead.

Nothing here is a claim that this project is better. Every tool below is mature, several are
OWASP flagships, and one is a commercial platform with resources this project does not have.

## The one-line version

An open, **code-first** threat modelling tool with **three surfaces over one document** (CLI,
REST API, web UI), **several methodologies** rather than one rule set, and **import from real
engineering artifacts** — designed to live in the repository and run in CI.

## Compared with

| Tool | Model lives in | Threats come from | Surfaces | Stronger than us at |
|---|---|---|---|---|
| [**OWASP pytm**](https://owasp.org/www-project-pytm/) | Python source | Python expressions over element properties | CLI / library | Being pure code. If your team is comfortable expressing a model as a Python program, pytm is more direct and more flexible than a schema. |
| [**Threagile**](https://threagile.io/) | YAML | ~40 built-in risk rules, plus custom rules | CLI / Docker | A more mature rule engine, and IDE schema autocomplete on the model file. |
| [**OWASP Threat Dragon**](https://threatdragon.github.io/) | A diagram, drawn in a GUI | Rule engine over the diagram | Web + desktop | Diagram-first UX, by a distance. It is an OWASP flagship and it is polished. If your modelling sessions are people around a whiteboard, start there. |
| [**IriusRisk**](https://www.iriusrisk.com/) | Diagram, OTM, or IaC via StartLeft | Commercial rule set with CAPEC mappings | Commercial platform | Enterprise depth, support, and the OTM standard itself — which this project implements rather than competes with. |
| **Microsoft TMT** | Diagram (GUI, Windows) | Template-driven STRIDE | Desktop app | Familiarity in Microsoft shops. |

## What is actually different here

**One document, three surfaces.** The `.otm.yaml` is the only source of truth. The CLI, the
REST API and the web UI are views over it — none of them owns state the others cannot see. In
practice that means a model authored in the UI is reviewable as a diff and gateable in CI
without an export step.

**Several methodologies, not one rule set.** STRIDE, LINDDUN, PASTA, NIST Data-Centric, OCTAVE
Allegro, CIA-DIE and PLOT4ai for AI systems, applied as lenses over the same model. A tool
built around one rule set answers one question well; this answers several, less deeply.

**Import from artifacts you already have.** OpenAPI, Kubernetes manifests, Terraform and Helm
produce a reviewable draft. The draft is a starting point, not an answer — it is explicitly
labelled as such — but it removes the blank page.

**Built for the pull request.** Threats carry CAPEC/CWE/ASVS/CSF/ISO references, analysis
exports as SARIF for code scanning, models diff semantically, and `otm diff --fail-on` fails a
build when a change adds risk. The committed model is the baseline, so there is no suppression
file to maintain.

**Extensible without a fork.** [Custom rules](features/CUSTOM_RULES.md) let an organisation add
its own heuristics as data — no expression language, no code execution.

## When not to use it

- **You want a diagram-first workshop tool.** Use Threat Dragon. This project renders Mermaid
  and has a React Flow canvas, but it is a document-first tool and it shows.
- **You want a deep, mature rule engine for architectural risk.** Threagile has more built-in
  rules and years of tuning behind them.
- **You want your model to be a program.** pytm is the honest answer.
- **You need enterprise support, SSO, or an auditable multi-team workflow.** This is a
  single-maintainer open-source project. Use a commercial platform.
- **You want a completeness guarantee.** No tool provides one, and this project states so in
  [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md). The engine is deterministic and heuristic: it
  surfaces what is worth a human's attention. A clean run is not a statement that the system is
  secure.

## On the name

The Python distribution is `open-threat-model` and the canonical file is `.otm.yaml`, because
this project implements IriusRisk's [Open Threat Model](https://github.com/iriusrisk/OpenThreatModel)
interchange format — `otm import otm` and `otm export --format otm`. It is an independent
implementation, not the standard itself, and not affiliated with IriusRisk. See
[NOTICE](../NOTICE).
