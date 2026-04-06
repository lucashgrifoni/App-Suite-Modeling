"""Installed version of the distributable package."""

from __future__ import annotations

import importlib.metadata


def installed_version() -> str:
    try:
        return importlib.metadata.version("open-threat-model")
    except importlib.metadata.PackageNotFoundError:
        return "dev"
