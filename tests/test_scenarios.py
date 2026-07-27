import pytest

from pt_debt_interest.scenarios import (
    refinancing_pass_through,
    refinancing_path_from_gdp,
    static_rate_shock_table,
)


def test_static_rate_shock_table_labels_assumptions() -> None:
    result = static_rate_shock_table(90.0, [100])

    assert result.loc[0, "additional_interest_pct_gdp_full_pass_through"] == pytest.approx(0.9)
    assert result.loc[0, "scenario_kind"] == "static_full_pass_through"
    assert result.loc[0, "baseline_debt_pct_gdp"] == 90.0


def test_static_rate_shock_table_rejects_non_positive_debt() -> None:
    with pytest.raises(ValueError, match="latest_debt_pct_gdp must be positive"):
        static_rate_shock_table(0.0, [100])


def test_static_rate_shock_table_rejects_non_finite_debt() -> None:
    with pytest.raises(ValueError, match="latest_debt_pct_gdp must be positive"):
        static_rate_shock_table(float("nan"), [100])


def test_static_rate_shock_table_rejects_non_finite_shock() -> None:
    with pytest.raises(ValueError, match="shock_bps must be a finite whole number"):
        static_rate_shock_table(90.0, [float("nan")])


def test_static_rate_shock_table_rejects_fractional_shock() -> None:
    with pytest.raises(ValueError, match="shock_bps must be a finite whole number"):
        static_rate_shock_table(90.0, [12.5])


def test_refinancing_pass_through_supports_negative_shock() -> None:
    result = refinancing_pass_through(2.0, 100.0, -100, [0.25, 0.25])

    assert result.loc[0, "additional_interest_pct_gdp"] == pytest.approx(-0.25)
    assert result.loc[1, "interest_pct_gdp_scenario"] == pytest.approx(1.5)


def test_refinancing_pass_through_rejects_invalid_shares() -> None:
    with pytest.raises(ValueError, match="outstanding stock"):
        refinancing_pass_through(2.0, 100.0, 100, [0.8, 0.3])


def test_refinancing_pass_through_rejects_non_finite_shares() -> None:
    with pytest.raises(ValueError, match="shares must be finite"):
        refinancing_pass_through(2.0, 100.0, 100, [float("nan")])


def test_refinancing_pass_through_rejects_non_positive_debt() -> None:
    with pytest.raises(ValueError, match="debt_pct_gdp must be positive"):
        refinancing_pass_through(2.0, -100.0, 100, [0.2])


def test_refinancing_pass_through_rejects_non_finite_shock() -> None:
    with pytest.raises(ValueError, match="shock_bps must be a finite whole number"):
        refinancing_pass_through(2.0, 100.0, float("inf"), [0.2])


def test_refinancing_path_requires_matching_gdp_path() -> None:
    with pytest.raises(ValueError, match="same length"):
        refinancing_path_from_gdp(5000.0, 250000.0, 100, [0.2, 0.2], [250000.0])


def test_refinancing_path_rejects_non_positive_debt_stock() -> None:
    with pytest.raises(ValueError, match="debt_stock_mio_eur must be positive"):
        refinancing_path_from_gdp(5000.0, 0.0, 100, [0.2], [250000.0])


def test_refinancing_path_rejects_non_finite_gdp_path() -> None:
    with pytest.raises(ValueError, match="nominal GDP path must contain positive values"):
        refinancing_path_from_gdp(5000.0, 250000.0, 100, [0.2], [float("nan")])


def test_refinancing_path_rejects_fractional_shock() -> None:
    with pytest.raises(ValueError, match="shock_bps must be a finite whole number"):
        refinancing_path_from_gdp(5000.0, 250000.0, 12.5, [0.2], [250000.0])
