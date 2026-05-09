from pathlib import Path

import pytest

from phantasma_py.carbon import (
    Bytes16,
    Bytes32,
    Bytes64,
    CarbonReader,
    CarbonWriter,
    IntX,
    SignedTxMsg,
    TokenSchemas,
    TxMsg,
    VMDynamicStruct,
    deserialize,
    serialize,
)


def read_value(value: str, rest: tuple[str, ...]) -> str:
    return rest[1] if len(rest) >= 2 else value


def parse_byte_arrays(value: str) -> list[bytes]:
    value = value.removeprefix("[[").removesuffix("]]")
    if not value:
        return []
    return [bytes.fromhex(part.replace(",", "")) for part in value.split("],[")]


def rows() -> list[tuple[str, str, str, tuple[str, ...]]]:
    parsed: list[tuple[str, str, str, tuple[str, ...]]] = []
    for line in Path("tests/fixtures/carbon_vectors.tsv").read_text().strip().splitlines():
        kind, value, expected, *rest = line.split("\t")
        parsed.append((kind, value, expected, tuple(rest)))
    return parsed


@pytest.mark.parametrize("kind,value,expected,rest", rows())
def test_carbon_shared_vectors(kind: str, value: str, expected: str, rest: tuple[str, ...]) -> None:
    # These vectors are shared with the Go/TS/C#/C++ SDKs and catch byte-order or packing drift.
    writer = CarbonWriter()
    if kind == "U8":
        writer.write1(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read1() == int(value)
    elif kind == "I16":
        writer.write2(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read2() == int(value)
    elif kind == "I32":
        writer.write4(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read4() == int(value)
    elif kind == "U32":
        writer.write4u(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read4u() == int(value)
    elif kind == "I64":
        writer.write8(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read8() == int(value)
    elif kind == "U64":
        writer.write8u(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read8u() == int(value)
    elif kind == "FIX16":
        writer.write16(Bytes16.from_hex(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read16() == Bytes16.from_hex(value)
    elif kind == "FIX32":
        writer.write32(Bytes32.from_hex(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read32() == Bytes32.from_hex(value)
    elif kind == "FIX64":
        writer.write64(Bytes64.from_hex(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read64() == Bytes64.from_hex(value)
    elif kind == "SZ":
        writer.write_string_z(value)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_string_z() == value
    elif kind == "ARRSZ":
        values = value.split(",")
        writer.write_string_z_array(values)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_string_z_array() == values
    elif kind == "ARR8":
        values = [int(x) for x in value.split(",")]
        writer.write_int_array(values, 1, signed=True)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_int_array(1, signed=True) == values
    elif kind == "ARR16":
        values = [int(x) for x in value.split(",")]
        writer.write_int_array(values, 2, signed=True)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_int_array(2, signed=True) == values
    elif kind == "ARR32":
        values = [int(x) for x in value.split(",")]
        writer.write_int_array(values, 4, signed=True)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_int_array(4, signed=True) == values
    elif kind == "ARR64":
        values = [int(x) for x in value.split(",")]
        writer.write_int_array(values, 8, signed=True)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_int_array(8, signed=True) == values
    elif kind == "ARRU64":
        values = [int(x) for x in value.split(",")]
        writer.write_int_array(values, 8, signed=False)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_int_array(8, signed=False) == values
    elif kind == "ARRBYTES-1D":
        writer.write_byte_array(bytes.fromhex(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_byte_array() == bytes.fromhex(value)
    elif kind == "ARRBYTES-2D":
        values = parse_byte_arrays(value)
        writer.write_byte_arrays(values)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_byte_arrays() == values
    elif kind == "BI":
        writer.write_big_int(int(value))
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_big_int() == int(read_value(value, rest))
    elif kind == "INTX":
        IntX(int(value)).write_carbon(writer)
        assert writer.bytes().hex() == expected.lower()
        assert IntX.read_carbon(CarbonReader(bytes.fromhex(expected))).value == int(read_value(value, rest))
    elif kind == "ARRBI":
        values = [int(x) for x in value.split(",")]
        writer.write_big_int_array(values)
        assert writer.bytes().hex() == expected.lower()
        assert CarbonReader(bytes.fromhex(expected)).read_big_int_array() == values
    elif kind in {"TX1", "TX-CREATE-TOKEN", "TX-CREATE-TOKEN-SERIES", "TX-MINT-NON-FUNGIBLE"}:
        assert serialize(deserialize(bytes.fromhex(expected), TxMsg)).hex() == expected.lower()
    elif kind == "TX2":
        assert serialize(deserialize(bytes.fromhex(expected), SignedTxMsg)).hex() == expected.lower()
    elif kind == "VMSTRUCT01":
        assert serialize(deserialize(bytes.fromhex(expected), TokenSchemas)).hex() == expected.lower()
    elif kind == "VMSTRUCT02":
        assert serialize(deserialize(bytes.fromhex(expected), VMDynamicStruct)).hex() == expected.lower()
    else:
        pytest.fail(f"unhandled vector kind: {kind}")
