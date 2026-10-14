---
type: "architecture"
title: "HTTP and browser surfaces"
description: "Navigate HTTP composition and the documented local-state deployment boundaries."
tags: ["otm","api","ui"]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-14T22:20:33.174Z
sources:
  - id: openwiki-source-84a6824e7346be004be32bec
    resource: repo://apps/api/otm_api/main.py
  - id: openwiki-source-b5beb2865989135504312c43
    resource: repo://docs/KNOWN_LIMITATIONS.md
generated: { by: "codex", at: "2026-10-14T19:49:02.006Z" }
---

# HTTP and browser surfaces

## HTTP composition

The FastAPI composition root exposes system routes and places model, analysis, template, export, import, remediation and report routers under /v1. The root response links to docs, redoc, OpenAPI and health. Middleware includes observability, optional API-key protection, CORS and rate limiting when configured.

Inspect the perimeter configuration and [deployment invariants](../../docs/architecture/DEPLOYMENT_INVARIANTS.md) for a specific deployment. Optional authentication in source is not evidence that a running instance has it enabled.

## Browser and persistence boundaries

The documented current UI stores local drafts in sessionStorage; it has no centralized accounts, teams or history. The API key protects /v1 only when configured. Publishing an API instance therefore needs a deliberate deployment boundary and the project's deployment guidance.

For web contributors, use the scripts documented by the repository, including the portable build path on Windows when shell wrappers fail on workspace names. Keep local UI build checks separate from HTTP end-to-end verification against a running backend.

Sources: [API composition](../../apps/api/otm_api/main.py#L68-L109), [current limitations](../../docs/KNOWN_LIMITATIONS.md). Return to [quickstart](../quickstart.md).
