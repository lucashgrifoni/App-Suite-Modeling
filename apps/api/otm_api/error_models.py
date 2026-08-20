"""As formas de erro que esta API realmente devolve, para o contrato publicado as declarar.

O OpenAPI gerado documentava o 422 de 16 das 19 operações como `HTTPValidationError` — o esquema
por omissão do FastAPI, `{detail: ValidationError[]}` — que esta API não produz em lado nenhum. As
duas formas reais são deliberadas e têm testes próprios; o que faltava era declará-las, para que
`contracts/openapi.json` e os tipos TypeScript gerados a partir dele descrevessem o que chega ao
cliente. Ver `tests/test_p4_openapi_422_matches_the_api.py`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorItem(BaseModel):
    """Uma entrada de `errors[]`: eco do input do cliente, com o caminho que falhou."""

    type: str = Field(description="Classe do erro, ex.: `value_error`, `body_unparsable`.")
    loc: list[Any] = Field(default_factory=list, description="Caminho até ao campo em falta ou inválido.")
    msg: str = Field(description="Mensagem legível para quem enviou o pedido.")


class ApiProblem(BaseModel):
    """Erro do **envelope** do pedido, devolvido no topo do corpo (sem `detail`).

    Produzido por `problem_detail` — corpo ilegível, validação do envelope, rate limit, 500.
    """

    code: str = Field(description="Código estável do erro, ex.: `REQUEST_VALIDATION_ERROR`.")
    message: str = Field(description="Mensagem user-facing, localizada por `Accept-Language`.")
    status: int = Field(description="Código HTTP repetido no corpo, para clientes que só leem o corpo.")
    errors: list[ApiErrorItem] | None = Field(default=None, description="Detalhe por campo, quando aplicável.")


class ApiErrorBody(BaseModel):
    """O conteúdo de `detail` num erro de **domínio**."""

    code: str = Field(description="Código estável do erro, ex.: `DOCUMENT_VALIDATION_ERROR`.")
    message: str = Field(description="Mensagem user-facing, localizada por `Accept-Language`.")
    errors: list[ApiErrorItem] | None = Field(default=None, description="Detalhe por campo, quando aplicável.")


class ApiErrorEnvelope(BaseModel):
    """Erro de **domínio**: `detail` é um objecto, não um array.

    É aqui que um cliente gerado do contrato antigo partia: lia `detail[0].msg` num dicionário.
    """

    detail: ApiErrorBody


#: Um 422 pode chegar por qualquer das duas vias na mesma rota — o envelope do pedido é validado
#: antes de a rota correr, e o domínio depois — por isso o contrato declara a união.
API_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {
        "description": "Pedido inválido: envelope (`ApiProblem`) ou domínio (`ApiErrorEnvelope`).",
        "model": ApiProblem | ApiErrorEnvelope,  # type: ignore[operator]
    }
}
