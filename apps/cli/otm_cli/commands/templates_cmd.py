"""`templates` command group."""

from __future__ import annotations

import typer
from rich.panel import Panel

from otm_cli.application import templates_service as tmpl
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError


def build_templates_app() -> typer.Typer:
    templates_app = typer.Typer(
        name="templates",
        help="Embedded template catalog (list, filters, detail).",
    )

    @templates_app.callback(invoke_without_command=True)
    def templates_callback(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
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

    @templates_app.command("list")
    def cmd_templates_list(
        category: str | None = typer.Option(None, "--category", "-c", help="Filter by category key."),
        tag: str | None = typer.Option(None, "--tag", help="Exact tag (case-insensitive)."),
        complexity: str | None = typer.Option(
            None,
            "--complexity",
            help="low | medium | high",
        ),
        q: str | None = typer.Option(None, "--query", "-q", help="Free text (id, title, description, tags)."),
    ) -> None:
        """List templates with optional filters."""
        infos = tmpl.list_template_infos(category=category, tag=tag, complexity=complexity, q=q)
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

    @templates_app.command("show")
    def cmd_templates_show(
        template_id: str = typer.Argument(..., help="Template ID (e.g. ai-rag-enterprise)."),
    ) -> None:
        """Show metadata for an embedded template."""
        try:
            text, tid = tmpl.get_template_detail(template_id)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        console.print(Panel.fit(text, title=f"template [cyan]{tid}[/cyan]", border_style="cyan"))

    return templates_app
