"""
CLI principal — comandos finos sobre `otm_core_schema`, motor e exportadores.

Arquitetura: este módulo só orquestra I/O de terminal; regras no core e no motor.
"""

from __future__ import annotations

import importlib.metadata
import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from otm_core_schema import dump_document_to_yaml
from otm_diagram_engine import export_flowchart_mermaid
from otm_exporters import export_document_json, export_document_markdown
from otm_framework_mappings import framework_display_name
from otm_industry_packs.loader import (
    list_pack_ids,
    list_template_ids,
    load_pack,
    load_template_info,
    load_template_yaml,
)
from otm_threat_engine import analyze_document
from otm_threat_engine.methodologies import recommend_methodology
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from otm_cli.io_util import format_validation_error, load_doc
from otm_cli.reporting import export_full_report_markdown

console = Console(stderr=True)

app = typer.Typer(
    name="otm",
    help=(
        "[bold]App Suite Modeling[/bold] — Threat Modeling as Code na linha de comando.\n\n"
        "Comandos principais: [cyan]init[/cyan], [cyan]validate[/cyan], [cyan]analyze[/cyan], "
        "[cyan]report[/cyan], [cyan]diagram[/cyan], [cyan]export[/cyan], "
        "[cyan]templates[/cyan], [cyan]packs[/cyan]."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

INIT_TEMPLATE = """# Gerado por: otm init
model:
  schema_version: "1.0.0"
  system_type: web_application
  industry_sector: generic

metadata:
  title: "Novo threat model"
  summary: "Edite este arquivo e rode: otm validate ."

trust_boundaries: []

components: []

data_flows: []

assets: []
threats: []
mitigations: []
evidence_suggestions: []
"""

_SCHEMA_INVALID_CAUSE = "o documento não é válido no schema canônico."


def _installed_version() -> str:
    try:
        return importlib.metadata.version("open-threat-model")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


def _print_cli_error(*, failed: str, cause: str, next_step: str) -> None:
    console.print(
        f"[red]Falha:[/red] {failed}\n"
        f"[yellow]Possível causa:[/yellow] {cause}\n"
        f"[cyan]Próximo passo:[/cyan] {next_step}"
    )


@app.callback(invoke_without_command=True)
def cli_root(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Mostra a versão e sai."),
    ] = False,
) -> None:
    """Open Threat Model CLI."""
    if version:
        console.print(f"otm (App Suite Modeling) [bold]v{_installed_version()}[/bold]")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("init")
def cmd_init(
    path: Annotated[
        Path,
        typer.Argument(help="Arquivo a criar (ex.: modelo.otm.yaml)."),
    ] = Path("threatmodel.otm.yaml"),
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescreve se já existir."),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Template embutido (IDs em [cyan]otm templates[/cyan]).",
    ),
    list_templates: bool = typer.Option(
        False,
        "--list-templates",
        help="Lista templates e sai.",
    ),
) -> None:
    """Cria um arquivo OTM mínimo ou a partir de um template embutido."""
    if list_templates:
        _print_templates_list()
        raise typer.Exit(0)

    if path.exists() and not force:
        console.print(
            f"[yellow]Já existe:[/yellow] {path}\n"
            "Use [cyan]--force[/cyan] para substituir ou escolha outro nome."
        )
        raise typer.Exit(code=1)

    if template:
        try:
            body = load_template_yaml(template)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1) from e
        path.write_text(body, encoding="utf-8")
        console.print(f"[green]Template[/green] [cyan]{template}[/green] → {path.resolve()}")
        info = load_template_info(template)
        if info and info.suggested_pack:
            console.print(
                "Sugestão: "
                f"[cyan]otm analyze {path} --pack {info.suggested_pack}[/cyan]"
            )
        else:
            console.print(f"Próximo passo: [cyan]otm validate {path}[/cyan]")
    else:
        path.write_text(INIT_TEMPLATE, encoding="utf-8")
        console.print(
            f"[green]Criado[/green] {path.resolve()}\n"
            f"Próximo passo: [cyan]otm validate {path}[/cyan] "
            "(ou [cyan]otm init -t saas-web[/cyan])"
        )


def _print_templates_list() -> None:
    console.print("[bold]Templates[/bold] (use: [cyan]otm init -t ID[/cyan]):")
    for tid in list_template_ids():
        info = load_template_info(tid)
        if info:
            line = f"  • [cyan]{tid}[/cyan] — {info.title}"
            console.print(line)
            if info.suggested_pack:
                console.print(f"    pack sugerido: {info.suggested_pack}")
        else:
            console.print(f"  • [cyan]{tid}[/cyan]")


@app.command("templates")
def cmd_templates() -> None:
    """Lista templates embutidos."""
    _print_templates_list()


@app.command("packs")
def cmd_packs() -> None:
    """Lista industry packs embutidos."""
    console.print("[bold]Industry packs[/bold] (use: [cyan]otm analyze --pack ID[/cyan]):")
    for pid in list_pack_ids():
        console.print(f"  • {pid}")


@app.command("recommend-methodology")
def cmd_recommend_methodology(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
) -> None:
    """Sugere metodologia principal com base no contexto do modelo."""
    try:
        doc = load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=f"recomendação de metodologia para `{path}`.",
            cause=_SCHEMA_INVALID_CAUSE,
            next_step="execute `otm validate` e corrija o documento.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=f"leitura do arquivo `{path}` para recomendação.",
            cause=str(e),
            next_step="confirme o caminho e a integridade do YAML.",
        )
        raise typer.Exit(1) from e

    rec = recommend_methodology(doc)
    console.print(
        Panel.fit(
            f"Metodologia sugerida: [bold]{rec.methodology.value}[/bold]\n\n"
            f"Motivo: {rec.reason}",
            title="recommend-methodology",
            border_style="magenta",
        )
    )


@app.command("validate")
def cmd_validate(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml / .yml.")],
) -> None:
    """Valida o documento contra o schema canônico."""
    try:
        doc = load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=f"validação do arquivo `{path}`.",
            cause="o conteúdo não segue o schema canônico.",
            next_step="corrija os campos listados abaixo e execute `otm validate` novamente.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=f"leitura do arquivo `{path}`.",
            cause=str(e),
            next_step="confirme o caminho, o YAML e permissões do arquivo.",
        )
        raise typer.Exit(1) from e

    console.print(
        Panel.fit(
            f"[green]Válido[/green]\n\n"
            f"Título: [bold]{doc.metadata.title}[/bold]\n"
            f"Schema: {doc.model_info.schema_version}\n"
            f"Componentes: {len(doc.components)} · Fluxos: {len(doc.data_flows)}",
            title="validate",
            border_style="green",
        )
    )


@app.command("analyze")
def cmd_analyze(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Só código de saída; sem resumo."),
    json_out: Path | None = typer.Option(
        None,
        "--json-out",
        help="Grava o resultado completo da análise em JSON.",
    ),
    pack: str | None = typer.Option(
        None,
        "--pack",
        "-p",
        help="Industry pack (veja [cyan]otm packs[/cyan]).",
    ),
    methodology: MethodologyOption | None = typer.Option(
        None,
        "--methodology",
        "-m",
        help=(
            "Metodologia/engine (stride, linddun, nist_data_centric, "
            "octave_allegro, cia_die, pasta, plot4ai)."
        ),
    ),
    auto_methodology: bool = typer.Option(
        False,
        "--auto-methodology",
        help="Se não houver metodologia explícita, aplica recomendação automática.",
    ),
) -> None:
    """Executa o motor (STRIDE heurístico, fronteiras, risco L×I, pack opcional)."""
    try:
        doc = load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=f"análise do arquivo `{path}`.",
            cause="o documento não passou na validação de schema.",
            next_step="execute `otm validate` e corrija os erros antes de analisar.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=f"carregamento do arquivo `{path}` para análise.",
            cause=str(e),
            next_step="valide o caminho do arquivo e o formato YAML.",
        )
        raise typer.Exit(1) from e

    pack_def = None
    if pack:
        try:
            pack_def = load_pack(pack)
        except FileNotFoundError as e:
            _print_cli_error(
                failed=f"carregamento do pack `{pack}`.",
                cause=str(e),
                next_step="execute `otm packs` e use um ID listado.",
            )
            raise typer.Exit(1) from e

    result = analyze_document(
        doc,
        pack=pack_def,
        methodology=methodology.value if methodology else None,
        auto_recommend=auto_methodology,
    )
    if json_out:
        payload = result.model_dump(mode="json")
        json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        if not quiet:
            console.print(f"[green]Análise gravada em[/green] {json_out.resolve()}")

    if quiet:
        raise typer.Exit(0)

    s = result.summary
    pack_line = ""
    if result.industry_pack_id:
        pack_line = f"Pack: {result.industry_pack_id} · ameaças pack: {s.pack_threats_generated}\n"
    fw_line = ""
    if s.framework_ref_counts_by_catalog:
        bits = [
            f"{framework_display_name(k)}: {v}"
            for k, v in sorted(s.framework_ref_counts_by_catalog.items())
        ]
        fw_line = "Refs por framework: " + " · ".join(bits) + "\n"
    console.print(
        Panel.fit(
            f"[bold]{result.document_title}[/bold]\n\n"
            f"{pack_line}"
            f"{fw_line}"
            f"Avisos estruturais: {s.structural_findings}\n"
            f"Metodologia: {result.methodology.value}\n"
            f"Fluxos entre fronteiras: {s.trust_boundary_findings}\n"
            f"Heurísticas base: {s.heuristic_threats_generated} novas · "
            f"{s.heuristic_threats_skipped_duplicate} já cobertas\n"
            f"Maior score (L×I): {s.max_risk_score!s}\n"
            f"Motor: {result.engine_version}",
            title="analyze",
            border_style="cyan",
        )
    )
    if result.methodology_recommendation_reason:
        console.print(
            f"[dim]Recomendação automática:[/dim] {result.methodology_recommendation_reason}"
        )


class ExportFormat(StrEnum):
    yaml = "yaml"
    json = "json"
    md = "md"


class MethodologyOption(StrEnum):
    stride = "stride"
    linddun = "linddun"
    nist_data_centric = "nist_data_centric"
    octave_allegro = "octave_allegro"
    cia_die = "cia_die"
    pasta = "pasta"
    plot4ai = "plot4ai"


@app.command("export")
def cmd_export(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
    export_format: Annotated[
        ExportFormat,
        typer.Option("--format", "-f", help="Formato de saída."),
    ] = ExportFormat.yaml,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Arquivo de saída (default: stdout)."),
    ] = None,
) -> None:
    """Exporta o modelo validado (YAML, JSON ou Markdown)."""
    try:
        doc = load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=f"exportação do arquivo `{path}`.",
            cause=_SCHEMA_INVALID_CAUSE,
            next_step="execute `otm validate` e corrija os erros antes de exportar.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=f"leitura do arquivo `{path}` para exportação.",
            cause=str(e),
            next_step="confirme o caminho e se o arquivo pode ser lido.",
        )
        raise typer.Exit(1) from e

    if export_format == ExportFormat.yaml:
        text = dump_document_to_yaml(doc)
    elif export_format == ExportFormat.json:
        text = export_document_json(doc)
    else:
        text = export_document_markdown(doc)

    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Exportado[/green] → {output.resolve()}")
    else:
        print(text, end="")


@app.command("report")
def cmd_report(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava o relatório (default: stdout)."),
    ] = None,
    pack: str | None = typer.Option(
        None,
        "--pack",
        "-p",
        help="Industry pack na análise.",
    ),
) -> None:
    """Gera relatório Markdown (modelo + análise do motor)."""
    try:
        doc = load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=f"geração de relatório para `{path}`.",
            cause=_SCHEMA_INVALID_CAUSE,
            next_step="execute `otm validate` e corrija os erros antes do relatório.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=f"leitura do arquivo `{path}` para relatório.",
            cause=str(e),
            next_step="valide caminho e integridade do YAML.",
        )
        raise typer.Exit(1) from e

    pack_def = None
    if pack:
        try:
            pack_def = load_pack(pack)
        except FileNotFoundError as e:
            _print_cli_error(
                failed=f"carregamento do pack `{pack}`.",
                cause=str(e),
                next_step="execute `otm packs` e tente novamente com um pack válido.",
            )
            raise typer.Exit(1) from e

    result = analyze_document(doc, pack=pack_def)
    text = export_full_report_markdown(doc, result)
    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Relatório[/green] → {output.resolve()}")
    else:
        print(text, end="")


@app.command("diagram")
def cmd_diagram(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Arquivo .mmd (default: stdout)."),
    ] = None,
) -> None:
    """Emite diagrama Mermaid (flowchart) dos componentes e fluxos."""
    try:
        doc = load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=f"geração de diagrama para `{path}`.",
            cause=_SCHEMA_INVALID_CAUSE,
            next_step="execute `otm validate` antes de gerar o diagrama.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=f"leitura do arquivo `{path}` para diagrama.",
            cause=str(e),
            next_step="confirme o caminho do arquivo e o YAML.",
        )
        raise typer.Exit(1) from e

    text = export_flowchart_mermaid(doc)
    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Diagrama[/green] → {output.resolve()}")
    else:
        print(text, end="")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
