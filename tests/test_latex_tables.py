from pathlib import Path

import pandas as pd

from pt_debt_interest.latex_tables import generate_latex_tables


def _annual_frame() -> pd.DataFrame:
    years = [2014, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    return pd.DataFrame(
        {
            "year": years,
            "interest_pct_gdp": [4.8, 2.9, 2.8, 2.4, 1.9, 2.1, 2.0, 1.9],
            "interest_mio_eur": [
                8334.4,
                6226.9,
                5697.1,
                5117.8,
                4608.0,
                5553.3,
                5934.8,
                5964.5,
            ],
            "government_expenditure_pct_gdp": [50.0, 42.5, 49.0, 47.0, 44.0, 42.0, 42.5, 42.7],
            "government_expenditure_mio_eur": [
                90000.0,
                100000.0,
                105000.0,
                108000.0,
                110000.0,
                112000.0,
                120000.0,
                130941.4,
            ],
            "government_revenue_pct_gdp": [42.0, 43.0, 43.2, 43.0, 43.1, 43.1, 43.2, 43.4],
            "government_revenue_mio_eur": [
                76000.0,
                95000.0,
                98000.0,
                100000.0,
                109000.0,
                114000.0,
                124000.0,
                133000.0,
            ],
            "debt_pct_gdp": [132.5, 116.1, 134.1, 123.9, 111.2, 96.9, 93.5, 89.7],
            "average_debt_interest_rate_pct": [
                3.68,
                2.50,
                2.20,
                1.90,
                1.71,
                2.08,
                2.23,
                2.18,
            ],
            "average_debt_interest_rate": [
                0.0368,
                0.0250,
                0.0220,
                0.0190,
                0.0171,
                0.0208,
                0.0223,
                0.0218,
            ],
            "debt_dynamics_interest_rate": [
                0.0380,
                0.0252,
                0.0221,
                0.0192,
                0.0173,
                0.0210,
                0.0225,
                0.0220,
            ],
            "interest_growth_contribution": [
                0.0100,
                -0.0200,
                0.1000,
                -0.0700,
                -0.1050,
                -0.0780,
                -0.0430,
                -0.0320,
            ],
            "primary_balance_contribution": [
                0.0260,
                -0.0300,
                0.0300,
                0.0040,
                -0.0160,
                -0.0320,
                -0.0260,
                -0.0260,
            ],
            "stock_flow_adjustment": [
                -0.0200,
                0.0000,
                0.0200,
                -0.0360,
                -0.0060,
                -0.0330,
                0.0350,
                0.0200,
            ],
            "observed_debt_ratio_change": [
                0.0160,
                -0.0500,
                0.1500,
                -0.1020,
                -0.1270,
                -0.1430,
                -0.0340,
                -0.0380,
            ],
            "reconstructed_debt_ratio_change": [
                0.0160,
                -0.0500,
                0.1500,
                -0.1020,
                -0.1270,
                -0.1430,
                -0.0340,
                -0.0380,
            ],
            "debt_dynamics_reconciliation_error": [0.0] * len(years),
            "overall_balance_pct_gdp": [-7.4, 0.1, -5.8, -2.8, -0.3, 1.1, 0.6, 0.7],
            "primary_balance_pct_gdp": [-2.6, 3.0, -3.0, -0.4, 1.6, 3.2, 2.6, 2.6],
            "nominal_gdp_growth_pct": [1.47, 4.63, -6.27, 7.69, 12.69, 10.82, 7.19, 5.85],
            "real_gdp_growth_pct": [0.8, 2.7, -8.2, 5.6, 7.0, 2.5, 1.9, 1.8],
            "gdp_deflator_growth_pct": [0.7, 1.8, 2.1, 2.0, 5.31, 7.49, 5.19, 3.98],
            "ten_year_yield_pct": [3.8, 0.8, 0.4, 0.3, 2.0, 3.2, 3.0, 3.08],
            "regime": [
                "Sovereign-debt crisis and adjustment",
                "Pre recent",
                "Pandemic",
                "Pandemic",
                "Inflation and monetary tightening",
                "Inflation and monetary tightening",
                "Inflation and monetary tightening",
                "Inflation and monetary tightening",
            ],
            "observation_status": ["observed"] * len(years),
        }
    )


def _panel_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2025, 2025],
            "geo": ["PT", "IT"],
            "geo_name": ["Portugal", "Italy"],
            "interest_burden_rank": [2, 1],
            "interest_pct_gdp": [1.9, 3.9],
            "debt_pct_gdp": [89.7, 137.1],
            "average_debt_interest_rate_pct": [2.18, 2.87],
            "ten_year_yield_pct": [3.08, 3.59],
            "primary_balance_pct_gdp": [2.6, 0.8],
            "is_aggregate": [False, False],
            "observation_status": ["observed", "observed"],
        }
    )


def test_generate_latex_tables_writes_expected_fragments(tmp_path: Path) -> None:
    paths = generate_latex_tables(
        _annual_frame(),
        tmp_path,
        main_start_year=2014,
        shocks_bps=[50, 100, 200],
        panel_frame=_panel_frame(),
    )
    names = {path.name for path in paths}

    assert "summary_statistics.tex" in names
    assert "paper_headlines.tex" in names
    assert "regime_averages.tex" in names
    assert "recent_dynamics.tex" in names
    assert "european_comparison_2025.tex" in names
    assert "static_sensitivities.tex" in names
    assert "annual_portugal_table.tex" in names
    assert "debt_dynamics_diagnostic_2020_2025.tex" in names


def test_generated_latex_tables_use_input_values(tmp_path: Path) -> None:
    generate_latex_tables(
        _annual_frame(),
        tmp_path,
        main_start_year=2014,
        shocks_bps=[50, 100, 200],
        panel_frame=_panel_frame(),
    )

    summary = (tmp_path / "summary_statistics.tex").read_text(encoding="utf-8")
    recent = (tmp_path / "recent_dynamics.tex").read_text(encoding="utf-8")
    comparison = (tmp_path / "european_comparison_2025.tex").read_text(encoding="utf-8")
    shock = (tmp_path / "static_sensitivities.tex").read_text(encoding="utf-8")
    headlines = (tmp_path / "paper_headlines.tex").read_text(encoding="utf-8")
    diagnostic = (tmp_path / "debt_dynamics_diagnostic_2020_2025.tex").read_text(
        encoding="utf-8"
    )

    assert "Interest/GDP" in summary
    assert "1.900" in summary
    assert "2025 & 1.9 & 5964.5 & 89.7" in recent
    assert "1 & Italy & 3.9 & 137.1" in comparison
    assert "89.70 & 100 & 0.010 & 0.897" in shock
    assert r"\newcommand{\LatestInterestPctGdp}{1.90}" in headlines
    assert r"\newcommand{\PortugalComparatorRankWord}{second}" in headlines
    assert "Debt-dynamics diagnostic table" in diagnostic
    assert "2025 & 1.90" in diagnostic
