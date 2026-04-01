# Congelamento de escopo — v0.1.0

**Data do freeze:** 2026-04-01  
**Versão alvo:** `v0.1.0` (semver `0.1.0`)  
**Nome do produto:** App Suite Modeling (`open-threat-model` no PyPI/metadata Python)

## Decisão de versão

- `pyproject.toml` e `apps/web/package.json` declaram **`0.1.0`**, alinhados a uma primeira entrega pública incremental séria (pós-fases RC documentadas).
- **Semver:** `0.y.z` comunica API e superfície ainda em evolução; dentro disso, `0.1.0` marca o primeiro marco de publicação coordenada (docs, validação, artefatos).
- **Antes de criar a tag `v0.1.0`:** confirmar com `git tag -l v0.1.0` (e no remoto) que não existe conflito; não reutilizar nem sobrescrever tag publicada — ver [`VERSIONING_AND_TAGS.md`](VERSIONING_AND_TAGS.md) e [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md).

## O que entra nesta release

- **Core:** schema canônico, motor multi-metodologia, exportadores (JSON, Markdown, Mermaid, relatórios).
- **Metodologias:** STRIDE (default), LINDDUN, NIST Data-Centric, OCTAVE Allegro, CIA/CIA-DIE, PASTA (fase 2), PLOT4ai (fase 2 calibrada com fixtures).
- **Produto:** CLI `otm`, API FastAPI, UI web (fluxo guiado sem persistência server-side).
- **Diferenciais:** import de artefatos (OpenAPI, Terraform, Kubernetes, Helm conforme implementado), diff de modelos e de análises, backlog de remediação, explainability (`ExplanationRecord` / CLI `explain`).
- **Qualidade:** suíte pytest ampla, smoke RC, smoke E2E mínimo Playwright, documentação operacional e de contratos.

## O que fica explicitamente fora

- Novos motores de metodologia ou reescrita da arquitetura multi-engine.
- Persistência de modelos/análises no servidor (autenticação/autorização multi-tenant).
- Canvas/diagrama visual como fluxo principal (dependência presente para evolução futura).
- Promessa de cobertura exaustiva de frameworks regulatórios além do mapeamento e heurísticas atuais.

## Estável vs incremental vs experimental

| Categoria | Significado neste projeto |
|-----------|---------------------------|
| **Estável** | Comportamento e contratos cobertos por testes; mudanças esperadas apenas com nota no CHANGELOG. |
| **Incremental (evolving)** | Funcionalidade real, mas superfície ou heurísticas continuam a receber melhorias compatíveis. |
| **Especializado (specialized)** | Profundidade e opinião de domínio (ex.: PASTA, PLOT4ai); não é “checklist genérico”. |
| **Experimental** | Não aplicável como etiqueta principal nesta release; recursos opcionais arriscados devem ser marcados explicitamente nas docs da feature. |

## Maturidade por área (convenção única)

Valores: **Mature** | **Evolving** | **Specialized** | **Experimental**

| Área | Nível | Nota breve |
|------|-------|------------|
| STRIDE | **Mature** | Default e maior cobertura heurística. |
| LINDDUN | **Evolving** | Camada nativa de privacidade; extensão contínua. |
| NIST Data-Centric | **Evolving** | Lentes e sinais; não substitui programa NIST completo. |
| OCTAVE Allegro | **Evolving** | Mapeado às estruturas do motor; foco em rastreabilidade. |
| CIA / CIA-DIE | **Evolving** | Visão executiva; complementa STRIDE. |
| PASTA | **Specialized** | Fase 2: risco/ataque/impacto com heurísticas dedicadas. |
| PLOT4ai | **Specialized** | Fase 2: AI/LLM com calibração e casos negativos documentados. |
| Artifact import | **Evolving** | Importadores reais; inferência assistida, revisão humana esperada. |
| Diff (modelo / análise) | **Evolving** | Semântico e acionável; regras podem refinar-se. |
| Backlog | **Evolving** | Priorização sugerida; não substitui gestão de produto. |
| Explainability | **Evolving** | Contrato estável; riqueza de explicações aumenta com o tempo. |
| UI | **Evolving** | MVP sólido; sem persistência server-side. |
| CLI | **Evolving** | Superfície estável; compatibilidade preservada em `0.1.x`. |
| API | **Evolving** | Versão `/v1/`; evolução incremental com contratos documentados. |

## Referências

- Notas de release: [`RELEASE_NOTES_v0.1.0.md`](RELEASE_NOTES_v0.1.0.md)
- Limitações: [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)
- Gate GO/NO-GO: [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md)
- Checklist de lançamento: [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md)
