---
type: "guide"
title: "App Suite Modeling quickstart"
description: "Use the canonical model through the CLI before moving to HTTP or browser workflows."
tags: ["otm","quickstart"]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-14T19:49:02.006Z
sources:
  - id: openwiki-source-599772ae4c23227bb62f171f
    resource: repo://apps/cli/otm_cli/cli.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
generated: { by: "codex", at: "2026-10-14T19:49:02.006Z" }
---

# App Suite Modeling quickstart

## One model, several surfaces

The distribution is named open-threat-model and requires Python 3.11 or newer. The otm CLI, FastAPI adapter and web UI operate on the canonical threat-model document. The CLI bootstrap registers modeling, analysis, export, import, template and comparison commands; business orchestration is in the application layer.

## First local model

From a clone, install the contributor extras described in [README](../README.md) and [pyproject.toml](../pyproject.toml), then run:

```sh
python -m pip install -e ".[dev,cli,api]"
otm init my-model.otm.yaml
otm validate my-model.otm.yaml
otm analyze my-model.otm.yaml --json-out analyze.json
```

Review the model and suggested threats before exporting them or using a gate result. Schema validity and heuristic output establish narrower facts than security approval.

- [Canonical model and analysis](concepts/model-and-analysis.md)
- [Imports and comparisons](guides/imports-and-comparisons.md)
- [HTTP and browser surfaces](architecture/application-surfaces.md)
- [OpenWiki setup](../docs/openwiki.md)

Sources: [package metadata](../pyproject.toml#L5-L24), [CLI registration](../apps/cli/otm_cli/cli.py#L30-L65), [analysis options](../apps/cli/otm_cli/commands/analyze_cmd.py#L96-L109).
