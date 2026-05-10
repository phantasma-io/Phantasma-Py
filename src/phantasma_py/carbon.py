"""Carbon wire-format support.

Carbon uses a different binary contract from Phantasma VM scripts:
fixed-width little-endian integers, zero-terminated strings, and compact signed
Int256 values. The implementation below mirrors the current Go/C#/TS/C++ SDK
contract and keeps all parsing bounds-checked.
"""

from __future__ import annotations

import base64
import json
import re
import struct
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import Any, ClassVar, Protocol, Self, TypeVar, cast

from .crypto import Address, AddressKind, PhantasmaKeys
from .encoding import decode_hex
from .errors import BuilderError, CryptoError, SerializationError


class CarbonSerializable(Protocol):
    def write_carbon(self, writer: CarbonWriter) -> None: ...

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> Self: ...


C = TypeVar("C", bound=CarbonSerializable)


class FixedBytes(bytes):
    """Base class for fixed-width Carbon byte values."""

    SIZE: ClassVar[int] = 0

    def __new__(cls, value: bytes | bytearray | str = b"") -> Self:
        raw = decode_hex(value) if isinstance(value, str) else bytes(value)
        if len(raw) == 0 and cls.SIZE:
            raw = bytes(cls.SIZE)
        if len(raw) != cls.SIZE:
            raise SerializationError(f"{cls.__name__} length must be {cls.SIZE}, got {len(raw)}")
        return bytes.__new__(cls, raw)

    @classmethod
    def from_hex(cls, value: str) -> Self:
        return cls(decode_hex(value))

    def __str__(self) -> str:
        return bytes(self).hex()


class Bytes16(FixedBytes):
    SIZE = 16


class Bytes32(FixedBytes):
    SIZE = 32


class Bytes64(FixedBytes):
    SIZE = 64


EMPTY_BYTES16 = Bytes16()
EMPTY_BYTES32 = Bytes32()
EMPTY_BYTES64 = Bytes64()
SYSTEM_ADDRESS_NULL = Bytes32()
SYSTEM_ADDRESS_GAS_POOL = Bytes32(bytes(31) + b"\x01")
SYSTEM_ADDRESS_DATA_POOL = Bytes32(bytes(31) + b"\x02")
STANDARD_META_ID = "_i"
_MISSING = object()


@dataclass(frozen=True, slots=True)
class SmallString:
    """Carbon one-byte-length UTF-8 string."""

    value: str = ""

    def __post_init__(self) -> None:
        raw = self.value.encode("utf-8")
        if len(raw) > 255:
            raise SerializationError("SmallString exceeds 255 UTF-8 bytes")

    def write_carbon(self, writer: CarbonWriter) -> None:
        raw = self.value.encode("utf-8")
        writer.write1(len(raw))
        writer.write(raw)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> SmallString:
        return cls(reader.read(reader.read1()).decode("utf-8"))

    def __str__(self) -> str:
        return self.value


class CarbonWriter:
    """Writer for Carbon binary primitives."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def write(self, data: bytes) -> None:
        self._buffer.extend(bytes(data))

    def write1(self, value: int) -> None:
        if value < 0 or value > 0xFF:
            raise SerializationError(f"u8 out of range: {value}")
        self._buffer.append(value)

    def write2(self, value: int) -> None:
        self.write(struct.pack("<h", _check_signed(value, 16)))

    def write4(self, value: int) -> None:
        self.write(struct.pack("<i", _check_signed(value, 32)))

    def write4u(self, value: int) -> None:
        self.write(struct.pack("<I", _check_unsigned(value, 32)))

    def write8(self, value: int) -> None:
        self.write(struct.pack("<q", _check_signed(value, 64)))

    def write8u(self, value: int) -> None:
        self.write(struct.pack("<Q", _check_unsigned(value, 64)))

    def write16(self, value: Bytes16 | bytes) -> None:
        self.write(bytes(Bytes16(value)))

    def write32(self, value: Bytes32 | bytes) -> None:
        self.write(bytes(Bytes32(value)))

    def write64(self, value: Bytes64 | bytes) -> None:
        self.write(bytes(Bytes64(value)))

    def write_big_int(self, value: int) -> None:
        if value == 0:
            self.write1(0)
            return

        word = _big_int_word(value)
        fill = 0xFF if word[31] & 0x80 else 0x00
        length = len(word)
        while length > 0 and word[length - 1] == fill:
            length -= 1
        header = length & 0x3F
        if fill == 0xFF:
            header |= 0x80
        self.write1(header)
        self.write(word[:length])

    def write_big_int_array(self, values: list[int]) -> None:
        self.write4(len(values))
        for value in values:
            self.write_big_int(value)

    def write_string_z(self, value: str) -> None:
        if "\x00" in value:
            raise SerializationError("zero-terminated string contains a zero byte")
        self.write(value.encode("utf-8"))
        self.write1(0)

    def write_string_z_array(self, values: list[str]) -> None:
        self.write4(len(values))
        for value in values:
            self.write_string_z(value)

    def write_byte_array(self, data: bytes) -> None:
        raw = bytes(data)
        self.write4(len(raw))
        self.write(raw)

    def write_byte_arrays(self, values: list[bytes]) -> None:
        self.write4(len(values))
        for value in values:
            self.write_byte_array(value)

    def write_int_array(self, values: list[int], width: int, *, signed: bool) -> None:
        self.write4(len(values))
        for value in values:
            if width == 1:
                self.write1(value & 0xFF)
            elif width == 2:
                self.write2(value)
            elif width == 4:
                self.write4(value)
            elif width == 8:
                self.write8(value) if signed else self.write8u(value)
            else:
                raise SerializationError(f"unsupported integer width: {width}")

    def bytes(self) -> bytes:
        return bytes(self._buffer)


class CarbonReader:
    """Bounds-checked reader for Carbon binary primitives."""

    def __init__(self, data: bytes) -> None:
        self._data = bytes(data)
        self._offset = 0

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    def assert_eof(self) -> None:
        if self.remaining:
            raise SerializationError(f"unexpected trailing bytes: {self.remaining}")

    def read(self, count: int) -> bytes:
        if count < 0 or count > self.remaining:
            raise SerializationError("end of stream reached")
        start = self._offset
        self._offset += count
        return self._data[start : start + count]

    def read_length(self) -> int:
        length = self.read4()
        if length < 0:
            raise SerializationError("negative array length")
        if length > self.remaining:
            raise SerializationError(f"array length {length} exceeds remaining bytes {self.remaining}")
        return length

    def read1(self) -> int:
        return self.read(1)[0]

    def read2(self) -> int:
        return int(struct.unpack("<h", self.read(2))[0])

    def read4(self) -> int:
        return int(struct.unpack("<i", self.read(4))[0])

    def read4u(self) -> int:
        return int(struct.unpack("<I", self.read(4))[0])

    def read8(self) -> int:
        return int(struct.unpack("<q", self.read(8))[0])

    def read8u(self) -> int:
        return int(struct.unpack("<Q", self.read(8))[0])

    def read16(self) -> Bytes16:
        return Bytes16(self.read(16))

    def read32(self) -> Bytes32:
        return Bytes32(self.read(32))

    def read64(self) -> Bytes64:
        return Bytes64(self.read(64))

    def read_big_int(self) -> int:
        return self.read_big_int_with_header(None)

    def read_big_int_with_header(self, header: int | None) -> int:
        if header is None:
            header = self.read1()
        if header == 0:
            return 0
        length = header & 0x3F
        if header & 0x40 or length > 32:
            raise SerializationError("BigInt too big")
        fill = 0xFF if header & 0x80 else 0x00
        word = bytearray(32)
        if length:
            word[:length] = self.read(length)
        for index in range(length, 32):
            word[index] = fill
        if (word[31] & 0x80) != (header & 0x80):
            raise SerializationError("non-standard BigInt header")
        return _int_from_word(bytes(word))

    def read_big_int_array(self) -> list[int]:
        return [self.read_big_int() for _ in range(self.read_length())]

    def read_string_z(self) -> str:
        start = self._offset
        while True:
            if self._offset >= len(self._data):
                raise SerializationError("end of stream reached")
            if self._data[self._offset] == 0:
                break
            self._offset += 1
        raw = self._data[start : self._offset]
        self._offset += 1
        return raw.decode("utf-8")

    def read_string_z_array(self) -> list[str]:
        return [self.read_string_z() for _ in range(self.read_length())]

    def read_byte_array(self) -> bytes:
        return self.read(self.read_length())

    def read_byte_arrays(self) -> list[bytes]:
        return [self.read_byte_array() for _ in range(self.read_length())]

    def read_int_array(self, width: int, *, signed: bool) -> list[int]:
        count = self.read_length()
        out: list[int] = []
        for _ in range(count):
            if width == 1:
                value = self.read1()
                if signed and value >= 0x80:
                    value -= 0x100
            elif width == 2:
                value = self.read2()
            elif width == 4:
                value = self.read4()
            elif width == 8:
                value = self.read8() if signed else self.read8u()
            else:
                raise SerializationError(f"unsupported integer width: {width}")
            out.append(value)
        return out


@dataclass(frozen=True, slots=True)
class IntX:
    """Carbon variable-width signed integer."""

    value: int = 0

    @property
    def is_8_byte_safe(self) -> bool:
        return -(1 << 63) <= self.value <= (1 << 63) - 1

    def write_carbon(self, writer: CarbonWriter) -> None:
        if self.is_8_byte_safe:
            writer.write1(0x88 if self.value < 0 else 0x08)
            writer.write8(self.value)
            return
        writer.write_big_int(self.value)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> IntX:
        header = reader.read1()
        length = header & 0x3F
        if length < 8:
            raise SerializationError("invalid IntX packing")
        if length == 8:
            raw = reader.read(8)
            value = int.from_bytes(raw, "little", signed=True)
            header_negative = bool(header & 0x80)
            if header_negative == (value < 0):
                return cls(value)
            fill = 0xFF if header_negative else 0x00
            word = raw + bytes([fill]) * 24
            return cls(_int_from_word(word))
        return cls(reader.read_big_int_with_header(header))

    def __str__(self) -> str:
        return str(self.value)


class TxType(IntEnum):
    CALL = 0
    CALL_MULTI = 1
    TRADE = 2
    TRANSFER_FUNGIBLE = 3
    TRANSFER_FUNGIBLE_GAS_PAYER = 4
    TRANSFER_NON_FUNGIBLE_SINGLE = 5
    TRANSFER_NON_FUNGIBLE_SINGLE_GAS_PAYER = 6
    TRANSFER_NON_FUNGIBLE_MULTI = 7
    TRANSFER_NON_FUNGIBLE_MULTI_GAS_PAYER = 8
    MINT_FUNGIBLE = 9
    BURN_FUNGIBLE = 10
    BURN_FUNGIBLE_GAS_PAYER = 11
    MINT_NON_FUNGIBLE = 12
    BURN_NON_FUNGIBLE = 13
    BURN_NON_FUNGIBLE_GAS_PAYER = 14
    PHANTASMA = 15
    PHANTASMA_RAW = 16


class ModuleID(IntEnum):
    GOVERNANCE = 0
    TOKEN = 1
    PHANTASMA = 2
    PHANTASMA_VM = 2
    ORG = 3
    MARKET = 4
    INTERNAL = 0xFFFFFFFF


class TokenContractMethod(IntEnum):
    TRANSFER_FUNGIBLE = 0
    TRANSFER_NON_FUNGIBLE = 1
    CREATE_TOKEN = 2
    MINT_FUNGIBLE = 3
    BURN_FUNGIBLE = 4
    GET_BALANCE = 5
    CREATE_TOKEN_SERIES = 6
    DELETE_TOKEN_SERIES = 7
    MINT_NON_FUNGIBLE = 8
    BURN_NON_FUNGIBLE = 9
    GET_INSTANCES = 10
    GET_NON_FUNGIBLE_INFO = 11
    GET_NON_FUNGIBLE_INFO_BY_ROM_ID = 12
    GET_SERIES_INFO = 13
    GET_SERIES_INFO_BY_META_ID = 14
    GET_TOKEN_INFO = 15
    GET_TOKEN_INFO_BY_SYMBOL = 16
    GET_TOKEN_SUPPLY = 17
    GET_SERIES_SUPPLY = 18
    GET_TOKEN_ID_BY_SYMBOL = 19
    GET_BALANCES = 20
    CREATE_MINTED_TOKEN_SERIES = 21
    APPLY_INFLATION = 22
    UPDATE_TOKEN_METADATA = 23
    GET_NEXT_TOKEN_INFLATION = 24
    SET_TOKENS_CONFIG = 25
    UPDATE_SERIES_METADATA = 26
    MINT_PHANTASMA_NON_FUNGIBLE = 27


class TokenFlags(IntFlag):
    NONE = 0
    BIG_FUNGIBLE = 1 << 0
    NON_FUNGIBLE = 1 << 1


class TokensConfigFlags(IntFlag):
    NONE = 0
    REQUIRE_METADATA = 1 << 0
    REQUIRE_SYMBOL = 1 << 1
    REQUIRE_NFT_META_ID = 1 << 2
    REQUIRE_NFT_STANDARD = 1 << 3
    ALLOW_EXPLICIT_NFT_META_ID_MINT = 1 << 4


class ListingType(IntEnum):
    FIXED_PRICE = 0


class MarketContractMethod(IntEnum):
    SELL_TOKEN = 0
    SELL_TOKEN_BY_ID = 1
    CANCEL_SALE = 2
    CANCEL_SALE_BY_ID = 3
    BUY_TOKEN = 4
    BUY_TOKEN_BY_ID = 5
    GET_TOKEN_LISTING_COUNT = 6
    GET_TOKEN_LISTING_INFO = 7
    GET_TOKEN_LISTING_INFO_BY_ID = 8


class MarketConfigFlags(IntFlag):
    NONE = 0
    PRICE_REQUIRED = 1 << 0
    ENFORCE_ROYALTIES = 1 << 1
    CAN_CANCEL_EARLY = 1 << 2
    CAN_PURCHASE_LATE = 1 << 3


MARKET_MINIMUM_LISTING_TIME_MS = 1_000
MARKET_MAXIMUM_LISTING_TIME_MS = 1_000 * 60 * 60 * 24 * 90
MARKET_DELISTING_GRACE_MS = 1_000 * 60 * 60 * 24
MARKET_ROYALTY_ONE_PERCENT = 10_000_000
MARKET_ROYALTY_HUNDRED_PERCENT = 100 * MARKET_ROYALTY_ONE_PERCENT


class VMType(IntEnum):
    DYNAMIC = 0
    ARRAY = 1
    BYTES = 1 << 1
    STRUCT = 2 << 1
    INT8 = 3 << 1
    INT16 = 4 << 1
    INT32 = 5 << 1
    INT64 = 6 << 1
    INT256 = 7 << 1
    BYTES16 = 8 << 1
    BYTES32 = 9 << 1
    BYTES64 = 10 << 1
    STRING = 11 << 1
    ARRAY_DYNAMIC = ARRAY | DYNAMIC
    ARRAY_BYTES = ARRAY | BYTES
    ARRAY_STRUCT = ARRAY | STRUCT
    ARRAY_INT8 = ARRAY | INT8
    ARRAY_INT16 = ARRAY | INT16
    ARRAY_INT32 = ARRAY | INT32
    ARRAY_INT64 = ARRAY | INT64
    ARRAY_INT256 = ARRAY | INT256
    ARRAY_BYTES16 = ARRAY | BYTES16
    ARRAY_BYTES32 = ARRAY | BYTES32
    ARRAY_BYTES64 = ARRAY | BYTES64
    ARRAY_STRING = ARRAY | STRING


class VMStructFlags(IntFlag):
    NONE = 0
    DYNAMIC_EXTRAS = 1 << 0
    IS_SORTED = 1 << 1


def serialize(value: CarbonSerializable) -> bytes:
    writer = CarbonWriter()
    value.write_carbon(writer)
    return writer.bytes()


def deserialize(data: bytes, cls: type[CarbonSerializable]) -> CarbonSerializable:
    reader = CarbonReader(data)
    value = cls.read_carbon(reader)
    reader.assert_eof()
    return value


def bytes32_from_public_key(public_key: bytes) -> Bytes32:
    raw = bytes(public_key)
    if len(raw) != 32:
        raise CryptoError(f"public key length must be 32, got {len(raw)}")
    return Bytes32(raw)


def bytes32_from_phantasma_address(address: Address) -> Bytes32:
    if address.kind not in {AddressKind.USER, AddressKind.SYSTEM}:
        raise CryptoError(f"unsupported address kind {address.kind}")
    return Bytes32(address.data[2:])


def bytes32_from_phantasma_address_text(text: str) -> Bytes32:
    return bytes32_from_phantasma_address(Address.from_text(text))


@dataclass(slots=True)
class VMVariableSchema:
    type: VMType
    struct_def: VMStructSchema | None = None

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.type)
        if self.type in {VMType.STRUCT, VMType.ARRAY_STRUCT}:
            (self.struct_def or VMStructSchema()).write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> VMVariableSchema:
        vm_type = VMType(reader.read1())
        struct_def = VMStructSchema.read_carbon(reader) if vm_type in {VMType.STRUCT, VMType.ARRAY_STRUCT} else None
        return cls(vm_type, struct_def)


@dataclass(slots=True)
class VMNamedVariableSchema:
    name: SmallString
    schema: VMVariableSchema

    @classmethod
    def make(cls, name: str, vm_type: VMType, struct_def: VMStructSchema | None = None) -> VMNamedVariableSchema:
        return cls(SmallString(name), VMVariableSchema(vm_type, struct_def))

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.name.write_carbon(writer)
        self.schema.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> VMNamedVariableSchema:
        return cls(SmallString.read_carbon(reader), VMVariableSchema.read_carbon(reader))


@dataclass(slots=True)
class VMStructSchema:
    fields: list[VMNamedVariableSchema] = field(default_factory=list)
    flags: VMStructFlags = VMStructFlags.NONE

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write4(len(self.fields))
        for item in self.fields:
            item.write_carbon(writer)
        writer.write1(self.flags)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> VMStructSchema:
        fields = [VMNamedVariableSchema.read_carbon(reader) for _ in range(reader.read_length())]
        return cls(fields, VMStructFlags(reader.read1()))


@dataclass(slots=True)
class VMDynamicVariable:
    type: VMType
    data: Any = None

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.type)
        self.write_static(self.type, None, writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> VMDynamicVariable:
        vm_type = VMType(reader.read1())
        value = cls(vm_type)
        value.read_static(vm_type, None, reader)
        return value

    def write_static(self, vm_type: VMType, schema: VMStructSchema | None, writer: CarbonWriter) -> bool:
        value = self.data if self.type == vm_type else _default_vm_value(vm_type)
        if vm_type == VMType.DYNAMIC:
            inner = value if isinstance(value, VMDynamicVariable) else VMDynamicVariable(VMType.ARRAY_DYNAMIC, [])
            inner.write_carbon(writer)
        elif vm_type == VMType.BYTES:
            writer.write_byte_array(bytes(value or b""))
        elif vm_type == VMType.STRUCT:
            struct_value = value if isinstance(value, VMDynamicStruct) else VMDynamicStruct()
            return struct_value.write_with_schema(schema, writer) if schema else _write_and_true(struct_value, writer)
        elif vm_type == VMType.INT8:
            writer.write1(int(value) & 0xFF)
        elif vm_type == VMType.INT16:
            writer.write2(int(value))
        elif vm_type == VMType.INT32:
            writer.write4(int(value))
        elif vm_type == VMType.INT64:
            writer.write8(int(value))
        elif vm_type == VMType.INT256:
            writer.write_big_int(int(value or 0))
        elif vm_type == VMType.BYTES16:
            writer.write16(value if isinstance(value, Bytes16) else Bytes16(value or b""))
        elif vm_type == VMType.BYTES32:
            writer.write32(value if isinstance(value, Bytes32) else Bytes32(value or b""))
        elif vm_type == VMType.BYTES64:
            writer.write64(value if isinstance(value, Bytes64) else Bytes64(value or b""))
        elif vm_type == VMType.STRING:
            writer.write_string_z(str(value or ""))
        elif vm_type == VMType.ARRAY_DYNAMIC:
            _write_dynamic_variables(writer, list(value or []))
        elif vm_type == VMType.ARRAY_BYTES:
            writer.write_byte_arrays(list(value or []))
        elif vm_type == VMType.ARRAY_STRUCT:
            used_schema: VMStructSchema | None
            if isinstance(value, VMStructArray):
                array = value
                structs = array.structs
                used_schema = schema or array.schema
            else:
                structs = list(value or [])
                array = VMStructArray(schema or VMStructSchema(), structs)
                used_schema = schema
            writer.write4(len(structs))
            if schema is None:
                array.schema.write_carbon(writer)
                used_schema = array.schema if array.schema.fields else None
            for struct_item in structs:
                struct_value = struct_item if isinstance(struct_item, VMDynamicStruct) else VMDynamicStruct()
                if used_schema:
                    struct_value.write_with_schema(used_schema, writer)
                else:
                    struct_value.write_carbon(writer)
        elif vm_type == VMType.ARRAY_INT8:
            writer.write_int_array(list(value or []), 1, signed=True)
        elif vm_type == VMType.ARRAY_INT16:
            writer.write_int_array(list(value or []), 2, signed=True)
        elif vm_type == VMType.ARRAY_INT32:
            writer.write_int_array(list(value or []), 4, signed=True)
        elif vm_type == VMType.ARRAY_INT64:
            writer.write_int_array(list(value or []), 8, signed=True)
        elif vm_type == VMType.ARRAY_INT256:
            writer.write_big_int_array([int(v) for v in list(value or [])])
        elif vm_type == VMType.ARRAY_BYTES16:
            values16 = [item if isinstance(item, Bytes16) else Bytes16(item) for item in list(value or [])]
            writer.write4(len(values16))
            for value16 in values16:
                writer.write16(value16)
        elif vm_type == VMType.ARRAY_BYTES32:
            values32 = [item if isinstance(item, Bytes32) else Bytes32(item) for item in list(value or [])]
            writer.write4(len(values32))
            for value32 in values32:
                writer.write32(value32)
        elif vm_type == VMType.ARRAY_BYTES64:
            values64 = [item if isinstance(item, Bytes64) else Bytes64(item) for item in list(value or [])]
            writer.write4(len(values64))
            for value64 in values64:
                writer.write64(value64)
        elif vm_type == VMType.ARRAY_STRING:
            writer.write_string_z_array(list(value or []))
        else:
            raise SerializationError(f"unsupported VM dynamic type: {vm_type}")
        return True

    def read_static(self, vm_type: VMType, schema: VMStructSchema | None, reader: CarbonReader) -> None:
        if vm_type == VMType.DYNAMIC:
            self.data = VMDynamicVariable.read_carbon(reader)
        elif vm_type == VMType.BYTES:
            self.data = reader.read_byte_array()
        elif vm_type == VMType.STRUCT:
            self.data = (
                VMDynamicStruct.read_with_schema(schema, reader) if schema else VMDynamicStruct.read_carbon(reader)
            )
        elif vm_type == VMType.INT8:
            value = reader.read1()
            self.data = value - 0x100 if value >= 0x80 else value
        elif vm_type == VMType.INT16:
            self.data = reader.read2()
        elif vm_type == VMType.INT32:
            self.data = reader.read4()
        elif vm_type == VMType.INT64:
            self.data = reader.read8()
        elif vm_type == VMType.INT256:
            self.data = reader.read_big_int()
        elif vm_type == VMType.BYTES16:
            self.data = reader.read16()
        elif vm_type == VMType.BYTES32:
            self.data = reader.read32()
        elif vm_type == VMType.BYTES64:
            self.data = reader.read64()
        elif vm_type == VMType.STRING:
            self.data = reader.read_string_z()
        elif vm_type == VMType.ARRAY_DYNAMIC:
            self.data = _read_dynamic_variables(reader)
        elif vm_type == VMType.ARRAY_BYTES:
            self.data = reader.read_byte_arrays()
        elif vm_type == VMType.ARRAY_STRUCT:
            count = reader.read_length()
            used_schema = schema
            array_schema = schema if schema is not None else VMStructSchema.read_carbon(reader)
            if used_schema is None and array_schema.fields:
                used_schema = array_schema
            structs = [
                VMDynamicStruct.read_with_schema(used_schema, reader)
                if used_schema
                else VMDynamicStruct.read_carbon(reader)
                for _ in range(count)
            ]
            self.data = VMStructArray(array_schema, structs)
        elif vm_type == VMType.ARRAY_INT8:
            self.data = reader.read_int_array(1, signed=True)
        elif vm_type == VMType.ARRAY_INT16:
            self.data = reader.read_int_array(2, signed=True)
        elif vm_type == VMType.ARRAY_INT32:
            self.data = reader.read_int_array(4, signed=True)
        elif vm_type == VMType.ARRAY_INT64:
            self.data = reader.read_int_array(8, signed=True)
        elif vm_type == VMType.ARRAY_INT256:
            self.data = reader.read_big_int_array()
        elif vm_type == VMType.ARRAY_BYTES16:
            self.data = [reader.read16() for _ in range(reader.read_length())]
        elif vm_type == VMType.ARRAY_BYTES32:
            self.data = [reader.read32() for _ in range(reader.read_length())]
        elif vm_type == VMType.ARRAY_BYTES64:
            self.data = [reader.read64() for _ in range(reader.read_length())]
        elif vm_type == VMType.ARRAY_STRING:
            self.data = reader.read_string_z_array()
        else:
            raise SerializationError(f"unsupported VM dynamic type: {vm_type}")


@dataclass(slots=True)
class VMNamedDynamicVariable:
    name: SmallString
    value: VMDynamicVariable

    @classmethod
    def make(cls, name: str, vm_type: VMType, value: Any) -> VMNamedDynamicVariable:
        return cls(SmallString(name), VMDynamicVariable(vm_type, value))

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.name.write_carbon(writer)
        self.value.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> VMNamedDynamicVariable:
        return cls(SmallString.read_carbon(reader), VMDynamicVariable.read_carbon(reader))


@dataclass(slots=True)
class VMDynamicStruct:
    fields: list[VMNamedDynamicVariable] = field(default_factory=list)

    def _sort(self) -> None:
        self.fields.sort(key=lambda field: field.name.value)

    def get(self, name: str) -> VMDynamicVariable | None:
        for field_value in self.fields:
            if field_value.name.value == name:
                return field_value.value
        return None

    def write_carbon(self, writer: CarbonWriter) -> None:
        self._sort()
        _write_named_dynamic_variables(writer, self.fields)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> VMDynamicStruct:
        out = cls(_read_named_dynamic_variables(reader))
        out._sort()
        return out

    def write_with_schema(self, schema: VMStructSchema | None, writer: CarbonWriter) -> bool:
        if schema is None:
            self.write_carbon(writer)
            return True
        ok = True
        fields_found = 0
        for schema_field in schema.fields:
            field_value = self.get(schema_field.name.value)
            if field_value is None:
                field_value = VMDynamicVariable(schema_field.schema.type, _default_vm_value(schema_field.schema.type))
            else:
                fields_found += 1
            ok = field_value.write_static(schema_field.schema.type, schema_field.schema.struct_def, writer) and ok

        if not schema.flags & VMStructFlags.DYNAMIC_EXTRAS:
            return ok

        if fields_found == len(schema.fields) and len(self.fields) == len(schema.fields):
            writer.write4u(0)
            return ok

        extras = [item for item in self.fields if not _schema_has_field(schema, item.name.value)]
        _write_named_dynamic_variables(writer, extras)
        return ok

    @classmethod
    def read_with_schema(cls, schema: VMStructSchema | None, reader: CarbonReader) -> VMDynamicStruct:
        if schema is None:
            return cls.read_carbon(reader)
        fields: list[VMNamedDynamicVariable] = []
        for schema_field in schema.fields:
            value = VMDynamicVariable(schema_field.schema.type)
            value.read_static(schema_field.schema.type, schema_field.schema.struct_def, reader)
            fields.append(VMNamedDynamicVariable(schema_field.name, value))
        if schema.flags & VMStructFlags.DYNAMIC_EXTRAS:
            fields.extend(_read_named_dynamic_variables(reader))
        out = cls(fields)
        out._sort()
        return out


@dataclass(slots=True)
class VMStructArray:
    schema: VMStructSchema = field(default_factory=VMStructSchema)
    structs: list[VMDynamicStruct] = field(default_factory=list)


@dataclass(slots=True)
class TokenSchemas:
    series_metadata: VMStructSchema = field(default_factory=VMStructSchema)
    rom: VMStructSchema = field(default_factory=VMStructSchema)
    ram: VMStructSchema = field(default_factory=VMStructSchema)

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.series_metadata.write_carbon(writer)
        self.rom.write_carbon(writer)
        self.ram.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TokenSchemas:
        return cls(
            VMStructSchema.read_carbon(reader), VMStructSchema.read_carbon(reader), VMStructSchema.read_carbon(reader)
        )


@dataclass(frozen=True, slots=True)
class TokenSchemaField:
    """Public JSON field declaration used by token schema builders."""

    name: str
    type: VMType


@dataclass(frozen=True, slots=True)
class TokenSchemasJSON:
    """Parsed public JSON token-schema shape shared with the other SDKs."""

    series_metadata: list[TokenSchemaField]
    rom: list[TokenSchemaField]
    ram: list[TokenSchemaField]


SchemaFieldInput = TokenSchemaField | tuple[str, VMType | str] | Mapping[str, object]


@dataclass(slots=True)
class ChainConfig:
    version: int = 0
    reserved1: int = 0
    reserved2: int = 0
    reserved3: int = 0
    allowed_tx_types: int = 0
    expiry_window: int = 0
    block_rate_target: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.version)
        writer.write1(self.reserved1)
        writer.write1(self.reserved2)
        writer.write1(self.reserved3)
        writer.write4u(self.allowed_tx_types)
        writer.write4u(self.expiry_window)
        writer.write4u(self.block_rate_target)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> ChainConfig:
        return cls(
            reader.read1(),
            reader.read1(),
            reader.read1(),
            reader.read1(),
            reader.read4u(),
            reader.read4u(),
            reader.read4u(),
        )


@dataclass(slots=True)
class GasConfig:
    version: int = 0
    max_name_length: int = 0
    max_token_symbol_length: int = 0
    fee_shift: int = 0
    max_structure_size: int = 0
    fee_multiplier: int = 0
    gas_token_id: int = 0
    data_token_id: int = 0
    minimum_gas_offer: int = 0
    data_escrow_per_row: int = 0
    gas_fee_transfer: int = 0
    gas_fee_query: int = 0
    gas_fee_create_token_base: int = 0
    gas_fee_create_token_symbol: int = 0
    gas_fee_create_token_series: int = 0
    gas_fee_per_byte: int = 0
    gas_fee_register_name: int = 0
    gas_burn_ratio_mul: int = 0
    gas_burn_ratio_shift: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.version)
        writer.write1(self.max_name_length)
        writer.write1(self.max_token_symbol_length)
        writer.write1(self.fee_shift)
        writer.write4u(self.max_structure_size)
        writer.write8u(self.fee_multiplier)
        writer.write8u(self.gas_token_id)
        writer.write8u(self.data_token_id)
        writer.write8u(self.minimum_gas_offer)
        writer.write8u(self.data_escrow_per_row)
        writer.write8u(self.gas_fee_transfer)
        writer.write8u(self.gas_fee_query)
        writer.write8u(self.gas_fee_create_token_base)
        writer.write8u(self.gas_fee_create_token_symbol)
        writer.write8u(self.gas_fee_create_token_series)
        writer.write8u(self.gas_fee_per_byte)
        writer.write8u(self.gas_fee_register_name)
        writer.write8u(self.gas_burn_ratio_mul)
        writer.write1(self.gas_burn_ratio_shift)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> GasConfig:
        return cls(
            reader.read1(),
            reader.read1(),
            reader.read1(),
            reader.read1(),
            reader.read4u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            reader.read1(),
        )


@dataclass(slots=True)
class TokensConfig:
    flags: TokensConfigFlags = TokensConfigFlags.NONE

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.flags)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TokensConfig:
        return cls(TokensConfigFlags(reader.read1()))


@dataclass(slots=True)
class TokenInfo:
    max_supply: IntX
    flags: TokenFlags
    decimals: int
    owner: Bytes32
    symbol: SmallString
    metadata: bytes
    token_schemas: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.max_supply.write_carbon(writer)
        writer.write1(self.flags)
        writer.write1(self.decimals)
        writer.write32(self.owner)
        self.symbol.write_carbon(writer)
        writer.write_byte_array(self.metadata)
        if self.flags & TokenFlags.NON_FUNGIBLE:
            writer.write_byte_array(self.token_schemas)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TokenInfo:
        max_supply = IntX.read_carbon(reader)
        flags = TokenFlags(reader.read1())
        decimals = reader.read1()
        owner = reader.read32()
        symbol = SmallString.read_carbon(reader)
        metadata = reader.read_byte_array()
        token_schemas = reader.read_byte_array() if flags & TokenFlags.NON_FUNGIBLE else b""
        return cls(max_supply, flags, decimals, owner, symbol, metadata, token_schemas)


@dataclass(slots=True)
class SeriesInfo:
    max_mint: int
    max_supply: int
    owner: Bytes32
    metadata: bytes
    rom: VMStructSchema = field(default_factory=VMStructSchema)
    ram: VMStructSchema = field(default_factory=VMStructSchema)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write4u(self.max_mint)
        writer.write4u(self.max_supply)
        writer.write32(self.owner)
        writer.write_byte_array(self.metadata)
        self.rom.write_carbon(writer)
        self.ram.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> SeriesInfo:
        return cls(
            reader.read4u(),
            reader.read4u(),
            reader.read32(),
            reader.read_byte_array(),
            VMStructSchema.read_carbon(reader),
            VMStructSchema.read_carbon(reader),
        )


@dataclass(slots=True)
class NFTMintInfo:
    series_id: int = 0
    rom: bytes = b""
    ram: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write4u(self.series_id)
        writer.write_byte_array(self.rom)
        writer.write_byte_array(self.ram)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> NFTMintInfo:
        return cls(reader.read4u(), reader.read_byte_array(), reader.read_byte_array())


@dataclass(slots=True)
class MintNonFungibleArgs:
    token_id: int = 0
    address: Bytes32 = EMPTY_BYTES32
    tokens: list[NFTMintInfo] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.address)
        _write_carbon_array(writer, self.tokens)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MintNonFungibleArgs:
        return cls(reader.read8u(), reader.read32(), _read_carbon_array(reader, NFTMintInfo))


@dataclass(slots=True)
class CreateTokenSeriesArgs:
    token_id: int = 0
    info: SeriesInfo = field(default_factory=lambda: SeriesInfo(0, 0, EMPTY_BYTES32, b""))

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        self.info.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> CreateTokenSeriesArgs:
        return cls(reader.read8u(), SeriesInfo.read_carbon(reader))


@dataclass(slots=True)
class CreateMintedTokenSeriesArgs:
    token_id: int = 0
    info: SeriesInfo = field(default_factory=lambda: SeriesInfo(0, 0, EMPTY_BYTES32, b""))
    address: Bytes32 = EMPTY_BYTES32
    roms: list[bytes] = field(default_factory=list)
    rams: list[bytes] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        self.info.write_carbon(writer)
        writer.write32(self.address)
        writer.write_byte_arrays(self.roms)
        writer.write_byte_arrays(self.rams)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> CreateMintedTokenSeriesArgs:
        return cls(
            reader.read8u(),
            SeriesInfo.read_carbon(reader),
            reader.read32(),
            reader.read_byte_arrays(),
            reader.read_byte_arrays(),
        )


@dataclass(slots=True)
class PhantasmaNFTMintInfo:
    phantasma_series_id: IntX = field(default_factory=IntX)
    rom: bytes = b""
    ram: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.phantasma_series_id.write_carbon(writer)
        writer.write_byte_array(self.rom)
        writer.write_byte_array(self.ram)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> PhantasmaNFTMintInfo:
        return cls(IntX.read_carbon(reader), reader.read_byte_array(), reader.read_byte_array())


@dataclass(slots=True)
class MintPhantasmaNonFungibleArgs:
    token_id: int = 0
    address: Bytes32 = EMPTY_BYTES32
    tokens: list[PhantasmaNFTMintInfo] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.address)
        _write_carbon_array(writer, self.tokens)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MintPhantasmaNonFungibleArgs:
        return cls(reader.read8u(), reader.read32(), _read_carbon_array(reader, PhantasmaNFTMintInfo))


@dataclass(slots=True)
class PhantasmaNFTMintResult:
    phantasma_nft_id: Bytes32 = EMPTY_BYTES32
    carbon_instance_id: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.phantasma_nft_id)
        writer.write8u(self.carbon_instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> PhantasmaNFTMintResult:
        return cls(reader.read32(), reader.read8u())


@dataclass(slots=True)
class MintFungibleArgs:
    token_id: int = 0
    to: Bytes32 = EMPTY_BYTES32
    amount: IntX = field(default_factory=IntX)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.to)
        self.amount.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MintFungibleArgs:
        return cls(reader.read8u(), reader.read32(), IntX.read_carbon(reader))


@dataclass(slots=True)
class TransferFungibleArgs:
    to: Bytes32 = EMPTY_BYTES32
    from_address: Bytes32 = EMPTY_BYTES32
    token_id: int = 0
    amount: IntX = field(default_factory=IntX)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        self.amount.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TransferFungibleArgs:
        return cls(reader.read32(), reader.read32(), reader.read8u(), IntX.read_carbon(reader))


@dataclass(slots=True)
class TransferNonFungibleArgs:
    to: Bytes32 = EMPTY_BYTES32
    from_address: Bytes32 = EMPTY_BYTES32
    token_id: int = 0
    instance_ids: list[int] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        writer.write_int_array(self.instance_ids, 8, signed=False)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TransferNonFungibleArgs:
        return cls(reader.read32(), reader.read32(), reader.read8u(), reader.read_int_array(8, signed=False))


@dataclass(slots=True)
class BurnFungibleArgs:
    token_id: int = 0
    from_address: Bytes32 = EMPTY_BYTES32
    amount: IntX = field(default_factory=IntX)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.from_address)
        self.amount.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> BurnFungibleArgs:
        return cls(reader.read8u(), reader.read32(), IntX.read_carbon(reader))


@dataclass(slots=True)
class BurnNonFungibleArgs:
    token_id: int = 0
    from_address: Bytes32 = EMPTY_BYTES32
    instance_ids: list[int] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.from_address)
        writer.write_int_array(self.instance_ids, 8, signed=False)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> BurnNonFungibleArgs:
        return cls(reader.read8u(), reader.read32(), reader.read_int_array(8, signed=False))


@dataclass(slots=True)
class UpdateTokenMetadataArgs:
    token_id: int = 0
    metadata: VMDynamicStruct = field(default_factory=VMDynamicStruct)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        self.metadata.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> UpdateTokenMetadataArgs:
        return cls(reader.read8u(), VMDynamicStruct.read_carbon(reader))


@dataclass(slots=True)
class UpdateSeriesMetadataArgs:
    token_id: int = 0
    series_id: int = 0
    metadata: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write4u(self.series_id)
        writer.write_byte_array(self.metadata)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> UpdateSeriesMetadataArgs:
        return cls(reader.read8u(), reader.read4u(), reader.read_byte_array())


@dataclass(slots=True)
class TokenListing:
    type: ListingType = ListingType.FIXED_PRICE
    seller: Bytes32 = EMPTY_BYTES32
    quote_token_id: int = 0
    price: IntX = field(default_factory=IntX)
    start_date: int = 0
    end_date: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.type)
        writer.write32(self.seller)
        writer.write8u(self.quote_token_id)
        self.price.write_carbon(writer)
        writer.write8(self.start_date)
        writer.write8(self.end_date)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TokenListing:
        return cls(
            ListingType(reader.read1()),
            reader.read32(),
            reader.read8u(),
            IntX.read_carbon(reader),
            reader.read8(),
            reader.read8(),
        )


@dataclass(slots=True)
class MarketConfig:
    minimum_listing_time: int = MARKET_MINIMUM_LISTING_TIME_MS
    maximum_listing_time: int = MARKET_MAXIMUM_LISTING_TIME_MS
    delisting_grace: int = MARKET_DELISTING_GRACE_MS
    flags: MarketConfigFlags = MarketConfigFlags.PRICE_REQUIRED | MarketConfigFlags.ENFORCE_ROYALTIES

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.minimum_listing_time)
        writer.write8u(self.maximum_listing_time)
        writer.write8u(self.delisting_grace)
        writer.write4u(self.flags)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketConfig:
        return cls(reader.read8u(), reader.read8u(), reader.read8u(), MarketConfigFlags(reader.read4u()))


def default_market_config() -> MarketConfig:
    return MarketConfig()


@dataclass(slots=True)
class MarketSellTokenArgs:
    from_address: Bytes32 = EMPTY_BYTES32
    token_id: int = 0
    instance_id: int = 0
    quote_token_id: int = 0
    price: IntX = field(default_factory=IntX)
    end_date: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)
        writer.write8u(self.quote_token_id)
        self.price.write_carbon(writer)
        writer.write8(self.end_date)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketSellTokenArgs:
        return cls(
            reader.read32(),
            reader.read8u(),
            reader.read8u(),
            reader.read8u(),
            IntX.read_carbon(reader),
            reader.read8(),
        )


@dataclass(slots=True)
class MarketSellTokenByIDArgs:
    from_address: Bytes32 = EMPTY_BYTES32
    symbol: SmallString = field(default_factory=SmallString)
    instance_id: VMDynamicVariable = field(default_factory=lambda: VMDynamicVariable(VMType.INT64, 0))
    quote_symbol: SmallString = field(default_factory=SmallString)
    price: IntX = field(default_factory=IntX)
    end_date: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.from_address)
        self.symbol.write_carbon(writer)
        self.instance_id.write_carbon(writer)
        self.quote_symbol.write_carbon(writer)
        self.price.write_carbon(writer)
        writer.write8(self.end_date)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketSellTokenByIDArgs:
        return cls(
            reader.read32(),
            SmallString.read_carbon(reader),
            VMDynamicVariable.read_carbon(reader),
            SmallString.read_carbon(reader),
            IntX.read_carbon(reader),
            reader.read8(),
        )


@dataclass(slots=True)
class MarketCancelSaleArgs:
    token_id: int = 0
    instance_id: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketCancelSaleArgs:
        return cls(reader.read8u(), reader.read8u())


@dataclass(slots=True)
class MarketCancelSaleByIDArgs:
    symbol: SmallString = field(default_factory=SmallString)
    instance_id: VMDynamicVariable = field(default_factory=lambda: VMDynamicVariable(VMType.INT64, 0))

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.symbol.write_carbon(writer)
        self.instance_id.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketCancelSaleByIDArgs:
        return cls(SmallString.read_carbon(reader), VMDynamicVariable.read_carbon(reader))


@dataclass(slots=True)
class MarketBuyTokenArgs:
    from_address: Bytes32 = EMPTY_BYTES32
    token_id: int = 0
    instance_id: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketBuyTokenArgs:
        return cls(reader.read32(), reader.read8u(), reader.read8u())


@dataclass(slots=True)
class MarketBuyTokenByIDArgs:
    from_address: Bytes32 = EMPTY_BYTES32
    symbol: SmallString = field(default_factory=SmallString)
    instance_id: VMDynamicVariable = field(default_factory=lambda: VMDynamicVariable(VMType.INT64, 0))

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.from_address)
        self.symbol.write_carbon(writer)
        self.instance_id.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketBuyTokenByIDArgs:
        return cls(reader.read32(), SmallString.read_carbon(reader), VMDynamicVariable.read_carbon(reader))


@dataclass(slots=True)
class MarketGetTokenListingCountArgs:
    token_id: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketGetTokenListingCountArgs:
        return cls(reader.read8u())


@dataclass(slots=True)
class MarketGetTokenListingInfoArgs:
    token_id: int = 0
    instance_id: int = 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketGetTokenListingInfoArgs:
        return cls(reader.read8u(), reader.read8u())


@dataclass(slots=True)
class MarketGetTokenListingInfoByIDArgs:
    symbol: SmallString = field(default_factory=SmallString)
    instance_id: VMDynamicVariable = field(default_factory=lambda: VMDynamicVariable(VMType.INT64, 0))

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.symbol.write_carbon(writer)
        self.instance_id.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> MarketGetTokenListingInfoByIDArgs:
        return cls(SmallString.read_carbon(reader), VMDynamicVariable.read_carbon(reader))


@dataclass(slots=True)
class TxMsgCall:
    module_id: int
    method_id: int
    args: bytes = b""
    sections: MsgCallArgSections | None = None

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write4u(self.module_id)
        writer.write4u(self.method_id)
        if self.sections is not None and self.sections.has_sections:
            self.sections.write_carbon(writer)
            return
        writer.write4(len(self.args))
        writer.write(self.args)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgCall:
        module_id = reader.read4u()
        method_id = reader.read4u()
        length = reader.read4()
        if length >= 0:
            return cls(module_id, method_id, reader.read(length))
        return cls(module_id, method_id, sections=MsgCallArgSections.read_with_count(reader, length))


@dataclass(slots=True)
class CallArgSection:
    register_offset: int = 0
    args: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        if self.register_offset < 0:
            writer.write4(self.register_offset)
            return
        writer.write4(len(self.args))
        writer.write(self.args)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> CallArgSection:
        value = reader.read4()
        if value < 0:
            return cls(register_offset=value)
        return cls(args=reader.read(value))


@dataclass(slots=True)
class MsgCallArgSections:
    sections: list[CallArgSection] = field(default_factory=list)

    @property
    def has_sections(self) -> bool:
        return len(self.sections) > 0

    def write_carbon(self, writer: CarbonWriter) -> None:
        if not self.sections:
            raise SerializationError("arg sections are empty")
        writer.write4(-len(self.sections))
        for section in self.sections:
            section.write_carbon(writer)

    @classmethod
    def read_with_count(cls, reader: CarbonReader, count_negative: int) -> MsgCallArgSections:
        if count_negative >= 0:
            raise SerializationError("arg sections count must be negative")
        return cls([CallArgSection.read_carbon(reader) for _ in range(-count_negative)])


@dataclass(slots=True)
class TxMsgCallMulti:
    calls: list[TxMsgCall] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write4(len(self.calls))
        for call in self.calls:
            call.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgCallMulti:
        return cls([TxMsgCall.read_carbon(reader) for _ in range(reader.read_length())])


@dataclass(slots=True)
class TxMsgSpecialResolution:
    resolution_id: int = 0
    calls: list[TxMsgCall] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.resolution_id)
        _write_carbon_array(writer, self.calls)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgSpecialResolution:
        return cls(reader.read8u(), _read_carbon_array(reader, TxMsgCall))


@dataclass(slots=True)
class TxMsgTransferFungible:
    to: Bytes32
    token_id: int
    amount: int

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write8u(self.token_id)
        writer.write8u(self.amount)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTransferFungible:
        return cls(reader.read32(), reader.read8u(), reader.read8u())


@dataclass(slots=True)
class TxMsgTransferFungibleGasPayer:
    to: Bytes32
    from_address: Bytes32
    token_id: int
    amount: int

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        writer.write8u(self.amount)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTransferFungibleGasPayer:
        return cls(reader.read32(), reader.read32(), reader.read8u(), reader.read8u())


@dataclass(slots=True)
class TxMsgTransferNonFungibleSingle:
    to: Bytes32
    token_id: int
    instance_id: int

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTransferNonFungibleSingle:
        return cls(reader.read32(), reader.read8u(), reader.read8u())


@dataclass(slots=True)
class TxMsgTransferNonFungibleSingleGasPayer:
    to: Bytes32
    from_address: Bytes32
    token_id: int
    instance_id: int

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTransferNonFungibleSingleGasPayer:
        return cls(reader.read32(), reader.read32(), reader.read8u(), reader.read8u())


@dataclass(slots=True)
class TxMsgTransferNonFungibleMulti:
    to: Bytes32
    token_id: int
    instance_ids: list[int] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write8u(self.token_id)
        writer.write_int_array(self.instance_ids, 8, signed=False)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTransferNonFungibleMulti:
        return cls(reader.read32(), reader.read8u(), reader.read_int_array(8, signed=False))


@dataclass(slots=True)
class TxMsgTransferNonFungibleMultiGasPayer:
    to: Bytes32
    from_address: Bytes32
    token_id: int
    instance_ids: list[int] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.to)
        writer.write32(self.from_address)
        writer.write8u(self.token_id)
        writer.write_int_array(self.instance_ids, 8, signed=False)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTransferNonFungibleMultiGasPayer:
        return cls(reader.read32(), reader.read32(), reader.read8u(), reader.read_int_array(8, signed=False))


@dataclass(slots=True)
class TxMsgMintFungible:
    token_id: int
    to: Bytes32
    amount: IntX

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.to)
        self.amount.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgMintFungible:
        return cls(reader.read8u(), reader.read32(), IntX.read_carbon(reader))


@dataclass(slots=True)
class TxMsgBurnFungible:
    token_id: int
    amount: IntX

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        self.amount.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgBurnFungible:
        return cls(reader.read8u(), IntX.read_carbon(reader))


@dataclass(slots=True)
class TxMsgBurnFungibleGasPayer:
    token_id: int
    from_address: Bytes32
    amount: IntX

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.from_address)
        self.amount.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgBurnFungibleGasPayer:
        return cls(reader.read8u(), reader.read32(), IntX.read_carbon(reader))


@dataclass(slots=True)
class TxMsgMintNonFungible:
    token_id: int
    to: Bytes32
    series_id: int
    rom: bytes
    ram: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.to)
        writer.write4u(self.series_id)
        writer.write_byte_array(self.rom)
        writer.write_byte_array(self.ram)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgMintNonFungible:
        return cls(
            reader.read8u(), reader.read32(), reader.read4u(), reader.read_byte_array(), reader.read_byte_array()
        )


@dataclass(slots=True)
class TxMsgBurnNonFungible:
    token_id: int
    instance_id: int

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgBurnNonFungible:
        return cls(reader.read8u(), reader.read8u())


@dataclass(slots=True)
class TxMsgBurnNonFungibleGasPayer:
    token_id: int
    from_address: Bytes32
    instance_id: int

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write8u(self.token_id)
        writer.write32(self.from_address)
        writer.write8u(self.instance_id)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgBurnNonFungibleGasPayer:
        return cls(reader.read8u(), reader.read32(), reader.read8u())


@dataclass(slots=True)
class TxMsgTrade:
    transfer_f: list[TxMsgTransferFungibleGasPayer] = field(default_factory=list)
    transfer_n: list[TxMsgTransferNonFungibleSingleGasPayer] = field(default_factory=list)
    mint_f: list[TxMsgMintFungible] = field(default_factory=list)
    burn_f: list[TxMsgBurnFungibleGasPayer] = field(default_factory=list)
    mint_n: list[TxMsgMintNonFungible] = field(default_factory=list)
    burn_n: list[TxMsgBurnNonFungibleGasPayer] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        _write_carbon_array(writer, self.transfer_f)
        _write_carbon_array(writer, self.transfer_n)
        _write_carbon_array(writer, self.mint_f)
        _write_carbon_array(writer, self.burn_f)
        _write_carbon_array(writer, self.mint_n)
        _write_carbon_array(writer, self.burn_n)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgTrade:
        return cls(
            _read_carbon_array(reader, TxMsgTransferFungibleGasPayer),
            _read_carbon_array(reader, TxMsgTransferNonFungibleSingleGasPayer),
            _read_carbon_array(reader, TxMsgMintFungible),
            _read_carbon_array(reader, TxMsgBurnFungibleGasPayer),
            _read_carbon_array(reader, TxMsgMintNonFungible),
            _read_carbon_array(reader, TxMsgBurnNonFungibleGasPayer),
        )


@dataclass(slots=True)
class TxMsgPhantasma:
    nexus: SmallString
    chain: SmallString
    script: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.nexus.write_carbon(writer)
        self.chain.write_carbon(writer)
        writer.write_byte_array(self.script)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgPhantasma:
        return cls(SmallString.read_carbon(reader), SmallString.read_carbon(reader), reader.read_byte_array())


@dataclass(slots=True)
class TxMsgPhantasmaRaw:
    transaction: bytes = b""

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write_byte_array(self.transaction)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsgPhantasmaRaw:
        return cls(reader.read_byte_array())


TxPayload = (
    TxMsgCall
    | TxMsgCallMulti
    | TxMsgTrade
    | TxMsgTransferFungible
    | TxMsgTransferFungibleGasPayer
    | TxMsgTransferNonFungibleSingle
    | TxMsgTransferNonFungibleSingleGasPayer
    | TxMsgTransferNonFungibleMulti
    | TxMsgTransferNonFungibleMultiGasPayer
    | TxMsgMintFungible
    | TxMsgBurnFungible
    | TxMsgBurnFungibleGasPayer
    | TxMsgMintNonFungible
    | TxMsgBurnNonFungible
    | TxMsgBurnNonFungibleGasPayer
    | TxMsgPhantasma
    | TxMsgPhantasmaRaw
)


@dataclass(slots=True)
class TxMsg:
    type: TxType
    expiry: int
    max_gas: int
    max_data: int
    gas_from: Bytes32
    payload: SmallString
    msg: TxPayload

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write1(self.type)
        writer.write8(self.expiry)
        writer.write8u(self.max_gas)
        writer.write8u(self.max_data)
        writer.write32(self.gas_from)
        self.payload.write_carbon(writer)
        self.msg.write_carbon(writer)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> TxMsg:
        tx_type = TxType(reader.read1())
        expiry = reader.read8()
        max_gas = reader.read8u()
        max_data = reader.read8u()
        gas_from = reader.read32()
        payload = SmallString.read_carbon(reader)
        return cls(tx_type, expiry, max_gas, max_data, gas_from, payload, _read_payload(tx_type, reader))


@dataclass(slots=True)
class Witness:
    address: Bytes32
    signature: Bytes64

    def write_carbon(self, writer: CarbonWriter) -> None:
        writer.write32(self.address)
        writer.write64(self.signature)

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> Witness:
        return cls(reader.read32(), reader.read64())


@dataclass(slots=True)
class SignedTxMsg:
    msg: TxMsg
    witnesses: list[Witness] = field(default_factory=list)

    def write_carbon(self, writer: CarbonWriter) -> None:
        self.msg.write_carbon(writer)
        if self.msg.type in {
            TxType.TRANSFER_FUNGIBLE,
            TxType.TRANSFER_NON_FUNGIBLE_SINGLE,
            TxType.TRANSFER_NON_FUNGIBLE_MULTI,
            TxType.MINT_FUNGIBLE,
            TxType.BURN_FUNGIBLE,
            TxType.MINT_NON_FUNGIBLE,
            TxType.BURN_NON_FUNGIBLE,
        }:
            if len(self.witnesses) != 1 or self.witnesses[0].address != self.msg.gas_from:
                raise SerializationError("single-witness transaction address mismatch")
            writer.write64(self.witnesses[0].signature)
            return
        if self.msg.type in {
            TxType.TRANSFER_FUNGIBLE_GAS_PAYER,
            TxType.TRANSFER_NON_FUNGIBLE_SINGLE_GAS_PAYER,
            TxType.TRANSFER_NON_FUNGIBLE_MULTI_GAS_PAYER,
            TxType.BURN_FUNGIBLE_GAS_PAYER,
            TxType.BURN_NON_FUNGIBLE_GAS_PAYER,
        }:
            if len(self.witnesses) != 2 or self.witnesses[0].address != self.msg.gas_from:
                raise SerializationError("gas witness address mismatch")
            writer.write64(self.witnesses[0].signature)
            writer.write64(self.witnesses[1].signature)
            return
        if self.msg.type in {TxType.CALL, TxType.CALL_MULTI, TxType.TRADE, TxType.PHANTASMA}:
            writer.write4(len(self.witnesses))
            for witness in self.witnesses:
                witness.write_carbon(writer)
            return
        if self.msg.type == TxType.PHANTASMA_RAW:
            if self.witnesses:
                raise SerializationError("raw Phantasma transaction must not contain witnesses")
            return
        raise SerializationError(f"unsupported signed transaction type: {self.msg.type}")

    @classmethod
    def read_carbon(cls, reader: CarbonReader) -> SignedTxMsg:
        msg = TxMsg.read_carbon(reader)
        if msg.type in {
            TxType.TRANSFER_FUNGIBLE,
            TxType.TRANSFER_NON_FUNGIBLE_SINGLE,
            TxType.TRANSFER_NON_FUNGIBLE_MULTI,
            TxType.MINT_FUNGIBLE,
            TxType.BURN_FUNGIBLE,
            TxType.MINT_NON_FUNGIBLE,
            TxType.BURN_NON_FUNGIBLE,
        }:
            return cls(msg, [Witness(msg.gas_from, reader.read64())])
        if msg.type in {
            TxType.TRANSFER_FUNGIBLE_GAS_PAYER,
            TxType.TRANSFER_NON_FUNGIBLE_SINGLE_GAS_PAYER,
            TxType.TRANSFER_NON_FUNGIBLE_MULTI_GAS_PAYER,
            TxType.BURN_FUNGIBLE_GAS_PAYER,
            TxType.BURN_NON_FUNGIBLE_GAS_PAYER,
        }:
            return cls(
                msg,
                [Witness(msg.gas_from, reader.read64()), Witness(_payload_from_address(msg.msg), reader.read64())],
            )
        if msg.type in {TxType.CALL, TxType.CALL_MULTI, TxType.TRADE, TxType.PHANTASMA}:
            return cls(msg, [Witness.read_carbon(reader) for _ in range(reader.read_length())])
        if msg.type == TxType.PHANTASMA_RAW:
            return cls(msg, [])
        raise SerializationError(f"unsupported signed transaction type: {msg.type}")


def _write_carbon_array(writer: CarbonWriter, values: Sequence[CarbonSerializable]) -> None:
    writer.write4(len(values))
    for value in values:
        value.write_carbon(writer)


def _read_carbon_array(reader: CarbonReader, cls: type[C]) -> list[C]:
    return [cls.read_carbon(reader) for _ in range(reader.read_length())]


def _read_payload(tx_type: TxType, reader: CarbonReader) -> TxPayload:
    payload_types: dict[TxType, type[CarbonSerializable]] = {
        TxType.CALL: TxMsgCall,
        TxType.CALL_MULTI: TxMsgCallMulti,
        TxType.TRADE: TxMsgTrade,
        TxType.TRANSFER_FUNGIBLE: TxMsgTransferFungible,
        TxType.TRANSFER_FUNGIBLE_GAS_PAYER: TxMsgTransferFungibleGasPayer,
        TxType.TRANSFER_NON_FUNGIBLE_SINGLE: TxMsgTransferNonFungibleSingle,
        TxType.TRANSFER_NON_FUNGIBLE_SINGLE_GAS_PAYER: TxMsgTransferNonFungibleSingleGasPayer,
        TxType.TRANSFER_NON_FUNGIBLE_MULTI: TxMsgTransferNonFungibleMulti,
        TxType.TRANSFER_NON_FUNGIBLE_MULTI_GAS_PAYER: TxMsgTransferNonFungibleMultiGasPayer,
        TxType.MINT_FUNGIBLE: TxMsgMintFungible,
        TxType.BURN_FUNGIBLE: TxMsgBurnFungible,
        TxType.BURN_FUNGIBLE_GAS_PAYER: TxMsgBurnFungibleGasPayer,
        TxType.MINT_NON_FUNGIBLE: TxMsgMintNonFungible,
        TxType.BURN_NON_FUNGIBLE: TxMsgBurnNonFungible,
        TxType.BURN_NON_FUNGIBLE_GAS_PAYER: TxMsgBurnNonFungibleGasPayer,
        TxType.PHANTASMA: TxMsgPhantasma,
        TxType.PHANTASMA_RAW: TxMsgPhantasmaRaw,
    }
    try:
        cls = payload_types[tx_type]
    except KeyError as exc:
        raise SerializationError(f"unsupported transaction type: {tx_type}") from exc
    return cast(TxPayload, cls.read_carbon(reader))


def _payload_from_address(payload: TxPayload) -> Bytes32:
    if isinstance(
        payload,
        (
            TxMsgTransferFungibleGasPayer,
            TxMsgTransferNonFungibleSingleGasPayer,
            TxMsgTransferNonFungibleMultiGasPayer,
            TxMsgBurnFungibleGasPayer,
            TxMsgBurnNonFungibleGasPayer,
        ),
    ):
        return payload.from_address
    return EMPTY_BYTES32


def sign_tx_msg(msg: TxMsg, keys: PhantasmaKeys) -> SignedTxMsg:
    if not isinstance(keys, PhantasmaKeys):
        raise CryptoError("key pair is required")
    signature = keys.sign(serialize(msg))
    return SignedTxMsg(msg, [Witness(bytes32_from_public_key(keys.public_key), Bytes64(signature.data))])


def sign_and_serialize_tx_msg(msg: TxMsg, keys: PhantasmaKeys) -> bytes:
    return serialize(sign_tx_msg(msg, keys))


def sign_and_serialize_tx_msg_hex(msg: TxMsg, keys: PhantasmaKeys) -> str:
    return sign_and_serialize_tx_msg(msg, keys).hex()


@dataclass(slots=True)
class FeeOptions:
    gas_fee_base: int = 10_000
    fee_multiplier: int = 1_000

    def calculate_max_gas(self) -> int:
        return self.gas_fee_base * self.fee_multiplier


@dataclass(slots=True)
class CreateTokenFeeOptions(FeeOptions):
    gas_fee_base: int = 10_000
    fee_multiplier: int = 10_000
    gas_fee_create_token_base: int = 10_000_000_000
    gas_fee_create_token_symbol: int = 10_000_000_000

    def calculate_max_gas_for_symbol(self, symbol: SmallString) -> int:
        shift = max(len(symbol.value.encode("utf-8")) - 1, 0)
        symbol_part = self.gas_fee_create_token_symbol >> shift if shift < 64 else 0
        return (self.gas_fee_base + self.gas_fee_create_token_base + symbol_part) * self.fee_multiplier


@dataclass(slots=True)
class CreateSeriesFeeOptions(FeeOptions):
    gas_fee_base: int = 10_000
    fee_multiplier: int = 10_000
    gas_fee_create_series_base: int = 2_500_000_000

    def calculate_max_gas(self) -> int:
        return (self.gas_fee_base + self.gas_fee_create_series_base) * self.fee_multiplier


@dataclass(slots=True)
class MintNFTFeeOptions(FeeOptions):
    pass


def now_unix_millis() -> int:
    return int(time.time() * 1000)


def prepare_standard_token_schemas(shared_metadata: bool = False) -> TokenSchemas:
    series_fields = _clone_schema_fields(_standard_series_fields())
    metadata_fields = _clone_schema_fields(_standard_metadata_fields())
    rom_fields = _clone_schema_fields(_standard_nft_fields())
    if shared_metadata:
        series_fields += metadata_fields
    else:
        rom_fields += metadata_fields
    return TokenSchemas(
        VMStructSchema(series_fields), VMStructSchema(rom_fields), VMStructSchema(flags=VMStructFlags.DYNAMIC_EXTRAS)
    )


def serialize_token_schemas(schemas: TokenSchemas) -> bytes:
    return serialize(schemas)


def serialize_token_schemas_hex(schemas: TokenSchemas) -> str:
    return serialize_token_schemas(schemas).hex().upper()


def build_and_serialize_token_schemas(schemas: TokenSchemas | None = None) -> bytes:
    return serialize_token_schemas(schemas or prepare_standard_token_schemas(False))


def parse_token_schemas_json(data: str) -> TokenSchemasJSON:
    raw = json.loads(data)
    if not isinstance(raw, Mapping):
        raise BuilderError("token schemas JSON must be an object")
    return TokenSchemasJSON(
        _parse_token_schema_field_array(raw, "seriesMetadata"),
        _parse_token_schema_field_array(raw, "rom"),
        _parse_token_schema_field_array(raw, "ram"),
    )


def token_schemas_from_json(data: str) -> TokenSchemas:
    parsed = parse_token_schemas_json(data)
    return build_token_schemas_from_fields(parsed.series_metadata, parsed.rom, parsed.ram)


def build_token_schemas_from_fields(
    series_metadata: Sequence[SchemaFieldInput],
    rom: Sequence[SchemaFieldInput],
    ram: Sequence[SchemaFieldInput],
) -> TokenSchemas:
    series_fields = _token_schema_fields_to_schemas(
        [*_schema_to_public_fields(_standard_series_fields()), *series_metadata]
    )
    rom_fields = _token_schema_fields_to_schemas([*_schema_to_public_fields(_standard_nft_fields()), *rom])
    ram_fields = _token_schema_fields_to_schemas(ram)
    schemas = TokenSchemas(
        VMStructSchema(series_fields),
        VMStructSchema(rom_fields),
        VMStructSchema(ram_fields, VMStructFlags.DYNAMIC_EXTRAS if not ram_fields else VMStructFlags.NONE),
    )
    verify_token_schemas(schemas)
    return schemas


def vm_type_from_string(value: str) -> VMType:
    try:
        return _VM_TYPE_NAME_MAP[value.strip()]
    except KeyError as exc:
        raise BuilderError(f"unknown VM type: {value}") from exc


def vm_type_name(vm_type: VMType) -> str:
    try:
        return _VM_TYPE_CANONICAL_NAMES[vm_type]
    except KeyError as exc:
        raise BuilderError(f"unknown VM type: {int(vm_type)}") from exc


def verify_token_schemas(schemas: TokenSchemas) -> None:
    _assert_metadata_fields([schemas.series_metadata, schemas.rom], _standard_metadata_fields())
    _assert_metadata_fields([schemas.series_metadata], _standard_series_fields())
    _assert_metadata_fields([schemas.rom], _standard_nft_fields())


def build_token_metadata(fields: dict[str, str]) -> bytes:
    required = ("name", "icon", "url", "description")
    if len(fields) < len(required):
        raise BuilderError("token metadata is mandatory")
    for field_name in required:
        if not fields.get(field_name, "").strip():
            raise BuilderError(f"token metadata is missing required field: {field_name}")
    _validate_icon_data_uri(fields["icon"])
    structure = VMDynamicStruct(
        [VMNamedDynamicVariable.make(name, VMType.STRING, value) for name, value in fields.items()]
    )
    return serialize(structure)


def build_token_info(
    symbol: str,
    max_supply: IntX,
    *,
    is_nft: bool,
    decimals: int,
    owner: Bytes32,
    metadata: bytes,
    token_schemas: bytes = b"",
) -> TokenInfo:
    check_token_symbol(symbol)
    if metadata is None:
        raise BuilderError("metadata is required for all tokens")
    flags = TokenFlags.NONE
    if is_nft:
        if not max_supply.is_8_byte_safe:
            raise BuilderError("NFT maximum supply must fit into Int64")
        if not token_schemas:
            raise BuilderError("token schemas are required for NFTs")
        flags = TokenFlags.NON_FUNGIBLE
    elif not max_supply.is_8_byte_safe:
        flags = TokenFlags.BIG_FUNGIBLE
    return TokenInfo(max_supply, flags, decimals, owner, SmallString(symbol), bytes(metadata), bytes(token_schemas))


def build_series_info(phantasma_series_id: int, max_mint: int, max_supply: int, owner: Bytes32) -> SeriesInfo:
    phantasma_series_id = _require_required_int("phantasma_series_id", phantasma_series_id)
    schemas = prepare_standard_token_schemas(False)
    metadata = build_token_series_metadata(schemas.series_metadata, phantasma_series_id, [])
    return SeriesInfo(max_mint, max_supply, owner, metadata)


def build_token_series_metadata(
    schema: VMStructSchema, phantasma_series_id: int, metadata: list[tuple[str, Any]]
) -> bytes:
    phantasma_series_id = _require_required_int("phantasma_series_id", phantasma_series_id)
    rom = _metadata_bytes(metadata, "rom")
    fields = [
        VMNamedDynamicVariable.make(STANDARD_META_ID, VMType.INT256, phantasma_series_id),
        VMNamedDynamicVariable.make("mode", VMType.INT8, 1 if rom else 0),
        VMNamedDynamicVariable.make("rom", VMType.BYTES, rom),
    ]
    fields.extend(_metadata_dynamic_fields_for_schema(schema, _standard_series_fields(), metadata))
    return _write_dynamic_struct_with_schema(VMDynamicStruct(fields), schema)


def build_nft_rom(schema: VMStructSchema, phantasma_nft_id: int, metadata: list[tuple[str, Any]]) -> bytes:
    phantasma_nft_id = _require_required_int("phantasma_nft_id", phantasma_nft_id)
    rom = _metadata_bytes(metadata, "rom")
    fields = [
        VMNamedDynamicVariable.make(STANDARD_META_ID, VMType.INT256, phantasma_nft_id),
        VMNamedDynamicVariable.make("rom", VMType.BYTES, rom),
    ]
    fields.extend(_metadata_dynamic_fields_for_schema(schema, _standard_nft_fields(), metadata))
    return _write_dynamic_struct_with_schema(VMDynamicStruct(fields), schema)


def build_phantasma_nft_public_mint_schema(nft_rom_schema: VMStructSchema) -> VMStructSchema:
    return VMStructSchema(
        [field for field in nft_rom_schema.fields if not _is_phantasma_nft_reserved_field(field.name.value)],
        nft_rom_schema.flags,
    )


def build_phantasma_nft_rom(nft_rom_schema: VMStructSchema, metadata: list[tuple[str, Any]]) -> bytes:
    if not metadata:
        raise BuilderError("metadata is required")
    for name, _value in metadata:
        if _is_phantasma_nft_reserved_field(name):
            raise BuilderError(f'metadata field "{name}" is reserved for chain-owned deterministic mint fields')
    public_schema = build_phantasma_nft_public_mint_schema(nft_rom_schema)
    fields = _metadata_dynamic_fields_for_schema(public_schema, [], metadata)
    return _write_dynamic_struct_with_schema(VMDynamicStruct(fields), public_schema)


def build_create_token_tx(
    token_info: TokenInfo,
    creator: Bytes32,
    fees: CreateTokenFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> TxMsg:
    fees = fees or CreateTokenFeeOptions()
    return TxMsg(
        TxType.CALL,
        expiry or now_unix_millis() + 60 * 1000,
        fees.calculate_max_gas_for_symbol(token_info.symbol),
        max_data,
        creator,
        SmallString(""),
        TxMsgCall(ModuleID.TOKEN, TokenContractMethod.CREATE_TOKEN, serialize(token_info)),
    )


def build_create_token_tx_and_sign(
    token_info: TokenInfo,
    signer: PhantasmaKeys,
    fees: CreateTokenFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> bytes:
    creator = bytes32_from_public_key(signer.public_key)
    return sign_and_serialize_tx_msg(build_create_token_tx(token_info, creator, fees, max_data, expiry), signer)


def build_create_token_tx_and_sign_hex(
    token_info: TokenInfo,
    signer: PhantasmaKeys,
    fees: CreateTokenFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> str:
    return build_create_token_tx_and_sign(token_info, signer, fees, max_data, expiry).hex()


def build_create_token_series_tx(
    token_id: int,
    series_info: SeriesInfo,
    creator: Bytes32,
    fees: CreateSeriesFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> TxMsg:
    fees = fees or CreateSeriesFeeOptions()
    writer = CarbonWriter()
    writer.write8u(token_id)
    series_info.write_carbon(writer)
    return TxMsg(
        TxType.CALL,
        expiry or now_unix_millis() + 60 * 1000,
        fees.calculate_max_gas(),
        max_data,
        creator,
        SmallString(""),
        TxMsgCall(ModuleID.TOKEN, TokenContractMethod.CREATE_TOKEN_SERIES, writer.bytes()),
    )


def build_create_token_series_tx_and_sign(
    token_id: int,
    series_info: SeriesInfo,
    signer: PhantasmaKeys,
    fees: CreateSeriesFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> bytes:
    creator = bytes32_from_public_key(signer.public_key)
    return sign_and_serialize_tx_msg(
        build_create_token_series_tx(token_id, series_info, creator, fees, max_data, expiry), signer
    )


def build_create_token_series_tx_and_sign_hex(
    token_id: int,
    series_info: SeriesInfo,
    signer: PhantasmaKeys,
    fees: CreateSeriesFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> str:
    return build_create_token_series_tx_and_sign(token_id, series_info, signer, fees, max_data, expiry).hex()


def build_mint_non_fungible_tx(
    token_id: int,
    series_id: int,
    sender: Bytes32,
    receiver: Bytes32,
    rom: bytes,
    ram: bytes = b"",
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> TxMsg:
    fees = fees or MintNFTFeeOptions()
    return TxMsg(
        TxType.MINT_NON_FUNGIBLE,
        expiry or now_unix_millis() + 60 * 1000,
        fees.calculate_max_gas(),
        max_data,
        sender,
        SmallString(""),
        TxMsgMintNonFungible(token_id, receiver, series_id, rom, ram),
    )


def build_mint_non_fungible_tx_and_sign(
    token_id: int,
    series_id: int,
    signer: PhantasmaKeys,
    receiver: Bytes32,
    rom: bytes,
    ram: bytes = b"",
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> bytes:
    sender = bytes32_from_public_key(signer.public_key)
    return sign_and_serialize_tx_msg(
        build_mint_non_fungible_tx(token_id, series_id, sender, receiver, rom, ram, fees, max_data, expiry), signer
    )


def build_mint_non_fungible_tx_and_sign_hex(
    token_id: int,
    series_id: int,
    signer: PhantasmaKeys,
    receiver: Bytes32,
    rom: bytes,
    ram: bytes = b"",
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> str:
    return build_mint_non_fungible_tx_and_sign(
        token_id, series_id, signer, receiver, rom, ram, fees, max_data, expiry
    ).hex()


def build_mint_phantasma_non_fungible_tx(
    token_id: int,
    sender: Bytes32,
    receiver: Bytes32,
    tokens: Sequence[PhantasmaNFTMintInfo],
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> TxMsg:
    fees = fees or MintNFTFeeOptions()
    args = MintPhantasmaNonFungibleArgs(token_id, receiver, list(tokens))
    return TxMsg(
        TxType.CALL,
        expiry or now_unix_millis() + 60 * 1000,
        fees.calculate_max_gas(),
        max_data,
        sender,
        SmallString(""),
        TxMsgCall(ModuleID.TOKEN, TokenContractMethod.MINT_PHANTASMA_NON_FUNGIBLE, serialize(args)),
    )


def build_mint_phantasma_non_fungible_tx_and_sign(
    token_id: int,
    signer: PhantasmaKeys,
    receiver: Bytes32,
    tokens: Sequence[PhantasmaNFTMintInfo],
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> bytes:
    sender = bytes32_from_public_key(signer.public_key)
    return sign_and_serialize_tx_msg(
        build_mint_phantasma_non_fungible_tx(token_id, sender, receiver, tokens, fees, max_data, expiry), signer
    )


def build_mint_phantasma_non_fungible_tx_and_sign_hex(
    token_id: int,
    signer: PhantasmaKeys,
    receiver: Bytes32,
    tokens: Sequence[PhantasmaNFTMintInfo],
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> str:
    return build_mint_phantasma_non_fungible_tx_and_sign(
        token_id, signer, receiver, tokens, fees, max_data, expiry
    ).hex()


def build_mint_phantasma_non_fungible_single_tx(
    token_id: int,
    phantasma_series_id: int,
    sender: Bytes32,
    receiver: Bytes32,
    public_rom: bytes,
    ram: bytes = b"",
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> TxMsg:
    phantasma_series_id = _require_required_int("phantasma_series_id", phantasma_series_id)
    return build_mint_phantasma_non_fungible_tx(
        token_id,
        sender,
        receiver,
        [PhantasmaNFTMintInfo(IntX(phantasma_series_id), public_rom, ram)],
        fees,
        max_data,
        expiry,
    )


def build_mint_phantasma_non_fungible_single_tx_and_sign(
    token_id: int,
    phantasma_series_id: int,
    signer: PhantasmaKeys,
    receiver: Bytes32,
    public_rom: bytes,
    ram: bytes = b"",
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> bytes:
    sender = bytes32_from_public_key(signer.public_key)
    return sign_and_serialize_tx_msg(
        build_mint_phantasma_non_fungible_single_tx(
            token_id, phantasma_series_id, sender, receiver, public_rom, ram, fees, max_data, expiry
        ),
        signer,
    )


def build_mint_phantasma_non_fungible_single_tx_and_sign_hex(
    token_id: int,
    phantasma_series_id: int,
    signer: PhantasmaKeys,
    receiver: Bytes32,
    public_rom: bytes,
    ram: bytes = b"",
    fees: MintNFTFeeOptions | None = None,
    max_data: int = 100_000_000,
    expiry: int = 0,
) -> str:
    return build_mint_phantasma_non_fungible_single_tx_and_sign(
        token_id, phantasma_series_id, signer, receiver, public_rom, ram, fees, max_data, expiry
    ).hex()


def get_nft_address(carbon_token_id: int, instance_id: int) -> Bytes32:
    address = bytearray(32)
    address[15] = 1
    address[16:24] = carbon_token_id.to_bytes(8, "little")
    address[24:32] = instance_id.to_bytes(8, "little")
    return Bytes32(address)


def unpack_nft_instance_id(instance_id: int) -> tuple[int, int]:
    return instance_id & 0xFFFFFFFF, (instance_id >> 32) & 0xFFFFFFFF


def parse_create_token_result(result_hex: str) -> int:
    reader = CarbonReader(decode_hex(result_hex))
    value = reader.read8u()
    reader.assert_eof()
    return value


def parse_create_token_series_result(result_hex: str) -> int:
    reader = CarbonReader(decode_hex(result_hex))
    value = reader.read4u()
    reader.assert_eof()
    return value


def parse_mint_non_fungible_result(carbon_token_id: int, result_hex: str) -> list[Bytes32]:
    reader = CarbonReader(decode_hex(result_hex))
    out = [get_nft_address(carbon_token_id, reader.read8u()) for _ in range(reader.read_length())]
    reader.assert_eof()
    return out


def parse_mint_phantasma_non_fungible_result(result_hex: str) -> list[PhantasmaNFTMintResult]:
    reader = CarbonReader(decode_hex(result_hex))
    out = [PhantasmaNFTMintResult.read_carbon(reader) for _ in range(reader.read_length())]
    reader.assert_eof()
    return out


def check_token_symbol(symbol: str) -> None:
    if not symbol:
        raise BuilderError("token symbol must not be empty")
    if len(symbol.encode("utf-8")) > 255:
        raise BuilderError("token symbol exceeds 255 UTF-8 bytes")
    if not re.fullmatch(r"[A-Z]+", symbol):
        raise BuilderError("token symbol must contain only uppercase ASCII letters A-Z")


def _parse_token_schema_field_array(raw: Mapping[str, object], key: str) -> list[TokenSchemaField]:
    items = raw.get(key)
    if not isinstance(items, list):
        raise BuilderError(f"{key} must be an array")
    out: list[TokenSchemaField] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise BuilderError(f"{key} field {index} invalid")
        name = item.get("name")
        raw_type = item.get("type")
        if not isinstance(name, str):
            raise BuilderError(f"{key} field name must be string")
        if not isinstance(raw_type, str):
            raise BuilderError(f"{key} field type must be string")
        out.append(TokenSchemaField(name, vm_type_from_string(raw_type)))
    return out


def _token_schema_fields_to_schemas(fields: Sequence[SchemaFieldInput]) -> list[VMNamedVariableSchema]:
    return [
        VMNamedVariableSchema.make(field.name, field.type)
        for field in (_coerce_token_schema_field(item) for item in fields)
    ]


def _coerce_token_schema_field(value: SchemaFieldInput) -> TokenSchemaField:
    if isinstance(value, TokenSchemaField):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        name_value = value[0]
        type_value = value[1]
        if not isinstance(name_value, str):
            raise BuilderError("field name must be string")
        if isinstance(type_value, VMType):
            return TokenSchemaField(name_value, type_value)
        if isinstance(type_value, str):
            return TokenSchemaField(name_value, vm_type_from_string(type_value))
        raise BuilderError("field type must be string")
    if isinstance(value, Mapping):
        name = value.get("name")
        raw_type = value.get("type")
        if not isinstance(name, str):
            raise BuilderError("field name must be string")
        if isinstance(raw_type, VMType):
            return TokenSchemaField(name, raw_type)
        if isinstance(raw_type, str):
            return TokenSchemaField(name, vm_type_from_string(raw_type))
        raise BuilderError("field type must be string")
    raise BuilderError("field declaration must be a TokenSchemaField, tuple, or mapping")


def _schema_to_public_fields(fields: Sequence[VMNamedVariableSchema]) -> list[TokenSchemaField]:
    return [TokenSchemaField(field.name.value, field.schema.type) for field in fields]


_VM_TYPE_NAME_MAP: dict[str, VMType] = {
    "Dynamic": VMType.DYNAMIC,
    "Array": VMType.ARRAY,
    "Bytes": VMType.BYTES,
    "Struct": VMType.STRUCT,
    "Int8": VMType.INT8,
    "Int16": VMType.INT16,
    "Int32": VMType.INT32,
    "Int64": VMType.INT64,
    "Int256": VMType.INT256,
    "Bytes16": VMType.BYTES16,
    "Bytes32": VMType.BYTES32,
    "Bytes64": VMType.BYTES64,
    "String": VMType.STRING,
    "Array_Dynamic": VMType.ARRAY_DYNAMIC,
    "Array_Bytes": VMType.ARRAY_BYTES,
    "Array_Struct": VMType.ARRAY_STRUCT,
    "Array_Int8": VMType.ARRAY_INT8,
    "Array_Int16": VMType.ARRAY_INT16,
    "Array_Int32": VMType.ARRAY_INT32,
    "Array_Int64": VMType.ARRAY_INT64,
    "Array_Int256": VMType.ARRAY_INT256,
    "Array_Bytes16": VMType.ARRAY_BYTES16,
    "Array_Bytes32": VMType.ARRAY_BYTES32,
    "Array_Bytes64": VMType.ARRAY_BYTES64,
    "Array_String": VMType.ARRAY_STRING,
    "ArrayDynamic": VMType.ARRAY_DYNAMIC,
    "ArrayBytes": VMType.ARRAY_BYTES,
    "ArrayStruct": VMType.ARRAY_STRUCT,
    "ArrayInt8": VMType.ARRAY_INT8,
    "ArrayInt16": VMType.ARRAY_INT16,
    "ArrayInt32": VMType.ARRAY_INT32,
    "ArrayInt64": VMType.ARRAY_INT64,
    "ArrayInt256": VMType.ARRAY_INT256,
    "ArrayBytes16": VMType.ARRAY_BYTES16,
    "ArrayBytes32": VMType.ARRAY_BYTES32,
    "ArrayBytes64": VMType.ARRAY_BYTES64,
    "ArrayString": VMType.ARRAY_STRING,
}

_VM_TYPE_CANONICAL_NAMES: dict[VMType, str] = {
    VMType.DYNAMIC: "Dynamic",
    VMType.ARRAY: "Array",
    VMType.BYTES: "Bytes",
    VMType.STRUCT: "Struct",
    VMType.INT8: "Int8",
    VMType.INT16: "Int16",
    VMType.INT32: "Int32",
    VMType.INT64: "Int64",
    VMType.INT256: "Int256",
    VMType.BYTES16: "Bytes16",
    VMType.BYTES32: "Bytes32",
    VMType.BYTES64: "Bytes64",
    VMType.STRING: "String",
    VMType.ARRAY_BYTES: "Array_Bytes",
    VMType.ARRAY_STRUCT: "Array_Struct",
    VMType.ARRAY_INT8: "Array_Int8",
    VMType.ARRAY_INT16: "Array_Int16",
    VMType.ARRAY_INT32: "Array_Int32",
    VMType.ARRAY_INT64: "Array_Int64",
    VMType.ARRAY_INT256: "Array_Int256",
    VMType.ARRAY_BYTES16: "Array_Bytes16",
    VMType.ARRAY_BYTES32: "Array_Bytes32",
    VMType.ARRAY_BYTES64: "Array_Bytes64",
    VMType.ARRAY_STRING: "Array_String",
}


def _metadata_bytes(metadata: list[tuple[str, Any]], name: str) -> bytes:
    _actual_name, value = _find_metadata_field(metadata, name)
    if value is _MISSING:
        return b""
    return _ensure_metadata_bytes(name, value)


def _metadata_dynamic_fields_for_schema(
    schema: VMStructSchema, defaults: Sequence[VMNamedVariableSchema], metadata: list[tuple[str, Any]]
) -> list[VMNamedDynamicVariable]:
    out: list[VMNamedDynamicVariable] = []
    for field_schema in schema.fields:
        name = field_schema.name.value
        if _has_default_field(defaults, name):
            continue
        _actual_name, value = _find_metadata_field(metadata, name)
        if value is _MISSING or value is None:
            raise BuilderError(f'metadata field "{name}" is mandatory')
        out.append(
            VMNamedDynamicVariable(
                field_schema.name,
                VMDynamicVariable(
                    field_schema.schema.type,
                    _coerce_metadata_value(name, field_schema.schema, value),
                ),
            )
        )
    return out


def _coerce_metadata_value(name: str, schema: VMVariableSchema, value: Any) -> Any:
    if value is None:
        raise BuilderError(f'metadata field "{name}" is mandatory')
    vm_type = schema.type
    if vm_type == VMType.BYTES:
        return _ensure_metadata_bytes(name, value)
    if vm_type == VMType.STRING:
        return _ensure_metadata_string(name, value)
    if vm_type in {VMType.INT8, VMType.INT16, VMType.INT32, VMType.INT64}:
        return _coerce_integer_for_vm_type(name, vm_type, value)
    if vm_type == VMType.INT256:
        return _coerce_int256(name, value)
    if vm_type == VMType.BYTES16:
        return _ensure_fixed_metadata_bytes(name, value, Bytes16)
    if vm_type == VMType.BYTES32:
        return _ensure_fixed_metadata_bytes(name, value, Bytes32)
    if vm_type == VMType.BYTES64:
        return _ensure_fixed_metadata_bytes(name, value, Bytes64)
    if vm_type == VMType.STRUCT:
        return _coerce_metadata_struct(name, schema.struct_def, value)
    if vm_type == VMType.ARRAY_STRUCT:
        return _coerce_metadata_struct_array(name, schema.struct_def, value)
    if vm_type == VMType.ARRAY_DYNAMIC:
        values = _ensure_metadata_sequence(name, value)
        if not all(isinstance(item, VMDynamicVariable) for item in values):
            raise BuilderError(f'metadata field "{name}" must contain dynamic VM variables')
        return list(values)
    if vm_type == VMType.ARRAY_BYTES:
        return [
            _ensure_metadata_bytes(f"{name}[{index}]", item)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    if vm_type == VMType.ARRAY_STRING:
        return [
            _ensure_metadata_string(f"{name}[{index}]", item)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    if vm_type in {VMType.ARRAY_INT8, VMType.ARRAY_INT16, VMType.ARRAY_INT32, VMType.ARRAY_INT64}:
        element_type = VMType(vm_type & ~VMType.ARRAY)
        return [
            _coerce_integer_for_vm_type(f"{name}[{index}]", element_type, item)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    if vm_type == VMType.ARRAY_INT256:
        return [
            _coerce_int256(f"{name}[{index}]", item)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    if vm_type == VMType.ARRAY_BYTES16:
        return [
            _ensure_fixed_metadata_bytes(f"{name}[{index}]", item, Bytes16)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    if vm_type == VMType.ARRAY_BYTES32:
        return [
            _ensure_fixed_metadata_bytes(f"{name}[{index}]", item, Bytes32)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    if vm_type == VMType.ARRAY_BYTES64:
        return [
            _ensure_fixed_metadata_bytes(f"{name}[{index}]", item, Bytes64)
            for index, item in enumerate(_ensure_metadata_sequence(name, value))
        ]
    return value


def _coerce_metadata_struct(name: str, schema: VMStructSchema | None, value: Any) -> VMDynamicStruct:
    if isinstance(value, VMDynamicStruct):
        return value
    if schema is None:
        raise BuilderError(f'metadata field "{name}" is missing struct schema')
    fields = _metadata_struct_input_to_fields(name, value)
    out = VMDynamicStruct(_metadata_dynamic_fields_for_schema(schema, [], fields))
    allowed = {field.name.value.lower() for field in schema.fields}
    for provided_name, _provided_value in fields:
        if provided_name.lower() not in allowed:
            raise BuilderError(f'metadata field "{name}" received unknown property "{provided_name}"')
    return out


def _coerce_metadata_struct_array(name: str, schema: VMStructSchema | None, value: Any) -> VMStructArray:
    if isinstance(value, VMStructArray):
        return value
    values = _ensure_metadata_sequence(name, value)
    if schema is None:
        raise BuilderError(f'metadata field "{name}" is missing a struct schema')
    structs: list[VMDynamicStruct] = []
    for index, item in enumerate(values):
        structs.append(_coerce_metadata_struct(f"{name}[{index}]", schema, item))
    return VMStructArray(schema, structs)


def _metadata_struct_input_to_fields(name: str, value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, Mapping):
        return [(_ensure_metadata_key(name, key), item_value) for key, item_value in value.items()]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        fields: list[tuple[str, Any]] = []
        for item in value:
            if isinstance(item, VMNamedDynamicVariable):
                fields.append((item.name.value, item.value.data))
                continue
            if not isinstance(item, Sequence) or isinstance(item, str | bytes | bytearray) or len(item) != 2:
                raise BuilderError(f'metadata field "{name}" must be provided as an object or array of fields')
            key, item_value = item
            fields.append((_ensure_metadata_key(name, key), item_value))
        return fields
    raise BuilderError(f'metadata field "{name}" must be provided as an object or array of fields')


def _ensure_metadata_key(parent_name: str, key: object) -> str:
    if not isinstance(key, str):
        raise BuilderError(f'metadata field "{parent_name}" must use string property names')
    return key


def _ensure_metadata_string(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise BuilderError(f'metadata field "{name}" must be a string')
    if not value.strip():
        raise BuilderError(f'metadata field "{name}" is mandatory')
    return value


def _ensure_metadata_bytes(name: str, value: Any) -> bytes:
    if isinstance(value, bytes | bytearray):
        return bytes(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise BuilderError(f'metadata field "{name}" must be a byte array or hex string')
        try:
            return _decode_flexible_hex(text)
        except BuilderError as exc:
            raise BuilderError(f'metadata field "{name}" must be a byte array or hex string') from exc
    raise BuilderError(f'metadata field "{name}" must be a byte array or hex string')


def _ensure_fixed_metadata_bytes(name: str, value: Any, cls: type[FixedBytes]) -> FixedBytes:
    if isinstance(value, cls):
        return value
    data = _ensure_metadata_bytes(name, value)
    if len(data) != cls.SIZE:
        raise BuilderError(f'metadata field "{name}" must be exactly {cls.SIZE} bytes')
    return cls(data)


def _ensure_metadata_sequence(name: str, value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return value
    raise BuilderError(f'metadata field "{name}" must be provided as an array')


def _coerce_integer_for_vm_type(name: str, vm_type: VMType, value: Any) -> int:
    bit_width = {
        VMType.INT8: 8,
        VMType.INT16: 16,
        VMType.INT32: 32,
        VMType.INT64: 64,
    }[vm_type]
    integer = _ensure_metadata_integer(name, value)
    signed_min = -(1 << (bit_width - 1))
    signed_max = (1 << (bit_width - 1)) - 1
    unsigned_max = (1 << bit_width) - 1
    if not (signed_min <= integer <= signed_max or 0 <= integer <= unsigned_max):
        raise BuilderError(
            f'metadata field "{name}" must be between {signed_min} and {signed_max} or between 0 and {unsigned_max}'
        )
    if bit_width == 8 or integer <= signed_max:
        return integer
    return integer - (1 << bit_width)


def _coerce_int256(name: str, value: Any) -> int:
    integer = _ensure_metadata_integer(name, value)
    signed_min = -(1 << 255)
    signed_max = (1 << 255) - 1
    unsigned_max = (1 << 256) - 1
    if not (signed_min <= integer <= signed_max or 0 <= integer <= unsigned_max):
        raise BuilderError(
            f'metadata field "{name}" must be between {signed_min} and {signed_max} or between 0 and {unsigned_max}'
        )
    return integer


def _ensure_metadata_integer(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BuilderError(f'metadata field "{name}" must be an integer')
    return value


def _require_required_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BuilderError(f"{name} is required")
    return value


def _find_metadata_field(metadata: list[tuple[str, Any]], name: str) -> tuple[str, Any]:
    for key, value in metadata:
        if key == name:
            return key, value
    for key, _value in metadata:
        if key.lower() == name.lower():
            raise BuilderError(f'metadata field "{name}" provided in incorrect case as "{key}"')
    return name, _MISSING


def _decode_flexible_hex(value: str) -> bytes:
    text = value.strip().removeprefix("0x").removeprefix("0X")
    if len(text) % 2:
        text = "0" + text
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise BuilderError("invalid hex byte") from exc


def _has_default_field(defaults: Sequence[VMNamedVariableSchema], name: str) -> bool:
    return any(item.name.value == name for item in defaults)


def _clone_schema_fields(fields: Sequence[VMNamedVariableSchema]) -> list[VMNamedVariableSchema]:
    return [VMNamedVariableSchema(field.name, field.schema) for field in fields]


def _standard_series_fields() -> list[VMNamedVariableSchema]:
    return [
        VMNamedVariableSchema.make(STANDARD_META_ID, VMType.INT256),
        VMNamedVariableSchema.make("mode", VMType.INT8),
        VMNamedVariableSchema.make("rom", VMType.BYTES),
    ]


def _standard_nft_fields() -> list[VMNamedVariableSchema]:
    return [
        VMNamedVariableSchema.make(STANDARD_META_ID, VMType.INT256),
        VMNamedVariableSchema.make("rom", VMType.BYTES),
    ]


def _standard_metadata_fields() -> list[VMNamedVariableSchema]:
    return [
        VMNamedVariableSchema.make("name", VMType.STRING),
        VMNamedVariableSchema.make("description", VMType.STRING),
        VMNamedVariableSchema.make("imageURL", VMType.STRING),
        VMNamedVariableSchema.make("infoURL", VMType.STRING),
        VMNamedVariableSchema.make("royalties", VMType.INT32),
    ]


def _assert_metadata_fields(schemas: Sequence[VMStructSchema], fields: Sequence[VMNamedVariableSchema]) -> None:
    for expected in fields:
        expected_name = expected.name.value
        case_mismatch = False
        for schema in schemas:
            for actual in schema.fields:
                actual_name = actual.name.value
                if actual_name == expected_name:
                    if actual.schema.type != expected.schema.type:
                        raise BuilderError(f"type mismatch for {expected_name} field")
                    case_mismatch = False
                    break
                if actual_name.lower() == expected_name.lower():
                    case_mismatch = True
            else:
                continue
            break
        else:
            if case_mismatch:
                raise BuilderError(f"case mismatch for {expected_name} field")
            raise BuilderError(f"mandatory metadata field not found: {expected_name}")


def _is_phantasma_nft_reserved_field(name: str) -> bool:
    return name.lower() in {STANDARD_META_ID.lower(), "rom"}


def _write_dynamic_struct_with_schema(structure: VMDynamicStruct, schema: VMStructSchema) -> bytes:
    writer = CarbonWriter()
    ok = structure.write_with_schema(schema, writer)
    if not ok:
        raise BuilderError("metadata does not match schema")
    return writer.bytes()


def _write_named_dynamic_variables(writer: CarbonWriter, values: list[VMNamedDynamicVariable]) -> None:
    writer.write4(len(values))
    for value in values:
        value.write_carbon(writer)


def _read_named_dynamic_variables(reader: CarbonReader) -> list[VMNamedDynamicVariable]:
    return [VMNamedDynamicVariable.read_carbon(reader) for _ in range(reader.read_length())]


def _write_dynamic_variables(writer: CarbonWriter, values: list[VMDynamicVariable]) -> None:
    writer.write4(len(values))
    for value in values:
        value.write_carbon(writer)


def _read_dynamic_variables(reader: CarbonReader) -> list[VMDynamicVariable]:
    return [VMDynamicVariable.read_carbon(reader) for _ in range(reader.read_length())]


def _write_and_true(value: CarbonSerializable, writer: CarbonWriter) -> bool:
    value.write_carbon(writer)
    return True


def _schema_has_field(schema: VMStructSchema, name: str) -> bool:
    return any(field_value.name.value == name for field_value in schema.fields)


def _default_vm_value(vm_type: VMType) -> Any:
    if vm_type == VMType.BYTES:
        return b""
    if vm_type == VMType.STRUCT:
        return VMDynamicStruct()
    if vm_type in {VMType.INT8, VMType.INT16, VMType.INT32, VMType.INT64, VMType.INT256}:
        return 0
    if vm_type == VMType.BYTES16:
        return EMPTY_BYTES16
    if vm_type == VMType.BYTES32:
        return EMPTY_BYTES32
    if vm_type == VMType.BYTES64:
        return EMPTY_BYTES64
    if vm_type == VMType.STRING:
        return ""
    if vm_type == VMType.ARRAY_STRUCT:
        return VMStructArray()
    if vm_type.name.startswith("ARRAY"):
        return []
    return None


def _validate_icon_data_uri(value: str) -> None:
    match = re.match(r"(?i)^data:image/(png|jpeg|webp);base64,", value)
    if not match:
        raise BuilderError("token icon must be a png/jpeg/webp data URI")
    payload = value.split(",", 1)[1]
    if not payload:
        raise BuilderError("token icon data URI must include a non-empty base64 payload")
    try:
        base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise BuilderError("token icon data URI contains invalid base64") from exc


def _big_int_word(value: int) -> bytes:
    if value.bit_length() > 256:
        raise SerializationError("BigInt overflow")
    unsigned = value % (1 << 256)
    return unsigned.to_bytes(32, "little", signed=False)


def _int_from_word(word: bytes) -> int:
    if len(word) != 32:
        raise SerializationError("BigInt word must be 32 bytes")
    value = int.from_bytes(word[::-1], "big", signed=False)
    if word[31] & 0x80:
        value -= 1 << 256
    return value


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
