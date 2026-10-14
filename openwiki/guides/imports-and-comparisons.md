---
type: "guide"
title: "Imports and comparisons"
description: "Review imported assumptions and interpret model-change gates within heuristic limits."
tags: ["otm","import","diff"]
sources:
  - id: openwiki-source-67791dadb9dd9fb70bc12bc1
    resource: repo://apps/cli/otm_cli/application/import_service.py
  - id: openwiki-source-b5beb2865989135504312c43
    resource: repo://docs/KNOWN_LIMITATIONS.md
generated: { by: "codex", at: "2026-10-14T19:49:02.006Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-10-14T22:20:33.174Z
---

# Imports and comparisons

## Imported artifacts are drafts

OpenAPI, Terraform and Kubernetes import services return canonical YAML with inference, unknown and assumption records. Keep these records when reviewing the generated model. Check names, boundaries, data classification and inferred relationships against the actual system before analysis.

The [artifact-import guide](../../docs/features/ARTIFACT_IMPORT.md) describes the supported formats and [comparison guide](../../docs/features/THREAT_MODEL_DIFF.md) describes the available diff surfaces.

## Gate interpretation

The documented diff limits include noise from renamed component/flow IDs and comparisons across engine versions. A green heuristic gate means no newly generated threat above its configured threshold; it does not establish that the model is secure. Use an explicit engine version and retain the before/after models and interpretation notes with review evidence.

Sources: [import services](../../apps/cli/otm_cli/application/import_service.py#L20-L81), [known comparison limits](../../docs/KNOWN_LIMITATIONS.md). Return to [quickstart](../quickstart.md).
