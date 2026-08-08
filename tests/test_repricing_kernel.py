"""Guards for the repricing kernel.

The kernel's headline is a bias with a sign. These tests pin the two mechanisms
apart and pin the behavioural band open at zero, because the estimate behind it
is not identified and a kernel reported without that band would be
self-refuting.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pt_debt.repricing.kernel import (
    REFIXING_PROFILE_PATH,
    KernelInputs,
    bias_table,
    build_kernel,
    fiscal_translation,
    geometric_kernel,
    refixing_comparison,
    wam_implied_kernel,
)
from pt_debt_interest.exceptions import ValidationError

INPUTS = KernelInputs(
    average_residual_maturity_years=7.52,
    fixed_rate_share=0.858,
    retail_share_of_stock=0.1539,
    retail_variable_share=0.1336,
    retail_fixed_share=0.0203,
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
        retail_variable_share=0.12,
        retail_fixed_share=0.03,
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


class TestPortfolioPartition:
    """Opening-stock classes must be mutually exclusive and sum to one.

    The earlier construction subtracted *all* retail debt from the fixed-rate
    track while treating the *entire* non-fixed residual as a wholesale reset
    block. Savings Certificates are retail and variable-rate, so they were
    removed from a track they were never in and counted in another.
    """

    SPLIT = KernelInputs(
        average_residual_maturity_years=7.52,
        fixed_rate_share=0.858,
        retail_share_of_stock=0.154,
        retail_variable_share=0.1336,
        retail_fixed_share=0.0203,
    )

    def test_classes_sum_to_one(self) -> None:
        assert sum(self.SPLIT.partition().values()) == pytest.approx(1.0)

    def test_retail_split_must_reconcile_to_total_retail_share(self) -> None:
        bad = KernelInputs(
            average_residual_maturity_years=7.52,
            fixed_rate_share=0.858,
            retail_share_of_stock=0.154,
            retail_variable_share=0.10,
            retail_fixed_share=0.02,
        )
        with pytest.raises(ValidationError, match="retail split must sum"):
            bad.partition()

    def test_no_class_is_negative(self) -> None:
        assert all(value >= 0.0 for value in self.SPLIT.partition().values())

    def test_variable_retail_is_not_taken_from_the_fixed_track(self) -> None:
        """The specific double count that motivated the partition."""
        classes = self.SPLIT.partition()
        # Only the *fixed* retail block comes out of the fixed-rate share.
        assert classes["wholesale_fixed"] == pytest.approx(0.858 - 0.0203)
        # Variable retail comes out of the non-fixed residual instead.
        assert classes["wholesale_floating"] == pytest.approx(
            (1.0 - 0.858) - 0.1336, abs=1e-9
        )

    def test_an_inconsistent_split_is_rejected(self) -> None:
        """More fixed retail than fixed debt cannot be partitioned."""
        bad = KernelInputs(
            average_residual_maturity_years=7.0,
            fixed_rate_share=0.10,
            retail_share_of_stock=0.50,
            retail_fixed_share=0.50,
        )
        with pytest.raises(ValidationError, match="negative classes"):
            bad.partition()

    def test_behaviour_column_is_flow_only(self) -> None:
        """It previously carried a contractual base that was not behavioural."""
        kernel = build_kernel(self.SPLIT, 100.0, 0.0)
        assert (kernel["behavioural_share"] == 0.0).all()

    def test_contractual_covers_both_fixed_classes(self) -> None:
        classes = self.SPLIT.partition()
        kernel = build_kernel(self.SPLIT, 100.0, 0.0, horizons=(1,))
        expected = (classes["wholesale_fixed"] + classes["retail_fixed"]) / (
            2.0 * 7.52
        )
        assert float(kernel["contractual_share"].iloc[0]) == pytest.approx(expected)

    def test_retail_variable_resets_on_its_own_clock(self) -> None:
        """Quarterly Euribor indexation, not the general wholesale cycle."""
        slow = build_kernel(
            self.SPLIT, 100.0, 0.0, horizons=(1,), retail_reset_cycle_years=10.0
        )
        fast = build_kernel(self.SPLIT, 100.0, 0.0, horizons=(1,))
        assert float(slow["reset_share"].iloc[0]) < float(fast["reset_share"].iloc[0])


class TestRefixingComparison:
    """The imposed shape can be checked against IGCP's own refixing profile."""

    INPUTS = KernelInputs(
        average_residual_maturity_years=7.52,
        fixed_rate_share=0.858,
        retail_share_of_stock=0.154,
        retail_variable_share=0.1336,
        retail_fixed_share=0.0203,
    )

    @staticmethod
    def _profile() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "bracket_lower_years": [0.0, 1.0, 3.0],
                "bracket_upper_years": [1.0, 3.0, 5.0],
                "share_of_portfolio": [0.20, 0.15, 0.12],
            }
        )

    def test_it_reports_one_row_per_bracket(self) -> None:
        result = refixing_comparison(self._profile(), self.INPUTS)
        assert len(result) == 3
        assert {"published_share", "kernel_implied_share", "difference_pp"} <= set(
            result.columns
        )

    def test_missing_columns_are_rejected(self) -> None:
        """A half-digitised chart must fail loudly, not compare against nothing."""
        with pytest.raises(ValidationError, match="missing columns"):
            refixing_comparison(pd.DataFrame({"bracket_lower_years": [0.0]}), self.INPUTS)

    def test_noninteger_bracket_edges_are_rejected(self) -> None:
        profile = self._profile()
        profile.loc[0, "bracket_upper_years"] = 1.5
        with pytest.raises(ValidationError, match="integer-year edges"):
            refixing_comparison(profile, self.INPUTS)

    def test_the_official_profile_is_shipped_with_source_metadata(self) -> None:
        profile_path = Path(REFIXING_PROFILE_PATH)
        assert profile_path.is_file()

        profile = pd.read_csv(profile_path)
        assert set(_REFIXING_COLUMNS_FOR_TEST) <= set(profile.columns)
        assert profile["reference_date"].nunique() == 1
        assert profile["reference_date"].iloc[0] == "2026-03-31"
        assert profile["share_of_portfolio"].to_list() == pytest.approx(
            [0.252, 0.509]
        )
        assert profile["source_url"].str.contains("igcp.pt").all()

    def test_the_official_profile_runs_through_the_comparison(self) -> None:
        profile = pd.read_csv(REFIXING_PROFILE_PATH)
        result = refixing_comparison(profile, self.INPUTS)
        assert len(result) == 2
        assert result["published_share"].to_list() == pytest.approx([0.252, 0.509])


_REFIXING_COLUMNS_FOR_TEST = {
    "reference_date",
    "bracket_lower_years",
    "bracket_upper_years",
    "share_of_portfolio",
    "source_title",
    "source_url",
    "source_detail",
}
