"""`diff` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from otm_cli.application.diff_service import run_model_diff
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("diff")
    def cmd_diff(
        baseline: Annotated[Path, typer.Argument(help="Previous version (baseline) .otm.yaml.")],
        revised: Annotated[Path, typer.Argument(help="New version (revised) .otm.yaml.")],
        json_out: Path | None = typer.Option(
            None,
            "--json-out",
            help="Write result to JSON.",
        ),
        fmt: DiffFormat = typer.Option(
            DiffFormat.text,
            "--format",
            "-f",
            help="text | json | markdown",
        ),
        with_analysis: bool = typer.Option(
            False,
            "--with-analysis",
            help="Run the engine on both YAML files and include risk/heuristic delta.",
        ),
        pack: str | None = typer.Option(
            None,
            "--pack",
            "-p",
            help="Industry pack when --with-analysis is set.",
        ),
        summary_only: bool = typer.Option(
            False,
            "--summary-only",
            help="Show only summary and key insights (text/markdown).",
        ),
    ) -> None:
        """Compare two threat model versions."""
        try:
            out_payload, json_print, md_text, panel_text = run_model_diff(
                baseline,
                revised,
                with_analysis=with_analysis,
                pack=pack,
                fmt=fmt,
                summary_only=summary_only,
            )
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            try:
                write_json_file(payload=out_payload, output=json_out)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Diff written to[/green] {json_out.resolve()}")
        if fmt == DiffFormat.json:
            body = json_print or ""
            print(body, end="" if body.endswith("\n") else "\n")
            return
        if fmt == DiffFormat.markdown:
            print(md_text or "", end="")
            return
        if summary_only:
            console.print(Panel(panel_text or "", title="diff (summary)", border_style="blue"))
            return
        console.print(Panel(panel_text or "", title="diff", border_style="blue"))
