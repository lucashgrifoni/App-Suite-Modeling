"""Testes para helpers de ambiente de desenvolvimento (scripts/dev_env.py)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from dev_env import npm_on_path, npm_popen, npm_run, repo_root, venv_python


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
    monkeypatch.setattr(sys, "platform", "linux")

    def _which(name: str) -> str | None:
        if name == "npm":
            return "/usr/bin/npm"
        return None

    monkeypatch.setattr(shutil, "which", _which)
    assert npm_on_path() is True


def test_windows_npm_launches_its_cli_directly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    node = tmp_path / "node.exe"
    node.touch()
    cli = tmp_path / "node_modules" / "npm" / "bin" / "npm-cli.js"
    cli.parent.mkdir(parents=True)
    cli.touch()
    paths = {"npm.cmd": str(tmp_path / "npm.cmd")}
    monkeypatch.setattr(shutil, "which", paths.get)
    run = Mock()
    popen = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "Popen", popen)

    cwd = tmp_path / "Workspace & checkout"
    assert npm_on_path() is True
    npm_run(["ci"], cwd=cwd)
    run.assert_called_once_with([str(node), str(cli), "ci"], cwd=cwd, check=True)
    assert npm_popen(["run", "dev"], cwd=cwd) is popen.return_value
    popen.assert_called_once_with([str(node), str(cli), "run", "dev"], cwd=cwd)
