import json
from pathlib import Path
from typing import Any

from phantasma_py.carbon import (
    Bytes32,
    CarbonReader,
    CarbonWriter,
    IntX,
    SeriesInfo,
    SmallString,
    TokenFlags,
    TokenInfo,
    VMDynamicStruct,
    VMDynamicVariable,
    VMNamedDynamicVariable,
    VMStructSchema,
    VMType,
    deserialize,
    serialize,
)

FIXTURES: dict[str, Any] = json.loads(Path("tests/fixtures/validator_int256_fixtures.json").read_text())
INT256_READBACK = {fixture["sourceDec"]: fixture["readBackSignedDec"] for fixture in FIXTURES["int256"]}


def test_raw_int256_matches_validator_fixtures() -> None:
    for fixture in FIXTURES["int256"]:
        writer = CarbonWriter()
        writer.write_big_int(int(fixture["sourceDec"]))
        assert writer.bytes().hex().upper() == fixture["wireHex"], fixture["id"]

        reader = CarbonReader(bytes.fromhex(fixture["wireHex"]))
        assert str(reader.read_big_int()) == fixture["readBackSignedDec"], fixture["id"]
        reader.assert_eof()


def test_intx_matches_validator_fixtures() -> None:
    for fixture in FIXTURES["intx"]:
        assert serialize(IntX(int(fixture["sourceDec"]))).hex().upper() == fixture["wireHex"], fixture["id"]
        assert str(deserialize(bytes.fromhex(fixture["wireHex"]), IntX)) == fixture["readBackDec"], fixture["id"]


def test_vm_dynamic_int256_matches_validator_fixtures() -> None:
    for fixture in FIXTURES["vmDynamicInt256"]:
        value = VMDynamicVariable(VMType.INT256, int(fixture["sourceDec"]))
        assert serialize(value).hex().upper() == fixture["wireHex"], fixture["id"]

        decoded = deserialize(bytes.fromhex(fixture["wireHex"]), VMDynamicVariable)
        assert decoded.type == VMType.INT256, fixture["id"]
        assert str(decoded.data) == INT256_READBACK[fixture["sourceDec"]], fixture["id"]


def test_vm_dynamic_int256_array_matches_validator_fixtures() -> None:
    for fixture in FIXTURES["vmDynamicInt256Array"]:
        value = VMDynamicVariable(VMType.ARRAY_INT256, [int(item) for item in fixture["values"]])
        assert serialize(value).hex().upper() == fixture["wireHex"], fixture["id"]

        decoded = deserialize(bytes.fromhex(fixture["wireHex"]), VMDynamicVariable)
        assert decoded.type == VMType.ARRAY_INT256, fixture["id"]
        assert [str(item) for item in decoded.data] == [INT256_READBACK[item] for item in fixture["values"]]


def test_metadata_structs_match_validator_fixtures() -> None:
    for fixture in FIXTURES["metadataStructs"]:
        value = _build_metadata_struct(fixture)
        assert serialize(value).hex().upper() == fixture["wireHex"], fixture["id"]

        decoded = deserialize(bytes.fromhex(fixture["wireHex"]), VMDynamicStruct)
        field_names = [field.name.value for field in decoded.fields]
        if fixture["shape"] == "nft-default":
            assert field_names == ["_i", "rom"], fixture["id"]
        else:
            assert field_names == ["_i", "mode", "rom"], fixture["id"]

        id_field = decoded.get("_i")
        assert id_field is not None and id_field.type == VMType.INT256, fixture["id"]
        assert str(id_field.data) == fixture["_iDec"], fixture["id"]

        rom_field = decoded.get("rom")
        assert rom_field is not None and rom_field.type == VMType.BYTES, fixture["id"]
        assert bytes(rom_field.data).hex().upper() == fixture["romHex"], fixture["id"]

        if "mode" in fixture:
            mode_field = decoded.get("mode")
            assert mode_field is not None and mode_field.type == VMType.INT8, fixture["id"]
            assert mode_field.data == fixture["mode"], fixture["id"]


def test_token_info_matches_validator_fixtures() -> None:
    for fixture in FIXTURES["tokenInfo"]:
        value = _build_token_info(fixture)
        assert serialize(value).hex().upper() == fixture["wireHex"], fixture["id"]

        decoded = deserialize(bytes.fromhex(fixture["wireHex"]), TokenInfo)
        assert str(decoded.max_supply) == fixture["maxSupplyDec"], fixture["id"]
        assert int(decoded.flags) == fixture["flags"], fixture["id"]
        assert decoded.decimals == fixture["decimals"], fixture["id"]
        assert decoded.owner == _expected_token_owner(fixture["id"]), fixture["id"]
        assert decoded.symbol.value == fixture["symbol"], fixture["id"]
        assert decoded.metadata.hex().upper() == fixture["metadataHex"], fixture["id"]


def test_series_info_matches_validator_fixtures() -> None:
    for fixture in FIXTURES["seriesInfo"]:
        value = _build_series_info(fixture)
        assert serialize(value).hex().upper() == fixture["wireHex"], fixture["id"]

        decoded = deserialize(bytes.fromhex(fixture["wireHex"]), SeriesInfo)
        assert decoded.max_mint == fixture["maxMint"], fixture["id"]
        assert decoded.max_supply == fixture["maxSupply"], fixture["id"]
        assert decoded.owner == _expected_series_owner(fixture["id"]), fixture["id"]
        assert decoded.metadata.hex().upper() == fixture["metadataHex"], fixture["id"]
        assert decoded.rom.fields == [], fixture["id"]
        assert decoded.ram.fields == [], fixture["id"]

        metadata = deserialize(decoded.metadata, VMDynamicStruct)
        id_field = metadata.get("_i")
        assert id_field is not None and str(id_field.data) == _expected_series_metadata_id(fixture["id"])


def _build_metadata_struct(fixture: dict[str, Any]) -> VMDynamicStruct:
    fields = [
        VMNamedDynamicVariable.make("_i", VMType.INT256, int(fixture["_iDec"])),
        VMNamedDynamicVariable.make("rom", VMType.BYTES, bytes.fromhex(fixture["romHex"])),
    ]
    if "mode" in fixture:
        fields.append(VMNamedDynamicVariable.make("mode", VMType.INT8, int(fixture["mode"])))
    return VMDynamicStruct(fields)


def _build_token_info(fixture: dict[str, Any]) -> TokenInfo:
    return TokenInfo(
        IntX(int(fixture["maxSupplyDec"])),
        TokenFlags(fixture["flags"]),
        int(fixture["decimals"]),
        _expected_token_owner(fixture["id"]),
        SmallString(fixture["symbol"]),
        bytes.fromhex(fixture["metadataHex"]),
    )


def _build_series_info(fixture: dict[str, Any]) -> SeriesInfo:
    return SeriesInfo(
        int(fixture["maxMint"]),
        int(fixture["maxSupply"]),
        _expected_series_owner(fixture["id"]),
        bytes.fromhex(fixture["metadataHex"]),
        VMStructSchema(),
        VMStructSchema(),
    )


def _expected_token_owner(fixture_id: str) -> Bytes32:
    if fixture_id == "fungible_zero_supply":
        return _pattern_bytes32(0x10)
    if fixture_id == "big_fungible_u64max_supply":
        return _pattern_bytes32(0x20)
    raise AssertionError(f"unknown token fixture id: {fixture_id}")


def _expected_series_owner(fixture_id: str) -> Bytes32:
    if fixture_id == "series_zero_metaid":
        return _pattern_bytes32(0x30)
    if fixture_id == "series_problematic_metaid":
        return _pattern_bytes32(0x40)
    raise AssertionError(f"unknown series fixture id: {fixture_id}")


def _expected_series_metadata_id(fixture_id: str) -> str:
    if fixture_id == "series_zero_metaid":
        return "0"
    if fixture_id == "series_problematic_metaid":
        return "342701406799689386264365071881606655601301200422094937311139938246178500459"
    raise AssertionError(f"unknown series fixture id: {fixture_id}")


def _pattern_bytes32(seed: int) -> Bytes32:
    return Bytes32(bytes((seed + index) & 0xFF for index in range(32)))
