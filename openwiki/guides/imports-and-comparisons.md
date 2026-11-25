---
type: "guide"
title: "Imports and comparisons"
description: "Review draft imports and apply compatible OpenAPI changes to a model."
tags: ["otm","import","openapi","diff"]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-25T16:05:04.236Z
sources:
  - id: openwiki-source-5f28b4dac24b7d499a13504c
    resource: repo://apps/api/otm_api/routers/imports.py
  - id: openwiki-source-62dc2ee8a20ea73737f9c496
    resource: repo://docs/features/ARTIFACT_IMPORT.md
  - id: openwiki-source-0f9bf6fe300589521a6cb586
    resource: repo://tests/test_cli_import_coverage.py
generated: { by: "codex", at: "2026-11-25T16:05:04.236Z" }
---

# Imports and comparisons

## Review imported drafts

Use OpenAPI, Kubernetes manifests or Terraform to seed a canonical threat model. Check the inferred boundaries and data flows before analyzing the draft. The [artifact import guide](../../docs/features/ARTIFACT_IMPORT.md) explains the supported inputs and limitations.

## Preview an OpenAPI revision

`otm import openapi-diff previous.yaml revised.yaml` lists added, removed and changed operations. In the web interface, provide the two contracts and the active model. Review conflicts before applying compatible changes. Decisions and conflicts remain available in the current model. Export the model to keep the updated revision.

Use the [comparison guide](../../docs/features/THREAT_MODEL_DIFF.md) to interpret model drift. Return to [quickstart](../quickstart.md).
