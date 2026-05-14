import pytest

from phantasma_py.carbon import (
    BurnFungibleArgs,
    BurnNonFungibleArgs,
    Bytes32,
    CarbonReader,
    CreateMintedTokenSeriesArgs,
    CreateSeriesFeeOptions,
    CreateTokenFeeOptions,
    CreateTokenSeriesArgs,
    IntX,
    MintFungibleArgs,
    MintNFTFeeOptions,
    MintPhantasmaNonFungibleArgs,
    ModuleID,
    PhantasmaNFTMintInfo,
    PhantasmaNFTMintResult,
    SeriesInfo,
    SmallString,
    TokenContractMethod,
    TokenFlags,
    TokenSchemaField,
    TokenSchemas,
    TransferFungibleArgs,
    TransferNonFungibleArgs,
    TxMsgCall,
    TxType,
    UpdateSeriesMetadataArgs,
    UpdateTokenMetadataArgs,
    VMDynamicStruct,
    VMDynamicVariable,
    VMNamedDynamicVariable,
    VMNamedVariableSchema,
    VMStructArray,
    VMStructFlags,
    VMStructSchema,
    VMType,
    build_and_serialize_token_schemas,
    build_mint_phantasma_non_fungible_single_tx,
    build_mint_phantasma_non_fungible_tx,
    build_nft_rom,
    build_phantasma_nft_public_mint_schema,
    build_phantasma_nft_rom,
    build_series_info,
    build_token_info,
    build_token_metadata,
    build_token_schemas_from_fields,
    build_token_series_metadata,
    check_token_symbol,
    deserialize,
    get_nft_address,
    parse_create_token_result,
    parse_create_token_series_result,
    parse_mint_non_fungible_result,
    parse_mint_phantasma_non_fungible_result,
    prepare_standard_token_schemas,
    serialize,
    serialize_token_schemas,
    serialize_token_schemas_hex,
    token_schemas_from_json,
    verify_token_schemas,
    vm_type_from_string,
    vm_type_name,
)
from phantasma_py.errors import BuilderError, PhantasmaError

SAMPLE_PNG_ICON_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)


def repeated_bytes32(value: int) -> Bytes32:
    return Bytes32(bytes([value]) * 32)


def vector_series_info() -> SeriesInfo:
    return SeriesInfo(3, 9, repeated_bytes32(0x33), bytes.fromhex("aabb"), VMStructSchema(), VMStructSchema())


def standard_nft_metadata() -> list[tuple[str, object]]:
    return [
        ("name", "My NFT #1"),
        ("description", "This is my first NFT!"),
        ("imageURL", "images-assets.nasa.gov/image/PIA13227/PIA13227~orig.jpg"),
        ("infoURL", "https://images.nasa.gov/details/PIA13227"),
        ("royalties", 10_000_000),
    ]


def build_schema(fields: list[tuple[str, VMType]]) -> VMStructSchema:
    return VMStructSchema([VMNamedVariableSchema.make(name, vm_type) for name, vm_type in fields])


def assert_blob_vector(expected_hex: str, value: object, cls: type[object]) -> None:
    # Reference vectors are copied from Go's token call-args tests and must round-trip byte-for-byte.
    raw = bytes.fromhex(expected_hex)
    assert serialize(value).hex().upper() == expected_hex
    assert deserialize(raw, cls) == value
    assert serialize(deserialize(raw, cls)).hex().upper() == expected_hex


def test_token_call_args_vectors_match_go_reference() -> None:
    # Token module ABI structures cover create/mint/transfer/burn calls shared across SDKs.
    one = repeated_bytes32(0x11)
    two = repeated_bytes32(0x22)
    four = repeated_bytes32(0x44)

    cases: list[tuple[str, object, type[object]]] = [
        (
            "010000000000000011111111111111111111111111111111111111111111111111111111111111110800E1F50500000000",
            MintFungibleArgs(1, one, IntX(100_000_000)),
            MintFungibleArgs,
        ),
        (
            "1111111111111111111111111111111111111111111111111111111111111111"
            "2222222222222222222222222222222222222222222222222222222222222222"
            "0100000000000000"
            "0800E1F50500000000",
            TransferFungibleArgs(one, two, 1, IntX(100_000_000)),
            TransferFungibleArgs,
        ),
        (
            "1111111111111111111111111111111111111111111111111111111111111111"
            "2222222222222222222222222222222222222222222222222222222222222222"
            "0100000000000000"
            "0200000007000000000000000800000000000000",
            TransferNonFungibleArgs(one, two, 1, [7, 8]),
            TransferNonFungibleArgs,
        ),
        (
            "010000000000000022222222222222222222222222222222222222222222222222222222222222220800E1F50500000000",
            BurnFungibleArgs(1, two, IntX(100_000_000)),
            BurnFungibleArgs,
        ),
        (
            "0100000000000000"
            "2222222222222222222222222222222222222222222222222222222222222222"
            "0200000007000000000000000800000000000000",
            BurnNonFungibleArgs(1, two, [7, 8]),
            BurnNonFungibleArgs,
        ),
        (
            "0900000000000000" + "0300000009000000" + "33" * 32 + "02000000AABB" + "0000000000" * 2,
            CreateTokenSeriesArgs(9, vector_series_info()),
            CreateTokenSeriesArgs,
        ),
        (
            "0900000000000000"
            "0300000009000000"
            + "33" * 32
            + "02000000AABB"
            + "0000000000" * 2
            + "44" * 32
            + "0200000002000000010200000000"
            + "010000000100000003",
            CreateMintedTokenSeriesArgs(9, vector_series_info(), four, [b"\x01\x02", b""], [b"\x03"]),
            CreateMintedTokenSeriesArgs,
        ),
        (
            "090000000000000001000000016E16616C70686100",
            UpdateTokenMetadataArgs(9, VMDynamicStruct([VMNamedDynamicVariable.make("n", VMType.STRING, "alpha")])),
            UpdateTokenMetadataArgs,
        ),
        (
            "09000000000000000700000004000000DEADBEEF",
            UpdateSeriesMetadataArgs(9, 7, bytes.fromhex("deadbeef")),
            UpdateSeriesMetadataArgs,
        ),
        (
            "0900000000000000"
            + "44" * 32
            + "02000000"
            + "082A0000000000000002000000AABB01000000CC"
            + "082B000000000000000000000002000000DDEE",
            MintPhantasmaNonFungibleArgs(
                9,
                four,
                [
                    PhantasmaNFTMintInfo(IntX(42), bytes.fromhex("aabb"), b"\xcc"),
                    PhantasmaNFTMintInfo(IntX(43), b"", bytes.fromhex("ddee")),
                ],
            ),
            MintPhantasmaNonFungibleArgs,
        ),
        ("55" * 32 + "7B00000000000000", PhantasmaNFTMintResult(repeated_bytes32(0x55), 123), PhantasmaNFTMintResult),
    ]

    for expected_hex, value, cls in cases:
        assert_blob_vector(expected_hex, value, cls)


def test_token_result_parsers_match_reference_behaviour() -> None:
    # Result helpers parse successful RPC blobs and reject malformed hex or truncated payloads.
    assert parse_create_token_result("0900000000000000") == 9
    assert parse_create_token_series_result("07000000") == 7
    assert parse_mint_non_fungible_result(9, "0200000007000000000000000800000000000000") == [
        get_nft_address(9, 7),
        get_nft_address(9, 8),
    ]

    payload = "02000000" + "55" * 32 + "0700000000000000" + "2A" + "00" * 30 + "80" + "0800000000000000"
    parsed = parse_mint_phantasma_non_fungible_result(payload)
    assert parsed[0].carbon_instance_id == 7
    assert parsed[1].phantasma_nft_id == Bytes32(bytes.fromhex("2A" + "00" * 30 + "80"))

    with pytest.raises(PhantasmaError):
        parse_mint_non_fungible_result(9, "not-hex")
    with pytest.raises(PhantasmaError):
        parse_create_token_result("01020304")
    with pytest.raises(PhantasmaError):
        parse_create_token_series_result("010203")
    with pytest.raises(PhantasmaError):
        parse_mint_non_fungible_result(9, "01000000")
    with pytest.raises(PhantasmaError):
        parse_mint_phantasma_non_fungible_result("01000000")


def test_token_builder_validation_matches_reference_sdks() -> None:
    # Token builders reject malformed public inputs before invalid Carbon payloads can be produced.
    metadata = build_token_metadata(
        {
            "name": "My test token!",
            "icon": SAMPLE_PNG_ICON_DATA_URI,
            "url": "http://example.com",
            "description": "My test token description",
        }
    )
    schemas = prepare_standard_token_schemas(False)

    for symbol in ("", "A" * 256, "AB1", "AbC"):
        with pytest.raises(BuilderError):
            check_token_symbol(symbol)
        with pytest.raises(BuilderError):
            build_token_info(symbol, IntX(0), is_nft=False, decimals=0, owner=Bytes32(), metadata=metadata)

    with pytest.raises(BuilderError):
        build_token_info("TEST", IntX(0), is_nft=False, decimals=0, owner=Bytes32(), metadata=None)  # type: ignore[arg-type]
    assert (
        build_token_info("FUNGIBLE", IntX(0), is_nft=False, decimals=8, owner=Bytes32(), metadata=metadata).flags
        == TokenFlags.NONE
    )
    with pytest.raises(BuilderError):
        build_token_info(
            "NFT",
            IntX(9_223_372_036_854_775_808),
            is_nft=True,
            decimals=0,
            owner=Bytes32(),
            metadata=metadata,
            token_schemas=serialize_token_schemas(schemas),
        )
    with pytest.raises(BuilderError):
        build_token_info("NFT", IntX(0), is_nft=True, decimals=0, owner=Bytes32(), metadata=metadata)


def test_token_metadata_and_schema_validation() -> None:
    # Metadata and schema validators catch missing, mistyped and case-mismatched mandatory fields.
    def metadata_fields(icon: str) -> dict[str, str]:
        return {"name": "T", "icon": icon, "url": "http://example.com", "description": "D"}

    with pytest.raises(BuilderError):
        build_token_metadata({})
    with pytest.raises(BuilderError):
        build_token_metadata(metadata_fields("not-a-data-uri"))
    with pytest.raises(BuilderError):
        build_token_metadata(metadata_fields("data:image/png;base64,!!!!"))
    with pytest.raises(BuilderError):
        build_token_metadata(metadata_fields("data:image/png;base64,"))
    with pytest.raises(BuilderError):
        build_token_metadata(metadata_fields("data:image/svg+xml;base64,PHN2Zy8+"))
    with pytest.raises(BuilderError):
        build_token_metadata(metadata_fields("data:image/gif;base64,R0lGODlhAQABAAAAACw="))
    for icon in (
        SAMPLE_PNG_ICON_DATA_URI,
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ==",
        "data:image/webp;base64,UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA",
    ):
        assert build_token_metadata(metadata_fields(icon))

    verify_token_schemas(prepare_standard_token_schemas(False))
    with pytest.raises(BuilderError, match="mandatory metadata field not found: name"):
        verify_token_schemas(
            TokenSchemas(
                build_schema([("_i", VMType.INT256), ("mode", VMType.INT8), ("rom", VMType.BYTES)]),
                build_schema([("_i", VMType.INT256), ("rom", VMType.BYTES)]),
                VMStructSchema(),
            )
        )
    with pytest.raises(BuilderError, match="type mismatch for name field"):
        verify_token_schemas(TokenSchemas(build_schema([("name", VMType.INT32)]), VMStructSchema(), VMStructSchema()))
    with pytest.raises(BuilderError, match="case mismatch for name field"):
        verify_token_schemas(TokenSchemas(build_schema([("Name", VMType.STRING)]), VMStructSchema(), VMStructSchema()))


def test_metadata_builders_validate_schema_inputs() -> None:
    # ROM builders enforce exact metadata names, required fields, bytes, fixed bytes and nested structs.
    schemas = prepare_standard_token_schemas(False)
    with pytest.raises(BuilderError, match="phantasma_series_id is required"):
        build_series_info(None, 1, 1, Bytes32())  # type: ignore[arg-type]
    with pytest.raises(BuilderError, match="phantasma_series_id is required"):
        build_token_series_metadata(schemas.series_metadata, None, [])  # type: ignore[arg-type]
    with pytest.raises(BuilderError, match="phantasma_nft_id is required"):
        build_nft_rom(schemas.rom, None, standard_nft_metadata())  # type: ignore[arg-type]
    with pytest.raises(BuilderError, match="phantasma_series_id is required"):
        build_mint_phantasma_non_fungible_single_tx(9, None, Bytes32(), Bytes32(), b"", b"", MintNFTFeeOptions())  # type: ignore[arg-type]
    with pytest.raises(BuilderError, match='metadata field "name" is mandatory'):
        build_nft_rom(schemas.rom, 1, [])
    with pytest.raises(BuilderError, match="incorrect case"):
        build_nft_rom(schemas.rom, 1, [("Name", "wrong case")])
    with pytest.raises(BuilderError, match="must be a byte array or hex string"):
        build_token_series_metadata(schemas.series_metadata, 1, [("rom", 7)])

    nested_schema = VMStructSchema([VMNamedVariableSchema.make("innerName", VMType.STRING)])
    custom_schema = VMStructSchema(
        [
            VMNamedVariableSchema.make("_i", VMType.INT256),
            VMNamedVariableSchema.make("rom", VMType.BYTES),
            VMNamedVariableSchema.make("details", VMType.STRUCT, nested_schema),
            VMNamedVariableSchema.make("roots", VMType.ARRAY_BYTES32),
        ]
    )
    with pytest.raises(BuilderError, match="unknown property"):
        build_nft_rom(custom_schema, 1, [("details", {"innerName": "demo", "extra": "oops"}), ("roots", [])])
    with pytest.raises(BuilderError, match="exactly 32 bytes"):
        build_nft_rom(custom_schema, 1, [("details", {"innerName": "demo"}), ("roots", ["00"])])

    scalar_schema = VMStructSchema(
        [
            VMNamedVariableSchema.make("_i", VMType.INT256),
            VMNamedVariableSchema.make("rom", VMType.BYTES),
            VMNamedVariableSchema.make("payload", VMType.BYTES),
            VMNamedVariableSchema.make("royalties", VMType.INT32),
            VMNamedVariableSchema.make("roots", VMType.ARRAY_BYTES32),
        ]
    )
    rom = build_nft_rom(
        scalar_schema,
        1,
        [
            ("payload", "0x0a0b"),
            ("royalties", 0xFFFFFFFF),
            ("roots", ["11" * 32]),
        ],
    )
    decoded = VMDynamicStruct.read_with_schema(scalar_schema, CarbonReader(rom))
    assert decoded.get("payload").data == b"\x0a\x0b"
    assert decoded.get("royalties").data == -1
    assert decoded.get("roots").data == [Bytes32(bytes([0x11]) * 32)]
    with pytest.raises(BuilderError, match="byte array or hex string"):
        build_nft_rom(scalar_schema, 1, [("payload", "xyz"), ("royalties", 0), ("roots", [])])
    with pytest.raises(BuilderError, match="royalties"):
        build_nft_rom(scalar_schema, 1, [("payload", b""), ("royalties", 1 << 32), ("roots", [])])


def test_array_struct_metadata_round_trips_with_schema() -> None:
    # Array-of-struct metadata uses the shared VmStructArray shape, including schema-bound reads.
    item_schema = VMStructSchema([VMNamedVariableSchema.make("name", VMType.STRING)])
    schema = VMStructSchema(
        [
            VMNamedVariableSchema.make("_i", VMType.INT256),
            VMNamedVariableSchema.make("rom", VMType.BYTES),
            VMNamedVariableSchema.make("items", VMType.ARRAY_STRUCT, item_schema),
        ]
    )
    rom = build_nft_rom(schema, 1, [("items", [{"name": "one"}, {"name": "two"}])])
    decoded = VMDynamicStruct.read_with_schema(schema, CarbonReader(rom))
    value = decoded.get("items")
    assert isinstance(value, VMDynamicVariable)
    assert isinstance(value.data, VMStructArray)
    assert [item.get("name").data for item in value.data.structs if item.get("name") is not None] == ["one", "two"]


def test_phantasma_nft_public_mint_rom_and_tx_helpers() -> None:
    # Deterministic Phantasma NFT minting omits chain-owned `_i` and nested `rom` fields from caller ROM.
    schemas = prepare_standard_token_schemas(False)
    rom = build_phantasma_nft_rom(schemas.rom, standard_nft_metadata())
    public_schema = build_phantasma_nft_public_mint_schema(schemas.rom)
    decoded = VMDynamicStruct.read_with_schema(public_schema, CarbonReader(rom))
    assert decoded.get("name").data == "My NFT #1"
    assert decoded.get("description").data == "This is my first NFT!"
    assert decoded.get("_i") is None
    assert decoded.get("rom") is None

    for field_name in ("_i", "rom", "_I", "ROM"):
        with pytest.raises(BuilderError, match="reserved"):
            build_phantasma_nft_rom(schemas.rom, [*standard_nft_metadata(), (field_name, b"\x01")])

    sender = repeated_bytes32(0x11)
    receiver = repeated_bytes32(0x22)
    tx = build_mint_phantasma_non_fungible_single_tx(42, 777, sender, receiver, rom, b"", MintNFTFeeOptions(), 123, 999)
    assert tx.type == TxType.CALL
    assert tx.expiry == 999
    assert tx.max_data == 123
    assert tx.gas_from == sender
    assert isinstance(tx.msg, TxMsgCall)
    assert tx.msg.module_id == ModuleID.TOKEN
    assert tx.msg.method_id == TokenContractMethod.MINT_PHANTASMA_NON_FUNGIBLE
    args = deserialize(tx.msg.args, MintPhantasmaNonFungibleArgs)
    assert isinstance(args, MintPhantasmaNonFungibleArgs)
    assert args.token_id == 42
    assert args.address == receiver
    assert len(args.tokens) == 1
    assert args.tokens[0].phantasma_series_id == IntX(777)
    assert args.tokens[0].rom == rom
    assert args.tokens[0].ram == b""


def test_token_schema_json_helpers_match_reference_shape() -> None:
    # Schema JSON helpers use the same public keys and VM type names as TS/C#/Go.
    parsed = token_schemas_from_json(
        """
        {
          "seriesMetadata": [{"name": "collection", "type": "String"}],
          "rom": [
            {"name": "name", "type": "String"},
            {"name": "description", "type": "String"},
            {"name": "imageURL", "type": "String"},
            {"name": "infoURL", "type": "String"},
            {"name": "royalties", "type": "Int32"},
            {"name": "rarity", "type": "Int32"}
          ],
          "ram": []
        }
        """
    )
    verify_token_schemas(parsed)
    assert parsed.series_metadata.fields[-1].name.value == "collection"
    assert parsed.rom.fields[-1].schema.type == VMType.INT32
    assert parsed.ram.flags == VMStructFlags.DYNAMIC_EXTRAS
    assert serialize_token_schemas_hex(parsed) == serialize_token_schemas(parsed).hex().upper()
    assert build_and_serialize_token_schemas(None) == serialize_token_schemas(prepare_standard_token_schemas(False))
    assert (
        build_token_schemas_from_fields(
            [TokenSchemaField("collection", VMType.STRING)],
            [
                ("name", "String"),
                ("description", "String"),
                ("imageURL", "String"),
                ("infoURL", "String"),
                ("royalties", "Int32"),
                ("rarity", "Int32"),
            ],
            [],
        )
        == parsed
    )
    assert vm_type_from_string("ArrayBytes32") == VMType.ARRAY_BYTES32
    assert vm_type_name(VMType.ARRAY_BYTES32) == "Array_Bytes32"
    with pytest.raises(BuilderError, match="ram must be an array"):
        token_schemas_from_json("""{"seriesMetadata": [], "rom": []}""")
    with pytest.raises(BuilderError, match="unknown VM type"):
        token_schemas_from_json("""{"seriesMetadata": [], "rom": [], "ram": [{"name": "bad", "type": "Nope"}]}""")


def test_reader_length_bounds_and_fee_defaults_match_reference_helpers() -> None:
    # Length-prefixed result readers reject impossible allocations; fee options produce non-zero safe defaults.
    with pytest.raises(PhantasmaError, match="exceeds remaining bytes"):
        parse_mint_non_fungible_result(9, "FFFFFF7F")
    assert CreateTokenFeeOptions().calculate_max_gas_for_symbol(SmallString("TOKEN")) > 0
    assert CreateSeriesFeeOptions().calculate_max_gas() > 0
    assert MintNFTFeeOptions().calculate_max_gas() > 0


def test_fee_options_scale_only_count_sensitive_mint_fees() -> None:
    assert MintNFTFeeOptions(gas_fee_base=10, fee_multiplier=1_000).calculate_max_gas(3) == 30_000
    assert (
        MintNFTFeeOptions(gas_fee_base=10, fee_multiplier=1_000).calculate_max_gas(
            [PhantasmaNFTMintInfo(IntX(1), b"", b""), PhantasmaNFTMintInfo(IntX(2), b"", b"")]
        )
        == 20_000
    )
    with pytest.raises(ValueError, match="count must be a positive integer"):
        MintNFTFeeOptions().calculate_max_gas([])

    series_fees = CreateSeriesFeeOptions(gas_fee_base=10, gas_fee_create_series_base=20, fee_multiplier=30)
    assert series_fees.calculate_max_gas() == 900
    assert series_fees.calculate_max_gas(1) == 900
    with pytest.raises(ValueError, match="not count-sensitive"):
        series_fees.calculate_max_gas(2)

    sender = repeated_bytes32(0x11)
    receiver = repeated_bytes32(0x22)
    tokens = [
        PhantasmaNFTMintInfo(IntX(1), b"\x01", b""),
        PhantasmaNFTMintInfo(IntX(2), b"\x02", b""),
        PhantasmaNFTMintInfo(IntX(3), b"\x03", b""),
    ]
    tx = build_mint_phantasma_non_fungible_tx(
        42, sender, receiver, tokens, MintNFTFeeOptions(gas_fee_base=10, fee_multiplier=1_000), 123, 999
    )
    assert tx.max_gas == 30_000
    with pytest.raises(ValueError, match="count must be a positive integer"):
        build_mint_phantasma_non_fungible_tx(42, sender, receiver, [], MintNFTFeeOptions(), 123, 999)
