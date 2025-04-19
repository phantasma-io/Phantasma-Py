import pytest
import responses
from phantasma_py import PhantasmaRPC

# RPC endpoint used by the SDK (requests will be intercepted by 'responses')
TEST_RPC_URL = "https://testnet.phantasma.info/rpc"

# Real RPC response for an invalid hash
REAL_ERROR_RESPONSE_INVALID_HASH = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "Code": -32603,
        "Message": "invalid transaction hash"
    }
}

# Real RPC response when transaction was not found
REAL_ERROR_RESPONSE_NOT_FOUND = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "Code": -32603,
        "Message": "Transaction not found"
    }
}

# Real successful RPC response
REAL_SUCCESS_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "hash": "A57614A26E47A7266FC2F50D18362F480C8BDEB6C2FD2482C1D8FAD31BA7A64C",
        "chainAddress": "S3d7TbZxtNPdXy11hfmBLJLYn67gZTG2ibL7fJBcVdihWU4",
        "timestamp": 1744908808,
        "blockHeight": 6441296,
        "blockHash": "34E5D4B02F38C0E5268CD170CC270453FAF1B542526CDC97487B8187555525E0",
        "script": "0D000303...",  # shortened for clarity
        "payload": "426C6F636B73",
        "debugComment": "",
        "events": [],
        "result": "",
        "fee": "461",
        "state": "Halt",
        "signatures": [],
        "sender": "P2KCeb65Fa8Rhfjjfroh5iA4K6jTEqKuYWfe8LnpeYBEx26",
        "gasPayer": "P2KCeb65Fa8Rhfjjfroh5iA4K6jTEqKuYWfe8LnpeYBEx26",
        "gasTarget": "S3d7TbZxtNPdXy11hfmBLJLYn67gZTG2ibL7fJBcVdihWU4",
        "gasPrice": "1",
        "gasLimit": "21000000000",
        "expiration": 1744908867
    }
}

@pytest.fixture
def rpc():
    return PhantasmaRPC(TEST_RPC_URL)


@responses.activate
def test_get_transaction_valid(rpc):
    # Simulate successful response from the RPC node
    responses.add(
        responses.POST,
        TEST_RPC_URL,
        json=REAL_SUCCESS_RESPONSE,
        status=200
    )

    tx_hash = "A57614A26E47A7266FC2F50D18362F480C8BDEB6C2FD2482C1D8FAD31BA7A64C"
    result = rpc.getTransaction(tx_hash)

    assert result["hash"] == tx_hash
    assert result["state"] == "Halt"


@responses.activate
def test_get_transaction_invalid_hash_error(rpc):
    # Simulate RPC error for malformed hash input
    responses.add(
        responses.POST,
        TEST_RPC_URL,
        json=REAL_ERROR_RESPONSE_INVALID_HASH,
        status=200
    )

    with pytest.raises(Exception) as excinfo:
        rpc.getTransaction("MALFORMED_TX")

    assert "invalid transaction hash" in str(excinfo.value)


@responses.activate
def test_get_transaction_not_found_error(rpc):
    # Simulate RPC error for non-existent transaction
    responses.add(
        responses.POST,
        TEST_RPC_URL,
        json=REAL_ERROR_RESPONSE_NOT_FOUND,
        status=200
    )

    with pytest.raises(Exception) as excinfo:
        rpc.getTransaction("A57614A26E47A7266FC2F50D18362F480C8BDEB6C2FD2482C1D8FAD31BA7A64D")

    assert "Transaction not found" in str(excinfo.value)
