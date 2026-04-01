# PLOT4ai — sistemas com IA / LLM

## Quando usar PLOT4ai

- Aplicações com **LLM** (chat, completion, assistentes).
- Arquitecturas com **RAG**, **embeddings** ou **vector DB**.
- **Agentes** com tool-use / function calling / orquestração.
- Integrações com **fornecedores de modelo** (APIs alojadas).
- Rascunhos gerados por **import OpenAPI/Kubernetes/Terraform** quando o corpus derivado (`import_signals_corpus`) ou o diagrama OTM contém sinais claros de IA (paths `/embeddings`, labels, `aws_bedrock`, etc.).
- Equipas que querem **threat modeling incremental** sem motor separado apenas para IA: a lente PLOT4ai reutiliza o pipeline STRIDE existente e acrescenta heurísticas e relatório especializado.

## Quando **não** assumir PLOT4ai

- Sistemas de **workflow**, **motor de regras**, **filas batch** e **orquestração operacional** sem linguagem natural generativa, sem retrieval/vector para LLM e sem fornecedor de modelo — mesmo que pareçam “tecnológicos”.
- Evitar menções acidentais a `LLM`/`RAG` em frases *negativas* (“sem LLM…”): apesar do matching por token (`has_any_token`) reduzir ruído, escrever sem estes tokens evita ambiguidade desnecessária.
- Se `looks_like_ai_context` for falso, as heurísticas `plot4ai_*` **não** são acrescentadas (a lente ainda pode gerar `ai_system_context` para contexto de relatório, mas sem hipóteses plot4ai).

## O que o projeto considera “AI system” (heurístico)

Um **sistema AI** no OTM é inferido por **sinais textuais e estruturais** no `ThreatModelDocument`:

- Metadados, tags, `business_context`, nomes de componentes, tecnologias, fluxos, ativos.
- Campo opcional **`import_signals_corpus`**: texto agregado pelo import de artefactos (paths OpenAPI, tags/imagens K8s, recursos Terraform com pistas de IA).
- Palavras-chave distribuídas por **camadas** (interação com modelo, prompt, retrieval, vector, agente, fornecedor, pipeline/governança).

Isto **não** valida que o serviço existe em produção nem a topologia real — é uma **aproximação** para workshops e documentação as-code.

## Fixtures oficiais de calibração

| ID | Ficheiro |
|----|----------|
| otm-ai-001 … 005 | `examples/plot4ai-calibration/otm-ai-*.otm.yaml` — cenários IA positivos |
| otm-nai-001 | `examples/plot4ai-calibration/otm-nai-001-rules-workflow.otm.yaml` — negativo ambíguo (regras + filas, sem IA) |
| otm-nai-002 | `examples/plot4ai-calibration/otm-nai-002-analytics-automation.otm.yaml` — analytics/automação “quase IA” sem GenAI |

Índice breve: `examples/plot4ai-calibration/README.md`.

## Arquitectura incremental

| Peça | Responsabilidade |
|------|------------------|
| `otm_artifact_import/ai_import_corpus.py` | Deriva texto de sinais a partir de OpenAPI/K8s/Terraform/Helm → `import_signals_corpus`. |
| `otm_core_schema` `ThreatModelDocument.import_signals_corpus` | Transporte opcional até ao motor (default `None`). |
| `otm_threat_engine/ai_modeling/corpus.py` | Junta OTM + `import_signals_corpus` num corpus único. |
| `otm_threat_engine/ai_modeling/keyword_signal_apply.py` | Regras lexicais sobre o corpus (maintainability). |
| `otm_threat_engine/ai_modeling/signals.py` | Orquestra keywords + enriquecimento estrutural → `AiSignalBundle`. |
| `otm_threat_engine/ai_modeling/heuristics.py` | Heurísticas `plot4ai_*` condicionais (RAG+vector, agente externo, etc.). |
| `otm_threat_engine/ai_modeling/summary.py` | Constrói `AiSystemContextSummary` e agrupa ameaças por camada. |
| `otm_threat_engine/ai_modeling/explanations.py` | Merge de explicabilidade; blocos em `explanation_plot4ai_blocks.py`. |
| `methodology_lenses/plot4ai.py` | Orquestra boosting STRIDE, heurísticas, recomendações, insights e resumo. |

Compatível com o **multi-engine**: PLOT4ai é uma lente aplicada após o núcleo STRIDE.

## Contrato na análise

- `methodology_insights`: blocos por **camada** (rótulos em português).
- `ai_system_context`: `synopsis`, `pattern_tags`, `layers[]`, `primary_risk_surfaces`, `prioritized_recommendations`, `sensitive_data_notes`, `heuristic_ids_by_layer`.
- `explanations`: entradas com `type=ai_specialized_rationale` / `category=ai_modeling` quando aplicável.
- `document.import_signals_corpus`: opcional no JSON do modelo quando preenchido pelo import (compatível: documentos antigos sem chave).

## Limites da deteção

- **Falsos negativos**: modelo manual minimalista sem vocabulário AI nem import com pistas.
- **Falsos positivos residuais**: contexto lexical ambíguo ainda pode ocorrer em texto muito curto; o gate já usa matching token-safe para `llm`/`rag` e `ai` com termos acompanhantes.
- Import **não** executa chamadas de rede; é derivado apenas do texto dos artefactos.
- Não distingue automaticamente “ML clássico” vs “LLM” quando só aparecem termos genéricos.

### Exemplos práticos de token-safe

- `outrage` **não** activa `rag` (word-boundary impede substring ingênua).
- `airflow` **não** activa `ai` (token `ai` isolado não está presente).
- `ai model inference controls` pode activar contexto IA (token `ai` + termos acompanhantes técnicos).

## Interpretação dos resultados

1. Ler `ai_system_context.synopsis` e `pattern_tags`.
2. Cruzar `heuristic_ids_by_layer` com a lista de ameaças `plot4ai_*`.
3. Usar `prioritized_recommendations` como *backlog de conversa*, não como controlos fechados.
4. Explicabilidade com `confidence=low` indica **hipótese fraca** — validar com dados reais.

## Roadmap sugerido

- Mapear mais campos de import (Terraform modules, Helm values) → corpus sem duplicar parsers.
- Políticas por área (máx. N heurísticas plot4ai por execução).
- Framework refs específicos OWASP LLM / NIST AI RMF (quando catálogo estiver alinhado).
- UI: filtros por camada sem aumentar a página principal.
