"""Record the collection size for the local regression gate."""

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--gate-count-file", required=True, type=Path)


def pytest_sessionfinish(session: pytest.Session) -> None:
    path = session.config.getoption("--gate-count-file")
    path.write_text(f"{session.testscollected}\n", encoding="utf-8")
