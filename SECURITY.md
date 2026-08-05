# Segurança

## Postura de implantação

A API (`uvicorn otm_api.main:app`) e a UI (`vite`) são desenhadas para **uso local** (single-user, `localhost`, ou ambiente de equipa atrás de proxy autenticado). Antes de expor a API a qualquer rede partilhada:

- Configure `rate_limit_default` (variável de ambiente lida em `apps/api/otm_api/perimeter_settings.py`) para ativar o `slowapi` em todos os endpoints. Sem essa configuração, os `GET /v1/templates` e `GET /v1/packs` não têm limite de pedidos.
- Ative `OptionalApiKeyMiddleware` definindo a chave esperada.
- Restrinja `CORS` via `cors_settings` para apenas as origens necessárias.
- Confirme que respostas `422` não excedem o tamanho esperado: a partir de `v7.6.0` o handler de validação trunca strings/dicts/listas com mais de 256 caracteres no campo `errors[].input` para evitar amplificação por *input echo*.

## Divulgação responsável

Se descobrir uma vulnerabilidade, **não** abra um issue público com detalhes exploitáveis.

Use o **relatório privado de vulnerabilidades do GitHub**, que é o único canal deste projeto:

**<https://github.com/lucashgrifoni/App-Suite-Modeling/security/advisories/new>**

O relatório fica visível apenas para os mantenedores e para quem reportou, e permite discutir,
corrigir e publicar o advisory sem nunca expor os detalhes num issue público.

Inclua:

- descrição do problema;
- impacto estimado;
- passos para reproduzir;
- versão afetada;
- sugestão de mitigação, se possível.

Compromisso do projeto (objetivo):

- confirmar recebimento em até 5 dias úteis;
- publicar correção incremental assim que validada;
- creditar o reporte de forma responsável (quando permitido).
