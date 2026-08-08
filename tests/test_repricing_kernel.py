"""Guards for the repricing kernel.

The kernel's headline is a bias with a sign. These tests pin the two mechanisms
apart and pin the behavioural band open at zero, because the estimate behind it
is a null and a kernel reported without that band would be self-refuting.
"""

from __future__ import annotations

import numpy as np
import pytest

from pt_debt.repricing.kernel import (
    KernelInputs,
    bias_table,
    build_kernel,
    fiscal_translation,
    geometric_kernel,
    wam_implied_kernel,
)
from pt_debt_interest.exceptions import ValidationError

INPUTS = KernelInputs(
    average_residual_maturity_years=7.52,
    fixed_rate_share=0.858,
    retail_share_of_stock=0.154,
)


def test_geometric_benchmark_is_memoryless() -> None:
    horizons = np.array([1.0, 2.0, 3.0])
    values = geometric_kernel(horizons, 7.52)
    unrepriced = 1.0 - values
    # A constant hazard means each year retires the same fraction of what is left.
    ratios = unrepriced[1:] / unrepriced[:-1]
    assert ratios == pytest.approx(ratios[0], rel=1e-9)
    assert values[0] == pytest.approx(1.0 / 7.52)


def test_kernel_components_sum_to_the_total() -> None:
    kernel = build_kernel(INPUTS, shock_bps=100, behavioural_response=0.0187)
    parts = (
        kernel["contractual_share"]
        + kernel["reset_share"]
        + kernel["behavioural_share"]
    )
    assert parts.to_numpy() == pytest.approx(kernel["repriced_share"].to_numpy())
    assert (kernel["repriced_share"] <= 1.0).all()
    assert (kernel["repriced_share"] >= 0.0).all()


def test_shape_bias_exists_without_any_behavioural_response() -> None:
    """Floating debt reprices without exiting; a maturity hazard cannot see it."""
    bias = bias_table(INPUTS, shock_bps=100, behavioural_response=0.0)
    one_year = bias.loc[bias["horizon_years"].eq(1)].iloc[0]
    assert one_year["shape_bias_pp"] > 0.0
    assert one_year["behaviour_bias_pp"] == pytest.approx(0.0)


def test_behavioural_band_is_open_at_zero() -> None:
    """The estimate is a null, so the low path must contribute nothing."""
    bias = bias_table(
        INPUTS,
        shock_bps=100,
        behavioural_response=0.0187,
        behavioural_low=-0.0084,
        behavioural_high=0.0499,
    )
    assert bias["behaviour_bias_low_pp"].abs().max() == pytest.approx(0.0)
    assert (bias["behaviour_bias_high_pp"] >= bias["behaviour_bias_pp"]).all()


def test_kernel_responds_to_the_shock() -> None:
    """The kernel is a function of the shock, not a portfolio constant."""
    unshocked = build_kernel(INPUTS, 0, 0.0187)["repriced_share"]
    shocked = build_kernel(INPUTS, 100, 0.0187)["repriced_share"]
    assert (shocked >= unshocked).all()
    assert (shocked > unshocked).any(), "the kernel is insensitive to the shock"


def test_fiscal_translation_scales_with_the_shock() -> None:
    bias = bias_table(INPUTS, shock_bps=100, behavioural_response=0.0)
    at_100 = fiscal_translation(bias, 89.70, 100, 306_749.6)
    at_200 = fiscal_translation(bias, 89.70, 200, 306_749.6)
    assert at_200["bias_interest_pct_gdp"].to_numpy() == pytest.approx(
        2.0 * at_100["bias_interest_pct_gdp"].to_numpy()
    )


def test_benchmark_matches_the_burden_paper_assumption() -> None:
    benchmark = wam_implied_kernel(INPUTS)
    assert benchmark["repriced_share"].iloc[0] == pytest.approx(
        1.0 / 7.52
    )


def test_invalid_inputs_are_refused() -> None:
    with pytest.raises(ValidationError):
        KernelInputs(0.0, 0.8, 0.1)
    with pytest.raises(ValidationError):
        KernelInputs(7.5, 1.2, 0.1)


class TestResetShockLoading:
    """Reset timing and shock loading are separate assumptions."""

    INPUTS = KernelInputs(
        average_residual_maturity_years=7.2,
        fixed_rate_share=0.86,
        retail_share_of_stock=0.15,
    )

    def test_unit_loading_leaves_the_two_shares_equal(self) -> None:
        """The default must change no existing result."""
        kernel = build_kernel(self.INPUTS, 100.0, 0.0)
        assert (kernel["repriced_share"] == kernel["shock_weighted_share"]).all()

    def test_partial_loading_reduces_shock_transmission(self) -> None:
        full = build_kernel(self.INPUTS, 100.0, 0.0)
        partial = build_kernel(self.INPUTS, 100.0, 0.0, reset_shock_loading=0.5)
        assert (
            partial["shock_weighted_share"] <= full["shock_weighted_share"]
        ).all()
        assert not partial["shock_weighted_share"].equals(full["shock_weighted_share"])

    def test_loading_does_not_move_physical_repricing(self) -> None:
        """A coupon still refreshes on schedule whatever it passes through."""
        full = build_kernel(self.INPUTS, 100.0, 0.0)
        partial = build_kernel(self.INPUTS, 100.0, 0.0, reset_shock_loading=0.25)
        assert (partial["repriced_share"] == full["repriced_share"]).all()

    def test_timing_and_loading_are_independent_levers(self) -> None:
        slower = build_kernel(self.INPUTS, 100.0, 0.0, reset_cycle_years=2.0)
        weaker = build_kernel(self.INPUTS, 100.0, 0.0, reset_shock_loading=0.5)
        # Slowing the clock moves the physical share; weakening loading does not.
        base = build_kernel(self.INPUTS, 100.0, 0.0)
        assert not slower["repriced_share"].equals(base["repriced_share"])
        assert weaker["repriced_share"].equals(base["repriced_share"])
