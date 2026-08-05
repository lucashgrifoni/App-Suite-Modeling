# Scorecard — auditoria de engenharia completa

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Data:** 2026-04-06  
**Metodologia:** revisão estática, amostragem de ficheiros críticos, cruzamento com documentação, execução de ferramentas existentes (ver `FULL_ENGINEERING_TOOL_EXECUTION_LOG.md`).

---

## Notas (0.0 – 10.0)

| Domínio | Nota | Comentário breve (evidência) |
|---------|------|------------------------------|
| Clean Code | **7.2** | Ruff lint OK; **drift massivo de formatação** (73 ficheiros); alguns `per-file-ignores` E501; módulos do motor extensos. |
| Clean Architecture | **7.8** | Camadas documentadas (`docs/architecture/ARCHITECTURE.md`) e **reforçadas** por script de boundary + testes; API fina; **SQLAlchemy extra sem uso**; UI orquestra estado local conforme desenho MVP. |
| Secure Development / AppSec | **6.3** | **Sem auth na API**; **sem rate limit**; CORS configurável; uploads limitados; logs sem corpo de pedido (`observability.py`); limitações **honestas** em `KNOWN_LIMITATIONS.md`. Risco **depende do modelo de implantação**. |
| Qualidade de testes | **8.4** | **408** testes Python + verificação OpenAPI + boundary; **9** testes Vitest; E2E/híbrido no **CI** (não reexecutado localmente nesta auditoria). |
| Governança de repositório | **7.4** | CI sólido (ruff, mypy parcial, pip-audit, pytest, npm audit critical, builds); Dependabot; **sem gate de formatação**; **sem SAST** (Bandit/Semgrep) no pipeline. |
| Documentação técnica | **8.8** | Documentação extensa, ADRs, limitações, contratos, guias de release; alguma duplicidade inevitável em monorepo maduro. |
| Frontend / UI | **7.0** | Typecheck limpo; componentização razoável; **CSP não evidenciada** no Vite; poucos testes unitários TS; E2E cobre jornadas. |
| Maturidade geral de engenharia | **7.5** | Disciplina de contrato e testes de regressão fortes; gaps em **hardening de API pública** e **gates de formatação/SAST**. |

### Nota global composta (média simples dos oito domínios)

**≈ 7.55 / 10.0**

*(Interpretação: acima da média para um produto open-source com motor complexo; não “enterprise hardening” completo para exposição pública sem compensações.)*

---

## Nível de risco (qualitativo)

| Eixo | Nível | Justificativa |
|------|-------|---------------|
| Risco estrutural (código) | **Médio-baixo** | Testes + fronteiras de import + OpenAPI sincronizado reduzem regressão estrutural. |
| Risco de segurança (implantação pública típica) | **Alto** | API aberta + sem rate limit = abuso e exfiltração de conteúdo de modelos submetidos. |
| Risco de segurança (uso local / rede confiável) | **Baixo a médio** | Alinhado com documentação do produto. |
| Risco de supply chain | **Médio-baixo** | pip-audit limpo na sessão; npm com moderates na cadeia de dev (contexto a monitorizar). |

---

## Maturidade (qualitativo)

- **Engenharia de software e testes:** **madura** para a série 7.x.
- **AppSec operacional (SAST, secrets em dev, formato estrito):** **intermédia**.
- **Produto:** MVP/congelamento coerente com docs; **não** posicionado como SaaS multi-tenant neste estado.

---

## Leitura executiva (uma frase)

O projeto demonstra **forte disciplina de contrato, testes de backend e CI**, mas **não** deve ser tratado como **seguro por omissão na Internet** sem camadas externas de autenticação, limite de taxa e endurecimento HTTP no edge.

---

## Decisão de aderência (resumo)

**Parcialmente aderente** aos critérios “enterprise Clean Architecture + AppSec completo”; **aderente** ao desenho declarado de ferramenta open-source com limitações documentadas.

Ver conclusão detalhada em `FULL_ENGINEERING_COMPLIANCE_AUDIT.md`.
