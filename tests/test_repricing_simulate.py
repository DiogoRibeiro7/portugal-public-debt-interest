"""Invariants of the simulation and backtest equations.

The suite was dense around parsing and manuscript consistency and empty around
the equations that carry the paper's empirical claims. Two defects survived a
large test count because of it: the backtest built its kernel at zero shock,
which silences the behavioural channel entirely, and it applied each year's
yield to the whole cumulative repriced share, overwriting earlier cohorts.

These tests assert the economics, not that files exist.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pt_debt.repricing.kernel import KernelInputs, build_kernel
from pt_debt.repricing.simulate import (
    _vintage_rate,
    backtest,
    backtest_across_cuts,
    simulate_paths,
)
from pt_debt_interest.exceptions import ValidationError

INPUTS = KernelInputs(
    average_residual_maturity_years=7.2,
    fixed_rate_share=0.86,
    retail_share_of_stock=0.15,
    retail_variable_share=0.12,
    retail_fixed_share=0.03,
)


def _burden_frame(years: range, yields: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": list(years),
            "average_debt_interest_rate_pct": np.linspace(2.0, 2.4, len(list(years))),
            "ten_year_yield_pct": yields,
        }
    )


class TestVintageAccounting:
    """Cohorts keep the yield they repriced at."""

    def test_a_flat_yield_path_reproduces_the_cumulative_formula(self) -> None:
        """The old and new formulations agree only here; that pins the fix."""
        anchor = 2.0
        kernel = np.array([0.2, 0.35, 0.5])
        flat = np.full(3, 4.0)
        for index in range(3):
            vintage = _vintage_rate(anchor, kernel, flat, index)
            cumulative = anchor + kernel[index] * (flat[index] - anchor)
            assert vintage == pytest.approx(cumulative)

    def test_an_early_cohort_keeps_its_own_yield(self) -> None:
        """A later yield must not rewrite debt that already repriced."""
        anchor = 2.0
        kernel = np.array([0.5, 0.5])  # everything reprices in year one
        yields = np.array([3.0, 9.0])
        # Nothing reprices in year two, so year two's yield is irrelevant.
        assert _vintage_rate(anchor, kernel, yields, 1) == pytest.approx(
            _vintage_rate(anchor, kernel, yields, 0)
        )

    def test_the_naive_formula_would_have_differed(self) -> None:
        """Guard against a silent revert to the cumulative form."""
        anchor, kernel = 2.0, np.array([0.5, 0.5])
        yields = np.array([3.0, 9.0])
        naive = anchor + kernel[1] * (yields[1] - anchor)
        assert _vintage_rate(anchor, kernel, yields, 1) != pytest.approx(naive)

    def test_weights_sum_to_the_cumulative_kernel(self) -> None:
        anchor, kernel = 2.0, np.array([0.2, 0.45, 0.7])
        yields = np.array([5.0, 5.0, 5.0])
        rate = _vintage_rate(anchor, kernel, yields, 2)
        assert rate == pytest.approx((1 - 0.7) * anchor + 0.7 * 5.0)

    def test_a_zero_kernel_leaves_the_anchor_untouched(self) -> None:
        rate = _vintage_rate(2.0, np.zeros(3), np.array([9.0, 9.0, 9.0]), 2)
        assert rate == pytest.approx(2.0)


class TestBehaviouralChannelIsLive:
    """The response parameter must be able to change a prediction."""

    def test_the_kernel_is_inert_at_zero_shock(self) -> None:
        """Why the old backtest was silently behaviour-free."""
        at_zero = build_kernel(INPUTS, 0.0, 0.0, (1, 3))["repriced_share"]
        responsive = build_kernel(INPUTS, 0.0, 0.5, (1, 3))["repriced_share"]
        assert at_zero.equals(responsive)

    def test_a_nonzero_shock_makes_the_response_matter(self) -> None:
        flat = build_kernel(INPUTS, 150.0, 0.0, (1, 3))["repriced_share"]
        responsive = build_kernel(INPUTS, 150.0, 0.5, (1, 3))["repriced_share"]
        assert (responsive >= flat).all() and not responsive.equals(flat)

    def test_backtest_predictions_move_with_the_response(self) -> None:
        """The end-to-end version of the defect, with the right driver."""
        frame = _burden_frame(range(2015, 2025), [3.0 + 0.2 * i for i in range(10)])
        common = {"cut_year": 2020, "realised_spread_pp": 1.5}
        flat = backtest(frame, INPUTS, behavioural_response=0.0, **common)
        responsive = backtest(frame, INPUTS, behavioural_response=0.8, **common)
        estimated = flat["model"].eq("estimated_kernel")
        assert not np.allclose(
            flat.loc[estimated, "predicted_rate_pct"].to_numpy(),
            responsive.loc[estimated, "predicted_rate_pct"].to_numpy(),
        )

    def test_no_spread_leaves_the_behavioural_track_at_zero(self) -> None:
        """A wrong driver is worse than none, so none is the default.

        The coefficient is per point of competing-return spread. Without that
        variable there is nothing it can legitimately be applied to, and an
        earlier version substituted the gap between the ten-year benchmark and
        the effective rate -- a different object in different units.
        """
        frame = _burden_frame(range(2015, 2025), [3.0 + 0.2 * i for i in range(10)])
        flat = backtest(frame, INPUTS, cut_year=2020, behavioural_response=0.0)
        responsive = backtest(frame, INPUTS, cut_year=2020, behavioural_response=0.8)
        estimated = flat["model"].eq("estimated_kernel")
        assert np.allclose(
            flat.loc[estimated, "predicted_rate_pct"].to_numpy(),
            responsive.loc[estimated, "predicted_rate_pct"].to_numpy(),
        )

    def test_the_benchmark_is_unaffected_by_the_response(self) -> None:
        frame = _burden_frame(range(2015, 2025), [3.0 + 0.2 * i for i in range(10)])
        flat = backtest(frame, INPUTS, cut_year=2020, behavioural_response=0.0)
        responsive = backtest(frame, INPUTS, cut_year=2020, behavioural_response=0.8)
        wam = flat["model"].eq("wam_benchmark")
        assert np.allclose(
            flat.loc[wam, "predicted_rate_pct"].to_numpy(),
            responsive.loc[wam, "predicted_rate_pct"].to_numpy(),
        )


class TestNoLookAhead:
    """State must come from the cut date, not the end of the sample."""

    @staticmethod
    def _panel() -> pd.DataFrame:
        periods = pd.date_range("2010-01-31", "2024-12-31", freq="ME")
        return pd.DataFrame({"period": periods, "value": range(len(periods))})

    def test_each_cut_records_the_state_it_used(self) -> None:
        frame = _burden_frame(range(2010, 2025), [3.0] * 15)
        seen: list[pd.Timestamp] = []

        def state_at(as_of: pd.Timestamp) -> KernelInputs:
            seen.append(as_of)
            return INPUTS

        scores = backtest_across_cuts(
            frame, self._panel(), state_at, cut_years=(2014, 2018, 2021)
        )
        assert [stamp.year for stamp in seen] == [2014, 2018, 2021]
        recorded = sorted(scores["state_as_of"].unique())
        assert [value[:4] for value in recorded] == ["2014", "2018", "2021"]

    def test_a_cut_before_the_panel_starts_is_rejected(self) -> None:
        frame = _burden_frame(range(2010, 2025), [3.0] * 15)
        with pytest.raises(ValidationError):
            backtest_across_cuts(
                frame, self._panel(), lambda _: INPUTS, cut_years=(2005,)
            )


class TestSimulationInvariants:
    def test_zero_shock_gives_zero_incremental_burden(self) -> None:
        paths = simulate_paths(
            INPUTS,
            initial_rate_pct=2.4,
            debt_pct_gdp=90.0,
            nominal_gdp_mio_eur=250_000.0,
            shocks_bps=(0,),
        )
        assert paths["incremental_burden_pct_gdp"].abs().max() == pytest.approx(0.0)

    def test_a_larger_shock_raises_the_burden(self) -> None:
        paths = simulate_paths(
            INPUTS,
            initial_rate_pct=2.4,
            debt_pct_gdp=90.0,
            nominal_gdp_mio_eur=250_000.0,
            shocks_bps=(50, 100),
        )
        at = paths.loc[paths["growth_path"].eq("central")].groupby("shock_bps")[
            "incremental_burden_pct_gdp"
        ].max()
        assert at.loc[100] > at.loc[50]
