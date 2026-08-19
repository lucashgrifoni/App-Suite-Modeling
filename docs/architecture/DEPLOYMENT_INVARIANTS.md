# Invariantes de deployment — API App Suite Modeling

Este documento fixa a **postura de deployment** para evitar ambiguidade entre “dev local” e “exposto na internet”.

## API sem autenticação integrada (por defeito)

**Sem `OTM_API_KEY`, a API não exige autenticação de aplicação.** Qualquer cliente que consiga alcançar o processo pode chamar os endpoints de `/v1`.

Para **qualquer exposição fora de localhost ou rede não confiável**, é **obrigatório** colocar a API atrás de um **reverse proxy / API gateway** que aplique pelo menos um dos seguintes (consoante a política da organização):

- **API keys** ou **OAuth2/OIDC** validados no edge;
- **mTLS** entre clientes e gateway;
- políticas de rede equivalentes (VPN + firewall de aplicação) **documentadas** e auditáveis.

Sem esta camada, **não** trate a API como segura na Internet pública.

## Decisão de produto (cenário adoptado)

**Cenário A — local / rede interna por defeito**

A API FastAPI é pensada para:

- desenvolvimento em `localhost`;
- execução em rede **confiável** (VPN, VPC, bastion) quando não há autenticação de aplicação.

**Não** se assume, por defeito, API pública na internet sem camada adicional (API gateway, mTLS, IdP, WAF).

Se no futuro o cenário passar a **B (exposto publicamente)**, é obrigatório acrescentar authn/authz ou gateway documentado — ver [`CI_AND_SECURITY_EVIDENCE.md`](../CI_AND_SECURITY_EVIDENCE.md) (secção perímetro da API).

## Quem pode aceder

| Ambiente | Quem |
|----------|------|
| `development` | Programadores na máquina local; origens Vite default (`localhost:5173`). |
| `staging` | Equipa interna; apenas origens definidas em `OTM_CORS_ORIGINS`. |
| `production` | Apenas consumidores explicitamente listados em `OTM_CORS_ORIGINS`; sem variável, **sem origens CORS** (browser não trata a API como cross-origin permitida). |

## Onde a API deve correr

- Preferencialmente atrás de **reverse proxy** com TLS em ambientes partilhados.
- Nunca expor portas de debug/administração para a internet pública.

## Reverse proxy e identidade do chamador (obrigatório ler antes de expor)

O uvicorn 0.52 corre `ProxyHeadersMiddleware` **por defeito** (`proxy_headers=True`,
`forwarded_allow_ips="127.0.0.1"`). Ou seja: **sem passar flag nenhuma**, o uvicorn reescreve
`request.client` a partir do cabeçalho `X-Forwarded-For` sempre que o peer TCP é loopback. Num
deployment com proxy no mesmo host — o cenário que este documento torna obrigatório — isso vale
para *todos* os pedidos, e o endereço que a app vê passa a vir de um cabeçalho.

A app **não confia** nesse endereço a não ser que o operador o declare. Ver
`apps/api/otm_api/middleware_rate_limit.py::client_key`.

Em `staging` e `production`, com o rate limit ativo, essa declaração é **obrigatória**: sem ela a
app **recusa arrancar**. Ver "Porque é que a omissão aborta o arranque", abaixo.

### Caso 1 — sem reverse proxy (a app recebe ligações diretas)

```bash
uvicorn otm_api.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers
# e, no processo da app (staging/production):
OTM_TRUSTED_PROXY=0
```

`--no-proxy-headers` desliga a reescrita, e o rate limit conta por endereço de peer, que é o
correto aqui. `OTM_TRUSTED_PROXY=0` declara essa postura: nenhum endereço vindo de
`X-Forwarded-For` conta como identidade. Um cliente que na mesma envie o cabeçalho com o próprio
endereço cai no balde partilhado — é uma degradação que ele próprio escolhe, e não afeta os
restantes chamadores diretos.

### Caso 2 — atrás de um reverse proxy que o operador controla

```bash
uvicorn otm_api.main:app --host 127.0.0.1 --port 8000 \
  --proxy-headers --forwarded-allow-ips='127.0.0.1'
# e, no processo da app:
OTM_TRUSTED_PROXY=1
```

`--forwarded-allow-ips` tem de listar **apenas** o endereço do proxy (`127.0.0.1` para proxy no
mesmo host; o IP do hop para proxy noutra máquina). Nunca `'*'` numa app exposta: significa
"aceito o `X-Forwarded-For` de quem quer que ligue".

O proxy tem de **acrescentar** o peer real ao cabeçalho, não reencaminhar o do cliente. Em nginx:

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

Sem esta linha, o nginx passa o `X-Forwarded-For` do cliente tal e qual e o valor é escolhido
pelo atacante. `$proxy_add_x_forwarded_for` acrescenta `$remote_addr` à direita, que é o que o
uvicorn seleciona (percorre a cadeia da direita para a esquerda e fica no primeiro hop não
confiável).

### Porque é que a omissão aborta o arranque

Quando a app não confia no endereço encaminhado, não tem forma nenhuma de distinguir chamadores:
o uvicorn já reescreveu `scope["client"]` a partir do cabeçalho antes de qualquer código da app
correr, por isso o peer real (o proxy) já não existe para nós. A única chave segura que resta é
**uma só, partilhada por todos os pedidos encaminhados**.

Isso é seguro e é honesto, mas tem um preço de disponibilidade que não pode ficar implícito:
atrás do reverse proxy que este documento torna obrigatório, **todos** os pedidos trazem o
cabeçalho, logo **todos** caem nesse balde. `120/minute` deixa de querer dizer "120 por chamador"
e passa a querer dizer "120 para o serviço inteiro" — um cliente ocupado devolve 429 a todos os
outros, incluindo à sonda `/health`. Medido: um chamador faz 120 pedidos e o **primeiro** pedido
do chamador seguinte leva 429.

Por isso a omissão deixou de ter default. Em `staging`/`production` com o limite ativo,
`resolve_trusted_proxy` levanta `TrustedProxyConfigError` e o processo não arranca, com as duas
opções e as respectivas consequências escritas na mensagem. Um deploy que falha é observável; um
serviço que serve 429 a toda a gente duas semanas depois do upgrade não é.

O que **não** muda: a propriedade de segurança. Rodar `X-Forwarded-For` continua a não criar um
balde novo, com `OTM_TRUSTED_PROXY=0` ou sem ele.

| Situação | Comportamento |
|----------|---------------|
| `development` (com ou sem limite) | Sem declaração exigida; endereço encaminhado não é de confiança. |
| Limite desligado (`OTM_RATE_LIMIT_DISABLED=1`) | Sem declaração exigida (não há balde). |
| `staging`/`production`, limite ativo, variável ausente ou em branco | **Arranque abortado.** |
| `OTM_TRUSTED_PROXY` com valor não reconhecido (`maybe`, `2`, …) | **Arranque abortado** — uma gralha não pode significar `off`. |
| `OTM_TRUSTED_PROXY=1` | Balde por chamador. Exige as flags do uvicorn do Caso 2. |
| `OTM_TRUSTED_PROXY=0` | Balde partilhado por todos os pedidos encaminhados, e o custo é escrito no arranque. |

### Como ver isto no log

- Arranque com `OTM_TRUSTED_PROXY=0` e limite ativo (fora de `development`):
  `rate_limit_shared_bucket` (WARNING), que nomeia o limite e diz que é o orçamento de todos.
- Primeira vez que um pedido cai mesmo no balde partilhado:
  `rate_limit_forwarded_client_untrusted` (WARNING), uma vez por processo — uma linha por pedido
  seria uma inundação de log controlada por quem envia o cabeçalho.
- 429 servido a partir do balde partilhado: `rate_limit_exceeded_shared_bucket`, em vez de
  `rate_limit_exceeded`. Do lado do cliente os dois 429 são idênticos; o nome do evento é o único
  sítio onde a diferença fica registada, e é o que responde a "está tudo a dar 429".

## Variáveis de ambiente

| Variável | Função |
|----------|--------|
| `OTM_ENV` | `development` \| `staging` \| `production` (aceita também `prod`). |
| `OTM_CORS_ORIGINS` | Lista separada por vírgulas de origens permitidas (ex.: `https://app.example.com`). |
| `OTM_LOG_LEVEL` | Nível de log da API (`INFO` por defeito). |
| `OTM_API_KEY` | Opcional. Quando definida, exige `X-OTM-API-Key` ou `Authorization: Bearer` em **`/v1/*`**. Ver `docs/features/API.md`. |
| `OTM_RATE_LIMIT` | Opcional. Limite no formato `limits` (ex.: `60/minute`), aplicado por IP a todas as rotas. Em staging/prod, sem esta variável aplica-se `120/minute` por defeito. Expressão inválida = falha no arranque; `0/...` também (não aceita pedido nenhum — use `OTM_RATE_LIMIT_DISABLED`). |
| `OTM_RATE_LIMIT_DISABLED` | `1` / `true` desativa o rate limit (útil em testes locais ou atrás de gateway próprio). |
| `OTM_MAX_YAML_NODES` | Tecto de nós **expandidos** ao compor YAML (defeito `500000`). É a defesa contra *billion laughs*: `safe_load` partilha o nó de destino ao resolver um alias, por isso ~600 bytes com aliases encadeados carregam em milissegundos e só custam gigabytes quando alguém serializa. Conta-se o custo expandido durante a composição e pára-se antes de o pagar. |
| `OTM_MAX_DOCUMENT_DEPTH` | Tecto de profundidade de aninhamento, o mesmo para YAML e JSON (defeito `100`). O tecto de nós não protege aqui: um documento sem um único alias atravessava-o até a pilha do parser esgotar, e o `RecursionError` subia como `500` com traceback completo — 62,8x de amplificação de log por pedido. |
| `OTM_MAX_DOCUMENT_ENTITIES` | Tecto de entidades de um documento. **Desligado por defeito** — sem esta variável não há tecto. Aplica-se no funil de `/v1/models/*`, `/v1/exports`, `/v1/remediation/backlog` e `/v1/reports/premium`; **não** nas rotas de importação, que têm o seu próprio limite de 2 MiB no ficheiro carregado. |
| `OTM_MAX_DOCUMENT_BYTES` | Tecto de bytes de um `.otm.yaml` **lido do disco** (defeito 8 MiB). Deliberadamente generoso: é rede de segurança contra um ficheiro absurdo, não uma opinião sobre o tamanho de um modelo. **Não limita corpos de pedidos HTTP** — as rotas JSON não têm tecto de corpo; ver [`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md). |
| `OTM_TRUSTED_PROXY` | Declaração de postura, não um interruptor opcional. `1`/`true`/`yes`/`on`: a API está atrás de um reverse proxy do operador e o endereço resolvido de `X-Forwarded-For` identifica o chamador (balde por chamador). `0`/`false`/`no`/`off`: não há tal proxy e os pedidos encaminhados partilham um balde único. Em `staging`/`production` com o limite ativo, **a omissão aborta o arranque**; um valor não reconhecido aborta sempre. Ver a secção "Reverse proxy e identidade do chamador". |

## Invariantes que o código reforça

- Em `production`, sem `OTM_CORS_ORIGINS`, `allow_origins` fica vazio (CORS restritivo para browser).
- Em `staging`/`production`, métodos e cabeçalhos CORS são listas explícitas (não `*`).
- O rate limit nunca usa um endereço vindo de `X-Forwarded-For` sem `OTM_TRUSTED_PROXY=1`; esses
  pedidos partilham um balde único, que não pode ser reiniciado a variar um cabeçalho.
- Em `staging`/`production` com o limite ativo, o processo não arranca sem `OTM_TRUSTED_PROXY`
  declarado: o balde partilhado é um orçamento único para o serviço inteiro e tem de ser uma
  escolha, não um default.
- O arranque escreve uma linha `api_perimeter` com ambiente, estado da chave de API, limite,
  número de origens CORS e `trusted_proxy=on` quando o proxy é tratado como de confiança.

## Revisão

Rever este ficheiro quando:

- a API passar a ser exposta publicamente;
- for introduzido OAuth2/JWT ou API keys;
- mudar o modelo de hosting (Kubernetes edge, serverless, etc.).
