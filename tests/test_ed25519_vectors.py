from __future__ import annotations

import hashlib
from pathlib import Path

from phantasma_py.crypto import Ed25519Signature, PhantasmaKeys

FIXTURE = Path("tests/fixtures/ed25519_vectors.tsv")
ED25519_FIXTURE_SHA256 = "dd747f5c49b49a67f1c63d02351be669558bf9da65571ed7311bcd8cf8d2bd01"


def test_ed25519_matches_shared_golden_vectors() -> None:
    data = FIXTURE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ED25519_FIXTURE_SHA256

    rows = list(_ed25519_rows(data.decode()))
    assert rows
    for case_id, seed_hex, public_key_hex, message_hex, signature_hex in rows:
        keys = PhantasmaKeys(bytes.fromhex(seed_hex))
        message = bytes.fromhex(message_hex)
        expected_signature = bytes.fromhex(signature_hex)

        assert keys.public_key.hex() == public_key_hex, case_id
        assert keys.sign(message).data == expected_signature, case_id
        assert Ed25519Signature(expected_signature).verify(message, [keys.address]), case_id

        wrong_message = bytearray(message or b"\x00")
        wrong_message[0] ^= 0xFF
        assert not Ed25519Signature(expected_signature).verify(bytes(wrong_message), [keys.address]), case_id


def _ed25519_rows(text: str):
    for line in text.splitlines():
        if not line or line.startswith("case_id\t"):
            continue
        parts = line.split("\t")
        assert len(parts) == 7
        yield parts[0], parts[2], parts[3], parts[4], parts[5]
