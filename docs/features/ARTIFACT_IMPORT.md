# Importação assistida de artefactos

Geração **semiautomática** de rascunho (`ThreatModelDocument`) a partir de evidência de infraestrutura e API. Isto **não** é análise de ameaças final: o motor (`analyze`) continua a ser o passo explícito após revisão humana.

## Princípios

- **Inferência pragmática** com limites claros.
- **Transparência**: cada passo relevante produz `InferenceRecord` (mensagem, `confidence`, `source`, componentes relacionados).
- **Rascunho editável** no YAML canónico; tags `draft` e `artifact-import` em `metadata.tags`.
- **Texto de auditoria** também espelhado em `business_context.assumptions` para o ficheiro ser autónimo.

## Suportado (MVP)

| Origem | Entrada | O que é inferido |
|--------|---------|------------------|
| OpenAPI 3 / Swagger 2 | YAML/JSON | Superfície REST agregada, contagem de operações, `servers`/host, pistas de `securitySchemes`, fluxo cliente→API, fronteiras pública vs aplicação. |
| Terraform | `.tf` (ficheiro ou directório) | Blocos `resource "tipo" "nome"`; buckets/DB/filas/gateways/heurística `0.0.0.0/0`; **não** resolve módulos nem expressões HCL. |
| Kubernetes | YAML multi-doc ou directório | Ingress/Service/Deployment/ConfigMap; fluxos cliente→Ingress→Service→Deployment quando nomes coincidem; LoadBalancer como exposição. |
| Helm | — | Apenas **menção** quando existe `helm_release` em Terraform; charts não são expandidos. |

## Não suportado (ainda)

- Graph Terraform real (`terraform graph`), avaliação de HCL, state/plan JSON.
- Resolução de selectors K8s (apenas heurística por nome).
- Helm templates/rendering.
- Descoberta automática de PII em schemas OpenAPI.

## CLI

```bash
otm import openapi ./spec.yaml --output draft.otm.yaml --explain-out explain.json
otm import terraform ./infra --output draft.otm.yaml
otm import k8s ./manifests --output draft.otm.yaml
otm import repo ./meu-servico --json-out scan.json --draft-out draft.otm.yaml
```

Sem `--output`, o YAML é escrito para **stdout**.

### Comparar contratos antes de reimportar

```bash
otm import openapi-diff ./spec-anterior.yaml ./spec-revisada.yaml
```

A prévia em JSON lista operações adicionadas, removidas e alteradas por método e caminho. Mudanças em seções compartilhadas, como segurança e componentes, ficam visíveis para revisão. O modelo canônico segue como fonte das decisões do analista. Para comparar contratos que usam referências em itens de caminho, forneça as declarações correspondentes nos dois arquivos.

Na interface local, abra um modelo criado a partir de OpenAPI e acesse **Importar → Atualizar modelo com OpenAPI**. Envie o contrato usado na última importação e o contrato revisado. A prévia mostra as operações afetadas, os campos que podem ser atualizados e os conflitos com edições do modelo. **Aplicar alterações sem conflito** atualiza a sessão após a revisão. As decisões de tratamento, os vínculos existentes e as fronteiras revisadas permanecem no modelo. Remoções de entidades e mudanças de identidade exigem revisão manual. Exporte o modelo para salvar a nova versão.

### `otm import repo` — scan pragmático de repositório

`otm import repo` é um varredor heurístico **leve** sobre fontes Node/Express (`routes`, `upload`, `session`, `external fetch`, `eval`). A saída principal é o JSON de **inferências** (`--json-out`); use `--draft-out` para também emitir um `.otm.yaml` *semente* derivado dessas inferências (componentes-fronteira, ativos placeholder e fluxos a partir de rotas detectadas). O *draft* é deliberadamente mínimo — encadeia diretamente em `otm validate` / `otm analyze`, mas existe para ser editado por um humano, não como "modelo pronto".

## API (`/v1/imports`)

- `POST /v1/imports/openapi` — `multipart/form-data`, campo `file`.
- `POST /v1/imports/openapi/reimport-preview` — `multipart/form-data`, arquivos `previous` e `revised` (OpenAPI/Swagger) e `document` (modelo atual em JSON). Retorna a comparação de contratos, as alterações, os conflitos e o modelo proposto. A rota não grava o modelo.
- `POST /v1/imports/terraform` — um único `.tf`.
- `POST /v1/imports/kubernetes` — YAML multi-documento.

Resposta: `document` (canónico), `inferences[]`, `unknowns[]`, `assumptions[]`. Limite MVP: **2 MiB** por upload.

## Como rever o draft

1. Ler `business_context.assumptions` e alinhar com a realidade arquitectural.
2. Ajustar `trust_boundaries` e membros; desdobrar componentes agregados (ex.: uma API → vários domínios).
3. Completar `data_flows` e `assets` onde a inferência marcou `[não inferido]`.
4. Só depois executar `otm validate` e `otm analyze` (ou equivalente na UI/API).

## Limitações conhecidas

- **Confiança** (`high` / `medium` / `low`) é heurística interna, não prova de segurança.
- **Falsos negativos/positivos** são esperados em parsers light; revisão humana é obrigatória.

## Próximos passos sugeridos

- Parser HCL com biblioteca dedicada ou suporte a `terraform show -json`.
- Helm: render `helm template` opt-in.
- OpenAPI: opcionalmente um processo por `tag` ou por prefixo de path.
- API: pacotes zip para directórios alinhados à CLI.
