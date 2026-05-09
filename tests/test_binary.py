import pytest

from phantasma_py.binary import BinaryReader, BinaryWriter, big_int_to_vm_bytes, vm_bytes_to_big_int
from phantasma_py.errors import SerializationError


@pytest.mark.parametrize(
    ("value", "encoded"),
    [
        (0xFC, "FC"),
        (0xFD, "FDFD00"),
        (0xFFFF, "FDFFFF"),
        (0x10000, "FE00000100"),
        (0xFFFFFFFF, "FEFFFFFFFF"),
        (0x100000000, "FF0000000001000000"),
    ],
)
def test_var_uint_boundaries_match_reference_sdks(value: int, encoded: str) -> None:
    writer = BinaryWriter()
    writer.write_var_uint(value)

    data = writer.bytes()
    reader = BinaryReader(data)
    assert data.hex().upper() == encoded
    assert reader.read_var_uint() == value
    reader.assert_eof()


@pytest.mark.parametrize("value", [-1, 1 << 64])
def test_var_uint_rejects_invalid_values(value: int) -> None:
    with pytest.raises(SerializationError):
        BinaryWriter().write_var_uint(value)


def test_reader_bounds_and_max_array_size_fail_closed() -> None:
    with pytest.raises(SerializationError, match="end of stream"):
        BinaryReader(b"\x01").read_u16_le()

    writer = BinaryWriter()
    writer.write_var_uint(4)
    writer.write(b"abcd")
    with pytest.raises(SerializationError, match="byte array too large"):
        BinaryReader(writer.bytes()).read_var_bytes(max_size=3)

    reader = BinaryReader(b"\x01\x02")
    assert reader.read_u8() == 1
    with pytest.raises(SerializationError, match="unexpected trailing"):
        reader.assert_eof()


@pytest.mark.parametrize(
    "value",
    [
        0,
        1,
        -1,
        127,
        128,
        -128,
        -129,
        255,
        256,
        -255,
        2**63 - 1,
        -(2**63),
    ],
)
def test_vm_big_integer_round_trip_edges(value: int) -> None:
    raw = big_int_to_vm_bytes(value)
    assert vm_bytes_to_big_int(raw) == value
    if len(raw) > 1:
        assert not (raw[-1] == 0x00 and raw[-2] & 0x80 == 0)
        assert not (raw[-1] == 0xFF and raw[-2] & 0x80 != 0)


def test_fixed_width_integer_writers_reject_out_of_range_values() -> None:
    writer = BinaryWriter()
    for action in (
        lambda: writer.write_u8(256),
        lambda: writer.write_u16_le(-1),
        lambda: writer.write_u32_le(1 << 32),
        lambda: writer.write_u64_le(1 << 64),
        lambda: writer.write_i64_le(1 << 63),
        lambda: writer.write_i64_le(-(1 << 63) - 1),
    ):
        with pytest.raises(SerializationError):
            action()
