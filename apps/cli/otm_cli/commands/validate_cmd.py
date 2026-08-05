"""`validate` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from otm_core_schema.document import ThreatModelDocument
from rich.panel import Panel

from otm_cli.application.validate_service import run_validate
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("validate")
    def cmd_validate(
        paths: Annotated[list[Path], typer.Argument(help=".otm.yaml / .yml file(s).")],
    ) -> None:
        """Validate the document against the canonical schema.

        Accepts several files so batch callers — pre-commit above all, which hands a tool every
        matching path at once — do not need a shell loop. A single-file invocation is unchanged:
        same panel, same exit code, same error handling.
        """
        if len(paths) == 1:
            _validate_one_or_exit(paths[0])
            return

        failures = 0
        for path in paths:
            try:
                _print_valid(run_validate(path))
            except CliUserError as e:
                # Report every bad file rather than dying on the first: a contributor fixing a
                # batch wants the whole list, not one error per commit attempt.
                failures += 1
                console.print(f"[red]Invalid[/red] {path}: {e.failed}")
        if failures:
            raise typer.Exit(1)


def _validate_one_or_exit(path: Path) -> None:
    try:
        doc = run_validate(path)
    except CliUserError as e:
        exit_on_cli_error(console, e)
        raise  # unreachable: exit_on_cli_error always raises; narrows `doc` for the type checker
    _print_valid(doc)


def _print_valid(doc: ThreatModelDocument) -> None:
    console.print(
        Panel.fit(
            f"[green]Valid[/green]\n\n"
            f"Title: [bold]{doc.metadata.title}[/bold]\n"
            f"Schema: {doc.model_info.schema_version}\n"
            f"Components: {len(doc.components)} · Flows: {len(doc.data_flows)}",
            title="validate",
            border_style="green",
        )
    )
