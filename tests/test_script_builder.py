from datetime import UTC, datetime

import pytest

from phantasma_py.binary import BinaryWriter
from phantasma_py.crypto import Address, PhantasmaKeys
from phantasma_py.errors import BuilderError, SerializationError
from phantasma_py.vm import Opcode, ScriptBuilder, VMObject, VMType

EXPECTED_CONSENSUS_SINGLE_VOTE = (
    "0D00030350340303000D000302102703000D000223220000000000000000000000000000000000000000000000000000"
    "000000000000000003000D000223220100AA53BE71FC41BC0889B694F4D6D03F7906A3D9A21705943CAF9632EEAFBB"
    "489503000D000408416C6C6F7747617303000D0004036761732D00012E010D0003010003000D00041D73797374656D"
    "2E6E657875732E70726F746F636F6C2E76657273696F6E03000D00042F50324B464579466576705166536157384734"
    "566A536D6857555A585234517247395951523148624D7054554370434C03000D00040A53696E676C65566F74650300"
    "0D000409636F6E73656E7375732D00012E010D000223220100AA53BE71FC41BC0889B694F4D6D03F7906A3D9A217"
    "05943CAF9632EEAFBB489503000D0004085370656E6447617303000D0004036761732D00012E010B"
)


def test_script_builder_matches_shared_consensus_vector() -> None:
    # Shared Go/C# vector proves addresses and numeric arguments are loaded with VM binary encoding.
    keys = PhantasmaKeys.from_wif("L5UEVHBjujaR1721aZM5Zm5ayjDyamMZS9W35RE9Y9giRkdf3dVx")
    script = (
        ScriptBuilder.begin()
        .allow_gas(keys.address, Address.null(), 10_000, 210_000)
        .call_contract("consensus", "SingleVote", keys.address.text, "system.nexus.protocol.version", 0)
        .spend_gas(keys.address)
        .end_script_hex()
    )
    assert script == EXPECTED_CONSENSUS_SINGLE_VOTE


def test_script_builder_resolves_labels_per_instance() -> None:
    # Label resolution is scoped per builder so scripts cannot leak jumps into later builders.
    script = (
        ScriptBuilder.begin()
        .emit_jump(Opcode.JMP, "done")
        .emit_load_string(0, "unused")
        .emit_label("DONE")
        .end_script()
    )
    target = int.from_bytes(script[1:3], "little")
    assert script[target - 1] == Opcode.NOP
    assert script[target] == Opcode.RET
    assert ScriptBuilder.begin().end_script() == bytes([Opcode.RET])


def test_script_builder_reports_errors_without_emitting_invalid_script() -> None:
    # Checked finalization gives callers a non-panic path for untrusted text input.
    script, error = ScriptBuilder.begin().transfer_tokens_text("SOUL", "bad-address", "NULL", 1).end_script_with_error()
    assert script == b""
    assert error is not None

    with pytest.raises(BuilderError):
        ScriptBuilder.begin().emit_jump(Opcode.JMP, "missing").end_script()


def test_script_builder_runtime_helper_parity() -> None:
    keys = PhantasmaKeys.from_wif("KxMn2TgXukYaNXx7tEdjh7qB2YaMgeuKy47j4rvKigHhBuZWeP3r")
    other = Address.null()

    assert (
        ScriptBuilder.begin().mint_tokens("SOUL", keys.address, other, 1).end_script()
        == ScriptBuilder.begin().call_interop("Runtime.MintTokens", keys.address, other, "SOUL", 1).end_script()
    )
    assert (
        ScriptBuilder.begin().transfer_balance("SOUL", keys.address, other).end_script()
        == ScriptBuilder.begin().call_interop("Runtime.TransferBalance", keys.address, other, "SOUL").end_script()
    )
    assert (
        ScriptBuilder.begin().transfer_nft("ART", keys.address, other, 42).end_script()
        == ScriptBuilder.begin().call_interop("Runtime.TransferToken", keys.address, other, "ART", 42).end_script()
    )
    assert (
        ScriptBuilder.begin().cross_transfer_token(other, "SOUL", keys.address, other, 1).end_script()
        == ScriptBuilder.begin().call_interop("Runtime.SendTokens", other, keys.address, other, "SOUL", 1).end_script()
    )
    assert (
        ScriptBuilder.begin().call_nft("ART", 7, "mint", keys.address).end_script()
        == ScriptBuilder.begin().call_contract("ART#7", "mint", keys.address).end_script()
    )


def test_script_builder_all_text_helpers_match_typed_helpers() -> None:
    keys = PhantasmaKeys.from_wif("KxMn2TgXukYaNXx7tEdjh7qB2YaMgeuKy47j4rvKigHhBuZWeP3r")
    address = keys.address
    null = Address.null()

    assert ScriptBuilder.begin().allow_gas_text(address.text, "NULL", 1, 2).end_script() == (
        ScriptBuilder.begin().allow_gas(address, null, 1, 2).end_script()
    )
    assert ScriptBuilder.begin().spend_gas_text(address.text).end_script() == (
        ScriptBuilder.begin().spend_gas(address).end_script()
    )
    assert ScriptBuilder.begin().transfer_tokens_text("KCAL", address.text, "NULL", 3).end_script() == (
        ScriptBuilder.begin().transfer_tokens("KCAL", address, null, 3).end_script()
    )
    assert ScriptBuilder.begin().mint_tokens_text("KCAL", address.text, "NULL", 3).end_script() == (
        ScriptBuilder.begin().mint_tokens("KCAL", address, null, 3).end_script()
    )
    assert ScriptBuilder.begin().transfer_tokens_to_text("KCAL", address, "NULL", 3).end_script() == (
        ScriptBuilder.begin().transfer_tokens("KCAL", address, null, 3).end_script()
    )
    assert ScriptBuilder.begin().transfer_balance_text("KCAL", address.text, "NULL").end_script() == (
        ScriptBuilder.begin().transfer_balance("KCAL", address, null).end_script()
    )
    assert ScriptBuilder.begin().transfer_nft_text("ART", address.text, "NULL", 4).end_script() == (
        ScriptBuilder.begin().transfer_nft("ART", address, null, 4).end_script()
    )
    assert ScriptBuilder.begin().transfer_nft_to_text("ART", address, "NULL", 4).end_script() == (
        ScriptBuilder.begin().transfer_nft("ART", address, null, 4).end_script()
    )
    assert ScriptBuilder.begin().cross_transfer_token_text("NULL", "KCAL", address.text, "NULL", 5).end_script() == (
        ScriptBuilder.begin().cross_transfer_token(null, "KCAL", address, null, 5).end_script()
    )
    assert ScriptBuilder.begin().cross_transfer_token_to_text(null, "KCAL", address, "NULL", 5).end_script() == (
        ScriptBuilder.begin().cross_transfer_token(null, "KCAL", address, null, 5).end_script()
    )
    assert ScriptBuilder.begin().cross_transfer_nft_text("NULL", "ART", address.text, "NULL", 6).end_script() == (
        ScriptBuilder.begin().cross_transfer_nft(null, "ART", address, null, 6).end_script()
    )
    assert ScriptBuilder.begin().cross_transfer_nft_to_text(null, "ART", address, "NULL", 6).end_script() == (
        ScriptBuilder.begin().cross_transfer_nft(null, "ART", address, null, 6).end_script()
    )
    assert ScriptBuilder.begin().stake_text(address.text, 7).end_script() == (
        ScriptBuilder.begin().stake(address, 7).end_script()
    )
    assert ScriptBuilder.begin().unstake_text(address.text, 8).end_script() == (
        ScriptBuilder.begin().unstake(address, 8).end_script()
    )


def test_script_builder_rejects_invalid_low_level_operations() -> None:
    with pytest.raises(BuilderError, match="invalid jump opcode"):
        ScriptBuilder.begin().emit_jump(Opcode.RET, "done").end_script()
    with pytest.raises(BuilderError, match="invalid conditional jump opcode"):
        ScriptBuilder.begin().emit_conditional_jump(Opcode.JMP, 0, "done").end_script()
    with pytest.raises(BuilderError, match="invalid number of registers"):
        ScriptBuilder.begin().emit_call("done", 0).end_script()
    with pytest.raises(BuilderError, match="tried to load too much data"):
        ScriptBuilder.begin().emit_load(0, b"x" * 0x10000, VMType.BYTES).end_script()


def test_script_builder_rejects_unsupported_arguments() -> None:
    script, error = ScriptBuilder.begin().call_interop("Runtime.Time", None).end_script_with_error()
    assert script == b""
    assert error is not None
    assert "unsupported nil argument" in str(error)

    script, error = ScriptBuilder.begin().call_interop("Runtime.Time", object()).end_script_with_error()
    assert script == b""
    assert error is not None
    assert "unsupported type object" in str(error)


def test_script_builder_array_and_timestamp_argument_paths_are_stable() -> None:
    script = (
        ScriptBuilder.begin()
        .call_interop("Runtime.Test", ["alpha", 7], datetime(2026, 5, 9, 12, 0, tzinfo=UTC))
        .end_script()
    )
    assert bytes([Opcode.CAST]) in script
    assert bytes([Opcode.PUT]) in script
    assert bytes([Opcode.EXTCALL]) in script


def test_vm_object_decodes_primitives_and_structs() -> None:
    assert VMObject.from_bytes(bytes([VMType.NONE])).as_number() == 0
    assert VMObject.from_bytes(bytes([VMType.NONE])).as_string() == "Null"
    assert VMObject.from_bytes(bytes([VMType.BOOL, 1])).as_string() == "true"
    assert VMObject.from_bytes(bytes([VMType.BOOL, 0])).as_number() == 0

    writer = BinaryWriter()
    writer.write_u8(VMType.STRUCT)
    writer.write_var_uint(2)
    writer.write_u8(VMType.STRING)
    writer.write_string("name")
    writer.write_u8(VMType.STRING)
    writer.write_string("sdk")
    writer.write_u8(VMType.NUMBER)
    writer.write_big_integer(7)
    writer.write_u8(VMType.BOOL)
    writer.write_bool(True)

    obj = VMObject.from_bytes(writer.bytes())
    assert obj.type is VMType.STRUCT
    assert obj.data[VMObject(VMType.STRING, "name")].as_string() == "sdk"
    assert obj.data[VMObject(VMType.NUMBER, 7)].as_number() == 1


def test_vm_object_rejects_invalid_or_incompatible_values() -> None:
    with pytest.raises(SerializationError, match="unsupported VM object type"):
        VMObject.from_bytes(b"\xff")
    with pytest.raises(SerializationError, match="unexpected trailing"):
        VMObject.from_bytes(bytes([VMType.BOOL, 1, 0]))
    with pytest.raises(SerializationError, match="cannot convert BYTES to number"):
        VMObject(VMType.BYTES, b"1").as_number()
    with pytest.raises(UnicodeDecodeError):
        VMObject(VMType.BYTES, b"\xff").as_string()
