import pandas as pd
import pytest

from pt_debt_interest.metrics import calculate_metrics


def test_calculate_core_metrics() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, 2022, 2023],
            "interest_mio_eur": [5000.0, 4800.0, 5500.0],
            "nominal_gdp_mio_eur": [220000.0, 245000.0, 265000.0],
            "debt_mio_eur": [270000.0, 272000.0, 265000.0],
            "overall_balance_pct_gdp": [-2.0, -0.3, 1.0],
            "real_gdp_growth_pct": [5.6, 6.8, 2.5],
        }
    )
    result = calculate_metrics(frame)
    assert result.loc[1, "interest_pct_gdp"] == pytest.approx(4800 / 245000 * 100)
    assert result.loc[1, "primary_balance_pct_gdp"] == pytest.approx(
        -0.3 + 4800 / 245000 * 100
    )
    assert result.loc[1, "implicit_interest_rate_pct"] == pytest.approx(
        4800 / ((270000 + 272000) / 2) * 100
    )
    assert result.loc[1, "implicit_interest_rate_previous_debt_pct"] == pytest.approx(
        4800 / 270000 * 100
    )
    assert "stock_flow_adjustment_pct_gdp" in result.columns


def test_calculate_metrics_rejects_decimal_debt_ratio() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, 2022],
            "interest_mio_eur": [5000.0, 4800.0],
            "nominal_gdp_mio_eur": [220000.0, 245000.0],
            "debt_mio_eur": [270000.0, 272000.0],
            "debt_pct_gdp_official": [1.22, 1.11],
        }
    )

    with pytest.raises(ValueError, match="percentage"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_duplicate_years() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, 2021],
            "interest_mio_eur": [5000.0, 4800.0],
            "nominal_gdp_mio_eur": [220000.0, 245000.0],
            "debt_mio_eur": [270000.0, 272000.0],
        }
    )

    with pytest.raises(ValueError, match="unique years"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_missing_years() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, None],
            "interest_mio_eur": [5000.0, 4800.0],
            "nominal_gdp_mio_eur": [220000.0, 245000.0],
            "debt_mio_eur": [270000.0, 272000.0],
        }
    )

    with pytest.raises(ValueError, match="non-missing years"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_numeric_years() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, "not-a-year"],
            "interest_mio_eur": [5000.0, 4800.0],
            "nominal_gdp_mio_eur": [220000.0, 245000.0],
            "debt_mio_eur": [270000.0, 272000.0],
        }
    )

    with pytest.raises(ValueError, match="numeric years"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_positive_gdp() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [0.0],
            "debt_mio_eur": [270000.0],
        }
    )

    with pytest.raises(ValueError, match="nominal_gdp_mio_eur must be finite and positive"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_numeric_gdp() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": ["not-a-number"],
            "debt_mio_eur": [270000.0],
        }
    )

    with pytest.raises(ValueError, match="nominal_gdp_mio_eur must be finite and positive"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_positive_debt() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [-1.0],
        }
    )

    with pytest.raises(ValueError, match="debt_mio_eur must be finite and positive"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_finite_debt() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [float("inf")],
        }
    )

    with pytest.raises(ValueError, match="debt_mio_eur must be finite and positive"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_invalid_real_growth_factor() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
            "real_gdp_growth_pct": [-100.0],
        }
    )

    with pytest.raises(ValueError, match="real_gdp_growth_pct must be greater than -100"):
        calculate_metrics(frame)


def test_calculate_metrics_nulls_lagged_values_across_basis_break() -> None:
    frame = pd.DataFrame(
        {
            "year": [1994, 1995],
            "interest_mio_eur": [5200.0, 5100.0],
            "nominal_gdp_mio_eur": [100000.0, 110000.0],
            "debt_mio_eur": [65000.0, 70000.0],
            "accounting_basis": ["linked_ESA2010_ESA95_ESA79", "ESA2010"],
        }
    )

    result = calculate_metrics(frame)

    assert pd.isna(result.loc[1, "nominal_gdp_growth_pct"])
    assert pd.isna(result.loc[1, "implicit_interest_rate_pct"])
