# Phantasma Python SDK

Typed Python SDK for the Phantasma blockchain with support for the Phoenix chain
update.

The package provides JSON-RPC access, transaction building and signing, VM script
helpers, Ed25519 keys/signatures, and Carbon wire-format support.

The public API uses Python naming conventions, dataclasses, exceptions, and type
hints. Fixture tests lock shared VM and Carbon wire formats against reference SDK
vectors.

## Requirements

- Python 3.11 or newer
- `cryptography`
- `requests`

Development uses `uv`, `ruff`, `mypy`, and `pytest`.

## Install

```sh
pip install phantasma-sdk-py
```

For local development:

```sh
uv sync --extra dev
just check
```

## Modules

- `phantasma_py.crypto`: addresses, hashes, WIF keys, Ed25519 signatures
- `phantasma_py.vm`: VM objects, opcodes, and `ScriptBuilder`
- `phantasma_py.transaction`: VM script transaction serialization/signing
- `phantasma_py.rpc`: JSON-RPC client and typed response dataclasses
- `phantasma_py.carbon`: Carbon primitives, VM schemas, module call args, token builders, and transaction messages

## RPC

```python
from phantasma_py.rpc import PhantasmaRPC

rpc = PhantasmaRPC.mainnet()
account = rpc.get_account("P...")
balance = account.get_token_balance("SOUL", decimals=8)

print(balance.decimal_amount())
```

`JsonRpcClient` validates JSON-RPC response ids, propagates RPC errors as
`RPCError`, and accepts endpoints that echo numeric ids as strings.

## Keys And Signatures

```python
from phantasma_py.crypto import PhantasmaKeys

keys = PhantasmaKeys.from_wif("...")
signature = keys.sign(b"message")

assert signature.verify(b"message", [keys.address])
```

Address parsing rejects malformed Base58/checksum data. `Address.from_text("NULL")`
and `Address.null()` produce the system null address.

## VM Scripts

```python
from phantasma_py.crypto import Address, PhantasmaKeys
from phantasma_py.vm import ScriptBuilder

keys = PhantasmaKeys.from_wif("...")

script = (
    ScriptBuilder.begin()
    .allow_gas(keys.address, Address.null(), gas_price=10_000, gas_limit=210_000)
    .call_contract("stake", "GetStake", keys.address)
    .spend_gas(keys.address)
    .end_script()
)
```

`end_script()` raises `BuilderError` if labels or user input are invalid.
`end_script_with_error()` returns `(script, error)` for callers that prefer an
explicit checked path.

## VM Script Transactions

```python
from phantasma_py.crypto import PhantasmaKeys
from phantasma_py.transaction import Transaction
from phantasma_py.vm import ScriptBuilder

keys = PhantasmaKeys.from_wif("...")
script = ScriptBuilder.begin().call_interop("Runtime.Time").end_script()

tx = Transaction("mainnet", "main", script, expiration=1_754_000_000)
tx.sign(keys)

raw_hex = tx.to_bytes().hex()
```

Broadcasting is intentionally separate from signing:

```python
tx_hash = rpc.send_raw_transaction(raw_hex)
```

Do not run broadcasting examples without explicit credentials, funds, and an
endpoint you intend to use.

## Carbon

Carbon serialization uses fixed-width little-endian integers, zero-terminated
strings, fixed byte types, compact signed Int256 values, and typed transaction
payloads. Use `serialize()` and `deserialize()` for stable wire round-trips.

```python
from phantasma_py.carbon import (
    Bytes32,
    IntX,
    build_token_info,
    build_token_metadata,
    prepare_standard_token_schemas,
    serialize,
)

owner = Bytes32()
schemas = prepare_standard_token_schemas(shared_metadata=False)
token = build_token_info(
    symbol="ART",
    max_supply=IntX(0),
    is_nft=True,
    decimals=0,
    owner=owner,
    metadata=build_token_metadata(
        {
            "name": "Art Token",
            "icon": "data:image/png;base64,AA==",
            "url": "https://example.invalid/art",
            "description": "Example token metadata",
        }
    ),
    token_schemas=serialize(schemas),
)

payload = serialize(token)
```

Carbon token and NFT helpers validate required metadata, token symbol casing,
standard schema fields, Carbon NFT address packing, and result parsing. Token
symbols follow the Carbon token-module rule of uppercase ASCII letters `A-Z`.

Carbon transaction signing is available without going through RPC:

```python
from phantasma_py.carbon import sign_and_serialize_tx_msg_hex
from phantasma_py.crypto import PhantasmaKeys

keys = PhantasmaKeys.from_wif("...")
raw_hex = sign_and_serialize_tx_msg_hex(tx_msg, keys)
```

## Development

```sh
just f          # format and autofix
just f-check    # verify formatting and lint
just typecheck  # strict mypy
just test       # pytest
just build      # package build
just check      # all checks above
```

The shared Carbon vector fixture in `tests/fixtures/carbon_vectors.tsv` is
copied from the Go SDK and should stay byte-for-byte compatible across SDKs.
