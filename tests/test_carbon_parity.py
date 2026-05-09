from pathlib import Path

import pytest

from phantasma_py.carbon import (
    Bytes32,
    ChainConfig,
    GasConfig,
    IntX,
    MarketConfig,
    MarketConfigFlags,
    MarketSellTokenByIDArgs,
    MintNFTFeeOptions,
    MintPhantasmaNonFungibleArgs,
    PhantasmaNFTMintInfo,
    SmallString,
    TokenListing,
    TokensConfig,
    TokensConfigFlags,
    TxMsg,
    TxMsgBurnFungibleGasPayer,
    TxMsgMintFungible,
    TxMsgTransferFungible,
    TxMsgTransferFungibleGasPayer,
    TxType,
    VMDynamicVariable,
    VMType,
    build_mint_non_fungible_tx_and_sign,
    build_mint_non_fungible_tx_and_sign_hex,
    bytes32_from_phantasma_address,
    bytes32_from_public_key,
    check_token_symbol,
    deserialize,
    parse_mint_phantasma_non_fungible_result,
    serialize,
    sign_and_serialize_tx_msg_hex,
    unpack_nft_instance_id,
)
from phantasma_py.crypto import PhantasmaKeys
from phantasma_py.errors import BuilderError


def vector_hex(kind: str) -> str:
    for line in Path("tests/fixtures/carbon_vectors.tsv").read_text().splitlines():
        parts = line.split("\t")
        if parts[0] == kind:
            return parts[2]
    raise AssertionError(f"missing vector {kind}")


def repeated_bytes32(value: int) -> Bytes32:
    return Bytes32(bytes([value]) * 32)


def test_chain_and_gas_config_round_trip() -> None:
    chain = ChainConfig(
        version=1,
        reserved1=2,
        reserved2=3,
        reserved3=4,
        allowed_tx_types=0xAABBCCDD,
        expiry_window=60_000,
        block_rate_target=1_000,
    )
    assert serialize(chain).hex() == "01020304ddccbbaa60ea0000e8030000"
    assert deserialize(serialize(chain), ChainConfig) == chain

    gas = GasConfig(
        version=1,
        max_name_length=2,
        max_token_symbol_length=3,
        fee_shift=4,
        max_structure_size=5,
        fee_multiplier=6,
        gas_token_id=7,
        data_token_id=8,
        minimum_gas_offer=9,
        data_escrow_per_row=10,
        gas_fee_transfer=11,
        gas_fee_query=12,
        gas_fee_create_token_base=13,
        gas_fee_create_token_symbol=14,
        gas_fee_create_token_series=15,
        gas_fee_per_byte=16,
        gas_fee_register_name=17,
        gas_burn_ratio_mul=18,
        gas_burn_ratio_shift=19,
    )
    raw = serialize(gas)
    assert len(raw) == 113
    assert raw[:8].hex() == "0102030405000000"
    assert raw[-9:].hex() == "120000000000000013"
    assert deserialize(raw, GasConfig) == gas


def test_token_and_market_config_wire_formats() -> None:
    tokens_config = TokensConfig(TokensConfigFlags.REQUIRE_METADATA | TokensConfigFlags.ALLOW_EXPLICIT_NFT_META_ID_MINT)
    assert serialize(tokens_config).hex() == "11"
    assert deserialize(serialize(tokens_config), TokensConfig) == tokens_config

    default_market = MarketConfig()
    assert default_market.flags == MarketConfigFlags.PRICE_REQUIRED | MarketConfigFlags.ENFORCE_ROYALTIES
    assert deserialize(serialize(default_market), MarketConfig) == default_market

    seller = Bytes32(bytes(range(32)))
    listing = TokenListing(
        seller=seller,
        quote_token_id=2,
        price=IntX(123),
        start_date=10,
        end_date=20,
    )
    expected = (
        "00"
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
        "0200000000000000"
        "087b00000000000000"
        "0a00000000000000"
        "1400000000000000"
    )
    assert serialize(listing).hex() == expected
    assert deserialize(bytes.fromhex(expected), TokenListing) == listing


def test_token_and_market_call_args_round_trip() -> None:
    mint_args = MintPhantasmaNonFungibleArgs(
        token_id=9,
        address=repeated_bytes32(0x11),
        tokens=[PhantasmaNFTMintInfo(IntX(7), b"\xaa\xbb", b"\xcc")],
    )
    assert serialize(mint_args).hex() == (
        "0900000000000000"
        "1111111111111111111111111111111111111111111111111111111111111111"
        "01000000"
        "080700000000000000"
        "02000000aabb"
        "01000000cc"
    )
    assert deserialize(serialize(mint_args), MintPhantasmaNonFungibleArgs) == mint_args

    market_args = MarketSellTokenByIDArgs(
        from_address=repeated_bytes32(0x22),
        symbol=SmallString("ART"),
        instance_id=VMDynamicVariable(VMType.INT64, 7),
        quote_symbol=SmallString("SOUL"),
        price=IntX(12),
        end_date=13,
    )
    decoded = deserialize(serialize(market_args), MarketSellTokenByIDArgs)
    assert decoded == market_args


def test_carbon_address_and_signing_helpers_match_shared_vector() -> None:
    keys = PhantasmaKeys.from_wif("KwPpBSByydVKqStGHAnZzQofCqhDmD2bfRgc9BmZqM3ZmsdWJw4d")
    receiver = PhantasmaKeys.from_wif("KwVG94yjfVg1YKFyRxAGtug93wdRbmLnqqrFV6Yd2CiA9KZDAp4H")

    sender_bytes = bytes32_from_public_key(keys.public_key)
    assert bytes32_from_phantasma_address(keys.address) == sender_bytes

    msg = TxMsg(
        TxType.TRANSFER_FUNGIBLE,
        1_759_711_416_000,
        10_000_000,
        1_000,
        sender_bytes,
        SmallString("test-payload"),
        TxMsgTransferFungible(bytes32_from_public_key(receiver.public_key), 1, 100_000_000),
    )
    assert sign_and_serialize_tx_msg_hex(msg, keys).upper() == vector_hex("TX2")


def test_extra_tx_vectors_match_cs_go_ts_reference() -> None:
    keys = PhantasmaKeys.from_wif("KwPpBSByydVKqStGHAnZzQofCqhDmD2bfRgc9BmZqM3ZmsdWJw4d")
    receiver = PhantasmaKeys.from_wif("KwVG94yjfVg1YKFyRxAGtug93wdRbmLnqqrFV6Yd2CiA9KZDAp4H")
    sender_bytes = bytes32_from_public_key(keys.public_key)
    receiver_bytes = bytes32_from_public_key(receiver.public_key)

    cases = [
        (
            "04C04EF9B6990100008096980000000000E803000000000000"
            "F94A8E45BDF1E37A8466B951849E92D1BAF870F49D1D04CD204D0BC9FE430896"
            "0C746573742D7061796C6F6164"
            "D4C5061B81C4682B27A0CFC6459CD9D7892EB60A43F73DD1060B6C478AA7C3D8"
            "F94A8E45BDF1E37A8466B951849E92D1BAF870F49D1D04CD204D0BC9FE430896"
            "010000000000000000E1F50500000000",
            TxMsg(
                TxType.TRANSFER_FUNGIBLE_GAS_PAYER,
                1_759_711_416_000,
                10_000_000,
                1_000,
                sender_bytes,
                SmallString("test-payload"),
                TxMsgTransferFungibleGasPayer(receiver_bytes, sender_bytes, 1, 100_000_000),
            ),
        ),
        (
            "0BC04EF9B6990100008096980000000000E803000000000000"
            "F94A8E45BDF1E37A8466B951849E92D1BAF870F49D1D04CD204D0BC9FE430896"
            "0C746573742D7061796C6F6164"
            "0100000000000000"
            "F94A8E45BDF1E37A8466B951849E92D1BAF870F49D1D04CD204D0BC9FE430896"
            "0800E1F50500000000",
            TxMsg(
                TxType.BURN_FUNGIBLE_GAS_PAYER,
                1_759_711_416_000,
                10_000_000,
                1_000,
                sender_bytes,
                SmallString("test-payload"),
                TxMsgBurnFungibleGasPayer(1, sender_bytes, IntX(100_000_000)),
            ),
        ),
        (
            "09C04EF9B6990100008096980000000000E803000000000000"
            "F94A8E45BDF1E37A8466B951849E92D1BAF870F49D1D04CD204D0BC9FE430896"
            "0C746573742D7061796C6F6164"
            "0100000000000000"
            "D4C5061B81C4682B27A0CFC6459CD9D7892EB60A43F73DD1060B6C478AA7C3D8"
            "0800E1F50500000000",
            TxMsg(
                TxType.MINT_FUNGIBLE,
                1_759_711_416_000,
                10_000_000,
                1_000,
                sender_bytes,
                SmallString("test-payload"),
                TxMsgMintFungible(1, receiver_bytes, IntX(100_000_000)),
            ),
        ),
    ]
    for expected_hex, msg in cases:
        assert serialize(msg).hex().upper() == expected_hex
        assert serialize(deserialize(bytes.fromhex(expected_hex), TxMsg)).hex().upper() == expected_hex


def test_unpack_nft_instance_id_matches_reference_helper() -> None:
    assert unpack_nft_instance_id(0x0000000800000007) == (7, 8)


def test_mint_nft_signing_hex_helper_matches_raw_helper() -> None:
    keys = PhantasmaKeys.from_wif("KwPpBSByydVKqStGHAnZzQofCqhDmD2bfRgc9BmZqM3ZmsdWJw4d")
    receiver = bytes32_from_public_key(
        PhantasmaKeys.from_wif("KwVG94yjfVg1YKFyRxAGtug93wdRbmLnqqrFV6Yd2CiA9KZDAp4H").public_key
    )
    raw = build_mint_non_fungible_tx_and_sign(
        9,
        7,
        keys,
        receiver,
        b"\xaa",
        fees=MintNFTFeeOptions(),
        max_data=0,
        expiry=1_759_711_416_000,
    )
    encoded = build_mint_non_fungible_tx_and_sign_hex(
        9,
        7,
        keys,
        receiver,
        b"\xaa",
        fees=MintNFTFeeOptions(),
        max_data=0,
        expiry=1_759_711_416_000,
    )
    assert encoded == raw.hex()


def test_parse_mint_phantasma_non_fungible_result() -> None:
    first = repeated_bytes32(0x55)
    second = repeated_bytes32(0xAA)
    result_hex = f"02000000{first.hex()}0700000000000000{second.hex()}0800000000000000"
    parsed = parse_mint_phantasma_non_fungible_result(result_hex)
    assert parsed[0].phantasma_nft_id == first
    assert parsed[0].carbon_instance_id == 7
    assert parsed[1].phantasma_nft_id == second
    assert parsed[1].carbon_instance_id == 8


def test_token_symbol_validation_matches_carbon_rule() -> None:
    check_token_symbol("SOUL")
    with pytest.raises(BuilderError):
        check_token_symbol("SOUL2")
