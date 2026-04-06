# Reports premium (Executive / Standard / Deep)

O App Suite Modeling gera relatórios consolidados a partir do **mesmo pipeline** usado pelo motor (`AnalysisResult`), backlog de remediação, explainability e, opcionalmente, **diff entre análises** — sem duplicar regras de negócio no frontend.

## Níveis

| Nível | Público | Conteúdo principal |
|-------|---------|-------------------|
| **executive** | Gestão | Capa, executive summary, top riscos, roadmap, diff (se houver baseline) |
| **standard** | Gestão + AppSec | Acima + arquitetura, distribuições, causas raiz, exploitability (amostra), quick wins, ownership, explainability |
| **deep** | Engenharia | Acima + apêndice técnico (listagem de ameaças), diagrama Mermaid no payload, voz metodológica |

## Priorização (P1 / P2 / P3)

A prioridade **não** é só severidade STRIDE: combina score de risco, exposição heurística, impacto de negócio sugerido e esforço de remediação estimado. Os tiers são **tercis** dentro do conjunto analisado. Tudo é **heurístico** — ver avisos no relatório.

## Baseline / diff

Passe uma análise anterior (`baseline`) para preencher riscos novos/removidos/modificados e narrativa de evolução. O matching segue o motor (`diff_analysis_results`).

## CLI

Relatório **legado** (modelo + análise em Markdown), inalterado:

```bash
otm report modelo.otm.yaml
```

Report **premium**:

```bash
otm report modelo.otm.yaml --level standard --format markdown
otm report modelo.otm.yaml --level executive --format pdf -o relatorio.pdf
otm report modelo.otm.yaml --level deep --format markdown --analysis-json analise.json
otm report modelo.otm.yaml --level standard --baseline analise_anterior.json
```

- `--analysis-json`: evita reexecutar o motor.
- `--baseline`: JSON de `AnalysisResult` anterior para a secção de diff.
- `--locale`: `pt-BR` (omissão) ou `en` — textos estruturais do relatório (Markdown/HTML/PDF).

**PDF:** requer `pip install -e ".[report]"` (ou `xhtml2pdf`).

## API

`POST /v1/reports/premium`

Corpo (resumo):

- `document` — canónico (obrigatório).
- `analysis` — `AnalysisResult` opcional se `run_analysis: true`.
- `baseline_analysis` — opcional.
- `level`: `executive` | `standard` | `deep`.
- `output_format`: `markdown` | `pdf`.
- `locale` (opcional): `pt-BR` | `en` — textos estruturais; omitido = `pt-BR` (retrocompat); valor inválido → `en`.

Resposta: `text/markdown` ou `application/pdf`.

## UI

Na página **Exportar**, secção **Report premium (API)** — escolha o nível e descarregue Markdown ou PDF (API em execução). O idioma do relatório premium segue o mesmo controlo **Idioma do artefacto** usado para exports Markdown/PDF da sessão. O PDF rápido no browser (jsPDF) permanece como pré-visualização leve.

## Internacionalização (pt-BR / en)

Rótulos de secções, disclaimers, tabelas, roadmap e mensagens de template do payload são gerados em **pt-BR** ou **en** conforme `locale`. Conteúdo dinâmico do motor (títulos de ameaças, `next_step` do backlog, etc.) não é traduzido automaticamente. Ver [`docs/I18N.md`](I18N.md).

## Limitações atuais

- Ownership e impacto de negócio são **sugestões** inferidas; não substituem governança interna.
- Heatmaps e rankings são derivados dos dados do modelo e das heurísticas — não são pentest.
- PDF HTML usa `xhtml2pdf`; layouts muito complexos podem exigir ajustes futuros de CSS.

## Próxima rodada (sugestão)

- Diagramas raster embutidos no PDF (opcional).
- Mais métricas por metodologia quando o motor expuser campos adicionais por lente.
