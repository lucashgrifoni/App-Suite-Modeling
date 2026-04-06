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

Se no futuro o cenário passar a **B (exposto publicamente)**, é obrigatório acrescentar authn/authz ou gateway documentado — ver [`CI_AND_SECURITY_EVIDENCE.md`](CI_AND_SECURITY_EVIDENCE.md) (secção perímetro da API).

## Quem pode aceder

| Ambiente | Quem |
|----------|------|
| `development` | Programadores na máquina local; origens Vite default (`localhost:5173`). |
| `staging` | Equipa interna; apenas origens definidas em `OTM_CORS_ORIGINS`. |
| `production` | Apenas consumidores explicitamente listados em `OTM_CORS_ORIGINS`; sem variável, **sem origens CORS** (browser não trata a API como cross-origin permitida). |

## Onde a API deve correr

- Preferencialmente atrás de **reverse proxy** com TLS em ambientes partilhados.
- Nunca expor portas de debug/administração para a internet pública.

## Variáveis de ambiente

| Variável | Função |
|----------|--------|
| `OTM_ENV` | `development` \| `staging` \| `production` (aceita também `prod`). |
| `OTM_CORS_ORIGINS` | Lista separada por vírgulas de origens permitidas (ex.: `https://app.example.com`). |
| `OTM_LOG_LEVEL` | Nível de log da API (`INFO` por defeito). |
| `OTM_API_KEY` | Opcional. Quando definida, exige `X-OTM-API-Key` ou `Authorization: Bearer` em **`/v1/*`**. Ver `docs/API.md`. |
| `OTM_RATE_LIMIT` | Opcional. Limite SlowAPI (ex.: `60/minute`). Em staging/prod, sem esta variável aplica-se `120/minute` por defeito. |
| `OTM_RATE_LIMIT_DISABLED` | `1` / `true` desativa o rate limit (útil em testes locais ou atrás de gateway próprio). |

## Invariantes que o código reforça

- Em `production`, sem `OTM_CORS_ORIGINS`, `allow_origins` fica vazio (CORS restritivo para browser).
- Em `staging`/`production`, métodos e cabeçalhos CORS são listas explícitas (não `*`).

## Revisão

Rever este ficheiro quando:

- a API passar a ser exposta publicamente;
- for introduzido OAuth2/JWT ou API keys;
- mudar o modelo de hosting (Kubernetes edge, serverless, etc.).
