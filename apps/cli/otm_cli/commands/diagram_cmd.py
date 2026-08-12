"""`diagram` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from otm_cli.application.diagram_service import run_diagram
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_text_file
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("diagram")
    def cmd_diagram(
        path: Annotated[Path, typer.Argument(help=".otm.yaml file.")],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help=".mmd file (default: stdout)."),
        ] = None,
    ) -> None:
        """Emit Mermaid flowchart for components and data flows."""
        try:
            text = run_diagram(path)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        if output:
            try:
                write_text_file(content=text, output=output)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Diagram[/green] → {safe(output.resolve())}")
        else:
            print(text, end="")
