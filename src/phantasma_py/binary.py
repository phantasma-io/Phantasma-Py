"""Phantasma VM binary reader/writer.

This module is intentionally separate from `carbon`: VM script transactions and
VM scripts use variable-length integer prefixes, while Carbon uses fixed
little-endian array lengths and compact Int256 encoding.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .errors import SerializationError

MAX_ARRAY_SIZE = 0x1000000


@dataclass(slots=True)
class BinaryWriter:
    """Append-only writer for Phantasma VM wire primitives."""

    _buffer: bytearray = field(default_factory=bytearray)

    def write_u8(self, value: int) -> None:
        if value < 0 or value > 0xFF:
            raise SerializationError(f"u8 out of range: {value}")
        self._buffer.append(value)

    def write_u16_le(self, value: int) -> None:
        self._buffer.extend(struct.pack("<H", _check_unsigned(value, 16)))

    def write_u32_le(self, value: int) -> None:
        self._buffer.extend(struct.pack("<I", _check_unsigned(value, 32)))

    def write_u64_le(self, value: int) -> None:
        self._buffer.extend(struct.pack("<Q", _check_unsigned(value, 64)))

    def write_i64_le(self, value: int) -> None:
        self._buffer.extend(struct.pack("<q", _check_signed(value, 64)))

    def write_bool(self, value: bool) -> None:
        self.write_u8(1 if value else 0)

    def write(self, data: bytes) -> None:
        self._buffer.extend(bytes(data))

    def write_var_uint(self, value: int) -> None:
        if value < 0:
            raise SerializationError("varuint cannot be negative")
        if value < 0xFD:
            self.write_u8(value)
        elif value <= 0xFFFF:
            self.write_u8(0xFD)
            self.write_u16_le(value)
        elif value <= 0xFFFFFFFF:
            self.write_u8(0xFE)
            self.write_u32_le(value)
        else:
            self.write_u8(0xFF)
            self.write_u64_le(value)

    def write_var_bytes(self, data: bytes) -> None:
        raw = bytes(data)
        self.write_var_uint(len(raw))
        self.write(raw)

    def write_string(self, value: str) -> None:
        self.write_var_bytes(value.encode("utf-8"))

    def write_big_integer(self, value: int) -> None:
        self.write_var_bytes(big_int_to_vm_bytes(value))

    def bytes(self) -> bytes:
        return bytes(self._buffer)


@dataclass(slots=True)
class BinaryReader:
    """Bounds-checked reader for Phantasma VM wire primitives."""

    _data: bytes
    _offset: int = 0

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    def assert_eof(self) -> None:
        if self.remaining != 0:
            raise SerializationError(f"unexpected trailing bytes: {self.remaining}")

    def read(self, count: int) -> bytes:
        if count < 0 or count > self.remaining:
            raise SerializationError("end of stream reached")
        start = self._offset
        self._offset += count
        return self._data[start : start + count]

    def read_u8(self) -> int:
        return self.read(1)[0]

    def read_u16_le(self) -> int:
        return int(struct.unpack("<H", self.read(2))[0])

    def read_u32_le(self) -> int:
        return int(struct.unpack("<I", self.read(4))[0])

    def read_u64_le(self) -> int:
        return int(struct.unpack("<Q", self.read(8))[0])

    def read_i64_le(self) -> int:
        return int(struct.unpack("<q", self.read(8))[0])

    def read_bool(self) -> bool:
        return self.read_u8() != 0

    def read_var_uint(self) -> int:
        first = self.read_u8()
        if first == 0xFD:
            return self.read_u16_le()
        if first == 0xFE:
            return self.read_u32_le()
        if first == 0xFF:
            return self.read_u64_le()
        return first

    def read_var_bytes(self, *, max_size: int = MAX_ARRAY_SIZE) -> bytes:
        size = self.read_var_uint()
        if size > max_size:
            raise SerializationError(f"byte array too large: {size}")
        return self.read(size)

    def read_string(self) -> str:
        return self.read_var_bytes().decode("utf-8")

    def read_big_integer(self) -> int:
        return vm_bytes_to_big_int(self.read_var_bytes())


def big_int_to_vm_bytes(value: int) -> bytes:
    """Encode a signed integer like Gen2 VM `ToSignedByteArray()`."""

    # BinaryWriter/VMObject numbers use Phantasma's Gen2 padded VM integer
    # storage. ScriptBuilder LOAD uses the unpadded C# bytes directly, so keep
    # this helper dedicated to persisted/serialized VM BigInteger values.
    raw = _big_int_to_csharp_bytes(value)
    if value < 0:
        if len(raw) == 1:
            raw += b"\xff\xff"
        elif raw[-1] == 0xFF:
            raw += b"\xff"
    elif raw[-1] != 0x00:
        raw += b"\x00"
    return raw


def _big_int_to_csharp_bytes(value: int) -> bytes:
    """Return normal C# `BigInteger.ToByteArray()` bytes, little-endian signed."""

    if value == 0:
        return b"\x00"
    bit_count = value.bit_length() + 1 if value > 0 else (~value).bit_length() + 1
    width = max(1, (bit_count + 7) // 8)
    return value.to_bytes(width, "little", signed=True)


def vm_bytes_to_big_int(data: bytes) -> int:
    if len(data) == 0:
        return 0
    return int.from_bytes(data, "little", signed=True)


def _check_unsigned(value: int, bits: int) -> int:
    if value < 0 or value >= 1 << bits:
        raise SerializationError(f"u{bits} out of range: {value}")
    return value


def _check_signed(value: int, bits: int) -> int:
    minimum = -(1 << (bits - 1))
    maximum = (1 << (bits - 1)) - 1
    if value < minimum or value > maximum:
        raise SerializationError(f"i{bits} out of range: {value}")
    return value
