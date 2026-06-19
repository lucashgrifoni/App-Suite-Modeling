"""`import` command group."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.panel import Panel

from otm_cli.application import import_service as import_app
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file, write_text_file
from otm_cli.shared.errors import CliUserError


def _emit_draft(
    yaml_text: str,
    explain_payload: dict[str, Any] | None,
    *,
    output: Path | None,
    explain_out: Path | None,
) -> None:
    """Escreve o draft `.otm.yaml` (ou imprime) e, opcionalmente, as inferências em JSON."""
    if output:
        try:
            write_text_file(content=yaml_text, output=output)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        console.print(f"[green]Draft[/green] → {output.resolve()}")
    else:
        print(yaml_text, end="")
    if explain_out and explain_payload:
        try:
            write_json_file(payload=explain_payload, output=explain_out)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        console.print(f"[green]Inferences[/green] → {explain_out.resolve()}")


def build_import_app() -> typer.Typer:
    import_cmd = typer.Typer(
        name="import",
        help=(
            "Assisted import: build a canonical [bold]draft[/bold] "
            "from artifacts (OpenAPI, Terraform, K8s) or [cyan]repo[/cyan] (Node/Express signals); "
            "or convert an [cyan]otm[/cyan] (Open Threat Model) file losslessly."
        ),
        no_args_is_help=True,
    )

    @import_cmd.command("openapi")
    def cmd_import_openapi(
        spec: Annotated[Path, typer.Argument(help="OpenAPI/Swagger file (YAML or JSON).")],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write draft `.otm.yaml`."),
        ] = None,
        explain_out: Annotated[
            Path | None,
            typer.Option(
                "--explain-out",
                help="Write document + inferences + unknowns to JSON (transparency).",
            ),
        ] = None,
    ) -> None:
        """Draft from OpenAPI 3 or Swagger 2 specification."""
        try:
            yaml_text, explain_payload, inferences = import_app.import_openapi(spec)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_draft(yaml_text, explain_payload, output=output, explain_out=explain_out)
        if inferences and output:
            console.print(
                Panel.fit(
                    "\n".join(f"• ({i.confidence}) {i.message}" for i in inferences[:12]),
                    title="Inferences (summary)",
                    border_style="cyan",
                )
            )

    @import_cmd.command("terraform")
    def cmd_import_terraform(
        target: Annotated[Path, typer.Argument(help="`.tf` file or directory containing `.tf`.")],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write draft `.otm.yaml`."),
        ] = None,
        explain_out: Annotated[
            Path | None,
            typer.Option("--explain-out", help="JSON with structured inferences."),
        ] = None,
    ) -> None:
        """Draft from Terraform resources (conservative parser)."""
        try:
            yaml_text, explain_payload, _inf = import_app.import_terraform(target)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_draft(yaml_text, explain_payload, output=output, explain_out=explain_out)

    @import_cmd.command("k8s")
    def cmd_import_k8s(
        target: Annotated[
            Path,
            typer.Argument(help="Multi-doc YAML or directory with `.yaml`/`.yml`."),
        ],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write draft `.otm.yaml`."),
        ] = None,
        explain_out: Annotated[
            Path | None,
            typer.Option("--explain-out", help="JSON with structured inferences."),
        ] = None,
    ) -> None:
        """Draft from Kubernetes manifests."""
        try:
            yaml_text, explain_payload, _inf = import_app.import_kubernetes(target)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_draft(yaml_text, explain_payload, output=output, explain_out=explain_out)

    @import_cmd.command("otm")
    def cmd_import_otm(
        spec: Annotated[Path, typer.Argument(help="Open Threat Model (OTM 0.2.0) file (YAML or JSON).")],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write canonical `.otm.yaml`."),
        ] = None,
    ) -> None:
        """Convert an Open Threat Model (IriusRisk OTM) file into the canonical format."""
        try:
            yaml_text = import_app.import_otm(spec)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if output:
            try:
                write_text_file(content=yaml_text, output=output)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Imported OTM[/green] → {output.resolve()}")
        else:
            print(yaml_text, end="")

    @import_cmd.command("repo")
    def cmd_import_repo(
        root: Annotated[Path, typer.Argument(help="Repository root (e.g. Node/Express service).")],
        json_out: Annotated[
            Path | None,
            typer.Option("--json-out", help="Write JSON with inferences and corpus excerpt."),
        ] = None,
        draft_out: Annotated[
            Path | None,
            typer.Option(
                "--draft-out",
                help=(
                    "Emit a minimal `.otm.yaml` seed derived from the scan, "
                    "chainable into `otm validate` / `otm analyze`."
                ),
            ),
        ] = None,
    ) -> None:
        """Pragmatic scan: routes, upload, session, external fetch, eval."""
        try:
            payload = import_app.scan_repo(root)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            try:
                write_json_file(payload=payload, output=json_out)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Scan repo[/green] → {json_out.resolve()}")
        if draft_out:
            yaml_text = import_app.scan_payload_to_draft_yaml(payload)
            try:
                write_text_file(content=yaml_text, output=draft_out)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Draft[/green] → {draft_out.resolve()}")
        if not json_out and not draft_out:
            txt = json.dumps(payload, indent=2, ensure_ascii=False)
            console.print(Panel.fit(txt[:14000], title="repo-scan", border_style="cyan"))

    return import_cmd
