"""`init` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from otm_cli.application.init_service import run_init
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("init")
    def cmd_init(
        path: Annotated[
            Path,
            typer.Argument(help="File to create (e.g. model.otm.yaml)."),
        ] = Path("threatmodel.otm.yaml"),
        force: bool = typer.Option(False, "--force", "-f", help="Overwrite if the file exists."),
        template: str | None = typer.Option(
            None,
            "--template",
            "-t",
            help="Embedded template (IDs from [cyan]otm templates[/cyan]).",
        ),
        list_templates: bool = typer.Option(
            False,
            "--list-templates",
            help="List templates and exit.",
        ),
    ) -> None:
        """Create a minimal OTM file or one from an embedded template."""
        from otm_cli.application import templates_service as tmpl

        if list_templates:
            infos = tmpl.list_template_infos()
            console.print("[bold]Templates[/bold] (use: [cyan]otm init -t ID[/cyan]):")
            for info in infos:
                line = f"  • [cyan]{info.id}[/cyan] — {info.title}"
                console.print(line)
                if info.suggested_pack:
                    console.print(f"    suggested pack: {info.suggested_pack}")
                if info.complexity:
                    console.print(f"    complexity: {info.complexity}")
                if info.category_label:
                    console.print(f"    category: {info.category_label}")
            raise typer.Exit(0)

        try:
            res = run_init(path, force=force, template=template)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if res.message_key == "template":
            console.print(f"[green]Template[/green] [cyan]{res.template_id}[/cyan] → {res.path.resolve()}")
            if res.suggested_pack:
                console.print(f"Suggestion: [cyan]otm analyze {res.path} --pack {res.suggested_pack}[/cyan]")
            else:
                console.print(f"Next step: [cyan]otm validate {res.path}[/cyan]")
        else:
            console.print(
                f"[green]Created[/green] {res.path.resolve()}\n"
                f"Next step: [cyan]otm validate {res.path}[/cyan] "
                "(or [cyan]otm init -t saas-web[/cyan])"
            )
