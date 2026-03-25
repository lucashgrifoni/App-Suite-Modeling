# PLOT4ai — sistemas com IA / LLM

## Quando usar PLOT4ai

- Aplicações com **LLM** (chat, completion, assistentes).
- Arquitecturas com **RAG**, **embeddings** ou **vector DB**.
- **Agentes** com tool-use / function calling / orquestração.
- Integrações com **fornecedores de modelo** (APIs alojadas).
- Equipas que querem **threat modeling incremental** sem motor separado apenas para IA: a lente PLOT4ai reutiliza o pipeline STRIDE existente e acrescenta heurísticas e relatório especializado.

## O que o projeto considera “AI system” (heurístico)

Um **sistema AI** no OTM é inferido por **sinais textuais e estruturais** no `ThreatModelDocument`:

- Metadados, tags, `business_context`, nomes de componentes, tecnologias, fluxos, ativos.
- Palavras-chave distribuídas por **camadas** (interação com modelo, prompt, retrieval, vector, agente, fornecedor, pipeline/governança).

Isto **não** valida que o serviço existe em produção nem a topologia real — é uma **aproximação** para workshops e documentação as-code.

## Arquitectura incremental

| Peça | Responsabilidade |
|------|------------------|
| `otm_threat_engine/ai_modeling/signals.py` | Agrega texto do documento → `AiSignalBundle` por camada. |
| `otm_threat_engine/ai_modeling/heuristics.py` | Heurísticas `plot4ai_*` condicionais (RAG+vector, agente externo, etc.). |
| `otm_threat_engine/ai_modeling/summary.py` | Constrói `AiSystemContextSummary` e agrupa ameaças por camada. |
| `otm_threat_engine/ai_modeling/explanations.py` | Frases de explicabilidade `AI_SPECIALIZED_RATIONALE` no merge global. |
| `methodology_lenses/plot4ai.py` | Orquestra boosting STRIDE, heurísticas, recomendações, insights e resumo. |

Compatível com o **multi-engine**: PLOT4ai é uma lente aplicada após o núcleo STRIDE.

## Contrato na análise

- `methodology_insights`: blocos por **camada** (rótulos em português).
- `ai_system_context`: `synopsis`, `pattern_tags`, `layers[]`, `primary_risk_surfaces`, `prioritized_recommendations`, `sensitive_data_notes`, `heuristic_ids_by_layer`.
- `explanations`: entradas com `type=ai_specialized_rationale` / `category=ai_modeling` quando aplicável.

## Limites da deteção

- **Falsos negativos**: modelo YAML mínimo sem vocabulário AI pode não disparar sinais.
- **Falsos positivos**: palavras como “agent” ou “model” em outro contexto podem activar camadas — interpretar como *hipótese*.
- Não há hoje ingestão automática de **OpenAPI/K8s** apenas para PLOT4ai; a trilha de importação assistida é partilhada — evolução futura: etiquetas `ai_signal` nos componentes importados.

## Interpretação dos resultados

1. Ler `ai_system_context.synopsis` e `pattern_tags`.
2. Cruzar `heuristic_ids_by_layer` com a lista de ameaças `plot4ai_*`.
3. Usar `prioritized_recommendations` como *backlog de conversa*, não como controlos fechados.
4. Explicabilidade com `confidence=low` indica **hipótese fraca** — validar com dados reais.

## Roadmap sugerido

- Mapear imports (OpenAPI/K8s) → reforço de `AiSignalBundle` com prova de origem.
- Políticas por área (máx. N heurísticas plot4ai por execução).
- Framework refs específicos OWASP LLM / NIST AI RMF (quando catálogo estiver alinhado).
- UI: filtros por camada sem aumentar a página principal.
