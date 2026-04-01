"""Testes para helpers de ambiente de desenvolvimento (scripts/dev_env.py)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from dev_env import npm_on_path, repo_root, venv_python


def test_repo_root_is_repo() -> None:
    root = repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "scripts" / "dev_env.py").is_file()


@pytest.mark.parametrize(
    ("platform", "suffix"),
    [
        ("win32", ".venv/Scripts/python.exe"),
        ("linux", ".venv/bin/python"),
        ("darwin", ".venv/bin/python"),
    ],
)
def test_venv_python_path(platform: str, suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", platform)
    root = Path("/repo")
    expected = Path("/repo") / suffix
    assert venv_python(root) == expected


def test_npm_on_path_false_without_npm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert npm_on_path() is False


def test_npm_on_path_true_when_npm_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def _which(name: str) -> str | None:
        if name == "npm":
            return "/usr/bin/npm"
        return None

    monkeypatch.setattr(shutil, "which", _which)
    assert npm_on_path() is True


def test_npm_on_path_true_npm_cmd_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")

    def _which(name: str) -> str | None:
        if name == "npm.cmd":
            return r"C:\Program Files\nodejs\npm.cmd"
        return None

    monkeypatch.setattr(shutil, "which", _which)
    assert npm_on_path() is True
