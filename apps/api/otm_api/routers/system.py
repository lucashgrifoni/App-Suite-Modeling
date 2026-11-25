from __future__ import annotations

from fastapi import APIRouter

from otm_api.error_models import API_ERROR_RESPONSES

router = APIRouter(tags=["System"], responses=API_ERROR_RESPONSES)


@router.get(
    "/health",
    summary="Health check",
    description="Liveness probe for load balancers / Kubernetes.",
)
def health() -> dict[str, str]:
    return {"status": "ok"}


# HEAD registado à parte porque o `APIRoute` do FastAPI, ao contrário do `Route` do
# Starlette, não o acrescenta junto do GET: monitores que sondam com HEAD por omissão
# (`curl -I`, UptimeRobot, alguns `check` de HAProxy/NGINX) apanhavam 405 num serviço
# saudável, precisamente na rota anunciada como liveness probe.
#
# Duas rotas e não `methods=["GET", "HEAD"]`: uma rota com dois métodos reutiliza o
# mesmo `operationId` nos dois, o que produz um OpenAPI inválido (e avisos de duplicação
# na geração dos tipos TS). Fica fora do schema porque HEAD é, por definição (RFC 9110),
# o GET sem corpo — não é uma operação distinta a documentar.
@router.head("/health", include_in_schema=False)
def health_head() -> dict[str, str]:
    return {"status": "ok"}
