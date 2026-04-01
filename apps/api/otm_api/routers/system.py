from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="Health check",
    description="Liveness probe for load balancers / Kubernetes.",
)
def health() -> dict[str, str]:
    return {"status": "ok"}
