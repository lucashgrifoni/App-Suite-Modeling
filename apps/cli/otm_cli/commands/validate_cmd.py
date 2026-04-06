"""`validate` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from otm_cli.application.validate_service import run_validate
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("validate")
    def cmd_validate(
        path: Annotated[Path, typer.Argument(help=".otm.yaml / .yml file.")],
    ) -> None:
        """Validate the document against the canonical schema."""
        try:
            doc = run_validate(path)
        except CliUserError as e:
            exit_on_cli_error(console, e)
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
