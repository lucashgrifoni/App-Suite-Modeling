"""
CLI — Typer bootstrap: command registration and sub-apps.

Business orchestration lives in `otm_cli.application`; terminal I/O in `otm_cli.commands`.
"""

from __future__ import annotations

import typer

from otm_cli.commands import (
    analyze_cmd,
    backlog_cmd,
    diagram_cmd,
    diff_analysis_cmd,
    diff_cmd,
    explain_cmd,
    export_cmd,
    import_cmd,
    init_cmd,
    packs_cmd,
    precheck_cmd,
    recommend_cmd,
    report_cmd,
    root_cmd,
    templates_cmd,
    validate_cmd,
)

app = typer.Typer(
    name="otm",
    help=(
        "[bold]App Suite Modeling[/bold] — Threat Modeling as Code from the command line.\n\n"
        "Main commands: [cyan]init[/cyan], [cyan]import[/cyan], "
        "[cyan]validate[/cyan], [cyan]precheck[/cyan], [cyan]diff[/cyan], "
        "[cyan]analyze[/cyan] ([cyan]--explain[/cyan]), [cyan]explain[/cyan], "
        "[cyan]backlog[/cyan], [cyan]report[/cyan], "
        "[cyan]diagram[/cyan], [cyan]export[/cyan], "
        "[cyan]templates[/cyan], [cyan]packs[/cyan]."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

root_cmd.register(app)
init_cmd.register(app)
validate_cmd.register(app)
precheck_cmd.register(app)
analyze_cmd.register(app)
explain_cmd.register(app)
export_cmd.register(app)
diagram_cmd.register(app)
backlog_cmd.register(app)
diff_cmd.register(app)
diff_analysis_cmd.register(app)
recommend_cmd.register(app)
report_cmd.register(app)
packs_cmd.register(app)

app.add_typer(import_cmd.build_import_app())
app.add_typer(templates_cmd.build_templates_app(), name="templates")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
