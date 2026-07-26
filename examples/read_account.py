"""Read-only RPC account lookup."""

from __future__ import annotations

import os

from phantasma_py.rpc import PhantasmaRPC

# The node rejects anything outside 1..100, so pages are requested at the documented maximum.
PAGE_SIZE = 100


def main() -> None:
    endpoint = os.environ.get("PHANTASMA_RPC", "https://pharpc1.phantasma.info/rpc")
    address = os.environ["PHANTASMA_ADDRESS"]

    rpc = PhantasmaRPC(endpoint)

    # Lightweight overview: registered name and staking only, no balance or NFT id lists.
    info = rpc.get_account_info(address)
    print(f"{info.address} ({info.name}): staked {info.stake.decimal_amount()} SOUL")

    # Balances arrive through cursor pagination; an empty cursor marks the last page.
    cursor = ""
    while True:
        page = rpc.get_account_fungible_tokens(address, page_size=PAGE_SIZE, cursor=cursor)
        for balance in page.result or []:
            print(f"  {balance.decimal_amount()} {balance.symbol}")
        if not page.cursor:
            break
        cursor = page.cursor


if __name__ == "__main__":
    main()
