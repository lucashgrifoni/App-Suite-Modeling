"""A declared floor is a promise that the tool runs there. Two of them were false.

`pip install open-threat-model` is the advertised install line, `action.yml` runs
`pip install "open-threat-model==${VERSION}"`, and the published pre-commit hook builds its own
isolated environment the same way. All three resolve against the floors in `[project.dependencies]`
— and a resolver that lands on a *declared-supported* version got a console script that died on
`otm --help`, with pip exiting 0 and printing no warning at all. CI never saw it, because CI always
resolves the newest of everything.

Measured against the built 7.9.0 wheel, one fresh venv per constraint (install exited 0 in every
case except where noted):

    typer==0.12.3   RuntimeError: Type not yet supported: str | None
    typer==0.15.3   TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'
    typer==0.15.4   ResolutionImpossible — it caps click<8.2, which the manifest requires
    typer==0.16.0   otm --help / otm validate / otm analyze all exit 0
    pyyaml==6.0     no wheel for CPython 3.11 or 3.12; source build fails with
                    "'build_ext' object has no attribute 'cython_sources'"
    pyyaml==6.0.1   installs and runs
    pydantic==2.5   runs (emits pydantic's own `model_` protected-namespace UserWarning)
    rich==13.7      runs
    combined floors typer==0.16.0 click==8.2.0 pydantic==2.5 pyyaml==6.0.1 rich==13.7 -> all green

The measurement itself needs venvs and a network, so it cannot live in this suite. What lives here
is the thing that decays: the *record*. These tests fail if a floor moves, if a base dependency
appears or disappears, or if the `dev` extra drifts away from the base again — which is how the
broken pairing survived, since `dev` carried its own `typer>=0.12.3` copy.

The last test guards the mirror-image mistake. Raising a floor is only safe up to a version that
actually exists and is actually exercised; a floor above the environment the suite is green in
would be an unmeasured promise pointing the other way.
"""

from __future__ import annotations

import tomllib
from importlib.metadata import version as installed_version
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

#: Canonical name -> lowest version measured to install *and* run. Changing a value here without
#: redoing the measurement above is the defect this file exists to prevent.
_VERIFIED_FLOORS = {
    "click": "8.2",
    "pydantic": "2.5",
    "pyyaml": "6.0.1",
    "rich": "13.7",
    "typer": "0.16",
}

#: The two the `dev` extra also declares, because the tests import the CLI.
_SHARED_WITH_DEV_EXTRA = ("typer", "click")


def _requirements(entries: list[str]) -> dict[str, Requirement]:
    parsed = [Requirement(entry) for entry in entries]
    return {canonicalize_name(req.name): req for req in parsed}


def _base() -> dict[str, Requirement]:
    return _requirements(_PYPROJECT["project"]["dependencies"])


def _dev_extra() -> dict[str, Requirement]:
    return _requirements(_PYPROJECT["project"]["optional-dependencies"]["dev"])


def _floor(req: Requirement) -> str | None:
    """The lowest version the specifier admits, or None when it admits everything."""
    lower = [spec.version for spec in req.specifier if spec.operator in (">=", "==", "~=")]
    return min(lower, key=Version) if lower else None


@pytest.mark.parametrize(("name", "expected"), sorted(_VERIFIED_FLOORS.items()))
def test_each_base_dependency_declares_the_measured_floor(name: str, expected: str) -> None:
    assert _floor(_base()[name]) == expected


def test_the_base_dependency_set_has_not_changed_without_a_measurement() -> None:
    """A new base dependency needs its own floor measured, not inherited by accident."""
    assert sorted(_base()) == sorted(_VERIFIED_FLOORS)


@pytest.mark.parametrize("name", _SHARED_WITH_DEV_EXTRA)
def test_the_dev_extra_does_not_drift_below_the_base_floor(name: str) -> None:
    """`dev` kept its own `typer>=0.12.3` copy; that copy is why the broken pairing stayed alive."""
    assert _floor(_dev_extra()[name]) == _VERIFIED_FLOORS[name]


@pytest.mark.parametrize("name", sorted(_VERIFIED_FLOORS))
def test_no_base_dependency_is_declared_without_a_lower_bound(name: str) -> None:
    assert _floor(_base()[name]) is not None


@pytest.mark.parametrize("name", sorted(_VERIFIED_FLOORS))
def test_the_environment_the_suite_is_green_in_satisfies_every_declared_floor(name: str) -> None:
    """A floor above what is installed here would be a promise nothing exercises."""
    req = _base()[name]
    assert req.specifier.contains(installed_version(name), prereleases=True)
