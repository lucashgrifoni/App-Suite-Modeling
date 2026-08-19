# UI Web (`apps/web`)

## Arquitetura

| Camada | Pasta | Função |
|--------|-------|--------|
| **API** | `src/api/` | Cliente HTTP (`fetch`) para `/api` (proxy Vite → FastAPI). Sem lógica de threat model. |
| **Tipos** | `src/types/` | Espelho leve dos contratos (`OtmDocument`, `AnalysisResult` parcial). |
| **Estado** | `src/context/SessionContext.tsx` | Documento + análise em memória; `sessionStorage` para refrescar sem perder rascunho. |
| **Páginas** | `src/pages/` | Fluxos: início, templates, assistente, revisão, análise, exportação. |
| **UI** | `src/components/ui/` | Botões, cartões, inputs — Tailwind, sem design system pesado. |
| **Layout** | `src/components/layout/` | Cabeçalho e navegação curta. |

A **validação**, o **motor STRIDE** e os **mapeamentos de framework** executam **só no backend**; a UI envia JSON e apresenta respostas.

## Fluxo do utilizador

1. **Início** — modelo em branco (POST `/v1/models`) ou **templates** (GET + POST instantiate).
2. **Assistente** — 4 passos: contexto, componentes, fluxos, conclusão (validação no servidor entre passos).
3. **Diagrama** — diagrama interactivo (React Flow) alinhado a `data_flows`, com lista de componentes e fluxos; JSON opcional para perfis técnicos.
4. **Análise** — POST `/v1/models/analyze`; filtros locais por score e framework (dados já vindos da API).
   - seletor de metodologia com `stride` default;
   - hint curto por metodologia (estático, apenas apresentação);
   - metadados visuais discretos: categoria, best for e maturidade;
   - recomendação via API (`POST /v1/models/recommend-methodology`);
   - motivo da recomendação exibido com possibilidade de override manual.
   - blocos de insights metodológicos (quando retornados pela API);
   - explicabilidade em blocos expansíveis curtos (sem poluir a tela);
   - para `plot4ai`, cartão compacto com camadas IA detectadas e ações prioritárias.
5. **Exportar** — POST `/v1/exports`; descarregar ficheiros gerados.

## Desenvolvimento

```bash
# Terminal 1 — API com CORS para localhost:5173
pip install -e ".[api]"
uvicorn otm_api.main:app --reload --port 8000

# Terminal 2 — UI (proxy `/api` → 8000)
cd apps/web && npm install && npm run dev
```

Variável opcional: `VITE_API_PREFIX` (default `/api`) se o proxy for diferente.

Se a porta 8000 já estiver ocupada, mova a API e o proxy em conjunto com `OTM_API_PORT`; para um backend remoto ou em container, `OTM_API_URL` substitui a origem inteira:

```bash
# Terminal 1
OTM_API_PORT=8123 uvicorn otm_api.main:app --reload --port 8123

# Terminal 2 — proxy `/api` → 8123
cd apps/web && OTM_API_PORT=8123 npm run dev
```

## Troubleshooting de build (Windows)

Em alguns ambientes Windows com projeto em caminho contendo `&`, os wrappers `.cmd` de `npm run` podem resolver paths incorretos para `vite`/`tsc`.

Sintoma típico:
- `Cannot find module 'C:\Users\...\Downloads\vite\bin\vite.js'`
- `Cannot find module 'C:\Users\...\Downloads\typescript\bin\tsc'`

Workaround imediato (validado):

```bash
node ./node_modules/typescript/bin/tsc --noEmit
node ./node_modules/vite/bin/vite.js build
```

Impacto:
- Código da UI pode estar saudável mesmo quando `npm run build` falha por resolução de path do wrapper.

## Guia robusto para Windows (paths e build)

Recomendação de ambiente:
- Preferir caminho sem `&` para o workspace quando possível.
- Exemplo preferido: `C:\workspace\app-suite-modeling`

Quando usar build portátil:
- Se `npm run build` ou `npm run typecheck` falhar com path truncado em `node_modules`.
- Use `npm run ci:build:portable` como caminho oficial.

Caminho recomendado para release validation em Windows:

```bash
cd apps/web
npm ci
npm run ci:build:portable
```

## Extensões futuras

- Autenticação e persistência multi-utilizador (API + BD). Ver
  [`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md) — hoje não há contas nem histórico centralizado.

O diagrama React Flow e a internacionalização estavam nesta lista e **já foram entregues**:
`apps/web/src/components/diagram/` e `apps/web/src/i18n/`, com cobertura em
`apps/web/e2e/diagram.spec.ts` e `apps/web/e2e/i18n.spec.ts`.

## Exemplos por metodologia (fluxo UI)

- `STRIDE`: escolha no seletor e execute análise direta.
- `LINDDUN`: escolha para foco em privacidade e riscos de dados pessoais.
- `NIST Data-Centric`: escolha para foco em dados críticos/classificados.
- `OCTAVE Allegro`: escolha para discussão de ativos e risco de negócio.
- `CIA/CIA-DIE`: escolha para workshops rápidos e visão executiva.
- `PASTA`: escolha para análise avançada orientada a risco/ataque.
- `PLOT4ai`: escolha para sistemas de IA/LLM e fluxos RAG/agentes.
