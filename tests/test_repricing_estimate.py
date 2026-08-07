"""Guards for repricing-model estimation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pt_debt.repricing.estimate import _moving_block_indices, monthly_retail_series
from pt_debt_interest.exceptions import ValidationError


class _HighStartGenerator:
    def __init__(self) -> None:
        self.high: int | None = None

    def integers(self, low: int, high: int, size: int | tuple[int, ...]) -> np.ndarray:
        self.high = high
        return np.full(size, high - 1)


def test_moving_block_sampler_can_draw_the_last_valid_block() -> None:
    generator = _HighStartGenerator()
    indices = _moving_block_indices(10, 3, generator)  # type: ignore[arg-type]

    assert generator.high == 8
    assert 9 in indices


class TestMonthlyAggregation:
    """The estimator must see a real monthly time series.

    The panel is stored sorted by instrument class and then period, so every
    month of one class precedes every month of the other. Newey-West and the
    moving-block bootstrap treat the rows as one sequence, but calendar time
    jumps backwards at the class boundary, so a twelve-month block could
    straddle a fifteen-year gap.
    """

    @staticmethod
    def _stacked() -> pd.DataFrame:
        months = pd.date_range("2011-01-31", periods=6, freq="ME")
        rows = []
        for cls, opening, flow in (("a", 1000.0, 50.0), ("b", 100.0, -10.0)):
            for index, period in enumerate(months):
                rows.append(
                    {
                        "instrument_class": cls,
                        "period": period,
                        "opening_outstanding_mio_eur": opening,
                        "repriced_lower_bound_mio_eur": max(flow, 0.0),
                        "spread_widening_pp": float(index),
                        "spread_narrowing_pp": 0.0,
                        "post_policy_break": False,
                        "average_residual_term_years": 7.0,
                        "share_fixed_rate_pct": 86.0,
                    }
                )
        return pd.DataFrame(rows).sort_values(["instrument_class", "period"])

    def test_the_stacked_panel_is_not_ordered_by_time(self) -> None:
        """The defect this aggregation exists to fix."""
        assert not self._stacked()["period"].is_monotonic_increasing

    def test_aggregation_restores_monotonic_calendar_time(self) -> None:
        aggregated = monthly_retail_series(self._stacked())
        assert aggregated["period"].is_monotonic_increasing

    def test_one_row_per_month(self) -> None:
        aggregated = monthly_retail_series(self._stacked())
        assert len(aggregated) == 6
        assert not aggregated["period"].duplicated().any()

    def test_the_share_is_value_weighted_not_an_average_of_shares(self) -> None:
        """A small class must not move the outcome as much as a large one."""
        aggregated = monthly_retail_series(self._stacked())
        # Class a contributes 50 of repriced euros on 1000; class b nothing on 100.
        assert aggregated["repriced_share"].iloc[0] == pytest.approx(50.0 / 1100.0)
        # Averaging the two class shares equally would let the small, inactive
        # class halve the measured intensity. Weighting by euros does not.
        equally_weighted = (50.0 / 1000.0 + 0.0 / 100.0) / 2.0
        assert float(aggregated["repriced_share"].iloc[0]) > equally_weighted

    def test_a_covariate_differing_within_a_month_is_rejected(self) -> None:
        """Taking the first value would silently discard the difference."""
        stacked = self._stacked()
        stacked.loc[stacked["instrument_class"].eq("b"), "spread_widening_pp"] = 99.0
        with pytest.raises(ValidationError, match="differs across instrument classes"):
            monthly_retail_series(stacked)
