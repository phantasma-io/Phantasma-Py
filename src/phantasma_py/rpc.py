"""JSON-RPC client and typed response models."""

from __future__ import annotations

import base64
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Generic, Protocol, TypeVar, cast, get_args, get_origin, get_type_hints

import requests

from .carbon import (
    Bytes32,
    SignedTxMsg,
    TxMsg,
    parse_create_token_result,
    parse_create_token_series_result,
    serialize,
    sign_tx_msg,
)
from .crypto import PhantasmaKeys
from .errors import RPCError
from .transaction import Transaction, tx_state_is_fault, tx_state_is_success
from .vm import VMObject

T = TypeVar("T")


class HTTPSession(Protocol):
    def post(self, url: str, *, json: Mapping[str, Any], timeout: float) -> Any: ...


@dataclass(slots=True)
class BalanceResult:
    chain: str = ""
    amount: str = "0"
    symbol: str = ""
    decimals: int = 0
    ids: list[str] | None = None

    def decimal_amount(self) -> str:
        return convert_decimals(self.amount, self.decimals)


@dataclass(slots=True)
class InteropResult:
    local: str = ""
    external: str = ""


@dataclass(slots=True)
class PlatformResult:
    platform: str = ""
    chain: str = ""
    fuel: str = ""
    tokens: list[str] = field(default_factory=list)
    interop: list[InteropResult] = field(default_factory=list)


@dataclass(slots=True)
class GovernanceResult:
    name: str = ""
    value: str = ""


@dataclass(slots=True)
class OrganizationResult:
    id: str | None = None
    name: str | None = None
    members: list[str] | None = None


@dataclass(slots=True)
class CrowdsaleResult:
    hash: str = ""
    name: str = ""
    creator: str = ""
    flags: str = ""
    start_date: int = 0
    end_date: int = 0
    sell_symbol: str = ""
    receive_symbol: str = ""
    price: int = 0
    global_soft_cap: str = "0"
    global_hard_cap: str = "0"
    user_soft_cap: str = "0"
    user_hard_cap: str = "0"


@dataclass(slots=True)
class StakeResult:
    amount: str = "0"
    time: int = 0
    unclaimed: str = "0"

    def decimal_amount(self) -> str:
        return convert_decimals(self.amount, 8)


@dataclass(slots=True)
class StorageResult:
    available: int = 0
    used: int = 0
    avatar: str = ""
    archives: list[ArchiveResult] = field(default_factory=list)


@dataclass(slots=True)
class AccountResult:
    address: str = ""
    name: str = ""
    stakes: StakeResult = field(default_factory=StakeResult)
    stake: str = "0"
    unclaimed: str = "0"
    relay: str | None = None
    validator: str = ""
    storage: StorageResult = field(default_factory=StorageResult)
    balances: list[BalanceResult] = field(default_factory=list)
    txs: list[str] | None = None

    def get_token_balance(self, symbol: str, decimals: int = 0) -> BalanceResult:
        for balance in self.balances:
            if balance.symbol == symbol:
                return balance
        balance = BalanceResult(chain="main", amount="0", symbol=symbol, decimals=decimals)
        self.balances.append(balance)
        return balance


@dataclass(slots=True)
class AddressTransactionsResult:
    address: str = ""
    txs: list[TransactionResult] = field(default_factory=list)


@dataclass(slots=True)
class LeaderboardRowResult:
    address: str = ""
    value: str = ""


@dataclass(slots=True)
class LeaderboardResult:
    name: str | None = None
    rows: list[LeaderboardRowResult] | None = None


@dataclass(slots=True)
class DappResult:
    name: str = ""
    address: str = ""
    chain: str = ""


@dataclass(slots=True)
class ChainResult:
    name: str | None = None
    address: str | None = None
    parent: str | None = None
    height: int = 0
    organization: str | None = None
    contracts: list[str] | None = None
    dapps: list[str] | None = None


@dataclass(slots=True)
class NexusResult:
    name: str | None = None
    protocol: int = 0
    platforms: list[PlatformResult] | None = None
    tokens: list[TokenResult] | None = None
    chains: list[ChainResult] | None = None
    governance: list[GovernanceResult] | None = None
    organizations: list[str] | None = None


@dataclass(slots=True)
class PaginatedResult(Generic[T]):
    page: int = 0
    page_size: int = 0
    total: int = 0
    total_pages: int = 0
    result: T | None = None


@dataclass(slots=True)
class CursorPaginatedResult(Generic[T]):
    result: T | None = None
    cursor: str | None = None


@dataclass(slots=True)
class EventResult:
    address: str = ""
    contract: str = ""
    kind: str = ""
    name: str = ""
    data: str = ""


@dataclass(slots=True)
class OracleResult:
    url: str = ""
    content: str = ""


@dataclass(slots=True)
class SignatureResult:
    kind: str = ""
    data: str = ""


@dataclass(slots=True)
class EventExResult:
    address: str = ""
    contract: str = ""
    kind: str = ""
    data: Any | None = None


@dataclass(slots=True)
class TransactionResult:
    hash: str = ""
    chain_address: str = ""
    timestamp: int = 0
    block_height: int = 0
    block_hash: str = ""
    script: str = ""
    payload: str = ""
    carbon_tx_type: int = 0
    carbon_tx_data: str = ""
    debug_comment: str | None = None
    events: list[EventResult] = field(default_factory=list)
    extended_events: list[EventExResult] = field(default_factory=list)
    state: str = ""
    result: str = ""
    fee: str = "0"
    signatures: list[SignatureResult] = field(default_factory=list)
    sender: str = ""
    gas_payer: str = ""
    gas_target: str = ""
    gas_price: str = ""
    gas_limit: str = ""
    expiration: int = 0

    @property
    def state_is_success(self) -> bool:
        return tx_state_is_success(self.state)

    @property
    def state_is_fault(self) -> bool:
        return tx_state_is_fault(self.state)


@dataclass(slots=True)
class BlockResult:
    hash: str = ""
    previous_hash: str = ""
    timestamp: int = 0
    height: int = 0
    chain_address: str = ""
    protocol: int = 0
    txs: list[TransactionResult] = field(default_factory=list)
    validator_address: str = ""
    reward: str = "0"
    events: list[EventResult] | None = None
    oracles: list[OracleResult] | None = None


@dataclass(slots=True)
class TokenPropertyResult:
    key: str = ""
    value: str = ""


@dataclass(slots=True)
class TokenExternalResult:
    platform: str = ""
    hash: str = ""


@dataclass(slots=True)
class TokenPriceResult:
    timestamp: int = 0
    open: str = "0"
    high: str = "0"
    low: str = "0"
    close: str = "0"


@dataclass(slots=True)
class VMVariableSchemaResult:
    type: str = ""
    schema: VMStructSchemaResult | None = None


@dataclass(slots=True)
class VMNamedVariableSchemaResult:
    name: str = ""
    schema: VMVariableSchemaResult = field(default_factory=VMVariableSchemaResult)


@dataclass(slots=True)
class VMStructSchemaResult:
    fields: list[VMNamedVariableSchemaResult] = field(default_factory=list)
    flags: int = 0


@dataclass(slots=True)
class TokenSchemasResult:
    series_metadata: VMStructSchemaResult = field(default_factory=VMStructSchemaResult)
    rom: VMStructSchemaResult = field(default_factory=VMStructSchemaResult)
    ram: VMStructSchemaResult = field(default_factory=VMStructSchemaResult)


@dataclass(slots=True)
class TokenSeriesResult:
    series_id: str = ""
    carbon_token_id: str = ""
    carbon_series_id: str = ""
    owner_address: str = ""
    max_mint: str = "0"
    mint_count: str = "0"
    current_supply: str = "0"
    max_supply: str = "0"
    burned_supply: str | None = None
    mode: str | None = None
    script: str | None = None
    methods: list[ABIMethodResult] | None = None
    metadata: list[TokenPropertyResult] = field(default_factory=list)


@dataclass(slots=True)
class TokenResult:
    symbol: str = ""
    name: str = ""
    decimals: int = 0
    current_supply: str = "0"
    max_supply: str = "0"
    burned_supply: str = "0"
    address: str = ""
    owner: str = ""
    flags: str = ""
    script: str | None = None
    series: list[TokenSeriesResult] = field(default_factory=list)
    carbon_id: str = ""
    metadata: list[TokenPropertyResult] | None = None
    token_schemas: TokenSchemasResult | None = None
    external: list[TokenExternalResult] | None = None
    price: list[TokenPriceResult] | None = None

    def has_flag(self, flag: str) -> bool:
        return flag in [item.strip() for item in self.flags.split(",")]

    def is_burnable(self) -> bool:
        return self.has_flag("Burnable")

    def is_divisible(self) -> bool:
        return self.has_flag("Divisible")

    def is_fiat(self) -> bool:
        return self.has_flag("Fiat")

    def is_finite(self) -> bool:
        return self.has_flag("Finite")

    def is_fuel(self) -> bool:
        return self.has_flag("Fuel")

    def is_fungible(self) -> bool:
        return self.has_flag("Fungible")

    def is_mintable(self) -> bool:
        return self.has_flag("Mintable")

    def is_stakable(self) -> bool:
        return self.has_flag("Stakable")

    def is_transferable(self) -> bool:
        return self.has_flag("Transferable")


@dataclass(slots=True)
class TokenDataResult:
    id: str = ""
    series: str = ""
    carbon_token_id: str = ""
    carbon_series_id: str = ""
    carbon_nft_address: str = ""
    mint: str = ""
    chain_name: str = ""
    owner_address: str = ""
    creator_address: str = ""
    ram: str = ""
    rom: str = ""
    status: str = ""
    infusion: list[TokenPropertyResult] = field(default_factory=list)
    properties: list[TokenPropertyResult] = field(default_factory=list)


@dataclass(slots=True)
class ScriptResult:
    events: list[EventResult] = field(default_factory=list)
    result: str | None = None
    error: str | None = None
    results: list[str] = field(default_factory=list)
    oracles: list[OracleResult] = field(default_factory=list)
    state: str | None = None
    gas: str | None = None

    def decode_result(self) -> VMObject:
        return VMObject.from_bytes(bytes.fromhex(self.result or ""))

    def decode_results(self, index: int) -> VMObject:
        return VMObject.from_bytes(bytes.fromhex(self.results[index]))


@dataclass(slots=True)
class ArchiveResult:
    name: str | None = None
    hash: str | None = None
    time: int = 0
    size: int = 0
    encryption: str | None = None
    block_count: int = 0
    missing_blocks: list[int] | None = None
    owners: list[str] | None = None


@dataclass(slots=True)
class ABIParameterResult:
    name: str = ""
    type: str = ""


@dataclass(slots=True)
class ABIMethodResult:
    name: str = ""
    return_type: str = ""
    parameters: list[ABIParameterResult] = field(default_factory=list)


@dataclass(slots=True)
class ABIEventResult:
    value: int = 0
    name: str = ""
    return_type: str = ""
    description: str = ""


@dataclass(slots=True)
class ContractResult:
    name: str = ""
    address: str = ""
    script: str = ""
    owner: str | None = None
    methods: list[ABIMethodResult] | None = None
    events: list[ABIEventResult] | None = None


@dataclass(slots=True)
class AuctionResult:
    creator_address: str = ""
    chain_address: str = ""
    start_date: int = 0
    end_date: int = 0
    base_symbol: str = ""
    quote_symbol: str = ""
    token_id: str = ""
    price: str = "0"
    end_price: str = "0"
    extension_period: str = "0"
    type: str = ""
    rom: str = ""
    ram: str = ""
    listing_fee: str = "0"
    current_winner: str = ""


@dataclass(slots=True)
class ChannelResult:
    creator_address: str = ""
    target_address: str = ""
    name: str = ""
    chain: str = ""
    creation_time: int = 0
    symbol: str = ""
    fee: str = "0"
    balance: str = "0"
    active: bool = False
    index: int = 0


@dataclass(slots=True)
class ReceiptResult:
    nexus: str = ""
    channel: str = ""
    index: str = ""
    timestamp: int = 0
    sender: str = ""
    receiver: str = ""
    script: str = ""


@dataclass(slots=True)
class PeerResult:
    url: str = ""
    version: str = ""
    flags: str = ""
    fee: str = "0"
    pow: int = 0


@dataclass(slots=True)
class ValidatorResult:
    address: str = ""
    type: str = ""


@dataclass(slots=True)
class SwapResult:
    source_platform: str = ""
    source_chain: str = ""
    source_hash: str = ""
    source_address: str = ""
    destination_platform: str = ""
    destination_chain: str = ""
    destination_hash: str = ""
    destination_address: str = ""
    symbol: str = ""
    value: str = "0"


@dataclass(slots=True)
class BuildInfoResult:
    version: str = ""
    commit: str = ""
    build_time_utc: str = ""


@dataclass(slots=True)
class PhantasmaVMConfigResult:
    is_stored: bool = False
    feature_level: int = 0
    gas_constructor: str = "0"
    gas_nexus: str = "0"
    gas_organization: str = "0"
    gas_account: str = "0"
    gas_leaderboard: str = "0"
    gas_standard: str = "0"
    gas_oracle: str = "0"
    fuel_per_contract_deploy: str = "0"


class JsonRpcClient:
    """Small JSON-RPC 2.0 client with strict response validation."""

    def __init__(self, endpoint: str, *, session: HTTPSession | None = None, timeout: float = 30.0) -> None:
        self.endpoint = endpoint
        self.session = session or requests.Session()
        self.timeout = timeout
        self._next_id = 0

    def call(self, method: str, *params: Any) -> Any:
        request_id = str(self._next_id)
        self._next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": list(params)}

        response = self.session.post(self.endpoint, json=payload, timeout=self.timeout)
        try:
            body = response.json()
        except Exception as exc:
            if getattr(response, "status_code", 200) >= 400:
                raise RPCError(f"HTTP {response.status_code} from RPC endpoint") from exc
            raise RPCError("RPC response is not valid JSON") from exc
        if not isinstance(body, Mapping):
            raise RPCError("RPC response must be an object")

        if "id" not in body or body["id"] is None:
            raise RPCError(f"RPC response missing id for request {request_id!r}")
        wire_id = body["id"]
        if str(wire_id) != request_id:
            raise RPCError(f"RPC response id mismatch: got {wire_id!r}, expected {request_id!r}")
        error = body.get("error")
        if error:
            if isinstance(error, Mapping):
                raise RPCError(
                    str(error.get("message", "RPC error")),
                    code=_optional_int(error.get("code")),
                    data=error.get("data"),
                )
            raise RPCError(str(error))
        if "result" not in body:
            raise RPCError("RPC response missing result")
        return body["result"]


class PhantasmaRPC:
    """Typed client for Phantasma JSON-RPC endpoints."""

    def __init__(self, endpoint: str, *, session: HTTPSession | None = None, timeout: float = 30.0) -> None:
        self.client = JsonRpcClient(endpoint, session=session, timeout=timeout)

    @classmethod
    def mainnet(cls) -> PhantasmaRPC:
        return cls("https://pharpc1.phantasma.info/rpc")

    @classmethod
    def testnet(cls) -> PhantasmaRPC:
        return cls("https://testnet.phantasma.info/rpc")

    def call(self, method: str, *params: Any) -> Any:
        return self.client.call(method, *params)

    def get_platforms(self) -> list[PlatformResult]:
        return _decode_list(PlatformResult, self.call("getPlatforms"))

    def get_account(
        self,
        address: str,
        *,
        extended: bool = False,
        check_address_reserved_byte: bool | None = None,
        address_type: str | None = None,
    ) -> AccountResult:
        params = _optional_params(address, extended, check_address_reserved_byte, address_type)
        return _decode_dataclass(AccountResult, self.call("getAccount", *params))

    def get_accounts(
        self,
        addresses: Sequence[str] | str,
        *,
        extended: bool = False,
        check_address_reserved_byte: bool | None = None,
        address_type: str | None = None,
    ) -> list[AccountResult]:
        text = addresses if isinstance(addresses, str) else ",".join(addresses)
        params = _optional_params(text, extended, check_address_reserved_byte, address_type)
        return _decode_list(AccountResult, self.call("getAccounts", *params))

    def get_accounts_text(self, addresses: str, *, extended: bool = False) -> list[AccountResult]:
        return self.get_accounts(addresses, extended=extended)

    def get_account_with_address_type(
        self, address: str, extended: bool, check_address_reserved_byte: bool, address_type: str
    ) -> AccountResult:
        return self.get_account(
            address,
            extended=extended,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def get_accounts_with_address_type(
        self, addresses: Sequence[str] | str, extended: bool, check_address_reserved_byte: bool, address_type: str
    ) -> list[AccountResult]:
        return self.get_accounts(
            addresses,
            extended=extended,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def lookup_name(self, name: str) -> str:
        return str(self.call("lookUpName", name))

    def look_up_name(self, name: str) -> str:
        return self.lookup_name(name)

    def get_address_transactions(
        self, address: str, page: int, page_size: int
    ) -> PaginatedResult[AddressTransactionsResult]:
        return _decode_paginated(
            AddressTransactionsResult, self.call("getAddressTransactions", address, page, page_size)
        )

    def get_address_transaction_count(self, address: str, chain: str = "main") -> int:
        return _coerce_int(self.call("getAddressTransactionCount", address, chain))

    def get_block_by_height(self, chain: str, height: int | str) -> BlockResult:
        return _decode_dataclass(BlockResult, self.call("getBlockByHeight", chain, height))

    def get_block_height(self, chain: str = "main") -> int:
        return _coerce_int(self.call("getBlockHeight", chain))

    def get_block_transaction_count_by_hash(self, block_hash: str, chain: str = "main") -> int:
        return _coerce_int(self.call("getBlockTransactionCountByHash", chain, block_hash))

    def get_block_transaction_count_by_hash_on_chain(self, chain: str, block_hash: str) -> int:
        return self.get_block_transaction_count_by_hash(block_hash, chain)

    def get_block_by_hash(self, block_hash: str) -> BlockResult:
        return _decode_dataclass(BlockResult, self.call("getBlockByHash", block_hash))

    def get_latest_block(self, chain: str = "main") -> BlockResult:
        return _decode_dataclass(BlockResult, self.call("getLatestBlock", chain))

    def get_transaction_by_block_hash_and_index(
        self, block_hash: str, index: int, *, chain: str = "main"
    ) -> TransactionResult:
        return _decode_dataclass(
            TransactionResult, self.call("getTransactionByBlockHashAndIndex", chain, block_hash, index)
        )

    def get_transaction_by_block_hash_and_index_on_chain(
        self, chain: str, block_hash: str, index: int
    ) -> TransactionResult:
        return self.get_transaction_by_block_hash_and_index(block_hash, index, chain=chain)

    def get_transaction(self, tx_hash: str) -> TransactionResult:
        return _decode_dataclass(TransactionResult, self.call("getTransaction", tx_hash))

    def get_chains(self, *, extended: bool = True) -> list[ChainResult]:
        return _decode_list(ChainResult, self.call("getChains", extended))

    def get_chain(self, name: str = "main", *, extended: bool = True) -> ChainResult:
        return _decode_dataclass(ChainResult, self.call("getChain", name, extended))

    def get_nexus(self, *, extended: bool = True) -> NexusResult:
        return _decode_dataclass(NexusResult, self.call("getNexus", extended))

    def get_contract(self, contract_name: str, chain: str = "main") -> ContractResult:
        return _decode_dataclass(ContractResult, self.call("getContract", chain, contract_name))

    def get_contract_by_name(self, chain: str, contract_name: str) -> ContractResult:
        return self.get_contract(contract_name, chain)

    def get_contract_by_address(self, chain: str, contract_address: str) -> ContractResult:
        return _decode_dataclass(ContractResult, self.call("getContractByAddress", chain, contract_address))

    def get_contracts(self, chain: str = "main", *, extended: bool = True) -> list[ContractResult]:
        return _decode_list(ContractResult, self.call("getContracts", chain, extended))

    def get_organization(self, organization_id: str, *, extended: bool = True) -> OrganizationResult:
        return _decode_dataclass(OrganizationResult, self.call("getOrganization", organization_id, extended))

    def get_organization_by_name(self, name: str, *, extended: bool = True) -> OrganizationResult:
        return _decode_dataclass(OrganizationResult, self.call("getOrganizationByName", name, extended))

    def get_organizations(self, *, extended: bool = False) -> list[OrganizationResult]:
        return _decode_list(OrganizationResult, self.call("getOrganizations", extended))

    def get_leaderboard(self, name: str) -> LeaderboardResult:
        return _decode_dataclass(LeaderboardResult, self.call("getLeaderboard", name))

    def get_token(self, symbol: str, *, extended: bool = True, carbon_token_id: int = 0) -> TokenResult:
        return _decode_dataclass(TokenResult, self.call("getToken", symbol, extended, carbon_token_id))

    def get_token_with_id(self, symbol: str, extended: bool, carbon_token_id: int) -> TokenResult:
        return self.get_token(symbol, extended=extended, carbon_token_id=carbon_token_id)

    def get_tokens(
        self, *, extended: bool = True, owner_address: str | None = None, address_type: str | None = None
    ) -> list[TokenResult]:
        params = _optional_params(extended, owner_address, address_type)
        return _decode_list(TokenResult, self.call("getTokens", *params))

    def get_tokens_by_owner(self, owner_address: str, *, extended: bool = True) -> list[TokenResult]:
        return self.get_tokens(extended=extended, owner_address=owner_address)

    def get_tokens_by_owner_with_address_type(
        self, owner_address: str, address_type: str, *, extended: bool = True
    ) -> list[TokenResult]:
        return self.get_tokens(extended=extended, owner_address=owner_address, address_type=address_type)

    def get_tokens_as_map(self, *, extended: bool = True) -> dict[str, TokenResult]:
        return {token.symbol: token for token in self.get_tokens(extended=extended)}

    def get_token_data(self, symbol: str, nft_id: str) -> TokenDataResult:
        return _decode_dataclass(TokenDataResult, self.call("getTokenData", symbol, nft_id))

    def get_token_balance(
        self,
        address: str,
        symbol: str,
        chain: str = "main",
        *,
        check_address_reserved_byte: bool | None = None,
        address_type: str | None = None,
    ) -> BalanceResult:
        params = _optional_params(address, symbol, chain, check_address_reserved_byte, address_type)
        return _decode_dataclass(BalanceResult, self.call("getTokenBalance", *params))

    def get_token_balance_checked(
        self, address: str, symbol: str, chain: str, check_address_reserved_byte: bool
    ) -> BalanceResult:
        return self.get_token_balance(address, symbol, chain, check_address_reserved_byte=check_address_reserved_byte)

    def get_token_balance_with_address_type(
        self, address: str, symbol: str, chain: str, check_address_reserved_byte: bool, address_type: str
    ) -> BalanceResult:
        return self.get_token_balance(
            address,
            symbol,
            chain,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def get_token_series(
        self, symbol: str, carbon_token_id: int = 0, page_size: int = 100, cursor: str = ""
    ) -> CursorPaginatedResult[list[TokenSeriesResult]]:
        return _decode_cursor(
            TokenSeriesResult, self.call("getTokenSeries", symbol, carbon_token_id, page_size, cursor)
        )

    def get_token_series_by_id(
        self, symbol: str, *, carbon_token_id: int = 0, series_id: str = "", carbon_series_id: int = 0
    ) -> TokenSeriesResult:
        return _decode_dataclass(
            TokenSeriesResult, self.call("getTokenSeriesById", symbol, carbon_token_id, series_id, carbon_series_id)
        )

    def get_token_nfts(
        self,
        carbon_token_id: int,
        carbon_series_id: int = 0,
        *,
        series_id: str = "",
        page_size: int = 100,
        cursor: str = "",
        extended: bool = True,
    ) -> CursorPaginatedResult[list[TokenDataResult]]:
        return _decode_cursor(
            TokenDataResult,
            self.call("getTokenNFTs", carbon_token_id, carbon_series_id, page_size, cursor, extended, series_id),
        )

    def get_token_nfts_with_series_id(
        self,
        carbon_token_id: int,
        carbon_series_id: int,
        series_id: str,
        page_size: int,
        cursor: str,
        extended: bool,
    ) -> CursorPaginatedResult[list[TokenDataResult]]:
        return self.get_token_nfts(
            carbon_token_id,
            carbon_series_id,
            series_id=series_id,
            page_size=page_size,
            cursor=cursor,
            extended=extended,
        )

    def get_account_fungible_tokens(
        self,
        account: str,
        token_symbol: str = "",
        carbon_token_id: int = 0,
        *,
        page_size: int = 100,
        cursor: str = "",
        check_address_reserved_byte: bool = False,
        address_type: str | None = None,
    ) -> CursorPaginatedResult[list[BalanceResult]]:
        params = _optional_params(
            account, token_symbol, carbon_token_id, page_size, cursor, check_address_reserved_byte, address_type
        )
        return _decode_cursor(BalanceResult, self.call("getAccountFungibleTokens", *params))

    def get_account_fungible_tokens_with_address_type(
        self,
        account: str,
        token_symbol: str,
        carbon_token_id: int,
        page_size: int,
        cursor: str,
        check_address_reserved_byte: bool,
        address_type: str,
    ) -> CursorPaginatedResult[list[BalanceResult]]:
        return self.get_account_fungible_tokens(
            account,
            token_symbol,
            carbon_token_id,
            page_size=page_size,
            cursor=cursor,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def get_account_nfts(
        self,
        account: str,
        token_symbol: str = "",
        carbon_token_id: int = 0,
        carbon_series_id: int = 0,
        *,
        page_size: int = 100,
        cursor: str = "",
        extended: bool = True,
        check_address_reserved_byte: bool = False,
        address_type: str | None = None,
    ) -> CursorPaginatedResult[list[TokenDataResult]]:
        params = _optional_params(
            account,
            token_symbol,
            carbon_token_id,
            carbon_series_id,
            page_size,
            cursor,
            extended,
            check_address_reserved_byte,
            address_type,
        )
        return _decode_cursor(TokenDataResult, self.call("getAccountNFTs", *params))

    def get_account_nfts_with_address_type(
        self,
        account: str,
        token_symbol: str,
        carbon_token_id: int,
        carbon_series_id: int,
        page_size: int,
        cursor: str,
        extended: bool,
        check_address_reserved_byte: bool,
        address_type: str,
    ) -> CursorPaginatedResult[list[TokenDataResult]]:
        return self.get_account_nfts(
            account,
            token_symbol,
            carbon_token_id,
            carbon_series_id,
            page_size=page_size,
            cursor=cursor,
            extended=extended,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def get_account_owned_tokens(
        self,
        account: str,
        token_symbol: str = "",
        carbon_token_id: int = 0,
        *,
        page_size: int = 100,
        cursor: str = "",
        check_address_reserved_byte: bool = False,
        address_type: str | None = None,
    ) -> CursorPaginatedResult[list[TokenResult]]:
        params = _optional_params(
            account, token_symbol, carbon_token_id, page_size, cursor, check_address_reserved_byte, address_type
        )
        return _decode_cursor(TokenResult, self.call("getAccountOwnedTokens", *params))

    def get_account_owned_tokens_with_address_type(
        self,
        account: str,
        token_symbol: str,
        carbon_token_id: int,
        page_size: int,
        cursor: str,
        check_address_reserved_byte: bool,
        address_type: str,
    ) -> CursorPaginatedResult[list[TokenResult]]:
        return self.get_account_owned_tokens(
            account,
            token_symbol,
            carbon_token_id,
            page_size=page_size,
            cursor=cursor,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def get_account_owned_token_series(
        self,
        account: str,
        token_symbol: str = "",
        carbon_token_id: int = 0,
        *,
        page_size: int = 100,
        cursor: str = "",
        check_address_reserved_byte: bool = False,
        address_type: str | None = None,
    ) -> CursorPaginatedResult[list[TokenSeriesResult]]:
        params = _optional_params(
            account, token_symbol, carbon_token_id, page_size, cursor, check_address_reserved_byte, address_type
        )
        return _decode_cursor(TokenSeriesResult, self.call("getAccountOwnedTokenSeries", *params))

    def get_account_owned_token_series_with_address_type(
        self,
        account: str,
        token_symbol: str,
        carbon_token_id: int,
        page_size: int,
        cursor: str,
        check_address_reserved_byte: bool,
        address_type: str,
    ) -> CursorPaginatedResult[list[TokenSeriesResult]]:
        return self.get_account_owned_token_series(
            account,
            token_symbol,
            carbon_token_id,
            page_size=page_size,
            cursor=cursor,
            check_address_reserved_byte=check_address_reserved_byte,
            address_type=address_type,
        )

    def get_auctions_count(self, chain: str, symbol: str) -> int:
        return _coerce_int(self.call("getAuctionsCount", chain, symbol))

    def get_auctions(self, chain: str, symbol: str, page: int, page_size: int) -> PaginatedResult[list[AuctionResult]]:
        return _decode_paginated_list(AuctionResult, self.call("getAuctions", chain, symbol, page, page_size))

    def get_auction(self, chain: str, symbol: str, token_id: str) -> AuctionResult:
        return _decode_dataclass(AuctionResult, self.call("getAuction", chain, symbol, token_id))

    def get_nft(self, symbol: str, nft_id: str, *, extended: bool = True) -> TokenDataResult:
        return _decode_dataclass(TokenDataResult, self.call("getNFT", symbol, nft_id, extended))

    def get_nfts(self, symbol: str, nft_ids: Sequence[str] | str, *, extended: bool = True) -> list[TokenDataResult]:
        text = nft_ids if isinstance(nft_ids, str) else ",".join(nft_ids)
        return _decode_list(TokenDataResult, self.call("getNFTs", symbol, text, extended))

    def get_nfts_text(self, symbol: str, nft_ids: str, *, extended: bool = True) -> list[TokenDataResult]:
        return self.get_nfts(symbol, nft_ids, extended=extended)

    def get_archive(self, archive_hash: str) -> ArchiveResult:
        return _decode_dataclass(ArchiveResult, self.call("getArchive", archive_hash))

    def write_archive(self, archive_hash: str, block_index: int, block_content: bytes | str) -> bool:
        content = base64.b64encode(block_content).decode("ascii") if isinstance(block_content, bytes) else block_content
        return _coerce_bool(self.call("writeArchive", archive_hash, block_index, content))

    def write_archive_base64(self, archive_hash: str, block_index: int, block_content: str) -> bool:
        return self.write_archive(archive_hash, block_index, block_content)

    def read_archive(self, archive_hash: str, block_index: int) -> str:
        return str(self.call("readArchive", archive_hash, block_index))

    def invoke_raw_script(self, chain: str, script_hex: str) -> ScriptResult:
        return _decode_dataclass(ScriptResult, self.call("invokeRawScript", chain, script_hex))

    def send_raw_transaction(self, tx: Transaction | bytes | str) -> str:
        if isinstance(tx, Transaction):
            payload = tx.to_bytes().hex()
        elif isinstance(tx, bytes):
            payload = tx.hex()
        else:
            payload = tx
        result = self.call("sendRawTransaction", payload)
        return _extract_hash_result(result)

    def send_carbon_transaction(self, tx: bytes | str) -> str:
        payload = tx.hex() if isinstance(tx, bytes) else tx
        result = self.call("sendCarbonTransaction", payload)
        return _extract_hash_result(result)

    def sign_and_send_transaction(
        self,
        keys: PhantasmaKeys,
        nexus: str,
        script: bytes,
        chain: str = "main",
        payload: bytes | str = b"",
        *,
        expiration: int | None = None,
    ) -> str:
        raw_payload = payload.encode("utf-8") if isinstance(payload, str) else payload
        tx = Transaction(nexus, chain, script, expiration or int(time.time()) + 20 * 60, raw_payload)
        tx.sign(keys)
        return self.send_raw_transaction(tx)

    def sign_and_send_built_transaction(self, tx: Transaction, keys: PhantasmaKeys) -> str:
        tx.sign(keys)
        return self.send_raw_transaction(tx)

    def sign_carbon_transaction(self, msg: TxMsg, keys: PhantasmaKeys) -> SignedTxMsg:
        return sign_tx_msg(msg, keys)

    def sign_and_send_carbon_transaction(self, msg: TxMsg, keys: PhantasmaKeys) -> str:
        return self.send_carbon_transaction(serialize(self.sign_carbon_transaction(msg, keys)))

    def get_version(self) -> BuildInfoResult:
        return _decode_dataclass(BuildInfoResult, self.call("getVersion"))

    def get_phantasma_vm_config(self, chain: str = "main") -> PhantasmaVMConfigResult:
        return _decode_dataclass(PhantasmaVMConfigResult, self.call("getPhantasmaVmConfig", chain))

    def parse_create_token_result(self, result_hex: str) -> int:
        return parse_create_token_result(result_hex)

    def parse_create_token_series_result(self, result_hex: str) -> int:
        return parse_create_token_series_result(result_hex)


def convert_decimals(raw: str | int, decimals: int, separator: str = ".") -> str:
    value = str(raw)
    negative = value.startswith("-")
    if negative:
        value = value[1:]
    value = value.zfill(decimals + 1)
    integer = value[:-decimals] if decimals else value
    fraction = value[-decimals:] if decimals else ""
    fraction = fraction.rstrip("0")
    out = integer if not fraction else integer + separator + fraction
    return "-" + out if negative else out


def _extract_hash_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, Mapping):
        error = result.get("error")
        if error:
            raise RPCError(str(error))
        if "hash" in result:
            return str(result["hash"])
    raise RPCError("send transaction response does not contain a hash")


def _optional_params(*values: Any) -> list[Any]:
    params = list(values)
    while params and params[-1] is None:
        params.pop()
    return params


def _decode_list(cls: type[T], raw: Any) -> list[T]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise RPCError(f"expected array for {cls.__name__} list")
    return [_decode_dataclass(cls, item) for item in raw]


def _decode_paginated(cls: type[T], raw: Any) -> PaginatedResult[T]:
    if not isinstance(raw, Mapping):
        raise RPCError("expected object for paginated result")
    page = _coerce_int(raw.get("page", 0))
    page_size = _coerce_int(raw.get("pageSize", raw.get("page_size", 0)))
    total = _coerce_int(raw.get("total", 0))
    total_pages = _coerce_int(raw.get("totalPages", raw.get("total_pages", 0)))
    result = _decode_dataclass(cls, raw.get("result", {}))
    return PaginatedResult(page=page, page_size=page_size, total=total, total_pages=total_pages, result=result)


def _decode_paginated_list(cls: type[T], raw: Any) -> PaginatedResult[list[T]]:
    if not isinstance(raw, Mapping):
        raise RPCError("expected object for paginated result")
    page = _coerce_int(raw.get("page", 0))
    page_size = _coerce_int(raw.get("pageSize", raw.get("page_size", 0)))
    total = _coerce_int(raw.get("total", 0))
    total_pages = _coerce_int(raw.get("totalPages", raw.get("total_pages", 0)))
    result = _decode_list(cls, raw.get("result", []))
    return PaginatedResult(page=page, page_size=page_size, total=total, total_pages=total_pages, result=result)


def _decode_cursor(cls: type[T], raw: Any) -> CursorPaginatedResult[list[T]]:
    if not isinstance(raw, Mapping):
        raise RPCError("expected object for cursor-paginated result")
    result = _decode_list(cls, raw.get("result", []))
    cursor = raw.get("cursor")
    return CursorPaginatedResult(result=result, cursor=None if cursor is None else str(cursor))


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RPCError(f"expected integer-compatible RPC value, got {value!r}") from exc


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1"}:
            return True
        if lowered in {"false", "0"}:
            return False
    if isinstance(value, int):
        return value != 0
    raise RPCError(f"expected boolean-compatible RPC value, got {value!r}")


def _decode_dataclass(cls: type[T], raw: Any) -> T:
    if not is_dataclass(cls):
        return cast(T, raw)
    if not isinstance(raw, Mapping):
        raise RPCError(f"expected object for {cls.__name__}")
    kwargs: dict[str, Any] = {}
    type_hints = get_type_hints(cls)
    for field_info in fields(cls):
        wire_key = _snake_to_camel(field_info.name)
        if field_info.name in raw:
            value = raw[field_info.name]
        elif wire_key in raw:
            value = raw[wire_key]
        else:
            continue
        kwargs[field_info.name] = _decode_value(type_hints.get(field_info.name, field_info.type), value)
    return cast(T, cls(**kwargs))


def _decode_value(target_type: Any, value: Any) -> Any:
    origin = get_origin(target_type)
    args = get_args(target_type)
    if origin is list and args:
        return [_decode_value(args[0], item) for item in (value or [])]
    if origin is type(None):
        return None
    if args and type(None) in args:
        inner = next(arg for arg in args if arg is not type(None))
        return None if value is None else _decode_value(inner, value)
    if isinstance(target_type, type) and is_dataclass(target_type):
        return _decode_dataclass(target_type, value)
    if target_type is Bytes32:
        return Bytes32(value)
    return value


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
