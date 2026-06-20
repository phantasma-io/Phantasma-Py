"""Version single-source-of-truth tests.

The package version is declared only in pyproject.toml and resolved at runtime from the installed
package metadata (see ``phantasma_py._version``). These tests guard that single source against drift -
a reintroduced hardcoded literal, a misfired "not installed" fallback, or a wrong distribution name -
all of which would make the runtime version disagree with what gets published.
"""

import tomllib
from pathlib import Path

from phantasma_py import __version__


def test_runtime_version_matches_pyproject() -> None:
    # __version__ is read from package metadata; it must equal the one declared source,
    # pyproject.toml [project].version. Compared against the file (not importlib.metadata again)
    # so the assertion is independent of the implementation and fails on real drift.
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert __version__ == declared


def test_runtime_version_is_not_the_uninstalled_fallback() -> None:
    # When the package is installed (the case under test), the metadata lookup must succeed, so the
    # "0.0.0" PackageNotFoundError sentinel must NOT leak into a real run.
    assert __version__ != "0.0.0"
