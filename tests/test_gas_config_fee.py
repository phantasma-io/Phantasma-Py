"""Gas-model-v2 GasConfig wire format + Tier-1 fee estimator tests.

The chain serializes the 10 v2 config fields only for version >= 1; the version-0 image is
frozen forever (historical replay). Expected fee numbers are hand-derived from the chain
billing formula and pinned as constants so any formula regression fails loudly. The same
fixtures and expectations exist in every SDK (parity suite).
"""

from __future__ import annotations

import dataclasses

import pytest

from phantasma_py import (
    CarbonReader,
    CarbonWriter,
    GasConfig,
    GasConfigDataResult,
    GasConfigResult,
    NativeFeeKind,
    RPCError,
    SerializationError,
    envelope_bytes_for,
    estimate_native_fee,
)


def live_v1_config() -> GasConfig:
    """The mainnet v1 values (feeMultiplier 10000, transfer 10 units, byte fee 250000, escrow 2)."""
    return GasConfig(
        version=0,
        max_name_length=32,
        max_token_symbol_length=10,
        fee_shift=0,
        max_structure_size=65536,
        fee_multiplier=10_000,
        gas_token_id=2,
        data_token_id=1,
        minimum_gas_offer=10,
        data_escrow_per_row=2,
        gas_fee_transfer=10,
        gas_fee_query=2,
        gas_fee_create_token_base=10_000_000_000,
        gas_fee_create_token_symbol=10_000_000_000,
        gas_fee_create_token_series=2_500_000_000,
        gas_fee_per_byte=250_000,
        gas_fee_register_name=10_000_000_000_000,
        gas_burn_ratio_mul=1,
    )


def v2_config() -> GasConfig:
    """The spec activation-package values for the v2 tail."""
    config = live_v1_config()
    config.version = 1
    config.data_escrow_per_row = 200_000
    config.minimum_gas_bill = 10_000_000
    config.policy_fee_create_token_base = 100_000_000_000_000
    config.policy_fee_create_token_symbol = 100_000_000_000_000
    config.policy_fee_create_token_series = 25_000_000_000_000
    config.policy_fee_register_name = 100_000_000_000_000_000
    config.legacy_data_escrow_per_row = 2
    return config


def serialize(config: GasConfig) -> bytes:
    writer = CarbonWriter()
    config.write_carbon(writer)
    return writer.bytes()


class TestGasConfigWireFormat:
    def test_v0_keeps_legacy_113_byte_layout(self) -> None:
        # Any growth of the version-0 image would corrupt every historical block image.
        assert len(serialize(live_v1_config())) == 113

    def test_v2_appends_66_byte_tail_after_unchanged_head(self) -> None:
        v2_bytes = serialize(v2_config())
        assert len(v2_bytes) == 179

        v0_twin = v2_config()
        v0_twin.version = 0  # same head values, version-0 layout
        v0_bytes = serialize(v0_twin)
        assert len(v0_bytes) == 113

        assert v2_bytes[0] == 1
        assert v0_bytes[0] == 0
        # The tail is a pure wire extension: the head encoding must be untouched.
        assert v2_bytes[1:113] == v0_bytes[1:113]

    def test_v2_roundtrip_preserves_all_fields(self) -> None:
        original = v2_config()
        decoded = GasConfig.read_carbon(CarbonReader(serialize(original)))

        assert dataclasses.asdict(decoded) == dataclasses.asdict(original)
        assert decoded.has_gas_model_v2

    def test_v0_read_zeroes_v2_fields(self) -> None:
        # Consumers must never see stale tail values on a v1 chain.
        decoded = GasConfig.read_carbon(CarbonReader(serialize(live_v1_config())))

        assert not decoded.has_gas_model_v2
        assert decoded.minimum_gas_bill == 0
        assert decoded.policy_fee_create_token_base == 0
        assert decoded.legacy_data_escrow_per_row == 0

    def test_truncated_v2_image_fails_to_parse(self) -> None:
        # Never silently produce a config with zeroed v2 prices (free product actions).
        truncated = serialize(v2_config())[:113]
        with pytest.raises(SerializationError):
            GasConfig.read_carbon(CarbonReader(truncated))


class TestEstimateNativeFee:
    def test_v1_transfer_existing_recipient_bills_work_only(self) -> None:
        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, live_v1_config(), fresh_rows=0)

        assert estimate.expected_gas_bill == 100_000
        # stdFee shape: 2x min offer + work + flat 1 KiB byte allowance.
        assert estimate.max_gas == 10 * 2 + 100_000 + 1024 * 250_000
        assert estimate.max_data == 0

    def test_v1_transfer_defaults_include_one_fresh_row(self) -> None:
        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, live_v1_config())

        assert estimate.expected_gas_bill == 100_000 + 250_000
        assert estimate.max_data == 2

    def test_v2_transfer_default_envelope_bill(self) -> None:
        # Default envelope 512 + 1 fresh row: blockData 513 -> 12825 byte units + 10 work
        # units = 12835 units * 10000 = 128_350_000 kcal-base (above the 1e7 floor).
        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, v2_config())

        assert estimate.expected_gas_bill == 128_350_000
        assert estimate.max_gas == 128_350_000 + 128_350_000 // 4
        assert estimate.max_data == 200_000

    def test_v2_transfer_exact_envelope_bill(self) -> None:
        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, v2_config(), envelope_bytes=250, fresh_rows=0)

        assert estimate.expected_gas_bill == (10 + 250 * 25) * 10_000

    def test_v2_floor_applies_to_small_bills(self) -> None:
        config = v2_config()
        config.minimum_gas_bill = 10_000_000_000  # exaggerated floor above the computed bill

        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, config, envelope_bytes=250, fresh_rows=0)

        assert estimate.expected_gas_bill == 10_000_000_000
        assert estimate.max_gas >= 10_000_000_000

    def test_v2_nft_multi_transfer_scales_units_and_rows(self) -> None:
        # Under v2 each instance recreates its lookup row -> escrow allowance (count + 1) rows.
        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_NON_FUNGIBLE, v2_config(), count=5, envelope_bytes=300)

        # work 5*10 units + bytes (300 envelope + 6 rows) * 25 units, all * 10000.
        assert estimate.expected_gas_bill == (50 + 306 * 25) * 10_000
        assert estimate.max_data == 6 * 200_000

    def test_create_token_both_models(self) -> None:
        # v1 charges unit-priced product fees through the multiplier; v2 pays the direct
        # kcal-base policy fee (no multiplier) plus the byte fee for its envelope.
        v1 = estimate_native_fee(
            NativeFeeKind.CREATE_TOKEN, live_v1_config(), symbol_length=4, fresh_rows=0, envelope_bytes=1000
        )
        assert v1.expected_gas_bill == (10_000_000_000 + 1_250_000_000) * 10_000

        v2 = estimate_native_fee(
            NativeFeeKind.CREATE_TOKEN, v2_config(), symbol_length=4, fresh_rows=0, envelope_bytes=1000
        )
        policy = 100_000_000_000_000 + (100_000_000_000_000 >> 3)
        assert v2.expected_gas_bill == policy + 1000 * 25 * 10_000

    def test_register_name_length_discount(self) -> None:
        v1 = estimate_native_fee(
            NativeFeeKind.REGISTER_NAME, live_v1_config(), name_length=8, fresh_rows=0, envelope_bytes=300
        )
        v2 = estimate_native_fee(
            NativeFeeKind.REGISTER_NAME, v2_config(), name_length=8, fresh_rows=0, envelope_bytes=300
        )

        assert v1.expected_gas_bill == (10_000_000_000_000 >> 7) * 10_000
        assert v2.expected_gas_bill == (100_000_000_000_000_000 >> 7) + 300 * 25 * 10_000

    def test_script_kind_budgets_vm_allowance(self) -> None:
        # Default 5000 VM units exceeds every script in mainnet history (max 3392).
        estimate = estimate_native_fee(NativeFeeKind.SCRIPT, v2_config(), envelope_bytes=568, fresh_rows=0)

        # (5000 vm units + (568 + 512 events) * 25) * 10000
        assert estimate.expected_gas_bill == (5000 + 1080 * 25) * 10_000

    def test_envelope_bytes_follow_witness_layout(self) -> None:
        # Native kinds append bare 64-byte signatures; call/script kinds append a
        # length-prefixed 96-byte witness array (mirrors SignedTxMsg).
        assert envelope_bytes_for(NativeFeeKind.TRANSFER_FUNGIBLE, 150) == 150 + 64
        assert envelope_bytes_for(NativeFeeKind.TRANSFER_FUNGIBLE, 150, 2) == 150 + 128
        assert envelope_bytes_for(NativeFeeKind.CREATE_TOKEN, 900) == 900 + 4 + 96
        assert envelope_bytes_for(NativeFeeKind.SCRIPT, 500, 2) == 500 + 4 + 192

    def test_invalid_inputs_raise(self) -> None:
        # Impossible inputs are rejected instead of quoting fees the chain would never admit.
        with pytest.raises(ValueError):
            estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, live_v1_config(), count=0)
        with pytest.raises(ValueError):
            estimate_native_fee(NativeFeeKind.REGISTER_NAME, live_v1_config())
        with pytest.raises(ValueError):
            # max_token_symbol_length is 10
            estimate_native_fee(NativeFeeKind.CREATE_TOKEN, live_v1_config(), symbol_length=11)

    def test_oversized_fee_shift_zeroes_scaled_terms(self) -> None:
        # The chain clamps shifts >= 64 to a zero work delta; the estimator must match.
        config = live_v1_config()
        config.fee_shift = 64

        estimate = estimate_native_fee(NativeFeeKind.TRANSFER_FUNGIBLE, config, fresh_rows=0)

        assert estimate.expected_gas_bill == 0


class TestGasConfigResultDecoding:
    def v2_result(self) -> GasConfigResult:
        return GasConfigResult(
            gas_model_version=2,
            block_rate_target=2000,
            expiry_window=90_000,
            units_per_block_data_byte=25,
            gas_config=GasConfigDataResult(
                version=1,
                max_name_length=32,
                max_token_symbol_length=10,
                fee_shift=0,
                max_structure_size=65536,
                fee_multiplier="10000",
                gas_token_id="2",
                data_token_id="1",
                minimum_gas_offer="10",
                data_escrow_per_row="200000",
                gas_fee_transfer="10",
                gas_fee_query="2",
                gas_fee_create_token_base="10000000000",
                gas_fee_create_token_symbol="10000000000",
                gas_fee_create_token_series="2500000000",
                gas_fee_per_byte="250000",
                gas_fee_register_name="10000000000000",
                gas_burn_ratio_mul="1",
                gas_burn_ratio_shift=0,
                minimum_gas_bill="10000000",
                gas_producer_ratio_mul="0",
                gas_producer_ratio_shift=0,
                gas_dapp_ratio_mul="0",
                gas_dapp_ratio_shift=0,
                policy_fee_create_token_base="100000000000000",
                policy_fee_create_token_symbol="100000000000000",
                policy_fee_create_token_series="25000000000000",
                # > 2^53: must survive exactly because it rides a string.
                policy_fee_register_name="100000000000000000",
                legacy_data_escrow_per_row="2",
            ),
        )

    def test_v2_response_maps_to_gas_config(self) -> None:
        config = self.v2_result().to_gas_config()

        assert config.has_gas_model_v2
        assert config.data_escrow_per_row == 200_000
        assert config.minimum_gas_bill == 10_000_000
        assert config.policy_fee_register_name == 100_000_000_000_000_000
        assert config.legacy_data_escrow_per_row == 2

    def test_v1_response_zeroes_absent_v2_fields(self) -> None:
        result = self.v2_result()
        assert result.gas_config is not None
        result.gas_config.version = 0

        config = result.to_gas_config()

        assert not config.has_gas_model_v2
        # v2 strings are still present in this synthetic fixture, but a version-0 config must
        # ignore them: v1 semantics never read the tail.
        assert config.minimum_gas_bill == 0
        assert config.policy_fee_register_name == 0

    def test_v2_response_with_missing_tail_field_raises(self) -> None:
        # Estimating fees from silently zeroed v2 prices would produce rejected transactions.
        result = self.v2_result()
        assert result.gas_config is not None
        result.gas_config.minimum_gas_bill = None

        with pytest.raises(RPCError):
            result.to_gas_config()

    def test_missing_gas_config_section_raises(self) -> None:
        with pytest.raises(RPCError):
            GasConfigResult(gas_model_version=1).to_gas_config()
