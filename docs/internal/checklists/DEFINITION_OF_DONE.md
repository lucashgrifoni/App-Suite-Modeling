# Definition of Done — App Suite Modeling

Regras práticas para considerar uma **mudança** pronta para merge na `main` (ou branch de release). Complementa CI e [`RELEASE_ENGINEERING_CHECKLIST.md`](RELEASE_ENGINEERING_CHECKLIST.md).

---

## 1. O que significa “pronto”

Uma alteração está **pronta** quando:

- Cumpre o objetivo acordado no PR/issue **sem** expandir escopo (sem “aproveitar” para features não pedidas).
- **Gates** abaixo passam ou a falha é **explícita**, aceite por escrito e rastreada.
- Documentação e contratos afetados foram **atualizados na mesma entrega** (não deixados para “depois”).

---

## 2. Gates que devem passar (por tipo de mudança)

| Tipo de mudança | Gates mínimos |
|------------------|---------------|
| **Qualquer** | `python -m pytest` na raiz (suíte relevante verde; sem ignorar falhas novas). |
| **API FastAPI** | `python scripts/verify_openapi_up_to_date.py` **ou** `npm run contracts:verify` em `apps/web` após regenerar contrato se necessário. |
| **Web (TS/React)** | `npm run typecheck` + `npm run build` em `apps/web` (ou variantes `:portable` no Windows). |
| **Fluxo crítico na UI** | Considerar `npm run e2e:critical`; se o fluxo toca API+UI, validar [`CONTRACTS_CI_HYBRID.md`](../../architecture/CONTRACTS_CI_HYBRID.md) / `e2e:hybrid` quando aplicável. |
| **Motor / diff / import** | Testes unitários ou de integração que cubram o caminho alterado; atualizar **goldens** ou **expectations** se a saída canónica mudou (ver secção 5). |

---

## 3. OpenAPI e tipos TypeScript

**Atualizar** `contracts/openapi.json` e `apps/web/src/types/generated/openapi.d.ts` quando:

- Adicionar ou alterar endpoints, `response_model`, query/body schemas ou códigos de erro documentados no contrato.
- Mudar campos Pydantic expostos na API.

**Como:** `cd apps/web && npm run contracts:sync`, depois `contracts:verify` e `typecheck`.

**Não fazer merge** com OpenAPI desatualizado em relação ao código (o gate `verify_openapi_up_to_date` deve falhar de propósito até corrigir).

---

## 4. Documentação

**Atualizar na mesma PR** quando:

- Comportamento **visível** ao utilizador (CLI, API, UI) mudar.
- Limitações, pré-requisitos ou comandos de validação mudarem (`README`, `docs/*.md` afetados).
- Versão ou escopo de release forem tocados (`CHANGELOG`, notas de release, freeze).

**Não é obrigatório** reescrever docs não relacionadas; manter links e versões **coerentes** com `pyproject.toml` e `apps/web/package.json`.

---

## 5. Testes, goldens e benchmarks

- **Novos comportamentos:** incluir testes que falhem sem a correção e passem com ela.
- **Regressões:** teste de regressão mínimo no mesmo domínio.
- **Goldens HTTP / fixtures JSON** (ex.: expectativas semânticas da API): atualizar **só** quando a mudança for **intencional** e revisada; nunca “verde a custo de apagar” sem entender o diff.
- **Benchmarks / waves:** se existir benchmark associado ao módulo, manter ou atualizar conforme convenção do ficheiro de teste (ex.: `test_modeling_benchmark_*`).

---

## 6. Impacto em UI, API e motor

| Camada | Obrigações |
|--------|------------|
| **API** | OpenAPI + tipos TS + testes Python (`tests/test_api.py` ou equivalente) + documentação de erro/contrato se aplicável. |
| **UI** | Typecheck, build, microcopy coerente; E2E se o fluxo for crítico ou novo. |
| **Motor (threat engine, diff, import)** | Testes no pacote afetado; diff semântico / versão de contrato se alterar formato estável (`comparison_contract_version`, etc.). |

---

## 7. O que não entra sem evidência suficiente

- Alterações que **quebrem** contratos públicos (`/v1/`, CLI estável, formatos de export) **sem** CHANGELOG, nota de migração ou bump de versão acordado.
- **Silenciar** falhas de teste, gates de contrato ou lint.
- **Segredos** ou dados reais de clientes em fixtures ou logs.
- **Workarounds** “temporários” em código crítico **sem** comentário de contexto + issue/rastreio (evitar acumular dívida opaca).

---

## Referências

- Checklist de release (engenharia): [`RELEASE_ENGINEERING_CHECKLIST.md`](RELEASE_ENGINEERING_CHECKLIST.md)
- Congelamento de escopo: [`ENGINEERING_CLOSEOUT_SCOPE.md`](../decisions/ENGINEERING_CLOSEOUT_SCOPE.md), [`RELEASE_SCOPE_FREEZE.md`](../decisions/RELEASE_SCOPE_FREEZE.md)
