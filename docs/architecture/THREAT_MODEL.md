# Threat model — App Suite Modeling

- **Escopo**: repositório `App-Suite-Modeling`, commit `f6e46a0`, branch `chore/full-project-validation-hardening`.
- **Data**: 2026-08-13. **Método**: STRIDE + LINDDUN + abuse cases + attack trees, cada ramo confrontado com o código e, quando indicado, com comportamento medido.
- **Limite da garantia**: isto cobre o que foi efetivamente avaliado. Não afirma ausência de vulnerabilidades. As áreas não cobertas estão listadas em [Cobertura e lacunas](#cobertura-e-lacunas).

Convenção usada nas tabelas: **`MEDIDO`** = comportamento reproduzido nesta auditoria; **`LIDO`** = controlo confirmado no código mas não exercitado; **`NÃO TESTADO`** = fora do que foi feito.

---

## 1. Arquitetura e superfície

Três clientes sobre um núcleo puro. O motor não conhece HTTP nem React.

```text
                        ┌──────────────────────────────────────┐
   ficheiro .otm.yaml ─▶│ CLI  (apps/cli, Typer)               │──▶ ficheiros no disco
   artefactos OpenAPI/  │  validate analyze report diff import │    (md, json, sarif, pdf)
   K8s/Terraform/Helm   └──────────────────────────────────────┘
   ficheiro de regras            │
                                 ▼
   HTTP (multipart, JSON) ┌──────────────────────────────┐
        ─────────────────▶│ API (apps/api, FastAPI)      │──▶ resposta JSON
                          │ perímetro: chave + limite    │
                          │ + CORS + observabilidade     │
                          └──────────────────────────────┘
                                 │
                                 ▼
                          ┌──────────────────────────────┐
   browser ──────────────▶│ Web (apps/web, React+Vite)   │──▶ localStorage / download
                          └──────────────────────────────┘
                                 │
                                 ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Núcleo (packages/)                                               │
   │  core-schema · threat-engine · artifact-import · exporters ·     │
   │  industry-packs · framework-mappings · report-premium            │
   └──────────────────────────────────────────────────────────────────┘
```

**A propriedade estrutural que define este threat model: não há egresso de rede.** Nenhum cliente HTTP em `packages/**` ou `apps/**` — as únicas ocorrências de `httpx`/`requests`/`aiohttp` são *padrões regex* em `repo_scan.py`, que **detetam** clientes HTTP no sistema a ser modelado. `MEDIDO` por varrimento do código. Sem `eval`, `exec`, `pickle`, `marshal` ou `subprocess` em `packages/` e `apps/`. Consequências diretas: SSRF, exfiltração para terceiros e desserialização insegura não têm caminho, e a maior parte da superfície clássica de aplicação web não se aplica.

**O que não existe, e portanto não é modelado**: contas de utilizador, sessões do lado do servidor, base de dados, multi-tenancy, pagamentos, e-mail. A persistência da web é do browser. Não há, por construção, acesso horizontal, vertical, IDOR, BOLA ou isolamento entre tenants a testar — o que reduz drasticamente o §13 do guião de auditoria, e é uma constatação, não uma dispensa.

### Trust boundaries

| # | Fronteira | Entra | Confiança |
|---|---|---|---|
| TB1 | Ficheiro → CLI | `.otm.yaml`/JSON, artefactos, ficheiro de regras | **Não confiável.** Um modelo pode vir de um repositório de terceiros ou de um PR. |
| TB2 | Internet → API | multipart (import), JSON (validate/analyze/export/diff) | **Não confiável.** |
| TB3 | Browser → Web | ficheiros que o utilizador larga na UI | **Não confiável.** |
| TB4 | Núcleo → disco | caminhos de saída dados pelo utilizador | Escrita com autoridade do processo. |
| TB5 | Repositório → CI/CD | workflows, actions, secrets | Actions de terceiros, pinadas por SHA. |
| TB6 | CI → PyPI | wheel/sdist | OIDC trusted publishing, sem token guardado. |

---

## 2. Ativos e atores

| Ativo | Onde | Porque importa |
|---|---|---|
| Conteúdo do modelo de ameaças | ficheiro do utilizador, corpo do pedido, `localStorage` | Descreve a arquitetura interna de um sistema real: componentes, fronteiras, dados sensíveis. É material de reconhecimento para quem o obtiver. |
| Disponibilidade do serviço API | processo | Único ativo operacional exposto. |
| Integridade do artefacto publicado | PyPI, GitHub Release | Um wheel adulterado corre na máquina de quem instala. |
| Segredos de CI | GitHub Actions | `SNYK_TOKEN`; publicação em PyPI é OIDC, sem token. |
| Integridade do resultado da análise | saída do motor | Um relatório que diz "sem riscos" quando há é pior do que nenhum relatório. |

| Ator | Capacidade |
|---|---|
| Utilizador de CLI | Corre localmente com a sua própria autoridade. |
| Cliente da API não autenticado | Quando `OTM_API_KEY` não está definido, tudo em `/v1/*`. |
| Autor hostil de modelo | Controla totalmente o conteúdo de um `.otm.yaml` ou artefacto que outra pessoa vai processar. **É o ator principal deste produto.** |
| Autor hostil de regras | Controla um ficheiro `--rules`. |
| Dependência comprometida | Executa no processo e no runner de CI. |
| Contribuidor externo via PR de fork | Corre workflows com token restrito e sem secrets. |

---

## 3. STRIDE

Cenários concretos. Categorias sem cenário foram omitidas de propósito.

### Spoofing

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| S1 | Cliente chama `/v1/*` sem credencial | `OTM_API_KEY` não definido | Uso não autenticado de toda a API | Perímetro opcional por omissão; documentado em `DEPLOYMENT_INVARIANTS.md` | **Aceite por design.** Ferramenta local-first; expor à internet exige gateway. |
| S2 | `OTM_API_KEY` resolve para vazio (secret de CI falhado, newline num secret k8s) e o perímetro abre em silêncio | Erro de configuração | Perímetro que o operador julga ligado está desligado | `resolve_api_key_perimeter` distingue *não definido* de *definido mas inutilizável*: o segundo **liga o perímetro e nenhuma credencial serve** | `LIDO`. Falha fechado, ruidosamente. |
| S3 | Atacante forja `X-Forwarded-For` para se fazer passar por outro chamador | Sem proxy de confiança declarado | Atribuição errada de identidade no limite de taxa e nos logs | Endereço reencaminhado não confiável nunca vira identidade: cai no balde partilhado `<forwarded>` | Ver D1, `MEDIDO`. |

### Tampering

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| T1 | Modelo com dois blocos `components:`; o YAML manda o último ganhar e metade do modelo desaparece — `otm validate` fica verde e o relatório sai "completo" | Merge mal resolvido, hostil ou acidental | **Integridade do resultado**: ameaças que dependiam do primeiro bloco nunca são geradas | `_BoundedSafeLoader.construct_mapping` recusa chave duplicada ao nível dos nós, com linha e coluna | `MEDIDO` (recusado). |
| T2 | Nome de componente com Markdown embebido injeta `## Conclusion / No risks were found. Approved for release.` num relatório executivo | Autor do modelo hostil | Relatório entregue a um revisor afirma o contrário do que a análise diz | `md_inline()` aplicado no renderer premium | Corrigido na fase 2. `LIDO`. |
| T3 | Regras personalizadas executam código no motor | Ficheiro `--rules` hostil | Execução arbitrária | Regras são **dados**: sem linguagem de expressão, sem regex, sem callbacks; `safe_load`, teto de tamanho, validação completa antes de chegar ao motor | `LIDO`. O pior caso é descrever ameaças que ninguém quer. |
| T4 | Action de terceiros trocada por versão maliciosa | Comprometimento a montante | Execução no runner com acesso a secrets | 22 actions pinadas por SHA de commit; Dependabot renova por PR revisável | `LIDO`. |

### Repudiation

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| R1 | Pedido falhado sem rasto correlacionável | — | Impossível reconstruir o que aconteceu | `ObservabilityMiddleware` é a camada **mais externa**, por isso apanha também o 401, o 429 e o 400 de preflight do CORS, que respondem sem chamar `call_next` | **`MEDIDO`**: `request_id` presente no registo tanto do 401 como do 429. |

### Information Disclosure

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| I1 | Erro do importador devolve traceback ao cliente | Artefacto malformado | Caminhos internos e estrutura do código expostos | Envelope `{code, message}`; traceback só no log do servidor | **`MEDIDO`**: 6 casos negativos (não-UTF-8, vazio, JSON truncado, forma errada, raiz não-mapping, aninhamento profundo) → 6× 400, todos no envelope com código específico, **0 tracebacks** no corpo. |
| I2 | Conteúdo do modelo (arquitetura interna) persiste no browser | Uso da web | Máquina partilhada expõe o modelo | Persistência é `localStorage` por design; sem servidor a guardar nada | Aceite e documentado. |
| I3 | Segredo real commitado no histórico | Erro humano | Credencial exposta | Gitleaks sobre 123 commits + Trivy secret; push protection quando público | `MEDIDO`: **0 segredos reais** em todo o histórico. |

### Denial of Service

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| D1 | Rotação de `X-Forwarded-For` a cada pedido para gerar um balde novo e contornar o limite | Limite ligado, sem proxy declarado | Limite de taxa inútil | Endereço reencaminhado não confiável colapsa no balde partilhado `<forwarded>` | **`MEDIDO`**: 40 pedidos com XFF único → `10 permitidos / 30 rejeitados`, **idêntico** ao controlo sem header. Sem bypass. |
| D2 | *Billion laughs*: ~600 bytes de aliases encadeados viram gigabytes ao serializar | Modelo hostil | Exaustão de memória | Custo expandido contabilizado na composição; teto `MAX_YAML_EXPANDED_NODES = 500 000` | **`MEDIDO`** (recusado). Alias recursivo também. |
| D3 | Bomba multi-documento: repetir a bomba após cada `---` para multiplicar o custo mantendo cada documento no limite | Manifest K8s hostil | Contorno de D2 | Orçamento **partilhado por todo o stream**, não por documento | **`MEDIDO`** (recusado). |
| D4 | Aninhamento profundo sem aliases: 10 KB de `[[[…]]]` esgotam a pilha; o `RecursionError` não é `ValueError` e escapava a 500 com traceback completo | Upload trivial | **62,8x de amplificação de log** (627 695 B por 10 003 B) → custo de disco e ingestão | `MAX_DOCUMENT_DEPTH = 100` no loader | **Corrigido** `f96817a`. `MEDIDO`: 400, 13 B de log, 0,00x. |
| D5 | O mesmo por JSON (`'{"a":' * 20000`), que não passa pelo loader YAML | Upload trivial | Idem D4 | Mesmo teto, medido por varrimento linear com saída à primeira violação | **Corrigido** `f96817a`. `MEDIDO`: 600 KB recusados em 0,003 s. |
| D6 | Upload gigante esgota memória | — | Indisponibilidade | Leitura limitada a `_MAX_BYTES + 1`, nunca materializa mais; 413 no envelope | `LIDO`. Limites de corpo ao nível do gateway delegados, documentado. |
| D7 | **Residual**: atrás de um proxy real *todos* os pedidos são reencaminhados, por isso "120 por chamador" vira "120 para o serviço inteiro" — um cliente ocupado esgota o balde de todos | Proxy presente **e** `OTM_TRUSTED_PROXY` declarado `0` | Negação de serviço entre clientes legítimos | O processo **recusa arrancar** em staging/produção com limite e sem declaração; o 429 do balde partilhado tem nome de evento próprio para o operador distinguir os dois casos | **`MEDIDO`**: produção sem declaração → `TrustedProxyConfigError`. Risco residual explícito, com decisão do operador forçada. |

### Elevation of Privilege

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| E1 | Desserialização insegura via YAML constrói objetos Python arbitrários | Modelo hostil | Execução de código | `SafeLoader` exclusivamente; nenhum `yaml.load` no código | `MEDIDO` (varrimento). |
| E2 | Workflow de fork acede a secrets | PR de fork | Roubo de credenciais | Sem `pull_request_target`; runs de Dependabot detetados no preflight e passos dependentes de secrets saltam com aviso explícito | `LIDO`. |
| E3 | Publicação em PyPI de um ref arbitrário | Acesso de escrita ao repo | Queimar um número de versão permanentemente | Versão construída verificada contra a tag em **todos** os refs; job de publicação exige `ref_type == tag` e ambiente `pypi` | `LIDO`. |

---

## 4. LINDDUN

Aplicabilidade reduzida e a razão é estrutural: **não há dados pessoais de utilizadores** — sem contas, sem sessões, sem telemetria, sem egresso. O que resta é o conteúdo do modelo.

| Categoria | Aplicável? | Nota |
|---|---|---|
| Linkability / Identifiability | **Não** | Não há sujeito de dados. Nenhum identificador é recolhido. |
| Non-repudiation | Não | Sem ação de utilizador a repudiar. |
| Detectability | Não | Sem registos por sujeito. |
| **Disclosure of information** | **Sim** | Um `.otm.yaml` descreve a arquitetura interna de um sistema real. Tratá-lo como documento público é o erro do utilizador que este produto pode induzir. Mitigação atual: persistência local, sem envio para lado nenhum. **Lacuna: a documentação não diz explicitamente "o teu modelo é material sensível; não o commites num repositório público sem pensar".** |
| Unawareness | Parcial | Mesma lacuna documental. |
| Non-compliance | N/A | Sem tratamento de dados pessoais a enquadrar. |

Esta secção não é parecer jurídico.

---

## 5. Abuse cases

| # | Ator | Objetivo | Caminho | Resultado |
|---|---|---|---|---|
| AC1 | Autor hostil de modelo | Fazer o relatório aprovar um sistema inseguro | Markdown embebido no nome do componente | **Bloqueado** (T2). |
| AC2 | Autor hostil de modelo | Esconder metade do sistema da análise | Blocos `components:` duplicados | **Bloqueado** (T1). |
| AC3 | Cliente anónimo | Encher o disco de logs do operador | Upload aninhado de 10 KB, em repetição | **Bloqueado** (D4/D5). Antes: 62,8x por pedido. |
| AC4 | Cliente anónimo | Contornar o limite de taxa | Rotação de `X-Forwarded-For` | **Bloqueado** (D1), `MEDIDO`. |
| AC5 | Cliente anónimo | Esgotar a memória do serviço | Bomba YAML, incluindo a variante multi-documento | **Bloqueado** (D2/D3). |
| AC6 | Contribuidor externo | Extrair secrets do CI | PR de fork que altera um workflow | **Bloqueado** (E2). |
| AC7 | Dependência comprometida | Executar no runner | Action ou pacote a montante | **Reduzido**: SHA pins, lockfiles, SBOM, Dependabot. Não eliminado. |

---

## 6. Attack tree — o objetivo com maior retorno

O ativo que mais compensa atacar não é o serviço: é **a confiança no resultado**. Um relatório falsamente tranquilizador atravessa uma revisão humana e é arquivado como prova.

```text
Objetivo: fazer um sistema inseguro passar por revisto e aprovado
├── Manipular a saída do relatório
│   ├── Markdown injetado em nome/título ............ BLOQUEADO (md_inline, T2)
│   └── Estrutura de tabela injetada ............... BLOQUEADO (mesma correção)
├── Fazer parte do sistema desaparecer da análise
│   ├── Chaves duplicadas no YAML .................. BLOQUEADO (T1)
│   ├── Componente que o motor apaga por heurística  CORRIGIDO antes (de04195: componentes
│   │                                                chamados "authorization" perdiam ameaças reais)
│   └── Artefacto vazio a produzir rascunho válido . BLOQUEADO (IMPORT_EMPTY_ARTIFACT)
├── Fazer o gate de CI não disparar
│   ├── Troca de metodologia mascarada de "sem risco novo"  CORRIGIDO antes (NOT EVALUATED, exit 0)
│   ├── Ameaça a subir sem cruzar banda ............ CORRIGIDO antes (avaliação por ameaça)
│   └── Gate que corre e não vê nada ............... CORRIGIDO antes (Semgrep `--severity` era filtro)
└── Fazer o revisor confiar num scanner cego
    ├── `.semgrepignore` a excluir o alvo .......... CORRIGIDO antes
    └── `.gitleaksignore` inválido, 94% de ruído ... CORRIGIDO `f6e46a0`
```

Cada ramo já foi fechado, e **cinco dos oito foram fechados por rondas anteriores desta campanha, não por esta**. O padrão que este produto tem de defender melhor do que qualquer outro é o portão que fica verde sem cobrir nada — e é reincidente: apareceu no Semgrep, no `.semgrepignore`, no `.gitleaksignore`, no gate de drift e na publicação PyPI.

---

## Cobertura e lacunas

| Área | Método | Resultado |
|---|---|---|
| Parsing de entrada não confiável | Manual + ataque | 2 defeitos, corrigidos |
| Perímetro da API (chave, limite, CORS, observabilidade) | Manual + ataque | Controlos válidos; D7 residual |
| SAST | Semgrep 119 regras/768 ficheiros, Bandit 25 624 LOC | 0 |
| Segredos | Gitleaks, 123 commits + worktree | 0 reais |
| SCA / IaC / workflows | Trivy, Grype, Checkov | 0 reais |
| Supply chain | SHA pins resolvidos contra tags | 0 |
| Lógica de negócio (motor, gate, banda de severidade) | Rondas anteriores | Ver CHANGELOG |
| **Segurança web (XSS, CSP, headers)** | — | **`NÃO TESTADO`** |
| **Travessia de caminho na escrita do CLI e no carregamento de packs** | — | **`NÃO TESTADO`** (existe `test_pack_path_traversal_security.py`, não exercitado à parte) |
| **Geração de PDF/relatório como superfície de injeção** | — | **`NÃO TESTADO`** para lá do que a fase 2 corrigiu |
| **Container / Kubernetes** | — | **`BLOCKED`**: daemon Docker parado |
| **KICS** | — | **`BLOCKED`**: ausente localmente; corre no CI |
| **DAST contra instância a correr** | — | **`NÃO TESTADO`**; exercício feito ao nível do `TestClient` |

**Conclusão dentro deste limite.** No commit, componentes, ferramentas e cenários efetivamente avaliados, não permanecem findings críticos ou altos conhecidos sem tratamento. Os controlos marcados `MEDIDO` têm evidência reproduzível registada em `.claude-orchestration/orchestration-state.md`. As áreas acima marcadas `NÃO TESTADO` e `BLOCKED` não estão aprovadas — estão por fazer.
