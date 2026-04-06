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
from otm_core_schema import (
    BLANK_DOCUMENT_YAML,
    ThreatModelDocument,
    diff_documents,
    dump_document_to_yaml,
)
from otm_core_schema.enums import ThreatModelMethodology
from otm_core_schema.model_quality_precheck import assess_model_precheck
from otm_diagram_engine import export_flowchart_mermaid
from otm_exporters import (
    export_comparison_markdown,
    export_document_json,
    export_document_markdown,
    export_remediation_backlog_json,
    export_remediation_backlog_markdown,
)
from otm_framework_mappings import framework_display_name
from otm_industry_packs.loader import (
    list_pack_ids,
    load_pack,
    load_template_info,
    load_template_yaml,
)
from otm_industry_packs.template_query import (
    filter_template_infos,
    get_template_info,
    load_all_template_infos,
)
from otm_report_premium import (
    build_premium_report_payload,
    html_to_pdf_bytes,
    render_premium_html,
    render_premium_markdown,
)
from otm_report_premium.enums import ReportFormat as PremiumReportFormat
from otm_report_premium.enums import ReportLevel as PremiumReportLevel
from otm_threat_engine import AnalysisResult, analyze_document, build_remediation_backlog
from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.methodologies import recommend_methodology
from otm_threat_engine.methodology_completeness import assess_methodology_completeness
from otm_threat_engine.threat_model_comparison import compare_threat_models
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
        "Comandos principais: [cyan]init[/cyan], [cyan]import[/cyan], "
        "[cyan]validate[/cyan], [cyan]precheck[/cyan], [cyan]diff[/cyan], "
        "[cyan]analyze[/cyan] ([cyan]--explain[/cyan]), [cyan]explain[/cyan], "
        "[cyan]backlog[/cyan], [cyan]report[/cyan], "
        "[cyan]diagram[/cyan], [cyan]export[/cyan], "
        "[cyan]templates[/cyan], [cyan]packs[/cyan]."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

INIT_TEMPLATE = BLANK_DOCUMENT_YAML

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


def _load_doc_or_exit(
    *,
    path: Path,
    failed: str,
    validation_next_step: str,
    runtime_next_step: str,
) -> ThreatModelDocument:
    try:
        return load_doc(path)
    except ValidationError as e:
        _print_cli_error(
            failed=failed,
            cause=_SCHEMA_INVALID_CAUSE,
            next_step=validation_next_step,
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e
    except RuntimeError as e:
        _print_cli_error(
            failed=failed,
            cause=str(e),
            next_step=runtime_next_step,
        )
        raise typer.Exit(1) from e


def _load_pack_or_exit(*, pack_id: str, failed: str, next_step: str):
    try:
        return load_pack(pack_id)
    except FileNotFoundError as e:
        _print_cli_error(
            failed=failed,
            cause=str(e),
            next_step=next_step,
        )
        raise typer.Exit(1) from e


def _emit_text(*, text: str, output: Path | None, ok_message: str) -> None:
    if output:
        output.write_text(text, encoding="utf-8")
        console.print(ok_message.format(path=output.resolve()))
    else:
        print(text, end="")


def _emit_bytes(*, data: bytes, output: Path | None, ok_message: str) -> None:
    if output:
        output.write_bytes(data)
        console.print(ok_message.format(path=output.resolve()))
    else:
        console.print("[red]Saída binária (PDF) requer --output.[/red]")
        raise typer.Exit(1)


def _write_json_file(*, payload: dict, output: Path) -> None:
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


class BacklogFormat(StrEnum):
    markdown = "markdown"
    json = "json"


@app.command("backlog")
def cmd_backlog(
    path: Annotated[
        Path,
        typer.Argument(help="Modelo `.otm.yaml` / `.yml` ou ficheiro `analysis.json`."),
    ],
    document: Annotated[
        Path | None,
        typer.Option(
            "--document",
            "-d",
            help=(
                "Com `path` .json: modelo YAML para resolver nomes de componentes (recomendado)."
            ),
        ),
    ] = None,
    fmt: BacklogFormat = typer.Option(
        BacklogFormat.markdown,
        "--format",
        "-f",
        help="markdown | json",
    ),
    group_by: str | None = typer.Option(
        None,
        "--group-by",
        help="Agrupamento no Markdown: root-cause | control | category.",
    ),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava saída; default stdout."),
    ] = None,
    pack: str | None = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack quando `path` é modelo YAML (corrida do motor).",
    ),
) -> None:
    """
    Backlog de remediação sugerido a partir do modelo (reanalisa) ou de JSON de análise.
    Não é gestão de tarefas — só priorização heurística com racional explícito.
    """
    pack_def = None
    if pack:
        pack_def = _load_pack_or_exit(
            pack_id=pack,
            failed=f"carregamento do pack `{pack}`.",
            next_step="execute `otm packs`.",
        )

    suf = path.suffix.lower()
    result: AnalysisResult
    doc = None

    if suf in (".yaml", ".yml"):
        doc = _load_doc_or_exit(
            path=path,
            failed=f"leitura do modelo `{path}`.",
            validation_next_step="execute `otm validate`.",
            runtime_next_step="confirme o caminho do YAML.",
        )
        result = analyze_document(doc, pack=pack_def)
    elif suf == ".json":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            result = AnalysisResult.model_validate(raw)
        except json.JSONDecodeError as e:
            console.print(f"[red]JSON inválido:[/red] {e}")
            raise typer.Exit(1) from e
        except ValidationError as e:
            console.print(
                f"[red]Não é um AnalysisResult válido:[/red]\n{format_validation_error(e)}"
            )
            raise typer.Exit(1) from e
        if document:
            doc = _load_doc_or_exit(
                path=document,
                failed=f"leitura do documento `{document}`.",
                validation_next_step="execute `otm validate`.",
                runtime_next_step="confirme o caminho do YAML.",
            )
    else:
        console.print("[red]Use .yaml/.yml (modelo) ou .json (analysis).[/red]")
        raise typer.Exit(1)

    backlog = build_remediation_backlog(result, doc)
    if fmt == BacklogFormat.json:
        text = export_remediation_backlog_json(backlog)
    else:
        text = export_remediation_backlog_markdown(backlog, group_by=group_by)
    _emit_text(text=text, output=output, ok_message="[green]Backlog[/green] → {path}")


import_cmd = typer.Typer(
    name="import",
    help=(
        "Importação assistida: gera [bold]rascunho[/bold] canónico "
        "a partir de artefactos (OpenAPI, Terraform, K8s) ou [cyan]repo[/cyan] (sinais Node/Express)."
    ),
    no_args_is_help=True,
)


@import_cmd.command("openapi")
def cmd_import_openapi(
    spec: Annotated[Path, typer.Argument(help="Ficheiro OpenAPI/Swagger (YAML ou JSON).")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava o `.otm.yaml` do rascunho."),
    ] = None,
    explain_out: Annotated[
        Path | None,
        typer.Option(
            "--explain-out",
            help="Grava documento + inferências + unknowns em JSON (transparência).",
        ),
    ] = None,
) -> None:
    """Rascunho a partir de especificação OpenAPI 3 ou Swagger 2."""
    from otm_artifact_import import import_openapi_path

    if not spec.is_file():
        console.print(f"[red]Não é ficheiro:[/red] {spec}")
        raise typer.Exit(1)
    result = import_openapi_path(spec)
    yaml_text = dump_document_to_yaml(result.document)
    if output:
        output.write_text(yaml_text, encoding="utf-8")
        console.print(f"[green]Rascunho[/green] → {output.resolve()}")
    else:
        print(yaml_text, end="")
    if explain_out:
        _write_json_file(
            payload={
                "document": result.document.model_dump(mode="json", by_alias=True),
                "inferences": [i.model_dump(mode="json") for i in result.inferences],
                "unknowns": result.unknowns,
                "assumptions": result.assumptions,
            },
            output=explain_out,
        )
        console.print(f"[green]Inferências[/green] → {explain_out.resolve()}")
    if result.inferences and output:
        console.print(
            Panel.fit(
                "\n".join(f"• ({i.confidence}) {i.message}" for i in result.inferences[:12]),
                title="Inferências (resumo)",
                border_style="cyan",
            )
        )


@import_cmd.command("terraform")
def cmd_import_terraform(
    target: Annotated[Path, typer.Argument(help="Ficheiro `.tf` ou directório com `.tf`.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava o `.otm.yaml` do rascunho."),
    ] = None,
    explain_out: Annotated[
        Path | None,
        typer.Option("--explain-out", help="JSON com inferências estruturadas."),
    ] = None,
) -> None:
    """Rascunho a partir de recursos Terraform (parser conservador)."""
    from otm_artifact_import import import_terraform_path

    if not target.exists():
        console.print(f"[red]Caminho inexistente:[/red] {target}")
        raise typer.Exit(1)
    result = import_terraform_path(target)
    yaml_text = dump_document_to_yaml(result.document)
    if output:
        output.write_text(yaml_text, encoding="utf-8")
        console.print(f"[green]Rascunho[/green] → {output.resolve()}")
    else:
        print(yaml_text, end="")
    if explain_out:
        _write_json_file(
            payload={
                "document": result.document.model_dump(mode="json", by_alias=True),
                "inferences": [i.model_dump(mode="json") for i in result.inferences],
                "unknowns": result.unknowns,
                "assumptions": result.assumptions,
            },
            output=explain_out,
        )
        console.print(f"[green]Inferências[/green] → {explain_out.resolve()}")


@import_cmd.command("k8s")
def cmd_import_k8s(
    target: Annotated[
        Path,
        typer.Argument(help="YAML multi-doc ou directório com `.yaml`/`.yml`."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava o `.otm.yaml` do rascunho."),
    ] = None,
    explain_out: Annotated[
        Path | None,
        typer.Option("--explain-out", help="JSON com inferências estruturadas."),
    ] = None,
) -> None:
    """Rascunho a partir de manifests Kubernetes."""
    from otm_artifact_import import import_kubernetes_path

    if not target.exists():
        console.print(f"[red]Caminho inexistente:[/red] {target}")
        raise typer.Exit(1)
    result = import_kubernetes_path(target)
    yaml_text = dump_document_to_yaml(result.document)
    if output:
        output.write_text(yaml_text, encoding="utf-8")
        console.print(f"[green]Rascunho[/green] → {output.resolve()}")
    else:
        print(yaml_text, end="")
    if explain_out:
        _write_json_file(
            payload={
                "document": result.document.model_dump(mode="json", by_alias=True),
                "inferences": [i.model_dump(mode="json") for i in result.inferences],
                "unknowns": result.unknowns,
                "assumptions": result.assumptions,
            },
            output=explain_out,
        )
        console.print(f"[green]Inferências[/green] → {explain_out.resolve()}")


@import_cmd.command("repo")
def cmd_import_repo(
    root: Annotated[Path, typer.Argument(help="Raiz do repositório (ex.: serviço Node/Express).")],
    json_out: Annotated[
        Path | None,
        typer.Option("--json-out", help="Grava JSON com inferências e excerto de corpus."),
    ] = None,
) -> None:
    """Varredura pragmática: rotas, upload, sessão, fetch externo, eval (sem precisão total)."""
    from otm_artifact_import import scan_node_express_repo

    if not root.is_dir():
        console.print(f"[red]Não é directório:[/red] {root}")
        raise typer.Exit(1)
    payload = scan_node_express_repo(root)
    if json_out:
        _write_json_file(payload=payload, output=json_out)
        console.print(f"[green]Scan repo[/green] → {json_out.resolve()}")
    else:
        txt = json.dumps(payload, indent=2, ensure_ascii=False)
        console.print(Panel.fit(txt[:14000], title="repo-scan", border_style="cyan"))


app.add_typer(import_cmd)


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
        _print_templates_list_filtered()
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
            console.print(f"Sugestão: [cyan]otm analyze {path} --pack {info.suggested_pack}[/cyan]")
        else:
            console.print(f"Próximo passo: [cyan]otm validate {path}[/cyan]")
    else:
        path.write_text(INIT_TEMPLATE, encoding="utf-8")
        console.print(
            f"[green]Criado[/green] {path.resolve()}\n"
            f"Próximo passo: [cyan]otm validate {path}[/cyan] "
            "(ou [cyan]otm init -t saas-web[/cyan])"
        )


def _print_templates_list_filtered(
    category: str | None = None,
    tag: str | None = None,
    complexity: str | None = None,
    q: str | None = None,
) -> None:
    infos = load_all_template_infos()
    infos = filter_template_infos(
        infos,
        category=category,
        tag=tag,
        complexity=complexity,
        q=q,
    )
    console.print("[bold]Templates[/bold] (use: [cyan]otm init -t ID[/cyan]):")
    for info in infos:
        line = f"  • [cyan]{info.id}[/cyan] — {info.title}"
        console.print(line)
        if info.suggested_pack:
            console.print(f"    pack sugerido: {info.suggested_pack}")
        if info.complexity:
            console.print(f"    complexidade: {info.complexity}")
        if info.category_label:
            console.print(f"    categoria: {info.category_label}")


templates_app = typer.Typer(
    name="templates",
    help="Catálogo de templates embutidos (lista, filtros, detalhe).",
)


@templates_app.callback(invoke_without_command=True)
def templates_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _print_templates_list_filtered()


@templates_app.command("list")
def cmd_templates_list(
    category: str | None = typer.Option(None, "--category", "-c", help="Filtra pela chave de categoria."),
    tag: str | None = typer.Option(None, "--tag", help="Tag exata (case-insensitive)."),
    complexity: str | None = typer.Option(
        None,
        "--complexity",
        help="low | medium | high",
    ),
    q: str | None = typer.Option(None, "--query", "-q", help="Texto livre (id, título, descrição, tags)."),
) -> None:
    """Lista templates com filtros opcionais (sem filtros = catálogo completo)."""
    _print_templates_list_filtered(category=category, tag=tag, complexity=complexity, q=q)


@templates_app.command("show")
def cmd_templates_show(
    template_id: str = typer.Argument(..., help="ID do template (ex.: ai-rag-enterprise)."),
) -> None:
    """Mostra metadados de um template embutido."""
    info = get_template_info(template_id)
    if info is None:
        console.print(f"[red]Template desconhecido:[/red] {template_id}")
        raise typer.Exit(1)
    lines = [
        f"[bold]ID:[/bold] {info.id}",
        f"[bold]Título:[/bold] {info.title}",
        f"[bold]Descrição:[/bold] {info.description or '—'}",
        f"[bold]Categoria:[/bold] {info.category_label} ({info.category})",
    ]
    if info.tags:
        lines.append(f"[bold]Tags:[/bold] {', '.join(info.tags)}")
    if info.complexity:
        lines.append(f"[bold]Complexidade:[/bold] {info.complexity}")
    if info.best_for:
        lines.append(f"[bold]Melhor para:[/bold] {info.best_for}")
    if info.suggested_pack:
        lines.append(f"[bold]Pack sugerido:[/bold] {info.suggested_pack}")
    if info.suggested_methodology:
        lines.append(f"[bold]Metodologia sugerida:[/bold] {info.suggested_methodology}")
    if info.recommendation_hints:
        lines.append(f"[bold]Sinais (recomendação):[/bold] {', '.join(info.recommendation_hints)}")
    console.print(Panel.fit("\n".join(lines), title=f"template [cyan]{info.id}[/cyan]", border_style="cyan"))


app.add_typer(templates_app, name="templates")


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
    doc = _load_doc_or_exit(
        path=path,
        failed=f"recomendação de metodologia para `{path}`.",
        validation_next_step="execute `otm validate` e corrija o documento.",
        runtime_next_step="confirme o caminho e a integridade do YAML.",
    )

    rec = recommend_methodology(doc)
    console.print(
        Panel.fit(
            f"Suggested methodology: [bold]{rec.methodology.value}[/bold]\n\nReason: {rec.reason}",
            title="recommend-methodology",
            border_style="magenta",
        )
    )


class DiffFormat(StrEnum):
    text = "text"
    json = "json"
    markdown = "markdown"


@app.command("diff")
def cmd_diff(
    baseline: Annotated[Path, typer.Argument(help="Versão anterior (baseline) .otm.yaml.")],
    revised: Annotated[Path, typer.Argument(help="Versão nova (revisão) .otm.yaml.")],
    json_out: Path | None = typer.Option(
        None,
        "--json-out",
        help="Grava o resultado em JSON (structural só com diff simples; veja --with-analysis).",
    ),
    fmt: DiffFormat = typer.Option(
        DiffFormat.text,
        "--format",
        "-f",
        help=(
            "text | json | markdown "
            "(markdown requer --with-analysis ou structural vazio de risco)."
        ),
    ),
    with_analysis: bool = typer.Option(
        False,
        "--with-analysis",
        help="Executa o motor em ambos os YAML e inclui delta de risco/heurísticas.",
    ),
    pack: str | None = typer.Option(
        None,
        "--pack",
        "-p",
        help="Industry pack quando --with-analysis está ativo.",
    ),
    summary_only: bool = typer.Option(
        False,
        "--summary-only",
        help="Mostra só resumo e insights principais (formato text/markdown).",
    ),
) -> None:
    """
    Compara duas versões do threat model.
    Com --with-analysis inclui diff semântico da análise.
    """
    doc_a = _load_doc_or_exit(
        path=baseline,
        failed=f"leitura da baseline `{baseline}`.",
        validation_next_step="execute `otm validate` na baseline.",
        runtime_next_step="confirme o caminho e o YAML.",
    )
    doc_b = _load_doc_or_exit(
        path=revised,
        failed=f"leitura da revisão `{revised}`.",
        validation_next_step="execute `otm validate` na revisão.",
        runtime_next_step="confirme o caminho e o YAML.",
    )
    pack_def = None
    if pack:
        pack_def = _load_pack_or_exit(
            pack_id=pack,
            failed=f"carregamento do pack `{pack}`.",
            next_step="execute `otm packs`.",
        )
    ba: AnalysisResult | None = None
    ra: AnalysisResult | None = None
    if with_analysis:
        ba = analyze_document(doc_a, pack=pack_def)
        ra = analyze_document(doc_b, pack=pack_def)
    full = compare_threat_models(doc_a, doc_b, baseline_analysis=ba, revised_analysis=ra)

    if with_analysis:
        out_payload = full.model_dump(mode="json")
    else:
        out_payload = diff_documents(doc_a, doc_b).model_dump(mode="json")
    if json_out:
        _write_json_file(payload=out_payload, output=json_out)
        console.print(f"[green]Diff gravado em[/green] {json_out.resolve()}")
    if fmt == DiffFormat.json:
        print(json.dumps(out_payload, indent=2, ensure_ascii=False))
        return

    if fmt == DiffFormat.markdown:
        print(export_comparison_markdown(full), end="")
        return

    if summary_only:
        lines2 = [full.summary.headline, "", "Insights:"]
        for ins in full.key_insights[:25]:
            lines2.append(f"- {ins}")
        console.print(Panel("\n".join(lines2), title="diff (resumo)", border_style="blue"))
        return

    result = full.structural
    lines: list[str] = [full.summary.headline, ""]
    if full.structural_insights:
        lines.append("Insights estruturais:")
        for ins in full.structural_insights[:12]:
            lines.append(f"- {ins}")
        lines.append("")
    if with_analysis and full.analysis_insights:
        lines.append("Insights de análise:")
        for ins in full.analysis_insights[:12]:
            lines.append(f"- {ins}")
        lines.append("")
    if with_analysis and full.meta:
        meta = full.meta
        disc = meta.interpretation_disclaimer
        if isinstance(disc, str) and disc.strip():
            lines.append("Aviso inferencial:")
            lines.append(f"  {disc.strip()}")
            lines.append("")
        sem = meta.semantic_diff_sections
        if sem is not None:
            scs = sem.structural_change_summary or []
            imp, wor, risk = sem.improved or [], sem.worsened or [], sem.risk_impact or []
            if scs or imp or wor or risk:
                lines.append("Diff semântico (heurístico):")
                for x in scs[:5]:
                    lines.append(f"  Δ {x}")
                for x in imp[:6]:
                    lines.append(f"  + {x}")
                for x in wor[:6]:
                    lines.append(f"  ! {x}")
                for x in risk[:5]:
                    lines.append(f"  ~ {x}")
                lines.append("")
        refs = meta.semantic_structural_refs
        if refs:
            lines.append("Refs estrutura→interpretação (ancoradas, não causais):")
            for item in refs[:12]:
                lines.append(f"  {item.ref} · {item.entity_kind} `{item.entity_id}`")
            lines.append("")
        ilinks = meta.semantic_interpretation_links
        if ilinks:
            lines.append("Correspondência ref → interpretação (v1.4, proxies de leitura):")
            for item in ilinks[:10]:
                lines.append(
                    f"  {item.structural_ref} → {item.related_section} "
                    f"[{item.link_kind}/{item.inference_strength}]: "
                    f"{str(item.summary)[:120]}"
                )
            lines.append("")
        si = meta.semantic_insights
        if si:
            lines.append("Insights semânticos:")
            for x in si[:10]:
                lines.append(f"- {x}")
            lines.append("")

    for label, sec in [
        ("model_info", result.model_info),
        ("metadata", result.metadata),
        ("business_context", result.business_context),
        ("residual_risk_summary", result.residual_risk_summary),
    ]:
        if sec:
            lines.append(f"[{label}]")
            for ch in sec:
                lines.append(f"  - {ch.field}: alterado")
            lines.append("")
    for name, sec in [
        ("assets", result.assets),
        ("components", result.components),
        ("data_flows", result.data_flows),
        ("trust_boundaries", result.trust_boundaries),
        ("threats", result.threats),
        ("mitigations", result.mitigations),
        ("evidence_suggestions", result.evidence_suggestions),
    ]:
        if sec.added or sec.removed or sec.modified:
            lines.append(f"[{name}] +{len(sec.added)} / -{len(sec.removed)} / ~{len(sec.modified)}")
            if sec.added:
                lines.append(f"  adicionados: {', '.join(sec.added)}")
            if sec.removed:
                lines.append(f"  removidos: {', '.join(sec.removed)}")
            for m in sec.modified[:12]:
                fields = ", ".join(c.field for c in m.changes)
                lines.append(f"  ~ {m.id}: {fields}")
            if len(sec.modified) > 12:
                lines.append(f"  … +{len(sec.modified) - 12} modificados")
            lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    console.print(Panel(text, title="diff", border_style="blue"))


@app.command("diff-analysis")
def cmd_diff_analysis(
    baseline: Annotated[Path, typer.Argument(help="JSON de AnalysisResult (baseline).")],
    revised: Annotated[Path, typer.Argument(help="JSON de AnalysisResult (revisão).")],
    json_out: Path | None = typer.Option(None, "--json-out", help="Grava AnalysisDiff em JSON."),
    fmt: DiffFormat = typer.Option(DiffFormat.text, "--format", "-f", help="text ou json."),
) -> None:
    """Compara dois ficheiros `analyze.json` (sem reexecutar o motor)."""
    try:
        b_obj = json.loads(baseline.read_text(encoding="utf-8"))
        r_obj = json.loads(revised.read_text(encoding="utf-8"))
        br = AnalysisResult.model_validate(b_obj)
        ar = AnalysisResult.model_validate(r_obj)
    except (OSError, json.JSONDecodeError) as e:
        _print_cli_error(
            failed=f"leitura de JSON em `{baseline}` / `{revised}`.",
            cause=str(e),
            next_step="confirme caminhos e que os ficheiros são JSON válidos.",
        )
        raise typer.Exit(1) from e
    except ValidationError as e:
        _print_cli_error(
            failed="validação de AnalysisResult.",
            cause=_SCHEMA_INVALID_CAUSE,
            next_step="gere novamente com `otm analyze --json-out`.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e

    ad = diff_analysis_results(br, ar)
    payload = ad.model_dump(mode="json")
    if json_out:
        _write_json_file(payload=payload, output=json_out)
        console.print(f"[green]Diff de análise gravado em[/green] {json_out.resolve()}")
    if fmt == DiffFormat.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    lines_a: list[str] = [
        f"Metodologia: {ad.methodology_before} → {ad.methodology_after}",
        f"Score máx.: {ad.max_risk_before} → {ad.max_risk_after} (Δ {ad.max_risk_delta!s})",
        "Heurísticas ativas: "
        f"+{len(ad.heuristic_threats.added)} / "
        f"−{len(ad.heuristic_threats.removed)} / "
        f"~{len(ad.heuristic_threats.modified)}",
        "",
    ]
    for h in ad.heuristic_threats.added[:8]:
        lines_a.append(f"  + {h.threat_id} (score {h.score_after})")
    for h in ad.heuristic_threats.removed[:8]:
        lines_a.append(f"  − {h.threat_id}")
    for h in ad.heuristic_threats.modified[:8]:
        lines_a.append(f"  ~ {h.threat_id} Δscore={h.score_delta!s}")
    if ad.signature_remap_hints:
        lines_a.append("")
        lines_a.extend(ad.signature_remap_hints[:6])
    console.print(Panel("\n".join(lines_a), title="diff-analysis", border_style="magenta"))


@app.command("validate")
def cmd_validate(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml / .yml.")],
) -> None:
    """Valida o documento contra o schema canônico."""
    doc = _load_doc_or_exit(
        path=path,
        failed=f"validação do arquivo `{path}`.",
        validation_next_step=(
            "corrija os campos listados abaixo e execute `otm validate` novamente."
        ),
        runtime_next_step="confirme o caminho, o YAML e permissões do arquivo.",
    )

    console.print(
        Panel.fit(
            f"[green]Valid[/green]\n\n"
            f"Title: [bold]{doc.metadata.title}[/bold]\n"
            f"Schema: {doc.model_info.schema_version}\n"
            f"Components: {len(doc.components)} · Flows: {len(doc.data_flows)}",
            title="validate",
            border_style="green",
        )
    )


@app.command("precheck")
def cmd_precheck(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml / .yml.")],
    json_out: Path | None = typer.Option(
        None,
        "--json-out",
        help="Grava pré-check + completude metodológica em JSON.",
    ),
    methodology: MethodologyOption | None = typer.Option(
        None,
        "--methodology",
        "-m",
        help="Metodologia para avaliar completeness (default: document.model.methodology).",
    ),
) -> None:
    """Pré-check de completude do modelo (score, banda, matriz de adequação) sem correr o motor STRIDE."""
    doc = _load_doc_or_exit(
        path=path,
        failed=f"pré-check do arquivo `{path}`.",
        validation_next_step="execute `otm validate` e corrija os erros antes do pré-check.",
        runtime_next_step="valide o caminho do arquivo e o formato YAML.",
    )
    chosen = doc.model_info.methodology
    if methodology is not None:
        chosen = ThreatModelMethodology(methodology.value)
    pre = assess_model_precheck(doc)
    mc = assess_methodology_completeness(doc, chosen)
    payload = {
        "precheck": pre.model_dump(mode="json"),
        "methodology_completeness": mc.model_dump(mode="json"),
    }
    if json_out:
        _write_json_file(payload=payload, output=json_out)
        console.print(f"[green]Pré-check gravado em[/green] {json_out.resolve()}")
    else:
        console.print(
            Panel.fit(
                json.dumps(payload, indent=2, ensure_ascii=False),
                title="precheck",
                border_style="cyan",
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
    explain: bool = typer.Option(
        False,
        "--explain",
        "-x",
        help="Mostra um resumo de explicabilidade estruturada no terminal.",
    ),
) -> None:
    """Executa o motor (STRIDE heurístico, fronteiras, risco L×I, pack opcional)."""
    doc = _load_doc_or_exit(
        path=path,
        failed=f"análise do arquivo `{path}`.",
        validation_next_step="execute `otm validate` e corrija os erros antes de analisar.",
        runtime_next_step="valide o caminho do arquivo e o formato YAML.",
    )

    pack_def = None
    if pack:
        pack_def = _load_pack_or_exit(
            pack_id=pack,
            failed=f"carregamento do pack `{pack}`.",
            next_step="execute `otm packs` e use um ID listado.",
        )

    result = analyze_document(
        doc,
        pack=pack_def,
        methodology=methodology.value if methodology else None,
        auto_recommend=auto_methodology,
    )
    if json_out:
        payload = result.model_dump(mode="json")
        _write_json_file(payload=payload, output=json_out)
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
        fw_line = "Framework refs: " + " · ".join(bits) + "\n"
    console.print(
        Panel.fit(
            f"[bold]{result.document_title}[/bold]\n\n"
            f"{pack_line}"
            f"{fw_line}"
            f"Structural warnings: {s.structural_findings}\n"
            f"Methodology: {result.methodology.value}\n"
            f"Cross-boundary flows: {s.trust_boundary_findings}\n"
            f"Base heuristics: {s.heuristic_threats_generated} new · "
            f"{s.heuristic_threats_skipped_duplicate} already covered\n"
            f"Highest score (L×I): {s.max_risk_score!s}\n"
            f"Engine: {result.engine_version}",
            title="analyze",
            border_style="cyan",
        )
    )
    if result.methodology_recommendation_reason:
        console.print(
            f"[dim]Auto recommendation:[/dim] {result.methodology_recommendation_reason}"
        )
    if result.methodology == ThreatModelMethodology.PLOT4AI and result.ai_system_context:
        ctx = result.ai_system_context
        tags = ", ".join(ctx.pattern_tags[:6]) if ctx.pattern_tags else "—"
        console.print(f"[dim]PLOT4ai (AI):[/dim] patterns ~ [{tags}]")
        if ctx.primary_risk_surfaces:
            console.print(f"[dim]  Surface:[/dim] {ctx.primary_risk_surfaces[0][:160]}")

    if explain and result.explanations:
        console.print("\n[bold]Explainability[/bold] (first 15 entries)")
        for ex in result.explanations[:15]:
            cat = getattr(ex.category, "value", ex.category)
            console.print(f"  [cyan]{cat}[/cyan] · {ex.subject} — {ex.message}")

    if result.wizard_context_notes or result.wizard_signal_trace:
        console.print("\n[bold]Assistente / audit trail[/bold] (resumo)")
        for n in result.wizard_context_notes[:6]:
            console.print(f"  [dim]nota:[/dim] {n[:200]}")
        for tr in result.wizard_signal_trace[:8]:
            console.print(
                f"  [dim]{tr.effect}[/dim] `{tr.source_tag[:64]}` "
                f"({tr.weight}) → {tr.explanation[:160]}"
            )


@app.command("explain")
def cmd_explain(
    path: Annotated[
        Path,
        typer.Argument(help="`analysis.json` (otm analyze --json-out) ou compare JSON."),
    ],
    kind: str = typer.Option(
        "analysis",
        "--from",
        "-f",
        help="Tipo: analysis | compare",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filtra por categoria de explicação (ex.: risk, methodology, ai_modeling).",
    ),
    limit: int = typer.Option(25, "--limit", "-n", help="Máximo de linhas."),
) -> None:
    """
    Imprime explicabilidade estruturada a partir de ficheiros JSON gerados pela CLI/API.

    Útil em CI: validar que o campo `explanations` existe sem abrir o payload completo.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    explanations: list = []
    if kind == "analysis":
        explanations = list(raw.get("explanations") or [])
    elif kind == "compare":
        explanations = list(raw.get("explanations") or [])
    else:
        console.print("[red]--from deve ser analysis ou compare.[/red]")
        raise typer.Exit(2)
    if not explanations:
        console.print("[yellow]Nenhuma explicação neste ficheiro.[/yellow]")
        raise typer.Exit(0)
    if category:
        explanations = [e for e in explanations if str(e.get("category", "")).strip().lower() == category.lower()]
    if not explanations:
        console.print("[yellow]Nenhuma explicação para o filtro informado.[/yellow]")
        raise typer.Exit(0)
    for item in explanations[:limit]:
        subj = item.get("subject", "")
        msg = item.get("message", "")
        cat = item.get("category", "")
        console.print(f"[cyan]{cat}[/cyan] · {subj} — {msg}")


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
    doc = _load_doc_or_exit(
        path=path,
        failed=f"exportação do arquivo `{path}`.",
        validation_next_step="execute `otm validate` e corrija os erros antes de exportar.",
        runtime_next_step="confirme o caminho e se o arquivo pode ser lido.",
    )

    if export_format == ExportFormat.yaml:
        text = dump_document_to_yaml(doc)
    elif export_format == ExportFormat.json:
        text = export_document_json(doc)
    else:
        text = export_document_markdown(doc)

    _emit_text(text=text, output=output, ok_message="[green]Exportado[/green] → {path}")


def _load_analysis_result_json(path: Path) -> AnalysisResult:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _print_cli_error(
            failed=f"leitura de `{path}`.",
            cause=str(e),
            next_step="confirme que o ficheiro é JSON válido (`otm analyze --json-out`).",
        )
        raise typer.Exit(1) from e
    try:
        return AnalysisResult.model_validate(raw)
    except ValidationError as e:
        _print_cli_error(
            failed=f"validação de AnalysisResult em `{path}`.",
            cause="estrutura incompatível.",
            next_step="regenere com `otm analyze --json-out`.",
        )
        console.print(f"[red]\n{format_validation_error(e)}[/red]")
        raise typer.Exit(1) from e


@app.command("report")
def cmd_report(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Grava o relatório (default: stdout para texto)."),
    ] = None,
    pack: str | None = typer.Option(
        None,
        "--pack",
        "-p",
        help="Industry pack na análise.",
    ),
    level: Annotated[
        PremiumReportLevel | None,
        typer.Option(
            "--level",
            "-l",
            help=(
                "Report premium: executive | standard | deep. "
                "Se omitido, gera o relatório legado (modelo + análise em Markdown)."
            ),
        ),
    ] = None,
    report_format: Annotated[
        PremiumReportFormat,
        typer.Option(
            "--format",
            "-f",
            help="Com --level: markdown (default) ou pdf.",
        ),
    ] = PremiumReportFormat.MARKDOWN,
    analysis_json: Annotated[
        Path | None,
        typer.Option(
            "--analysis-json",
            help="Reutiliza `AnalysisResult` em JSON em vez de correr o motor.",
        ),
    ] = None,
    baseline_json: Annotated[
        Path | None,
        typer.Option(
            "--baseline",
            help="JSON de análise anterior para secção baseline/diff no report premium.",
        ),
    ] = None,
) -> None:
    """Relatório legado (Markdown) ou report premium (níveis executive/standard/deep)."""
    doc = _load_doc_or_exit(
        path=path,
        failed=f"geração de relatório para `{path}`.",
        validation_next_step="execute `otm validate` e corrija os erros antes do relatório.",
        runtime_next_step="valide caminho e integridade do YAML.",
    )

    pack_def = None
    if pack:
        pack_def = _load_pack_or_exit(
            pack_id=pack,
            failed=f"carregamento do pack `{pack}`.",
            next_step="execute `otm packs` e tente novamente com um pack válido.",
        )

    if analysis_json:
        result = _load_analysis_result_json(analysis_json)
    else:
        result = analyze_document(doc, pack=pack_def)

    if level is None:
        text = export_full_report_markdown(doc, result)
        _emit_text(text=text, output=output, ok_message="[green]Relatório[/green] → {path}")
        return

    baseline: AnalysisResult | None = None
    if baseline_json:
        baseline = _load_analysis_result_json(baseline_json)

    payload = build_premium_report_payload(
        doc,
        result,
        level=level,
        baseline=baseline,
        app_version=_installed_version(),
    )
    if report_format == PremiumReportFormat.MARKDOWN:
        text = render_premium_markdown(payload)
        _emit_text(text=text, output=output, ok_message="[green]Report premium (Markdown)[/green] → {path}")
        return

    html = render_premium_html(payload)
    try:
        pdf_bytes = html_to_pdf_bytes(html)
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    default_out = output or Path("report-premium.pdf")
    _emit_bytes(data=pdf_bytes, output=default_out, ok_message="[green]Report premium (PDF)[/green] → {path}")


@app.command("diagram")
def cmd_diagram(
    path: Annotated[Path, typer.Argument(help="Arquivo .otm.yaml.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Arquivo .mmd (default: stdout)."),
    ] = None,
) -> None:
    """Emite diagrama Mermaid (flowchart) dos componentes e fluxos."""
    doc = _load_doc_or_exit(
        path=path,
        failed=f"geração de diagrama para `{path}`.",
        validation_next_step="execute `otm validate` antes de gerar o diagrama.",
        runtime_next_step="confirme o caminho do arquivo e o YAML.",
    )

    text = export_flowchart_mermaid(doc)
    _emit_text(text=text, output=output, ok_message="[green]Diagrama[/green] → {path}")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
