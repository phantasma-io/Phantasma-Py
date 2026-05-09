"""Phantasma VM objects, opcodes, and script builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

from .binary import BinaryReader, BinaryWriter, big_int_to_vm_bytes
from .crypto import Address
from .errors import BuilderError, SerializationError


class Opcode(IntEnum):
    NOP = 0
    MOVE = 1
    COPY = 2
    PUSH = 3
    POP = 4
    SWAP = 5
    CALL = 6
    EXTCALL = 7
    JMP = 8
    JMPIF = 9
    JMPNOT = 10
    RET = 11
    THROW = 12
    LOAD = 13
    CAST = 14
    CAT = 15
    RANGE = 16
    LEFT = 17
    RIGHT = 18
    SIZE = 19
    COUNT = 20
    NOT = 21
    AND = 22
    OR = 23
    XOR = 24
    EQUAL = 25
    LT = 26
    GT = 27
    LTE = 28
    GTE = 29
    INC = 30
    DEC = 31
    SIGN = 32
    NEGATE = 33
    ABS = 34
    ADD = 35
    SUB = 36
    MUL = 37
    DIV = 38
    MOD = 39
    SHL = 40
    SHR = 41
    MIN = 42
    MAX = 43
    POW = 44
    CTX = 45
    SWITCH = 46
    PUT = 47
    GET = 48
    CLEAR = 49
    UNPACK = 50
    PACK = 51
    DEBUG = 52
    SUBSTR = 53
    REMOVE = 54
    EVM = 255


class VMType(IntEnum):
    NONE = 0
    STRUCT = 1
    BYTES = 2
    NUMBER = 3
    STRING = 4
    TIMESTAMP = 5
    BOOL = 6
    ENUM = 7
    OBJECT = 8


@dataclass(frozen=True, slots=True)
class VMObject:
    """Decoded classic VM object."""

    type: VMType = VMType.NONE
    data: Any = None

    @classmethod
    def from_bytes(cls, data: bytes) -> VMObject:
        reader = BinaryReader(data)
        out = cls.read(reader)
        reader.assert_eof()
        return out

    @classmethod
    def read(cls, reader: BinaryReader) -> VMObject:
        try:
            vm_type = VMType(reader.read_u8())
        except ValueError as exc:
            raise SerializationError("unsupported VM object type") from exc
        if vm_type == VMType.NONE:
            return cls(vm_type, None)
        if vm_type == VMType.BOOL:
            return cls(vm_type, reader.read_bool())
        if vm_type == VMType.BYTES:
            return cls(vm_type, reader.read_var_bytes())
        if vm_type == VMType.ENUM:
            return cls(vm_type, reader.read_u32_le())
        if vm_type == VMType.NUMBER:
            return cls(vm_type, reader.read_big_integer())
        if vm_type == VMType.STRING:
            return cls(vm_type, reader.read_string())
        if vm_type == VMType.TIMESTAMP:
            return cls(vm_type, reader.read_u32_le())
        if vm_type == VMType.OBJECT:
            return cls(vm_type, reader.read_var_bytes())
        if vm_type == VMType.STRUCT:
            count = reader.read_var_uint()
            items: dict[VMObject, VMObject] = {}
            for _ in range(count):
                key = cls.read(reader)
                value = cls.read(reader)
                items[key] = value
            return cls(vm_type, items)
        raise SerializationError(f"unsupported VM object type: {vm_type}")

    def as_number(self) -> int:
        if self.type == VMType.NUMBER:
            return int(self.data)
        if self.type == VMType.BOOL:
            return 1 if self.data else 0
        if self.type in {VMType.STRING, VMType.ENUM, VMType.TIMESTAMP}:
            return int(self.data)
        if self.type == VMType.NONE:
            return 0
        raise SerializationError(f"cannot convert {self.type.name} to number")

    def as_string(self) -> str:
        if self.type == VMType.STRING:
            return str(self.data)
        if self.type == VMType.BYTES:
            return bytes(self.data).decode("utf-8")
        if self.type == VMType.BOOL:
            return "true" if self.data else "false"
        if self.type in {VMType.NUMBER, VMType.ENUM, VMType.TIMESTAMP}:
            return str(self.data)
        if self.type == VMType.NONE:
            return "Null"
        raise SerializationError(f"cannot convert {self.type.name} to string")


class ScriptBuilder:
    """Incremental Phantasma VM bytecode builder.

    Builder errors are retained and returned by `end_script_with_error`; the
    convenience `end_script` raises when invalid user input would otherwise
    produce a malformed script.
    """

    MAX_REGISTER_COUNT = 32

    def __init__(self) -> None:
        self._writer = BinaryWriter()
        self._jump_locations: dict[int, str] = {}
        self._label_locations: dict[str, int] = {}
        self._error: Exception | None = None

    @classmethod
    def begin(cls) -> ScriptBuilder:
        return cls()

    @property
    def current_size(self) -> int:
        return len(self._writer.bytes())

    def end_script(self) -> bytes:
        script, error = self.end_script_with_error()
        if error is not None:
            raise error
        return script

    def end_script_hex(self) -> str:
        return self.end_script().hex().upper()

    def end_script_with_error(self) -> tuple[bytes, Exception | None]:
        self.emit(Opcode.RET)
        if self._error is not None:
            return b"", self._error
        try:
            return self.to_script(), None
        except Exception as exc:
            return b"", exc

    def to_script(self) -> bytes:
        script = bytearray(self._writer.bytes())
        for offset, label in self._jump_locations.items():
            normalized = label.lower()
            if normalized not in self._label_locations:
                raise BuilderError(f"could not find label: {label}")
            target = self._label_locations[normalized]
            if offset < 0 or offset + 1 >= len(script):
                raise BuilderError(f"invalid jump patch offset: {offset}")
            script[offset : offset + 2] = target.to_bytes(2, "little")
        return bytes(script)

    def emit(self, opcode: Opcode) -> ScriptBuilder:
        self._writer.write_u8(int(opcode))
        return self

    def emit_raw(self, data: bytes) -> ScriptBuilder:
        self._writer.write(bytes(data))
        return self

    def emit_push(self, reg: int) -> ScriptBuilder:
        return self.emit(Opcode.PUSH)._byte(reg)

    def emit_pop(self, reg: int) -> ScriptBuilder:
        return self.emit(Opcode.POP)._byte(reg)

    def emit_throw(self, reg: int) -> ScriptBuilder:
        return self.emit(Opcode.THROW)._byte(reg)

    def emit_ext_call(self, method: str, reg: int = 0) -> ScriptBuilder:
        return self.emit_load_string(reg, method).emit(Opcode.EXTCALL)._byte(reg)

    def emit_load(self, reg: int, data: bytes, vm_type: VMType) -> ScriptBuilder:
        raw = bytes(data)
        if len(raw) > 0xFFFF:
            return self._fail(f"tried to load too much data: {len(raw)} bytes")
        self.emit(Opcode.LOAD)
        self._byte(reg)
        self._byte(vm_type)
        self._writer.write_var_uint(len(raw))
        self._writer.write(raw)
        return self

    def emit_load_string(self, reg: int, value: str) -> ScriptBuilder:
        return self.emit_load(reg, value.encode("utf-8"), VMType.STRING)

    def emit_load_bool(self, reg: int, value: bool) -> ScriptBuilder:
        return self.emit_load(reg, b"\x01" if value else b"\x00", VMType.BOOL)

    def emit_load_number(self, reg: int, value: int) -> ScriptBuilder:
        return self.emit_load(reg, big_int_to_vm_bytes(value), VMType.NUMBER)

    def emit_load_time(self, reg: int, value: datetime) -> ScriptBuilder:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return self.emit_load(reg, int(value.timestamp()).to_bytes(8, "little"), VMType.TIMESTAMP)

    def emit_move(self, src_reg: int, dst_reg: int) -> ScriptBuilder:
        return self.emit(Opcode.MOVE)._byte(src_reg)._byte(dst_reg)

    def emit_copy(self, src_reg: int, dst_reg: int) -> ScriptBuilder:
        return self.emit(Opcode.COPY)._byte(src_reg)._byte(dst_reg)

    def emit_label(self, label: str) -> ScriptBuilder:
        self.emit(Opcode.NOP)
        self._label_locations[label.lower()] = self.current_size
        return self

    def emit_jump(self, opcode: Opcode, label: str, reg: int = 0) -> ScriptBuilder:
        if opcode not in {Opcode.JMP, Opcode.JMPIF, Opcode.JMPNOT}:
            return self._fail(f"invalid jump opcode: {opcode}")
        self.emit(opcode)
        if opcode != Opcode.JMP:
            self._byte(reg)
        offset = self.current_size
        self._writer.write_u16_le(0)
        self._jump_locations[offset] = label
        return self

    def emit_call(self, label: str, register_count: int) -> ScriptBuilder:
        if register_count < 1 or register_count > self.MAX_REGISTER_COUNT:
            return self._fail(f"invalid number of registers: {register_count}")
        self.emit(Opcode.CALL)
        self._byte(register_count)
        offset = self.current_size
        self._writer.write_u16_le(0)
        self._jump_locations[offset] = label
        return self

    def emit_conditional_jump(self, opcode: Opcode, src_reg: int, label: str) -> ScriptBuilder:
        if opcode not in {Opcode.JMPIF, Opcode.JMPNOT}:
            return self._fail(f"invalid conditional jump opcode: {opcode.name}")
        return self.emit_jump(opcode, label, src_reg)

    def emit_var_bytes(self, value: int) -> ScriptBuilder:
        self._writer.write_var_uint(value)
        return self

    def call_interop(self, method: str, *args: Any) -> ScriptBuilder:
        self._insert_method_args(args)
        self.emit_load_string(0, method)
        self.emit(Opcode.EXTCALL)
        self._byte(0)
        return self

    def call_contract(self, contract_name: str, method: str, *args: Any) -> ScriptBuilder:
        self._insert_method_args(args)
        self.emit_load_string(0, method)
        self.emit_push(0)
        self.emit_load_string(0, contract_name)
        self.emit(Opcode.CTX)
        self._byte(0)
        self._byte(1)
        self.emit(Opcode.SWITCH)
        self._byte(1)
        return self

    def allow_gas(self, from_address: Address, to_address: Address, gas_price: int, gas_limit: int) -> ScriptBuilder:
        return self.call_contract("gas", "AllowGas", from_address, to_address, gas_price, gas_limit)

    def allow_gas_text(self, from_address: str, to_address: str, gas_price: int, gas_limit: int) -> ScriptBuilder:
        try:
            return self.allow_gas(Address.from_text(from_address), Address.from_text(to_address), gas_price, gas_limit)
        except Exception as exc:
            return self._fail(str(exc))

    def spend_gas(self, address: Address) -> ScriptBuilder:
        return self.call_contract("gas", "SpendGas", address)

    def spend_gas_text(self, address: str) -> ScriptBuilder:
        try:
            return self.spend_gas(Address.from_text(address))
        except Exception as exc:
            return self._fail(str(exc))

    def transfer_tokens(self, symbol: str, from_address: Address, to_address: Address, amount: int) -> ScriptBuilder:
        return self.call_interop("Runtime.TransferTokens", from_address, to_address, symbol, amount)

    def transfer_tokens_text(self, symbol: str, from_address: str, to_address: str, amount: int) -> ScriptBuilder:
        try:
            return self.transfer_tokens(symbol, Address.from_text(from_address), Address.from_text(to_address), amount)
        except Exception as exc:
            return self._fail(str(exc))

    def mint_tokens(self, symbol: str, from_address: Address, to_address: Address, amount: int) -> ScriptBuilder:
        return self.call_interop("Runtime.MintTokens", from_address, to_address, symbol, amount)

    def mint_tokens_text(self, symbol: str, from_address: str, to_address: str, amount: int) -> ScriptBuilder:
        try:
            return self.mint_tokens(symbol, Address.from_text(from_address), Address.from_text(to_address), amount)
        except Exception as exc:
            return self._fail(str(exc))

    def transfer_tokens_to_text(
        self, symbol: str, from_address: Address, to_address: str, amount: int
    ) -> ScriptBuilder:
        try:
            return self.transfer_tokens(symbol, from_address, Address.from_text(to_address), amount)
        except Exception as exc:
            return self._fail(str(exc))

    def transfer_balance(self, symbol: str, from_address: Address, to_address: Address) -> ScriptBuilder:
        return self.call_interop("Runtime.TransferBalance", from_address, to_address, symbol)

    def transfer_balance_text(self, symbol: str, from_address: str, to_address: str) -> ScriptBuilder:
        try:
            return self.transfer_balance(symbol, Address.from_text(from_address), Address.from_text(to_address))
        except Exception as exc:
            return self._fail(str(exc))

    def transfer_nft(self, symbol: str, from_address: Address, to_address: Address, token_id: int) -> ScriptBuilder:
        return self.call_interop("Runtime.TransferToken", from_address, to_address, symbol, token_id)

    def transfer_nft_text(self, symbol: str, from_address: str, to_address: str, token_id: int) -> ScriptBuilder:
        try:
            return self.transfer_nft(symbol, Address.from_text(from_address), Address.from_text(to_address), token_id)
        except Exception as exc:
            return self._fail(str(exc))

    def transfer_nft_to_text(self, symbol: str, from_address: Address, to_address: str, token_id: int) -> ScriptBuilder:
        try:
            return self.transfer_nft(symbol, from_address, Address.from_text(to_address), token_id)
        except Exception as exc:
            return self._fail(str(exc))

    def cross_transfer_token(
        self, destination_chain: Address, symbol: str, from_address: Address, to_address: Address, amount: int
    ) -> ScriptBuilder:
        return self.call_interop("Runtime.SendTokens", destination_chain, from_address, to_address, symbol, amount)

    def cross_transfer_token_text(
        self, destination_chain: str, symbol: str, from_address: str, to_address: str, amount: int
    ) -> ScriptBuilder:
        try:
            destination = Address.from_text(destination_chain)
            sender = Address.from_text(from_address)
            receiver = Address.from_text(to_address)
            return self.cross_transfer_token(destination, symbol, sender, receiver, amount)
        except Exception as exc:
            return self._fail(str(exc))

    def cross_transfer_token_to_text(
        self, destination_chain: Address, symbol: str, from_address: Address, to_address: str, amount: int
    ) -> ScriptBuilder:
        try:
            return self.cross_transfer_token(
                destination_chain, symbol, from_address, Address.from_text(to_address), amount
            )
        except Exception as exc:
            return self._fail(str(exc))

    def cross_transfer_nft(
        self, destination_chain: Address, symbol: str, from_address: Address, to_address: Address, token_id: int
    ) -> ScriptBuilder:
        return self.call_interop("Runtime.SendToken", destination_chain, from_address, to_address, symbol, token_id)

    def cross_transfer_nft_text(
        self, destination_chain: str, symbol: str, from_address: str, to_address: str, token_id: int
    ) -> ScriptBuilder:
        try:
            destination = Address.from_text(destination_chain)
            sender = Address.from_text(from_address)
            receiver = Address.from_text(to_address)
            return self.cross_transfer_nft(destination, symbol, sender, receiver, token_id)
        except Exception as exc:
            return self._fail(str(exc))

    def cross_transfer_nft_to_text(
        self, destination_chain: Address, symbol: str, from_address: Address, to_address: str, token_id: int
    ) -> ScriptBuilder:
        try:
            return self.cross_transfer_nft(
                destination_chain, symbol, from_address, Address.from_text(to_address), token_id
            )
        except Exception as exc:
            return self._fail(str(exc))

    def stake(self, address: Address, amount: int) -> ScriptBuilder:
        return self.call_contract("stake", "Stake", address, amount)

    def stake_text(self, address: str, amount: int) -> ScriptBuilder:
        try:
            return self.stake(Address.from_text(address), amount)
        except Exception as exc:
            return self._fail(str(exc))

    def unstake(self, address: Address, amount: int) -> ScriptBuilder:
        return self.call_contract("stake", "Unstake", address, amount)

    def unstake_text(self, address: str, amount: int) -> ScriptBuilder:
        try:
            return self.unstake(Address.from_text(address), amount)
        except Exception as exc:
            return self._fail(str(exc))

    def call_nft(self, symbol: str, series_id: int, method: str, *args: Any) -> ScriptBuilder:
        return self.call_contract(f"{symbol}#{series_id}", method, *args)

    def _insert_method_args(self, args: tuple[Any, ...]) -> None:
        for arg in reversed(args):
            self._load_into_register(0, arg)
            self.emit_push(0)

    def _load_into_register(self, reg: int, value: Any) -> None:
        if value is None:
            self._fail("unsupported nil argument")
        elif isinstance(value, Address):
            self.emit_load(reg, value.prefixed_bytes(), VMType.BYTES)
        elif isinstance(value, str):
            self.emit_load_string(reg, value)
        elif isinstance(value, bool):
            self.emit_load_bool(reg, value)
        elif isinstance(value, bytes | bytearray):
            self.emit_load(reg, bytes(value), VMType.BYTES)
        elif isinstance(value, int):
            self.emit_load_number(reg, value)
        elif isinstance(value, datetime):
            self.emit_load_time(reg, value)
        elif isinstance(value, list | tuple):
            if reg > self.MAX_REGISTER_COUNT - 3:
                self._fail(f"array load needs three registers starting at {reg}")
                return
            self.emit(Opcode.CAST)
            self._byte(reg)
            self._byte(reg)
            self._byte(VMType.NONE)
            for index, item in enumerate(value):
                self._load_into_register(reg + 1, item)
                self._load_into_register(reg + 2, index)
                self.emit(Opcode.PUT)
                self._byte(reg + 1)
                self._byte(reg)
                self._byte(reg + 2)
        else:
            self._fail(f"unsupported type {type(value).__name__}")

    def _byte(self, value: int) -> ScriptBuilder:
        self._writer.write_u8(int(value))
        return self

    def _fail(self, message: str) -> ScriptBuilder:
        if self._error is None:
            self._error = BuilderError(message)
        return self
