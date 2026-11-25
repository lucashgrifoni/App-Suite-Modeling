---
type: "concept"
title: "Canonical model and analysis"
description: "Follow a suggested threat from the model to a recorded decision."
tags: ["otm","schema","analysis","risk"]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-25T16:05:04.236Z
sources:
  - id: openwiki-source-1438a54573ec698bdb08b460
    resource: repo://packages/report-premium/otm_report_premium/treatment_policy.py
  - id: openwiki-source-139dfade46df189695fe90fa
    resource: repo://tests/test_report_treatment_decisions.py
generated: { by: "codex", at: "2026-11-25T16:05:04.236Z" }
---

# Canonical model and analysis

## Model and analyze

The canonical YAML or JSON document records components, data flows, assets and trust boundaries. Validation checks the model structure. Analysis adds suggested threats from the selected methodology and supports JSON and SARIF output. Review the underlying model and assumptions when interpreting a suggestion.

## Record a risk decision

In the analysis workspace, a suggestion can become a declared threat with a treatment state and rationale. For accepted risks, set the owner and review date. The unified report includes the recorded decisions and lists accepted risks in their review queue. The cover counts registered threats, and the exposure view reflects their treatment.

See [risk reports](../../docs/features/PREMIUM_REPORTS.md) for report sections and [known limitations](../../docs/KNOWN_LIMITATIONS.md) for interpretation guidance. Return to [quickstart](../quickstart.md).
