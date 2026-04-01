# Branding e Design System

Este documento define a identidade oficial do produto **App Suite Modeling**.

## Direção de marca

- Moderna, técnica e confiável.
- Tom premium/open source para AppSec, DevSecOps e Threat Modeling.
- Linguagem visual de proteção + análise + modelagem (escudo, grafo, lente).

Tagline sugerida: **Model. Analyze. Secure.**

## Paleta oficial

| Grupo | Nome | HEX | Função |
|------|------|-----|--------|
| Primária | `navy-deep` | `#0B1220` | Base institucional, confiança e contraste forte |
| Primária | `electric-blue` | `#1E40FF` | Ação principal, links e elementos de destaque |
| Secundária | `blue-strong` | `#0B2A8F` | Estados hover/ativo da primária |
| Secundária | `slate-ink` | `#1E293B` | Texto técnico secundário e labels |
| Acento | `signal-green` | `#00A36A` | Êxito, controles efetivos, status positivo |
| Acento | `signal-amber` | `#F59E0B` | Avisos, atenção e risco médio |
| Acento | `signal-red` | `#EF4444` | Falhas críticas, risco alto e destructive |
| Neutro | `canvas-light` | `#F4F7FB` | Fundo principal light |
| Neutro | `surface-light` | `#FFFFFF` | Cards e superfícies elevadas |
| Neutro | `border-soft` | `#D7E1EE` | Bordas discretas |
| Neutro | `text-strong` | `#0B1220` | Texto primário |
| Neutro | `text-muted` | `#475569` | Texto auxiliar |

### Modo dark (base)

| Token | HEX |
|------|-----|
| `dark-bg` | `#030712` |
| `dark-surface` | `#0B1220` |
| `dark-border` | `#1E293B` |
| `dark-text` | `#E2E8F0` |
| `dark-muted` | `#94A3B8` |

## Tokens de design (UI)

Mapeamento pensado para Tailwind + CSS variables:

- `--asm-bg`: fundo global
- `--asm-surface`: superfície de cards/painéis
- `--asm-text`: texto principal
- `--asm-text-muted`: texto secundário
- `--asm-primary`: botão principal/links de ação
- `--asm-primary-strong`: hover/active da primária
- `--asm-border`: borda padrão
- `--asm-success`: sucesso
- `--asm-warning`: warning
- `--asm-danger`: destructive

## Cores por metodologia (uso sutil)

| Metodologia | Cor sugerida | Uso recomendado |
|------------|--------------|-----------------|
| STRIDE | `#1E40FF` | Badge default e destaque neutro |
| LINDDUN | `#7C3AED` | Privacidade/compliance |
| NIST Data-Centric | `#0EA5E9` | Dados críticos e caminhos sensíveis |
| OCTAVE Allegro | `#F59E0B` | Risco de negócio/ativos |
| CIA/CIA-DIE | `#64748B` | Modo executivo simplificado |
| PASTA | `#C2410C` | Avançado/risk-centric |
| PLOT4ai | `#14B8A6` | Especializado AI/LLM |

Regra: usar apenas em acentos (badges, chips, ícones, bordas finas), nunca como fundo dominante.

## Sistema de logo (especificação)

### Conceito

Símbolo combinando:
- escudo (segurança),
- nós/conexões (modelagem de sistema),
- lente/sinal (análise de risco).

### Versões

- **Principal**: símbolo + wordmark “App Suite Modeling”.
- **Horizontal**: símbolo à esquerda, wordmark à direita.
- **Ícone**: símbolo isolado para favicon/avatar.
- **Dark**: marca clara sobre fundo escuro.
- **Light**: marca escura sobre fundo claro.

### Área de respiro e tamanho

- Área mínima de respiro: `0.5x` (onde `x` = altura do símbolo).
- Tamanho mínimo recomendado:
  - principal/horizontal: 140px largura
  - ícone: 24px

### Usos incorretos

- Não distorcer proporção.
- Não aplicar gradiente aleatório.
- Não trocar cores fora da paleta oficial.
- Não usar sobre fundo com baixo contraste.
- Não adicionar sombra pesada/glow.

## Aplicação da marca

- **README/docs**: usar nome oficial “App Suite Modeling”.
- **UI**: manter visual limpo com acentos de marca discretos.
- **CLI**: preservar texto simples; marca aparece em `--version` e docs.

## Guia para contribuidores

- Qualquer novo componente deve reutilizar tokens.
- Evitar “rainbow UI”; usar metodologias como reforço visual, não decoração.
- Priorizar legibilidade e contraste (WCAG AA).
