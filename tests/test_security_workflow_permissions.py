"""Regressions for the Git history scanner's PR token contract."""

from pathlib import Path

import yaml


def test_gitleaks_can_read_pr_commits_without_write_permissions():
    workflow = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".github/workflows/security-ci-cd.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["secrets-history-gitleaks"]
    assert job["permissions"].get("pull-requests") == "read"
    assert job["permissions"].get("contents") == "read"
    assert "write" not in job["permissions"].values()
    checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["persist-credentials"] is False
    scanner = next(step for step in job["steps"] if step.get("uses", "").startswith("gitleaks/gitleaks-action@"))
    assert scanner["env"]["GITLEAKS_ENABLE_COMMENTS"] == "false"
