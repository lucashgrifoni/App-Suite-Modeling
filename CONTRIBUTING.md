# Contribuir

Obrigado pelo interesse em contribuir. Este projeto prioriza **simplicidade**, **testes** e **um único núcleo de domínio** partilhado por CLI, API e UI.

## Ambiente Python

- Python **3.11+**
- Criar venv, instalar em modo editável com extras de desenvolvimento:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev,cli,api]"
```

## Comandos úteis

```bash
python -m pytest
python -m ruff check packages apps tests
```

## Frontend (`apps/web`)

```bash
cd apps/web
npm install
npm run dev
```

## Pull requests

1. Uma alteração lógica por PR quando possível.
2. Incluir ou atualizar testes quando mudar comportamento do core ou contratos públicos.
3. Seguir o estilo existente (Ruff) e manter documentação alinhada se alterar a estrutura do repositório.

## Onde colocar código

- **Regra de negócio / schema:** `packages/*`
- **HTTP ou CLI:** `apps/api` ou `apps/cli` apenas como adaptadores
- **Decisões de arquitetura:** `docs/adr/` (ADRs curtos)

Ver [docs/MONOREPO.md](docs/MONOREPO.md) para o mapa completo do repositório.
