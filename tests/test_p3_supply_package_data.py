"""The wheel must describe the source, not the builder's disk.

`[tool.setuptools.package-data]` used four bare recursive globs (`data/**/*`, `assets/*`) with no
exclusion and no MANIFEST.in, so setuptools copied whatever happened to exist under those
directories at build time. Measured, not hypothetical: importing the two data packages (which a
test run does) leaves `__pycache__/__init__.cpython-312.pyc` beside the threat catalog, and the
same tree then builds a different artifact —

    old globs, tree dirtied by a test run   321 entries, 2 .pyc  shipped
    new globs, same dirty tree              319 entries, 0 .pyc, all 84 data files intact

— which is what makes an independent rebuild useless as a tamper check against the build-provenance
attestation the publish workflow produces. The release path happens to be clean today because it
builds on a fresh checkout and runs no tests first; that is ordering, not construction.

Naming extensions instead of `**/*` fixes it, and introduces its own failure mode: a data file with
a new extension would stop shipping, silently, and the first symptom would be a
`FileNotFoundError` inside somebody else's install. So the first test below walks the directories
on disk and fails if anything present is not covered by a declared pattern. Adding
`data/packs/x.csv` breaks the build here, where it is cheap, instead of at a user's import.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
_SETUPTOOLS = _PYPROJECT["tool"]["setuptools"]
_PACKAGE_DATA: dict[str, list[str]] = _SETUPTOOLS["package-data"]
_EXCLUDE_PACKAGE_DATA: dict[str, list[str]] = _SETUPTOOLS["exclude-package-data"]
_WHERE: list[str] = _SETUPTOOLS["packages"]["find"]["where"]

_PACKAGES = sorted(_PACKAGE_DATA)

#: Bytecode and editor debris: never data, and the reason the globs needed narrowing.
_MUST_BE_EXCLUDED = ("**/__pycache__/*", "*.pyc", "*.pyo")


def _package_dir(package: str) -> Path:
    for root in _WHERE:
        candidate = _ROOT / root / package
        if candidate.is_dir():
            return candidate
    raise AssertionError(f"{package} is declared in package-data but is not under any `where` root")


def _declared_files(package: str) -> set[Path]:
    base = _package_dir(package)
    declared: set[Path] = set()
    for pattern in _PACKAGE_DATA[package]:
        declared.update(path for path in base.glob(pattern) if path.is_file())
    return declared


def _present_files(package: str) -> set[Path]:
    """Everything actually on disk under the directories the patterns point at."""
    base = _package_dir(package)
    roots = {pattern.split("/")[0] for pattern in _PACKAGE_DATA[package]}
    present: set[Path] = set()
    for root in roots:
        present.update(path for path in (base / root).rglob("*") if path.is_file())
    return present


def _is_python_module(path: Path) -> bool:
    """`.py` under a data directory ships as a module via `packages.find`, not as package data."""
    return path.suffix == ".py"


def _is_build_debris(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


@pytest.mark.parametrize("package", _PACKAGES)
def test_every_data_file_on_disk_is_covered_by_a_declared_pattern(package: str) -> None:
    """Guards the cost of naming extensions: a new one must not vanish from the wheel."""
    uncovered = _present_files(package) - _declared_files(package)
    surprising = [p for p in uncovered if not _is_python_module(p) and not _is_build_debris(p)]
    unexplained = sorted(str(p.relative_to(_ROOT)) for p in surprising)
    assert unexplained == []


@pytest.mark.parametrize("package", _PACKAGES)
def test_no_package_data_pattern_is_an_unfiltered_glob(package: str) -> None:
    """`data/**/*` ships whatever is lying around; every pattern must name what it means."""
    unfiltered = sorted(p for p in _PACKAGE_DATA[package] if not Path(p).suffix)
    assert unfiltered == []


@pytest.mark.parametrize("package", _PACKAGES)
def test_every_declared_pattern_still_matches_something(package: str) -> None:
    """A pattern that matches nothing is a rename nobody noticed, not a decision."""
    empty = sorted(p for p in _PACKAGE_DATA[package] if not any(_package_dir(package).glob(p)))
    assert empty == []


@pytest.mark.parametrize("pattern", _MUST_BE_EXCLUDED)
def test_bytecode_stays_excluded_for_every_package(pattern: str) -> None:
    assert pattern in _EXCLUDE_PACKAGE_DATA["*"]


def test_the_shipped_data_set_is_not_empty() -> None:
    """Control: the assertions above would all pass on a configuration that ships nothing."""
    shipped = sum(len(_declared_files(package)) for package in _PACKAGES)
    assert shipped > 80
