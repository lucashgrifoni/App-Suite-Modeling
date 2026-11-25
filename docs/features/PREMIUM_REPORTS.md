# Relatório de riscos

O App Suite Modeling gera PDF e Markdown a partir da análise do motor e das decisões registradas no modelo. A leitura começa pelo resumo executivo e pelo ranking. O relatório mostra a prioridade calculada, o estado de tratamento e a justificativa registrada para as ameaças declaradas, inclusive para as que ficam sem pontuação. As sugestões ainda sem tratamento aparecem como **Sem decisão**.

A capa destaca o total de ameaças do relatório. O resumo de tratamento mostra os estados registrados e inclui as sugestões que aguardam triagem no grupo a triar ou tratar.

## Exposição e prioridade

O total da capa inclui as ameaças declaradas, os registros históricos e as sugestões deduplicadas. A exposição ativa inclui as ameaças que ainda representam risco e as sugestões pendentes de triagem. A distribuição por severidade usa as ameaças ativas com pontuação.

- Ameaças novas, triadas e em andamento entram no ranking quando têm pontuação. Decisões sem pontuação aparecem na seção de tratamento.
- Riscos aceitos continuam na exposição ativa e têm uma fila própria de revisão. A fila mostra responsável, data de revisão e justificativa. Dados ausentes ficam sinalizados.
- Riscos sem correção prevista continuam na exposição e no fluxo de ação para revisão da decisão.
- Mitigações ainda por verificar, riscos residuais e falsos positivos aguardando confirmação continuam na exposição. Os encerramentos registrados permanecem no histórico e no total da capa.

O ranking do relatório unificado usa a classificação dos ativos como sinal adicional. Ameaças de modificação, divulgação ou elevação de privilégio relacionadas a dados restritos recebem um acréscimo de 0,04 na pontuação composta. A severidade de origem permanece igual. No resultado estruturado, os grupos de causa raiz mantêm os IDs das ações de remediação e as referências aos achados que as originaram.

No modelo YAML ou JSON, registre o responsável em `assignee`, a justificativa em `treatment_notes` e a data de revisão em `metadata.risk_review_date`, no formato `AAAA-MM-DD`. Para registrar a verificação, use `metadata.treatment_verification` na ameaça específica:

| Estado | Registro para sair da exposição |
|---|---|
| `mitigated` | `outcome: risk_closed`, `reference` com a evidência de verificação e uma mitigação `verified` vinculada à ameaça em `threat_ids`. |
| `false_positive` | `outcome: false_positive_confirmed`, `reference` com a evidência da triagem e justificativa em `treatment_notes`. |

O relatório aplica a classificação aos registros do modelo. O revisor pode consultar a referência indicada para avaliar a evidência.

O PDF organiza o conteúdo em cinco seções: resumo executivo com gráfico de severidade, tabela de prioridades, cartões de decisões, diagrama de arquitetura e próxima revisão. Os fluxos e as fronteiras vêm do modelo. Justificativas longas continuam nas páginas seguintes. As prioridades e as ações sugeridas são heurísticas. Confirmar os controles exige evidência do ambiente.

## Interface

Em **Exportar**, escolha o idioma e baixe o **Relatório de riscos** em PDF ou Markdown. Os artefatos técnicos, como o modelo em JSON e o diagrama Mermaid, têm controles próprios. No **Histórico**, os dois formatos usam o modelo e a análise da revisão selecionada. Quando a revisão salva contém somente o modelo, o serviço executa uma análise na exportação e o relatório identifica essa origem.

Em **Análise**, selecione **Risco aceito** ao registrar ou editar a decisão. O responsável e a data de revisão ficam no modelo exportado e aparecem na fila de revisão do relatório.

Em **Mitigado** e **Falso positivo**, registre uma referência e confirme o resultado após consultar a evidência. Você pode salvar a referência antes da confirmação. O relatório só encerra o risco quando os critérios da tabela de exposição são atendidos.

A geração pelo navegador usa o serviço local. O PDF requer a dependência opcional instalada no serviço. Markdown fica disponível pelo mesmo fluxo.

## Linha de comando

```bash
otm report modelo.otm.yaml -o relatorio.md
otm report modelo.otm.yaml --format pdf --locale pt-BR -o relatorio.pdf
otm report modelo.otm.yaml --analysis-json analise.json --baseline analise-anterior.json
```

- `--format` aceita `markdown` (padrão) ou `pdf`.
- `--locale` aceita `pt-BR` (padrão) ou `en`. O idioma seleciona os rótulos do relatório, e os dados e justificativas do modelo seguem o idioma de origem.
- `--analysis-json` permite usar uma análise existente da mesma revisão. `--baseline` inclui a comparação com uma análise anterior do mesmo sistema.
- O PDF exige `pip install "open-threat-model[report]"` e as dependências nativas aplicáveis. `OTM_PREMIUM_LOGO_PATH` aceita uma imagem PNG personalizada de até 2 MB.
- Sem `-o`, o Markdown vai para a saída padrão e o PDF é gravado em `report-premium.pdf` no diretório atual. Use `-o` para escolher o destino.

## API

`POST /v1/reports` recebe `document` e `analysis`, ou `document` e `run_analysis: true`. Aceita também `baseline_analysis`, `locale` e `output_format`. A resposta tem tipo `text/markdown` ou `application/pdf`.

## Migração

A opção `--level standard` funciona como o comando sem nível. Os níveis explícitos `executive` e `deep` da linha de comando e a rota `POST /v1/reports/premium` continuam disponíveis para integrações existentes, com a apresentação anterior. Os PDFs desses caminhos de compatibilidade têm rótulos em inglês. Para novos consumidores, use `otm report` ou `POST /v1/reports`.
