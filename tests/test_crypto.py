import pytest

from phantasma_py.crypto import Address, AddressKind, CryptoError, Ed25519Signature, Hash, PhantasmaKeys
from phantasma_py.encoding import decode_base58, encode_base58


def test_base58_round_trip_preserves_leading_zeroes() -> None:
    # Address/WIF text depends on Bitcoin Base58 preserving leading zero bytes.
    payload = b"\x00\x00hello phantasma"
    assert decode_base58(encode_base58(payload)) == payload


@pytest.mark.parametrize(
    ("wif", "address"),
    [
        ("KxMn2TgXukYaNXx7tEdjh7qB2YaMgeuKy47j4rvKigHhBuZWeP3r", "P2K9zmyFDNGN6n6hHiTUAz6jqn29s5G1SWLiXwCVQcpHcQb"),
        ("L2sTuSzangXQCFxXFXJqfPAKJsstKvQdkGqP9J2VFkFRbEjd1Ez6", "P2K65RZhfxZhQcXKGgSPZL6c6hkygXipNxdeuW5FU531Bqc"),
    ],
)
def test_wif_and_address_vectors(wif: str, address: str) -> None:
    # These are existing Python SDK vectors and must remain stable after the rewrite.
    keys = PhantasmaKeys.from_wif(wif)
    assert keys.to_wif() == wif
    assert keys.address.text == address
    assert Address.from_text(address) == keys.address
    assert keys.address.kind is AddressKind.USER


def test_signature_verifies_against_derived_address() -> None:
    # Signatures must validate through the public address, matching the other SDKs' transaction signing model.
    keys = PhantasmaKeys.from_wif("KxMn2TgXukYaNXx7tEdjh7qB2YaMgeuKy47j4rvKigHhBuZWeP3r")
    message = b"phantasma-python-sdk"
    signature = keys.sign(message)
    assert signature.verify(message, [keys.address])
    assert not signature.verify(message + b"!", [keys.address])


def test_hash_difficulty_matches_phantasma_little_endian_pow() -> None:
    # Phantasma PoW difficulty follows the validator/Go/TS little-endian hash convention.
    assert Hash(bytes([0xFF] * 31 + [0x00])).difficulty() == 8
    assert Hash(bytes([0x00] + [0xFF] * 31)).difficulty() == 0
    assert Hash(bytes(32)).difficulty() == 256


def test_invalid_wif_checksum_is_rejected() -> None:
    # User-supplied private key material must fail closed on checksum errors.
    with pytest.raises(CryptoError):
        PhantasmaKeys.from_wif("KxMn2TgXukYaNXx7tEdjh7qB2YaMgeuKy47j4rvKigHhBuZWeP3s")


def test_null_address_text_round_trip() -> None:
    # NULL is a public API spelling, not a Base58 address.
    assert Address.from_text("NULL").text == "NULL"
    assert Address.from_text(None).kind is AddressKind.SYSTEM


def test_invalid_address_and_key_inputs_fail_closed() -> None:
    with pytest.raises(CryptoError, match="invalid public key length"):
        Address.from_public_key(b"short")
    with pytest.raises(CryptoError, match="address length"):
        Address(b"\x01")
    with pytest.raises(CryptoError, match="unknown address prefix"):
        Address.from_text("Z" + encode_base58(Address.null().data))
    with pytest.raises(CryptoError, match="address has to be of type User"):
        Address.from_text("P" + encode_base58(Address.null().data))
    with pytest.raises(CryptoError, match="only user addresses"):
        _ = Address.null().public_key
    with pytest.raises(CryptoError, match="hash length"):
        Hash(b"\x00")
    with pytest.raises(CryptoError, match="signature length"):
        Ed25519Signature(b"\x00")
    with pytest.raises(CryptoError, match="WIF is required"):
        PhantasmaKeys.from_wif("")
    with pytest.raises(CryptoError, match="private key length"):
        PhantasmaKeys(b"\x00")
