---
type: "testing"
title: "Dependency and pull request checks"
description: "Trace the checks for local report generation and CI permissions."
tags: ["otm","pdf","ci","sarif"]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-25T16:05:04.236Z
sources:
  - id: openwiki-source-54e9868c5c0e267416e28e06
    resource: repo://.github/workflows/security-ci-cd.yml
  - id: openwiki-source-aa8effd3193d220b37c52fa8
    resource: repo://tests/test_cicd_pipeline_invariants.py
  - id: openwiki-source-6a000c3b508bec6d0c6d8516
    resource: repo://tests/test_p2_export_sarif_location.py
  - id: openwiki-source-0c127a0a58224efb45d17f15
    resource: repo://tests/test_p2r2_cli_custom_rules_drift.py
generated: { by: "codex", at: "2026-11-25T16:05:04.236Z" }
---

# Dependency and pull request checks

## Verify the report

The browser delegates report generation to the local API. The Python tests exercise the downloaded PDF and Markdown, including recorded treatment details. Use the [report guide](../../docs/features/PREMIUM_REPORTS.md) to find supported formats and options.

## Review the pipeline

The history-scanning job grants read access to contents and pull requests, uses full history and disables scanner comments. Review the actual CI run for a specific revision.

The composite action can use the organisation rules from the event's base commit in both analysis and drift checks. Use a published revision with the inputs documented in the [custom rules guide](../../docs/features/CUSTOM_RULES.md). CLI SARIF results can include the source entity line in a local YAML model.

Return to [quickstart](../quickstart.md).
