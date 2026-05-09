"""Text and byte encodings used by Phantasma.

The Base58 implementation is local so address and WIF parsing have no hidden
behavior drift from third-party packages. It implements the Bitcoin alphabet
used by the other SDKs.
"""

from __future__ import annotations

from .errors import EncodingError

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_INDEX = {char: index for index, char in enumerate(BASE58_ALPHABET)}


def encode_base58(data: bytes) -> str:
    """Encode bytes with the Bitcoin/Phantasma Base58 alphabet."""

    value = int.from_bytes(data, "big")
    encoded = ""
    while value:
        value, remainder = divmod(value, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded

    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading_zeroes + (encoded or "")


def decode_base58(text: str) -> bytes:
    """Decode Bitcoin/Phantasma Base58 text."""

    if not isinstance(text, str) or text == "":
        raise EncodingError("base58 text is empty")

    value = 0
    for char in text:
        try:
            digit = _BASE58_INDEX[char]
        except KeyError as exc:
            raise EncodingError(f"invalid base58 character: {char!r}") from exc
        value = value * 58 + digit

    raw = value.to_bytes((value.bit_length() + 7) // 8, "big") if value else b""
    leading_zeroes = len(text) - len(text.lstrip("1"))
    return b"\x00" * leading_zeroes + raw


def decode_hex(value: str) -> bytes:
    """Decode hex text, accepting an optional `0x` prefix."""

    if not isinstance(value, str):
        raise EncodingError("hex value must be text")
    text = value.strip()
    if text.startswith(("0x", "0X")):
        text = text[2:]
    if len(text) % 2 != 0:
        raise EncodingError("hex value must contain an even number of digits")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise EncodingError("invalid hex value") from exc


def encode_hex(data: bytes) -> str:
    """Encode bytes as lowercase hex."""

    return bytes(data).hex()
