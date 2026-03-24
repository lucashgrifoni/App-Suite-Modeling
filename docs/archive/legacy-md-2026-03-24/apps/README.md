# Aplicações (`apps/`)

Entregáveis finais que **orquestram** os pacotes em `packages/`.

| App | Stack | Papel |
|-----|--------|--------|
| `api/` | FastAPI, Uvicorn | HTTP, OpenAPI, persistência futura |
| `cli/` | Typer | Mesmas operações de alto nível que usuários esperam em CI |
| `web/` | Vite, React, TypeScript | Interface; consome API; não duplica o motor de ameaças |

Desenvolvimento local típico: instalar o projeto Python em modo editável na raiz; em `web/`, `npm install` e `npm run dev`.
