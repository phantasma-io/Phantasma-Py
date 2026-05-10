# RPC Client

`phantasma_py.rpc` contains a small JSON-RPC 2.0 transport and typed response
models for the current Phantasma RPC surface used by the other SDKs.

## Client

```python
from phantasma_py.rpc import PhantasmaRPC

rpc = PhantasmaRPC("http://localhost:5172/rpc")
account = rpc.get_account("P...", extended=False)
```

The client sends positional parameters as JSON arrays and validates response ids.
Some endpoints echo ids as JSON strings even when the caller uses a numeric id;
the Python client compares ids by string value to stay compatible while still
rejecting mismatches.

## Errors

Transport and RPC failures raise `RPCError`.

```python
from phantasma_py.errors import RPCError

try:
    rpc.lookup_name("missing-name")
except RPCError as exc:
    print(exc.code, exc.data)
```

## Result Decoding

RPC objects are decoded into dataclasses such as `AccountResult`,
`TokenResult`, `TokenSeriesResult`, `BlockResult`, and `TransactionResult`.
Nested arrays are decoded as typed dataclass instances, not raw dictionaries.

`ScriptResult.decode_result()` and `decode_results(index)` parse VM object bytes
returned by script invocation endpoints.
