# Fixtures de calibração PLOT4ai

Conjunto sintético **otm-ai-001 … 005** (cenários IA) e **otm-nai-001** (negativo ambíguo) para regressão de deteção AI/LLM, heurísticas `plot4ai_*` e explicabilidade `AI_SPECIALIZED_RATIONALE`.

| Ficheiro | Cenário |
|----------|---------|
| `otm-ai-001-llm-chat.otm.yaml` | Chat de suporte com orquestração de prompts e LLM externo |
| `otm-ai-002-rag-enterprise.otm.yaml` | RAG corporativo (retrieval + vector DB + audit) |
| `otm-ai-003-agent-tools.otm.yaml` | Agente com tool-gateway e ferramentas **internas** |
| `otm-ai-004-copilot-hr-finance.otm.yaml` | Copiloto com contexto RH/Finanças sensível |
| `otm-ai-005-inference-pipeline.otm.yaml` | Pipeline de inferência com provider externo e audit |
| `otm-nai-001-rules-workflow.otm.yaml` | Workflow de regras + filas + batch **sem** LLM/RAG/agent/fornecedor IA (gate negativo) |
| `otm-nai-002-analytics-automation.otm.yaml` | Pipeline de analytics/automação “quase IA” sem sinais de GenAI (gate negativo) |

Sinais vindos de **import de artefactos** preenchem `document.import_signals_corpus` (ver `otm_artifact_import/ai_import_corpus.py`), agregados em `build_ai_calibration_corpus`.

Testes: `tests/test_plot4ai_calibration_fixtures.py`, `tests/test_artifact_import_ai_signals.py`.

### Matching “token-safe” (redução de falsos positivos)

- Tokens curtos como `rag` e `llm` usam matching por **token/word-boundary simples** no gate (`looks_like_ai_context`) e na aplicação de keywords (`apply_keyword_signals`).
- Ainda pode existir ruído se o modelo contiver literalmente esses tokens em textos *negativos*; preferir redação sem incluir os tokens.

### Quando o produto tende a recomendar PLOT4ai

- Texto/diagrama (ou corpus de import) menciona LLM, RAG, embeddings, agent/tool-use, fornecedor de modelo, etc. (ver `looks_like_ai_context` + recomendação).

### Quando **não** deve ser tratado como contexto IA

- Automação determinística, workflows por regras e pipelines batch **sem** vocabulário ou endpoints de modelo — ex.: `otm-nai-001`. Evitar acrónimos tipo `LLM` mesmo em frases negativas (“sem …”), pois o gate é por substring.
