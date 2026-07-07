"""estimateTransaction response decoding + Tier-2 fee-estimate conversion.

The node serializes 64-bit amounts as decimal strings (JSON-number precision). A completed
estimate must convert into the same NativeFeeEstimate the Tier-1 estimator produces, so wallet
code consumes both tiers identically. The same fixtures exist in every SDK (parity suite).
"""

from __future__ import annotations

import pytest

from phantasma_py import EstimateTransactionResult, RPCError
from phantasma_py.rpc import _decode_dataclass

# Completed dry run: recommendations present, no abort. recommendedMaxGas deliberately exceeds
# 2^53 to pin the strings-not-numbers decision.
_COMPLETED = {
    "wouldAbort": False,
    "abortReason": "",
    "gasBillKcalBase": "10000000",
    "dataRows": "1",
    "dataEscrowAtoms": "200000",
    "dataRefundAtoms": "0",
    "recommendedMaxGas": "100000000000000000",
    "recommendedMaxData": "400000",
}

# Aborted dry run: the settled abort bill is still reported (aborts pay), recommendations are 0.
_ABORTED = {
    "wouldAbort": True,
    "abortReason": "gas fees [gas=3125 max=40]",
    "gasBillKcalBase": "40",
    "dataRows": "0",
    "dataEscrowAtoms": "0",
    "dataRefundAtoms": "0",
    "recommendedMaxGas": "0",
    "recommendedMaxData": "0",
}


def test_completed_estimate_converts() -> None:
    result = _decode_dataclass(EstimateTransactionResult, _COMPLETED)
    assert result.would_abort is False
    estimate = result.to_fee_estimate()
    # Above-2^53 value survives exactly because it rides a string.
    assert estimate.max_gas == 100_000_000_000_000_000
    assert estimate.max_data == 400_000
    assert estimate.expected_gas_bill == 10_000_000


def test_aborted_estimate_refuses_conversion() -> None:
    # An aborted simulation has no recommendations; converting must fail rather than yield zero
    # ceilings a wallet could sign with.
    result = _decode_dataclass(EstimateTransactionResult, _ABORTED)
    assert result.would_abort is True
    with pytest.raises(RPCError, match="gas fees"):
        result.to_fee_estimate()


def test_missing_field_fails() -> None:
    # A malformed server response (lost field) must not silently become a zero ceiling.
    result = _decode_dataclass(EstimateTransactionResult, {"wouldAbort": False})
    with pytest.raises(RPCError, match="recommendedMaxGas"):
        result.to_fee_estimate()
