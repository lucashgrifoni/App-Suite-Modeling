# Invariantes de deployment — API App Suite Modeling

Este documento fixa a **postura de deployment** para evitar ambiguidade entre “dev local” e “exposto na internet”.

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

## Invariantes que o código reforça

- Em `production`, sem `OTM_CORS_ORIGINS`, `allow_origins` fica vazio (CORS restritivo para browser).
- Em `staging`/`production`, métodos e cabeçalhos CORS são listas explícitas (não `*`).

## Revisão

Rever este ficheiro quando:

- a API passar a ser exposta publicamente;
- for introduzido OAuth2/JWT ou API keys;
- mudar o modelo de hosting (Kubernetes edge, serverless, etc.).
