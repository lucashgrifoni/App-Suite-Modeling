---
type: "concept"
title: "Canonical model and analysis"
description: "Trace schema validation and analysis options to their current source."
tags: ["otm","schema","analysis"]
sources:
  - id: openwiki-source-b89ca78a5fab77cc9f5e6e65
    resource: repo://apps/cli/otm_cli/application/analyze_service.py
  - id: openwiki-source-07de06f2c6817c1c18abd3d3
    resource: repo://apps/cli/otm_cli/commands/analyze_cmd.py
  - id: openwiki-source-9c184a13b61c6de486e8d25d
    resource: repo://packages/core-schema/otm_core_schema/document.py
generated: { by: "codex", at: "2026-10-14T19:49:02.006Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-10-14T22:20:33.174Z
---

# Canonical model and analysis

## Canonical references

The schema rejects duplicate entity IDs and references to missing components, flows, assets or boundaries. These checks prevent inconsistent model structure; they do not prove that the model includes the entire deployed architecture. Start with the architecture and data-flow details that an owner can verify.

## Analysis orchestration

The CLI application service loads the document, an optional industry pack and optional custom rules. It then calls analyze_document with the selected methodology or automatic recommendation setting. Invalid custom-rule files become CLI input errors with a next step. The analyze command can emit full JSON and suggested-threat SARIF and can display structured explanations.

## Interpret heuristics

The documented limits include false positives and negatives and varying methodology maturity. Human review remains necessary for risk decisions. A valid model, an explainable recommendation and an approved risk decision are separate outcomes.

Sources: [schema reference checks](../../packages/core-schema/otm_core_schema/document.py#L27-L84), [analysis service](../../apps/cli/otm_cli/application/analyze_service.py#L15-L55), [analysis options](../../apps/cli/otm_cli/commands/analyze_cmd.py#L96-L137), [known limits](../../docs/KNOWN_LIMITATIONS.md). Return to [quickstart](../quickstart.md).
