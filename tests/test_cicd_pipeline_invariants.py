"""Security invariants of the delivery pipeline itself.

Every assertion here exists because a gate was found not gating, or a document was found
claiming a control that no workflow ran. The subject under test is the YAML in
`.github/workflows/`, `action.yml` and the two pre-commit files, plus the evidence document
that describes them.

The shell-level tests execute the real step body extracted from the YAML, with the external
commands (`gh`, `git`, `otm`) replaced by bash *functions*. A function shadows a binary
without needing a file on PATH or an executable bit, so the same test runs on a Linux runner
and on a Windows workstation with Git Bash, and no git repository is ever created or touched.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SECURITY_WF = WORKFLOWS / "security-ci-cd.yml"
PROJECT_WF = WORKFLOWS / "github-ci-cd.yml"
PUBLISH_WF = WORKFLOWS / "publish-pypi.yml"
ACTION_YML = REPO_ROOT / "action.yml"
PRE_COMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
PRE_COMMIT_HOOKS = REPO_ROOT / ".pre-commit-hooks.yaml"
README = REPO_ROOT / "README.md"
EVIDENCE_DOC = REPO_ROOT / "docs" / "CI_AND_SECURITY_EVIDENCE.md"

SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _resolve_bash() -> str | None:
    """A POSIX shell that actually runs, not merely one that is on PATH.

    On Windows, `shutil.which("bash")` finds `C:\\Windows\\System32\\bash.exe` first — the WSL
    launcher. With no distribution installed it exits non-zero with
    `execvpe(/bin/bash) failed`, so every step body below "failed" for a reason that has
    nothing to do with the workflow under test. Git Bash sits further down PATH, or off it
    entirely at its install location.

    Each candidate is therefore *executed* before being accepted.
    """
    candidates = [
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        "/bin/bash",
    ]
    for candidate in candidates:
        if not candidate or not pathlib.Path(candidate).exists():
            continue
        try:
            probe = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user input
                [candidate, "-c", "echo ok"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _resolve_bash()


def _load(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_security_event_write_is_granted_to_upload_jobs_only() -> None:
    workflow = _load(SECURITY_WF)
    assert workflow["permissions"].get("security-events") != "write"

    for job_id, job in workflow["jobs"].items():
        uploads_security_events = any(
            step.get("uses", "").startswith(("github/codeql-action/upload-sarif@", "github/codeql-action/analyze@"))
            for step in job["steps"]
        )
        has_write = job.get("permissions", {}).get("security-events") == "write"
        assert has_write == uploads_security_events, job_id


def _triggers(workflow: dict) -> dict:
    """`on:` is YAML 1.1 truthy, so PyYAML keys it under `True`."""
    return workflow.get("on", workflow.get(True))


def _steps(workflow_path: pathlib.Path, job: str) -> list[dict]:
    return _load(workflow_path)["jobs"][job]["steps"]


def _step(workflow_path: pathlib.Path, job: str, name: str) -> dict:
    for step in _steps(workflow_path, job):
        if step.get("name") == name:
            return step
    raise AssertionError(f"{workflow_path.name}: job '{job}' has no step named '{name}'")


def _action_step(name: str) -> dict:
    for step in _load(ACTION_YML)["runs"]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"action.yml has no step named '{name}'")


def test_snyk_jobs_share_the_verified_cli_installer() -> None:
    for job_id in ("sast-snyk-code", "sca-snyk"):
        install = _step(SECURITY_WF, job_id, "Install Snyk CLI")
        assert install["run"] == "bash scripts/install-snyk-cli.sh"


def test_snyk_installer_rejects_a_mismatched_download(tmp_path: pathlib.Path) -> None:
    path_file = tmp_path / "github-path"
    path_file.write_text("", encoding="utf-8")
    installer = (REPO_ROOT / "scripts" / "install-snyk-cli.sh").as_posix()
    result = _run_bash(
        """
        curl() {
          while [ "$#" -gt 1 ]; do
            if [ "$1" = "--output" ]; then
              printf 'checksum test fixture' > "$2"
              return
            fi
            shift
          done
          return 2
        }
        export -f curl
        bash "$INSTALLER"
        """,
        {"INSTALLER": installer, "RUNNER_TEMP": tmp_path.as_posix(), "GITHUB_PATH": path_file.as_posix()},
        tmp_path,
    )
    assert result.returncode == 1, result.stderr
    assert "FAILED" in result.stdout, result.stdout
    assert path_file.read_text(encoding="utf-8") == ""


def _run_bash(script: str, env: dict[str, str], tmp_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    assert BASH is not None, "these pipeline tests need a POSIX shell; install git-bash or run on Linux"
    full_env = dict(os.environ)
    full_env.update(env)
    # `-e` mirrors the shell GitHub actually gives a `run:` step (`bash -e {0}`), so a step
    # that only survives locally because errexit was off cannot pass here.
    return subprocess.run(
        [BASH, "-e", "-c", script],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(tmp_path),
    )


def _actions_env(tmp_path: pathlib.Path) -> dict[str, str]:
    out = tmp_path / "gh_output"
    summary = tmp_path / "gh_summary"
    out.write_text("", encoding="utf-8")
    summary.write_text("", encoding="utf-8")
    return {
        "GITHUB_OUTPUT": str(out).replace("\\", "/"),
        "GITHUB_STEP_SUMMARY": str(summary).replace("\\", "/"),
        "RUNNER_TEMP": str(tmp_path).replace("\\", "/"),
    }


# ---------------------------------------------------------------------------------------
# Preflight must fail CLOSED when it cannot reach the API (finding #3)
# ---------------------------------------------------------------------------------------

PREFLIGHT_BASE_ENV = {
    "ACTOR": "someuser",
    "REPO": "owner/repo",
    "SNYK_TOKEN": "",
    "GH_TOKEN": "t",
    "PREFLIGHT_PROBE_BACKOFF": "0",
}

GH_STUB_UNREACHABLE = 'gh() { echo "gh: API rate limit exceeded for installation" >&2; return 1; }\n'
GH_STUB_PUBLIC = 'gh() { case "$*" in *visibility*) echo public ;; *) echo "" ;; esac; }\n'
GH_STUB_PRIVATE_NO_GHAS = 'gh() { case "$*" in *visibility*) echo private ;; *) echo "" ;; esac; }\n'
GH_STUB_PRIVATE_NULL_GHAS = 'gh() { case "$*" in *visibility*) echo private ;; *) echo null ;; esac; }\n'


def _run_preflight(stub: str, tmp_path: pathlib.Path) -> tuple[subprocess.CompletedProcess[str], str]:
    body = _step(SECURITY_WF, "preflight", "Determine context")["run"]
    env = dict(PREFLIGHT_BASE_ENV)
    env.update(_actions_env(tmp_path))
    result = _run_bash(stub + body, env, tmp_path)
    written = (tmp_path / "gh_output").read_text(encoding="utf-8")
    return result, written


def test_preflight_fails_closed_when_the_api_probe_errors(tmp_path):
    """A rate limit or 5xx must not be read as 'code scanning is unavailable'."""
    result, _ = _run_preflight(GH_STUB_UNREACHABLE, tmp_path)
    assert result.returncode != 0, f"probe failure left the step green: {result.stdout}{result.stderr}"


def test_preflight_does_not_disable_code_scanning_on_a_probe_error(tmp_path):
    _, written = _run_preflight(GH_STUB_UNREACHABLE, tmp_path)
    assert "code_scanning=false" not in written


def test_preflight_enables_code_scanning_for_a_public_repository(tmp_path):
    """The fix must not degrade into 'refuse everything': a real answer still decides."""
    result, written = _run_preflight(GH_STUB_PUBLIC, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert "code_scanning=true" in written


def test_preflight_disables_code_scanning_for_a_private_repo_without_advanced_security(tmp_path):
    """An EMPTY Advanced Security field is an answer ('off'), not an unreachable API."""
    result, written = _run_preflight(GH_STUB_PRIVATE_NO_GHAS, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert "code_scanning=false" in written


def test_preflight_treats_a_literal_null_advanced_security_field_as_off(tmp_path):
    """`gh --jq` prints `null` for an absent field; that is still an answer, not an outage."""
    result, written = _run_preflight(GH_STUB_PRIVATE_NULL_GHAS, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert "code_scanning=false" in written


# ---------------------------------------------------------------------------------------
# Snyk auth classifier must not read a transient failure as an auth rejection (finding #12)
# ---------------------------------------------------------------------------------------

SNYK_JOBS = ("sast-snyk-code", "sca-snyk")

AUTH_REJECTIONS = (
    "Authentication error (SNYK-0005)",
    "token is not provisioned",
    "Unauthorized (401) - your token is invalid",
)

TRANSIENT_FAILURES = (
    "Snyk CLI failed. request-id: 8a401f2e-3b7d-4e11-9f02-cc1d2e5b7a99",
    "ERROR: 502 Bad Gateway (trace 3401)",
    "connect ECONNREFUSED 10.0.0.1:8401",
    "Too many requests (429) request-id: 1f2c9ab0",
    "Internal Server Error (500)",
    "ETIMEDOUT connecting to api.snyk.io",
)


def _snyk_auth_classifier(job: str) -> str:
    body = _step(SECURITY_WF, job, "Authenticate Snyk")["run"]
    match = re.search(r"grep -qiE '([^']+)'", body)
    assert match is not None, f"{job}: no `grep -qiE '...'` classifier found in the auth step"
    return match.group(1)


def test_snyk_auth_classifier_is_one_definition_shared_by_both_jobs():
    patterns = {job: _snyk_auth_classifier(job) for job in SNYK_JOBS}
    assert len(set(patterns.values())) == 1, patterns


def test_snyk_auth_classifier_recognises_a_real_auth_rejection():
    pattern = _snyk_auth_classifier("sast-snyk-code")
    missed = [text for text in AUTH_REJECTIONS if not re.search(pattern, text, re.IGNORECASE)]
    assert missed == [], f"auth rejections would fail the job instead of skipping: {missed}"


def test_snyk_auth_classifier_does_not_skip_on_transient_errors():
    """A `401` inside a request id must not silently drop the Snyk gate behind a green check."""
    pattern = _snyk_auth_classifier("sast-snyk-code")
    misread = [text for text in TRANSIENT_FAILURES if re.search(pattern, text, re.IGNORECASE)]
    assert misread == [], f"transient failures misread as auth rejections: {misread}"


# ---------------------------------------------------------------------------------------
# The drift gate must not trust a baseline the pull request can rewrite (finding #8)
# ---------------------------------------------------------------------------------------

GIT_STUB_BASE_AVAILABLE = (
    "git() {\n"
    '  if [ "$1" = "fetch" ]; then return 0; fi\n'
    '  if [ "$1" = "show" ]; then\n'
    '    case "$2" in\n'
    '      origin/main:*) echo "BASE-BRANCH-BASELINE"; return 0 ;;\n'
    "      *) return 128 ;;\n"
    "    esac\n"
    "  fi\n"
    "  return 128\n"
    "}\n"
)

GIT_STUB_BASE_UNREACHABLE = "git() { return 128; }\n"

OTM_STUB_RECORDING = 'otm() { printf "%s\\n" "$*" > "$RUNNER_TEMP/otm-argv"; return 0; }\n'


def _run_gate(stub: str, env_extra: dict[str, str], tmp_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    body = _action_step("Threat-model drift gate")["run"]
    env = {
        "MODEL": "threat-model.otm.yaml",
        "BASELINE": "baseline/threat-model.otm.yaml",
        "BASELINE_REF": "",
        "FAIL_ON": "high",
        "RISK_INCREASE": "false",
        "METHODOLOGY": "",
        "PACK": "",
        "GITHUB_BASE_REF": "main",
    }
    env.update(_actions_env(tmp_path))
    env.update(env_extra)
    return _run_bash(stub + OTM_STUB_RECORDING + body, env, tmp_path)


def test_gate_reads_the_baseline_from_the_base_branch_not_the_checkout(tmp_path):
    """The tree the pull request controls must not supply the baseline it is judged against."""
    result = _run_gate(GIT_STUB_BASE_AVAILABLE, {}, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    argv = (tmp_path / "otm-argv").read_text(encoding="utf-8")
    assert "baseline/threat-model.otm.yaml" not in argv, f"gate diffed the in-tree baseline: {argv}"


def test_gate_baseline_content_comes_from_the_base_revision(tmp_path):
    _run_gate(GIT_STUB_BASE_AVAILABLE, {}, tmp_path)
    resolved = (tmp_path / "otm-gate-baseline.otm.yaml").read_text(encoding="utf-8")
    assert "BASE-BRANCH-BASELINE" in resolved


def test_gate_refuses_a_verdict_when_the_base_revision_cannot_be_read(tmp_path):
    result = _run_gate(GIT_STUB_BASE_UNREACHABLE, {}, tmp_path)
    assert result.returncode != 0, f"{result.stdout}{result.stderr}"


def test_gate_never_reports_passed_when_the_baseline_is_unresolvable(tmp_path):
    _run_gate(GIT_STUB_BASE_UNREACHABLE, {}, tmp_path)
    written = (tmp_path / "gh_output").read_text(encoding="utf-8")
    assert "outcome=passed" not in written


def test_gate_reports_not_evaluated_when_the_baseline_is_unresolvable(tmp_path):
    _run_gate(GIT_STUB_BASE_UNREACHABLE, {}, tmp_path)
    written = (tmp_path / "gh_output").read_text(encoding="utf-8")
    assert "outcome=not-evaluated" in written


def test_gate_still_runs_on_push_events_where_there_is_no_pull_request(tmp_path):
    """No base ref means no pull request to tamper with: the in-tree baseline is legitimate."""
    result = _run_gate(GIT_STUB_BASE_UNREACHABLE, {"GITHUB_BASE_REF": ""}, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    argv = (tmp_path / "otm-argv").read_text(encoding="utf-8")
    assert "baseline/threat-model.otm.yaml" in argv


def test_gate_worktree_mode_is_an_explicit_opt_in_that_still_works(tmp_path):
    """An adopter whose checkout cannot reach the base branch keeps a usable, documented path."""
    result = _run_gate(GIT_STUB_BASE_UNREACHABLE, {"BASELINE_REF": "worktree"}, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    argv = (tmp_path / "otm-argv").read_text(encoding="utf-8")
    assert "baseline/threat-model.otm.yaml" in argv


def test_gate_worktree_mode_says_out_loud_that_the_baseline_is_rewritable(tmp_path):
    result = _run_gate(GIT_STUB_BASE_UNREACHABLE, {"BASELINE_REF": "worktree"}, tmp_path)
    assert "::warning::" in result.stdout


def test_gate_without_a_baseline_is_still_skipped(tmp_path):
    result = _run_gate(GIT_STUB_BASE_UNREACHABLE, {"BASELINE": ""}, tmp_path)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    written = (tmp_path / "gh_output").read_text(encoding="utf-8")
    assert "outcome=skipped" in written


def test_action_declares_the_baseline_ref_input():
    assert "baseline-ref" in _load(ACTION_YML)["inputs"]


# ---------------------------------------------------------------------------------------
# The composite action must not run `python -m pip` inside the caller's checkout (finding #19)
# ---------------------------------------------------------------------------------------


def test_action_install_step_does_not_run_inside_the_callers_checkout():
    """`python -m pip` puts the CWD first on sys.path, so a `pip.py` in the caller's repo wins."""
    step = _action_step("Install open-threat-model")
    assert step.get("working-directory") != "${{ inputs.working-directory }}"


def test_action_install_step_keeps_the_cwd_off_sys_path():
    step = _action_step("Install open-threat-model")
    assert step.get("env", {}).get("PYTHONSAFEPATH") == "1"


def test_semgrep_install_keeps_the_cwd_off_sys_path():
    step = _step(SECURITY_WF, "sast-semgrep", "Install Semgrep")
    assert step.get("env", {}).get("PYTHONSAFEPATH") == "1"


# ---------------------------------------------------------------------------------------
# The evidence document must describe controls that exist (finding #4)
# ---------------------------------------------------------------------------------------

DOC_CLAIMED_CI_COMMANDS = (
    ("python", "bandit -r packages apps -ll -q"),
    ("python", "pip_audit --desc on -S ."),
    ("web", "npm audit --audit-level=moderate"),
)


def _job_run_bodies(workflow_path: pathlib.Path, job: str) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(workflow_path, job))


def test_every_ci_command_the_evidence_doc_claims_is_actually_run():
    doc = EVIDENCE_DOC.read_text(encoding="utf-8")
    missing = []
    for job, command in DOC_CLAIMED_CI_COMMANDS:
        if command not in doc:
            missing.append(f"doc no longer claims '{command}'")
        if command not in _job_run_bodies(PROJECT_WF, job):
            missing.append(f"job '{job}' does not run '{command}'")
    assert missing == [], missing


def _semgrep_configs() -> set[str]:
    body = _step(SECURITY_WF, "sast-semgrep", "Scan application and workflow code")["run"]
    return set(re.findall(r"--config (\S+)", body))


def test_semgrep_configs_match_the_evidence_doc():
    """Blockquote lines are excluded: a correction note has to be able to name what is NOT run."""
    doc = EVIDENCE_DOC.read_text(encoding="utf-8")
    section = doc.split("## 6. Semgrep", 1)[1].split("\n## ", 1)[0]
    claims = "\n".join(line for line in section.splitlines() if not line.startswith(">"))
    documented = set(re.findall(r"`(p/[a-z-]+|rules/semgrep/[\w./-]+)`", claims))
    assert documented == _semgrep_configs()


# ---------------------------------------------------------------------------------------
# The publish workflow's own hardening notes must match its permissions (finding #13)
# ---------------------------------------------------------------------------------------


def _publish_header() -> str:
    return PUBLISH_WF.read_text(encoding="utf-8").split("\nname:", 1)[0]


NO_TOKEN_CLAIMS = ("build job has no", "only `publish` can mint")


def test_publish_header_matches_the_build_job_permissions():
    can_mint = "id-token" in _load(PUBLISH_WF)["jobs"]["build"]["permissions"]
    header = _publish_header()
    contradictions = [phrase for phrase in NO_TOKEN_CLAIMS if can_mint and phrase in header]
    assert contradictions == [], f"header says the build job cannot mint an OIDC token, but it can: {contradictions}"


def test_publish_job_is_the_only_environment_bound_job():
    jobs = _load(PUBLISH_WF)["jobs"]
    assert jobs["publish"]["environment"]["name"] == "pypi"
    assert "environment" not in jobs["build"]


def test_gitleaks_reads_pull_request_commits_without_write_permissions():
    job = "secrets-history-gitleaks"
    assert _load(SECURITY_WF)["jobs"][job]["permissions"] == {"contents": "read", "pull-requests": "read"}
    checkout = _step(SECURITY_WF, job, "Checkout")["with"]
    assert checkout["fetch-depth"] == 0
    assert checkout["persist-credentials"] is False
    scan_env = _step(SECURITY_WF, job, "Scan git history for leaked secrets")["env"]
    assert scan_env["GITLEAKS_ENABLE_COMMENTS"] == "false"


# ---------------------------------------------------------------------------------------
# Executable references this repository resolves itself must be immutable (findings #14/#31)
# ---------------------------------------------------------------------------------------


def test_pre_commit_hooks_are_pinned_to_commit_shas():
    remote = [repo for repo in _load(PRE_COMMIT_CONFIG)["repos"] if repo["repo"] != "local"]
    unpinned = [repo["repo"] for repo in remote if not SHA40.match(str(repo.get("rev", "")))]
    assert unpinned == []


def test_pre_commit_pins_record_the_tag_they_were_frozen_from():
    """A bare SHA is unreadable; the tag comment is what makes the pin reviewable."""
    text = PRE_COMMIT_CONFIG.read_text(encoding="utf-8")
    assert re.search(r"# frozen: v\d+\.\d+\.\d+", text) is not None


def _workflow_uses_refs(path: pathlib.Path) -> list[str]:
    return re.findall(r"^\s*(?:- )?uses: (\S+)", path.read_text(encoding="utf-8"), re.MULTILINE)


def test_every_action_reference_stays_pinned_to_a_commit_sha():
    unpinned = []
    for path in sorted(WORKFLOWS.glob("*.yml")) + [ACTION_YML]:
        for ref in _workflow_uses_refs(path):
            if ref.startswith("./"):
                continue
            if not SHA40.match(ref.split("@", 1)[-1]):
                unpinned.append(f"{path.name}: {ref}")
    assert unpinned == []


def test_downstream_usage_snippets_warn_that_a_tag_is_mutable():
    """The snippets adopters copy are how this project models the standard it documents."""
    for path in (README, PRE_COMMIT_HOOKS):
        assert "commit SHA" in path.read_text(encoding="utf-8"), path.name


# ---------------------------------------------------------------------------------------
# A branch scanned after the merge must also be scanned before it (finding #26)
# ---------------------------------------------------------------------------------------


def test_pull_request_and_push_branch_allowlists_agree():
    for path in (SECURITY_WF, PROJECT_WF):
        triggers = _triggers(_load(path))
        assert set(triggers["pull_request"]["branches"]) == set(triggers["push"]["branches"]), path.name
