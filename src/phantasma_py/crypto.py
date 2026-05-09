"""Cryptographic primitives for Phantasma addresses and signatures."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .binary import BinaryWriter
from .encoding import decode_base58, encode_base58
from .errors import CryptoError

ADDRESS_LENGTH = 34
PRIVATE_KEY_LENGTH = 32
PUBLIC_KEY_LENGTH = 32
SIGNATURE_LENGTH = 64


class AddressKind(IntEnum):
    INVALID = 0
    USER = 1
    SYSTEM = 2
    INTEROP = 3


class SignatureKind(IntEnum):
    NONE = 0
    ED25519 = 1
    ECDSA = 2
    RING = 3


@dataclass(frozen=True, slots=True)
class Address:
    """A 34-byte Phantasma address with checked text conversion."""

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != ADDRESS_LENGTH:
            raise CryptoError(f"address length must be {ADDRESS_LENGTH}, got {len(self.data)}")

    @classmethod
    def null(cls) -> Address:
        return cls(bytes(ADDRESS_LENGTH))

    @classmethod
    def from_public_key(cls, public_key: bytes) -> Address:
        raw = bytes(public_key)
        if len(raw) == PUBLIC_KEY_LENGTH:
            return cls(bytes([AddressKind.USER, 0]) + raw)
        if len(raw) == PUBLIC_KEY_LENGTH + 1:
            return cls(bytes([AddressKind.USER]) + raw)
        if len(raw) == 64:
            return cls(bytes([AddressKind.USER, 0]) + raw[:PUBLIC_KEY_LENGTH])
        raise CryptoError(f"invalid public key length: {len(raw)}")

    @classmethod
    def from_text(cls, text: str | None) -> Address:
        if text is None or text == "" or text.upper() == "NULL":
            return cls.null()
        if len(text) < 2:
            raise CryptoError("address text is too short")

        prefix = text[0]
        data = decode_base58(text[1:])
        address = cls(data)
        if prefix == "P" and address.kind is not AddressKind.USER:
            raise CryptoError("address has to be of type User")
        if prefix == "S" and address.kind is not AddressKind.SYSTEM:
            raise CryptoError("address has to be of type System")
        if prefix == "X" and address.kind is not AddressKind.INTEROP:
            raise CryptoError("address has to be of type Interop")
        if prefix not in {"P", "S", "X"}:
            raise CryptoError(f"unknown address prefix: {prefix}")
        return address

    @classmethod
    def from_hash(cls, value: bytes | str) -> Address:
        raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        return cls(bytes([AddressKind.USER, 0]) + hashlib.sha256(raw).digest())

    @property
    def is_null(self) -> bool:
        return self.data == bytes(ADDRESS_LENGTH)

    @property
    def kind(self) -> AddressKind:
        if self.is_null:
            return AddressKind.SYSTEM
        if self.data[0] >= AddressKind.INTEROP:
            return AddressKind.INTEROP
        if self.data[0] == AddressKind.SYSTEM:
            return AddressKind.SYSTEM
        if self.data[0] == AddressKind.USER:
            return AddressKind.USER
        return AddressKind.INVALID

    @property
    def public_key(self) -> bytes:
        if self.kind is not AddressKind.USER:
            raise CryptoError("only user addresses contain an Ed25519 public key")
        return self.data[2:]

    @property
    def text(self) -> str:
        if self.is_null:
            return "NULL"
        prefix = "P"
        if self.kind is AddressKind.SYSTEM:
            prefix = "S"
        elif self.kind is AddressKind.INTEROP:
            prefix = "X"
        return prefix + encode_base58(self.data)

    def prefixed_bytes(self) -> bytes:
        """Classic serialization form: var-bytes length prefix plus address."""

        writer = BinaryWriter()
        writer.write_var_bytes(self.data)
        return writer.bytes()

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class Hash:
    """A fixed 32-byte hash."""

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != 32:
            raise CryptoError(f"hash length must be 32, got {len(self.data)}")

    @classmethod
    def sha256(cls, data: bytes) -> Hash:
        return cls(hashlib.sha256(data).digest())

    @classmethod
    def from_hex(cls, text: str) -> Hash:
        return cls(bytes.fromhex(text))

    @property
    def hex(self) -> str:
        return self.data.hex().upper()

    def difficulty(self) -> int:
        """Return Phantasma proof-of-work difficulty.

        Classic Phantasma SDKs treat hash bytes as a little-endian integer for
        PoW. This intentionally matches the Go/TypeScript `GetDifficulty`
        helpers and the validator's `hash.GetDifficulty()` check.
        """

        last_set_bit = 0
        for byte_index, byte in enumerate(self.data):
            for bit_index in range(8):
                if byte & (1 << bit_index):
                    last_set_bit = 1 + (byte_index << 3) + bit_index
        return 256 - last_set_bit

    def __str__(self) -> str:
        return self.hex


@dataclass(frozen=True, slots=True)
class Ed25519Signature:
    """A 64-byte Ed25519 signature."""

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != SIGNATURE_LENGTH:
            raise CryptoError(f"signature length must be {SIGNATURE_LENGTH}, got {len(self.data)}")

    @property
    def kind(self) -> SignatureKind:
        return SignatureKind.ED25519

    def verify(self, message: bytes, addresses: Iterable[Address]) -> bool:
        for address in addresses:
            if address.kind is not AddressKind.USER:
                continue
            try:
                ed25519.Ed25519PublicKey.from_public_bytes(address.public_key).verify(self.data, message)
                return True
            except InvalidSignature:
                continue
        return False

    def serialize_data(self) -> bytes:
        writer = BinaryWriter()
        writer.write_var_bytes(self.data)
        return writer.bytes()


@dataclass(frozen=True, slots=True)
class PhantasmaKeys:
    """An Ed25519 key pair with Phantasma WIF and address helpers."""

    private_key: bytes

    def __post_init__(self) -> None:
        raw = bytes(self.private_key)
        if len(raw) == 64:
            raw = raw[:PRIVATE_KEY_LENGTH]
        if len(raw) != PRIVATE_KEY_LENGTH:
            raise CryptoError(f"private key length must be {PRIVATE_KEY_LENGTH}, got {len(raw)}")
        object.__setattr__(self, "private_key", raw)

    @classmethod
    def generate(cls) -> PhantasmaKeys:
        return cls(os.urandom(PRIVATE_KEY_LENGTH))

    @classmethod
    def from_wif(cls, wif: str) -> PhantasmaKeys:
        if not wif:
            raise CryptoError("WIF is required")
        data = decode_base58(wif)
        if len(data) != 38:
            raise CryptoError("invalid WIF length")
        payload, checksum = data[:-4], data[-4:]
        if _double_sha256(payload)[:4] != checksum:
            raise CryptoError("invalid WIF checksum")
        if len(payload) != 34 or payload[0] != 0x80 or payload[-1] != 0x01:
            raise CryptoError("invalid compressed Ed25519 WIF payload")
        return cls(payload[1:33])

    @property
    def _private_object(self) -> ed25519.Ed25519PrivateKey:
        return ed25519.Ed25519PrivateKey.from_private_bytes(self.private_key)

    @property
    def public_key(self) -> bytes:
        return self._private_object.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def address(self) -> Address:
        return Address.from_public_key(self.public_key)

    def to_wif(self) -> str:
        payload = b"\x80" + self.private_key + b"\x01"
        return encode_base58(payload + _double_sha256(payload)[:4])

    def sign(self, message: bytes) -> Ed25519Signature:
        return Ed25519Signature(self._private_object.sign(bytes(message)))

    def __str__(self) -> str:
        return self.address.text


def _double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


NULL_ADDRESS = Address.null()
