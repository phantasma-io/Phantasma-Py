"""SDK exception hierarchy.

The public SDK raises explicit domain exceptions instead of returning partially
decoded values or letting low-level `struct`/JSON errors leak through API
boundaries.
"""

from __future__ import annotations


class PhantasmaError(Exception):
    """Base class for SDK errors."""


class EncodingError(PhantasmaError, ValueError):
    """Raised when textual or binary data is not valid Phantasma encoding."""


class SerializationError(PhantasmaError, ValueError):
    """Raised when a wire-format payload is malformed or inconsistent."""


class CryptoError(PhantasmaError, ValueError):
    """Raised when cryptographic key, address, or signature input is invalid."""


class RPCError(PhantasmaError):
    """Raised when JSON-RPC transport or response handling fails."""

    def __init__(self, message: str, *, code: int | None = None, data: object | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


class BuilderError(PhantasmaError, ValueError):
    """Raised when an SDK builder cannot produce a valid payload."""
