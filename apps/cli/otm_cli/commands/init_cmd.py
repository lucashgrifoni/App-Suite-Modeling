"""`init` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from otm_cli.application.init_service import InitResult, run_init
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def _emit_template_list() -> None:
    """Lista templates embutidos (saída idêntica ao fluxo `--list-templates`)."""
    from otm_cli.application import templates_service as tmpl

    infos = tmpl.list_template_infos()
    console.print("[bold]Templates[/bold] (use: [cyan]otm init -t ID[/cyan]):")
    for info in infos:
        console.print(f"  • [cyan]{safe(info.id)}[/cyan] — {safe(info.title)}")
        if info.suggested_pack:
            console.print(f"    suggested pack: {safe(info.suggested_pack)}")
        if info.complexity:
            console.print(f"    complexity: {safe(info.complexity)}")
        if info.category_label:
            console.print(f"    category: {safe(info.category_label)}")


def _emit_init_result(res: InitResult) -> None:
    """Mensagem final após criar o ficheiro (template vs blank)."""
    if res.message_key == "template":
        console.print(f"[green]Template[/green] [cyan]{safe(res.template_id)}[/cyan] → {safe(res.path.resolve())}")
        if res.suggested_pack:
            console.print(f"Suggestion: [cyan]otm analyze {safe(res.path)} --pack {safe(res.suggested_pack)}[/cyan]")
        else:
            console.print(f"Next step: [cyan]otm validate {safe(res.path)}[/cyan]")
    else:
        console.print(
            f"[green]Created[/green] {safe(res.path.resolve())}\n"
            f"Next step: [cyan]otm validate {safe(res.path)}[/cyan] "
            "(or [cyan]otm init -t saas-web[/cyan])"
        )


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
        if list_templates:
            _emit_template_list()
            raise typer.Exit(0)

        try:
            res = run_init(path, force=force, template=template)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_init_result(res)
