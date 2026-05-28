# CLI (`otm`)

Interface oficial em linha de comando — mesma base que a API (`ThreatModelDocument` + `otm_threat_engine`).

## Arquitetura

| Camada | Módulo | Função |
|--------|--------|--------|
| Orquestração | `otm_cli/cli.py` | Comandos Typer, mensagens, ficheiros |
| Carga / erros | `otm_cli/io_util.py` | `load_doc`, formatação de `ValidationError` |
| Relatório MD | `otm_cli/reporting.py` | Documento + resultado do motor (legado) |
| Report premium | `otm_report_premium` | Payload + Markdown/HTML/PDF (níveis executive/standard/deep) |
| Schema | `otm_core_schema` | Validação e serialização |
| Motor | `otm_threat_engine` | `analyze_document` |
| Export neutro | `otm_exporters`, `otm_diagram_engine` | JSON/MD/Mermaid sem lógica de negócio extra |

## Instalação

```bash
pip install -e ".[cli]"
```

Para **PDF premium**, instale também o extra `report` (`xhtml2pdf`): `pip install -e ".[cli,report]"`.

O executável é **`otm`** (ou `python -m otm_cli.cli`).

## Comandos

| Comando | Descrição |
|---------|-----------|
| `otm init [arquivo]` | Cria um `.otm.yaml` mínimo (default: `threatmodel.otm.yaml`). |
| `otm validate <arquivo>` | Valida o schema; painel com resumo. |
| `otm precheck <arquivo>` | Pré-check de completude (score, matriz de adequação metodológica) + completude da metodologia; não corre o motor. `--json-out` para CI. |
| `otm analyze <arquivo>` | Corre o motor (STRIDE heurístico, fronteiras, L×I). |
| `otm analyze ... --methodology <id>` | Seleciona engine/metodologia (`stride`, `linddun`, `nist_data_centric`, `octave_allegro`, `cia_die`, `pasta`, `plot4ai`). |
| `otm analyze ... --auto-methodology` | Aplica recomendação automática de metodologia pelo contexto do documento. |
| `otm analyze ... --json-out resultado.json` | Grava o `AnalysisResult` completo (CI/CD). |
| `otm analyze ... --explain` | Mostra um resumo curto de `explanations` no terminal. |
| `otm explain <ficheiro.json> --from analysis\|compare` | Lê `explanations` de artefactos JSON sem despejar o payload completo. |
| `otm recommend-methodology <arquivo>` | Sugere metodologia e explica o motivo. |
| `otm report <arquivo>` | Markdown: modelo + análise (stdout ou `-o`) — relatório legado. |
| `otm report <arquivo> --level executive\|standard\|deep` | Report premium (Markdown ou PDF com `-f markdown\|pdf`). Ver `docs/features/PREMIUM_REPORTS.md`. |
| `otm report ... --analysis-json <ficheiro>` | Reutiliza `AnalysisResult` JSON. |
| `otm report ... --baseline <ficheiro>` | Análise anterior para diff no report premium. |
| `otm diagram <arquivo>` | Mermaid flowchart (stdout ou `-o`). |
| `otm export <arquivo> -f yaml\|json\|md` | Modelo normalizado (default: stdout). |
| `otm --version` | Versão. |

## Exemplos (pipelines)

```bash
# Validação em CI
otm validate modelo.otm.yaml || exit 1

# Análise silenciosa com artefacto JSON
otm analyze modelo.otm.yaml -q --json-out analise.json

# Relatório para revisão humana
otm report modelo.otm.yaml -o RELATORIO.md

# Diagrama para documentação (GitHub renderiza Mermaid)
otm diagram modelo.otm.yaml -o docs/diagrama.mmd
```

## Exemplos por metodologia

```bash
# default/madura
otm analyze modelo.otm.yaml --methodology stride

# privacidade (fase nativa incremental)
otm analyze modelo.otm.yaml --methodology linddun

# dados críticos (base para v1 preparada)
otm analyze modelo.otm.yaml --methodology nist_data_centric

# risco organizacional orientado a ativos
otm analyze modelo.otm.yaml --methodology octave_allegro

# visão executiva simplificada
otm analyze modelo.otm.yaml --methodology cia_die

# avançado/risk-centric (PASTA fase 2)
otm analyze modelo.otm.yaml --methodology pasta

# AI/LLM specialized (PLOT4ai fase 2)
otm analyze modelo.otm.yaml --methodology plot4ai
```

Em `--methodology pasta` e `--methodology plot4ai`, o JSON (`--json-out`) inclui `methodology_insights` com blocos especializados, sem quebrar o contrato base de análise.

Para `plot4ai`, a saída também pode incluir `ai_system_context` (camadas detectadas, superfícies de risco, recomendações e agrupamento de heurísticas por camada).

## Saída e erros

- Mensagens de sucesso e painéis usam **Rich** (muitas vezes em **stderr**); dados puros (YAML/JSON/MD/Mermaid) vão para **stdout** quando não há `-o`.
- Erros de schema listam caminhos Pydantic de forma legível.
- Quando `-o` / `--json-out` / `--output` aponta para um diretório que não existe, a CLI emite um erro de utilizador (sem stack trace) com a sugestão de criar o diretório.
- `--methodology` e `--auto-methodology` são mutuamente exclusivos em `analyze`; passe apenas um.

### Windows — caracteres acentuados, setas e emojis

Desde `v7.6.0`, o entrypoint `otm` força UTF-8 em `stdout`/`stderr` (`PYTHONIOENCODING=utf-8` + `sys.stdout.reconfigure`) e o console Rich corre com `legacy_windows=False`. Em terminais modernos (Windows Terminal, PowerShell 7, VS Code) acentos `pt-BR`, setas `→`, em-dashes `—` e emojis aparecem íntegros sem `chcp 65001`. Em sessões antigas de `cmd.exe`, se notar mojibake, rode `chcp 65001` antes do comando.
