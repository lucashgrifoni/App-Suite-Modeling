"""
CORS e perfil de ambiente (`OTM_ENV`, `OTM_CORS_ORIGINS`).

Em `production` sem `OTM_CORS_ORIGINS`, as origens ficam vazias (CORS desativado para browser).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CorsProfile:
    origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    environment: str


def resolve_cors_profile() -> CorsProfile:
    raw_env = (os.environ.get("OTM_ENV") or "development").strip().lower()
    if raw_env in ("prod", "production"):
        environment = "production"
    elif raw_env == "staging":
        environment = "staging"
    else:
        environment = "development"

    raw_origins = (os.environ.get("OTM_CORS_ORIGINS") or "").strip()
    if raw_origins:
        origins = [x.strip() for x in raw_origins.split(",") if x.strip()]
    elif environment == "production":
        origins = []
    else:
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    if environment == "development":
        methods = ["*"]
        headers = ["*"]
    else:
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
        headers = ["Content-Type", "Authorization", "X-Request-ID", "Accept"]

    return CorsProfile(
        origins=origins,
        allow_methods=methods,
        allow_headers=headers,
        environment=environment,
    )
