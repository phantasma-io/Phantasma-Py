"""Typed arguments of the calls a special resolution can carry.

The concrete shape is chosen by the ``module`` and ``method`` of the call that carries it, so a
consumer matches on a type instead of walking an untyped tree::

    if isinstance(call.arguments, ImportContractsArguments):
        for contract in call.arguments.contracts:
            use(contract.script, contract.tables)

Shapes that repeat across methods share one class on purpose: a query by token id looks the same
whichever query it is. Every numeric field is a string, because chain values are big integers and
JSON numbers lose precision above 2^53.

Decoding is total: a module/method pair this build does not model, and a modeled pair whose payload
does not match its shape, both arrive as :class:`UnrecognizedArguments` with the JSON preserved
verbatim. The C# reference SDK drops those instead; this SDK keeps them so that data answered by a
node newer than the SDK is never silently lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._wire_shapes import ShapeMismatch, decode_shape
from .vm_value import VmValue

# --------------------------------------------------------------------------- fallback shapes


@dataclass(slots=True)
class RawArguments:
    """Arguments of a call the answering node itself could not decode: the buffer as hex."""

    raw_args: str = ""


@dataclass(slots=True)
class UnrecognizedArguments:
    """Arguments of a module/method pair this build does not model, or of a modeled pair whose
    payload did not match its shape. The parsed JSON is kept as answered."""

    data: Any = None

    def to_wire(self) -> Any:
        """Writes the preserved arguments back unchanged."""
        return self.data


# --------------------------------------------------------------------------- governance module


@dataclass(slots=True)
class GasConfigArguments:
    """Arguments of ``governance.SetGasConfig``."""

    version: str = ""
    max_name_length: str = ""
    max_token_symbol_length: str = ""
    fee_shift: str = ""
    max_structure_size: str = ""
    fee_multiplier: str = ""
    gas_token_id: str = ""
    data_token_id: str = ""
    minimum_gas_offer: str = ""
    data_escrow_per_row: str = ""
    gas_fee_transfer: str = ""
    gas_fee_query: str = ""
    gas_fee_create_token_base: str = ""
    gas_fee_create_token_symbol: str = ""
    gas_fee_create_token_series: str = ""
    gas_fee_per_byte: str = ""
    gas_fee_register_name: str = ""
    gas_burn_ratio_mul: str = ""
    gas_burn_ratio_shift: str = ""
    # Gas-model-v2 tail: present only when the packaged config declares version >= 1.
    minimum_gas_bill: str | None = None
    gas_producer_ratio_mul: str | None = None
    gas_producer_ratio_shift: str | None = None
    gas_dapp_ratio_mul: str | None = None
    gas_dapp_ratio_shift: str | None = None
    policy_fee_create_token_base: str | None = None
    policy_fee_create_token_symbol: str | None = None
    policy_fee_create_token_series: str | None = None
    policy_fee_register_name: str | None = None
    legacy_data_escrow_per_row: str | None = None


@dataclass(slots=True)
class ChainConfigArguments:
    """Arguments of ``governance.SetChainConfig``."""

    version: str = ""
    reserved1: str = ""
    reserved2: str = ""
    reserved3: str = ""
    allowed_tx_types: str = ""
    expiry_window: str = ""
    block_rate_target: str = ""


@dataclass(slots=True)
class NestedResolutionArguments:
    """Arguments of ``governance.SpecialResolution``: a resolution nested inside another one.

    Its own calls are reported in the carrying call's ``calls``, not here.
    """

    # Rendered as a string here, unlike the numeric resolution id of the resolution envelope.
    resolution_id: str = ""


@dataclass(slots=True)
class MetadataArguments:
    """Arguments of ``governance.SetMetadata``."""

    metadata: dict[str, VmValue] = field(default_factory=dict)


@dataclass(slots=True)
class ConsensusNode:
    """One node of a ``governance.SetNodeConfig`` call."""

    id: str = ""
    type: str = ""


@dataclass(slots=True)
class NodeConfigArguments:
    """Arguments of ``governance.SetNodeConfig``."""

    nodes: list[ConsensusNode] = field(default_factory=list)


@dataclass(slots=True)
class RegisterNameArguments:
    """Arguments of ``governance.RegisterName``."""

    address: str = ""
    name: str = ""


@dataclass(slots=True)
class AddressArguments:
    """A single address argument, shared by ``governance.LookupName`` and ``token.GetBalances``."""

    address: str = ""


@dataclass(slots=True)
class NameArguments:
    """A single name argument, shared by ``governance.LookupAddress`` and
    ``phantasma_vm.IsContractDeployed``."""

    name: str = ""


# --------------------------------------------------------------------------- phantasma_vm module


@dataclass(slots=True)
class ExecuteScriptArguments:
    """Arguments of ``phantasma_vm.ExecuteScript``."""

    max_gas: str = ""
    gas_from: str = ""
    script: str = ""


@dataclass(slots=True)
class RegisterTokenContractArguments:
    """Arguments of ``phantasma_vm.RegisterTokenContract``."""

    token_id: str = ""
    symbol: str = ""
    script: str = ""
    abi: str = ""
    # Resolved token symbol; absent when the token could not be resolved at answer time.
    token: str | None = None


@dataclass(slots=True)
class DeployContractArguments:
    """Arguments of ``phantasma_vm.DeployContract``."""

    from_: str = field(default="", metadata={"wire": "from"})
    contract_name: str = ""
    script: str = ""
    abi: str = ""


@dataclass(slots=True)
class PhantasmaVmConfigArguments:
    """Arguments of ``phantasma_vm.SetConfig``."""

    feature_level: str = ""
    gas_constructor: str = ""
    gas_nexus: str = ""
    gas_organization: str = ""
    gas_account: str = ""
    gas_leaderboard: str = ""
    gas_standard: str = ""
    gas_oracle: str = ""
    fuel_per_contract_deploy: str = ""


@dataclass(slots=True)
class ContractStorageRow:
    """A key/value row of contract storage; both sides are hex because they hold arbitrary bytes."""

    key: str = ""
    value: str = ""


@dataclass(slots=True)
class ContractStorageTable:
    """One map or list table of a contract, with every row it carries."""

    name: str = ""
    rows: list[ContractStorageRow] = field(default_factory=list)


@dataclass(slots=True)
class ImportedContract:
    """One contract restored by a migration: identity, code and the whole of its stored state."""

    name: str = ""
    address: str = ""
    owner: str = ""
    script: str = ""
    abi: str = ""
    root_variables: list[ContractStorageRow] = field(default_factory=list)
    tables: list[ContractStorageTable] = field(default_factory=list)


@dataclass(slots=True)
class ImportContractsArguments:
    """Arguments of ``phantasma_vm.ImportContracts``."""

    contracts_count: str = "0"
    contracts: list[ImportedContract] = field(default_factory=list)


@dataclass(slots=True)
class SeriesSupplement:
    """The definition needed to rebuild one Phantasma series."""

    token: str = ""
    token_id: str = ""
    phantasma_series_id: str = ""
    max_supply: str = ""
    mint_count: str = ""
    mode: str = ""
    script: str = ""
    abi: str = ""
    rom: str = ""


@dataclass(slots=True)
class SeriesMintCountRepair:
    """The mint-count repair of one Phantasma series."""

    token: str = ""
    token_id: str = ""
    phantasma_series_id: str = ""
    imported_live_count: str = ""
    script: str = ""
    abi: str = ""


@dataclass(slots=True)
class RepairSeriesArguments:
    """Arguments of ``phantasma_vm.RepairSeries``."""

    supplements_count: str = "0"
    supplements: list[SeriesSupplement] = field(default_factory=list)
    repairs_count: str = "0"
    repairs: list[SeriesMintCountRepair] = field(default_factory=list)


@dataclass(slots=True)
class TokenRepair:
    """The repair of one token definition."""

    token: str = ""
    token_id: str = ""
    symbol: str = ""
    script: str = ""
    abi: str = ""
    token_flags: str = ""
    # Bitmask of the repair operations the chain was asked to perform. Kept numeric on purpose: a
    # new chain-side operation must not silently render as an unrelated name here.
    repair_mask: str = ""


@dataclass(slots=True)
class RepairTokenArguments:
    """Arguments of ``phantasma_vm.RepairToken``."""

    repairs_count: str = "0"
    repairs: list[TokenRepair] = field(default_factory=list)


# --------------------------------------------------------------------------- token module


@dataclass(slots=True)
class TokenReferenceArguments:
    """Token identity: the resolved symbol plus the numeric id it was resolved from.

    Also the arguments of the plain token queries (``GetTokenInfo``, ``GetTokenSupply``,
    ``ApplyInflation``, ``GetNextTokenInflation``).
    """

    token: str = ""
    token_id: str = ""


@dataclass(slots=True)
class TokenSeriesReferenceArguments(TokenReferenceArguments):
    """Addresses one series of a token: ``DeleteTokenSeries``, ``GetSeriesInfo``,
    ``GetSeriesSupply``."""

    series_id: str = ""


@dataclass(slots=True)
class SymbolArguments:
    """A single symbol argument: ``GetTokenInfoBySymbol`` and ``GetTokenIdBySymbol``."""

    symbol: str = ""


@dataclass(slots=True)
class TransferFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.TransferFungible``."""

    from_: str = field(default="", metadata={"wire": "from"})
    to: str = ""
    amount: str = ""


@dataclass(slots=True)
class TransferNonFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.TransferNonFungible``."""

    from_: str = field(default="", metadata={"wire": "from"})
    to: str = ""
    instance_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MintFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.MintFungible``."""

    to: str = ""
    amount: str = ""


@dataclass(slots=True)
class BurnFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.BurnFungible``."""

    from_: str = field(default="", metadata={"wire": "from"})
    amount: str = ""


@dataclass(slots=True)
class BalanceArguments(TokenReferenceArguments):
    """Arguments of ``token.GetBalance``."""

    address: str = ""


@dataclass(slots=True)
class CreateTokenArguments:
    """Arguments of ``token.CreateToken``."""

    symbol: str = ""
    owner: str = ""
    max_supply: str = ""
    decimals: str = ""
    flags: str = ""
    # Decoded metadata fields; absent when the token carries none.
    metadata: dict[str, VmValue] | None = None
    # NFT schema blob as hex; absent for fungible tokens.
    token_schemas: str | None = None


@dataclass(slots=True)
class TokenSeriesArguments(TokenReferenceArguments):
    """A series definition, as carried by ``token.CreateTokenSeries``."""

    owner: str = ""
    max_mint: str = ""
    max_supply: str = ""
    # Decoded series metadata; absent when the token declares no schema for it.
    metadata: dict[str, VmValue] | None = None
    # Phantasma series id taken from the decoded metadata, when the schema carries one.
    series_id: str | None = None
    # Metadata blob as hex, reported instead of ``metadata`` when it cannot be decoded.
    metadata_raw: str | None = None


@dataclass(slots=True)
class CreateMintedTokenSeriesArguments(TokenSeriesArguments):
    """Arguments of ``token.CreateMintedTokenSeries``."""

    recipient: str = ""
    roms: list[str] = field(default_factory=list)
    rams: list[str] = field(default_factory=list)


@dataclass(slots=True)
class NftMint:
    """One NFT to mint, addressed by the carbon series id."""

    series_id: str = ""
    rom: str = ""
    ram: str = ""


@dataclass(slots=True)
class PhantasmaNftMint:
    """One NFT to mint, addressed by the 32-byte Phantasma series id."""

    phantasma_series_id: str = ""
    rom: str = ""
    ram: str = ""


@dataclass(slots=True)
class MintNonFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.MintNonFungible``."""

    owner: str = ""
    tokens: list[NftMint] = field(default_factory=list)


@dataclass(slots=True)
class MintPhantasmaNonFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.MintPhantasmaNonFungible``."""

    owner: str = ""
    tokens: list[PhantasmaNftMint] = field(default_factory=list)


@dataclass(slots=True)
class BurnNonFungibleArguments(TokenReferenceArguments):
    """Arguments of ``token.BurnNonFungible``."""

    address: str = ""
    instance_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class NonFungibleInfoArguments(TokenReferenceArguments):
    """Arguments of ``token.GetNonFungibleInfo``."""

    instance_id: str = ""
    get_schemas: str = ""


@dataclass(slots=True)
class NonFungibleInfoByRomIdArguments(TokenReferenceArguments):
    """Arguments of ``token.GetNonFungibleInfoByRomId``."""

    rom_id: str = ""
    get_schemas: str = ""


@dataclass(slots=True)
class SeriesInfoByMetaIdArguments(TokenReferenceArguments):
    """Arguments of ``token.GetSeriesInfoByMetaId``."""

    rom_id: str = ""


@dataclass(slots=True)
class TokensConfigArguments:
    """Arguments of ``token.SetTokensConfig``."""

    flags: str = ""
    # Names of the flags that are set, including a Reserved0xNN entry for unknown bits.
    flags_names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UpdateTokenMetadataArguments(TokenReferenceArguments):
    """Arguments of ``token.UpdateTokenMetadata``."""

    metadata: dict[str, VmValue] | None = None


@dataclass(slots=True)
class UpdateSeriesMetadataArguments(TokenReferenceArguments):
    """Arguments of ``token.UpdateSeriesMetadata``."""

    series_id: str = ""
    # Metadata blob as hex: this call carries it unschematized.
    metadata: str = ""


SpecialResolutionArguments = (
    RawArguments
    | UnrecognizedArguments
    | GasConfigArguments
    | ChainConfigArguments
    | NestedResolutionArguments
    | MetadataArguments
    | NodeConfigArguments
    | RegisterNameArguments
    | AddressArguments
    | NameArguments
    | ExecuteScriptArguments
    | RegisterTokenContractArguments
    | DeployContractArguments
    | PhantasmaVmConfigArguments
    | ImportContractsArguments
    | RepairSeriesArguments
    | RepairTokenArguments
    | TokenReferenceArguments
    | TokenSeriesReferenceArguments
    | SymbolArguments
    | TransferFungibleArguments
    | TransferNonFungibleArguments
    | MintFungibleArguments
    | BurnFungibleArguments
    | BalanceArguments
    | CreateTokenArguments
    | TokenSeriesArguments
    | CreateMintedTokenSeriesArguments
    | MintNonFungibleArguments
    | MintPhantasmaNonFungibleArguments
    | BurnNonFungibleArguments
    | NonFungibleInfoArguments
    | NonFungibleInfoByRomIdArguments
    | SeriesInfoByMetaIdArguments
    | TokensConfigArguments
    | UpdateTokenMetadataArguments
    | UpdateSeriesMetadataArguments
)

# Module and method to the shape of that call's arguments. Mirrors the converter of the C# SDK and
# the node's SpecialResolutionHelper, which build these answers. A pair missing here is not an
# error: the node answers the raw argument buffer for anything it cannot decode, and an unmodeled
# pair keeps its JSON.
ARGUMENT_SHAPES: dict[str, dict[str, type[SpecialResolutionArguments]]] = {
    "governance": {
        "SetGasConfig": GasConfigArguments,
        "SetChainConfig": ChainConfigArguments,
        "SpecialResolution": NestedResolutionArguments,
        "SetMetadata": MetadataArguments,
        "SetNodeConfig": NodeConfigArguments,
        "RegisterName": RegisterNameArguments,
        "LookupName": AddressArguments,
        "LookupAddress": NameArguments,
    },
    "phantasma_vm": {
        "ExecuteScript": ExecuteScriptArguments,
        "RegisterTokenContract": RegisterTokenContractArguments,
        "DeployContract": DeployContractArguments,
        "IsContractDeployed": NameArguments,
        "SetConfig": PhantasmaVmConfigArguments,
        "ImportContracts": ImportContractsArguments,
        "RepairSeries": RepairSeriesArguments,
        "RepairToken": RepairTokenArguments,
    },
    "token": {
        "TransferFungible": TransferFungibleArguments,
        "TransferNonFungible": TransferNonFungibleArguments,
        "CreateToken": CreateTokenArguments,
        "MintFungible": MintFungibleArguments,
        "BurnFungible": BurnFungibleArguments,
        "GetBalance": BalanceArguments,
        "CreateTokenSeries": TokenSeriesArguments,
        "DeleteTokenSeries": TokenSeriesReferenceArguments,
        "MintNonFungible": MintNonFungibleArguments,
        "BurnNonFungible": BurnNonFungibleArguments,
        "GetNonFungibleInfo": NonFungibleInfoArguments,
        "GetNonFungibleInfoByRomId": NonFungibleInfoByRomIdArguments,
        "GetSeriesInfo": TokenSeriesReferenceArguments,
        "GetSeriesInfoByMetaId": SeriesInfoByMetaIdArguments,
        "GetTokenInfo": TokenReferenceArguments,
        "GetTokenInfoBySymbol": SymbolArguments,
        "GetTokenSupply": TokenReferenceArguments,
        "GetSeriesSupply": TokenSeriesReferenceArguments,
        "GetTokenIdBySymbol": SymbolArguments,
        "GetBalances": AddressArguments,
        "CreateMintedTokenSeries": CreateMintedTokenSeriesArguments,
        "ApplyInflation": TokenReferenceArguments,
        "UpdateTokenMetadata": UpdateTokenMetadataArguments,
        "GetNextTokenInflation": TokenReferenceArguments,
        "SetTokensConfig": TokensConfigArguments,
        "UpdateSeriesMetadata": UpdateSeriesMetadataArguments,
        "MintPhantasmaNonFungible": MintPhantasmaNonFungibleArguments,
    },
}


def decode_special_resolution_arguments(module: str, method: str, raw: Any) -> SpecialResolutionArguments | None:
    """Types the arguments of one call from its module and method.

    Absent arguments yield None; everything else follows the totality rule documented on this
    module.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return UnrecognizedArguments(data=raw)

    # The undecoded case is recognised by its content, not by the method name: a method this build
    # knows can still arrive as a raw dump from an older node, and reading that as the typed shape
    # would silently produce an object with every field empty.
    if "rawArgs" in raw:
        try:
            return decode_shape(RawArguments, raw)
        except ShapeMismatch:
            return UnrecognizedArguments(data=raw)

    shape = ARGUMENT_SHAPES.get(module, {}).get(method)
    if shape is None:
        return UnrecognizedArguments(data=raw)

    try:
        return decode_shape(shape, raw)
    except ShapeMismatch:
        return UnrecognizedArguments(data=raw)
