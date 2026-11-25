"""Root callback (`--version`, default help)."""

from __future__ import annotations

from typing import Annotated

import typer

from otm_cli.commands.bootstrap import console
from otm_cli.shared.render import safe
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
            console.print(f"otm (App Suite Modeling) [bold]v{safe(installed_version())}[/bold]")
            raise typer.Exit(0)
        if ctx.invoked_subcommand is None:  # pragma: no cover - app has no_args_is_help; typer shows help before this
            console.print(ctx.get_help())
