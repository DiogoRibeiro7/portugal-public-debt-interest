from pathlib import Path

import pandas as pd

from pt_debt_interest.plotting import generate_all_plots
from pt_debt_interest.reporting import generate_report


def _fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2021, 2022, 2023],
            "interest_mio_eur": [5000.0, 4800.0, 5500.0],
            "interest_pct_gdp": [2.2, 2.0, 2.1],
            "debt_pct_gdp": [125.0, 115.0, 105.0],
            "implicit_interest_rate_pct": [2.0, 1.8, 2.1],
            "overall_balance_pct_gdp": [-2.0, -0.3, 1.0],
            "primary_balance_pct_gdp": [0.2, 1.7, 3.1],
            "ten_year_yield_pct": [0.3, 1.7, 3.0],
            "nominal_gdp_growth_pct": [None, 11.0, 8.0],
            "real_gdp_growth_pct": [5.6, 6.8, 2.5],
            "gdp_deflator_growth_pct": [None, 3.9, 5.4],
            "debt_stabilising_primary_balance_pct_gdp": [None, -9.0, -6.0],
            "stock_flow_adjustment_pct_gdp": [None, -1.0, 0.5],
            "source": ["Eurostat", "Eurostat", "Eurostat"],
            "accounting_basis": ["ESA2010", "ESA2010", "ESA2010"],
            "observation_status": ["observed", "observed", "observed"],
        }
    )


def test_generate_all_plots_writes_png_svg_and_manifest(tmp_path: Path) -> None:
    paths = generate_all_plots(_fixture_frame(), tmp_path)
    names = {path.name for path in paths}

    assert "01_interest_pct_gdp.png" in names
    assert "01_interest_pct_gdp.svg" in names
    assert "figures_manifest.csv" in names


def test_generate_report_writes_generated_values(tmp_path: Path) -> None:
    destination = generate_report(_fixture_frame(), tmp_path / "summary.md", 1995, [100])
    content = destination.read_text(encoding="utf-8")

    assert "2023" in content
    assert "5.5 billion" in content
    assert "Static full-pass-through sensitivities" in content
