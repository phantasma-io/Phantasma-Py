# Classic VM Scripts And Transactions

`phantasma_py.vm` and `phantasma_py.transaction` cover the script-based VM
transaction flow used by the current RPC.

## Script Builder

`ScriptBuilder` mirrors the VM bytecode contract from the reference SDKs while
using a chainable Python API.

```python
from phantasma_py.crypto import Address
from phantasma_py.vm import ScriptBuilder

script = (
    ScriptBuilder.begin()
    .allow_gas(Address.null(), Address.null(), 10_000, 210_000)
    .call_interop("Runtime.Time")
    .spend_gas(Address.null())
    .end_script()
)
```

Use `end_script()` when invalid scripts should raise `BuilderError`. Use
`end_script_with_error()` when handling untrusted user input and returning an
explicit error is preferable.

## Transactions

```python
from phantasma_py.crypto import PhantasmaKeys
from phantasma_py.transaction import Transaction

keys = PhantasmaKeys.from_wif("...")
tx = Transaction("mainnet", "main", script, expiration=1_754_000_000)
signature = tx.sign(keys)

assert signature.verify(tx.to_bytes(with_signatures=False), [keys.address])
```

`Transaction.hash` is computed from the unsigned signing payload. The signed wire
bytes include a variable-length signature list and can be submitted with
`PhantasmaRPC.send_raw_transaction()`.

Broadcasting requires funded keys and an endpoint chosen by the caller. The SDK
does not broadcast from examples or tests.
