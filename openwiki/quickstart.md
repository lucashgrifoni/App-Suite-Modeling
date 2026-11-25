---
type: "guide"
title: "App Suite Modeling quickstart"
description: "Create a model, validate it and generate your first risk report."
tags: ["otm","quickstart"]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-25T16:05:04.236Z
sources:
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "codex", at: "2026-11-25T16:05:04.236Z" }
---

# App Suite Modeling quickstart

## Run your first analysis

Install the Python distribution with Python 3.11 or newer. In a new directory, run:

```sh
python -m pip install open-threat-model
otm init my-model.otm.yaml --template saas-web
otm validate my-model.otm.yaml
otm analyze my-model.otm.yaml --methodology stride
otm report my-model.otm.yaml -o risk-report.md
```

Use the generated model to review components, flows and trust boundaries. Confirm these details against your own service before acting on suggested threats.

## Find the next task

- [Understand models and risk decisions](concepts/model-and-analysis.md)
- [Import or compare models](guides/imports-and-comparisons.md)
- [Run the API and web interface](architecture/application-surfaces.md)
- [Verify reports and workflow behavior](testing/dependency-and-pr-checks.md)
<!-- openwiki: broken internal link [../docs/openwiki.md] file "../docs/openwiki.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- [Maintain this wiki](../docs/openwiki.md)

See the [project README](../README.md) for contributor setup.
