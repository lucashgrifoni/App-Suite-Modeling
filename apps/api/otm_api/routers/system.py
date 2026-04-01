from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Sistema"])


@router.get(
    "/health",
    summary="Health check",
    description="Indica que o processo está vivo (load balancers / k8s).",
)
def health() -> dict[str, str]:
    return {"status": "ok"}
