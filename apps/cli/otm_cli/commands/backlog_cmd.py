"""`backlog` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from otm_cli.application.backlog_service import run_backlog
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import input_paths, write_text_file
from otm_cli.shared.enums import BacklogFormat, BacklogGroupBy
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("backlog")
    def cmd_backlog(
        path: Annotated[
            Path,
            typer.Argument(help="`.otm.yaml` / `.yml` model or `analysis.json` file."),
        ],
        document: Annotated[
            Path | None,
            typer.Option(
                "--document",
                "-d",
                help=("With a `.json` path: YAML model to resolve component names (recommended)."),
            ),
        ] = None,
        fmt: BacklogFormat = typer.Option(
            BacklogFormat.markdown,
            "--format",
            "-f",
            help="markdown | json",
        ),
        group_by: BacklogGroupBy | None = typer.Option(
            None,
            "--group-by",
            help="Markdown grouping: root-cause | control | category.",
        ),
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write output; default stdout."),
        ] = None,
        pack: str | None = typer.Option(
            None,
            "--pack",
            "-p",
            help="Pack when `path` is a YAML model (runs the engine).",
        ),
    ) -> None:
        """Remediation backlog from the model or analysis JSON."""
        try:
            text = run_backlog(path, document=document, pack=pack, fmt=fmt, group_by=group_by)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if output:
            try:
                write_text_file(content=text, output=output, sources=input_paths(path, document))
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Backlog[/green] → {safe(output.resolve())}")
        else:
            print(text, end="")
