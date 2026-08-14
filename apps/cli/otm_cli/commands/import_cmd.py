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
from otm_cli.shared.render import safe


def _write_text_or_exit(*, content: str, output: Path, sources: tuple[Path, ...] = ()) -> None:
    """Write the file, or render the `CliUserError` and exit with its code."""
    try:
        write_text_file(content=content, output=output, sources=sources)
    except CliUserError as e:
        exit_on_cli_error(console, e)


def _write_json_or_exit(*, payload: dict[str, Any], output: Path, sources: tuple[Path, ...] = ()) -> None:
    try:
        write_json_file(payload=payload, output=output, sources=sources)
    except CliUserError as e:
        exit_on_cli_error(console, e)


def _emit_text(content: str, *, output: Path | None, label: str, sources: tuple[Path, ...] = ()) -> None:
    """Write to `output` and say where, or print to stdout so the caller can pipe it."""
    if output:
        _write_text_or_exit(content=content, output=output, sources=sources)
        console.print(f"[green]{label}[/green] → {safe(output.resolve())}")
    else:
        print(content, end="")


def _emit_draft(
    yaml_text: str,
    explain_payload: dict[str, Any] | None,
    *,
    output: Path | None,
    explain_out: Path | None,
    source: Path,
) -> None:
    """Escreve o draft `.otm.yaml` (ou imprime) e, opcionalmente, as inferências em JSON."""
    _emit_text(yaml_text, output=output, label="Draft", sources=(source,))
    if explain_out and explain_payload:
        _write_json_or_exit(payload=explain_payload, output=explain_out, sources=(source,))
        console.print(f"[green]Inferences[/green] → {safe(explain_out.resolve())}")


def _print_inference_summary(inferences: list[Any]) -> None:
    console.print(
        Panel.fit(
            "\n".join(f"• ({safe(i.confidence)}) {safe(i.message)}" for i in inferences[:12]),
            title="Inferences (summary)",
            border_style="cyan",
        )
    )


def _scanned_sources(payload: dict[str, Any]) -> tuple[Path, ...]:
    """Os ficheiros que o scan leu, para o emissor recusar escrever por cima de um deles.

    Este comando era o único do CLI a escrever sem passar `sources=`, e por isso destruía um
    ficheiro do repositório analisado segundos depois de o ler, devolvendo **exit 0** — enquanto
    `export`, `analyze`, `diff` e `backlog` recusam o caso equivalente com exit 1 e uma mensagem
    que diz porquê. Reproduzido com um `src/app.js` de um repositório Node.
    """
    root = Path(str(payload.get("root", "")))
    return tuple(root / rel for rel in payload.get("files_scanned_paths", []))


def _emit_repo_scan(payload: dict[str, Any], *, json_out: Path | None, draft_out: Path | None) -> None:
    """Write whichever artifacts were asked for; with neither, show the payload on screen."""
    sources = _scanned_sources(payload)
    if json_out:
        _write_json_or_exit(payload=payload, output=json_out, sources=sources)
        console.print(f"[green]Scan repo[/green] → {safe(json_out.resolve())}")
    if draft_out:
        yaml_text = import_app.scan_payload_to_draft_yaml(payload)
        _write_text_or_exit(content=yaml_text, output=draft_out, sources=sources)
        console.print(f"[green]Draft[/green] → {safe(draft_out.resolve())}")
    if not json_out and not draft_out:
        txt = json.dumps(payload, indent=2, ensure_ascii=False)
        console.print(Panel.fit(safe(txt[:14000]), title="repo-scan", border_style="cyan"))


def _warn_not_imported(notes: list[str]) -> None:
    """Name every category the OTM bridge left behind (stderr, so stdout stays pipeable)."""
    if not notes:
        return
    console.print("[yellow]Not imported[/yellow] (the OTM bridge converts the architecture only):")
    for note in notes:
        console.print(f"  • {safe(note)}")


def build_import_app() -> typer.Typer:
    import_cmd = typer.Typer(
        name="import",
        help=(
            "Assisted import: build a canonical [bold]draft[/bold] "
            "from artifacts (OpenAPI, Terraform, K8s) or [cyan]repo[/cyan] (Node/Express signals); "
            "or convert the architecture of an [cyan]otm[/cyan] (Open Threat Model) file "
            "(OTM threats and mitigations are not imported)."
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

        _emit_draft(yaml_text, explain_payload, output=output, explain_out=explain_out, source=spec)
        if inferences and output:
            # Only when the draft went to a file: on stdout the panel would corrupt the YAML.
            _print_inference_summary(inferences)

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
            yaml_text, explain_payload, inferences = import_app.import_terraform(target)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_draft(yaml_text, explain_payload, output=output, explain_out=explain_out, source=target)
        if inferences and output:
            # Same rule as `import openapi`: the caveats are shown only when the draft went to a
            # file, because on stdout the panel would corrupt the YAML the caller is piping.
            _print_inference_summary(inferences)

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
            yaml_text, explain_payload, inferences = import_app.import_kubernetes(target)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_draft(yaml_text, explain_payload, output=output, explain_out=explain_out, source=target)
        if inferences and output:
            # Same rule as `import openapi`: the caveats are shown only when the draft went to a
            # file, because on stdout the panel would corrupt the YAML the caller is piping.
            _print_inference_summary(inferences)

    @import_cmd.command("otm")
    def cmd_import_otm(
        spec: Annotated[Path, typer.Argument(help="Open Threat Model (OTM 0.2.0) file (YAML or JSON).")],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write canonical `.otm.yaml`."),
        ] = None,
    ) -> None:
        """Convert the architecture of an Open Threat Model (IriusRisk OTM) file.

        The bridge carries project, trust zones, components, dataflows and assets. OTM
        `threats`/`mitigations` and its 0-100 risk attributes have no canonical equivalent, so
        anything left behind is listed on stderr rather than silently dropped.
        """
        try:
            yaml_text, not_imported = import_app.import_otm(spec)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        _emit_text(yaml_text, output=output, label="Imported OTM", sources=(spec,))
        _warn_not_imported(not_imported)

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

        _emit_repo_scan(payload, json_out=json_out, draft_out=draft_out)

    return import_cmd
