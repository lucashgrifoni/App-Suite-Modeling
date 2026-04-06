"""Render `CliUserError` as Typer output."""

from __future__ import annotations

import typer
from rich.console import Console

from otm_cli.shared.errors import CliUserError


def exit_on_cli_error(console: Console, exc: CliUserError) -> None:
    console.print(
        f"[red]Failure:[/red] {exc.failed}\n"
        f"[yellow]Likely cause:[/yellow] {exc.cause}\n"
        f"[cyan]Next step:[/cyan] {exc.next_step}"
    )
    if exc.validation_detail:
        console.print(f"[red]\n{exc.validation_detail}[/red]")
    raise typer.Exit(exc.exit_code) from exc
