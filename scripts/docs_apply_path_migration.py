"""
One-shot helper: rewrite docs/*.md path references after docs/ reorganization.

Usage (from repo root):
  python scripts/docs_apply_path_migration.py

Do not re-run after migration is applied (idempotent for exact string pairs only).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_MIGRATION: dict[str, str] = {
    # features/
    "docs/features/API.md": "docs/features/API.md",
    "docs/features/CLI.md": "docs/features/CLI.md",
    "docs/features/UI.md": "docs/features/UI.md",
    "docs/features/ARTIFACT_IMPORT.md": "docs/features/ARTIFACT_IMPORT.md",
    "docs/features/THREAT_MODEL_DIFF.md": "docs/features/THREAT_MODEL_DIFF.md",
    "docs/features/EXPORTERS.md": "docs/features/EXPORTERS.md",
    "docs/features/PREMIUM_REPORTS.md": "docs/features/PREMIUM_REPORTS.md",
    "docs/features/REMEDIATION_BACKLOG.md": "docs/features/REMEDIATION_BACKLOG.md",
    "docs/features/EXPLAINABILITY.md": "docs/features/EXPLAINABILITY.md",
    "docs/features/TEMPLATES_AND_PACKS.md": "docs/features/TEMPLATES_AND_PACKS.md",
    "docs/features/TEMPLATE_CATALOG.md": "docs/features/TEMPLATE_CATALOG.md",
    "docs/features/CHOOSE_METHODOLOGY.md": "docs/features/CHOOSE_METHODOLOGY.md",
    "docs/features/MULTI_ENGINE_ARCHITECTURE.md": "docs/features/MULTI_ENGINE_ARCHITECTURE.md",
    "docs/features/PLOT4AI_AI_SYSTEM.md": "docs/features/PLOT4AI_AI_SYSTEM.md",
    "docs/features/I18N.md": "docs/features/I18N.md",
    "docs/features/CONTRACT_AND_SNAPSHOTS.md": "docs/features/CONTRACT_AND_SNAPSHOTS.md",
    "docs/features/SCHEMA_V1.md": "docs/features/SCHEMA_V1.md",
    "docs/features/CORE_ENGINE.md": "docs/features/CORE_ENGINE.md",
    "docs/features/MVP_ROADMAP.md": "docs/features/MVP_ROADMAP.md",
    "docs/features/PRODUCT_POSITIONING.md": "docs/features/PRODUCT_POSITIONING.md",
    "docs/features/BRANDING.md": "docs/features/BRANDING.md",
    "docs/features/SCREENSHOT_GUIDE.md": "docs/features/SCREENSHOT_GUIDE.md",
    "docs/features/MODELING_QUALITY.md": "docs/features/MODELING_QUALITY.md",
    "docs/features/SECURITY_HEADERS.md": "docs/features/SECURITY_HEADERS.md",
    # architecture/
    "docs/architecture/ARCHITECTURE.md": "docs/architecture/ARCHITECTURE.md",
    "docs/architecture/DESIGN_SYSTEM_FOUNDATION.md": "docs/architecture/DESIGN_SYSTEM_FOUNDATION.md",
    "docs/architecture/CONTRACTS_CI_HYBRID.md": "docs/architecture/CONTRACTS_CI_HYBRID.md",
    "docs/architecture/DEPLOYMENT_INVARIANTS.md": "docs/architecture/DEPLOYMENT_INVARIANTS.md",
    "docs/architecture/PRE_COMMIT.md": "docs/architecture/PRE_COMMIT.md",
    "docs/architecture/SEMGREP_POLICY.md": "docs/architecture/SEMGREP_POLICY.md",
    "docs/architecture/SMOKE_VALIDATION.md": "docs/architecture/SMOKE_VALIDATION.md",
    "docs/architecture/adr/": "docs/architecture/adr/",
    # internal/audits
    "docs/internal/audits/FULL_ENGINEERING_COMPLIANCE_AUDIT.md": "docs/internal/audits/FULL_ENGINEERING_COMPLIANCE_AUDIT.md",
    "docs/internal/audits/FULL_ENGINEERING_FILE_COVERAGE.md": "docs/internal/audits/FULL_ENGINEERING_FILE_COVERAGE.md",
    "docs/internal/audits/FULL_ENGINEERING_FINDINGS_MATRIX.md": "docs/internal/audits/FULL_ENGINEERING_FINDINGS_MATRIX.md",
    "docs/internal/audits/FULL_ENGINEERING_SCORECARD.md": "docs/internal/audits/FULL_ENGINEERING_SCORECARD.md",
    "docs/internal/audits/FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT.md": "docs/internal/audits/FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT.md",
    "docs/internal/audits/FULL_PROJECT_QUALITY_SCORECARD.md": "docs/internal/audits/FULL_PROJECT_QUALITY_SCORECARD.md",
    "docs/internal/audits/SONAR_DECISION_REPORT.md": "docs/internal/audits/SONAR_DECISION_REPORT.md",
    # internal/logs
    "docs/internal/logs/FULL_ENGINEERING_TOOL_EXECUTION_LOG.md": "docs/internal/logs/FULL_ENGINEERING_TOOL_EXECUTION_LOG.md",
    "docs/internal/logs/FINAL_RELEASE_EXECUTION_LOG.md": "docs/internal/logs/FINAL_RELEASE_EXECUTION_LOG.md",
    # internal/reports
    "docs/internal/reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md": "docs/internal/reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md",
    "docs/internal/reports/FINAL_RELEASE_SCORECARD.md": "docs/internal/reports/FINAL_RELEASE_SCORECARD.md",
    "docs/internal/reports/VALIDATION_REPORT_v0.1.0.md": "docs/internal/reports/VALIDATION_REPORT_v0.1.0.md",
    "docs/internal/reports/RELEASE_NOTES_v0.1.0.md": "docs/internal/reports/RELEASE_NOTES_v0.1.0.md",
    "docs/internal/reports/RELEASE_NOTES_RC1.md": "docs/internal/reports/RELEASE_NOTES_RC1.md",
    "docs/internal/reports/RELEASE_NOTES_RC2.md": "docs/internal/reports/RELEASE_NOTES_RC2.md",
    "docs/internal/reports/FULL_ENGINEERING_NEXT_ACTIONS.md": "docs/internal/reports/FULL_ENGINEERING_NEXT_ACTIONS.md",
    "docs/internal/reports/FULL_PROJECT_REMEDIATION_BACKLOG.md": "docs/internal/reports/FULL_PROJECT_REMEDIATION_BACKLOG.md",
    "docs/internal/reports/FULL_PROJECT_REMEDIATION_PLAN.md": "docs/internal/reports/FULL_PROJECT_REMEDIATION_PLAN.md",
    "docs/internal/reports/RESIDUAL_RISK_REGISTER.md": "docs/internal/reports/RESIDUAL_RISK_REGISTER.md",
    "docs/internal/reports/FRONTEND_UI_ROLLOUT_HISTORY.md": "docs/internal/reports/FRONTEND_UI_ROLLOUT_HISTORY.md",
    "docs/internal/reports/GITHUB_README_AND_METADATA.md": "docs/internal/reports/GITHUB_README_AND_METADATA.md",
    # internal/decisions
    "docs/internal/decisions/STRIDE_GENERICITY_REDUCTION_DECISION.md": "docs/internal/decisions/STRIDE_GENERICITY_REDUCTION_DECISION.md",
    "docs/internal/decisions/E2E_GATE_DECISION.md": "docs/internal/decisions/E2E_GATE_DECISION.md",
    "docs/internal/decisions/ENGINEERING_CLOSEOUT_SCOPE.md": "docs/internal/decisions/ENGINEERING_CLOSEOUT_SCOPE.md",
    "docs/internal/decisions/RELEASE_SCOPE_FREEZE.md": "docs/internal/decisions/RELEASE_SCOPE_FREEZE.md",
    "docs/internal/decisions/NEXT_PHASE_RECOMMENDATIONS.md": "docs/internal/decisions/NEXT_PHASE_RECOMMENDATIONS.md",
    # internal/checklists
    "docs/internal/checklists/LAUNCH_CHECKLIST.md": "docs/internal/checklists/LAUNCH_CHECKLIST.md",
    "docs/internal/checklists/RELEASE_ENGINEERING_CHECKLIST.md": "docs/internal/checklists/RELEASE_ENGINEERING_CHECKLIST.md",
    "docs/internal/checklists/RELEASE_CHECKLIST_RC.md": "docs/internal/checklists/RELEASE_CHECKLIST_RC.md",
    "docs/internal/checklists/PREPUBLISH_CHECKLIST.md": "docs/internal/checklists/PREPUBLISH_CHECKLIST.md",
    "docs/internal/checklists/DEFINITION_OF_DONE.md": "docs/internal/checklists/DEFINITION_OF_DONE.md",
    "docs/internal/checklists/GO_NO_GO_v0.1.0.md": "docs/internal/checklists/GO_NO_GO_v0.1.0.md",
    "docs/internal/checklists/PUBLISH_PLAYBOOK.md": "docs/internal/checklists/PUBLISH_PLAYBOOK.md",
}

# Sort by descending old length to avoid partial substitutions.
_PAIRS = sorted(_MIGRATION.items(), key=lambda x: -len(x[0]))

_SKIP_PARTS = {".venv", "node_modules", "dist", "build", ".git", "htmlcov", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".ts", ".tsx", ".json"}


def main() -> None:
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _SUFFIXES:
            continue
        if any(p in path.parts for p in _SKIP_PARTS):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        orig = text
        for old, new in _PAIRS:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            changed += 1
    print(f"Updated {changed} files.")


if __name__ == "__main__":
    main()
