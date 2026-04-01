# Guia de screenshots — App Suite Modeling (otm-web)

Sugestões para README, GitHub Social Preview e posts de demo. Preferir **tema dark** (principal), resolução **1440×900** ou **1920×1080**, zoom do browser **100%**, sem DevTools visíveis.

## Pré-requisitos rápidos

- API de desenvolvimento acessível se precisar de dados reais; para séries uniformes pode usar modelo criado em branco + fluxo mínimo.
- **Social preview:** após deploy, validar `og:image` (`/og-image.png`) e metadados; crawlers podem exigir URL absoluta — nesse caso configurar `og:url` / base no hosting ou documentação do projeto.

## Estados ideais por ecrã

| Ecrã | Rota | Estado recomendado para captura | O que deve aparecer |
|------|------|----------------------------------|----------------------|
| Home | `/` | Tema dark, scroll no topo | Hero com título *Threat modeling, passo a passo*, CTAs, coluna “Porquê usar”; opcional segunda captura com **Pipeline técnico** (grid 6 passos). |
| Assistente | `/wizard` | Após “Criar novo modelo” ou template | Stepper visível, passo **Contexto** com título do modelo preenchido. |
| Análise | `/analysis` | Após **Gerar análise** com sucesso | Grid de métricas (incl. Maior L×I com barra), lista de ameaças com L×I; filtros visíveis mas não obrigatórios no crop. |
| Exportar | `/export` | Com sessão ativa | Cartão **Formatos** com checkboxes; ideal incluir **Descarregar** após “Gerar ficheiros” numa segunda imagem. |
| Diff | `/diff` | Com sessão + JSON de revisão + **Comparar** executado | Cartão **Resumo** + secção **Mudanças por secção** com pelo menos um bloco com alterações (para não parecer vazio). |

## Telas prioritárias (referência)

1. **Home (`/`)** — Hero completo ou pipeline em grid.
2. **Assistente (`/wizard`)** — Stepper + contexto preenchido.
3. **Diagrama (`/review`)** — Canvas com fluxos quando existir modelo.
4. **Análise (`/analysis`)** — Métricas e ameaças pós-motor.
5. **Exportar (`/export`)** — Formatos e, se possível, descargas.
6. **Diff (`/diff`)** — Resultado de comparação com resumo legível.

## Consistência visual

- Usar o mesmo **tema** (dark ou light) em todas as capturas de uma série.
- Incluir **header** da app (logo OTM + navegação) para branding coerente.
- Evitar dados sensíveis reais; usar modelos de exemplo ou texto genérico.

## Metadados e favicon

- `index.html`: título, descrição, `og:title`, `og:description`, `og:image` (`/og-image.png`, 1200×630), `og:image:alt`, `twitter:card` (`summary_large_image`), `twitter:image`, `favicon.svg`.
- Para partilhas em redes, validar preview quando o site estiver num domínio público (ferramentas de debug de OG do fornecedor).
