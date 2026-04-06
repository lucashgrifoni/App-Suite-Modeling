"""`explain` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from otm_cli.application.explain_service import run_explain
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("explain")
    def cmd_explain(
        path: Annotated[
            Path,
            typer.Argument(help="`analysis.json` (otm analyze --json-out) or compare JSON."),
        ],
        kind: str = typer.Option(
            "analysis",
            "--from",
            "-f",
            help="Kind: analysis | compare",
        ),
        category: str | None = typer.Option(
            None,
            "--category",
            "-c",
            help="Filter by explanation category (e.g. risk, methodology, ai_modeling).",
        ),
        limit: int = typer.Option(25, "--limit", "-n", help="Maximum lines."),
    ) -> None:
        """Print structured explainability from JSON produced by the CLI/API."""
        try:
            rows = run_explain(path, kind=kind, category=category, limit=limit)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if not rows:
            if category:
                console.print("[yellow]No explanations for the given filter.[/yellow]")
            else:
                console.print("[yellow]No explanations in this file.[/yellow]")
            raise typer.Exit(0)

        for cat, subj, msg in rows:
            console.print(f"[cyan]{cat}[/cyan] · {subj} — {msg}")
