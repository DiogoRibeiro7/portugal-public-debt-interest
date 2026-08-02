"""Guards for the repricing panel.

The bound on repriced amount is one-sided by design. These tests pin that
asymmetry, because treating a net-outflow month as zero repricing would assume
exactly what the data cannot show.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pt_debt.repricing.panel import (
    POLICY_BREAK,
    add_competing_return_spread,
    build_repricing_panel,
    reconcile_to_aggregate_debt,
    validate_panel,
)
from pt_debt_interest.exceptions import ValidationError


def _tidy(series: str, values: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": pd.to_datetime(list(values)),
            "series": series,
            "value": list(values.values()),
        }
    )


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.Series]]:
    months = pd.date_range("2023-01-31", periods=8, freq="ME")
    keys = [month.strftime("%Y-%m-%d") for month in months]

    savings = dict(
        zip(keys, [100.0, 130.0, 180.0, 175.0, 176.0, 176.0, 170.0, 172.0], strict=False)
    )
    treasury = dict(zip(keys, [50.0] * 8, strict=False))
    total = dict(zip(keys, [1000.0] * 8, strict=False))

    stock = pd.concat(
        [
            _tidy("savings_certificates_mio_eur", savings),
            _tidy("treasury_certificates_mio_eur", treasury),
            _tidy("total_debt_mio_eur", total),
        ],
        ignore_index=True,
    )
    indicators = pd.concat(
        [
            _tidy("average_residual_term_years", dict(zip(keys, [7.2] * 8, strict=False))),
            _tidy("share_fixed_rate_pct", dict(zip(keys, [80.0] * 8, strict=False))),
        ],
        ignore_index=True,
    )
    covariates = {
        "short_rate": pd.Series([2.0, 2.5, 3.0, 3.5, 3.5, 3.5, 3.5, 3.5], index=months),
        "deposit_rate": pd.Series([1.0, 1.2, 1.4, 1.6, 2.0, 2.5, 3.0, 3.6], index=months),
    }
    return stock, indicators, covariates


def test_repriced_bound_is_one_sided() -> None:
    stock, indicators, covariates = _inputs()
    panel = build_repricing_panel(stock, indicators, covariates)
    savings = panel.loc[panel["instrument_class"].eq("savings_certificates")]
    savings = savings.set_index("period")

    # An inflow month: the bound equals the net flow.
    inflow = savings.loc[pd.Timestamp("2023-02-28")]
    assert inflow["net_flow_mio_eur"] == pytest.approx(30.0)
    assert inflow["repriced_lower_bound_mio_eur"] == pytest.approx(30.0)
    assert inflow["net_outflow_mio_eur"] == pytest.approx(0.0)

    # An outflow month: the bound is zero, and the outflow is carried
    # separately rather than being asserted as zero repricing.
    outflow = savings.loc[pd.Timestamp("2023-04-30")]
    assert outflow["net_flow_mio_eur"] == pytest.approx(-5.0)
    assert outflow["repriced_lower_bound_mio_eur"] == pytest.approx(0.0)
    assert outflow["net_outflow_mio_eur"] == pytest.approx(5.0)


def test_accounting_closes_exactly() -> None:
    stock, indicators, covariates = _inputs()
    panel = build_repricing_panel(stock, indicators, covariates)
    residual = (
        panel["opening_outstanding_mio_eur"]
        + panel["net_flow_mio_eur"]
        - panel["outstanding_mio_eur"]
    ).abs()
    assert residual.max() == pytest.approx(0.0, abs=1e-9)

    checks = validate_panel(panel)
    errors = checks.loc[checks["severity"].eq("error")]
    assert errors["passed"].all(), errors.to_dict("records")


def test_covariates_are_lagged() -> None:
    """No estimate may use information unavailable at the decision point."""
    stock, indicators, covariates = _inputs()
    panel = build_repricing_panel(stock, indicators, covariates)
    panel = add_competing_return_spread(panel, "short_rate", "deposit_rate")

    savings = panel.loc[panel["instrument_class"].eq("savings_certificates")]
    savings = savings.set_index("period")

    # First usable month carries no lagged spread.
    assert pd.isna(savings["competing_return_spread_pp"].iloc[0])
    # March's spread is February's: 2.5 - 1.2.
    assert savings.loc[pd.Timestamp("2023-03-31"), "competing_return_spread_pp"] == (
        pytest.approx(1.3)
    )
    assert savings["covariate_lag_months"].eq(1).all()


def test_spread_split_into_signed_parts() -> None:
    stock, indicators, covariates = _inputs()
    panel = build_repricing_panel(stock, indicators, covariates)
    panel = add_competing_return_spread(panel, "short_rate", "deposit_rate")
    usable = panel.dropna(subset=["competing_return_spread_pp"])

    rebuilt = usable["spread_widening_pp"] - usable["spread_narrowing_pp"]
    assert rebuilt.to_numpy() == pytest.approx(usable["competing_return_spread_pp"].to_numpy())
    assert (usable["spread_widening_pp"] >= 0).all()
    assert (usable["spread_narrowing_pp"] >= 0).all()


def test_policy_break_flag() -> None:
    stock, indicators, covariates = _inputs()
    panel = build_repricing_panel(stock, indicators, covariates)
    assert pd.Timestamp("2023-06-30") == POLICY_BREAK

    before = panel.loc[panel["period"].eq(pd.Timestamp("2023-05-31"))]
    after = panel.loc[panel["period"].eq(pd.Timestamp("2023-07-31"))]
    assert not before["post_policy_break"].any()
    assert after["post_policy_break"].all()
    assert before["months_since_policy_break"].iloc[0] == -1
    assert after["months_since_policy_break"].iloc[0] == 1


def test_missing_series_is_refused() -> None:
    stock, indicators, covariates = _inputs()
    stock = stock.loc[~stock["series"].eq("total_debt_mio_eur")]
    with pytest.raises(ValidationError, match="total_debt_mio_eur"):
        build_repricing_panel(stock, indicators, covariates)


def test_reconciliation_reports_the_gap_rather_than_asserting_agreement() -> None:
    stock, indicators, covariates = _inputs()
    panel = build_repricing_panel(stock, indicators, covariates)
    # A December period is needed for the annual comparison.
    december = panel.iloc[[0]].copy()
    december["period"] = pd.Timestamp("2023-12-31")
    december["total_debt_mio_eur"] = 1000.0
    panel = pd.concat([panel, december], ignore_index=True)

    burden = pd.DataFrame({"year": [2023], "debt_mio_eur": [900.0]})
    comparison = reconcile_to_aggregate_debt(panel, burden)

    row = comparison.iloc[0]
    assert row["difference_mio_eur"] == pytest.approx(-100.0)
    assert row["difference_pct_of_maastricht"] == pytest.approx(-100.0 / 900.0 * 100.0)
