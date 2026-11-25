"""Resource identity in a Terraform configuration with local modules."""

from pathlib import Path

from otm_artifact_import.terraform_import import import_terraform_path
from otm_cli.cli import app
from typer.testing import CliRunner


def _write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_module_calls_preserve_distinct_resources_and_flows(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "main.tf",
        'resource "aws_lb" "catalog" {}\n'
        'module "storefront" { source = "./catalog" }\n'
        'module "internal" { source = "./catalog" }\n',
    )
    _write(
        tmp_path,
        "catalog/main.tf",
        'resource "aws_lb" "catalog" { cidr_blocks = ["0.0.0.0/0"] }\nmodule "storage" { source = "../storage" }\n',
    )
    _write(tmp_path, "storage/main.tf", 'resource "aws_s3_bucket" "catalog" {}')
    draft = import_terraform_path(tmp_path).document
    ids = {c.name: c.id for c in draft.components if c.technology}
    assert set(ids) == {
        "aws_lb.catalog",
        "module.storefront.aws_lb.catalog",
        "module.internal.aws_lb.catalog",
        "module.storefront.module.storage.aws_s3_bucket.catalog",
        "module.internal.module.storage.aws_s3_bucket.catalog",
    }
    assert len(set(ids.values())) == len(ids)
    assert ids["aws_lb.catalog"] == "aws_lb_catalog"
    assert {f.to_component for f in draft.data_flows} == {
        ids["module.storefront.aws_lb.catalog"],
        ids["module.internal.aws_lb.catalog"],
    }


def test_module_ids_survive_reordering_and_moving_files(tmp_path: Path) -> None:
    root = tmp_path / "project"
    prefix = "catalog_" + "a" * 49
    calls = [
        f'module "{prefix}_east" {{ source = "./shared" }}',
        f'module "{prefix}_west" {{ source = "./shared" }}',
    ]
    root_file = _write(root, "first.tf", "\n".join(calls))
    child_file = _write(root, "shared/lb.tf", 'resource "aws_lb" "catalog" { cidr_blocks = ["0.0.0.0/0"] }')
    original = import_terraform_path(root).document
    assert len(original.components) == 3
    assert len(original.data_flows) == 2

    child_file.rename(child_file.with_name("renamed.tf"))
    root_file.write_text("\n".join(reversed(calls)), encoding="utf-8")
    _write(root, "unrelated.tf", 'resource "aws_s3_bucket" "unrelated" {}')
    relocated = root.rename(tmp_path / "relocated")
    revised = import_terraform_path(relocated).document
    before = {c.name: c.id for c in original.components}
    after = {c.name: c.id for c in revised.components}
    assert {name: after[name] for name in before} == before
    assert {f.to_component: f.id for f in original.data_flows} == {f.to_component: f.id for f in revised.data_flows}


def test_only_declared_local_modules_inside_the_project_are_followed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write(
        root,
        "main.tf",
        """
# module "comment" { source = "./unused" }
locals {
  label = "${format("braces { %s", "value")}"
  text = <<EOF
module "heredoc" { source = "./unused" }
EOF
}
module "outside" { source = "../sibling" }
module "registry" { source = "example/catalog/aws" }
module "inside" { source = "./used" }
""",
    )
    _write(root, "unused/main.tf", 'resource "aws_s3_bucket" "unused" {}')
    _write(root, "used/main.tf", 'resource "aws_s3_bucket" "local" {}\nmodule "cycle" { source = "../used" }')
    _write(tmp_path, "sibling/main.tf", 'resource "aws_s3_bucket" "outside" {}')
    result = import_terraform_path(root)
    assert {c.name for c in result.document.components if c.technology} == {"module.inside.aws_s3_bucket.local"}
    for module in ("module.outside", "module.registry", "module.inside.module.cycle"):
        assert any(module in note for note in result.unknowns)


def test_cli_refuses_to_overwrite_a_child_module_input(tmp_path: Path) -> None:
    source = 'resource "aws_s3_bucket" "catalog" {}'
    _write(tmp_path, "main.tf", 'module "catalog" { source = "./catalog" }')
    child = _write(tmp_path, "catalog/main.tf", source)
    result = CliRunner().invoke(app, ["import", "terraform", str(tmp_path), "-o", str(child)])
    assert result.exit_code == 1, result.output
    assert child.read_text(encoding="utf-8") == source
