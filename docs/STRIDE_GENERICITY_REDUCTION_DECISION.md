# Redução de genericidade residual do STRIDE (decisão técnica)

## Problema atual

O STRIDE base é, por natureza, mais genérico e tende a gerar **múltiplos achados “corretos porém repetitivos”** quando o modelo já possui achados `biz_*` que descrevem melhor a **mesma causa raiz** (ex.: replay de webhook, mismatch pagamento→entitlement, stacking de cupom).

Efeito observado:

- O `report.md` fica com **dominância narrativa** de STRIDE genérico (principalmente `tampering`/`elevation_of_privilege`) que compete com achados `biz_*`.
- O `analyze.json` precisa **preservar rastreabilidade** (não pode “sumir” achado).

## Definição objetiva de “feito” (esta rodada)

Considerar sucesso **somente** se, para `finance` e `ecommerce-subscription`:

- **`report.md`**: reduzir itens STRIDE genéricos redundantes quando já existir `biz_*` cobrindo a mesma causa raiz/cluster temático, mantendo leitura mais coesa.
- **`analyze.json`**: **nenhuma perda** de rastreabilidade (sem remoção de achados no JSON).
- Evidência objetiva de before/after comparável.

## Por que esta ordem (baixo risco → maior impacto)

- **Etapa 1 (apresentação)**: deduplicação/cluster no exporter Markdown é o maior ganho com menor risco porque **não altera o motor** nem o JSON.
- **Etapa 2 (apresentação)**: agrupamento por categoria melhora leitura sem mexer em heurísticas.
- **Etapa 3 (motor)**: reduzir geração de STRIDE na origem tem risco moderado (pode remover cobertura útil); só vale se 1+2 não resolverem o critério central.

## O que mexe só em apresentação vs. motor

- **Somente apresentação (Markdown)**:
  - Supressão conservadora por clusters temáticos quando há `biz_*` correlato (sem apagar do JSON).
  - Bloco curto “Categorias de risco (top)”.
- **Motor (opcional / não executado nesta rodada)**:
  - Caps/limites por alvo quando `biz_*` já cobre causa raiz.
  - Redução de ruído em `ComponentKind.USER`.

## Riscos por etapa

- **Etapa 1**:
  - Suprimir demais e esconder sinal útil no `report.md` (mitigação: regras conservadoras, só `tampering`/`eop`, por famílias `biz_*`).
  - Regra frágil por string exata (mitigação: tokens por família + alvo/flow/tema; ainda heurístico e documentado).
- **Etapa 2**:
  - Inflar texto (mitigação: top‑N curto por categoria).
- **Etapa 3**:
  - Perda real de cobertura (mitigação: testes extras + evidência before/after; só executar se necessário).

## Critérios de parada

Parar após Etapas 1 e 2 se:

- houver redução observável de STRIDE genérico redundante no `report.md` (finance + e-commerce),
- e `analyze.json` permanecer intacto,
- e os testes obrigatórios passarem.

## Limitações conhecidas (honestidade técnica)

- STRIDE **permanece genérico por construção**; a meta é reduzir sua dominância narrativa quando `biz_*` é mais explicativo.
- A supressão é **apenas de apresentação** e baseada em clusters semânticos controlados; não é “prova” de equivalência perfeita.

---

## Anexo — plano e validação (consolidado)

**Escopo:** alterações cirúrgicas no exporter Markdown (`packages/exporters/otm_exporters/analysis_markdown.py`); evidência em fixtures **finance** e **ecommerce-subscription**. Fora de escopo: refactor amplo do motor, alteração de schema OTM, novos fixtures dedicados só para este fim.

**Testes:** regressão com `python -m pytest`. Evidência before/after reproduzível:

```bash
python scripts/run_stride_genericity_before_after.py
```

