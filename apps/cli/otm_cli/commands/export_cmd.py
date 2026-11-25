"""`export` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from otm_cli.application.export_service import run_export
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_text_file
from otm_cli.shared.enums import ExportFormat
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("export")
    def cmd_export(
        path: Annotated[Path, typer.Argument(help=".otm.yaml file.")],
        export_format: Annotated[
            ExportFormat,
            typer.Option("--format", "-f", help="Output format."),
        ] = ExportFormat.yaml,
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Output file (default: stdout)."),
        ] = None,
    ) -> None:
        """Export the validated model (YAML, JSON, or Markdown)."""
        try:
            text = run_export(path, export_format=export_format)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        if output:
            try:
                write_text_file(content=text, output=output, sources=(path,))
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Exported[/green] → {safe(output.resolve())}")
        else:
            print(text, end="")
