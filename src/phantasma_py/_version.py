"""Single source for the package version, shared by runtime payloads (the SDK payload tag in
``transaction.py``) and the public ``__version__`` export.

The version is resolved from the installed package metadata (produced from ``pyproject.toml`` at
build/install time) instead of a hardcoded literal, so it lives in exactly one place -
``pyproject.toml`` - and can never drift out of sync with the published package.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("phantasma-sdk-py")
except PackageNotFoundError:
    # Only reached when imported from a source checkout that was never installed (no dist metadata).
    # Normal usage installs the package (pip install / editable), so this is a dev-only fallback.
    __version__ = "0.0.0"
