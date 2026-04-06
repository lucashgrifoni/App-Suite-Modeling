# Scorecard brutal — bar Staff/Principal

**Nota geral (engenharia real, todo o sistema):** **6,8 / 10**

**Comparativo cruel:** para **produto de plataforma em produção**, a nota efetiva cai para **~5,5 / 10**. Para **OSS de análise local**, sobe para **~7,5 / 10**. O scorecard abaixo é **sem** separar cenários — é a média honesta.

---

## Nota por dimensão

| Dimensão | Nota | Classificação |
|----------|------|---------------|
| Clean Code | 6,3 | OK |
| Clean Architecture (núcleo) | 7,8 | BOM |
| Clean Architecture (adaptadores + ops) | 5,8 | FRACO |
| Design de sistema / extensibilidade | 6,5 | OK |
| Segurança (AppSec) | 5,5 | FRACO |
| Testabilidade / testes | 7,8 | BOM |
| DevSecOps / CI / gates | 5,5 | FRACO |
| Frontend / UI / a11y | 7,0 | BOM |
| Dívida técnica / sustentabilidade | 6,0 | OK |
| Observabilidade / operação | 4,5 | CRÍTICO |

**Legenda:** EXCELENTE (≥8,5) · BOM (7,0–8,4) · OK (5,5–6,9) · FRACO (4,0–5,4) · CRÍTICO (<4,0)

---

## Veredicto contra o bar Staff/Principal

| Pergunta | Resposta |
|----------|----------|
| É nível Staff/Principal no conjunto? | **Não** |
| O núcleo justifica orgulho de Senior? | **Sim** |
| O “todo” sustenta escala multi-equipa sem dor? | **Não** |

---

## Uma frase para o CTO

> **Domínio e testes carregam o projeto; CLI, API operacional e CI não estão no mesmo patamar — isso define o teto.**

---

## O que impede 10/10 (checklist brutal)

- [ ] CLI sem god module  
- [ ] API com logging estruturado + correlação  
- [ ] AuthN/Z ou posicionamento explícito “só rede privada” **enforceado** (docs + exemplos + defaults)  
- [ ] CORS/métodos/headers **por ambiente**, seguros em prod  
- [ ] `mypy` no CI (estratégia gradual aceite, mas **gate existe**)  
- [ ] SCA (pip + npm) no CI  
- [ ] Sonar **ou** equivalente **no** pipeline  
- [ ] E2E crítico **bloqueante**  
- [ ] Ruff (ou ferramenta equivalente) com regras alargadas **com plano**  
- [ ] Estratégia única para dois fronts ou fusão de tokens  

**Até aqui faltar qualquer item crítico → não é 10/10.**
