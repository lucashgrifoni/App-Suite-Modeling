---
type: testing
title: Dependency and pull request checks
description: Trace the PDF dependency override, regression assertions and Git history scanner permissions.
tags: [dependencies, pdf, ci, regression]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-14T22:20:33.174Z
sources:
  - id: openwiki-source-54e9868c5c0e267416e28e06
    resource: repo://.github/workflows/security-ci-cd.yml
  - id: openwiki-source-99de51df25f29bfc72caf823
    resource: repo://apps/web/package.json
  - id: openwiki-source-30f1310f30bd3b5722b1f121
    resource: repo://apps/web/src/lib/pdfDependencySecurity.test.ts
  - id: openwiki-source-acf3bce6ad6edcf7ba5d68ed
    resource: repo://tests/test_security_workflow_permissions.py
generated: { by: "codex", at: "2026-10-14T22:20:33.174Z" }
---

# Dependency and pull request checks

## The PDF dependency boundary

The [web manifest](../../apps/web/package.json) applies a DOMPurify 3.4.16 override under jsPDF. The [lockfile](../../apps/web/package-lock.json) records the resolved dependency; contributors should install from that lockfile when reproducing checks. Updating a vulnerable library and demonstrating an exploit in the application are separate claims.

The [security regression tests](../../apps/web/src/lib/pdfDependencySecurity.test.ts) exercise both after-sanitization hook sites in in-place mode and a removed rawtext root. They assert that unsafe event-handler markup does not survive those conditions. A positive control checks ordinary sanitization and a text-only PDF result. These checks target the installed library API; they do not establish that the application exposes every tested hook or HTML path.

## The PR scanner token

The [Git history scanner job](../../.github/workflows/security-ci-cd.yml) grants contents and pull-request reads, checks out full history without persisted credentials and disables scanner comments. Reading PR commits is needed by that action; a configured permission alone does not establish that a hosted scan completed.

The [workflow regression test](../../tests/test_security_workflow_permissions.py) checks those permissions and rejects write permissions for that job. It also verifies the full-history checkout and comment setting. Repository history and the incoming PR range remain different scan scopes; a clean incoming range does not establish that the entire history is clean.

## Review the result

Read the actual CI run, finding reports and required reviews for the revision under consideration. Dependency updates, a passing model-analysis gate and release approval prove different things. Return to [quickstart](../quickstart.md) for contributor entry points or [HTTP and browser surfaces](../architecture/application-surfaces.md) for runtime boundaries.
