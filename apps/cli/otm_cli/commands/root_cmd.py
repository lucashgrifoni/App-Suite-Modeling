"""Root callback (`--version`, default help)."""

from __future__ import annotations

from typing import Annotated

import typer

from otm_cli.commands.bootstrap import console
from otm_cli.shared.version_util import installed_version


def register(app: typer.Typer) -> None:
    @app.callback(invoke_without_command=True)
    def cli_root(
        ctx: typer.Context,
        version: Annotated[
            bool,
            typer.Option("--version", "-V", help="Print version and exit."),
        ] = False,
    ) -> None:
        """Open Threat Model CLI."""
        if version:
            console.print(f"otm (App Suite Modeling) [bold]v{installed_version()}[/bold]")
            raise typer.Exit(0)
        if ctx.invoked_subcommand is None:
            console.print(ctx.get_help())
