import numpy as np
import pandas as pd
import pytest

from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.interest_decomposition import (
    DEFAULT_DECOMPOSITION_INTERVALS,
    build_interest_burden_counterfactuals,
    build_interest_burden_decomposition,
    build_interest_burden_decomposition_inputs,
)
from pt_debt_interest.latex_tables import headline_macros


def _frame() -> pd.DataFrame:
    years = [1995, 1996, 2000, 2007, 2014, 2019, 2020, 2021, 2022, 2023, 2025]
    debt = [95.0, 100.0, 110.0, 140.0, 210.0, 230.0, 240.0, 235.0, 220.0, 215.0, 200.0]
    gdp = [100.0, 108.0, 140.0, 180.0, 210.0, 250.0, 260.0, 270.0, 280.0, 295.0, 310.0]
    rates = [0.050, 0.048, 0.042, 0.038, 0.035, 0.025, 0.023, 0.021, 0.019, 0.020, 0.022]
    interest = [4.75]
    for index in range(1, len(years)):
        average_debt = (debt[index - 1] + debt[index]) / 2.0
        interest.append(rates[index] * average_debt)
    official = [
        round(value / current_gdp * 100.0, 1)
        for value, current_gdp in zip(interest, gdp, strict=True)
    ]
    return pd.DataFrame(
        {
            "year": years,
            "interest_mio_eur": interest,
            "interest_pct_gdp": official,
            "average_debt_interest_rate": rates,
            "debt_mio_eur": debt,
            "nominal_gdp_mio_eur": gdp,
            "observation_status": ["observed"] * len(years),
            "regime": ["sample"] * len(years),
            "debt_pct_gdp": [
                debt_value / gdp_value * 100.0
                for debt_value, gdp_value in zip(debt, gdp, strict=True)
            ],
            "government_expenditure_mio_eur": [50.0] * len(years),
            "government_expenditure_pct_gdp": [45.0] * len(years),
            "government_revenue_mio_eur": [52.0] * len(years),
            "government_revenue_pct_gdp": [47.0] * len(years),
            "ten_year_yield_pct": [3.0] * len(years),
            "overall_balance_pct_gdp": [0.0] * len(years),
            "primary_balance_pct_gdp": [2.0] * len(years),
            "nominal_gdp_growth_pct": [np.nan] + [4.0] * (len(years) - 1),
            "real_gdp_growth_pct": [2.0] * len(years),
            "gdp_deflator_growth_pct": [2.0] * len(years),
            "average_debt_interest_rate_pct": [rate * 100.0 for rate in rates],
        }
    )


def test_symmetric_decomposition_is_exact() -> None:
    result = build_interest_burden_decomposition(_frame(), intervals=((2014, 2025),))
    row = result.iloc[0]

    assert row.total_change_pp == pytest.approx(
        row.rate_effect_pp + row.debt_exposure_effect_pp
    )
    assert row.decomposition_reconciliation_error_pp == pytest.approx(0.0, abs=1e-12)


def test_symmetric_decomposition_has_no_interaction_term() -> None:
    result = build_interest_burden_decomposition(_frame())

    assert not any("interaction" in column for column in result.columns)


def test_decomposition_uses_unrounded_nominal_inputs() -> None:
    annual = build_interest_burden_decomposition_inputs(_frame())
    year_2025 = annual.loc[annual["year"].eq(2025)].iloc[0]

    assert year_2025.reconstructed_interest_burden_pct_gdp == pytest.approx(
        _frame().loc[_frame()["year"].eq(2025), "interest_mio_eur"].iloc[0] / 310.0 * 100.0
    )
    assert year_2025.reconstructed_interest_burden_pct_gdp != pytest.approx(
        year_2025.official_interest_burden_pct_gdp
    )


def test_decomposition_rejects_missing_endpoint() -> None:
    with pytest.raises(ValidationError, match="missing endpoint"):
        build_interest_burden_decomposition(_frame(), intervals=((2014, 2024),))


def test_decomposition_reconciliation_all_configured_periods() -> None:
    result = build_interest_burden_decomposition(_frame())

    assert set(zip(result["start_year"], result["end_year"], strict=True)) == set(
        DEFAULT_DECOMPOSITION_INTERVALS
    )
    assert np.allclose(result["decomposition_reconciliation_error_pp"], 0.0, atol=1e-12)


def test_counterfactual_matrix_values() -> None:
    result = build_interest_burden_counterfactuals(_frame())
    cross = result.loc[
        result["counterfactual"].eq("rate_2014_with_exposure_2025")
    ].iloc[0]
    annual = build_interest_burden_decomposition_inputs(_frame())
    year_2014 = annual.loc[annual["year"].eq(2014)].iloc[0]
    year_2025 = annual.loc[annual["year"].eq(2025)].iloc[0]

    assert cross.interest_burden_pct_gdp == pytest.approx(
        year_2014.average_debt_rate * year_2025.average_debt_ratio * 100.0
    )
    assert set(result["interpretation"]) == {
        "arithmetic counterfactual, not a causal estimate"
    }


def test_report_context_uses_generated_decomposition_values(tmp_path) -> None:
    path = headline_macros(_frame(), tmp_path, 1995, [50, 100, 200])
    content = path.read_text(encoding="utf-8")
    interval = build_interest_burden_decomposition(_frame(), intervals=((2014, 2025),)).iloc[0]

    assert (
        rf"\newcommand{{\DecompTotalTwentyFourteenToLatestPp}}{{{interval.total_change_pp:.2f}}}"
        in content
    )
