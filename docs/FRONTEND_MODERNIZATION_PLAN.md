# Plano de modernização do frontend (otm-web)

**Data:** 2026-04-01  
**Versão app:** otm-web v0.1.0  
**Objetivo:** elevar UI/UX para produto premium (threat modeling / security engineering), com design system tokenizado, dark-first, sem quebrar rotas, API ou smoke E2E.

---

## 1. Diagnóstico da UI atual

### 1.1 Estado geral

- **Stack sólida:** React 18, TS, Vite 5, Tailwind, React Router — adequada para evolução incremental.
- **Visual:** MVP funcional com estética **light** genérica (fundo `#f4f7fb`, primário azul `#1e40ff` em CSS vars), pouco alinhado a uma identidade “security tool” premium.
- **Tailwind:** `extend` mínimo (só `fontFamily`); a maior parte do estilo vem de classes ad-hoc (`slate-*`) e variáveis `--asm-*` parcialmente usadas.
- **Layout:** `AppLayout` com header simples, `max-w-5xl`, navegação condicional quando há documento; **sem sidebar**; footer informativo.
- **Componentes UI:** pequenos e legíveis, porém **sem sistema de variantes** rico (Card sem variantes; Button com 4 variantes acopladas a cores antigas).

### 1.2 Inconsistências visuais

- Mistura de **identidade** (`--asm-primary` azul) com **Tailwind slate** sem tokens semânticos compartilhados.
- Títulos de página variam (`text-2xl` vs `text-xl`) sem escala tipográfica oficial.
- Cards e painéis usam bordas `slate-100/200` sem hierarquia de “superfície” (elevated vs inset).
- Badges/Alerts com **sky/amber** genéricos; sem ligação à paleta verde institucional pedida.

### 1.3 Hierarquia, espaçamento e tipografia

- Espaçamento vertical razoável (`space-y-6/8`), mas **sem grid de tokens** (4/8/12 documentado).
- Falta **display vs body** distinto: apenas DM Sans em todo o app.
- Home com hierarquia ok; páginas densas (Analysis, Diff) com **blocos de texto longos** sem `SectionHeader` / painéis consistentes.

### 1.4 UX — pontos fracos

- **Empty states** fracos (ex.: Templates: uma linha de texto; Analysis: mensagem mínima sem ilustração estrutural).
- **Loading:** poucos skeletons; estados “A carregar…” apenas em botões.
- **Wizard:** stepper funcional mas visualmente “pílulas” genéricas; pouca sensação de progresso premium.
- **Import:** input file nativo sem área de drop destacada.
- **Diff:** comparação útil, mas **added/removed/changed** podem ganhar codificação visual mais forte (sem alterar semântica).

### 1.5 Layout

- Largura máxima fixa modesta; produto “dashboard técnico” beneficiaria de **shell** mais amplo e ritmo entre hero → conteúdo.
- Header não comunica “ferramenta profissional” (sem camadas, sem marca visual forte).

### 1.6 Gaps de design system

- Ausência de **tokens** centralizados (cor, radius, sombra, blur, motion, z-index, focus).
- Sem camada **patterns** (PageHeader, EmptyState, StatCard reutilizável).
- Sem documentação de fundações além do código.

### 1.7 Riscos de performance

- React Flow já é dependência pesada nas rotas que usam diagrama (Review pode evoluir); evitar **bibliotecas de animação** pesadas por padrão.
- Muitas **box-shadows** e **backdrop-blur** podem custar em hardware fraco — usar com moderação e `will-change` só onde necessário.
- Evitar re-renders: novos contextos (ex.: tema/toast) devem ser **memoizados** e escopados.

### 1.8 Riscos de acessibilidade

- Contraste em modo **dark + verdes** precisa validação (texto sobre superfícies).
- Foco: inputs usam `ring` genérico; padronizar **focus ring** com tokens.
- Motion: obrigatório respeitar **`prefers-reduced-motion`**.
- Estados de erro não devem depender só de cor (ícones/texto já ajudam — manter).

### 1.9 Riscos de regressão

- **Smoke E2E** depende de strings e seletores: `h1` “Threat modeling, passo a passo”, botão “Criar novo modelo”, `#methodology`, “Gerar análise”, “Heurísticas novas”, texto de ameaça, “Exportar resultados”, “Gerar ficheiros”, `h2` “Descarregar”.
- Qualquer mudança de copy ou remoção de `id` em selects quebra o teste.

---

## 2. Plano de evolução por prioridade

| Prioridade | Entrega |
|------------|---------|
| P0 | Tokens + Tailwind + `index.css` dark-first + variáveis light preparadas |
| P0 | Refatorar primitives: Button, Card, Input, Select, Badge, Alert, Checkbox, Label |
| P0 | Shell: AppLayout, fundo em camadas, navegação premium, footer |
| P1 | Patterns: PageHeader, SectionHeader, StatCard, EmptyState, Skeleton, Stepper, Panel, Surface, GlowDivider, badges de metodologia/framework/status |
| P1 | Páginas: aplicar linguagem visual sem alterar fluxo nem contratos |
| P2 | Motion via CSS (keyframes + utilitários), `prefers-reduced-motion`, lift sutil em cards |
| P2 | Toast leve (opcional) ou feedback via Alert aprimorado — preferir solução mínima com alta qualidade |
| P3 | Documentação: fundação, validação, handoff |

---

## 3. Arquivos a criar ou alterar (previsto)

### Criar

- `docs/FRONTEND_MODERNIZATION_PLAN.md` (este ficheiro)
- `docs/DESIGN_SYSTEM_FOUNDATION.md`
- `docs/FRONTEND_MODERNIZATION_VALIDATION.md`
- `docs/FRONTEND_MODERNIZATION_HANDOFF.md`
- `apps/web/src/design-system/tokens.ts`
- `apps/web/src/hooks/usePrefersReducedMotion.ts`
- `apps/web/src/components/patterns/PageHeader.tsx`
- `apps/web/src/components/patterns/SectionHeader.tsx`
- `apps/web/src/components/patterns/StatCard.tsx`
- `apps/web/src/components/patterns/EmptyState.tsx`
- `apps/web/src/components/patterns/Skeleton.tsx`
- `apps/web/src/components/patterns/Stepper.tsx`
- `apps/web/src/components/patterns/Panel.tsx`
- `apps/web/src/components/patterns/Surface.tsx`
- `apps/web/src/components/patterns/GlowDivider.tsx`
- `apps/web/src/components/ui/MethodologyBadge.tsx`
- `apps/web/src/components/ui/FrameworkTag.tsx`
- `apps/web/src/components/ui/StatusPill.tsx`
- `apps/web/src/components/motion/FadeIn.tsx` (wrapper leve)

### Alterar

- `apps/web/tailwind.config.js` — theme extend completo
- `apps/web/src/index.css` — tokens CSS, animações, base dark
- `apps/web/index.html` — fonte display opcional (Google Fonts)
- `apps/web/src/components/layout/AppLayout.tsx` — shell premium
- `apps/web/src/components/ui/*` — Button, Card, Input, Select, Badge, Alert, Checkbox, Label
- `apps/web/src/utils/wizardStepPill.ts` — integrar com Stepper/tokens ou deprecar uso direto
- `apps/web/src/pages/*.tsx` — todas as páginas listadas no pedido

### Justificativa curta por bloco

| Bloco | Porquê |
|-------|--------|
| Tokens + Tailwind | Fonte única de verdade visual; evita drift e facilita OSS |
| index.css | Variáveis CSS para gradientes, glass e motion sem JS |
| AppLayout | Primeira impressão “produto”; navegação clara e hierárquica |
| Primitives | Todos os fluxos passam por botões/cards/inputs — máximo impacto |
| Patterns | Reduz duplicação entre páginas e uniformiza hierarquia |
| Páginas | Aplicar sistema sem mudar lógica de negócio |
| Motion CSS | Leve, sem dependência extra; respeita reduced-motion |
| Docs | Onboarding de contribuidores e critérios de aceitação |

---

## 4. Critérios de saída da Fase 1

- [x] Diagnóstico documentado
- [x] Riscos e mitigação identificados (E2E, a11y, performance)
- [x] Lista de ficheiros e prioridades acordada para implementação

**Próximo passo:** FASE 2 — implementação de tokens e documentação `DESIGN_SYSTEM_FOUNDATION.md`.
