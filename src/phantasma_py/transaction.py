"""Classic Phantasma transaction support."""

from __future__ import annotations

from dataclasses import dataclass, field

from .binary import BinaryReader, BinaryWriter
from .crypto import Ed25519Signature, Hash, PhantasmaKeys, SignatureKind

SDK_PAYLOAD = b"PY-SDK-v2.0.1"


@dataclass(slots=True)
class Transaction:
    """Classic VM transaction used by script-based RPC endpoints."""

    nexus_name: str
    chain_name: str
    script: bytes
    expiration: int
    payload: bytes = SDK_PAYLOAD
    signatures: list[Ed25519Signature] = field(default_factory=list)

    @property
    def hash(self) -> Hash:
        return Hash.sha256(self.to_bytes(with_signatures=False))

    def to_bytes(self, *, with_signatures: bool = True) -> bytes:
        writer = BinaryWriter()
        writer.write_string(self.nexus_name)
        writer.write_string(self.chain_name)
        writer.write_var_bytes(self.script)
        writer.write_u32_le(self.expiration)
        writer.write_var_bytes(self.payload)
        if with_signatures:
            writer.write_var_uint(len(self.signatures))
            for signature in self.signatures:
                writer.write_u8(signature.kind)
                writer.write_var_bytes(signature.data)
        return writer.bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> Transaction:
        reader = BinaryReader(data)
        tx = cls(
            nexus_name=reader.read_string(),
            chain_name=reader.read_string(),
            script=reader.read_var_bytes(),
            expiration=reader.read_u32_le(),
            payload=reader.read_var_bytes(),
        )
        count = reader.read_var_uint()
        for _ in range(count):
            kind = SignatureKind(reader.read_u8())
            if kind != SignatureKind.ED25519:
                raise ValueError(f"unsupported signature kind: {kind}")
            tx.signatures.append(Ed25519Signature(reader.read_var_bytes()))
        reader.assert_eof()
        return tx

    def sign(self, key_pair: PhantasmaKeys) -> Ed25519Signature:
        signature = key_pair.sign(self.to_bytes(with_signatures=False))
        self.signatures.append(signature)
        return signature

    def is_signed_by(self, key_pair: PhantasmaKeys) -> bool:
        message = self.to_bytes(with_signatures=False)
        return any(signature.verify(message, [key_pair.address]) for signature in self.signatures)

    def mine(self, difficulty: int) -> None:
        if difficulty <= 0:
            return
        nonce = 0
        while self.hash.difficulty() < difficulty:
            nonce += 1
            self.payload = nonce.to_bytes(4, "little")


def tx_state_is_success(state: str) -> bool:
    return state.upper() == "HALT"


def tx_state_is_fault(state: str) -> bool:
    return state.upper() in {"FAULT", "BREAK"}
