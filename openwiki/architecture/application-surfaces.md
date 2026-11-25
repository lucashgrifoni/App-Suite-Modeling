---
type: "architecture"
title: "HTTP and browser surfaces"
description: "Understand the local web workspace and report service."
tags: ["otm","api","ui"]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-25T16:05:04.236Z
sources:
  - id: openwiki-source-84a6824e7346be004be32bec
    resource: repo://apps/api/otm_api/main.py
  - id: openwiki-source-969a0556126f8a43d6e0c5cb
    resource: repo://apps/web/src/api/otmApi.ts
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "codex", at: "2026-11-25T16:05:04.236Z" }
---

# HTTP and browser surfaces

## Local application

The CLI and HTTP API share the model, analysis and reporting packages. Use the contributor setup in the [README](../../README.md) and run `python scripts/run_dev.py` to start the API and web interface together.

The browser maintains the editing session. Open the local service to generate a PDF or Markdown risk report through `/v1/reports`.

## Deployment boundaries

Review [deployment invariants](../../docs/architecture/DEPLOYMENT_INVARIANTS.md) before exposing an API instance. Check the deployed authentication and rate-limit configuration for the environment in use.

Return to [quickstart](../quickstart.md).
