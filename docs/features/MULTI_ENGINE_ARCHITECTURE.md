# Arquitetura Multi-Engine (base)

Este documento define a base para suportar múltiplas metodologias sem aumentar a complexidade do produto.

## Objetivo

- **Simplicidade para o utilizador** (CLI/UI/API com a mesma experiência de escolha).
- **Fonte única de verdade** no core/schema.
- **STRIDE como default oficial**.
- Outras metodologias como engines opcionais e principais quando escolhidas:
  - `linddun`
  - `nist_data_centric`
  - `octave_allegro`
  - `cia_die`
  - `pasta`
  - `plot4ai`

## Decisões de arquitetura

1. **Uma API de análise só** (`analyze_document`) com parâmetros de seleção de metodologia.
2. **Sem duplicar motor inteiro agora**: base STRIDE + “lente metodológica” inicial por engine.
3. **Recomendação automática centralizada** no pacote `otm_threat_engine`:
   - reutilizável por CLI, API e UI.
4. **Schema canônico guarda a metodologia escolhida** (`model.methodology`).

## Estrutura de módulos

- `otm_core_schema.enums.ThreatModelMethodology`
- `otm_core_schema.document.ModelInfo.methodology`
- `otm_threat_engine.methodologies`
  - `ThreatModelingEngine` (abstração leve)
  - `recommend_methodology(doc)`
  - `apply_methodology_lens(result, methodology=...)`
- `otm_threat_engine.engine`
  - `_analyze_stride_core` (núcleo atual)
  - `analyze(..., methodology=..., auto_recommend=...)`
- `otm_threat_engine.result.AnalysisResult`
  - `methodology`
  - `methodology_recommendation_reason`

## Regras iniciais de recomendação

- **STRIDE**: web, API, híbrido, cloud-native (default técnico).
- **LINDDUN**: privacidade, LGPD, GDPR, PII.
- **NIST Data-Centric**: dados críticos, pagamentos, saúde, classificação de dados.
- **OCTAVE Allegro**: foco em ativos e risco organizacional.
- **CIA/CIA-DIE**: workshops rápidos, visão executiva, iniciantes.
- **PASTA**: contexto enterprise/avançado orientado a ataque, vulnerabilidade, risco e impacto.
- **PLOT4ai**: sistemas de IA/LLM, RAG, agentes e pipelines de treino/inferência.

## Convenção de maturidade

- **Mature**: comportamento estável, default e maior cobertura prática.
- **Evolving**: já funcional, com evolução incremental ativa.
- **Specialized**: metodologia focada em contexto específico com profundidade dedicada.
- **Experimental**: conceito validado, ainda em validação de campo.

## Estado atual de maturidade (MVP+)

| Metodologia | Objetivo | Quando usar | Complexidade | Maturidade | Recomendação automática | Perfil ideal |
|-------------|----------|-------------|--------------|------------|-------------------------|--------------|
| STRIDE | Segurança técnica de sistemas | Web, API, microsserviços, cloud-native | Baixa-Média | **Mature** | Sim (fallback técnico/default) | AppSec/Dev |
| LINDDUN | Privacidade e proteção de dados pessoais | LGPD/GDPR, PII, consentimento | Média | **Evolving** | Sim (contexto de privacidade/PII) | Privacy/GRC |
| NIST Data-Centric | Proteção de dados críticos | Pagamentos, saúde, classificação de dados | Média | **Evolving** | Sim (dados críticos/setores sensíveis) | Data security |
| OCTAVE Allegro | Risco orientado a ativos/negócio | Contexto organizacional e gestão de risco | Média | **Evolving** | Sim (ativos/risco organizacional) | Risk managers |
| CIA / CIA-DIE | Análise simplificada e executiva | Workshops rápidos e iniciantes | Baixa | **Evolving** | Sim (workshop/visão executiva) | Liderança/Produto |
| PASTA | Análise avançada risk-centric | Enterprise, avaliação profunda de ataque/vulnerabilidade/impacto | Média-Alta | **Specialized** (fase 2) | Sim (sinais de análise avançada/risco/ataque) | Arquitetura + Red/Blue |
| PLOT4ai | Threat modeling de AI/LLM | LLM, RAG, agentes, inferência, treino, AI pipelines | Média | **Specialized** (fase 2) | Sim (sinais de IA/LLM/RAG/agentes) | AI security / ML |

## Como a engine influencia a análise (estado atual)

- `stride`: saída base do motor.
- `linddun`: reforça impacto para ameaças de privacidade/divulgação e adiciona heurísticas incrementais por categorias principais (linkability, identifiability, detectability, disclosure, unawareness, non-compliance), além de recomendações iniciais de consentimento, minimização, retenção e exposição.
- `nist_data_centric`: reforça foco em dados críticos/divulgação e adiciona notas de preparação para v1 (classificação, caminhos sensíveis e controles por contexto de dados).
- `octave_allegro`: adiciona marcação de lente para priorização de risco de negócio.
- `cia_die`: resume ameaças ativas para visão executiva (top score).
- `pasta`: reforça análise risk-centric, prioriza impacto e adiciona blocos estruturados (objetivos de negócio, escopo técnico, superfície de ataque, objetivos de atacante, vulnerabilidades correlatas, impacto e achados orientados a risco).
- `plot4ai`: reforça ameaças de IA e adiciona subdomínios incrementais (interação com modelo, prompt/input, retrieval/grounding, agent action/tool execution, data leakage, governança de pipeline).

> STRIDE continua a metodologia default e a mais madura. As demais já são suportadas pela arquitetura e influenciam a análise por recomendação + lentes, com evolução nativa incremental.

## Exemplos de uso

### CLI

```bash
# explicitamente STRIDE (default)
otm analyze modelo.otm.yaml --methodology stride

# recomenda automaticamente e aplica
otm analyze modelo.otm.yaml --auto-methodology

# contexto enterprise avançado
otm analyze modelo.otm.yaml --methodology pasta

# contexto AI/LLM
otm analyze modelo.otm.yaml --methodology plot4ai

# só recomendar, sem analisar
otm recommend-methodology modelo.otm.yaml
```

### API

```json
POST /v1/models/analyze
{
  "document": { "...": "..." },
  "methodology": "linddun"
}
```

```json
POST /v1/models/recommend-methodology
{
  "document": { "...": "..." }
}
```

### UI (fluxo atual)

1. “Análise” mostra seletor de metodologia (default `stride`, ou valor atual do documento).
2. UI exibe hint curto estático para cada metodologia ao lado do seletor (apresentação apenas).
3. Botão “Recomendar metodologia” chama `/v1/models/recommend-methodology`.
4. UI exibe motivo da recomendação e permite override manual antes de analisar.

## Plano incremental (sem overengineering)

1. **Base pronta** (esta fase): enum no schema, seleção de metodologia, recomendação, lente inicial.
2. **UX unificada**: expor seletor na UI e `--methodology` no onboarding da CLI.
3. **Heurísticas dedicadas por engine**: evolução por metodologia (uma de cada vez, com testes).
4. **Packs por metodologia**: opcional, mantendo contratos estáveis.

## Preparação NIST Data-Centric v1 (esta rodada)

Base preparada, sem motor novo:
- Notas estruturadas no resultado para orientar classificação de dados críticos.
- Direção para mapear caminhos de dados sensíveis ponta a ponta.
- Direção para reforçar controles por estado do dado (repouso, trânsito, uso).
