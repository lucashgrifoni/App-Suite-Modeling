# Decisão de gate — E2E critical vs smoke vs hybrid (B-08 / P1-3)

## Objetivo

Eliminar ambiguidade sobre o papel de **`e2e:critical`** no pipeline e a relação com **smoke** e **hybrid**.

## O que cada camada cobre

| Suite | Comando / job CI | O que cobre |
|-------|------------------|-------------|
| **Smoke** | `npm run e2e:smoke:portable` → job `web-e2e-smoke` | Caminho mínimo da UI contra **stack mockada** (rápido, baixo custo). |
| **Critical** | `npm run e2e:critical` → job `web-e2e-critical` | Jornadas **críticas** do produto (cockpit, diff, export, etc.) contra **stack mockada**, com maior profundidade que smoke. |
| **Hybrid** | `npm run e2e:hybrid` → job `hybrid-e2e` | UI + **API Python real** + Vite; valida integração vertical próxima de produção (mais lento, mais infra). |

## Decisão de política

- **`e2e:critical` é gate obrigatório em PR/push** (job dedicado `web-e2e-critical` no mesmo workflow que smoke e hybrid).
- **Smoke** permanece como **primeira linha** rápida na mesma fase de UI.
- **Hybrid** **complementa** e **não substitui** critical: valida contratos e stack real, mas não duplica todas as jornadas do critical; por isso ambos coexistem.

## Por que critical é obrigatório

- Garante regressões funcionais nas jornadas de maior valor de utilizador sem subir a API Python em cada execução (custo/latência menores que hybrid puro para tudo).
- O hybrid já cobre risco de **desalinhamento API↔UI**; o critical cobre **fluxo de produto** de forma estável e reprodutível.

## Risco residual aceite

- Diferenças de comportamento entre **mock** e **API real** podem não ser apanhadas apenas pelo critical; mitigado pelo job **hybrid-e2e**.
- Playwright depende de browsers e timing: flakes devem ser tratados com retries e selectors estáveis (fora do âmbito deste documento).

## Revisão

Rever quando:

- o mock passar a espelhar 100% o contrato OpenAPI gerado;
- houver orquestração única (ex.: Testcontainers) que unifique critical+hybrid sem duplicação.
