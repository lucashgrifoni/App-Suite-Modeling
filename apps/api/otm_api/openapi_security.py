"""
Os esquemas de segurança do contrato — **documentação**, não aplicação.

O perímetro de `OTM_API_KEY` vive num middleware ASGI puro (`middleware_api_key`), que o
FastAPI não consegue inspecionar. O resultado era um `openapi.json` sem
`components.securitySchemes` e sem `security` em nenhuma das operações `/v1`: o Swagger UI
que a rota raiz anuncia não tinha botão **Authorize**, os tipos gerados em
`apps/web/src/types/generated/openapi.d.ts` não traziam credencial, e qualquer SDK gerado a
partir do contrato saía a falar com uma API protegida sem forma de se autenticar.

Estas dependências existem só para pôr no contrato o que o middleware já aceita — o cabeçalho
`X-OTM-API-Key` **ou** `Authorization: Bearer <token>`. Duas propriedades são deliberadas e
estão fixadas por `tests/test_p3_api_openapi_security_scheme.py`:

* `auto_error=False`: a dependência **nunca** decide nada. Com o default (`True`), a falta do
  cabeçalho seria um 403 emitido dentro da rota, em todas as operações e independentemente de
  `OTM_API_KEY` — ou seja, o modo por omissão do produto (API aberta, ver
  `docs/architecture/DEPLOYMENT_INVARIANTS.md`) passava a responder 403 a toda a gente, e o
  401 documentado deixava de ser o que o cliente recebe. O ponto de aplicação continua a ser
  um só: o middleware.
* dois esquemas em vez de um: em OpenAPI, `security: [{A: []}, {B: []}]` lê-se "A **ou** B",
  que é exatamente a escolha que `middleware_api_key._extract_api_key` oferece. Declarar só o
  cabeçalho deixaria metade do que é aceite fora do contrato.

A descrição de cada esquema diz *quando* a credencial é exigida, porque o contrato é estático
e o perímetro é uma decisão de deployment: sem ela, o contrato afirmaria que `/v1` está
sempre protegido, que é a mentira simétrica da que existia.
"""

from __future__ import annotations

from fastapi.security import APIKeyHeader, HTTPBearer

_WHEN_REQUIRED = (
    "Required when the server sets `OTM_API_KEY`; ignored when it does not. "
    "See `docs/features/API.md` and `docs/architecture/DEPLOYMENT_INVARIANTS.md`."
)

#: `X-OTM-API-Key: <secret>` — a forma que a resposta 401 manda usar.
api_key_header = APIKeyHeader(
    name="X-OTM-API-Key",
    scheme_name="ApiKeyHeader",
    description=f"API key for every `/v1` operation. {_WHEN_REQUIRED}",
    auto_error=False,
)

#: `Authorization: Bearer <secret>` — o mesmo segredo, para clientes que só sabem falar OAuth.
bearer_token = HTTPBearer(
    scheme_name="BearerToken",
    description=f"The same `OTM_API_KEY` secret sent as a bearer token. {_WHEN_REQUIRED}",
    auto_error=False,
)
