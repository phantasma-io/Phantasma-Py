import pytest

from phantasma_py import __version__
from phantasma_py.binary import BinaryWriter
from phantasma_py.crypto import PhantasmaKeys
from phantasma_py.transaction import SDK_PAYLOAD, Transaction, tx_state_is_fault, tx_state_is_success
from phantasma_py.vm import ScriptBuilder


def test_default_sdk_payload_matches_package_version() -> None:
    # The VM script transaction default payload is visible on-chain, so it must
    # move with the package version instead of retaining a stale release string.
    assert f"PY-SDK-v{__version__}".encode() == SDK_PAYLOAD


def test_vm_script_transaction_sign_and_round_trip() -> None:
    # VM script transaction bytes are the signing payload for VM script broadcasts.
    keys = PhantasmaKeys.from_wif("KxMn2TgXukYaNXx7tEdjh7qB2YaMgeuKy47j4rvKigHhBuZWeP3r")
    script = ScriptBuilder.begin().call_interop("Runtime.Time").end_script()
    tx = Transaction("mainnet", "main", script, 1_754_000_000)
    signature = tx.sign(keys)

    assert signature.verify(tx.to_bytes(with_signatures=False), [keys.address])
    assert tx.is_signed_by(keys)
    assert len(str(tx.hash)) == 64

    decoded = Transaction.from_bytes(tx.to_bytes())
    assert decoded.nexus_name == tx.nexus_name
    assert decoded.chain_name == tx.chain_name
    assert decoded.script == tx.script
    assert decoded.payload == tx.payload
    assert len(decoded.signatures) == 1


def test_transaction_state_helpers() -> None:
    # RPC state helpers keep application code from duplicating state spelling checks.
    assert tx_state_is_success("HALT")
    assert tx_state_is_fault("FAULT")
    assert tx_state_is_fault("break")
    assert not tx_state_is_success("FAULT")


def test_transaction_mine_uses_phantasma_pow_difficulty() -> None:
    script = ScriptBuilder.begin().call_interop("Runtime.Time").end_script()
    tx = Transaction("simnet", "main", script, 1_754_000_000, b"seed")

    tx.mine(5)

    assert tx.hash.difficulty() >= 5
    assert len(tx.payload) == 4 or tx.payload == b"seed"


def test_transaction_mine_zero_preserves_payload() -> None:
    script = ScriptBuilder.begin().call_interop("Runtime.Time").end_script()
    tx = Transaction("simnet", "main", script, 1_754_000_000, b"payload")

    tx.mine(0)

    assert tx.payload == b"payload"


def test_transaction_from_bytes_rejects_unsupported_signature_kind() -> None:
    script = ScriptBuilder.begin().call_interop("Runtime.Time").end_script()
    tx = Transaction("simnet", "main", script, 1_754_000_000, b"payload")
    writer = BinaryWriter()
    writer.write(tx.to_bytes(with_signatures=False))
    writer.write_var_uint(1)
    writer.write_u8(2)
    writer.write_var_bytes(b"not-ed25519")

    with pytest.raises(ValueError, match="unsupported signature kind"):
        Transaction.from_bytes(writer.bytes())
