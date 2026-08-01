"""Typed extended-event decoding: kind dispatch, per-method argument dispatch, raw fallbacks.

Live fixtures were captured from https://devnet.phantasma.info/rpc on 2026-08-01 via
getBlockByHeight("main", <height>); the height is stated on each test. Long hex payloads (contract
scripts, ABIs, ROMs) are truncated to keep the fixtures readable - the field set, the field types
and every other value are verbatim. Shape-only fixtures for the event kinds without a capturable
live sample (token and market events) mirror the node's emission sites in
RpcEventBuilder.TokenEvents.cs / RpcEventBuilder.MarketEvents.cs, whose serializer settings
(camelCase, enum names as strings, nulls omitted) are the same ones verified live on the
special-resolution family.
"""

from typing import Any

import pytest

from phantasma_py.extended_events import (
    EventExResult,
    MarketOrderData,
    SpecialResolutionCall,
    SpecialResolutionData,
    TokenCreateData,
    TokenSeriesCreateData,
    UnknownEventData,
)
from phantasma_py.special_resolution_arguments import (
    ARGUMENT_SHAPES,
    AddressArguments,
    BalanceArguments,
    BurnFungibleArguments,
    BurnNonFungibleArguments,
    ChainConfigArguments,
    CreateMintedTokenSeriesArguments,
    CreateTokenArguments,
    DeployContractArguments,
    ExecuteScriptArguments,
    GasConfigArguments,
    ImportContractsArguments,
    MetadataArguments,
    MintFungibleArguments,
    MintNonFungibleArguments,
    MintPhantasmaNonFungibleArguments,
    NameArguments,
    NestedResolutionArguments,
    NodeConfigArguments,
    NonFungibleInfoArguments,
    NonFungibleInfoByRomIdArguments,
    PhantasmaVmConfigArguments,
    RawArguments,
    RegisterNameArguments,
    RegisterTokenContractArguments,
    RepairSeriesArguments,
    RepairTokenArguments,
    SeriesInfoByMetaIdArguments,
    SymbolArguments,
    TokenReferenceArguments,
    TokensConfigArguments,
    TokenSeriesArguments,
    TokenSeriesReferenceArguments,
    TransferFungibleArguments,
    TransferNonFungibleArguments,
    UnrecognizedArguments,
    UpdateSeriesMetadataArguments,
    UpdateTokenMetadataArguments,
)

# Devnet block 8,736,259: one SpecialResolution event whose single call is
# phantasma_vm.RepairSeries with 3,649 supplements and 8,370 repairs. The fixture keeps the first
# supplement and the first repair.
REPAIR_SERIES_EVENT: dict[str, Any] = {
    "address": "P2KJPTC82NAFEzXg3X4eA83JvyWQ8PJVaBop2fUUsKPBcou",
    "contract": "governance",
    "kind": "SpecialResolution",
    "data": {
        "resolutionId": 37,
        "description": "Special Resolution",
        "calls": [
            {
                "moduleId": 2,
                "module": "phantasma_vm",
                "methodId": 6,
                "method": "RepairSeries",
                "arguments": {
                    "supplementsCount": "3649",
                    "supplements": [
                        {
                            "token": "BRC",
                            "tokenId": "23",
                            "phantasmaSeriesId": "6472",
                            "maxSupply": "1000",
                            "mintCount": "30",
                            "mode": "1",
                            "script": "0004010D000403524F4D0300",
                            "abi": "080A67657443726561746564",
                            "rom": "010804076372656174656405",
                        }
                    ],
                    "repairsCount": "8370",
                    "repairs": [
                        {
                            "token": "CROWN",
                            "tokenId": "4",
                            "phantasmaSeriesId": "0",
                            "importedLiveCount": "10998",
                            "script": "0004000E0000040D01040743",
                            "abi": "04076765744E616D65040100",
                        }
                    ],
                },
            }
        ],
    },
}


def test_special_resolution_repair_series_decodes_from_the_devnet_answer() -> None:
    event = EventExResult.from_wire(REPAIR_SERIES_EVENT)

    assert event.contract == "governance"
    assert event.kind == "SpecialResolution"
    assert isinstance(event.data, SpecialResolutionData)
    assert event.data.resolution_id == 37
    assert event.data.description == "Special Resolution"
    assert len(event.data.calls) == 1

    call = event.data.calls[0]
    assert (call.module_id, call.module, call.method_id, call.method) == (2, "phantasma_vm", 6, "RepairSeries")
    assert call.calls == []

    arguments = call.arguments
    assert isinstance(arguments, RepairSeriesArguments)
    assert arguments.supplements_count == "3649"
    assert arguments.repairs_count == "8370"
    supplement = arguments.supplements[0]
    assert (supplement.token, supplement.token_id, supplement.phantasma_series_id) == ("BRC", "23", "6472")
    assert (supplement.max_supply, supplement.mint_count, supplement.mode) == ("1000", "30", "1")
    repair = arguments.repairs[0]
    assert (repair.token, repair.token_id, repair.imported_live_count) == ("CROWN", "4", "10998")


def test_special_resolution_round_trips_to_the_wire_shape() -> None:
    # Re-writing the decoded event must reproduce the wire object exactly: camelCase names, numeric
    # ids as numbers, string counts as strings, and no null keys for the absent nested calls.
    assert EventExResult.from_wire(REPAIR_SERIES_EVENT).to_wire() == REPAIR_SERIES_EVENT


def test_special_resolution_transfer_fungible_decodes_from_the_devnet_answer() -> None:
    # Devnet block 8,736,266: resolution 44 "Repair imported NFT fungible infusions" carries 9,600
    # token.TransferFungible calls; this is its first call verbatim.
    event = EventExResult.from_wire(
        {
            "address": "P2KJPTC82NAFEzXg3X4eA83JvyWQ8PJVaBop2fUUsKPBcou",
            "contract": "governance",
            "kind": "SpecialResolution",
            "data": {
                "resolutionId": 44,
                "description": "Repair imported NFT fungible infusions",
                "calls": [
                    {
                        "moduleId": 1,
                        "module": "token",
                        "methodId": 0,
                        "method": "TransferFungible",
                        "arguments": {
                            "from": "S3dPnV8dfdkHDHDcJiHY255FEUZCM7oAmDW78LpYZ4jveGW",
                            "to": "S3dPnV8dfdkHDHDcJiHY255FEUZCM7oAmDW78LpYZ4jveGW",
                            "amount": "10000000000",
                            "token": "KCAL",
                            "tokenId": "1",
                        },
                    }
                ],
            },
        }
    )

    assert isinstance(event.data, SpecialResolutionData)
    assert event.data.resolution_id == 44
    transfer = event.data.calls[0].arguments
    assert isinstance(transfer, TransferFungibleArguments)
    # "from" is a Python keyword, so the model spells it from_ and declares the wire name.
    assert transfer.from_ == "S3dPnV8dfdkHDHDcJiHY255FEUZCM7oAmDW78LpYZ4jveGW"
    assert transfer.to == transfer.from_
    assert (transfer.amount, transfer.token, transfer.token_id) == ("10000000000", "KCAL", "1")


def test_import_contracts_decodes_from_the_devnet_answer() -> None:
    # Devnet block 8,736,257: phantasma_vm.ImportContracts restoring 70 contracts. The fixture
    # keeps the "mail" contract (empty storage) and the "pharming" contract's first root variable
    # and first table row.
    event = EventExResult.from_wire(
        {
            "address": "P2KJPTC82NAFEzXg3X4eA83JvyWQ8PJVaBop2fUUsKPBcou",
            "contract": "governance",
            "kind": "SpecialResolution",
            "data": {
                "resolutionId": 36,
                "description": "Special Resolution",
                "calls": [
                    {
                        "moduleId": 2,
                        "module": "phantasma_vm",
                        "methodId": 5,
                        "method": "ImportContracts",
                        "arguments": {
                            "contractsCount": "70",
                            "contracts": [
                                {
                                    "name": "mail",
                                    "address": "S3d6cUXRwJbudV4ADbRtMz3P9527ts7D2Lh9h2J96m48FPW",
                                    "owner": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
                                    "script": "0B",
                                    "abi": "090B507573684D657373616765",
                                    "rootVariables": [],
                                    "tables": [],
                                },
                                {
                                    "name": "pharming",
                                    "address": "S3d6cUXRwJbudV4ADbRtMz3P9527ts7D2Lh9h2J96m48FPW",
                                    "owner": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
                                    "script": "0B",
                                    "abi": "0906676574546F6B656E",
                                    "rootVariables": [
                                        {
                                            "key": "6D616E61676572",
                                            "value": "0100E9F4F69F677473684D2E201672A6AC30CA8F2A238C68",
                                        }
                                    ],
                                    "tables": [
                                        {
                                            "name": "addrs_kcal_bnb",
                                            "rows": [{"key": "3C003E", "value": "0104040B534F554C41646472657373"}],
                                        }
                                    ],
                                },
                            ],
                        },
                    }
                ],
            },
        }
    )

    assert isinstance(event.data, SpecialResolutionData)
    imported = event.data.calls[0].arguments
    assert isinstance(imported, ImportContractsArguments)
    assert imported.contracts_count == "70"
    assert len(imported.contracts) == 2
    assert imported.contracts[0].name == "mail"
    assert imported.contracts[0].root_variables == []
    assert imported.contracts[0].tables == []
    pharming = imported.contracts[1]
    assert pharming.root_variables[0].key == "6D616E61676572"
    assert pharming.tables[0].name == "addrs_kcal_bnb"
    assert pharming.tables[0].rows[0].key == "3C003E"


def test_token_create_data_decodes_and_round_trips() -> None:
    # Shape per RpcEventBuilder.TokenEvents.cs:153: carbonTokenId is a JSON number, maxSupply a
    # string, and the metadata values are rendered to strings by the node - unlike the metadata of
    # a token response, which carries VM values.
    wire: dict[str, Any] = {
        "address": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
        "contract": "token",
        "kind": "TokenCreate",
        "data": {
            "symbol": "CROWN",
            "maxSupply": "0",
            "decimals": 0,
            "isNonFungible": True,
            "carbonTokenId": 4,
            "metadata": {"name": "Crown", "description": "Phantasma Crown"},
        },
    }

    event = EventExResult.from_wire(wire)
    assert isinstance(event.data, TokenCreateData)
    assert event.data.symbol == "CROWN"
    assert event.data.max_supply == "0"
    assert event.data.decimals == 0
    assert event.data.is_non_fungible is True
    assert event.data.carbon_token_id == 4
    assert event.data.metadata == {"name": "Crown", "description": "Phantasma Crown"}
    assert event.to_wire() == wire


def test_token_series_create_data_decodes() -> None:
    # Shape per RpcEventBuilder.TokenEvents.cs:360: seriesId is the Phantasma id as a string while
    # the carbon ids and the mint bounds are JSON numbers.
    event = EventExResult.from_wire(
        {
            "address": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
            "contract": "token",
            "kind": "TokenSeriesCreate",
            "data": {
                "symbol": "CROWN",
                "seriesId": "6472",
                "maxMint": 100,
                "maxSupply": 1000,
                "owner": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
                "carbonTokenId": 4,
                "carbonSeriesId": 1,
                "metadata": {"name": "Crown Series"},
            },
        }
    )

    assert isinstance(event.data, TokenSeriesCreateData)
    assert event.data.series_id == "6472"
    assert (event.data.max_mint, event.data.max_supply) == (100, 1000)
    assert (event.data.carbon_token_id, event.data.carbon_series_id) == (4, 1)
    assert event.data.metadata == {"name": "Crown Series"}


@pytest.mark.parametrize("kind", ["OrderCreated", "OrderCancelled", "OrderFilled"])
def test_market_order_data_decodes_for_each_order_kind(kind: str) -> None:
    # Shape per RpcEventBuilder.MarketEvents.cs:403; all three order kinds share it, which is why
    # the carrying event's kind is the only way to tell them apart. On a cancel the node repeats
    # the seller in buyer, so that field is asserted as answered rather than expected to be empty.
    event = EventExResult.from_wire(
        {
            "address": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
            "contract": "market",
            "kind": kind,
            "data": {
                "baseSymbol": "CROWN",
                "quoteSymbol": "SOUL",
                "tokenId": "114421",
                "carbonBaseTokenId": 4,
                "carbonQuoteTokenId": 2,
                "carbonInstanceId": 7,
                "seller": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
                "buyer": "P2K6hJ8LQ4dqiiTBUxKfLwCbGKRDvcnCkTQ8vHjaBGnDy5B",
                "price": "1000000000",
                "endPrice": "0",
                "startDate": 1785000000,
                "endDate": 1785600000,
                "type": "Fixed",
            },
        }
    )

    assert isinstance(event.data, MarketOrderData)
    assert event.data.token_id == "114421"
    assert (event.data.carbon_base_token_id, event.data.carbon_quote_token_id) == (4, 2)
    assert event.data.carbon_instance_id == 7
    assert (event.data.price, event.data.end_price, event.data.type) == ("1000000000", "0", "Fixed")
    assert (event.data.start_date, event.data.end_date) == (1785000000, 1785600000)


def test_unknown_event_kind_keeps_its_payload_verbatim() -> None:
    # A node newer than this SDK can answer an event kind that is not modeled here. Losing that
    # payload - or failing the whole block answer over it - would be worse than handing the raw
    # JSON to the caller.
    payload = {"somethingNew": "7", "nested": {"deep": True}}
    event = EventExResult.from_wire({"address": "P", "contract": "x", "kind": "BrandNewKind", "data": payload})

    assert event.data == UnknownEventData(data=payload)


def test_mismatched_known_kind_falls_back_to_the_raw_payload() -> None:
    # The kind names a modeled shape but the payload does not match it: keeping the JSON is what
    # lets a consumer detect that the node's shape drifted, instead of reading a half-empty object
    # as if it were complete.
    payload = {"symbol": "CROWN", "carbonTokenId": "not-a-number"}
    event = EventExResult.from_wire({"address": "P", "contract": "token", "kind": "TokenCreate", "data": payload})

    assert event.data == UnknownEventData(data=payload)


def test_extended_event_without_data_decodes_to_no_payload() -> None:
    event = EventExResult.from_wire({"address": "P", "contract": "gas", "kind": "GasEscrow"})
    assert event.data is None


def test_special_resolution_envelope_tolerates_missing_fields() -> None:
    # Response models are default-tolerant across this SDK; an empty data object decodes to the
    # empty resolution instead of failing the transaction it belongs to.
    event = EventExResult.from_wire({"address": "P", "contract": "governance", "kind": "SpecialResolution", "data": {}})

    assert event.data == SpecialResolutionData(resolution_id=0, description=None, calls=[])


def call_wire(module: str, method: str, arguments: Any) -> dict[str, Any]:
    """Wraps one arguments payload into the call that carries it, which is the only way the decoder
    learns which shape to expect."""
    return {"moduleId": 0, "module": module, "methodId": 0, "method": method, "arguments": arguments}


# Pins the shape every module/method pair decodes into. The pairs and their shapes mirror the C#
# reference converter and the node's SpecialResolutionHelper, which build these answers; each
# payload carries real fields of its shape, so a wrong or missing wire name shows up as an
# all-default object rather than passing silently.
ARGUMENT_DISPATCH_CASES: list[tuple[str, str, dict[str, Any], type]] = [
    ("governance", "SetGasConfig", {"version": "1", "feeMultiplier": "16"}, GasConfigArguments),
    ("governance", "SetChainConfig", {"version": "0", "expiryWindow": "600"}, ChainConfigArguments),
    ("governance", "SpecialResolution", {"resolutionId": "31"}, NestedResolutionArguments),
    ("governance", "SetMetadata", {"metadata": {"name": "Phantasma"}}, MetadataArguments),
    ("governance", "SetNodeConfig", {"nodes": [{"id": "1", "type": "Validator"}]}, NodeConfigArguments),
    ("governance", "RegisterName", {"address": "P2K6h", "name": "alex"}, RegisterNameArguments),
    ("governance", "LookupName", {"address": "P2K6h"}, AddressArguments),
    ("governance", "LookupAddress", {"name": "alex"}, NameArguments),
    (
        "phantasma_vm",
        "ExecuteScript",
        {"maxGas": "10000", "gasFrom": "P2K6h", "script": "0B"},
        ExecuteScriptArguments,
    ),
    (
        "phantasma_vm",
        "RegisterTokenContract",
        {"tokenId": "4", "symbol": "CROWN", "script": "0B", "abi": "09"},
        RegisterTokenContractArguments,
    ),
    (
        "phantasma_vm",
        "DeployContract",
        {"from": "P2K6h", "contractName": "mail", "script": "0B", "abi": "09"},
        DeployContractArguments,
    ),
    ("phantasma_vm", "IsContractDeployed", {"name": "mail"}, NameArguments),
    ("phantasma_vm", "SetConfig", {"featureLevel": "3", "gasNexus": "100"}, PhantasmaVmConfigArguments),
    ("phantasma_vm", "ImportContracts", {"contractsCount": "70", "contracts": []}, ImportContractsArguments),
    (
        "phantasma_vm",
        "RepairSeries",
        {"supplementsCount": "3649", "repairsCount": "8370"},
        RepairSeriesArguments,
    ),
    ("phantasma_vm", "RepairToken", {"repairsCount": "2", "repairs": []}, RepairTokenArguments),
    (
        "token",
        "TransferFungible",
        {"from": "S3dPn", "to": "S3dPn", "amount": "1", "token": "KCAL", "tokenId": "1"},
        TransferFungibleArguments,
    ),
    (
        "token",
        "TransferNonFungible",
        {"from": "S3dPn", "to": "S3dPn", "instanceIds": ["7"], "token": "CROWN", "tokenId": "4"},
        TransferNonFungibleArguments,
    ),
    (
        "token",
        "CreateToken",
        {"symbol": "SOUL", "owner": "P2K6h", "maxSupply": "0", "decimals": "8", "flags": "199"},
        CreateTokenArguments,
    ),
    ("token", "MintFungible", {"to": "S3dPn", "amount": "5", "token": "KCAL", "tokenId": "1"}, MintFungibleArguments),
    (
        "token",
        "BurnFungible",
        {"from": "S3dPn", "amount": "5", "token": "KCAL", "tokenId": "1"},
        BurnFungibleArguments,
    ),
    ("token", "GetBalance", {"address": "P2K6h", "token": "KCAL", "tokenId": "1"}, BalanceArguments),
    (
        "token",
        "CreateTokenSeries",
        {"owner": "P2K6h", "maxMint": "100", "maxSupply": "1000", "token": "CROWN", "tokenId": "4"},
        TokenSeriesArguments,
    ),
    (
        "token",
        "DeleteTokenSeries",
        {"seriesId": "1", "token": "CROWN", "tokenId": "4"},
        TokenSeriesReferenceArguments,
    ),
    (
        "token",
        "MintNonFungible",
        {
            "owner": "P2K6h",
            "tokens": [{"seriesId": "1", "rom": "CA", "ram": "FE"}],
            "token": "CROWN",
            "tokenId": "4",
        },
        MintNonFungibleArguments,
    ),
    (
        "token",
        "BurnNonFungible",
        {"address": "P2K6h", "instanceIds": ["7"], "token": "CROWN", "tokenId": "4"},
        BurnNonFungibleArguments,
    ),
    (
        "token",
        "GetNonFungibleInfo",
        {"instanceId": "7", "getSchemas": "1", "token": "CROWN", "tokenId": "4"},
        NonFungibleInfoArguments,
    ),
    (
        "token",
        "GetNonFungibleInfoByRomId",
        {"romId": "CAFE", "getSchemas": "1", "token": "CROWN", "tokenId": "4"},
        NonFungibleInfoByRomIdArguments,
    ),
    ("token", "GetSeriesInfo", {"seriesId": "1", "token": "CROWN", "tokenId": "4"}, TokenSeriesReferenceArguments),
    (
        "token",
        "GetSeriesInfoByMetaId",
        {"romId": "CAFE", "token": "CROWN", "tokenId": "4"},
        SeriesInfoByMetaIdArguments,
    ),
    ("token", "GetTokenInfo", {"token": "CROWN", "tokenId": "4"}, TokenReferenceArguments),
    ("token", "GetTokenInfoBySymbol", {"symbol": "CROWN"}, SymbolArguments),
    ("token", "GetTokenSupply", {"token": "CROWN", "tokenId": "4"}, TokenReferenceArguments),
    ("token", "GetSeriesSupply", {"seriesId": "1", "token": "CROWN", "tokenId": "4"}, TokenSeriesReferenceArguments),
    ("token", "GetTokenIdBySymbol", {"symbol": "CROWN"}, SymbolArguments),
    ("token", "GetBalances", {"address": "P2K6h"}, AddressArguments),
    (
        "token",
        "CreateMintedTokenSeries",
        {
            "recipient": "P2K6h",
            "roms": ["CA"],
            "rams": ["FE"],
            "owner": "P2K6h",
            "maxMint": "1",
            "maxSupply": "1",
            "token": "CROWN",
            "tokenId": "4",
        },
        CreateMintedTokenSeriesArguments,
    ),
    ("token", "ApplyInflation", {"token": "SOUL", "tokenId": "2"}, TokenReferenceArguments),
    (
        "token",
        "UpdateTokenMetadata",
        {"metadata": {"name": "Crown"}, "token": "CROWN", "tokenId": "4"},
        UpdateTokenMetadataArguments,
    ),
    ("token", "GetNextTokenInflation", {"token": "SOUL", "tokenId": "2"}, TokenReferenceArguments),
    ("token", "SetTokensConfig", {"flags": "3", "flagsNames": ["Transferable"]}, TokensConfigArguments),
    (
        "token",
        "UpdateSeriesMetadata",
        {"seriesId": "1", "metadata": "CAFE", "token": "CROWN", "tokenId": "4"},
        UpdateSeriesMetadataArguments,
    ),
    (
        "token",
        "MintPhantasmaNonFungible",
        {
            "owner": "P2K6h",
            "tokens": [{"phantasmaSeriesId": "6472", "rom": "CA", "ram": "FE"}],
            "token": "CROWN",
            "tokenId": "4",
        },
        MintPhantasmaNonFungibleArguments,
    ),
]


@pytest.mark.parametrize("module, method, arguments, shape", ARGUMENT_DISPATCH_CASES)
def test_arguments_dispatch_covers_every_module_method_pair(
    module: str, method: str, arguments: dict[str, Any], shape: type
) -> None:
    decoded = SpecialResolutionCall.from_wire(call_wire(module, method, arguments)).arguments

    assert type(decoded) is shape, f"{module}.{method} decoded to {type(decoded).__name__}"
    assert decoded != shape(), f"{module}.{method} decoded to an all-default shape: no field was reached"


def test_every_decoded_method_has_a_dispatch_case() -> None:
    # Guards the table above against drift: a method added to the dispatch map without a case here
    # would otherwise ship untested.
    covered = {(module, method) for module, method, _, _ in ARGUMENT_DISPATCH_CASES}
    declared = {(module, method) for module, methods in ARGUMENT_SHAPES.items() for method in methods}

    assert declared - covered == set()
    assert len(ARGUMENT_DISPATCH_CASES) == len(declared)


def test_raw_arguments_win_over_a_known_method() -> None:
    # An older node can answer a raw dump for a method this build models. Dispatching on the method
    # name first would decode that dump into a typed shape with every field empty, which a consumer
    # cannot tell apart from a genuinely empty call.
    call = SpecialResolutionCall.from_wire(call_wire("token", "TransferFungible", {"rawArgs": "0104040B534F554C"}))

    assert call.arguments == RawArguments(raw_args="0104040B534F554C")


def test_unmodeled_method_keeps_its_arguments_verbatim() -> None:
    payload = {"brandNewField": "7", "nested": {"deep": ["1"]}}
    call = SpecialResolutionCall.from_wire(call_wire("token", "BrandNewMethod", payload))

    assert call.arguments == UnrecognizedArguments(data=payload)


def test_mismatched_known_shape_keeps_its_arguments_verbatim() -> None:
    # The pair is modeled but the payload is not the modeled shape - a node whose fields drifted.
    # Keeping the JSON makes the drift visible instead of silently reporting empty fields.
    payload = {"supplementsCount": ["3649"]}
    call = SpecialResolutionCall.from_wire(call_wire("phantasma_vm", "RepairSeries", payload))

    assert call.arguments == UnrecognizedArguments(data=payload)


def test_nested_resolution_calls_decode_recursively() -> None:
    # A resolution can carry another resolution: the outer call holds the nested id in its
    # arguments and the nested calls in its calls, which dispatch exactly like top-level ones.
    call = SpecialResolutionCall.from_wire(
        {
            "moduleId": 0,
            "module": "governance",
            "methodId": 2,
            "method": "SpecialResolution",
            "arguments": {"resolutionId": "31"},
            "calls": [
                {
                    "moduleId": 1,
                    "module": "token",
                    "methodId": 0,
                    "method": "TransferFungible",
                    "arguments": {"from": "S3dPn", "to": "S3dPn", "amount": "5", "token": "KCAL", "tokenId": "1"},
                }
            ],
        }
    )

    # The envelope reports resolutionId as a number, this argument shape as a string; both follow
    # the wire rather than being normalized to one of the two.
    assert call.arguments == NestedResolutionArguments(resolution_id="31")
    assert len(call.calls) == 1
    nested = call.calls[0].arguments
    assert isinstance(nested, TransferFungibleArguments)
    assert nested.amount == "5"


def test_create_token_arguments_carry_vm_metadata() -> None:
    # token.CreateToken metadata values are VM values, not plain strings: the interest array of
    # getToken("SOUL", true) is the shape that motivated VmValue (devnet, 2026-08-01).
    call = SpecialResolutionCall.from_wire(
        call_wire(
            "token",
            "CreateToken",
            {
                "symbol": "SOUL",
                "owner": "P2KFNXEbt65rQiWqogAzqkVGMqFirPmqPw8mQyxvRKsrXV8",
                "maxSupply": "0",
                "decimals": "8",
                "flags": "199",
                "metadata": {"_ia": [{"mul": "25", "div": "10000"}], "name": "Phantasma Stake"},
            },
        )
    )

    created = call.arguments
    assert isinstance(created, CreateTokenArguments)
    assert created.decimals == "8"
    assert created.metadata is not None
    assert created.metadata["name"].as_text() == "Phantasma Stake"
    interest = created.metadata["_ia"].as_items()
    assert interest is not None and len(interest) == 1
    mul = interest[0].get("mul")
    assert mul is not None and mul.as_text() == "25"
    assert created.token_schemas is None


def test_gas_config_v2_tail_is_optional() -> None:
    version0: dict[str, Any] = {
        "version": "0",
        "maxNameLength": "255",
        "maxTokenSymbolLength": "10",
        "feeShift": "10",
        "maxStructureSize": "65535",
        "feeMultiplier": "16",
        "gasTokenId": "1",
        "dataTokenId": "0",
        "minimumGasOffer": "10000",
        "dataEscrowPerRow": "1000000",
        "gasFeeTransfer": "1000",
        "gasFeeQuery": "100",
        "gasFeeCreateTokenBase": "100000000",
        "gasFeeCreateTokenSymbol": "10000000",
        "gasFeeCreateTokenSeries": "1000000",
        "gasFeePerByte": "10",
        "gasFeeRegisterName": "100000",
        "gasBurnRatioMul": "1",
        "gasBurnRatioShift": "1",
    }

    # A version 0 config has no gas-model-v2 tail on the wire; the optional fields must stay absent
    # and writing the call back must not invent null keys for them.
    call = SpecialResolutionCall.from_wire(call_wire("governance", "SetGasConfig", version0))
    config = call.arguments
    assert isinstance(config, GasConfigArguments)
    assert config.fee_multiplier == "16"
    assert config.minimum_gas_bill is None
    assert call.to_wire() == call_wire("governance", "SetGasConfig", version0)

    # A version 1 config carries the tail; the same shape must pick it up.
    with_tail = dict(version0, version="1", minimumGasBill="21000", gasProducerRatioMul="45")
    config = SpecialResolutionCall.from_wire(call_wire("governance", "SetGasConfig", with_tail)).arguments
    assert isinstance(config, GasConfigArguments)
    assert config.minimum_gas_bill == "21000"
    assert config.gas_producer_ratio_mul == "45"


def test_absent_and_null_arguments_carry_no_shape() -> None:
    # The node omits absent arguments (its serializer drops nulls), but both spellings must land on
    # no arguments at all rather than on a fabricated empty shape.
    call = SpecialResolutionCall.from_wire(
        {"moduleId": 1, "module": "token", "methodId": 0, "method": "TransferFungible"}
    )
    assert call.arguments is None
    assert call.calls == []

    call = SpecialResolutionCall.from_wire(call_wire("token", "TransferFungible", None))
    assert call.arguments is None


def test_call_tolerates_odd_envelope_fields() -> None:
    # One malformed call must not fail the transaction it belongs to: ids that are not numbers and
    # names that are not strings fall back to their defaults, and the arguments still dispatch on
    # whatever module and method could be read.
    call = SpecialResolutionCall.from_wire(
        {
            "moduleId": "two",
            "module": ["token"],
            "methodId": 0,
            "method": "TransferFungible",
            "arguments": {"amount": "5"},
            "calls": {},
        }
    )

    assert call.module_id == 0
    assert call.module == ""
    assert call.calls == []
    # Module was unreadable, so the pair is unknown and the arguments keep their JSON.
    assert call.arguments == UnrecognizedArguments(data={"amount": "5"})
