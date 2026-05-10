from hashlib import sha256
from pathlib import Path

from phantasma_py.binary import BinaryWriter, big_int_to_vm_bytes, vm_bytes_to_big_int
from phantasma_py.errors import SerializationError
from phantasma_py.vm import ScriptBuilder, VMObject, VMType

CLASSIC_TYPE_NAMES = {
    VMType.NONE: "None",
    VMType.STRUCT: "Struct",
    VMType.BYTES: "Bytes",
    VMType.NUMBER: "Number",
    VMType.STRING: "String",
    VMType.TIMESTAMP: "Timestamp",
    VMType.BOOL: "Bool",
    VMType.ENUM: "Enum",
    VMType.OBJECT: "Object",
}

UNIT_COVERED_GEN2_FIXTURES = {
    "gen2_csharp_vm_bigint_binary.tsv",
    "gen2_csharp_vm_bigint_decimal.tsv",
    "gen2_csharp_vmobject_arraytype.tsv",
    "gen2_csharp_vmobject_asbool.tsv",
    "gen2_csharp_vmobject_asbytes.tsv",
    "gen2_csharp_vmobject_asnumber.tsv",
    "gen2_csharp_vmobject_asstring.tsv",
    "gen2_csharp_vmobject_cast_struct.tsv",
    "gen2_csharp_vmobject_serde.tsv",
}

LIVE_RUNNER_COVERED_GEN2_FIXTURES = {
    "gen2_csharp_vm_scriptcontext_ops.tsv",
    "gen2_csharp_vm_scriptcontext_unary.tsv",
}

NOT_SDK_UNIT_APPLICABLE_GEN2_FIXTURES = {
    "gen2_csharp_vm_bigint_narrow_int.tsv",
    "gen2_csharp_vm_bigint_ops.tsv",
    "gen2_csharp_vm_bigint_unary_ops.tsv",
}

GEN2_FIXTURE_SHA256 = {
    "gen2_csharp_vm_bigint_binary.tsv": "a5be05751b35de8b7b3578577bb2769073ac7a2ddea3eaf9503d76d0302fa464",
    "gen2_csharp_vm_bigint_decimal.tsv": "1bede4198883018817d94eceefe4e7b70a9f5c96c9d60d57481990ad21b027a9",
    "gen2_csharp_vm_bigint_narrow_int.tsv": "b82315b4483c23ee7e3e9943b5c41cf8daf12c627c6e12f30b735ad7dbde1445",
    "gen2_csharp_vm_bigint_ops.tsv": "997f3a935393358a89c7be785176e8528535111994bc5193c7d7ddc2429aa3d3",
    "gen2_csharp_vm_bigint_unary_ops.tsv": "53719de8a1528897a083401aaad251cdb3e9e201f8639d29cd3708beeda93ea7",
    "gen2_csharp_vm_scriptcontext_ops.tsv": "c87e4a5ec075b8efc0abe88a551ae8fe505df04167cb0e4f2714768c0a1e917f",
    "gen2_csharp_vm_scriptcontext_unary.tsv": "7198d33a84bd61c671dc1871f2b56e232748c41d69e957e8f994cd2dc9b5922c",
    "gen2_csharp_vmobject_arraytype.tsv": "f6b7ce9cd92f464d260018ffb1a0ab01202ca908cf915dead3295e8270ddf532",
    "gen2_csharp_vmobject_asbool.tsv": "a2979cc7eccd22760de82f8401de4b8b41c45fedf09b91a94871d3a3051c85d5",
    "gen2_csharp_vmobject_asbytes.tsv": "dd326e18c94e2e116705893f742c708cfb1cd7b96c8a40a2ab6637b39ae409b9",
    "gen2_csharp_vmobject_asnumber.tsv": "986cfc21658c66b04c1ffaaa7bb9fa08bc9a3acd929276d0d2496ba43c43bf69",
    "gen2_csharp_vmobject_asstring.tsv": "eb14408b7e65fc417bf1bbfe4fb1e87c3d06d28734c7c25514a806f41fceede6",
    "gen2_csharp_vmobject_cast_struct.tsv": "1580a9ec312619a7e2632076073ae80d57dcfc3defc0ef7b4876da34c0e231af",
    "gen2_csharp_vmobject_serde.tsv": "0c74c90e83c5c20bed48b1d52ca5489d15a7c4f67874184c1d0a4f708ce5e42f",
}


def test_phantasma_bigint_vectors_match_vm_writer_and_script_builder() -> None:
    for line_number, line in enumerate(Path("tests/fixtures/phantasma_bigint_vectors.tsv").read_text().splitlines()):
        if line_number == 0 or not line:
            continue
        number, pha, csharp = line.split("\t")
        value = int(number)
        expected_vm_bytes = _decimal_bytes(pha)
        expected_csharp_bytes = _decimal_bytes(csharp)

        vm_bytes = big_int_to_vm_bytes(value)
        assert vm_bytes == expected_vm_bytes, number
        assert vm_bytes_to_big_int(vm_bytes) == value, number

        writer = BinaryWriter()
        writer.write_big_integer(value)
        expected_writer = BinaryWriter()
        expected_writer.write_var_bytes(expected_vm_bytes)
        assert writer.bytes() == expected_writer.bytes(), number

        builder = ScriptBuilder.begin()
        builder.emit_load_number(0, value)
        script = builder.to_script()
        assert script[0] == 13, number
        assert script[1] == 0, number
        assert script[2] == VMType.NUMBER, number
        assert script[3] == len(expected_csharp_bytes), number
        assert script[4:] == expected_csharp_bytes, number


def test_gen2_fixture_manifest_is_explicit() -> None:
    discovered = {path.name for path in Path("tests/fixtures").glob("gen2_csharp_*.tsv")}
    classified = UNIT_COVERED_GEN2_FIXTURES | LIVE_RUNNER_COVERED_GEN2_FIXTURES | NOT_SDK_UNIT_APPLICABLE_GEN2_FIXTURES
    assert discovered == classified


def test_gen2_fixture_hashes_are_locked() -> None:
    assert set(GEN2_FIXTURE_SHA256) == {
        *UNIT_COVERED_GEN2_FIXTURES,
        *LIVE_RUNNER_COVERED_GEN2_FIXTURES,
        *NOT_SDK_UNIT_APPLICABLE_GEN2_FIXTURES,
    }
    for name, expected in GEN2_FIXTURE_SHA256.items():
        assert sha256((Path("tests/fixtures") / name).read_bytes()).hexdigest() == expected, name


def test_vmobject_as_string_matches_gen2_csharp_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asstring.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        assert outcome == "ok", case_id
        assert _object_from_fixture(source_kind, payload).as_string() == expected, case_id


def test_vmobject_string_as_number_matches_gen2_csharp_decimal_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vm_bigint_decimal.tsv"):
        case_id, input_text, outcome, expected, *_ = parts
        result = _call_result(lambda input_text=input_text: VMObject(VMType.STRING, input_text).as_number())
        if outcome == "ok":
            assert result == int(expected), case_id
        else:
            assert isinstance(result, Exception), case_id


def test_vmobject_as_bytes_matches_gen2_csharp_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asbytes.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).as_bytes()
        )
        if outcome == "ok":
            assert result == bytes.fromhex(expected), case_id
        else:
            assert isinstance(result, Exception), case_id


def test_vmobject_as_bool_matches_gen2_csharp_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asbool.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).as_bool()
        )
        if outcome == "ok":
            assert str(result).lower() == expected, case_id
        else:
            assert isinstance(result, Exception), case_id


def test_vmobject_array_type_matches_gen2_csharp_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_arraytype.tsv"):
        case_id, source_kind, _source_type, payload, expected = parts
        actual = _object_from_fixture(source_kind, payload).array_type()
        assert CLASSIC_TYPE_NAMES[actual] == expected, case_id


def test_vmobject_serde_matches_gen2_csharp_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_serde.tsv"):
        case_id, source_kind, _source_type, payload, serialized_hex, roundtrip_type, descriptor = parts
        obj = _object_from_fixture(source_kind, payload)
        assert obj.to_bytes().hex() == serialized_hex, case_id

        roundtrip = VMObject.from_bytes(bytes.fromhex(serialized_hex))
        assert CLASSIC_TYPE_NAMES[roundtrip.type] == roundtrip_type, case_id
        assert _object_descriptor(roundtrip) == descriptor, case_id


def test_vmobject_cast_struct_matches_gen2_csharp_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_cast_struct.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected_type, descriptor, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).cast_to(
                VMType.STRUCT
            )
        )
        if outcome == "ok":
            assert isinstance(result, VMObject), case_id
            assert CLASSIC_TYPE_NAMES[result.type] == expected_type, case_id
            assert _object_descriptor(result) == descriptor, case_id
        else:
            assert isinstance(result, Exception), case_id


def test_vmobject_cast_to_common_targets_matches_gen2_conversion_fixtures() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asstring.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).cast_to(
                VMType.STRING
            )
        )
        if outcome == "ok":
            assert isinstance(result, VMObject), case_id
            assert result.type == VMType.STRING, case_id
            assert result.data == expected, case_id
        else:
            assert isinstance(result, Exception), case_id

    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asbytes.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).cast_to(
                VMType.BYTES
            )
        )
        if outcome == "ok":
            assert isinstance(result, VMObject), case_id
            assert result.type == VMType.BYTES, case_id
            assert result.data == bytes.fromhex(expected), case_id
        else:
            assert isinstance(result, Exception), case_id

    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asnumber.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).cast_to(
                VMType.NUMBER
            )
        )
        if outcome == "ok":
            assert isinstance(result, VMObject), case_id
            assert result.type == VMType.NUMBER, case_id
            assert result.data == int(expected), case_id
        else:
            assert isinstance(result, Exception), case_id

    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_asbool.tsv"):
        case_id, source_kind, _source_type, payload, outcome, expected, *_ = parts
        result = _call_result(
            lambda source_kind=source_kind, payload=payload: _object_from_fixture(source_kind, payload).cast_to(
                VMType.BOOL
            )
        )
        if outcome == "ok":
            assert isinstance(result, VMObject), case_id
            assert result.type == VMType.BOOL, case_id
            assert result.data == (expected == "true"), case_id
        else:
            assert isinstance(result, Exception), case_id


def test_vmobject_serde_fixture_payloads_reject_truncation() -> None:
    for parts in _fixture_rows("tests/fixtures/gen2_csharp_vmobject_serde.tsv"):
        case_id, *_prefix, serialized_hex, _roundtrip_type, _descriptor = parts
        payload = bytes.fromhex(serialized_hex)
        assert payload
        result = _call_result(lambda payload=payload: VMObject.from_bytes(payload[:-1]))
        assert isinstance(result, Exception), case_id


def _decimal_bytes(value: str) -> bytes:
    return bytes(int(part) for part in value.split()) if value.strip() else b""


def _fixture_rows(path: str) -> list[list[str]]:
    rows: list[list[str]] = []
    width = 0
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if line.startswith("case_id\t"):
            width = len(parts)
            continue
        if width and len(parts) < width:
            parts.extend([""] * (width - len(parts)))
        rows.append(parts)
    return rows


def _object_from_fixture(source_kind: str, payload: str) -> VMObject:
    if source_kind == "serialized_vmobject":
        return VMObject.from_bytes(bytes.fromhex(payload))
    if source_kind == "empty":
        return VMObject(VMType.NONE)
    if source_kind == "string":
        return VMObject(VMType.STRING, payload)
    if source_kind == "bytes":
        return VMObject(VMType.BYTES, bytes.fromhex(payload))
    if source_kind == "bool":
        return VMObject(VMType.BOOL, payload == "true")
    if source_kind == "enum":
        return VMObject(VMType.ENUM, int(payload))
    if source_kind == "timestamp":
        return VMObject(VMType.TIMESTAMP, int(payload))
    if source_kind == "number":
        return VMObject(VMType.NUMBER, int(payload))
    if source_kind == "object":
        return VMObject(VMType.OBJECT, bytes.fromhex(payload))
    if source_kind == "struct":
        return VMObject(
            VMType.STRUCT,
            {
                VMObject(VMType.STRING, "name"): VMObject(VMType.STRING, "neo"),
                VMObject(VMType.STRING, "count"): VMObject(VMType.NUMBER, 7),
            },
        )
    raise AssertionError(f"unsupported fixture source kind: {source_kind}")


def _object_descriptor(obj: VMObject) -> str:
    if obj.type == VMType.NONE:
        return "None"
    if obj.type == VMType.STRUCT:
        return f"Struct:{obj.to_bytes().hex()}"
    if obj.type == VMType.BYTES:
        return f"Bytes:{bytes(obj.data).hex()}"
    if obj.type == VMType.NUMBER:
        return f"Number:{obj.data}"
    if obj.type == VMType.STRING:
        return f"String:{obj.data}"
    if obj.type == VMType.TIMESTAMP:
        return f"Timestamp:{obj.data}"
    if obj.type == VMType.BOOL:
        return f"Bool:{str(obj.data).lower()}"
    if obj.type == VMType.ENUM:
        return f"Enum:{obj.data}"
    if obj.type == VMType.OBJECT and len(bytes(obj.data)) == 34:
        return f"Object.Address:{bytes(obj.data).hex()}"
    if obj.type == VMType.OBJECT and len(bytes(obj.data)) == 32:
        return f"Object.Hash:{bytes(obj.data).hex()}"
    if obj.type == VMType.OBJECT:
        return f"Object:{bytes(obj.data).hex()}"
    raise AssertionError(f"unsupported object type: {obj.type}")


def _call_result(action):
    try:
        return action()
    except (SerializationError, UnicodeDecodeError, ValueError) as exc:
        return exc
