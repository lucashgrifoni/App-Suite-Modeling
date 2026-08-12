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

### Caso 1 — sem reverse proxy (a app recebe ligações diretas)

```bash
uvicorn otm_api.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers
```

`--no-proxy-headers` desliga a reescrita. Sem `OTM_TRUSTED_PROXY`, o rate limit conta por
endereço de peer, que é o correto aqui.

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

### O que acontece se não declarar nada

`OTM_TRUSTED_PROXY` por omissão é `off`. Pedidos que trazem `X-Forwarded-For` compatível com o
endereço observado são contados **num balde partilhado** em vez de um balde por endereço: o
limite continua a existir e não pode ser reiniciado a rodar um cabeçalho. Na primeira vez que
isso acontece, a app escreve `rate_limit_forwarded_client_untrusted` (WARNING) no log. Se a app
está de facto atrás de um proxy seu, essa linha é o sinal para ligar `OTM_TRUSTED_PROXY=1`.

## Variáveis de ambiente

| Variável | Função |
|----------|--------|
| `OTM_ENV` | `development` \| `staging` \| `production` (aceita também `prod`). |
| `OTM_CORS_ORIGINS` | Lista separada por vírgulas de origens permitidas (ex.: `https://app.example.com`). |
| `OTM_LOG_LEVEL` | Nível de log da API (`INFO` por defeito). |
| `OTM_API_KEY` | Opcional. Quando definida, exige `X-OTM-API-Key` ou `Authorization: Bearer` em **`/v1/*`**. Ver `docs/features/API.md`. |
| `OTM_RATE_LIMIT` | Opcional. Limite no formato `limits` (ex.: `60/minute`), aplicado por IP a todas as rotas. Em staging/prod, sem esta variável aplica-se `120/minute` por defeito. Expressão inválida = falha no arranque; `0/...` também (não aceita pedido nenhum — use `OTM_RATE_LIMIT_DISABLED`). |
| `OTM_RATE_LIMIT_DISABLED` | `1` / `true` desativa o rate limit (útil em testes locais ou atrás de gateway próprio). |
| `OTM_TRUSTED_PROXY` | `1` / `true` declara que a API está atrás de um reverse proxy controlado pelo operador, e que o endereço resolvido de `X-Forwarded-For` identifica o chamador para efeitos de rate limit. Omissão = desconfiar. Ver a secção "Reverse proxy e identidade do chamador". |

## Invariantes que o código reforça

- Em `production`, sem `OTM_CORS_ORIGINS`, `allow_origins` fica vazio (CORS restritivo para browser).
- Em `staging`/`production`, métodos e cabeçalhos CORS são listas explícitas (não `*`).
- O rate limit nunca usa um endereço vindo de `X-Forwarded-For` sem `OTM_TRUSTED_PROXY`; esses
  pedidos partilham um balde único, que não pode ser reiniciado a variar um cabeçalho.
- O arranque escreve uma linha `api_perimeter` com ambiente, estado da chave de API, limite,
  número de origens CORS e `trusted_proxy=on` quando o proxy é tratado como de confiança.

## Revisão

Rever este ficheiro quando:

- a API passar a ser exposta publicamente;
- for introduzido OAuth2/JWT ou API keys;
- mudar o modelo de hosting (Kubernetes edge, serverless, etc.).
