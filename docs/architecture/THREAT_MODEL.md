# Threat model — App Suite Modeling

- **Escopo**: repositório `App-Suite-Modeling`, commit `6e13872`, branch `chore/full-project-validation-hardening`.
- **Data**: primeira versão 2026-08-13, **revisto 2026-08-13** após uma auditoria adversarial que falsificou parte dele. Ver [Correções](#correções-a-este-documento).
- **Método**: STRIDE + LINDDUN + abuse cases + attack trees, cada ramo confrontado com o código e, quando indicado, com comportamento medido.
- **Limite da garantia**: isto cobre o que foi efetivamente avaliado. Não afirma ausência de vulnerabilidades. As áreas não cobertas estão listadas em [Cobertura e lacunas](#cobertura-e-lacunas).

> **Este documento já esteve errado, em negrito e marcado `MEDIDO`.** A secção
> [Correções](#correções-a-este-documento) diz exatamente onde e porquê, e não é apêndice: é a
> parte com mais valor de reutilização, porque descreve um **método de verificação** que produziu
> uma conclusão falsa com toda a aparência de rigor.

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

**Sobre egresso de rede — a afirmação anterior deste documento estava errada.** Ver
[Correções](#correções-a-este-documento). O que é verdade e o que não é:

- **Verdade**: não há cliente HTTP em `packages/**` ou `apps/**`. As únicas ocorrências de
  `httpx`/`requests`/`aiohttp` são *padrões regex* em `repo_scan.py`, que **detetam** clientes HTTP
  no sistema a ser modelado. Também não há `eval`, `exec`, `pickle`, `marshal` ou `subprocess`.
  `MEDIDO` por varrimento do código.
- **Falso, e era o que este documento concluía daí**: que "SSRF e exfiltração não têm caminho".
  Não ter um cliente HTTP **no código próprio** não é não ter egresso. O relatório premium entrega
  HTML ao `xhtml2pdf`, e é essa dependência que vai buscar `<img src>`, `<link rel=stylesheet>` e
  `@import`. Enquanto o conteúdo do modelo conseguiu injetar markup, houve SSRF a partir de um
  corpo de pedido **não autenticado** (S4/I4 abaixo), medido contra um servidor de sonda.

A conclusão correta, e a que se mantém depois da correção `c64bccf`: **o egresso é do renderizador
de PDF, e é acessível apenas por injeção de markup**. Fechada a injeção, não há caminho conhecido
para lá — mas a propriedade é agora "uma dependência não recebe conteúdo que a faça buscar nada",
que é bem mais estreita do que "não há egresso", e que só um teste sustenta.

Desserialização insegura continua sem caminho: `SafeLoader` exclusivamente, sem `pickle`.

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
| S4 | **SSRF**: markup injetado no PDF premium faz o host buscar um URL do atacante (`<img src="http://…">`) | Injeção de markup (I5) | O serviço fala com destinos escolhidos por quem envia o corpo do pedido, **sem autenticação** | `pdf_text._MARKUP_CHARS` impede a tag de existir | **`MEDIDO`, corrigido `c64bccf`.** Servidor de sonda: 6 hits antes, 0 depois. Falsificou a afirmação de "sem egresso" deste documento. |

### Tampering

| ID | Cenário | Pré-condição | Impacto | Controlo | Estado |
|---|---|---|---|---|---|
| T1 | Modelo com dois blocos `components:`; o YAML manda o último ganhar e metade do modelo desaparece — `otm validate` fica verde e o relatório sai "completo" | Merge mal resolvido, hostil ou acidental | **Integridade do resultado**: ameaças que dependiam do primeiro bloco nunca são geradas | `_BoundedSafeLoader.construct_mapping` recusa chave duplicada ao nível dos nós, com linha e coluna | `MEDIDO` (recusado). |
| T2 | Nome de componente com Markdown embebido injeta `## Conclusion / No risks were found. Approved for release.` num relatório executivo | Autor do modelo hostil | Relatório entregue a um revisor afirma o contrário do que a análise diz | `md_block()` nos cinco sites de lista + `>` em `_LEADING_BLOCK` | **`MEDIDO`, corrigido `6e13872`.** Esta linha dizia "Corrigido na fase 2, `LIDO`" e **estava errada** — ver [Correções](#correções-a-este-documento). |
| T5 | Id de ameaça não injetivo: componente `flow_svc` e fluxo `svc` produzem a mesma string, e o gate de drift julga uma ameaça **substituída** onde foi **acrescentada** | Nomes que colidem, hostis ou acidentais | Um portão de CI aprova uma mudança que adiciona ameaças CRITICAL | Análise recusada, nomeando os dois sujeitos | **`MEDIDO`, corrigido `57e566e`.** Alcançável a partir de um `info.title` de OpenAPI, sem autoria de modelo. |
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
| I4 | Markup injetado no PDF premium faz o host ler um ficheiro local e devolvê-lo ao chamador: `<img src="C:/…">` embute os pixels no PDF | Injeção de markup (I5) | Leitura de ficheiro do host da API por um pedido não autenticado, limitada a imagens que o Pillow decodifica | Fold fechado em relação a markup | **`MEDIDO`, corrigido `c64bccf`.** |
| I5 | O fold de fontes NFKD corria **depois** do `html.escape` e re-materializava `< > & " '`: `＜` (U+FF1C) atravessa o escape e vira `<` | Autor do modelo hostil | Causa raiz de S4, I4 e T2 no caminho PDF: markup arbitrário, outline forjado, `/Title` sob controlo do modelo | `pdf_text._MARKUP_CHARS` | **`MEDIDO`, corrigido `c64bccf`.** O escape corria; a transformação seguinte desfazia-o. |

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

Aplicabilidade reduzida e a razão é estrutural: **não há dados pessoais de utilizadores** — sem contas, sem sessões, sem telemetria. O que resta é o conteúdo do modelo.

Nota sobre o egresso corrigido em C1: o SSRF (S4) não abria uma via de exfiltração de dados
pessoais, porque o URL buscado era uma string estática dentro do markup que o atacante escreveu —
ele fazia o host falar, não fazia o host contar-lhe nada sobre o modelo. A conclusão desta secção
mantém-se; a justificação é que não há sujeito de dados, e essa não dependia do egresso.

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
| AC1 | Autor hostil de modelo | Fazer o relatório aprovar um sistema inseguro | Markdown embebido no nome do componente | **Bloqueado desde `6e13872`.** Esta linha dizia "Bloqueado" quando **não estava**: 6 cabeçalhos forjados no executive, 13 no standard e deep. Ver [Correções](#correções-a-este-documento). |
| AC8 | Autor hostil de modelo | Fazer o mesmo pelo PDF, e de caminho fazer o host buscar um URL seu | `＜img src=…＞` em fullwidth no `metadata.title` | **Bloqueado desde `c64bccf`** (S4/I4/I5). |
| AC9 | Autor de um spec OpenAPI de terceiros | Fazer o gate de CI aprovar uma mudança que adiciona ameaças CRITICAL | Título do spec escolhido para colidir com um id de fluxo | **Bloqueado desde `57e566e`** (T5). Sem escrever um modelo. |
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
│   ├── Markdown injetado em nome/título ........... BLOQUEADO `6e13872` (5 sites + `>`)
│   ├── Markup injetado no PDF (fold desfazia o escape)  BLOQUEADO `c64bccf` (I5)
│   └── Estrutura de tabela injetada ............... BLOQUEADO (`_md_cell`, atacado e resistiu)
├── Fazer parte do sistema desaparecer da análise
│   ├── Chaves duplicadas no YAML .................. BLOQUEADO (T1)
│   ├── Componente que o motor apaga por heurística  CORRIGIDO antes (de04195)
│   ├── Id de ameaça colidido a fundir duas em uma . BLOQUEADO `57e566e` (T5)
│   └── Artefacto vazio a produzir rascunho válido . BLOQUEADO (IMPORT_EMPTY_ARTIFACT)
├── Fazer o gate de CI não disparar
│   ├── Troca de metodologia mascarada de "sem risco novo"  CORRIGIDO antes (NOT EVALUATED)
│   ├── Ameaça a subir sem cruzar banda ............ CORRIGIDO antes (avaliação por ameaça)
│   ├── Id colidido a virar "modificação" ou "descida"  BLOQUEADO `57e566e` (T5)
│   └── Gate que corre e não vê nada ............... CORRIGIDO antes (Semgrep `--severity`)
└── Fazer o revisor confiar num portão cego
    ├── `.semgrepignore` a excluir o alvo .......... CORRIGIDO antes
    ├── `.gitleaksignore` inválido, 94% de ruído ... CORRIGIDO `f6e46a0`
    └── Oráculo de estrutura cego a blocos aninhados  CORRIGIDO `6e13872` — 85 testes verdes
                                                     com a falsificação viva
```

**O ramo que este documento não tinha, e é o que mais interessa**: o último. A primeira versão da
árvore declarava os oito ramos fechados. Três não estavam — e um deles era o próprio teste que os
declarava fechados.

O padrão é reincidente e agora tem **seis** ocorrências registadas: o filtro `--severity` do
Semgrep, o `.semgrepignore` a excluir `.github/`, as entradas inválidas do `.gitleaksignore`, a
condição de publicação no PyPI, o gate de drift sob troca de metodologia, e o oráculo de estrutura
Markdown. Sempre a mesma forma — **verde porque está a olhar para outro lado**. Num produto cujo
valor é dizer a um revisor no que confiar, é a classe de defeito a tratar como prioritária.

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
| **Travessia de caminho: escrita do CLI, packs, templates** | Ataque executado, 79 ids de pack + 19 de template hostis | **Resistiu.** `../`, absolutos POSIX e Windows, UNC, `\\?\`, `%252e`, UTF-8 overlong, byte nulo, NFD/NFKD, fullwidth, homoglifos, RTL, 8.3, ADS, `CON`/`NUL` — todos rejeitados no loader, na API e no CLI. Escrita atómica resistiu a interrupção a meio e a destino read-only. |
| **Geração de relatório como superfície de injeção** | Ataque executado | **4 defeitos, corrigidos** — I5/S4/I4 no PDF, T2 no Markdown |
| **Segurança web (XSS, CSP, headers)** | — | **`NÃO TESTADO`**. `apps/web` não foi aberto por nenhuma lente; `diagramSanitize.ts`, citado como o sanitizador de conteúdo não confiável, nunca foi lido. |
| **Container / Kubernetes** | — | **`BLOCKED`**: daemon Docker parado |
| **KICS** | — | **`BLOCKED`**: ausente localmente; corre no CI |
| **DAST contra instância a correr** | — | **`NÃO TESTADO`**; exercício feito ao nível do `TestClient` |

**Conclusão dentro deste limite.** No commit, componentes, ferramentas e cenários efetivamente avaliados, não permanecem findings críticos ou altos conhecidos sem tratamento. Os controlos marcados `MEDIDO` têm evidência reproduzível registada em `.claude-orchestration/orchestration-state.md`. As áreas acima marcadas `NÃO TESTADO` e `BLOCKED` não estão aprovadas — estão por fazer.

---

## Correções a este documento

A primeira versão foi escrita em 2026-08-13 e falsificada no mesmo dia por uma auditoria
adversarial que atacou as superfícies que ela dava por não testadas. Três afirmações caíram. Ficam
registadas aqui em vez de reescritas em silêncio, porque **o erro de método é mais reutilizável do
que a conclusão certa**.

| # | O que dizia | O que era verdade | Correção |
|---|---|---|---|
| C1 | "não há egresso de rede … SSRF e exfiltração não têm caminho", **em negrito, `MEDIDO`** | Havia SSRF não autenticado via `xhtml2pdf`, medido contra um servidor de sonda | `c64bccf`, §1 e S4 |
| C2 | T2 "Corrigido na fase 2, `LIDO`" | A fase 2 corrigiu o caminho **HTML/PDF**; o **Markdown** ficou aberto — 13 cabeçalhos forjados no relatório deep | `6e13872`, T2 |
| C3 | AC1 "**Bloqueado**" e "cada ramo já foi fechado" na attack tree | Três ramos abertos, um deles o próprio oráculo que os declarava fechados | `6e13872`, §6 |

### O erro de método, que é o que vale a pena guardar

C1 não veio de desleixo. Veio de uma verificação que **parecia** rigorosa: um varrimento de
`packages/**` e `apps/**` à procura de `httpx`, `requests`, `aiohttp`, `urllib`. O varrimento
estava certo — não há mesmo nenhum cliente HTTP no código próprio. O erro foi a **generalização**:
de "não temos cliente HTTP" para "não há egresso possível".

Essa inferência ignora tudo o que uma dependência faz com o que lhe entregamos. O `xhtml2pdf`
recebe HTML e vai buscar os recursos que ele referencia; o egresso é dele, com a identidade do
nosso processo. Nenhum `grep` ao nosso código o podia ver.

**A regra que fica**: uma propriedade negativa sobre um sistema — "não faz X" — não se estabelece
lendo o código próprio quando o sistema entrega dados a terceiros. Estabelece-se **observando o
sistema a correr**, com uma sonda no sítio onde X apareceria. Foi assim que a auditoria a
falsificou, e é assim que ela está agora fixada: `test_p3_pdf_render_markup_containment.py` mais a
sonda HTTP local.

O mesmo se aplica a C2 e C3, com outra forma: ambas eram **`LIDO` apresentado ao lado de `MEDIDO`**
numa tabela onde a distinção é fácil de perder de vista. Um controlo lido é uma hipótese. Só o
ataque que falha o torna um facto — e é por isso que a coluna de estado deste documento nomeia,
agora, o ataque concreto que não funcionou.
