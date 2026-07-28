import pandas as pd
import pytest

from pt_debt_interest.metrics import calculate_metrics


def test_calculate_core_metrics() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, 2022, 2023],
            "interest_mio_eur": [5000.0, 4800.0, 5500.0],
            "government_expenditure_mio_eur": [105000.0, 110000.0, 112000.0],
            "government_expenditure_pct_gdp_official": [47.7, 44.9, 42.3],
            "nominal_gdp_mio_eur": [220000.0, 245000.0, 265000.0],
            "debt_mio_eur": [270000.0, 272000.0, 265000.0],
            "overall_balance_pct_gdp": [-2.0, -0.3, 1.0],
            "real_gdp_growth_pct": [5.6, 6.8, 2.5],
        }
    )
    result = calculate_metrics(frame)
    assert result.loc[1, "interest_pct_gdp"] == pytest.approx(4800 / 245000 * 100)
    assert result.loc[1, "government_expenditure_pct_gdp"] == pytest.approx(44.9)
    assert result.loc[1, "government_expenditure_pct_gdp_calculated"] == pytest.approx(
        110000 / 245000 * 100
    )
    assert result.loc[1, "government_expenditure_eur"] == pytest.approx(110_000_000_000.0)
    assert result.loc[1, "primary_balance_pct_gdp"] == pytest.approx(
        -0.3 + 4800 / 245000 * 100
    )
    assert result.loc[1, "implicit_interest_rate_average_debt_pct"] == pytest.approx(
        4800 / ((270000 + 272000) / 2) * 100
    )
    assert result.loc[1, "effective_interest_rate_debt_dynamics_pct"] == pytest.approx(
        4800 / 270000 * 100
    )
    assert "stock_flow_adjustment_pp" in result.columns
    assert result.loc[1, "reconstructed_debt_ratio_change_pp"] == pytest.approx(
        result.loc[1, "observed_debt_ratio_change_pp"]
    )


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


def test_calculate_metrics_rejects_non_numeric_official_interest_ratio() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
            "interest_pct_gdp_official": ["not-a-number"],
        }
    )

    with pytest.raises(ValueError, match="interest_pct_gdp_official must be numeric"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_finite_overall_balance() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
            "overall_balance_pct_gdp": [float("inf")],
        }
    )

    with pytest.raises(ValueError, match="overall_balance_pct_gdp must be numeric"):
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


def test_calculate_metrics_rejects_fractional_years() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021, 2021.5],
            "interest_mio_eur": [5000.0, 4800.0],
            "nominal_gdp_mio_eur": [220000.0, 245000.0],
            "debt_mio_eur": [270000.0, 272000.0],
        }
    )

    with pytest.raises(ValueError, match="whole-number years"):
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

    with pytest.raises(ValueError, match="real_gdp_growth_pct must be finite"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_numeric_real_growth() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
            "real_gdp_growth_pct": ["not-a-number"],
        }
    )

    with pytest.raises(ValueError, match="real_gdp_growth_pct must be finite"):
        calculate_metrics(frame)


def test_calculate_metrics_rejects_non_finite_real_growth() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
            "real_gdp_growth_pct": [float("inf")],
        }
    )

    with pytest.raises(ValueError, match="real_gdp_growth_pct must be finite"):
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
    assert pd.isna(result.loc[1, "effective_interest_rate_debt_dynamics_pct"])
    assert pd.isna(result.loc[1, "implicit_interest_rate_average_debt_pct"])


def test_calculate_metrics_rejects_fractional_regime_boundary_years() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
        }
    )

    with pytest.raises(ValueError, match="regime boundary start year"):
        calculate_metrics(
            frame,
            regime_boundaries=[{"start": 2020.5, "end": 2022, "label": "Invalid"}],
        )


def test_calculate_metrics_rejects_non_numeric_regime_boundary_years() -> None:
    frame = pd.DataFrame(
        {
            "year": [2021],
            "interest_mio_eur": [5000.0],
            "nominal_gdp_mio_eur": [220000.0],
            "debt_mio_eur": [270000.0],
        }
    )

    with pytest.raises(ValueError, match="regime boundary end year"):
        calculate_metrics(
            frame,
            regime_boundaries=[{"start": 2020, "end": "not-a-year", "label": "Invalid"}],
        )
