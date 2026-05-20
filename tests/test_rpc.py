import pytest

from phantasma_py.errors import RPCError
from phantasma_py.rpc import (
    AccountResult,
    ArchiveResult,
    BlockResult,
    ChainResult,
    CursorPaginatedResult,
    PhantasmaRPC,
    ScriptResult,
    TokenDataResult,
    TokenResult,
    TokenSeriesResult,
    TransactionResult,
    convert_decimals,
)


class FakeResponse:
    def __init__(self, body: dict, status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code

    def json(self) -> dict:
        return self._body


class BrokenJsonResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def json(self) -> dict:
        raise ValueError("not json")


class RawResponse:
    def __init__(self, body: bytes, status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code
        self.headers = {"content-length": str(len(body))}
        self.encoding = "utf-8"

    def iter_content(self, chunk_size: int = 65536):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]

    def close(self) -> None:
        pass


class FakeSession:
    def __init__(self, result: object, *, response_id: object = "0", include_id: bool = True) -> None:
        self.result = result
        self.response_id = response_id
        self.include_id = include_id
        self.requests: list[dict] = []

    def post(self, url: str, *, json: dict, timeout: float, stream: bool = False) -> FakeResponse:
        self.requests.append({"url": url, "json": json, "timeout": timeout, "stream": stream})
        body = {"jsonrpc": "2.0", "result": self.result}
        if self.include_id:
            body["id"] = self.response_id
        return FakeResponse(body)


class ScriptedSession:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.requests: list[dict] = []

    def post(self, url: str, *, json: dict, timeout: float, stream: bool = False) -> FakeResponse:
        self.requests.append({"url": url, "json": json, "timeout": timeout, "stream": stream})
        return FakeResponse(self.responses.pop(0))


class ErrorSession:
    def __init__(self, body: dict, status_code: int = 400) -> None:
        self.body = body
        self.status_code = status_code
        self.requests: list[dict] = []

    def post(self, url: str, *, json: dict, timeout: float, stream: bool = False) -> FakeResponse:
        self.requests.append({"url": url, "json": json, "timeout": timeout, "stream": stream})
        return FakeResponse(self.body, self.status_code)


class BrokenJsonSession:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def post(self, url: str, *, json: dict, timeout: float, stream: bool = False) -> BrokenJsonResponse:
        return BrokenJsonResponse(self.status_code)


class RawSession:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def post(self, url: str, *, json: dict, timeout: float, stream: bool = False) -> RawResponse:
        return RawResponse(self.body)


class SpyRPC(PhantasmaRPC):
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def call(self, method: str, *params: object) -> object:
        self.calls.append((method, params))
        return self.result


def test_rpc_wraps_params_and_accepts_string_response_ids() -> None:
    # Current RPC may echo ids as strings; the client should accept that and still validate mismatches.
    session = FakeSession({"address": "Pabc", "balances": [{"symbol": "SOUL", "amount": "123", "decimals": 8}]})
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)

    account = rpc.get_account("Pabc")
    assert isinstance(account, AccountResult)
    assert account.balances[0].symbol == "SOUL"
    assert session.requests[0]["json"]["params"] == ["Pabc", False]
    assert session.requests[0]["stream"] is True


def test_rpc_accepts_numeric_response_id_echo() -> None:
    # Some transports decode the echoed JSON-RPC id as a number; it is valid only when it matches the request id.
    session = FakeSession({"version": "1.0.0", "commit": "abc"}, response_id=0)
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)

    assert rpc.get_version().commit == "abc"


def test_rpc_rejects_response_id_mismatch() -> None:
    # Mismatched ids must fail before callers can consume an unrelated response body.
    session = FakeSession({}, response_id="99")
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)
    with pytest.raises(RPCError):
        rpc.lookup_name("alice")


@pytest.mark.parametrize("response_id", [0, "0", "2", {"unexpected": "object"}])
def test_rpc_rejects_stale_or_wrong_response_ids_after_counter_advances(response_id: object) -> None:
    session = ScriptedSession(
        [
            {"jsonrpc": "2.0", "id": "0", "result": {"version": "1.0.0", "commit": "abc"}},
            {"jsonrpc": "2.0", "id": response_id, "result": {"version": "1.0.1", "commit": "def"}},
        ]
    )
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)

    assert rpc.get_version().commit == "abc"
    with pytest.raises(RPCError, match="id mismatch"):
        rpc.get_version()

    assert session.requests[0]["json"]["id"] == "0"
    assert session.requests[1]["json"]["id"] == "1"


@pytest.mark.parametrize("response_id, include_id", [(None, True), ("0", False)])
def test_rpc_rejects_missing_or_null_response_id(response_id: object, include_id: bool) -> None:
    # Missing and null ids are not correlated with this request and must fail closed.
    session = FakeSession({}, response_id=response_id, include_id=include_id)
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)
    with pytest.raises(RPCError, match="missing id"):
        rpc.lookup_name("alice")


def test_rpc_decodes_json_rpc_errors_from_http_error_status() -> None:
    session = ErrorSession({"jsonrpc": "2.0", "id": "0", "error": {"code": -32603, "message": "Execution failed"}})
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)
    with pytest.raises(RPCError, match="Execution failed") as exc:
        rpc.get_version()
    assert exc.value.code == -32603


def test_rpc_rejects_id_mismatch_before_json_rpc_error_body() -> None:
    session = ErrorSession(
        {"jsonrpc": "2.0", "id": "1", "error": {"code": -32603, "message": "Execution failed"}},
        status_code=500,
    )
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)

    with pytest.raises(RPCError, match="id mismatch") as exc:
        rpc.get_version()

    assert exc.value.code is None
    assert "Execution failed" not in str(exc.value)


def test_rpc_sends_empty_params_for_no_argument_calls() -> None:
    session = FakeSession({"version": "1.0.0", "commit": "abc"})
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)
    assert rpc.get_version().commit == "abc"
    assert session.requests[-1]["json"]["params"] == []


def test_rpc_rejects_malformed_response_shapes() -> None:
    for body, match in [
        ([], "must be an object"),
        ({"jsonrpc": "2.0", "id": "0"}, "missing result"),
        ({"jsonrpc": "2.0", "id": "0", "error": "plain error"}, "plain error"),
    ]:
        rpc = PhantasmaRPC("http://localhost/rpc", session=ErrorSession(body, status_code=200))
        with pytest.raises(RPCError, match=match):
            rpc.get_version()


def test_rpc_reports_non_json_http_and_rpc_bodies() -> None:
    rpc = PhantasmaRPC("http://localhost/rpc", session=BrokenJsonSession(status_code=200))
    with pytest.raises(RPCError, match="not valid JSON"):
        rpc.get_version()

    rpc = PhantasmaRPC("http://localhost/rpc", session=BrokenJsonSession(status_code=500))
    with pytest.raises(RPCError, match="HTTP 500"):
        rpc.get_version()


def test_rpc_rejects_oversized_response_body() -> None:
    body = b'{"jsonrpc":"2.0","id":"0","result":"0123456789ABCDEF"}'
    rpc = PhantasmaRPC("http://localhost/rpc", session=RawSession(body), max_response_bytes=len(body) - 1)

    with pytest.raises(RPCError, match="exceeds"):
        rpc.get_version()


def test_rpc_decodes_current_series_shape() -> None:
    # TokenSeriesResult must use current Carbon-aware field names from the RPC and reference SDKs.
    session = FakeSession(
        {"seriesId": "1", "carbonTokenId": "7", "carbonSeriesId": "8", "metadata": [{"key": "name", "value": "A"}]}
    )
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)

    series = rpc.get_token_series_by_id("ART", series_id="1")
    assert isinstance(series, TokenSeriesResult)
    assert series.series_id == "1"
    assert series.carbon_token_id == "7"
    assert series.carbon_series_id == "8"
    assert series.metadata[0].key == "name"


def test_rpc_dtos_decode_current_response_shapes_without_stale_aliases() -> None:
    tx_payload = {
        "hash": "HASH",
        "chainAddress": "CHAIN",
        "timestamp": 123,
        "blockHeight": 456,
        "blockHash": "BLOCK",
        "script": "",
        "payload": "CAFE",
        "carbonTxType": 9,
        "carbonTxData": "BEEF",
        "debugComment": "mint",
        "events": [{"address": "Pevent", "contract": "gas", "kind": "GasEscrow", "name": "GasEscrow", "data": "00"}],
        "extendedEvents": [{"address": "Pevent", "contract": "market", "kind": "Order", "data": {"id": "7"}}],
        "state": "Halt",
        "result": "",
        "fee": "2600000",
        "signatures": [{"kind": "Ed25519", "data": "AA"}],
        "sender": "Psender",
        "gasPayer": "Pgas",
        "gasTarget": "Ptarget",
        "gasPrice": "1",
        "gasLimit": "100000000",
        "expiration": 789,
    }
    tx = PhantasmaRPC("http://localhost/rpc", session=FakeSession(tx_payload)).get_transaction("HASH")
    assert isinstance(tx, TransactionResult)
    assert tx.carbon_tx_type == 9
    assert tx.carbon_tx_data == "BEEF"
    assert tx.debug_comment == "mint"
    assert tx.sender == "Psender"
    assert tx.gas_payer == "Pgas"
    assert tx.gas_target == "Ptarget"
    assert tx.gas_price == "1"
    assert tx.gas_limit == "100000000"
    assert tx.events[0].name == "GasEscrow"
    assert tx.extended_events[0].data == {"id": "7"}
    assert tx.signatures[0].kind == "Ed25519"
    assert tx.signatures[0].data == "AA"

    stale_tx = dict(tx_payload)
    stale_tx["signatures"] = [{"Kind": "Ed25519", "Data": "AA"}]
    stale_tx["events"] = [{"address": "Pevent", "contract": "gas", "Kind": "GasEscrow", "Data": "00"}]
    stale = PhantasmaRPC("http://localhost/rpc", session=FakeSession(stale_tx)).get_transaction("HASH")
    assert stale.signatures[0].kind == ""
    assert stale.signatures[0].data == ""
    assert stale.events[0].kind == ""
    assert stale.events[0].data == ""

    block = PhantasmaRPC(
        "http://localhost/rpc",
        session=FakeSession({"hash": "BLOCK", "height": 456, "txs": [tx_payload], "reward": "0"}),
    ).get_block_by_hash("BLOCK")
    assert isinstance(block, BlockResult)
    assert block.events is None
    assert block.oracles is None
    assert block.txs[0].carbon_tx_type == 9

    token_payload = {
        "symbol": "CROWN",
        "name": "Crown",
        "decimals": 0,
        "currentSupply": "1",
        "maxSupply": "0",
        "burnedSupply": "0",
        "address": "S-token",
        "owner": "Powner",
        "flags": "Transferable, NonFungible",
        "carbonId": "4",
        "metadata": [{"key": "name", "value": "Crown"}],
        "series": [{"seriesId": "0", "carbonTokenId": "4", "carbonSeriesId": "1"}],
    }
    token = PhantasmaRPC("http://localhost/rpc", session=FakeSession(token_payload)).get_token("CROWN")
    assert isinstance(token, TokenResult)
    assert token.carbon_id == "4"
    assert token.metadata is not None
    assert token.metadata[0].key == "name"
    assert token.series[0].series_id == "0"
    assert token.series[0].carbon_series_id == "1"
    assert token.script is None
    assert token.external is None
    assert token.price is None

    stale_token = dict(token_payload)
    stale_token["carbonID"] = "999"
    stale_token["metadata"] = [{"Key": "name", "Value": "Crown"}]
    stale_token.pop("carbonId")
    stale_decoded = PhantasmaRPC("http://localhost/rpc", session=FakeSession(stale_token)).get_token("CROWN")
    assert stale_decoded.carbon_id == ""
    assert stale_decoded.metadata is not None
    assert stale_decoded.metadata[0].key == ""
    assert stale_decoded.metadata[0].value == ""

    stale_metadata = dict(token_payload)
    stale_metadata["metadata"] = [{"Key": "name", "Value": "Crown"}]
    stale_metadata_decoded = PhantasmaRPC("http://localhost/rpc", session=FakeSession(stale_metadata)).get_token(
        "CROWN"
    )
    assert stale_metadata_decoded.metadata is not None
    assert stale_metadata_decoded.metadata[0].key == ""
    assert stale_metadata_decoded.metadata[0].value == ""

    nft_payload = {
        "id": "114421",
        "series": "0",
        "carbonTokenId": "4",
        "carbonSeriesId": "1",
        "carbonNftAddress": "ABCDEF",
        "mint": "1",
        "chainName": "main",
        "ownerAddress": "Powner",
        "creatorAddress": "Pcreator",
        "ram": "",
        "rom": "CAFE",
        "status": "Active",
        "infusion": [],
        "properties": [{"key": "name", "value": "Crown #1"}],
    }
    nft = PhantasmaRPC("http://localhost/rpc", session=FakeSession(nft_payload)).get_nft("CROWN", "114421")
    assert isinstance(nft, TokenDataResult)
    assert nft.id == "114421"
    assert nft.series == "0"
    assert nft.carbon_series_id == "1"
    assert nft.properties[0].value == "Crown #1"

    stale_nft = dict(nft_payload)
    stale_nft["ID"] = stale_nft.pop("id")
    stale_nft_decoded = PhantasmaRPC("http://localhost/rpc", session=FakeSession(stale_nft)).get_nft("CROWN", "114421")
    assert stale_nft_decoded.id == ""
    assert stale_nft_decoded.series == "0"

    chain = PhantasmaRPC("http://localhost/rpc", session=FakeSession({"height": 0})).get_chain("main")
    assert isinstance(chain, ChainResult)
    assert chain.height == 0
    assert chain.name is None
    assert chain.contracts is None

    archive = PhantasmaRPC(
        "http://localhost/rpc", session=FakeSession({"time": 0, "size": 0, "blockCount": 0})
    ).get_archive("hash")
    assert isinstance(archive, ArchiveResult)
    assert archive.name is None
    assert archive.missing_blocks is None

    script = PhantasmaRPC(
        "http://localhost/rpc",
        session=FakeSession({"events": [], "result": "0601", "results": ["0601"], "oracles": []}),
    ).invoke_raw_script("main", "0B")
    assert script.error is None
    assert script.state is None
    assert script.gas is None


def test_rpc_decodes_cursor_paginated_series() -> None:
    session = FakeSession(
        {"result": [{"seriesId": "1", "carbonTokenId": "7", "carbonSeriesId": "8"}], "cursor": "next"}
    )
    rpc = PhantasmaRPC("http://localhost/rpc", session=session)

    page = rpc.get_token_series("ART", carbon_token_id=7, page_size=50, cursor="")
    assert isinstance(page, CursorPaginatedResult)
    assert page.result is not None
    assert page.result[0].series_id == "1"
    assert page.cursor == "next"
    assert session.requests[0]["json"]["params"] == ["ART", 7, 50, ""]


def test_rpc_alias_methods_preserve_reference_parameter_order() -> None:
    count_session = FakeSession(0)
    count_rpc = PhantasmaRPC("http://localhost/rpc", session=count_session)
    count_rpc.get_block_transaction_count_by_hash_on_chain("side", "abc")
    assert count_session.requests[-1]["json"]["method"] == "getBlockTransactionCountByHash"
    assert count_session.requests[-1]["json"]["params"] == ["side", "abc"]

    page_session = FakeSession({"result": [], "cursor": ""})
    page_rpc = PhantasmaRPC("http://localhost/rpc", session=page_session)
    page_rpc.get_token_nfts_with_series_id(7, 8, "series", 50, "cursor", False)
    assert page_session.requests[-1]["json"]["method"] == "getTokenNFTs"
    assert page_session.requests[-1]["json"]["params"] == [7, 8, 50, "cursor", False, "series"]

    account_session = FakeSession({"result": [], "cursor": ""})
    account_rpc = PhantasmaRPC("http://localhost/rpc", session=account_session)
    account_rpc.get_account_nfts_with_address_type("Pabc", "ART", 7, 8, 10, "", True, False, "User")
    assert account_session.requests[-1]["json"]["method"] == "getAccountNFTs"
    assert account_session.requests[-1]["json"]["params"] == ["Pabc", "ART", 7, 8, 10, "", True, False, "User"]


def test_rpc_wrapper_parameter_shapes_cover_public_alias_surface() -> None:
    cases = [
        (SpyRPC([]), lambda rpc: rpc.get_platforms(), "getPlatforms", ()),
        (SpyRPC([{}]), lambda rpc: rpc.get_chains(extended=False), "getChains", (False,)),
        (SpyRPC({}), lambda rpc: rpc.get_chain("side", extended=False), "getChain", ("side", False)),
        (SpyRPC({}), lambda rpc: rpc.get_nexus(extended=False), "getNexus", (False,)),
        (
            SpyRPC({"balances": []}),
            lambda rpc: rpc.get_account_with_address_type("Pabc", True, False, "User"),
            "getAccount",
            ("Pabc", True, False, "User"),
        ),
        (SpyRPC([]), lambda rpc: rpc.get_accounts_text("P1,P2", extended=True), "getAccounts", ("P1,P2", True)),
        (SpyRPC("Pabc"), lambda rpc: rpc.look_up_name("alice"), "lookUpName", ("alice",)),
        (
            SpyRPC({"page": 1, "pageSize": 10, "total": 0, "totalPages": 0, "result": {}}),
            lambda rpc: rpc.get_address_transactions("Pabc", 1, 10),
            "getAddressTransactions",
            ("Pabc", 1, 10),
        ),
        (
            SpyRPC(12),
            lambda rpc: rpc.get_address_transaction_count("Pabc", "main"),
            "getAddressTransactionCount",
            ("Pabc", "main"),
        ),
        (SpyRPC({}), lambda rpc: rpc.get_block_by_height("main", 7), "getBlockByHeight", ("main", 7)),
        (SpyRPC({}), lambda rpc: rpc.get_block_by_hash("hash"), "getBlockByHash", ("hash",)),
        (SpyRPC({}), lambda rpc: rpc.get_latest_block("main"), "getLatestBlock", ("main",)),
        (SpyRPC({}), lambda rpc: rpc.get_transaction("hash"), "getTransaction", ("hash",)),
        (SpyRPC({}), lambda rpc: rpc.get_contract_by_address("main", "Sabc"), "getContractByAddress", ("main", "Sabc")),
        (SpyRPC([]), lambda rpc: rpc.get_organizations(extended=True), "getOrganizations", (True,)),
        (SpyRPC({}), lambda rpc: rpc.get_leaderboard("board"), "getLeaderboard", ("board",)),
        (SpyRPC({}), lambda rpc: rpc.get_token_with_id("SOUL", True, 2), "getToken", ("SOUL", True, 2)),
        (
            SpyRPC([]),
            lambda rpc: rpc.get_tokens_by_owner_with_address_type("Pabc", "User", extended=False),
            "getTokens",
            (False, "Pabc", "User"),
        ),
        (SpyRPC({}), lambda rpc: rpc.get_token_data("ART", "1"), "getTokenData", ("ART", "1")),
        (
            SpyRPC({}),
            lambda rpc: rpc.get_token_balance_with_address_type("Pabc", "SOUL", "main", False, "User"),
            "getTokenBalance",
            ("Pabc", "SOUL", "main", False, "User"),
        ),
        (
            SpyRPC({"result": [], "cursor": ""}),
            lambda rpc: rpc.get_account_owned_tokens("Pabc"),
            "getAccountOwnedTokens",
            ("Pabc", "", 0, 100, "", False),
        ),
        (SpyRPC(0), lambda rpc: rpc.get_auctions_count("main", "ART"), "getAuctionsCount", ("main", "ART")),
        (
            SpyRPC({"page": 1, "pageSize": 10, "total": 0, "totalPages": 0, "result": []}),
            lambda rpc: rpc.get_auctions("main", "ART", 1, 10),
            "getAuctions",
            ("main", "ART", 1, 10),
        ),
        (SpyRPC({}), lambda rpc: rpc.get_auction("main", "ART", "1"), "getAuction", ("main", "ART", "1")),
        (SpyRPC({}), lambda rpc: rpc.get_nft("ART", "1", extended=False), "getNFT", ("ART", "1", False)),
        (SpyRPC([]), lambda rpc: rpc.get_nfts_text("ART", "1,2", extended=False), "getNFTs", ("ART", "1,2", False)),
        (SpyRPC({}), lambda rpc: rpc.get_archive("hash"), "getArchive", ("hash",)),
        (SpyRPC(True), lambda rpc: rpc.write_archive("hash", 1, b"abc"), "writeArchive", ("hash", 1, "YWJj")),
        (SpyRPC("data"), lambda rpc: rpc.read_archive("hash", 2), "readArchive", ("hash", 2)),
        (SpyRPC({}), lambda rpc: rpc.invoke_raw_script("main", "0B"), "invokeRawScript", ("main", "0B")),
    ]

    for rpc, action, method, params in cases:
        action(rpc)
        assert rpc.calls[-1] == (method, params)


def test_script_result_decode_result() -> None:
    # VM result decoding is part of RPC result parsing, not caller helper code.
    result = ScriptResult(result="030101")
    assert result.decode_result().as_number() == 1


def test_convert_decimals() -> None:
    assert convert_decimals("123456789", 8) == "1.23456789"
    assert convert_decimals("100000000", 8) == "1"


def test_rpc_decode_helpers_fail_closed_on_hostile_shapes() -> None:
    with pytest.raises(RPCError, match="expected array"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession({})).get_tokens()
    with pytest.raises(RPCError, match="expected object for paginated"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession([])).get_address_transactions("Pabc", 1, 1)
    with pytest.raises(RPCError, match="expected object for cursor-paginated"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession([])).get_token_series("ART")
    with pytest.raises(RPCError, match="expected integer-compatible"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession("abc")).get_block_height()
    with pytest.raises(RPCError, match="expected boolean-compatible"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession("maybe")).write_archive_base64("hash", 0, "")


def test_send_transaction_hash_extraction_paths() -> None:
    rpc = PhantasmaRPC("http://localhost/rpc", session=FakeSession("ABC"))
    assert rpc.send_raw_transaction("00") == "ABC"

    rpc = PhantasmaRPC("http://localhost/rpc", session=FakeSession({"hash": "DEF"}))
    assert rpc.send_carbon_transaction(b"\x00") == "DEF"

    with pytest.raises(RPCError, match="bad"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession({"error": "bad"})).send_raw_transaction("00")
    with pytest.raises(RPCError, match="does not contain a hash"):
        PhantasmaRPC("http://localhost/rpc", session=FakeSession({})).send_raw_transaction("00")
