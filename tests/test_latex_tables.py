from pathlib import Path

import pandas as pd

from pt_debt_interest.latex_tables import generate_latex_tables


def _annual_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2023, 2024, 2025],
            "interest_pct_gdp": [2.1, 2.0, 1.9],
            "interest_mio_eur": [5553.3, 5934.8, 5964.5],
            "government_expenditure_pct_gdp": [42.0, 42.5, 42.7],
            "government_expenditure_mio_eur": [112000.0, 120000.0, 130941.4],
            "government_revenue_pct_gdp": [43.1, 43.2, 43.4],
            "government_revenue_mio_eur": [114000.0, 124000.0, 133000.0],
            "debt_pct_gdp": [96.9, 93.5, 89.7],
            "implicit_interest_rate_average_debt_pct": [2.08, 2.23, 2.18],
            "overall_balance_pct_gdp": [1.1, 0.6, 0.7],
            "primary_balance_pct_gdp": [3.2, 2.6, 2.6],
            "nominal_gdp_growth_pct": [10.82, 7.19, 5.85],
            "real_gdp_growth_pct": [2.5, 1.9, 1.8],
            "gdp_deflator_growth_pct": [7.49, 5.19, 3.98],
            "ten_year_yield_pct": [3.2, 3.0, 3.08],
            "regime": ["Recent", "Recent", "Recent"],
            "observation_status": ["observed", "observed", "observed"],
        }
    )


def _panel_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2025, 2025],
            "geo_name": ["Portugal", "Italy"],
            "interest_burden_rank": [2, 1],
            "interest_pct_gdp": [1.9, 3.9],
            "debt_pct_gdp": [89.7, 137.1],
            "implicit_interest_rate_average_debt_pct": [2.18, 2.87],
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
        main_start_year=2023,
        shocks_bps=[100],
        panel_frame=_panel_frame(),
    )
    names = {path.name for path in paths}

    assert "summary_statistics.tex" in names
    assert "regime_averages.tex" in names
    assert "recent_dynamics.tex" in names
    assert "european_comparison_2025.tex" in names
    assert "static_sensitivities.tex" in names
    assert "annual_portugal_table.tex" in names


def test_generated_latex_tables_use_input_values(tmp_path: Path) -> None:
    generate_latex_tables(
        _annual_frame(),
        tmp_path,
        main_start_year=2023,
        shocks_bps=[100],
        panel_frame=_panel_frame(),
    )

    summary = (tmp_path / "summary_statistics.tex").read_text(encoding="utf-8")
    recent = (tmp_path / "recent_dynamics.tex").read_text(encoding="utf-8")
    comparison = (tmp_path / "european_comparison_2025.tex").read_text(encoding="utf-8")
    shock = (tmp_path / "static_sensitivities.tex").read_text(encoding="utf-8")

    assert "Interest/GDP" in summary
    assert "1.900" in summary
    assert "2025 & 1.9 & 5964.5 & 89.7" in recent
    assert "1 & Italy & 3.9 & 137.1" in comparison
    assert "89.70 & 100 & 0.010 & 0.897" in shock
