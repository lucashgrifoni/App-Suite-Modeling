"""Round-2 regression: `import terraform` and `import k8s` printed no inference summary.

Running the three command lines exactly as `docs/features/ARTIFACT_IMPORT.md` gives them,
`otm import openapi` showed an "Inferences (summary)" panel with its caveats while the terraform
and k8s siblings printed only the draft path — despite producing inference records of their own.
The records were not lost (they are mirrored into `business_context.assumptions` of the draft),
but the operator following the documented line saw nothing on the terminal for two of the three
importers. Both commands already bound the value and threw it away.

The panel is shown only when the draft went to a *file*, matching `import openapi`: on stdout it
would corrupt the YAML the caller is piping.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from typer.testing import CliRunner

_SUMMARY_TITLE = "Inferences"

_TERRAFORM = """
resource "aws_s3_bucket" "logs" {
  bucket = "my-logs"
}
resource "aws_security_group" "open" {
  ingress {
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""

_K8S = """
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
  - port: 80
"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


@pytest.fixture
def terraform_import(runner: CliRunner, tmp_path: Path) -> Result:
    source = tmp_path / "infra.tf"
    source.write_text(_TERRAFORM, encoding="utf-8")
    return runner.invoke(app, ["import", "terraform", str(source), "-o", str(tmp_path / "draft.otm.yaml")])


@pytest.fixture
def k8s_import(runner: CliRunner, tmp_path: Path) -> Result:
    source = tmp_path / "manifests.yaml"
    source.write_text(_K8S, encoding="utf-8")
    return runner.invoke(app, ["import", "k8s", str(source), "-o", str(tmp_path / "draft.otm.yaml")])


def test_terraform_import_succeeds(terraform_import: Result) -> None:
    assert terraform_import.exit_code == 0


def test_terraform_import_shows_its_inference_summary(terraform_import: Result) -> None:
    assert _SUMMARY_TITLE in _out(terraform_import)


def test_kubernetes_import_succeeds(k8s_import: Result) -> None:
    assert k8s_import.exit_code == 0


def test_kubernetes_import_shows_its_inference_summary(k8s_import: Result) -> None:
    assert _SUMMARY_TITLE in _out(k8s_import)


def test_terraform_import_to_stdout_stays_pipeable(runner: CliRunner, tmp_path: Path) -> None:
    """Without `-o` the draft IS the stdout payload; a panel would corrupt the YAML."""
    source = tmp_path / "infra.tf"
    source.write_text(_TERRAFORM, encoding="utf-8")

    result = runner.invoke(app, ["import", "terraform", str(source)])

    assert _SUMMARY_TITLE not in _out(result)


def test_the_draft_cannot_be_written_over_the_manifest_it_came_from(runner: CliRunner, tmp_path: Path) -> None:
    source = tmp_path / "manifests.yaml"
    source.write_text(_K8S, encoding="utf-8")
    before = source.read_bytes()

    runner.invoke(app, ["import", "k8s", str(source), "-o", str(source)])

    assert source.read_bytes() == before
